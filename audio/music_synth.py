"""Nhạc nền tổng hợp theo "chất" từng nước (mục 9), dài bằng video, tự lặp có biến tấu.

  vietnam : drone trầm + trống trận + giai điệu ngũ cung kiểu sáo
  korea   : trống buk (nhịp 3) + giai điệu ngũ cung kiểu Hàn, rung (nonghyeon) sâu, gảy kiểu gayageum
  japan   : trống taiko + thang âm in / miyako-bushi, sáo shakuhachi (hơi thở, luyến), gảy kiểu koto
  england : drone quãng 5 + trống trận + giai điệu điệu thức dorian kiểu Trung cổ

Tâm trạng: yen_binh, cang_thang, cao_trao, bi_trang, ket_thuc.
generate(country, segments=[(t0, t1, mood), ...], seed) -> mảng stereo float32 (n, 2) ở 44100 Hz.
"""
import math

import numpy as np

SR = 44100
MOODS = ["yen_binh", "cang_thang", "cao_trao", "bi_trang", "ket_thuc"]

# tonic (Hz), thang âm (bán cung so với tonic), nhạc cụ
STYLES = {
    "vietnam": {"tonic": 146.83, "scale": [0, 2, 5, 7, 9], "lead": "flute", "pluck": "dan", "drum": "tron",
                "vib": (5.0, 0.004), "slide": 0.08},
    "korea": {"tonic": 138.59, "scale": [0, 3, 5, 7, 10], "lead": "flute", "pluck": "gayageum", "drum": "buk",
              "vib": (3.2, 0.012), "slide": 0.12, "meter": 3},
    "japan": {"tonic": 146.83, "scale": [0, 1, 5, 7, 8], "lead": "shakuhachi", "pluck": "koto", "drum": "taiko",
              "vib": (4.5, 0.006), "slide": 0.15},
    "england": {"tonic": 146.83, "scale": [0, 2, 3, 5, 7, 9, 10], "lead": "recorder", "pluck": "harp", "drum": "tabor",
                "vib": (5.5, 0.003), "slide": 0.0},
}
MOOD = {
    "yen_binh": {"bpm": 62, "drum": 0.0, "drone": 0.10, "lead": 0.10, "density": 0.45, "pluck": 0.07, "oct": 1},
    "cang_thang": {"bpm": 78, "drum": 0.35, "drone": 0.14, "lead": 0.06, "density": 0.3, "pluck": 0.05, "oct": 1, "tense": True},
    "cao_trao": {"bpm": 96, "drum": 0.75, "drone": 0.16, "lead": 0.10, "density": 0.7, "pluck": 0.06, "oct": 1},
    "bi_trang": {"bpm": 64, "drum": 0.45, "drone": 0.15, "lead": 0.10, "density": 0.4, "pluck": 0.03, "oct": 0},
    "ket_thuc": {"bpm": 56, "drum": 0.1, "drone": 0.10, "lead": 0.09, "density": 0.35, "pluck": 0.06, "oct": 0, "resolve": True},
}


def _bandnoise(rng, n, lo, hi):
    x = rng.standard_normal(max(2, n))
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    y = np.fft.irfft(X, len(x))
    return y / (np.abs(y).max() + 1e-9)


# ---------------------------------------------------------------- nhạc cụ
def lead_note(kind, f, d, rng, vib=(5.0, 0.004), f_prev=None, slide=0.0):
    n = int(SR * d)
    t = np.arange(n) / SR
    rate, depth = vib
    vdepth = depth * np.clip((t - 0.25) / 0.4, 0, 1)
    ff = f * (1 + vdepth * np.sin(2 * np.pi * rate * t))
    if f_prev and slide > 0:
        ff = ff + (f_prev - f) * np.exp(-t / slide) * (t < slide * 4)
    ph = 2 * np.pi * np.cumsum(ff) / SR
    att = {"shakuhachi": 0.18, "flute": 0.1, "recorder": 0.05}.get(kind, 0.1)
    env = np.minimum(1, t / att) * np.minimum(1, (d - t) / 0.25).clip(0, 1) * (0.85 + 0.15 * np.exp(-t * 2))
    if kind == "recorder":
        s = np.sin(ph) + 0.25 * np.sin(2 * ph) + 0.12 * np.sin(3 * ph)
        breath = 0.05
    elif kind == "shakuhachi":
        s = np.sin(ph) + 0.12 * np.sin(2 * ph)
        breath = 0.22
        env *= 1 + 0.25 * np.sin(np.pi * np.clip(t / d, 0, 1))
    else:
        s = np.sin(ph) + 0.18 * np.sin(2 * ph) + 0.05 * np.sin(3 * ph)
        breath = 0.1
    s += breath * _bandnoise(rng, n, f * 1.5, f * 6) * (0.4 + 0.6 * np.exp(-t * 4))
    return s * env


