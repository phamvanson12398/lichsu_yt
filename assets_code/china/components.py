"""Bộ thành phần Trung Hoa (dùng cho phe địch / quân xâm lược trong trận Việt Nam, Hàn Quốc...):
thuyền buồm kiểu Trung Hoa (junk), quân đội mũ nhọn.
"""
from assets_code.common.elements import crowd
from assets_code.common.shiputil import burning_flames, ship_on_tmp
from assets_code.registry import component
from render.common import mix


@component("junk_ship", category="ship", anim="bob", y_default=0.64, spacing=0.2,
           desc="Thuyền buồm Trung Hoa (vd thuyền quân Nam Hán, Nguyên, Minh): 2 cột buồm cánh dơi có nẹp, lầu đuôi, mái chèo. Rộng ~430px ở scale 1.",
           params={"state": "normal | burning | broken", "tilt": "độ nghiêng", "flip": "true = quay trái"})
def draw_junk_ship(c, x, y, scale, t, state="normal", tilt=0, flip=False, **p):
    pal = c.pal
    s = c.u * scale * 0.55
    hull = pal["wood"] + (255,)
    mast = mix(pal["wood"], pal["sil"], 0.5) + (255,)
    sail = (pal["sail"] if state != "burning" else mix(pal["sail"], pal["sil"], 0.3)) + (255,)
    flag = pal["flag_enemy"] + (255,)
    batten = mix(pal["sail"], pal["sil"], 0.5) + (255,)
    f = -1 if flip else 1

    def fn(d, ox, oy, s):
        X = lambda v: ox + f * v * s
        d.polygon([(X(-380), oy - 90 * s), (X(400), oy - 120 * s), (X(300), oy + 10 * s), (X(-300), oy + 10 * s)], fill=hull)
        d.rectangle([min(X(-260), X(-120)), oy - 150 * s, max(X(-260), X(-120)), oy - 90 * s], fill=hull)
        masts = [(-60, 520, 210), (150, 430, 170)]
        if state == "broken":
            masts = [(-60, 260, 0), (150, 430, 170)]
        for mx, mh, sw in masts:
            xm = X(mx)
            d.line([(xm, oy - 90 * s), (xm, oy - (90 + mh) * s)], fill=mast, width=max(2, int(10 * s)))
            if sw == 0:
                continue
            top = oy - (90 + mh - 30) * s
            bot = oy - 150 * s
            d.polygon([(xm - f * 8 * s, top), (xm + f * sw * s, top + 30 * s), (xm + f * sw * 1.1 * s, bot), (xm - f * 8 * s, bot)], fill=sail)
            for k in range(1, 6):
                yy = top + (bot - top) * k / 6
                d.line([(xm - f * 8 * s, yy), (xm + f * sw * 1.05 * s, yy + 15 * s)], fill=batten, width=max(1, int(5 * s)))
            d.polygon([(xm, oy - (90 + mh) * s), (xm + f * 70 * s, oy - (90 + mh - 15) * s), (xm, oy - (90 + mh - 35) * s)], fill=flag)
        for k in range(7):
            xo = X(-240 + k * 75)
            d.line([(xo, oy - 40 * s), (xo - f * 40 * s, oy + 60 * s)], fill=mast, width=max(1, int(6 * s)))
        if state == "burning":
            burning_flames(d, [(X(-40), oy - 150 * s, 90), (X(170), oy - 140 * s, 110), (X(-200), oy - 160 * s, 70)], s, pal["fire"])

    fires = [(-40 * f, -230, 150), (170 * f, -240, 170)] if state == "burning" else []
    if state == "broken" and not tilt:
        tilt = 14 if x < 0.5 else -10
    ship_on_tmp(c, c.px(x), c.py(y), s, tilt, fn, fires=fires)


@component("soldiers_cn", category="people", y_default=0.8, spacing=0.4,
           desc="Quân Trung Hoa cổ: mũ trụ nhọn có chỏm, giáo/kích, khiên chữ nhật (bóng người).",
           params={"width": "độ rộng", "rows": "số hàng", "density": "low|medium|high", "facing": "1/-1", "weapon": "spear|bow|sword"})
def draw_soldiers_cn(c, x, y, scale, t, width=0.4, rows=3, density="medium", facing=-1, weapon="spear", banners=0.0, **p):
    crowd(c, x, y, scale, t, width=width, rows=rows, density=density, head="cone", weapon=weapon, shield="rect",
          facing=facing, banners=banners, banner_col=c.pal["flag_enemy"])
