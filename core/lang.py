"""Hỗ trợ nhiều ngôn ngữ lời kể (mục 2): vi (tiếng Việt, mặc định), en (tiếng Anh), ko (tiếng Hàn), ja (tiếng Nhật).

Mỗi ngôn ngữ có: cách đếm độ dài (chữ / âm tiết / ký tự), tốc độ đọc, cách tách câu, cách đổi số thành chữ
khi đọc, chữ cố định trên hình (bản đồ, chú thích...), câu mẫu thử giọng, mã cho nhận dạng giọng nói.
"""
import re
import unicodedata

ALIASES = {
    "vi": "vi", "tiếng việt": "vi", "tieng viet": "vi", "vietnamese": "vi", "việt": "vi",
    "en": "en", "tiếng anh": "en", "tieng anh": "en", "english": "en", "anh": "en",
    "ko": "ko", "kr": "ko", "tiếng hàn": "ko", "tieng han": "ko", "korean": "ko", "hàn": "ko", "한국어": "ko",
    "ja": "ja", "jp": "ja", "tiếng nhật": "ja", "tieng nhat": "ja", "japanese": "ja", "nhật": "ja", "日本語": "ja",
}

LANGS = {
    "vi": {
        "name": "tiếng Việt", "unit": "chữ (âm tiết, đếm theo khoảng trắng)", "per_min": 140, "per_sec_speech": 2.6,
        "scene_units": (15, 25), "max_sentence": 55,
        "asr": "vi", "sample": "Xin chào các bạn, đây là giọng đọc thử cho kênh lịch sử. Năm 938, Ngô Quyền đánh tan quân Nam Hán trên sông Bạch Đằng.",
        "ui": {"map_note": "Sơ đồ minh họa, không theo tỉ lệ", "red": "Đỏ", "blue": "Xanh", "north": "B", "year": "Năm {y}",
               "yt_titles": "=== GỢI Ý TIÊU ĐỀ ===", "yt_desc": "=== MÔ TẢ ===", "yt_chapters": "Mốc thời gian:", "yt_tags": "=== TAG ===",
               "yt_sources": "Nguồn tham khảo chính:", "intro": "Mở đầu",
               "yt_notes": ["Hình ảnh trong video là tranh minh họa vẽ bằng code, không phải ảnh tư liệu thật.",
                            "Bản đồ là sơ đồ minh họa, không theo tỉ lệ.", "Âm nhạc và hiệu ứng âm thanh được tổng hợp bằng máy tính."],
               "yt_voice": "Giọng đọc được tạo bằng mô hình OmniVoice (k2-fsa) từ giọng mẫu có sự đồng ý.",
               "yt_desc_default": "Câu chuyện về {t}, kể lại bằng hình minh họa động.", "yt_tag_history": "lịch sử"},
    },
    "en": {
        "name": "tiếng Anh (English)", "unit": "words", "per_min": 150, "per_sec_speech": 2.5,
        "scene_units": (15, 25), "max_sentence": 50,
        "asr": "en", "sample": "Hello, this is a test voice for a history channel. In the year 1066, William of Normandy crossed the Channel to claim the English crown.",
        "ui": {"map_note": "Illustrative map, not to scale", "red": "Red", "blue": "Blue", "north": "N", "year": "{y}",
               "yt_titles": "=== TITLE IDEAS ===", "yt_desc": "=== DESCRIPTION ===", "yt_chapters": "Chapters:", "yt_tags": "=== TAGS ===",
               "yt_sources": "Main sources:", "intro": "Intro",
               "yt_notes": ["All images in this video are illustrations drawn with code, not historical photographs.",
                            "Maps are illustrative and not to scale.", "Music and sound effects are computer-synthesized."],
               "yt_voice": "Narration voice generated with the OmniVoice model (k2-fsa) from a consented voice sample.",
               "yt_desc_default": "The story of {t}, told with animated illustrations.", "yt_tag_history": "history"},
    },
    "ko": {
        "name": "tiếng Hàn (한국어)", "unit": "글자 (âm tiết Hangul, không tính khoảng trắng)", "per_min": 300, "per_sec_speech": 5.2,
        "scene_units": (35, 60), "max_sentence": 110,
        "asr": "ko", "sample": "안녕하세요, 역사 채널을 위한 시험 음성입니다. 1592년, 이순신 장군은 한산도 앞바다에서 일본 수군을 크게 무찔렀습니다.",
        "ui": {"map_note": "설명용 지도이며 축척과 다릅니다", "red": "빨강", "blue": "파랑", "north": "N", "year": "{y}년",
               "yt_titles": "=== 제목 후보 ===", "yt_desc": "=== 설명 ===", "yt_chapters": "타임라인:", "yt_tags": "=== 태그 ===",
               "yt_sources": "주요 참고 자료:", "intro": "도입",
               "yt_notes": ["영상 속 그림은 코드로 그린 일러스트이며 실제 사료 사진이 아닙니다.",
                            "지도는 설명용이며 축척과 다릅니다.", "음악과 효과음은 컴퓨터로 합성했습니다."],
               "yt_voice": "내레이션은 동의를 받은 음성 샘플로 OmniVoice(k2-fsa) 모델을 사용해 생성했습니다.",
               "yt_desc_default": "{t} 이야기를 움직이는 그림으로 전합니다.", "yt_tag_history": "역사"},
    },
    "ja": {
        "name": "tiếng Nhật (日本語)", "unit": "文字 (ký tự, không tính khoảng trắng)", "per_min": 300, "per_sec_speech": 5.5,
        "scene_units": (35, 60), "max_sentence": 110,
        "asr": "ja", "sample": "こんにちは、歴史チャンネルのための試験音声です。一六〇〇年、関ヶ原で東軍と西軍が天下を分ける戦いを繰り広げました。",
        "ui": {"map_note": "説明用の図であり縮尺は正確ではありません", "red": "赤", "blue": "青", "north": "N", "year": "{y}年",
               "yt_titles": "=== タイトル案 ===", "yt_desc": "=== 概要欄 ===", "yt_chapters": "チャプター:", "yt_tags": "=== タグ ===",
               "yt_sources": "主な参考資料:", "intro": "導入",
               "yt_notes": ["映像内の画像はコードで描いたイラストであり、実際の史料写真ではありません。",
                            "地図は説明用で縮尺は正確ではありません。", "音楽と効果音はコンピューターで合成しています。"],
               "yt_voice": "ナレーションは本人の同意を得た音声サンプルから OmniVoice（k2-fsa）モデルで生成しました。",
               "yt_desc_default": "{t}の物語を動くイラストでお届けします。", "yt_tag_history": "歴史"},
    },
}


