"""Thành phần chung: đuốc, lửa trại, đám cháy, cột khói, cờ bay, hàng cờ, cây, đá, lều trại,
đám quân (bóng người), kỵ binh, loạt tên bay.
"""
import math
import random

from PIL import Image, ImageDraw, ImageFilter

from assets_code.common.shapes import figure, flag_points, horse
from assets_code.registry import component
from render.common import lerp, mix


def flame(d, x, yb, w, h, t, seed=0, col_out=(255, 110, 25), col_in=(255, 220, 120)):
    """Ngọn lửa chập chờn (đa giác thay đổi theo t)."""
    for layer, (col, k) in enumerate([(col_out, 1.0), (col_in, 0.55)]):
        pts = []
        n = 9
        for i in range(n + 1):
            u = i / n
            a = math.pi * u
            fl = 0.75 + 0.25 * math.sin(t * 9 + i * 1.7 + seed) + 0.12 * math.sin(t * 17 + i * 2.3 + seed * 3)
            rr = math.sin(a) ** 0.8
            px = x - w * k / 2 + w * k * u
            py = yb - h * k * rr * fl * (1.0 if 0.3 < u < 0.7 else 0.65)
            pts.append((px, py))
        tipx = x + math.sin(t * 6 + seed) * w * 0.12
        pts.insert(n // 2 + 1, (tipx, yb - h * k * (1.15 + 0.15 * math.sin(t * 11 + seed))))
        pts += [(x + w * k / 2, yb), (x - w * k / 2, yb)]
        d.polygon(pts, fill=col + (235,))


@component("torch", category="effect", anim="redraw", bbox=(70, 200), desc="Đuốc cắm đất, lửa chập chờn.",
           params={"height": "chiều cao (px 1080p, mặc định 120)"})
def draw_torch(c, x, y, scale, t, height=120, **p):
    X, Y = c.px(x), c.py(y)
    h = float(height) * c.u * scale
    c.d.line([(X, Y), (X + h * 0.05, Y - h)], fill=c.pal["wood"] + (255,), width=max(2, int(h * 0.06)))
    flame(c.d, X + h * 0.05, Y - h * 0.95, h * 0.22, h * 0.4, t, seed=x * 10, col_out=c.pal["fire"])
    c.add_fire(X, Y - h * 1.05, h * 0.5)


@component("campfire", category="effect", anim="redraw", bbox=(220, 220), desc="Lửa trại, củi chéo, ánh lửa.")
def draw_campfire(c, x, y, scale, t, **p):
    X, Y = c.px(x), c.py(y)
    s = c.u * scale
    w = 90 * s
    d = c.d
    for k in (-1, 1):
        d.line([(X - w * 0.6 * k, Y), (X + w * 0.5 * k, Y - 25 * s)], fill=c.pal["wood"] + (255,), width=max(2, int(12 * s)))
    flame(d, X, Y - 10 * s, w, 150 * s, t, seed=x * 7, col_out=c.pal["fire"])
    c.add_fire(X, Y - 70 * s, 130 * s)


@component("fire", category="effect", anim="redraw", bbox=(420, 420), desc="Đám cháy lớn (đặt lên thuyền / nhà đang cháy).",
           params={"size": "độ lớn (mặc định 1)"})
def draw_fire(c, x, y, scale, t, **p):
    X, Y = c.px(x), c.py(y)
    s = c.u * scale
    for k in range(3):
        flame(c.d, X + (k - 1) * 70 * s, Y, 140 * s, (240 + 60 * (k == 1)) * s, t + k * 0.37, seed=k * 3 + x * 5,
              col_out=c.pal["fire"])
    c.add_fire(X, Y - 150 * s, 220 * s)


@component("smoke_column", category="effect", desc="Cột khói lớn bốc lên (tĩnh, mờ). Kết hợp hạt 'smoke' để có khói động.")
def draw_smoke_column(c, x, y, scale, t, **p):
    X, Y = c.px(x), c.py(y)
    s = c.u * scale
    m = Image.new("L", (c.W, c.H), 0)
    d = ImageDraw.Draw(m)
    rr = random.Random(int(x * 1000))
    for k in range(12):
        r = (60 + k * 16) * s
        cx = X + k * 18 * s + rr.uniform(-20, 20) * s
        cy = Y - k * 70 * s
        d.ellipse([cx - r, cy - r * 0.8, cx + r, cy + r * 0.8], fill=int(150 - k * 7))
    m = m.filter(ImageFilter.GaussianBlur(40 * s))
    col = mix(c.pal["sil"], c.pal["fog"], 0.35)
    lay = Image.new("RGBA", (c.W, c.H), col + (0,))
    lay.putalpha(m)
    c.img.alpha_composite(lay)


@component("flag", category="effect", anim="redraw", bbox=(260, 380), desc="Cờ bay phấp phới trên cột.",
           params={"side": "ally | enemy (màu theo bảng màu)", "color": "[r,g,b] tuỳ chọn", "height": "px 1080p (mặc định 260)",
                   "facing": "1 phải / -1 trái", "emblem": "circle | stripe | none"})
def draw_flag(c, x, y, scale, t, side="ally", color=None, height=260, facing=1, emblem="none", **p):
    X, Y = c.px(x), c.py(y)
    h = float(height) * c.u * scale
    col = tuple(color) if color else c.pal["flag_ally" if side == "ally" else "flag_enemy"]
    d = c.d
    d.line([(X, Y), (X, Y - h)], fill=c.pal["wood"] + (255,), width=max(2, int(h * 0.025)))
    pts = flag_points(X, Y - h, h * 0.55, h * 0.32, t + x * 3, facing=1 if facing >= 0 else -1)
    d.polygon(pts, fill=col + (255,))
    if emblem == "circle":
        cx = X + (1 if facing >= 0 else -1) * h * 0.27
        d.ellipse([cx - h * 0.07, Y - h + h * 0.09, cx + h * 0.07, Y - h + h * 0.23], fill=(240, 210, 120, 255))
    elif emblem == "stripe":
        d.line(pts[:13], fill=(240, 210, 120, 255), width=max(1, int(h * 0.02)))


@component("banners_row", category="effect", anim="redraw", bbox=(900, 380), desc="Hàng cờ hiệu dọc theo đội quân.",
           params={"n": "số cờ", "side": "ally | enemy", "width": "độ rộng hàng (tỉ lệ khung, mặc định 0.4)",
                   "style": "wide | tall (tall = cờ dọc kiểu Nhật nobori)"})
def draw_banners_row(c, x, y, scale, t, n=6, side="ally", width=0.4, style="wide", color=None, **p):
    n = int(n)
    col = tuple(color) if color else c.pal["flag_ally" if side == "ally" else "flag_enemy"]
    h = 200 * c.u * scale
    for k in range(n):
        X = c.px(x - width / 2 + width * (k + 0.5) / n)
        Y = c.py(y) + math.sin(k * 2.1) * 6 * c.u
        c.d.line([(X, Y), (X, Y - h)], fill=c.pal["wood"] + (255,), width=max(1, int(h * 0.02)))
        if style == "tall":
            pts = flag_points(X, Y - h, h * 0.18, h * 0.6, t + k * 0.6, waves=1.0, amp=0.04)
            c.d.line([(X, Y - h), (X + h * 0.2, Y - h)], fill=c.pal["wood"] + (255,), width=max(1, int(h * 0.015)))
        else:
            pts = flag_points(X, Y - h, h * 0.45, h * 0.26, t + k * 0.6)
        c.d.polygon(pts, fill=col + (255,))


@component("tree", category="element", desc="Cây đơn (tán tròn hoặc thông).", params={"style": "broadleaf | pine | palm"}, spacing=0.08)
def draw_tree(c, x, y, scale, t, style="broadleaf", **p):
    X, Y = c.px(x), c.py(y)
    h = 300 * c.u * scale
    col = c.pal["sil"]
    d = c.d
    if style == "pine":
        for k in range(4):
            w = h * (0.32 - k * 0.06)
            yb = Y - h * (0.15 + k * 0.2)
            d.polygon([(X - w, yb), (X + w, yb), (X, yb - h * 0.35)], fill=col + (255,))
        d.rectangle([X - h * 0.03, Y - h * 0.2, X + h * 0.03, Y], fill=col + (255,))
    elif style == "palm":
        d.line([(X, Y), (X + h * 0.1, Y - h * 0.5), (X + h * 0.05, Y - h)], fill=col + (255,), width=max(2, int(h * 0.04)))
        for a in range(7):
            ang = -math.pi / 2 + (a - 3) * 0.5
            d.line([(X + h * 0.05, Y - h), (X + h * 0.05 + math.cos(ang) * h * 0.35, Y - h + math.sin(ang) * h * 0.2 + h * 0.15)],
                   fill=col + (255,), width=max(2, int(h * 0.03)))
    else:
        d.rectangle([X - h * 0.04, Y - h * 0.5, X + h * 0.04, Y], fill=col + (255,))
        rr = random.Random(int(x * 999))
        for _ in range(7):
            cx = X + rr.uniform(-0.2, 0.2) * h
            cy = Y - h * rr.uniform(0.55, 0.85)
            r = h * rr.uniform(0.15, 0.24)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col + (255,))


