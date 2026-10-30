"""Đọc config.yaml (có giá trị mặc định nếu thiếu)."""
import copy
import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULTS = {
    "writer": "agy", "planner": "claude", "checker": "claude", "check_facts": True, "fallback": True,
    "claude": {"model": None, "timeout": 900},
    "agy": {"model": None, "timeout": 900, "prompt_via": "stdin"},
    "narration_language": "tiếng Việt",
    "default_minutes": 10, "words_per_minute": 140,
    "review_after": ["script", "plan"],
    "voice": {"engine": "omnivoice", "default": None, "default_by_country": {}, "device": "auto", "num_step": 32,
              "draft_num_step": 16, "speed": 1.0, "qc": True, "qc_max_retries": 3, "qc_max_cer": 0.25,
              "model": "k2-fsa/OmniVoice", "asr_model": "openai/whisper-small"},
    "kenh_kiem_tien": False,
    "render": {"size": [1920, 1080], "fps": 30, "crf": 19, "preset": "veryfast", "supersample": 2.0, "grain": 7.0, "grain_animated": False,
               "fade": 0.4, "burn_subtitles": True, "subtitle_size": 46, "workers": 0},
    "audio": {"loudness": -16.0, "music": "auto", "music_file": None, "levels": {}},
    "fonts": {},
}


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
