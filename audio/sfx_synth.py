"""Âm thanh hiệu ứng tổng hợp bằng numpy (không bản quyền), giữ phong cách textfx.py / motion.py của demo.

Tag: boom, riser, shimmer, click, pop, whoosh (stereo pan), tick, bell, lua_tach (lửa lách tách),
     gio_u (gió rền), song_nuoc (sóng nước), tieng_tron (trống trận), kiem_cham (kiếm chạm),
     mua (mưa), vo_ngua (vó ngựa), ten_bay (tên bay).
Các tag lua_tach / gio_u / song_nuoc / mua còn có bản "nền" (ambience) kéo dài theo cảnh: bed(tag, dur).
"""
import numpy as np

SR = 44100
_rng = np.random.default_rng(3)


def bandnoise(n, lo, hi, rng=None):
    rng = rng or _rng
    n = max(2, int(n))
    x = rng.standard_normal(n)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    y = np.fft.irfft(X, n)
    return y / (np.abs(y).max() + 1e-9)


def _t(d):
    n = int(SR * d)
    return n, np.arange(n) / SR


def boom():
    n, t = _t(2.2)
    f = 42 * (1 + 1.5 * np.exp(-t * 18))
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.2)
    s += 0.35 * bandnoise(n, 30, 400) * np.exp(-t * 4)
    s += 0.25 * bandnoise(n, 1000, 6000) * np.exp(-t * 30)
    return s


def riser():
    n, t = _t(0.5)
    return 0.5 * bandnoise(n, 400, 5000) * (t / t[-1]) ** 2


def shimmer():
    n, t = _t(1.5)
    s = sum(np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, d in [(1760, 3), (2637, 4), (3520, 5)])
    return 0.12 * s * np.minimum(1, t / 0.05)


def click():
    n, t = _t(0.03)
    s = bandnoise(n, 1500 + _rng.uniform(0, 1500), 9000) * np.exp(-t * 220)
    s += 0.5 * np.sin(2 * np.pi * _rng.uniform(180, 260) * t) * np.exp(-t * 150)
    return 0.55 * s


def pop():
    n, t = _t(0.09)
    f0 = _rng.uniform(650, 850)
    f = f0 * (1 + 0.8 * np.exp(-t * 60))
    return 0.35 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 45) * np.minimum(1, t / 0.003)


def whoosh(d=0.7):
    n, t = _t(d)
    env = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 2.5
    env = np.roll(env, -int(SR * 0.08 * d / 0.7))
    s = 0.7 * bandnoise(n, 250, 3500) * env
    pan = np.clip(t / (d * 0.86), 0, 1)
    return np.stack([s * (1 - 0.7 * pan), s * (0.3 + 0.7 * pan)], 1)


def tick():
    n, t = _t(0.025)
    return 0.3 * np.sin(2 * np.pi * 2200 * t) * np.exp(-t * 300)


def bell():
    n, t = _t(2.5)
    s = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t * d)
            for f, a, d in [(523.25, 1, 1.2), (1046.5, 0.5, 1.8), (1569.8, 0.3, 2.5), (2637, 0.15, 4)])
    s += 0.5 * np.sin(2 * np.pi * 65 * t) * np.exp(-t * 6)
    return 0.35 * s


def tieng_tron(big=True):
    n, t = _t(0.9)
    f = 55 * (1 + 1.2 * np.exp(-t * 25))
    hit = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * (5 if big else 9))
    hit += 0.15 * _rng.standard_normal(n) * np.exp(-t * 40)
    return (0.8 if big else 0.5) * hit


def kiem_cham():
    n, t = _t(1.2)
    s = sum(a * np.sin(2 * np.pi * f * t + _rng.uniform(0, 6)) * np.exp(-t * d)
            for f, a, d in [(2210, 1, 5), (3120, 0.7, 7), (4470, 0.5, 9), (5830, 0.3, 12), (1340, 0.4, 6)])
    s += 0.8 * bandnoise(n, 2000, 9000) * np.exp(-t * 60)
    return 0.3 * s


def ten_bay():
    n, t = _t(0.45)
    env = np.sin(np.pi * t / 0.45) ** 2
    s = bandnoise(n, 1500, 6000) * env * 0.4
    pan = t / 0.45
    return np.stack([s * (1 - 0.6 * pan), s * (0.4 + 0.6 * pan)], 1)


