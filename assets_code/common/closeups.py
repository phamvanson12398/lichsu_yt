"""Cảnh cận và trung (cho video đỡ toàn cảnh rộng): tướng chỉ huy cận cảnh, người đánh trống trận,
bàn bàn kế, nội thất điện / doanh trại, khung lá tiền cảnh (nhìn qua tán lá ra sông).
"""
import math
import random

from PIL import ImageDraw

from assets_code.common.shapes import _poly, headgear
from assets_code.registry import component
from render.common import lerp, mix

HEADS = {"vietnam": "round", "china": "cone", "korea": "joseon_helmet", "japan": "kabuto", "england": "norman"}


def _rgb(v, default):
    try:
        return tuple(int(x) for x in v[:3]) if v else default
    except (TypeError, ValueError):
        return default


def _commander(d, X, Y, H, col, facing, pose, head, accent):
    """Bóng tướng đứng nghiêng 3/4: chân, giáp, áo choàng bay ngược, đầu đội mũ trụ, tay giơ kiếm / chỉ."""
    f = facing
    r = H * 0.062
    hx, hy = X + f * H * 0.02, Y - H * 0.87
    hip = Y - H * 0.47
    sh = Y - H * 0.76
    # áo choàng (sau lưng, bay về phía ngược hướng nhìn)
    _poly(d, [(X - f * H * 0.05, sh), (X - f * H * 0.16, sh + H * 0.05), (X - f * H * 0.36, Y - H * 0.08),
              (X - f * H * 0.27, Y - H * 0.03), (X - f * H * 0.12, Y - H * 0.06), (X + f * H * 0.02, hip)], col)
    # chân
    lw = H * 0.045
    _poly(d, [(X - lw * 1.8, hip), (X + lw * 0.2, hip), (X - H * 0.05, Y), (X - H * 0.05 - lw * 1.6, Y)], col)
    _poly(d, [(X - lw * 0.2, hip), (X + lw * 1.9, hip), (X + f * H * 0.1 + lw, Y), (X + f * H * 0.1 - lw * 0.6, Y)], col)
    # thân + vạt giáp
    _poly(d, [(X - H * 0.085, sh), (X + H * 0.085, sh), (X + H * 0.075, hip + H * 0.08), (X + H * 0.1, hip + H * 0.13),
              (X - H * 0.1, hip + H * 0.13), (X - H * 0.075, hip + H * 0.08)], col)
    for sg in (-1, 1):   # giáp vai
        d.pieslice([X + sg * H * 0.085 - H * 0.055, sh - H * 0.03, X + sg * H * 0.085 + H * 0.055, sh + H * 0.07], 180, 360, fill=col)
    d.rectangle([X - H * 0.1, hip - H * 0.01, X + H * 0.1, hip + H * 0.015], fill=accent)        # đai lưng
    d.rectangle([hx - r * 0.5, sh - H * 0.05, hx + r * 0.5, sh + 2], fill=col)                       # cổ
    d.ellipse([hx - r, hy - r * 1.1, hx + r, hy + r * 1.05], fill=col)
    headgear(d, hx, hy, r, head, col, accent=accent, facing=f)
    # tay
    aw = max(2, int(H * 0.035))
    shx = X + f * H * 0.08
    if pose == "point":
        hand = (shx + f * H * 0.3, sh - H * 0.06)
        d.line([(shx, sh + H * 0.02), hand], fill=col, width=aw)
        d.ellipse([hand[0] - aw * 0.7, hand[1] - aw * 0.7, hand[0] + aw * 0.7, hand[1] + aw * 0.7], fill=col)
    elif pose == "sword_up":
        hand = (shx + f * H * 0.1, sh - H * 0.2)
        d.line([(shx, sh + H * 0.02), (shx + f * H * 0.09, sh - H * 0.06), hand], fill=col, width=aw, joint="curve")
        d.line([hand, (hand[0] + f * H * 0.12, hand[1] - H * 0.36)], fill=col, width=max(2, int(H * 0.016)))
        d.line([(hand[0] - H * 0.035, hand[1] + f * 0), (hand[0] + H * 0.035, hand[1])], fill=col, width=max(2, int(H * 0.014)))
    else:   # đứng chống kiếm
        tip = (shx + f * H * 0.12, Y)
        d.line([(shx, sh + H * 0.02), (shx + f * H * 0.1, hip - H * 0.02)], fill=col, width=aw)
        d.line([(shx + f * H * 0.1, hip - H * 0.06), tip], fill=col, width=max(2, int(H * 0.016)))
    bx = X - f * H * 0.08            # tay kia buông
    d.line([(bx, sh + H * 0.02), (bx - f * H * 0.03, hip + H * 0.02)], fill=col, width=aw)


