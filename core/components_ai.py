"""Cảnh đặc biệt (mục 5.3): khi plan.json cần thứ thư viện chưa có, AI VIẾT MỚI một hàm vẽ thành phần
(Python + Pillow/numpy) theo đúng chuẩn thư viện, lưu vào assets_code/custom/ để dùng lại.

An toàn:
  - AI chỉ trả về MÃ NGUỒN dạng văn bản (không được cấp quyền ghi file / chạy lệnh). Tool tự ghi file vào
    assets_code/custom/ — đây là thư mục duy nhất được ghi.
  - Kiểm tra mã bằng AST: chỉ cho import math, random, numpy, PIL và các module trong assets_code / render.common;
    cấm open, exec, eval, __import__, os, sys, subprocess, socket, requests... (không đọc/ghi file, không gọi mạng).
  - Hàm mới ở trạng thái "pending" cho tới khi xem trước (preview) và duyệt (approve).
"""
import ast
import importlib
import json
import os
import re

from PIL import Image

from assets_code import registry
from core.config import ROOT

CUSTOM_DIR = os.path.join(ROOT, "assets_code", "custom")
ALLOWED_IMPORTS = {"math", "random", "numpy", "PIL", "PIL.Image", "PIL.ImageDraw", "PIL.ImageFilter", "assets_code.registry",
                   "assets_code.common.shapes", "assets_code.common.shiputil", "assets_code.common.elements", "render.common"}
BANNED_NAMES = {"open", "exec", "eval", "compile", "__import__", "globals", "locals", "vars", "getattr", "setattr", "delattr",
                "input", "breakpoint", "exit", "quit", "help", "memoryview"}
BANNED_ATTRS = {"system", "popen", "remove", "unlink", "rmtree", "save", "load", "tofile", "fromfile", "__globals__",
                "__builtins__", "__subclasses__", "__class__", "__bases__", "__mro__", "__code__", "f_globals"}

PROMPT = """Viết MỘT hàm Python vẽ thành phần mới cho thư viện hình minh họa lịch sử (phong cách tranh phẳng, BÓNG,
nhiều lớp, như các thành phần có sẵn). Thành phần cần vẽ: "{desc}" (tên: {name}, nước: {country}).

CHUẨN BẮT BUỘC (xem ví dụ):
- Khai báo bằng decorator:
    @component("{name}", category="<ship|building|people|element|effect>", desc="<mô tả tiếng Việt>", y_default=<0..1>,
               era=(<năm từ>, <năm đến>), params={{"tên_tham_số": "giải thích"}}, anim=None|"bob")
    def draw_{name}(c, x, y, scale, t, **p):
- c là Canvas: c.px(x), c.py(y) đổi toạ độ tỉ lệ 0–1 sang pixel; c.u = số pixel ứng với 1px ở khung 1080p
  (kích thước phải nhân c.u * scale); c.d là ImageDraw để vẽ; c.pal là bảng màu (dict: "sil", "wood", "sail", "stone",
  "roof", "flag_ally", "flag_enemy", "fire", "ground": [2 màu], "mount": [3 màu], "sky": [3 màu]); màu RGB tuple + (255,).
  c.add_fire(px, py, r) để thêm điểm lửa (ánh sáng + tàn lửa) khi state == "burning".
- (x, y) = tâm ngang và điểm chạm đất / nước của vật. Toạ độ ra ngoài khung cũng được.
- CHỈ import: math, random, numpy as np, from PIL import Image, ImageDraw, ImageFilter,
  from assets_code.registry import component, from assets_code.common.shapes import figure, horse, flag_points, stake,
  from assets_code.common.shiputil import ship_on_tmp, burning_flames, from render.common import mix, lerp.
- KHÔNG đọc/ghi file, KHÔNG gọi mạng, KHÔNG dùng os/sys/subprocess/open/eval/exec.
- Người/ngựa vẽ dạng bóng đơn giản, không cận mặt. Đúng lịch sử nước {country}.

VÍ DỤ THÀNH PHẦN CÓ SẴN:
```python
{example}
```

CHỈ trả về JSON: {{"code": "<toàn bộ mã nguồn module>", "notes": "<ghi chú ngắn>"}}
"""


