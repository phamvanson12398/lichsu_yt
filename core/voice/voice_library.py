"""Thư viện giọng (mục 8.2, 8.3):

voices/<ten_giong>/
   ref.wav       đoạn mẫu đã xử lý (3–10 s, mono 24 kHz)
   ref.txt       lời thoại của đoạn mẫu
   prompt.bin    voice_clone_prompt tính sẵn (nếu thư viện hỗ trợ)
   sample.wav    câu nghe thử
   meta.json     {"ten", "loai": "clone"|"design", "instruct", "mo_ta", "ngon_ngu", "toc_do", "ngay_tao", "dong_y", "ref_hash"}
voices/defaults.json   {"default": "...", "by_country": {"japan": "..."}}
"""
import datetime
import hashlib
import json
import os
import platform
import shutil
import subprocess
import tempfile

import numpy as np

from core.config import ROOT
from core.voice.omnivoice_engine import (CONSENT_TEXT, LICENSE_WARNING, OmniVoiceEngine, cer, read_wav, save_wav)

VOICES_DIR = os.path.join(ROOT, "voices")
SAMPLE_TEXT = ("Xin chào các bạn, đây là giọng đọc thử cho kênh lịch sử. Năm chín trăm ba mươi tám, "
               "Ngô Quyền đánh tan quân Nam Hán trên sông Bạch Đằng.")
DESIGN_ATTRS = {
    "gender": ["male", "female"],
    "age": ["child", "teenager", "young adult", "middle-aged", "elderly"],
    "pitch": ["very low pitch", "low pitch", "moderate pitch", "high pitch", "very high pitch"],
}


class Voice:
    def __init__(self, name):
        self.name = name
        self.dir = os.path.join(VOICES_DIR, name)
        if not os.path.isdir(self.dir):
            raise FileNotFoundError(f"Không có giọng '{name}'. Xem danh sách: python main.py voice list")
        with open(os.path.join(self.dir, "meta.json"), encoding="utf-8") as f:
            self.meta = json.load(f)
        self.ref_wav = os.path.join(self.dir, "ref.wav")
        with open(os.path.join(self.dir, "ref.txt"), encoding="utf-8") as f:
            self.ref_text = f.read().strip()
        self._prompt = None

    def clone_prompt(self, eng):
        if self._prompt is not None:
            return self._prompt
        p = os.path.join(self.dir, "prompt.bin")
        pr = OmniVoiceEngine.load_prompt(p)
        if pr is None:
            try:
                pr = eng.clone_prompt(self.ref_wav, self.ref_text)
                if pr is not None:
                    OmniVoiceEngine.save_prompt(pr, p)
            except Exception:
                pr = None
        self._prompt = pr
        return pr


# ---------------------------------------------------------------- danh sách / mặc định
def list_voices():
    out = []
    if not os.path.isdir(VOICES_DIR):
        return out
    for n in sorted(os.listdir(VOICES_DIR)):
        mp = os.path.join(VOICES_DIR, n, "meta.json")
        if os.path.exists(mp):
            with open(mp, encoding="utf-8") as f:
                out.append(json.load(f) | {"_name": n})
    return out


