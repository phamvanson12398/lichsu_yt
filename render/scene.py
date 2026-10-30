"""Dựng một cảnh minh họa từ mô tả "scene" trong plan.json (mục 5, 6).

  scene = {"time_of_day": "dusk", "weather": "clear", "horizon": 0.58,
           "background": ["sky", "mountains:3", "river"],
           "elements": [{"kind": "boat_vn", "x": 0.7, "y": 0.66, "scale": 0.5, "count": 2, "move": [-0.1, 0]}]}

Cách làm: vẽ mọi lớp ở 2x (nét mịn, không răng cưa), sau đó thu về độ phân giải làm việc
(1.25x cho cảnh zoom, 1x cho cảnh trượt / parallax) để mỗi khung chỉ phải cắt + ghép.
SceneVisual(...).frame(t) trả về mảng float32 (H, W, 3) tại thời điểm t (gọi lần lượt, t tăng dần).
"""
import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from assets_code import registry
from assets_code.registry import Canvas
from render import palettes
from render.common import add_image, finish_frame, glow_image, safe_composite
from render.motion import Camera, canvas_spec
from render.particles import KINDS, System

DEPTH_NAMES = {"far": 0.45, "mid": 0.65, "near": 0.85, "front": 1.05, "fg": 1.3}
TOKEN_ARG = {"mountains": "n", "hills": "n", "islands": "n", "clouds": "n", "coast": "side", "forest": "style",
             "reeds": "height", "bank_near": "top"}
NIGHT_TINT = np.array([0.42, 0.48, 0.64], np.float32)


def parse_token(tok):
    """'mountains:3' -> ('mountains', {'n': 3}); dict {"kind":..., ...} cũng được."""
    if isinstance(tok, dict):
        p = dict(tok)
        return p.pop("kind"), p
    name, _, arg = str(tok).partition(":")
    p = {}
    if arg:
        key = TOKEN_ARG.get(name, "n")
        try:
            p[key] = float(arg) if "." in arg else int(arg)
        except ValueError:
            p[key] = arg
    return name.strip(), p


def depth_for(y, horizon, layer=None):
    if layer is not None:
        if isinstance(layer, (int, float)):
            return float(layer)
        return DEPTH_NAMES.get(str(layer), 0.85)
    f = (y - horizon) / max(0.05, 1 - horizon)
    if f < 0.12:
        return 0.45
    if f < 0.4:
        return 0.65
    if f < 0.75:
        return 0.85
    return 1.05


def persp(y, horizon):
    f = (y - horizon) / max(0.05, 1 - horizon)
    return max(0.25, min(1.8, 0.35 + 1.5 * f))


class Sprite:
    def __init__(self, img, X, Y, depth, anim=None, phase=0.0, move=(0, 0), fires=None, redraw=None):
        self.img, self.X, self.Y, self.depth = img, X, Y, depth
        self.anim, self.phase, self.move = anim, phase, move
        self.fires = fires or []
        self.redraw = redraw          # (func, x, y, scale, params, size, draw_ox, draw_oy)
        self._cache = (None, None)


def expand(el, comp, horizon, seed):
    n = max(1, int(el.get("count", 1)))
    x = float(el.get("x", 0.5))
    y = float(el.get("y", comp.y_default))
    spacing = float(el.get("spacing", comp.spacing))
    rr = random.Random(seed)
    out = []
    for i in range(n):
        if n == 1:
            xi, yi = x, y
        else:
            xi = x + (i - (n - 1) / 2) * spacing + rr.uniform(-0.15, 0.15) * spacing
            yi = y + (0.025 if i % 2 else 0) + rr.uniform(-0.01, 0.01)
        sc = el.get("scale")
        sc = float(sc) if sc is not None else comp.scale_default * (persp(yi, horizon) if comp.persp else 1.0)
        if n > 1:
            sc *= rr.uniform(0.9, 1.05) * (1 + (yi - y) * 1.5)
        out.append((xi, yi, sc))
    return out


