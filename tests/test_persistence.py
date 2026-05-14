"""Tests für das Persistenz-Modul."""
import unittest
import os
import tempfile
import shutil
import json

from game2d.persistence import (
    validate_name,
    sanitize_name,
    MAX_NAME_LENGTH,
    MIN_NAME_LENGTH,
)


class TestNameValidation(unittest.TestCase):
    """Testet die Namensvalidierung."""

    def test_valid_name_simple(self):
        """Testet einfache gültige Namen."""
        self.assertTrue(validate_name("Player"))
        self.assertTrue(validate_name("Player1"))
        self.assertTrue(validate_name("Player-Name"))
        self.assertTrue(validate_name("Player_Name"))
        self.assertTrue(validate_name("Player Name"))

    def test_valid_name_with_spaces(self):
        """Testet Namen mit Leerzeichen."""
        self.assertTrue(validate_name("John Doe"))
        self.assertTrue(validate_name("  John  "))  # Whitespace wird getrimmt

    def test_invalid_name_too_short(self):
        """Testet zu kurze Namen."""
        self.assertFalse(validate_name(""))
        self.assertFalse(validate_name(" "))
        self.assertFalse(validate_name("  "))

    def test_invalid_name_too_long(self):
        """Testet zu lange Namen."""
        self.assertFalse(validate_name("A" * (MAX_NAME_LENGTH + 1)))

    def test_invalid_name_special_chars(self):
        """Testet Namen mit unerlaubten Sonderzeichen."""
        self.assertFalse(validate_name("Player@"))
        self.assertFalse(validate_name("Player#"))
        self.assertFalse(validate_name("Player$"))
        self.assertFalse(validate_name("Player%"))

    def test_invalid_name_path_traversal(self):
        """Testet Namen mit Path-Traversal-Versuch."""
        self.assertFalse(validate_name("../Player"))
        self.assertFalse(validate_name("Player/../"))
        self.assertFalse(validate_name("Player\\..\\"))

    def test_invalid_name_not_string(self):
        """Testet Nicht-String-Werte."""
        self.assertFalse(validate_name(None))
        self.assertFalse(validate_name(123))
        self.assertFalse(validate_name([]))
        self.assertFalse(validate_name({}))


class TestNameSanitization(unittest.TestCase):
    """Testet die Namensbereinigung."""

    def test_sanitize_valid_name(self):
        """Testet dass gültige Namen unverändert bleiben."""
        self.assertEqual(sanitize_name("Player"), "Player")
        self.assertEqual(sanitize_name("Player1"), "Player1")
        self.assertEqual(sanitize_name("Player-Name"), "Player-Name")

    def test_sanitize_removes_special_chars(self):
        """Testet dass Sonderzeichen entfernt werden."""
        self.assertEqual(sanitize_name("Player@Name"), "PlayerName")
        self.assertEqual(sanitize_name("Player#1"), "Player1")
        self.assertEqual(sanitize_name("Player$Test"), "PlayerTest")

    def test_sanitize_path_traversal(self):
        """Testet dass Path-Traversal-Zeichen entfernt werden."""
        self.assertEqual(sanitize_name("../Player"), "Player")
        self.assertEqual(sanitize_name("Player/../Name"), "PlayerName")
        self.assertEqual(sanitize_name("Player\\Test"), "PlayerTest")

    def test_sanitize_trims_whitespace(self):
        """Testet dass Whitespace getrimmt wird."""
        self.assertEqual(sanitize_name("  Player  "), "Player")
        self.assertEqual(sanitize_name("\tPlayer\n"), "Player")

    def test_sanitize_truncates_long_names(self):
        """Testet dass lange Namen gekürzt werden."""
        long_name = "A" * 100
        result = sanitize_name(long_name)
        self.assertEqual(len(result), MAX_NAME_LENGTH)

    def test_sanitize_empty_name(self):
        """Testet dass leere Namen zu 'Spieler' werden."""
        self.assertEqual(sanitize_name(""), "Spieler")
        self.assertEqual(sanitize_name("   "), "Spieler")

    def test_sanitize_non_string(self):
        """Testet dass Nicht-String-Werte zu 'Spieler' werden."""
        self.assertEqual(sanitize_name(None), "Spieler")
        self.assertEqual(sanitize_name(123), "Spieler")

    def test_sanitize_only_special_chars(self):
        """Testet dass nur Sonderzeichen zu 'Spieler' werden."""
        self.assertEqual(sanitize_name("@@@"), "Spieler")
        self.assertEqual(sanitize_name("/\\:*?<>|"), "Spieler")


class TestPersistenceIntegration(unittest.TestCase):
    """Integrationstests für das Persistenz-Modul."""

    def setUp(self):
        """Erstellt ein temporäres Verzeichnis für Testdateien."""
        self.test_dir = tempfile.mkdtemp()
        self.original_scores_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath("game2d/persistence.py"))),
            "scores.json"
        )
        # Temporär die SCORES_FILE Path ändern
        # Da persistence.py eine globale Konstante hat, mocken wir sie
        import game2d.persistence as persistence_module
        self.original_file = persistence_module.SCORES_FILE
        persistence_module.SCORES_FILE = os.path.join(self.test_dir, "scores.json")

    def tearDown(self):
        """Bereinigt temporäre Dateien."""
        import game2d.persistence as persistence_module
        persistence_module.SCORES_FILE = self.original_file
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_save_and_load_score(self):
        """Testet das Speichern und Laden von Scores."""
        import game2d.persistence as persistence_module
        
        # Score speichern
        scores = persistence_module.save_score("TestPlayer", 1000)
        self.assertEqual(len(scores), 1)
        self.assertEqual(scores[0]["name"], "TestPlayer")
        self.assertEqual(scores[0]["money"], 1000)
        
        # Scores laden
        loaded_scores = persistence_module.load_scores()
        self.assertEqual(len(loaded_scores), 1)
        self.assertEqual(loaded_scores[0]["name"], "TestPlayer")

    def test_save_and_load_last_name(self):
        """Testet das Speichern und Laden des letzten Namens."""
        import game2d.persistence as persistence_module
        
        persistence_module.save_last_name("TestPlayer")
        last_name = persistence_module.load_last_name()
        self.assertEqual(last_name, "TestPlayer")

    def test_score_ordering(self):
        """Testet dass Scores nach Geld absteigend sortiert werden."""
        import game2d.persistence as persistence_module
        
        persistence_module.save_score("Player1", 100)
        persistence_module.save_score("Player2", 500)
        persistence_module.save_score("Player3", 1000)
        
        scores = persistence_module.load_scores()
        self.assertEqual(scores[0]["money"], 1000)
        self.assertEqual(scores[1]["money"], 500)
        self.assertEqual(scores[2]["money"], 100)

    def test_max_scores_limit(self):
        """Testet dass nur die Top 20 Scores gespeichert werden."""
        import game2d.persistence as persistence_module
        
        # 25 Scores speichern
        for i in range(25):
            persistence_module.save_score(f"Player{i}", i * 100)
        
        scores = persistence_module.load_scores()
        self.assertLessEqual(len(scores), 20)


if __name__ == '__main__':
    unittest.main()
