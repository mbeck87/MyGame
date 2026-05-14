"""Tests für das Spielstand-Speichern und Laden."""
import unittest
import os
import shutil
import tempfile
import json

from game2d.state import GameState
from game2d.systems.savegame import (
    save_game,
    load_game,
    has_saved_game,
    delete_save,
    get_save_info,
    get_all_save_infos,
    auto_save,
    quick_load,
    _serialize_state,
    _deserialize_state,
    _ensure_save_dir,
    _get_save_path,
    SAVE_DIR,
    NUM_SLOTS,
)


class TestSaveGameUtilities(unittest.TestCase):
    """Testet Utility-Funktionen."""

    def test_ensure_save_dir(self):
        """Testet das Erstellen des Save-Verzeichnisses."""
        # Speichere den aktuellen SAVE_DIR
        original_dir = SAVE_DIR
        
        # Verwende ein temporäres Verzeichnis für den Test
        import game2d.systems.savegame as savegame_module
        test_dir = tempfile.mkdtemp()
        savegame_module.SAVE_DIR = test_dir
        
        try:
            result = _ensure_save_dir()
            self.assertTrue(result)
            self.assertTrue(os.path.exists(test_dir))
        finally:
            savegame_module.SAVE_DIR = original_dir
            shutil.rmtree(test_dir, ignore_errors=True)

    def test_get_save_path(self):
        """Testet den Pfad-Generator."""
        import game2d.systems.savegame as savegame_module
        original_dir = savegame_module.SAVE_DIR
        test_dir = tempfile.mkdtemp()
        savegame_module.SAVE_DIR = test_dir
        
        try:
            for slot in range(1, NUM_SLOTS + 1):
                path = _get_save_path(slot)
                self.assertEqual(path, os.path.join(test_dir, f'slot_{slot}.json'))
        finally:
            savegame_module.SAVE_DIR = original_dir
            shutil.rmtree(test_dir, ignore_errors=True)


class TestSerialization(unittest.TestCase):
    """Testet die Serialisierung und Deserialisierung."""

    def test_serialize_state(self):
        """Testet die Serialisierung des States."""
        state = GameState(player_name="TestPlayer")
        state.weapon = 2
        state.ammo = {1: 50, 2: 30}
        state.unlocked_weapons = {0, 1, 2}
        state.kill_count = 10
        state.cop_kills = 5
        state.wanted_heat = 25.0
        state.cam = [100, 200]
        
        data = _serialize_state(state)
        
        self.assertEqual(data['version'], 1)
        self.assertEqual(data['player_name'], "TestPlayer")
        self.assertIn('timestamp', data)
        self.assertIn('data', data)
        self.assertEqual(data['data']['weapon'], 2)
        self.assertEqual(data['data']['kill_count'], 10)

    def test_deserialize_state(self):
        """Testet die Deserialisierung in einen State."""
        state = GameState(player_name="Original")
        
        data = {
            'version': 1,
            'player_name': 'TestPlayer',
            'timestamp': '2024-01-01T00:00:00',
            'data': {
                'money': 1000,
                'hp': 75,
                'weapon': 3,
                'ammo': {1: 20, 2: 40},
                'unlocked_weapons': [0, 1, 2, 3],
                'kill_count': 15,
                'cop_kills': 8,
                'wanted_heat': 30.0,
                'wanted_level': 2,
                'cam': [150, 250]
            }
        }
        
        _deserialize_state(data, state)
        
        self.assertEqual(state.weapon, 3)
        self.assertEqual(state.kill_count, 15)
        self.assertEqual(state.cop_kills, 8)


