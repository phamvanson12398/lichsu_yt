"""Giao diện web chạy trên máy (chỉ dùng thư viện có sẵn của Python).

    python web/server.py            -> mở http://127.0.0.1:8765 trong trình duyệt

Máy chủ chỉ nghe ở 127.0.0.1 (máy khác trong mạng không vào được). Mọi việc nặng vẫn do main.py làm,
chạy trong tiến trình con; nhật ký được đẩy lên trình duyệt từng dòng.
"""
import json
import mimetypes
import os
import re
import subprocess
import sys
import threading
import time
import urllib.parse
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
WEB = os.path.join(ROOT, "web")
PROJECTS = os.path.join(ROOT, "projects")
VOICES = os.path.join(ROOT, "voices")
EDITABLE = {"script.md", "plan.json", "pronunciation.json", "script_check.md"}
ACTIONS = {"continue", "script", "plan", "diversify", "preview", "voice-gen", "render", "validate", "check-facts"}
STEPS = ["parsed", "script", "plan", "voice", "render"]

mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("font/ttf", ".ttf")
mimetypes.add_type("video/mp4", ".mp4")


# ====================================================================== việc chạy nền
class Job:
    def __init__(self, args, title, project=None):
        self.id = uuid.uuid4().hex[:10]
        self.args, self.title, self.project = args, title, project
        self.lines, self.rc, self.started, self.ended = [], None, time.time(), None
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", PYTHONUNBUFFERED="1", HVT_NONINTERACTIVE="1")
        flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        self.proc = subprocess.Popen([sys.executable, os.path.join(ROOT, "main.py")] + args, cwd=ROOT, env=env,
                                     stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     text=True, encoding="utf-8", errors="replace", bufsize=1, creationflags=flags)
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        for line in self.proc.stdout:
            self.lines.append(line.rstrip("\n"))
        self.rc = self.proc.wait()
        self.ended = time.time()

    @property
    def running(self):
        return self.rc is None

    def stop(self):
        if not self.running:
            return
        if os.name == "nt":   # dừng cả các tiến trình con dựng cảnh song song
            subprocess.call(["taskkill", "/F", "/T", "/PID", str(self.proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            self.proc.terminate()
        self.lines.append("⏹ Đã dừng theo yêu cầu.")

    def info(self, since=0):
        return {"id": self.id, "title": self.title, "project": self.project, "running": self.running, "rc": self.rc,
                "started": self.started, "ended": self.ended, "total": len(self.lines), "lines": self.lines[since:]}


JOBS = {}


def start_job(args, title, project=None):
    j = Job(args, title, project)
    JOBS[j.id] = j
    return j


def project_busy(name):
    return any(j.running and j.project == name for j in JOBS.values())


# ====================================================================== dữ liệu dự án
def _load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f) if path.endswith(".json") else f.read()


def safe_name(name):
    if not re.fullmatch(r"[\w.-]+", name or "") or name.startswith("."):
        raise ValueError("Tên không hợp lệ")
    return name


def project_summary(name):
    d = os.path.join(PROJECTS, name)
    info = _load(os.path.join(d, "input.json"), {}) or {}
    st = _load(os.path.join(d, "state.json"), {"done": []}) or {"done": []}
    plan = None
    try:
        plan = _load(os.path.join(d, "plan.json"))
    except Exception:
        pass
    out = os.path.join(d, "output")
    vids = [f for f in ("video_final.mp4", "video_draft.mp4") if os.path.exists(os.path.join(out, f))]
    title = (plan or {}).get("title") or info.get("topic") or name
    md = _load(os.path.join(d, "script.md"))
    if md and not plan:
        m = re.search(r"^#\s+(.+)$", md, re.M)
        title = m.group(1).strip() if m else title
    return {"name": name, "title": title, "minutes": info.get("minutes"), "language": (plan or {}).get("language") or info.get("language", "vi"),
            "country": (plan or {}).get("country") or info.get("country"), "done": st.get("done", []),
            "scenes": len((plan or {}).get("scenes", [])), "videos": vids,
            "preview": os.path.exists(os.path.join(out, "preview.jpg")), "mtime": os.path.getmtime(d),
            "busy": project_busy(name)}


def project_detail(name):
    d = os.path.join(PROJECTS, name)
    s = project_summary(name)
    files = {}
    for f in ("script.md", "plan.json", "script_check.md", "pronunciation.json"):
        p = os.path.join(d, f)
        files[f] = open(p, encoding="utf-8").read() if os.path.exists(p) else None
    out = os.path.join(d, "output")
    for f in ("youtube.txt", "phu_de.srt"):
        p = os.path.join(out, f)
        files[f] = open(p, encoding="utf-8").read() if os.path.exists(p) else None
    report = None
    if files["plan.json"]:
        try:
            from core.plan_schema import validate
            E, W = validate(json.loads(files["plan.json"]))
            report = {"errors": E, "warnings": W}
        except json.JSONDecodeError as e:
            report = {"errors": [f"plan.json sai cú pháp JSON: {e}"], "warnings": []}
        except Exception as e:
            report = {"errors": [str(e)], "warnings": []}
    timings = _load(os.path.join(d, "voice", "timings.json"), {}) or {}
    flagged = [s_["display"] for sc in timings.get("scenes", {}).values() for s_ in sc.get("sentences", []) if s_.get("can_nghe_lai")]
    s.update(files=files, report=report, voice=timings.get("voice"), flagged=flagged,
             jobs=[j.info(len(j.lines)) for j in JOBS.values() if j.project == name])
    return s


def voices_list():
    from core.voice import voice_library as VL
    vs = VL.list_voices()
    for v in vs:
        v["sample"] = os.path.exists(os.path.join(VOICES, v["_name"], "sample.wav"))
    return {"voices": vs, "defaults": VL.defaults()}


# ====================================================================== HTTP
class Handler(BaseHTTPRequestHandler):
    server_version = "LichSuVideo/1.0"

    def log_message(self, fmt, *args):
        pass

    # ---------------------------------------------------------------- tiện ích
    def _json(self, data, code=200):
        b = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def _err(self, msg, code=400):
        self._json({"error": msg}, code)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else b""

    def _jbody(self):
        b = self._body()
        return json.loads(b.decode("utf-8")) if b else {}

    def _file(self, path, base):
        path = os.path.realpath(path)
        if not path.startswith(os.path.realpath(base) + os.sep) or not os.path.isfile(path):
            return self._err("Không tìm thấy file", 404)
        size = os.path.getsize(path)
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/json", "text/javascript"):
            ctype += "; charset=utf-8"
        rng = self.headers.get("Range")
        start, end = 0, size - 1
        if rng and (m := re.match(r"bytes=(\d*)-(\d*)", rng)):
            if m.group(1):
                start = int(m.group(1))
                end = int(m.group(2)) if m.group(2) else size - 1
            else:
                start = max(0, size - int(m.group(2)))
            end = min(end, size - 1)
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        try:
            with open(path, "rb") as f:
                f.seek(start)
                left = end - start + 1
                while left > 0:
                    chunk = f.read(min(1 << 20, left))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    # ---------------------------------------------------------------- GET
    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        p = urllib.parse.unquote(u.path)
        q = urllib.parse.parse_qs(u.query)
        try:
            if p in ("/", "/index.html"):
                return self._file(os.path.join(WEB, "index.html"), WEB)
            if p.startswith("/static/"):
                return self._file(os.path.join(WEB, p[len("/static/"):]), WEB)
            if p.startswith("/fonts/"):
                return self._file(os.path.join(ROOT, "fonts", os.path.basename(p)), os.path.join(ROOT, "fonts"))
            if p.startswith("/files/projects/"):
                return self._file(os.path.join(PROJECTS, p[len("/files/projects/"):]), PROJECTS)
            if p.startswith("/files/voices/"):
                return self._file(os.path.join(VOICES, p[len("/files/voices/"):]), VOICES)
            if p == "/api/projects":
                ps = [project_summary(n) for n in os.listdir(PROJECTS) if os.path.isdir(os.path.join(PROJECTS, n))] \
                    if os.path.isdir(PROJECTS) else []
                return self._json(sorted(ps, key=lambda x: -x["mtime"]))
            if m := re.fullmatch(r"/api/projects/([\w.-]+)", p):
                if not os.path.isdir(os.path.join(PROJECTS, m.group(1))):
                    return self._err("Không có dự án này", 404)
                return self._json(project_detail(safe_name(m.group(1))))
            if p == "/api/jobs":
                return self._json([j.info(len(j.lines)) for j in sorted(JOBS.values(), key=lambda j: -j.started)][:20])
            if m := re.fullmatch(r"/api/jobs/(\w+)", p):
                j = JOBS.get(m.group(1))
                if not j:
                    return self._err("Không có việc này", 404)
                return self._json(j.info(int(q.get("since", ["0"])[0])))
            if p == "/api/voices":
                return self._json(voices_list())
            if p == "/api/config":
                return self._json({"text": _load(os.path.join(ROOT, "config.yaml"), "")})
            if p == "/api/ai":
                from core import config as C
                from core.llm.base import which
                cfg = C.load()
                return self._json({"roles": {r: cfg.get(r) for r in C.AI_ROLES}, "fallback": bool(cfg.get("fallback", True)),
                                   "names": C.AI_NAMES, "installed": {k: bool(which(k)) for k in C.AI_NAMES}})
            if p == "/api/options":
                from assets_code import registry
                from render.palettes import PALETTES
                return self._json({"palettes": list(PALETTES), "components": sorted(registry.names())})
            return self._err("Không có trang này", 404)
        except ValueError as e:
            return self._err(str(e))
        except Exception as e:
            return self._err(f"Lỗi máy chủ: {e}", 500)

    # ---------------------------------------------------------------- POST / PUT / DELETE
    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        p = urllib.parse.unquote(u.path)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        try:
            if p == "/api/projects":
                b = self._jbody()
                topic = (b.get("topic") or "").strip()
                if not topic:
                    return self._err("Chưa nhập chủ đề")
                lang = b.get("lang", "vi")
                line = f"{topic} ({float(b.get('minutes') or 10):g}p, {lang})"
                from core.input_parser import parse
                slug = parse(line)["slug"]
                args = [line, "--quality", b.get("quality", "chuan")]
                if b.get("auto"):
                    args.append("--auto")
                if b.get("offline"):
                    args.append("--offline")
                if b.get("ai") in ("claude", "agy"):
                    args += ["--ai", b["ai"]]
                j = start_job(args, f"Tạo video: {topic}", slug)
                return self._json({"job": j.id, "project": slug})
            if m := re.fullmatch(r"/api/projects/([\w.-]+)/run", p):
                name = safe_name(m.group(1))
                b = self._jbody()
                act = b.get("action")
                if act not in ACTIONS:
                    return self._err("Việc không hợp lệ")
                if project_busy(name):
                    return self._err("Dự án đang có việc chạy, đợi xong hoặc bấm Dừng.")
                args = [act, name]
                if act in ("continue", "render") and b.get("quality"):
                    args += ["--quality", b["quality"]]
                if act == "voice-gen":
                    args.append("--auto")
                if b.get("offline") and act in ("continue", "plan"):
                    args.append("--offline")
                if b.get("voice") and act in ("continue", "voice-gen"):
                    args += ["--voice", b["voice"]]
                if b.get("ai") in ("claude", "agy") and act in ("continue", "script", "plan", "check-facts"):
                    args += ["--ai", b["ai"]]
                labels = {"continue": "Chạy tiếp", "script": "Viết lại kịch bản", "plan": "Lập lại kế hoạch dựng", "diversify": "Đa dạng góc nhìn",
                          "preview": "Xem trước", "voice-gen": "Tạo giọng đọc", "render": "Dựng video",
                          "validate": "Kiểm tra plan", "check-facts": "Kiểm tra sự kiện"}
                j = start_job(args, f"{labels[act]}: {name}", name)
                return self._json({"job": j.id})
            if m := re.fullmatch(r"/api/jobs/(\w+)/stop", p):
                j = JOBS.get(m.group(1))
                if j:
                    j.stop()
                return self._json({"ok": True})
            if p == "/api/demo":
                return self._json({"job": start_job(["demo"], "Video mẫu Bạch Đằng 938", "demo_bach_dang_938").id})
            if p == "/api/check":
                return self._json({"job": start_job(["check"], "Kiểm tra máy").id})
            if p == "/api/voices/upload":
                name = safe_name(q.get("name", ""))
                if q.get("consent") != "1":
                    return self._err("Cần xác nhận đây là giọng của bạn hoặc đã được người đó đồng ý.")
                ext = os.path.splitext(q.get("filename", "a.wav"))[1].lower()
                if ext not in (".mp3", ".m4a", ".wav", ".ogg", ".flac", ".webm", ".aac"):
                    return self._err("Chỉ nhận file âm thanh mp3 / m4a / wav / ogg / flac / webm")
                data = self._body()
                if len(data) < 1000:
                    return self._err("File quá nhỏ")
                up = os.path.join(VOICES, "_tai_len")
                os.makedirs(up, exist_ok=True)
                fp = os.path.join(up, f"{name}{ext}")
                with open(fp, "wb") as f:
                    f.write(data)
                args = ["voice", "add", name, "--file", fp, "--dong-y", "--auto", "--lang", q.get("lang", "vi")]
                if q.get("text"):
                    args += ["--text", q["text"]]
                return self._json({"job": start_job(args, f"Thêm giọng: {name}").id})
            if p == "/api/voices/auto":
                b = self._jbody()
                args = ["voice", "auto", b.get("topic") or "video lịch sử", "--auto", "--lang", b.get("lang", "vi")]
                if b.get("name"):
                    args += ["--name", safe_name(b["name"])]
                return self._json({"job": start_job(args, "Thiết kế giọng tự động").id})
            if p == "/api/voices/default":
                b = self._jbody()
                from core.voice import voice_library as VL
                VL.set_default(safe_name(b["name"]), language=b.get("lang") or None)
                return self._json({"ok": True})
            return self._err("Không có chức năng này", 404)
        except ValueError as e:
            return self._err(str(e))
        except Exception as e:
            return self._err(f"Lỗi máy chủ: {e}", 500)

    def do_PUT(self):
        p = urllib.parse.unquote(urllib.parse.urlparse(self.path).path)
        try:
            if m := re.fullmatch(r"/api/projects/([\w.-]+)/files/([\w.-]+)", p):
                name, fname = safe_name(m.group(1)), m.group(2)
                if fname not in EDITABLE:
                    return self._err("Không được sửa file này")
                text = self._jbody().get("text", "")
                if fname.endswith(".json"):
                    try:
                        json.loads(text)
                    except json.JSONDecodeError as e:
                        return self._err(f"JSON sai cú pháp ở dòng {e.lineno}, cột {e.colno}: {e.msg}")
                with open(os.path.join(PROJECTS, name, fname), "w", encoding="utf-8") as f:
                    f.write(text)
                return self._json({"ok": True})
            if p == "/api/ai":
                from core import config as C
                b = self._jbody()
                C.save_ai(b.get("roles") or {}, b.get("fallback"))
                return self._json({"ok": True})
            if p == "/api/config":
                text = self._jbody().get("text", "")
                import yaml
                try:
                    yaml.safe_load(text)
                except yaml.YAMLError as e:
                    return self._err(f"config.yaml sai cú pháp: {e}")
                with open(os.path.join(ROOT, "config.yaml"), "w", encoding="utf-8") as f:
                    f.write(text)
                return self._json({"ok": True})
            return self._err("Không có chức năng này", 404)
        except ValueError as e:
            return self._err(str(e))

    def do_DELETE(self):
        p = urllib.parse.unquote(urllib.parse.urlparse(self.path).path)
        if m := re.fullmatch(r"/api/voices/([\w.-]+)", p):
            from core.voice import voice_library as VL
            try:
                VL.delete(safe_name(m.group(1)))
                return self._json({"ok": True})
            except (FileNotFoundError, ValueError) as e:
                return self._err(str(e))
        return self._err("Không có chức năng này", 404)


def main(port=8765, open_browser=True):
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    os.makedirs(PROJECTS, exist_ok=True)
    for p in range(port, port + 20):
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", p), Handler)
            break
        except OSError:
            continue
    else:
        print("Không mở được cổng mạng nào từ", port)
        return 1
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    print(f"Giao diện web đang chạy tại: {url}\nGiữ cửa sổ này mở trong lúc dùng. Đóng cửa sổ = tắt giao diện.")
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    for j in JOBS.values():
        j.stop()
    return 0


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 8765
    sys.exit(main(port, open_browser="--no-browser" not in sys.argv))
