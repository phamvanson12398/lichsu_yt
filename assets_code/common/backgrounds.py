"""Nền chung: bầu trời theo giờ, mặt trời, trăng, sao, mây, núi nhiều lớp, đồi, sông, biển,
bờ biển, đảo, rừng, cánh đồng, đồng bằng, cỏ lau, dải sương, bờ gần.

Dùng trong plan.json ở "background": ["sky", "mountains:3", "river", ...]
Thứ tự trong danh sách = thứ tự vẽ (sau đè lên trước).
"""
import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from assets_code.registry import component
from render.common import add_glow, lerp, mix


def _ridge(c, base, amp, seed, smooth=False, freq=1.0):
    r = random.Random(seed)
    ph = [r.uniform(0, 6.28) for _ in range(4)]
    fr = [r.uniform(0.6, 1.4) * freq for _ in range(4)]
    k = [0.55, 0.3, 0.15, 0.06] if not smooth else [0.75, 0.22, 0.04, 0.0]
    step = max(2, int(6 * c.u))
    pts = []
    for X in range(int(c.left) - step, int(c.right) + 2 * step, step):
        u = (X + c.ox - c.vx0) / c.vw
        y = base - amp * (k[0] * math.sin(u * 6 * fr[0] + ph[0]) + k[1] * math.sin(u * 13 * fr[1] + ph[1])
                          + k[2] * math.sin(u * 31 * fr[2] + ph[2]) + k[3] * math.sin(u * 77 * fr[3] + ph[3]))
        pts.append((X, y))
    return pts


