"""Bộ thành phần Nhật Bản: thuyền atakebune, lâu đài nhiều tầng (tenshu), cổng torii,
samurai (bóng), ashigaru cầm giáo / súng hỏa mai, cờ sashimono / nobori.
"""
from assets_code.common.elements import crowd, draw_banners_row
from assets_code.common.shiputil import burning_flames, ship_on_tmp
from assets_code.registry import component
from render.common import mix


@component("atakebune", category="ship", anim="bob", y_default=0.64, era=(1550, 1640), spacing=0.22,
           desc="Chiến thuyền atakebune Nhật: thân hộp lớn, mạn che bằng tấm khiên gỗ, lầu yagura nhiều tầng, 1 buồm vuông. Rộng ~460px ở scale 1.",
           params={"state": "normal | burning | broken", "flip": "true = quay trái", "tilt": "độ nghiêng"})
def draw_atakebune(c, x, y, scale, t, state="normal", flip=False, tilt=0, **p):
    pal = c.pal
    s = c.u * scale * 0.55
    f = -1 if flip else 1
    hull = pal["wood"] + (255,)
    box = mix(pal["wood"], pal["roof"], 0.3) + (255,)
    dark = mix(pal["wood"], pal["sil"], 0.6) + (255,)
    sail = pal["sail"] + (255,)
    flag = pal["flag_enemy"] + (255,)

    def fn(d, ox, oy, s):
        X = lambda v: ox + f * v * s
        d.polygon([(X(-400), oy - 120 * s), (X(430), oy - 140 * s), (X(340), oy + 10 * s), (X(-320), oy + 10 * s)], fill=hull)
        d.rectangle([min(X(-360), X(380)), oy - 250 * s, max(X(-360), X(380)), oy - 120 * s], fill=box)
        for k in range(14):
            xx = X(-345 + k * 52)
            d.rectangle([min(xx, xx + f * 44 * s), oy - 245 * s, max(xx, xx + f * 44 * s), oy - 125 * s], outline=dark,
                        width=max(1, int(3 * s)))
            d.rectangle([xx + f * 18 * s - 4 * s, oy - 200 * s, xx + f * 18 * s + 4 * s, oy - 190 * s], fill=dark)
        for lvl, (w, h) in enumerate([(220, 80), (150, 70)]):
            yb = oy - 250 * s - lvl * 90 * s
            cx = X(-120)
            d.rectangle([cx - w / 2 * s, yb - h * s, cx + w / 2 * s, yb], fill=box)
            d.polygon([(cx - (w / 2 + 40) * s, yb - h * s), (cx + (w / 2 + 40) * s, yb - h * s), (cx + w / 3 * s, yb - (h + 30) * s),
                       (cx - w / 3 * s, yb - (h + 30) * s)], fill=dark)
        if state != "broken":
            xm = X(170)
            d.line([(xm, oy - 250 * s), (xm, oy - 650 * s)], fill=dark, width=max(2, int(11 * s)))
            d.rectangle([xm - 120 * s, oy - 620 * s, xm + 120 * s, oy - 320 * s], fill=sail)
            for k in range(1, 5):
                d.line([(xm - 120 * s, oy - 620 * s + k * 60 * s), (xm + 120 * s, oy - 620 * s + k * 60 * s)], fill=dark,
                       width=max(1, int(3 * s)))
        for k in range(3):
            fx = X(300 + k * 30)
            d.line([(fx, oy - 250 * s), (fx, oy - 400 * s)], fill=dark, width=max(1, int(4 * s)))
            d.rectangle([min(fx, fx + f * 20 * s), oy - 400 * s, max(fx, fx + f * 20 * s), oy - 310 * s], fill=flag)
        for k in range(9):
            xo = X(-280 + k * 70)
            d.line([(xo, oy - 60 * s), (xo - f * 45 * s, oy + 60 * s)], fill=dark, width=max(1, int(6 * s)))
        if state == "burning":
            burning_flames(d, [(X(-120), oy - 420 * s, 100), (X(160), oy - 260 * s, 110)], s, pal["fire"])

    fires = [(-120 * f, -500, 160), (160 * f, -340, 170)] if state == "burning" else []
    if state == "broken" and not tilt:
        tilt = -12
    ship_on_tmp(c, c.px(x), c.py(y), s, tilt, fn, size=(1000, 1000), anchor=(500, 850), fires=fires)


@component("tenshu", category="building", y_default=0.66, era=(1576, 1900), spacing=0.4,
           desc="Lâu đài Nhật nhiều tầng (tenshu): nền đá dốc ishigaki, tường trắng, mái cong xếp tầng. Cao ~520px ở scale 1.",
           params={"tiers": "số tầng 3-6", "state": "normal | burning"})
