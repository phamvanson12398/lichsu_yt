"""Điều phối dựng video (mục 10):
  - tính dòng thời gian từ plan.json + mốc giọng đọc (timings.json)
  - dựng từng cảnh -> 1 file mp4 (đẩy khung thẳng vào FFmpeg qua stdin, rawvideo rgb24)
  - ghi tên tạm rồi đổi tên khi FFmpeg xong (exit 0), cache theo hash nội dung cảnh + code
  - cảnh tĩnh: dùng loop của FFmpeg, không vẽ lại từng khung
  - dựng song song nhiều cảnh (multiprocessing)
  - ghép bằng concat demuxer -c copy, thêm âm -c:v copy
  - preview: 1 khung "bận nhất" mỗi cảnh, ghép lưới
"""
import glob
import hashlib
import json
import math
import multiprocessing as mp
import os
import shutil
import subprocess
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance

from render.common import N, ROOT, RichFont, grain_frames, set_language, text_layer, vignette
from render import infographic
from render.map_anim import MapVisual
from render.scene import SceneVisual
from render.text_fx import Subtitles, TextFX
from render.transitions import cross_weight, fade_gain, flash_gain

LEAD_IN = 0.15        # giây trước khi giọng bắt đầu trong cảnh
SENT_GAP = 0.25       # khoảng nghỉ giữa các câu
TAIL_PAD = 0.4        # đệm sau giọng (mục 4)
WATER = ("river", "sea", "lake")


# ======================================================================== timeline
def default_mood(i, n):
    f = i / max(1, n - 1)
    if f < 0.15:
        return "yen_binh"
    if f < 0.45:
        return "cang_thang"
    if f < 0.75:
        return "cao_trao"
    if f < 0.92:
        return "bi_trang"
    return "ket_thuc"


def estimate_speech(text, lang="vi"):
    """Ước lượng thời lượng đọc (giây) khi chưa có giọng, theo tốc độ đọc của từng ngôn ngữ."""
    from core import lang as L
    return L.speech_seconds(N(text), lang)


def build_timeline(plan, timings=None, fps=30):
    timings = (timings or {}).get("scenes", {})
    out = []
    t = 0.0
    scenes = plan["scenes"]
    mood = None
    for i, sc in enumerate(scenes):
        sid = str(sc["id"])
        cues, clips = [], []
        if sc.get("narration"):
            tm = timings.get(sid)
            if tm and tm.get("sentences"):
                sents = tm["sentences"]
            else:
                from core.voice.text_norm import split_sentences
                lg = plan.get("language", "vi")
                sents = [{"text": s, "file": None, "dur": estimate_speech(s, lg)} for s in split_sentences(sc["narration"], lang=lg)]
            lt = float(sc.get("voice_start", LEAD_IN))
            for s in sents:
                cues.append((lt, lt + s["dur"], s.get("display") or s["text"]))
                if s.get("file"):
                    clips.append((lt, s["file"]))
                lt += s["dur"] + SENT_GAP
            dur = max(lt - SENT_GAP + TAIL_PAD, float(sc.get("duration", 0) or 0), 2.5)
        else:
            dur = float(sc.get("duration", 4.0))
        nf = max(1, int(round(dur * fps)))
        dur = nf / fps
        mood = sc.get("mood") or (mood if mood and any(s.get("mood") for s in scenes[:i]) else default_mood(i, len(scenes)))
        out.append({"scene": sc, "start": t, "dur": dur, "frames": nf, "cues": cues, "clips": clips, "mood": mood})
        t += dur
    return out


