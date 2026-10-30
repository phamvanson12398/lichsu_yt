@echo off
rem Tìm Python: ưu tiên trình khởi chạy "py", sau đó "python"
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY exit /b 1
rem "python" giả của Microsoft Store không chạy được -> coi như chưa cài
%PY% --version >nul 2>nul || exit /b 1
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if errorlevel 1 exit /b 2
exit /b 0