@component("rock", category="element", desc="Tảng đá / mỏm đá.", spacing=0.06)
def draw_rock(c, x, y, scale, t, **p):
    X, Y = c.px(x), c.py(y)
    s = 120 * c.u * scale
    rr = random.Random(int(x * 777))
    pts = [(X - s, Y)]
    for k in range(1, 8):
        u = k / 8
        pts.append((X - s + 2 * s * u, Y - s * 0.7 * math.sin(math.pi * u) * rr.uniform(0.7, 1.1)))
    pts.append((X + s, Y))
    c.d.polygon(pts, fill=mix(c.pal["stone"], c.pal["sil"], 0.4) + (255,))


@component("tents", category="building", desc="Doanh trại: nhiều lều vải.", params={"n": "số lều", "width": "độ rộng"})
def draw_tents(c, x, y, scale, t, n=5, width=0.35, **p):
    d = c.d
    rr = random.Random(int(x * 555))
    col = mix(c.pal["sail"], c.pal["sil"], 0.4)
    for k in range(int(n)):
        X = c.px(x - width / 2 + width * (k + 0.5) / n) + rr.uniform(-10, 10) * c.u
        Y = c.py(y) + rr.uniform(-8, 8) * c.u
        s = 90 * c.u * scale * rr.uniform(0.8, 1.2)
        d.polygon([(X - s, Y), (X + s, Y), (X + s * 0.1, Y - s * 0.9), (X - s * 0.1, Y - s * 0.9)], fill=col + (255,))
        d.polygon([(X - s * 0.15, Y), (X + s * 0.15, Y), (X, Y - s * 0.5)], fill=c.pal["sil"] + (255,))
        d.line([(X, Y - s * 0.9), (X, Y - s * 1.2)], fill=c.pal["wood"] + (255,), width=max(1, int(3 * c.u)))