# ======================================================================== visuals
class CardVisual:
    """Nền cho thẻ chữ khi không có cảnh: nền tối có hạt nhiễu (hoặc giấy cổ)."""

    def __init__(self, OW, OH, fps, dur, pal, kind="dark", particles=(), seed=1):
        from render.particles import System
        self.OW, self.OH = OW, OH
        if kind == "parchment":
            base = np.zeros((OH, OW, 3), np.float32) + np.array(pal.get("paper", (226, 206, 165)), np.float32)
            base += np.random.default_rng(seed).normal(0, 6, (OH, OW, 1))
        else:
            c1 = np.array(pal["sky"][0], np.float32) * 0.5
            c2 = np.array(pal["sil"], np.float32) * 0.6 + np.array(pal["fire"], np.float32) * 0.08
            yy, xx = np.mgrid[0:OH, 0:OW].astype(np.float32)
            r = np.sqrt(((xx - OW / 2) / (OW / 2)) ** 2 + ((yy - OH / 2) / (OH / 2)) ** 2)[..., None]
            base = c2 + (c1 - c2) * np.clip(r / 1.3, 0, 1) + np.array([22, 16, 12], np.float32) * np.clip(1 - r, 0, 1)
        base = base * vignette(OW, OH, 0.6) + np.random.default_rng(seed + 99).normal(0, 6.0, (OH, OW, 1))
        self.base = Image.fromarray(base.clip(0, 255).astype(np.uint8))      # hạt nhiễu + viền tối nướng sẵn
        self.systems = [System(p, OW, OH, fps, seed=seed + i, fog_col=pal["fog"], fire_col=pal["fire"]) for i, p in enumerate(particles)
                        if p in ("embers", "dust", "snow", "cherry_blossom", "leaves", "mist", "fire_glow", "smoke")]
        self.static = not self.systems

    def frame(self, t):
        im = self.base.copy()
        for s in self.systems:
            s.step(t)
            im = s.apply(im, t)
        return im


def make_visual(sc, plan, dur, OW, OH, fps, cfg, seed):
    from render import palettes
    pal_name = sc.get("palette") or (sc.get("scene") or {}).get("palette") or plan.get("palette")
    country = plan.get("country", "vietnam")
    common = dict(supersample=cfg.get("supersample", 2.0), grain=cfg.get("grain", 7.0), grain_n=4 if cfg.get("grain_animated") else 1)
    typ = sc.get("type", "narration")
    if typ == "map":
        return MapVisual(sc.get("map", {}), OW, OH, fps, dur, title=sc.get("map", {}).get("title") or plan.get("title", ""), seed=seed,
                         lang=plan.get("language", "vi"),
                         subtitles=bool(sc.get("narration")) and cfg.get("burn_subtitles", True))
    if typ in infographic.TYPES:
        return infographic.make(typ, sc.get(typ) or {}, OW, OH, fps, dur, palettes.get(pal_name),
                                subtitles=bool(sc.get("narration")) and cfg.get("burn_subtitles", True), seed=seed,
                                lang=plan.get("language", "vi"), country=country)
    if sc.get("scene"):
        return SceneVisual(sc["scene"], OW, OH, fps, dur, palette=pal_name, country=country,
                           motion=sc.get("motion", "static"), particles=sc.get("particles", []), seed=seed, **common)
    kind = sc.get("background", "parchment" if pal_name == "giay_co" else "dark")
    return CardVisual(OW, OH, fps, dur, palettes.get(pal_name), kind=kind, particles=sc.get("particles", []), seed=seed)


