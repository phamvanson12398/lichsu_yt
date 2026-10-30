"""Bộ thành phần Hàn Quốc (Triều Tiên thời Joseon): thuyền rùa geobukseon, panokseon, cung điện mái cong,
tường thành, binh sĩ đội mũ, cờ.
"""
import random

from assets_code.common.elements import crowd, draw_flag
from assets_code.common.shiputil import burning_flames, ship_on_tmp
from assets_code.registry import component
from render.common import mix


@component("turtle_ship", category="ship", anim="bob", y_default=0.66, era=(1400, 1900), spacing=0.2,
           desc="Thuyền rùa (geobukseon) Joseon: mui kín như mai rùa có gai sắt, đầu rồng ở mũi phả khói, nhiều mái chèo. Rộng ~420px ở scale 1.",
           params={"state": "normal | burning", "flip": "true = quay trái", "smoke": "true = đầu rồng phả khói"})
def draw_turtle_ship(c, x, y, scale, t, state="normal", flip=False, tilt=0, smoke=True, **p):
    pal = c.pal
    s = c.u * scale * 0.55
    f = -1 if flip else 1
    hull = pal["wood"] + (255,)
    shell = mix(pal["wood"], pal["sil"], 0.35) + (255,)
    spike = mix(pal["stone"], (200, 200, 200), 0.3) + (255,)
    dark = mix(pal["wood"], pal["sil"], 0.6) + (255,)

    def fn(d, ox, oy, s):
        X = lambda v: ox + f * v * s
        d.polygon([(X(-360), oy - 110 * s), (X(380), oy - 110 * s), (X(330), oy + 10 * s), (X(-320), oy + 10 * s)], fill=hull)
        d.chord([min(X(-340), X(340)), oy - 280 * s, max(X(-340), X(340)), oy - 40 * s], 180, 360, fill=shell)
        for k in range(-6, 7):
            for row in range(3):
                px_ = X(k * 45 + row * 12)
                py_ = oy - (240 - row * 40 - abs(k) * (6 + row * 3)) * s
                d.polygon([(px_ - 6 * s, py_), (px_ + 6 * s, py_), (px_, py_ - 18 * s)], fill=spike)
        d.line([(X(-300), oy - 160 * s), (X(300), oy - 160 * s)], fill=dark, width=max(1, int(4 * s)))
        hx = X(390)
        d.polygon([(X(340), oy - 140 * s), (hx, oy - 190 * s), (X(450), oy - 175 * s), (X(445), oy - 150 * s),
                   (X(395), oy - 130 * s)], fill=dark)
        d.ellipse([X(420) - 6 * s, oy - 178 * s, X(420) + 6 * s, oy - 168 * s], fill=(230, 200, 80, 255))
        for k in range(10):
            xo = X(-280 + k * 60)
            d.rectangle([xo - 6 * s, oy - 95 * s, xo + 6 * s, oy - 80 * s], fill=dark)
            d.line([(xo, oy - 85 * s), (xo - f * 45 * s, oy + 60 * s)], fill=dark, width=max(1, int(6 * s)))
        if state == "burning":
            burning_flames(d, [(X(-100), oy - 230 * s, 80), (X(120), oy - 240 * s, 90)], s, pal["fire"])

    fires = [(-100 * f, -300, 140), (120 * f, -310, 150)] if state == "burning" else []
    X0, Y0 = c.px(x), c.py(y)
    ship_on_tmp(c, X0, Y0, s, tilt, fn, fires=fires)
    if smoke:
        c.add_effect(type="emitter", kind="smoke", depth=c.depth, at=(X0 + c.ox + f * 450 * s, Y0 + c.oy - 165 * s), rate=0.3,
                     size=0.6 * s / c.u)


@component("panokseon", category="ship", anim="bob", y_default=0.64, era=(1555, 1900), spacing=0.22,
           desc="Chiến thuyền panokseon Joseon: thân cao 2 tầng, lầu chỉ huy trên boong, 2 buồm vuông, nhiều mái chèo. Rộng ~460px ở scale 1.",
           params={"state": "normal | burning | broken", "flip": "true = quay trái"})
