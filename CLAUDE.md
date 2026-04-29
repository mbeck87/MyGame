# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Starten

```bash
# Venv aktivieren und Spiel starten
source venv/bin/activate
python game2d.py
```

Das Spiel läuft direkt ohne Build-Schritt. Abhängigkeiten: `pygame` (im venv vorinstalliert via Panda3D-Distribution).

## Architektur

Einzelne Datei: `game2d.py` (~1939 Zeilen), kein Modulsystem. Keine externen Assets — alle Grafiken werden prozedural zur Laufzeit gezeichnet.

**Aufbau (grob):**

1. **Scoreboard** (~13): `scores.json` speichert Top-20-Scores + letzten Namen. `name_input_screen()` = Startbildschirm.

2. **Farb-Konstanten** (~97): Alle Farben als globale Tupel (`ASPHALT`, `GRASS`, `SKIN`, `COP_BLUE`, etc.).

3. **Sprite-Generatoren** (~133): Alle pygame.Surface-Objekte werden hier erzeugt — siehe Sprite-Spezifikationen.

4. **Weltgenerierung** (~282): Grid aus BLOCK-px-Blöcken. Gebäude deterministisch per `random.seed(7)`. `buildings[]` als `(pygame.Rect, Surface)`-Tupel. `AI_OBSTACLES = buildings + WATER_RECTS`.

5. **Traffic-System** (~354): Ampeln mit 4 Phasen (red/red_yellow/green/yellow). `traffic_light_state(ix, iy)` → `(axis, phase)`.

6. **Klasse `Car`** (~443): `max_spd` 380 (Cop) / 320 (Normal). Bei `hp <= 0` → `burning` → `explode()`. Kollisions-Rect: 34×62 (vertikal) oder 62×34 (horizontal).

7. **Klasse `Ped`** (~1004): Cops + Passanten. `state = 'wander' | 'flee'`. Cops: HP 200, Passanten: HP 60.

8. **Spielschleife** (~1503): 60 FPS, Kamera Smooth-Follow. Wanted, Verkehr, NPCs, Bullets, Pickups, Render.

**Wichtige Globals:** `player`, `in_car`, `weapon`, `ammo`, `cam`, `game_over`, `traffic_time`, `intersection_claims`.

**Globale Listen:** `cars`, `peds`, `cops`, `bullets`, `blood_splats`, `blood_particles`, `corpses`, `wrecks`, `explosions`, `fire_particles`, `smoke_particles`.

## Sprite-Spezifikationen

| Sprite | Größe | Funktion |
|--------|-------|----------|
| Auto (normal) | 46×78 px | `make_car_sprite(body_col)` |
| Auto (Cop) | 46×78 px | `make_cop_car_sprite()` |
| Fußgänger-Frame | 20×24 px | `_draw_ped_frame(...)` |
| Gebäude-Zelle | 32×32 px | Basis für `make_building()` |

Sprite-Koordinatensystem: Y-Achse zeigt nach unten. Fußgänger-Sprites: "vorn" = -y (oben), werden beliebig rotiert.

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

## Waffensystem

| Index | Name | Rate (s) | Schaden | Pellets | Spread | Auto |
|-------|------|----------|---------|---------|--------|------|
| 0 | Fäuste | 0.5 | 25 | 1 | 0 | Nein |
| 1 | Pistole | 0.4 | 35 | 1 | 0.03 | Nein |
| 2 | SMG | 0.08 | 15 | 1 | 0.08 | Ja |
| 3 | Schrotflinte | 0.85 | 80 | 6 | 0.22 | Nein |
| 4 | MG | 0.05 | 28 | 1 | 0.06 | Ja |
| 5 | Raketenwerfer | 1.6 | 200 (Explosion) | 1 | 0 | Nein |

Waffen 0+1 von Anfang an. 2–5 per Pickup freischalten. `ammo = {1: 80, ...}`, Rakete spawnt `rockets[]`-Eintrag.