@component("commander", category="people", y_default=0.95, persp=False, bbox=(700, 760),
           desc="Tướng chỉ huy CẬN CẢNH (bóng lớn cao ~60% khung, viền sáng). Đặt y 0.9–1.0, x 0.25–0.4 hoặc 0.6–0.75; "
                "phía sau là nền xa (sông, đồi, doanh trại...).",
           params={"pose": "point | sword_up | stand", "facing": "1 (nhìn phải) / -1",
                   "head": "kiểu mũ (mặc định theo nước)", "side": "ally | enemy"})
def draw_commander(c, x, y, scale, t, pose="point", facing=1, head=None, side="ally", **p):
    X, Y = c.px(x), c.py(y)
    H = 640 * c.u * float(scale)
    try:
        f = 1 if float(facing) >= 0 else -1
    except (TypeError, ValueError):
        f = 1
    head = head or HEADS.get(c.country, "round")
    col = c.pal["sil"] + (255,)
    rim = lerp(c.pal["sun_glow"], (255, 240, 210), 0.3) + (255,)
    accent = c.pal["flag_enemy" if side == "enemy" else "flag_ally"][:3] + (255,)
    o = max(2.0, 4 * c.u)      # viền sáng: vẽ bóng lệch về phía ánh sáng rồi phủ bóng tối lên
    _commander(c.d, X + o * f, Y - o * 0.6, H, rim, f, pose, head, rim)
    _commander(c.d, X, Y, H, col, f, pose, head, accent)


@component("war_drum", category="people", anim="redraw", y_default=0.86, persp=False, bbox=(460, 470),
           desc="Người đánh trống trận cạnh trống lớn trên giá, dùi vung theo nhịp (cảnh trung). Hợp với sfx 'tieng_tron'.",
           params={"facing": "1/-1", "tempo": "nhịp mỗi giây (mặc định 2)"})
def draw_war_drum(c, x, y, scale, t, facing=1, tempo=2.0, **p):
    X, Y = c.px(x), c.py(y)
    s = c.u * float(scale)
    try:
        f = 1 if float(facing) >= 0 else -1
    except (TypeError, ValueError):
        f = 1
    d = c.d
    col = c.pal["sil"] + (255,)
    wood = mix(c.pal["wood"], c.pal["sil"], 0.4) + (255,)
    skin = mix(c.pal["sail"], c.pal["sil"], 0.45) + (255,)
    # trống trên giá
    R = 120 * s
    dx = X + f * 95 * s
    dy = Y - 200 * s
    d.line([(dx - R * 0.8, Y), (dx - R * 0.5, dy)], fill=wood, width=max(2, int(14 * s)))
    d.line([(dx + R * 0.8, Y), (dx + R * 0.5, dy)], fill=wood, width=max(2, int(14 * s)))
    d.ellipse([dx - R * 0.55, dy - R, dx + R * 0.55, dy + R], fill=wood)                 # thân trống (nhìn nghiêng)
    d.ellipse([dx - f * R * 0.15 - R * 0.42, dy - R * 0.94, dx - f * R * 0.15 + R * 0.42, dy + R * 0.94], fill=skin)
    for k in range(-2, 3):
        yy = dy + k * R * 0.38
        d.ellipse([dx + f * R * 0.4 - 5 * s, yy - 5 * s, dx + f * R * 0.4 + 5 * s, yy + 5 * s], fill=col)
    # người đánh trống
    H = 300 * s
    px = X - f * 60 * s
    hip = Y - H * 0.45
    sh = Y - H * 0.78
    _poly(d, [(px - 22 * s, hip), (px + 4 * s, hip), (px - 30 * s, Y), (px - 52 * s, Y)], col)
    _poly(d, [(px - 4 * s, hip), (px + 22 * s, hip), (px + 40 * s, Y), (px + 18 * s, Y)], col)
    _poly(d, [(px - 28 * s, sh), (px + 28 * s, sh), (px + 24 * s, hip + 8 * s), (px - 24 * s, hip + 8 * s)], col)
    d.ellipse([px - 20 * s + f * 6 * s, sh - 50 * s, px + 20 * s + f * 6 * s, sh - 6 * s], fill=col)
    d.rectangle([px - 22 * s + f * 6 * s, sh - 44 * s, px + 22 * s + f * 6 * s, sh - 36 * s], fill=c.pal["flag_ally"][:3] + (255,))
    ph = t * float(tempo) * math.pi
    for k, off in ((0, 0.0), (1, math.pi)):
        a = 0.5 + 0.5 * math.sin(ph + off)               # 0 = chạm mặt trống, 1 = giơ cao
        shx = px + f * (10 + 14 * k) * s
        ang = math.radians(-10 - 95 * a)
        el = (shx + f * math.cos(ang) * 70 * s, sh + 10 * s + math.sin(ang) * 70 * s)
        hand = (el[0] + f * 55 * s, el[1] - 35 * s * a + 25 * s * (1 - a))
        d.line([(shx, sh + 10 * s), el, hand], fill=col, width=max(2, int(14 * s)), joint="curve")
        tip = (hand[0] + f * 70 * s * (1 - a * 0.5), hand[1] - 70 * s * a + 10 * s)
        d.line([hand, tip], fill=wood, width=max(2, int(9 * s)))
        d.ellipse([tip[0] - 10 * s, tip[1] - 10 * s, tip[0] + 10 * s, tip[1] + 10 * s], fill=wood)


