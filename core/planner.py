"""Bước 3 - Lập kế hoạch dựng plan.json (mục 4).

AI (planner) chia cảnh theo từng PHẦN LỚN của kịch bản (gộp ít lần gọi), mỗi cảnh ghi: lời đọc hay ngừng,
kiểu chữ, cảnh vẽ gì (theo thư viện thành phần), chuyển động, hạt, âm thanh. Kết quả được kiểm tra bằng
plan_schema.validate; sai thì gửi lỗi lại cho AI sửa (tối đa 3 lần).

Không có AI (--offline hoặc planner: rule): lập plan tự động theo mẫu cảnh từng nước.
"""
import difflib
import json
import random
import re

from assets_code import registry
from audio.music_synth import MOODS
from audio.sfx_synth import TAGS
from core.plan_schema import validate
from core.voice.text_norm import split_sentences
from render.map_anim import FEATURES, MARKERS
from render.motion import MOTIONS
from render.palettes import PALETTES
from render.particles import KINDS
from render.text_fx import STYLES

FOREIGN = {"vietnam": ["china"], "korea": ["japan", "china"], "japan": ["korea", "china"], "england": []}

PROMPT = """Bạn là đạo diễn hình ảnh cho video lịch sử "{title}" ({country_name}, {era}).
Toàn bộ hình được VẼ BẰNG CODE từ thư viện thành phần bên dưới (không có ảnh thật). Hãy chia đoạn kịch bản
thành các CẢNH và trả về JSON {{"scenes": [...]}} theo đúng định dạng plan.json.

ĐOẠN KỊCH BẢN CẦN CHIA (phần {part_no}/{part_total}, id cảnh bắt đầu từ {start_id}):
{text}

QUY TẮC:
- Lời đọc ("narration") của các cảnh ghép lại phải ĐÚNG NGUYÊN VĂN đoạn trên ({lang_name}), đúng thứ tự, không thêm bớt, không dịch.
  Mỗi cảnh narration ~{u0}–{u1} {unit} (≈ 4–7 giây), cắt ở ranh giới câu. Hình phải đổi mỗi 3–5 giây:
  cảnh dài hơn ~5 giây thì thêm "scene2" (cảnh thứ hai, khác góc nhìn) + "switch_at" (giây đổi) hoặc dùng motion rõ.
- HÌNH THEO VAI TỪNG PHẦN (vai ghi trong [tên phần | vai: ...]):
  * hook: vào thẳng khoảnh khắc gay cấn (lửa, thuyền vỡ, trống trận, tướng cận cảnh), cảnh ngắn, nhạc căng;
    KHÔNG vẽ lộ "bí mật" của video (vd bãi cọc, sơ đồ tide, mưu kế) — chỉ gợi (mặt nước đục, bóng tối dưới nước); cuối hook
    có câu hỏi lớn -> text_card word_by_word nhắc lại câu hỏi đó (≤ 10 chữ, duration 3). Sau phần hook là cảnh title.
  * sides: thẻ character cho TỪNG vị chỉ huy hai phe (role ally / enemy) khi được nhắc lần đầu; compare quân số / thuyền
    (có "note" về độ chắc chắn); map vị trí hai phe.
  * prep: map địa hình (sông, núi, đường tiếp tế), council trong hall khi bàn mưu, timeline nếu nhắc chuỗi sự kiện,
    foliage_frame khi nói mai phục; KHÔNG vẽ lộ phần mưu kế còn giữ bí mật.
  * turn: một cú đổi hình mạnh (flash_at + sfx boom, đổi palette / time_of_day), text_card slide_in nhấn sự kiện bước ngoặt.
  * battle: BẮT BUỘC map cho từng giai đoạn (mũi tên, khối quân), xen cảnh cận (commander, war_drum, thuyền cháy / vỡ),
    tide ĐÚNG LÚC lời kể hé lộ bí mật nếu trận dựa vào thủy triều; cảnh ngắn (cận dưới số {unit}), motion nhanh (zoom_in_fast, parallax), mood cao_trao.
  * outcome: compare thương vong (có note), text_card typewriter nêu câu trả lời cho câu hỏi lớn.
  * legacy: cảnh rộng tĩnh lặng (dawn / mist), motion chậm; câu hỏi mở cuối -> text_card typewriter.
- Chữ hiện trên hình ("text", "subtext", nhãn / chú thích bản đồ, "legend") viết bằng {lang_name}.
- Kiểu cảnh: title (MỘT lần: ngay SAU phần hook; không có phần hook thì là cảnh đầu) | narration | text_card (thẻ chữ, không lời, có "duration") |
  map (bản đồ động, có thể kèm narration) | pause (cảnh ngừng không lời, có "duration") |
  CẢNH ĐỒ HỌA (có thể kèm narration; không có thì cần "duration"), dữ liệu đặt trong trường cùng tên:
    timeline : {{"timeline": {{"title": "...", "events": [{{"year": "905", "text": "..."}}, ...tối đa 7], "highlight": chỉ số mốc chính}}}}
               — dùng khi lời kể nhắc chuỗi sự kiện / bối cảnh trước trận.
    character: {{"character": {{"name": "...", "subtitle": "năm sinh – năm mất hoặc chức vị", "role": "ally|enemy|neutral",
               "look": "general|king|scholar|admiral|monk|queen", "facts": ["≤ 3 ý ngắn"]}}}} — khi NHÂN VẬT QUAN TRỌNG xuất hiện lần đầu.
    compare  : {{"compare": {{"title": "...", "unit": "...", "items": [{{"label": "...", "value": số, "side": "enemy|ally"}}], "note": "..."}}}}
               — so sánh quân số / số thuyền; "note" BẮT BUỘC ghi độ chắc chắn ("theo sử cũ, chưa chắc chắn"). Không bịa số.
               CHỈ dùng khi lời kể có CON SỐ CỤ THỂ khác nhau giữa các bên; sử chỉ ghi "quá nửa", "rất đông"... thì
               KHÔNG dùng compare (thay bằng text_card hoặc cảnh minh họa).
    tide     : {{"tide": {{"label_high": "...", "label_low": "...", "label_stakes": "...", "fall_at": giây}}}}
               — sơ đồ mặt cắt thủy triều rút làm thuyền mắc cọc (trận dựa vào thủy triều).
- ĐA DẠNG GÓC NHÌN (quan trọng — người xem chán nếu toàn cảnh rộng sông nước):
  * Dùng đủ các cỡ cảnh: TOÀN (cảnh rộng) | TRUNG (war_drum, đoàn quân gần, nền "bank_near") |
    CẬN (commander: tướng đứng trên bờ, bóng lớn) | NỘI THẤT (nền "hall" + "council": bàn kế, hội họp) |
    NHÌN LÉN ("foliage_frame" cuối background: nhìn qua tán lá ra sông — mai phục) | ĐỒ HỌA (timeline, character, compare, tide) | map.
  * Không quá 2 cảnh liền cùng một kiểu nền (vd 2 cảnh sông rồi phải đổi sang cận / nội thất / đồ họa / bản đồ).
  * Cảnh có mặt nước ≤ một nửa số cảnh. Cứ ~5 cảnh nên có ít nhất 1 cảnh cận, nội thất hoặc đồ họa.
  * Đổi "motion", vị trí thành phần chính (trái / giữa / phải) giữa các cảnh liền nhau.
  * "time_of_day" đi theo THỜI ĐIỂM CÂU CHUYỆN, không đổi cho vui: các cảnh của cùng một sự kiện / một trận giữ cùng
    giờ (hoặc chuyển dần: day -> dusk -> night); chỉ nhảy giờ khi câu chuyện chuyển sang sự kiện khác.
  * Nhân vật phe địch dùng commander với "side": "enemy" (tự đội mũ nước địch), vd tướng Nam Hán.
- Thỉnh thoảng chèn text_card (năm: count_year; câu nói / ý chính: word_by_word hoặc typewriter; tên nhân vật / địa danh:
  slide_in) và map ở phần diễn biến (mũi tên hành quân).
- ĐÚNG NƯỚC, ĐÚNG THỜI KỲ: chỉ dùng thành phần của "common", "{country}"{foreign}. Năm {year}: không dùng
  thành phần có [năm ...] không bao gồm năm này; không có súng (musket) trước năm 1543.
- Toạ độ x, y theo tỉ lệ 0–1 của khung (y = điểm chạm nước / mặt đất; đường chân trời ~0.58).
  Người, ngựa là BÓNG; đám đông để xa. Cận cảnh người chỉ dùng commander / war_drum / council (bóng, không vẽ mặt).
  Phụ đề chiếm ~20% dưới khung: cảnh có lời đọc nên đặt thành phần chính ở y 0.6–0.8.
  Cảnh minh họa phải khớp NỘI DUNG lời đọc của chính cảnh đó (nói về thuyền thì vẽ thuyền, kỵ binh thì vẽ kỵ binh...).
- Bảng màu cả video: "{palette}" (cảnh nào cần khác thì ghi "palette" trong cảnh, tối đa 1 bảng phụ).
- "mood" (nhạc nền) chỉ ghi ở cảnh bắt đầu đổi tâm trạng: {moods}.

GIÁ TRỊ HỢP LỆ:
- motion: {motions}
- particles: {particles}
- text_style: {styles}
- sfx / sfx_at tag: {sfx}
- scene.time_of_day: dawn, day, dusk, night | scene.weather: clear, cloudy, overcast, rain, snow, fog
- map: toạ độ 0–1; có lời đọc thì giữ nhãn / mũi tên trong y < 0.75 (phụ đề ở dưới). map.features: {features} | map.markers kind: {markers} | arrows side: enemy (đỏ, bên tấn công) / ally (xanh)
- palettes: {palettes}

THƯ VIỆN THÀNH PHẦN (background dùng trong "background", còn lại dùng trong "elements"):
{catalog}

MẪU (rút gọn):
{example}

CÁC CẢNH TRƯỚC ĐÓ (để nối tiếp và tránh lặp): {prev}

CHỈ trả về JSON {{"scenes": [...]}}.
"""

