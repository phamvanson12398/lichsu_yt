"""Claude Code CLI ở chế độ không tương tác:
    claude -p --output-format json [--model ...]      (prompt qua stdin, lấy trường "result")
Chỉ trả lời văn bản: chặn các công cụ ghi file / chạy lệnh / mạng. Không dùng --dangerously-skip-permissions.
"""
import json

from core.llm.base import CLIBackend, LLMError

NO_TOOLS = ["Bash", "Edit", "Write", "MultiEdit", "NotebookEdit", "WebFetch", "WebSearch", "Task", "Agent"]


class ClaudeCLI(CLIBackend):
    name = "claude"
    cmd = "claude"
    label = "Claude Code (claude)"

    def build_args(self, schema=None, write_dir=None, allowed_tools=None):
        args = ["--output-format", "json"]
        if self.cfg.get("model"):
            args += ["--model", str(self.cfg["model"])]
        if allowed_tools:
            args += ["--allowedTools"] + list(allowed_tools)
        else:
            args += ["--disallowedTools"] + NO_TOOLS
        return args

    def parse_output(self, stdout):
        try:
            data = json.loads(stdout)
        except Exception:
            # một số phiên bản in nhiều dòng JSON (stream) -> lấy dòng cuối có "result"
            data = None
            for line in reversed(stdout.strip().splitlines()):
                try:
                    d = json.loads(line)
                    if isinstance(d, dict) and "result" in d:
                        data = d
                        break
                except Exception:
                    continue
            if data is None:
                return stdout
        if isinstance(data, list):
            data = next((d for d in reversed(data) if isinstance(d, dict) and "result" in d), {})
        if data.get("is_error") or data.get("subtype", "success") not in ("success",):
            raise LLMError(f"Claude báo lỗi: {str(data.get('result') or data.get('subtype'))[:300]}", "other")
        return data.get("result", "")