def draw_panokseon(c, x, y, scale, t, state="normal", flip=False, tilt=0, **p):
    pal = c.pal
    s = c.u * scale * 0.55
    f = -1 if flip else 1
    hull = pal["wood"] + (255,)
    deck = mix(pal["wood"], pal["roof"], 0.4) + (255,)
    dark = mix(pal["wood"], pal["sil"], 0.6) + (255,)
    sail = pal["sail"] + (255,)
    flag = pal["flag_ally"] + (255,)

    def fn(d, ox, oy, s):
        X = lambda v: ox + f * v * s
        d.polygon([(X(-400), oy - 150 * s), (X(420), oy - 150 * s), (X(340), oy + 10 * s), (X(-330), oy + 10 * s)], fill=hull)
        d.rectangle([min(X(-330), X(330)), oy - 230 * s, max(X(-330), X(330)), oy - 150 * s], fill=deck)
        for k in range(12):
            xx = X(-310 + k * 55)
            d.rectangle([xx - 8 * s, oy - 205 * s, xx + 8 * s, oy - 180 * s], fill=dark)
        d.rectangle([min(X(-80), X(80)), oy - 310 * s, max(X(-80), X(80)), oy - 230 * s], fill=deck)
        d.polygon([(X(-120), oy - 305 * s), (X(120), oy - 305 * s), (X(80), oy - 350 * s), (X(-80), oy - 350 * s)], fill=dark)
        if state != "broken":
            for mx, mh, sw in [(-170, 520, 160), (190, 470, 150)]:
                xm = X(mx)
                d.line([(xm, oy - 230 * s), (xm, oy - (230 + mh) * s)], fill=dark, width=max(2, int(10 * s)))
                d.rectangle([min(xm - sw / 2 * s, xm + sw / 2 * s), oy - (230 + mh - 30) * s, max(xm - sw / 2 * s, xm + sw / 2 * s),
                             oy - 300 * s], fill=sail)
                for k in range(1, 6):
                    yy = oy - (230 + mh - 30) * s + k * (mh - 100) * s / 6
                    d.line([(xm - sw / 2 * s, yy), (xm + sw / 2 * s, yy)], fill=dark, width=max(1, int(4 * s)))
                d.polygon([(xm, oy - (230 + mh) * s), (xm + f * 60 * s, oy - (230 + mh - 15) * s), (xm, oy - (230 + mh - 35) * s)], fill=flag)
        for k in range(9):
            xo = X(-280 + k * 70)
            d.line([(xo, oy - 60 * s), (xo - f * 45 * s, oy + 60 * s)], fill=dark, width=max(1, int(6 * s)))
        if state == "burning":
            burning_flames(d, [(X(-150), oy - 240 * s, 90), (X(150), oy - 240 * s, 100)], s, pal["fire"])

    fires = [(-150 * f, -320, 150), (150 * f, -330, 160)] if state == "burning" else []
    if state == "broken" and not tilt:
        tilt = 12
    ship_on_tmp(c, c.px(x), c.py(y), s, tilt, fn, size=(1000, 1000), anchor=(500, 820), fires=fires)


def curved_roof(d, X, Y, w, h, col, lift=0.25, s=1.0):
    """Mái cong Đông Á: đáy rộng, hai đầu đao vểnh lên."""
    pts = [(X - w * 0.5, Y - h * lift), (X - w * 0.44, Y), (X + w * 0.44, Y), (X + w * 0.5, Y - h * lift),
           (X + w * 0.32, Y - h * 0.55), (X + w * 0.22, Y - h), (X - w * 0.22, Y - h), (X - w * 0.32, Y - h * 0.55)]
    d.polygon(pts, fill=col)


@component("joseon_palace", category="building", y_default=0.7, era=(1392, 1910), spacing=0.5,
           desc="Cung điện Joseon (kiểu Gyeongbokgung): nền đá, hàng cột đỏ, mái cong hai tầng.")
