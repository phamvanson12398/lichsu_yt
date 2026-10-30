"""Thư viện thành phần vẽ bằng code (mục 5.2 + 10).

Chuẩn hàm thành phần:
    draw_<ten>(canvas, x, y, scale, t, **params)
  - canvas : đối tượng Canvas bên dưới (ảnh lớp hiện tại ở canvas.img, bút vẽ canvas.d)
  - x, y   : toạ độ tỉ lệ 0-1 theo khung hình (x = tâm, y = điểm chạm nước / mặt đất)
  - scale  : tỉ lệ (1.0 = kích thước chuẩn ghi trong mô tả)
  - t      : thời gian (giây), để thành phần tự chuyển động khi được vẽ lại từng khung
  - params : tham số riêng (state="burning"/"broken", tilt, flip, color, density...)

Đăng ký bằng decorator @component(...). Mỗi module nước có danh sách thành phần + mô tả
để AI biết được dùng gì (xem catalog_text()).
"""
import importlib
import json
import os
import pkgutil
import random
from dataclasses import dataclass, field

from PIL import Image, ImageDraw

ASSETS_DIR = os.path.dirname(os.path.abspath(__file__))
COUNTRY_PACKAGES = ["common", "vietnam", "china", "korea", "japan", "england", "custom"]


@dataclass
class Comp:
    name: str
    func: object
    country: str = "common"
    category: str = "element"         # background | element | ship | building | people | effect
    desc: str = ""
    y_default: float = 0.7
    scale_default: float = 1.0
    anim: str = None                  # None | bob | sway | redraw (vẽ lại từng khung với t)
    era: tuple = (-3000, 2100)        # khoảng năm phù hợp lịch sử
    params: dict = field(default_factory=dict)
    bbox: tuple = (400, 400)          # khung bao (px ở 1080p, scale=1) — cho thành phần vẽ lại từng khung
    spacing: float = 0.14             # khoảng cách mặc định khi count > 1 (tỉ lệ khung)
    module: str = ""


REGISTRY = {}


def component(name, **meta):
    def deco(fn):
        meta.setdefault("module", fn.__module__)
        if "country" not in meta:
            parts = fn.__module__.split(".")
            meta["country"] = parts[1] if len(parts) > 2 else "common"
        REGISTRY[name] = Comp(name=name, func=fn, **meta)
        return fn
    return deco


_loaded = False


def load_all(include_pending=False):
    """Nạp mọi module thành phần. Thành phần AI viết (custom) chỉ nạp khi đã duyệt."""
    global _loaded
    if _loaded and not include_pending:
        return REGISTRY
    approved = custom_status()
    for pkg in COUNTRY_PACKAGES:
        pdir = os.path.join(ASSETS_DIR, pkg)
        if not os.path.isdir(pdir):
            continue
        for m in pkgutil.iter_modules([pdir]):
            if pkg == "custom":
                st = approved.get(m.name, {}).get("status")
                if st != "approved" and not include_pending:
                    continue
            importlib.import_module(f"assets_code.{pkg}.{m.name}")
    _loaded = True
    return REGISTRY


def custom_status():
    p = os.path.join(ASSETS_DIR, "custom", "status.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_custom_status(st):
    p = os.path.join(ASSETS_DIR, "custom", "status.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=2)


def get(name):
    load_all()
    return REGISTRY.get(name)


def names(category=None):
    load_all()
    return [k for k, v in REGISTRY.items() if category is None or v.category == category]


def catalog_text(countries=None):
    """Danh sách thành phần + mô tả để đưa cho AI khi lập plan.json."""
    load_all()
    lines = []
    by = {}
    for c in REGISTRY.values():
        by.setdefault(c.country, []).append(c)
    for country in COUNTRY_PACKAGES:
        if country not in by or (countries and country not in countries and country != "common"):
            continue
        lines.append(f"## {country}")
        for c in sorted(by[country], key=lambda c: (c.category, c.name)):
            era = "" if c.era == (-3000, 2100) else f" [năm {c.era[0]}–{c.era[1]}]"
            ps = ", ".join(f"{k}: {v}" for k, v in c.params.items())
            lines.append(f"- {c.name} ({c.category}){era}: {c.desc}" + (f" | tham số: {ps}" if ps else ""))
    return "\n".join(lines)


# ======================================================================
class Canvas:
    """Vùng vẽ của một cảnh. Ảnh các lớp có kích thước W x H (có lề cho camera).

    Khung nhìn chuẩn (x,y = 0..1) nằm ở (vx0, vy0, vw, vh) trong toạ độ canvas.
    canvas.u = số pixel ứng với 1 pixel ở khung 1080p (để thành phần tự co giãn).
    """

    def __init__(self, W, H, vx0, vy0, vw, vh, palette, time_of_day="dusk", horizon=0.58, seed=1,
                 weather="clear", country="vietnam"):
        self.W, self.H = int(W), int(H)
        self.vx0, self.vy0, self.vw, self.vh = vx0, vy0, vw, vh
        self.u = vh / 1080.0
        self.pal = palette
        self.tod = time_of_day
        self.weather = weather
        self.country = country
        self.horizon = horizon
        self.seed = seed
        self.rng = random.Random(seed)
        self.layers = {}
        self.img = None
        self.d = None
        self.depth = 0.5
        self.fires = []      # (px, py, r, depth)
        self.effects = []    # {"type": "shimmer", ...}
        self.ox = 0
        self.oy = 0

    # toạ độ ------------------------------------------------------
    def px(self, x):
        return self.vx0 + x * self.vw - self.ox

    def py(self, y):
        return self.vy0 + y * self.vh - self.oy

    def hz(self):
        return self.py(self.horizon)

    @property
    def left(self):
        return -self.ox

    @property
    def right(self):
        return self.W - self.ox

    @property
    def bottom(self):
        return self.H - self.oy

    # lớp ---------------------------------------------------------
    def layer(self, depth):
        depth = round(float(depth), 3)
        if depth not in self.layers:
            self.layers[depth] = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        return self.layers[depth]

    def use(self, depth):
        self.depth = round(float(depth), 3)
        self.img = self.layer(self.depth)
        self.d = ImageDraw.Draw(self.img)
        return self.d

    def set_target(self, img, depth, ox=0, oy=0):
        self.img = img
        self.d = ImageDraw.Draw(img)
        self.depth = depth
        self.ox, self.oy = ox, oy

    # hiệu ứng ----------------------------------------------------
    def add_fire(self, px, py, r):
        self.fires.append((px + self.ox, py + self.oy, r, self.depth))

    def add_effect(self, **kw):
        self.effects.append(kw)

    def composite(self, sprite, px, py):
        """Dán ảnh RGBA lên lớp hiện tại (px,py = góc trên trái theo toạ độ canvas)."""
        from render.common import safe_composite
        safe_composite(self.img, sprite, px, py)
