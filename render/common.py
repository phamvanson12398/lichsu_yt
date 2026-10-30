"""Các hàm dùng chung cho dựng hình: font, màu, gradient, glow, ridge, vignette, hạt nhiễu."""
import math
import os
import random
import unicodedata
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD = (244, 210, 140)


def N(s):
    """Chuẩn hóa Unicode NFC cho tiếng Việt."""
    return unicodedata.normalize("NFC", s or "")


def lerp(a, b, t):
    t = min(max(t, 0.0), 1.0)
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


# ---------------------------------------------------------------- fonts
_FONT_CANDIDATES = {
    "serif_bold": ["NotoSerif-Bold.ttf", "timesbd.ttf", "DejaVuSerif-Bold.ttf"],
    "serif": ["NotoSerif-Regular.ttf", "times.ttf", "DejaVuSerif.ttf"],
    "serif_italic": ["NotoSerif-Italic.ttf", "timesi.ttf", "DejaVuSerif-Italic.ttf"],
    "sans": ["NotoSans-Regular.ttf", "arial.ttf", "DejaVuSans.ttf"],
    "sans_bold": ["NotoSans-Bold.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"],
    # chữ Hàn / Nhật / Hán: font riêng từng nước (Hán tự hiển thị theo ngôn ngữ video)
    "cjk_ko": ["NotoSerifKR-Bold.ttf", "NotoSerifCJK-Bold.ttc", "NotoSerifCJKkr-Bold.otf", "malgunbd.ttf", "malgun.ttf",
               "batang.ttc", "AppleSDGothicNeo.ttc", "NotoSansCJK-Bold.ttc", "wqy-zenhei.ttc"],
    "cjk_ko_reg": ["NotoSerifKR-Regular.ttf", "NotoSerifCJK-Regular.ttc", "malgun.ttf", "batang.ttc", "NotoSansCJK-Regular.ttc",
                   "wqy-zenhei.ttc"],
    "cjk_ja": ["NotoSerifJP-Bold.ttf", "NotoSerifCJK-Bold.ttc", "NotoSerifCJKjp-Bold.otf", "YuMinchoB.ttc", "YuGothB.ttc",
               "msmincho.ttc", "msgothic.ttc", "Hiragino Mincho ProN W6.ttc", "NotoSansCJK-Bold.ttc", "wqy-zenhei.ttc"],
    "cjk_ja_reg": ["NotoSerifJP-Regular.ttf", "NotoSerifCJK-Regular.ttc", "YuMincho.ttc", "yumin.ttf", "msmincho.ttc",
                   "NotoSansCJK-Regular.ttc", "wqy-zenhei.ttc"],
}
_FONT_CANDIDATES["cjk"] = _FONT_CANDIDATES["cjk_ja"] + _FONT_CANDIDATES["cjk_ko"]
_LANG = {"code": "vi"}


def set_language(code):
    """Ngôn ngữ video (vi | en | ko | ja): quyết định font cho Hán tự và cách xuống dòng."""
    _LANG["code"] = code or "vi"


def get_language():
    return _LANG["code"]


_FONT_DIRS = [os.path.join(ROOT, "fonts"), "C:\\Windows\\Fonts", os.path.expanduser("~/AppData/Local/Microsoft/Windows/Fonts"),
              "/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/opentype/noto", "/usr/share/fonts/truetype/noto",
              "/usr/share/fonts/noto-cjk", "/usr/share/fonts/truetype/wqy", "/System/Library/Fonts", "/Library/Fonts"]
_FONT_OVERRIDES = {}


def set_font_overrides(d):
    """config.yaml: fonts: {serif_bold: "C:/.../abc.ttf", ...}"""
    _FONT_OVERRIDES.update({k: v for k, v in (d or {}).items() if v})
    font_path.cache_clear()
    font.cache_clear()


@lru_cache(None)
def font_path(kind):
    if kind in _FONT_OVERRIDES and os.path.exists(_FONT_OVERRIDES[kind]):
        return _FONT_OVERRIDES[kind]
    for name in _FONT_CANDIDATES.get(kind, []):
        for d in _FONT_DIRS:
            p = os.path.join(d, name)
            if os.path.exists(p):
                return p
    if kind.startswith("cjk"):
        return None
    raise RuntimeError(f"Không tìm thấy font '{kind}'. Hãy chép file NotoSerif-*.ttf vào thư mục fonts/.")