def crowd(c, x, y, scale, t, width=0.4, rows=3, density="medium", head="round", weapon="spear", shield=None,
          facing=1, banners=0, accent=None, banner_col=None, mix_weapons=None, color=None, side="ally"):
    """Đám đông bóng người, xếp nhiều hàng (hàng sau nhỏ hơn và mờ hơn)."""
    d = c.d
    # màu từ plan.json có thể là danh sách [r, g, b] hoặc bị bỏ trống -> chuẩn hoá về tuple, mặc định theo phe
    accent = tuple(int(v) for v in accent[:3]) if accent else None
    banner_col = tuple(int(v) for v in banner_col[:3]) if banner_col else \
        tuple(c.pal["flag_enemy" if side == "enemy" else "flag_ally"][:3])
    color = tuple(int(v) for v in color[:3]) if color else None
    try:
        facing = float(facing)
    except (TypeError, ValueError):
        facing = 1
    rr = random.Random(int(x * 1000 + y * 100 + rows))
    dens = {"low": 0.55, "medium": 1.0, "high": 1.6}.get(str(density), 1.0)
    base_h = 70 * c.u * scale
    col0 = tuple(color) if color else c.pal["sil"]
    weapons = mix_weapons or [weapon]
    fx = 1 if facing >= 0 else -1
    for r in range(int(rows) - 1, -1, -1):
        h = base_h * (1 - 0.13 * r)
        yb = c.py(y) - r * h * 0.32
        col = mix(col0, c.pal["sky"][2], 0.12 * r)
        spacing = h * 0.32 / dens
        X = c.px(x - width / 2)
        x_end = c.px(x + width / 2)
        k = 0
        while X < x_end:
            w = weapons[rr.randrange(len(weapons))]
            figure(d, X + rr.uniform(-0.2, 0.2) * spacing, yb + rr.uniform(-0.04, 0.04) * h, h * rr.uniform(0.92, 1.06),
                   col + (255,), head=head, weapon=w, shield=shield, facing=fx, phase=rr.uniform(0, 6.28),
                   accent=(accent + (255,)) if accent else None,
                   banner=(banner_col + (255,)) if (banners and rr.random() < float(banners)) else None,
                   lean=rr.uniform(-0.3, 0.3))
            X += spacing * rr.uniform(0.8, 1.2)
            k += 1


