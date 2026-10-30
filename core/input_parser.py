"""Bước 1 - Phân tích đầu vào một dòng: "Trận Bạch Đằng năm 938 (10p)" -> chủ đề, thời lượng, năm, nước, thời kỳ."""
import re
import unicodedata

from core.voice.text_norm import _nfc

COUNTRY_KEYWORDS = {
    "vietnam": ["bạch đằng", "ngô quyền", "trần hưng đạo", "lý thường kiệt", "như nguyệt", "chi lăng", "đống đa",
                "ngọc hồi", "rạch gầm", "xoài mút", "quang trung", "lê lợi", "hai bà trưng", "bà triệu", "đinh bộ lĩnh",
                "điện biên", "đại việt", "đại cồ việt", "tây sơn", "hàm tử", "chương dương", "vạn kiếp", "tốt động",
                "lam sơn", "nhà trần", "nhà lý", "nhà lê", "nhà nguyễn", "việt nam", "thăng long", "cổ loa", "an dương vương",
                "hùng vương", "văn lang", "âu lạc", "lê hoàn", "nguyên mông", "mông nguyên", "nam hán"],
    "korea": ["hansan", "myeongnyang", "noryang", "yi sun-sin", "lý thuấn thần", "joseon", "triều tiên", "goguryeo",
              "cao câu ly", "silla", "tân la", "baekje", "bách tế", "goryeo", "cao ly", "hàn quốc", "imjin", "nhâm thìn",
              "salsu", "gwiju", "haengju", "jinju", "sejong", "thế tông", "hangul"],
    "japan": ["sekigahara", "nagashino", "okehazama", "dan-no-ura", "dannoura", "tokugawa", "oda nobunaga", "toyotomi",
              "hideyoshi", "sengoku", "chiến quốc nhật", "samurai", "nhật bản", "edo", "kamakura", "minamoto", "taira",
              "genpei", "shimabara", "osaka", "kyoto", "heian", "meiji", "minh trị", "mạc phủ", "shogun"],
    "england": ["hastings", "agincourt", "crécy", "crecy", "bosworth", "stamford bridge", "william the conqueror",
                "harold", "norman", "anh quốc", "nước anh", "england", "tudor", "plantagenet", "henry", "richard sư tử",
                "magna carta", "trafalgar", "armada", "elizabeth", "waterloo", "edward", "wessex", "alfred"],
}
COUNTRY_NAMES = {"vietnam": "Việt Nam", "korea": "Hàn Quốc / Triều Tiên", "japan": "Nhật Bản", "england": "Anh"}


def slugify(s):
    s = _nfc(s).lower().replace("đ", "d")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"\(.*?\)", " ", s)
    words = [w for w in re.split(r"[^a-z0-9]+", s) if w and w not in ("tran", "nam", "chien", "dich", "cuoc", "the", "of", "battle")]
    return "_".join(words)[:60] or "du_an"


def guess_era(country, year):
    if year is None:
        return ""
    if country == "vietnam":
        if year < 939:
            return f"thời Bắc thuộc, thế kỷ {year // 100 + 1}"
        for a, b, n in [(939, 968, "nhà Ngô"), (968, 980, "nhà Đinh"), (980, 1009, "nhà Tiền Lê"), (1009, 1225, "nhà Lý"),
                        (1225, 1400, "nhà Trần"), (1400, 1407, "nhà Hồ"), (1407, 1427, "thời thuộc Minh / khởi nghĩa Lam Sơn"),
                        (1428, 1789, "nhà Hậu Lê"), (1778, 1802, "nhà Tây Sơn"), (1802, 1945, "nhà Nguyễn")]:
            if a <= year < b:
                return f"{n}, năm {year}"
        return f"năm {year}"
    if country == "korea":
        if year >= 1392:
            return f"Triều Tiên thời Joseon, năm {year}"
        if year >= 918:
            return f"thời Goryeo, năm {year}"
        return f"thời Tam Quốc Triều Tiên, năm {year}"
    if country == "japan":
        for a, b, n in [(794, 1185, "thời Heian"), (1185, 1333, "thời Kamakura"), (1336, 1467, "thời Muromachi"),
                        (1467, 1603, "thời Sengoku"), (1603, 1868, "thời Edo"), (1868, 1912, "thời Minh Trị")]:
            if a <= year < b:
                return f"Nhật Bản {n}, năm {year}"
        return f"Nhật Bản, năm {year}"
    if country == "england":
        if year < 1066:
            return f"Anh thời Anglo-Saxon, năm {year}"
        if year < 1500:
            return f"Anh thời Trung cổ, năm {year}"
        return f"Anh, năm {year}"
    return f"năm {year}"


LANG_TAG = r"(vi|en|ko|ja|kr|jp|tiếng\s+việt|tiếng\s+anh|tiếng\s+hàn|tiếng\s+nhật|english|korean|japanese)"


def parse(line, default_minutes=10, default_lang="vi"):
    """Trả về dict: topic, minutes, year, country (đoán, có thể None), era, slug, language.

    Ngôn ngữ lời kể ghi kèm trong ngoặc: "Trận Hastings năm 1066 (8p, en)" hoặc "(10p tiếng Nhật)" hoặc "[ko]".
    """
    from core import lang as L
    line = _nfc(line.strip())
    minutes = default_minutes
    language = L.code(default_lang)
    m = re.search(r"\(\s*(\d+(?:[.,]\d+)?)\s*(p|ph|phút|m|min|')?\s*(?:[,;/]?\s*" + LANG_TAG + r")?\s*\)", line, re.I)
    if m:
        minutes = float(m.group(1).replace(",", "."))
        if m.group(3):
            language = L.code(m.group(3))
        line_topic = (line[: m.start()] + line[m.end():]).strip()
    else:
        line_topic = line
    m2 = re.search(r"[\[(]\s*" + LANG_TAG + r"\s*[\])]", line_topic, re.I)
    if m2:
        language = L.code(m2.group(1))
        line_topic = (line_topic[: m2.start()] + line_topic[m2.end():]).strip()
    years = [int(y) for y in re.findall(r"\b(\d{3,4})\b", line_topic)]
    year = years[0] if years else None
    low = line_topic.lower()
    country = None
    best = 0
    for c, kws in COUNTRY_KEYWORDS.items():
        score = sum(1 for k in kws if k in low)
        if score > best:
            country, best = c, score
    return {"topic": line_topic, "minutes": minutes, "year": year, "country": country,
            "era": guess_era(country, year) if country else "", "slug": slugify(line_topic) + ("" if language == "vi" else "_" + language),
            "raw": line, "language": language}
