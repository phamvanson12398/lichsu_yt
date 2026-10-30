"""Bảng màu cho cả video (mục 5.4). Mỗi bảng: bầu trời, núi (xa -> gần), nước, đất, bóng, lửa..."""

PALETTES = {
    "hoang_hon_do": {
        "mo_ta": "Hoàng hôn đỏ cam, ấm, bi tráng",
        "sky": [(38, 22, 48), (150, 70, 70), (232, 128, 60)],
        "sun": (255, 226, 170), "sun_glow": (255, 200, 120),
        "mount": [(120, 62, 64), (78, 40, 46), (44, 24, 30)],
        "water": [(150, 76, 52), (24, 14, 20)], "shimmer": (240, 150, 80),
        "ground": [(92, 50, 40), (30, 18, 18)],
        "sil": (26, 14, 16), "wood": (40, 26, 18), "sail": (150, 70, 40),
        "cloud": (200, 110, 90), "fog": (210, 140, 110), "fire": (255, 120, 30),
        "flag_ally": (190, 40, 30), "flag_enemy": (60, 40, 30), "stone": (110, 80, 72), "roof": (60, 32, 30),
    },
    "dem_lua": {
        "mo_ta": "Đêm rực lửa, đỏ thẫm, khói",
        "sky": [(18, 6, 10), (70, 22, 18), (190, 70, 30)],
        "sun": (255, 170, 90), "sun_glow": (255, 120, 40),
        "mount": [(70, 26, 22), (40, 16, 16), (26, 10, 10)],
        "water": [(120, 46, 26), (20, 10, 10)], "shimmer": (240, 120, 50),
        "ground": [(60, 24, 18), (16, 8, 8)],
        "sil": (14, 8, 6), "wood": (36, 20, 14), "sail": (110, 50, 32),
        "cloud": (90, 40, 30), "fog": (120, 60, 40), "fire": (255, 110, 25),
        "flag_ally": (200, 40, 25), "flag_enemy": (50, 30, 20), "stone": (80, 50, 44), "roof": (40, 18, 16),
    },
    "binh_minh_xanh": {
        "mo_ta": "Bình minh xanh lam, trong trẻo, yên bình",
        "sky": [(30, 52, 92), (110, 140, 170), (236, 196, 150)],
        "sun": (255, 236, 196), "sun_glow": (255, 210, 160),
        "mount": [(104, 124, 150), (70, 90, 116), (42, 58, 80)],
        "water": [(118, 140, 160), (22, 34, 50)], "shimmer": (240, 220, 190),
        "ground": [(70, 96, 84), (26, 40, 36)],
        "sil": (20, 28, 38), "wood": (52, 40, 30), "sail": (170, 140, 100),
        "cloud": (230, 210, 200), "fog": (200, 210, 220), "fire": (255, 140, 50),
        "flag_ally": (200, 50, 40), "flag_enemy": (60, 60, 70), "stone": (120, 124, 132), "roof": (60, 54, 60),
    },
    "suong_mu_xam": {
        "mo_ta": "Sương mù xám, lạnh, căng thẳng",
        "sky": [(96, 104, 112), (150, 156, 160), (198, 198, 192)],
        "sun": (236, 232, 220), "sun_glow": (220, 216, 206),
        "mount": [(150, 156, 158), (116, 122, 128), (80, 86, 94)],
        "water": [(140, 146, 148), (38, 44, 52)], "shimmer": (226, 226, 220),
        "ground": [(100, 106, 100), (40, 44, 44)],
        "sil": (34, 38, 44), "wood": (50, 44, 40), "sail": (150, 140, 124),
        "cloud": (190, 192, 190), "fog": (214, 216, 214), "fire": (255, 130, 50),
        "flag_ally": (170, 50, 40), "flag_enemy": (60, 60, 64), "stone": (130, 132, 134), "roof": (60, 62, 66),
    },
    "tuyet_trang": {
        "mo_ta": "Tuyết trắng, mùa đông",
        "sky": [(120, 140, 166), (186, 196, 210), (232, 234, 238)],
        "sun": (255, 250, 236), "sun_glow": (240, 236, 226),
        "mount": [(198, 206, 218), (160, 172, 188), (118, 130, 148)],
        "water": [(120, 140, 160), (48, 58, 74)], "shimmer": (240, 244, 250),
        "ground": [(236, 238, 242), (190, 198, 210)],
        "sil": (36, 40, 50), "wood": (60, 48, 40), "sail": (190, 180, 160),
        "cloud": (236, 238, 242), "fog": (228, 232, 238), "fire": (255, 140, 60),
        "flag_ally": (180, 40, 36), "flag_enemy": (50, 56, 70), "stone": (150, 154, 160), "roof": (70, 70, 80),
    },
    "trua_nang": {
        "mo_ta": "Trưa nắng, trời xanh, rõ ràng",
        "sky": [(58, 110, 170), (120, 170, 210), (226, 222, 196)],
        "sun": (255, 250, 220), "sun_glow": (255, 240, 200),
        "mount": [(120, 150, 160), (84, 116, 110), (54, 82, 70)],
        "water": [(90, 140, 160), (24, 56, 70)], "shimmer": (250, 246, 224),
        "ground": [(110, 140, 80), (50, 72, 40)],
        "sil": (30, 36, 30), "wood": (80, 56, 36), "sail": (200, 180, 140),
        "cloud": (250, 250, 248), "fog": (230, 236, 236), "fire": (255, 140, 40),
        "flag_ally": (200, 40, 36), "flag_enemy": (60, 60, 60), "stone": (150, 146, 136), "roof": (80, 60, 50),
    },
    "dem_trang": {
        "mo_ta": "Đêm trăng xanh thẫm, tĩnh lặng",
        "sky": [(6, 10, 24), (20, 30, 56), (52, 66, 100)],
        "sun": (236, 236, 220), "sun_glow": (150, 170, 210),
        "mount": [(44, 56, 84), (30, 40, 62), (18, 24, 40)],
        "water": [(50, 64, 96), (8, 12, 22)], "shimmer": (190, 206, 236),
        "ground": [(30, 40, 50), (10, 14, 20)],
        "sil": (8, 10, 16), "wood": (26, 22, 22), "sail": (80, 84, 96),
        "cloud": (60, 70, 96), "fog": (80, 96, 130), "fire": (255, 130, 40),
        "flag_ally": (150, 36, 30), "flag_enemy": (40, 40, 50), "stone": (60, 66, 80), "roof": (24, 26, 36),
    },
    "giay_co": {
        "mo_ta": "Giấy cổ cho bản đồ",
        "paper": (226, 206, 165), "ink": (85, 50, 25), "ink_light": (110, 80, 45),
        "water_map": (150, 170, 165), "water_line": (115, 138, 135), "land_hi": (214, 194, 150),
        "mount_fill": (205, 180, 135), "mount_line": (120, 95, 60), "label_water": (40, 66, 76),
        "enemy": (190, 40, 30), "ally": (40, 80, 150),
        # dùng được như bảng cảnh (dự phòng)
        "sky": [(120, 96, 70), (190, 166, 126), (226, 206, 165)], "sun": (250, 236, 200), "sun_glow": (240, 220, 180),
        "mount": [(170, 146, 110), (140, 116, 84), (110, 86, 60)], "water": [(150, 170, 165), (80, 96, 96)],
        "shimmer": (230, 220, 200), "ground": [(170, 150, 110), (100, 84, 60)], "sil": (60, 40, 24),
        "wood": (70, 50, 30), "sail": (190, 170, 130), "cloud": (220, 206, 176), "fog": (226, 210, 180),
        "fire": (220, 90, 30), "flag_ally": (40, 80, 150), "flag_enemy": (190, 40, 30), "stone": (150, 130, 100),
        "roof": (100, 70, 44),
    },
}

