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
- **Beschreibung**: Nur Entities im Viewport (+ 300px Puffer) voll updaten. Cars/Peds/Cats außerhalb: Position behalten, aber AI/Animate pausieren. Cops immer updaten (hohe Priorität).
- **Vorteil**: Skaliert linear mit sichtbaren Entities
- **Dateien**: `game2d/main.py`
- **Konstante**: `UPDATE_RANGE_BUFFER = 300`
- **Funktion**: `_is_in_update_range()`

### B. Update-Frequenz stufen
- **Status**: PENDING
- **Beschreibung**: Sichtbare Entities: 60 FPS, nah außerhalb: 30 FPS, fern: 15 FPS
- **Vorteil**: Reduziert Updates bei hoher Entity-Dichte
- **Abhängigkeit**: Testen ob A ausreicht

### C. AI-Kosten reduzieren
- **Status**: NOT STARTED
- **Beschreibung**: `ai_update()` für Cars optimieren (Pathfinding cachen, vereinfachen). Route-Berechnung nur bei Bedarf.
- **Vorteil**: Cars sind wahrscheinlich der größte Einzelposten

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
