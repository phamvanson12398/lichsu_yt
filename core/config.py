"""Đọc config.yaml (có giá trị mặc định nếu thiếu)."""
import copy
import os
import re

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULTS = {
    "writer": "agy", "planner": "claude", "checker": "claude", "check_facts": True, "fallback": True,
    "claude": {"model": None, "timeout": 900},
    "agy": {"model": None, "timeout": 900, "prompt_via": "auto"},
    "narration_language": "vi",
    "default_minutes": 10, "script_parts_from_minutes": 12, "words_per_minute": 200,
    "review_after": ["script", "plan"],
    "voice": {"engine": "omnivoice", "default": None, "default_by_country": {}, "device": "auto", "num_step": 32,
              "draft_num_step": 16, "speed": 1.0, "qc": True, "qc_max_retries": 3, "qc_max_cer": 0.25,
              "model": "k2-fsa/OmniVoice", "asr_model": "openai/whisper-small"},
    "kenh_kiem_tien": False,
    "render": {"quality": "chuan", "fps": 30, "crf": None, "preset": None, "tune": "animation", "sharpen": None,
               "supersample": 2.0, "grain": 4.5, "grain_animated": False,
               "fade": 0.4, "burn_subtitles": True, "subtitle_size": 46, "workers": 0},
    "audio": {"loudness": -16.0, "music": "auto", "music_file": None, "levels": {}},
    "fonts": {},
}


def interactive():
    """Có người gõ phím được không? Giao diện web / app.py đặt HVT_NONINTERACTIVE=1 cho tiến trình con.
    (Trên Windows, stdin = NUL vẫn báo isatty() = True nên không chỉ dựa vào isatty.)"""
    import sys
    if os.environ.get("HVT_NONINTERACTIVE") == "1":
        return False
    try:
        return bool(sys.stdin) and sys.stdin.isatty()
    except Exception:
        return False


def _merge(a, b):
    out = copy.deepcopy(a)
    for k, v in (b or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load(path=None):
    path = path or os.path.join(ROOT, "config.yaml")
    data = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    cfg = _merge(DEFAULTS, data)
    from render.common import set_font_overrides
    set_font_overrides(cfg.get("fonts"))
    return cfg


AI_NAMES = {"claude": "Claude (Claude Code)", "agy": "Antigravity (agy / Gemini)"}
AI_ROLES = ("writer", "planner", "checker")


def apply_ai(cfg, ai):
    """Dùng một AI cho mọi việc trong lần chạy này (ai = claude | agy; rỗng / auto = theo config.yaml)."""
    if ai in AI_NAMES:
        for r in AI_ROLES:
            cfg[r] = ai
    return cfg


def save_ai(choices, fallback=None, path=None):
    """Ghi lựa chọn AI vào config.yaml, giữ nguyên các dòng ghi chú."""
    path = path or os.path.join(ROOT, "config.yaml")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    items = {k: v for k, v in choices.items() if k in AI_ROLES and v in AI_NAMES}
    if fallback is not None:
        items["fallback"] = "true" if fallback else "false"
    for k, v in items.items():
        pat = re.compile(rf"^({k}:[ \t]*)[^#\n]*?([ \t]*(#.*)?)$", re.M)
        if pat.search(text):
            text = pat.sub(lambda m: m.group(1) + v + (m.group(2) or ""), text, count=1)
        else:
            text = f"{k}: {v}\n" + text
    yaml.safe_load(text)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
