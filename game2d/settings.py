"""Lade/Speichere Spieleinstellungen aus ``settings.json`` im Repo-Root.

Format: flaches JSON-Objekt. Unbekannte Keys werden ignoriert, fehlende mit
Defaults aufgefüllt. Korrupte/fehlende Datei → Defaults.
"""
import json
import os


SETTINGS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'settings.json',
)

DEFAULTS = {
    'sfx_volume': 0.5,
}


def load():
    """Settings aus Datei lesen und mit Defaults mergen."""
    out = dict(DEFAULTS)
    try:
        with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for k, v in data.items():
            if k in DEFAULTS:
                out[k] = v
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    out['sfx_volume'] = max(0.0, min(1.0, float(out['sfx_volume'])))
    return out


def save(settings):
    """Settings atomisch nach SETTINGS_PATH schreiben."""
    tmp = SETTINGS_PATH + '.tmp'
    try:
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
        os.replace(tmp, SETTINGS_PATH)
    except OSError:
        pass