def draw_joseon_palace(c, x, y, scale, t, **p):
    d = c.d
    s = c.u * scale
    X, Y = c.px(x), c.py(y)
    stone = mix(c.pal["stone"], (200, 196, 186), 0.2) + (255,)
    d.rectangle([X - 330 * s, Y - 40 * s, X + 330 * s, Y], fill=stone)
    d.rectangle([X - 280 * s, Y - 60 * s, X + 280 * s, Y - 40 * s], fill=stone)
    pillar = mix((150, 40, 30), c.pal["sil"], 0.35) + (255,)
    for k in range(9):
        cx = X - 240 * s + k * 60 * s
        d.rectangle([cx - 8 * s, Y - 190 * s, cx + 8 * s, Y - 60 * s], fill=pillar)
    d.rectangle([X - 250 * s, Y - 205 * s, X + 250 * s, Y - 185 * s], fill=mix((40, 90, 70), c.pal["sil"], 0.4) + (255,))
    roof = c.pal["roof"] + (255,)
    curved_roof(d, X, Y - 195 * s, 640 * s, 120 * s, roof)
    d.rectangle([X - 170 * s, Y - 345 * s, X + 170 * s, Y - 300 * s], fill=pillar)
    curved_roof(d, X, Y - 330 * s, 460 * s, 110 * s, roof)


@component("fortress_wall_kr", category="building", y_default=0.7, spacing=0.6,
           desc="Tường thành đá Triều Tiên có lỗ châu mai và lầu cổng mái cong.", params={"width": "độ rộng 0.3-1.2"})
def draw_fortress_wall_kr(c, x, y, scale, t, width=0.8, **p):
    d = c.d
    s = c.u * scale
    X0, X1, Y = c.px(x - width / 2), c.px(x + width / 2), c.py(y)
    stone = c.pal["stone"] + (255,)
    dark = mix(c.pal["stone"], c.pal["sil"], 0.5) + (255,)
    d.rectangle([X0, Y - 150 * s, X1, Y], fill=stone)
    rr = random.Random(int(x * 91))
    for row in range(5):
        yy = Y - 30 * s * row
        d.line([(X0, yy), (X1, yy)], fill=dark, width=max(1, int(2 * s)))
        xx = X0 + rr.uniform(0, 40) * s
        while xx < X1:
            d.line([(xx, yy), (xx, yy - 30 * s)], fill=dark, width=max(1, int(2 * s)))
            xx += rr.uniform(40, 70) * s
    xx = X0
    while xx < X1:
        d.rectangle([xx, Y - 180 * s, xx + 40 * s, Y - 150 * s], fill=stone)
        xx += 60 * s
    gx = c.px(x)
    d.rectangle([gx - 110 * s, Y - 240 * s, gx + 110 * s, Y - 150 * s], fill=mix((150, 40, 30), c.pal["sil"], 0.4) + (255,))
    curved_roof(d, gx, Y - 230 * s, 300 * s, 90 * s, c.pal["roof"] + (255,))
    d.chord([gx - 50 * s, Y - 110 * s, gx + 50 * s, Y + 10 * s], 180, 360, fill=c.pal["sil"] + (255,))
    d.rectangle([gx - 50 * s, Y - 50 * s, gx + 50 * s, Y], fill=c.pal["sil"] + (255,))


@component("soldiers_kr", category="people", y_default=0.8, spacing=0.4,
           desc="Binh sĩ Joseon: mũ trụ có chỏm lông (hoặc mũ gat), giáo / cung (bóng người).",
           params={"width": "độ rộng", "rows": "số hàng", "density": "low|medium|high", "weapon": "spear|bow|sword",
                   "hat": "helmet | gat", "facing": "1/-1"})
def draw_soldiers_kr(c, x, y, scale, t, width=0.4, rows=3, density="medium", weapon="spear", hat="helmet", facing=1, banners=0.0, **p):
    crowd(c, x, y, scale, t, width=width, rows=rows, density=density, head="gat" if hat == "gat" else "joseon_helmet",
          weapon=weapon, facing=facing, accent=mix(c.pal["flag_ally"], c.pal["sil"], 0.3), banners=banners,
          banner_col=c.pal["flag_ally"])


@component("flag_kr", category="effect", anim="redraw", bbox=(260, 380), desc="Cờ hiệu quân Joseon bay trên cột.",
           params={"height": "px 1080p", "facing": "1/-1", "color": "[r,g,b]"})
def draw_flag_kr(c, x, y, scale, t, height=260, facing=1, color=None, **p):
    draw_flag(c, x, y, scale, t, side="ally", color=color or (40, 70, 130), height=height, facing=facing, emblem="circle")
