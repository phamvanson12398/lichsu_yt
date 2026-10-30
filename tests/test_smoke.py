"""Kiểm tra nhanh (không cần AI, GPU, giọng):  python -m pytest tests  hoặc  python tests/test_smoke.py"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402


def test_num2words():
    from core.voice.text_norm import normalize, num2words
    assert num2words(938) == "chín trăm ba mươi tám"
    assert num2words(1592) == "một nghìn năm trăm chín mươi hai"
    assert num2words(1066) == "một nghìn không trăm sáu mươi sáu"
    assert num2words(21) == "hai mươi mốt" and num2words(25) == "hai mươi lăm" and num2words(105) == "một trăm linh năm"
    assert "thế kỷ mười" in normalize("TK X")
    assert normalize("Yi Sun-sin", {"Yi Sun-sin": "I Xun Xin"}) == "I Xun Xin"


def test_input_parser():
    from core.input_parser import parse
    i = parse("Trận Hansan năm 1592 (8p)")
    assert i["minutes"] == 8 and i["year"] == 1592 and i["country"] == "korea" and i["slug"] == "hansan_1592"
    assert parse("Trận Hastings năm 1066")["minutes"] == 10


def test_sample_plan_valid():
    from core.plan_schema import validate
    plan = json.load(open(os.path.join(ROOT, "samples", "bach_dang_938", "plan.json"), encoding="utf-8"))
    E, _ = validate(plan)
    assert not E, E


def test_validator_catches_errors():
    from core.plan_schema import validate
    bad = {"title": "x", "country": "vietnam", "year": 938, "scenes": [
        {"id": 1, "type": "narration", "narration": "a", "scene": {"elements": [{"kind": "tenshu"}, {"kind": "khong_co"}]}},
        {"id": 2, "type": "pause"},
        {"id": 3, "type": "text_card", "text": "x", "text_style": "abc", "duration": 2}]}
    E, W = validate(bad)
    txt = " ".join(E)
    assert "khong_co" in txt and "tenshu" in txt and "duration" in txt and "abc" in txt


def test_every_component_draws():
    """Mọi thành phần trong thư viện vẽ được, không lỗi, có hình."""
    from assets_code import registry
    from render.scene import SceneVisual
    registry.load_all()
    for name, comp in registry.REGISTRY.items():
        if comp.category == "background":
            desc = {"background": ["sky", f"{name}"] if name != "sky" else ["sky"], "elements": []}
        else:
            bg = ["sky", "mountains:2", "sea"] if comp.category == "ship" else ["sky", "hills", "plain"]
            desc = {"background": bg, "elements": [{"kind": name, "x": 0.5, "scale": 0.8}]}
        v = SceneVisual(desc, 480, 270, 10, 1.0, motion="static", supersample=1.0)
        a = np.asarray(v.frame(0.2)).astype(np.float32)
        assert a.shape == (270, 480, 3) and np.isfinite(a).all(), name


def test_render_one_frame_each_type():
    from render.renderer import SceneRenderer, build_timeline
    plan = json.load(open(os.path.join(ROOT, "samples", "bach_dang_938", "plan.json"), encoding="utf-8"))
    for e in build_timeline(plan, None, 10):
        r = SceneRenderer(e, plan, 480, 270, 10, {"supersample": 1.0, "grain": 4})
        f = r.frame(min(1.0, e["dur"] / 2))
        assert f.shape == (270, 480, 3) and f.dtype == np.uint8


def test_audio_synth():
    from audio import music_synth, sfx_synth
    for tag in sfx_synth.TAGS:
        s = sfx_synth.make(tag)
        assert s is not None and s.ndim == 2 and np.isfinite(s).all(), tag
    for c in ("vietnam", "korea", "japan", "england"):
        m = music_synth.generate(c, [(0, 3, "yen_binh"), (3, 6, "cao_trao")], seed=1)
        assert m.shape[1] == 2 and np.abs(m).max() <= 1.0


def test_component_code_checker():
    from core.components_ai import check_code
    assert check_code("import os\n@component('x')\ndef f(c,x,y,s,t): os.system('x')")
    assert not check_code("from assets_code.registry import component\n@component('x')\ndef draw_x(c,x,y,s,t,**p):\n    c.d.line([(0,0),(1,1)])\n")


def test_rule_planner():
    from core.planner import plan_rule_based
    from core.plan_schema import validate
    from core.script_writer import parse_markdown
    md = open(os.path.join(ROOT, "samples", "bach_dang_938", "script.md"), encoding="utf-8").read()
    s = parse_markdown(md)
    plan = plan_rule_based(s, {"country": "vietnam", "year": 938, "era": "thế kỷ 10"})
    E, _ = validate(plan)
    assert not E, E
    assert plan["scenes"][0]["type"] == "title"


def test_languages_numbers():
    from core.voice.text_norm import normalize
    assert normalize("In 1066, 7,000 men.", None, "en") == "In ten sixty-six, seven thousand men."
    assert normalize("Henry VIII", None, "en") == "Henry the Eighth"
    assert normalize("1592년 6월", None, "ko") == "천오백구십이년 유월"
    assert normalize("1600年", None, "ja") == "千六百年"


def test_languages_split_and_wrap():
    from core import lang as L
    from render.common import RichFont, set_language, wrap_text
    assert L.split_sentences("関ヶ原の戦い。東軍が勝った！", "ja") == ["関ヶ原の戦い。", "東軍が勝った！"]
    assert L.count("이순신 장군", "ko") == 5 and L.count("In 1066 he won", "en") == 4
    set_language("ja")
    lines = wrap_text("1600年9月15日、霧に包まれた関ヶ原に、東西あわせて十数万の兵が集まりました。", RichFont("serif_bold", 46), 1650)
    assert len(lines) == 2 and lines[0].endswith("、")
    set_language("vi")


def test_input_language_tag():
    from core.input_parser import parse
    assert parse("Trận Hastings năm 1066 (8p, en)")["language"] == "en"
    assert parse("Trận Sekigahara năm 1600 (12p tiếng Nhật)")["language"] == "ja"
    assert parse("Trận Hansan năm 1592 [ko]")["language"] == "ko"


def test_quality_presets():
    from render.renderer import resolve_quality
    c = resolve_quality({"crf": None, "preset": None, "sharpen": None}, quality="cao")
    assert tuple(c["size"]) == (2560, 1440) and c["crf"] == 17
    assert tuple(resolve_quality({}, draft=True)["size"]) == (960, 540)


if __name__ == "__main__":
    n = 0
    for k, fn in list(globals().items()):
        if k.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("✔", k)
    print(f"Xong {n} kiểm tra.")
