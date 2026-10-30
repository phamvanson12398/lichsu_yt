"""Tool tự làm video lịch sử cho YouTube — dòng lệnh.

  python main.py "Trận Bạch Đằng năm 938 (10p)"            chạy hết, dừng ở bước duyệt
  python main.py "Trận Hastings năm 1066 (8p)" --auto      chạy hết không dừng
  python main.py "Trận Hastings năm 1066 (8p, en)"         lời kể tiếng Anh (en | ko | ja | vi), hoặc thêm --lang en
  python main.py render bach_dang_938 --quality cao         dựng nét hơn: nhap | chuan (1080p) | cao (1440p) | 4k
  python main.py continue bach_dang_938                    chạy tiếp sau khi duyệt / sửa
  python main.py preview  projects/bach_dang_938           ảnh xem trước từng cảnh
  python main.py render   projects/bach_dang_938 [--draft] dựng lại video
  python main.py demo                                      video mẫu ~30 giây (không cần AI, giọng)
  python main.py check                                     kiểm tra máy đã cài đủ chưa
  python main.py voice ...                                 quản lý giọng (gõ: python main.py voice)
  python main.py component ...                             thư viện thành phần vẽ (gõ: python main.py component)
"""
import argparse
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

COMMANDS = ["continue", "script", "plan", "validate", "voice-gen", "preview", "render", "demo", "check", "voice", "voice-save",
            "component", "list", "check-facts", "fonts", "help"]


def log(msg=""):
    print(msg, flush=True)


def _proj(path):
    from core.pipeline import Project
    return Project(path)


def cmd_check(cfg):
    import shutil
    import subprocess
    from core.llm.base import which
    ok = True
    log("Kiểm tra máy:")
    v = sys.version_info
    log(f"  {'✔' if v >= (3, 11) else '✖'} Python {v.major}.{v.minor}" + ("" if v >= (3, 11) else "  (cần 3.11 trở lên)"))
    ok &= v >= (3, 11)
    ff = shutil.which("ffmpeg")
    log(f"  {'✔' if ff else '✖'} FFmpeg" + (f" ({ff})" if ff else "  — chưa cài, xem HUONG_DAN_CAI_DAT.md"))
    ok &= bool(ff)
    for mod in ("PIL", "numpy", "yaml"):
        try:
            __import__(mod)
            log(f"  ✔ thư viện {mod}")
        except ImportError:
            log(f"  ✖ thiếu thư viện {mod}: chạy  pip install -r requirements.txt")
            ok = False
    from render.common import font_path
    try:
        log(f"  ✔ font tiếng Việt: {font_path('serif_bold')}")
    except RuntimeError as e:
        log(f"  ✖ {e}")
        ok = False
    for k_, lab in (("cjk_ko", "font tiếng Hàn"), ("cjk_ja", "font tiếng Nhật")):
        fp = font_path(k_)
        log(f"  {'✔' if fp else '✖'} {lab}: {fp or 'chưa có — chạy: python main.py fonts'}")
    for name, label in (("claude", "Claude Code CLI"), ("agy", "Antigravity CLI")):
        p = which(name)
        if p:
            try:
                r = subprocess.run([p, "--version"], capture_output=True, text=True, timeout=30, encoding="utf-8", errors="replace")
                ver = (r.stdout or r.stderr).strip().splitlines()[0] if (r.stdout or r.stderr).strip() else ""
            except Exception:
                ver = ""
            log(f"  ✔ {label} ({name}) {ver}")
        else:
            log(f"  • {label} ({name}) chưa cài — cần cho bước viết kịch bản / lập plan")
    try:
        import torch
        cuda = torch.cuda.is_available()
        log(f"  ✔ PyTorch {torch.__version__} — {'GPU: ' + torch.cuda.get_device_name(0) if cuda else 'không có GPU NVIDIA (giọng đọc sẽ chậm)'}")
    except Exception:
        log("  • PyTorch chưa cài — cần cho giọng đọc OmniVoice")
    from core.voice.omnivoice_engine import OmniVoiceEngine
    log(f"  {'✔' if OmniVoiceEngine.installed() else '•'} OmniVoice" + ("" if OmniVoiceEngine.installed() else " chưa cài (pip install omnivoice)"))
    log("  Đăng nhập AI: mở cửa sổ lệnh gõ 'claude' (hoặc 'agy') một lần để đăng nhập; tool không dùng API key.")
    if cfg.get("kenh_kiem_tien"):
        from core.voice.omnivoice_engine import LICENSE_WARNING
        log(LICENSE_WARNING)
    log("\n" + ("✅ Đủ để dựng video." if ok else "❌ Còn thiếu, xem các dòng ✖ ở trên."))


