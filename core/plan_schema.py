"""Kiểm tra plan.json trước khi dựng (mục 4): kiểu cảnh, thành phần có trong thư viện, thời gian hợp lệ,
độ chính xác lịch sử (thành phần đúng nước / thời kỳ). Báo lỗi tiếng Việt dễ hiểu.

validate(plan) -> (errors, warnings)
"""
from assets_code import registry
from audio.sfx_synth import TAGS
from audio.music_synth import MOODS
from render.map_anim import FEATURES, MARKERS
from render.motion import MOTIONS
from render.palettes import PALETTES
from render.particles import KINDS
from render.scene import parse_token
from render.text_fx import STYLES

SCENE_TYPES = ["title", "narration", "text_card", "map", "pause", "timeline", "character", "compare", "tide"]
COUNTRIES = ["vietnam", "korea", "japan", "england", "china", "common"]
TIMES = ["dawn", "day", "dusk", "night"]
WEATHERS = ["clear", "cloudy", "overcast", "rain", "storm", "snow", "fog"]
# bộ thành phần nước khác được phép dùng cho phe địch trong trận của nước này
ALLOWED_FOREIGN = {"vietnam": ["china"], "korea": ["japan", "china"], "japan": ["korea", "china"], "england": []}

# JSON Schema rút gọn (cũng gửi cho AI khi lập plan)
PLAN_SCHEMA = {
    "type": "object", "required": ["title", "country", "scenes"],
    "properties": {
        "title": {"type": "string"}, "country": {"type": "string"}, "era": {"type": "string"},
        "year": {"type": "integer"}, "palette": {"type": "string"}, "voice": {"type": ["string", "null"]},
        "scenes": {"type": "array", "items": {"type": "object", "required": ["id", "type"]}},
    },
}


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def validate(plan, year=None):
    registry.load_all()
    E, W = [], []
    if not isinstance(plan, dict):
        return ["plan.json phải là một đối tượng JSON {...}"], []
    for k in ("title", "country", "scenes"):
        if k not in plan:
            E.append(f"Thiếu trường bắt buộc '{k}' ở đầu plan.json")
    country = plan.get("country", "vietnam")
    if country not in COUNTRIES:
        W.append(f"Nước '{country}' chưa có bộ thành phần riêng; sẽ dùng bộ chung")
    year = year or plan.get("year")
    pal = plan.get("palette")
    if pal and pal not in PALETTES:
        E.append(f"Bảng màu '{pal}' không có. Chọn một trong: {', '.join(PALETTES)}")
    scenes = plan.get("scenes") or []
    if not scenes:
        E.append("plan.json không có cảnh nào")
    ids = set()
    pals_used = set([pal] if pal else [])
    for i, sc in enumerate(scenes):
        where = f"Cảnh {sc.get('id', i + 1)}"
        sid = sc.get("id")
        if sid in ids:
            E.append(f"{where}: trùng id")
        ids.add(sid)
        typ = sc.get("type")
        if typ not in SCENE_TYPES:
            E.append(f"{where}: kiểu cảnh '{typ}' không hợp lệ (chỉ dùng: {', '.join(SCENE_TYPES)})")
            continue
        has_narr = bool(sc.get("narration"))
        if not has_narr:
            d = sc.get("duration")
            if not _num(d) or d <= 0:
                E.append(f"{where}: cảnh không có lời đọc phải có 'duration' > 0 (giây)")
            elif d > 30:
                W.append(f"{where}: duration {d}s khá dài cho cảnh không lời")
        elif not isinstance(sc["narration"], str):
            E.append(f"{where}: 'narration' phải là chuỗi văn bản")
        if typ == "text_card" and not sc.get("text"):
            E.append(f"{where}: thẻ chữ (text_card) cần có 'text'")
        if typ == "title" and not sc.get("text"):
            W.append(f"{where}: cảnh tiêu đề nên có 'text'")
        ts = sc.get("text_style")
        if ts and ts not in STYLES:
            E.append(f"{where}: kiểu chữ '{ts}' không có (chỉ dùng: {', '.join(STYLES)})")
        if ts == "count_year" and not any(ch.isdigit() for ch in str(sc.get("text", ""))):
            E.append(f"{where}: count_year cần 'text' là một con số năm, vd \"938\"")
        mo = sc.get("motion")
        if mo and mo not in MOTIONS:
            E.append(f"{where}: chuyển động '{mo}' không có (chỉ dùng: {', '.join(MOTIONS)})")
        for p in sc.get("particles", []) or []:
            if str(p).split(":")[0] not in KINDS:
                E.append(f"{where}: hạt '{p}' không có (chỉ dùng: {', '.join(KINDS)})")
        for tag in sc.get("sfx", []) or []:
            if tag not in TAGS:
                E.append(f"{where}: âm thanh '{tag}' không có (chỉ dùng: {', '.join(TAGS)})")
        for it in sc.get("sfx_at", []) or []:
            if not isinstance(it, dict) or it.get("tag") not in TAGS or not _num(it.get("t", None)):
                E.append(f"{where}: sfx_at phải dạng {{\"t\": giây, \"tag\": tên}} với tag hợp lệ")
        if sc.get("mood") and sc["mood"] not in MOODS:
            E.append(f"{where}: tâm trạng nhạc '{sc['mood']}' không có (chỉ dùng: {', '.join(MOODS)})")
        if sc.get("palette"):
            if sc["palette"] not in PALETTES:
                E.append(f"{where}: bảng màu '{sc['palette']}' không có")
            pals_used.add(sc["palette"])
        for key in ("scene", "scene2"):
            if sc.get(key):
                _check_scene(sc[key], f"{where} ({key})", country, year, E, W, pals_used)
        if typ in ("narration", "title", "pause") and not sc.get("scene"):
            if typ != "narration" or not sc.get("map"):
                W.append(f"{where}: không có mô tả 'scene' -> sẽ dùng nền tối")
        if typ == "map":
            _check_map(sc.get("map") or {}, where, E, W)
        if typ in ("timeline", "character", "compare", "tide"):
            _check_graphic(typ, sc.get(typ), where, E, W)
    _check_variety(plan, W)
    if len(pals_used) > 2:
        W.append(f"Video dùng {len(pals_used)} bảng màu ({', '.join(sorted(pals_used))}); khuyên chỉ 1–2 bảng cho thống nhất")
    return E, W


