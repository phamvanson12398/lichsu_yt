"""Lớp gọi AI chung (mục 2): ask(prompt, schema=None, timeout=...) -> text / JSON.

Không dùng API / SDK. Gọi CLI đã cài + đăng nhập sẵn trên máy (claude, agy) bằng subprocess,
truyền prompt qua stdin (tránh giới hạn độ dài dòng lệnh Windows), UTF-8 cho tiếng Việt.
Chạy trong thư mục tạm trống, không cấp quyền ghi file hay chạy lệnh.
Mỗi lần gọi được ghi log vào projects/<du_an>/logs/.
"""
import datetime
import json
import os
import re
import shutil
import subprocess
import tempfile
import time


class LLMError(Exception):
    """Lỗi gọi AI, thông báo tiếng Việt dễ hiểu."""

    def __init__(self, msg, kind="other"):
        super().__init__(msg)
        self.kind = kind     # not_installed | not_logged_in | quota | timeout | bad_output | other


QUOTA_PAT = re.compile(r"usage limit|rate.?limit|quota|limit reached|resource.?exhausted|429|too many requests|"
                       r"credit balance|out of (extra )?usage|5-hour limit|weekly limit", re.I)
LOGIN_PAT = re.compile(r"not logged in|please log ?in|/login|authenticat|unauthori[sz]ed|invalid api key|401|"
                       r"sign in|login required|oauth", re.I)


def which(cmd):
    p = shutil.which(cmd)
    if p is None and os.name == "nt":
        for ext in (".cmd", ".exe", ".bat", ".ps1"):
            p = shutil.which(cmd + ext)
            if p:
                break
    return p


def repair_json(s):
    """Sửa các lỗi JSON hay gặp ở câu trả lời của AI: ngoặc kép kiểu “ ”, ngoặc kép lọt giữa chuỗi chưa thoát (\\"),
    xuống dòng trong chuỗi, dấu phẩy thừa trước } / ]."""
    s = s.replace("\ufeff", "")
    s = re.sub(r'([{\[,:]\s*)[\u201c\u201d]', r'\1"', s)          # ngoặc kép kiểu “ ” ở vị trí cú pháp JSON
    s = re.sub(r'[\u201c\u201d](\s*[:,}\]])', r'"\1', s)
    out, i, n, in_str = [], 0, len(s), False
    while i < n:
        ch = s[i]
        if not in_str:
            if ch == '"':
                in_str = True
            out.append(ch)
        else:
            if ch == "\\" and i + 1 < n:
                out.append(ch + s[i + 1])
                i += 2
                continue
            if ch == '"':
                j = i + 1
                while j < n and s[j] in " \t\r\n":
                    j += 1
                if j >= n or s[j] in ",}]:":
                    in_str = False                           # ngoặc kép đóng chuỗi thật
                    out.append(ch)
                else:
                    out.append('\\"')                      # ngoặc kép nằm giữa câu -> thoát
            elif ch == "\n":
                out.append("\\n")
            elif ch == "\r":
                pass
            elif ch == "\t":
                out.append("\\t")
            else:
                out.append(ch)
        i += 1
    r = "".join(out)
    return re.sub(r",\s*([}\]])", r"\1", r)


def extract_json(text):
    """Lấy khối JSON đầu tiên trong câu trả lời (```json ... ``` hoặc {...} / [...]); hỏng nhẹ thì tự sửa."""
    if text is None:
        raise ValueError("rỗng")
    if isinstance(text, (dict, list)):
        return text
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    cands = [m.group(1)] if m else []
    s = text.strip()
    pairs = [("{", "}"), ("[", "]")]
    if -1 < s.find("[") < s.find("{") or s.find("{") == -1:
        pairs.reverse()                                      # khối ngoài cùng là mảng
    for open_, close in pairs:
        i = s.find(open_)
        j = s.rfind(close)
        if i != -1 and j > i:
            cands.append(s[i:j + 1])
    if not s:
        raise ValueError("AI trả lời RỖNG — thường do nội dung cần viết quá dài so với giới hạn một lần trả lời của AI")
    if not cands:
        raise ValueError("không thấy khối JSON nào ({...}) trong câu trả lời — AI trả lời bằng chữ thường. "
                         "Đầu câu trả lời: " + s[:200].replace("\n", " "))
    last = None
    for c in cands:
        for fix in (lambda c: c, repair_json):
            try:
                return json.loads(fix(c), strict=False)
            except Exception as e:      # thử bản tiếp theo
                last = e
    msg = str(last)
    pos = getattr(last, "pos", None)
    if pos is not None and cands:
        c = cands[-1]
        msg += f" — đoạn hỏng: …{c[max(0, pos - 80):pos + 40]}…"
    raise ValueError(f"không đọc được JSON: {msg}")