EXAMPLE = {"scenes": [
    {"id": 1, "type": "title", "scene": {"time_of_day": "dusk", "weather": "clear", "background": ["sky", "mountains:3", "river"],
                                         "elements": [{"kind": "stakes_field", "x": 0.2, "y": 0.68, "density": "high", "tide": "high"},
                                                      {"kind": "boat_vn", "x": 0.7, "y": 0.62, "scale": 0.5, "count": 2}]},
     "motion": "zoom_in_slow", "particles": ["mist"], "text": "TRẬN BẠCH ĐẰNG", "subtext": "Năm 938",
     "text_style": "cinematic", "sfx": ["riser", "boom"], "duration": 4.5, "mood": "yen_binh"},
    {"id": 2, "type": "narration", "scene": {"time_of_day": "day", "background": ["sky", "clouds", "hills:2", "river", "bank_near:0.86"],
                                             "elements": [{"kind": "soldiers_vn", "x": 0.6, "y": 0.92, "width": 0.5, "layer": "front"}]},
     "motion": "parallax_right", "narration": "Năm 938, Ngô Quyền cho quân cắm cọc gỗ đầu bịt sắt...",
     "sfx_at": [{"t": 1.5, "tag": "tieng_tron"}]},
    {"id": 3, "type": "text_card", "text": "938", "text_style": "count_year", "count_from": 900, "subtext": "...", "duration": 3.5},
    {"id": 4, "type": "character", "character": {"name": "Ngô Quyền", "subtitle": "898 – 944", "role": "ally", "look": "general",
                                                 "facts": ["...", "..."]}, "narration": "..."},
    {"id": 5, "type": "narration", "scene": {"time_of_day": "night", "background": ["hall"], "elements": [{"kind": "council", "x": 0.5, "y": 0.84}]},
     "motion": "zoom_in_slow", "narration": "..."},
    {"id": 6, "type": "narration", "scene": {"background": ["sky", "mountains:2", "river", "bank_near:0.93"],
                                             "elements": [{"kind": "junk_ship", "x": 0.7, "y": 0.66, "scale": 0.45, "count": 3, "flip": True},
                                                          {"kind": "commander", "x": 0.22, "y": 0.99, "pose": "point"}]},
     "motion": "parallax_right", "narration": "..."},
    {"id": 7, "type": "map", "map": {"features": ["river", "coast_right", "islands"],
                                     "labels": [{"text": "Sông Bạch Đằng", "at": [0.2, 0.3], "style": "water"}],
                                     "arrows": [{"side": "enemy", "path": [[0.95, 0.75], [0.6, 0.55], [0.35, 0.38]], "start": 1.8, "dur": 2.4,
                                                 "label": "Thuyền quân Nam Hán"}],
                                     "markers": [{"kind": "stakes", "at": [0.47, 0.44], "start": 0.6},
                                                 {"kind": "clash_x", "at": [0.47, 0.44], "start": 6.9}],
                                     "legend": {"enemy": "Quân Nam Hán", "ally": "Quân Ngô Quyền"}},
     "narration": "..."}]}

