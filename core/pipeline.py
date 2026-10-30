"""Quy trình tổng thể (mục 3):
  1. phân tích đầu vào  2. viết kịch bản (AI)  3. lập plan.json (AI)  4. tạo giọng (OmniVoice)
  5. dựng hình + trộn âm  6. xuất video_final.mp4 + youtube.txt
Người dùng có thể dừng sau bước 2 hoặc 3 để duyệt / sửa, rồi chạy tiếp (python main.py continue <dự án>).
"""
import json
import os
import shutil
import sys
import time

from core import config as config_mod
from core import export, input_parser, plan_schema, planner, script_writer
from core.config import ROOT
from core.llm.base import LLMError, Router
from core.voice import text_norm

PROJECTS = os.path.join(ROOT, "projects")
STEPS = ["parsed", "script", "plan", "voice", "render"]


class Project:
    def __init__(self, path):
        if not os.path.isabs(path) and not os.path.isdir(path):
            path = os.path.join(PROJECTS, path)
        self.dir = os.path.abspath(path)
        if not os.path.isdir(self.dir):
            raise FileNotFoundError(f"Không tìm thấy dự án '{path}'. Các dự án có: {', '.join(list_projects()) or '(chưa có)'}")
        for d in ("logs", "cache", "output", "voice"):
            os.makedirs(os.path.join(self.dir, d), exist_ok=True)

    def p(self, *a):
        return os.path.join(self.dir, *a)

    def load(self, name, default=None):
        fp = self.p(name)
        if not os.path.exists(fp):
            return default
        with open(fp, encoding="utf-8") as f:
            return json.load(f) if name.endswith(".json") else f.read()

    def save(self, name, data):
        fp = self.p(name)
        tmp = fp + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            if name.endswith(".json"):
                f.write(dumps_plan(data) if name == "plan.json" else json.dumps(data, ensure_ascii=False, indent=2))
            else:
                f.write(data)
        os.replace(tmp, fp)
        return fp

    @property
    def state(self):
        return self.load("state.json", {"done": [], "approved": []})

    def mark(self, step, approved=False):
        st = self.state
        if step not in st["done"]:
            st["done"].append(step)
        if approved and step not in st["approved"]:
            st["approved"].append(step)
        self.save("state.json", st)

    @property
    def info(self):
        return self.load("input.json", {})


def dumps_plan(plan):
    """JSON dễ đọc: mỗi cảnh xuống dòng, các mảng nhỏ (toạ độ, danh sách ngắn) trên một dòng."""
    s = json.dumps(plan, ensure_ascii=False, indent=2)
    import re
    s = re.sub(r"\[\s+([^\[\]{}]{0,80}?)\s+\]", lambda m: "[" + re.sub(r",\s+", ", ", m.group(1)) + "]", s)
    s = re.sub(r"\[\s+(\[[^\[\]]*\](?:,\s+\[[^\[\]]*\])*)\s+\]", lambda m: "[" + re.sub(r",\s+\[", ", [", m.group(1)) + "]", s)
    return s + "\n"


def _lang_name(code):
    from core import lang as L
    return L.get(code)["name"]


def list_projects():
    if not os.path.isdir(PROJECTS):
        return []
    return sorted(d for d in os.listdir(PROJECTS) if os.path.isdir(os.path.join(PROJECTS, d)))


def pronunciation(proj=None, lang="vi"):
    """Từ điển phát âm chung (theo ngôn ngữ) + của riêng dự án."""
    name = os.path.basename(text_norm.pronunciation_files(ROOT, lang))
    return text_norm.load_pronunciation(os.path.join(ROOT, name), proj.p(name) if proj else None)


