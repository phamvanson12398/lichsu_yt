"""Bước 2 - Viết kịch bản (AI): độ dài lời kể khớp thời lượng, bố cục 7 phần giữ chân người xem
(hook mở thẳng vào khoảnh khắc quyết định -> hai phe -> trước trận -> bước ngoặt -> cao trào -> kết cục -> di sản),
một câu hỏi lớn + một "bí mật" giấu đến cao trào; kèm GHI CHÚ NGUỒN; chỗ tranh cãi nói rõ. Lưu script.md để người dùng sửa.
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
        "big_question": {"type": "string"}, "answer": {"type": "string"},
        "secret": {"type": "object"},
        "sections": {"type": "array", "items": {"type": "object", "required": ["heading", "role", "paragraphs"],
                                                "properties": {"heading": {"type": "string"}, "mood": {"type": "string"},
                                                               "role": {"type": "string"},
                                                               "paragraphs": {"type": "array", "items": {"type": "string"}}}}},
        "sources": {"type": "array", "items": {"type": "object", "required": ["claim", "source"]}},
        "disputed": {"type": "array", "items": {"type": "string"}},
        "youtube": {"type": "object", "required": ["titles", "description", "tags"]},
    },
}

# Bố cục 7 phần (tỉ lệ theo video 15 phút: 1 / 2 / 3 / 1.5 / 4.5 / 2 / 1 phút)
ROLES = [
    ("hook", 1.0, "cang_thang", "COLD OPEN / HOOK",
     "Mở THẲNG vào khoảnh khắc quyết định của trận: kể hẳn một cảnh gay cấn rồi DỪNG đúng lúc căng nhất. "
     "Nêu CÂU HỎI LỚN của cả video (kết bằng dấu hỏi). Nhắc tới một 'bí mật' (mưu kế chính / sự thật bất ngờ) sẽ hé lộ về sau. "
     "CẤM chào hỏi, giới thiệu kênh, 'hôm nay chúng ta sẽ tìm hiểu'."),
    ("sides", 2.0, "yen_binh", "HAI PHE VÀ CÁN CÂN LỰC LƯỢNG",
     "Ai đánh ai, vì sao phải đánh, bên thua mất gì. Giới thiệu HAI VỊ CHỈ HUY như hai nhân vật đối đầu, mỗi người có điểm mạnh "
     "và điểm yếu. So quân số, vũ khí, kinh nghiệm để thấy 'kèo lệch'. Kể qua góc nhìn nhân vật, không liệt kê. "
     "Kết bằng một câu treo (kiểu 'Nhưng điều không ai ngờ là...')."),
    ("prep", 3.0, "cang_thang", "TRƯỚC TRẬN: MƯU KẾ VÀ CHUẨN BỊ",
     "Địa hình, thời tiết, đường tiếp tế; kế hoạch mỗi bên — GIỮ LẠI một phần mưu kế bên thắng để hé lộ ở cao trào. "
     "Những sai lầm nhỏ của bên thua bắt đầu lộ ra. Cứ 60–90 giây lại có một 'móc': chi tiết lạ, con số gây sốc, câu hỏi phụ."),
    ("turn", 1.5, "cang_thang", "BƯỚC NGOẶT GIỮA VIDEO",
     "Một cú lật làm người xem nhìn lại câu hỏi lớn: phục binh, phản bội, chỉ huy tử trận, thời tiết đổi chiều, "
     "hoặc một quyết định liều lĩnh (chỉ dùng điều có trong sử liệu)."),
    ("battle", 4.5, "cao_trao", "DIỄN BIẾN TRẬN ĐÁNH — CAO TRÀO",
     "Chia 2–3 giai đoạn rõ ràng (mỗi giai đoạn mở bằng một câu định vị: ai ở đâu, tiến về đâu — để dựng bản đồ). "
     "Kể chậm lại ở khoảnh khắc then chốt, xen chi tiết cận cảnh người lính (vũ khí, tiếng động, nỗi sợ) — chỉ điều có trong sử liệu. "
     "HÉ LỘ 'bí mật' ở đây (khoảng 2/3 video). Câu ngắn hơn, nhịp nhanh hơn."),
    ("outcome", 2.0, "bi_trang", "KẾT CỤC VÀ CÁI GIÁ",
     "Thương vong, số phận các chỉ huy. TRẢ LỜI RÕ câu hỏi lớn ở hook: yếu tố nào thực sự quyết định thắng bại."),
    ("legacy", 1.0, "ket_thuc", "DI SẢN VÀ KẾT",
     "Trận đánh thay đổi lịch sử thế nào (một câu, không giảng giải). Kết bằng một câu hỏi mở sang câu chuyện tiếp theo "
     "(vd 'Nhưng chỉ vài năm sau...'). KHÔNG kêu gọi like / đăng ký."),
]
ROLE_NAMES = [r[0] for r in ROLES]


def role_budgets(minutes, words):
    """Số chữ cho từng phần: hook 30–60 giây, kết ≤ 1 phút, phần giữa chia theo tỉ lệ."""
    per_min = words / max(0.5, minutes)
    total = sum(r[1] for r in ROLES)
    out = {r[0]: words * r[1] / total for r in ROLES}
    out["hook"] = min(max(out["hook"], per_min * 0.5), per_min * 1.0)
    out["legacy"] = min(out["legacy"], per_min * 1.0)
    rest = words - out["hook"] - out["legacy"]
    mid = [r for r in ROLES if r[0] not in ("hook", "legacy")]
    for r in mid:
        out[r[0]] = rest * r[1] / sum(m[1] for m in mid)
    return {k: int(round(v)) for k, v in out.items()}


PROMPT = """Bạn là biên kịch phim tài liệu lịch sử cho kênh YouTube không lộ mặt, viết lời kể (voice-over) bằng {lang}.
Mục tiêu số 1: GIỮ CHÂN NGƯỜI XEM đến cuối video mà vẫn ĐÚNG LỊCH SỬ.