COUNTRY_NAMES = {"vietnam": "Việt Nam", "korea": "Triều Tiên / Hàn Quốc", "japan": "Nhật Bản", "england": "Anh"}
DEFAULT_PALETTE = {"vietnam": "hoang_hon_do", "korea": "binh_minh_xanh", "japan": "suong_mu_xam", "england": "suong_mu_xam"}


def _norm(s):
    return re.sub(r"\s+", " ", s).strip()


def coverage(plan_text, script_text):
    return difflib.SequenceMatcher(None, _norm(plan_text), _norm(script_text), autojunk=False).ratio()


def batches(sections, max_words=450, lang="vi"):
    """Gộp các phần kịch bản thành lô ~450 chữ (≈ 1000 ký tự Hàn / Nhật) để ít lần gọi AI."""
    from core import lang as L
    out, cur, n = [], [], 0
    for s in sections:
        w = sum(L.count(p, lang) for p in s["paragraphs"])
        if cur and n + w > max_words:
            out.append(cur)
            cur, n = [], 0
        cur.append(s)
        n += w
    if cur:
        out.append(cur)
    return out


def plan_with_ai(router, script, meta, cfg, log=print):
    registry.load_all()
    country = meta.get("country") or "vietnam"
    year = int(meta["year"]) if str(meta.get("year", "")).strip().lstrip("-").isdigit() else None
    palette = meta.get("palette") or DEFAULT_PALETTE.get(country, "hoang_hon_do")
    allowed = ["common", country] + FOREIGN.get(country, []) + ["custom"]
    catalog = registry.catalog_text(allowed)
    from core import lang as L
    lg = meta.get("language", "vi")
    LI = L.get(lg)
    lots = batches(script["sections"], max_words=450 if lg in ("vi", "en") else 1000, lang=lg)
    scenes = []
    for i, lot in enumerate(lots):
        text = "\n\n".join(f"[{s['heading']}" + (f" | vai: {s['role']}" if s.get("role") else "")
                             + (f" | mood: {s['mood']}" if s.get("mood") else "") + "]\n" + "\n".join(s["paragraphs"]) for s in lot)
        from core.diversify import family
        prev = json.dumps([{"id": s["id"], "type": s["type"], "kiểu_nền": family(s), "chính": (s.get("scene") or {}).get("elements", [{}])[:1]}
                           for s in scenes[-6:]],
                          ensure_ascii=False) if scenes else (
            "(đây là phần đầu: phần hook kể ngay từ cảnh 1, cảnh title đặt ngay sau phần hook)"
            if lot and lot[0].get("role") == "hook" else "(đây là phần đầu: cảnh 1 phải là title)")
        fr = FOREIGN.get(country, [])
        prompt = PROMPT.format(lang_name=LI["name"], u0=LI["scene_units"][0], u1=LI["scene_units"][1], unit=LI["unit"],
                               title=script["title"], country_name=COUNTRY_NAMES.get(country, country), era=meta.get("era", ""),
                               part_no=i + 1, part_total=len(lots), start_id=len(scenes) + 1, text=text, country=country,
                               foreign=("" if not fr else " và (cho phe địch) " + ", ".join(f'"{x}"' for x in fr)), year=year or "?",
                               palette=palette, moods=", ".join(MOODS), motions=", ".join(MOTIONS), particles=", ".join(KINDS),
                               styles=", ".join(STYLES), sfx=", ".join(TAGS), features=", ".join(FEATURES), markers=", ".join(MARKERS),
                               palettes=", ".join(PALETTES), catalog=catalog, example=json.dumps(EXAMPLE, ensure_ascii=False), prev=prev)
        lot_text = " ".join(p for s in lot for p in s["paragraphs"])
        start_id = len(scenes) + 1

        def validator(data, lot_text=lot_text, start_id=start_id):
            sc = data.get("scenes") if isinstance(data, dict) else None
            if not isinstance(sc, list) or not sc:
                return ["Thiếu mảng 'scenes'"]
            for k, s in enumerate(sc):
                s["id"] = start_id + k
            E, W = validate({"title": script["title"], "country": country, "palette": palette, "scenes": sc}, year=year)
            E += [w for w in W if "cột bằng nhau" in w or "số 'minh họa'" in w]   # lúc lập plan thì bắt AI sửa luôn
            got = " ".join(s.get("narration", "") for s in sc)
            cov = coverage(got, lot_text)
            if cov < 0.9:
                E.append(f"Lời đọc các cảnh chỉ khớp {cov:.0%} với đoạn kịch bản — phải chép ĐÚNG NGUYÊN VĂN, đủ, đúng thứ tự")
            return E

        log(f"🎬 Lập plan phần {i + 1}/{len(lots)} ({L.count(lot_text, lg)} {LI['unit'].split(' (')[0]})...")
        data = router.ask("planner", prompt, schema={"type": "object", "required": ["scenes"]}, validator=validator)
        scenes += data["scenes"]
    plan = {"title": script["title"], "country": country, "era": meta.get("era", ""), "year": year, "palette": palette,
            "language": lg, "voice": meta.get("voice_name"), "scenes": scenes}
    return plan


