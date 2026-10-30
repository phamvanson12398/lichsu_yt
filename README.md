# Tool tự làm video lịch sử cho YouTube

Gõ một dòng chủ đề → tool viết kịch bản (kèm ghi chú nguồn), lập kế hoạch dựng, tạo giọng đọc, **vẽ toàn bộ hình
bằng code** (cảnh minh họa nhiều lớp, bản đồ động, hiệu ứng chữ), tổng hợp âm thanh + nhạc nền theo từng nước,
rồi xuất `video_final.mp4` + `youtube.txt`. Tool **không tự đăng YouTube** — bạn luôn xem lại trước.

- Không dùng ảnh / clip bên ngoài (không Veo, Pexels, Pixabay, Google Images, YouTube).
- AI gọi qua **Claude Code CLI** (`claude`) và **Antigravity CLI** (`agy`) đã đăng nhập — không cần API key.
- Giọng đọc **OmniVoice** chạy trên máy (nhân bản giọng của bạn hoặc thiết kế giọng tự động).
- Chủ đề: Việt Nam, Hàn Quốc, Nhật Bản, Anh (mở rộng thêm được). Khung 1920x1080, 30 fps.

👉 Cài đặt từng bước: **[HUONG_DAN_CAI_DAT.md](HUONG_DAN_CAI_DAT.md)**

## Dùng nhanh trên Windows (bấm đúp)

