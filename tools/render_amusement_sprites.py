#!/usr/bin/env python3
"""
Amusement Park Sprite Renderer

Tool zum Vorrendern von Amusement-Park Fahrgeschäften als Sprite-Sheets oder Einzel-PNGs.
Die generierten Sprites können später als Assets im Spiel geladen werden.

Verwendung:
    python tools/render_amusement_sprites.py [OPTIONEN]

Optionen:
    --output, -o TEXT    Ausgabeverzeichnis (default: assets/sprites/amusement/)
    --ride, -r TEXT     Welches Fahrgeschäft rendern (alle, ferris_wheel, carousel, swing, strongman, pirate_ship, bumper_cars, claw_machine, roller_coaster)
    --frames, -f INT    Anzahl Frames pro Animation (default: 36)
    --size, -s INT     Größe der Sprites in Pixeln (default: 200)
    --sheet, -S        Als Sprite-Sheet rendern (statt Einzelbilder)
    --transparent     Mit Transparenz (SRCALPHA) rendern
    --list            Verfügbare Fahrgeschäfte auflisten

Beispiele:
    # Alle Fahrgeschäfte als Einzel-PNGs rendern
    python tools/render_amusement_sprites.py --ride alle
    
    # Nur Riesenrad als Sprite-Sheet rendern
    python tools/render_amusement_sprites.py --ride ferris_wheel --sheet
    
    # Karussell mit 60 Frames rendern
    python tools/render_amusement_sprites.py --ride carousel --frames 60
"""

import argparse
import math
import os
import sys
import pygame

# Füge den Projekt-Pfad hinzu, um die Module zu importieren
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from game2d.render.world_bg import (
    _draw_ferris_wheel, _draw_carousel,
    _draw_strongman_dynamic, _draw_pirate_ship_dynamic,
    _draw_bumper_cars_dynamic, _draw_swing_ride_dynamic,
    _draw_claw_machine_dynamic, _draw_new_roller_coaster,
    _draw_swing_ride_base, _draw_strongman_base, _draw_pirate_ship_base,
    _draw_claw_machine_base, _draw_bumper_arena, _amusement_new_layout
)