# ======================================================================== lập plan không cần AI
TEMPLATES = {   # (từ khoá trong lời kể, mô tả cảnh) — y thành phần chính ≤ 0.8 để không bị phụ đề che
    "vietnam": [
        ("thuyền chiến|thủy quân|đánh thủy|chiến thuyền|ra biển", {"background": ["sky", "mountains:3", "river"], "elements": [{"kind": "boat_vn", "x": 0.68, "y": 0.66, "count": 2}]}),
        ("quân|binh|lính|tướng|xuất quân|hành quân", {"background": ["sky", "clouds", "hills:2", "field"], "elements": [{"kind": "soldiers_vn", "x": 0.5, "y": 0.78, "width": 0.7, "rows": 3}, {"kind": "flag_vn", "x": 0.2, "y": 0.76, "scale": 0.7}]}),
        ("cọc|bãi cọc|thủy triều|triều", {"background": ["sky", "mountains:2", "river", "reeds"], "elements": [{"kind": "stakes_field", "x": 0.5, "y": 0.72, "width": 1.1, "tide": "low"}]}),
        ("thành|kinh đô|cổ loa|đóng đô|thăng long", {"background": ["sky", "forest", "plain"], "elements": [{"kind": "citadel_vn", "x": 0.55, "y": 0.66, "width": 0.8}, {"kind": "torch", "x": 0.2, "y": 0.8, "count": 2, "spacing": 0.6}]}),
        ("voi|kỵ|tượng binh", {"background": ["sky", "mountains:2", "plain"], "elements": [{"kind": "war_elephant", "x": 0.3, "y": 0.78}, {"kind": "soldiers_vn", "x": 0.68, "y": 0.8, "width": 0.5}]}),
        ("làng|dân|nhân dân|đồng ruộng|cày", {"background": ["sky", "forest:bamboo", "field"], "elements": [{"kind": "village_gate", "x": 0.5, "y": 0.78}]}),
        ("giặc|quân địch|nam hán|nguyên|minh|tống|xâm lược", {"background": ["sky", "mountains:2", "river"], "elements": [{"kind": "junk_ship", "x": 0.5, "y": 0.66, "count": 3, "spacing": 0.28}]}),
        ("đình|lễ|tế|tưởng nhớ|đền", {"background": ["sky", "hills", "plain"], "elements": [{"kind": "dinh_roof", "x": 0.5, "y": 0.76}, {"kind": "tree", "x": 0.15, "y": 0.78}]}),
    ],
    "korea": [
        ("thuyền rùa|geobukseon|quy thuyền", {"background": ["sky", "mountains:3", "sea", "islands"], "elements": [{"kind": "turtle_ship", "x": 0.35, "y": 0.7}, {"kind": "panokseon", "x": 0.72, "y": 0.66, "scale": 0.7}]}),
        ("vua|triều đình|cung|hoàng|kinh thành", {"background": ["sky", "mountains:2", "plain"], "elements": [{"kind": "joseon_palace", "x": 0.5, "y": 0.7}]}),
        ("thành|phòng thủ|lính|quân|binh", {"background": ["sky", "hills:2", "plain"], "elements": [{"kind": "fortress_wall_kr", "x": 0.5, "y": 0.68}, {"kind": "soldiers_kr", "x": 0.5, "y": 0.79, "width": 0.7}]}),
        ("nhật|địch|xâm lược|hạm đội nhật|wakisaka", {"background": ["sky", "mountains:2", "sea"], "elements": [{"kind": "atakebune", "x": 0.6, "y": 0.66, "count": 3, "spacing": 0.25, "flip": True}]}),
        ("hạm đội|chiến thuyền|biển|đảo|eo biển|panokseon", {"background": ["sky", "clouds", "mountains:2", "sea", "islands"], "elements": [{"kind": "panokseon", "x": 0.5, "y": 0.68, "count": 3, "spacing": 0.3}, {"kind": "flag_kr", "x": 0.12, "y": 0.8, "scale": 0.7}]}),
    ],
    "japan": [
        ("lâu đài|thành|osaka|edo|daimyo", {"background": ["sky", "mountains:3", "plain"], "elements": [{"kind": "tenshu", "x": 0.68, "y": 0.64}]}),
        ("samurai|tướng|chỉ huy|kiếm", {"background": ["sky", "hills:2", "plain"], "elements": [{"kind": "samurai", "x": 0.4, "y": 0.78, "width": 0.6}, {"kind": "nobori_row", "x": 0.4, "y": 0.74, "width": 0.5}]}),
        ("súng|hỏa mai|bộ binh|ashigaru|quân", {"background": ["sky", "mountains:2", "field"], "elements": [{"kind": "ashigaru", "x": 0.5, "y": 0.8, "width": 0.8, "rows": 4}]}),
        ("đền|chùa|cầu nguyện|thần", {"background": ["sky", "forest:pine", "plain"], "elements": [{"kind": "torii", "x": 0.5, "y": 0.78}]}),
        ("thuyền|biển|hải quân", {"background": ["sky", "mountains:2", "sea"], "elements": [{"kind": "atakebune", "x": 0.55, "y": 0.66, "count": 2, "spacing": 0.35}]}),
    ],
    "england": [
        ("lâu đài|thành|vương quốc|vua", {"background": ["sky", "hills:2", "plain"], "elements": [{"kind": "stone_castle", "x": 0.62, "y": 0.62, "scale": 0.8}]}),
        ("kỵ binh|hiệp sĩ|ngựa|xông", {"background": ["sky", "clouds", "hills:2", "plain"], "elements": [{"kind": "knights", "x": 0.35, "y": 0.78}, {"kind": "banner_en", "x": 0.12, "y": 0.78, "scale": 0.7}]}),
        ("khiên|tường khiên|bộ binh|anglo|saxon|đồi", {"background": ["sky", "hills", "plain"], "elements": [{"kind": "shield_wall", "x": 0.5, "y": 0.78, "width": 0.8}]}),
        ("thuyền|biển|vượt eo|viking|na uy|đổ bộ", {"background": ["sky", "mountains:2", "sea"], "elements": [{"kind": "longship", "x": 0.5, "y": 0.68, "count": 3, "spacing": 0.3}]}),
        ("cung|tên|bắn", {"background": ["sky", "hills:2", "plain"], "elements": [{"kind": "archers_en", "x": 0.3, "y": 0.8, "width": 0.4}, {"kind": "archers_volley", "x": 0.3, "y": 0.72, "to": [0.8, 0.78]}]}),
    ],
}