def code(lang):
    """'tiếng Việt' / 'English' / 'ko' ... -> mã chuẩn vi | en | ko | ja (mặc định vi)."""
    if not lang:
        return "vi"
    k = unicodedata.normalize("NFC", str(lang)).strip().lower()
    if k in LANGS:
        return k
    return ALIASES.get(k, "vi")


def get(lang):
    return LANGS[code(lang)]


def ui(lang, key, **kw):
    s = get(lang)["ui"][key]
    return s.format(**kw) if kw and isinstance(s, str) else s


def is_cjk_lang(lang):
    return code(lang) in ("ko", "ja")


def count(text, lang):
    """Độ dài lời kể theo đơn vị của ngôn ngữ (vi/en: số từ; ko/ja: số ký tự không tính khoảng trắng, dấu câu)."""
    text = unicodedata.normalize("NFC", text or "")
    if is_cjk_lang(lang):
        return len(re.sub(r"[\s\W_]", "", text))
    return len(text.split())


def speech_seconds(text, lang, speed=1.0):
    return max(1.2, count(text, lang) / (get(lang)["per_sec_speech"] * speed))


# ------------------------------------------------------------------ tách câu
def split_sentences(text, lang="vi", max_units=None):
    text = unicodedata.normalize("NFC", text or "").strip()
    max_units = max_units or get(lang)["max_sentence"]
    if is_cjk_lang(lang):
        parts = re.split(r"(?<=[。！？!?])\s*|(?<=[.])\s+", text)
        soft = r"(?<=[、，,；;：:])"
    else:
        parts = re.split(r"(?<=[.!?…])\s+(?=[\"“(\[A-ZÀ-Ỹ0-9])", text)
        soft = r"(?<=[,;:])\s+"
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if count(p, lang) <= max_units:
            out.append(p)
            continue
        cur = ""
        for c in re.split(soft, p):
            joiner = "" if is_cjk_lang(lang) and code(lang) == "ja" else " "
            cand = (cur + joiner + c).strip() if cur else c
            if cur and count(cand, lang) > max_units:
                out.append(cur)
                cur = c
            else:
                cur = cand
        if cur:
            out.append(cur)
    return out


