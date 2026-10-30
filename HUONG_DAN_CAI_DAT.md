# HƯỚNG DẪN CÀI ĐẶT (Windows) — từng bước

Tài liệu cho người không phải lập trình viên. Làm lần lượt từ trên xuống. Mỗi lệnh gõ vào **cửa sổ lệnh**
(bấm phím Windows, gõ `cmd`, Enter). Gõ xong một lệnh thì bấm Enter.

---

## 1. Cài Python 3.11 trở lên

1. Vào https://www.python.org/downloads/ → bấm **Download Python 3.12** (hoặc mới hơn).
2. Mở file vừa tải. **QUAN TRỌNG:** tick ô **"Add python.exe to PATH"** ở màn hình đầu, rồi bấm **Install Now**.
3. Kiểm tra: mở cửa sổ lệnh mới, gõ:

   ```
   python --version
   ```

   Thấy `Python 3.12.x` là được.

## 2. Cài FFmpeg (ghép video, âm thanh)

Cách dễ nhất (Windows 10/11 có sẵn `winget`):

```
winget install Gyan.FFmpeg
```

Đóng cửa sổ lệnh, mở lại, gõ `ffmpeg -version` để kiểm tra.
(Nếu không có winget: tải bản "release essentials" ở https://www.gyan.dev/ffmpeg/builds/, giải nén vào `C:\ffmpeg`,
rồi thêm `C:\ffmpeg\bin` vào biến môi trường Path.)

## 3. Tải tool và cài thư viện

1. Tải thư mục tool về máy (ví dụ `D:\video_lich_su`).
2. Mở cửa sổ lệnh tại thư mục đó: trong File Explorer, bấm vào thanh địa chỉ, gõ `cmd`, Enter.
3. Cài thư viện:

   ```
   pip install -r requirements.txt
   ```

4. Kiểm tra máy:

   ```
   python main.py check
   ```

5. Làm thử video mẫu 30 giây (không cần AI, không cần giọng):

   ```
   python main.py demo
   ```

   Kết quả ở `projects\demo_bach_dang_938\output\video_final.mp4`.

## 4. Cài AI CLI (viết kịch bản, lập kế hoạch dựng)

Tool **không dùng API key**. Tool gọi 2 chương trình dòng lệnh đã đăng nhập bằng gói đăng ký của bạn.
Chỉ cần ít nhất MỘT trong hai; có cả hai thì một bên hết lượt tool tự chuyển sang bên kia.

### 4a. Claude Code (lệnh `claude`)
- Cài theo hướng dẫn chính thức: https://docs.claude.com/en/docs/claude-code/setup
- Đăng nhập: mở cửa sổ lệnh, gõ `claude`, làm theo hướng dẫn đăng nhập bằng tài khoản Claude (gói Pro / Max). Xong gõ `/exit`.

### 4b. Google Antigravity CLI (lệnh `agy`, Gemini Pro)
- Cài theo hướng dẫn của Google Antigravity, sau đó gõ `agy` để đăng nhập tài khoản Google.
- Nếu `agy` không nhận nội dung qua stdin, mở `config.yaml`, sửa `prompt_via: stdin` thành `prompt_via: arg`.
- Giới hạn quyền ghi file cho agy (khuyên dùng): trong `%USERPROFILE%\.gemini\antigravity-cli\settings.json`
  thêm quy tắc "permissions" chỉ cho phép ghi vào thư mục `assets_code` của tool. Tool hiện chỉ dùng agy để
  trả lời văn bản / JSON, nên không cần cấp quyền ghi.

### 4c. Chọn AI cho từng việc
Mở `config.yaml` bằng Notepad:

```yaml
writer: agy        # ai viết kịch bản
planner: claude    # ai lập plan.json
checker: claude    # ai kiểm tra lại sự kiện
fallback: true     # một bên lỗi / hết lượt thì tự chuyển sang bên kia
```

Lưu ý: hai CLI dùng hạn mức gói đăng ký. Tool đã gộp việc thành ít lần gọi
(viết kịch bản 1–2 lần, lập plan theo từng phần lớn ~450 chữ).

## 5. Giọng đọc OmniVoice (chạy trên máy, miễn phí)