@component("council", category="people", y_default=0.84, persp=False, bbox=(900, 460),
           desc="Bàn bàn kế: bàn trải bản đồ, ngọn nến, các tướng đứng quanh (cảnh trung, hợp nền 'hall').",
           params={"n": "số người 3-6", "head": "kiểu mũ (mặc định theo nước)"})
def draw_council(c, x, y, scale, t, n=4, head=None, **p):
    X, Y = c.px(x), c.py(y)
    s = c.u * float(scale)
    d = c.d
    head = head or HEADS.get(c.country, "round")
    col = c.pal["sil"] + (255,)
    wood = mix(c.pal["wood"], c.pal["sil"], 0.5) + (255,)
    n = max(2, min(6, int(n)))
    rr = random.Random(int(x * 999) + n)
    tw, th = 420 * s, 70 * s
    ty = Y - 150 * s
    # người phía sau bàn (thấy nửa thân trên)
    for k in range(n):
        u = (k + 0.5) / n
        hx = X - tw * 0.95 + u * tw * 1.9
        H = 330 * s * rr.uniform(0.92, 1.06)
        sh = ty - H * 0.36
        lean = (X - hx) * 0.06
        _poly(d, [(hx - 46 * s, sh), (hx + 46 * s, sh), (hx + 40 * s + lean, ty + 5), (hx - 40 * s + lean, ty + 5)], col)
        r = 24 * s
        hy = sh - r * 1.5
        d.ellipse([hx + lean * 0.4 - r, hy - r * 1.1, hx + lean * 0.4 + r, hy + r], fill=col)
        headgear(d, hx + lean * 0.4, hy, r, head if k % 2 == 0 else "topknot", col)
        if k == n // 2:                               # người ở giữa chỉ tay xuống bản đồ
            d.line([(hx + 30 * s, sh + 20 * s), (hx + 60 * s, ty + 4 * s)], fill=col, width=max(2, int(13 * s)))
    # mặt bàn (phối cảnh) + bản đồ
    _poly(d, [(X - tw, ty), (X + tw, ty), (X + tw * 1.12, ty + th), (X - tw * 1.12, ty + th)], wood)
    d.rectangle([X - tw * 1.12, ty + th, X + tw * 1.12, ty + th + 18 * s], fill=col)
    for sg in (-1, 1):
        d.rectangle([X + sg * tw * 0.95 - 12 * s, ty + th, X + sg * tw * 0.95 + 12 * s, Y], fill=col)
    paper = lerp((214, 190, 140), c.pal["sail"], 0.25) + (255,)
    _poly(d, [(X - tw * 0.55, ty + 8 * s), (X + tw * 0.5, ty + 6 * s), (X + tw * 0.6, ty + th - 10 * s), (X - tw * 0.62, ty + th - 8 * s)], paper)
    ink = mix(paper[:3], (40, 30, 20), 0.6) + (255,)
    pts = [(X - tw * 0.5 + i * tw * 0.1, ty + th * (0.35 + 0.25 * math.sin(i * 1.3))) for i in range(11)]
    d.line(pts, fill=ink, width=max(1, int(3 * s)))
    for i in range(5):
        mx = X - tw * 0.2 + i * tw * 0.09
        d.line([(mx, ty + th * 0.55), (mx + 4 * s, ty + th * 0.4)], fill=(150, 40, 30, 255), width=max(1, int(3 * s)))
    # nến
    cx = X + tw * 0.75
    d.rectangle([cx - 7 * s, ty - 40 * s, cx + 7 * s, ty + 10 * s], fill=(230, 214, 180, 255))
    d.ellipse([cx - 7 * s, ty - 66 * s, cx + 7 * s, ty - 40 * s], fill=c.pal["fire"][:3] + (255,))
    c.add_lamp(cx, ty - 50 * s, 160 * s)