| File | Việc |
|---|---|
| `CAI_DAT.bat` | Cài lần đầu: kiểm tra / cài Python 3.12, thư viện, FFmpeg (qua winget), rồi kiểm tra máy |
| `CAI_GIONG_DOC.bat` | Cài giọng đọc OmniVoice + PyTorch (tự chọn bản GPU NVIDIA hay CPU) |
| `CHAY_TOOL.bat` | **Menu tiếng Việt**: tạo video mới, chạy tiếp, xem trước, dựng lại, giọng đọc, video mẫu... |
| `GIAO_DIEN_WEB.bat` | **Giao diện web đẹp** trong trình duyệt (http://127.0.0.1:8765): dự án có ảnh bìa, tạo video, sửa kịch bản / plan, xem video, giọng đọc (kéo thả file hoặc ghi âm trực tiếp), cài đặt, nhật ký chạy trực tiếp |
| `GIAO_DIEN.bat` | Giao diện cửa sổ đơn giản (tkinter) |

Lần đầu bấm `CHAY_TOOL.bat` mà chưa cài, tool tự chạy phần cài đặt.

## Dùng nhanh bằng dòng lệnh

```
python main.py demo                                   # video mẫu ~35 giây (không cần AI, giọng)
python main.py "Trận Bạch Đằng năm 938 (10p)"          # chạy, dừng để duyệt kịch bản rồi plan
python main.py continue bach_dang_938                 # chạy tiếp sau khi duyệt / sửa
python main.py "Trận Hastings năm 1066 (8p)" --auto    # chạy hết không dừng
python main.py preview bach_dang_938                  # ảnh lưới xem trước mỗi cảnh
python main.py render  bach_dang_938 --draft          # dựng nháp 960x540 cho nhanh
python app.py                                         # giao diện đơn giản
```

Đầu vào một dòng: chủ đề + thời lượng trong ngoặc (`(10p)` = 10 phút; không ghi thì 10 phút).
Tool tự nhận nước / thời kỳ từ chủ đề.

### Ngôn ngữ lời kể: Việt, Anh, Hàn, Nhật

Mặc định kể bằng tiếng Việt (`narration_language: vi` trong `config.yaml`). Đổi cho từng video:

```
python main.py "Trận Hastings năm 1066 (8p, en)"        # tiếng Anh
python main.py "Trận Hansan năm 1592 (8p, ko)"          # tiếng Hàn
python main.py "Trận Sekigahara năm 1600 (12p, ja)"     # tiếng Nhật
python main.py "Trận Bạch Đằng năm 938 (10p)" --lang en # hoặc dùng --lang
```

Theo ngôn ngữ, tool tự đổi: kịch bản (AI viết văn bản ngữ, độ dài tính theo từ / ký tự: en 150 từ/phút, ko & ja ~300 ký tự/phút),
đọc số (`1066` → "ten sixty-six", `1592년` → "천오백구십이년", `1600年` → "千六百年"), tách câu (。！？), phụ đề và xuống dòng
(tiếng Nhật ngắt theo ký tự, ưu tiên sau 、), font (Noto Serif KR / JP có sẵn trong `fonts/`), chữ trên bản đồ, `youtube.txt`,
câu thử giọng và nhận dạng giọng nói. Ghi chú nguồn trong `script.md` vẫn bằng tiếng Việt để bạn kiểm tra.
Từ điển phát âm riêng: `pronunciation.en.json`, `pronunciation.ko.json`, `pronunciation.ja.json`.
Giọng: `python main.py voice add giong_anh --file en.m4a --lang en` rồi `python main.py voice default giong_anh --lang en`.

### Độ nét

```
python main.py render bach_dang_938 --quality cao      # nhap (960x540) | chuan (1080p) | cao (1440p) | 4k
```

Đặt mặc định trong `config.yaml` → `render: quality:`. Mỗi cảnh vẽ ở 2x rồi thu nhỏ (không răng cưa), camera phóng ảnh bằng
bicubic, nén x264 preset medium + tune animation, CRF 18, làm nét nhẹ (unsharp). **Mẹo:** tải lên YouTube bản 1440p hoặc 4K —
YouTube nén bằng VP9 / AV1 với bitrate cao hơn nên người xem ở 1080p cũng thấy nét hơn rõ (đổi lại dựng lâu hơn ~1.8x / ~4x).

### Các bước và file trong dự án `projects/<tên>/`

| Bước | Lệnh riêng | File |
|---|---|---|
| 1. Phân tích đầu vào | (tự động) | `input.json` |
| 2. Viết kịch bản (AI, kèm nguồn) | `script <dự án>` | `script.md` (sửa được), `script.json`, `script_check.md` |
| 3. Lập kế hoạch dựng (AI) | `plan <dự án> [--offline]`, `validate <dự án>` | `plan.json` |
| 4. Tạo giọng (OmniVoice) | `voice-gen <dự án> [--voice tên]` | `voice/*.wav`, `voice/timings.json` |
| 5–6. Dựng hình, trộn âm, xuất | `render <dự án> [--draft]` | `output/video_final.mp4`, `output/youtube.txt`, `output/phu_de.srt` |

Dừng duyệt mặc định sau bước 2 và 3 (`review_after` trong `config.yaml`). Sửa `script.md` thì chạy
`python main.py plan <dự án>` để lập lại plan; sửa `plan.json` thì chạy `render` (cảnh không đổi lấy từ cache).
`python main.py diversify <dự án>` đổi góc nhìn các cảnh lặp nhau (nhìn qua tán lá, tướng chỉ huy cận cảnh, lau sậy,
đổi chuyển động camera) mà không gọi AI, không đổi lời đọc; bản cũ lưu ở `plan_truoc_da_dang.json`.

**Các kiểu cảnh cho video đa dạng:** ngoài cảnh rộng và bản đồ còn có cảnh đồ họa `timeline` (dòng thời gian),
`character` (thẻ nhân vật), `compare` (biểu đồ so sánh quân số, luôn kèm ghi chú độ chắc chắn), `tide` (sơ đồ thủy triều);
cảnh cận / trung `commander` (tướng chỉ huy), `war_drum` (trống trận), nền `hall` + `council` (bàn kế trong điện / lều),
`foliage_frame` (nhìn qua tán lá ra sông). AI lập kế hoạch được dặn không để quá 2 cảnh liền cùng kiểu nền.

### Giọng đọc

```
python main.py voice add giong_cua_toi --file giong.m4a --text "lời mẫu"   # (A) nhân bản giọng của bạn
python main.py voice auto "Trận Hansan năm 1592"                          # (B) AI đề xuất + 3 ứng viên
python main.py voice design giong_tram --instruct "male, middle-aged, low pitch"
python main.py voice list | play <tên> | default <tên> [--country japan] | delete <tên>
python main.py voice-save giong_cua_toi --ref ref.wav --text "lời của đoạn mẫu"
```

Giọng thiết kế được "khoá" bằng cách lấy chính file nghe thử làm đoạn mẫu nhân bản → cả video một giọng.
Số / năm tự đổi thành chữ (`938` → "chín trăm ba mươi tám"), số La Mã, viết tắt; tên riêng nước ngoài đọc theo
`pronunciation.json`. Mỗi câu được nhận dạng lại để kiểm tra; câu sai nhiều tự tạo lại (tối đa 3 lần) rồi đánh dấu
"nên nghe lại". Câu không đổi thì không tạo lại (cache).

### Thư viện thành phần vẽ

```
python main.py component list [--country japan]
python main.py component new beacon_tower --desc "phong hỏa đài trên núi" --country korea   # AI viết hàm mới
python main.py component approve beacon_tower                                               # sau khi xem preview
```

Thành phần do AI viết chỉ được lưu vào `assets_code/custom/`, qua kiểm tra an toàn (không đọc/ghi file, không gọi
mạng) và phải xem trước + duyệt mới dùng được.

## Định dạng plan.json (tóm tắt)

```json
{
  "title": "Trận Bạch Đằng năm 938", "country": "vietnam", "era": "thế kỷ 10", "year": 938,
  "palette": "hoang_hon_do", "voice": "giong_cua_toi",
  "scenes": [
    {"id": 1, "type": "title",
     "scene": {"time_of_day": "dusk", "weather": "clear", "background": ["sky", "mountains:3", "river"],
               "elements": [{"kind": "stakes_field", "x": 0.2, "y": 0.68, "density": "high"},
                            {"kind": "boat_vn", "x": 0.7, "y": 0.62, "scale": 0.5, "count": 2}]},
     "motion": "zoom_in_slow", "particles": ["mist"],
     "text": "TRẬN BẠCH ĐẰNG", "subtext": "Năm 938", "text_style": "cinematic", "sfx": ["riser", "boom"], "duration": 4.0},
    {"id": 2, "type": "narration", "scene": {"...": "..."}, "motion": "parallax_right",
     "narration": "Năm 938, Ngô Quyền cho quân cắm cọc...", "sfx_at": [{"t": 1.5, "tag": "song_nuoc"}], "mood": "cang_thang"},
    {"id": 3, "type": "text_card", "text": "938", "text_style": "count_year", "count_from": 900, "duration": 3.5},
    {"id": 4, "type": "map", "map": {"features": ["river", "coast_right", "islands"],
       "labels": [{"text": "Sông Bạch Đằng", "at": [0.2, 0.3]}],
       "arrows": [{"side": "enemy", "path": [[0.95,0.75],[0.6,0.55],[0.35,0.38]], "start": 1.8, "dur": 2.4, "label": "Thuyền quân Nam Hán"}],
       "markers": [{"kind": "stakes", "at": [0.47,0.44], "start": 0.6}, {"kind": "clash_x", "at": [0.47,0.44], "start": 6.9}]},
     "narration": "..."}
  ]
}
```

- Toạ độ 0–1 theo khung hình; `y` của thành phần = điểm chạm nước / đất. Đường chân trời mặc định 0.58.
- Cảnh có `narration`: thời lượng = độ dài giọng + đệm 0.4 s. Không có lời: dùng `duration`.
- Kiểu cảnh: `title | narration | text_card | map | pause`.
- Chuyển động: `static, zoom_in_slow, zoom_out_slow, zoom_in_fast, pan_left, pan_right, parallax_left, parallax_right`.
- Hạt: `embers, smoke, fire_glow, mist, rain, snow, dust, sparks, cherry_blossom, leaves` (thêm `:0.5` để chỉnh độ dày).
- Kiểu chữ: `cinematic, typewriter, word_by_word, slide_in, count_year, subtitle` (+ `text_start`, `text_pos`).
- Âm thanh (`sfx`, `sfx_at`): `boom, riser, shimmer, click, pop, whoosh, tick, bell, lua_tach, gio_u, song_nuoc, tieng_tron, kiem_cham, mua, vo_ngua, ten_bay`.
  Âm nền (`ambience`) tự thêm theo cảnh: sông/biển → sóng nước, lửa → lửa lách tách, mưa, gió.
- Nhạc nền: `mood` = `yen_binh | cang_thang | cao_trao | bi_trang | ket_thuc` (ghi ở cảnh đổi tâm trạng).
- Thêm: `palette` riêng cảnh, `flash_at` (chớp sáng va chạm), `transition` (`fade` | `cut`), `fade`,
  `scene2` + `switch_at` (crossfade bên trong một cảnh), thành phần có `move: [dx, dy]` (tiến quân / thuyền chạy),
  `layer: far|mid|near|front|fg`, `state: burning|broken`, `flip`, `tilt`.
- Bảng màu: `hoang_hon_do, dem_lua, binh_minh_xanh, suong_mu_xam, tuyet_trang, giay_co, trua_nang, dem_trang`.

`python main.py validate <dự án>` kiểm tra plan (kiểu cảnh, thành phần có trong thư viện, thời gian, đúng nước /
thời kỳ — vd không có súng trước 1543, không lâu đài Nhật trong trận Việt Nam) và báo lỗi tiếng Việt.

## Cấu trúc thư mục

```
config.yaml            chọn claude / agy cho từng việc, giọng, thông số dựng
main.py, app.py        dòng lệnh, giao diện đơn giản
core/                  input_parser, script_writer, planner, plan_schema, pipeline, export, components_ai
  llm/                 base (ask + kiểm JSON + sửa lỗi 3 lần + fallback), claude_cli, agy_cli
  voice/               omnivoice_engine, voice_library, text_norm
render/                scene (lớp + parallax), motion, particles, map_anim, text_fx, transitions, renderer, palettes
assets_code/           common/, vietnam/, china/, korea/, japan/, england/, custom/  (hàm vẽ thành phần)
audio/                 sfx_synth, music_synth, mixer
voices/                thư viện giọng
projects/<dự án>/      script.md, plan.json, voice/, cache/, logs/, output/
samples/               plan.json viết tay mẫu (GĐ1)
fonts/                 Noto Serif / Noto Sans (SIL Open Font License)
```

## Kỹ thuật

- Mỗi cảnh vẽ ở 2x rồi thu về độ phân giải làm việc (1.2x cho cảnh zoom), khung hình đẩy thẳng vào FFmpeg qua
  stdin (rawvideo rgb24), libx264 veryfast CRF 19, yuv420p; AAC 192k; âm chuẩn hoá −16 LUFS (loudnorm).
- Mỗi cảnh 1 file mp4 (ghi tên tạm, đổi tên khi FFmpeg exit 0), ghép bằng concat demuxer `-c copy`.
- Cache theo hash nội dung cảnh + mã nguồn thành phần; dựng song song nhiều cảnh (multiprocessing).
- Cảnh tĩnh dùng `-loop 1` của FFmpeg, không vẽ lại từng khung.

## Lưu ý

- Hình vẽ bằng code là tranh minh họa, không phải ảnh thật; bản đồ luôn ghi "Sơ đồ minh họa, không theo tỉ lệ".
- Kịch bản luôn kèm ghi chú nguồn — hãy kiểm tra năm, tên người, số liệu trước khi đăng.
- OmniVoice có giấy phép CC-BY-NC (phi thương mại). Chỉ nhân bản giọng của bạn hoặc người đã đồng ý.
- YouTube hạn chế kiếm tiền với nội dung hàng loạt, rập khuôn: giữ dấu ấn riêng (giọng thật, góc nhìn riêng).
