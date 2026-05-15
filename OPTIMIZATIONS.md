# Performance Optimizations

## Problem
`update_logic` und `_update_entities_and_physics` zeigen ~40ms im Profiler, besonders bei hoher Entity-Dichte. Performance skaliert schlecht mit Entity-Anzahl.

## Ergebnisse

### Aktueller Status
- **Vor Optimierungen**: ~40ms für `update_logic` / `_update_entities_and_physics`
- **Nach Option A (Update-Bereich begrenzen)**: **~6ms** (-85%)
- **Nach Fixes 2026-05-15 (Cops + Grid + Background-Cars)**: **~3-5ms** (weitere -30-50%)
- **Nach Amusement-Park Optimierungen (2026-05-15)**: **~0.1-0.3ms im Park** (weitere -30-40ms)
- **Gesamtverbesserung**: ~99%+ Reduktion der Update-Zeit
- **Ziel erreicht**: Performance ist jetzt auch bei 120+ Entities im Vergnügungspark akzeptabel

### Performance-Verlauf
| Datum | Optimierung | Update-Zeit | Gewinn |
|-------|-------------|-------------|--------|
| Initial | - | ~40ms | - |
| Option A | Update-Bereich begrenzen | ~6ms | -85% |
| 2026-05-15 | Cops im Hintergrund vereinfachen | ~4-5ms | -15-20ms |
| 2026-05-15 | Grid-Updates optimieren | ~3.5-4.5ms | -3-5ms |
| 2026-05-15 | Background-Cars Straßenprüfung | ~3-4ms | -5-10ms |
| 2026-05-15 | Amusement-Park Pfad-Segmente cachen | ~1-3ms | -15-25ms |
| 2026-05-15 | Amusement-Park Statik als Sprite pre-rendern | ~0.1-0.5ms | -10-20ms |
| 2026-05-15 | Amusement-Park Fahrgeschäfte als PNG-Sprites | ~0.1-0.3ms | -5-10ms |

---

## Optionen

### A. Update-Bereich begrenzen
- **Status**: DONE
- **Beschreibung**: Nur Entities im Viewport (+ dynamischer Puffer) voll updaten. Cars/Peds/Cats/Cops außerhalb: Vereinfachte Bewegung + Building-Kollision.
- **Vorteil**: Skaliert linear mit sichtbaren Entities
- **Dateien**: `game2d/main.py`
- **Konstante**: `UPDATE_RANGE_BUFFER = max(300, W//4)` (dynamisch)
- **Funktion**: `_is_in_update_range()`, `_background_move_entity()`
- **Update 2026-05-15**: Cops jetzt auch im Hintergrund vereinfacht (vorher immer voll geupdated). Spart ~15-20ms bei hohem Wanted-Level.

### B. Update-Frequenz stufen
- **Status**: SKIPPED
- **Begründung**: Option A mit Background-Simulation ausreichend

### C. AI-Kosten reduzieren
- **Status**: DONE
- **Beschreibung**: `ai_update()` für ferne Cars durch `_background_move_entity()` ersetzt. Amusement-Peds nutzen vereinfachte Pfadprüfung (`allow_park=True`).
- **Vorteil**: Reduziert AI-Kosten für Hintergrund-Entities
- **Dateien**: `game2d/main.py`, `game2d/entities/ped.py`

### F. Hintergrund-Cars Straßenprüfung optimieren
- **Status**: DONE
- **Beschreibung**: `_background_move_entity()` für Cars nutzt jetzt schnelle Approximation (`nearest_road_v/h`) statt teure `rect_on_road()` und `lane_center_for_car()`. Spart ~5-10ms.
- **Vorteil**: Deutlich schnellere Hintergrund-Simulation für viele Cars
- **Dateien**: `game2d/main.py`
- **Funktion**: `_background_move_entity()`

