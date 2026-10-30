"""Bước 2 - Viết kịch bản (AI): độ dài lời kể khớp thời lượng, cấu trúc mở đầu -> bối cảnh -> diễn biến ->
cao trào -> kết quả & ý nghĩa -> kết; kèm GHI CHÚ NGUỒN; chỗ tranh cãi nói rõ. Lưu script.md để người dùng sửa.
"""
import json
import re

from audio.music_synth import MOODS
from core.voice.text_norm import _nfc

SCRIPT_SCHEMA = {
    "type": "object",
    "required": ["title", "country", "era", "sections", "sources", "youtube"],
    "properties": {
        "title": {"type": "string"}, "country": {"type": "string", "enum": ["vietnam", "korea", "japan", "england", "other"]},
        "era": {"type": "string"}, "year": {"type": ["integer", "null"]},
        "voice_suggestion": {"type": "string"},
        "sections": {"type": "array", "items": {"type": "object", "required": ["heading", "paragraphs"],
                                                "properties": {"heading": {"type": "string"}, "mood": {"type": "string"},
                                                               "paragraphs": {"type": "array", "items": {"type": "string"}}}}},
        "sources": {"type": "array", "items": {"type": "object", "required": ["claim", "source"]}},
        "disputed": {"type": "array", "items": {"type": "string"}},
        "youtube": {"type": "object", "required": ["titles", "description", "tags"]},
    },
}

PROMPT = """Bạn là biên kịch phim tài liệu lịch sử cho kênh YouTube, viết lời kể (voice-over) bằng {lang}.

CHỦ ĐỀ: {topic}
Thông tin tool đoán được (có thể sai, hãy sửa nếu cần): nước = {country}, thời kỳ = {era}, năm = {year}
THỜI LƯỢNG VIDEO: {minutes} phút. Lời kể cần khoảng {words} chữ (đếm theo khoảng trắng; tốc độ đọc ~{wpm} chữ/phút,
đã trừ thời gian các đoạn ngừng hiện chữ / bản đồ). Đừng ngắn hơn {wmin} hay dài hơn {wmax} chữ.

YÊU CẦU:
1. Cấu trúc 6 phần (heading tiếng Việt ngắn): Mở đầu gây tò mò -> Bối cảnh -> Diễn biến -> Cao trào ->
   Kết quả & ý nghĩa -> Kết. Mỗi phần gắn "mood" nhạc nền, chọn trong: {moods}.
2. Văn nói tự nhiên, câu ngắn vừa (tối đa ~35 chữ/câu), dễ đọc thành tiếng, giàu hình ảnh để minh họa được.
   Không dùng tiêu đề, gạch đầu dòng, ký hiệu hay chú thích trong lời kể.
3. Viết năm bằng chữ số (vd 938, 1592); tool sẽ tự đổi thành chữ khi đọc.
4. Tên riêng nước ngoài ghi theo cách phổ biến trong tiếng Việt, lần đầu xuất hiện kèm tên gốc trong ngoặc,
   vd: Lý Thuấn Thần (Yi Sun-sin). Lời kể bằng {lang} kể cả khi chủ đề là Hàn, Nhật, Anh.
5. CHÍNH XÁC LỊCH SỬ: không bịa chi tiết, con số, lời thoại. Chỗ sử liệu còn tranh cãi thì nói rõ
   "theo sử sách ghi lại" hoặc "có nhiều ý kiến khác nhau". Chủ đề nhạy cảm kể khách quan, tôn trọng các bên.
6. "sources": GHI CHÚ NGUỒN cho từng sự kiện, năm, tên người, số liệu quan trọng (claim = điều khẳng định,
   source = sách / sử liệu / tài liệu tham khảo cụ thể, note = mức độ chắc chắn hoặc ghi chú) để người dùng kiểm tra.
   "disputed": liệt kê các điểm còn tranh cãi.
7. "voice_suggestion": mô tả giọng đọc hợp chủ đề bằng thuộc tính tiếng Anh của OmniVoice voice design,
   chỉ dùng: giới tính (male/female), tuổi (child/teenager/young adult/middle-aged/elderly), cao độ (very low pitch/low pitch/
   moderate pitch/high pitch/very high pitch). Ví dụ: "male, middle-aged, low pitch".
8. "youtube": 3–5 gợi ý tiêu đề hấp dẫn nhưng không giật tít sai sự thật, mô tả 3–5 câu, 10–15 tag.

CHỈ trả về MỘT khối JSON đúng mẫu sau (không thêm lời nào khác):
{{"title": "...", "country": "vietnam|korea|japan|england|other", "era": "...", "year": 938,
  "voice_suggestion": "male, middle-aged, low pitch",
  "sections": [{{"heading": "Mở đầu", "mood": "yen_binh", "paragraphs": ["...", "..."]}}],
  "sources": [{{"claim": "...", "source": "...", "note": "..."}}],
  "disputed": ["..."],
  "youtube": {{"titles": ["..."], "description": "...", "tags": ["..."]}}}}
"""

EXPAND = """Kịch bản dưới đây mới có {have} chữ, cần khoảng {words} chữ. Hãy viết lại cho đủ độ dài bằng cách thêm chi tiết
lịch sử CÓ THẬT (bối cảnh, nhân vật, diễn biến), giữ nguyên cấu trúc, giữ các ghi chú nguồn và bổ sung nguồn cho chi tiết mới.
Trả về toàn bộ JSON cùng mẫu.

{script}
"""

