"""Cảnh đồ họa (làm video đa dạng hơn, không chỉ toàn cảnh rộng):

  timeline  : dòng thời gian, các mốc hiện dần     {"events": [{"year": "905", "text": "..."}], "highlight": 2}
  character : thẻ nhân vật — chân dung bóng trong khung tròn viền vàng, tên, năm, vài ý chính
              {"name": "Ngô Quyền", "subtitle": "898 – 944", "role": "ally|enemy|neutral",
               "look": "general|king|scholar|admiral|monk", "facts": ["...", "..."]}
  compare   : biểu đồ so sánh (quân số, số thuyền...) — luôn kèm "note" ghi độ chắc chắn của số liệu
              {"title": "...", "unit": "chiến thuyền", "items": [{"label": "...", "value": 100, "side": "enemy"}], "note": "..."}
  tide      : mặt cắt dòng sông: triều lên thuyền nổi qua bãi cọc, triều rút thuyền mắc cọc
              {"label_high": "Triều lên", "label_low": "Triều rút", "label_stakes": "Cọc gỗ đầu bịt sắt", "fall_at": 4.0}

Mỗi lớp có frame(t) -> ảnh RGB và events() -> [(t, tag, gain)]. Cảnh có thể kèm "narration" (phụ đề vẽ ở renderer).
"""
import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from assets_code.common.shapes import headgear
from render.common import GOLD, N, RichFont, ease, ease_out, text_layer, vignette, with_alpha, wrap_text

TYPES = ["timeline", "character", "compare", "tide"]
LOOKS = ["general", "king", "scholar", "admiral", "monk", "queen"]