def vo_ngua(d=2.0):
    n, t = _t(d)
    s = np.zeros(n)
    beat = 0.36
    for k, st in enumerate(np.arange(0, d - 0.1, beat / 4)):
        if k % 4 == 3:
            continue
        m, tt = _t(0.08)
        h = (np.sin(2 * np.pi * 110 * tt) * np.exp(-tt * 60) + 0.5 * _rng.standard_normal(m) * np.exp(-tt * 90))
        i = int(st * SR)
        s[i:i + m] += h[: n - i] * (0.5 + 0.3 * (k % 4 == 0))
    return 0.5 * s


# ---------------------------------------------------------------- nền kéo dài (ambience)
def bed(tag, d, seed=0):
    rng = np.random.default_rng(seed + sum(map(ord, tag)))
    n, t = _t(max(0.2, d))
    env = np.minimum(1, np.minimum(t / 0.6, (d - t) / 0.6))
    if tag == "lua_tach":
        roar = bandnoise(n, 40, 500, rng) * .35 * (1 + .3 * np.sin(t * 2.1))
        crack = np.zeros(n)
        for _ in range(int(d * 28)):
            i = int(rng.integers(0, max(1, n - 2000)))
            L = int(rng.integers(80, 600))
            crack[i:i + L] += bandnoise(L, 1500, 8000, rng)[: n - i] * np.exp(-np.arange(L) / (L / 4))[: n - i] * rng.uniform(.2, .9)
        return (roar + .5 * crack) * env
    if tag == "gio_u":
        w = bandnoise(n, 150, 900, rng) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.13 * t + 1) ** 2)
        howl = sum(np.sin(2 * np.pi * (f + 15 * np.sin(2 * np.pi * 0.07 * t)) * t) for f in (220, 330)) * 0.04
        return (0.45 * w + howl * (0.5 + 0.5 * np.sin(2 * np.pi * 0.1 * t))) * env
    if tag == "song_nuoc":
        base = bandnoise(n, 80, 1200, rng) * 0.3
        swell = 0.55 + 0.45 * np.sin(2 * np.pi * 0.18 * t) ** 2
        lap = np.zeros(n)
        for st in np.arange(0.3, d, 1.1):
            m, tt = _t(0.6)
            i = int((st + rng.uniform(-0.2, 0.2)) * SR)
            if 0 <= i < n:
                lap[i:i + m] += (bandnoise(m, 300, 3000, rng) * np.sin(np.pi * tt / 0.6) ** 2 * 0.3)[: n - i]
        return (base * swell + lap) * env
    if tag == "mua":
        return (0.35 * bandnoise(n, 1500, 9000, rng) + 0.2 * bandnoise(n, 200, 1500, rng)) * env
    if tag == "tieng_tron":
        s = np.zeros(n)
        k = 0
        for st in np.arange(0.2, d - 0.3, 0.6):
            h = tieng_tron(k % 2 == 0)
            i = int(st * SR)
            m = min(len(h), n - i)
            s[i:i + m] += h[:m] * 0.8
            k += 1
        return s * env
    if tag == "vo_ngua":
        return vo_ngua(d) * env
    return np.zeros(n)


ONE_SHOTS = {"boom": boom, "riser": riser, "shimmer": shimmer, "click": click, "pop": pop, "whoosh": whoosh,
             "tick": tick, "bell": bell, "tieng_tron": tieng_tron, "kiem_cham": kiem_cham, "ten_bay": ten_bay,
             "vo_ngua": vo_ngua, "lua_tach": lambda: bed("lua_tach", 2.5), "gio_u": lambda: bed("gio_u", 3.0),
             "song_nuoc": lambda: bed("song_nuoc", 3.0), "mua": lambda: bed("mua", 3.0)}
BED_TAGS = ["lua_tach", "gio_u", "song_nuoc", "mua", "tieng_tron", "vo_ngua"]
TAGS = sorted(ONE_SHOTS)


def make(tag):
    fn = ONE_SHOTS.get(tag)
    if fn is None:
        return None
    s = fn()
    if s.ndim == 1:
        s = np.stack([s, s], 1)
    return s.astype(np.float32)