CHỦ ĐỀ: {topic}
Thông tin tool đoán được (có thể sai, hãy sửa nếu cần): nước = {country}, thời kỳ = {era}, năm = {year}
THỜI LƯỢNG VIDEO: {minutes} phút. Lời kể tổng cộng khoảng {words} {unit} (giọng đọc ~{wpm} {unit}/phút).
Đừng ngắn hơn {wmin} hay dài hơn {wmax}.

NGUYÊN TẮC:
- Kể như MỘT CÂU CHUYỆN có nhân vật, xung đột, câu hỏi chưa trả lời — không liệt kê sự kiện kiểu sách giáo khoa,
  không kể đều đều theo trình tự năm.
- Cả video trả lời MỘT câu "vì sao" rõ ràng (thắng nhờ địa hình, hậu cần, mưu kế, hay vì đối phương chủ quan...).
- Nếu chủ đề không phải một trận đánh, giữ đúng tinh thần bố cục: xung đột, bước ngoặt, cao trào, cái giá, di sản.

BỐ CỤC BẮT BUỘC — đúng 7 phần, đúng thứ tự, mỗi phần có "role" như sau (số {unit} là mục tiêu cho phần đó):
{roles}

KỸ THUẬT GIỮ CHÂN (áp dụng xuyên suốt):
- Vòng lặp mở: luôn còn ít nhất một câu hỏi chưa được trả lời. Mỗi phần (trừ phần cuối) KẾT BẰNG MỘT CÂU TREO —
  người xem hay bỏ đi ở ranh giới giữa các phần.
- Dùng nhân vật thay vì sự kiện ("Ngô Quyền biết rằng..." cuốn hơn "Năm 938 quân ta..."). Có thể đặt người xem vào
  vị trí chỉ huy: "Nếu bạn là X lúc này, bạn sẽ rút hay đánh?". Suy đoán tâm lý thì nói rõ là suy đoán ("có lẽ", "hẳn là"),
  KHÔNG bịa lời thoại.
- Không dồn thông tin: niên đại, con số, tên riêng nào không phục vụ câu chuyện thì bỏ.
- Con số đi kèm hình dung CHÍNH XÁC (vd "đủ lấp kín một sân vận động lớn" cho khoảng 50.000 người).
- Phân biệt sử liệu với giai thoại; số quân trong sử cũ thường bị phóng đại — nói rõ khi số liệu còn tranh cãi
  (vừa đáng tin, vừa là một 'móc' hay).
- Câu ngắn, có nhịp, giàu hình ảnh để minh họa được (mỗi câu đọc dưới ~10 giây); văn nói tự nhiên của người bản ngữ {lang},
  không văn dịch. {lang_note} Không dùng tiêu đề, gạch đầu dòng, ký hiệu hay chú thích trong lời kể.
- "heading" mỗi phần là TÊN CHƯƠNG GÂY TÒ MÒ (vd "Sai lầm của Ô Mã Nhi", không phải "Diễn biến"); dùng làm mốc chương YouTube.

