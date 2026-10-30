"""Bản đồ động (mục 6.3): nền giấy cổ, sông, bờ biển, núi ký hiệu, la bàn, nhãn hiện dần,
mũi tên hành quân vẽ dần theo đường cong (đỏ = phe địch / bên tấn công, xanh = phe còn lại),
chấm bãi cọc, dấu X + vòng sóng giao chiến. Luôn ghi "Sơ đồ minh họa, không theo tỉ lệ".

  "map": {
    "title": "TRẬN BẠCH ĐẰNG NĂM 938",
    "features": ["river", "coast_right", "islands", "mountains", "forest"],
    "river_path": [[0.08,0.23],[0.3,0.3],[0.55,0.45],[0.77,0.62]],      (tuỳ chọn)
    "labels": [{"text": "Sông Bạch Đằng", "at": [0.2, 0.3], "start": 0.5, "style": "water"}],
    "arrows": [{"side": "enemy", "path": [[0.95,0.75],[0.6,0.55],[0.35,0.38]], "start": 1.8, "dur": 2.4, "label": "..."}],
    "markers": [{"kind": "stakes", "at": [0.47,0.44], "start": 0.6}, {"kind": "clash_x", "at": [0.47,0.44], "start": 6.9}],
    "legend": {"enemy": "Quân Nam Hán", "ally": "Quân Ngô Quyền"}
  }
Marker: stakes | clash_x | castle | city | camp | fire | ships | star
"""
import math
import random

import numpy as np
from PIL import Image, ImageDraw

from render import palettes
from render.common import N, RichFont, ease, grain_frames, smooth_path, text_layer, vignette, with_alpha

MARKERS = ["stakes", "clash_x", "castle", "city", "camp", "fire", "ships", "star"]
FEATURES = ["river", "coast_right", "coast_left", "coast_top", "coast_bottom", "sea", "islands", "mountains", "forest", "lake"]


