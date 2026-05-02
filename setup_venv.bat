@echo off
REM Erstellt und befuellt eine virtuelle Python-Umgebung fuer Windows
REM Verwendung: setup_venv.bat

set VENV_DIR=venv

REM Python pruefen
python --version >nul 2>&1
if errorlevel 1 (
    echo Fehler: python nicht gefunden. Bitte Python 3.10+ von python.org installieren.
    pause
    exit /b 1
)

REM venv erstellen
python -m venv %VENV_DIR%
if errorlevel 1 (
    echo Fehler: venv konnte nicht erstellt werden.
    pause
    exit /b 1
)

REM Pakete installieren
%VENV_DIR%\Scripts\python -m pip install --upgrade pip
%VENV_DIR%\Scripts\pip install -r requirements.txt
if errorlevel 1 (
    echo Fehler: Pakete konnten nicht installiert werden.
    pause
    exit /b 1
)

echo.
echo Fertig. Aktivieren mit:
echo   %VENV_DIR%\Scripts\activate
echo Starten mit:
echo   python game2d.py
pause