QUY ĐỊNH KHÁC:
1. "mood" nhạc nền mỗi phần, chọn trong: {moods} (gợi ý: hook cang_thang/cao_trao, battle cao_trao, outcome bi_trang, legacy ket_thuc).
2. Viết năm bằng chữ số (vd 938, 1592); tool sẽ tự đổi thành chữ khi đọc.
3. {names_rule} Toàn bộ lời kể, tên phần (heading), "youtube" đều viết bằng {lang}, dù chủ đề thuộc nước nào.
4. CHÍNH XÁC LỊCH SỬ: không bịa chi tiết, con số, lời thoại. Chỗ sử liệu còn tranh cãi thì nói rõ
   "theo sử sách ghi lại" hoặc "có nhiều ý kiến khác nhau". Chủ đề nhạy cảm kể khách quan, tôn trọng các bên.
5. "big_question": câu hỏi lớn đặt ở hook. "answer": câu trả lời (nói ở phần outcome).
   "secret": {{"what": "bí mật / mưu kế được giấu", "hint": "câu gợi ý trong hook", "reveal": "câu hé lộ trong phần battle"}}.
6. "sources": GHI CHÚ NGUỒN cho từng sự kiện, năm, tên người, số liệu quan trọng (claim = điều khẳng định,
   source = sách / sử liệu / tài liệu tham khảo cụ thể, note = mức độ chắc chắn hoặc ghi chú) để người dùng kiểm tra.
   "disputed": liệt kê các điểm còn tranh cãi.
7. "voice_suggestion": mô tả giọng đọc hợp chủ đề bằng thuộc tính tiếng Anh của OmniVoice voice design,
   chỉ dùng: giới tính (male/female), tuổi (child/teenager/young adult/middle-aged/elderly), cao độ (very low pitch/low pitch/
   moderate pitch/high pitch/very high pitch). Ví dụ: "male, middle-aged, low pitch".
8. "youtube": 3–5 tiêu đề gây tò mò nhưng KHỚP NỘI DUNG (lời hứa của tiêu đề phải được trả lời trong video, không giật tít sai sự thật),
   mô tả 3–5 câu, 10–15 tag (bằng {lang}); "thumbnail": 3 gợi ý ảnh bìa, mỗi gợi ý gồm "text" (≤ 5 chữ, bằng {lang})
   và "image" (mô tả hình bằng tiếng Việt).
9. "sources", "disputed", "secret" viết bằng tiếng Việt để người dùng (người Việt) kiểm tra.

CHỈ trả về MỘT khối JSON đúng mẫu sau (không thêm lời nào khác):
{{"title": "...", "country": "vietnam|korea|japan|england|other", "era": "...", "year": 938,
  "voice_suggestion": "male, middle-aged, low pitch",
  "big_question": "...", "answer": "...", "secret": {{"what": "...", "hint": "...", "reveal": "..."}},
  "sections": [{{"role": "hook", "heading": "...", "mood": "cang_thang", "paragraphs": ["...", "..."]}}, ... đủ 7 phần],
  "sources": [{{"claim": "...", "source": "...", "note": "..."}}],
  "disputed": ["..."],
  "youtube": {{"titles": ["..."], "description": "...", "tags": ["..."], "thumbnail": [{{"text": "...", "image": "..."}}]}}}}
"""

EXPAND = """Kịch bản dưới đây mới có {have} {unit}, cần khoảng {words} {unit}. Hãy viết lại cho đủ độ dài bằng cách thêm chi tiết
lịch sử CÓ THẬT (nhân vật, diễn biến, chi tiết cận cảnh), ưu tiên phần thiếu nhiều nhất: {short}.
Giữ nguyên 7 phần và "role", câu hỏi lớn, bí mật, câu treo cuối mỗi phần; giữ ghi chú nguồn và bổ sung nguồn cho chi tiết mới.
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


NAMES_RULE = {
    "vi": "Tên riêng nước ngoài ghi theo cách phổ biến trong tiếng Việt, lần đầu xuất hiện kèm tên gốc trong ngoặc, vd: Lý Thuấn Thần (Yi Sun-sin).",
    "en": "Use the standard English spelling of names (e.g. Yi Sun-sin, Tokugawa Ieyasu, Ngo Quyen); Vietnamese names may be written without diacritics.",
    "ko": "Tên riêng viết theo cách phổ biến trong tiếng Hàn (vd 이순신, 도쿠가와 이에야스, 응오꾸옌), lần đầu có thể kèm chữ Hán / tên gốc trong ngoặc.",
    "ja": "Tên riêng viết theo cách phổ biến trong tiếng Nhật (vd 李舜臣（イ・スンシン）, 徳川家康, ゴ・クエン), lần đầu kèm cách đọc nếu khó.",
}
LANG_NOTE = {
    "vi": "",
    "en": "Write for a documentary narrator; avoid clichés.",
    "ko": "Dùng văn kể chuyện tài liệu lịch sự (-습니다 / -였습니다).",
    "ja": "Dùng thể です・ます của phim tài liệu (ナレーション), không viết chữ La-tinh trừ khi cần.",
}