class SceneRenderer:
    """Toàn bộ một cảnh: hình + chữ + phụ đề + fade."""

    def __init__(self, entry, plan, OW, OH, fps, cfg):
        sc = entry["scene"]
        set_language(plan.get("language", "vi"))
        self.sc, self.entry, self.OW, self.OH, self.fps, self.cfg = sc, entry, OW, OH, fps, cfg
        dur = entry["dur"]
        self.dur = dur
        seed = int(sc.get("seed", sc.get("id", 1))) * 7 + 3
        self.vis = make_visual(sc, plan, dur, OW, OH, fps, cfg, seed)
        self.vis2 = None
        if sc.get("scene2"):
            sc2 = dict(sc, scene=sc["scene2"], motion=sc.get("motion2", sc.get("motion", "static")))
            self.vis2 = make_visual(sc2, plan, dur, OW, OH, fps, cfg, seed + 1)
            self.switch = float(sc.get("switch_at", dur / 2))
        self.dim = 1.0
        typ = sc.get("type", "narration")
        if typ == "text_card" and sc.get("scene"):
            self.dim = 0.6
        self.texts = []
        if sc.get("text") and sc.get("text_style", "cinematic") != "subtitle":
            style = sc.get("text_style") or ("cinematic" if typ == "title" else "word_by_word")
            start = float(sc.get("text_start", 0.3 if typ in ("title", "text_card") else 0.6))
            self.texts.append(TextFX(dict(sc, text_style=style), OW, OH, start=start, dur=dur - start))
        self.subs = None
        if entry["cues"] and cfg.get("burn_subtitles", True) and typ != "title":
            self.subs = Subtitles(entry["cues"], OW, OH, size=cfg.get("subtitle_size", 46))
        self.fade = cfg.get("fade", 0.4)

    def is_static(self):
        v = self.vis
        st = isinstance(v, CardVisual) and v.static
        if isinstance(v, SceneVisual):
            st = (v.cam.motion == "static" and not v.systems and not v.shimmer and not v.arrows and not v.static_fires
                  and not any(s.anim for s in v.sprites) and not any(it[3] for it in v.items))
        if isinstance(v, MapVisual):
            sp = v.spec
            st = not sp.get("arrows") and not sp.get("markers") and not sp.get("labels")
        return st and not self.texts and not self.subs and self.vis2 is None and self.sc.get("flash_at") is None

    def _text_active(self, t):
        if self.subs and any(a <= t < b for a, b, _ in self.subs.cues):
            return True
        return any(t >= tx.start for tx in self.texts)

    def frame_image(self, t):
        """Khung hoàn chỉnh (ảnh RGB 8-bit): hình + crossfade + chớp sáng + chữ + phụ đề + mờ qua đen."""
        im = self.vis.frame(t)
        if self.vis2 is not None:
            w = cross_weight(t, self.switch)
            im2 = self.vis2.frame(t)
            if w > 0:
                im = Image.blend(im, im2, min(1.0, w))
        if self.dim != 1.0:
            im = im.point(_lut(self.dim))
        fl = flash_gain(t, self.sc)
        if fl:
            im = Image.blend(im, Image.new("RGB", im.size, (255, 255, 255)), min(1.0, fl))
        if self._text_active(t):
            im = im.convert("RGBA")
            for tx in self.texts:
                tx.draw(im, t)
            if self.subs:
                self.subs.draw(im, t)
            im = im.convert("RGB")
        g = fade_gain(t, self.dur, self.sc, self.fade)
        if g < 1:
            im = im.point(_lut(g))
        return im

    def frame(self, t):
        return np.asarray(self.frame_image(t))


def _lut(g):
    g = round(max(0.0, min(1.0, g)), 3)
    return [int(v * g) for v in range(256)] * 3


# ======================================================================== events (âm thanh)
def _pal(sc, plan):
    from render import palettes
    return palettes.get(sc.get("palette") or plan.get("palette"))


def scene_events(entry, plan, OW=1920, OH=1080):
    """Hiệu ứng âm thanh + âm nền của một cảnh, thời gian tính trong cảnh."""
    sc = entry["scene"]
    dur = entry["dur"]
    ev, beds = [], []
    typ = sc.get("type", "narration")
    if sc.get("text") and sc.get("text_style", "cinematic") not in ("subtitle",) and sc.get("text_sfx", True):
        style = sc.get("text_style") or ("cinematic" if typ == "title" else "word_by_word")
        start = float(sc.get("text_start", 0.3 if typ in ("title", "text_card") else 0.6))
        ev += TextFX(dict(sc, text_style=style), OW, OH, start=start, dur=dur - start).events()
    if typ == "map":
        ev += MapVisual.events(_MapEv(sc.get("map", {})))
    if typ in infographic.TYPES:
        ev += infographic.make(typ, sc.get(typ) or {}, 320, 180, 10, dur, _pal(sc, plan)).events()
    have = {e[1] for e in ev}
    for tag in sc.get("sfx", []) or []:
        if tag not in have:
            ev.append((0.2 if tag != "boom" else 0.5, tag, 0.9))
    for it in sc.get("sfx_at", []) or []:
        ev.append((float(it.get("t", 0)), it.get("tag"), float(it.get("gain", 0.9))))
    if sc.get("flash_at") is not None and "boom" not in {e[1] for e in ev}:
        ev.append((float(sc["flash_at"]), "boom", 0.8))
    amb = sc.get("ambience")
    if amb is None:
        amb = []
        desc = sc.get("scene") or {}
        bg = [str(b).split(":")[0] if not isinstance(b, dict) else b.get("kind") for b in desc.get("background", [])]
        if any(w in bg for w in WATER):
            amb.append("song_nuoc")
        burning = any(str(el.get("state")) == "burning" or el.get("kind") in ("fire", "campfire", "torch")
                      for el in desc.get("elements", []))
        if burning or "embers" in (sc.get("particles") or []):
            amb.append("lua_tach")
        if desc.get("weather") == "rain" or "rain" in (sc.get("particles") or []):
            amb.append("mua")
        if desc.get("weather") in ("fog", "snow") or "snow" in (sc.get("particles") or []):
            amb.append("gio_u")
    for tag in amb:
        beds.append((0.0, dur, tag, 0.8 if tag != "song_nuoc" else 0.6))
    return ev, beds


