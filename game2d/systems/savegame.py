"""Spielstand-Speichern und Laden.

Erweitert das bestehende Persistenz-System um vollständige Spielstand-Speicherung.

Features:
- Speichern des Spielzustands (Geld, Waffen, Position, etc.)
- Laden von gespeicherten Spielen
- Mehrere Spielstand-Slots
- Automatisches Speichern

Usage:
    from game2d.systems.savegame import save_game, load_game, has_saved_game
    
    # Spielstand speichern
    save_game(state, slot=1)
    
    # Spielstand laden
    load_game(state, slot=1)
    
    # Prüfen ob ein Spielstand existiert
    if has_saved_game(slot=1):
        # Lade Spielstand
        pass
"""
import json
import os
from datetime import datetime
from typing import Any, Optional

from game2d.state import GameState
from game2d.systems.validation import validate_and_fix


# Verzeichnis für Spielstand-Dateien
SAVE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'saves'
)

# Anzahl der Spielstand-Slots
NUM_SLOTS = 5

# Schema für Spielstand-Validierung
SAVEGAME_SCHEMA = {
    'type': 'object',
    'properties': {
        'version': {'type': 'integer', 'minimum': 1},
        'player_name': {'type': 'string', 'maxLength': 18},
        'timestamp': {'type': 'string'},
        'data': {
            'type': 'object',
            'properties': {
                'money': {'type': 'integer', 'minimum': 0},
                'weapon': {'type': 'integer', 'minimum': 0, 'maximum': 5},
                'ammo': {'type': 'object'},
                'unlocked_weapons': {'type': 'array', 'items': {'type': 'integer'}},
                'kill_count': {'type': 'integer', 'minimum': 0},
                'cop_kills': {'type': 'integer', 'minimum': 0},
                'cam': {'type': 'array', 'items': {'type': 'number'}},
                'wanted_heat': {'type': 'number', 'minimum': 0},
                'wanted_level': {'type': 'integer', 'minimum': 0, 'maximum': 5},
            }
        }
    },
    'required': ['version', 'player_name', 'timestamp', 'data']
}


def _ensure_save_dir() -> bool:
    """Stellt sicher, dass das Save-Verzeichnis existiert.
    
    Returns:
        True wenn das Verzeichnis existiert oder erstellt werden konnte
    """
    if not os.path.exists(SAVE_DIR):
        try:
            os.makedirs(SAVE_DIR, exist_ok=True)
            return True
        except OSError:
            return False
    return True


def _get_save_path(slot: int) -> str:
    """Gibt den Pfad für einen Spielstand-Slot zurück.
    
    Args:
        slot: Der Slot-Index (1-5)
        
    Returns:
        Der Dateipfad
    """
    return os.path.join(SAVE_DIR, f'slot_{slot}.json')


def _get_save_path_tmp(slot: int) -> str:
    """Gibt den temporären Pfad für atomisches Speichern zurück.
    
    Args:
        slot: Der Slot-Index (1-5)
        
    Returns:
        Der temporäre Dateipfad
    """
    return os.path.join(SAVE_DIR, f'slot_{slot}.json.tmp')


def _serialize_state(state: GameState) -> dict:
    """Serialisiert den relevanten Spielzustand.
    
    Args:
        state: Der GameState
        
    Returns:
        Serialisierbares Dictionary
    """
    # Spieler-Daten
    player_data = {
        'money': state.player.money if state.player else 0,
        'hp': state.player.hp if state.player else 100,
    }
    
    # Waffen & Ausrüstung
    equipment_data = {
        'weapon': state.weapon,
        'ammo': dict(state.ammo),
        'unlocked_weapons': list(state.unlocked_weapons),
    }
    
    # Spielstatistiken
    stats_data = {
        'kill_count': state.kill_count,
        'cop_kills': state.cop_kills,
        'wanted_heat': state.wanted_heat,
        'last_wanted_level': state.last_wanted_level,
    }
    
    # Kamera-Position
    camera_data = {
        'cam': list(state.cam),
    }
    
    return {
        'version': 1,
        'player_name': state.player_name,
        'timestamp': datetime.now().isoformat(),
        'data': {
            **player_data,
            **equipment_data,
            **stats_data,
            **camera_data,
        }
    }


