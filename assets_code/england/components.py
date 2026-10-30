"""Bộ thành phần Anh (Trung cổ): thuyền dài kiểu Viking / Norman, lâu đài đá, tường thành răng cưa,
hiệp sĩ cưỡi ngựa (bóng), cung thủ, tường khiên, cờ hiệu.
"""
import random

from assets_code.common.elements import crowd, draw_cavalry, draw_flag
from assets_code.common.shiputil import burning_flames, ship_on_tmp
from assets_code.registry import component
from render.common import mix


@component("longship", category="ship", anim="bob", y_default=0.66, era=(700, 1300), spacing=0.2,
           desc="Thuyền dài kiểu Viking / Norman: thân thấp dài, mũi lái cong cao, hàng khiên tròn bên mạn, buồm vuông sọc. Rộng ~440px ở scale 1.",
           params={"state": "normal | burning", "flip": "true = quay trái", "sail": "true/false"})
def draw_longship(c, x, y, scale, t, state="normal", flip=False, tilt=0, sail=True, **p):
    pal = c.pal
    s = c.u * scale * 0.55
    f = -1 if flip else 1
    hull = pal["wood"] + (255,)
    dark = mix(pal["wood"], pal["sil"], 0.6) + (255,)
    shield_cols = [mix(pal["flag_ally"], pal["sil"], 0.2) + (255,), mix((200, 180, 120), pal["sil"], 0.3) + (255,)]
    sail_a = pal["sail"] + (255,)
    sail_b = mix(pal["flag_ally"], pal["sail"], 0.3) + (255,)

    def fn(d, ox, oy, s):
        X = lambda v: ox + f * v * s
        d.polygon([(X(-420), oy - 230 * s), (X(-400), oy - 120 * s), (X(-330), oy - 60 * s), (X(330), oy - 60 * s),
                   (X(400), oy - 120 * s), (X(430), oy - 240 * s), (X(445), oy - 230 * s), (X(420), oy - 80 * s),
                   (X(320), oy + 8 * s), (X(-320), oy + 8 * s), (X(-430), oy - 90 * s), (X(-440), oy - 220 * s)], fill=hull)
        d.ellipse([X(430) - 14 * s, oy - 262 * s, X(430) + 14 * s, oy - 232 * s], fill=hull)
        for k in range(12):
            sx = X(-300 + k * 55)
            d.ellipse([sx - 24 * s, oy - 100 * s, sx + 24 * s, oy - 52 * s], fill=shield_cols[k % 2])
            d.ellipse([sx - 6 * s, oy - 82 * s, sx + 6 * s, oy - 70 * s], fill=dark)
        for k in range(10):
            xo = X(-270 + k * 60)
            d.line([(xo, oy - 50 * s), (xo - f * 45 * s, oy + 60 * s)], fill=dark, width=max(1, int(5 * s)))
        if sail:
            xm = X(0)
            d.line([(xm, oy - 60 * s), (xm, oy - 520 * s)], fill=dark, width=max(2, int(10 * s)))
            top, bot = oy - 480 * s, oy - 170 * s
            for k in range(6):
                x0 = xm - 180 * s + k * 60 * s
                d.rectangle([x0, top + 10 * s, x0 + 60 * s, bot], fill=sail_a if k % 2 == 0 else sail_b)
            d.line([(xm - 190 * s, top), (xm + 190 * s, top)], fill=dark, width=max(1, int(8 * s)))
        if state == "burning":
            burning_flames(d, [(X(-60), oy - 200 * s, 100), (X(160), oy - 120 * s, 90)], s, pal["fire"])

    fires = [(-60 * f, -270, 150), (160 * f, -190, 140)] if state == "burning" else []
    ship_on_tmp(c, c.px(x), c.py(y), s, tilt, fn, fires=fires)


@component("stone_castle", category="building", y_default=0.66, era=(1066, 1600), spacing=0.5,
           desc="Lâu đài đá Trung cổ: tháp vuông (keep), tháp góc tròn, tường răng cưa, cờ trên đỉnh. Rộng ~600px ở scale 1.",
           params={"state": "normal | burning"})
def draw_stone_castle(c, x, y, scale, t, state="normal", **p):
    d = c.d
    s = c.u * scale
    X, Y = c.px(x), c.py(y)
    stone = c.pal["stone"] + (255,)
    dark = mix(c.pal["stone"], c.pal["sil"], 0.5) + (255,)

    def crenel(x0, x1, ytop, h=22):
        xx = x0
        while xx < x1:
            d.rectangle([xx, ytop - h * s, min(x1, xx + 18 * s), ytop], fill=stone)
            xx += 32 * s

    d.rectangle([X - 300 * s, Y - 160 * s, X + 300 * s, Y], fill=stone)
    crenel(X - 300 * s, X + 300 * s, Y - 160 * s)
    for side in (-1, 1):
        tx = X + side * 300 * s
        d.rectangle([tx - 50 * s, Y - 260 * s, tx + 50 * s, Y], fill=stone)
        crenel(tx - 50 * s, tx + 50 * s, Y - 260 * s)
        d.rectangle([tx - 6 * s, Y - 200 * s, tx + 6 * s, Y - 170 * s], fill=dark)
    d.rectangle([X - 110 * s, Y - 360 * s, X + 110 * s, Y - 120 * s], fill=stone)
    crenel(X - 110 * s, X + 110 * s, Y - 360 * s)
    for k in range(3):
        d.rectangle([X - 70 * s + k * 60 * s, Y - 300 * s, X - 60 * s + k * 60 * s, Y - 270 * s], fill=dark)
    d.chord([X - 45 * s, Y - 110 * s, X + 45 * s, Y + 10 * s], 180, 360, fill=c.pal["sil"] + (255,))
    d.rectangle([X - 45 * s, Y - 50 * s, X + 45 * s, Y], fill=c.pal["sil"] + (255,))
    d.line([(X, Y - 382 * s), (X, Y - 470 * s)], fill=dark, width=max(1, int(4 * s)))
    d.polygon([(X, Y - 470 * s), (X + 60 * s, Y - 455 * s), (X, Y - 435 * s)], fill=c.pal["flag_ally"] + (255,))
    rr = random.Random(int(x * 13))
    for _ in range(int(40 * scale)):
        bx, by = X + rr.uniform(-290, 290) * s, Y - rr.uniform(10, 150) * s
        d.line([(bx, by), (bx + 26 * s, by)], fill=dark, width=max(1, int(2 * s)))
    if state == "burning":
        burning_flames(d, [(X - 80 * s, Y - 360 * s, 110), (X + 280 * s, Y - 260 * s, 90)], s, c.pal["fire"])
        c.add_fire(X, Y - 350 * s, 260 * s)