class SceneVisual:
    def __init__(self, desc, OW, OH, fps, dur, palette=None, country="vietnam", motion="static", particles=(),
                 seed=1, supersample=2.0, grain=7.0, vignette_strength=0.55, focus=(0.5, 0.5), grain_n=1, max_draw_h=2880, **_):
        registry.load_all()
        self.OW, self.OH, self.fps, self.dur = OW, OH, fps, dur
        desc = desc or {}
        self.desc = desc
        pal_name = desc.get("palette") or palette
        tod = desc.get("time_of_day", "dusk")
        # cảnh tự ghi bảng màu riêng thì dùng đúng bảng đó; không thì bảng của video được chỉnh theo giờ trong cảnh
        self.pal = palettes.get(pal_name) if desc.get("palette") else palettes.for_time(pal_name, tod)
        # phủ màu đêm chỉ khi cảnh tự chọn bảng màu không phải bảng đêm (bảng chỉnh theo giờ đã là màu đêm)
        self.night = tod == "night" and bool(desc.get("palette")) and pal_name not in ("dem_lua", "dem_trang")
        sp = canvas_spec(motion, OW, OH, supersample, max_draw_h=max_draw_h)
        cam_args = dict(focus=tuple(desc.get("focus", focus)), strength=float(desc.get("motion_strength", 1.0)))
        self.cam = Camera(motion, dur, sp, **cam_args)
        horizon = float(desc.get("horizon", 0.58))
        weather = desc.get("weather", "clear")
        c = Canvas(sp["W"], sp["H"], sp["vx0"], sp["vy0"], sp["vw"], sp["vh"], self.pal, desc.get("time_of_day", "dusk"),
                   horizon, seed=seed, weather=weather, country=country)
        self.c = c
        self.sprites = []
        self._build_background(desc, weather)
        self._build_elements(desc.get("elements", []), horizon, seed)
        self._finish_layers()
        # thu về độ phân giải làm việc
        r = sp["work"] / sp["S"]
        self.r = r
        self._rescale(r)
        wsp = {k: (v * r if k in ("W", "H", "vx0", "vy0", "vw", "vh") else v) for k, v in sp.items()}
        wsp["W"], wsp["H"] = int(round(wsp["W"])), int(round(wsp["H"]))
        self.sp = wsp
        self.cam = Camera(motion, dur, wsp, **cam_args)
        self.u = c.u * r
        # lửa tĩnh, hạt, lấp lánh, mũi tên
        self.static_fires = [(X * r, Y * r, rad * r, d) for (X, Y, rad, d) in c.fires + c.lamps]
        self._fires_out = []
        self._extra_emit_out = []
        self.emitters = [dict(e, at=(e["at"][0] * r, e["at"][1] * r)) for e in c.effects if e.get("type") == "emitter"]
        has_fire = bool(c.fires) or any(s.fires for s in self.sprites)
        parts = list(particles or [])
        auto = {"rain": "rain", "snow": "snow", "fog": "mist"}
        if weather in auto and auto[weather] not in parts:
            parts.append(auto[weather])
        if has_fire:
            for p in ("embers", "smoke"):
                if p not in [q.split(":")[0] for q in parts]:
                    parts.append(p)
        self.systems = []
        for i, name in enumerate(parts):
            name, _, inten = str(name).partition(":")
            if name not in KINDS:
                continue
            ems = []
            if name in ("embers", "smoke") and has_fire:
                ems.append(lambda t: self._fires_out)
            if name == "smoke" and self.emitters:
                ems.append(lambda t: self._extra_emit_out)
            self.systems.append(System(name, OW, OH, fps, seed=seed * 31 + i, emitters=ems, intensity=float(inten or 1.0),
                                       fog_col=self.pal["fog"], fire_col=self.pal["fire"]))
        if self.emitters and not any(s.kind == "smoke" for s in self.systems):
            self.systems.append(System("smoke", OW, OH, fps, seed=seed * 7, emitters=[lambda t: self._extra_emit_out],
                                       fog_col=self.pal["fog"]))
        self._warm = False
        self.shimmer = None
        sh = [e for e in c.effects if e.get("type") == "shimmer"]
        if sh:
            self._make_shimmer(sh[0]["color"], sh[0]["y0"] * r)
        self.arrows = [dict(e, src=(e["src"][0] * r, e["src"][1] * r), dst=(e["dst"][0] * r, e["dst"][1] * r), size=e["size"] * r)
                       for e in c.effects if e.get("type") == "arrows"]
        self.vig_strength = vignette_strength
        self.grain = grain
        self.fi = 0
        self._gcache = {}

    # ------------------------------------------------------------------ build
    def _build_background(self, desc, weather):
        c = self.c
        bg = list(desc.get("background") or ["sky", "mountains:3", "river"])
        names = [parse_token(t)[0] for t in bg]
        if "sky" not in names:
            bg.insert(0, "sky")
        if weather in ("cloudy", "overcast", "rain") and "clouds" not in names:
            bg.insert(1, "clouds:9")
        if weather == "fog" and "mist_band" not in names:
            bg.append("mist_band")
        for tok in bg:
            name, p = parse_token(tok)
            comp = registry.get(name)
            if comp is None:
                raise ValueError(f"Nền '{name}' không có trong thư viện")
            comp.func(c, 0.5, 0.5, float(p.pop("scale", 1.0)), 0.0, **p)

    def _build_elements(self, elements, horizon, seed):
        c = self.c
        insts = []
        for ei, el in enumerate(elements):
            comp = registry.get(el.get("kind"))
            if comp is None:
                raise ValueError(f"Thành phần '{el.get('kind')}' không có trong thư viện")
            params = {k: v for k, v in el.items() if k not in ("kind", "x", "y", "scale", "count", "spacing", "layer", "move")}
            for j, (x, y, sc) in enumerate(expand(el, comp, horizon, seed * 100 + ei)):
                d = depth_for(y, horizon, el.get("layer"))
                insts.append((d, y, ei, j, comp, x, sc, params, el.get("move")))
        insts.sort(key=lambda r: (r[0], r[1], r[2], r[3]))
        for d, y, ei, j, comp, x, sc, params, move in insts:
            anim = comp.anim
            if move and anim is None:
                anim = "move"
            if anim is None:
                c.use(d)
                _safe_draw(comp, c, x, y, sc, 0.0, params)
                continue
            mv = (float(move[0]) * c.vw, float(move[1]) * c.vh) if move else (0.0, 0.0)
            nf = len(c.fires)
            phase = random.Random(ei * 13 + j).uniform(0, 6.28)
            if anim == "redraw":
                bw = comp.bbox[0] * c.u * sc * 1.4 + 20
                bh = comp.bbox[1] * c.u * sc * 1.25 + 20
                ox = c.px(x) - bw / 2
                oy = c.py(y) - bh * 0.9
                sub = Image.new("RGBA", (int(bw), int(bh)), (0, 0, 0, 0))
                c.set_target(sub, d, ox, oy)
                ok = _safe_draw(comp, c, x, y, sc, 0.0, params)
                fires = [(fx - ox, fy - oy, r) for fx, fy, r, _ in c.fires[nf:]]
                del c.fires[nf:]
                c.ox = c.oy = 0
                if not ok:
                    continue
                self.sprites.append(Sprite(sub, ox, oy, d, "redraw", phase=phase, move=mv, fires=fires,
                                           redraw=(comp.func, x, y, sc, params, sub.size, ox, oy)))
                continue
            tmp = Image.new("RGBA", (c.W, c.H), (0, 0, 0, 0))
            c.set_target(tmp, d)
            _safe_draw(comp, c, x, y, sc, 0.0, params)
            bb = tmp.getbbox()
            if not bb:
                continue
            pad = int(0.04 * max(bb[2] - bb[0], bb[3] - bb[1])) + 4
            bb = (max(0, bb[0] - pad), max(0, bb[1] - pad), min(c.W, bb[2] + pad), min(c.H, bb[3] + pad))
            fires = [(fx - bb[0], fy - bb[1], r) for fx, fy, r, _ in c.fires[nf:]]
            del c.fires[nf:]
            self.sprites.append(Sprite(tmp.crop(bb), bb[0], bb[1], d, anim, phase=phase, move=mv, fires=fires))
        c.img = None

    def _finish_layers(self):
        c = self.c
        for e in c.effects:
            dk = round(e.get("depth", -1), 3)
            if e.get("type") == "blur_layer" and dk in c.layers:
                c.layers[dk] = c.layers[dk].filter(ImageFilter.GaussianBlur(e["radius"]))
        if self.night:
            for k, im in list(c.layers.items()):
                c.layers[k] = _tint(im)
            for s in self.sprites:
                s.img = _tint(s.img)
        drifts = {round(e["depth"], 3): e["speed"] for e in c.effects if e.get("type") == "drift"}
        self.items = []
        depths = sorted(set(list(c.layers.keys()) + [s.depth for s in self.sprites]))
        sens = self.cam.depth_sensitive
        for dpt in depths:
            if dpt in c.layers:
                im = c.layers[dpt]
                if im.getbbox():
                    dr = drifts.get(dpt, 0.0)
                    last = self.items[-1] if self.items else None
                    # gộp các lớp tĩnh liền nhau khi camera không phụ thuộc độ sâu
                    if last and last[0] == "layer" and not dr and not last[3] and (not sens or last[1] == dpt):
                        last[2].alpha_composite(im)
                    else:
                        self.items.append(["layer", dpt, im, dr])
                    if dpt == 0.5:
                        self.items.append(["shimmer", 0.5, None, 0.0])
            for s in self.sprites:
                if s.depth == dpt:
                    self.items.append(["sprite", dpt, s, 0.0])
        c.layers = {}

    def _rescale(self, r):
        if abs(r - 1) < 1e-3:
            self._crop_layers()
            return
        for it in self.items:
            if it[0] == "layer":
                im = it[2]
                it[2] = im.resize((max(1, round(im.width * r)), max(1, round(im.height * r))), Image.LANCZOS)
                it[3] *= r
        # lớp nền đầu tiên (bầu trời) luôn kín -> lưu RGB cho nhanh
        if self.items and self.items[0][0] == "layer":
            self.items[0][2] = self.items[0][2].convert("RGB")
        for s in self.sprites:
            if s.redraw is None:
                s.img = s.img.resize((max(1, round(s.img.width * r)), max(1, round(s.img.height * r))), Image.LANCZOS)
            s.X, s.Y = s.X * r, s.Y * r
            s.move = (s.move[0] * r, s.move[1] * r)
            s.fires = [(fx * r, fy * r, rad * r) for fx, fy, rad in s.fires]
        self._crop_layers()

    def _crop_layers(self):
        """Cắt mỗi lớp trong suốt theo vùng thật sự có hình (núi, bờ, cỏ lau... chỉ là một dải):
        mỗi khung chỉ phải dán / phóng phần nhỏ đó thay vì cả khung."""
        for it in self.items:
            if it[0] != "layer":
                continue
            im = it[2]
            off = (0, 0)
            if im.mode == "RGBA":
                bb = im.getchannel("A").getbbox()
                if bb and (bb[2] - bb[0]) * (bb[3] - bb[1]) < im.width * im.height * 0.9:
                    im = im.crop(bb)
                    off = (bb[0], bb[1])
            it[2] = im
            if len(it) == 4:
                it.append(off)
            else:
                it[4] = off

    def _make_shimmer(self, col, y0):
        OW, OH = self.OW, self.OH
        rr = random.Random(10)
        col = tuple(col)
        k = OW / 1920.0
        layers = []
        for s in range(2):
            w = OW + int(900 * k)
            im = Image.new("RGBA", (w, OH), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            for _ in range(int(420 * k * k) + 100):
                y = rr.uniform(4, OH)
                t = y / OH
                x = rr.uniform(0, w)
                d.line([(x, y), (x + rr.uniform(30, 140) * k * (.4 + t), y)], fill=col + (int(rr.uniform(60, 170) * (1 - .5 * t)),),
                       width=max(1, int((1 + 3 * t) * k)))
            layers.append((im.convert("RGB"), im.getchannel("A")))
        self.shimmer = (layers, y0)

    # ------------------------------------------------------------------ per-frame
    def _sprite_pos(self, s, t):
        dx = s.move[0] * (t / self.dur)
        dy = s.move[1] * (t / self.dur)
        ang = 0.0
        if s.anim == "bob":
            dy += 5 * self.u * math.sin(t * 1.3 + s.phase)
            ang = 0.9 * math.sin(t * 1.05 + s.phase * 1.7)
        elif s.anim == "move":
            dy -= 2 * self.u * abs(math.sin(t * 4 + s.phase))
        return s.X + dx, s.Y + dy, ang

    def _draw_sprite(self, frame, s, t, box):
        k = self.OW / (box[2] - box[0])
        X, Y, ang = self._sprite_pos(s, t)
        if s.redraw and getattr(s, "_last", None) and t - s._last[0] < 1 / 15 - 1e-6 and s._last[1] == k:
            img = s._last[2]                    # cờ / lửa vẽ lại 15 lần mỗi giây là đủ mượt
        elif s.redraw:
            func, x, y, sc, params, size, dox, doy = s.redraw
            sub = Image.new("RGBA", size, (0, 0, 0, 0))
            c = self.c
            nf, ne = len(c.fires), len(c.effects)
            c.set_target(sub, s.depth, dox, doy)
            try:
                func(c, x, y, sc, t + s.phase, **params)
            except Exception:
                pass                       # lỗi đã báo lúc dựng nền; khung này để trống phần đó
            del c.fires[nf:]
            del c.effects[ne:]
            c.ox = c.oy = 0
            if self.night:
                sub = _tint(sub)
            kk = k * self.r
            img = sub.resize((max(1, int(sub.width * kk)), max(1, int(sub.height * kk))), Image.BILINEAR)
            s._last = (t, k, img)
        else:
            ck, cimg = s._cache
            if ck is None or abs(ck - k) / k > 0.008:
                cimg = s.img if abs(k - 1) < 1e-3 else s.img.resize(
                    (max(1, int(s.img.width * k)), max(1, int(s.img.height * k))), Image.BILINEAR)
                s._cache = (k, cimg)
            img = cimg
            if abs(ang) > 0.05:
                img = img.rotate(ang, resample=Image.BILINEAR)
        safe_composite(frame, img, (X - box[0]) * k, (Y - box[1]) * k)
        for (fx, fy, r) in s.fires:
            self._fires_out.append(((X + fx - box[0]) * k, (Y + fy - box[1]) * k, r * k))

    def _paste_layer(self, frame, im, off, box):
        """Dán phần lớp (đã cắt, nằm ở off trong canvas) rơi vào khung nhìn box, co giãn nếu camera zoom."""
        OW, OH = self.OW, self.OH
        ox, oy = off
        w, h = im.size
        sx = OW / (box[2] - box[0])
        sy = OH / (box[3] - box[1])
        mask = im if im.mode == "RGBA" else None
        if abs(sx - 1) < 1e-3 and abs(sy - 1) < 1e-3:      # chỉ trượt: cắt nguyên pixel, không co giãn
            x0, y0 = int(round(box[0])), int(round(box[1]))
            cx0, cy0 = max(0, x0 - ox), max(0, y0 - oy)
            cx1, cy1 = min(w, x0 + OW - ox), min(h, y0 + OH - oy)
            if cx1 <= cx0 or cy1 <= cy0:
                return
            part = im.crop((cx0, cy0, cx1, cy1))
            frame.paste(part, (ox + cx0 - x0, oy + cy0 - y0), part if mask else None)
            return
        # zoom: tính vùng xuất (nguyên pixel) tương ứng phần lớp, phóng đúng phần đó
        X0 = max(0, math.floor((ox - box[0]) * sx))
        Y0 = max(0, math.floor((oy - box[1]) * sy))
        X1 = min(OW, math.ceil((ox + w - box[0]) * sx))
        Y1 = min(OH, math.ceil((oy + h - box[1]) * sy))
        if X1 <= X0 or Y1 <= Y0:
            return
        lx0 = min(max(0.0, box[0] + X0 / sx - ox), w)
        ly0 = min(max(0.0, box[1] + Y0 / sy - oy), h)
        lx1 = min(max(0.0, box[0] + X1 / sx - ox), w)
        ly1 = min(max(0.0, box[1] + Y1 / sy - oy), h)
        if lx1 <= lx0 or ly1 <= ly0:
            return
        part = im.resize((X1 - X0, Y1 - Y0), Image.BILINEAR, box=(lx0, ly0, lx1, ly1))
        frame.paste(part, (X0, Y0), part if mask else None)

    def compose(self, t):
        OW, OH = self.OW, self.OH
        frame = Image.new("RGB", (OW, OH))
        self._fires_out = []
        item_off = {id(it[2]): (it[4] if len(it) > 4 else (0, 0)) for it in self.items if it[0] == "layer"}
        for it in self.items:
            kind, depth, obj, drift = it[:4]
            box = self.cam.box(t, depth, drift)
            if kind == "layer":
                self._paste_layer(frame, obj, item_off[id(obj)], box)
            elif kind == "sprite":
                self._draw_sprite(frame, obj, t, box)
            elif kind == "shimmer" and self.shimmer:
                layers, y0 = self.shimmer
                _, yo = self.cam.to_out(0, y0, box, OW, OH)
                yo = int(max(0, yo))
                if yo >= OH:
                    continue
                for k_, (rgb, alpha) in enumerate(layers):
                    a = .5 + .5 * math.sin(t * 2.2 + k_ * math.pi)
                    off = int((t * 25 * OW / 1920 + k_ * 300 * OW / 1920) % (rgb.width - OW))
                    box_ = (off, 0, off + OW, OH - yo)
                    lv = int(round(a * 12))           # độ mờ lấp lánh lượng tử 13 mức -> bảng tra tính sẵn
                    if lv == 0:
                        continue
                    frame.paste(rgb.crop(box_), (0, yo), alpha.crop(box_).point(_ALPHA_LUT[lv]))
        for (X, Y, rad, depth) in self.static_fires:
            b = self.cam.box(t, depth)
            k = OW / (b[2] - b[0])
            self._fires_out.append(((X - b[0]) * k, (Y - b[1]) * k, rad * k))
        self._extra_emit_out = []
        for e in self.emitters:
            b = self.cam.box(t, e["depth"])
            k = OW / (b[2] - b[0])
            X, Y = e["at"]
            self._extra_emit_out.append(((X - b[0]) * k, (Y - b[1]) * k, 120 * e.get("size", 1) * OW / 1920))
        if self.arrows:
            self._draw_arrows(frame, t)
        return frame

    def _draw_arrows(self, frame, t):
        d = ImageDraw.Draw(frame)
        for e in self.arrows:
            box = self.cam.box(t, e["depth"])
            k = self.OW / (box[2] - box[0])
            sx, sy = self.cam.to_out(*e["src"], box, self.OW, self.OH)
            tx, ty = self.cam.to_out(*e["dst"], box, self.OW, self.OH)
            rr = random.Random(5)
            arc = 0.28 * self.OH
            L = e["size"] * k
            col = tuple(e["col"][:3])
            for i in range(e["n"]):
                delay = rr.uniform(0, 0.7)
                jx, jy = rr.uniform(-40, 40) * k, rr.uniform(-25, 25) * k
                u = (t - e["start"] - delay) / e["dur"]
                if not 0 < u < 1:
                    continue
                x = sx + (tx - sx) * u + jx
                y = sy + (ty - sy) * u - arc * 4 * u * (1 - u) + jy
                vx = (tx - sx)
                vy = (ty - sy) - arc * 4 * (1 - 2 * u)
                n = math.hypot(vx, vy) or 1
                d.line([(x - vx / n * L, y - vy / n * L), (x, y)], fill=col, width=max(1, int(2 * self.OW / 1920)))

    def frame(self, t):
        """Khung hình tại t (ảnh RGB). Phải gọi lần lượt t tăng dần (hạt được mô phỏng theo thời gian)."""
        if not self._warm:
            self._warm = True
            self.compose(0)
            for s in self.systems:
                if s.kind in ("embers", "smoke", "sparks", "dust"):
                    s.warm(1.3)
        im = self.compose(t)
        for i, (fx, fy, r) in enumerate(self._fires_out):
            fl = .75 + .18 * math.sin(t * 11 + i * 2) + .1 * math.sin(t * 23 + i * 5) + .05 * math.sin(t * 37 + i)
            add_image(im, self._glow_for(r, fl), fx, fy)
        for s in self.systems:
            s.step(t)
            im = s.apply(im, t)
        return finish_frame(im, self.vig_strength, self.grain)

    def _glow_for(self, r, fl=1.0):
        key = max(4, int(r / 6) * 6 + 6)
        level = round(min(1.15, max(0.5, fl)) * 10) / 10      # 8 mức chập chờn, tính sẵn
        return glow_image(key, tuple(self.pal["fire"]), (255, 220, 120), level)


def _safe_draw(comp, c, x, y, sc, t, params):
    """Vẽ một thành phần; nếu lỗi (vd tham số AI ghi sai trong plan.json) thì bỏ qua RIÊNG thành phần đó
    và báo trong nhật ký, không làm hỏng cả cảnh / cả video."""
    try:
        comp.func(c, x, y, sc, t, **params)
        return True
    except Exception as e:
        print(f"   ⚠️  bỏ qua thành phần '{comp.name}' (tham số {params}): {type(e).__name__}: {e}", flush=True)
        return False


_ALPHA_LUT = [[int(v * i / 12) for v in range(256)] for i in range(13)]


def _tint(im):
    a = np.asarray(im).astype(np.float32)
    a[..., :3] *= NIGHT_TINT
    return Image.fromarray(a.clip(0, 255).astype(np.uint8), im.mode)
