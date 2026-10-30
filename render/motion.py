"""Chuyển động cảnh (mục 6.1): zoom_in_slow / zoom_out_slow / pan_left / pan_right (Ken Burns),
parallax_left / parallax_right (mỗi lớp trôi tốc độ khác nhau), static.

Camera.box(t, depth) trả về vùng (x0, y0, x1, y1) trong toạ độ canvas cần lấy ra cho khung xuất.
"""
import math

MOTIONS = ["static", "zoom_in_slow", "zoom_out_slow", "pan_left", "pan_right", "parallax_left", "parallax_right",
           "zoom_in_fast"]


def canvas_spec(motion, OW, OH, supersample=2.0, max_draw_h=2880):
    """Kích thước canvas vẽ (2x để không vỡ hình) + độ phân giải làm việc sau khi thu nhỏ.

    work = 1.3 cho cảnh có zoom (đủ nét khi phóng 12-25%), 1.0 cho cảnh trượt / tĩnh.
    """
    if motion in ("zoom_in_slow", "zoom_out_slow", "zoom_in_fast"):
        work, m = (1.3 if motion == "zoom_in_fast" else 1.2), 0.04
    elif motion in ("pan_left", "pan_right", "parallax_left", "parallax_right"):
        work, m = 1.0, 0.11
    else:
        work, m = 1.0, 0.03
    # vẽ ở 2x; với khung 1440p / 4K giới hạn chiều cao vẽ (~2880px) để không tốn quá nhiều bộ nhớ
    S = max(work, min(float(supersample), max_draw_h / OH))
    vw, vh = OW * S, OH * S
    CW, CH = int(round(vw * (1 + 2 * m))), int(round(vh))
    return {"S": S, "work": work, "W": CW, "H": CH, "vx0": vw * m, "vy0": 0.0, "vw": vw, "vh": vh, "margin": m}


def _ease(u):
    u = min(max(u, 0.0), 1.0)
    return 0.5 - 0.5 * math.cos(math.pi * u)


class Camera:
    def __init__(self, motion, dur, spec, focus=(0.5, 0.5), strength=1.0):
        self.motion = motion or "static"
        self.dur = max(0.1, float(dur))
        self.sp = spec
        self.focus = focus
        self.strength = float(strength)
        self.aspect = spec["vh"] / spec["vw"]

    @property
    def depth_sensitive(self):
        return self.motion.startswith("parallax")

    def zoom(self, t):
        u = _ease(t / self.dur)
        a = 0.12 * self.strength
        if self.motion == "zoom_in_slow":
            return 1.0 + a * u
        if self.motion == "zoom_in_fast":
            return 1.0 + 0.25 * self.strength * u
        if self.motion == "zoom_out_slow":
            return 1.0 + a * (1 - u)
        if self.motion in ("pan_left", "pan_right"):
            return 1.0
        return 1.0

    def box(self, t, depth=0.5, drift=0.0):
        sp = self.sp
        vw, vh = sp["vw"], sp["vh"]
        z = self.zoom(t)
        w, h = vw / z, vh / z
        cx = sp["vx0"] + vw * 0.5
        cy = sp["vy0"] + vh * 0.5
        if z > 1.0001 and self.motion.startswith("zoom"):
            fx, fy = self.focus
            # dịch tâm về điểm lấy nét theo mức zoom
            k = (1 - 1 / z)
            cx += (fx - 0.5) * vw * k
            cy += (fy - 0.5) * vh * k
        u = _ease(t / self.dur) - 0.5
        if self.motion in ("pan_left", "pan_right", "parallax_left", "parallax_right"):
            P = vw * (0.14 if self.motion.startswith("parallax") else 0.12) * self.strength
            sign = 1 if self.motion.endswith("right") else -1
            dk = depth if self.motion.startswith("parallax") else 0.75
            cx += sign * P * u * dk
        if drift:
            cx -= drift * t
        x0, y0 = cx - w / 2, cy - h / 2
        x0 = min(max(x0, 0.0), sp["W"] - w)
        y0 = min(max(y0, 0.0), sp["H"] - h)
        return (x0, y0, x0 + w, y0 + h)

    def to_out(self, X, Y, box, OW, OH):
        x0, y0, x1, y1 = box
        return (X - x0) * OW / (x1 - x0), (Y - y0) * OH / (y1 - y0)