@lru_cache(256)
def font(kind, size):
    p = font_path(kind)
    if p is None:
        return None
    return ImageFont.truetype(p, max(6, int(size)))


def script_of(ch):
    """'ko' (Hangul) | 'ja' (kana) | 'han' (Hán tự, dấu câu CJK) | 'lat' (còn lại)."""
    o = ord(ch)
    if 0xAC00 <= o <= 0xD7AF or 0x1100 <= o <= 0x11FF or 0x3130 <= o <= 0x318F:
        return "ko"
    if 0x3040 <= o <= 0x30FF or 0x31F0 <= o <= 0x31FF or 0xFF66 <= o <= 0xFF9F:
        return "ja"
    if 0x3400 <= o <= 0x4DBF or 0x4E00 <= o <= 0x9FFF or 0xF900 <= o <= 0xFAFF or 0x3000 <= o <= 0x303F or 0xFF00 <= o <= 0xFF65:
        return "han"
    return "lat"


def is_cjk(ch):
    return script_of(ch) != "lat"


def runs(txt):
    """Tách chuỗi thành các đoạn theo loại chữ để vẽ bằng font phù hợp. Hán tự theo ngữ cảnh / ngôn ngữ video."""
    kinds = [script_of(ch) for ch in txt]
    if "han" in kinds:
        if "ja" in kinds:
            hk = "ja"
        elif "ko" in kinds:
            hk = "ko"
        else:
            hk = "ko" if get_language() == "ko" else "ja"
        kinds = [hk if k == "han" else k for k in kinds]
    out = []
    for ch, k in zip(txt, kinds):
        if k == "lat" and ch == " " and out and out[-1][0] != "lat":
            k = out[-1][0]          # khoảng trắng giữa chữ CJK giữ cùng font
        if out and out[-1][0] == k:
            out[-1][1] += ch
        else:
            out.append([k, ch])
    return out


class RichFont:
    """Font Latin/Việt + font Hàn + font Nhật, vẽ chung một baseline."""

    def __init__(self, kind, size):
        size = max(6, int(round(size)))
        self.main = font(kind, size)
        bold = kind.endswith("bold") or kind == "serif_bold"
        self.ko = font("cjk_ko" if bold else "cjk_ko_reg", size) or font("cjk", size) or self.main
        self.ja = font("cjk_ja" if bold else "cjk_ja_reg", size) or font("cjk", size) or self.main
        self.size = size

    def _f(self, c):
        return self.ko if c == "ko" else self.ja if c == "ja" else self.main

    def length(self, txt):
        d = _DUMMY
        return sum(d.textlength(t, font=self._f(c)) for c, t in runs(txt))

    def metrics(self):
        ms = [f.getmetrics() for f in {id(f): f for f in (self.main, self.ko, self.ja)}.values()]
        return max(m[0] for m in ms), max(m[1] for m in ms)

    def draw(self, d, xy, txt, fill):
        """xy = góc trên trái của dòng (theo ascent chung)."""
        asc, _ = self.metrics()
        x, y = xy
        for c, t in runs(txt):
            f = self._f(c)
            d.text((x, y + asc), t, font=f, fill=fill, anchor="ls")
            x += d.textlength(t, font=f)


_DUMMY = ImageDraw.Draw(Image.new("RGBA", (1, 1)))