BANNED = {
    "vi": ["xin chào", "chào mừng các bạn", "hôm nay chúng ta", "hôm nay mình", "đăng ký kênh", "nhấn like", "bấm like", "bấm chuông"],
    "en": ["welcome back", "welcome to", "today we", "in this video we", "subscribe", "smash that like", "hit the like"],
    "ko": ["안녕하세요", "구독", "좋아요", "오늘은 우리가"],
    "ja": ["こんにちは", "チャンネル登録", "高評価", "今日は皆さん"],
}


def check_structure(data, lang="vi"):
    """Lỗi bố cục (gửi lại cho AI sửa): đủ 7 phần đúng thứ tự, hook có câu hỏi, không chào hỏi / kêu gọi đăng ký."""
    E = []
    secs = data.get("sections") or []
    roles = [str(s.get("role", "")).strip().lower() for s in secs]
    if roles != ROLE_NAMES:
        E.append(f"Phải có đúng 7 phần với role theo thứ tự {ROLE_NAMES}; hiện có {roles}")
    if not secs:
        return E
    q = ("?", "？")
    hook = " ".join(secs[0].get("paragraphs") or [])
    if not any(c in hook for c in q):
        E.append("Phần hook phải đặt CÂU HỎI LỚN của video (có dấu chấm hỏi)")
    low_all = [(s.get("role"), " ".join(s.get("paragraphs") or []).lower()) for s in secs]
    for role, txt in low_all:
        for w in BANNED.get(lang, []):
            if w in txt:
                E.append(f"Phần {role}: bỏ câu chào hỏi / kêu gọi kiểu \"{w}\" — vào thẳng câu chuyện, kết bằng câu hỏi mở")
    if not data.get("big_question"):
        E.append("Thiếu 'big_question'")
    if not isinstance(data.get("secret"), dict) or not data["secret"].get("what"):
        E.append("Thiếu 'secret' {what, hint, reveal}")
    last = " ".join(secs[-1].get("paragraphs") or [])
    if len(secs) >= 7 and not any(c in last for c in q):
        E.append("Phần legacy phải kết bằng một câu hỏi mở sang câu chuyện tiếp theo")
    return E


def word_count(script, lang="vi"):
    from core import lang as L
    return sum(L.count(p, lang) for s in script["sections"] for p in s["paragraphs"])


def target_words(minutes, wpm=200, pause_ratio=0.12):
    return int(minutes * wpm * (1 - pause_ratio))


def write(router, info, cfg, log=print):
    from core import lang as L
    lg = info.get("language", "vi")
    LI = L.get(lg)
    wpm = cfg.get("words_per_minute", 200) if lg == "vi" else LI["per_min"]
    words = target_words(info["minutes"], wpm)
    bud = role_budgets(info["minutes"], words)
    unit_short = LI["unit"].split(" (")[0]
    if info["minutes"] >= float(cfg.get("script_parts_from_minutes", 12)):
        return write_in_parts(router, info, cfg, log, lg, LI, wpm, words, bud, unit_short)
    roles = "\n".join(f"  {i + 1}. role \"{r}\" — {title} (~{bud[r]} {unit_short}, ~{bud[r] / wpm:.1f} phút): {how}"
                      for i, (r, _, _, title, how) in enumerate(ROLES))
    prompt = PROMPT.format(lang=LI["name"], topic=info["topic"], country=info.get("country") or "?", unit=LI["unit"],
                           era=info.get("era") or "?", year=info.get("year") or "?", minutes=info["minutes"], words=words,
                           wmin=int(words * 0.9), wmax=int(words * 1.1), wpm=wpm, moods=", ".join(MOODS), roles=roles,
                           names_rule=NAMES_RULE[lg], lang_note=LANG_NOTE[lg])
    log(f"✍️  Viết kịch bản {LI['name']} ~{words} {unit_short} cho {info['minutes']} phút (bố cục 7 phần giữ chân người xem)...")
    check = lambda d: check_structure(d, lg)
    data = router.ask("writer", prompt, schema=SCRIPT_SCHEMA, validator=check)
    have = word_count(data, lg)
    if have < words * 0.8:
        from core import lang as L2
        got = {s.get("role"): sum(L2.count(p, lg) for p in s["paragraphs"]) for s in data["sections"]}
        short = ", ".join(f"{r} ({got.get(r, 0)}/{bud[r]})" for r in sorted(bud, key=lambda r: got.get(r, 0) - bud[r])[:3])
        log(f"   kịch bản mới {have} (< 80% mục tiêu) — nhờ AI viết dài thêm")
        data = router.ask("writer", EXPAND.format(have=have, words=words, unit=LI["unit"], short=short,
                                                  script=json.dumps(data, ensure_ascii=False)),
                          schema=SCRIPT_SCHEMA, validator=check)
    for s in data["sections"]:
        if s.get("mood") not in MOODS:
            s["mood"] = None
        if s.get("role") not in ROLE_NAMES:
            s["role"] = None
    log(f"   ✔ kịch bản {word_count(data, lg)} {LI['unit'].split(' (')[0]}, {len(data['sections'])} phần, {len(data.get('sources', []))} ghi chú nguồn")
    return data


