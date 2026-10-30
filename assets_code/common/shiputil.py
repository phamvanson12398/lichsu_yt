"""Tiện ích vẽ thuyền trên lớp tạm rồi xoay (nghiêng / mắc cạn), dùng cho mọi bộ nước."""
import math

from PIL import Image, ImageDraw


def ship_on_tmp(c, X, Y, s, tilt, draw_fn, size=(900, 900), anchor=(450, 700), fires=()):
    """draw_fn(d, ox, oy, s) vẽ thuyền với tâm đường nước ở (ox, oy) trên ảnh tạm, rồi xoay + dán vào canvas.

    fires: danh sách (dx, dy, r) theo đơn vị thuyền (nhân s) — ghi điểm lửa để có ánh sáng + tàn lửa.
    """
    W, H = int(size[0] * s) + 4, int(size[1] * s) + 4
    tmp = Image.new("RGBA", (max(4, W), max(4, H)), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    ox, oy = anchor[0] * s, anchor[1] * s
    draw_fn(d, ox, oy, s)
    if tilt:
        tmp = tmp.rotate(tilt, resample=Image.BICUBIC, center=(ox, oy))
    c.composite(tmp, X - ox, Y - oy)
    a = math.radians(-tilt or 0)
    for dx, dy, r in fires:
        fx = dx * s * math.cos(a) - dy * s * math.sin(a)
        fy = dx * s * math.sin(a) + dy * s * math.cos(a)
        c.add_fire(X + fx, Y + fy, r * s)


def burning_flames(d, pts, s, col=(255, 110, 25), core=(255, 220, 120)):
    """Ngọn lửa tĩnh trên thuyền (ánh sáng chập chờn do renderer cộng thêm)."""
    for (x, y, r) in pts:
        r *= s
        d.polygon([(x - r * 0.7, y), (x - r * 0.4, y - r * 1.2), (x - r * 0.1, y - r * 0.7), (x, y - r * 1.9),
                   (x + r * 0.25, y - r * 0.8), (x + r * 0.5, y - r * 1.3), (x + r * 0.7, y)], fill=col + (235,))
        d.polygon([(x - r * 0.35, y), (x - r * 0.15, y - r * 0.8), (x, y - r * 1.2), (x + r * 0.2, y - r * 0.7),
                   (x + r * 0.35, y)], fill=core + (240,))
