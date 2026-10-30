"""Bộ thành phần Việt Nam: thuyền chiến, thuyền thúng, cọc Bạch Đằng, quân nón lá, thành lũy,
cổng làng, mái đình, voi chiến, cờ.
"""
import math
import random

from assets_code.common.elements import crowd, draw_flag
from assets_code.common.shapes import figure, stake
from assets_code.common.shiputil import burning_flames, ship_on_tmp
from assets_code.registry import component
from render.common import lerp, mix


@component("boat_vn", category="ship", anim="bob", y_default=0.66, spacing=0.18,
           desc="Thuyền chiến Việt: thân dài, mũi lái cong, mui che giữa, nhiều mái chèo, cờ đỏ. Rộng ~420px ở scale 1.",
           params={"state": "normal | burning | broken", "tilt": "độ nghiêng", "flip": "true = quay trái", "sail": "true/false"})
def draw_boat_vn(c, x, y, scale, t, state="normal", tilt=0, flip=False, sail=True, **p):
    pal = c.pal
    s = c.u * scale * 0.55
    hull = pal["wood"] + (255,)
    dark = mix(pal["wood"], pal["sil"], 0.5) + (255,)
    flag = pal["flag_ally"] + (255,)
    sailc = mix(pal["sail"], pal["wood"], 0.25) + (255,)
    f = -1 if flip else 1

    def fn(d, ox, oy, s):
        X = lambda v: ox + f * v * s
        d.polygon([(X(-400), oy - 120 * s), (X(-340), oy - 70 * s), (X(-250), oy - 40 * s), (X(250), oy - 40 * s),
                   (X(360), oy - 80 * s), (X(420), oy - 140 * s), (X(380), oy - 30 * s), (X(300), oy + 12 * s),
                   (X(-300), oy + 12 * s), (X(-370), oy - 40 * s)], fill=hull)
        d.line([(X(-330), oy - 45 * s), (X(330), oy - 45 * s)], fill=dark, width=max(1, int(6 * s)))
        # mui thuyền
        d.chord([min(X(-130), X(120)), oy - 150 * s, max(X(-130), X(120)), oy - 10 * s], 180, 360, fill=dark)
        for k in range(10):
            ox_ = X(-260 + k * 55)
            d.line([(ox_, oy - 30 * s), (ox_ - f * 40 * s, oy + 70 * s)], fill=dark, width=max(1, int(6 * s)))
        if sail and state != "broken":
            mx = X(160)
            d.line([(mx, oy - 45 * s), (mx, oy - 420 * s)], fill=dark, width=max(2, int(9 * s)))
            d.polygon([(mx, oy - 400 * s), (mx + f * 150 * s, oy - 380 * s), (mx + f * 170 * s, oy - 120 * s), (mx, oy - 110 * s)], fill=sailc)
            for k in range(1, 5):
                yy = oy - 400 * s + k * 58 * s
                d.line([(mx, yy), (mx + f * 160 * s, yy + 10 * s)], fill=dark, width=max(1, int(4 * s)))
            d.polygon([(mx, oy - 420 * s), (mx + f * 70 * s, oy - 405 * s), (mx, oy - 385 * s)], fill=flag)
        elif state == "broken":
            mx = X(160)
            d.line([(mx, oy - 45 * s), (mx + f * 60 * s, oy - 220 * s)], fill=dark, width=max(2, int(9 * s)))
        d.line([(X(-380), oy - 120 * s), (X(-395), oy - 260 * s)], fill=dark, width=max(1, int(5 * s)))
        d.polygon([(X(-395), oy - 260 * s), (X(-310), oy - 245 * s), (X(-395), oy - 215 * s)], fill=flag)
        if state == "burning":
            burning_flames(d, [(X(-60), oy - 140 * s, 70), (X(150), oy - 120 * s, 90)], s, pal["fire"])

    fires = [(-60 * f, -200, 140), (150 * f, -210, 160)] if state == "burning" else []
    ship_on_tmp(c, c.px(x), c.py(y), s, tilt + (12 * (1 if x < 0.5 else -1) if state == "broken" and not tilt else 0), fn,
                fires=fires)