def _colors(lst, n):
    """Nội suy n màu từ danh sách màu (xa -> gần)."""
    if n <= 1:
        return [lst[len(lst) // 2]]
    out = []
    for i in range(n):
        f = i / (n - 1) * (len(lst) - 1)
        a = int(math.floor(f))
        b = min(len(lst) - 1, a + 1)
        out.append(lerp(lst[a], lst[b], f - a))
    return out


def celestial(c):
    """Vị trí mặt trời / trăng theo giờ trong ngày (tỉ lệ khung)."""
    tod = c.tod
    hz = c.horizon
    if tod == "dawn":
        return "sun", 0.28, hz - 0.07
    if tod == "day":
        return "sun", 0.74, 0.16
    if tod == "night":
        return "moon", 0.78, 0.17
    return "sun", 0.65, hz - 0.1   # dusk


@component("sky", category="background", desc="Bầu trời theo giờ (dawn/day/dusk/night). Tự có mặt trời hoặc trăng + sao.",
           params={"sun": "true/false", "stars": "true/false"})
def draw_sky(c, x, y, scale, t, **p):
    c.use(0.0)
    pal = c.pal
    top, mid, bot = pal["sky"]
    hz = c.hz()
    H, W = c.H, c.W
    ys = np.arange(H, dtype=np.float32)[:, None]
    u = np.clip((ys - c.py(0)) / max(1, hz - c.py(0)), 0, 1)
    top_, mid_, bot_ = (np.array(v, np.float32) for v in (top, mid, bot))
    a = np.where(u < 0.55, (u / 0.55), (u - 0.55) / 0.45)
    col = np.where(u[..., None] < 0.55, top_ + (mid_ - top_) * a[..., None], mid_ + (bot_ - mid_) * a[..., None])
    if c.weather in ("rain", "storm", "overcast"):
        g = col.mean(-1, keepdims=True)
        col = col * 0.45 + g * 0.55 - 18
    arr = np.broadcast_to(col, (H, W, 3)).clip(0, 255).astype(np.uint8)
    img = Image.fromarray(arr, "RGB").convert("RGBA")
    kind, sx, sy = celestial(c)
    show = p.get("sun", True) not in (False, "false") and c.weather not in ("rain", "storm", "overcast", "fog")
    if kind == "moon" or p.get("stars"):
        d = ImageDraw.Draw(img)
        rr = random.Random(c.seed + 77)
        for _ in range(int(380 * W * H / (3840 * 2160))):
            px, py = rr.uniform(0, W), rr.uniform(0, hz * 0.85)
            b = int(rr.uniform(120, 255) * (1 - py / max(1, hz)) ** 0.5)
            s = rr.choice([1, 1, 1, 2]) * max(1, c.u)
            d.ellipse([px - s / 2, py - s / 2, px + s / 2, py + s / 2], fill=(b, b, min(255, b + 20), 255))
    if show:
        X, Y = c.px(sx), c.py(sy)
        r = (120 if kind == "sun" else 70) * c.u * (0.8 if c.tod == "day" else 1.0)
        img = add_glow(img, X, Y, r * 2.0, pal["sun_glow"], 1.1 if kind == "sun" else 0.6)
        d = ImageDraw.Draw(img)
        d.ellipse([X - r, Y - r, X + r, Y + r], fill=tuple(pal["sun"]) + (255,))
        if kind == "moon":
            d.ellipse([X - r * 0.55, Y - r * 0.65, X - r * 0.15, Y - r * 0.25], fill=lerp(pal["sun"], (160, 160, 150), 0.25) + (255,))
    c.layers[0.0] = img
    c.img = img
    c.d = ImageDraw.Draw(img)


@component("clouds", category="background", desc="Mây trôi chậm (lớp sau núi).", params={"n": "số đám mây (mặc định 6)"})
def draw_clouds(c, x, y, scale, t, n=6, **p):
    c.use(0.03)
    lay = Image.new("RGBA", (c.W, c.H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    rr = random.Random(c.seed + 5)
    col = c.pal["cloud"]
    for _ in range(int(n)):
        cx = rr.uniform(c.left, c.right)
        cy = c.py(rr.uniform(0.06, c.horizon * 0.6))
        w = rr.uniform(220, 520) * c.u
        for k in range(rr.randint(4, 8)):
            ex = cx + rr.uniform(-w / 2, w / 2)
            ey = cy + rr.uniform(-w * 0.08, w * 0.06)
            r = rr.uniform(w * 0.12, w * 0.25)
            d.ellipse([ex - r * 1.6, ey - r * 0.6, ex + r * 1.6, ey + r * 0.6], fill=col + (150,))
    lay = lay.filter(ImageFilter.GaussianBlur(18 * c.u))
    c.img.alpha_composite(lay)
    c.add_effect(type="drift", depth=0.03, speed=6.0 * c.u)


@component("mountains", category="background", desc="Núi nhiều lớp mờ dần theo khoảng cách. Viết 'mountains:3' = 3 lớp.",
           params={"n": "số lớp (1-5)"})
def draw_mountains(c, x, y, scale, t, n=3, **p):
    n = max(1, min(5, int(n)))
    hz = c.hz()
    cols = _colors(c.pal["mount"], n)
    sky_bot = c.pal["sky"][2]
    for i in range(n):
        f = i / max(1, n - 1)
        depth = 0.08 + 0.2 * f
        c.use(depth)
        amp = (150 - 70 * f) * c.u * (scale or 1)
        base = hz - (120 - 115 * f) * c.u
        col = mix(cols[i], sky_bot, 0.18 * (1 - f))
        pts = _ridge(c, base, amp, c.seed * 13 + i * 7 + 11)
        c.d.polygon(pts + [(c.right + 20, hz + 6 * c.u), (c.left - 20, hz + 6 * c.u)], fill=col + (255,))


@component("hills", category="background", desc="Đồi thoai thoải phía xa (mềm hơn núi).", params={"n": "số lớp (1-3)"})
def draw_hills(c, x, y, scale, t, n=2, **p):
    n = max(1, min(3, int(n)))
    hz = c.hz()
    near = c.pal["mount"][-1]
    g = c.pal["ground"][0]
    for i in range(n):
        f = i / max(1, n - 1)
        c.use(0.3 + 0.08 * f)
        col = mix(mix(near, g, 0.4 + 0.3 * f), c.pal["sky"][2], 0.15 * (1 - f))
        pts = _ridge(c, hz - (45 - 30 * f) * c.u, (50 - 20 * f) * c.u, c.seed * 7 + 31 + i, smooth=True, freq=0.6)
        c.d.polygon(pts + [(c.right + 20, hz + 6 * c.u), (c.left - 20, hz + 6 * c.u)], fill=col + (255,))


def _water(c, far_bank=False, waves=False):
    c.use(0.5)
    pal = c.pal
    hz = int(c.hz())
    H = c.H - hz
    top, bot = pal["water"]
    if c.weather in ("rain", "storm", "overcast"):
        top, bot = mix(top, (90, 96, 100), 0.4), mix(bot, (20, 22, 26), 0.3)
    t_ = np.linspace(0, 1, max(2, H), dtype=np.float32)[:, None, None] ** 0.8
    arr = (np.array(top, np.float32) + (np.array(bot, np.float32) - np.array(top, np.float32)) * t_)
    arr = np.broadcast_to(arr, (H, c.W, 3)).astype(np.uint8)
    w = Image.fromarray(arr, "RGB").convert("RGBA")
    c.img.alpha_composite(w, (0, hz))
    d = c.d
    rr = random.Random(c.seed + 3)
    shim = pal["shimmer"]
    n = int(260 * c.W * c.H / (3840 * 2160) + 60)
    for _ in range(n):
        yy = rr.uniform(hz + 4 * c.u, c.H)
        tt = (yy - hz) / max(1, H)
        xx = rr.uniform(0, c.W)
        L = rr.uniform(30, 130) * c.u * (0.4 + tt)
        col = lerp(shim, bot, rr.uniform(0.3, 0.85))
        d.line([(xx, yy), (xx + L, yy)], fill=col + (255,), width=max(1, int((1.5 + 2.5 * tt) * c.u)))
    kind, sx, sy = celestial(c)
    if c.tod in ("dusk", "dawn", "night") and c.weather not in ("rain", "storm", "overcast", "fog"):
        cx = c.px(sx)
        col = pal["sun"] if kind == "sun" else lerp(pal["sun"], bot, 0.3)
        for _ in range(70):
            yy = rr.uniform(hz, c.H)
            spread = 150 * c.u * (0.5 + (yy - hz) / max(1, H))
            xx = cx + rr.gauss(0, spread * 0.45)
            L = rr.uniform(20, 90) * c.u
            d.line([(xx - L / 2, yy), (xx + L / 2, yy)], fill=lerp(col, top, 0.25) + (255,), width=max(1, int(rr.uniform(1.5, 4) * c.u)))
    if waves:
        for _ in range(int(n * 0.4)):
            yy = rr.uniform(hz + 20 * c.u, c.H)
            tt = (yy - hz) / max(1, H)
            xx = rr.uniform(0, c.W)
            L = rr.uniform(40, 120) * c.u * (0.5 + tt)
            d.arc([xx, yy - L * 0.12, xx + L, yy + L * 0.12], 200, 340, fill=lerp(shim, (255, 255, 255), 0.3) + (180,),
                  width=max(1, int(2 * c.u * (0.5 + tt))))
    if far_bank:
        pts = _ridge(c, hz - 4 * c.u, 6 * c.u, c.seed + 91, smooth=True, freq=2.0)
        d.polygon(pts + [(c.right + 10, hz + 3 * c.u), (c.left - 10, hz + 3 * c.u)], fill=mix(pal["mount"][-1], pal["sil"], 0.4) + (255,))
    c.add_effect(type="shimmer", depth=0.5, y0=hz, color=shim)


@component("river", category="background", desc="Mặt sông từ đường chân trời xuống (lấp lánh), có bờ xa mờ.")
def draw_river(c, x, y, scale, t, **p):
    _water(c, far_bank=True)


@component("sea", category="background", desc="Mặt biển rộng, có sóng nhỏ.")
def draw_sea(c, x, y, scale, t, **p):
    _water(c, waves=True)


@component("lake", category="background", desc="Mặt hồ phẳng lặng.")
def draw_lake(c, x, y, scale, t, **p):
    _water(c, far_bank=True)


def _ground(c, field=False, snow=False):
    c.use(0.5)
    pal = c.pal
    hz = int(c.hz())
    H = c.H - hz
    top, bot = pal["ground"]
    if snow:
        top, bot = mix(top, (236, 238, 242), 0.7), mix(bot, (196, 202, 214), 0.7)
    t_ = np.linspace(0, 1, max(2, H), dtype=np.float32)[:, None, None]
    arr = (np.array(top, np.float32) + (np.array(bot, np.float32) - np.array(top, np.float32)) * t_)
    arr = np.broadcast_to(arr, (H, c.W, 3)).astype(np.uint8)
    c.img.alpha_composite(Image.fromarray(arr, "RGB").convert("RGBA"), (0, hz))
    d = c.d
    rr = random.Random(c.seed + 8)
    if field:   # luống ruộng hội tụ về điểm xa
        vx = c.px(0.5)
        for k in range(-24, 25):
            xb = vx + k * 150 * c.u
            d.line([(vx + k * 6 * c.u, hz), (xb, c.H)], fill=lerp(top, bot, 0.25) + (45,), width=max(1, int(2 * c.u)))
    for _ in range(int(500 * c.W * c.H / (3840 * 2160) + 80)):
        yy = rr.uniform(hz + 3 * c.u, c.H)
        tt = (yy - hz) / max(1, H)
        xx = rr.uniform(0, c.W)
        L = rr.uniform(6, 26) * c.u * (0.3 + tt * 1.5)
        col = lerp(top, bot, rr.uniform(0, 1)) if not snow else lerp((255, 255, 255), bot, rr.uniform(0.2, 0.7))
        d.line([(xx, yy), (xx + rr.uniform(-0.3, 0.3) * L, yy - L)], fill=col + (255,), width=max(1, int(2 * c.u * (0.4 + tt))))


@component("plain", category="background", desc="Mặt đất / đồng bằng trống (bãi chiến trường).")
def draw_plain(c, x, y, scale, t, **p):
    _ground(c, snow=(c.weather == "snow" or p.get("snow")))


@component("field", category="background", desc="Cánh đồng có luống ruộng.")
def draw_field(c, x, y, scale, t, **p):
    _ground(c, field=True, snow=(c.weather == "snow"))


@component("snowfield", category="background", desc="Mặt đất phủ tuyết.")
def draw_snowfield(c, x, y, scale, t, **p):
    _ground(c, snow=True)


@component("coast", category="background", desc="Dải đất bờ biển/bờ sông một bên. Viết 'coast:left' hoặc 'coast:right'.",
           params={"side": "left | right", "width": "độ rộng 0.15-0.5"})
def draw_coast(c, x, y, scale, t, side="right", width=0.3, **p):
    c.use(0.55)
    hz = c.hz()
    rr = random.Random(c.seed + 21)
    width = float(width)
    pts = []
    n = 40
    for i in range(n + 1):
        yy = hz + (c.bottom - hz) * i / n
        f = i / n
        wx = width * (0.25 + 0.75 * f ** 0.8) + 0.03 * math.sin(i * 0.9 + rr.uniform(0, 1)) * f
        xx = c.px(1 - wx) if side == "right" else c.px(wx)
        pts.append((xx, yy))
    edge = c.right + 10 if side == "right" else c.left - 10
    poly = pts + [(edge, c.bottom), (edge, hz)]
    col = mix(c.pal["ground"][0], c.pal["mount"][-1], 0.5)
    c.d.polygon(poly, fill=col + (255,))
    c.d.line(pts, fill=lerp(c.pal["shimmer"], (255, 255, 255), 0.2) + (200,), width=max(1, int(4 * c.u)))
    inner = [(px + (25 * c.u if side == "right" else -25 * c.u), py) for px, py in pts]
    c.d.polygon(inner + [(edge, c.bottom), (edge, hz)], fill=mix(col, c.pal["sil"], 0.35) + (255,))


@component("islands", category="background", desc="Vài hòn đảo nhỏ trên đường chân trời.", params={"n": "số đảo (mặc định 4)"})
def draw_islands(c, x, y, scale, t, n=4, **p):
    c.use(0.36)
    hz = c.hz()
    rr = random.Random(c.seed + 41)
    col = mix(c.pal["mount"][-1], c.pal["sky"][2], 0.25)
    for _ in range(int(n)):
        cx = c.px(rr.uniform(0.05, 0.95))
        w = rr.uniform(60, 200) * c.u
        h = rr.uniform(25, 80) * c.u
        pts = []
        for k in range(21):
            u = k / 20
            pts.append((cx - w / 2 + w * u, hz - h * math.sin(math.pi * u) ** 0.7 * (0.8 + 0.2 * math.sin(u * 13))))
        c.d.polygon(pts + [(cx + w / 2, hz + 2 * c.u)], fill=col + (255,))


@component("forest", category="background", desc="Rừng cây ở đường chân trời.", params={"style": "broadleaf | pine | bamboo"})
def draw_forest(c, x, y, scale, t, style="broadleaf", **p):
    c.use(0.4)
    hz = c.hz()
    rr = random.Random(c.seed + 51)
    col = mix(c.pal["mount"][-1], c.pal["sil"], 0.35)
    d = c.d
    X = c.left - 20
    while X < c.right + 20:
        h = rr.uniform(40, 95) * c.u * (scale or 1)
        if style == "pine":
            w = h * 0.45
            d.polygon([(X - w, hz + 2), (X + w, hz + 2), (X, hz - h)], fill=col + (255,))
            X += w * rr.uniform(0.6, 1.0)
        elif style == "bamboo":
            for k in range(3):
                bx = X + rr.uniform(-10, 10) * c.u
                d.line([(bx, hz + 2), (bx + rr.uniform(-8, 8) * c.u, hz - h * 1.2)], fill=col + (255,), width=max(1, int(3 * c.u)))
                d.ellipse([bx - h * 0.25, hz - h * 1.3, bx + h * 0.25, hz - h * 0.8], fill=col + (255,))
            X += h * 0.3
        else:
            r = h * 0.45
            d.ellipse([X - r, hz - h, X + r, hz - h + 2 * r], fill=col + (255,))
            d.rectangle([X - r * 0.9, hz - h + r, X + r * 0.9, hz + 2], fill=col + (255,))
            X += r * rr.uniform(0.9, 1.4)


@component("reeds", category="background", desc="Cỏ lau tiền cảnh (lớp gần nhất, hơi nhòe).", params={"height": "chiều cao 0.1-0.35"})
def draw_reeds(c, x, y, scale, t, height=0.22, **p):
    c.use(1.3)
    rr = random.Random(c.seed + 61)
    d = c.d
    base = c.bottom + 10
    col = c.pal["sil"]
    plume = lerp(c.pal["fog"], c.pal["sil"], 0.35)
    hmax = float(height) * c.vh
    X = c.left
    while X < c.right:
        h = rr.uniform(0.35, 1.0) * hmax
        lean = rr.uniform(-0.25, 0.35) * h
        tip = (X + lean, base - h)
        d.line([(X, base), ((X + tip[0]) / 2 + lean * 0.15, base - h * 0.55), tip], fill=col + (255,), width=max(1, int(rr.uniform(2, 5) * c.u)))
        if rr.random() < 0.45:
            d.ellipse([tip[0] - 9 * c.u, tip[1] - 38 * c.u, tip[0] + 9 * c.u, tip[1] + 6 * c.u], fill=plume + (220,))
        X += rr.uniform(6, 22) * c.u
    c.add_effect(type="blur_layer", depth=1.3, radius=3.0 * c.u)


@component("bank_near", category="background", desc="Dải đất bờ gần phía dưới khung (đứng trên bờ nhìn ra).",
           params={"top": "mép trên 0.7-0.95"})
def draw_bank_near(c, x, y, scale, t, top=0.86, **p):
    c.use(0.95)
    top_y = c.py(float(top))
    pts = _ridge(c, top_y, 14 * c.u, c.seed + 71, smooth=True, freq=1.5)
    col = mix(c.pal["ground"][1], c.pal["sil"], 0.4)
    c.d.polygon(pts + [(c.right + 20, c.bottom + 20), (c.left - 20, c.bottom + 20)], fill=col + (255,))
    rr = random.Random(c.seed + 72)
    for _ in range(int(120 * c.W / 3840) + 40):
        xx = rr.uniform(c.left, c.right)
        yy = top_y + rr.uniform(-4, 30) * c.u
        h = rr.uniform(10, 34) * c.u
        c.d.line([(xx, yy + h * 0.3), (xx + rr.uniform(-6, 6) * c.u, yy - h)], fill=c.pal["sil"] + (255,), width=max(1, int(2 * c.u)))


@component("mist_band", category="background", desc="Dải sương mờ nằm ngang đường chân trời.")
def draw_mist_band(c, x, y, scale, t, **p):
    c.use(0.45)
    m = Image.new("L", (c.W, c.H), 0)
    hz = c.hz()
    ImageDraw.Draw(m).rectangle([0, hz - 50 * c.u, c.W, hz + 30 * c.u], fill=150)
    m = m.filter(ImageFilter.GaussianBlur(40 * c.u))
    fog = Image.new("RGBA", (c.W, c.H), c.pal["fog"] + (0,))
    fog.putalpha(m)
    c.img.alpha_composite(fog)