def defaults():
    p = os.path.join(VOICES_DIR, "defaults.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {"default": None, "by_country": {}}


def set_default(name, country=None):
    Voice(name)
    d = defaults()
    if country:
        d.setdefault("by_country", {})[country] = name
    else:
        d["default"] = name
    os.makedirs(VOICES_DIR, exist_ok=True)
    with open(os.path.join(VOICES_DIR, "defaults.json"), "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


def pick_voice(plan_voice, country, cfg):
    """Thứ tự: giọng ghi trong plan.json -> mặc định theo nước -> mặc định kênh -> config. None nếu chưa có giọng nào."""
    d = defaults()
    for n in (plan_voice, d.get("by_country", {}).get(country), d.get("default"), cfg["voice"].get("default"),
              (cfg["voice"].get("default_by_country") or {}).get(country)):
        if n and os.path.isdir(os.path.join(VOICES_DIR, n)):
            return Voice(n)
    return None


def play(path):
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    if platform.system() == "Windows":
        os.startfile(path)  # noqa
    elif platform.system() == "Darwin":
        subprocess.run(["afplay", path])
    else:
        for cmd in (["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path], ["aplay", path]):
            if shutil.which(cmd[0]):
                subprocess.run(cmd)
                return


def delete(name):
    d = os.path.join(VOICES_DIR, name)
    if not os.path.isdir(d):
        raise FileNotFoundError(f"Không có giọng '{name}'")
    shutil.rmtree(d)


# ---------------------------------------------------------------- xử lý file mẫu
def prepare_reference(src, log=print):
    """FFmpeg: wav mono 24 kHz, cắt lặng đầu/cuối, chuẩn hóa âm lượng; chọn đoạn sạch nhất 3–10 s.
    Trả về (audio 24k float32, cảnh_báo[])."""
    tmp = tempfile.mkdtemp(prefix="hvt_ref_")
    out = os.path.join(tmp, "clean.wav")
    af = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.1,areverse,"
          "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.1,areverse,"
          "highpass=f=70,loudnorm=I=-20:TP=-2:LRA=11")
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-ac", "1", "-ar", "24000", "-af", af, out], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"FFmpeg không đọc được file giọng: {r.stderr.decode('utf-8', 'ignore')[:300]}")
    x, sr = read_wav(out)
    shutil.rmtree(tmp, ignore_errors=True)
    warns = []
    total = len(x) / sr
    if total < 3:
        warns.append(f"File giọng quá ngắn ({total:.1f}s). Cần ít nhất 3 giây nói liên tục, tốt nhất 6–10 giây.")
        return x, warns
    hop = int(0.02 * sr)
    n = len(x) // hop
    rms = np.sqrt((x[: n * hop].reshape(n, hop) ** 2).mean(1) + 1e-12)
    db = 20 * np.log10(rms)
    floor = np.percentile(db, 10)
    speech = np.percentile(db, 90)
    snr = speech - floor
    if snr < 15:
        warns.append(f"File có vẻ ỒN (độ chênh tiếng nói / nền chỉ {snr:.0f} dB). Nên thu lại ở phòng yên tĩnh.")
    clip = np.mean(np.abs(x) > 0.99)
    if clip > 0.001:
        warns.append("Âm thanh bị rè / quá to (clipping). Nên thu lại nhỏ hơn.")
    L = min(10.0, total)
    win = int(L / 0.02)
    best, best_i = -1e9, 0
    quiet = db < floor + 6
    for i in range(0, max(1, n - win + 1), 25):
        seg = db[i:i + win]
        long_sil = _longest_run(quiet[i:i + win]) * 0.02
        score = seg.mean() - floor - 4 * max(0, long_sil - 0.6)
        if i > 0 and not quiet[i]:
            score -= 3
        if i + win < n and not quiet[min(n - 1, i + win)]:
            score -= 3
        if score > best:
            best, best_i = score, i
    seg = x[best_i * hop: best_i * hop + win * hop]
    fade = int(0.02 * sr)
    seg[:fade] *= np.linspace(0, 1, fade)
    seg[-fade:] *= np.linspace(1, 0, fade)
    return seg, warns


def _longest_run(b):
    m = c = 0
    for v in b:
        c = c + 1 if v else 0
        m = max(m, c)
    return m


def _save(name, ref_audio, sr, ref_text, meta, sample=None):
    d = os.path.join(VOICES_DIR, name)
    os.makedirs(d, exist_ok=True)
    save_wav(os.path.join(d, "ref.wav"), ref_audio, sr)
    with open(os.path.join(d, "ref.txt"), "w", encoding="utf-8") as f:
        f.write(ref_text.strip())
    if sample is not None:
        save_wav(os.path.join(d, "sample.wav"), sample[0], sample[1])
    meta = dict(meta, ten=name, ngay_tao=datetime.datetime.now().isoformat(timespec="seconds"),
                ref_hash=hashlib.sha1(np.asarray(ref_audio, np.float32).tobytes()).hexdigest()[:12])
    meta.setdefault("ngon_ngu", "vi")
    meta.setdefault("toc_do", 1.0)
    with open(os.path.join(d, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    pp = os.path.join(d, "prompt.bin")
    if os.path.exists(pp):
        os.remove(pp)
    return d


def ask_consent(given=False, ask=input):
    if given:
        return True
    ans = ask(f"Xác nhận: \"{CONSENT_TEXT}\" (gõ co / khong): ").strip().lower()
    return ans in ("co", "có", "c", "y", "yes")


# ---------------------------------------------------------------- (A) giọng nhân bản
def add_clone(name, src, ref_text=None, consent=False, cfg=None, log=print, ask=input, interactive=True, mo_ta=""):
    if not ask_consent(consent, ask):
        raise RuntimeError("Chưa xác nhận đồng ý. Chỉ nhân bản giọng của chính bạn hoặc người đã đồng ý; không nhân bản giọng người nổi tiếng.")
    if cfg.get("kenh_kiem_tien"):
        log(LICENSE_WARNING)
    seg, warns = prepare_reference(src, log)
    for w in warns:
        log("⚠️  " + w)
    if len(seg) / 24000 < 3:
        raise RuntimeError("Đoạn giọng sạch ngắn hơn 3 giây — không đủ để nhân bản.")
    log(f"✔ Đã chọn đoạn mẫu sạch nhất dài {len(seg) / 24000:.1f}s")
    eng = OmniVoiceEngine.get(cfg["voice"], log)
    tmpd = tempfile.mkdtemp(prefix="hvt_v_")
    tmp_ref = os.path.join(tmpd, "ref.wav")
    save_wav(tmp_ref, seg, 24000)
    if not ref_text:
        log("Chưa nhập lời mẫu -> nhận dạng tự động (Whisper)...")
        ref_text = eng.transcribe(tmp_ref) or ""
        log(f"   Máy nghe được: \"{ref_text}\"")
        if interactive:
            fix = ask("Sửa lại lời cho đúng (Enter để giữ nguyên): ").strip()
            ref_text = fix or ref_text
    if not ref_text:
        raise RuntimeError("Cần lời thoại của đoạn mẫu (--text \"...\").")
    log("Tạo câu nghe thử...")
    a, sr = eng.generate(SAMPLE_TEXT, ref_audio=tmp_ref, ref_text=ref_text)
    sample = os.path.join(tmpd, "sample.wav")
    save_wav(sample, a, sr)
    if interactive:
        log(f"▶ Nghe thử: {sample}")
        try:
            play(sample)
        except Exception:
            pass
        if ask("Lưu giọng này? (co / khong): ").strip().lower() not in ("co", "có", "c", "y", "yes"):
            raise RuntimeError("Đã huỷ, không lưu giọng.")
    d = _save(name, seg, 24000, ref_text, {"loai": "clone", "instruct": "", "mo_ta": mo_ta or f"Nhân bản từ {os.path.basename(src)}",
                                           "dong_y": True}, sample=(a, sr))
    shutil.rmtree(tmpd, ignore_errors=True)
    log(f"✔ Đã lưu giọng '{name}' vào {d}")
    return d


# ---------------------------------------------------------------- (B) giọng thiết kế
def design_candidates(instructs, cfg, log=print, text=SAMPLE_TEXT):
    eng = OmniVoiceEngine.get(cfg["voice"], log)
    tmpd = tempfile.mkdtemp(prefix="hvt_design_")
    out = []
    for i, ins in enumerate(instructs):
        log(f"🎙  Ứng viên {i + 1}: \"{ins}\"")
        a, sr = eng.generate(text, instruct=ins)
        p = os.path.join(tmpd, f"ung_vien_{i + 1}.wav")
        save_wav(p, a, sr)
        hyp = eng.transcribe(p) if cfg["voice"].get("qc", True) else None
        score = cer(text, hyp) if hyp is not None else None
        out.append({"instruct": ins, "path": p, "audio": a, "sr": sr, "cer": score})
        log(f"   -> {p}" + (f"  (sai lệch nhận dạng {score:.0%})" if score is not None else ""))
    return out


def save_design(name, cand, text=SAMPLE_TEXT, mo_ta=""):
    """Giữ giọng ổn định: lấy chính file nghe thử làm đoạn mẫu (ref) để nhân bản cho cả video."""
    return _save(name, cand["audio"], cand["sr"], text, {"loai": "design", "instruct": cand["instruct"],
                                                          "mo_ta": mo_ta or f"Giọng thiết kế: {cand['instruct']}", "dong_y": True},
                 sample=(cand["audio"], cand["sr"]))


def choose(cands, auto=False, ask=input, log=print):
    if auto:
        scored = [c for c in cands if c["cer"] is not None]
        best = min(scored, key=lambda c: c["cer"]) if scored else cands[0]
        log(f"🤖 Tự chọn ứng viên: \"{best['instruct']}\"")
        return best
    for i, c in enumerate(cands):
        log(f"  [{i + 1}] {c['instruct']}  —  {c['path']}")
    while True:
        a = ask("Nghe các file trên rồi gõ số ứng viên muốn chọn (p<số> để phát, vd p1): ").strip().lower()
        if a.startswith("p") and a[1:].isdigit() and 1 <= int(a[1:]) <= len(cands):
            try:
                play(cands[int(a[1:]) - 1]["path"])
            except Exception:
                pass
            continue
        if a.isdigit() and 1 <= int(a) <= len(cands):
            return cands[int(a) - 1]


def suggest_instructs(router, topic, script_hint=""):
    """AI đề xuất 3 mô tả giọng chỉ dùng thuộc tính OmniVoice hỗ trợ."""
    schema = {"type": "object", "required": ["instructs"], "properties": {"instructs": {"type": "array", "items": {"type": "string"}}}}
    prompt = (f"Đề xuất 3 mô tả giọng đọc khác nhau cho video lịch sử \"{topic}\" (giọng kể chuyện tài liệu, tiếng Việt).\n"
              f"Gợi ý từ kịch bản: {script_hint}\n"
              f"Mỗi mô tả là chuỗi tiếng Anh ghép bằng dấu phẩy, CHỈ dùng các thuộc tính: giới tính {DESIGN_ATTRS['gender']}, "
              f"tuổi {DESIGN_ATTRS['age']}, cao độ {DESIGN_ATTRS['pitch']}. Ví dụ: \"male, middle-aged, low pitch\".\n"
              "Trả JSON: {\"instructs\": [\"...\", \"...\", \"...\"]}")

    def validator(d):
        errs = []
        for s in d.get("instructs", []):
            parts = [p.strip() for p in s.split(",")]
            allowed = sum(DESIGN_ATTRS.values(), [])
            bad = [p for p in parts if p not in allowed]
            if bad:
                errs.append(f"'{s}' có thuộc tính không hỗ trợ: {bad}")
        if len(d.get("instructs", [])) < 3:
            errs.append("Cần đúng 3 mô tả")
        return errs

    return router.ask("writer", prompt, schema=schema, validator=validator)["instructs"][:3]


def fallback_instructs(country=None, mood="bi_trang"):
    return ["male, middle-aged, low pitch", "male, elderly, low pitch", "female, young adult, moderate pitch"]