@component("basket_boat", category="ship", anim="bob", y_default=0.72, spacing=0.07,
           desc="Thuyền thúng tròn đan tre, một người chèo. Rộng ~120px ở scale 1.")
def draw_basket_boat(c, x, y, scale, t, **p):
    X, Y = c.px(x), c.py(y)
    s = c.u * scale
    d = c.d
    d.chord([X - 60 * s, Y - 40 * s, X + 60 * s, Y + 22 * s], 0, 180, fill=c.pal["wood"] + (255,))
    d.line([(X - 60 * s, Y - 9 * s), (X + 60 * s, Y - 9 * s)], fill=mix(c.pal["wood"], (200, 170, 110), 0.3) + (255,), width=max(1, int(3 * s)))
    figure(d, X, Y - 6 * s, 70 * s, c.pal["sil"] + (255,), head="nonla", weapon="none",
           accent=mix(c.pal["sail"], (200, 170, 100), 0.4) + (255,))
    d.line([(X + 10 * s, Y - 40 * s), (X + 55 * s, Y + 25 * s)], fill=c.pal["sil"] + (255,), width=max(1, int(4 * s)))


@component("stakes_field", category="element", y_default=0.7, spacing=0.5,
           desc="Bãi cọc gỗ đầu bịt sắt cắm lòng sông (Bạch Đằng). Nước lên chỉ lộ chóp, nước rút lộ cả cọc.",
           params={"width": "độ rộng 0.1-1.2", "density": "low|medium|high", "tide": "high | low", "rows": "1-4"})
def draw_stakes_field(c, x, y, scale, t, width=0.5, density="medium", tide="low", rows=2, **p):
    d = c.d
    rr = random.Random(int(x * 1000) + 3)
    dens = {"low": 0.6, "medium": 1.0, "high": 1.6}.get(str(density), 1.0)
    wood = mix(c.pal["wood"], c.pal["sil"], 0.3) + (255,)
    iron = mix((120, 124, 130), c.pal["sil"], 0.35) + (255,)
    for r in range(int(rows) - 1, -1, -1):
        k = 1 - 0.18 * r
        w = 22 * c.u * scale * k
        Yb = c.py(y) - r * 30 * c.u * scale
        tall = (130 if tide == "low" else 45) * c.u * scale * k
        X = c.px(x - width / 2)
        while X < c.px(x + width / 2):
            tip = Yb - tall * rr.uniform(0.75, 1.15)
            stake(d, X, tip, Yb + 10 * c.u, w=w, wood=wood, iron=iron, lean=rr.uniform(-1, 1) * w * 0.8)
            X += w * rr.uniform(3.2, 6.0) / dens


@component("soldiers_vn", category="people", y_default=0.8, spacing=0.4,
           desc="Quân Việt: nón lá, giáo, khiên mây (bóng người, đông). Kích thước người ~70px ở scale 1.",
           params={"width": "độ rộng", "rows": "số hàng", "density": "low|medium|high", "weapon": "spear|bow|sword",
                   "facing": "1/-1", "banners": "0-1"})
def draw_soldiers_vn(c, x, y, scale, t, width=0.4, rows=3, density="medium", weapon="spear", facing=1, banners=0.0, **p):
    crowd(c, x, y, scale, t, width=width, rows=rows, density=density, head="nonla", weapon=weapon, shield="round",
          facing=facing, accent=mix(c.pal["sail"], (190, 160, 100), 0.4), banners=banners, banner_col=c.pal["flag_ally"])


@component("citadel_vn", category="building", y_default=0.62, spacing=0.6,
           desc="Thành lũy đất kiểu cổ (Cổ Loa): tường đất dốc, hàng rào gỗ, vọng lâu mái cong ở cổng.",
           params={"width": "độ rộng 0.3-1.2"})