def _draw_new_roller_coaster_for_sprites(surf, area, t):
    """Modifizierte Version die Wagen auch in der Station zeichnet (für Sprite-Generierung)."""
    import math
    import pygame
    from game2d.render.world_bg import _draw_centered_label
    
    # Kopiere den vollständigen Code von _draw_new_roller_coaster
    # aber deaktiviere die station_hide Prüfung
    pygame.draw.rect(surf, (38, 92, 58), area.inflate(18, 18), border_radius=10)
    pygame.draw.rect(surf, (42, 104, 64), area.inflate(10, 10), border_radius=8)
    ground_y = area.bottom - 12
    pygame.draw.rect(surf, (52, 124, 70), (area.left - 4, ground_y - 8, area.w + 8, 20), border_radius=5)
    pygame.draw.line(surf, (92, 142, 74), (area.left - 2, ground_y - 8), (area.right + 2, ground_y - 8), 2)

    station = pygame.Rect(area.left + 14, area.bottom - 70, 116, 52)
    pygame.draw.rect(surf, (42, 30, 26), station.move(4, 5), border_radius=4)
    pygame.draw.rect(surf, (178, 62, 70), station, border_radius=4)
    pygame.draw.rect(surf, (100, 42, 48), station, 2, border_radius=4)
    pygame.draw.polygon(surf, (238, 194, 70), [
        (station.left - 8, station.top + 6),
        (station.centerx, station.top - 24),
        (station.right + 8, station.top + 6),
    ])
    pygame.draw.line(surf, (120, 74, 38), (station.left - 4, station.top + 6), (station.right + 4, station.top + 6), 2)
    for sx in range(station.left + 12, station.right - 8, 17):
        pygame.draw.line(surf, (230, 204, 118), (sx, station.top + 10), (sx, station.top + 23), 2)
    entry_door = pygame.Rect(station.left + 12, station.bottom - 24, 30, 24)
    exit_door = pygame.Rect(station.right - 42, station.bottom - 24, 30, 24)
    for door, label in ((entry_door, "EIN"), (exit_door, "AUS")):
        pygame.draw.rect(surf, (44, 34, 30), door, border_radius=2)
        pygame.draw.rect(surf, (238, 206, 118), (door.left + 4, door.top + 4, door.w - 8, 8), border_radius=1)
        _draw_centered_label(surf, label, (door.centerx, door.top + 8), 12, (82, 48, 32))
    platform = pygame.Rect(station.left + 8, station.top + 25, station.w - 16, 7)
    pygame.draw.rect(surf, (92, 48, 42), platform, border_radius=2)

    def p(rx, ry):
        return area.left + area.w * rx, area.top + area.h * ry

    def bezier_points(a, b, c, d, count=30):
        points = []
        for i in range(count):
            u = i / (count - 1)
            inv = 1 - u
            x = inv**3 * a[0] + 3 * inv**2 * u * b[0] + 3 * inv * u**2 * c[0] + u**3 * d[0]
            y = inv**3 * a[1] + 3 * inv**2 * u * b[1] + 3 * inv * u**2 * c[1] + u**3 * d[1]
            points.append((x, y))
        return points

    station_track_y = station.bottom - 6
    station_entry = (entry_door.centerx, station_track_y)
    station_exit = (exit_door.centerx, station_track_y)
    start = station_exit
    end = station_entry
    lcx, lcy = p(0.63, 0.45)
    loop_r = min(area.w * 0.086, area.h * 0.27)
    loop_bottom = (lcx, lcy + loop_r)
    loop_points = []
    for i in range(73):
        u = i / 72
        ang = math.radians(90) - math.tau * u
        loop_points.append((lcx + math.cos(ang) * loop_r, lcy + math.sin(ang) * loop_r))

    samples = [station_entry]
    curves = (
        (start, p(0.23, 0.83), p(0.26, 0.77), p(0.29, 0.70)),
        (p(0.29, 0.70), p(0.31, 0.39), p(0.34, 0.14), p(0.39, 0.16)),
        (p(0.39, 0.16), p(0.46, 0.15), p(0.47, 0.76), p(0.53, 0.75)),
        (p(0.53, 0.75), p(0.57, 0.76), p(0.59, 0.69), loop_bottom),
    )
    for curve_idx, curve in enumerate(curves):
        pts = bezier_points(*curve, count=30)
        if curve_idx:
            pts = pts[1:]
        samples.extend(pts)
    samples.extend(loop_points[1:])
    return_curves = (
        (loop_points[-1], p(0.72, 0.76), p(0.76, 0.23), p(0.83, 0.27)),
        (p(0.83, 0.27), p(0.92, 0.38), p(0.96, 0.70), p(0.90, 0.74)),
        (p(0.90, 0.74), p(0.72, 0.86), p(0.50, 0.82), p(0.34, 0.76)),
        (p(0.34, 0.76), p(0.24, 0.82), p(0.15, 0.86), end),
    )
    for curve in return_curves:
        samples.extend(bezier_points(*curve, count=30)[1:])

    pts_i = [(int(x), int(y)) for x, y in samples]
    support_points = []
    station_clear = station.inflate(18, 28)
    for i in range(6, len(pts_i) - 6, 15):
        x, y = pts_i[i]
        if station_clear.collidepoint(x, y) or ground_y - y < 22:
            continue
        support_points.append((x, y, ground_y))
    for x, y, base_y in support_points:
        pygame.draw.line(surf, (62, 62, 68), (x, y + 4), (x, base_y), 3)
        pygame.draw.line(surf, (142, 142, 150), (x + 1, y + 5), (x + 1, base_y - 2), 1)
        pygame.draw.ellipse(surf, (54, 54, 58), (x - 10, base_y - 3, 20, 6))
    for prev, cur in zip(support_points, support_points[1:]):
        ax, ay, abase = prev
        bx, by, bbase = cur
        if abs(bx - ax) > 42:
            continue
        pygame.draw.line(surf, (86, 86, 94), (ax, abase - 8), (bx, by + 8), 1)
        pygame.draw.line(surf, (86, 86, 94), (ax, ay + 8), (bx, bbase - 8), 1)

    pygame.draw.lines(surf, (34, 52, 34), False, pts_i, 9)
    pygame.draw.lines(surf, (82, 26, 32), False, pts_i, 7)
    pygame.draw.lines(surf, (220, 58, 66), False, pts_i, 4)
    pygame.draw.lines(surf, (252, 142, 132), False, pts_i, 1)
    for i in range(0, len(pts_i), 8):
        x, y = pts_i[i]
        pygame.draw.circle(surf, (100, 36, 42), (x, y), 2)
        pygame.draw.circle(surf, (248, 160, 144), (x, y - 1), 1)

    travel_points = samples
    if math.hypot(samples[-1][0] - samples[0][0], samples[-1][1] - samples[0][1]) > 0.01:
        travel_points = samples + [samples[0]]
    segment_lengths = []
    total_len = 0.0
    for a, b in zip(travel_points, travel_points[1:]):
        seg_len = math.hypot(b[0] - a[0], b[1] - a[1])
        segment_lengths.append(seg_len)
        total_len += seg_len

    def point_on_track(distance):
        distance %= total_len
        walked = 0.0
        for i, seg_len in enumerate(segment_lengths):
            if walked + seg_len >= distance:
                a = travel_points[i]
                b = travel_points[i + 1]
                frac = 0.0 if seg_len <= 0 else (distance - walked) / seg_len
                x = a[0] + (b[0] - a[0]) * frac
                y = a[1] + (b[1] - a[1]) * frac
                ang = math.atan2(b[1] - a[1], b[0] - a[0])
                return x, y, ang
            walked += seg_len
        a = travel_points[-2]
        b = travel_points[-1]
        return b[0], b[1], math.atan2(b[1] - a[1], b[0] - a[0])

    train_head = (t * 116) % total_len
    # MODIFIED: Skip station_hide check - always draw cars for sprite rendering
    car_cols = ((42, 92, 210), (58, 140, 226), (242, 186, 60), (220, 64, 78))
    for car_no, gap in enumerate((0, 26, 52, 78)):
        x, y, ang = point_on_track(train_head - gap)
        # ALWAYS DRAW - no station hide check
        ux, uy = math.cos(ang), math.sin(ang)
        nx, ny = -uy, ux
        if ny > 0:
            nx, ny = -nx, -ny
        x += nx * 7
        y += ny * 7
        body = []
        for lx, ly in ((-12, -8), (13, -7), (14, 6), (-13, 7)):
            body.append((int(x + ux * lx + nx * ly), int(y + uy * lx + ny * ly)))
        pygame.draw.polygon(surf, (26, 24, 34), [(px + 2, py + 3) for px, py in body])
        pygame.draw.polygon(surf, car_cols[car_no], body)
        pygame.draw.lines(surf, (22, 24, 34), True, body, 1)
        pygame.draw.line(surf, (238, 238, 230),
                         (int(x + ux * -5 + nx * -4), int(y + uy * -5 + ny * -4)),
                         (int(x + ux * 8 + nx * -4), int(y + uy * 8 + ny * -4)), 2)
        for lx in (-8, 8):
            wx = int(x + ux * lx - nx * 7)
            wy = int(y + uy * lx - ny * 7)
            pygame.draw.circle(surf, (24, 24, 28), (wx, wy), 3)
            pygame.draw.circle(surf, (198, 198, 204), (wx, wy), 1)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Rendere Amusement-Park Fahrgeschäfte als Sprites",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  python %(prog)s --ride alle
  python %(prog)s --ride ferris_wheel --frames 36 --size 256
  python %(prog)s --ride carousel --sheet --output custom/output/
        """
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=os.path.join(PROJECT_ROOT, "assets", "sprites", "amusement"),
        help="Ausgabeverzeichnis (default: assets/sprites/amusement/)"
    )
    parser.add_argument(
        "--ride", "-r",
        type=str,
        default="alle",
        choices=["alle", "ferris_wheel", "carousel", "swing", "strongman", 
                 "pirate_ship", "bumper_cars", "claw_machine", "roller_coaster"],
        help="Welches Fahrgeschäft rendern"
    )
    parser.add_argument(
        "--frames", "-f",
        type=int,
        default=36,
        help="Anzahl Frames pro Animation (default: 36)"
    )
    parser.add_argument(
        "--size", "-s",
        type=int,
        default=200,
        help="Größe der Einzel-Sprites in Pixeln (default: 200)"
    )
    parser.add_argument(
        "--sheet", "-S",
        action="store_true",
        help="Als Sprite-Sheet rendern (alle Frames in einer Datei)"
    )
    parser.add_argument(
        "--transparent",
        action="store_true",
        default=True,
        help="Mit Transparenz rendern (default: True)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Verfügbare Fahrgeschäfte auflisten und beenden"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Nur simulieren, keine Dateien schreiben"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Ausführliche Ausgabe"
    )
    return parser.parse_args()


# Import der Base-Funktionen
from game2d.render.world_bg import (
    _draw_claw_machine_base, _draw_strongman_base,
    _draw_pirate_ship_base, _draw_swing_ride_base
)

# Konfiguration für jedes Fahrgeschäft
# speed: Animationsgeschwindigkeit (t * speed % num_frames)
RIDE_CONFIG = {
    "ferris_wheel": {
        "func": _draw_ferris_wheel,
        "center_offset": (100, 100),
        "size": (200, 200),
        "description": "Riesenrad mit 12 Gondeln",
        "speed": 2.4,
        "has_base": False  # Zeichnet Basis + Gondeln in einer Funktion
    },
    "carousel": {
        "func": _draw_carousel,
        "center_offset": (100, 100),
        "size": (200, 200),
        "description": "Karussell mit 6 Pferden",
        "speed": 2.4,
        "has_base": False  # Zeichnet Basis + Pferde in einer Funktion
    },
    "swing": {
        "func": _draw_swing_ride_dynamic,
        "base_func": _draw_swing_ride_base,
        "center_offset": (100, 100),
        "size": (200, 200),
        "description": "Schaukel-Fahrgeschäft",
        "speed": 3.6,
        "has_base": True  # Benötigt separate Base
    },
    "strongman": {
        "func": _draw_strongman_dynamic,
        "base_func": _draw_strongman_base,
        "center_offset": (100, 100),
        "size": (200, 200),
        "description": "Kraftmensch (Hammerschlag)",
        "speed": 1.44,
        "has_base": True  # Benötigt separate Base
    },
    "pirate_ship": {
        "func": _draw_pirate_ship_dynamic,
        "base_func": _draw_pirate_ship_base,
        "center_offset": (100, 100),
        "size": (200, 200),
        "description": "Piratenschiff (Schaukelbewegung)",
        "speed": 2.0,
        "has_base": True  # Benötigt separate Base
    },
    "bumper_cars": {
        "func": _draw_bumper_cars_dynamic,
        "base_func": _draw_bumper_arena,
        "center_offset": (0, 0),
        "size": (400, 250),
        "description": "Stoßautos",
        "speed": 4.5,
        "rect_param": True,  # Benötigt ein Rect statt (x, y)
        "rect": (50, 50, 300, 150),  # Area innerhalb der 400x250 Surface
        "has_base": True  # Benötigt separate Base (Arena)
    },
    "claw_machine": {
        "func": _draw_claw_machine_dynamic,
        "base_func": _draw_claw_machine_base,
        "center_offset": (75, 75),
        "size": (150, 150),
        "description": "Kranspiel",
        "speed": 7.2,
        "extra_params": (25, 25, 58, 78),  # (x, y, w, h) für Claw Machine
        "has_base": True  # Benötigt separate Base
    },
    "roller_coaster": {
        "func": _draw_new_roller_coaster_for_sprites,
        "center_offset": (0, 0),
        "size": (500, 200),
        "description": "Achterbahn (komplex, prozedural)",
        "speed": 6.0,
        "rect_param": True,
        "area": (0, 20, 500, 160),  # (x, y, w, h) - angepasst an Surface-Größe
        "has_base": False  # _draw_new_roller_coaster_for_sprites zeichnet Bahn + Wagen
    }
}


def ensure_output_dir(output_dir, dry_run=False):
    """Stelle sicher, dass das Ausgabeverzeichnis existiert."""
    if dry_run:
        return
    os.makedirs(output_dir, exist_ok=True)


def render_single_ride(ride_name, output_dir, num_frames=36, size=200, 
                      sheet_mode=False, transparent=True, dry_run=False, verbose=False):
    """Rendere ein einzelnes Fahrgeschäft als Sprites."""
    config = RIDE_CONFIG[ride_name]
    
    if verbose:
        print(f"  Rendere {ride_name} ({config['description']})...")
    
    # Erstelle Surface für Einzel-Frames
    frame_size = config.get('size', (size, size))
    use_alpha = transparent
    
    frames = []
    for frame_idx in range(num_frames):
        # Erstelle ein leeres Surface
        surf = pygame.Surface(frame_size, pygame.SRCALPHA if use_alpha else 0)
        surf.fill((0, 0, 0, 0) if use_alpha else (0, 0, 0))
        
        # Berechne t-Wert für diese Animation
        # Für Roller Coaster: Skalierung, um flüssige Animation zu gewährleisten
        # t_scale=1.5 bewegt den Zug ca. 28 Pixel pro Frame bei total_len≈1500
        t_scale = 1.5 if ride_name == "roller_coaster" else 1.0
        t = (frame_idx / num_frames) * math.tau * t_scale  # 0 bis 2*pi (* scale)
        
        center_x, center_y = config['center_offset']
        
        # Zuerst die Basis zeichnen, falls vorhanden
        if config.get('has_base', False) and 'base_func' in config:
            base_func = config['base_func']
            base_params = config.get('base_params', ())
            if ride_name == "claw_machine":
                # _draw_claw_machine_base(surf, x, y, w, h)
                x, y, w, h = config['extra_params']
                base_func(surf, x, y, w, h)
            elif ride_name == "bumper_cars":
                # _draw_bumper_arena(surf, rect)
                rect = pygame.Rect(*config['rect'])
                base_func(surf, rect)
            else:
                # Standard: _draw_*_base(surf, cx, cy)
                base_func(surf, center_x, center_y)
        
        # Dann die dynamischen/beweglichen Teile zeichnen
        func = config['func']
        
        if ride_name == "roller_coaster":
            # Rollercoaster benötigt ein Rect
            area = pygame.Rect(*config['area'])
            func(surf, area, t)
        elif ride_name == "bumper_cars":
            # Bumper Cars benötigt ein Rect - verwende das spezifische Rect aus der Config
            if 'rect' in config:
                rect = pygame.Rect(*config['rect'])
            else:
                rect = pygame.Rect(0, 0, *frame_size)
            func(surf, rect, t)
        elif ride_name == "claw_machine":
            # Claw Machine benötigt x, y, w, h
            if 'extra_params' in config:
                x, y, w, h = config['extra_params']
                func(surf, x, y, w, h, t)
            else:
                func(surf, center_x, center_y, 58, 78, t)
        else:
            # Standard: (surf, cx, cy, t)
            func(surf, center_x, center_y, t)
        
        frames.append(surf)
    
    # Speichern als Einzelbilder oder Sprite-Sheet
    if sheet_mode:
        # Sprite-Sheet: Alle Frames in einem Bild
        sheet_width = frame_size[0] * len(frames)
        sheet_height = frame_size[1]
        sheet = pygame.Surface((sheet_width, sheet_height), pygame.SRCALPHA if use_alpha else 0)
        sheet.fill((0, 0, 0, 0) if use_alpha else (0, 0, 0))
        
        for i, frame in enumerate(frames):
            sheet.blit(frame, (i * frame_size[0], 0))
        
        filename = os.path.join(output_dir, f"{ride_name}_sheet_{num_frames}f.png")
        if not dry_run:
            pygame.image.save(sheet, filename)
        if verbose:
            print(f"    → Sprite-Sheet gespeichert: {filename}")
        
        # Metadaten speichern
        meta = {
            "ride": ride_name,
            "frames": num_frames,
            "frame_width": frame_size[0],
            "frame_height": frame_size[1],
            "sheet_width": sheet_width,
            "sheet_height": sheet_height,
            "type": "sheet"
        }
        _save_meta(output_dir, ride_name, meta, dry_run, verbose)
    else:
        # Einzelbilder
        for i, frame in enumerate(frames):
            filename = os.path.join(output_dir, f"{ride_name}_frame_{i:03d}.png")
            if not dry_run:
                pygame.image.save(frame, filename)
            if verbose:
                print(f"    → Frame {i:03d} gespeichert: {filename}")
        
        # Metadaten speichern
        meta = {
            "ride": ride_name,
            "frames": num_frames,
            "frame_width": frame_size[0],
            "frame_height": frame_size[1],
            "type": "frames"
        }
        _save_meta(output_dir, ride_name, meta, dry_run, verbose)
    
    return len(frames)


def _save_meta(output_dir, ride_name, meta, dry_run, verbose):
    """Speichere Metadaten als JSON-Datei."""
    import json
    filename = os.path.join(output_dir, f"{ride_name}_meta.json")
    
    # Füge speed aus RIDE_CONFIG hinzu, falls vorhanden
    if ride_name in RIDE_CONFIG and 'speed' in RIDE_CONFIG[ride_name]:
        meta['speed'] = RIDE_CONFIG[ride_name]['speed']
    
    if not dry_run:
        with open(filename, 'w') as f:
            json.dump(meta, f, indent=2)
    if verbose:
        print(f"    → Metadaten gespeichert: {filename}")


def list_rides():
    """Liste alle verfügbaren Fahrgeschäfte auf."""
    print("\nVerfügbare Fahrgeschäfte:")
    print("-" * 50)
    for name, config in RIDE_CONFIG.items():
        print(f"  {name:20s} - {config['description']}")
    print("-" * 50)
    print(f"  alle                   - Alle {len(RIDE_CONFIG)} Fahrgeschäfte rendern")
    print()


def main():
    """Hauptfunktion."""
    args = parse_args()
    
    # Liste anzeigen und beenden
    if args.list:
        list_rides()
        return 0
    
    # Pygame initialisieren (nur fürs Rendern, kein Fenster)
    pygame.init()
    pygame.display.set_mode((1, 1))  # Minimaler Modus
    
    print(f"Amusement Park Sprite Renderer")
    print(f"===============================")
    print()
    
    # Ausgabeverzeichnis vorbereiten
    output_dir = args.output
    ensure_output_dir(output_dir, args.dry_run)
    
    if args.verbose:
        print(f"Ausgabeverzeichnis: {output_dir}")
        print(f"Frames pro Animation: {args.frames}")
        print(f"Sprite-Größe: {args.size}x{args.size}")
        print(f"Sprite-Sheet-Modus: {args.sheet}")
        print(f"Transparenz: {args.transparent}")
        print(f"Dry-Run: {args.dry_run}")
        print()
    
    # Bestimme welche Fahrgeschäfte gerendert werden sollen
    if args.ride == "alle":
        rides_to_render = list(RIDE_CONFIG.keys())
    else:
        rides_to_render = [args.ride]
    
    total_frames = 0
    for ride in rides_to_render:
        count = render_single_ride(
            ride, output_dir,
            num_frames=args.frames,
            size=args.size,
            sheet_mode=args.sheet,
            transparent=args.transparent,
            dry_run=args.dry_run,
            verbose=args.verbose
        )
        total_frames += count
    
    print()
    if args.dry_run:
        print(f"[DRY RUN] Würde {total_frames} Frames für {len(rides_to_render)} Fahrgeschäft(e) generieren")
    else:
        print(f"✓ Erfolgreich {total_frames} Frames für {len(rides_to_render)} Fahrgeschäft(e) gerendert")
        print(f"  Gespeichert in: {os.path.abspath(output_dir)}")
    
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
