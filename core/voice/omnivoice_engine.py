"""Tích hợp OmniVoice (k2-fsa) chạy trên máy người dùng (mục 8).

- Nạp model MỘT lần cho cả phiên, dùng lại cho mọi câu.
- generate() hỗ trợ: text, ref_audio, ref_text, instruct, voice_clone_prompt, speed, duration, num_step, normalize_text.
- normalize_text mặc định TẮT: tool đã tự đổi số -> chữ, số La Mã, viết tắt (core/voice/text_norm.py, core/lang.py).
  Chuẩn hoá của OmniVoice cần WeTextProcessing / pynini, rất khó cài trên Windows và chỉ hỗ trợ tiếng Anh / Trung.
  Thư viện có thể đổi tên tham số giữa các phiên bản -> chỉ truyền tham số mà hàm generate() thực sự nhận
  (đọc bằng inspect). Kiểm tra lại docs/voice-design.md của OmniVoice khi nâng cấp.
- Nhận dạng giọng nói (Whisper) để: tự điền lời mẫu (ref_text) và kiểm tra chất lượng câu đã tạo.
"""
import difflib
import hashlib
import inspect
import json
import os
import re
import shutil
import time
import wave

import numpy as np

from core.voice import text_norm

OUT_SR = 24000
LICENSE_WARNING = ("⚠️  LƯU Ý BẢN QUYỀN: mô hình OmniVoice dùng giấy phép CC-BY-NC (PHI THƯƠNG MẠI). Video đăng lên kênh có "
                   "bật kiếm tiền có thể bị coi là dùng thương mại. Hãy cân nhắc trước khi bật kiếm tiền.")
CONSENT_TEXT = "Đây là giọng của tôi hoặc tôi đã được người này đồng ý"


class VoiceUnavailable(Exception):
    pass