def cmd_voice(args, cfg):
    from core.voice import voice_library as VL
    sub = args.rest[0] if args.rest else "list"
    rest = args.rest[1:]
    if sub == "list":
        vs = VL.list_voices()
        d = VL.defaults()
        if not vs:
            log("Chưa có giọng nào. Thêm giọng: python main.py voice add <tên> --file giong.mp3")
        for v in vs:
            mark = " (mặc định)" if d.get("default") == v["_name"] else ""
            cs = [c for c, n in d.get("by_country", {}).items() if n == v["_name"]]
            log(f"- {v['_name']}{mark}{' [mặc định cho ' + ', '.join(cs) + ']' if cs else ''} — {v.get('loai')} — "
                f"ngôn ngữ {v.get('ngon_ngu', 'vi')} — {v.get('mo_ta', '')}"
                f"{' — instruct: ' + v['instruct'] if v.get('instruct') else ''}")
        return
    if sub == "play":
        VL.play(os.path.join(VL.VOICES_DIR, rest[0], "sample.wav"))
        return
    if sub == "default":
        VL.set_default(rest[0], args.country, args.lang)
        log(f"✔ Đặt '{rest[0]}' làm giọng mặc định{' cho ' + (args.lang or args.country) if (args.lang or args.country) else ''}")
        return
    if sub == "delete":
        if input(f"Xoá giọng '{rest[0]}'? (co / khong): ").strip().lower() in ("co", "có", "y", "yes", "c"):
            VL.delete(rest[0])
            log("✔ Đã xoá")
        return
    if sub == "add":
        if not args.file:
            raise SystemExit("Cần --file <đường dẫn file mp3/m4a/wav>")
        VL.add_clone(rest[0], args.file, args.text, consent=args.dong_y, cfg=cfg, log=log, interactive=not args.auto,
                     lang=args.lang or "vi")
        return
    if sub == "design":
        if not args.instruct:
            raise SystemExit('Cần --instruct "male, middle-aged, low pitch"')
        cands = VL.design_candidates([args.instruct] * 3, cfg, log, lang=args.lang or "vi")
        best = VL.choose(cands, auto=args.auto, log=log)
        VL.save_design(rest[0], best)
        log(f"✔ Đã lưu giọng thiết kế '{rest[0]}'")
        return
    if sub == "auto":
        from core.llm.base import LLMError, Router
        topic = " ".join(rest) or "video lịch sử"
        try:
            ins = VL.suggest_instructs(Router(cfg, log=log), topic, lang=args.lang or "vi")
        except LLMError as e:
            log(f"⚠️  {e} — dùng mô tả mặc định")
            ins = VL.fallback_instructs()
        cands = VL.design_candidates(ins, cfg, log, lang=args.lang or "vi")
        best = VL.choose(cands, auto=args.auto, log=log)
        from core.input_parser import slugify
        name = args.name or ("thiet_ke_" + slugify(topic))
        VL.save_design(name, best)
        log(f"✔ Đã lưu giọng '{name}'. Đặt làm mặc định: python main.py voice default {name}")
        return
    log("Lệnh giọng: list | play <tên> | default <tên> [--country japan] | delete <tên> | "
        "add <tên> --file giong.mp3 [--text \"lời mẫu\"] [--dong-y] | design <tên> --instruct \"male, middle-aged, low pitch\" | auto \"<chủ đề>\"")


def cmd_component(args, cfg):
    from assets_code import registry
    from core import components_ai as CA
    sub = args.rest[0] if args.rest else "list"
    rest = args.rest[1:]
    if sub == "list":
        log(registry.catalog_text([args.country] if args.country else None))
        st = registry.custom_status()
        pend = [k for k, v in st.items() if v.get("status") != "approved"]
        if pend:
            log("\nĐang chờ duyệt: " + ", ".join(pend))
        return
    if sub == "new":
        from core.llm.base import Router
        name, path = CA.write_component(Router(cfg, log=log), rest[0], args.desc or rest[0], args.country or "custom", log)
        out = os.path.join(CA.CUSTOM_DIR, f"{name}_preview.jpg")
        drew = CA.preview_component(name, out)
        log(f"🖼  Xem trước: {out}" + ("" if drew else "  (⚠️ hình gần như trống)"))
        if args.auto and drew:
            CA.approve(name)
            log(f"✔ Tự duyệt '{name}' (chế độ --auto)")
        else:
            log(f"Nếu thấy ổn: python main.py component approve {name}")
        return
    if sub == "preview":
        out = os.path.join(CA.CUSTOM_DIR, f"{rest[0]}_preview.jpg")
        CA.preview_component(rest[0], out)
        log(f"🖼  {out}")
        return
    if sub == "approve":
        CA.approve(rest[0])
        log(f"✔ Đã duyệt '{rest[0]}', từ nay dùng được trong plan.json")
        return
    log("Lệnh thành phần: list [--country vietnam] | new <tên> --desc \"mô tả\" --country korea | preview <tên> | approve <tên>")


