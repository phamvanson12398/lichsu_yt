"""Chuẩn bị văn bản trước khi đưa vào OmniVoice (mục 8.4):
  - đổi số, năm thành chữ tiếng Việt ("938" -> "chín trăm ba mươi tám")
  - số La Mã ("thế kỷ X" -> "thế kỷ mười"), viết tắt ("TK" -> "thế kỷ")
  - từ điển phát âm do người dùng sửa (pronunciation.json): "Yi Sun-sin" -> "I Xun Xin"
  - tách lời thành từng câu (tối đa ~20-25 giây)
Chữ trên màn hình vẫn giữ cách viết gốc.
"""
import json
import os
import re
import unicodedata

DIGITS = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]
ABBR = {
    r"\bTK\b": "thế kỷ", r"\bTCN\b": "trước Công nguyên", r"\bSCN\b": "sau Công nguyên", r"\bCN\b": "Công nguyên",
    r"\bkm\b": "ki lô mét", r"\bTP\.": "thành phố", r"\bVN\b": "Việt Nam", r"\bkg\b": "ki lô gam",
    r"\bv\.v\.?": "vân vân", r"\bkm2\b": "ki lô mét vuông", r"%": " phần trăm",
}
ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def _nfc(s):
    return unicodedata.normalize("NFC", s)


def _read3(n, full=False):
    """Đọc số 0..999. full=True: đọc cả 'không trăm' (dùng cho nhóm sau nhóm nghìn)."""
    tr, ch, dv = n // 100, (n // 10) % 10, n % 10
    out = []
    if tr or full:
        out += [DIGITS[tr], "trăm"]
    if ch == 0:
        if dv and (tr or full):
            out.append("linh")
    elif ch == 1:
        out.append("mười")
    else:
        out += [DIGITS[ch], "mươi"]
    if dv:
        if dv == 1 and ch >= 2:
            out.append("mốt")
        elif dv == 5 and ch >= 1:
            out.append("lăm")
        elif dv == 4 and ch >= 2:
            out.append("tư")
        else:
            out.append(DIGITS[dv])
    return out


def num2words(n):
    """Số nguyên -> chữ tiếng Việt. 938 -> chín trăm ba mươi tám; 1592 -> một nghìn năm trăm chín mươi hai."""
    n = int(n)
    if n < 0:
        return "âm " + num2words(-n)
    if n == 0:
        return "không"
    units = ["", "nghìn", "triệu", "tỷ"]
    groups = []
    while n:
        groups.append(n % 1000)
        n //= 1000
    out = []
    for i in range(len(groups) - 1, -1, -1):
        g = groups[i]
        if g == 0:
            if i % 3 == 0 and i > 0 and out:
                out.append(units[3] if i == 3 else "")
            continue
        out += _read3(g, full=bool(out))
        if i:
            out.append(units[i] if i < 4 else "tỷ")
    return " ".join(w for w in out if w)


def roman2int(s):
    s = s.upper()
    total, prev = 0, 0
    for ch in reversed(s):
        v = ROMAN.get(ch, 0)
        if v < prev:
            total -= v
        else:
            total += v
            prev = v
    return total


def _is_roman(s):
    return bool(re.fullmatch(r"M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})", s)) and s != ""


def load_pronunciation(*paths):
    d = {}
    for p in paths:
        if p and os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            d.update({k: v for k, v in data.items() if not k.startswith("_")})
    return d


def apply_pronunciation(text, pron):
    for k in sorted(pron, key=len, reverse=True):
        text = re.sub(r"(?<!\w)" + re.escape(_nfc(k)) + r"(?!\w)", _nfc(pron[k]), text)
    return text


def normalize(text, pron=None):
    """Văn bản để đọc (không dùng để hiển thị)."""
    t = _nfc(text)
    if pron:
        t = apply_pronunciation(t, pron)
    for pat, rep in ABBR.items():
        t = re.sub(pat, rep, t)
    # số La Mã sau "thế kỷ", "đời", "vua", "chương", "phần", hoặc tên vua châu Âu (Henry VIII)
    def roman_repl(m):
        return m.group(1) + num2words(roman2int(m.group(2)))
    t = re.sub(r"((?:thế kỷ|Thế kỷ|kỷ|chương|Chương|phần|Phần|thứ)\s+)([IVXLCDM]+)\b",
               lambda m: roman_repl(m) if _is_roman(m.group(2)) else m.group(0), t)
    t = re.sub(r"(\b[A-Z][a-z]+\s+)([IVX]{2,})\b", lambda m: m.group(1) + "đệ " + num2words(roman2int(m.group(2)))
               if _is_roman(m.group(2)) else m.group(0), t)
    # ngày tháng 12/8/1592
    t = re.sub(r"(?:\b[Nn]gày\s+)?\b(\d{1,2})/(\d{1,2})/(\d{3,4})\b",
               lambda m: f"ngày {num2words(m.group(1))} tháng {num2words(m.group(2))} năm {num2words(m.group(3))}", t)
    # khoảng năm 1592-1598 / 1592–1598
    t = re.sub(r"\b(\d{1,4})\s*[-–]\s*(\d{1,4})\b", lambda m: f"{num2words(m.group(1))} đến {num2words(m.group(2))}", t)
    # số thập phân 1,5  và số có dấu chấm nghìn 10.000
    t = re.sub(r"\b(\d{1,3}(?:\.\d{3})+)\b", lambda m: m.group(1).replace(".", ""), t)
    t = re.sub(r"\b(\d+),(\d+)\b", lambda m: f"{num2words(m.group(1))} phẩy {' '.join(DIGITS[int(c)] for c in m.group(2))}"
               if len(m.group(2)) > 2 else f"{num2words(m.group(1))} phẩy {num2words(m.group(2))}", t)
    t = re.sub(r"\b\d+\b", lambda m: num2words(m.group(0)), t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def split_sentences(text, max_syllables=55):
    """Tách đoạn thành câu; câu quá dài (> ~22 giây) cắt tiếp ở dấu phẩy / chấm phẩy."""
    text = _nfc(text).strip()
    parts = re.split(r"(?<=[.!?…])\s+(?=[\"“(\[A-ZÀ-Ỹ0-9])", text)
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if len(p.split()) <= max_syllables:
            out.append(p)
            continue
        chunks = re.split(r"(?<=[,;:])\s+", p)
        cur = ""
        for c in chunks:
            if cur and len((cur + " " + c).split()) > max_syllables:
                out.append(cur)
                cur = c
            else:
                cur = (cur + " " + c).strip()
        if cur:
            while len(cur.split()) > max_syllables:
                w = cur.split()
                out.append(" ".join(w[:max_syllables]))
                cur = " ".join(w[max_syllables:])
            out.append(cur)
    return out


def syllables(text):
    return len(_nfc(text).split())
