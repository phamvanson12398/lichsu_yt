"""Giao diện đơn giản (GĐ6) — chạy:  python app.py
Gõ chủ đề một dòng, bấm các nút theo thứ tự. Nhật ký hiện ở khung dưới.
"""
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)


class App:
    def __init__(self, root):
        from core import config as C
        from core import pipeline as P
        self.C, self.P = C, P
        self.cfg = C.load()
        self.root = root
        self.q = queue.Queue()
        self.busy = False
        root.title("Tool video lịch sử")
        root.geometry("980x680")
        f = ttk.Frame(root, padding=10)
        f.pack(fill="both", expand=True)

        ttk.Label(f, text="Chủ đề (vd: Trận Bạch Đằng năm 938 (10p)):").grid(row=0, column=0, sticky="w")
        self.topic = ttk.Entry(f, width=70)
        self.topic.grid(row=1, column=0, columnspan=3, sticky="we", pady=4)
        ttk.Button(f, text="Tạo dự án mới + viết kịch bản", command=self.new).grid(row=1, column=3, padx=4)

        ttk.Label(f, text="Dự án:").grid(row=2, column=0, sticky="w", pady=(10, 0))
        self.proj = ttk.Combobox(f, values=P.list_projects(), width=50)
        self.proj.grid(row=3, column=0, columnspan=2, sticky="we")
        ttk.Button(f, text="↻", width=3, command=self.refresh).grid(row=3, column=2, sticky="w")

        self.auto = tk.BooleanVar(value=False)
        self.draft = tk.BooleanVar(value=False)
        self.offline = tk.BooleanVar(value=False)
        opts = ttk.Frame(f)
        opts.grid(row=4, column=0, columnspan=4, sticky="w", pady=6)
        ttk.Label(opts, text="Lời kể:").pack(side="left")
        self.lang = ttk.Combobox(opts, width=14, state="readonly",
                                 values=["vi - Tiếng Việt", "en - English", "ko - 한국어", "ja - 日本語"])
        self.lang.set("vi - Tiếng Việt")
        self.lang.pack(side="left", padx=(2, 10))
        ttk.Label(opts, text="Độ nét:").pack(side="left")
        self.quality = ttk.Combobox(opts, width=16, state="readonly",
                                    values=["chuan - 1080p", "cao - 1440p", "4k - 2160p"])
        self.quality.set("chuan - 1080p")
        self.quality.pack(side="left", padx=(2, 10))
        ttk.Checkbutton(opts, text="Chạy hết không dừng duyệt", variable=self.auto).pack(side="left")
        ttk.Checkbutton(opts, text="Chế độ nháp (nhanh, 960x540)", variable=self.draft).pack(side="left", padx=10)
        ttk.Checkbutton(opts, text="Không dùng AI (lập plan theo mẫu)", variable=self.offline).pack(side="left")

        b = ttk.Frame(f)
        b.grid(row=5, column=0, columnspan=4, sticky="w", pady=4)
        for txt, fn in [("Chạy tiếp", self.cont), ("Mở kịch bản", lambda: self.open_file("script.md")),
                        ("Mở plan.json", lambda: self.open_file("plan.json")), ("Lập lại plan", self.replan),
                        ("Xem trước", self.preview), ("Tạo giọng", self.voicegen), ("Dựng video", self.render),
                        ("Mở thư mục kết quả", self.open_out)]:
            ttk.Button(b, text=txt, command=fn).pack(side="left", padx=2)

        v = ttk.Frame(f)
        v.grid(row=6, column=0, columnspan=4, sticky="w", pady=4)
        ttk.Label(v, text="Giọng:").pack(side="left")
        ttk.Button(v, text="Thêm giọng của tôi...", command=self.voice_add).pack(side="left", padx=2)
        ttk.Button(v, text="Danh sách giọng", command=lambda: self.run_cmd(["voice", "list"])).pack(side="left", padx=2)
        ttk.Button(v, text="Video mẫu 30 giây", command=lambda: self.run_cmd(["demo"])).pack(side="left", padx=12)
        ttk.Button(v, text="Kiểm tra máy", command=lambda: self.run_cmd(["check"])).pack(side="left", padx=2)

        self.out = scrolledtext.ScrolledText(f, height=24, font=("Consolas", 10))
        self.out.grid(row=7, column=0, columnspan=4, sticky="nsew", pady=6)
        f.columnconfigure(0, weight=1)
        f.rowconfigure(7, weight=1)
        if self.cfg.get("kenh_kiem_tien"):
            from core.voice.omnivoice_engine import LICENSE_WARNING
            self.log(LICENSE_WARNING)
        root.after(100, self.poll)

    # --------------------------------------------------------------- tiện ích
    def log(self, msg=""):
        self.q.put(str(msg))

    def poll(self):
        while not self.q.empty():
            self.out.insert("end", self.q.get() + "\n")
            self.out.see("end")
        self.root.after(100, self.poll)

    def refresh(self):
        self.proj["values"] = self.P.list_projects()

    def flags(self):
        a = ["--quality", self.quality.get().split(" ")[0]]
        if self.auto.get():
            a.append("--auto")
        if self.draft.get():
            a.append("--draft")
        if self.offline.get():
            a.append("--offline")
        return a

    def run_cmd(self, args):
        """Chạy main.py trong tiến trình con (để dựng song song an toàn), đưa nhật ký vào khung."""
        if self.busy:
            messagebox.showinfo("Đang chạy", "Đợi việc trước xong đã.")
            return
        self.busy = True

        def work():
            try:
                p = subprocess.Popen([sys.executable, os.path.join(ROOT, "main.py")] + args, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, stdin=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
                                     cwd=ROOT, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
                for line in p.stdout:
                    self.log(line.rstrip())
                p.wait()
            finally:
                self.busy = False
                self.root.after(0, self.refresh)
        threading.Thread(target=work, daemon=True).start()

    def cur(self):
        p = self.proj.get().strip()
        if not p:
            messagebox.showwarning("Chưa chọn dự án", "Chọn dự án trong danh sách trước.")
        return p

    def open_path(self, path):
        if not os.path.exists(path):
            messagebox.showwarning("Không có", path)
            return
        if sys.platform.startswith("win"):
            os.startfile(path)  # noqa
        elif sys.platform == "darwin":
            subprocess.run(["open", path])
        else:
            subprocess.run(["xdg-open", path])

    # --------------------------------------------------------------- nút
    def new(self):
        t = self.topic.get().strip()
        if not t:
            return
        from core.input_parser import slugify
        self.proj.set(slugify(t))
        self.run_cmd([t, "--lang", self.lang.get().split(" ")[0]] + self.flags())

    def cont(self):
        p = self.cur()
        if p:
            self.run_cmd(["continue", p] + self.flags())

    def replan(self):
        p = self.cur()
        if p:
            self.run_cmd(["plan", p] + (["--offline"] if self.offline.get() else []))

    def preview(self):
        p = self.cur()
        if p:
            self.run_cmd(["preview", p])

    def voicegen(self):
        p = self.cur()
        if p:
            self.run_cmd(["voice-gen", p] + (["--draft"] if self.draft.get() else []) + ["--auto"])

    def render(self):
        p = self.cur()
        if p:
            self.run_cmd(["render", p, "--quality", self.quality.get().split(" ")[0]] + (["--draft"] if self.draft.get() else []))

    def open_file(self, name):
        p = self.cur()
        if p:
            self.open_path(os.path.join(ROOT, "projects", p, name))

    def open_out(self):
        p = self.cur()
        if p:
            self.open_path(os.path.join(ROOT, "projects", p, "output"))

    def voice_add(self):
        f = filedialog.askopenfilename(title="Chọn file giọng (mp3 / m4a / wav)", filetypes=[("Âm thanh", "*.mp3 *.m4a *.wav *.ogg *.flac")])
        if not f:
            return
        name = simpledialog.askstring("Tên giọng", "Đặt tên cho giọng (không dấu, vd: giong_cua_toi):")
        if not name:
            return
        text = simpledialog.askstring("Lời mẫu", "Nhập đúng lời đã nói trong file (để trống = tự nhận dạng):") or ""
        ok = messagebox.askyesno("Xác nhận", "Đây là giọng của tôi hoặc tôi đã được người này đồng ý?")
        if not ok:
            return
        args = ["voice", "add", name, "--file", f, "--dong-y", "--auto", "--lang", self.lang.get().split(" ")[0]] + (["--text", text] if text else [])
        self.run_cmd(args)


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