class _MapEv:
    def __init__(self, spec):
        self.spec = spec


# ======================================================================== encoding
QUALITY = {
    # tên: kích thước, CRF, preset x264. YouTube cấp bitrate cao hơn (VP9 / AV1) cho video tải lên 1440p, 4K
    # -> người xem ở 1080p cũng thấy nét hơn.
    "nhap": {"size": (960, 540), "crf": 23, "preset": "ultrafast", "sharpen": 0.0},
    "chuan": {"size": (1920, 1080), "crf": 17, "preset": "veryfast", "sharpen": 0.35},
    "cao": {"size": (2560, 1440), "crf": 17, "preset": "veryfast", "sharpen": 0.3},
    "4k": {"size": (3840, 2160), "crf": 17, "preset": "veryfast", "sharpen": 0.25},
}


def x264_args(cfg):
    """Tham số nén chung cho mọi cảnh (phải giống nhau để ghép -c copy)."""
    a = ["-c:v", "libx264", "-preset", cfg.get("preset", "medium"), "-crf", str(cfg.get("crf", 18)),
         "-profile:v", "high", "-pix_fmt", "yuv420p"]
    if cfg.get("enc_threads"):
        a += ["-threads", str(int(cfg["enc_threads"]))]
    if cfg.get("tune", "animation"):
        a += ["-tune", cfg.get("tune", "animation")]   # hợp với tranh phẳng nhiều mảng màu
    return a


def video_filter(cfg, extra=None):
    f = []
    if extra:
        f.append(extra)
    sh = float(cfg.get("sharpen", 0) or 0)
    if sh > 0:
        f.append(f"unsharp=5:5:{sh}:5:5:0")        # làm nét nhẹ kênh sáng, không đụng màu
    f.append("format=yuv420p")
    return ["-vf", ",".join(f)]


def ffmpeg_encoder(path, OW, OH, fps, cfg):
    return subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}",
                             "-r", str(fps), "-i", "-"] + video_filter(cfg) + x264_args(cfg)
                            + ["-r", str(fps), "-video_track_timescale", str(fps * 512), "-f", "mp4", path], stdin=subprocess.PIPE)


# Mã vẽ ảnh hưởng tới từng loại cảnh — sửa bản đồ thì chỉ cảnh bản đồ phải dựng lại, không phải cả video.
# (renderer.py không nằm ở đây: đổi cách ghép khung trong file này thì tăng "render_v" trong scene_hash.)
CODE_SHARED = ["render/common.py", "render/text_fx.py", "render/transitions.py", "render/palettes.py"]
CODE_BY_KIND = {
    "map": ["render/map_anim.py"],
    "graphic": ["render/infographic.py", "assets_code/common/shapes.py"],
    "scene": ["render/scene.py", "render/motion.py", "render/particles.py", "assets_code/**/*.py", "assets_code/custom/status.json"],
}


def scene_kind(sc):
    from render import infographic
    typ = sc.get("type")
    if typ == "map":
        return "map"
    if typ in infographic.TYPES:
        return "graphic"
    return "scene"