def draw_citadel_vn(c, x, y, scale, t, width=0.7, **p):
    d = c.d
    s = c.u * scale
    X0, X1 = c.px(x - width / 2), c.px(x + width / 2)
    Y = c.py(y)
    earth = mix(c.pal["ground"][0], c.pal["mount"][-1], 0.5) + (255,)
    d.polygon([(X0 - 60 * s, Y), (X1 + 60 * s, Y), (X1, Y - 110 * s), (X0, Y - 110 * s)], fill=earth)
    wood = c.pal["wood"] + (255,)
    xx = X0
    while xx < X1:
        d.polygon([(xx - 6 * s, Y - 108 * s), (xx + 6 * s, Y - 108 * s), (xx, Y - 150 * s)], fill=wood)
        d.rectangle([xx - 6 * s, Y - 135 * s, xx + 6 * s, Y - 108 * s], fill=wood)
        xx += 16 * s
    gx = c.px(x)
    d.rectangle([gx - 70 * s, Y - 230 * s, gx + 70 * s, Y - 100 * s], fill=wood)
    d.rectangle([gx - 32 * s, Y - 160 * s, gx + 32 * s, Y - 100 * s], fill=c.pal["sil"] + (255,))
    roof = c.pal["roof"] + (255,)
    d.polygon([(gx - 120 * s, Y - 220 * s), (gx + 120 * s, Y - 220 * s), (gx + 140 * s, Y - 245 * s), (gx + 60 * s, Y - 290 * s),
               (gx - 60 * s, Y - 290 * s), (gx - 140 * s, Y - 245 * s)], fill=roof)


@component("village_gate", category="building", y_default=0.8, spacing=0.3,
           desc="Cổng làng Bắc Bộ: cổng gạch vòm, mái ngói cong nhỏ, luỹ tre hai bên.")
def draw_village_gate(c, x, y, scale, t, **p):
    d = c.d
    s = c.u * scale
    X, Y = c.px(x), c.py(y)
    brick = mix(c.pal["stone"], c.pal["ground"][0], 0.3) + (255,)
    d.rectangle([X - 130 * s, Y - 260 * s, X + 130 * s, Y], fill=brick)
    d.chord([X - 60 * s, Y - 220 * s, X + 60 * s, Y - 100 * s], 180, 360, fill=c.pal["sil"] + (255,))
    d.rectangle([X - 60 * s, Y - 160 * s, X + 60 * s, Y], fill=c.pal["sil"] + (255,))
    roof = c.pal["roof"] + (255,)
    d.polygon([(X - 175 * s, Y - 250 * s), (X + 175 * s, Y - 250 * s), (X + 195 * s, Y - 285 * s), (X + 110 * s, Y - 330 * s),
               (X - 110 * s, Y - 330 * s), (X - 195 * s, Y - 285 * s)], fill=roof)
    rr = random.Random(int(x * 77))
    bam = mix(c.pal["sil"], c.pal["ground"][0], 0.2) + (255,)
    for side in (-1, 1):
        for k in range(14):
            bx = X + side * (150 + k * 22) * s
            h = rr.uniform(260, 380) * s
            d.line([(bx, Y), (bx + side * 30 * s, Y - h)], fill=bam, width=max(1, int(5 * s)))
            d.ellipse([bx + side * 30 * s - 30 * s, Y - h - 20 * s, bx + side * 30 * s + 30 * s, Y - h + 50 * s], fill=bam)


@component("dinh_roof", category="building", y_default=0.75, spacing=0.4,
           desc="Đình làng: mái ngói lớn, đầu đao cong vút, hàng cột gỗ.")
