"""Hiệu ứng chữ xuất hiện (mục 7), mỗi kiểu kèm âm thanh:

  cinematic    : chữ to thu nhỏ + mờ dần vào, đường kẻ vàng chạy ra hai bên, dòng phụ hiện sau. (riser + boom + shimmer)
  typewriter   : hiện từng ký tự, con trỏ nhấp nháy.                                     (gõ phím, dùng ít)
  word_by_word : hiện từng từ, nổi lên nhẹ.                                              (pop nhẹ)
  slide_in     : trượt từ trái vào, có vệt nhòe.                                         (whoosh trái -> phải)
  count_year   : số năm chạy (vd 900 -> 938).                                            (tích tắc + chuông)
  subtitle     : phụ đề dưới màn hình khớp lời đọc, không âm thanh.

TextFX(spec, OW, OH).draw(frame_rgba, u) vẽ tại thời điểm u (giây kể từ lúc chữ bắt đầu).
TextFX.events() trả về danh sách (thời điểm, tag âm thanh, âm lượng).
"""
import re

from PIL import Image, ImageDraw, ImageFilter

from render.common import GOLD, N, RichFont, ease, ease_out, text_layer, with_alpha, wrap_text

STYLES = ["cinematic", "typewriter", "word_by_word", "slide_in", "count_year", "subtitle", "none"]


def band(OW, OH, y0, y1, strength=170, blur=60):
    m = Image.new("L", (OW, OH), 0)
    ImageDraw.Draw(m).rectangle([0, y0, OW, y1], fill=strength)
    m = m.filter(ImageFilter.GaussianBlur(blur * OW / 1920))
    b = Image.new("RGBA", (OW, OH), (0, 0, 0, 0))
    b.putalpha(m)
    return b


