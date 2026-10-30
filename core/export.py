"""Bước 6 - Xuất phụ đề .srt và youtube.txt (gợi ý tiêu đề, mô tả, tag, mốc chương, nguồn)."""
import os


def _ts(t, sep=","):
    h, r = divmod(max(0.0, t), 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}{sep}{int(round((s - int(s)) * 1000)):03d}"


def write_srt(timeline, path):
    n = 0
    with open(path, "w", encoding="utf-8") as f:
        for e in timeline:
            for a, b, text in e["cues"]:
                n += 1
                f.write(f"{n}\n{_ts(e['start'] + a)} --> {_ts(e['start'] + b)}\n{text}\n\n")
    return path


def chapters(timeline, script=None):
    """Mốc chương YouTube: đầu mỗi phần kịch bản (dựa vào cảnh có lời trùng đoạn đầu của phần)."""
    out = [(0.0, "Mở đầu")]
    if not script:
        return out
    starts = []
    for sec in script.get("sections", [])[1:]:
        head = " ".join(sec["paragraphs"][0].split()[:6]) if sec["paragraphs"] else ""
        for e in timeline:
            if head and head in (e["scene"].get("narration") or ""):
                starts.append((max(0.0, e["start"]), sec["heading"]))
                break
    for t, h in starts:
        if t - out[-1][0] >= 10:
            out.append((t, h))
    return out


def write_youtube(path, plan, timeline, script_data=None, script_parsed=None, sources_md=None, voice_name=None):
    yt = (script_data or {}).get("youtube") or {}
    title = plan.get("title", "")
    titles = yt.get("titles") or [title, f"{title} – Trận đánh thay đổi lịch sử", f"{title}: chuyện ít người biết"]
    desc = yt.get("description") or f"Câu chuyện về {title}, kể lại bằng hình minh họa động."
    tags = yt.get("tags") or [title, "lịch sử", "lịch sử Việt Nam" if plan.get("country") == "vietnam" else "lịch sử thế giới",
                              "trận đánh", "phim tài liệu", plan.get("era", "")]
    L = ["=== GỢI Ý TIÊU ĐỀ ==="] + [f"- {t}" for t in titles] + ["", "=== MÔ TẢ ===", desc, ""]
    ch = chapters(timeline, script_parsed)
    if len(ch) >= 3:
        L.append("Mốc thời gian:")
        for t, h in ch:
            m, s = divmod(int(t), 60)
            L.append(f"{m:02d}:{s:02d} {h}")
        L.append("")
    L += ["Hình ảnh trong video là tranh minh họa vẽ bằng code, không phải ảnh tư liệu thật.",
          "Bản đồ là sơ đồ minh họa, không theo tỉ lệ.", "Âm nhạc và hiệu ứng âm thanh được tổng hợp bằng máy tính."]
    if voice_name:
        L.append("Giọng đọc được tạo bằng mô hình OmniVoice (k2-fsa) từ giọng mẫu có sự đồng ý.")
    if sources_md:
        L += ["", "Nguồn tham khảo chính:"] + [ln for ln in sources_md.splitlines() if ln.startswith("- ")][:15]
    L += ["", "=== TAG ===", ", ".join(t for t in tags if t), "",
          "=== NHẮC VIỆC TRƯỚC KHI ĐĂNG ===",
          "- Xem lại toàn bộ video, nghe các câu được đánh dấu 'nên nghe lại' (nếu có).",
          "- Kiểm tra lại năm, tên người, số liệu theo phần GHI CHÚ NGUỒN trong script.md.",
          "- Nếu kênh bật kiếm tiền: lưu ý giấy phép CC-BY-NC của OmniVoice."]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    return path


def sources_section(script_md):
    if not script_md or "GHI CHÚ NGUỒN" not in script_md:
        return ""
    return script_md.split("GHI CHÚ NGUỒN", 1)[1]