def save_wav(path, audio, sr):
    a = np.asarray(audio, np.float32).reshape(-1)
    peak = np.abs(a).max() if a.size else 0
    if peak > 1.0:
        a = a / peak * 0.98
    s = (a * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(int(sr))
        w.writeframes(s.tobytes())


def wav_duration(path):
    with wave.open(path, "rb") as w:
        return w.getnframes() / float(w.getframerate())


def read_wav(path):
    with wave.open(path, "rb") as w:
        sr = w.getframerate()
        ch = w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    if ch > 1:
        x = x.reshape(-1, ch).mean(1)
    return x, sr


def cer(ref, hyp):
    """Tỉ lệ sai khác ký tự (0 = giống hệt) sau khi bỏ dấu câu, chữ thường."""
    f = lambda s: re.sub(r"[^\w]+", " ", text_norm._nfc(s or "").lower()).strip()
    a, b = f(ref), f(hyp)
    if not a:
        return 0.0 if not b else 1.0
    return 1 - difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


class OmniVoiceEngine:
    _instance = None

    def __init__(self, cfg, log=print):
        self.cfg = cfg
        self.log = log
        self.model = None
        self.asr = None
        self.device = None
        self._gen_params = None

    @classmethod
    def get(cls, cfg, log=print):
        if cls._instance is None:
            cls._instance = cls(cfg, log)
        return cls._instance

    @staticmethod
    def installed():
        try:
            import omnivoice  # noqa: F401
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------ model
    def load(self):
        if self.model is not None:
            return self.model
        try:
            import torch
            from omnivoice import OmniVoice
        except Exception as e:
            raise VoiceUnavailable("Chưa cài OmniVoice / PyTorch. Chạy:  pip install omnivoice  (xem HUONG_DAN_CAI_DAT.md mục Giọng đọc). "
                                   f"Chi tiết: {e}")
        dev = self.cfg.get("device", "auto")
        if dev == "auto":
            if torch.cuda.is_available():
                dev = "cuda:0"
            elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
                dev = "mps"
            else:
                dev = "cpu"
        dtype = torch.float16 if dev.startswith("cuda") else torch.float32
        self.device = dev
        if dev == "cpu":
            self.log("⚠️  Không thấy GPU: OmniVoice chạy bằng CPU sẽ CHẬM (có thể vài phút cho mỗi phút giọng). "
                     "Tool sẽ báo thời gian ước tính sau câu đầu tiên.")
        self.log(f"🔊 Nạp mô hình OmniVoice ({self.cfg.get('model', 'k2-fsa/OmniVoice')}) trên {dev}...")
        t0 = time.time()
        try:
            self.model = OmniVoice.from_pretrained(self.cfg.get("model", "k2-fsa/OmniVoice"), device_map=dev, dtype=dtype)
        except TypeError:
            self.model = OmniVoice.from_pretrained(self.cfg.get("model", "k2-fsa/OmniVoice"), device_map=dev, torch_dtype=dtype)
        self.log(f"   ✔ nạp xong sau {time.time() - t0:.0f}s")
        try:
            sig = inspect.signature(self.model.generate)
            self._gen_params = None if any(p.kind == p.VAR_KEYWORD for p in sig.parameters.values()) else set(sig.parameters)
        except (TypeError, ValueError):
            self._gen_params = None
        return self.model

    @property
    def sr(self):
        for a in ("sampling_rate", "sample_rate", "sr"):
            v = getattr(self.model, a, None)
            if isinstance(v, int):
                return v
        return OUT_SR

    def _to_audio(self, out):
        sr = self.sr
        if isinstance(out, dict):
            sr = out.get("sample_rate") or out.get("sr") or sr
            out = out.get("audio") if out.get("audio") is not None else out.get("wav", out.get("waveform"))
        if isinstance(out, (tuple, list)) and len(out) == 2 and isinstance(out[1], int):
            out, sr = out
        if isinstance(out, (tuple, list)):
            out = out[0]
        if hasattr(out, "detach"):
            out = out.detach().float().cpu().numpy()
        a = np.asarray(out, np.float32).squeeze()
        if a.ndim > 1:
            a = a.reshape(-1) if a.shape[0] == 1 else a[0]
        return a, int(sr)

    def generate(self, text, ref_audio=None, ref_text=None, instruct=None, voice_clone_prompt=None, speed=1.0,
                 num_step=None, duration=None, normalize_text=None):
        self.load()
        if normalize_text is None:
            normalize_text = bool(self.cfg.get("omnivoice_normalize", False)) and not getattr(self, "_tn_missing", False)
        kw = {"text": text, "ref_audio": ref_audio, "ref_text": ref_text, "instruct": instruct,
              "voice_clone_prompt": voice_clone_prompt, "speed": speed, "duration": duration,
              "num_step": num_step or self.cfg.get("num_step", 32), "normalize_text": normalize_text}
        kw = {k: v for k, v in kw.items() if v is not None}
        if self._gen_params is not None:
            kw = {k: v for k, v in kw.items() if k in self._gen_params}
        try:
            out = self.model.generate(**kw)
        except ImportError as e:
            if "WeTextProcessing" not in str(e) and "tn" not in str(e):
                raise
            # thiếu thư viện chuẩn hoá của OmniVoice -> tắt hẳn, tool đã tự chuẩn hoá văn bản
            self._tn_missing = True
            self.log("ℹ️  Bỏ qua chuẩn hoá văn bản của OmniVoice (thiếu WeTextProcessing) — tool đã tự đổi số thành chữ.")
            kw["normalize_text"] = False
            out = self.model.generate(**kw)
        return self._to_audio(out)

    def clone_prompt(self, ref_audio, ref_text):
        """voice_clone_prompt tính sẵn (nếu thư viện hỗ trợ) để tạo nhanh hơn."""
        self.load()
        for name in ("create_voice_clone_prompt", "build_voice_clone_prompt", "get_voice_clone_prompt"):
            fn = getattr(self.model, name, None)
            if fn:
                try:
                    return fn(ref_audio=ref_audio, ref_text=ref_text)
                except TypeError:
                    return fn(ref_audio, ref_text)
        return None

    @staticmethod
    def save_prompt(prompt, path):
        try:
            if hasattr(prompt, "save"):
                prompt.save(path)
            else:
                import torch
                torch.save(prompt, path)
            return True
        except Exception:
            return False

    @staticmethod
    def load_prompt(path):
        if not os.path.exists(path):
            return None
        try:
            from omnivoice import VoiceClonePrompt
            return VoiceClonePrompt.load(path)
        except Exception:
            try:
                import torch
                return torch.load(path, weights_only=False)
            except Exception:
                return None

    # ------------------------------------------------------------------ ASR
    def transcribe(self, path, lang="vi"):
        """Nhận dạng lời trong file (Whisper). Trả về None nếu không có ASR."""
        self.load()
        for name in ("transcribe", "asr"):
            fn = getattr(self.model, name, None)
            if callable(fn):
                try:
                    r = fn(path)
                    return r if isinstance(r, str) else (r.get("text") if isinstance(r, dict) else str(r))
                except Exception:
                    pass
        if self.asr is None:
            try:
                from transformers import pipeline
                dev = 0 if (self.device or "").startswith("cuda") else -1
                self.asr = pipeline("automatic-speech-recognition", model=self.cfg.get("asr_model", "openai/whisper-small"), device=dev)
            except Exception as e:
                self.log(f"   (không có nhận dạng giọng nói: {e})")
                self.asr = False
        if not self.asr:
            return None
        x, sr = read_wav(path)
        from core import lang as L
        r = self.asr({"raw": x, "sampling_rate": sr}, generate_kwargs={"language": L.get(lang)["asr"], "task": "transcribe"})
        return (r.get("text") if isinstance(r, dict) else str(r)).strip()


# ====================================================================== tạo giọng cho cả dự án
def voice_key(voice_meta, speak, speed, num_step):
    s = json.dumps([voice_meta.get("ten"), voice_meta.get("ngay_tao"), voice_meta.get("ref_hash"), speak, speed, num_step],
                   ensure_ascii=False)
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:16]


