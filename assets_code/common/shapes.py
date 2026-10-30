"""Hình dáng dùng chung: bóng người (nhiều kiểu mũ, vũ khí), ngựa, cờ, cọc gỗ, mái chèo.

Người / ngựa vẽ dạng BÓNG (silhouette) đơn giản, nhìn từ xa, không vẽ mặt.
"""
import math


def _poly(d, pts, col):
    d.polygon([(float(x), float(y)) for x, y in pts], fill=col)


def headgear(d, hx, hy, r, kind, col, accent=None, facing=1):
    """Vẽ mũ/nón trên đầu tâm (hx,hy) bán kính r."""
    if kind == "nonla":           # nón lá Việt
        _poly(d, [(hx - r * 2.4, hy - r * 0.15), (hx + r * 2.4, hy - r * 0.15), (hx, hy - r * 2.1)], accent or col)
    elif kind == "cone":          # mũ nhọn kiểu Trung Hoa / Mông Cổ, có chỏm
        _poly(d, [(hx - r * 1.25, hy - r * 0.2), (hx + r * 1.25, hy - r * 0.2), (hx, hy - r * 2.2)], col)
        d.line([(hx, hy - r * 2.2), (hx, hy - r * 2.9)], fill=accent or col, width=max(1, int(r * 0.35)))
    elif kind == "kabuto":        # mũ samurai: vành loe + sừng chữ V
        d.ellipse([hx - r * 1.15, hy - r * 1.35, hx + r * 1.15, hy + r * 0.3], fill=col)
        _poly(d, [(hx - r * 1.9, hy + r * 0.2), (hx + r * 1.9, hy + r * 0.2), (hx + r * 1.2, hy - r * 0.5),
                  (hx - r * 1.2, hy - r * 0.5)], col)
        w = max(1, int(r * 0.35))
        d.line([(hx, hy - r * 1.0), (hx - r * 1.1, hy - r * 2.6)], fill=accent or col, width=w)
        d.line([(hx, hy - r * 1.0), (hx + r * 1.1, hy - r * 2.6)], fill=accent or col, width=w)
    elif kind == "jingasa":       # nón dẹt của ashigaru
        _poly(d, [(hx - r * 1.9, hy - r * 0.1), (hx + r * 1.9, hy - r * 0.1), (hx, hy - r * 1.3)], col)
    elif kind == "gat":           # mũ vành rộng Joseon
        d.ellipse([hx - r * 2.2, hy - r * 0.75, hx + r * 2.2, hy - r * 0.25], fill=col)
        d.rectangle([hx - r * 0.75, hy - r * 1.9, hx + r * 0.75, hy - r * 0.5], fill=col)
    elif kind == "joseon_helmet":  # mũ trụ Joseon có chỏm lông
        d.ellipse([hx - r * 1.1, hy - r * 1.5, hx + r * 1.1, hy + r * 0.1], fill=col)
        d.line([(hx, hy - r * 1.5), (hx, hy - r * 2.6)], fill=accent or col, width=max(1, int(r * 0.4)))
        d.ellipse([hx - r * 0.45, hy - r * 3.0, hx + r * 0.45, hy - r * 2.3], fill=accent or col)
    elif kind == "norman":        # mũ chóp nhọn có thanh che mũi
        _poly(d, [(hx - r * 1.12, hy - r * 0.1), (hx + r * 1.12, hy - r * 0.1), (hx + r * 0.6, hy - r * 1.4),
                  (hx, hy - r * 2.0), (hx - r * 0.6, hy - r * 1.4)], col)
    elif kind == "round":         # mũ trụ tròn
        d.ellipse([hx - r * 1.15, hy - r * 1.45, hx + r * 1.15, hy + r * 0.25], fill=col)
    elif kind == "greathelm":     # mũ hiệp sĩ hình trụ
        d.rectangle([hx - r * 1.05, hy - r * 1.3, hx + r * 1.05, hy + r * 0.9], fill=col)
    elif kind == "topknot":       # búi tóc
        d.ellipse([hx - r * 0.5, hy - r * 1.7, hx + r * 0.5, hy - r * 0.8], fill=col)
    elif kind == "hood":
        _poly(d, [(hx - r * 1.2, hy + r * 0.6), (hx + r * 1.2, hy + r * 0.6), (hx + r * 0.9, hy - r * 1.1),
                  (hx - r * 0.2 * facing, hy - r * 1.6), (hx - r * 0.9, hy - r * 1.1)], col)


