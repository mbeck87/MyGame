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

Einzelne Datei: `game2d.py` (~718 Zeilen), kein Modulsystem.

**Aufbau (grob):**

1. **Sprite-Generatoren** (Zeilen 33–165): Alle Grafiken werden zur Laufzeit prozedural gezeichnet — kein externes Asset. `make_car_sprite`, `make_cop_car_sprite`, `make_ped_frames`, `make_building` erzeugen `pygame.Surface`-Objekte.

2. **Weltgenerierung** (167–201): Grid aus `BLOCK=400`-px-Blöcken. Straßen liegen auf Vielfachen von `BLOCK`. Gebäude werden deterministisch per `random.seed(7)` platziert und als `(pygame.Rect, Surface)`-Tupel in `buildings[]` gespeichert.

3. **Spielobjekte** (204–367):
   - `Car` — Spieler- und KI-Fahrzeuge; `ai_update()` navigiert mit simplem Obstacle-Avoidance + Zufalls-Turn.
   - `Ped` — Fußgänger & Cops; Cops verfolgen Spieler (`state='wander'|'flee'`), feuern Bullets.
   - Globale Listen: `cars`, `peds`, `cops`, `bullets`, `blood_splats`, `blood_particles`, `corpses`.

4. **Spielschleife** (494–717): Klassische pygame-Schleife @ 60 FPS.
   - Kamera als geglättetes Smooth-Follow (`cam`-Liste, Zeile 555).
   - Wanted-System (1–5 Sterne): steuert Cop-Spawn-Rate und -Anzahl.
   - Bullets als `[x, y, vx, vy, ttl, from_cop, dmg]`-Listen.

**Wichtige Globals:** `player`, `in_car`, `weapon`, `ammo`, `cam`, `game_over`.

## Steuerung

| Taste | Aktion |
|-------|--------|
| WASD | Bewegen / Fahren |
| Maus | Zielen |
| LMB / SPACE | Schießen |
| E | Auto ein-/aussteigen |
| F | Passanten berauben |
| 1–5 | Waffe wechseln |
| R | Neustart (nach Game Over) |
| ESC | Beenden |