class TextFX:
    def __init__(self, spec, OW, OH, start=0.0, dur=4.0):
        self.style = spec.get("text_style") or "cinematic"
        self.text = N(str(spec.get("text", "")))
        self.sub = N(str(spec.get("subtext", "") or ""))
        self.pos = spec.get("text_pos", "center")
        self.count_from = spec.get("count_from")
        self.OW, self.OH = OW, OH
        self.k = OW / 1920.0
        self.start = float(start)
        self.dur = float(dur)
        self.hold_out = spec.get("text_out")  # giây (cục bộ) để chữ mờ đi; None = giữ tới hết cảnh
        k = self.k
        self.cy = {"center": 520, "top": 260, "lower": 800}.get(self.pos, 520) * k
        self._band = None
        self._cache = {}
        st = self.style
        if st == "cinematic":
            size = 130 if len(self.text) <= 18 else 100 if len(self.text) <= 28 else 76
            self.L_main = text_layer(self.text, "serif_bold", size * k)
            self.L_sub = text_layer(self.sub, "serif", 54 * k) if self.sub else None
        elif st in ("typewriter", "slide_in"):
            size = 72 if len(self.text) <= 34 else 56
            self.size = size * k
            rf = RichFont("serif_bold", self.size)
            self.lines = wrap_text(self.text, rf, OW * 0.82)
            self.L_lines = [text_layer(ln, "serif_bold", self.size) for ln in self.lines]
            self.L_sub = text_layer(self.sub, "serif", 50 * k) if self.sub else None
            self.cps = 15 if len(self.text) < 60 else 22
        elif st == "word_by_word":
            size = 72 if len(self.text) <= 40 else 58
            rf = RichFont("serif_bold", size * k)
            lines = wrap_text(self.text, rf, OW * 0.82)
            self.words = []   # (layer, x, y)
            lh = rf.metrics()[0] + rf.metrics()[1] + 26 * k
            y = self.cy - lh * (len(lines) - 1) / 2
            sp = 22 * k
            for ln in lines:
                ws = [text_layer(w, "serif_bold", size * k) for w in ln.split()]
                x = (OW - (sum(w.width for w in ws) + sp * (len(ws) - 1))) / 2
                for w in ws:
                    self.words.append((w, x, y))
                    x += w.width + sp
                y += lh
            n = max(1, len(self.words))
            self.stagger = min(0.3, max(0.12, (self.dur - 1.2) / n))
            self.L_sub = text_layer(self.sub, "serif", 50 * k) if self.sub else None
        elif st == "count_year":
            digits = re.sub(r"[^0-9-]", "", self.text) or "0"
            self.target = int(digits)
            self.c_from = int(self.count_from if self.count_from is not None else max(0, self.target - 40))
            self.prefix = self.text[: self.text.find(digits[0])] if digits[0] in self.text else ""
            self.L_sub = text_layer(self.sub, "serif", 54 * k) if self.sub else None
            self.run = min(1.6, max(0.8, self.dur * 0.45))

    # -------------------------------------------------------------- helpers
    def _bandimg(self):
        if self._band is None:
            if self.style == "subtitle":
                self._band = band(self.OW, self.OH, int(self.OH * 0.78), self.OH, 200, 60)
            else:
                cy = self.cy
                self._band = band(self.OW, self.OH, int(cy - 120 * self.k), int(cy + 140 * self.k), 165, 60)
        return self._band

    def _paste_c(self, fr, lay, cy, dx=0, a=1.0):
        if a <= 0:
            return
        lay = with_alpha(lay, a)
        fr.alpha_composite(lay, (int((self.OW - lay.width) / 2 + dx), int(cy - lay.height / 2)))

    def _out_alpha(self, u):
        if self.hold_out is None:
            return 1.0
        return 1 - ease((u - self.hold_out) / 0.4)

    # -------------------------------------------------------------- draw
    def draw(self, fr, t):
        u = t - self.start
        if u < 0 or self.style == "none" or not self.text:
            return
        oa = self._out_alpha(u)
        if oa <= 0:
            return
        fr.alpha_composite(with_alpha(self._bandimg(), min(1.0, u / 0.4) * oa))
        k = self.k
        st = self.style
        gold = GOLD + (int(255 * oa),)
        if st == "cinematic":
            a = ease_out((u - 0.5) / 0.35)
            if a > 0:
                s = 1.25 - 0.25 * a
                lay = self.L_main.resize((int(self.L_main.width * s), int(self.L_main.height * s)), Image.BICUBIC)
                self._paste_c(fr, lay, self.cy - 10 * k, a=a * oa)
            b = ease_out((u - 1.25) / 0.5)
            if b > 0:
                hw = min(self.OW * 0.4, max(260 * k, self.L_main.width * 0.35)) * b
                y = self.cy + self.L_main.height * 0.42
                ImageDraw.Draw(fr).line([(self.OW / 2 - hw, y), (self.OW / 2 + hw, y)], fill=gold, width=max(1, int(3 * k)))
                if self.L_sub:
                    self._paste_c(fr, self.L_sub, y + 50 * k, a=b * oa)
        elif st == "typewriter":
            n = int(max(0, u - 0.4) * self.cps)
            lh = self.L_lines[0].height
            y0 = self.cy - lh * len(self.lines) / 2
            left = n
            d = ImageDraw.Draw(fr)
            for i, (ln, full) in enumerate(zip(self.lines, self.L_lines)):
                shown = ln[:max(0, left)]
                left -= len(ln) + 1
                x0 = (self.OW - full.width) / 2
                y = y0 + i * lh
                if shown:
                    key = (i, len(shown))
                    if key not in self._cache:
                        self._cache = {kk: vv for kk, vv in self._cache.items() if kk[0] != i}
                        self._cache[key] = text_layer(shown, "serif_bold", self.size)
                    fr.alpha_composite(with_alpha(self._cache[key], oa), (int(x0), int(y)))
                if 0 <= left + len(ln) + 1 <= len(ln) or (i == len(self.lines) - 1 and left >= 0):
                    if (u * 2.5) % 1 < 0.6 or left < 0:
                        rf = RichFont("serif_bold", self.size)
                        cw = rf.length(shown) if shown else 0
                        d.rectangle([x0 + 14 * k + cw, y + lh * 0.18, x0 + 20 * k + cw, y + lh * 0.82], fill=gold)
            done = (u - 0.4) * self.cps > len(self.text)
            if done and self.L_sub:
                self._paste_c(fr, self.L_sub, y0 + lh * len(self.lines) + 40 * k, a=ease_out((u - 0.4 - len(self.text) / self.cps) / 0.5) * oa)
        elif st == "word_by_word":
            for i, (w, x, y) in enumerate(self.words):
                a = ease_out((u - 0.4 - i * self.stagger) / 0.3)
                if a > 0:
                    fr.alpha_composite(with_alpha(w, a * oa), (int(x), int(y - w.height / 2 + 30 * k * (1 - a))))
            if self.L_sub:
                tsub = 0.4 + len(self.words) * self.stagger + 0.3
                self._paste_c(fr, self.L_sub, self.words[-1][2] + 90 * k, a=ease_out((u - tsub) / 0.5) * oa)
        elif st == "slide_in":
            a = ease_out((u - 0.4) / 0.55)
            if a > 0:
                lh = self.L_lines[0].height
                y0 = self.cy - lh * (len(self.L_lines) - 1) / 2
                for i, L in enumerate(self.L_lines):
                    dx = -(self.OW / 2 + L.width / 2) * (1 - a)
                    if a < 0.98:
                        streak = L.filter(ImageFilter.BoxBlur(18 * k * (1 - a)))
                        self._paste_c(fr, streak, y0 + i * lh, dx - 40 * k * (1 - a), a=oa)
                    self._paste_c(fr, L, y0 + i * lh, dx, a=oa)
                b = ease_out((u - 0.9) / 0.5)
                if b > 0:
                    hw = (max(L.width for L in self.L_lines) / 2) * b
                    y = y0 + (len(self.L_lines) - 0.5) * lh + 10 * k
                    ImageDraw.Draw(fr).line([(self.OW / 2 - hw, y), (self.OW / 2 + hw, y)], fill=gold, width=max(1, int(3 * k)))
                    if self.L_sub:
                        self._paste_c(fr, self.L_sub, y + 50 * k, a=b * oa)
        elif st == "count_year":
            y = self.year_at(u)
            done = u > 0.3 + self.run
            col = (255, 236, 190) if done else GOLD
            key = (y, done)
            if key not in self._cache:
                self._cache = {key: text_layer(f"{self.prefix}{y}", "serif_bold", 170 * k, fill=col)}
            lay = self._cache[key]
            if done:
                s = 1 + 0.08 * max(0, 1 - (u - 0.3 - self.run) / 0.25)
                lay = lay.resize((int(lay.width * s), int(lay.height * s)), Image.BICUBIC)
            self._paste_c(fr, lay, self.cy - 40 * k, a=min(1, u / 0.25) * oa)
            b = ease_out((u - 0.5 - self.run) / 0.5)
            if b > 0 and self.L_sub:
                self._paste_c(fr, self.L_sub, self.cy + 120 * k, a=b * oa)

    def year_at(self, u):
        if u <= 0.3:
            return self.c_from
        return int(round(self.c_from + (self.target - self.c_from) * ease_out((u - 0.3) / self.run)))

    # -------------------------------------------------------------- sound
    def events(self):
        """(t tuyệt đối trong cảnh, tag, gain)"""
        s, st = self.start, self.style
        ev = []
        if not self.text or st in ("none", "subtitle"):
            return ev
        if st == "cinematic":
            ev += [(s + 0.0, "riser", 1.0), (s + 0.5, "boom", 0.9), (s + 1.25, "shimmer", 1.0)]
        elif st == "typewriter":
            n = len(self.text)
            step = max(1, n // 40)
            for i in range(0, n, step):
                if self.text[i] != " ":
                    ev.append((s + 0.4 + i / self.cps, "click", 0.7))
        elif st == "word_by_word":
            for i in range(len(self.words)):
                ev.append((s + 0.4 + i * self.stagger, "pop", 0.8))
        elif st == "slide_in":
            ev += [(s + 0.3, "whoosh", 1.0), (s + 0.9, "shimmer", 0.6)]
        elif st == "count_year":
            last = self.c_from
            u = 0.3
            while u <= 0.3 + self.run:
                y = self.year_at(u)
                if y != last:
                    ev.append((s + u, "tick", 0.8))
                    last = y
                u += 1 / 30
            ev.append((s + 0.3 + self.run, "bell", 1.0))
        return ev


class Subtitles:
    """Phụ đề dưới màn hình khớp từng câu (chia câu dài thành đoạn ngắn tối đa 2 dòng)."""

    def __init__(self, cues, OW, OH, size=46):
        self.OW, self.OH = OW, OH
        self.k = OW / 1920
        self.rf = RichFont("serif_bold", size * self.k)
        self.size = size * self.k
        self.cues = []
        for (a, b, text) in cues:
            for (ca, cb, chunk) in split_cue(a, b, N(text), self.rf, OW * 0.86):
                self.cues.append((ca, cb, chunk))
        self.bandimg = band(OW, OH, int(OH * 0.80), OH, 190, 55)
        self._cache = {}

    def draw(self, fr, t):
        for i, (a, b, text) in enumerate(self.cues):
            if a <= t < b:
                al = min(1, (t - a) / 0.15, (b - t) / 0.15)
                fr.alpha_composite(with_alpha(self.bandimg, 0.9))
                if i not in self._cache:
                    lines = wrap_text(text, self.rf, self.OW * 0.86)
                    self._cache[i] = [text_layer(ln, "serif_bold", self.size) for ln in lines]
                lays = self._cache[i]
                lh = lays[0].height * 0.92
                y = self.OH - 60 * self.k - lh * len(lays)
                for L in lays:
                    fr.alpha_composite(with_alpha(L, al), (int((self.OW - L.width) / 2), int(y)))
                    y += lh
                return


def split_cue(a, b, text, rf, max_w):
    lines = wrap_text(text, rf, max_w)
    if len(lines) <= 2:
        return [(a, b, text)]
    chunks = [" ".join(lines[i:i + 2]) for i in range(0, len(lines), 2)]
    total = sum(len(c) for c in chunks)
    out, t = [], a
    for c in chunks:
        d = (b - a) * len(c) / total
        out.append((t, t + d, c))
        t += d
    return out