def figure(d, x, yb, h, col, head="round", weapon="spear", shield=None, facing=1, phase=0.0, accent=None,
           banner=None, lean=0.0):
    """Bóng một người lính đứng/đi. (x, yb) = chân chạm đất, h = chiều cao."""
    r = h * 0.075
    hx, hy = x + lean * h * 0.08 * facing, yb - h * 0.88
    step = math.sin(phase) * h * 0.07
    # chân
    hip_y = yb - h * 0.45
    lw = h * 0.055
    _poly(d, [(x - lw * 1.6, hip_y), (x - lw * 0.1, hip_y), (x - h * 0.06 - step, yb), (x - h * 0.06 - step - lw * 1.4, yb)], col)
    _poly(d, [(x + lw * 0.1, hip_y), (x + lw * 1.6, hip_y), (x + h * 0.06 + step + lw * 1.4, yb), (x + h * 0.06 + step, yb)], col)
    # thân (áo dài phủ hông)
    sh_y = yb - h * 0.79
    _poly(d, [(hx - h * 0.115, sh_y), (hx + h * 0.115, sh_y), (x + h * 0.13, yb - h * 0.36), (x - h * 0.13, yb - h * 0.36)], col)
    # cổ + đầu
    d.rectangle([hx - r * 0.45, hy, hx + r * 0.45, sh_y + 2], fill=col)
    d.ellipse([hx - r, hy - r, hx + r, hy + r], fill=col)
    headgear(d, hx, hy, r, head, col, accent, facing)
    # tay + vũ khí
    hand = (hx + facing * h * 0.17, yb - h * 0.55)
    aw = max(1, int(h * 0.05))
    d.line([(hx + facing * h * 0.08, sh_y + h * 0.03), hand], fill=col, width=aw)
    ww = max(1, int(h * 0.028))
    if weapon == "spear":
        top = (hand[0] + facing * h * 0.18, yb - h * 1.42)
        bot = (hand[0] - facing * h * 0.05, yb - h * 0.12)
        d.line([bot, top], fill=col, width=ww)
        ang = math.atan2(top[1] - bot[1], top[0] - bot[0])
        L = h * 0.13
        tip = (top[0] + math.cos(ang) * L, top[1] + math.sin(ang) * L)
        _poly(d, [tip, (top[0] + math.cos(ang + 1.6) * L * 0.25, top[1] + math.sin(ang + 1.6) * L * 0.25),
                  (top[0] + math.cos(ang - 1.6) * L * 0.25, top[1] + math.sin(ang - 1.6) * L * 0.25)], accent or col)
    elif weapon == "naginata":
        top = (hand[0] + facing * h * 0.2, yb - h * 1.3)
        d.line([(hand[0] - facing * h * 0.05, yb - h * 0.15), top], fill=col, width=ww)
        _poly(d, [top, (top[0] + facing * h * 0.12, top[1] - h * 0.16), (top[0] + facing * h * 0.03, top[1] + h * 0.02)], accent or col)
    elif weapon == "bow":
        bx = hand[0] + facing * h * 0.04
        d.arc([bx - h * 0.18, yb - h * 1.05, bx + h * 0.18, yb - h * 0.2], 270 - 70 if facing > 0 else 90 - 70,
              270 + 70 if facing > 0 else 90 + 70, fill=col, width=ww)
        d.line([(bx, yb - h * 1.0), (bx, yb - h * 0.25)], fill=col, width=1)
    elif weapon == "sword":
        d.line([hand, (hand[0] + facing * h * 0.12, hand[1] - h * 0.42)], fill=accent or col, width=ww + 1)
    elif weapon == "musket":
        d.line([(hx - facing * h * 0.05, sh_y + h * 0.06), (hx + facing * h * 0.55, sh_y - h * 0.05)], fill=col, width=ww + 1)
    elif weapon == "axe":
        top = (hand[0] + facing * h * 0.05, hand[1] - h * 0.55)
        d.line([hand, top], fill=col, width=ww)
        _poly(d, [top, (top[0] + facing * h * 0.13, top[1] - h * 0.04), (top[0] + facing * h * 0.13, top[1] + h * 0.12),
                  (top[0], top[1] + h * 0.1)], accent or col)
    if shield:
        sx, sy = hx + facing * h * 0.14, yb - h * 0.55
        if shield == "kite":
            _poly(d, [(sx - h * 0.1, sy - h * 0.2), (sx + h * 0.1, sy - h * 0.2), (sx + h * 0.08, sy + h * 0.05),
                      (sx, sy + h * 0.25), (sx - h * 0.08, sy + h * 0.05)], accent or col)
        elif shield == "rect":
            d.rectangle([sx - h * 0.09, sy - h * 0.2, sx + h * 0.09, sy + h * 0.18], fill=accent or col)
        else:
            d.ellipse([sx - h * 0.13, sy - h * 0.15, sx + h * 0.13, sy + h * 0.15], fill=accent or col)
    if banner:                    # cờ cắm sau lưng (sashimono) hoặc cờ hiệu
        bx = hx - facing * h * 0.08
        d.line([(bx, sh_y + h * 0.1), (bx, yb - h * 1.45)], fill=col, width=max(1, int(h * 0.02)))
        x_a, x_b = sorted((bx, bx - facing * h * 0.13))
        d.rectangle([x_a, yb - h * 1.45, x_b, yb - h * 1.05], fill=banner)