def code_version(kind=None):
    h = hashlib.sha1()
    pats = CODE_SHARED + (CODE_BY_KIND.get(kind, []) if kind else [p for v in CODE_BY_KIND.values() for p in v])
    files = sorted({f for pat in pats for f in glob.glob(os.path.join(ROOT, pat), recursive=True)})
    for p in files:
        with open(p, "rb") as f:
            h.update(f.read())
    return h.hexdigest()[:12]


def scene_hash(entry, plan, OW, OH, fps, cfg, ver):
    key = {"scene": entry["scene"], "dur": entry["dur"], "cues": entry["cues"], "OW": OW, "OH": OH, "fps": fps,
           "pal": plan.get("palette"), "country": plan.get("country"), "title": plan.get("title"), "lang": plan.get("language"),
           "render_v": 3, "cfg": {k: cfg.get(k) for k in ("supersample", "grain", "grain_animated", "burn_subtitles", "subtitle_size", "fade", "crf",
                                          "preset", "tune", "sharpen")}, "ver": ver}
    return hashlib.sha1(json.dumps(key, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def render_scene_job(job):
    """Chạy trong tiến trình con: dựng một cảnh ra mp4."""
    entry, plan, OW, OH, fps, cfg, out = job
    sys.path.insert(0, ROOT)
    t0 = time.time()
    rnd = SceneRenderer(entry, plan, OW, OH, fps, cfg)
    tmp = out + ".tmp.mp4"
    if rnd.is_static():
        png = out + ".png"
        rnd.frame_image(entry["dur"] / 2).save(png)
        f = cfg.get("fade", 0.4) / 2
        d = entry["dur"]
        vf = f"fade=in:st=0:d={f},fade=out:st={max(0, d - f)}:d={f}"
        r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", str(fps), "-i", png, "-frames:v",
                            str(entry["frames"])] + video_filter(cfg, vf) + x264_args(cfg)
                           + ["-r", str(fps), "-video_track_timescale", str(fps * 512), "-f", "mp4", tmp])
        os.remove(png)
        if r.returncode != 0:
            raise RuntimeError(f"FFmpeg lỗi khi dựng cảnh tĩnh {entry['scene'].get('id')}")
    else:
        p = ffmpeg_encoder(tmp, OW, OH, fps, cfg)
        try:
            for i in range(entry["frames"]):
                p.stdin.write(rnd.frame_image(i / fps).tobytes())
        finally:
            p.stdin.close()
        if p.wait() != 0:
            raise RuntimeError(f"FFmpeg lỗi khi dựng cảnh {entry['scene'].get('id')}")
    os.replace(tmp, out)
    return out, time.time() - t0


def _hms(sec):
    sec = int(sec)
    return f"{sec // 3600} giờ {sec % 3600 // 60} phút" if sec >= 3600 else f"{sec // 60} phút {sec % 60:02d} giây"


def resolve_quality(cfg, draft=False, quality=None):
    """Gộp mức chất lượng (nhap | chuan | cao | 4k) vào cấu hình dựng. Giá trị ghi rõ trong config vẫn được ưu tiên."""
    q = "nhap" if draft else (quality or cfg.get("quality") or "chuan")
    if q not in QUALITY:
        raise ValueError(f"Mức chất lượng '{q}' không có. Chọn: {', '.join(QUALITY)}")
    out = dict(cfg)
    preset = QUALITY[q]
    for k, v in preset.items():
        if k == "size" or q == "nhap" or out.get(k) is None:
            out[k] = v
    out["quality"] = q
    if q in ("cao", "4k") and not out.get("workers"):
        out["workers"] = max(1, min((os.cpu_count() or 2) - 1, 3 if q == "cao" else 2))
    return out


RAM_PER_WORKER_GB = {"nhap": 0.4, "chuan": 0.9, "cao": 1.6, "4k": 3.0}
MAX_WORKERS = 32          # quá số này máy chỉ tranh nhau RAM / ổ đĩa, không nhanh thêm
WIN_MAX_WORKERS = 60      # Windows: multiprocessing chỉ quản lý được tối đa ~61 tiến trình con


