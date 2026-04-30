@echo off
REM Erstellt und befüllt eine virtuelle Python-Umgebung fuer Windows
REM Verwendung: setup_venv.bat

set VENV_DIR=venv

REM Python pruefen
python --version >nul 2>&1
if errorlevel 1 (
    echo Fehler: python nicht gefunden. Bitte Python 3.9+ von python.org installieren.
    pause
    exit /b 1
)

REM venv erstellen
python -m venv %VENV_DIR%

REM Pakete installieren
%VENV_DIR%\Scripts\pip install --upgrade pip
%VENV_DIR%\Scripts\pip install -r requirements.txt

echo.
echo Fertig. Aktivieren mit:
echo   %VENV_DIR%\Scripts\activate
echo Starten mit:
echo   python game2d.py
pause