def _deserialize_state(data: dict, state: GameState) -> None:
    """Deserialisiert Daten in einen GameState.
    
    Args:
        data: Die serialisierten Daten
        state: Der Ziel-GameState
    """
    if 'data' not in data:
        return
    
    d = data['data']
    
    # Spieler-Daten
    if state.player:
        state.player.money = d.get('money', 0)
        state.player.hp = d.get('hp', 100)
    
    # Waffen & Ausrüstung
    state.weapon = d.get('weapon', 0)
    if 'ammo' in d:
        state.ammo.update(d['ammo'])
    if 'unlocked_weapons' in d:
        state.unlocked_weapons.update(set(d['unlocked_weapons']))
    
    # Spielstatistiken
    state.kill_count = d.get('kill_count', 0)
    state.cop_kills = d.get('cop_kills', 0)
    state.wanted_heat = d.get('wanted_heat', 0.0)
    state.last_wanted_level = d.get('last_wanted_level', 0)
    
    # Kamera-Position
    if 'cam' in d:
        state.cam = list(d['cam'])


def save_game(state: GameState, slot: int = 1) -> bool:
    """Speichert den aktuellen Spielstand.
    
    Args:
        state: Der aktuelle GameState
        slot: Der Slot-Index (1-5, Default: 1)
        
    Returns:
        True wenn das Speichern erfolgreich war
    """
    if slot < 1 or slot > NUM_SLOTS:
        return False
    
    if not _ensure_save_dir():
        return False
    
    # Serialisiere den State
    save_data = _serialize_state(state)
    
    # Atomisches Schreiben
    tmp_path = _get_save_path_tmp(slot)
    target_path = _get_save_path(slot)
    
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2)
        os.replace(tmp_path, target_path)
        return True
    except OSError:
        return False


def load_game(state: GameState, slot: int = 1) -> bool:
    """Lädt einen gespeicherten Spielstand.
    
    Args:
        state: Der GameState in den geladen werden soll
        slot: Der Slot-Index (1-5, Default: 1)
        
    Returns:
        True wenn das Laden erfolgreich war
    """
    if slot < 1 or slot > NUM_SLOTS:
        return False
    
    save_path = _get_save_path(slot)
    
    if not os.path.exists(save_path):
        return False
    
    try:
        with open(save_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validierung
        validated, errors = validate_and_fix(data, SAVEGAME_SCHEMA)
        if errors:
            # Logge Fehler (optional)
            pass
        
        # Deserialisiere in den State
        _deserialize_state(validated, state)
        return True
    except (OSError, json.JSONDecodeError):
        return False


def has_saved_game(slot: int = 1) -> bool:
    """Prüft ob ein Spielstand in einem Slot existiert.
    
    Args:
        slot: Der Slot-Index (1-5, Default: 1)
        
    Returns:
        True wenn ein Spielstand existiert
    """
    if slot < 1 or slot > NUM_SLOTS:
        return False
    return os.path.exists(_get_save_path(slot))


def delete_save(slot: int = 1) -> bool:
    """Löscht einen gespeicherten Spielstand.
    
    Args:
        slot: Der Slot-Index (1-5, Default: 1)
        
    Returns:
        True wenn das Löschen erfolgreich war
    """
    if slot < 1 or slot > NUM_SLOTS:
        return False
    
    save_path = _get_save_path(slot)
    
    if os.path.exists(save_path):
        try:
            os.remove(save_path)
            return True
        except OSError:
            return False
    return True  # Keine Datei zum Löschen ist auch OK


def get_save_info(slot: int = 1) -> Optional[dict]:
    """Holt Metadaten zu einem Spielstand (ohne Laden).
    
    Args:
        slot: Der Slot-Index (1-5, Default: 1)
        
    Returns:
        Dictionary mit Metadaten (player_name, timestamp) oder None
    """
    if slot < 1 or slot > NUM_SLOTS:
        return None
    
    save_path = _get_save_path(slot)
    
    if not os.path.exists(save_path):
        return None
    
    try:
        with open(save_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return {
            'slot': slot,
            'player_name': data.get('player_name', 'Unbekannt'),
            'timestamp': data.get('timestamp', ''),
            'exists': True
        }
    except (OSError, json.JSONDecodeError):
        return None


def get_all_save_infos() -> list:
    """Holt Metadaten zu allen Spielständen.
    
    Returns:
        Liste von Metadaten-Dictionaries für alle Slots
    """
    infos = []
    for slot in range(1, NUM_SLOTS + 1):
        info = get_save_info(slot)
        if info:
            infos.append(info)
        else:
            infos.append({
                'slot': slot,
                'player_name': 'Leer',
                'timestamp': '',
                'exists': False
            })
    return infos


def auto_save(state: GameState) -> bool:
    """Speichert automatisch in Slot 1 (für Quick-Save).
    
    Args:
        state: Der aktuelle GameState
        
    Returns:
        True wenn das Speichern erfolgreich war
    """
    return save_game(state, slot=1)


def quick_load(state: GameState) -> bool:
    """Lädt automatisch aus Slot 1 (für Quick-Load).
    
    Args:
        state: Der GameState in den geladen werden soll
        
    Returns:
        True wenn das Laden erfolgreich war
    """
    return load_game(state, slot=1)