# cảnh cận / nội thất / nhìn qua lá — dùng chung mọi nước (mũ, áo tự theo nước)
CLOSE_TEMPLATES = [
    ("tướng|chỉ huy|ra lệnh|hạ lệnh|thống lĩnh|general|commander|ordered|장군|명령|지휘|将|命じ|指揮",
     {"background": ["sky", "mountains:2", "river", "bank_near:0.93"],
      "elements": [{"kind": "commander", "x": 0.24, "y": 0.99, "pose": "point"}]}),
    ("trống|hiệu lệnh|xung trận|tiến công|tấn công|drum|attack|charge|북|공격|太鼓|攻撃|突撃",
     {"background": ["sky", "hills:2", "plain"], "elements": [{"kind": "war_drum", "x": 0.3, "y": 0.86},
                                                            {"kind": "army", "x": 0.68, "y": 0.68, "width": 0.5, "rows": 3}]}),
    ("bàn|kế|mưu|họp|bàn bạc|hội nghị|kế hoạch|plan|council|strategy|계책|회의|작전|軍議|作戦|策",
     {"background": ["hall"], "time_of_day": "night", "elements": [{"kind": "council", "x": 0.5, "y": 0.84}]}),
    ("mai phục|phục binh|ẩn nấp|chờ đợi|lén|ambush|hidden|waited|매복|숨어|伏兵|待ち伏せ|潜",
     {"background": ["sky", "mountains:2", "river", "foliage_frame"], "elements": []}),
]
TIDE_KW = "thủy triều|triều rút|triều xuống|nước rút|tide|조수|썰물|潮"


