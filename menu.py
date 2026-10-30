"""Menu tiếng Việt cho người không quen dòng lệnh (được gọi từ file CHAY_TOOL.bat).
Mọi việc vẫn do main.py làm; menu chỉ hỏi thông tin rồi gọi đúng lệnh.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECTS = os.path.join(ROOT, "projects")
LANGS = [("vi", "Tiếng Việt"), ("en", "Tiếng Anh"), ("ko", "Tiếng Hàn"), ("ja", "Tiếng Nhật")]
QUALITIES = [("chuan", "Chuẩn 1080p (khuyên dùng)"), ("cao", "Cao 1440p — nét hơn, dựng lâu gấp ~2"),
             ("4k", "4K — nét nhất, dựng rất lâu"), ("nhap", "Nháp 960x540 — xem nhanh")]

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def run(*args):
    """Chạy main.py với các tham số, hiện kết quả trực tiếp."""
    print()
    r = subprocess.call([sys.executable, os.path.join(ROOT, "main.py"), *args], cwd=ROOT)
    print("\n" + ("✔ Xong." if r == 0 else "✖ Có lỗi, xem thông báo ở trên."))
    return r


def ask(prompt, default=""):
    try:
        v = input(f"{prompt}{f' [{default}]' if default else ''}: ").strip()
    except EOFError:
        v = ""
    return v or default


def choose(title, items, default=1):
    print(f"\n{title}")
    for i, (_, label) in enumerate(items, 1):
        print(f"  {i}. {label}")
    while True:
        v = ask("Chọn số", str(default))
        if v.isdigit() and 1 <= int(v) <= len(items):
            return items[int(v) - 1][0]
        print("  Gõ một số trong danh sách.")


def yes(prompt, default="c"):
    return ask(f"{prompt} (c = có / k = không)", default).lower() in ("c", "co", "có", "y", "yes")


def projects():
    if not os.path.isdir(PROJECTS):
        return []
    return sorted((d for d in os.listdir(PROJECTS) if os.path.isdir(os.path.join(PROJECTS, d))),
                  key=lambda d: -os.path.getmtime(os.path.join(PROJECTS, d)))


def pick_project():
    ps = projects()
    if not ps:
        print("\nChưa có dự án nào. Hãy tạo video mới trước.")
        return None
    return choose("Chọn dự án (mới nhất ở trên):", [(p, p) for p in ps])


def open_path(p):
    if not os.path.exists(p):
        print(f"Chưa có: {p}")
        return
    if sys.platform.startswith("win"):
        os.startfile(p)  # noqa
    elif sys.platform == "darwin":
        subprocess.call(["open", p])
    else:
        subprocess.call(["xdg-open", p])


def pick_file(title):
    try:
        import tkinter as tk
        from tkinter import filedialog
        r = tk.Tk()
        r.withdraw()
        r.attributes("-topmost", True)
        f = filedialog.askopenfilename(title=title, filetypes=[("Âm thanh", "*.mp3 *.m4a *.wav *.ogg *.flac"), ("Tất cả", "*.*")])
        r.destroy()
        return f
    except Exception:
        return ask(title + " (dán đường dẫn file)").strip('"')


# ------------------------------------------------------------------ các việc
def new_video():
    topic = ask("\nNhập chủ đề (vd: Trận Bạch Đằng năm 938)")
    if not topic:
        return
    minutes = ask("Thời lượng (phút)", "10")
    lang = choose("Ngôn ngữ lời kể:", [(c, n) for c, n in LANGS])
    quality = choose("Độ nét video:", QUALITIES)
    auto = not yes("Dừng lại để bạn duyệt kịch bản và kế hoạch dựng trước khi làm tiếp?", "c")
    args = [f"{topic} ({minutes}p, {lang})", "--quality", quality]
    if auto:
        args.append("--auto")
    run(*args)
    if not auto:
        print("\nKhi đã xem / sửa xong script.md (và plan.json), chọn mục 2 'Chạy tiếp dự án'.")


def continue_project():
    p = pick_project()
    if p:
        q = choose("Độ nét video:", QUALITIES)
        run("continue", p, "--quality", q)


def render_again():
    p = pick_project()
    if p:
        q = choose("Độ nét video:", QUALITIES)
        run("render", p, "--quality", q)
        open_path(os.path.join(PROJECTS, p, "output"))


def diversify():
    p = pick_project()
    if not p:
        return
    print("Tool sẽ đổi góc nhìn các cảnh lặp (nhìn qua tán lá, tướng cận cảnh, lau sậy...), KHÔNG đổi lời đọc.")
    print("Muốn AI lập lại kế hoạch mới hoàn toàn (có thêm thẻ nhân vật, dòng thời gian...) thì chọn 'Lập lại kế hoạch bằng AI'.")
    if run("diversify", p) == 0 and yes("Dựng lại video luôn?", "c"):
        q = choose("Độ nét video:", QUALITIES)
        run("render", p, "--quality", q)
        open_path(os.path.join(PROJECTS, p, "output"))


def replan():
    p = pick_project()
    if p and run("plan", p) == 0 and yes("Dựng lại video luôn?", "c"):
        q = choose("Độ nét video:", QUALITIES)
        run("render", p, "--quality", q)
        open_path(os.path.join(PROJECTS, p, "output"))


def preview():
    p = pick_project()
    if p and run("preview", p) == 0:
        open_path(os.path.join(PROJECTS, p, "output", "preview.jpg"))


def open_files():
    p = pick_project()
    if not p:
        return
    what = choose("Mở gì?", [("script.md", "Kịch bản (script.md)"), ("plan.json", "Kế hoạch dựng (plan.json)"),
                             ("script_check.md", "Ghi chú kiểm tra sự kiện"), ("output", "Thư mục kết quả (video, youtube.txt)")])
    open_path(os.path.join(PROJECTS, p, what))


def voices():
    act = choose("Giọng đọc:", [("list", "Xem danh sách giọng"), ("add", "Thêm giọng của tôi (từ file ghi âm)"),
                                ("auto", "Để AI thiết kế giọng tự động"), ("default", "Đặt giọng mặc định"),
                                ("gen", "Tạo lại giọng cho một dự án")])
    if act == "list":
        run("voice", "list")
    elif act == "add":
        f = pick_file("Chọn file giọng (mp3 / m4a / wav, nói 10–30 giây)")
        if not f:
            return
        name = ask("Đặt tên giọng (không dấu, không cách, vd giong_cua_toi)", "giong_cua_toi")
        lang = choose("Giọng này nói tiếng gì?", [(c, n) for c, n in LANGS])
        text = ask("Gõ đúng lời đã nói trong file (Enter để máy tự nghe)")
        if not yes("Đây là giọng của tôi hoặc tôi đã được người này đồng ý?", "k"):
            print("Chỉ nhân bản giọng của bạn hoặc người đã đồng ý.")
            return
        args = ["voice", "add", name, "--file", f, "--dong-y", "--lang", lang]
        if text:
            args += ["--text", text]
        run(*args)
    elif act == "auto":
        topic = ask("Chủ đề video (để AI chọn kiểu giọng)", "video lịch sử")
        lang = choose("Ngôn ngữ:", [(c, n) for c, n in LANGS])
        run("voice", "auto", topic, "--lang", lang)
    elif act == "default":
        run("voice", "list")
        name = ask("Tên giọng muốn đặt mặc định")
        if name:
            lang = choose("Mặc định cho ngôn ngữ nào?", [(c, n) for c, n in LANGS])
            run("voice", "default", name, "--lang", lang)
    elif act == "gen":
        p = pick_project()
        if p:
            run("voice-gen", p)


MENU = [
    ("Tạo video mới", new_video),
    ("Chạy tiếp dự án (sau khi duyệt / sửa)", continue_project),
    ("Xem ảnh trước các cảnh", preview),
    ("Dựng lại video (vd sau khi sửa plan.json, đổi độ nét)", render_again),
    ("Làm cảnh đa dạng hơn cho dự án đã có (nhanh, không cần AI)", diversify),
    ("Lập lại kế hoạch cảnh bằng AI (giữ kịch bản và giọng)", replan),
    ("Mở kịch bản / kế hoạch / thư mục kết quả", open_files),
    ("Giọng đọc", voices),
    ("Làm video mẫu 30 giây (thử máy)", lambda: (run("demo"), open_path(os.path.join(PROJECTS, "demo_bach_dang_938", "output")))),
    ("Kiểm tra máy đã cài đủ chưa", lambda: run("check")),
    ("Mở giao diện cửa sổ", lambda: subprocess.call([sys.executable, os.path.join(ROOT, "app.py")], cwd=ROOT)),
    ("Mở giao diện web (đẹp hơn, trong trình duyệt)", lambda: subprocess.call([sys.executable, os.path.join(ROOT, "web", "server.py")], cwd=ROOT)),
]


def main():
    while True:
        print("\n" + "=" * 56)
        print("   TOOL LÀM VIDEO LỊCH SỬ")
        print("=" * 56)
        for i, (label, _) in enumerate(MENU, 1):
            print(f"  {i}. {label}")
        print("  0. Thoát")
        v = ask("\nChọn số")
        if v in ("0", "q", "thoat"):
            return
        if v.isdigit() and 1 <= int(v) <= len(MENU):
            try:
                MENU[int(v) - 1][1]()
            except KeyboardInterrupt:
                print("\nĐã dừng việc đang làm.")
        else:
            print("Gõ một số trong menu.")


if __name__ == "__main__":
    main()