class MapVisual:
    def __init__(self, spec, OW, OH, fps, dur, title="", seed=4, grain=5.0):
        self.spec = spec or {}
        self.OW, self.OH, self.fps, self.dur = OW, OH, fps, dur
        self.k = OW / 1920.0
        self.pal = palettes.get("giay_co")
        self.title = N(self.spec.get("title") or title or "")
        self.seed = seed
        self.base = self._base()
        self.arrows = []
        for a in self.spec.get("arrows", []):
            pts = [(x * OW, y * OH) for x, y in a["path"]]
            self.arrows.append((a, smooth_path(pts, 260)))
        rs = random.Random(9)
        self.stake_dots = [(rs.uniform(0, 6.28), rs.uniform(0, 1) ** .5, rs.uniform(0, .6)) for _ in range(30)]
        self.label_layers = {}
        self.vig = vignette(OW, OH, 0.6)
        self.grain = grain_frames(OW, OH, grain) if grain else None
        self.fi = 0

    def P(self, xy):
        return xy[0] * self.OW, xy[1] * self.OH

    # ---------------------------------------------------------------- base
    def _base(self):
        OW, OH, k, pal = self.OW, self.OH, self.k, self.pal
        rng = np.random.default_rng(self.seed)
        im = Image.new("RGB", (OW, OH), pal["paper"])
        a = np.asarray(im).astype(np.float32)
        noise = rng.normal(0, 1, (OH // 8 + 1, OW // 8 + 1))
        noise = np.asarray(Image.fromarray(((noise + 3) * 40).clip(0, 255).astype(np.uint8)).resize((OW, OH), Image.BICUBIC)).astype(np.float32)
        a += (noise[..., None] - 120) * .12 + rng.normal(0, 4, (OH, OW, 1))
        im = Image.fromarray(a.clip(0, 255).astype(np.uint8))
        d = ImageDraw.Draw(im)
        feats = self.spec.get("features", ["river", "coast_right", "islands", "mountains"])
        water = pal["water_map"]
        line = pal["ink_light"]
        mask_pts = []
        for f in feats:
            side = f.split("_")[1] if f.startswith("coast_") else ("right" if f == "sea" else None)
            if side:
                pts = []
                if side in ("right", "left"):
                    base = OW * (0.76 if side == "right" else 0.24)
                    for y in range(0, OH + 10, 10):
                        pts.append((base + (1 if side == "right" else -1) * (60 * math.sin(y / 90) + 30 * math.sin(y / 37)) * k, y))
                    edge = OW if side == "right" else 0
                    d.polygon(pts + [(edge, OH), (edge, 0)], fill=water)
                    rng2 = random.Random(3)
                    for y in range(40, OH, int(46 * k)):
                        for x in range(int(base + 110 * k) if side == "right" else 40, OW if side == "right" else int(base - 110 * k), int(120 * k)):
                            xx = x + (y % 92) * .6
                            d.arc([xx, y, xx + 40 * k, y + 16 * k], 200, 340, fill=pal["water_line"], width=max(1, int(3 * k)))
                else:
                    base = OH * (0.2 if side == "top" else 0.8)
                    for x in range(0, OW + 10, 10):
                        pts.append((x, base + (1 if side == "bottom" else -1) * (40 * math.sin(x / 110) + 20 * math.sin(x / 41)) * k))
                    edge = OH if side == "bottom" else 0
                    d.polygon(pts + [(OW, edge), (0, edge)], fill=water)
                d.line(pts, fill=line, width=max(1, int(4 * k)))
                mask_pts += pts
        if "lake" in feats:
            cx, cy = OW * 0.5, OH * 0.55
            d.ellipse([cx - 220 * k, cy - 110 * k, cx + 220 * k, cy + 110 * k], fill=water, outline=line, width=max(1, int(3 * k)))
        if "islands" in feats:
            rr = random.Random(5)
            for _ in range(4):
                cx, cy, r = OW * rr.uniform(0.82, 0.95), OH * rr.uniform(0.15, 0.9), rr.uniform(22, 40) * k
                d.ellipse([cx - r, cy - r * .7, cx + r, cy + r * .7], fill=pal["land_hi"], outline=line, width=max(1, int(3 * k)))
        river = None
        if "river" in feats:
            rp = self.spec.get("river_path") or [[0.08, 0.23], [0.17, 0.28], [0.31, 0.32], [0.45, 0.4], [0.58, 0.47], [0.7, 0.56], [0.79, 0.63]]
            river = smooth_path([(x * OW, y * OH) for x, y in rp], 300)
            for i, (x, y) in enumerate(river):
                r = (30 + 40 * i / len(river)) / 2 * k
                d.ellipse([x - r, y - r, x + r, y + r], fill=water)
        rr = random.Random(4)
        arr_now = np.asarray(im)
        n_leg = len(self.spec.get("legend") or {}) or len({a.get("side", "enemy") for a in self.spec.get("arrows", []) if a.get("label")})
        busy = [(0, 0, 760 * k, 200 * k), (0, OH - (90 + 44 * n_leg) * k, 760 * k, OH), (OW - 260 * k, 0, OW, 260 * k)]

        def free(x, y):
            return not any(a <= x <= c and b <= y <= d for a, b, c, d in busy)
        if "mountains" in feats:
            for _ in range(60):
                x, y = rr.uniform(80, OW * 0.72), rr.uniform(80, OH - 80)
                if river is not None and np.min(np.hypot(river[:, 0] - x, river[:, 1] - y)) < 110 * k:
                    continue
                if not free(x, y) or arr_now[int(y), int(x)].tolist() == list(water):
                    continue
                s = rr.uniform(18, 30) * k
                d.polygon([(x - s, y + s * .6), (x, y - s * .6), (x + s, y + s * .6)], outline=pal["mount_line"], fill=pal["mount_fill"])
                d.line([(x, y - s * .6), (x + s * .3, y)], fill=pal["mount_line"], width=max(1, int(2 * k)))
        if "forest" in feats:
            for _ in range(70):
                x, y = rr.uniform(80, OW * 0.72), rr.uniform(80, OH - 80)
                if river is not None and np.min(np.hypot(river[:, 0] - x, river[:, 1] - y)) < 90 * k:
                    continue
                if not free(x, y) or arr_now[int(y), int(x)].tolist() == list(water):
                    continue
                s = rr.uniform(8, 13) * k
                d.ellipse([x - s, y - s, x + s, y + s], outline=pal["mount_line"], fill=(176, 170, 120))
                d.line([(x, y + s), (x, y + s * 1.6)], fill=pal["mount_line"], width=max(1, int(2 * k)))
        # khung viền + tiêu đề + chú thích
        d.rectangle([20 * k, 20 * k, OW - 20 * k, OH - 20 * k], outline=(110, 80, 45), width=max(2, int(6 * k)))
        d.rectangle([34 * k, 34 * k, OW - 34 * k, OH - 34 * k], outline=(110, 80, 45), width=max(1, int(2 * k)))
        if self.title:
            RichFont("serif_bold", 48 * k).draw(d, (80 * k, 70 * k), self.title, pal["ink"])
        RichFont("serif_italic", 30 * k).draw(d, (82 * k, 136 * k), N("Sơ đồ minh họa, không theo tỉ lệ"), pal["ink_light"])
        cx, cy = OW - 140 * k, 140 * k
        d.polygon([(cx, cy - 60 * k), (cx + 14 * k, cy), (cx, cy + 60 * k), (cx - 14 * k, cy)], fill=(110, 80, 45))
        d.ellipse([cx - 34 * k, cy - 34 * k, cx + 34 * k, cy + 34 * k], outline=(110, 80, 45), width=max(1, int(2 * k)))
        RichFont("serif_bold", 30 * k).draw(d, (cx - 10 * k, cy - 108 * k), "B", pal["ink"])
        legend = self.spec.get("legend") or {}
        if not legend:
            for a in self.spec.get("arrows", []):
                if a.get("label"):
                    legend.setdefault(a.get("side", "enemy"), a["label"])
        if legend:
            y = OH - 70 * k - 44 * k * len(legend)
            x = 80 * k
            for side in ("enemy", "ally"):
                if side not in legend:
                    continue
                col = pal["enemy" if side == "enemy" else "ally"]
                d.line([(x, y + 18 * k), (x + 60 * k, y + 18 * k)], fill=col, width=max(2, int(10 * k)))
                d.polygon([(x + 60 * k, y + 6 * k), (x + 80 * k, y + 18 * k), (x + 60 * k, y + 30 * k)], fill=col)
                RichFont("serif", 30 * k).draw(d, (x + 96 * k, y), N(f"{'Đỏ' if side == 'enemy' else 'Xanh'}: {legend[side]}"), pal["ink"])
                y += 44 * k
        a = np.asarray(im).astype(np.float32) * vignette(OW, OH, 0.6)
        return Image.fromarray(a.clip(0, 255).astype(np.uint8)).convert("RGBA")

    # ---------------------------------------------------------------- per-frame
    def _arrow(self, d, path, prog, col, width):
        n = max(2, int(len(path) * prog))
        seg = [tuple(p) for p in path[:n]]
        k = self.k
        d.line(seg, fill=(40, 20, 10), width=int(width + 8 * k), joint="curve")
        d.line(seg, fill=col, width=int(width), joint="curve")
        (x1, y1), (x2, y2) = path[max(0, n - 6)], path[n - 1]
        ang = math.atan2(y2 - y1, x2 - x1)
        L = width * 2.6
        tip = (x2 + math.cos(ang) * L * .6, y2 + math.sin(ang) * L * .6)
        l_ = (x2 + math.cos(ang + 2.5) * L, y2 + math.sin(ang + 2.5) * L)
        r_ = (x2 + math.cos(ang - 2.5) * L, y2 + math.sin(ang - 2.5) * L)
        d.polygon([tip, l_, r_], fill=col, outline=(40, 20, 10))

    def _label(self, fr, txt, xy, kind, col, a, size=34):
        if a <= 0:
            return
        key = (txt, kind, size, col)
        if key not in self.label_layers:
            self.label_layers[key] = text_layer(txt, kind, size * self.k, fill=col, shadow=False)
        lay = self.label_layers[key]
        fr.alpha_composite(with_alpha(lay, a), (int(xy[0]), int(xy[1])))

    def compose(self, t):
        fr = self.base.copy()
        d = ImageDraw.Draw(fr)
        k = self.k
        pal = self.pal
        for lb in self.spec.get("labels", []):
            st = float(lb.get("start", 0.4))
            col = pal["label_water"] if lb.get("style") == "water" else pal["ink"]
            self._label(fr, N(lb["text"]), self.P(lb["at"]), "serif_italic" if lb.get("style") == "water" else "serif_bold",
                        col, ease((t - st) / .5), lb.get("size", 34))
        for mk in self.spec.get("markers", []):
            st = float(mk.get("start", 0.5))
            if t < st:
                continue
            u = t - st
            x, y = self.P(mk["at"])
            kind = mk.get("kind", "star")
            if kind == "stakes":
                for ang, rr, delay in self.stake_dots:
                    a = ease((u - delay) / .25)
                    if a > 0:
                        px, py = x + math.cos(ang) * rr * 110 * k, y + math.sin(ang) * rr * 42 * k
                        r = 6 * a * k
                        d.ellipse([px - r, py - r, px + r, py + r], fill=(60, 35, 20), outline=(20, 10, 5))
            elif kind == "clash_x":
                for j in range(3):
                    rr = (u * 260 - j * 70) * k
                    if 0 < rr < 300 * k:
                        al = int(255 * (1 - rr / (300 * k)))
                        lay = Image.new("RGBA", fr.size, (0, 0, 0, 0))
                        ImageDraw.Draw(lay).ellipse([x - rr * 1.3, y - rr * .6, x + rr * 1.3, y + rr * .6], outline=(200, 50, 30, al),
                                                    width=max(1, int(5 * k)))
                        fr.alpha_composite(lay)
                s = 46 * k * ease(u / .3) * (1 + .15 * math.sin(u * 8) * math.exp(-u * 2))
                for dx in (-1, 1):
                    d.line([(x - s, y - s * dx), (x + s, y + s * dx)], fill=(40, 10, 5), width=max(2, int(22 * k)))
                    d.line([(x - s, y - s * dx), (x + s, y + s * dx)], fill=(210, 40, 25), width=max(1, int(14 * k)))
            else:
                a = ease(u / .3)
                s = 22 * k * (0.6 + 0.4 * a)
                col = pal["enemy"] if mk.get("side") == "enemy" else pal["ally"] if mk.get("side") == "ally" else pal["ink"]
                if kind == "castle":
                    d.rectangle([x - s, y - s * .8, x + s, y + s * .6], fill=col)
                    for j in range(3):
                        d.rectangle([x - s + j * s * .8, y - s * 1.2, x - s + j * s * .8 + s * .4, y - s * .8], fill=col)
                elif kind == "city":
                    d.ellipse([x - s * .6, y - s * .6, x + s * .6, y + s * .6], fill=col, outline=(40, 20, 10), width=max(1, int(3 * k)))
                elif kind == "camp":
                    for j in (-1, 0, 1):
                        d.polygon([(x + j * s * 1.1 - s * .5, y + s * .4), (x + j * s * 1.1 + s * .5, y + s * .4), (x + j * s * 1.1, y - s * .5)], fill=col)
                elif kind == "fire":
                    fl = 1 + .15 * math.sin(t * 12)
                    d.polygon([(x - s * .6, y + s * .5), (x, y - s * 1.2 * fl), (x + s * .6, y + s * .5)], fill=(220, 90, 30))
                    d.polygon([(x - s * .3, y + s * .5), (x, y - s * .5 * fl), (x + s * .3, y + s * .5)], fill=(250, 200, 90))
                elif kind == "ships":
                    for j in range(3):
                        sx, sy = x + (j - 1) * s * 1.4, y + (j % 2) * s * .6
                        d.polygon([(sx - s * .6, sy), (sx + s * .6, sy), (sx + s * .4, sy + s * .3), (sx - s * .4, sy + s * .3)], fill=col)
                        d.line([(sx, sy), (sx, sy - s * .8)], fill=col, width=max(1, int(3 * k)))
                else:
                    pts = []
                    for j in range(10):
                        rr = s if j % 2 == 0 else s * .45
                        an = -math.pi / 2 + j * math.pi / 5
                        pts.append((x + math.cos(an) * rr, y + math.sin(an) * rr))
                    d.polygon(pts, fill=col)
                if mk.get("label"):
                    self._label(fr, N(mk["label"]), (x + 30 * k, y - 20 * k), "serif_bold", pal["ink"], a, 30)
        for a_spec, path in self.arrows:
            st, du = float(a_spec.get("start", 1.0)), float(a_spec.get("dur", 2.0))
            pr = ease((t - st) / du)
            if pr <= 0:
                continue
            col = self.pal["enemy" if a_spec.get("side", "enemy") == "enemy" else "ally"]
            self._arrow(d, path, pr, col, (16 if a_spec.get("side") == "ally" else 14) * k)
            if a_spec.get("label"):
                lp = a_spec.get("label_at")
                pos = self.P(lp) if lp else (path[0][0] - 220 * k, path[0][1] + 20 * k)
                pos = (min(max(50 * k, pos[0]), self.OW - 420 * k), min(max(50 * k, pos[1]), self.OH - 90 * k))
                self._label(fr, N(a_spec["label"]), pos, "serif_bold", col, ease((t - st - 0.4) / .6), 34)
        if self.spec.get("caption"):
            cs = float(self.spec.get("caption_start", self.dur * 0.7))
            self._label(fr, N(self.spec["caption"]), (480 * k, OH_CAPTION * self.OH), "serif_bold", (150, 25, 15),
                        ease((t - cs) / .6), 46)
        return fr

    def frame(self, t):
        fr = self.compose(t)
        a = np.asarray(fr.convert("RGB")).astype(np.float32)
        if self.grain is not None:
            a += self.grain[self.fi % len(self.grain)] * 0.6
        self.fi += 1
        return a

    def events(self):
        ev = []
        for mk in self.spec.get("markers", []):
            st = float(mk.get("start", 0.5))
            kind = mk.get("kind")
            if kind == "stakes":
                ev += [(st + j * 0.06, "pop", 0.5) for j in range(0, 10)]
            elif kind == "clash_x":
                ev.append((st, "boom", 0.9))
            else:
                ev.append((st, "pop", 0.8))
        for a in self.spec.get("arrows", []):
            ev.append((float(a.get("start", 1.0)), "whoosh", 0.7))
        for lb in self.spec.get("labels", []):
            ev.append((float(lb.get("start", 0.4)), "pop", 0.35))
        return ev


OH_CAPTION = 0.82
