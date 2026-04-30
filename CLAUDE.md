# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Arbeitsweise

Beim Hinzufügen von neuem Code immer genau auf die unten beschriebene Architektur achten und neue Funktionalität strukturkonform an der richtigen Stelle einfügen (passendes Modul in `game2d/`, Zugriff auf Zustand via `state.current()`, keine Umgehung der bestehenden Aufteilung).

## Sound-Assets

Wenn neue Sounds gebraucht werden:

1. **Runterladen** von kenney.nl (CC0, kein Account, keine Attribution): `https://kenney.nl/assets/category:Audio` — passendes Audio-Pack auswählen, ZIP runterladen.
2. **Ablegen** als `.ogg` in `game2d/assets/sfx/` mit Namensschema `<category>_<variant>.ogg` (z.B. `door_open_a.ogg`, `door_open_b.ogg`). Mehrere Varianten = `audio.play(...)` würfelt zufällig.
3. **Implementieren**: `audio.play("category", pos=(x, y))` aus `game2d/systems/audio.py` an der passenden Stelle aufrufen. `audio.init()` lädt alle SFX automatisch beim Start ein, neue Kategorien sind sofort verfügbar.

Für Loop-Sounds (z.B. fliegende Geschosse, Motor): `audio.start_loop(...)` / `update_loop(...)` / `stop_loop(...)`. Master-Lautstärke regelt der User per ESC → Options-Slider, persistiert in `settings.json`.

**Wichtig (pygame-CE-Bug):** `Channel.set_volume(left, right)` (2-arg) setzt nur Panning, NICHT die Master-Lautstärke des Kanals. Daher in `audio.py` immer `Channel.set_volume(value)` (single-arg) verwenden — und zwar NACH `Channel.play(snd)`, weil `play()` die Channel-Volume zurücksetzt.

## Starten

```bash
# Venv aktivieren und Spiel starten
source venv/bin/activate
python game2d.py
# oder
python -m game2d.main
```

Abhängigkeiten: `pygame` (im venv vorinstalliert).

## Architektur

Das Spiel ist als Python-Paket `game2d/` strukturiert. `game2d.py` im Repo-Root ist nur ein 11-Zeilen-Shim, der `game2d.main:main()` aufruft.

```
game2d/
├── __init__.py
├── main.py              # Einstiegspunkt: pygame init, GameState, Hauptschleife
├── config.py            # W, H, WORLD_*, BLOCK, ROAD_W, Farben, WPN_*, PICKUP_*
├── state.py             # @dataclass GameState + Singleton-Accessor (init/current)
├── persistence.py       # scores.json, name_input_screen
├── world/
│   ├── geometry.py      # in_water, in_city, rect_on_road, lane_center_for_car, …
│   ├── generation.py    # build_world() — Wasser-Ring, Straßenraster, Häuser
│   ├── traffic.py       # LIGHT_*-Konstanten, traffic_light_state, _allows
│   └── spawning.py      # safe_spawn, road_spawn, cop_car_spawn_near, exit_car_position
├── entities/
│   ├── car.py           # class Car
│   └── ped.py           # class Ped
├── render/
│   ├── sprites.py       # make_car_sprite, make_ped_frames, make_building, …
│   ├── world_bg.py      # draw_world_bg, draw_crosswalks, draw_traffic_lights
│   └── hud.py           # draw_star
└── systems/
    ├── weapons.py       # fire(), aim_to_mouse()
    └── effects.py       # spawn_blood, make_corpse, do_explosion, trigger_game_over
```

Keine externen Assets — alle Grafiken werden prozedural zur Laufzeit gezeichnet.

### Zentraler GameState

`game2d/state.py` definiert `@dataclass GameState` mit allen Spielzustands-Feldern: Listen (cars, peds, cops, bullets, rockets, particles, …), Spielerzustand (player, in_car, weapon, ammo, fire_cd, …), Welt-Geometrie (buildings, roads_h/v, AI_OBSTACLES, WATER_RECTS), Loop-State (cam, traffic_time, game_over, …).

Module greifen via `from game2d.state import current` auf den aktuellen `GameState` zu. `main.py` ruft einmalig `state.init(GameState(...))` auf, alle anderen Module nutzen `current()`.

### Spielfluss in `main.py`

1. `pygame.init()`, Display + Fonts erzeugen
2. `name_input_screen()` (Startbildschirm)
3. `GameState` erzeugen, `state.init(state)` setzen
4. `build_world(state)` baut Wasser, Straßen, Häuser, AI_OBSTACLES
5. Initial-Verkehr (50 Autos) und NPCs (60) spawnen
6. Spieler initialisieren, Pickups verteilen
7. Hauptschleife (60 FPS): Events, Bewegung, KI, Bullets, Partikel, Rendering, HUD

## Sprite-Spezifikationen

| Sprite | Größe | Funktion |
|--------|-------|----------|
| Auto (normal) | 46×78 px | `render.sprites.make_car_sprite(body_col)` |
| Auto (Cop) | 46×78 px | `render.sprites.make_cop_car_sprite()` |
| Fußgänger-Frame | 20×24 px | `render.sprites._draw_ped_frame(...)` |
| Gebäude-Zelle | 32×32 px | Basis für `render.sprites.make_building()` |

Sprite-Koordinatensystem: Y-Achse zeigt nach unten. Fußgänger-Sprites: "vorn" = -y (oben).

## Steuerung

| Taste | Aktion |
|-------|--------|
| WASD | Bewegen / Fahren |
| Maus | Zielen |
| LMB / SPACE | Schießen |
| E | Auto ein-/aussteigen |
| F | Passanten berauben |
| 1–6 | Waffe wechseln (6 = RPG) |
| R | Neustart (nach Game Over) |
| ESC | Beenden |