def draw_dinh_roof(c, x, y, scale, t, **p):
    d = c.d
    s = c.u * scale
    X, Y = c.px(x), c.py(y)
    wood = c.pal["wood"] + (255,)
    d.rectangle([X - 250 * s, Y - 12 * s, X + 250 * s, Y], fill=mix(c.pal["stone"], c.pal["sil"], 0.3) + (255,))
    for k in range(7):
        cx = X - 210 * s + k * 70 * s
        d.rectangle([cx - 7 * s, Y - 140 * s, cx + 7 * s, Y - 12 * s], fill=wood)
    roof = c.pal["roof"] + (255,)
    d.polygon([(X - 330 * s, Y - 140 * s), (X + 330 * s, Y - 140 * s), (X + 230 * s, Y - 300 * s), (X - 230 * s, Y - 300 * s)], fill=roof)
    for side in (-1, 1):
        d.polygon([(X + side * 300 * s, Y - 140 * s), (X + side * 360 * s, Y - 190 * s), (X + side * 345 * s, Y - 150 * s)], fill=roof)
    d.line([(X - 235 * s, Y - 300 * s), (X + 235 * s, Y - 300 * s)], fill=mix(c.pal["roof"], c.pal["sil"], 0.4) + (255,), width=max(2, int(10 * s)))


@component("war_elephant", category="people", anim="bob", y_default=0.8, spacing=0.16,
           desc="Voi chiến có bành, quản tượng và lính cầm giáo (bóng). Cao ~220px ở scale 1.",
           params={"facing": "1/-1", "flag": "true/false"})
def draw_war_elephant(c, x, y, scale, t, facing=1, flag=True, **p):
    d = c.d
    s = c.u * scale
    f = 1 if facing >= 0 else -1
    X, Y = c.px(x), c.py(y)
    col = c.pal["sil"] + (255,)
    d.ellipse([X - 130 * s, Y - 210 * s, X + 110 * s, Y - 70 * s], fill=col)
    for lx in (-95, -45, 45, 85):
        d.rectangle([X + f * lx * s - 18 * s, Y - 110 * s, X + f * lx * s + 18 * s, Y], fill=col)
    hx = X + f * 120 * s
    d.ellipse([hx - 55 * s, Y - 230 * s, hx + 55 * s, Y - 120 * s], fill=col)
    d.line([(hx + f * 40 * s, Y - 160 * s), (hx + f * 75 * s, Y - 80 * s), (hx + f * 60 * s, Y - 20 * s)], fill=col, width=max(2, int(22 * s)))
    d.line([(hx + f * 30 * s, Y - 140 * s), (hx + f * 85 * s, Y - 135 * s)], fill=(220, 210, 190, 255), width=max(1, int(7 * s)))
    d.ellipse([hx - f * 20 * s - 35 * s, Y - 225 * s, hx - f * 20 * s + 35 * s, Y - 140 * s], fill=col)
    d.rectangle([X - 70 * s, Y - 260 * s, X + 40 * s, Y - 205 * s], fill=mix(c.pal["wood"], c.pal["sil"], 0.2) + (255,))
    d.polygon([(X - 85 * s, Y - 260 * s), (X + 55 * s, Y - 260 * s), (X - 15 * s, Y - 300 * s)], fill=c.pal["roof"] + (255,))
    figure(d, hx - f * 10 * s, Y - 215 * s, 60 * s, col, head="nonla", weapon="none", facing=f)
    figure(d, X - 20 * s, Y - 255 * s, 55 * s, col, head="nonla", weapon="spear", facing=f)
    if flag:
        d.line([(X - 60 * s, Y - 260 * s), (X - 60 * s, Y - 380 * s)], fill=col, width=max(1, int(4 * s)))
        d.polygon([(X - 60 * s, Y - 380 * s), (X - 60 * s - f * 60 * s, Y - 365 * s), (X - 60 * s, Y - 345 * s)], fill=c.pal["flag_ally"] + (255,))


@component("flag_vn", category="effect", anim="redraw", bbox=(260, 380), desc="Cờ hiệu quân Việt (đỏ, viền vàng) bay trên cột.",
           params={"height": "px 1080p", "facing": "1/-1"})
def draw_flag_vn(c, x, y, scale, t, height=260, facing=1, **p):
    draw_flag(c, x, y, scale, t, side="ally", color=c.pal["flag_ally"], height=height, facing=facing, emblem="stripe")