def _check_scene(desc, where, country, year, E, W, pals_used):
    if not isinstance(desc, dict):
        E.append(f"{where}: 'scene' phải là đối tượng {{...}}")
        return
    if desc.get("time_of_day") and desc["time_of_day"] not in TIMES:
        E.append(f"{where}: time_of_day '{desc['time_of_day']}' không hợp lệ ({', '.join(TIMES)})")
    if desc.get("weather") and desc["weather"] not in WEATHERS:
        E.append(f"{where}: weather '{desc['weather']}' không hợp lệ ({', '.join(WEATHERS)})")
    if desc.get("palette"):
        pals_used.add(desc["palette"])
    for tok in desc.get("background", []) or []:
        try:
            name, _ = parse_token(tok)
        except Exception:
            E.append(f"{where}: nền '{tok}' viết sai")
            continue
        c = registry.get(name)
        if not c or c.category != "background":
            E.append(f"{where}: nền '{name}' không có trong thư viện (xem: python main.py component list)")
    for el in desc.get("elements", []) or []:
        if not isinstance(el, dict) or "kind" not in el:
            E.append(f"{where}: mỗi thành phần phải có 'kind'")
            continue
        c = registry.get(el["kind"])
        if not c or c.category == "background":
            E.append(f"{where}: thành phần '{el['kind']}' không có trong thư viện (xem: python main.py component list)")
            continue
        for k in ("x", "y"):
            if k in el and (not _num(el[k]) or not -0.5 <= el[k] <= 1.5):
                E.append(f"{where}: '{el['kind']}' có {k}={el[k]} ngoài khoảng cho phép (0–1, tối đa -0.5..1.5)")
            elif k in el and not 0 <= el[k] <= 1:
                W.append(f"{where}: '{el['kind']}' có {k}={el[k]} nằm ngoài khung 0–1 (chỉ thấy một phần)")
        if "scale" in el and (not _num(el["scale"]) or el["scale"] <= 0 or el["scale"] > 5):
            E.append(f"{where}: '{el['kind']}' scale={el.get('scale')} không hợp lệ (0 < scale ≤ 5)")
        if "count" in el and (not isinstance(el["count"], int) or not 1 <= el["count"] <= 30):
            E.append(f"{where}: '{el['kind']}' count phải là số nguyên 1–30")
        # độ chính xác lịch sử
        if c.country not in ("common", "custom", country) and c.country not in ALLOWED_FOREIGN.get(country, []):
            W.append(f"{where}: '{el['kind']}' thuộc bộ {c.country}, không phải {country} — kiểm tra lại có đúng lịch sử không")
        if year and not (c.era[0] <= year <= c.era[1]):
            E.append(f"{where}: '{el['kind']}' chỉ phù hợp năm {c.era[0]}–{c.era[1]}, không hợp với năm {year}")
        if year and year < 1500 and el.get("weapon") == "musket":
            E.append(f"{where}: súng hỏa mai (musket) không có vào năm {year}")


