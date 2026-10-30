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

if not exist "%~dp0.da_cai_dat" (
    call "%~dp0CAI_DAT.bat" /im_lang
    if errorlevel 1 (
        pause
        exit /b 1
    )
)
echo Dang mo giao dien web... Trinh duyet se tu mo. GIU CUA SO NAY MO trong luc dung.
%PY% "%~dp0web\server.py"
if errorlevel 1 pause
endlocal
exit /b 0

:setpy
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY set "PY=python"
exit /b 0