def generate_project_voice(plan, proj_dir, voice, cfg, pron, draft=False, log=print, only_scenes=None):
    """Tạo giọng từng câu: voice/<id_canh>_<so_cau>.wav + voice/timings.json (mốc thời gian, cờ cần nghe lại)."""
    vcfg = cfg["voice"]
    eng = OmniVoiceEngine.get(vcfg, log)
    if cfg.get("kenh_kiem_tien"):
        log(LICENSE_WARNING)
    vdir = os.path.join(proj_dir, "voice")
    os.makedirs(vdir, exist_ok=True)
    tpath = os.path.join(vdir, "timings.json")
    old = json.load(open(tpath, encoding="utf-8")) if os.path.exists(tpath) else {"scenes": {}}
    old_cache = {s["key"]: s for sc in old.get("scenes", {}).values() for s in sc.get("sentences", []) if s.get("key")}
    speed = float(voice.meta.get("toc_do", vcfg.get("speed", 1.0)))
    num_step = vcfg.get("draft_num_step", 16) if draft else vcfg.get("num_step", 32)
    prompt = voice.clone_prompt(eng)
    lang = plan.get("language", "vi")
    vlang = voice.meta.get("ngon_ngu", "vi")
    if vlang and vlang != lang:
        log(f"ℹ️  Giọng '{voice.name}' được tạo cho ngôn ngữ '{vlang}', video dùng '{lang}' — OmniVoice vẫn đọc được nhưng nên nghe kỹ.")
    out = {"voice": voice.name, "language": lang, "scenes": {}}
    flagged = []
    jobs = []
    for sc in plan["scenes"]:
        if not sc.get("narration"):
            continue
        for k, sent in enumerate(text_norm.split_sentences(sc["narration"], lang=lang), 1):
            jobs.append((sc["id"], k, sent))
    from core import lang as L
    total_syl = sum(L.count(j[2], lang) for j in jobs)
    done_syl, t_start, told = 0, time.time(), False
    for sid, k, sent in jobs:
        speak = text_norm.normalize(sent, pron, lang)
        key = voice_key(voice.meta, speak, speed, num_step)
        fname = f"{int(sid):03d}_{k:02d}.wav" if str(sid).isdigit() else f"{sid}_{k:02d}.wav"
        fpath = os.path.join(vdir, fname)
        entry = {"text": speak, "display": sent, "file": os.path.join("voice", fname), "key": key}
        if key in old_cache and os.path.exists(os.path.join(proj_dir, old_cache[key]["file"])):
            prev = old_cache[key]
            if prev["file"] != entry["file"]:
                shutil.copyfile(os.path.join(proj_dir, prev["file"]), fpath)
            entry.update(dur=wav_duration(fpath) if os.path.exists(fpath) else prev["dur"], cer=prev.get("cer"),
                         can_nghe_lai=prev.get("can_nghe_lai", False))
        else:
            best = None
            tries = vcfg.get("qc_max_retries", 3) if vcfg.get("qc", True) else 1
            for attempt in range(max(1, tries)):
                a, sr = eng.generate(speak, ref_audio=voice.ref_wav if prompt is None else None,
                                     ref_text=voice.ref_text if prompt is None else None, voice_clone_prompt=prompt,
                                     speed=speed, num_step=num_step)
                a = trim_silence(a, sr)
                save_wav(fpath, a, sr)
                score = None
                if vcfg.get("qc", True):
                    hyp = eng.transcribe(fpath, lang)
                    score = cer(speak, hyp) if hyp is not None else None
                if best is None or (score is not None and (best[0] is None or score < best[0])):
                    best = (score, a, sr)
                if score is None or score <= vcfg.get("qc_max_cer", 0.25):
                    break
                log(f"   ↻ câu {sid}.{k} đọc sai lệch {score:.0%}, tạo lại ({attempt + 2}/{tries})")
            score, a, sr = best
            save_wav(fpath, a, sr)
            entry.update(dur=len(a) / sr, cer=score, can_nghe_lai=bool(score is not None and score > vcfg.get("qc_max_cer", 0.25)))
            done_syl += L.count(sent, lang)
            if not told and time.time() - t_start > 5 and done_syl:
                rate = (time.time() - t_start) / done_syl
                log(f"   ⏱  ước tính còn khoảng {rate * (total_syl - done_syl) / 60:.1f} phút để tạo giọng")
                told = True
        if entry.get("can_nghe_lai"):
            flagged.append(f"{fname}: \"{sent[:60]}\"")
        out["scenes"].setdefault(str(sid), {"sentences": []})["sentences"].append(entry)
        log(f"   🗣  {fname} ({entry['dur']:.1f}s)")
    with open(tpath, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    if flagged:
        log("⚠️  Các câu nên nghe lại (máy nhận dạng thấy khác văn bản nhiều):\n   - " + "\n   - ".join(flagged))
    return out


def trim_silence(a, sr, thresh=0.01, keep=0.05):
    """Cắt khoảng lặng đầu / cuối câu."""
    if a.size == 0:
        return a
    idx = np.where(np.abs(a) > thresh)[0]
    if not len(idx):
        return a
    i0 = max(0, idx[0] - int(keep * sr))
    i1 = min(len(a), idx[-1] + int(keep * 2 * sr))
    return a[i0:i1]


def estimate_timings(plan, pron=None):
    """Khi chưa có giọng: ước lượng thời lượng câu (để dựng thử, phụ đề vẫn chạy)."""
    from render.renderer import estimate_speech
    lang = plan.get("language", "vi")
    out = {"voice": None, "language": lang, "scenes": {}}
    for sc in plan["scenes"]:
        if not sc.get("narration"):
            continue
        for sent in text_norm.split_sentences(sc["narration"], lang=lang):
            out["scenes"].setdefault(str(sc["id"]), {"sentences": []})["sentences"].append(
                {"text": text_norm.normalize(sent, pron, lang), "display": sent, "file": None, "dur": estimate_speech(sent, lang)})
    return out