# ====================================================================== các bước
def new_project(line, cfg, log=print, name=None, lang=None):
    info = input_parser.parse(line, cfg.get("default_minutes", 10), cfg.get("narration_language", "vi"))
    if lang:
        from core import lang as L
        info["language"] = L.code(lang)
    slug = name or info["slug"]
    d = os.path.join(PROJECTS, slug)
    os.makedirs(d, exist_ok=True)
    proj = Project(d)
    if not os.path.exists(proj.p("input.json")):
        proj.save("input.json", info)
    log(f"📁 Dự án: {proj.dir}")
    log(f"   Chủ đề: {info['topic']} | {info['minutes']:g} phút | nước: {input_parser.COUNTRY_NAMES.get(info['country'], 'chưa rõ (AI sẽ xác định)')}"
        f"{' | ' + info['era'] if info['era'] else ''} | lời kể: {_lang_name(info.get('language'))}")
    proj.mark("parsed")
    return proj


def step_script(proj, cfg, router, log=print, offline=False):
    info = proj.info
    if offline:
        raise RuntimeError("Chế độ --offline không viết được kịch bản. Hãy tự viết script.md theo mẫu samples/bach_dang_938/script.md")
    data = script_writer.write(router, info, cfg, log)
    if data.get("country") in input_parser.COUNTRY_NAMES:
        info["country"] = data["country"]
    info["era"] = data.get("era") or info.get("era")
    info["year"] = data.get("year") or info.get("year")
    proj.save("input.json", info)
    proj.save("script.json", data)
    md = script_writer.to_markdown(data, info)
    proj.save("script.md", md)
    log(f"   ✔ đã lưu {proj.p('script.md')}")
    if cfg.get("check_facts", True):
        try:
            issues = script_writer.check_facts(router, info, md, log)
            L = ["# Kiểm tra sự kiện (do AI, chỉ để tham khảo)", ""]
            for it in issues:
                L.append(f"- **[{it.get('severity', '?')}]** \"{it.get('quote', '')}\"\n  - Vấn đề: {it.get('problem', '')}\n  - Gợi ý: {it.get('suggestion', '')}")
            if not issues:
                L.append("Không thấy vấn đề lớn.")
            proj.save("script_check.md", "\n".join(L) + "\n")
            log(f"   ✔ {len(issues)} điểm cần xem lại -> {proj.p('script_check.md')}")
        except LLMError as e:
            log(f"   ⚠️  bỏ qua bước kiểm tra sự kiện: {e}")
    proj.mark("script")


def script_meta(proj):
    md = proj.load("script.md")
    if not md:
        raise RuntimeError(f"Chưa có {proj.p('script.md')}")
    parsed = script_writer.parse_markdown(md)
    info = proj.info
    meta = dict(language=parsed["meta"].get("language") or info.get("language") or "vi",
                country=parsed["meta"].get("country") or info.get("country") or "vietnam",
                era=parsed["meta"].get("era") or info.get("era", ""), year=parsed["meta"].get("year") or info.get("year"))
    if not parsed["title"]:
        parsed["title"] = info.get("topic", "")
    return parsed, meta


def step_plan(proj, cfg, router, log=print, offline=False):
    parsed, meta = script_meta(proj)
    if offline or cfg.get("planner") == "rule":
        log("🎬 Lập plan.json tự động theo mẫu (không dùng AI)...")
        plan = planner.plan_rule_based(parsed, meta)
    else:
        try:
            plan = planner.plan_with_ai(router, parsed, meta, cfg, log)
        except LLMError as e:
            log(f"⚠️  AI không lập được plan ({e}). Dùng cách lập plan tự động theo mẫu.")
            plan = planner.plan_rule_based(parsed, meta)
    plan = diversify_plan(plan, cfg, log)
    script_text = " ".join(p for s in parsed["sections"] for p in s["paragraphs"])
    plan_text = " ".join(s.get("narration", "") for s in plan["scenes"])
    cov = planner.coverage(plan_text, script_text)
    if cov < 0.95:
        log(f"⚠️  Lời đọc trong plan chỉ khớp {cov:.0%} với script.md — kiểm tra lại có thiếu đoạn nào không.")
    proj.save("plan.json", plan)
    E, W = plan_schema.validate(plan)
    log(plan_schema.format_report(E, W))
    log(f"   ✔ {len(plan['scenes'])} cảnh -> {proj.p('plan.json')}")
    proj.mark("plan")


