"""Zentraler Spielzustand mit Singleton-Accessor.

`GameState` aggregiert alle bisherigen Modul-Globals. Module wie
`game2d.world.*` greifen via `current()` auf die aktuelle Instanz zu.
`init(state)` wird einmalig aus `game2d.py`/`main.py` aufgerufen.

Listen/Dicts/Sets sind by-reference geteilt — Mutationen sind sowohl
über das alte Global als auch über `state.<feld>` sichtbar. Skalare
müssen explizit über `state.<feld>` reassigned werden.
"""
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class GameState:
    # ── Welt-Geometrie (initialisiert durch world.generation) ───────
    buildings: list = field(default_factory=list)        # [(rect, surface), ...]
    parks:     list = field(default_factory=list)        # [rect, ...]
    park_ponds: list = field(default_factory=list)       # [[(x, y), ...], ...]
    park_trees: list = field(default_factory=list)       # [(x, y, crown, trunk, dark_g, light_g), ...]
    park_ducks: list = field(default_factory=list)       # [(kind, family, follow_slot, x, y, rx, ry, speed, phase), ...]
    amusement_parks: list = field(default_factory=list)  # [rect, ...]
    amusement_stands: list = field(default_factory=list) # [(x, y, kind), ...]
    pedestrian_nodes: list = field(default_factory=list) # [(x, y), ...]
    pedestrian_edges: dict = field(default_factory=dict) # {node_idx: [neighbor_idx, ...]}
    pedestrian_park_nodes: set = field(default_factory=set)
    amusement_park_nodes: set = field(default_factory=set)
    central_bank_rect: Any = None
    roads_h:   list = field(default_factory=list)        # horizontale Straßen-y
    roads_v:   list = field(default_factory=list)        # vertikale Straßen-x
    AI_OBSTACLES: list = field(default_factory=list)     # Häuser + Wasser
    WATER_RECTS:  list = field(default_factory=list)

    # ── Entities ────────────────────────────────────────────────────
    cars: list = field(default_factory=list)
    peds: list = field(default_factory=list)
    cops: list = field(default_factory=list)
    player: Any = None
    in_car: Any = None
    intersection_claims: dict = field(default_factory=dict)

    # ── Waffen & Spieler-State ──────────────────────────────────────
    weapon: int = 0
    ammo: dict = field(default_factory=lambda: {1: 80, 2: 0, 3: 0, 4: 0, 5: 0})
    unlocked_weapons: set = field(default_factory=lambda: {0, 1})
    fire_cd: float = 0.0
    cop_spawn: float = 0.0
    wanted_heat: float = 0.0
    last_wanted_level: int = 0

    # ── Pickups ─────────────────────────────────────────────────────
    pickups: list = field(default_factory=list)          # [[x, y, kind, respawn_cd], ...]

    # ── Partikel & Effekte ──────────────────────────────────────────
    bullets:         list = field(default_factory=list)
    rockets:         list = field(default_factory=list)
    blood_splats:    list = field(default_factory=list)
    blood_particles: list = field(default_factory=list)
    smoke_particles: list = field(default_factory=list)
    fire_particles:  list = field(default_factory=list)
    explosions:      list = field(default_factory=list)
    lightsaber_swings: list = field(default_factory=list)
    wrecks:          list = field(default_factory=list)
    corpses:         list = field(default_factory=list)

    # Service locations and police extras.
    garages: list = field(default_factory=list)          # [(x, y), ...]
    shops:   list = field(default_factory=list)          # [(x, y), ...]
    barbers: list = field(default_factory=list)          # [(x, y), ...]
    roadblocks: list = field(default_factory=list)       # [Roadblock, ...]
    roadblock_wanted_level: int = 0
    roadblocks_cleared_on_drop: bool = False

    # ── Loop / Frame ────────────────────────────────────────────────
    cam: list = field(default_factory=lambda: [0, 0])
    traffic_time: float = 0.0
    duck_easter_timer: float = 0.0
    duck_easter_done: bool = False
    duck_easter_duck: Any = None                         # [x, y, target_x, target_y, ttl]
    duck_easter_last_pos: Any = None
    running: bool = True
    paused: bool = False
    message: str = ""
    message_timer: float = 0.0
    game_over: bool = False
    score_saved: bool = False
    final_scores: list = field(default_factory=list)

    # ── Player-Identität ────────────────────────────────────────────
    player_name: str = "Spieler"

    # ── Menü / Settings ─────────────────────────────────────────────
    menu: Optional[str] = None                           # None | 'pause' | 'options'
    settings: dict = field(default_factory=dict)
    barber_step: str = "style"


# ── Singleton-Accessor ──────────────────────────────────────────────
_singleton: Optional[GameState] = None


def init(state: GameState) -> None:
    """Globalen Zugriff auf den GameState setzen."""
    global _singleton
    _singleton = state


def current() -> GameState:
    """Aktuelle GameState-Instanz; muss zuvor mit init() gesetzt sein."""
    if _singleton is None:
        raise RuntimeError("GameState wurde noch nicht via state.init() initialisiert")
    return _singleton