# ------------------------------------------------------------------ video dài: viết theo từng phần
OUTLINE = """Bạn là biên kịch phim tài liệu lịch sử cho kênh YouTube không lộ mặt (lời kể bằng {lang}).
Mục tiêu số 1: GIỮ CHÂN NGƯỜI XEM đến cuối video mà vẫn ĐÚNG LỊCH SỬ. Video dài nên sẽ viết theo từng phần;
BƯỚC NÀY CHỈ LẬP DÀN Ý (chưa viết lời kể).

CHỦ ĐỀ: {topic}
Thông tin tool đoán được (có thể sai, hãy sửa nếu cần): nước = {country}, thời kỳ = {era}, năm = {year}
THỜI LƯỢNG: {minutes} phút (lời kể tổng ~{words} {unit}).

NGUYÊN TẮC: kể như MỘT CÂU CHUYỆN có nhân vật, xung đột, câu hỏi chưa trả lời; cả video trả lời MỘT câu "vì sao" rõ ràng;
giữ một "bí mật" (mưu kế chính / sự thật bất ngờ) để hé lộ ở cao trào. Không bịa chi tiết, con số, lời thoại.
Nếu chủ đề không phải một trận đánh, giữ đúng tinh thần bố cục: xung đột, bước ngoặt, cao trào, cái giá, di sản.

BỐ CỤC BẮT BUỘC — đúng 7 phần, đúng thứ tự, mỗi phần có "role":
{roles}

Mỗi phần cho: "heading" = TÊN CHƯƠNG GÂY TÒ MÒ bằng {lang} (vd "Sai lầm của Ô Mã Nhi", không phải "Diễn biến");
"mood" (chọn trong: {moods}); "beats" = 4–12 ý chính theo đúng thứ tự kể (viết tiếng Việt, cụ thể: ai, làm gì, ở đâu, chi tiết
đắt giá, con số có nguồn, câu treo cuối phần). Phần battle chia rõ 2–3 giai đoạn trong beats.

"voice_suggestion": thuộc tính tiếng Anh của OmniVoice voice design (vd "male, middle-aged, low pitch").
"youtube": 3–5 tiêu đề gây tò mò nhưng KHỚP NỘI DUNG, mô tả 3–5 câu, 10–15 tag (bằng {lang}), "thumbnail": 3 gợi ý
{{"text": "≤ 5 chữ bằng {lang}", "image": "mô tả hình bằng tiếng Việt"}}.
"big_question", "answer", "secret" viết bằng tiếng Việt.

CHỈ trả về MỘT khối JSON (in thẳng ra, không ghi file; trong chuỗi không dùng dấu ngoặc kép "):
{{"title": "...", "country": "vietnam|korea|japan|england|other", "era": "...", "year": 938, "voice_suggestion": "...",
  "big_question": "...", "answer": "...", "secret": {{"what": "...", "hint": "...", "reveal": "..."}},
  "sections": [{{"role": "hook", "heading": "...", "mood": "cang_thang", "beats": ["...", "..."]}}, ... đủ 7 phần],
  "youtube": {{"titles": ["..."], "description": "...", "tags": ["..."], "thumbnail": [{{"text": "...", "image": "..."}}]}}}}
"""