def draw_tenshu(c, x, y, scale, t, tiers=5, state="normal", **p):
    d = c.d
    s = c.u * scale
    X, Y = c.px(x), c.py(y)
    stone = c.pal["stone"] + (255,)
    wall = mix((230, 226, 214), c.pal["sky"][2], 0.25) + (255,)
    roof = mix(c.pal["roof"], c.pal["sil"], 0.3) + (255,)
    d.polygon([(X - 230 * s, Y), (X + 230 * s, Y), (X + 170 * s, Y - 130 * s), (X - 170 * s, Y - 130 * s)], fill=stone)
    yb = Y - 130 * s
    w = 300 * s
    for k in range(int(tiers)):
        h = 70 * s * (1 - k * 0.06)
        d.rectangle([X - w / 2, yb - h, X + w / 2, yb], fill=wall)
        for wx in range(3):
            xx = X - w / 3 + wx * w / 3
            d.rectangle([xx - 8 * s, yb - h * 0.6, xx + 8 * s, yb - h * 0.35], fill=c.pal["sil"] + (255,))
        ry = yb - h
        d.polygon([(X - w / 2 - 45 * s, ry + 10 * s), (X - w / 2 - 25 * s, ry + 2 * s), (X + w / 2 + 25 * s, ry + 2 * s),
                   (X + w / 2 + 45 * s, ry + 10 * s), (X + w / 2 - 10 * s, ry - 35 * s), (X - w / 2 + 10 * s, ry - 35 * s)], fill=roof)
        if k % 2 == 1:
            d.polygon([(X - 40 * s, ry - 20 * s), (X + 40 * s, ry - 20 * s), (X, ry - 60 * s)], fill=roof)
        yb = ry - 30 * s
        w *= 0.8
    d.line([(X - 20 * s, yb + 5 * s), (X - 35 * s, yb - 20 * s)], fill=(210, 180, 90, 255), width=max(1, int(5 * s)))
    d.line([(X + 20 * s, yb + 5 * s), (X + 35 * s, yb - 20 * s)], fill=(210, 180, 90, 255), width=max(1, int(5 * s)))
    if state == "burning":
        burning_flames(d, [(X - 60 * s, Y - 200 * s, 100), (X + 70 * s, Y - 300 * s, 120)], s, c.pal["fire"])
        c.add_fire(X, Y - 300 * s, 260 * s)


@component("torii", category="building", y_default=0.8, spacing=0.25,
           desc="Cổng torii màu son trước đền Thần đạo. Cao ~300px ở scale 1.")
def draw_torii(c, x, y, scale, t, **p):
    d = c.d
    s = c.u * scale
    X, Y = c.px(x), c.py(y)
    red = mix((200, 60, 40), c.pal["sil"], 0.25) + (255,)
    blk = c.pal["sil"] + (255,)
    for side in (-1, 1):
        d.polygon([(X + side * 105 * s, Y), (X + side * 125 * s, Y), (X + side * 112 * s, Y - 280 * s), (X + side * 96 * s, Y - 280 * s)], fill=red)
    d.rectangle([X - 150 * s, Y - 245 * s, X + 150 * s, Y - 228 * s], fill=red)
    d.polygon([(X - 200 * s, Y - 300 * s), (X - 175 * s, Y - 280 * s), (X + 175 * s, Y - 280 * s), (X + 200 * s, Y - 300 * s),
               (X + 160 * s, Y - 290 * s), (X - 160 * s, Y - 290 * s)], fill=blk)
    d.rectangle([X - 170 * s, Y - 282 * s, X + 170 * s, Y - 266 * s], fill=red)
    d.rectangle([X - 10 * s, Y - 266 * s, X + 10 * s, Y - 245 * s], fill=red)


@component("samurai", category="people", y_default=0.8, spacing=0.4,
           desc="Samurai (bóng): mũ kabuto có sừng, kiếm / naginata / cung, cờ sashimono sau lưng.",
           params={"width": "độ rộng", "rows": "số hàng", "density": "low|medium|high", "weapon": "sword|naginata|bow|spear",
                   "facing": "1/-1", "banners": "tỉ lệ cắm sashimono 0-1", "side": "ally | enemy (màu sashimono)"})
def draw_samurai(c, x, y, scale, t, width=0.4, rows=2, density="medium", weapon="sword", facing=1, banners=0.6, side="ally", **p):
    crowd(c, x, y, scale, t, width=width, rows=rows, density=density, head="kabuto", weapon=weapon, facing=facing,
          accent=(200, 170, 80), banners=banners, banner_col=c.pal["flag_ally" if side == "ally" else "flag_enemy"])


@component("ashigaru", category="people", y_default=0.82, spacing=0.4,
           desc="Lính bộ ashigaru: nón dẹt jingasa, giáo dài hoặc súng hỏa mai (tanegashima, sau 1543).",
           params={"width": "độ rộng", "rows": "số hàng", "density": "low|medium|high", "weapon": "spear | musket",
                   "facing": "1/-1", "banners": "0-1", "side": "ally | enemy"})
def draw_ashigaru(c, x, y, scale, t, width=0.4, rows=3, density="medium", weapon="spear", facing=1, banners=0.25, side="ally", **p):
    crowd(c, x, y, scale, t, width=width, rows=rows, density=density, head="jingasa", weapon=weapon, facing=facing,
          banners=banners, banner_col=c.pal["flag_ally" if side == "ally" else "flag_enemy"])


@component("nobori_row", category="effect", anim="redraw", bbox=(900, 420),
           desc="Hàng cờ dọc nobori / sashimono kiểu Nhật phấp phới.", params={"n": "số cờ", "side": "ally | enemy", "width": "độ rộng"})
def draw_nobori_row(c, x, y, scale, t, n=7, side="ally", width=0.4, color=None, **p):
    draw_banners_row(c, x, y, scale, t, n=n, side=side, width=width, style="tall", color=color)
