# Code Review: `develope` → `main`

**Datum:** 2026-05-14  
**Branch:** develope  
**Commits:** 10 Commits (2b1e511 → d4c37d0)  
**Scope:** +10.020 / -998 Zeilen, 43 Dateien

---

## Übersicht

Der Branch bringt fünf klar trennbare Bereiche:

| Bereich | Dateien | Status |
|---------|---------|--------|
| Neue Gameplay-Features (Katze, Armor, Falloff) | `cat.py`, `main.py`, `car.py`, `config.py` | Gut integriert |
| Refactoring `main.py` | `main.py` | Positiv |
| Neue Infrastruktur-Module | `ecs.py`, `events.py`, `di.py`, `logging.py`, `profiling.py`, `savegame.py`, `pooling.py`, `spatial.py`, `utils.py`, `validation.py` | Teilweise dead code |
| Test-Suite | `tests/` | 194 Tests, alle grün |
| Dokumentation | `AGENTS.md`, `code_review.md`, `TASK_TRACKING.md` | Temporär, nicht nötig |

---

## Kritische Probleme

### 1. `events.py` – fehlender `pygame`-Import (Bug)

```python
# game2d/systems/events.py:98
timestamp: float = field(default_factory=lambda: pygame.time.get_ticks() / 1000.0)
```

`pygame` wird in `events.py` nicht importiert. `Event(...)` zu instanziieren wirft `NameError: name 'pygame' is not defined`. Da `EventBus` nirgendwo im Spielcode importiert wird, schlägt dies derzeit nie fehl – es macht den Code aber unbrauchbar sobald er genutzt wird.

**Fix:** `import pygame` ergänzen, oder `time.monotonic()` verwenden (kein pygame-Dependency).

---

### 2. `SpatialGrid` importiert, aber nie befüllt

```python
# game2d/state.py
entity_grid: Any = field(default_factory=lambda: SpatialGrid(cell_size=150))
```

`entity_grid` wird in keiner anderen Datei außer `state.py` und `systems/profiling.py` (Profiling-Test) referenziert. Die Performance-Verbesserung durch Spatial Partitioning existiert nur auf dem Papier.

**Risiko:** Zirkulärer Import: `state.py` importiert `SpatialGrid` beim Laden – das initialisiert das gesamte `systems/spatial.py`-Modul, ohne dass es jemals genutzt wird.

---

### 3. Object Pooling – `init_pools` / `reset_pools` ohne Effekt

`main.py` ruft `init_pools()` und `reset_pools()` auf. Die Pools in `pooling.py` werden aber nirgendwo für Bullets, Particles oder andere häufig allozierte Objekte verwendet. Die Pools laufen leer, der GC-Gewinn ist null.

---

## Mittlere Probleme

### 4. Dead Infrastructure-Module

Acht neue Module unter `game2d/systems/` werden im Spielcode nicht verwendet:

| Modul | Verwendet von |
|-------|---------------|
| `ecs.py` (438 Zeilen) | nur Tests |
| `events.py` (505 Zeilen) | niemand |
| `di.py` (198 Zeilen) | nur Tests |
| `logging.py` (283 Zeilen) | nur Tests |
| `profiling.py` (724 Zeilen) | nur Tests |
| `savegame.py` (368 Zeilen) | nur Tests |
| `utils.py` (203 Zeilen) | nur Tests |

Das sind ~3.700 Zeilen Code, die das Paket aufblähen ohne Gameplay-Nutzen. Die Module sind gut geschrieben, aber per CLAUDE.md-Grundsatz: *"Don't design for hypothetical future requirements"*.

**Empfehlung:** In einem separaten Branch parken oder entfernen bis tatsächlich benötigt.

---

### 5. `ECSManager._systems` – falsche Typ-Annotation

```python
self._systems: List[Callable[[float], None]] = []
# aber dann:
self._systems.append((priority, system))  # Tuple, kein Callable!
```