@component("army", category="people", desc="Đám quân đông (bóng người nhìn từ xa), dùng chung mọi nước.",
           params={"width": "độ rộng 0.1-1", "rows": "số hàng 1-6", "density": "low|medium|high",
                   "head": "nonla|cone|kabuto|jingasa|gat|joseon_helmet|norman|round|greathelm|topknot|hood|bare",
                   "weapon": "spear|bow|sword|musket|axe|naginata|none", "shield": "round|kite|rect|null",
                   "facing": "1 (nhìn phải) / -1", "banners": "tỉ lệ người cắm cờ lưng 0-1"}, spacing=0.4)
def draw_army(c, x, y, scale, t, **p):
    crowd(c, x, y, scale, t, **{k: v for k, v in p.items() if k in (
        "width", "rows", "density", "head", "weapon", "shield", "facing", "banners", "accent", "banner_col", "mix_weapons", "color",
        "side")})


@component("cavalry", category="people", desc="Kỵ binh: hàng ngựa có người cưỡi (bóng).",
           params={"n": "số ngựa", "width": "độ rộng", "head": "kiểu mũ", "weapon": "spear|sword|bow", "facing": "1/-1",
                   "shield": "kite|round|null"}, spacing=0.4)
def draw_cavalry(c, x, y, scale, t, n=6, width=0.4, head="round", weapon="spear", facing=1, shield=None, rows=1, **p):
    rr = random.Random(int(x * 333))
    fx = 1 if facing >= 0 else -1
    for r in range(int(rows) - 1, -1, -1):
        hh = 80 * c.u * scale * (1 - 0.15 * r)
        col = mix(c.pal["sil"], c.pal["sky"][2], 0.12 * r)
        for k in range(int(n)):
            X = c.px(x - width / 2 + width * (k + 0.5) / n) + rr.uniform(-12, 12) * c.u
            Y = c.py(y) - r * hh * 0.4 + rr.uniform(-5, 5) * c.u
            horse(c.d, X, Y, hh * rr.uniform(0.92, 1.05), col + (255,), facing=fx, phase=rr.uniform(0, 6),
                  rider={"head": head, "weapon": weapon, "shield": shield}, rider_col=col + (255,))


@component("archers_volley", category="effect", desc="Loạt tên bay theo đường cong (động).",
           params={"to": "[x,y] điểm rơi", "n": "số mũi tên (mặc định 40)", "start": "giây bắt đầu", "dur": "thời gian bay"})
def draw_archers_volley(c, x, y, scale, t, to=(0.7, 0.6), n=40, start=0.5, dur=2.0, **p):
    c.add_effect(type="arrows", depth=c.depth, src=(c.px(x) + c.ox, c.py(y) + c.oy),
                 dst=(c.px(to[0]) + c.ox, c.py(to[1]) + c.oy), n=int(n), start=float(start), dur=float(dur),
                 col=c.pal["sil"], size=40 * c.u * scale)


@component("house_thatch", category="building", desc="Nhà tranh mái rạ (làng quê Á Đông).", spacing=0.12)
def draw_house_thatch(c, x, y, scale, t, **p):
    X, Y = c.px(x), c.py(y)
    s = 140 * c.u * scale
    d = c.d
    wall = mix(c.pal["wood"], c.pal["ground"][0], 0.4)
    d.rectangle([X - s, Y - s * 0.6, X + s, Y], fill=wall + (255,))
    roof = mix(c.pal["sail"], c.pal["sil"], 0.45)
    d.polygon([(X - s * 1.35, Y - s * 0.55), (X + s * 1.35, Y - s * 0.55), (X + s * 0.8, Y - s * 1.3), (X - s * 0.8, Y - s * 1.3)], fill=roof + (255,))
    d.rectangle([X - s * 0.2, Y - s * 0.45, X + s * 0.2, Y], fill=c.pal["sil"] + (255,))