def cmd_fonts():
    """Tải font Noto Serif KR / JP (Google Fonts) vào fonts/ để hiện tên gốc Hàn / Nhật."""
    import re
    import urllib.request
    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
    for fam, fn in (("Noto+Serif+KR:wght@700", "NotoSerifKR-Bold.ttf"), ("Noto+Serif+JP:wght@700", "NotoSerifJP-Bold.ttf")):
        css = urllib.request.urlopen(urllib.request.Request(f"https://fonts.googleapis.com/css2?family={fam}",
                                                            headers={"User-Agent": "curl/8"})).read().decode()
        urls = re.findall(r"url\((https://[^)]+\.ttf)\)", css)
        if not urls:
            log(f"✖ không tải được {fn}")
            continue
        data = urllib.request.urlopen(urls[0]).read()
        with open(os.path.join(dest, fn), "wb") as f:
            f.write(data)
        log(f"✔ {fn} ({len(data) // 1024} KB)")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(prog="main.py", description="Tool tự làm video lịch sử", add_help=True)
    ap.add_argument("cmd", nargs="?", default="help")
    ap.add_argument("rest", nargs="*")
    ap.add_argument("--auto", action="store_true", help="chạy hết không dừng duyệt")
    ap.add_argument("--draft", action="store_true", help="chế độ nháp 960x540, giọng nhanh")
    ap.add_argument("--offline", action="store_true", help="không gọi AI (lập plan theo mẫu)")
    ap.add_argument("--voice", help="tên giọng dùng cho video")
    ap.add_argument("--lang", help="ngôn ngữ lời kể: vi | en | ko | ja")
    ap.add_argument("--quality", help="độ nét: nhap | chuan | cao (1440p) | 4k")
    ap.add_argument("--project", help="tên thư mục dự án")
    ap.add_argument("--file")
    ap.add_argument("--ref")
    ap.add_argument("--text")
    ap.add_argument("--instruct")
    ap.add_argument("--country")
    ap.add_argument("--desc")
    ap.add_argument("--name")
    ap.add_argument("--dong-y", dest="dong_y", action="store_true", help="xác nhận giọng của bạn / đã được đồng ý")
    ap.add_argument("--config")
    args = ap.parse_args(argv)
    from core import config as C
    cfg = C.load(args.config)
    from core import pipeline as P
    c = args.cmd
    try:
        if c in ("help", "-h"):
            log(__doc__)
        elif c == "check":
            cmd_check(cfg)
        elif c == "demo":
            P.make_demo(cfg, log, draft=args.draft, quality=args.quality)
        elif c == "list":
            for p in P.list_projects():
                st = P.Project(p).state
                log(f"- {p}: đã xong {', '.join(st['done'])}")
        elif c == "continue":
            P.run(_proj(args.rest[0]), cfg, log, auto=args.auto, draft=args.draft, offline=args.offline, voice_name=args.voice,
                  quality=args.quality)
        elif c == "script":
            from core.llm.base import Router
            proj = _proj(args.rest[0])
            P.step_script(proj, cfg, Router(cfg, proj.p("logs"), log), log)
        elif c == "check-facts":
            from core import script_writer
            from core.llm.base import Router
            proj = _proj(args.rest[0])
            issues = script_writer.check_facts(Router(cfg, proj.p("logs"), log), proj.info, proj.load("script.md"), log)
            for it in issues:
                log(f"- [{it.get('severity')}] {it.get('quote')}\n    {it.get('problem')} -> {it.get('suggestion')}")
        elif c == "plan":
            from core.llm.base import Router
            proj = _proj(args.rest[0])
            P.step_plan(proj, cfg, None if args.offline else Router(cfg, proj.p("logs"), log), log, offline=args.offline)
        elif c == "validate":
            from core import plan_schema
            proj = _proj(args.rest[0])
            log(plan_schema.format_report(*plan_schema.validate(proj.load("plan.json"))))
        elif c == "voice-gen":
            from core.llm.base import Router
            proj = _proj(args.rest[0])
            P.step_voice(proj, cfg, Router(cfg, proj.p("logs"), log), log, draft=args.draft, auto=args.auto, voice_name=args.voice)
        elif c == "preview":
            P.step_preview(_proj(args.rest[0]), cfg, log)
        elif c == "render":
            P.step_render(_proj(args.rest[0]), cfg, log, draft=args.draft, quality=args.quality)
        elif c == "voice":
            cmd_voice(args, cfg)
        elif c == "voice-save":
            from core.voice import voice_library as VL
            VL.add_clone(args.rest[0], args.ref or args.file, args.text, consent=args.dong_y, cfg=cfg, log=log, interactive=not args.auto,
                         lang=args.lang or "vi")
        elif c == "component":
            cmd_component(args, cfg)
        elif c == "fonts":
            cmd_fonts()
        else:
            line = " ".join([c] + args.rest)
            proj = P.new_project(line, cfg, log, name=args.project, lang=args.lang)
            P.run(proj, cfg, log, auto=args.auto, draft=args.draft, offline=args.offline, voice_name=args.voice, quality=args.quality)
    except KeyboardInterrupt:
        log("\nĐã dừng.")
        return 130
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        log(f"\n❌ {e}")
        return 1
    except Exception as e:  # lỗi khác: vẫn báo dễ hiểu, kèm chi tiết để gửi người hỗ trợ
        import traceback
        log(f"\n❌ Lỗi không mong đợi: {e}\n(Chi tiết kỹ thuật bên dưới, gửi cho người hỗ trợ nếu cần)\n")
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
