"""Chuyển cảnh (mục 6.4): mờ qua đen 0.3–0.5 s (mặc định) hoặc cắt thẳng.
Crossfade nằm BÊN TRONG một file cảnh (scene + scene2, đổi ở switch_at), không fade giữa các file đã dựng.
"""
from render.common import ease

TRANSITIONS = ["fade", "cut", "crossfade", "flash"]


def fade_gain(t, dur, scene, default_fade=0.4):
    """Hệ số sáng (0..1) của khung tại t do fade vào / ra."""
    tr_in = scene.get("transition_in", scene.get("transition", "fade"))
    tr_out = scene.get("transition_out", scene.get("transition", "fade"))
    f = float(scene.get("fade", default_fade)) / 2
    g = 1.0
    if tr_in in ("fade", "crossfade") and f > 0:
        g = min(g, t / f)
    if tr_out in ("fade", "crossfade") and f > 0:
        g = min(g, (dur - t) / f)
    return max(0.0, min(1.0, g))


def flash_gain(t, scene):
    """Chớp trắng ngắn (cho khoảnh khắc va chạm). scene["flash_at"] = giây."""
    fa = scene.get("flash_at")
    if fa is None:
        return 0.0
    u = t - float(fa)
    if u < 0 or u > 0.5:
        return 0.0
    return (1 - ease(u / 0.5)) * float(scene.get("flash_strength", 0.5))


def cross_weight(t, switch_at, dur=0.8):
    """Trọng số cảnh 2 khi crossfade bên trong một cảnh."""
    return ease((t - switch_at) / dur)