# ------------------------------------------------------------------ nền nội thất / tiền cảnh
@component("hall", category="background",
           desc="Nội thất điện / doanh trại (thay cho trời + núi): tường gỗ, cột sơn, xà, đèn lồng / đuốc treo tỏa ánh ấm. "
                "Dùng cho cảnh bàn kế, vua tướng hội họp; ghép với 'council', 'commander'.",
           params={"style": "palace | tent", "lanterns": "số đèn (mặc định 4)"})
def draw_hall(c, x, y, scale, t, style="palace", lanterns=4, **p):
    c.use(0.5)
    d = c.d
    W0, W1, T0, B0 = c.left - 20, c.right + 20, -c.oy - 20, c.bottom + 20
    floor_y = c.py(0.72)
    dark = lerp(c.pal["sil"], (0, 0, 0), 0.25)
    if style == "tent":
        wall = mix(c.pal["sail"], c.pal["sil"], 0.6)
        for i in range(24):            # vải lều: dải sáng tối
            xa = W0 + (W1 - W0) * i / 24
            d.rectangle([xa, T0, xa + (W1 - W0) / 24 + 2, floor_y], fill=lerp(wall, dark, 0.15 + 0.2 * (i % 2)) + (255,))
        d.polygon([(W0, T0), (W1, T0), (W1, c.py(0.12)), ((W0 + W1) / 2, c.py(0.02)), (W0, c.py(0.12))], fill=dark + (255,))
    else:
        wall = lerp(mix(c.pal["wood"], c.pal["sil"], 0.2), c.pal["fire"], 0.18)
        d.rectangle([W0, T0, W1, floor_y], fill=wall + (255,))
        for i in range(30):            # ván gỗ dọc
            xa = W0 + (W1 - W0) * i / 30
            d.line([(xa, T0), (xa, floor_y)], fill=lerp(wall, dark, 0.35) + (255,), width=max(1, int(3 * c.u)))
        lac = mix((128, 30, 24), c.pal["sil"], 0.45)           # cột sơn son
        for i in range(6):
            cx = c.px(0.04 + i * 0.184)
            w = 34 * c.u
            d.rectangle([cx - w, T0, cx + w, floor_y + 8 * c.u], fill=lac + (255,))
            d.rectangle([cx - w * 0.3, T0, cx - w * 0.05, floor_y], fill=lerp(lac, (230, 150, 90), 0.25) + (255,))
            d.rectangle([cx - w * 1.3, floor_y - 4 * c.u, cx + w * 1.3, floor_y + 14 * c.u], fill=dark + (255,))
        for yy in (c.py(0.06), c.py(0.14)):                     # xà ngang
            d.rectangle([W0, yy - 14 * c.u, W1, yy + 14 * c.u], fill=dark + (255,))
    # sàn
    fl = mix(c.pal["wood"], c.pal["sil"], 0.6)
    d.rectangle([W0, floor_y, W1, B0], fill=fl + (255,))
    for i in range(12):
        yy = floor_y + (B0 - floor_y) * (i / 12) ** 1.6
        d.line([(W0, yy), (W1, yy)], fill=lerp(fl, dark, 0.3) + (255,), width=max(1, int(2 * c.u)))
    # đèn lồng / đuốc treo
    n = max(0, min(8, int(lanterns)))
    for i in range(n):
        lx = c.px((i + 0.5) / n)
        ly = c.py(0.24)
        d.line([(lx, c.py(0.14)), (lx, ly - 30 * c.u)], fill=dark + (255,), width=max(1, int(3 * c.u)))
        d.ellipse([lx - 26 * c.u, ly - 34 * c.u, lx + 26 * c.u, ly + 30 * c.u], fill=lerp(c.pal["fire"], (255, 210, 140), 0.4) + (255,))
        d.rectangle([lx - 18 * c.u, ly - 38 * c.u, lx + 18 * c.u, ly - 30 * c.u], fill=dark + (255,))
        c.add_lamp(lx, ly, 150 * c.u)


