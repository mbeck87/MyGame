"""Dependency Injection für State Management.

Bietet eine Infrastruktur für:
- State-Mocking für Tests
- Context-basierten State-Zugriff
- Einfache Factory für Test-States

Usage:
    # Normaler Spielbetrieb
    from game2d.state import GameState, init as state_init
    from game2d.systems.di import StateProvider
    
    state = GameState()
    state_init(state)
    
    # Für Tests mit Mock-State
    from game2d.systems.di import create_test_state, with_state
    
    test_state = create_test_state()
    with with_state(test_state):
        # code that uses current() will use test_state
        pass
"""
from contextlib import contextmanager
from typing import Generator, Optional, Any, List

from game2d.state import GameState, init as state_init, _singleton


# Stack für verschachtelte State-Contexts
_state_stack: List[Optional[GameState]] = []


class StateProvider:
    """Bereitsteller für GameState-Instanzen.
    
    Ermöglicht das Erstellen, Zurücksetzen und Mocken von States.
    """
    
    def __init__(self):
        self._original: Optional[GameState] = None
    
    def create(self, **kwargs: Any) -> GameState:
        """Erstellt eine neue GameState-Instanz.
        
        Args:
            **kwargs: Optionale Überschreibungen für Default-Werte
            
        Returns:
            Neue GameState-Instanz
        """
        state = GameState(**kwargs)
        return state
    
    def create_test_state(
        self,
        player_name: str = "TestPlayer",
        world_size: tuple[int, int] = (6000, 6000),
        with_player: bool = True
    ) -> GameState:
        """Erstellt einen Test-State mit minimaler Konfiguration.
        
        Args:
            player_name: Name des Test-Spielers
            world_size: Größe der Spielwelt
            with_player: Ob ein Player-Ped erstellt werden soll
            
        Returns:
            Konfigurierte GameState-Instanz für Tests
        """
        state = self.create(player_name=player_name)
        # Grundlegende Welt-Konfiguration
        state.roads_h = []
        state.roads_v = []
        state.cam = [0, 0]
        state.running = True
        state.paused = False
        state.game_over = False
        
        return state
    
    def install(self, state: GameState) -> None:
        """Installiert einen State als Singleton.
        
        Args:
            state: Die zu installierende GameState-Instanz
        """
        state_init(state)
        self._original = state


# Globale Instanz
provider = StateProvider()


def create_test_state(
    player_name: str = "TestPlayer",
    world_size: tuple[int, int] = (6000, 6000),
    with_player: bool = True
) -> GameState:
    """Convenience-Funktion: Erstellt einen Test-State.
    
    Args:
        player_name: Name des Test-Spielers
        world_size: Größe der Spielwelt
        with_player: Ob ein Player-Ped erstellt werden soll
        
    Returns:
        Konfigurierte GameState-Instanz für Tests
    """
    return provider.create_test_state(player_name, world_size, with_player)


@contextmanager
def with_state(state: GameState) -> Generator[GameState, None, None]:
    """Context-Manager für temporären State-Zugriff.
    
    Innerhalb des Contexts verwendet `current()` den angegebenen State.
    Danach wird der ursprüngliche State wiederhergestellt.
    
    Args:
        state: Der temporäre State
        
    Yields:
        Der temporäre State
        
    Usage:
        test_state = create_test_state()
        with with_state(test_state):
            # current() returns test_state here
            pass
        # current() returns original state again
    """
    # Speichere den aktuellen State BEVOR wir ihn ändern
    import game2d.state as state_module
    original = state_module._singleton
    _state_stack.append(original)
    
    try:
        state_init(state)
        yield state
    finally:
        # Stelle den ursprünglichen State wieder her
        if _state_stack:
            original = _state_stack.pop()
            if original is not None:
                state_module._singleton = original
            else:
                state_module._singleton = None


@contextmanager
def with_test_state(
    player_name: str = "TestPlayer",
    world_size: tuple[int, int] = (6000, 6000)
) -> Generator[GameState, None, None]:
    """Context-Manager für einen temporären Test-State.
    
    Erstellt automatisch einen Test-State und stellt ihn wieder her.
    
    Args:
        player_name: Name des Test-Spielers
        world_size: Größe der Spielwelt
        
    Yields:
        Der Test-State
        
    Usage:
        with with_test_state() as state:
            # current() returns a test state here
            pass
    """
    test_state = create_test_state(player_name, world_size)
    with with_state(test_state):
        yield test_state


class MockPlayer:
    """Mock-Player für Tests."""
    
    def __init__(
        self,
        x: float = 0.0,
        y: float = 0.0,
        hp: int = 100,
        money: int = 0,
        wanted: int = 0
    ):
        self.x = x
        self.y = y
        self.hp = hp
        self.money = money
        self.wanted = wanted
        self.angle = 0.0
        self.aim_angle = 0.0
        self.state = 'idle'
        self.in_car = None
        self.is_cop = False
