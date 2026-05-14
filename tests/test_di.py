"""Tests für das Dependency Injection Modul."""
import unittest

from game2d.state import GameState, init as state_init, current
from game2d.systems.di import (
    StateProvider,
    create_test_state,
    with_state,
    with_test_state,
    MockPlayer,
    provider,
)


class TestStateProvider(unittest.TestCase):
    """Testet den StateProvider."""

    def setUp(self):
        """Setzt einen Test-State für jeden Test."""
        self.test_state = GameState()
        state_init(self.test_state)

    def test_create(self):
        """Testet das Erstellen eines States."""
        state = provider.create()
        self.assertIsInstance(state, GameState)

    def test_create_with_kwargs(self):
        """Testet das Erstellen eines States mit kwargs."""
        state = provider.create(player_name="Test")
        self.assertEqual(state.player_name, "Test")

    def test_create_test_state(self):
        """Testet das Erstellen eines Test-States."""
        state = provider.create_test_state()
        self.assertIsInstance(state, GameState)
        self.assertEqual(state.player_name, "TestPlayer")
        self.assertEqual(state.roads_h, [])
        self.assertEqual(state.roads_v, [])
        self.assertFalse(state.paused)
        self.assertFalse(state.game_over)

    def test_create_test_state_custom_params(self):
        """Testet das Erstellen eines Test-States mit benutzerdefinierten Parametern."""
        state = provider.create_test_state(
            player_name="Custom",
            world_size=(1000, 1000)
        )
        self.assertEqual(state.player_name, "Custom")


class TestWithStateContext(unittest.TestCase):
    """Testet den with_state Context-Manager."""

    def setUp(self):
        """Setzt einen Test-State für jeden Test."""
        self.test_state = GameState()
        state_init(self.test_state)

    def test_with_state(self):
        """Testet den with_state Context-Manager."""
        original = current()
        test_state = GameState(player_name="ContextTest")
        
        with with_state(test_state):
            # Innerhalb des Contexts sollte current() den Test-State zurückgeben
            self.assertIs(current(), test_state)
            self.assertEqual(current().player_name, "ContextTest")
        
        # Danach sollte der ursprüngliche State wiederhergestellt sein
        self.assertIs(current(), original)

    def test_with_test_state(self):
        """Testet den with_test_state Context-Manager."""
        original = current()
        
        with with_test_state(player_name="AutoTest") as state:
            self.assertIsInstance(state, GameState)
            self.assertEqual(current().player_name, "AutoTest")
        
        # Danach sollte der ursprüngliche State wiederhergestellt sein
        self.assertIs(current(), original)

    def test_nested_contexts(self):
        """Testet verschachtelte Contexts."""
        original = current()
        outer_state = GameState(player_name="Outer")
        inner_state = GameState(player_name="Inner")
        
        with with_state(outer_state):
            self.assertEqual(current().player_name, "Outer")
            
            with with_state(inner_state):
                self.assertEqual(current().player_name, "Inner")
            
            # Nach dem inneren Context sollte der äußere wiederhergestellt sein
            self.assertEqual(current().player_name, "Outer")
        
        # Danach sollte der ursprüngliche State wiederhergestellt sein
        self.assertIs(current(), original)


class TestMockPlayer(unittest.TestCase):
    """Testet den MockPlayer."""

    def test_mock_player_defaults(self):
        """Testet die Default-Werte des MockPlayer."""
        player = MockPlayer()
        self.assertEqual(player.x, 0.0)
        self.assertEqual(player.y, 0.0)
        self.assertEqual(player.hp, 100)
        self.assertEqual(player.money, 0)
        self.assertEqual(player.wanted, 0)
        self.assertEqual(player.angle, 0.0)
        self.assertEqual(player.aim_angle, 0.0)
        self.assertEqual(player.state, 'idle')

    def test_mock_player_custom(self):
        """Testet den MockPlayer mit benutzerdefinierten Werten."""
        player = MockPlayer(x=100.0, y=200.0, hp=50, money=1000, wanted=3)
        self.assertEqual(player.x, 100.0)
        self.assertEqual(player.y, 200.0)
        self.assertEqual(player.hp, 50)
        self.assertEqual(player.money, 1000)
        self.assertEqual(player.wanted, 3)


class TestCreateTestStateFunction(unittest.TestCase):
    """Testet die Convenience-Funktion create_test_state."""

    def test_create_test_state_function(self):
        """Testet die create_test_state Funktion."""
        state = create_test_state()
        self.assertIsInstance(state, GameState)
        self.assertEqual(state.player_name, "TestPlayer")

    def test_create_test_state_with_params(self):
        """Testet create_test_state mit Parametern."""
        state = create_test_state(player_name="FunctionTest")
        self.assertEqual(state.player_name, "FunctionTest")


if __name__ == '__main__':
    unittest.main()