### 5a. Có card đồ hoạ NVIDIA (khuyên dùng)
1. Cài PyTorch bản CUDA (chọn đúng lệnh ở https://pytorch.org/get-started/locally/), ví dụ:

   ```
   pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
   ```

2. Cài OmniVoice:

   ```
   pip install "omnivoice[tn]"
   ```

3. `python main.py check` phải thấy dòng `✔ PyTorch ... GPU: ...` và `✔ OmniVoice`.

### 5b. Không có card NVIDIA
- `pip install torch torchaudio` rồi `pip install "omnivoice[tn]"`. Chạy bằng CPU được nhưng CHẬM
  (tool sẽ báo thời gian ước tính sau câu đầu tiên). Máy Mac chip M dùng bản PyTorch thường.

### 5c. Thêm giọng của bạn (cách A — khuyên dùng, tiếng Việt tốt nhất)
1. Thu âm 10–30 giây đọc một đoạn văn bất kỳ, phòng yên tĩnh (điện thoại cũng được), lưu file mp3 / m4a / wav.
2. Chạy:

   ```
   python main.py voice add giong_cua_toi --file D:\giong.m4a --text "đúng lời bạn đã đọc trong file"
   ```

   - Tool tự chuyển định dạng, cắt khoảng lặng, chuẩn hoá âm lượng, chọn đoạn sạch nhất 3–10 giây.
   - Bỏ `--text` thì tool tự nhận dạng lời rồi cho bạn sửa.
   - Tool hỏi xác nhận "Đây là giọng của tôi hoặc tôi đã được người này đồng ý". **Không nhân bản giọng người nổi tiếng.**
   - Nghe câu thử, gõ `co` để lưu.
3. Đặt làm giọng mặc định: `python main.py voice default giong_cua_toi`
   (theo nước: `python main.py voice default giong_cua_toi --country japan`)

### 5d. Giọng thiết kế tự động (cách B)
- `python main.py voice auto "Trận Hansan năm 1592"` → AI đề xuất 3 mô tả giọng, tool tạo 3 ứng viên, bạn nghe và chọn.
- Hoặc tự mô tả: `python main.py voice design giong_tram --instruct "male, middle-aged, low pitch"`.
- Lưu ý: voice design của OmniVoice học chủ yếu bằng tiếng Trung / Anh nên tiếng Việt có thể kém ổn định —
  nghe thử trước, nếu chưa tốt hãy dùng cách A.

### 5e. Bản quyền
Mô hình OmniVoice có giấy phép **CC-BY-NC (phi thương mại)**. Nếu kênh bật kiếm tiền, đặt `kenh_kiem_tien: true`
trong `config.yaml` để tool nhắc; hãy tự cân nhắc trước khi dùng cho kênh kiếm tiền.

## 6. Font chữ
- Font Noto Serif (đủ dấu tiếng Việt) đã có sẵn trong thư mục `fonts/`.
- Muốn hiện tên gốc tiếng Hàn / Nhật (vd 이순신, 関ヶ原): `python main.py fonts` (tải Noto Serif KR / JP), hoặc
  Windows đã có sẵn Malgun Gothic / Yu Gothic, tool tự tìm.

## 7. Lỗi thường gặp

| Thông báo | Cách xử lý |
|---|---|
| `Chưa cài 'claude'` / `'agy'` | Làm lại mục 4; mở cửa sổ lệnh MỚI sau khi cài. |
| `chưa đăng nhập` | Gõ `claude` (hoặc `agy`) để đăng nhập, rồi chạy lại. |
| `đã hết lượt dùng của gói đăng ký` | Đợi gói được làm mới, hoặc để `fallback: true` dùng AI còn lại. |
| `trả lời quá lâu` | Tăng `timeout` trong `config.yaml`, chạy lại `python main.py continue <dự án>`. |
| `FFmpeg` không có | Làm lại mục 2, mở cửa sổ lệnh mới. |
| Chữ tiếng Việt bị ô vuông | Kiểm tra thư mục `fonts/` còn file NotoSerif-*.ttf. |
| Giọng đọc sai tên riêng | Thêm vào `pronunciation.json` (vd `"Sekigahara": "Xê-ki-ga-ha-ra"`). |