def _era_ok(tmpl, year):
    if not year:
        return True
    for el in tmpl.get("elements", []):
        c = registry.get(el["kind"])
        if c and not (c.era[0] <= year <= c.era[1]):
            return False
    return True


KW_EXTRA = {   # từ khoá Anh / Hàn / Nhật theo thành phần chính của mẫu cảnh
    "ship": "ship|fleet|navy|boat|sail|sea|배|함대|수군|바다|함선|船|艦隊|水軍|海",
    "turtle_ship": "turtle|거북선|亀甲船",
    "people": "army|troops|soldier|march|warrior|군사|병사|군대|장군|軍|兵|武士|侍",
    "stakes_field": "stake|tide|말뚝|조수|杭|潮",
    "building": "castle|fort|capital|king|palace|wall|city|성|궁|왕|성벽|城|宮|王|都",
    "cavalry": "cavalry|horse|knight|charge|elephant|기병|말|騎馬|騎兵|馬",
    "archers": "arrow|archer|bow|화살|궁수|활|矢|弓",
    "village": "village|people|temple|shrine|peasant|마을|백성|절|村|民|神社|寺",
}


def _extra_kw(t):
    kinds = [e["kind"] for e in t.get("elements", [])]
    c = registry.get(kinds[0]) if kinds else None
    out = []
    if c:
        out.append(KW_EXTRA.get(c.category, ""))
    for kd in kinds:
        if kd in ("turtle_ship", "stakes_field"):
            out.append(KW_EXTRA[kd])
        if kd in ("knights", "cavalry", "war_elephant"):
            out.append(KW_EXTRA["cavalry"])
        if kd in ("archers_en", "archers_volley"):
            out.append(KW_EXTRA["archers"])
        if kd in ("village_gate", "dinh_roof", "torii"):
            out.append(KW_EXTRA["village"])
    return "|".join(x for x in out if x)