def text_layer(txt, kind="serif_bold", size=60, fill=GOLD, alpha=1.0, shadow=True, pad=None):
    """Ảnh RGBA chứa một dòng chữ (có bóng đổ), mọi từ cùng baseline."""
    txt = N(txt)
    size = max(6, int(round(size)))
    rf = RichFont(kind, size)
    asc, desc = rf.metrics()
    pad = pad if pad is not None else max(6, size // 6)
    w = int(rf.length(txt)) + 2 * pad + 4
    h = asc + desc + 2 * pad
    im = Image.new("RGBA", (max(1, w), max(1, h)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if shadow:
        off = max(2, size // 28)
        rf.draw(d, (pad + off, pad + off), txt, (0, 0, 0, int(200 * alpha)))
    rf.draw(d, (pad, pad), txt, tuple(fill[:3]) + (int(255 * alpha),))
    return im


def with_alpha(im, a):
    if a >= 0.999:
        return im
    arr = np.asarray(im).copy()
    arr[..., 3] = (arr[..., 3].astype(np.float32) * max(0.0, a)).astype(np.uint8)
    return Image.fromarray(arr)


NO_LINE_START = set("、。，．・：；？！ー）」』】〕〉》”’ゃゅょぁぃぅぇぉっャュョァィゥェォッ…,.!?:;)]")


def tokens(txt):
    """Đơn vị để xuống dòng / hiện từng từ: theo khoảng trắng; tiếng Nhật (không khoảng trắng) theo từng ký tự."""
    txt = N(txt)
    if " " in txt.strip() and not (get_language() == "ja" and sum(1 for c in txt if is_cjk(c)) > len(txt) * 0.5):
        return [w for w in txt.split()], " "
    return list(txt.replace(" ", "")), ""


def wrap_text(txt, rf, max_w):
    toks, sep = tokens(txt)
    if not sep and rf.length(txt) > max_w and rf.length(txt) <= 2 * max_w:
        return _split_two(toks, rf, max_w)
    lines, cur = [], ""
    for w in toks:
        t = (cur + sep + w) if cur else w
        if rf.length(t) <= max_w or not cur or (not sep and w in NO_LINE_START):
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _split_two(chars, rf, max_w):
    """Chữ không khoảng trắng (tiếng Nhật): chia 2 dòng cân nhau, ưu tiên ngắt sau dấu câu、。 và sau chữ kana."""
    s = "".join(chars)
    total = rf.length(s)
    best, best_i = None, len(s) // 2
    for i in range(1, len(s)):
        if s[i] in NO_LINE_START:
            continue
        w1 = rf.length(s[:i])
        if w1 > max_w or total - w1 > max_w:
            continue
        pen = abs(total - 2 * w1) / total
        prev = s[i - 1]
        if prev in "、。！？」』":
            pen -= 0.6
        elif script_of(prev) == "ja" and script_of(s[i]) == "han":
            pen -= 0.3           # ngắt trước Hán tự (đầu từ mới) tự nhiên hơn
        elif script_of(prev) == "han" and script_of(s[i]) == "han":
            pen += 0.2           # tránh cắt đôi một từ Hán (tên người, địa danh)
        if best is None or pen < best:
            best, best_i = pen, i
    return [s[:best_i], s[best_i:]]


def phrase_chunks(txt, n=5):
    """Chia câu tiếng Nhật thành cụm ~n ký tự (cắt sau dấu câu) cho hiệu ứng hiện từng từ."""
    toks, sep = tokens(txt)
    if sep:
        return toks
    out, cur = [], ""
    for ch in toks:
        cur += ch
        if ch in "、。！？」』" or (len(cur) >= n and ch not in NO_LINE_START):
            out.append(cur)
            cur = ""
    if cur:
        if out and len(cur) <= 1:
            out[-1] += cur
        else:
            out.append(cur)
    return out


# ---------------------------------------------------------------- drawing helpers
def vgradient(w, h, top, bottom, power=1.0):
    t = np.linspace(0, 1, max(2, h), dtype=np.float32)[:, None] ** power
    top = np.array(top[:3], np.float32)
    bottom = np.array(bottom[:3], np.float32)
    row = top + (bottom - top) * t[..., None]
    arr = np.broadcast_to(row, (h, w, 3))
    return Image.fromarray(arr.astype(np.uint8), "RGB")


def vgradient_rgba(w, h, top, bottom, a_top=255, a_bottom=255, power=1.0):
    rgb = vgradient(w, h, top, bottom, power)
    t = np.linspace(0, 1, max(2, h), dtype=np.float32) ** power
    a = (a_top + (a_bottom - a_top) * t)[:, None] * np.ones((1, w), np.float32)
    im = rgb.convert("RGBA")
    im.putalpha(Image.fromarray(a.astype(np.uint8)))
    return im


def ridge(base, amp, seed, width, step=8, x0=0, freq=1.0, smooth=False):
    """Đường sống núi (danh sách điểm) dùng nhiều hình sin như demo."""
    r = random.Random(seed)
    ph = [r.uniform(0, 6.28) for _ in range(4)]
    fr = [r.uniform(0.6, 1.4) * freq for _ in range(4)]
    k = [0.55, 0.3, 0.15, 0.06] if not smooth else [0.7, 0.25, 0.05, 0.0]
    ref = 3840.0
    pts = []
    for x in range(int(x0), int(x0 + width + step), step):
        u = x / ref
        y = base - amp * (k[0] * math.sin(u * 6 * fr[0] + ph[0]) + k[1] * math.sin(u * 13 * fr[1] + ph[1])
                          + k[2] * math.sin(u * 31 * fr[2] + ph[2]) + k[3] * math.sin(u * 77 * fr[3] + ph[3]))
        pts.append((x, y))
    return pts


def add_glow(img, cx, cy, r, col, strength=1.0):
    """Cộng sáng (additive) một đốm mờ vào ảnh RGB/RGBA (vùng con để nhanh)."""
    r = max(2, int(r))
    pad = int(r * 3.8)
    x0, y0 = int(cx - pad), int(cy - pad)
    size = 2 * pad
    g = Image.new("RGB", (size, size))
    ImageDraw.Draw(g).ellipse([pad - r, pad - r, pad + r, pad + r], fill=col[:3])
    g = g.filter(ImageFilter.GaussianBlur(r * 0.9))
    ga = np.asarray(g).astype(np.float32) * strength
    mode = img.mode
    a = np.asarray(img).astype(np.float32)
    H, W = a.shape[:2]
    sx0, sy0 = max(0, x0), max(0, y0)
    sx1, sy1 = min(W, x0 + size), min(H, y0 + size)
    if sx1 <= sx0 or sy1 <= sy0:
        return img
    a[sy0:sy1, sx0:sx1, :3] += ga[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), mode)


def glow_sprite(r, col, core=None):
    """Đốm sáng float32 (h,w,3) để cộng vào khung hình."""
    r = max(3, int(r))
    pad = int(r * 3.4)
    g = Image.new("RGB", (2 * pad, 2 * pad))
    d = ImageDraw.Draw(g)
    d.ellipse([pad - r, pad - r, pad + r, pad + r], fill=col[:3])
    if core:
        d.ellipse([pad - r * .4, pad - r * .3, pad + r * .4, pad + r * .5], fill=core[:3])
    g = g.filter(ImageFilter.GaussianBlur(r * 0.75))
    return np.asarray(g).astype(np.float32)


def safe_composite(dst, src, x, y):
    """alpha_composite cho phép toạ độ âm / tràn ngoài ảnh."""
    x, y = int(round(x)), int(round(y))
    W, H = dst.size
    w, h = src.size
    sx0, sy0 = max(0, -x), max(0, -y)
    sx1, sy1 = min(w, W - x), min(h, H - y)
    if sx1 <= sx0 or sy1 <= sy0:
        return
    if (sx0, sy0, sx1, sy1) != (0, 0, w, h):
        src = src.crop((sx0, sy0, sx1, sy1))
    if dst.mode == "RGBA" and src.mode == "RGBA":
        dst.alpha_composite(src, (x + sx0, y + sy0))
    else:
        dst.paste(src, (x + sx0, y + sy0), src if src.mode == "RGBA" else None)


def add_array(dst, src, cx, cy, gain=1.0):
    """Cộng mảng src (h,w,c) vào dst (H,W,c) tại tâm cx,cy."""
    h, w = src.shape[:2]
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    H, W = dst.shape[:2]
    sx0, sy0, sx1, sy1 = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if sx1 <= sx0 or sy1 <= sy0:
        return
    dst[sy0:sy1, sx0:sx1] += src[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] * gain


@lru_cache(8)
def vignette(w, h, strength=0.55):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    return (1 - strength * np.clip(r - 0.38, 0, 1) ** 1.5)[..., None].astype(np.float32)


@lru_cache(4)
def grain_frames(w, h, amount=7.0, n=1, seed=11):
    """Hạt nhiễu. n=1: hạt tĩnh như demo (nén tốt, file nhỏ); n>1: hạt động kiểu phim (file nặng hơn nhiều)."""
    rng = np.random.default_rng(seed)
    return [rng.normal(0, amount, (h, w, 1)).astype(np.float32) for _ in range(n)]


def smooth_path(pts, n=200):
    """Nội suy đường gấp khúc thành đường cong mượt (Catmull-Rom) với n điểm."""
    pts = np.array(pts, float)
    if len(pts) < 2:
        return pts
    if len(pts) > 2:
        P = np.vstack([pts[0], pts, pts[-1]])
        out = []
        for i in range(1, len(P) - 2):
            p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
            for t in np.linspace(0, 1, 24, endpoint=False):
                t2, t3 = t * t, t * t * t
                out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                                  + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
        out.append(pts[-1])
        pts = np.array(out)
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]
    s = np.linspace(0, d[-1], n)
    return np.c_[np.interp(s, d, pts[:, 0]), np.interp(s, d, pts[:, 1])]


def darken(col, k):
    return tuple(int(c * k) for c in col[:3])


def mix(a, b, t):
    return lerp(a, b, t)