DEFAULT = "hoang_hon_do"


def get(name):
    return PALETTES.get(name or DEFAULT, PALETTES[DEFAULT])


def names():
    return list(PALETTES)


# Mỗi giờ trong ngày kéo màu về một bảng tham chiếu (trời ban ngày xanh, đêm xanh thẫm...), vẫn giữ một phần màu chủ đạo
# của video để các cảnh đồng bộ. Cờ hai phe và màu lửa giữ nguyên theo bảng của video.
TIME_REF = {"day": "trua_nang", "dawn": "binh_minh_xanh", "night": "dem_trang", "dusk": "hoang_hon_do"}
KEEP = ("mo_ta", "flag_ally", "flag_enemy", "fire")
_cache = {}


def _mix(a, b, w):
    if isinstance(a, (list, tuple)) and a and isinstance(a[0], (list, tuple)):
        return [_mix(x, y, w) for x, y in zip(a, b)]
    return tuple(int(round(x + (y - x) * w)) for x, y in zip(a, b))


def for_time(name, tod, weight=0.7):
    """Bảng màu của video chỉnh theo giờ trong cảnh (dawn | day | dusk | night)."""
    ref = TIME_REF.get(tod or "dusk")
    base = get(name)
    if not ref or ref == (name or DEFAULT) or name in ("giay_co",) or (tod == "night" and name == "dem_lua"):
        return base
    key = (name, tod, weight)
    if key not in _cache:
        r = PALETTES[ref]
        _cache[key] = {k: (v if k in KEEP or k not in r else _mix(v, r[k], weight)) for k, v in base.items()}
    return _cache[key]