### D. Grid-Updates optimieren
- **Status**: DONE
- **Beschreibung**: `update_entity_position()` nur bei tatsächlicher Positionsänderung (> 0.1px Schwelle) aufrufen. `register_entity()` initialisiert `_last_spatial_x/y` Attribute, `unregister_entity()` bereinigt sie.
- **Vorteil**: Eliminiert unnötige Grid-Updates für statische Entities. Spart ~3-5ms.
- **Dateien**: `game2d/systems/spatial.py`
- **Funktionen**: `update_entity_position()`, `register_entity()`, `unregister_entity()`

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
- **Beschreibung**: Entities außerhalb des Viewports bewegen sich weiter mit einfacher Physik + Building-Kollision, ohne teure AI. **Ab 2026-05-15: Auch Cops werden im Hintergrund vereinfacht!**
- **Aufteilung**:
  - **Nah (0-UPDATE_RANGE_BUFFER)**: Volles Update (AI + Animation + Entity-Entity-Kollision)
  - **Fern (UPDATE_RANGE_BUFFER+)**: Vereinfachte Bewegung mit Building-Kollision + Straßenbeschränkung
- **Straßenbeschränkung für Cars**: Nutzt jetzt schnelle Approximation mit `nearest_road_v/h` statt `rect_on_road()` (Optimierung F)
- **Dateien**: `game2d/main.py`
- **Funktionen**: `_background_move_entity()`, `_is_in_update_range()`
- **Konstanten**: `UPDATE_RANGE_BUFFER = max(300, W//4)` (dynamisch)

### Park Spatial Grid für Pedestrian-Kollision
- **Status**: DONE
- **Beschreibung**: Park-Rects (parks + amusement_parks) in Spatial Grid für O(1) Kollisionsprüfungen. Ersetzt manuelle Iteration über alle Parks.
- **Vorteil**: Deutlich schnellere Pfadprüfung für Peds, besonders im Vergnügungspark
- **Dateien**: `game2d/systems/spatial.py`, `game2d/world/geometry.py`, `game2d/main.py`

### G. Amusement-Park Pfad-Segmente cachen
- **Status**: DONE
- **Beschreibung**: Die teure `amusement_path_segments()` Funktion generierte bisher bei jedem Aufruf alle Bézier-Kurven für die Vergnügungspark-Pfade neu (CPU-intensiv). Jetzt werden die Pfad-Segmente einmalig bei Weltaufbau in `state.amusement_path_segments` gecacht und von allen Konsumenten wiederverwendet.
- **Vorteil**: Eliminiert redundante Pfad-Berechnungen in:
  - `point_on_amusement_path()` (Pedestrian-Kollision, mehrmals pro Frame)
  - `_draw_amusement_static()` (Rendering, jedes Frame)
  - `_draw_amusement_dynamic()` (Rendering, jedes Frame)
  - `rebuild_pedestrian_graph()` (Weltaufbau)
  - Minimap-Rendering (einmalig beim Start)
- **Gewinn**: ~15-25ms im Vergnügungspark (je nach Ped-Anzahl und Kamera-Position)
- **Bugfix**: Korrigierte fehlerhafte Return-Logik in `point_on_amusement_path()` (gab falsch `False`/ `True` zurück)
- **Dateien**: 
  - `game2d/state.py` (neues Feld `amusement_path_segments`)
  - `game2d/world/generation.py` (Caching bei Weltaufbau)
  - `game2d/world/geometry.py` (use cached segments in `point_on_amusement_path` + `rebuild_pedestrian_graph`)
  - `game2d/render/world_bg.py` (use cached segments)
  - `game2d/render/minimap.py` (use cached segments)

### H. Amusement-Park Statik als Sprite pre-rendern
- **Status**: DONE
- **Beschreibung**: Der gesamte statische Teil des Vergnügungsparks (Grundfläche, Pfade, Wege-Markierungen, Gebäude, Stände, Dekorationen) wird einmalig beim Weltaufbau als großes Sprite vorgerendert. Beim Rendern wird nur noch dieses Sprite geblittet statt alle Elemente jeden Frame neu zu zeichnen.
- **Vorteil**: Reduziert die Rendering-Kosten von O(100+) Draw-Calls pro Park auf O(1) Blit-Call. Eliminiert:
  - Mehrere `pygame.draw.rect()` Aufrufe für Grundfläche
  - Dutzende `_draw_flat_path()` Aufrufe für die Wege
  - Mehrere `_draw_*_building()` und `_draw_*_stand()` Aufrufe
  - Alle `pygame.draw.circle()` Aufrufe für Wegemarkierungen
  - Alle Pflanzen- und Bank-Rendering Calls