def _check_variety(plan, W):
    from core.diversify import stats
    cnt, fams = stats(plan)
    visual = [f for f in fams if f != "card"]
    if len(visual) >= 8:
        water = cnt.get("water", 0)
        if water / len(visual) > 0.6:
            W.append(f"{water}/{len(visual)} cảnh là toàn cảnh mặt nước — nên xen cảnh cận (commander, war_drum), nội thất (hall + council), "
                     "đồ họa (timeline, character, compare, tide) hoặc nhìn qua tán lá (foliage_frame)")
        if not any(f in cnt for f in ("close", "graphic", "interior", "forest")):
            W.append("Video chỉ có cảnh rộng và bản đồ — nên thêm cảnh cận / đồ họa cho đa dạng (lệnh: python main.py diversify <dự án>)")
    run, prev = 0, None
    for sc, f in zip(plan.get("scenes") or [], fams):
        run = run + 1 if f == prev and f in ("water", "land") else 1
        prev = f
        if run == 4:
            W.append(f"Cảnh {sc.get('id')}: 4 cảnh liền cùng kiểu nền ({'mặt nước' if f == 'water' else 'đất liền'}) — nên đổi góc nhìn")


def _check_graphic(typ, g, where, E, W):
    if not isinstance(g, dict):
        E.append(f"{where}: cảnh '{typ}' cần trường \"{typ}\": {{...}}")
        return
    if typ == "timeline":
        ev = g.get("events")
        if not isinstance(ev, list) or not ev or not all(isinstance(e, dict) and e.get("year") is not None for e in ev):
            E.append(f"{where}: timeline cần 'events' = [{{\"year\": ..., \"text\": ...}}, ...]")
        elif len(ev) > 7:
            W.append(f"{where}: timeline chỉ hiện tối đa 7 mốc")
    elif typ == "character":
        if not g.get("name"):
            E.append(f"{where}: character cần 'name'")
        if g.get("look") and g["look"] not in ("general", "king", "scholar", "admiral", "monk", "queen"):
            E.append(f"{where}: character look '{g['look']}' không có (general, king, scholar, admiral, monk, queen)")
    elif typ == "compare":
        it = g.get("items")
        if not isinstance(it, list) or not it or not all(isinstance(i, dict) and _num(i.get("value")) for i in it):
            E.append(f"{where}: compare cần 'items' = [{{\"label\": ..., \"value\": số}}, ...]")
        if not g.get("note"):
            W.append(f"{where}: compare nên có 'note' ghi độ chắc chắn của số liệu (vd: \"Số liệu theo sử cũ, chưa chắc chắn\")")
    elif typ == "tide":
        if "fall_at" in g and not _num(g["fall_at"]):
            E.append(f"{where}: tide 'fall_at' phải là số giây")


def _check_map(m, where, E, W):
    for f in m.get("features", []) or []:
        if f not in FEATURES:
            E.append(f"{where}: bản đồ có feature '{f}' không hợp lệ ({', '.join(FEATURES)})")
    pts_ok = lambda p: isinstance(p, (list, tuple)) and len(p) == 2 and all(_num(v) and -0.05 <= v <= 1.05 for v in p)
    for a in m.get("arrows", []) or []:
        if a.get("side", "enemy") not in ("enemy", "ally"):
            E.append(f"{where}: mũi tên side phải là 'enemy' (đỏ) hoặc 'ally' (xanh)")
        path = a.get("path") or []
        if len(path) < 2 or not all(pts_ok(p) for p in path):
            E.append(f"{where}: mũi tên cần 'path' ≥ 2 điểm, toạ độ 0–1")
        if not _num(a.get("start", 0)) or not _num(a.get("dur", 1)) or a.get("dur", 1) <= 0:
            E.append(f"{where}: mũi tên cần start ≥ 0 và dur > 0 (giây)")
    for mk in m.get("markers", []) or []:
        if mk.get("kind") not in MARKERS:
            E.append(f"{where}: marker '{mk.get('kind')}' không hợp lệ ({', '.join(MARKERS)})")
        if not pts_ok(mk.get("at")):
            E.append(f"{where}: marker cần 'at' = [x, y] trong 0–1")
    for lb in m.get("labels", []) or []:
        if not lb.get("text") or not pts_ok(lb.get("at")):
            E.append(f"{where}: nhãn bản đồ cần 'text' và 'at' = [x, y] trong 0–1")


def format_report(E, W):
    lines = []
    if E:
        lines.append(f"❌ {len(E)} lỗi cần sửa:")
        lines += [f"   - {e}" for e in E]
    if W:
        lines.append(f"⚠️  {len(W)} lưu ý:")
        lines += [f"   - {w}" for w in W]
    if not E and not W:
        lines.append("✅ plan.json hợp lệ.")
    return "\n".join(lines)