def pick_template(tmpls, text, k, last):
    """Chọn mẫu cảnh có nhiều từ khoá trùng lời kể nhất; hoà thì xoay vòng; tránh lặp mẫu vừa dùng."""
    low = text.lower()
    best, best_s = None, -1
    for i in range(len(tmpls)):
        j = (k + i) % len(tmpls)
        kw, t = tmpls[j]
        kw = kw + "|" + _extra_kw(t)
        sc = sum(1 for w in kw.split("|") if w and w in low)
        if j == last:
            sc -= 0.5
        if sc > best_s:
            best, best_s = j, sc
    return best


MOTION_CYCLE = ["zoom_in_slow", "parallax_right", "pan_left", "zoom_out_slow", "parallax_left", "pan_right"]
FAST_CYCLE = ["zoom_in_fast", "parallax_right", "zoom_in_slow", "parallax_left"]
TOD_CYCLE = ["dusk", "day", "dusk", "night", "dawn"]


def plan_rule_based(script, meta, seed=1):
    """Lập plan đơn giản không cần AI (để chạy thử / khi hết lượt AI)."""
    rr = random.Random(seed)
    registry.load_all()
    country = meta.get("country") if meta.get("country") in TEMPLATES else "vietnam"
    year_ = int(meta["year"]) if str(meta.get("year", "")).strip().lstrip("-").isdigit() else None
    tmpls = ([t for t in TEMPLATES[country] if _era_ok(t[1], year_)] or TEMPLATES[country]) + CLOSE_TEMPLATES
    palette = meta.get("palette") or DEFAULT_PALETTE.get(country, "hoang_hon_do")
    year = int(meta["year"]) if str(meta.get("year", "")).strip().lstrip("-").isdigit() else None
    title = script["title"]
    from core import lang as L
    lg = meta.get("language", "vi")
    limit = L.get(lg)["scene_units"][1]
    scenes = []
    first = dict(tmpls[pick_template(tmpls, title, 0, -1)][1])
    secs = script["sections"]
    hook_first = bool(secs) and secs[0].get("role") == "hook"   # bố cục giữ chân: kể hook trước, tiêu đề sau
    title_sc = {"id": 1, "type": "title", "scene": dict(first, time_of_day="dusk"), "motion": "zoom_in_slow", "particles": ["mist"],
                   "text": re.sub(r"[\s,:;–-]*(năm|NĂM|in|IN)?\s*\d+\S*$", "", title).strip(" ,:;–-").upper() or title, "subtext": L.ui(lg, "year", y=year) if year else meta.get("era", ""),
                   "text_style": "cinematic", "duration": 5.0, "mood": "yen_binh"}
    if not hook_first:
        scenes.append(title_sc)
    from core.script_writer import ROLES
    role_mood = {r[0]: r[2] for r in ROLES}
    k = 0
    last_t = -1
    used_tide = False
    for si, sec in enumerate(secs):
        if si == 1 and hook_first:
            title_sc.pop("mood", None)
            scenes.append(title_sc)
        if si == 1 and year:
            scenes.append({"id": len(scenes) + 1, "type": "text_card", "text": str(year), "text_style": "count_year",
                           "count_from": max(0, year - 40), "subtext": meta.get("era", ""), "particles": ["embers"], "duration": 3.5})
        if si > 0:
            scenes.append({"id": len(scenes) + 1, "type": "text_card", "text": sec["heading"], "text_style": "slide_in",
                           "duration": 2.8, "particles": ["dust"]})
        sents = [s for p in sec["paragraphs"] for s in split_sentences(p, lang=lg)]
        groups, cur, n = [], [], 0
        for s in sents:
            w = L.count(s, lg)
            if cur and n + w > limit:
                groups.append(cur)
                cur, n = [], 0
            cur.append(s)
            n += w
        if cur:
            groups.append(cur)
        for gi, group in enumerate(groups):
            gtext = " ".join(group).lower()
            if not used_tide and any(w in gtext for w in TIDE_KW.split("|")):
                used_tide = True
                scenes.append({"id": len(scenes) + 1, "type": "tide", "tide": {},
                               "narration": ("" if lg == "ja" else " ").join(group)})
                continue
            ti = pick_template(tmpls, " ".join(group), k, last_t)
            last_t = ti
            t = tmpls[ti][1]
            tod = TOD_CYCLE[k % len(TOD_CYCLE)]
            parts = ["embers"] if tod == "night" else ["mist"] if tod == "dawn" else []
            fast = sec.get("role") in ("hook", "battle")
            sc = {"id": len(scenes) + 1, "type": "narration", "scene": dict(t, time_of_day=tod),
                  "motion": (FAST_CYCLE if fast else MOTION_CYCLE)[k % len(FAST_CYCLE if fast else MOTION_CYCLE)], "particles": parts,
                  "narration": ("" if lg == "ja" else " ").join(group)}
            mood = sec.get("mood") or role_mood.get(sec.get("role"))
            if gi == 0 and mood:
                sc["mood"] = mood
            scenes.append(sc)
            k += 1
    if title_sc not in scenes:
        scenes.insert(0, title_sc)
    for i, sc in enumerate(scenes):
        sc["id"] = i + 1
    plan = {"title": title, "country": country, "era": meta.get("era", ""), "year": year, "palette": palette,
            "language": lg, "voice": meta.get("voice_name"), "scenes": scenes}
    return plan