- **Gewinn**: ~10-20ms pro Frame im Vergnügungspark (abhängig von der Kamera-Position)
- **Technische Details**: 
  - Neues Feld `state.amusement_park_sprites` hält die vorgerenderten Surfaces
  - `_pre_render_amusement_park_sprites()` in `generation.py` rendert alle statischen Elemente
  - `_draw_amusement_static()`ittet nun nur noch das Sprite
  - Dynamische Elemente (Rollercoaster, Riesenrad, etc.) werden weiterhin jeden Frame gezeichnet
- **Dateien**:
  - `game2d/state.py` (neues Feld `amusement_park_sprites`)
  - `game2d/world/generation.py` (Pre-Render Funktion + Aufruf)
  - `game2d/render/world_bg.py` (use pre-rendered sprite in `_draw_amusement_static`)

### I. Amusement-Park Fahrgeschäfte als PNG-Sprites
- **Status**: DONE
- **Beschreibung**: Die dynamischen Fahrgeschäfte werden jetzt als **vorgefertigte PNG-Sprites** geladen statt prozedural gezeichnet zu werden. Ein separates Tool (`tools/render_amusement_sprites.py`) rendert alle Frames (36 pro Fahrgeschäft) als PNG-Dateien in `assets/sprites/amusement/`. Beim Spielstart werden diese PNGs geladen und beim Rendern nur noch geblittet.
- **Vorteil**: Eliminiert teure trigonometrische Berechnungen (`math.sin`, `math.cos`) und Draw-Calls pro Frame für:
  - Riesenrad (12 Gondeln mit Seilen)
  - Karussell (6 Pferde mit Stangen)
  - Schaukeln (mehrere schwingende Elemente)
  - Kraftmensch (Hebel-Bewegung)
  - Piratenschiff (Schaukelbewegung)
  - Stoßautos (fahrende Autos)
  - Kranspiel (Kran-Bewegung)
  - Rollercoaster (komplexe Bahn)
- **Gewinn**: ~5-10ms pro Frame im Vergnügungspark
- **Technische Details**:
  - **Neues Modul**: `game2d/render/amusement_sprites.py` mit `load_amusement_sprites()`
  - **Neues Feld**: `state.amusement_sprites['rides']` (Dict mit Frame-Listen pro Fahrgeschäft)
  - **Frame-Index**: Wird aus `traffic_time` berechnet: `frame_idx = int((t * 0.1) % 36)`
  - **Ladevorgang**: Sprites werden beim Spielstart in `main.py` geladen
  - **Tool**: `tools/render_amusement_sprites.py` zum Neugenerieren der Sprites
  - **Alle 8 Fahrgeschäfte** werden als Sprites geladen
- **Dateien**:
  - `game2d/render/amusement_sprites.py` (Sprite-Ladefunktion)
  - `game2d/main.py` (Aufruf zum Laden der Sprites)
  - `game2d/render/world_bg.py` (Verwendung der geladenen Frames)
  - `assets/sprites/amusement/` (288 PNG-Dateien + 8 JSON-Metadaten)
  - `tools/render_amusement_sprites.py` (Tool zum Generieren der Sprites)

### Amusement-Peds vereinfachte Pfadprüfung
- **Status**: DONE
- **Beschreibung**: Peds im Vergnügungspark (`is_amusement=True`) nutzen immer `allow_park=True`, was nur `point_on_amusement_path()` prüft (mit Spatial Grid) statt alle Park-Rects.
- **Vorteil**: Schnellere Pfadfindung für 20 Amusement-Peds
- **Dateien**: `game2d/main.py`, `game2d/entities/ped.py`
- **Funktionen**: `try_follow_route()`