# ------------------------------------------------------------------ số -> chữ
EN_ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
EN_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def en_words(n):
    n = int(n)
    if n < 0:
        return "minus " + en_words(-n)
    if n < 20:
        return EN_ONES[n]
    if n < 100:
        return EN_TENS[n // 10] + ("-" + EN_ONES[n % 10] if n % 10 else "")
    if n < 1000:
        return EN_ONES[n // 100] + " hundred" + (" " + en_words(n % 100) if n % 100 else "")
    for div, name in ((10 ** 9, "billion"), (10 ** 6, "million"), (1000, "thousand")):
        if n >= div:
            return en_words(n // div) + " " + name + (" " + en_words(n % div) if n % div else "")
    return str(n)


def en_year(n):
    """1066 -> ten sixty-six; 1600 -> sixteen hundred; 2005 -> two thousand five; 938 -> nine thirty-eight."""
    n = int(n)
    if 2000 <= n <= 2009:
        return en_words(n)
    if 100 <= n <= 9999:
        hi, lo = divmod(n, 100)
        if lo == 0:
            return en_words(hi) + " hundred"
        return en_words(hi) + " " + ("oh-" + EN_ONES[lo] if lo < 10 else en_words(lo))
    return en_words(n)


KO_DIG = "영일이삼사오육칠팔구"


def ko_words(n):
    """Số Hán-Hàn: 1592 -> 천오백구십이."""
    n = int(n)
    if n == 0:
        return "영"
    if n < 0:
        return "마이너스 " + ko_words(-n)
    out = ""
    for div, name in ((10 ** 12, "조"), (10 ** 8, "억"), (10 ** 4, "만")):
        if n >= div:
            q = n // div
            out += ("" if (q == 1 and name == "만") else _ko4(q)) + name + " "
            n %= div
    out += _ko4(n)
    return out.strip()


def _ko4(n):
    s = ""
    for div, name in ((1000, "천"), (100, "백"), (10, "십")):
        q = n // div
        if q:
            s += ("" if q == 1 else KO_DIG[q]) + name
        n %= div
    if n:
        s += KO_DIG[n]
    return s


JA_DIG = "〇一二三四五六七八九"


def ja_words(n):
    """Số kanji: 1600 -> 千六百; 1592 -> 千五百九十二."""
    n = int(n)
    if n == 0:
        return "零"
    out = ""
    for div, name in ((10 ** 8, "億"), (10 ** 4, "万")):
        if n >= div:
            out += _ja4(n // div) + name
            n %= div
    return out + _ja4(n)


def _ja4(n):
    s = ""
    for div, name in ((1000, "千"), (100, "百"), (10, "十")):
        q = n // div
        if q:
            s += ("" if q == 1 else JA_DIG[q]) + name
        n %= div
    if n:
        s += JA_DIG[n]
    return s


ROMAN_ORD_EN = {1: "the First", 2: "the Second", 3: "the Third", 4: "the Fourth", 5: "the Fifth", 6: "the Sixth",
                7: "the Seventh", 8: "the Eighth", 9: "the Ninth", 10: "the Tenth", 11: "the Eleventh", 12: "the Twelfth"}


def normalize_en(t):
    from core.voice.text_norm import _is_roman, roman2int
    t = re.sub(r"\b([A-Z][a-z]+)\s+([IVX]{1,4})\b",
               lambda m: f"{m.group(1)} {ROMAN_ORD_EN.get(roman2int(m.group(2)), m.group(2))}" if _is_roman(m.group(2)) and m.group(2) != "I" else m.group(0), t)
    t = re.sub(r"\b(\d{1,4})\s*[-–]\s*(\d{1,4})\b", lambda m: f"{en_year(m.group(1))} to {en_year(m.group(2))}", t)
    t = re.sub(r"\b(\d{1,3}(?:,\d{3})+)\b", lambda m: m.group(1).replace(",", ""), t)
    t = re.sub(r"\b(\d+(?:\.\d+)?)\s*%", lambda m: m.group(1) + " percent", t)
    t = re.sub(r"\b(\d+)\.(\d+)\b", lambda m: en_words(m.group(1)) + " point " + " ".join(EN_ONES[int(c)] for c in m.group(2)), t)
    t = re.sub(r"\b(\d+)(st|nd|rd|th)\b", lambda m: _en_ord(int(m.group(1))), t)
    # năm: số 3–4 chữ số đứng sau in/of/year/since/by/from/until/AD/BC hoặc 1100–1999
    t = re.sub(r"\b(in|of|year|since|by|from|until|till|around|circa|AD|BC|summer|autumn|winter|spring)\s+(\d{3,4})\b",
               lambda m: m.group(1) + " " + en_year(m.group(2)), t, flags=re.I)
    t = re.sub(r"\b(1[1-9]\d\d)\b", lambda m: en_year(m.group(1)), t)
    t = re.sub(r"\b\d+\b", lambda m: en_words(m.group(0)), t)
    return re.sub(r"\s+", " ", t).strip()


def _en_ord(n):
    w = en_words(n)
    special = {"one": "first", "two": "second", "three": "third", "five": "fifth", "eight": "eighth", "nine": "ninth", "twelve": "twelfth"}
    last = re.split(r"([ -])", w)
    tail = last[-1]
    tail = special.get(tail, (tail[:-1] + "ieth") if tail.endswith("y") else tail + "th")
    return "".join(last[:-1]) + tail


def normalize_ko(t):
    t = re.sub(r"\b(\d{1,3}(?:,\d{3})+)\b", lambda m: m.group(1).replace(",", ""), t)
    t = re.sub(r"(\d+(?:\.\d+)?)\s*%", lambda m: m.group(1) + " 퍼센트", t)
    t = re.sub(r"(?<!\d)6\s*월", "유월", t)
    t = re.sub(r"(?<!\d)10\s*월", "시월", t)
    t = re.sub(r"(\d+)\.(\d+)", lambda m: ko_words(m.group(1)) + "점" + "".join(KO_DIG[int(c)] for c in m.group(2)), t)
    t = re.sub(r"\d+", lambda m: ko_words(m.group(0)), t)
    return re.sub(r"\s+", " ", t).strip()


def normalize_ja(t):
    t = re.sub(r"(\d{1,3}(?:,\d{3})+)", lambda m: m.group(1).replace(",", ""), t)
    t = re.sub(r"(\d+(?:\.\d+)?)\s*[%％]", lambda m: m.group(1) + "パーセント", t)
    t = re.sub(r"(\d+)\.(\d+)", lambda m: ja_words(m.group(1)) + "点" + "".join(JA_DIG[int(c)] for c in m.group(2)), t)
    t = re.sub(r"\d+", lambda m: ja_words(m.group(0)), t)
    return t.strip()
