@echo off
setlocal

if exist .venv\Scripts\python.exe (
    .\.venv\Scripts\python.exe game2d.py
    exit /b %errorlevel%
)

if exist venv\Scripts\python.exe (
    .\venv\Scripts\python.exe game2d.py
    exit /b %errorlevel%
)

echo Fehler: Keine virtuelle Umgebung gefunden. Fuehre zuerst setup_venv.bat aus.
exit /b 1