def pluck_note(kind, f, d, rng):
    n = int(SR * d)
    t = np.arange(n) / SR
    s = np.zeros(n)
    dec = {"koto": 2.5, "gayageum": 2.0, "harp": 1.8, "dan": 2.8}.get(kind, 2.2)
    bend = 1.0
    if kind == "gayageum":
        bend = 1 + 0.01 * np.sin(2 * np.pi * 4 * t) * np.clip((t - 0.2) / 0.3, 0, 1)
    for h, a in [(1, 1.0), (2, 0.5), (3, 0.25), (4, 0.12), (5, 0.06)]:
        s += a * np.sin(2 * np.pi * f * h * np.cumsum(np.ones(n) * bend) / SR) * np.exp(-t * dec * h ** 0.7)
    s *= np.minimum(1, t / 0.004)
    return s


def drum_hit(kind, big, rng):
    if kind == "taiko":
        d, f0, dec = 1.4, 48, 3.5 if big else 6
    elif kind == "buk":
        d, f0, dec = 1.0, 62, 5 if big else 9
    elif kind == "tabor":
        d, f0, dec = 0.5, 140 if not big else 70, 10 if not big else 6
    else:
        d, f0, dec = 0.9, 55, 5 if big else 9
    n = int(SR * d)
    t = np.arange(n) / SR
    f = f0 * (1 + 1.2 * np.exp(-t * 25))
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * dec)
    s += 0.15 * rng.standard_normal(n) * np.exp(-t * 40)
    if kind == "tabor" and not big:
        s += 0.5 * _bandnoise(rng, n, 1500, 7000) * np.exp(-t * 30)
    if kind == "taiko" and not big:   # tiếng gõ vành "ka"
        s = 0.6 * _bandnoise(rng, n, 1200, 5000) * np.exp(-t * 45)
    return s * (1.0 if big else 0.55)


# ---------------------------------------------------------------- reverb (tích chập FFT theo khối)
def reverb(x, decay=2.2, mix=0.25, seed=1):
    rng = np.random.default_rng(seed)
    n_ir = int(SR * decay)
    t = np.arange(n_ir) / SR
    ir = rng.standard_normal(n_ir) * np.exp(-t * 6.9 / decay)
    ir[: int(SR * 0.02)] = 0
    ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
    B = 1 << 17
    nfft = 1 << int(math.ceil(math.log2(B + n_ir)))
    IR = np.fft.rfft(ir, nfft)
    out = np.zeros(len(x) + n_ir)
    for i in range(0, len(x), B):
        blk = x[i:i + B]
        y = np.fft.irfft(np.fft.rfft(blk, nfft) * IR, nfft)[: len(blk) + n_ir]
        out[i:i + len(y)] += y
    return x * (1 - mix) + out[: len(x)] * mix * 1.6