def diversify_plan(plan, cfg, log=print):
    """Tự đa dạng góc nhìn (không đổi lời đọc). Tắt bằng  plan_diversify: false  trong config.yaml."""
    if not cfg.get("plan_diversify", True):
        return plan
    from core.diversify import diversify
    plan, notes = diversify(plan)
    if notes:
        log(f"🎨 Đa dạng hóa góc nhìn: {len(notes)} chỉnh sửa")
        for n in notes[:12]:
            log(f"   - {n}")
        if len(notes) > 12:
            log(f"   ... và {len(notes) - 12} chỉnh sửa khác")
    return plan


def step_diversify(proj, cfg, log=print):
    """Lệnh riêng cho dự án đã có plan.json (không cần AI). Lưu bản cũ thành plan_truoc_da_dang.json."""
    plan = proj.load("plan.json")
    if plan is None:
        raise RuntimeError(f"Chưa có {proj.p('plan.json')}")
    proj.save("plan_truoc_da_dang.json", plan)
    plan = diversify_plan(plan, dict(cfg, plan_diversify=True), log)
    proj.save("plan.json", plan)
    E, W = plan_schema.validate(plan)
    log(plan_schema.format_report(E, W))
    log(f"   ✔ Đã lưu {proj.p('plan.json')} (bản cũ: plan_truoc_da_dang.json). Dựng lại video để xem.")


def load_plan(proj, log=print, strict=True):
    plan = proj.load("plan.json")
    if plan is None:
        raise RuntimeError(f"Chưa có {proj.p('plan.json')}")
    E, W = plan_schema.validate(plan)
    if E or W:
        log(plan_schema.format_report(E, W))
    if E and strict:
        raise RuntimeError("plan.json còn lỗi, hãy sửa rồi chạy lại (python main.py validate <dự án> để xem lỗi).")
    return plan


def step_voice(proj, cfg, router, log=print, draft=False, auto=False, ask=input, voice_name=None):
    from core.voice import voice_library as VL
    from core.voice.omnivoice_engine import OmniVoiceEngine, VoiceUnavailable, estimate_timings, generate_project_voice
    plan = load_plan(proj, log)
    lang = plan.get("language", "vi")
    pron = pronunciation(proj, lang)
    if not OmniVoiceEngine.installed():
        log("⚠️  Chưa cài OmniVoice — dựng video KHÔNG có giọng (thời lượng ước tính, vẫn có phụ đề).")
        log("   Cài theo HUONG_DAN_CAI_DAT.md mục 'Giọng đọc', rồi chạy: python main.py voice-gen " + os.path.basename(proj.dir))
        proj.save(os.path.join("voice", "timings.json"), estimate_timings(plan, pron))
        proj.mark("voice")
        return
    voice = VL.Voice(voice_name) if voice_name else VL.pick_voice(plan.get("voice"), plan.get("country"), cfg, lang)
    if voice is None:
        log("Chưa chọn giọng -> AI tự mô tả giọng hợp chủ đề, tạo 3 ứng viên và tự chọn bản đọc rõ nhất (không cần bạn làm gì).")
        hint = (proj.load("script.json") or {}).get("voice_suggestion", "")
        try:
            instructs = VL.suggest_instructs(router, plan["title"], hint, lang) if router else VL.fallback_instructs()
        except LLMError as e:
            log(f"   ⚠️  {e} — dùng mô tả giọng mặc định")
            instructs = VL.fallback_instructs()
        log("⚠️  Voice design của OmniVoice học chủ yếu tiếng Trung / Anh; tiếng Việt có thể kém ổn định. "
            "Nếu nghe chưa tốt, nên dùng giọng thật của bạn: python main.py voice add <tên> --file giong.mp3")
        log("   Mô tả giọng AI đề xuất: " + " | ".join(instructs))
        cands = VL.design_candidates(instructs, cfg, log, lang=lang)
        best = VL.choose(cands, auto=True, log=log)          # luôn tự chọn, không hỏi
        name = "tu_dong_" + os.path.basename(proj.dir)
        VL.save_design(name, best, mo_ta=f"AI tự thiết kế cho '{plan['title']}': {best['instruct']}")
        # giữ lại cả 3 ứng viên trong dự án để nghe / đổi sau nếu muốn
        for i, c in enumerate(cands, 1):
            try:
                shutil.copyfile(c["path"], proj.p("voice", f"ung_vien_{i}.wav"))
            except OSError:
                pass
        log(f"   ✔ Đã lưu giọng '{name}' ({best['instruct']}). 3 ứng viên để nghe lại: {os.path.join(proj.p('voice'), 'ung_vien_*.wav')}")
        if lang != "vi":
            VL.set_default(name, language=lang)
        elif not VL.defaults().get("default"):
            VL.set_default(name)
        voice = VL.Voice(name)
    log(f"🎙  Giọng: {voice.name} ({voice.meta.get('loai')})")
    try:
        generate_project_voice(plan, proj.dir, voice, cfg, pron, draft=draft, log=log)
    except VoiceUnavailable as e:
        log(f"⚠️  {e}")
        proj.save(os.path.join("voice", "timings.json"), estimate_timings(plan, pron))
    proj.mark("voice")


