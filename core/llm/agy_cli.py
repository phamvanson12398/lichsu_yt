"""Google Antigravity CLI (Gemini Pro) ở chế độ không tương tác:
    agy -p --output-format json [--json-schema '<schema>'] [--print-timeout 10m] [--model <slug>]
Lấy nội dung ở "response" (hoặc "structured_output" khi có --json-schema); kiểm tra "status" = "SUCCESS".
Quyền ghi file cho agy được giới hạn bằng quy tắc "permissions" trong ~/.gemini/antigravity-cli/settings.json
(xem HUONG_DAN_CAI_DAT.md). Tool này chỉ dùng agy để trả lời văn bản / JSON.

Lưu ý: nếu bản agy của bạn không đọc prompt từ stdin, đặt  agy: {prompt_via: arg}  trong config.yaml.
"""
import json

from core.llm.base import CLIBackend, LLMError, which


class AgyCLI(CLIBackend):
    name = "agy"
    cmd = "agy"
    label = "Antigravity (agy)"

    def build_args(self, schema=None, write_dir=None, allowed_tools=None):
        args = ["-p", "-"] if self.cfg.get("stdin_dash") and self.cfg.get("prompt_via") != "arg" else ["-p"]
        args += ["--output-format", "json"]
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
