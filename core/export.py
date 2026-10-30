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


def chapters(timeline, script=None, lang="vi"):
    """Mốc chương YouTube: đầu mỗi phần kịch bản (dựa vào cảnh có lời trùng đoạn đầu của phần)."""
    from core import lang as L
    out = [(0.0, L.ui(lang, "intro"))]
    if not script:
        return out
    starts = []
    for sec in script.get("sections", [])[1:]:
        p0 = sec["paragraphs"][0] if sec["paragraphs"] else ""
        head = p0[:12] if L.is_cjk_lang(lang) and " " not in p0[:12] else " ".join(p0.split()[:6])
        for e in timeline:
            if head and head in (e["scene"].get("narration") or ""):
                starts.append((max(0.0, e["start"]), sec["heading"]))
                break
    for t, h in starts:
        if t - out[-1][0] >= 10:
            out.append((t, h))
    return out


def write_youtube(path, plan, timeline, script_data=None, script_parsed=None, sources_md=None, voice_name=None, lang="vi"):
    from core import lang as LG
    u = lambda k, **kw: LG.ui(lang, k, **kw)
    yt = (script_data or {}).get("youtube") or {}
    title = plan.get("title", "")
    titles = yt.get("titles") or [title]
    desc = yt.get("description") or u("yt_desc_default", t=title)
    tags = yt.get("tags") or [title, u("yt_tag_history"), plan.get("era", "")]
    L = [u("yt_titles")] + [f"- {t}" for t in titles] + ["", u("yt_desc"), desc, ""]
    ch = chapters(timeline, script_parsed, lang)
    if len(ch) >= 3:
        L.append(u("yt_chapters"))
        for t, h in ch:
            m, s = divmod(int(t), 60)
            L.append(f"{m:02d}:{s:02d} {h}")
        L.append("")
    L += list(u("yt_notes"))
    if voice_name:
        L.append(u("yt_voice"))
    if sources_md:
        import re
        plain = [re.sub(r"\*\*|(?<!\w)_|_(?!\w)", "", ln) for ln in sources_md.split("###")[0].splitlines() if ln.startswith("- ")]
        L += ["", u("yt_sources")] + plain[:15]
    L += ["", u("yt_tags"), ", ".join(t for t in tags if t), "",
          "=== NHẮC VIỆC TRƯỚC KHI ĐĂNG (phần này không dán lên YouTube) ===",
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