def free_ram_gb():
    """RAM còn trống (GB), không đọc được thì trả None."""
    try:
        if sys.platform == "win32":
            import ctypes

            class MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                            ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong),
                            ("ullAvailPageFile", ctypes.c_ulonglong), ("ullTotalVirtual", ctypes.c_ulonglong),
                            ("ullAvailVirtual", ctypes.c_ulonglong), ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            m = MS()
            m.dwLength = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return m.ullAvailPhys / 2 ** 30
        with open("/proc/meminfo") as f:
            for ln in f:
                if ln.startswith("MemAvailable:"):
                    return int(ln.split()[1]) / 2 ** 20
    except Exception:
        return None
    return None


def pick_workers(cfg, n_jobs):
    """Số cảnh dựng song song: theo số nhân CPU, RAM còn trống, giới hạn của Windows."""
    cpu = os.cpu_count() or 2
    asked = int(cfg.get("workers") or 0)
    n = asked if asked > 0 else min(cpu - 1, MAX_WORKERS)
    if asked <= 0:
        ram = free_ram_gb()
        if ram:
            n = min(n, int(ram * 0.75 / RAM_PER_WORKER_GB.get(cfg.get("quality"), 0.9)))
    if sys.platform == "win32":
        n = min(n, WIN_MAX_WORKERS)
    return max(1, min(n, n_jobs))


def render_video(plan, timeline, proj_dir, cfg, draft=False, log=print, only=None, quality=None):
    """Dựng mọi cảnh (có cache, song song) rồi ghép thành silent.mp4. Trả về đường dẫn silent.mp4."""
    cfg = resolve_quality(cfg, draft, quality)
    OW, OH = tuple(cfg["size"])
    fps = int(cfg.get("fps", 30))
    vers = {k: code_version(k) for k in CODE_BY_KIND}
    cdir = os.path.join(proj_dir, "cache", "scenes_" + cfg["quality"])
    os.makedirs(cdir, exist_ok=True)
    jobs, outs = [], []
    for e in timeline:
        sid = e["scene"]["id"]
        sc = e["scene"]
        ver = vers["scene"] if sc.get("scene") or sc.get("scene2") else vers[scene_kind(sc)]
        if scene_kind(sc) != "scene" and (sc.get("scene") or sc.get("scene2")):
            ver = vers["scene"] + vers[scene_kind(sc)]
        h = scene_hash(e, plan, OW, OH, fps, cfg, ver)
        out = os.path.join(cdir, f"scene_{int(sid):03d}_{h}.mp4") if str(sid).isdigit() else os.path.join(cdir, f"scene_{sid}_{h}.mp4")
        outs.append(out)
        if os.path.exists(out) or (only and sid not in only):
            continue
        jobs.append((e, plan, OW, OH, fps, cfg, out))
    log(f"Dựng {len(jobs)} cảnh mới / {len(timeline)} cảnh (còn lại lấy từ cache) — {OW}x{OH}, chất lượng '{cfg['quality']}'")
    workers = pick_workers(cfg, max(1, len(jobs)))
    # mỗi tiến trình nén video chỉ dùng phần nhân CPU của nó (nhiều tiến trình x nhiều luồng = tranh nhau, chậm hơn)
    cfg = dict(cfg, enc_threads=max(1, min(8, (os.cpu_count() or 2) // workers)))
    if len(jobs) > 1:
        log(f"   dựng song song {workers} cảnh một lúc")
    t0 = time.time()
    frames_of = {j[6]: j[0]["frames"] for j in jobs}
    total_frames = max(1, sum(frames_of.values()))
    done = [0]

    def eta(out):
        """Ước tính thời gian còn lại theo số khung đã dựng."""
        done[0] += frames_of.get(out, 0)
        el = time.time() - t0
        left = el / max(1, done[0]) * (total_frames - done[0])
        return f" — đã {done[0] * 100 // total_frames}%, còn khoảng {_hms(left)}" if done[0] < total_frames else ""

    if jobs:
        if workers == 1 or len(jobs) == 1:
            for k, j in enumerate(jobs):
                out, dt = render_scene_job(j)
                log(f"  [{k + 1}/{len(jobs)}] cảnh {j[0]['scene']['id']} xong ({dt:.1f}s){eta(out)}")
        else:
            ctx = mp.get_context("spawn")
            with ctx.Pool(workers) as pool:
                for k, (out, dt) in enumerate(pool.imap_unordered(render_scene_job, jobs)):
                    log(f"  [{k + 1}/{len(jobs)}] {os.path.basename(out)} xong ({dt:.1f}s){eta(out)}")
    log(f"Dựng hình xong sau {time.time() - t0:.0f}s")
    # dọn file cache cũ không còn dùng
    keep = set(outs)
    for f in glob.glob(os.path.join(cdir, "scene_*.mp4")):
        if f not in keep and not f.endswith(".tmp.mp4"):
            try:
                os.remove(f)
            except OSError:
                pass
    log(f"🔗 Ghép {len(outs)} cảnh thành một video liền...")
    lst = os.path.join(proj_dir, "cache", "concat.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for o in outs:
            f.write("file '" + os.path.abspath(o).replace("\\", "/").replace("'", "'\\''") + "'\n")
    silent = os.path.join(proj_dir, "cache", f"silent_{cfg['quality']}.mp4")
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent + ".tmp.mp4"])
    if r.returncode != 0:
        raise RuntimeError("FFmpeg không ghép được các cảnh (concat).")
    os.replace(silent + ".tmp.mp4", silent)
    return silent


def mux(silent, wav, out, loudness=-16.0):
    tmp = out + ".tmp.mp4"
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", silent, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                        "-af", f"loudnorm=I={loudness}:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "192k",
                        "-shortest", "-movflags", "+faststart", tmp])
    if r.returncode != 0:
        raise RuntimeError("FFmpeg không ghép được âm thanh vào video.")
    os.replace(tmp, out)
    return out