## Waffensystem (`config.py`)

| Index | Name | Rate (s) | Schaden | Pellets | Spread | Auto |
|-------|------|----------|---------|---------|--------|------|
| 0 | Fäuste | 0.5 | 25 | 1 | 0 | Nein |
| 1 | Pistole | 0.4 | 35 | 1 | 0.03 | Nein |
| 2 | SMG | 0.08 | 15 | 1 | 0.08 | Ja |
| 3 | Schrotflinte | 0.85 | 80 | 6 | 0.22 | Nein |
| 4 | MG | 0.05 | 28 | 1 | 0.06 | Ja |
| 5 | Raketenwerfer | 1.6 | 200 (Explosion) | 1 | 0 | Nein |

Waffen 0+1 von Anfang an. 2–5 per Pickup freischalten.

## Spieler-Objekt

`state.player` ist eine `Ped`-Instanz mit Extra-Feldern:
- `hp = 100` (Cops 200, Passanten 60, Autos 200)
- `money`, `wanted` (0–5), `crime_timer`, `aim_angle`
- Sprite: blau `(40, 100, 200)`, Haare dunkel `(30, 20, 15)`
- Spieler-Sprite folgt Laufrichtung (WASD), **nicht** Mauszeiger — `aim_angle` steuert Schussrichtung separat

## Pickup-System

`state.pickups` als `[x, y, kind, respawn_cd]`. Respawn nach 20s. Konstanten in `config.py` (`PICKUP_AMMO`, `PICKUP_COLOR`, `PICKUP_LABEL`, `PICKUP_RESPAWN`).

| Kind | Farbe | Inhalt |
|------|-------|--------|
| `'hp'` | Grün | +30 HP (max 100) |
| 2 | Gelb | SMG +60 Schuss |
| 3 | Orange | Schrot +10 |
| 4 | Rot | MG +120 |
| 5 | Lila | RPG +3 |

## Render-Reihenfolge (in `main.py`)

1. `draw_world_bg(screen, icam)` — Wasser, Sand, Gras, Straßen, Ampeln
2. `state.blood_splats` (permanent, unter allem)
3. `state.pickups`
4. `state.corpses`
5. `state.buildings`
6. `state.wrecks`
7. `state.cars`
8. `state.peds`, `state.cops`, Spieler
9. Partikel: `blood_particles`, `bullets`, `rockets`, `fire_particles`, `smoke_particles`, `explosions`
10. HUD (HP-Balken, Geld, Waffe, Wanted-Sterne, Game Over)

## Wanted-System

- 0–5 Sterne, gesteuert durch `player.wanted` und `player.crime_timer`
- `crime_timer` zählt runter; bei 0 → `wanted -= 1`, Timer reset auf 25s
- Cops spawnen per `cop_car_spawn_near()` in 420–760px Radius vom Spieler
- Cop-Spawn-Rate: `max(2, 8 - wanted*1.5)` Sekunden zwischen Spawns
- Bei `wanted == 0`: alle Cop-Autos + Fuß-Cops sofort entfernt
- Wanted steigt bei: Passant überfahren/erschießen, Cop töten, Raub (F), Explosion

## Geld-System

| Aktion | Gewinn |
|--------|--------|
| Passant überfahren | 10–35 $ |
| Passant erschießen | 15–60 $ |
| Cop töten | 40–80 $ (Auto) / 50–100 $ (Rakete) |
| Auto explodiert (NPC) | 20–50 $ |
| Passant berauben (F) | 15–50 $ |
| Passant per Explosion | 20–55 $ |

## Wasser & Tod

- Wasserring: 220px an allen 4 Seiten (`WATER_W = 220`)
- Spieler betritt Wasser zu Fuß → sofort `hp = 0`, blaue Partikel, Game Over
- Auto fährt ins Wasser → `car.explode()` sofort

## Game Over & Scoreboard

- `trigger_game_over()` in `systems/effects.py` setzt `state.game_over = True`, speichert Score in `scores.json`
- Top-20 werden gespeichert, eigener Eintrag wird gelb hervorgehoben
- `scores.json` speichert auch `last_name` für Vorausfüllung beim nächsten Start
- Neustart (R): `os.execv(sys.executable, ...)` — vollständiger Prozess-Neustart

## Spawning-Logik (`world/spawning.py`)

- `safe_spawn()` — findet freie Position für Fußgänger (bevorzugt Gehsteig)
- `road_spawn()` — findet freie Fahrbahnposition + Ausrichtung für KI-Autos
- `cop_car_spawn_near(tx, ty)` — spawnt Cop-Auto in 420–760px Umkreis
- `exit_car_position(car)` — sucht freie Position seitlich/hinten vom Auto

## Partikel-Formate (Listen auf `state`)

```python
bullets         = [x, y, vx, vy, ttl, from_cop, dmg]
blood_particles = [x, y, vx, vy, ttl, radius]
smoke_particles = [x, y, vx, vy, ttl, max_ttl, radius]
fire_particles  = [x, y, vx, vy, ttl, max_ttl, radius]
explosions      = [x, y, t, max_t, max_radius]
rockets         = [x, y, vx, vy, ttl, audio_channel]
wrecks          = (sprite, x, y, angle, dents_list)
corpses         = (sprite, x, y, angle)
blood_splats    = (x, y, radius, color)
```

## Wichtige Konstanten (`config.py`)

```python
WORLD_W, WORLD_H = 6000, 6000
BLOCK        = 600    # Stadtblockgröße
ROAD_W       = 118    # Fahrbahnbreite
SIDEWALK_W   = 34     # Gehsteigbreite
WATER_W      = 220    # Wasserring-Breite
BEACH_W      = 110    # Strandbreite
W, H         = 1280, 800  # Fenstergröße
```
