# Performance Optimizations

## Problem
`update_logic` und `_update_entities_and_physics` zeigen ~40ms im Profiler, besonders bei hoher Entity-Dichte. Performance skaliert schlecht mit Entity-Anzahl.

## Ergebnisse

### Aktueller Status
- **Vor Optimierungen**: ~40ms für `update_logic` / `_update_entities_and_physics`
- **Nach Option A (Update-Bereich begrenzen)**: **~6ms** (-85%)
- **Ziel erreicht**: Performance ist jetzt akzeptabel

---

## Optionen

### A. Update-Bereich begrenzen
- **Status**: DONE
- **Beschreibung**: Nur Entities im Viewport (+ dynamischer Puffer) voll updaten. Cars/Peds/Cats außerhalb: Vereinfachte Bewegung + Building-Kollision. Cops immer voll updaten.
- **Vorteil**: Skaliert linear mit sichtbaren Entities
- **Dateien**: `game2d/main.py`
- **Konstante**: `UPDATE_RANGE_BUFFER = max(300, W//4)` (dynamisch)
- **Funktion**: `_is_in_update_range()`, `_background_move_entity()`

### B. Update-Frequenz stufen
- **Status**: SKIPPED
- **Begründung**: Option A mit Background-Simulation ausreichend

### C. AI-Kosten reduzieren
- **Status**: DONE (teilweise)
- **Beschreibung**: `ai_update()` für ferne Cars durch `_background_move_entity()` ersetzt. Amusement-Peds nutzen vereinfachte Pfadprüfung (`allow_park=True`).
- **Vorteil**: Reduziert AI-Kosten für Hintergrund-Entities
- **Dateien**: `game2d/main.py`, `game2d/entities/ped.py`

### D. Grid-Updates optimieren
- **Status**: NOT STARTED
- **Beschreibung**: `update_entity_position()` nur bei tatsächlicher Positionsänderung aufrufen. Batch-Updates für Spatial Grid.
- **Vorteil**: Weniger Grid-Operationen

### E. Animate-Optimierung
- **Status**: NOT STARTED
- **Beschreibung**: Frame-Wechsel nur bei Bewegung > Schwelle. Sprite-Cache voll nutzen.
- **Vorteil**: Weniger Rect-Berechnungen & Sprite-Rotationen

---

## Implementierte Optimierungen

### Spatial Grid für Collision Detection
- **Status**: DONE
- **Änderungen**:
  - Bullet-Collision nutzt `query_entities_radius()` statt manuelle Iteration
  - Rocket-Collision nutzt `query_entities_radius()` und `query_buildings_radius()`
  - Building-Collision für Rockets optimiert
- **Dateien**: `game2d/main.py`

### Rect-Caching
- **Status**: DONE
- **Änderungen**:
  - `Ped.rect()` mit Caching
  - `Cat.rect()` mit Caching
- **Dateien**: `game2d/entities/ped.py`, `game2d/entities/cat.py`

### Hintergrund-Simulation (World Alive)
- **Status**: DONE
- **Beschreibung**: Entities außerhalb des Viewports bewegen sich weiter mit einfacher Physik + Building-Kollision, ohne teure AI. Cops immer voll geupdated.
- **Aufteilung**:
  - **Nah (0-UPDATE_RANGE_BUFFER)**: Volles Update (AI + Animation + Entity-Entity-Kollision)
  - **Fern (UPDATE_RANGE_BUFFER+)**: Vereinfachte Bewegung mit Building-Kollision + Straßenbeschränkung
- **Straßenbeschränkung für Cars**: Prüft `rect_on_road()` und lenkt mit `lane_center_for_car()` zur Straßenmitte zurück
- **Dateien**: `game2d/main.py`
- **Funktionen**: `_background_move_entity()`, `_is_in_update_range()`
- **Konstanten**: `UPDATE_RANGE_BUFFER = max(300, W//4)` (dynamisch)
- **Importiert**: `rect_on_road`, `lane_center_for_car` aus `game2d.world.geometry`

### Park Spatial Grid für Pedestrian-Kollision
- **Status**: DONE
- **Beschreibung**: Park-Rects (parks + amusement_parks) in Spatial Grid für O(1) Kollisionsprüfungen. Ersetzt manuelle Iteration über alle Parks.
- **Vorteil**: Deutlich schnellere Pfadprüfung für Peds, besonders im Vergnügungspark
- **Dateien**: `game2d/systems/spatial.py`, `game2d/world/geometry.py`, `game2d/main.py`
- **Funktionen**: `query_parks_radius()`, `init_and_populate_park_grid()`, `reset_park_grid()`
- **Geändert**: `_ped_point_clear()`, `_ped_segment_clear()`, `pedestrian_step_clear()`

### Amusement-Peds vereinfachte Pfadprüfung
- **Status**: DONE
- **Beschreibung**: Peds im Vergnügungspark (`is_amusement=True`) nutzen immer `allow_park=True`, was nur `point_on_amusement_path()` prüft (mit Spatial Grid) statt alle Park-Rects.
- **Vorteil**: Schnellere Pfadfindung für 20 Amusement-Peds
- **Dateien**: `game2d/main.py`, `game2d/entities/ped.py`
- **Funktionen**: `try_follow_route()`
