# Tools für MyGame

Hier liegen Hilfsprogramme für die Spielentwicklung.

## 🎡 render_amusement_sprites.py

Rendert Amusement-Park Fahrgeschäfte als Sprite-Sheets oder Einzel-PNGs.

### Verwendung

```bash
# Alle Fahrgeschäfte als Einzel-PNGs rendern
python tools/render_amusement_sprites.py --ride alle

# Nur Riesenrad als Sprite-Sheet rendern
python tools/render_amusement_sprites.py --ride ferris_wheel --sheet

# Karussell mit 60 Frames und Größe 256x256 rendern
python tools/render_amusement_sprites.py --ride carousel --frames 60 --size 256

# Alle Fahrgeschäfte in ein Custom-Verzeichnis rendern
python tools/render_amusement_sprites.py --ride alle --output custom/sprites/

# Verfügbare Fahrgeschäfte auflisten
python tools/render_amusement_sprites.py --list

# Nur simulieren (keine Dateien schreiben)
python tools/render_amusement_sprites.py --ride ferris_wheel --dry-run

# Ausführliche Ausgabe
python tools/render_amusement_sprites.py --ride alle --verbose
```

### Optionen

| Option | Beschreibung | Standardwert |
|--------|--------------|--------------|
| `--output, -o` | Ausgabeverzeichnis | `assets/sprites/amusement/` |
| `--ride, -r` | Fahrgeschäft (alle, ferris_wheel, carousel, swing, strongman, pirate_ship, bumper_cars, claw_machine, roller_coaster) | `alle` |
| `--frames, -f` | Anzahl Frames pro Animation | `36` |
| `--size, -s` | Größe der Sprites in Pixeln | `200` |
| `--sheet, -S` | Als Sprite-Sheet rendern | `False` |
| `--transparent` | Mit Transparenz rendern | `True` |
| `--list` | Verfügbare Fahrgeschäfte auflisten | `False` |
| `--dry-run` | Nur simulieren, keine Dateien schreiben | `False` |
| `--verbose, -v` | Ausführliche Ausgabe | `False` |

### Ausgabe

Das Tool erstellt:

#### Einzelbilder-Modus (Standard)
```
assets/sprites/amusement/
├── ferris_wheel_frame_000.png
├── ferris_wheel_frame_001.png
├── ...
├── ferris_wheel_frame_035.png
├── ferris_wheel_meta.json
├── carousel_frame_000.png
├── ...
└── carousel_meta.json
```

#### Sprite-Sheet-Modus (`--sheet`)
```
assets/sprites/amusement/
├── ferris_wheel_sheet_36f.png  # Alle 36 Frames in einem Bild
├── ferris_wheel_meta.json
├── carousel_sheet_36f.png
└── carousel_meta.json
```

### Metadaten-Datei

Jedes Fahrgeschäft erhält eine `{ride}_meta.json` Datei mit:

```json
{
  "ride": "ferris_wheel",
  "frames": 36,
  "frame_width": 200,
  "frame_height": 200,
  "sheet_width": 7200,
  "sheet_height": 200,
  "type": "sheet"
}
```

### Verfügbare Fahrgeschäfte

| Name | Beschreibung | Größe |
|------|--------------|-------|
| `ferris_wheel` | Riesenrad mit 12 Gondeln | 200x200 |
| `carousel` | Karussell mit 6 Pferden | 200x200 |
| `swing` | Schaukel-Fahrgeschäft | 200x200 |
| `strongman` | Kraftmensch (Hammerschlag) | 200x200 |
| `pirate_ship` | Piratenschiff (Schaukelbewegung) | 200x200 |
| `bumper_cars` | Stoßautos | 400x250 |
| `claw_machine` | Kranspiel | 150x150 |
| `roller_coaster` | Achterbahn (komplex) | 500x200 |

### später Integration ins Spiel

Nach dem Rendern können die Sprites im Spiel geladen werden:

```python
# Einzelbilder laden
import pygame
frames = []
for i in range(36):
    surf = pygame.image.load(f"assets/sprites/amusement/ferris_wheel_frame_{i:03d}.png")
    frames.append(surf)

# Sprite-Sheet laden und Frames extrahieren
import pygame
sheet = pygame.image.load("assets/sprites/amusement/ferris_wheel_sheet_36f.png")
frame_width = 200  # aus meta.json
frames = []
for i in range(36):
    frame = sheet.subsurface((i * frame_width, 0, frame_width, 200))
    frames.append(frame)

# Animation abspielen
current_frame = 0
def update(dt):
    global current_frame
    current_frame = (current_frame + 1) % len(frames)

def render(surf, x, y):
    surf.blit(frames[current_frame], (x, y))
```

### Abhängigkeiten

- pygame-ce
- Das `game2d` Paket muss importierbar sein

### Hinweise

- Das Tool muss vom Projekt-Root aus aufgerufen werden
- Pygame wird im Headless-Modus (1x1 Fenster) initialisiert
- Die Sprites werden mit Transparenz (Alpha-Kanal) gerendert
- Für beste Ergebnisse: Größe an das Spiel anpassen (Standard: 200px)
