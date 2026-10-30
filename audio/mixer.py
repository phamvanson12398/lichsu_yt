"""Trộn âm (mục 9): giọng là chính, nhạc tự giảm khi có lời (ducking) và tăng lại ở đoạn không lời,
hiệu ứng + âm nền theo cảnh, fade đầu / cuối. Chuẩn hóa -16 LUFS làm ở bước ghép cuối bằng FFmpeg loudnorm.
"""
import subprocess
import wave

import numpy as np

from audio import music_synth, sfx_synth

SR = 44100


def load_audio(path, sr=SR):
    """Đọc mọi định dạng (wav/mp3/m4a...) qua FFmpeg -> mono float32."""
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"],
                       capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(f"Không đọc được file âm thanh {path}: {p.stderr.decode('utf-8', 'ignore')[:300]}")
    return np.frombuffer(p.stdout, np.float32).copy()


def write_wav(path, x, sr=SR):
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    s = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(s.shape[1])
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(s.tobytes())


def rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)


def _env(x, win=0.05, attack=0.15, release=0.7):
    """Đường bao mức giọng (0..1) để giảm nhạc."""
    hop = int(SR * win)
    n = len(x) // hop + 1
    pad = np.zeros(n * hop, np.float32)
    pad[: len(x)] = np.abs(x)
    lv = pad.reshape(n, hop).mean(1)
    on = (lv > 0.01).astype(np.float32)
    out = np.zeros(n, np.float32)
    a_up = 1 - np.exp(-win / attack)
    a_dn = 1 - np.exp(-win / release)
    v = 0.0
    for i in range(n):
        v += (on[i] - v) * (a_up if on[i] > v else a_dn)
        out[i] = v
    return np.repeat(out, hop)[: len(x)]


def mix(total, voice_clips, events, beds, music_segments, country, seed=1, levels=None, music_file=None):
    """
    voice_clips    : [(t, path)]  các câu đọc
    events         : [(t, tag, gain)] hiệu ứng ngắn
    beds           : [(t0, t1, tag, gain)] âm nền kéo dài theo cảnh
    music_segments : [(t0, t1, mood)]
    trả về mảng stereo float32
    """
    lv = {"voice": 1.0, "music": 0.32, "music_duck": 0.11, "sfx": 0.55, "bed": 0.35}
    lv.update(levels or {})
    n = int(SR * total) + 1
    voice = np.zeros(n, np.float32)
    for t, path in voice_clips:
        v = load_audio(path)
        g = 10 ** ((-20 - rms_db(v)) / 20)          # mỗi câu về cùng mức -20 dBFS RMS
        v = v * min(g, 8.0)
        i = int(t * SR)
        m = min(len(v), n - i)
        if m > 0:
            voice[i:i + m] += v[:m]
    fx = np.zeros((n, 2), np.float32)
    cache = {}
    for t, tag, gain in events:
        if tag not in cache:
            cache[tag] = sfx_synth.make(tag)
        s = cache[tag]
        if s is None:
            continue
        i = int(max(0, t) * SR)
        m = min(len(s), n - i)
        if m > 0:
            fx[i:i + m] += s[:m] * gain * lv["sfx"]
    for k, (t0, t1, tag, gain) in enumerate(beds):
        s = sfx_synth.bed(tag, t1 - t0, seed=k)
        i = int(t0 * SR)
        m = min(len(s), n - i)
        if m > 0:
            fx[i:i + m] += (s[:m] * gain * lv["bed"])[:, None]
    if music_file:
        mus = load_audio(music_file)
        reps = int(np.ceil(n / max(1, len(mus))))
        mus = np.tile(mus, reps)[:n]
        mus = np.stack([mus, mus], 1)
    elif music_segments:
        mus = music_synth.generate(country, music_segments, seed=seed, total=total)
        if len(mus) < n:
            mus = np.vstack([mus, np.zeros((n - len(mus), 2), np.float32)])
        mus = mus[:n]
    else:
        mus = np.zeros((n, 2), np.float32)
    env = _env(voice)
    g_m = lv["music"] + (lv["music_duck"] - lv["music"]) * env
    out = fx + mus * g_m[:, None] + voice[:, None] * lv["voice"]
    tt = np.arange(n) / SR
    fade = np.minimum(1, np.minimum(tt / 0.8, (total - tt) / 2.0)).clip(0, 1)
    out *= fade[:, None]
    peak = np.abs(out).max()
    if peak > 0.98:
        out = np.tanh(out / peak * 1.4) / np.tanh(1.4) * 0.97
    return out.astype(np.float32)