def check_code(code):
    """Kiểm tra AST; trả về danh sách lỗi (rỗng = an toàn)."""
    errs = []
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [f"Lỗi cú pháp: {e}"]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name not in ALLOWED_IMPORTS:
                    errs.append(f"Không được import '{a.name}'")
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "") not in ALLOWED_IMPORTS:
                errs.append(f"Không được import từ '{node.module}'")
        elif isinstance(node, ast.Name) and node.id in BANNED_NAMES:
            errs.append(f"Không được dùng '{node.id}'")
        elif isinstance(node, ast.Attribute) and (node.attr in BANNED_ATTRS or node.attr.startswith("__")):
            errs.append(f"Không được dùng thuộc tính '.{node.attr}'")
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            errs.append("Không được dùng global / nonlocal")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and re.search(r"(\.\./|[A-Za-z]:\\|/etc/|https?://)", node.value):
            errs.append("Có chuỗi giống đường dẫn file / địa chỉ mạng")
    if "@component(" not in code:
        errs.append("Thiếu decorator @component(...)")
    return sorted(set(errs))


def write_component(router, name, desc, country="custom", log=print):
    name = re.sub(r"[^a-z0-9_]", "_", name.lower()).strip("_")
    with open(os.path.join(ROOT, "assets_code", "vietnam", "components.py"), encoding="utf-8") as f:
        src = f.read()
    m = re.search(r'@component\("dinh_roof".*?(?=\n\n\n)', src, re.S)
    example = m.group(0) if m else ""
    prompt = PROMPT.format(name=name, desc=desc, country=country, example=example)

    def validator(d):
        errs = check_code(d.get("code", ""))
        if not errs and f'"{name}"' not in d["code"]:
            errs.append(f'Tên thành phần trong @component phải là "{name}"')
        return errs

    log(f"🧩 Nhờ AI viết thành phần mới '{name}'...")
    data = router.ask("planner", prompt, schema={"type": "object", "required": ["code"]}, validator=validator)
    path = os.path.join(CUSTOM_DIR, f"{name}.py")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f'"""Thành phần do AI viết: {desc} (nước: {country}). Trạng thái xem assets_code/custom/status.json."""\n')
        f.write(data["code"].strip() + "\n")
    st = registry.custom_status()
    st[name] = {"status": "pending", "desc": desc, "country": country, "notes": data.get("notes", "")}
    registry.save_custom_status(st)
    log(f"   ✔ đã lưu {path} (trạng thái: chờ duyệt)")
    return name, path


def preview_component(name, out_path, palette="hoang_hon_do"):
    """Vẽ thử thành phần trên nền mẫu (3 kích thước, có state burning nếu hỗ trợ). Lỗi -> ném ngoại lệ."""
    path = os.path.join(CUSTOM_DIR, f"{name}.py")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            errs = check_code(f.read())
        if errs:
            raise RuntimeError("Mã không an toàn: " + "; ".join(errs))
        mod = importlib.import_module(f"assets_code.custom.{name}")
        importlib.reload(mod)
    comp = registry.REGISTRY.get(name)
    if comp is None:
        raise RuntimeError(f"Không tìm thấy thành phần '{name}' sau khi nạp")
    from render.scene import SceneVisual
    import numpy as np
    bg = ["sky", "mountains:2", "sea"] if comp.category == "ship" else ["sky", "hills:2", "plain"]
    y = comp.y_default
    desc = {"time_of_day": "dusk", "background": bg,
            "elements": [{"kind": name, "x": 0.22, "y": y, "scale": 0.6}, {"kind": name, "x": 0.52, "y": y, "scale": 1.0},
                         {"kind": name, "x": 0.82, "y": y, "scale": 0.8, "state": "burning"}]}
    v = SceneVisual(desc, 1280, 720, 10, 2.0, palette=palette, motion="static")
    a = v.frame(1.0)
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    arr = np.asarray(img).astype(np.int32)
    v2 = SceneVisual(dict(desc, elements=[]), 1280, 720, 10, 2.0, palette=palette, motion="static")
    empty = np.clip(v2.frame(1.0), 0, 255).astype(np.int32)
    diff = np.abs(arr - empty).mean()
    img.save(out_path, quality=90)
    return diff > 0.5


def approve(name):
    st = registry.custom_status()
    if name not in st:
        raise RuntimeError(f"Không có thành phần chờ duyệt tên '{name}'")
    st[name]["status"] = "approved"
    registry.save_custom_status(st)
