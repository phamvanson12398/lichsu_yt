@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
echo ==========================================================
echo    CÀI ĐẶT TOOL VIDEO LỊCH SỬ
echo ==========================================================
echo.
echo [1/4] Kiểm tra Python...
call "%~dp0_tim_python.bat"
if errorlevel 2 (
    echo   Python trên máy cũ hơn 3.11. Hãy cài Python 3.12: https://www.python.org/downloads/
    echo   ^(nhớ tick "Add python.exe to PATH"^), rồi chạy lại file này.
    goto :ketthuc_loi
)
if errorlevel 1 (
    echo   Chưa có Python. Đang thử cài Python 3.12 bằng winget...
    where winget >nul 2>nul || (
        echo   Máy không có winget. Hãy tự cài Python 3.12 từ https://www.python.org/downloads/
        echo   ^(nhớ tick "Add python.exe to PATH"^), rồi chạy lại file này.
        goto :ketthuc_loi
    )
    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    echo.
    echo   Đã cài Python. HÃY ĐÓNG CỬA SỔ NÀY VÀ BẤM ĐÚP CAI_DAT.bat LẦN NỮA.
    goto :ketthuc_loi
)
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY set "PY=python"
%PY% --version

echo.
echo [2/4] Cài thư viện Python (Pillow, numpy, PyYAML...)...
%PY% -m pip install --upgrade pip >nul
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
    echo   Cài thư viện bị lỗi. Kiểm tra kết nối mạng rồi chạy lại.
    goto :ketthuc_loi
)

echo.
echo [3/4] Kiểm tra FFmpeg...
where ffmpeg >nul 2>nul
if errorlevel 1 (
    echo   Chưa có FFmpeg. Đang thử cài bằng winget...
    where winget >nul 2>nul && (
        winget install -e --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
        echo   Đã cài FFmpeg. Hãy đóng cửa sổ này, mở lại để máy nhận FFmpeg.
    ) || (
        echo   Máy không có winget. Xem HUONG_DAN_CAI_DAT.md mục 2 để cài FFmpeg bằng tay.
    )
) else (
    echo   Đã có FFmpeg.
)

echo.
echo [4/4] Kiểm tra toàn bộ...
%PY% main.py check
echo ok> "%~dp0.da_cai_dat"
echo.
echo ----------------------------------------------------------
echo  Xong. Giọng đọc OmniVoice cài riêng bằng CAI_GIONG_DOC.bat
echo  Dùng tool: bấm đúp CHAY_TOOL.bat
echo ----------------------------------------------------------
if /i not "%~1"=="/im_lang" pause
endlocal
exit /b 0

:ketthuc_loi
echo.
if /i not "%~1"=="/im_lang" pause
endlocal
exit /b 1