def _bg(OW, OH, pal, seed=1, kind="dark"):
    """Nền tối có ánh ấm (hoặc giấy cổ), viền tối + hạt nhiễu nướng sẵn."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:OH, 0:OW].astype(np.float32)
    r = np.sqrt(((xx - OW * 0.5) / (OW * 0.6)) ** 2 + ((yy - OH * 0.45) / (OH * 0.7)) ** 2)[..., None]
    if kind == "parchment":
        base = np.zeros((OH, OW, 3), np.float32) + np.array((226, 206, 165), np.float32)
    else:
        c_out = np.array(pal["sil"], np.float32) * 0.55
        c_in = np.array(pal["sky"][0], np.float32) * 0.55 + np.array(pal["fire"], np.float32) * 0.07 + 10
        base = c_in + (c_out - c_in) * np.clip(r, 0, 1)
    base = base * vignette(OW, OH, 0.6) + rng.normal(0, 5.0, (OH, OW, 1))
    return Image.fromarray(base.clip(0, 255).astype(np.uint8))


def _paste(fr, lay, x, y, a=1.0, center=False):
    if a <= 0:
        return
    lay = with_alpha(lay, a)
    if center:
        x, y = x - lay.width / 2, y - lay.height / 2
    fr.alpha_composite(lay, (int(x), int(y)))


class _Base:
    def __init__(self, spec, OW, OH, fps, dur, pal, subtitles=False, seed=1, lang="vi"):
        self.spec, self.OW, self.OH, self.fps, self.dur, self.pal = spec or {}, OW, OH, fps, dur, pal
        self.k = OW / 1920.0
        self.subtitles = subtitles
        self.bottom = OH * (0.76 if subtitles else 0.92)      # giữ nội dung trên vùng phụ đề
        self.seed = seed
        self.lang = lang
        self.base = _bg(OW, OH, pal, seed, self.spec.get("background", "dark"))
        self._cache = {}

    def T(self, key, txt, kind, size, fill=GOLD, shadow=True):
        k = (key, txt, kind, size, fill)
        if k not in self._cache:
            self._cache[k] = text_layer(txt, kind, size * self.k, fill=fill, shadow=shadow)
        return self._cache[k]

    def title(self, fr, t):
        if self.spec.get("title"):
            lay = self.T("title", N(self.spec["title"]), "serif_bold", 50)
            _paste(fr, lay, self.OW / 2, 95 * self.k, ease((t - 0.1) / 0.5), center=True)

    def frame(self, t):
        fr = self.base.copy().convert("RGBA")
        self.draw(fr, t)
        return fr.convert("RGB")


# ======================================================================== dòng thời gian
class TimelineVisual(_Base):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        ev = list(self.spec.get("events") or [])[:7]
        self.evs = ev
        n = max(1, len(ev))
        self.step = max(0.35, min(1.2, (self.dur - 1.8) / n))
        self.hi = self.spec.get("highlight", n - 1)

    def times(self):
        return [0.7 + i * self.step for i in range(len(self.evs))]

    def draw(self, fr, t):
        k, OW = self.k, self.OW
        self.title(fr, t)
        d = ImageDraw.Draw(fr)
        n = max(1, len(self.evs))
        y = (self.bottom * 0.5 + 40 * k) if not self.spec.get("title") else self.bottom * 0.52
        x0, x1 = OW * 0.08, OW * 0.92
        prog = ease((t - 0.2) / max(0.5, 0.5 + self.step * n))
        d.line([(x0, y), (x0 + (x1 - x0) * prog, y)], fill=GOLD + (255,), width=max(2, int(4 * k)))
        if prog >= 0.98:
            d.polygon([(x1 + 4 * k, y - 12 * k), (x1 + 28 * k, y), (x1 + 4 * k, y + 12 * k)], fill=GOLD + (255,))
        gap = (x1 - x0) / n
        rf = RichFont("serif", 27 * k)
        for i, (e, ti) in enumerate(zip(self.evs, self.times())):
            a = ease_out((t - ti) / 0.4)
            if a <= 0:
                continue
            cx = x0 + gap * (i + 0.5)
            hi = i == self.hi
            r = (15 if hi else 10) * k * (0.6 + 0.4 * a)
            if hi:
                for g in range(3):
                    rr = r + (8 + g * 9) * k * a
                    d.ellipse([cx - rr, y - rr, cx + rr, y + rr], outline=(200, 70, 40, int(160 * a / (g + 1))), width=max(1, int(3 * k)))
            d.ellipse([cx - r, y - r, cx + r, y + r], fill=(255, 236, 190, int(255 * a)) if hi else GOLD + (int(255 * a),),
                      outline=(40, 25, 10, 255), width=max(1, int(2 * k)))
            yl = self.T(f"y{i}", N(str(e.get("year", ""))), "serif_bold", 54 if hi else 44, fill=(255, 236, 190) if hi else GOLD)
            _paste(fr, yl, cx, y - 58 * k - 20 * k * (1 - a), a, center=True)
            lines = wrap_text(N(str(e.get("text", ""))), rf, gap * 0.92)[:3]
            for j, ln in enumerate(lines):
                lay = self.T(f"t{i}{j}", ln, "serif", 27, fill=(232, 222, 205))
                _paste(fr, lay, cx, y + 48 * k + j * 36 * k + 14 * k * (1 - a), a, center=True)

    def events(self):
        ev = [(0.2, "whoosh", 0.6)]
        for i, ti in enumerate(self.times()):
            ev.append((ti, "bell" if i == self.hi else "pop", 0.5 if i == self.hi else 0.8))
        return ev


# ======================================================================== thẻ nhân vật
def draw_bust(size, look="general", country="vietnam", col=(14, 10, 8, 255)):
    """Chân dung dạng bóng (đầu + vai + mũ / mão theo nước, vai trò). Trả về ảnh RGBA vuông."""
    S = size * 2
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = S * 0.5
    hy = S * 0.42
    r = S * 0.13
    # vai + thân
    if look in ("general", "admiral"):
        d.polygon([(cx - S * 0.42, S), (cx + S * 0.42, S), (cx + S * 0.36, S * 0.66), (cx + S * 0.2, S * 0.58),
                   (cx - S * 0.2, S * 0.58), (cx - S * 0.36, S * 0.66)], fill=col)
        for sgn in (-1, 1):   # giáp vai
            d.pieslice([cx + sgn * S * 0.3 - S * 0.13, S * 0.56, cx + sgn * S * 0.3 + S * 0.13, S * 0.8], 180, 360, fill=col)
    else:
        d.polygon([(cx - S * 0.4, S), (cx + S * 0.4, S), (cx + S * 0.3, S * 0.64), (cx + S * 0.12, S * 0.58),
                   (cx - S * 0.12, S * 0.58), (cx - S * 0.3, S * 0.64)], fill=col)
    d.rectangle([cx - r * 0.45, hy, cx + r * 0.45, S * 0.62], fill=col)
    d.ellipse([cx - r, hy - r * 1.15, cx + r, hy + r * 1.05], fill=col)
    # mũ / mão
    if look == "king":
        if country == "korea":          # mũ dực thiện quan: mũ đen, 2 cánh tròn phía sau
            d.ellipse([cx - r * 1.05, hy - r * 1.7, cx + r * 1.05, hy - r * 0.2], fill=col)
            for sgn in (-1, 1):
                d.ellipse([cx + sgn * r * 0.9 - r * 0.45, hy - r * 1.9, cx + sgn * r * 0.9 + r * 0.45, hy - r * 1.2], fill=col)
        elif country == "japan":        # mũ eboshi cao
            d.polygon([(cx - r * 0.9, hy - r * 0.6), (cx + r * 0.9, hy - r * 0.6), (cx + r * 0.6, hy - r * 2.6), (cx - r * 0.2, hy - r * 2.9)], fill=col)
        elif country == "england":      # vương miện răng cưa
            d.rectangle([cx - r * 1.05, hy - r * 1.55, cx + r * 1.05, hy - r * 0.8], fill=col)
            for j in range(5):
                x = cx - r + j * r / 2
                d.polygon([(x - r * 0.18, hy - r * 1.5), (x + r * 0.18, hy - r * 1.5), (x, hy - r * 2.1)], fill=col)
        else:                           # mão có tấm phẳng (kiểu miện / bình thiên) + dải ngọc
            d.rectangle([cx - r * 0.95, hy - r * 1.75, cx + r * 0.95, hy - r * 0.7], fill=col)
            d.rectangle([cx - r * 1.7, hy - r * 1.95, cx + r * 1.7, hy - r * 1.72], fill=col)
            for j in range(-3, 4):
                d.line([(cx + j * r * 0.45, hy - r * 1.72), (cx + j * r * 0.45, hy - r * 1.2)], fill=col, width=max(1, int(r * 0.08)))
    elif look == "scholar":
        if country == "korea":
            headgear(d, cx, hy - r * 0.2, r, "gat", col)
        else:                           # khăn / mũ cánh chuồn
            d.rectangle([cx - r * 0.95, hy - r * 1.6, cx + r * 0.95, hy - r * 0.6], fill=col)
            for sgn in (-1, 1):
                d.ellipse([cx + sgn * r * 1.5 - r * 0.6, hy - r * 1.35, cx + sgn * r * 1.5 + r * 0.6, hy - r * 0.95], fill=col)
    elif look == "monk":
        pass
    elif look == "queen":
        d.ellipse([cx - r * 0.7, hy - r * 2.0, cx + r * 0.7, hy - r * 0.9], fill=col)
        d.polygon([(cx - r * 1.3, hy - r * 0.2), (cx - r * 1.0, hy - r * 1.0), (cx - r * 0.7, hy + r * 1.2)], fill=col)
        d.polygon([(cx + r * 1.3, hy - r * 0.2), (cx + r * 1.0, hy - r * 1.0), (cx + r * 0.7, hy + r * 1.2)], fill=col)
    else:                               # tướng / đô đốc: mũ trụ theo nước
        head = {"vietnam": "round", "china": "cone", "korea": "joseon_helmet", "japan": "kabuto", "england": "norman"}.get(country, "round")
        headgear(d, cx, hy, r, head, col, accent=col)
    return im.resize((size, size), Image.LANCZOS)


class CharacterVisual(_Base):
    def __init__(self, spec, OW, OH, fps, dur, pal, subtitles=False, seed=1, lang="vi", country="vietnam"):
        super().__init__(spec, OW, OH, fps, dur, pal, subtitles, seed, lang)
        k = self.k
        self.R = int(min(OH * 0.3, (self.bottom - 60 * k) * 0.42))
        self.cx, self.cy = OW * 0.3, (self.bottom + 40 * k) * 0.5
        role = self.spec.get("role", "ally")
        ring = GOLD if role != "enemy" else (214, 120, 96)
        # khung tròn: nền hoàng hôn theo bảng màu + chân dung bóng + viền sáng
        D = self.R * 2
        port = Image.new("RGBA", (D, D), (0, 0, 0, 0))
        top, mid, bot = (np.array(c, np.float32) for c in pal["sky"])
        yy = np.linspace(0, 1, D, dtype=np.float32)[:, None, None]
        grad = np.where(yy < 0.6, top + (mid - top) * (yy / 0.6), mid + (bot - mid) * ((yy - 0.6) / 0.4))
        sky = Image.fromarray(np.broadcast_to(grad, (D, D, 3)).clip(0, 255).astype(np.uint8)).convert("RGBA")
        bust = draw_bust(int(D * 0.95), self.spec.get("look", "general"), self.spec.get("country", country))
        rim = bust.getchannel("A").filter(ImageFilter.GaussianBlur(D * 0.012))
        rim_l = Image.new("RGBA", bust.size, tuple(pal["sun_glow"]) + (0,))
        rim_l.putalpha(rim)
        sky.alpha_composite(rim_l, (int(D * 0.025) + int(D * 0.01), int(D * 0.05)))
        sky.alpha_composite(bust, (int(D * 0.025), int(D * 0.05)))
        mask = Image.new("L", (D, D), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, D - 1, D - 1], fill=255)
        port.paste(sky, (0, 0), mask)
        ImageDraw.Draw(port).ellipse([2, 2, D - 3, D - 3], outline=ring + (255,), width=max(2, int(6 * k)))
        self.port = port
        self.ring = ring
        self.facts = [N(str(f)) for f in (self.spec.get("facts") or [])][:3]

    def draw(self, fr, t):
        k = self.k
        a = ease_out((t - 0.2) / 0.6)
        if a > 0:
            s = 0.92 + 0.08 * a
            p = self.port.resize((int(self.port.width * s), int(self.port.height * s)), Image.BICUBIC)
            _paste(fr, p, self.cx, self.cy, a, center=True)
        tx = self.OW * 0.52
        name = self._name()
        b = ease_out((t - 0.7) / 0.5)
        top = self.cy - self.R * 0.55
        _paste(fr, name, tx - 60 * k * (1 - b), top, b)
        d = ImageDraw.Draw(fr)
        if b > 0:
            d.line([(tx + 6 * k, top + name.height + 4 * k), (tx + 6 * k + 420 * k * b, top + name.height + 4 * k)],
                   fill=self.ring + (255,), width=max(1, int(3 * k)))
        sub = self.spec.get("subtitle")
        if sub:
            _paste(fr, self.T("sub", N(sub), "serif", 38, fill=(225, 214, 196)), tx, top + name.height + 16 * k, ease((t - 1.1) / 0.5))
        rf = RichFont("serif", 32 * k)
        y = top + name.height + 90 * k
        for i, f in enumerate(self.facts):
            c = ease((t - 1.6 - i * 0.6) / 0.45)
            for j, ln in enumerate(wrap_text("• " + f, rf, self.OW * 0.42)[:2]):
                _paste(fr, self.T(f"f{i}{j}", ln, "serif", 32, fill=(236, 228, 214)), tx + 24 * k * (1 - c), y, c)
                y += 44 * k
            y += 10 * k

    def _name(self):
        """Tên tự thu nhỏ cho vừa khung (tên dài kèm tên gốc trong ngoặc)."""
        size, room = 74, self.OW * 0.45
        while True:
            lay = self.T("name", N(self.spec.get("name", "")), "serif_bold", size)
            if lay.width <= room or size <= 40:
                return lay
            size -= 4

    def events(self):
        return [(0.2, "riser", 0.5), (0.7, "whoosh", 0.7), (1.1, "shimmer", 0.6)] + \
               [(1.6 + i * 0.6, "pop", 0.7) for i in range(len(self.facts))]


# ======================================================================== biểu đồ so sánh
class CompareVisual(_Base):
    COLORS = {"enemy": (196, 72, 52), "ally": (82, 128, 196), "neutral": (170, 160, 140)}

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.items = list(self.spec.get("items") or [])[:5]
        self.vmax = max([float(i.get("value") or 0) for i in self.items] + [1])

    def draw(self, fr, t):
        k = self.k
        self.title(fr, t)
        d = ImageDraw.Draw(fr)
        n = max(1, len(self.items))
        top = 200 * k
        bot = self.bottom - (90 if self.spec.get("note") else 30) * k
        rowh = min(170 * k, (bot - top) / n)
        top += max(0, (bot - top - rowh * n) / 2)
        x0 = self.OW * 0.33
        wmax = self.OW * 0.5
        for i, it in enumerate(self.items):
            st = 0.6 + i * 0.5
            a = ease_out((t - st) / 1.1)
            y = top + i * rowh + rowh * 0.2
            lab = self.T(f"l{i}", N(str(it.get("label", ""))), "serif_bold", 36, fill=(236, 228, 214))
            _paste(fr, lab, x0 - 30 * k - lab.width, y + rowh * 0.3 - lab.height / 2, min(1, (t - st + 0.3) / 0.4))
            if a <= 0:
                continue
            v = float(it.get("value") or 0)
            w = wmax * (v / self.vmax) * a
            col = self.COLORS.get(it.get("side", "neutral"), self.COLORS["neutral"])
            h = rowh * 0.5
            d.rounded_rectangle([x0, y + rowh * 0.3 - h / 2, x0 + max(h * 0.3, w), y + rowh * 0.3 + h / 2], radius=h * 0.25,
                                fill=col + (255,))
            val = it.get("display") or (f"{int(round(v * a)):,}".replace(",", ".") + (" " + self.spec.get("unit", "") if a >= 0.999 else ""))
            num = text_layer(N(str(val)), "serif_bold", 34 * k, fill=GOLD)
            fr.alpha_composite(num, (int(x0 + w + 18 * k), int(y + rowh * 0.3 - num.height / 2)))
        if self.spec.get("note"):
            note = self.T("note", N(self.spec["note"]), "serif_italic", 28, fill=(190, 178, 160))
            _paste(fr, note, self.OW / 2, self.bottom - 45 * k, ease((t - 1.5) / 0.6), center=True)

    def events(self):
        return [(0.6 + i * 0.5, "whoosh", 0.5) for i in range(len(self.items))] + [(0.6 + len(self.items) * 0.5 + 0.8, "pop", 0.6)]


# ======================================================================== sơ đồ thủy triều
class TideVisual(_Base):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        OW, OH, k = self.OW, self.OH, self.k
        self.fall = float(self.spec.get("fall_at", self.dur * 0.45))
        self.bed = self.bottom - 40 * k
        self.y_hi = OH * 0.36
        self.stake_top = OH * 0.47
        self.y_lo = OH * 0.58
        rr = random.Random(7)
        self.stakes = [(OW * (0.12 + 0.76 * i / 13) + rr.uniform(-15, 15) * k, self.stake_top + rr.uniform(-20, 25) * k,
                        rr.uniform(-10, 10) * k) for i in range(14)]
        n = int(self.spec.get("boats", 3))
        self.boats = [(OW * (0.95 + 0.2 * i), rr.uniform(0.9, 1.1)) for i in range(n)]
        self.pal2 = self.pal
        # nền tĩnh: trời, núi xa, bùn đáy sông
        im = self.base.copy()
        d = ImageDraw.Draw(im)
        top, mid, low = self.pal["sky"]
        for y in range(int(self.bed)):
            u = min(1.0, y / (OH * 0.5))
            d.line([(0, y), (OW, y)], fill=tuple(int(top[i] + (low[i] - top[i]) * u) for i in range(3)))
        pts = [(x, OH * 0.33 - 60 * k * (0.6 * math.sin(x / OW * 7) + 0.4 * math.sin(x / OW * 17 + 1))) for x in range(0, OW + 20, 20)]
        d.polygon(pts + [(OW, self.bed), (0, self.bed)], fill=tuple(self.pal["mount"][1]))
        d.rectangle([0, self.bed, OW, OH], fill=(58, 44, 32))
        d.line([(0, self.bed), (OW, self.bed)], fill=(90, 70, 50), width=max(1, int(3 * k)))
        self.static = im

    def level(self, t):
        u = ease((t - self.fall) / 1.6)
        return self.y_hi + (self.y_lo - self.y_hi) * u, u

    def frame(self, t):
        OW, OH, k = self.OW, self.OH, self.k
        fr = self.static.copy().convert("RGBA")
        lv, u = self.level(t)
        water = Image.new("RGBA", (OW, OH), (0, 0, 0, 0))
        dw = ImageDraw.Draw(water)
        wave = [(x, lv + 6 * k * math.sin(x / (70 * k) + t * 2.5)) for x in range(0, OW + 20, 20)]
        wc = tuple(int(c * 0.45 + b) for c, b in zip(self.pal["water"][0], (18, 38, 58)))
        dw.polygon(wave + [(OW, self.bed), (0, self.bed)], fill=wc + (200,))
        dw.line(wave, fill=tuple(self.pal["shimmer"]) + (220,), width=max(1, int(3 * k)))
        d = ImageDraw.Draw(fr)
        wood, iron = (64, 42, 26, 255), (150, 152, 158, 255)
        for x, tip, lean in self.stakes:
            d.polygon([(x - 9 * k, self.bed + 4 * k), (x + 9 * k, self.bed + 4 * k), (x + 9 * k + lean, tip + 30 * k),
                       (x + lean, tip), (x - 9 * k + lean, tip + 30 * k)], fill=wood)
            d.polygon([(x - 9 * k + lean, tip + 30 * k), (x + lean, tip), (x + 9 * k + lean, tip + 30 * k)], fill=iron)
        # thuyền: trôi vào khi nước lên, nước rút thì mắc trên chóp cọc, nghiêng
        prog = ease(min(t, self.fall) / max(0.5, self.fall))
        for i, (x_start, sc) in enumerate(self.boats):
            x = x_start - (x_start - OW * (0.3 + 0.2 * i)) * prog
            stuck_y = self.stake_top - 4 * k
            y = min(lv, stuck_y) if u > 0 else lv
            tilt = (8 + 5 * i) * (1 if i % 2 else -1) * u
            self._boat(fr, x, y + 3 * k * math.sin(t * 2 + i) * (1 - u), sc, tilt)
        fr.alpha_composite(water)
        # nhãn trạng thái
        from core.lang import ui
        hi = self.T("hi", N(self.spec.get("label_high") or ui(self.lang, "tide_high")), "serif_bold", 48)
        lo = self.T("lo", N(self.spec.get("label_low") or ui(self.lang, "tide_low")), "serif_bold", 48, fill=(255, 190, 160))
        a_hi, a_lo = (1 - u) * ease(t / 0.5), u
        _paste(fr, hi, 110 * k, 60 * k, a_hi)
        _paste(fr, lo, 110 * k, 60 * k, a_lo)
        d = ImageDraw.Draw(fr)
        ax, ay = 78 * k, 60 * k + hi.height / 2
        for a, up, col in ((a_hi, True, GOLD), (a_lo, False, (255, 190, 160))):
            if a > 0.02:
                sg = -1 if up else 1
                d.line([(ax, ay - sg * 18 * k), (ax, ay + sg * 8 * k)], fill=col + (int(255 * a),), width=max(2, int(6 * k)))
                d.polygon([(ax - 14 * k, ay + sg * 6 * k), (ax + 14 * k, ay + sg * 6 * k), (ax, ay + sg * 24 * k)], fill=col + (int(255 * a),))
        lab = self.spec.get("label_stakes", ui(self.lang, "stakes"))
        if lab:
            st = self.T("st", N(lab), "serif_italic", 32, fill=(236, 228, 214))
            sx, sy = self.stakes[-3][0], self.stakes[-3][1]
            a = ease((t - 0.8) / 0.5)
            _paste(fr, st, OW - st.width - 60 * k, self.bed + 10 * k if not self.subtitles else sy - 120 * k, a)
        return fr.convert("RGB")

    def _boat(self, fr, x, y, sc, tilt):
        k = self.k * sc
        w, h = int(360 * k), int(330 * k)
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        wl = h * 0.78
        hull = tuple(self.pal["wood"]) + (255,)
        d.polygon([(w * 0.04, wl - 26 * k), (w * 0.96, wl - 34 * k), (w * 0.8, wl + 26 * k), (w * 0.2, wl + 26 * k)], fill=hull)
        d.line([(w * 0.5, wl - 30 * k), (w * 0.5, h * 0.05)], fill=hull, width=max(1, int(6 * k)))
        d.polygon([(w * 0.5, h * 0.08), (w * 0.82, h * 0.14), (w * 0.86, wl - 40 * k), (w * 0.5, wl - 40 * k)], fill=tuple(self.pal["sail"]) + (255,))
        if tilt:
            im = im.rotate(tilt, resample=Image.BICUBIC, center=(w / 2, wl))
        fr.alpha_composite(im, (int(x - w / 2), int(y - wl)))

    def draw(self, fr, t):
        pass

    def events(self):
        return [(self.fall, "whoosh", 0.6), (self.fall + 1.4, "boom", 0.8), (self.fall + 1.5, "kiem_cham", 0.5)]


def make(typ, spec, OW, OH, fps, dur, pal, subtitles=False, seed=1, lang="vi", country="vietnam"):
    cls = {"timeline": TimelineVisual, "character": CharacterVisual, "compare": CompareVisual, "tide": TideVisual}[typ]
    if cls is CharacterVisual:
        return cls(spec, OW, OH, fps, dur, pal, subtitles, seed, lang, country)
    return cls(spec, OW, OH, fps, dur, pal, subtitles, seed, lang)