CHECK = """Bạn là người kiểm tra sự kiện lịch sử. Đọc kịch bản sau và liệt kê những chỗ có thể SAI hoặc THIẾU CHẮC CHẮN
(năm, tên người, địa danh, số liệu, quan hệ nhân quả, chi tiết có vẻ bịa). Không sửa văn phong.
Trả về JSON: {{"issues": [{{"quote": "trích nguyên câu", "problem": "vấn đề", "suggestion": "gợi ý sửa", "severity": "cao|vừa|thấp"}}]}}
Nếu không thấy vấn đề, trả {{"issues": []}}.

CHỦ ĐỀ: {topic}

KỊCH BẢN:
{script}
"""


def word_count(script):
    return sum(len(p.split()) for s in script["sections"] for p in s["paragraphs"])


def target_words(minutes, wpm=140, pause_ratio=0.12):
    return int(minutes * wpm * (1 - pause_ratio))


def write(router, info, cfg, log=print):
    words = target_words(info["minutes"], cfg.get("words_per_minute", 140))
    prompt = PROMPT.format(lang=cfg.get("narration_language", "tiếng Việt"), topic=info["topic"], country=info.get("country") or "?",
                           era=info.get("era") or "?", year=info.get("year") or "?", minutes=info["minutes"], words=words,
                           wmin=int(words * 0.9), wmax=int(words * 1.1), wpm=cfg.get("words_per_minute", 140), moods=", ".join(MOODS))
    log(f"✍️  Viết kịch bản ~{words} chữ cho {info['minutes']} phút...")
    data = router.ask("writer", prompt, schema=SCRIPT_SCHEMA)
    have = word_count(data)
    if have < words * 0.8:
        log(f"   kịch bản mới {have} chữ (< 80% mục tiêu) — nhờ AI viết dài thêm")
        data = router.ask("writer", EXPAND.format(have=have, words=words, script=json.dumps(data, ensure_ascii=False)), schema=SCRIPT_SCHEMA)
    for s in data["sections"]:
        if s.get("mood") not in MOODS:
            s["mood"] = None
    log(f"   ✔ kịch bản {word_count(data)} chữ, {len(data['sections'])} phần, {len(data.get('sources', []))} ghi chú nguồn")
    return data


def check_facts(router, info, script_md, log=print):
    log("🔎 Nhờ AI kiểm tra lại sự kiện...")
    data = router.ask("checker", CHECK.format(topic=info["topic"], script=script_md),
                      schema={"type": "object", "required": ["issues"], "properties": {"issues": {"type": "array"}}})
    return data.get("issues", [])


# ------------------------------------------------------------------ script.md
def to_markdown(data, info):
    L = [f"# {data['title']}",
         f"<!-- country: {data.get('country')} | era: {data.get('era')} | year: {data.get('year') or ''} | minutes: {info['minutes']}"
         f" | voice: {data.get('voice_suggestion', '')} -->", "",
         "> Sửa lời kể thoải mái. Giữ các dòng '## ' (tên phần) và dòng '<!-- mood: ... -->'. Phần sau '## GHI CHÚ NGUỒN' không được đọc.", ""]
    for s in data["sections"]:
        L.append(f"## {s['heading']}")
        if s.get("mood"):
            L.append(f"<!-- mood: {s['mood']} -->")
        L.append("")
        for p in s["paragraphs"]:
            L += [p.strip(), ""]
    L += ["---", "## GHI CHÚ NGUỒN (không đọc)", ""]
    for src in data.get("sources", []):
        note = f" _({src['note']})_" if src.get("note") else ""
        L.append(f"- **{src['claim']}** — nguồn: {src['source']}{note}")
    if data.get("disputed"):
        L += ["", "### Điểm còn tranh cãi", ""] + [f"- {d}" for d in data["disputed"]]
    return "\n".join(L) + "\n"


def parse_markdown(md):
    """script.md -> {title, meta, sections:[{heading, mood, paragraphs}]} (bỏ phần ghi chú nguồn)."""
    md = _nfc(md)
    body = re.split(r"^##\s+GHI CHÚ NGUỒN.*$", md, flags=re.M)[0]
    body = re.sub(r"^---\s*$", "", body, flags=re.M)
    title = ""
    meta = {}
    m = re.search(r"^#\s+(.+)$", body, re.M)
    if m:
        title = m.group(1).strip()
    m = re.search(r"<!--\s*country:(.*?)-->", body, re.S)
    if m:
        for part in ("country:" + m.group(1)).split("|"):
            if ":" in part:
                k, v = part.split(":", 1)
                meta[k.strip()] = v.strip()
    sections = []
    for chunk in re.split(r"^##\s+", body, flags=re.M)[1:]:
        lines = chunk.splitlines()
        heading = lines[0].strip()
        rest = "\n".join(lines[1:])
        mm = re.search(r"<!--\s*mood:\s*(\w+)\s*-->", rest)
        mood = mm.group(1) if mm else None
        rest = re.sub(r"<!--.*?-->", "", rest, flags=re.S)
        paras = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", rest)]
        paras = [p for p in paras if p and not p.startswith(">")]
        if paras:
            sections.append({"heading": heading, "mood": mood if mood in MOODS else None, "paragraphs": paras})
    return {"title": title, "meta": meta, "sections": sections}