# ---------------------------------------------------------------- tạo nhạc
def _smooth(x, w):
    """Trung bình trượt nhanh (cumsum) độ rộng w mẫu."""
    c = np.cumsum(np.r_[np.zeros(w // 2 + 1), x, np.full(w // 2 + 1, x[-1])])
    return ((c[w:] - c[:-w]) / w)[: len(x)]


def _mood_at(segments, t):
    for a, b, m in segments:
        if a <= t < b:
            return m
    return segments[-1][2] if segments else "yen_binh"


def _motif(rng, length, nscale):
    """Motif = bước đi ngẫu nhiên trên thang âm, kết về nốt chủ."""
    deg = [0]
    for _ in range(length - 1):
        step = rng.choice([-2, -1, -1, 1, 1, 2, 0, 3])
        deg.append(int(np.clip(deg[-1] + step, -2, nscale + 3)))
    rhythms = [[2, 1, 1, 2, 2, 4], [1, 1, 2, 1, 1, 2, 4], [3, 1, 2, 2, 4], [2, 2, 1, 1, 2, 4]]
    rhythm = rhythms[int(rng.integers(len(rhythms)))]
    return deg, list(rhythm)


def generate(country, segments, seed=1, total=None):
    st = STYLES.get(country, STYLES["vietnam"])
    rng = np.random.default_rng(seed)
    total = total or (segments[-1][1] if segments else 10.0)
    n = int(SR * total) + SR
    drone = np.zeros(n, np.float32)
    lead = np.zeros(n, np.float32)
    drum = np.zeros(n, np.float32)
    pl = np.zeros(n, np.float32)
    tonic = st["tonic"]
    sc = st["scale"]

    def freq(deg, octave=0):
        o, i = divmod(deg, len(sc))
        return tonic * 2 ** ((sc[i] + 12 * (o + octave)) / 12)

    def add(buf, t0, s, g):
        i = int(t0 * SR)
        if i >= n:
            return
        m = min(len(s), n - i)
        buf[i:i + m] += (g * s[:m]).astype(np.float32)

    # --- drone: liên tục, mức theo tâm trạng (nội suy mượt)
    t = np.arange(n) / SR
    lvl_pts = np.array([MOOD[_mood_at(segments, x)]["drone"] for x in np.arange(0, total + 1, 0.5)])
    lvl = np.interp(t, np.arange(len(lvl_pts)) * 0.5, lvl_pts)
    lvl = _smooth(lvl, SR)
    f_d = tonic / 2
    dr = np.sin(2 * np.pi * f_d * t + 0.3 * np.sin(2 * np.pi * 0.2 * t)) + 0.6 * np.sin(2 * np.pi * f_d * 1.5 * t)
    dr += 0.25 * np.sin(2 * np.pi * f_d * 2 * t + 0.5 * np.sin(2 * np.pi * 0.13 * t))
    if country == "england":
        dr += 0.3 * np.sin(2 * np.pi * f_d * 3 * t) + 0.2 * np.sin(2 * np.pi * f_d * 4 * t)
    tense_pts = np.array([1.0 if MOOD[_mood_at(segments, x)].get("tense") else 0.0 for x in np.arange(0, total + 1, 0.5)])
    tense = _smooth(np.interp(t, np.arange(len(tense_pts)) * 0.5, tense_pts), SR)
    dr += tense * 0.35 * np.sin(2 * np.pi * f_d * 2 ** (1 / 12) * 2 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 3 * t))
    drone[:] = (dr * lvl * 0.6).astype(np.float32)
    del dr, t

    # --- motif chung cho cả bài, biến tấu theo đoạn
    motifs = [_motif(rng, 6, len(sc)) for _ in range(3)]
    form = [0, 0, 1, 0, 2, 1, 0, 2]
    pos = 0.0
    phrase = 0
    f_prev = None
    while pos < total - 1.0:
        mood = _mood_at(segments, pos)
        M = MOOD[mood]
        beat = 60.0 / M["bpm"]
        deg, rhy = motifs[form[phrase % len(form)]]
        var = phrase // len(form)
        shift = [0, 1, -1, 2][var % 4] if mood != "ket_thuc" else 0
        if rng.random() > M["density"] + 0.25:
            pos += beat * 4          # nghỉ một ô nhịp
            phrase += 1
            continue
        for j, (dg, r) in enumerate(zip(deg, rhy)):
            d = r * beat * 0.5 * (1.5 if mood in ("bi_trang", "ket_thuc") else 1)
            if pos + d > total - 0.5:
                break
            if M.get("resolve") and j == len(deg) - 1:
                dg = 0
            if rng.random() < 0.15 and j not in (0, len(deg) - 1):
                pos += d
                continue
            f = freq(dg + shift, M["oct"])
            add(lead, pos, lead_note(st["lead"], f, d * 1.05 + 0.2, rng, st["vib"], f_prev, st["slide"]), M["lead"])
            f_prev = f
            if M["pluck"] and rng.random() < 0.6:
                add(pl, pos, pluck_note(st["pluck"], freq(dg + shift - len(sc), M["oct"]), 2.0, rng), M["pluck"])
            pos += d
        pos += beat * float(rng.choice([1, 2, 2, 3]))
        phrase += 1

    # --- trống theo tâm trạng
    pos = 0.4
    k = 0
    meter = st.get("meter", 4)
    while pos < total - 0.5:
        M = MOOD[_mood_at(segments, pos)]
        beat = 60.0 / M["bpm"]
        if M["drum"] > 0:
            ramp = min(1.0, 0.6 + 0.4 * pos / max(1, total))
            if meter == 3:      # nhịp 3 kiểu semachi: dài-ngắn
                pat = [1.0, 0, 0.5] if M["drum"] < 0.6 else [1.0, 0.5, 0.7]
            else:
                pat = [1.0, 0, 0.6, 0] if M["drum"] < 0.6 else [1.0, 0.4, 0.8, 0.5]
            a = pat[k % len(pat)]
            if a:
                add(drum, pos, drum_hit(st["drum"], a >= 0.8, rng), M["drum"] * a * 0.7 * ramp)
        pos += beat / (1 if meter == 4 else 1.5) if M["drum"] < 0.6 else beat / 2
        k += 1

    wet = reverb(lead + pl, 2.4, 0.35, seed)
    mixm = drone + wet.astype(np.float32) + reverb(drum, 1.2, 0.18, seed + 1).astype(np.float32)
    # stereo nhẹ: lead hơi lệch, drone giữa
    L = mixm + 0.15 * wet
    R = mixm - 0.15 * wet
    out = np.stack([L, R], 1)[: int(SR * total)]
    tt = np.arange(len(out)) / SR
    fade = np.minimum(1, np.minimum(tt / 2.0, (total - tt) / 3.0)).clip(0, 1)
    out *= fade[:, None]
    peak = np.abs(out).max() + 1e-9
    return (out / peak * 0.8).astype(np.float32)
