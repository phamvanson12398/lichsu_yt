"""Tự đa dạng hóa plan.json sau khi lập kế hoạch (không gọi AI, kết quả cố định).

Mục tiêu: video không bị toàn cảnh rộng sông / bản đồ lặp mãi. Không đổi lời đọc, chỉ đổi CÁCH NHÌN:
  - Chuỗi ≥ 3 cảnh liền cùng "họ nền" (vd đều là mặt sông): cảnh thứ 3 trở đi lần lượt được
      nhìn qua tán lá (foliage_frame) / đứng trên bờ có tướng chỉ huy cận cảnh / nhìn qua lau sậy.
  - Hai cảnh liền cùng chuyển động camera -> đổi chuyển động.
  - Quá lâu (≥ 7 cảnh) không có cảnh cận / đồ họa -> thêm tướng chỉ huy cận cảnh vào một cảnh rộng.

    plan, notes = diversify(plan)
"""
import copy

from assets_code import registry
from render.scene import parse_token

GRAPHIC = ("timeline", "character", "compare", "tide")
WATER = ("river", "sea", "lake")
CLOSE = ("commander", "war_drum", "council")
MOTIONS = ["zoom_in_slow", "parallax_right", "pan_left", "zoom_out_slow", "parallax_left", "pan_right"]
SHIPS = ("ship",)


def _bg_names(desc):
    out = []
    for tok in desc.get("background", []) or []:
        try:
            out.append(parse_token(tok)[0])
        except Exception:
            pass
    return out


def family(sc):
    """Họ hình ảnh của cảnh: graphic | map | card | interior | forest | close | shore | water | land."""
    typ = sc.get("type")
    if typ in GRAPHIC:
        return "graphic"
    if typ == "map":
        return "map"
    desc = sc.get("scene")
    if not desc:
        return "card"
    bg = _bg_names(desc)
    kinds = [e.get("kind") for e in desc.get("elements", []) or [] if isinstance(e, dict)]
    if "hall" in bg:
        return "interior"
    if any(k in CLOSE for k in kinds):
        return "close"
    if "foliage_frame" in bg:
        return "forest"
    if any(w in bg for w in WATER):
        return "shore" if ("reeds" in bg or "bank_near" in bg) else "water"
    return "land"


def _main_x(desc):
    xs = [float(e.get("x", 0.5)) for e in desc.get("elements", []) or [] if isinstance(e, dict) and isinstance(e.get("x", 0.5), (int, float))]
    return sum(xs) / len(xs) if xs else 0.5


def _has_ship(desc):
    for e in desc.get("elements", []) or []:
        c = registry.get(e.get("kind")) if isinstance(e, dict) else None
        if c and c.category in SHIPS:
            return True
    return False


def _add_commander(desc, side="ally"):
    mx = _main_x(desc)
    x, facing = (0.2, 1) if mx >= 0.5 else (0.8, -1)
    bg = list(desc.get("background") or [])
    if not any(str(b).startswith(("bank_near", "plain", "field")) for b in bg):
        bg.append("bank_near:0.93")
    desc["background"] = bg
    # thành phần cũ nằm sát mép dưới sẽ bị bờ đất che -> đẩy lên một chút
    for e in desc.get("elements", []) or []:
        if isinstance(e, dict) and isinstance(e.get("y"), (int, float)) and e["y"] > 0.86:
            e["y"] = 0.84
    desc.setdefault("elements", []).append({"kind": "commander", "x": x, "y": 0.99, "pose": "point", "facing": facing, "side": side})


def _through_leaves(desc, style):
    bg = [b for b in desc.get("background") or [] if not str(b).startswith("foliage_frame")]
    bg.append("foliage_frame" if style == "leaves" else f"foliage_frame:style={style}")
    desc["background"] = bg


def _through_reeds(desc):
    bg = list(desc.get("background") or [])
    if "reeds" not in _bg_names(desc):
        bg.append("reeds")
    desc["background"] = bg


def diversify(plan, country=None):
    registry.load_all()
    plan = copy.deepcopy(plan)
    country = country or plan.get("country", "vietnam")
    leaf_style = {"vietnam": "bamboo", "japan": "pine", "korea": "pine"}.get(country, "leaves")
    notes = []
    scenes = plan.get("scenes") or []
    prev_fam, run = None, 0
    since_close = 0
    k = 0
    for sc in scenes:
        fam = family(sc)
        desc = sc.get("scene")
        editable = bool(desc) and sc.get("type") in ("narration", "pause") and not sc.get("scene2") and not sc.get("keep")
        run = run + 1 if fam == prev_fam and fam not in ("card",) else 1
        changed = None
        if editable and fam in ("water", "land") and run >= 3:
            choice = k % 3
            k += 1
            if choice == 0 and fam == "water":
                _through_leaves(desc, leaf_style)
                changed = "nhìn qua tán lá"
            elif choice == 1 or (choice == 0 and fam == "land"):
                _add_commander(desc)
                changed = "thêm tướng chỉ huy cận cảnh"
            else:
                _through_reeds(desc)
                desc["focus"] = [0.35 if _main_x(desc) < 0.5 else 0.65, 0.6]
                sc["motion"] = "zoom_in_slow"
                changed = "nhìn qua lau sậy, đẩy gần"
            fam = family(sc)
        elif editable and since_close >= 7 and fam in ("water", "land"):
            _add_commander(desc)
            changed = "thêm tướng chỉ huy cận cảnh (lâu rồi chưa có cảnh cận)"
            fam = family(sc)
        if changed:
            notes.append(f"Cảnh {sc.get('id')}: {changed}")
        since_close = 0 if fam in ("close", "graphic", "interior", "forest", "map") else since_close + 1
        prev_fam = fam if not changed else None
        if changed:
            run = 0
    # chuyển động camera không lặp 2 cảnh liền
    last = None
    for i, sc in enumerate(scenes):
        if not sc.get("scene") or sc.get("type") == "title":
            last = None
            continue
        mo = sc.get("motion", "static")
        if mo == last and mo != "static":
            new = MOTIONS[(MOTIONS.index(mo) + 1 + i) % len(MOTIONS)] if mo in MOTIONS else "zoom_in_slow"
            if new == mo:
                new = MOTIONS[(MOTIONS.index(new) + 1) % len(MOTIONS)]
            sc["motion"] = new
            notes.append(f"Cảnh {sc.get('id')}: đổi chuyển động camera {mo} -> {new}")
        last = sc.get("motion", "static")
    return plan, notes


def stats(plan):
    """Đếm họ hình ảnh để báo cáo / cảnh báo."""
    fams = [family(s) for s in plan.get("scenes") or []]
    out = {}
    for f in fams:
        out[f] = out.get(f, 0) + 1
    return out, fams
