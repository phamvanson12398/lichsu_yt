"""Google Antigravity CLI (Gemini Pro) ở chế độ không tương tác:
    agy -p='<prompt>' --output-format json [--json-schema '<schema>'] [--print-timeout 10m] [--model <slug>]

Cờ -p của agy BẮT BUỘC dính liền nội dung (-p='...'), không đọc prompt qua stdin.
Prompt dài (vượt giới hạn dòng lệnh Windows) hoặc agy chạy qua file .cmd: tool ghi prompt ra file prompt.md
trong thư mục tạm rồi bảo agy đọc file đó.
Lấy nội dung ở "response" (hoặc "structured_output" khi có --json-schema); kiểm tra "status" = "SUCCESS".
Quyền ghi file cho agy được giới hạn bằng quy tắc "permissions" trong ~/.gemini/antigravity-cli/settings.json
(xem HUONG_DAN_CAI_DAT.md). Tool này chỉ dùng agy để trả lời văn bản / JSON.

config.yaml -> agy: prompt_via: auto (mặc định) | arg (luôn dính vào -p) | file (luôn qua file) | stdin (bản agy cũ đọc stdin)
"""
import json
import os

from core.llm.base import CLIBackend, LLMError, which


class AgyCLI(CLIBackend):
    name = "agy"
    cmd = "agy"
    label = "Antigravity (agy)"

    FILE_HINT = ("Đọc TOÀN BỘ file prompt.md trong thư mục hiện tại và làm đúng mọi yêu cầu trong đó. "
                 "Chỉ trả về đúng kết quả được yêu cầu, không giải thích thêm.")

    def prompt_args(self, prompt, cwd, exe):
        mode = str(self.cfg.get("prompt_via") or "auto").lower()
        if mode == "stdin" and self.cfg.get("force_stdin"):
            return ["-p", "-"], prompt
        wrapper = exe.lower().endswith((".cmd", ".bat", ".ps1"))
        limit = 0 if wrapper else int(self.cfg.get("max_arg_chars", 24000))   # Windows giới hạn ~32.000 ký tự / lệnh
        if mode != "file" and (mode == "arg" or len(prompt) <= limit):
            return [f"-p={prompt}"], None
        with open(os.path.join(cwd, "prompt.md"), "w", encoding="utf-8") as f:
            f.write(prompt)
        return [f"-p={self.FILE_HINT}"], None

    def build_args(self, schema=None, write_dir=None, allowed_tools=None):
        args = ["--output-format", "json"]
        to = int(self.cfg.get("timeout", 900))
        args += ["--print-timeout", f"{max(1, to // 60)}m"]
        exe = (which(self.cmd) or "").lower()
        # qua file .cmd/.bat trên Windows, cmd.exe có thể làm hỏng dấu " trong JSON -> bỏ --json-schema (tool vẫn tự kiểm JSON)
        if schema and self.cfg.get("use_json_schema", True) and not exe.endswith((".cmd", ".bat")):
            args += ["--json-schema", json.dumps(schema, ensure_ascii=False)]
        if self.cfg.get("model"):
            args += ["--model", str(self.cfg["model"])]
        return args

    def parse_output(self, stdout):
        try:
            data = json.loads(stdout)
        except Exception:
            return stdout
        if not isinstance(data, dict):
            return stdout
        st = str(data.get("status", "SUCCESS")).upper()
        if st != "SUCCESS":
            raise LLMError(f"Antigravity báo trạng thái {st}: {str(data.get('error') or data.get('response'))[:300]}", "other")
        if data.get("structured_output") is not None:
            return data["structured_output"]
        return data.get("response", "")