@component("castle_wall", category="building", y_default=0.72, spacing=0.6,
           desc="Tường thành đá răng cưa kiểu châu Âu (crenellated), có tháp canh.", params={"width": "độ rộng 0.3-1.2"})
def draw_castle_wall(c, x, y, scale, t, width=0.8, **p):
    d = c.d
    s = c.u * scale
    X0, X1, Y = c.px(x - width / 2), c.px(x + width / 2), c.py(y)
    stone = c.pal["stone"] + (255,)
    dark = mix(c.pal["stone"], c.pal["sil"], 0.5) + (255,)
    d.rectangle([X0, Y - 170 * s, X1, Y], fill=stone)
    xx = X0
    while xx < X1:
        d.rectangle([xx, Y - 195 * s, xx + 22 * s, Y - 170 * s], fill=stone)
        xx += 38 * s
    n = max(2, int((X1 - X0) / (320 * s)))
    for k in range(n + 1):
        tx = X0 + (X1 - X0) * k / n
        d.rectangle([tx - 40 * s, Y - 250 * s, tx + 40 * s, Y], fill=stone)
        for j in range(3):
            d.rectangle([tx - 40 * s + j * 30 * s, Y - 275 * s, tx - 22 * s + j * 30 * s, Y - 250 * s], fill=stone)
        d.rectangle([tx - 5 * s, Y - 210 * s, tx + 5 * s, Y - 180 * s], fill=dark)


@component("knights", category="people", y_default=0.8, era=(1000, 1550), spacing=0.4,
           desc="Hiệp sĩ cưỡi ngựa (bóng): mũ chóp Norman, giáo dài, khiên hình diều.",
           params={"n": "số ngựa", "width": "độ rộng", "facing": "1/-1", "rows": "1-3"})
def draw_knights(c, x, y, scale, t, n=6, width=0.45, facing=1, rows=2, **p):
    draw_cavalry(c, x, y, scale, t, n=n, width=width, head="norman", weapon="spear", facing=facing, shield="kite", rows=rows)


@component("archers_en", category="people", y_default=0.82, spacing=0.4,
           desc="Cung thủ (bóng), mũ trùm / mũ tròn, cung dài.",
           params={"width": "độ rộng", "rows": "số hàng", "density": "low|medium|high", "facing": "1/-1"})
def draw_archers_en(c, x, y, scale, t, width=0.4, rows=2, density="medium", facing=1, **p):
    crowd(c, x, y, scale, t, width=width, rows=rows, density=density, head="hood", weapon="bow", facing=facing)


@component("shield_wall", category="people", y_default=0.8, era=(700, 1100), spacing=0.4,
           desc="Tường khiên Anglo-Saxon: hàng lính sát nhau, khiên tròn che trước, rìu và giáo.",
           params={"width": "độ rộng", "rows": "số hàng", "facing": "1/-1"})
def draw_shield_wall(c, x, y, scale, t, width=0.5, rows=3, facing=1, **p):
    crowd(c, x, y, scale, t, width=width, rows=rows, density="high", head="round", weapon="spear", shield="round",
          facing=facing, accent=mix(c.pal["flag_ally"], c.pal["sil"], 0.35), mix_weapons=["spear", "axe", "spear"])


@component("soldiers_norman", category="people", y_default=0.8, era=(900, 1200), spacing=0.4,
           desc="Bộ binh Norman (bóng): mũ chóp có thanh mũi, khiên diều, giáo / kiếm.",
           params={"width": "độ rộng", "rows": "số hàng", "density": "low|medium|high", "facing": "1/-1"})
def draw_soldiers_norman(c, x, y, scale, t, width=0.4, rows=3, density="medium", facing=-1, **p):
    crowd(c, x, y, scale, t, width=width, rows=rows, density=density, head="norman", weapon="spear", shield="kite",
          facing=facing, accent=mix(c.pal["flag_enemy"], c.pal["sil"], 0.2), mix_weapons=["spear", "sword"])


@component("banner_en", category="effect", anim="redraw", bbox=(260, 380), desc="Cờ hiệu Trung cổ (đuôi nhọn) bay trên cột.",
           params={"height": "px 1080p", "facing": "1/-1", "side": "ally | enemy", "color": "[r,g,b]"})
def draw_banner_en(c, x, y, scale, t, height=260, facing=1, side="ally", color=None, **p):
    draw_flag(c, x, y, scale, t, side=side, color=color, height=height, facing=facing, emblem="stripe")