def timeline_for(proj, plan, cfg):
    from render.renderer import build_timeline
    timings = proj.load(os.path.join("voice", "timings.json"))
    if timings:     # mốc cũ không khớp lời mới -> bỏ cảnh đó (ước lượng lại)
        for sc in plan["scenes"]:
            tm = timings.get("scenes", {}).get(str(sc["id"]))
            if tm and sc.get("narration"):
                disp = " ".join(s.get("display", "") for s in tm["sentences"])
                if text_norm._nfc(disp.split()[0] if disp else "") != text_norm._nfc((sc["narration"].split() or [""])[0]) or \
                        len(disp.split()) != len(sc["narration"].split()):
                    timings["scenes"].pop(str(sc["id"]), None)
    return build_timeline(plan, timings, int(cfg["render"].get("fps", 30)))


def step_render(proj, cfg, log=print, draft=False, quality=None):
    from audio import mixer
    from render.renderer import mux, render_video, scene_events
    plan = load_plan(proj, log)
    tl = timeline_for(proj, plan, cfg)
    total = tl[-1]["start"] + tl[-1]["dur"]
    log(f"🎞  Dựng video {total / 60:.1f} phút, {len(tl)} cảnh...")
    rcfg = dict(cfg["render"])
    t0 = time.time()
    silent = render_video(plan, tl, proj.dir, rcfg, draft=draft, log=log, quality=quality)
    log(f"🔉 Trộn âm thanh: giọng + tiếng động + nhạc nền tự tạo cho {total / 60:.1f} phút (máy đang tính, có thể mất vài phút)...")
    clips, events, beds, moods = [], [], [], []
    for e in tl:
        for (t, f) in e["clips"]:
            clips.append((e["start"] + t, proj.p(f)))
        ev, bd = scene_events(e, plan)
        events += [(e["start"] + t, tag, g) for (t, tag, g) in ev]
        beds += [(e["start"] + a, e["start"] + b, tag, g) for (a, b, tag, g) in bd]
        if moods and moods[-1][2] == e["mood"]:
            moods[-1] = (moods[-1][0], e["start"] + e["dur"], e["mood"])
        else:
            moods.append((e["start"], e["start"] + e["dur"], e["mood"]))
    acfg = cfg.get("audio", {})
    music_file = acfg.get("music_file") if acfg.get("music") == "file" else None
    audio = mixer.mix(total, clips, events, beds, moods if acfg.get("music", "auto") != "off" else [], plan.get("country", "vietnam"),
                      seed=sum(map(ord, plan.get("title", ""))) % 1000, levels=acfg.get("levels"), music_file=music_file)
    wav = proj.p("cache", "mix.wav")
    mixer.write_wav(wav, audio)
    out = proj.p("output", "video_draft.mp4" if draft else "video_final.mp4")
    log("🎚  Cân âm lượng chuẩn YouTube và gắn âm thanh vào video...")
    mux(silent, wav, out, acfg.get("loudness", -16))
    export.write_srt(tl, proj.p("output", "phu_de.srt"))
    md = proj.load("script.md") or ""
    parsed = script_writer.parse_markdown(md) if md else None
    timings = proj.load(os.path.join("voice", "timings.json")) or {}
    export.write_youtube(proj.p("output", "youtube.txt"), plan, tl, proj.load("script.json"), parsed,
                         export.sources_section(md), timings.get("voice"), lang=plan.get("language", "vi"))
    if not any(e["clips"] for e in tl):
        log("ℹ️  Video chưa có giọng đọc (chưa tạo giọng / chưa cài OmniVoice).")
    if cfg.get("kenh_kiem_tien"):
        from core.voice.omnivoice_engine import LICENSE_WARNING
        log(LICENSE_WARNING)
    log(f"✅ Xong sau {time.time() - t0:.0f}s: {out}")
    log(f"   + {proj.p('output', 'youtube.txt')}   + {proj.p('output', 'phu_de.srt')}")
    proj.mark("render")
    return out