## Spieler-Objekt (`player`)

`player` ist eine `Ped`-Instanz mit extra Feldern:
- `hp = 100` — Cops: 200, Passanten: 60, Autos: 200
- `money`, `wanted` (0–5), `crime_timer`, `aim_angle`
- Sprite: blau `(40, 100, 200)`, Haare dunkel `(30, 20, 15)`
- Spieler-Sprite folgt Laufrichtung (WASD), **nicht** Mauszeiger — `aim_angle` steuert Schussrichtung separat

## Pickup-System

`pickups[]` als `[x, y, kind, respawn_cd]`. Respawn nach 20s.

| Kind | Farbe | Inhalt |
|------|-------|--------|
| `'hp'` | Grün | +30 HP (max 100) |
| 2 | Gelb | SMG +60 Schuss |
| 3 | Orange | Schrot +10 |
| 4 | Rot | MG +120 |
| 5 | Lila | RPG +3 |

## Render-Reihenfolge

1. Weltboden (`draw_world_bg`) — Wasser, Sand, Gras, Straßen, Ampeln
2. `blood_splats` (permanent, unter allem)
3. Pickups
4. Leichen (`corpses`)
5. Gebäude (`buildings`)
6. Wracks (`wrecks`)
7. Autos (`cars`)
8. Passanten (`peds`), Cops (`cops`), Spieler
9. Partikel: Blut, Bullets, Raketen, Feuer, Rauch, Explosionen
10. HUD (HP-Balken, Geld, Waffe, Wanted-Sterne)

## Wanted-System

- 0–5 Sterne, gesteuert durch `player.wanted` und `player.crime_timer`
- `crime_timer` zählt runter; bei 0 → `wanted -= 1`, Timer reset auf 25s
- Cops spawnen per `cop_car_spawn_near()` in 420–760px Radius vom Spieler
- Cop-Spawn-Rate: `max(2, 8 - wanted*1.5)` Sekunden zwischen Spawns
- Bei `wanted == 0`: alle Cop-Autos + Fuß-Cops sofort entfernt
- Wanted steigt bei: Passant überfahr/erschießen, Cop töten, Raub (F), Explosion

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

- `trigger_game_over()` setzt `game_over = True`, speichert Score in `scores.json`
- Top-20 werden gespeichert, eigener Eintrag wird gelb hervorgehoben
- `scores.json` speichert auch `last_name` für Vorausfüllung beim nächsten Start
- Neustart: `os.execv(sys.executable, ...)` — vollständiger Prozess-Neustart

## Spawning-Logik

- `safe_spawn()` — findet freie Position für Fußgänger (bevorzugt Gehsteig)
- `road_spawn()` — findet freie Fahrbahnposition + Ausrichtung für KI-Autos
- `cop_car_spawn_near(tx, ty)` — spawnt Cop-Auto in 420–760px Umkreis
- `exit_car_position(car)` — sucht freie Position seitlich/hinten vom Auto

## Partikel-Formate

```python
bullets        = [x, y, vx, vy, ttl, from_cop, dmg]
blood_particles= [x, y, vx, vy, ttl, radius]
smoke_particles= [x, y, vx, vy, ttl, max_ttl, radius]
fire_particles = [x, y, vx, vy, ttl, max_ttl, radius]
explosions     = [x, y, t, max_t, max_radius]
rockets        = [x, y, vx, vy, ttl]
wrecks         = (sprite, x, y, angle, dents_list)
corpses        = (sprite, x, y, angle)
blood_splats   = (x, y, radius, color)
```

## Wichtige Konstanten

```python
WORLD_W, WORLD_H = 6000, 6000
BLOCK        = 600    # Stadtblockgröße
ROAD_W       = 118    # Fahrbahnbreite
SIDEWALK_W   = 34     # Gehsteigbreite
WATER_W      = 220    # Wasserring-Breite
BEACH_W      = 110    # Strandbreite
W, H         = 1280, 800  # Fenstergröße
```