`add_system` appended `(priority, system)` statt `system`, `remove_system` und `update` iterieren über Tuples – die Typ-Annotation stimmt nicht und mypy würde dies als Fehler melden.

---

### 6. `pooling.py` – `object.__setattr__` auf Listen

```python
if not hasattr(obj, '_pool_id'):
    object.__setattr__(obj, '_pool_id', None)
object.__setattr__(obj, '_pool_id', obj_id)
```

`_pool_id` auf einer Python-Liste zu setzen funktioniert nicht – Listen haben kein `__dict__`, `object.__setattr__` wirft `AttributeError`. Der Pool ist für generische Objekte designt, schlägt aber bei den tatsächlichen Game-Strukturen (Listen wie `[x, y, vx, vy, ttl]`) fehl.

---

## Kleine Probleme / Verbesserungen

### 7. `_building_collider_cache` – ungenutzte Variablen

```python
# car.py
_building_collider_cache = None
_building_collider_frame = -1
```

`_building_collider_frame` wird nie beschrieben/gelesen – der Cache-Mechanismus ist unvollständig. Entweder implementieren oder entfernen.

---

### 8. Kommentare mit Magic Numbers trotz config.py-Refactor

```python
# main.py:121-123
# Original: 50 Autos, 60 Peds, 38 Amusement-Peds
NUM_START_CARS = 50
NUM_START_PEDS = 40  # Reduziert von 60
```

Kommentare die "Original"-Werte dokumentieren sind Rauschen – die Git-History zeigt die Änderung. Kommentare entfernen.

---

### 9. Logging-Tests: Temp-Dir-Warning

```
WARNING: Konnte Log-Datei /tmp/tmpx_mjzdrr/configured.log nicht öffnen
```

Der Test erstellt ein `tmpdir`, richtet Logger darauf ein, löscht das Verzeichnis dann, aber der Logger schlägt immer noch fehl. Teardown-Reihenfolge im Test prüfen.

---

## Positiv hervorhebenswert

**Armor-System** – vollständig integriert: config, spawning, pickup, damage-absorption, HUD. Sauber durchgezogen.

**Explosions-Falloff** (`car.py`) – `calc_damage(dist, rad)` mit linearem Falloff statt Flat-Damage. Gute Gameplay-Verbesserung.

**Katzen-Entity** (`cat.py`) – eigenständige Pixel-Art-Sprite-Generierung mit 4 Animationsframes, Pathfinding, Audio. Gut gekapseltes Modul.

**`main.py` Refactoring** – `_handle_events`, `_update_*`, `_render_*` Aufteilung macht die 1.400-Zeilen-Datei deutlich besser navigierbar.

**`reset_game()`-Fix** – Loop-Sounds werden jetzt für `_siren_channel`, `_engine_channel` UND `_squeal_channel` gestoppt. Vorher wurden `squeal_channel`-Sounds nach Neustart nie gestoppt.

**194 Tests** – gute Abdeckung der neuen Infrastruktur-Module.

---

## Zusammenfassung

| Kategorie | Bewertung |
|-----------|-----------|
| Gameplay-Features | Gut |
| Code-Qualität | Mittel (dead code) |
| Korrektheit | 1 aktiver Bug (`events.py`), 2 latente Bugs |
| Tests | Gut (194 grün) |
| Architektur-Konformität | Teilweise (neue Module umgehen kein bestehendes System, aber sind ungenutzt) |

**Empfehlung:** Vor dem Merge:
1. `pygame`-Import in `events.py` fixen oder `EventBus` entfernen
2. Dead-Infrastructure-Module (ecs, events, di, logging, profiling, savegame, utils) in eigenen Branch auslagern
3. `entity_grid` aus `state.py` entfernen bis `SpatialGrid` tatsächlich befüllt wird
4. `_building_collider_frame` Cache vervollständigen oder entfernen