def check_schema(data, schema, path="$"):
    """Kiểm tra JSON theo schema rút gọn (type, required, properties, items, enum). Trả về danh sách lỗi."""
    errs = []
    if not schema:
        return errs
    t = schema.get("type")
    types = t if isinstance(t, list) else [t] if t else []
    pymap = {"object": dict, "array": list, "string": str, "integer": int, "number": (int, float), "boolean": bool, "null": type(None)}
    if types and not any(isinstance(data, pymap[x]) and not (x in ("integer", "number") and isinstance(data, bool)) for x in types):
        return [f"{path}: phải là {'/'.join(types)}"]
    if "enum" in schema and data not in schema["enum"]:
        errs.append(f"{path}: giá trị '{data}' không thuộc {schema['enum']}")
    if isinstance(data, dict):
        for k in schema.get("required", []):
            if k not in data:
                errs.append(f"{path}: thiếu trường '{k}'")
        for k, sub in schema.get("properties", {}).items():
            if k in data:
                errs += check_schema(data[k], sub, f"{path}.{k}")
    if isinstance(data, list) and "items" in schema:
        for i, it in enumerate(data):
            errs += check_schema(it, schema["items"], f"{path}[{i}]")
            if len(errs) > 20:
                break
    return errs


class CLIBackend:
    name = "base"
    cmd = ""

    def __init__(self, cfg=None, log_dir=None):
        self.cfg = cfg or {}
        self.log_dir = log_dir

    # -- được lớp con cài đặt
    def prompt_args(self, prompt, cwd, exe):
        """Mặc định: cờ -p, nội dung prompt gửi qua stdin. Trả về (tham số, văn_bản_stdin)."""
        if self.cfg.get("prompt_via") == "arg" and len(prompt) < 7000:
            return ["-p", prompt], None
        return ["-p"], prompt

    def build_args(self, schema=None, write_dir=None, allowed_tools=None):
        raise NotImplementedError

    def parse_output(self, stdout):
        raise NotImplementedError

    # -- chung
    def available(self):
        return which(self.cmd) is not None

    def _log(self, prompt, out, err, dt, ok):
        if not self.log_dir:
            return
        os.makedirs(self.log_dir, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        p = os.path.join(self.log_dir, f"{ts}_{self.name}.log")
        with open(p, "w", encoding="utf-8") as f:
            f.write(f"# {self.name}  thời gian: {dt:.1f}s  kết quả: {'OK' if ok else 'LỖI'}\n\n## PROMPT\n{prompt}\n\n## TRẢ LỜI\n{out}\n")
            if err:
                f.write(f"\n## STDERR\n{err}\n")

    def run(self, prompt, schema=None, timeout=None, cwd=None, allowed_tools=None):
        exe = which(self.cmd)
        if not exe:
            raise LLMError(f"Chưa cài '{self.cmd}' ({self.label}). Xem HUONG_DAN_CAI_DAT.md mục 'Cài AI CLI'.", "not_installed")
        timeout = timeout or self.cfg.get("timeout", 900)
        tmp = None
        if cwd is None:
            tmp = tempfile.mkdtemp(prefix="hvt_ai_")
            cwd = tmp
        pargs, stdin_text = self.prompt_args(prompt, cwd, exe)
        args = [exe] + pargs + self.build_args(schema=schema, allowed_tools=allowed_tools)
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        t0 = time.time()
        try:
            p = subprocess.run(args, input=stdin_text, stdin=None if stdin_text is not None else subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=timeout, cwd=cwd, env=env)
        except subprocess.TimeoutExpired:
            self._log(prompt, "", "timeout", time.time() - t0, False)
            raise LLMError(f"{self.label} trả lời quá lâu (quá {timeout} giây). Thử lại hoặc tăng 'timeout' trong config.yaml.", "timeout")
        finally:
            written = _written_files(cwd) if tmp else {}
            if tmp:
                shutil.rmtree(tmp, ignore_errors=True)
        dt = time.time() - t0
        out, err = p.stdout or "", p.stderr or ""
        both = out + "\n" + err
        if p.returncode != 0 or not out.strip():
            self._log(prompt, out, err, dt, False)
            if QUOTA_PAT.search(both):
                raise LLMError(f"{self.label}: đã hết lượt dùng của gói đăng ký (hoặc bị giới hạn tạm thời). Đợi một lúc hoặc chuyển sang AI còn lại.", "quota")
            if LOGIN_PAT.search(both):
                raise LLMError(f"{self.label}: chưa đăng nhập. Mở cửa sổ lệnh, gõ '{self.cmd}' rồi làm theo hướng dẫn đăng nhập.", "not_logged_in")
            raise LLMError(f"{self.label} báo lỗi (mã {p.returncode}): {(err or out).strip()[:400]}", "other")
        try:
            text = self.parse_output(out)
        except LLMError as e:
            self._log(prompt, out, err, dt, False)
            if QUOTA_PAT.search(str(e)):
                raise LLMError(f"{self.label}: đã hết lượt dùng của gói đăng ký.", "quota")
            raise
        if isinstance(text, str) and "{" not in text and written:
            # AI dạng agent có khi ghi kết quả ra file (vd output.json) rồi chỉ trả lời "đã tạo file" -> lấy nội dung file
            best = max(written.items(), key=lambda kv: (kv[1].lstrip().startswith(("{", "[", "```")), len(kv[1])))
            text = best[1]
        self._log(prompt, text if isinstance(text, str) else json.dumps(text, ensure_ascii=False, indent=1), err, dt, True)
        return text


def _written_files(d):
    """Các file AI tự ghi trong thư mục tạm (trừ prompt.md) — {tên: nội dung}."""
    out = {}
    for root, _, files in os.walk(d):
        for f in files:
            if f == "prompt.md" or not f.lower().endswith((".json", ".md", ".txt")):
                continue
            p = os.path.join(root, f)
            try:
                if os.path.getsize(p) < 4_000_000:
                    with open(p, encoding="utf-8", errors="replace") as fh:
                        out[os.path.relpath(p, d)] = fh.read()
            except OSError:
                pass
    return out


class Router:
    """Chọn AI cho từng việc theo config, tự chuyển sang bên kia khi lỗi / hết lượt (fallback)."""

    def __init__(self, cfg, log_dir=None, log=print):
        from core.llm.agy_cli import AgyCLI
        from core.llm.claude_cli import ClaudeCLI
        self.cfg = cfg
        self.log = log
        self.backends = {"claude": ClaudeCLI(cfg.get("claude", {}), log_dir), "agy": AgyCLI(cfg.get("agy", {}), log_dir)}

    def order(self, role):
        first = self.cfg.get(role, "claude")
        other = "agy" if first == "claude" else "claude"
        return [first, other] if self.cfg.get("fallback", True) else [first]

    def ask(self, role, prompt, schema=None, timeout=None, retries=3, validator=None):
        """Gửi prompt; nếu cần JSON thì parse + kiểm tra schema/validator, sai thì gửi lỗi lại cho AI sửa (tối đa 3 lần)."""
        last = None
        for name in self.order(role):
            be = self.backends[name]
            if not be.available():
                last = LLMError(f"Chưa cài '{be.cmd}' ({be.label}).", "not_installed")
                self.log(f"   ⚠️  {last}")
                continue
            p = prompt
            try:
                for attempt in range(retries):
                    self.log(f"   → hỏi {be.label} ({role}){' — lần sửa ' + str(attempt) if attempt else ''}...")
                    out = be.run(p, schema=schema, timeout=timeout)
                    if schema is None and validator is None:
                        return out
                    try:
                        data = extract_json(out)
                        errs = check_schema(data, schema) if schema else []
                        if validator and not errs:
                            errs = validator(data) or []
                    except ValueError as e:
                        data, errs = None, [f"Câu trả lời không phải JSON hợp lệ: {e}"]
                    if not errs:
                        return data
                    self.log(f"   ⚠️  JSON chưa đúng ({len(errs)} lỗi), gửi lại cho AI sửa")
                    p = (prompt + "\n\n---\nCâu trả lời trước của bạn có lỗi sau, hãy trả lại TOÀN BỘ JSON đã sửa (chỉ JSON, in thẳng ra câu trả lời, "
                         "KHÔNG ghi ra file; trong chuỗi, dấu ngoặc kép phải viết \\\" hoặc dùng ngoặc đơn ' thay thế):\n- "
                         + "\n- ".join(errs[:25]) + "\n\nCâu trả lời trước:\n" + (out if isinstance(out, str) else json.dumps(out, ensure_ascii=False))[:20000])
                raise LLMError(f"{be.label} trả JSON sai sau {retries} lần sửa: {errs[:5]}", "bad_output")
            except LLMError as e:
                last = e
                self.log(f"   ⚠️  {e}")
                if e.kind in ("not_installed",):
                    continue
                if not self.cfg.get("fallback", True):
                    break
                self.log("   ↪ chuyển sang AI còn lại")
        raise last or LLMError("Không có AI nào dùng được.")
