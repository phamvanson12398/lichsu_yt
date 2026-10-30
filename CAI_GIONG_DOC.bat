@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
call "%~dp0_tim_python.bat"
if errorlevel 2 (
    echo.
    echo [LOI] Python tren may cu hon 3.11. Hay cai Python 3.12 tu https://www.python.org/downloads/
    echo       nho tick "Add python.exe to PATH" khi cai.
    pause
    exit /b 1
)
if errorlevel 1 (
    echo.
    echo [LOI] Chua cai Python. Chay file CAI_DAT.bat truoc, hoac cai Python 3.12 tu https://www.python.org/downloads/
    echo       nho tick "Add python.exe to PATH" khi cai.
    pause
    exit /b 1
)
call :setpy

echo ==========================================================
echo    CÀI GIỌNG ĐỌC OMNIVOICE (PyTorch + OmniVoice)
echo ==========================================================
echo  Tải khoảng 2-3 GB, có thể mất 10-30 phút tuỳ mạng.
echo.
where nvidia-smi >nul 2>nul
if errorlevel 1 (
    echo Không thấy card NVIDIA: cài PyTorch bản CPU ^(giọng đọc sẽ chạy chậm^).
    %PY% -m pip install torch torchaudio
) else (
    echo Thấy card NVIDIA: cài PyTorch bản CUDA ^(nhanh^).
    nvidia-smi --query-gpu=name --format=csv,noheader
    %PY% -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
)
if errorlevel 1 (
    echo Cài PyTorch bị lỗi. Xem HUONG_DAN_CAI_DAT.md mục 5.
    pause
    exit /b 1
)
echo.
echo Cài OmniVoice...
%PY% -m pip install "omnivoice[tn]"
if errorlevel 1 %PY% -m pip install omnivoice
echo.
%PY% main.py check
echo.
echo Xong. Thêm giọng của bạn: CHAY_TOOL.bat -^> mục 6 "Giọng đọc".
pause
endlocal
exit /b 0

:setpy
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY set "PY=python"
exit /b 0