class TestSaveLoadFunctions(unittest.TestCase):
    """Testet die Save/Load-Funktionen."""

    def setUp(self):
        """Erstellt ein temporäres Save-Verzeichnis."""
        import game2d.systems.savegame as savegame_module
        self.original_dir = savegame_module.SAVE_DIR
        self.test_dir = tempfile.mkdtemp()
        savegame_module.SAVE_DIR = self.test_dir

    def tearDown(self):
        """Bereinigt das temporäre Verzeichnis."""
        import game2d.systems.savegame as savegame_module
        savegame_module.SAVE_DIR = self.original_dir
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_save_game(self):
        """Testet das Speichern eines Spielstands."""
        state = GameState(player_name="SaveTest")
        state.weapon = 2
        
        result = save_game(state, slot=1)
        self.assertTrue(result)
        
        # Prüfe ob die Datei existiert
        save_path = os.path.join(self.test_dir, 'slot_1.json')
        self.assertTrue(os.path.exists(save_path))

    def test_save_game_invalid_slot(self):
        """Testet das Speichern mit ungültigem Slot."""
        state = GameState()
        
        result = save_game(state, slot=0)
        self.assertFalse(result)
        
        result = save_game(state, slot=10)
        self.assertFalse(result)

    def test_load_game(self):
        """Testet das Laden eines Spielstands."""
        # Erst speichern
        state = GameState(player_name="LoadTest")
        state.weapon = 3
        state.kill_count = 20
        save_game(state, slot=2)
        
        # Dann laden in einen neuen State
        new_state = GameState(player_name="New")
        result = load_game(new_state, slot=2)
        self.assertTrue(result)
        
        self.assertEqual(new_state.weapon, 3)
        self.assertEqual(new_state.kill_count, 20)

    def test_load_game_nonexistent(self):
        """Testet das Laden eines nicht existierenden Spielstands."""
        state = GameState()
        result = load_game(state, slot=3)
        self.assertFalse(result)

    def test_has_saved_game(self):
        """Testet das Prüfen auf existierende Spielstände."""
        # Kein Spielstand
        self.assertFalse(has_saved_game(slot=1))
        
        # Speichern
        state = GameState()
        save_game(state, slot=1)
        
        # Prüfen
        self.assertTrue(has_saved_game(slot=1))
        self.assertFalse(has_saved_game(slot=2))

    def test_delete_save(self):
        """Testet das Löschen eines Spielstands."""
        state = GameState()
        save_game(state, slot=1)
        
        self.assertTrue(has_saved_game(slot=1))
        
        result = delete_save(slot=1)
        self.assertTrue(result)
        
        self.assertFalse(has_saved_game(slot=1))

    def test_delete_save_nonexistent(self):
        """Testet das Löschen eines nicht existierenden Spielstands."""
        result = delete_save(slot=1)
        self.assertTrue(result)  # Keine Datei zum Löschen ist OK

    def test_get_save_info(self):
        """Testet das Holen von Metadaten."""
        state = GameState(player_name="InfoTest")
        save_game(state, slot=1)
        
        info = get_save_info(slot=1)
        self.assertIsNotNone(info)
        self.assertEqual(info['slot'], 1)
        self.assertEqual(info['player_name'], "InfoTest")
        self.assertIn('timestamp', info)
        self.assertTrue(info['exists'])

    def test_get_save_info_nonexistent(self):
        """Testet das Holen von Metadaten für nicht existierenden Spielstand."""
        info = get_save_info(slot=1)
        self.assertIsNone(info)

    def test_get_all_save_infos(self):
        """Testet das Holen aller Spielstand-Infos."""
        # Speichere einige Spielstände
        for i in range(1, 4):
            state = GameState(player_name=f"Player{i}")
            save_game(state, slot=i)
        
        infos = get_all_save_infos()
        self.assertEqual(len(infos), NUM_SLOTS)
        
        for i, info in enumerate(infos, 1):
            self.assertEqual(info['slot'], i)
            if i <= 3:
                self.assertTrue(info['exists'])
                self.assertEqual(info['player_name'], f"Player{i}")
            else:
                self.assertFalse(info['exists'])

    def test_auto_save_and_quick_load(self):
        """Testet Auto-Save und Quick-Load."""
        state = GameState(player_name="AutoSaveTest")
        state.money = 5000
        
        result = auto_save(state)
        self.assertTrue(result)
        
        new_state = GameState()
        result = quick_load(new_state)
        self.assertTrue(result)
        
        # Der Geldwert sollte geladen worden sein
        # (wenn state.player existiert)


if __name__ == '__main__':
    unittest.main()