# ======================================================================== preview
def busy_time(entry):
    sc = entry["scene"]
    d = entry["dur"]
    if sc.get("type") == "map":
        return d * 0.92
    if sc.get("type") in ("title", "text_card"):
        return min(d - 0.3, max(2.6, d * 0.75))
    if entry["cues"]:
        return entry["cues"][0][0] + min(2.0, (entry["cues"][0][1] - entry["cues"][0][0]) / 2)
    return d * 0.6


def preview_grid(plan, timeline, out_path, cfg, cols=4, log=print):
    OW, OH = 960, 540
    fps = 10
    cfg = dict(cfg, supersample=1.6)
    thumbs = []
    for e in timeline:
        t = busy_time(e)
        try:
            rnd = SceneRenderer(e, plan, OW, OH, fps, cfg)
            v = rnd.vis
            if isinstance(v, SceneVisual):
                v._warm = True
                v.compose(0)
            for s in getattr(v, "systems", []):
                if s.kind in ("embers", "smoke", "sparks", "dust"):
                    s.warm(2.0)
            img = Image.fromarray(rnd.frame(t))
        except Exception as ex:   # cảnh lỗi vẫn hiện ô báo lỗi
            img = Image.new("RGB", (OW, OH), (60, 0, 0))
            RichFont("sans", 22).draw(ImageDraw.Draw(img), (20, 240), f"LỖI: {ex}"[:80], (255, 255, 255))
        lab = text_layer(f"#{e['scene']['id']} · {e['scene'].get('type', '')} · {e['dur']:.1f}s", "sans_bold", 22, fill=(255, 255, 255))
        img = img.convert("RGBA")
        img.alpha_composite(lab, (10, 8))
        thumbs.append(img.convert("RGB").resize((480, 270)))
        log(f"  xem trước cảnh {e['scene']['id']}")
    rows = math.ceil(len(thumbs) / cols)
    g = Image.new("RGB", (cols * 480 + (cols + 1) * 6, rows * 270 + (rows + 1) * 6), (20, 20, 20))
    for i, th in enumerate(thumbs):
        g.paste(th, (6 + (i % cols) * 486, 6 + (i // cols) * 276))
    g.save(out_path, quality=88)
    return out_path