def horse(d, x, yb, h, col, facing=1, phase=0.0, rider=None, rider_col=None):
    """Bóng ngựa (h = chiều cao tới vai), tuỳ chọn có người cưỡi (dict tham số figure)."""
    f = facing
    bx0, bx1 = x - f * h * 0.55, x + f * h * 0.45
    by0, by1 = yb - h * 1.0, yb - h * 0.55
    d.ellipse([min(bx0, bx1), by0, max(bx0, bx1), by1], fill=col)
    # cổ + đầu
    nx = x + f * h * 0.35
    _poly(d, [(nx, by0 + h * 0.15), (nx + f * h * 0.18, by0 - h * 0.35), (nx + f * h * 0.3, by0 - h * 0.38),
              (nx + f * h * 0.5, by0 - h * 0.12), (nx + f * h * 0.42, by0 - h * 0.05), (nx + f * h * 0.25, by0 - h * 0.15),
              (nx + f * h * 0.15, by0 + h * 0.3)], col)
    _poly(d, [(nx + f * h * 0.2, by0 - h * 0.35), (nx + f * h * 0.24, by0 - h * 0.48), (nx + f * h * 0.28, by0 - h * 0.36)], col)
    # chân
    lw = max(1, int(h * 0.07))
    for k, lx in enumerate([x - f * h * 0.4, x - f * h * 0.25, x + f * h * 0.2, x + f * h * 0.32]):
        sw = math.sin(phase + k * 1.7) * h * 0.12
        d.line([(lx, by1 - h * 0.1), (lx + sw, yb)], fill=col, width=lw)
    # đuôi
    tx = x - f * h * 0.55
    d.line([(tx, by0 + h * 0.1), (tx - f * h * 0.2, by0 + h * 0.55)], fill=col, width=max(1, int(h * 0.09)))
    if rider:
        rp = dict(rider)
        rh = h * 0.95
        figure(d, x - f * h * 0.05, by0 + h * 0.25, rh, rider_col or col, facing=f, **rp)


def flag_points(x, ytop, w, h, t, facing=1, waves=2.0, amp=0.12):
    """Đa giác lá cờ bay (vẽ lại theo t để cờ phấp phới)."""
    pts_top, pts_bot = [], []
    n = 12
    for i in range(n + 1):
        u = i / n
        off = math.sin(u * math.pi * waves - t * 5.0) * h * amp * u
        pts_top.append((x + facing * u * w, ytop + off))
        pts_bot.append((x + facing * u * w * 0.97, ytop + h + off * 1.1 - u * h * 0.08))
    return pts_top + pts_bot[::-1]


def stake(d, x, ytip, ybase, w=26, wood=(52, 34, 22), iron=(120, 124, 130), lean=0):
    """Cọc gỗ đầu bịt sắt (như demo draw.py)."""
    s = w / 26
    d.polygon([(x - w / 2, ybase), (x + w / 2, ybase), (x + w / 2 + lean, ytip + 70 * s), (x + lean, ytip),
               (x - w / 2 + lean, ytip + 70 * s)], fill=wood)
    d.polygon([(x - w / 2 + lean, ytip + 70 * s), (x + lean, ytip), (x + w / 2 + lean, ytip + 70 * s),
               (x + w / 2 + lean - 3 * s, ytip + 85 * s), (x - w / 2 + lean + 3 * s, ytip + 85 * s)], fill=iron)


def oars(d, x0, x1, y, length, col, n=7, width=4, angle=0.5):
    for k in range(n):
        x = x0 + (x1 - x0) * k / max(1, n - 1)
        d.line([(x, y), (x - length * math.sin(angle), y + length * math.cos(angle))], fill=col, width=width)
