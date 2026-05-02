#!/usr/bin/env bash
# Erstellt und befüllt eine virtuelle Python-Umgebung für Linux/macOS
# Verwendung: bash setup_venv.sh

set -e

VENV_DIR="venv"

# Python 3 prüfen
if ! command -v python3 &> /dev/null; then
    echo "Fehler: python3 nicht gefunden. Bitte Python 3.9+ installieren."
    exit 1
fi

# venv erstellen
python3 -m venv "$VENV_DIR"

# Pakete installieren
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r requirements.txt

echo ""
echo "Fertig. Aktivieren mit:"
echo "  source $VENV_DIR/bin/activate"
echo "Starten mit:"
echo "  python game2d.py"