PART = """Bạn là biên kịch phim tài liệu lịch sử cho kênh YouTube không lộ mặt, viết lời kể (voice-over) bằng {lang}.
Video "{title}" ({minutes} phút) đang được viết THEO TỪNG PHẦN. Câu hỏi lớn của video: {big_question}
Bí mật giấu đến cao trào: {secret} (chỉ được HÉ LỘ trong phần battle; các phần trước chỉ gợi, không nói ra).

DÀN Ý CẢ VIDEO:
{outline}

ĐOẠN CUỐI CỦA PHẦN ĐÃ VIẾT NGAY TRƯỚC (để nối mạch, KHÔNG lặp lại):
{prev}

BÂY GIỜ HÃY VIẾT: phần {no}/7 — role "{role}" — "{heading}"{sub}
Ý chính cần kể (đúng thứ tự): {beats}
Yêu cầu riêng của phần này: {how}
Độ dài: khoảng {budget} {unit} (trong khoảng {bmin}–{bmax}).{ending}

CÁCH VIẾT:
- Kể như câu chuyện có nhân vật, không liệt kê kiểu sách giáo khoa. Câu ngắn, có nhịp, giàu hình ảnh để minh họa được
  (mỗi câu đọc dưới ~10 giây); văn nói tự nhiên của người bản ngữ {lang}, không văn dịch. {lang_note}
- Dùng nhân vật thay vì sự kiện; có thể đặt người xem vào vị trí chỉ huy. Suy đoán tâm lý thì nói rõ là suy đoán, KHÔNG bịa lời thoại.
- Con số đi kèm hình dung chính xác; số liệu còn tranh cãi thì nói rõ. Không bịa chi tiết.
- {names_rule} Viết năm bằng chữ số (vd 938). Không tiêu đề, gạch đầu dòng, ký hiệu hay chú thích trong lời kể.
- Không chào hỏi, không giới thiệu kênh, không kêu gọi like / đăng ký.

"sources": ghi chú nguồn (tiếng Việt) cho sự kiện, năm, tên người, số liệu quan trọng trong phần này
({{"claim": "...", "source": "sách / sử liệu cụ thể", "note": "mức độ chắc chắn"}}). "disputed": điểm còn tranh cãi (nếu có).

CHỈ trả về MỘT khối JSON (in thẳng ra, không ghi file; trong lời kể dùng ngoặc đơn hoặc « » thay cho dấu ngoặc kép "):
{{"paragraphs": ["đoạn 1", "đoạn 2", "..."], "sources": [...], "disputed": [...]}}
"""

OUTLINE_SCHEMA = {"type": "object", "required": ["title", "sections"],
                  "properties": {"sections": {"type": "array", "items": {"type": "object", "required": ["role", "heading", "beats"]}}}}
PART_SCHEMA = {"type": "object", "required": ["paragraphs"], "properties": {"paragraphs": {"type": "array", "items": {"type": "string"}}}}
PART_MAX_UNITS = 1000      # một lượt AI viết tối đa ~1000 chữ (≈ 5 phút đọc), phần dài hơn chia nhỏ