def step_preview(proj, cfg, log=print):
    from render.renderer import preview_grid
    plan = load_plan(proj, log, strict=False)
    tl = timeline_for(proj, plan, cfg)
    out = proj.p("output", "preview.jpg")
    preview_grid(plan, tl, out, cfg["render"], log=log)
    log(f"🖼  Ảnh xem trước: {out}")
    return out


def run(proj, cfg, log=print, auto=False, draft=False, offline=False, ask=input, voice_name=None, quality=None):
    """Chạy tiếp các bước còn thiếu; dừng ở bước duyệt (trừ khi --auto)."""
    router = None if offline else Router(cfg, log_dir=proj.p("logs"), log=log)
    review = [] if auto else cfg.get("review_after", ["script", "plan"])
    st = proj.state
    name = os.path.basename(proj.dir)
    if "script" not in st["done"] and not os.path.exists(proj.p("script.md")):
        step_script(proj, cfg, router, log, offline)
        if "script" in review:
            log(f"\n⏸  DỪNG ĐỂ DUYỆT: mở {proj.p('script.md')}, sửa nếu cần (xem cả script_check.md), rồi chạy:\n"
                f"     python main.py continue {name}")
            proj.mark("script")
            return "review_script"
    proj.mark("script", approved=True)
    st = proj.state
    if "plan" not in st["done"] or not os.path.exists(proj.p("plan.json")):
        step_plan(proj, cfg, router, log, offline)
        if "plan" in review:
            log(f"\n⏸  DỪNG ĐỂ DUYỆT: xem ảnh xem trước rồi sửa {proj.p('plan.json')} nếu cần. Tiếp tục bằng:\n"
                f"     python main.py continue {name}")
            try:
                step_preview(proj, cfg, log)
            except Exception as e:
                log(f"   (không tạo được ảnh xem trước: {e})")
            return "review_plan"
    proj.mark("plan", approved=True)
    # không có bàn phím (chạy từ giao diện web) -> tự chọn giọng ứng viên tốt nhất
    interactive = config_mod.interactive()
    step_voice(proj, cfg, router, log, draft=draft, auto=auto or not interactive, ask=ask, voice_name=voice_name)
    return step_render(proj, cfg, log, draft=draft, quality=quality)


def make_demo(cfg, log=print, draft=False, quality=None):
    """Dự án mẫu GĐ1: plan.json viết tay (samples/bach_dang_938) -> video ~30 giây."""
    d = os.path.join(PROJECTS, "demo_bach_dang_938")
    os.makedirs(d, exist_ok=True)
    proj = Project(d)
    src = os.path.join(ROOT, "samples", "bach_dang_938")
    for f in ("plan.json", "script.md"):
        if os.path.exists(os.path.join(src, f)):
            shutil.copyfile(os.path.join(src, f), proj.p(f))
    proj.save("input.json", input_parser.parse("Trận Bạch Đằng năm 938 (1p)"))
    plan = load_plan(proj, log)
    from core.voice.omnivoice_engine import estimate_timings
    if not os.path.exists(proj.p("voice", "timings.json")):
        proj.save(os.path.join("voice", "timings.json"), estimate_timings(plan, pronunciation(proj)))
    return step_render(proj, cfg, log, draft=draft, quality=quality)