@component("foliage_frame", category="background",
           desc="Tán lá / cành cây tiền cảnh viền mép trên và hai bên khung (nhìn lén qua rừng ra sông — cảnh mai phục). "
                "Đặt CUỐI danh sách background.",
           params={"style": "leaves | bamboo | pine", "side": "both | left | right | top"})
def draw_foliage_frame(c, x, y, scale, t, style="leaves", side="both", **p):
    c.use(1.35)
    d = c.d
    rr = random.Random(c.seed + 91)
    col = lerp(c.pal["sil"], (0, 0, 0), 0.3)
    col2 = lerp(c.pal["sil"], c.pal["ground"][0], 0.25)
    sides = {"both": ("left", "right", "top"), "left": ("left", "top"), "right": ("right", "top"), "top": ("top",)}.get(str(side), ("left", "right", "top"))

    def leaf(cx, cy, L, ang, cc):
        if style == "pine":
            for k in range(-4, 5):
                a2 = ang + k * 0.08
                d.line([(cx, cy), (cx + math.cos(a2) * L, cy + math.sin(a2) * L)], fill=cc + (255,), width=max(1, int(2 * c.u)))
            return
        w = L * (0.16 if style == "bamboo" else 0.3)
        ca, sa = math.cos(ang), math.sin(ang)
        pts = [(cx, cy), (cx + ca * L * 0.5 - sa * w, cy + sa * L * 0.5 + ca * w), (cx + ca * L, cy + sa * L),
               (cx + ca * L * 0.5 + sa * w, cy + sa * L * 0.5 - ca * w)]
        d.polygon(pts, fill=cc + (255,))

    def branch(x0, y0, x1, y1, n):
        d.line([(x0, y0), ((x0 + x1) / 2, (y0 + y1) / 2 + 20 * c.u), (x1, y1)], fill=col + (255,), width=max(2, int(14 * c.u)), joint="curve")
        for i in range(n):
            u = rr.random()
            bx, by = x0 + (x1 - x0) * u, y0 + (y1 - y0) * u + 20 * c.u * math.sin(u * math.pi)
            L = rr.uniform(60, 130) * c.u
            leaf(bx, by, L, rr.uniform(0, 2 * math.pi), col if rr.random() < 0.7 else col2)

    L, R, T = c.left, c.right, -c.oy
    vw, vh = c.vw, c.vh
    if "top" in sides:
        for i in range(5):
            xa = c.px(rr.uniform(-0.05, 1.05))
            branch(xa - vw * 0.2, T - 10, xa + vw * 0.15, c.py(rr.uniform(0.05, 0.14)), 40)
    for sd in ("left", "right"):
        if sd not in sides:
            continue
        edge = L - 10 if sd == "left" else R + 10
        inner = c.px(0.16) if sd == "left" else c.px(0.84)
        if style == "bamboo":
            for k in range(4):
                bx = c.px(rr.uniform(0.0, 0.08)) if sd == "left" else c.px(rr.uniform(0.92, 1.0))
                d.line([(bx, T), (bx + rr.uniform(-20, 20) * c.u, c.bottom + 10)], fill=col + (255,), width=max(3, int(rr.uniform(16, 26) * c.u)))
        for k in range(3):
            yy = c.py(rr.uniform(0.15, 0.7))
            branch(edge, yy, inner + rr.uniform(-0.05, 0.05) * vw, yy + rr.uniform(-0.12, 0.12) * vh, 36)
    c.add_effect(type="blur_layer", depth=1.35, radius=4.0 * c.u)