def write_in_parts(router, info, cfg, log, lg, LI, wpm, words, bud, unit_short):
    """Video dài: dàn ý trước, rồi viết từng phần (mỗi lượt ngắn, không quá thời gian / độ dài trả lời của AI)."""
    import math
    from core import lang as L
    roles_txt = "\n".join(f"  {i + 1}. role \"{r}\" — {title} (~{bud[r]} {unit_short}, ~{bud[r] / wpm:.1f} phút): {how}"
                          for i, (r, _, _, title, how) in enumerate(ROLES))
    log(f"✍️  Video dài {info['minutes']:g} phút (~{words} {unit_short}): lập dàn ý trước, rồi viết từng phần...")

    def check_outline(d):
        roles = [str(x.get("role", "")).lower() for x in d.get("sections") or []]
        E = [] if roles == ROLE_NAMES else [f"Phải có đúng 7 phần với role theo thứ tự {ROLE_NAMES}; hiện có {roles}"]
        E += [f"Phần {x.get('role')} thiếu 'beats'" for x in d.get("sections") or [] if not x.get("beats")]
        if not d.get("big_question"):
            E.append("Thiếu 'big_question'")
        return E
    outline = router.ask("writer", OUTLINE.format(lang=LI["name"], topic=info["topic"], country=info.get("country") or "?",
                                                  era=info.get("era") or "?", year=info.get("year") or "?", minutes=info["minutes"],
                                                  words=words, unit=LI["unit"], roles=roles_txt, moods=", ".join(MOODS)),
                         schema=OUTLINE_SCHEMA, validator=check_outline)
    secret = outline.get("secret") if isinstance(outline.get("secret"), dict) else {}
    outline_txt = "\n".join(f"{i + 1}. [{x['role']}] {x['heading']}: " + " / ".join(map(str, x.get("beats") or []))
                             for i, x in enumerate(outline["sections"]))
    how = {r[0]: r[4] for r in ROLES}
    sections, sources, disputed = [], [], list(outline.get("disputed") or [])
    prev = "(đây là phần đầu tiên của video)"
    for i, sec in enumerate(outline["sections"]):
        role = sec["role"]
        beats = [str(b) for b in sec.get("beats") or []]
        n = max(1, math.ceil(bud[role] / PART_MAX_UNITS))
        per = bud[role] / n
        paras = []
        for k in range(n):
            part_beats = beats[k * len(beats) // n:(k + 1) * len(beats) // n] or beats
            last_sub = k == n - 1
            ending = ""
            if last_sub and role == "hook":
                ending = "\nKết phần bằng CÂU HỎI LỚN của video (có dấu chấm hỏi) và một câu gợi tới bí mật."
            elif last_sub and role == "legacy":
                ending = "\nKết bằng một câu hỏi mở sang câu chuyện tiếp theo (có dấu chấm hỏi), không kêu gọi like / đăng ký."
            elif last_sub:
                ending = "\nKết phần bằng MỘT CÂU TREO dẫn sang phần sau: " + (outline["sections"][i + 1]["heading"] if i + 1 < len(outline["sections"]) else "")
            else:
                ending = "\nĐây chưa phải cuối phần: dừng ở chỗ tự nhiên, đoạn sau sẽ viết tiếp."
            sub = f" (đoạn {k + 1}/{n} của phần này)" if n > 1 else ""
            log(f"   ✍️  Phần {i + 1}/7 «{sec['heading']}»{sub} ~{int(per)} {unit_short}...")

            def check_part(d, per=per, role=role, last_sub=last_sub):
                ps = [p for p in d.get("paragraphs") or [] if isinstance(p, str) and p.strip()]
                if not ps:
                    return ["'paragraphs' rỗng"]
                have = sum(L.count(p, lg) for p in ps)
                E = []
                if have < per * 0.6:
                    E.append(f"Phần này mới {have} {unit_short}, cần khoảng {int(per)} — viết dài hơn bằng chi tiết có thật")
                elif have > per * 1.45:
                    E.append(f"Phần này dài {have} {unit_short}, chỉ cần khoảng {int(per)} — viết gọn lại, bỏ chi tiết phụ")
                txt = " ".join(ps).lower()
                E += [f"Bỏ câu chào hỏi / kêu gọi kiểu \"{w}\"" for w in BANNED.get(lg, []) if w in txt]
                if last_sub and role in ("hook", "legacy") and not any(c in txt for c in ("?", "？")):
                    E.append("Phần này phải kết bằng một câu hỏi (có dấu chấm hỏi)")
                return E
            d = router.ask("writer", PART.format(lang=LI["name"], title=outline.get("title") or info["topic"], minutes=info["minutes"],
                                                 big_question=outline.get("big_question", ""), secret=secret.get("what", ""),
                                                 outline=outline_txt, prev=prev, no=i + 1, role=role, heading=sec["heading"], sub=sub,
                                                 beats=" / ".join(part_beats), how=how.get(role, ""), budget=int(per), bmin=int(per * 0.85), bmax=int(per * 1.1),
                                                 unit=unit_short, ending=ending, lang_note=LANG_NOTE[lg], names_rule=NAMES_RULE[lg]),
                           schema=PART_SCHEMA, validator=check_part)
            new = [p.strip() for p in d["paragraphs"] if isinstance(p, str) and p.strip()]
            paras += new
            sources += [x for x in d.get("sources") or [] if isinstance(x, dict) and x.get("claim")]
            disputed += [str(x) for x in d.get("disputed") or [] if x]
            prev = "\n\n".join(paras[-2:])
        sections.append({"role": role, "heading": sec["heading"], "mood": sec.get("mood") if sec.get("mood") in MOODS else None,
                         "paragraphs": paras})
    data = {k: outline.get(k) for k in ("title", "country", "era", "year", "voice_suggestion", "big_question", "answer", "secret", "youtube")}
    data.update(sections=sections, sources=sources, disputed=list(dict.fromkeys(disputed)))
    if data.get("country") not in ("vietnam", "korea", "japan", "england", "other"):
        data["country"] = info.get("country") or "other"
    for w in check_structure(data, lg):
        log(f"   ⚠️  {w}")
    log(f"   ✔ kịch bản {word_count(data, lg)} {unit_short}, 7 phần, {len(sources)} ghi chú nguồn")
    return data


def check_facts(router, info, script_md, log=print):
    log("🔎 Nhờ AI kiểm tra lại sự kiện...")
    schema = {"type": "object", "required": ["issues"], "properties": {"issues": {"type": "array"}}}
    body = re.split(r"(?m)^##\s+GHI CHÚ NGUỒN", script_md)[0]
    chunks, cur = [], ""
    for part in re.split(r"(?m)^(?=## )", body):           # kịch bản dài: kiểm tra từng cụm phần (~6000 ký tự)
        if cur and len(cur) + len(part) > 6000:
            chunks.append(cur)
            cur = ""
        cur += part
    if cur.strip():
        chunks.append(cur)
    issues = []
    for i, ch in enumerate(chunks):
        if len(chunks) > 1:
            log(f"   🔎 đoạn {i + 1}/{len(chunks)}...")
        data = router.ask("checker", CHECK.format(topic=info["topic"], script=ch), schema=schema)
        issues += data.get("issues", [])
    return issues


# ------------------------------------------------------------------ script.md
def to_markdown(data, info):
    L = [f"# {data['title']}",
         f"<!-- country: {data.get('country')} | era: {data.get('era')} | year: {data.get('year') or ''} | minutes: {info['minutes']}"
         f" | language: {info.get('language', 'vi')}"
         f" | voice: {data.get('voice_suggestion', '')} -->", "",
         "> Sửa lời kể thoải mái. Giữ các dòng '## ' (tên phần) và dòng '<!-- mood: ... -->'. Phần sau '## GHI CHÚ NGUỒN' không được đọc.", ""]
    for s in data["sections"]:
        L.append(f"## {s['heading']}")
        tags = [f"mood: {s['mood']}"] if s.get("mood") else []
        if s.get("role"):
            tags.append(f"vai: {s['role']}")
        if tags:
            L.append(f"<!-- {' | '.join(tags)} -->")
        L.append("")
        for p in s["paragraphs"]:
            L += [p.strip(), ""]
    L += ["---", "## GHI CHÚ NGUỒN (không đọc)", ""]
    for src in data.get("sources", []):
        note = f" _({src['note']})_" if src.get("note") else ""
        L.append(f"- **{src['claim']}** — nguồn: {src['source']}{note}")
    if data.get("disputed"):
        L += ["", "### Điểm còn tranh cãi", ""] + [f"- {d}" for d in data["disputed"]]
    sec = data.get("secret") if isinstance(data.get("secret"), dict) else {}
    if data.get("big_question") or sec:
        L += ["", "### Khung giữ chân người xem (để bạn kiểm tra)", ""]
        if data.get("big_question"):
            L.append(f"- Câu hỏi lớn (đặt ở hook): {data['big_question']}")
        if data.get("answer"):
            L.append(f"- Câu trả lời (ở phần kết cục): {data['answer']}")
        if sec.get("what"):
            L.append(f"- Bí mật giấu đến cao trào: {sec['what']}")
        if sec.get("hint"):
            L.append(f"- Gợi ý ở hook: {sec['hint']}")
        if sec.get("reveal"):
            L.append(f"- Hé lộ ở cao trào: {sec['reveal']}")
        L.append("- Vai các phần (dòng <!-- vai: ... --> dưới mỗi tên phần): " + " → ".join(ROLE_NAMES))
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
        tags = {}
        for cm in re.findall(r"<!--(.*?)-->", rest, flags=re.S):
            for part in cm.split("|"):
                if ":" in part:
                    k, v = part.split(":", 1)
                    tags[k.strip().lower()] = v.strip()
        mood = tags.get("mood")
        role = tags.get("vai") or tags.get("role")
        rest = re.sub(r"<!--.*?-->", "", rest, flags=re.S)
        paras = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", rest)]
        paras = [p for p in paras if p and not p.startswith(">")]
        if paras:
            sections.append({"heading": heading, "mood": mood if mood in MOODS else None,
                             "role": role if role in ROLE_NAMES else None, "paragraphs": paras})
    return {"title": title, "meta": meta, "sections": sections}
