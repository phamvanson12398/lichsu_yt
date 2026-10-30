"""Hệ hạt (mục 6.2): embers (tàn lửa), smoke (khói), fire_glow (ánh lửa), mist (sương), rain, snow,
dust, sparks, cherry_blossom (hoa anh đào), leaves.

Mô phỏng trong toạ độ khung hình xuất ra, có seed để cùng kết quả mỗi lần dựng.
Hàm apply(arr, t) cộng / trộn hiệu ứng vào mảng float32 (H, W, 3).
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

KINDS = ["embers", "smoke", "fire_glow", "mist", "rain", "snow", "dust", "sparks", "cherry_blossom", "leaves"]


class System:
    def __init__(self, kind, W, H, fps, seed=1, emitters=None, intensity=1.0, fog_col=(210, 210, 210), fire_col=(255, 120, 30)):
        self.kind = kind
        self.W, self.H, self.fps = W, H, fps
        self.k = W / 1920.0
        self.rng = np.random.default_rng(seed)
        self.emitters = emitters or []      # hàm(t) -> list (x, y, r) trong toạ độ khung xuất
        self.intensity = float(intensity)
        self.fog_col = np.array(fog_col, np.float32)
        self.fire_col = fire_col
        self.p = np.zeros((0, 8), np.float32)   # x y vx vy age life size rot
        self.t = 0.0
        self._mist = None
        if kind in ("rain", "snow", "dust", "cherry_blossom", "leaves"):
            n = {"rain": 420, "snow": 260, "dust": 90, "cherry_blossom": 70, "leaves": 45}[kind]
            n = int(n * self.intensity)
            self.p = self._spawn_global(n, anywhere=True)

    # ---------------------------------------------------------- spawning
    def _spawn_global(self, n, anywhere=False):
        r = self.rng
        W, H, k = self.W, self.H, self.k
        p = np.zeros((n, 8), np.float32)
        p[:, 0] = r.uniform(-0.1 * W, 1.1 * W, n)
        p[:, 1] = r.uniform(-0.1 * H, H, n) if anywhere else r.uniform(-0.15 * H, -0.02 * H, n)
        if self.kind == "rain":
            p[:, 2] = -120 * k
            p[:, 3] = r.uniform(1400, 1900, n) * k
            p[:, 6] = r.uniform(18, 34, n) * k
            p[:, 5] = 99
        elif self.kind == "snow":
            p[:, 2] = r.normal(10, 10, n) * k
            p[:, 3] = r.uniform(40, 110, n) * k
            p[:, 6] = r.uniform(2, 5.5, n) * k
            p[:, 5] = 99
        elif self.kind == "dust":
            p[:, 1] = r.uniform(0.35 * H, H, n)
            p[:, 2] = r.normal(8, 6, n) * k
            p[:, 3] = r.normal(-3, 4, n) * k
            p[:, 6] = r.uniform(1.2, 3, n) * k
            p[:, 5] = r.uniform(4, 9, n)
            if anywhere:
                p[:, 4] = r.uniform(0, 1, n) * p[:, 5]
        elif self.kind in ("cherry_blossom", "leaves"):
            p[:, 2] = r.normal(35, 15, n) * k
            p[:, 3] = r.uniform(50, 110, n) * k
            p[:, 6] = r.uniform(6, 12, n) * k * (1.4 if self.kind == "leaves" else 1)
            p[:, 7] = r.uniform(0, 6.28, n)
            p[:, 5] = 99
        return p

    def _spawn_emit(self, t):
        r = self.rng
        k = self.k
        out = []
        srcs = []
        for em in self.emitters:
            srcs += em(t)
        if self.kind == "embers":
            if not srcs:     # tàn lửa bay lên từ đáy khung
                srcs = [(r.uniform(0, self.W), self.H + 10, 200 * k)]
                n_each = 2 if r.random() < 0.6 * self.intensity else 1
            else:
                n_each = 1 if r.random() < 0.7 else 2
            for fx, fy, rad in srcs:
                for _ in range(n_each):
                    out.append([fx + r.normal(0, rad * 0.3), fy, r.normal(0, 25) * k, -r.uniform(60, 180) * k, 0,
                                r.uniform(1.5, 3.5), r.uniform(1.0, 2.4) * k, 0])
        elif self.kind == "smoke":
            if not srcs:
                srcs = [(r.uniform(0, self.W), self.H * 0.75, 200 * k)] if r.random() < 0.25 * self.intensity else []
            for fx, fy, rad in srcs:
                if r.random() < 0.35 * self.intensity:
                    out.append([fx + r.normal(0, 20 * k), fy - 30 * k, r.normal(8, 6) * k, -r.uniform(25, 45) * k, 0,
                                r.uniform(4, 7), r.uniform(50, 90) * k * max(0.6, rad / (150 * k)), 0])
        elif self.kind == "sparks":
            if r.random() < 0.08 * self.intensity:
                cx, cy = (srcs[0][:2] if srcs else (r.uniform(0.25, 0.75) * self.W, r.uniform(0.45, 0.75) * self.H))
                for _ in range(int(r.integers(12, 26))):
                    a = r.uniform(-math.pi, 0)
                    sp = r.uniform(200, 600) * k
                    out.append([cx, cy, math.cos(a) * sp, math.sin(a) * sp, 0, r.uniform(0.3, 0.8), r.uniform(1.5, 3) * k, 0])
        elif self.kind == "dust" and len(self.p) < 90 * self.intensity:
            return self._spawn_global(1)
        return np.array(out, np.float32).reshape(-1, 8)

    # ---------------------------------------------------------- simulation
    def step(self, t):
        dt = 1.0 / self.fps
        self.t = t
        if self.kind in ("embers", "smoke", "sparks", "dust"):
            new = self._spawn_emit(t)
            if len(new):
                self.p = np.vstack([self.p, new])
        p = self.p
        if not len(p):
            return
        if self.kind == "embers":
            p[:, 2] += (np.sin(t * 3 + p[:, 1] * 0.02 / self.k) * 20 + 12) * dt * self.k
        elif self.kind == "smoke":
            p[:, 6] += 22 * dt * self.k
        elif self.kind == "sparks":
            p[:, 3] += 900 * dt * self.k
        elif self.kind in ("snow", "cherry_blossom", "leaves"):
            p[:, 2] += np.sin(t * 1.3 + p[:, 7] * 3) * 30 * dt * self.k
            p[:, 7] += dt * 2.0
        p[:, 0] += p[:, 2] * dt
        p[:, 1] += p[:, 3] * dt
        p[:, 4] += dt
        if self.kind in ("rain", "snow", "cherry_blossom", "leaves"):
            out = (p[:, 1] > self.H + 40) | (p[:, 0] < -0.15 * self.W) | (p[:, 0] > 1.15 * self.W)
            if out.any():
                p[out] = self._spawn_global(int(out.sum()))
        else:
            self.p = p[p[:, 4] < p[:, 5]]

    def warm(self, seconds):
        n = int(seconds * self.fps)
        for i in range(n):
            self.step(-seconds + i / self.fps)

    # ---------------------------------------------------------- drawing
    def apply(self, arr, t):
        k = self.kind
        W, H = self.W, self.H
        if k == "fire_glow":
            fl = 0.75 + 0.15 * math.sin(t * 9) + 0.08 * math.sin(t * 23) + 0.04 * self.rng.standard_normal()
            g = np.linspace(0, 1, H, dtype=np.float32)[:, None, None] ** 2.2
            arr += g * np.array(self.fire_col, np.float32) * 0.28 * fl * self.intensity
            return arr
        if k == "mist":
            if self._mist is None:
                lw, lh = W // 8 + 2, H // 8 + 2
                n = self.rng.normal(0, 1, (lh // 4 + 2, lw // 2 + 2)).astype(np.float32)
                im = Image.fromarray(((n + 3) * 40).clip(0, 255).astype(np.uint8)).resize((lw * 2, lh), Image.BICUBIC)
                im = im.filter(ImageFilter.GaussianBlur(6))
                m = np.asarray(im).astype(np.float32) / 255.0
                yy = np.linspace(0, 1, lh, dtype=np.float32)[:, None]
                m = m * (0.35 + 0.65 * np.exp(-((yy - 0.62) / 0.28) ** 2))
                self._mist = m
            m = self._mist
            lw = W // 8 + 2
            off = int((t * 6) % (m.shape[1] - lw))
            sl = m[:, off:off + lw]
            a = np.asarray(Image.fromarray((sl * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)).astype(np.float32)
            a = (a / 255.0 * 0.55 * self.intensity)[..., None]
            arr[:] = arr * (1 - a) + self.fog_col * a
            return arr
        p = self.p
        if not len(p):
            return arr
        if k in ("embers", "sparks", "dust"):
            hw, hh = W // 2, H // 2
            em = Image.new("RGB", (hw, hh))
            d = ImageDraw.Draw(em)
            for x, y, vx, vy, age, life, sz, _ in p:
                a = max(0.0, 1 - age / life)
                if k == "dust":
                    a = math.sin(math.pi * age / life) * 0.5
                    c = (int(230 * a), int(200 * a), int(150 * a))
                elif k == "sparks":
                    c = (int(255 * a), int(220 * a), int(140 * a))
                    d.line([(x / 2, y / 2), ((x - vx * 0.03) / 2, (y - vy * 0.03) / 2)], fill=c, width=max(1, int(sz / 2)))
                    continue
                else:
                    c = (int(255 * a), int(170 * a * a), int(60 * a ** 3))
                r = sz / 2
                d.ellipse([x / 2 - r, y / 2 - r, x / 2 + r, y / 2 + r], fill=c)
            glow = em.filter(ImageFilter.GaussianBlur(3))
            half = np.asarray(em).astype(np.float32) * 1.2 + np.asarray(glow).astype(np.float32) * 1.6
            bb = em.getbbox()
            if not bb:
                return arr
            full = Image.fromarray(np.clip(half, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)
            arr += np.asarray(full).astype(np.float32)
            return arr
        if k == "smoke":
            sm = Image.new("L", (W // 4, H // 4))
            d = ImageDraw.Draw(sm)
            for x, y, *_rest in p:
                age, life, sz = _rest[2], _rest[3], _rest[4]
                a = math.sin(math.pi * age / life) * 70
                r = sz / 4
                d.ellipse([x / 4 - r, y / 4 - r, x / 4 + r, y / 4 + r], fill=int(a))
            sm = sm.filter(ImageFilter.GaussianBlur(10)).resize((W, H), Image.BILINEAR)
            s = np.asarray(sm).astype(np.float32)[..., None] / 255.0
            arr[:] = arr * (1 - s * 0.85) + s * 30
            return arr
        if k == "rain":
            L = Image.new("L", (W, H))
            d = ImageDraw.Draw(L)
            for x, y, vx, vy, age, life, sz, _ in p:
                d.line([(x, y), (x - vx * 0.012, y - sz)], fill=110, width=max(1, int(1.5 * self.k)))
            a = np.asarray(L).astype(np.float32)[..., None] / 255.0
            arr[:] = arr * (1 - a * 0.5) + 200 * a * 0.5
            arr *= 0.97
            return arr
        # snow / petals / leaves: vẽ trực tiếp
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(L)
        for x, y, vx, vy, age, life, sz, rot in p:
            if k == "snow":
                d.ellipse([x - sz, y - sz, x + sz, y + sz], fill=(245, 248, 255, 220))
            else:
                col = (250, 190, 205, 235) if k == "cherry_blossom" else (150, 96, 40, 235)
                c, s_ = math.cos(rot), math.sin(rot)
                pts = [(x + c * sz, y + s_ * sz * 0.5), (x - s_ * sz * 0.45, y + c * sz * 0.45),
                       (x - c * sz, y - s_ * sz * 0.5), (x + s_ * sz * 0.45, y - c * sz * 0.45)]
                d.polygon(pts, fill=col)
        a = np.asarray(L).astype(np.float32)
        al = a[..., 3:4] / 255.0
        arr[:] = arr * (1 - al) + a[..., :3] * al
        return arr
