"""Prozedurale Sprite-Generatoren (Autos, Fußgänger, Gebäude)."""
import math
import random
import pygame

from game2d.config import (
    SKIN, COP_BLUE, COP_DARK,
    WALL1, WALL2, ROOF1, ROOF2,
    WIN, WIN_LIT, DOOR,
)


# =============================================================================
# SPRITE CACHES - Verhindert duplicate Generierung identischer Sprites
# =============================================================================

# Cache für Ped-Frames: (shirt, skin, hair, is_cop, cop_kind, gender, hair_style, back) -> [4 frames]
_ped_frames_cache: dict = {}

# Cache für Swim-Frames: (shirt, skin, hair, is_cop, cop_kind, gender, hair_style) -> [4 frames]
_swim_frames_cache: dict = {}

# Cache für Car-Sprites: (body_col, w, h, kind) -> Surface
_car_sprite_cache: dict = {}

# Cache für Cop-Car-Sprites: (kind, w, h) -> Surface
_cop_car_sprite_cache: dict = {}

# Cache für Gebäude: (w_cells, h_cells, seed, kind) -> Surface
_building_cache: dict = {}

# Cache für Rocket-Sprite
_rocket_sprite: pygame.Surface = None


def get_rocket_sprite() -> pygame.Surface:
    """Gibt das gecachte Rocket-Sprite zurueck oder erstellt es neu."""
    global _rocket_sprite
    if _rocket_sprite is None:
        _rocket_sprite = pygame.Surface((18, 8), pygame.SRCALPHA)
        pygame.draw.ellipse(_rocket_sprite, (255, 140, 30), (0, 0, 18, 8))
        pygame.draw.ellipse(_rocket_sprite, (255, 240, 100), (0, 1, 10, 6))
    return _rocket_sprite


def _shade(col, delta):
    return tuple(max(0, min(255, c + delta)) for c in col)


def clear_sprite_caches():
    """Clears all sprite caches. Call on game reset or resolution change."""
    _ped_frames_cache.clear()
    _swim_frames_cache.clear()
    _car_sprite_cache.clear()
    _cop_car_sprite_cache.clear()
    _building_cache.clear()


def _draw_car_shadow(surf, w, h, inset_x=6, inset_y=9):
    pygame.draw.ellipse(
        surf,
        (0, 0, 0, 70),
        (inset_x, inset_y, w - inset_x * 2, h - inset_y * 2),
    )


def _draw_car_wheels(surf, w, h, front_y=14, rear_y=None, wheel_w=4, wheel_h=14):
    rear_y = h - front_y - wheel_h if rear_y is None else rear_y
    for x in (0, w - wheel_w):
        pygame.draw.rect(surf, (18, 18, 18), (x, front_y, wheel_w, wheel_h), border_radius=2)
        pygame.draw.rect(surf, (18, 18, 18), (x, rear_y, wheel_w, wheel_h), border_radius=2)


def _draw_car_lights(surf, w, h, front_w=8, rear_w=8):
    pygame.draw.rect(surf, (255, 250, 200), (5, 6, front_w, 5), border_radius=2)
    pygame.draw.rect(surf, (255, 250, 200), (w - 5 - front_w, 6, front_w, 5), border_radius=2)
    pygame.draw.rect(surf, (200, 30, 30), (5, h - 10, rear_w, 5), border_radius=2)
    pygame.draw.rect(surf, (200, 30, 30), (w - 5 - rear_w, h - 10, rear_w, 5), border_radius=2)


def _draw_sedan_sprite(body_col, w, h):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    _draw_car_shadow(s, w, h)
    pygame.draw.rect(s, body_col, (2, 4, w - 4, h - 8), border_radius=8)
    pygame.draw.rect(s, _shade(body_col, 35), (4, 6, w - 8, 4), border_radius=4)
    pygame.draw.polygon(s, (60, 80, 100), [(6, 16), (w - 6, 16), (w - 10, 30), (10, 30)])
    pygame.draw.polygon(s, (130, 180, 220), [(8, 17), (w - 8, 17), (w - 12, 28), (12, 28)])
    pygame.draw.polygon(s, (60, 80, 100), [(8, h - 22), (w - 8, h - 22), (w - 12, h - 12), (12, h - 12)])
    pygame.draw.polygon(s, (130, 180, 220), [(10, h - 21), (w - 10, h - 21), (w - 13, h - 13), (13, h - 13)])
    pygame.draw.rect(s, _shade(body_col, -25), (10, 30, w - 20, h - 60))
    pygame.draw.line(s, (0,0,0,180), (4, h//2), (w-4, h//2), 1)
    _draw_car_lights(s, w, h)
    _draw_car_wheels(s, w, h)
    return s


def _draw_limo_sprite(body_col, w, h):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    _draw_car_shadow(s, w, h, inset_x=5, inset_y=10)
    pygame.draw.rect(s, body_col, (2, 4, w - 4, h - 8), border_radius=7)
    pygame.draw.rect(s, _shade(body_col, 30), (5, 7, w - 10, 5), border_radius=3)
    pygame.draw.rect(s, _shade(body_col, -25), (7, 23, w - 14, h - 47), border_radius=5)
    pygame.draw.polygon(s, (70, 88, 108), [(8, 16), (w - 8, 16), (w - 11, 28), (11, 28)])
    pygame.draw.polygon(s, (150, 195, 225), [(10, 17), (w - 10, 17), (w - 13, 26), (13, 26)])
    pygame.draw.polygon(s, (65, 78, 92), [(8, h - 25), (w - 8, h - 25), (w - 11, h - 13), (11, h - 13)])
    pygame.draw.polygon(s, (135, 175, 205), [(10, h - 24), (w - 10, h - 24), (w - 13, h - 15), (13, h - 15)])
    for y in range(36, h - 37, 18):
        pygame.draw.rect(s, (118, 165, 196), (8, y, 8, 10), border_radius=2)
        pygame.draw.rect(s, (118, 165, 196), (w - 16, y, 8, 10), border_radius=2)
    pygame.draw.line(s, _shade(body_col, 55), (6, h // 2), (w - 6, h // 2), 1)
    _draw_car_lights(s, w, h, front_w=7, rear_w=7)
    _draw_car_wheels(s, w, h, front_y=17, rear_y=h - 31, wheel_h=16)
    return s


def _draw_sport_sprite(body_col, w, h):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    _draw_car_shadow(s, w, h, inset_x=4, inset_y=6)

    # Fastback-Coupe Karosserie: spitze Nase, breite Kotflügel, abfallendes Heck
    pygame.draw.polygon(s, body_col, [
        (w // 2, 2),    (w - 7, 10),   (w - 2, 24),
        (w - 3, h - 16), (w // 2, h - 3), (3, h - 16),
        (2, 24),         (7, 10),
    ])

    # Motorhaube mit hellem Reflex
    pygame.draw.polygon(s, _shade(body_col, 40), [
        (w // 2, 4), (w - 9, 12), (w - 11, 22), (11, 22), (9, 12)
    ])
    # Mittlere Haubenkante (Sportwagen-Detail)
    pygame.draw.polygon(s, _shade(body_col, 58), [
        (w // 2 - 2, 4), (w // 2 + 2, 4), (w // 2 + 3, 22), (w // 2 - 3, 22)
    ])

    # Frontscheibe (breit, stark geneigt)
    pygame.draw.polygon(s, (48, 68, 90), [
        (8, 23), (w - 8, 23), (w - 12, 40), (12, 40)
    ])
    pygame.draw.polygon(s, (105, 175, 220), [
        (10, 24), (w - 10, 24), (w - 14, 38), (14, 38)
    ])

    # Dach / Kabine (niedrig, dunkel — Sportwagenoptik)
    pygame.draw.rect(s, _shade(body_col, -44), (12, 41, w - 24, 11), border_radius=3)

    # Heckscheibe (Fastback-Neigung)
    pygame.draw.polygon(s, (48, 68, 90), [
        (11, 53), (w - 11, 53), (w - 9, 61), (9, 61)
    ])
    pygame.draw.polygon(s, (88, 148, 192), [
        (12, 54), (w - 12, 54), (w - 10, 60), (10, 60)
    ])

    # Seitliche Karosserie-Kante (Styling-Linie)
    pygame.draw.line(s, _shade(body_col, 26), (4, 28), (4, h - 18), 1)
    pygame.draw.line(s, _shade(body_col, 26), (w - 4, 28), (w - 4, h - 18), 1)

    # Heck-Diffusor
    pygame.draw.polygon(s, _shade(body_col, -50), [
        (7, h - 14), (w - 7, h - 14), (w - 4, h - 5), (4, h - 5)
    ])

    # LED-Scheinwerfer (schmal, scharf)
    pygame.draw.rect(s, (255, 252, 195), (5, 7, 9, 3), border_radius=1)
    pygame.draw.rect(s, (255, 252, 195), (w - 14, 7, 9, 3), border_radius=1)
    pygame.draw.line(s, (210, 228, 255), (5, 11), (13, 11), 1)
    pygame.draw.line(s, (210, 228, 255), (w - 13, 11), (w - 5, 11), 1)

    # Breite Rücklichter
    pygame.draw.rect(s, (220, 22, 22), (5, h - 8, 11, 4), border_radius=1)
    pygame.draw.rect(s, (220, 22, 22), (w - 16, h - 8, 11, 4), border_radius=1)
    pygame.draw.line(s, (255, 95, 95), (6, h - 7), (14, h - 7), 1)
    pygame.draw.line(s, (255, 95, 95), (w - 15, h - 7), (w - 7, h - 7), 1)

    _draw_car_wheels(s, w, h, front_y=10, rear_y=h - 26, wheel_h=14)
    return s


def _draw_lamborghini_sprite(body_col, w, h):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    _draw_car_shadow(s, w, h, inset_x=3, inset_y=6)

    # Ultra-eckige Supercar-Karosserie (Huracán/Aventador-Stil)
    pygame.draw.polygon(s, body_col, [
        (w // 2, 3),      (w - 5, 8),    (w - 2, 20),
        (w - 2, h - 24),  (w - 6, h - 6), (w // 2, h - 4),
        (6, h - 6),       (2, h - 24),   (2, 20),
        (5, 8),
    ])

    # Frontspoiler / Splitter (aggressiv, flach)
    pygame.draw.polygon(s, (20, 20, 23), [
        (w // 2, 2), (w - 6, 7), (w - 8, 13), (8, 13), (6, 7)
    ])

    # Motorhaube mit starker Mittelkante
    pygame.draw.polygon(s, _shade(body_col, 50), [
        (w // 2, 5), (w - 9, 10), (w - 10, 20), (10, 20), (9, 10)
    ])
    pygame.draw.polygon(s, _shade(body_col, 68), [
        (w // 2 - 2, 5), (w // 2 + 2, 5), (w // 2 + 3, 20), (w // 2 - 3, 20)
    ])
    # Hauben-Lüftungsschlitze
    pygame.draw.line(s, _shade(body_col, -8), (w // 2 - 7, 14), (w // 2 - 5, 20), 1)
    pygame.draw.line(s, _shade(body_col, -8), (w // 2 + 7, 14), (w // 2 + 5, 20), 1)

    # Sehr eckige Frontscheibe
    pygame.draw.polygon(s, (30, 44, 60), [
        (8, 21), (w - 8, 21), (w - 14, 39), (14, 39)
    ])
    pygame.draw.polygon(s, (72, 145, 200), [
        (10, 22), (w - 10, 22), (w - 15, 37), (15, 37)
    ])
    pygame.draw.line(s, (18, 28, 40), (8, 21), (14, 39), 1)
    pygame.draw.line(s, (18, 28, 40), (w - 8, 21), (w - 14, 39), 1)

    # Cockpit (sehr schmal — Mittelmotor-Supercar)
    pygame.draw.rect(s, (10, 10, 14), (13, 40, w - 26, 13), border_radius=2)

    # SEITENLUFTEINLÄSSE (Lambo-Signaturmerkmal)
    pygame.draw.polygon(s, (14, 14, 17), [(2, 43), (9, 40), (9, 56), (2, 58)])
    pygame.draw.polygon(s, (38, 38, 44), [(3, 44), (8, 41), (8, 55), (3, 57)])
    pygame.draw.polygon(s, (14, 14, 17), [(w - 2, 43), (w - 9, 40), (w - 9, 56), (w - 2, 58)])
    pygame.draw.polygon(s, (38, 38, 44), [(w - 3, 44), (w - 8, 41), (w - 8, 55), (w - 3, 57)])

    # Heckdeckel / Motorabdeckung (eckig)
    pygame.draw.polygon(s, (30, 44, 60), [
        (14, 54), (w - 14, 54), (w - 11, 63), (11, 63)
    ])
    pygame.draw.polygon(s, (58, 125, 175), [
        (15, 55), (w - 15, 55), (w - 12, 62), (12, 62)
    ])

    # HECKSPOILER (fest, hochmontiert)
    wing_y = h - 22
    pygame.draw.rect(s, (18, 18, 21), (5, wing_y - 1, w - 10, 4))
    pygame.draw.rect(s, _shade(body_col, -10), (6, wing_y, w - 12, 2))
    pygame.draw.rect(s, (18, 18, 21), (8, wing_y - 5, 3, 5))
    pygame.draw.rect(s, (18, 18, 21), (w - 11, wing_y - 5, 3, 5))

    # Heck-Diffusor mit Lamellen
    pygame.draw.polygon(s, (14, 14, 17), [
        (8, h - 20), (w - 8, h - 20), (w - 6, h - 5), (6, h - 5)
    ])
    for xi in range(10, w - 10, 6):
        pygame.draw.line(s, (34, 34, 38), (xi, h - 19), (xi, h - 6), 1)

    # Eckige Scheinwerfer mit DRL-Slash (Huracán-Stil)
    pygame.draw.rect(s, (255, 252, 188), (6, 7, 11, 3), border_radius=1)
    pygame.draw.rect(s, (255, 252, 188), (w - 17, 7, 11, 3), border_radius=1)
    pygame.draw.line(s, (215, 232, 255), (7, 11), (14, 16), 1)
    pygame.draw.line(s, (215, 232, 255), (w - 7, 11), (w - 14, 16), 1)

    # DURCHGEHENDER Rücklichtstreifen (Aventador-Signatur)
    pygame.draw.rect(s, (215, 16, 16), (6, h - 9, w - 12, 4), border_radius=1)
    pygame.draw.line(s, (255, 72, 72), (7, h - 8), (w - 7, h - 8), 1)
    # Mittelunterbrechung mit Auspuffrohren
    pygame.draw.rect(s, (14, 14, 17), (w // 2 - 5, h - 10, 10, 5))
    pygame.draw.circle(s, (28, 28, 32), (w // 2 - 2, h - 8), 2)
    pygame.draw.circle(s, (28, 28, 32), (w // 2 + 2, h - 8), 2)

    _draw_car_wheels(s, w, h, front_y=9, rear_y=h - 29, wheel_h=18)
    return s


def _draw_mini_sprite(body_col, w, h):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    _draw_car_shadow(s, w, h, inset_x=4, inset_y=7)
    pygame.draw.rect(s, body_col, (2, 4, w - 4, h - 8), border_radius=9)
    pygame.draw.rect(s, _shade(body_col, 32), (5, 7, w - 10, 4), border_radius=3)
    pygame.draw.rect(s, (232, 236, 228), (7, 21, w - 14, 18), border_radius=5)
    pygame.draw.polygon(s, (130, 180, 215), [(8, 14), (w - 8, 14), (w - 10, 22), (10, 22)])
    pygame.draw.polygon(s, (105, 150, 188), [(8, h - 19), (w - 8, h - 19), (w - 11, h - 11), (11, h - 11)])
    pygame.draw.rect(s, _shade(body_col, -25), (9, 40, w - 18, h - 52), border_radius=4)
    pygame.draw.rect(s, (255, 250, 200), (5, 7, 6, 4), border_radius=2)
    pygame.draw.rect(s, (255, 250, 200), (w - 11, 7, 6, 4), border_radius=2)
    pygame.draw.rect(s, (200, 30, 30), (5, h - 9, 6, 4), border_radius=2)
    pygame.draw.rect(s, (200, 30, 30), (w - 11, h - 9, 6, 4), border_radius=2)
    _draw_car_wheels(s, w, h, front_y=11, rear_y=h - 23, wheel_h=12)
    return s


def _draw_semi_sprite(body_col, w, h):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    _draw_car_shadow(s, w, h, inset_x=5, inset_y=10)
    cab_h = max(38, int(h * 0.30))
    trailer_y = cab_h - 2
    pygame.draw.rect(s, (42, 42, 46), (4, trailer_y, w - 8, h - trailer_y - 8), border_radius=4)
    pygame.draw.rect(s, (222, 222, 214), (7, trailer_y + 4, w - 14, h - trailer_y - 16), border_radius=3)
    pygame.draw.rect(s, (188, 188, 180), (10, trailer_y + 10, w - 20, 7), border_radius=2)
    pygame.draw.line(s, (150, 150, 145), (w // 2, trailer_y + 7), (w // 2, h - 18), 1)
    pygame.draw.rect(s, body_col, (6, 6, w - 12, cab_h), border_radius=7)
    pygame.draw.rect(s, _shade(body_col, 28), (10, 10, w - 20, 8), border_radius=3)
    pygame.draw.polygon(s, (48, 66, 82), [(11, 20), (w - 11, 20), (w - 15, 35), (15, 35)])
    pygame.draw.polygon(s, (112, 174, 214), [(13, 21), (w - 13, 21), (w - 16, 33), (16, 33)])
    pygame.draw.rect(s, _shade(body_col, -24), (11, 39, w - 22, cab_h - 38), border_radius=4)
    for x in (0, w - 6):
        pygame.draw.rect(s, (18, 18, 18), (x, 23, 6, 16), border_radius=2)
        pygame.draw.rect(s, (18, 18, 18), (x, h - 44, 6, 17), border_radius=2)
        pygame.draw.rect(s, (18, 18, 18), (x, h - 24, 6, 17), border_radius=2)
    pygame.draw.rect(s, (255, 248, 200), (9, 8, 10, 5), border_radius=2)
    pygame.draw.rect(s, (255, 248, 200), (w - 19, 8, 10, 5), border_radius=2)
    pygame.draw.rect(s, (205, 35, 35), (9, h - 12, 9, 5), border_radius=2)
    pygame.draw.rect(s, (205, 35, 35), (w - 18, h - 12, 9, 5), border_radius=2)
    return s


def _draw_bus_sprite(body_col, w, h):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    _draw_car_shadow(s, w, h, inset_x=5, inset_y=10)
    _draw_car_wheels(s, w, h, front_y=17, rear_y=h - 35, wheel_w=5, wheel_h=18)
    pygame.draw.rect(s, (38, 38, 42), (4, 6, w - 8, h - 12), border_radius=7)
    pygame.draw.rect(s, body_col, (6, 8, w - 12, h - 16), border_radius=6)
    pygame.draw.rect(s, _shade(body_col, 26), (9, 12, w - 18, 9), border_radius=3)
    pygame.draw.polygon(s, (42, 58, 74), [(10, 24), (w - 10, 24), (w - 14, 40), (14, 40)])
    pygame.draw.polygon(s, (110, 178, 218), [(12, 25), (w - 12, 25), (w - 15, 38), (15, 38)])
    pygame.draw.rect(s, _shade(body_col, -18), (9, 48, w - 18, h - 73), border_radius=4)
    for y in range(53, h - 42, 18):
        pygame.draw.rect(s, (112, 176, 214), (11, y, 9, 11), border_radius=2)
        pygame.draw.rect(s, (112, 176, 214), (w - 20, y, 9, 11), border_radius=2)
    pygame.draw.rect(s, (36, 42, 48), (w // 2 - 11, h - 31, 22, 14), border_radius=3)
    pygame.draw.rect(s, (255, 248, 200), (8, 10, 9, 5), border_radius=2)
    pygame.draw.rect(s, (255, 248, 200), (w - 17, 10, 9, 5), border_radius=2)
    pygame.draw.rect(s, (205, 35, 35), (8, h - 13, 9, 5), border_radius=2)
    pygame.draw.rect(s, (205, 35, 35), (w - 17, h - 13, 9, 5), border_radius=2)
    return s


def make_car_sprite(body_col, w=None, h=None, kind="sedan"):
    """Generiert oder holt aus Cache ein Car-Sprite."""
    if kind == "lamborgini":
        kind = "lamborghini"
    kind = kind if kind in ("sedan", "limo", "sport", "lamborghini", "mini", "semi", "bus", "motorcycle") else "sedan"
    default_sizes = {
        "sedan": (46, 78),
        "limo": (50, 132),
        "sport": (44, 72),
        "lamborghini": (48, 76),
        "mini": (36, 58),
        "semi": (58, 150),
        "bus": (56, 136),
        "motorcycle": (24, 56),
    }
    default_w, default_h = default_sizes[kind]
    w = default_w if w is None else w
    h = default_h if h is None else h
    
    # Cache-Key: body_col kann ein Tuple sein, also direkt verwenden
    key = (body_col, w, h, kind)
    if key in _car_sprite_cache:
        return _car_sprite_cache[key]
    
    if kind == "limo":
        surf = _draw_limo_sprite(body_col, w, h)
    elif kind == "sport":
        surf = _draw_sport_sprite(body_col, w, h)
    elif kind == "lamborghini":
        surf = _draw_lamborghini_sprite(body_col, w, h)
    elif kind == "mini":
        surf = _draw_mini_sprite(body_col, w, h)
    elif kind == "semi":
        surf = _draw_semi_sprite(body_col, w, h)
    elif kind == "bus":
        surf = _draw_bus_sprite(body_col, w, h)
    elif kind == "motorcycle":
        surf = _draw_motorcycle_sprite(body_col, w, h)
    else:
        surf = _draw_sedan_sprite(body_col, w, h)
    
    _car_sprite_cache[key] = surf
    return surf


def _draw_motorcycle_sprite(body_col, w, h):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    cx = w // 2
    pygame.draw.ellipse(s, (0, 0, 0, 95), (cx - 8, h // 4, 16, h - h // 2))

    pygame.draw.rect(s, (16, 16, 18), (cx - 4, 4, 8, 14), border_radius=2)
    pygame.draw.rect(s, (52, 52, 56), (cx - 3, 6, 6, 10), border_radius=1)
    pygame.draw.line(s, (118, 118, 122), (cx, 7), (cx, 14), 1)

    pygame.draw.line(s, (60, 60, 64), (cx - 3, 14), (cx - 3, 19), 2)
    pygame.draw.line(s, (60, 60, 64), (cx + 3, 14), (cx + 3, 19), 2)

    pygame.draw.circle(s, (40, 38, 36), (cx, 4), 3)
    pygame.draw.circle(s, (250, 240, 180), (cx, 4), 2)
    pygame.draw.circle(s, (255, 255, 220), (cx - 1, 3), 1)

    pygame.draw.line(s, (28, 28, 30), (cx - 9, 14), (cx + 9, 14), 3)
    pygame.draw.circle(s, (22, 20, 22), (cx - 9, 14), 2)
    pygame.draw.circle(s, (22, 20, 22), (cx + 9, 14), 2)

    pygame.draw.rect(s, _shade(body_col, -32), (cx - 7, 18, 14, 19), border_radius=4)
    pygame.draw.rect(s, body_col, (cx - 6, 19, 12, 17), border_radius=3)
    pygame.draw.line(s, _shade(body_col, 55), (cx - 4, 21), (cx - 4, 32), 2)
    pygame.draw.line(s, _shade(body_col, -10), (cx + 4, 22), (cx + 4, 32), 1)

    pygame.draw.rect(s, (28, 26, 28), (cx - 6, 36, 12, 9), border_radius=2)
    pygame.draw.rect(s, (52, 48, 50), (cx - 5, 36, 10, 8), border_radius=2)

    pygame.draw.rect(s, (60, 58, 62), (cx + 5, 38, 4, 13), border_radius=1)
    pygame.draw.rect(s, (118, 116, 120), (cx + 6, 38, 2, 12), border_radius=1)

    pygame.draw.circle(s, (20, 20, 24), (cx, 28), 5)
    pygame.draw.circle(s, (38, 38, 42), (cx - 1, 27), 4)
    pygame.draw.rect(s, (140, 200, 230), (cx - 4, 25, 8, 4), border_radius=2)

    pygame.draw.line(s, (100, 30, 36), (cx - 5, 32), (cx - 9, 16), 4)
    pygame.draw.line(s, (100, 30, 36), (cx + 5, 32), (cx + 9, 16), 4)
    pygame.draw.line(s, (190, 50, 60), (cx - 5, 32), (cx - 9, 16), 2)
    pygame.draw.line(s, (190, 50, 60), (cx + 5, 32), (cx + 9, 16), 2)

    pygame.draw.rect(s, (32, 30, 34), (cx - 7, 31, 14, 12), border_radius=3)
    pygame.draw.rect(s, (190, 50, 60), (cx - 6, 32, 12, 10), border_radius=2)
    pygame.draw.line(s, (220, 80, 90), (cx, 33), (cx, 41), 1)

    pygame.draw.circle(s, (28, 26, 28), (cx - 9, 16), 2)
    pygame.draw.circle(s, (28, 26, 28), (cx + 9, 16), 2)

    pygame.draw.rect(s, (16, 16, 18), (cx - 5, h - 18, 10, 16), border_radius=2)
    pygame.draw.rect(s, (52, 52, 56), (cx - 4, h - 16, 8, 12), border_radius=1)
    pygame.draw.line(s, (118, 118, 122), (cx, h - 14), (cx, h - 6), 1)

    pygame.draw.rect(s, (180, 30, 30), (cx - 3, h - 5, 6, 3), border_radius=1)
    return s


_BLOCK_LETTERS = {
    "A": ("010", "101", "111", "101", "101"),
    "B": ("110", "101", "110", "101", "110"),
    "F": ("111", "100", "110", "100", "100"),
    "I": ("111", "010", "010", "010", "111"),
    "S": ("111", "100", "111", "001", "111"),
    "T": ("111", "010", "010", "010", "010"),
    "W": ("101", "101", "101", "111", "101"),
}


def _draw_block_text(surf, text, x, y, color, scale=2):
    cursor = x
    for ch in text:
        rows = _BLOCK_LETTERS.get(ch)
        if rows is None:
            cursor += scale * 2
            continue
        for ry, row in enumerate(rows):
            for rx, bit in enumerate(row):
                if bit == "1":
                    pygame.draw.rect(
                        surf,
                        color,
                        (cursor + rx * scale, y + ry * scale, scale, scale),
                    )
        cursor += (len(rows[0]) + 1) * scale


def _draw_vehicle_star(surf, cx, cy, radius, color):
    pts = []
    for i in range(10):
        r = radius if i % 2 == 0 else radius * 0.42
        a = -math.pi / 2 + i * math.pi / 5
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    pygame.draw.polygon(surf, color, pts)


def _draw_swat_bus_sprite(body_col, w, h):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    _draw_car_shadow(s, w, h, inset_x=5, inset_y=10)
    _draw_car_wheels(s, w, h, front_y=17, rear_y=h - 34, wheel_w=5, wheel_h=18)
    pygame.draw.rect(s, body_col, (4, 5, w - 8, h - 10), border_radius=6)
    pygame.draw.rect(s, _shade(body_col, 22), (7, 9, w - 14, 8), border_radius=3)
    pygame.draw.rect(s, _shade(body_col, -18), (8, 28, w - 16, h - 54), border_radius=4)
    pygame.draw.polygon(s, (38, 58, 78), [(10, 18), (w - 10, 18), (w - 14, 32), (14, 32)])
    pygame.draw.polygon(s, (98, 146, 172), [(12, 19), (w - 12, 19), (w - 15, 30), (15, 30)])
    for y in (43, 60):
        pygame.draw.rect(s, (82, 118, 142), (9, y, 8, 10), border_radius=2)
        pygame.draw.rect(s, (82, 118, 142), (w - 17, y, 8, 10), border_radius=2)
    pygame.draw.rect(s, (12, 16, 24), (12, h - 25, w - 24, 10), border_radius=3)
    _draw_block_text(s, "SWAT", w // 2 - 16, h // 2 - 5, (230, 235, 230), scale=2)
    pygame.draw.rect(s, (210, 35, 35), (w // 2 - 8, 33, 8, 4), border_radius=2)
    pygame.draw.rect(s, (40, 90, 230), (w // 2, 33, 8, 4), border_radius=2)
    pygame.draw.rect(s, (255, 245, 190), (8, 8, 9, 5), border_radius=2)
    pygame.draw.rect(s, (255, 245, 190), (w - 17, 8, 9, 5), border_radius=2)
    pygame.draw.rect(s, (205, 35, 35), (8, h - 12, 9, 5), border_radius=2)
    pygame.draw.rect(s, (205, 35, 35), (w - 17, h - 12, 9, 5), border_radius=2)
    return s


def _draw_military_truck_sprite(body_col, w, h):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    _draw_car_shadow(s, w, h, inset_x=5, inset_y=10)
    _draw_car_wheels(s, w, h, front_y=15, rear_y=h - 34, wheel_w=6, wheel_h=18)
    pygame.draw.rect(s, (52, 64, 42), (5, 5, w - 10, h - 10), border_radius=5)
    pygame.draw.rect(s, body_col, (7, 8, w - 14, h - 16), border_radius=4)
    pygame.draw.rect(s, _shade(body_col, 20), (9, 13, w - 18, 19), border_radius=4)
    pygame.draw.polygon(s, (42, 58, 48), [(10, 18), (w - 10, 18), (w - 14, 34), (14, 34)])
    pygame.draw.polygon(s, (94, 132, 112), [(12, 19), (w - 12, 19), (w - 15, 31), (15, 31)])
    pygame.draw.rect(s, _shade(body_col, -22), (9, 41, w - 18, h - 61), border_radius=5)
    for patch in ((13, 46, 14, 10), (34, 51, 13, 12), (18, 69, 16, 9), (38, 76, 10, 8)):
        pygame.draw.rect(s, (48, 72, 42), patch, border_radius=3)
    _draw_vehicle_star(s, w // 2, h // 2 + 6, 10, (230, 230, 205))
    pygame.draw.rect(s, (210, 35, 35), (8, h - 12, 9, 5), border_radius=2)
    pygame.draw.rect(s, (210, 35, 35), (w - 17, h - 12, 9, 5), border_radius=2)
    pygame.draw.rect(s, (255, 245, 190), (8, 8, 9, 5), border_radius=2)
    pygame.draw.rect(s, (255, 245, 190), (w - 17, 8, 9, 5), border_radius=2)
    return s


def make_cop_car_sprite(kind="cop", w=None, h=None):
    """Generiert oder holt aus Cache ein Cop-Car-Sprite."""
    kind = kind if kind in ("cop", "fbi", "swat", "military") else "cop"
    
    # Cache-Key
    key = (kind, w, h)
    if key in _cop_car_sprite_cache:
        return _cop_car_sprite_cache[key]
    
    if kind == "swat":
        surf = _draw_swat_bus_sprite((18, 26, 42), 58 if w is None else w, 104 if h is None else h)
    elif kind == "military":
        surf = _draw_military_truck_sprite((78, 96, 56), 60 if w is None else w, 102 if h is None else h)
    elif kind == "fbi":
        s = make_car_sprite((24, 24, 28), 48 if w is None else w, 80 if h is None else h)
        w_out, h_out = s.get_size()
        pygame.draw.rect(s, (230, 230, 220), (5, h_out // 2 - 13, w_out - 10, 26), border_radius=3)
        pygame.draw.rect(s, (24, 24, 28), (8, h_out // 2 - 9, w_out - 16, 18), border_radius=2)
        _draw_block_text(s, "FBI", w_out // 2 - 12, h_out // 2 - 5, (245, 245, 235), scale=2)
        pygame.draw.rect(s, (40, 40, 45), (10, 33, w_out - 20, 6), border_radius=2)
        pygame.draw.rect(s, (210, 35, 35), (12, 34, (w_out - 24) // 2, 4), border_radius=2)
        pygame.draw.rect(s, (40, 85, 220), (12 + (w_out - 24) // 2, 34, (w_out - 24) // 2, 4), border_radius=2)
        surf = s
    else:
        s = make_car_sprite((245, 245, 250), 46 if w is None else w, 78 if h is None else h)
        w_out, h_out = s.get_size()
        pygame.draw.rect(s, (20,20,25), (2, h_out//2 - 14, w_out-4, 28))
        pygame.draw.rect(s, (245,245,250), (2, h_out//2 - 4, w_out-4, 8))
        pygame.draw.rect(s, (40,40,45), (10, 32, w_out-20, 6))
        pygame.draw.rect(s, (220,40,40), (12, 33, (w_out-24)//2, 4))
        pygame.draw.rect(s, (40,80,220), (12+(w_out-24)//2, 33, (w_out-24)//2, 4))
        surf = s
    
    _cop_car_sprite_cache[key] = surf
    return surf


def _draw_hair(surf, cx, head_y, hair, hair_style="short", swim=False):
    if hair_style == "bald":
        pygame.draw.arc(surf, _shade(hair, 45), (cx - 3, head_y - 3, 6, 5), math.radians(205), math.radians(335), 1)
        return
    if swim:
        if hair_style in ("bob", "long", "ponytail"):
            pygame.draw.ellipse(surf, _shade(hair, -12), (cx - 6, head_y - 5, 12, 8))
            if hair_style == "ponytail":
                pygame.draw.ellipse(surf, hair, (cx + 4, head_y - 2, 5, 5))
        elif hair_style == "mohawk":
            pygame.draw.polygon(surf, hair, [(cx, head_y - 9), (cx + 2, head_y - 2), (cx - 2, head_y - 2)])
        else:
            pygame.draw.circle(surf, hair, (cx, head_y), 4)
        return
    if hair_style == "bob":
        pygame.draw.ellipse(surf, _shade(hair, -14), (cx - 6, head_y - 4, 12, 10))
        pygame.draw.rect(surf, hair, (cx - 6, head_y - 1, 12, 6))
        pygame.draw.line(surf, _shade(hair, 28), (cx - 4, head_y - 3), (cx + 4, head_y - 3), 1)
    elif hair_style == "long":
        pygame.draw.ellipse(surf, _shade(hair, -14), (cx - 6, head_y - 5, 12, 11))
        pygame.draw.rect(surf, hair, (cx - 6, head_y - 1, 3, 10))
        pygame.draw.rect(surf, hair, (cx + 3, head_y - 1, 3, 10))
        pygame.draw.rect(surf, _shade(hair, -25), (cx - 5, head_y + 6, 10, 3))
    elif hair_style == "ponytail":
        pygame.draw.circle(surf, hair, (cx, head_y), 5)
        pygame.draw.ellipse(surf, _shade(hair, -8), (cx + 3, head_y - 2, 7, 8))
        pygame.draw.circle(surf, _shade(hair, 35), (cx + 4, head_y - 1), 1)
    elif hair_style == "mohawk":
        pygame.draw.circle(surf, _shade(hair, -45), (cx, head_y), 3)
        pygame.draw.polygon(surf, hair, [(cx, head_y - 10), (cx + 3, head_y - 2), (cx - 3, head_y - 2)])
        pygame.draw.line(surf, _shade(hair, 45), (cx, head_y - 9), (cx, head_y - 3), 1)
    elif hair_style == "buzz":
        pygame.draw.circle(surf, _shade(hair, -35), (cx, head_y), 4)
        pygame.draw.circle(surf, _shade(hair, 20), (cx - 1, head_y - 2), 1)
    elif hair_style == "parted":
        pygame.draw.ellipse(surf, hair, (cx - 5, head_y - 4, 10, 8))
        pygame.draw.polygon(surf, _shade(hair, -18), [(cx - 1, head_y - 4), (cx + 5, head_y - 2), (cx + 4, head_y + 1), (cx, head_y)])
        pygame.draw.line(surf, _shade(hair, 55), (cx - 1, head_y - 4), (cx - 4, head_y), 1)
    else:
        pygame.draw.ellipse(surf, hair, (cx - 5, head_y - 4, 10, 8))
        pygame.draw.rect(surf, _shade(hair, -12), (cx - 4, head_y - 4, 8, 2))


def _draw_ped_frame(shirt_col, skin, hair, phase, is_cop=False, cop_kind="cop", gender="m", hair_style="short", back=False):
    s = pygame.Surface((20, 24), pygame.SRCALPHA)
    cx, cy = 10, 12
    pants = (40, 40, 80)
    boot  = (20, 20, 20)
    if is_cop:
        if cop_kind == "fbi":
            pants = (22, 22, 26)
        elif cop_kind == "swat":
            pants = (12, 18, 30)
        elif cop_kind == "military":
            pants = (58, 76, 42)
    pygame.draw.ellipse(s, (0, 0, 0, 90), (3, cy + 3, 14, 7))
    leg_l_y = cy + 3 - phase * 3
    leg_r_y = cy + 3 + phase * 3
    pygame.draw.rect(s, pants, (cx - 3, leg_l_y, 2, 5))
    pygame.draw.rect(s, pants, (cx + 1, leg_r_y, 2, 5))
    pygame.draw.rect(s, boot,  (cx - 3, leg_l_y + 5, 2, 2))
    pygame.draw.rect(s, boot,  (cx + 1, leg_r_y + 5, 2, 2))
    torso = (cx - 4, cy - 3, 8, 9) if gender == "w" and not is_cop else (cx - 5, cy - 3, 10, 9)
    pygame.draw.ellipse(s, shirt_col, torso)
    hl = tuple(min(255, c + 30) for c in shirt_col)
    if back:
        pygame.draw.ellipse(s, _shade(shirt_col, -25), (torso[0] + 1, cy + 2, torso[2] - 2, 3))
    else:
        pygame.draw.ellipse(s, hl, (torso[0] + 1, cy - 2, torso[2] - 2, 3))
    if gender == "w" and not is_cop:
        pygame.draw.polygon(s, _shade(shirt_col, -24), [(cx - 5, cy + 4), (cx + 5, cy + 4), (cx + 3, cy + 8), (cx - 3, cy + 8)])
    arm_l_y = cy + phase * 2
    arm_r_y = cy - phase * 2
    pygame.draw.rect(s, shirt_col, (cx - 7, arm_l_y, 2, 4))
    pygame.draw.rect(s, shirt_col, (cx + 5, arm_r_y, 2, 4))
    pygame.draw.rect(s, skin,      (cx - 7, arm_l_y + 4, 2, 2))
    pygame.draw.rect(s, skin,      (cx + 5, arm_r_y + 4, 2, 2))
    head_y = cy - 5
    _draw_hair(s, cx, head_y, hair, hair_style)
    if back:
        pygame.draw.circle(s, hair if hair_style != "bald" else _shade(skin, -18), (cx, head_y - 1), 3)
    else:
        pygame.draw.circle(s, skin, (cx, head_y - 1), 3)
    if is_cop and cop_kind == "fbi":
        pygame.draw.circle(s, (18, 18, 20), (cx, head_y), 4)
        pygame.draw.rect(s, (235, 235, 225), (cx - 2, cy - 3, 4, 7))
        pygame.draw.line(s, (40, 70, 160), (cx, cy - 2), (cx, cy + 3), 1)
        pygame.draw.line(s, (20, 20, 24), (cx - 3, head_y - 1), (cx + 3, head_y - 1), 1)
        pygame.draw.rect(s, (230, 200, 60), (cx + 3, cy - 1, 2, 2))
    elif is_cop and cop_kind == "swat":
        pygame.draw.circle(s, (8, 12, 20), (cx, head_y), 5)
        pygame.draw.rect(s, (25, 35, 50), (cx - 4, head_y - 4, 8, 3))
        pygame.draw.rect(s, (90, 130, 150), (cx - 3, head_y - 1, 6, 2))
        pygame.draw.rect(s, (8, 12, 18), (cx - 4, cy - 3, 8, 8), 1)
    elif is_cop and cop_kind == "military":
        pygame.draw.circle(s, (52, 70, 38), (cx, head_y), 5)
        pygame.draw.rect(s, (42, 58, 34), (cx - 5, head_y - 3, 10, 3))
        pygame.draw.rect(s, (218, 214, 170), (cx - 1, cy - 1, 2, 2))
        pygame.draw.rect(s, (40, 58, 34), (cx - 4, cy - 3, 8, 8), 1)
    elif is_cop:
        pygame.draw.circle(s, COP_DARK, (cx, head_y), 4)
        pygame.draw.rect(s, COP_DARK, (cx - 4, head_y - 4, 8, 3))
        pygame.draw.rect(s, (230, 200, 60), (cx - 1, head_y - 1, 2, 2))
    return s


def make_ped_frames(shirt_col, skin=SKIN, hair=(60,40,30), is_cop=False, cop_kind="cop", gender="m", hair_style="short", back=False):
    """Generiert oder holt aus Cache 4 Ped-Animationsframes.
    
    Caching reduziert Startzeit und GC-Pressure deutlich.
    """
    # Erstelle hashbaren Cache-Key
    key = (shirt_col, skin, hair, is_cop, cop_kind, gender, hair_style, back)
    
    if key in _ped_frames_cache:
        return _ped_frames_cache[key]
    
    frames = [
        _draw_ped_frame(shirt_col, skin, hair, 0, is_cop, cop_kind, gender, hair_style, back),
        _draw_ped_frame(shirt_col, skin, hair, 1, is_cop, cop_kind, gender, hair_style, back),
        _draw_ped_frame(shirt_col, skin, hair, 0, is_cop, cop_kind, gender, hair_style, back),
        _draw_ped_frame(shirt_col, skin, hair, -1, is_cop, cop_kind, gender, hair_style, back),
    ]
    _ped_frames_cache[key] = frames
    return frames


def _draw_swim_frame(shirt_col, skin, hair, phase, is_cop=False, cop_kind="cop", gender="m", hair_style="short"):
    s = pygame.Surface((20, 24), pygame.SRCALPHA)
    cx, water_y = 10, 14
    wave_col = (72, 152, 208, 170)
    foam_col = (210, 240, 250, 180)
    torso_y = water_y - 4 + phase
    arm_span = 5 + abs(phase)

    pygame.draw.ellipse(s, (0, 0, 0, 60), (4, water_y + 1, 12, 5))
    pygame.draw.ellipse(s, shirt_col, (cx - 4, torso_y, 8, 5))
    hl = tuple(min(255, c + 30) for c in shirt_col)
    pygame.draw.ellipse(s, hl, (cx - 3, torso_y, 6, 2))
    pygame.draw.line(s, shirt_col, (cx - arm_span, torso_y + 2), (cx - 2, torso_y + 1), 2)
    pygame.draw.line(s, shirt_col, (cx + 2, torso_y + 1), (cx + arm_span, torso_y + 2), 2)
    pygame.draw.circle(s, skin, (cx, torso_y - 3), 3)
    if is_cop:
        head_col = COP_DARK
        if cop_kind == "fbi":
            head_col = (18, 18, 20)
        elif cop_kind == "swat":
            head_col = (8, 12, 20)
        elif cop_kind == "military":
            head_col = (52, 70, 38)
        pygame.draw.circle(s, head_col, (cx, torso_y - 4), 4)
        pygame.draw.rect(s, head_col, (cx - 4, torso_y - 7, 8, 2))
        badge_col = (90, 130, 150) if cop_kind == "swat" else (230, 200, 60)
        pygame.draw.rect(s, badge_col, (cx - 1, torso_y - 4, 2, 2))
    else:
        _draw_hair(s, cx, torso_y - 4, hair, hair_style, swim=True)

    for wx in range(3, 18, 4):
        pygame.draw.arc(s, wave_col, (wx - 3, water_y - 1, 7, 5), 3.2, 6.1, 2)
    pygame.draw.arc(s, foam_col, (cx - 8, water_y - 2, 16, 5), 3.35, 5.95, 1)
    return s


def make_swim_frames(shirt_col, skin=SKIN, hair=(60,40,30), is_cop=False, cop_kind="cop", gender="m", hair_style="short"):
    """Generiert oder holt aus Cache 4 Swim-Animationsframes."""
    key = (shirt_col, skin, hair, is_cop, cop_kind, gender, hair_style)
    
    if key in _swim_frames_cache:
        return _swim_frames_cache[key]
    
    frames = [
        _draw_swim_frame(shirt_col, skin, hair, 0, is_cop, cop_kind, gender, hair_style),
        _draw_swim_frame(shirt_col, skin, hair, 1, is_cop, cop_kind, gender, hair_style),
        _draw_swim_frame(shirt_col, skin, hair, 0, is_cop, cop_kind, gender, hair_style),
        _draw_swim_frame(shirt_col, skin, hair, -1, is_cop, cop_kind, gender, hair_style),
    ]
    _swim_frames_cache[key] = frames
    return frames


def make_ped_sprite(shirt_col, skin=SKIN, hair=(60,40,30)):
    return make_ped_frames(shirt_col, skin, hair)[0]


def make_cop_sprite():
    return make_ped_frames(COP_BLUE, is_cop=True)[0]


def make_duck_sprite(kind, swim_phase=0, facing=1, paddle_phase=0.0):
    scale = {'drake': 1.0, 'hen': 0.94, 'duckling': 0.48}[kind]
    w = max(32, int(52 * scale))
    h = max(16, int(30 * scale))
    surf = pygame.Surface((w, h), pygame.SRCALPHA)

    if kind == 'drake':
        head_col = (44, 118, 82)
        head_hi = (72, 156, 114)
        neck_ring = (238, 242, 226)
        bill_col = (226, 198, 78)
        foot_col = (220, 126, 42)
        body_col = (190, 198, 198)
        wing_col = (128, 136, 142)
        chest_col = (118, 72, 50)
        belly_col = (218, 220, 210)
        tail_col = (32, 36, 38)
        eye_col = (20, 22, 18)
    elif kind == 'hen':
        head_col = (122, 92, 58)
        head_hi = (150, 118, 80)
        neck_ring = None
        bill_col = (212, 142, 58)
        foot_col = (220, 126, 42)
        body_col = (148, 112, 72)
        wing_col = (100, 76, 48)
        chest_col = (166, 128, 84)
        belly_col = (184, 146, 94)
        tail_col = (88, 68, 46)
        eye_col = (26, 20, 14)
    else:
        head_col = (178, 136, 64)
        head_hi = (208, 184, 98)
        neck_ring = None
        bill_col = (206, 142, 66)
        foot_col = (222, 132, 48)
        body_col = (214, 184, 92)
        wing_col = (160, 120, 58)
        chest_col = (228, 204, 122)
        belly_col = (236, 214, 136)
        tail_col = (124, 94, 48)
        eye_col = (28, 22, 16)

    def sc(value):
        return int(round(value * scale))

    bob = swim_phase * max(1, sc(1.2))
    water_y = h - sc(7)

    body = pygame.Rect(sc(6), sc(11) + bob, sc(29), sc(14))
    rump = pygame.Rect(sc(5), sc(12) + bob, sc(16), sc(13))
    chest = pygame.Rect(sc(23), sc(11) + bob, sc(12), sc(13))
    belly = pygame.Rect(sc(10), sc(17) + bob, sc(22), sc(8))
    wing = pygame.Rect(sc(13), sc(13) + bob, sc(16), sc(8))
    neck_y = sc(6 if kind == 'drake' else 7) + bob
    head_y = sc(2 if kind == 'drake' else 4) + bob
    neck = pygame.Rect(sc(28), neck_y, sc(7), sc(12))
    head = pygame.Rect(sc(30), head_y, sc(11), sc(10))

    tail_pts = [
        (body.left + sc(1), body.top + sc(2)),
        (body.left - sc(7), body.top + sc(5)),
        (body.left + sc(1), body.top + sc(9)),
    ]
    bill_pts = [
        (head.right - sc(1), head.centery - sc(2)),
        (head.right + sc(5 if kind == 'duckling' else 6), head.centery),
        (head.right - sc(1), head.centery + sc(2)),
    ]

    pygame.draw.polygon(surf, tail_col, tail_pts)
    if kind != 'duckling':
        foot_y = water_y + sc(1) + bob // 2
        foot_stride = math.sin(paddle_phase)
        rear_foot_x = body.left + sc(5) - int(foot_stride * sc(2))
        front_foot_x = body.left + sc(12) + int(foot_stride * sc(2))
        rear_foot_w = sc(7) + int(max(0, foot_stride) * sc(2))
        front_foot_w = sc(7) + int(max(0, -foot_stride) * sc(2))
        pygame.draw.ellipse(surf, foot_col, (rear_foot_x, foot_y, rear_foot_w, max(2, sc(3))))
        pygame.draw.ellipse(surf, foot_col, (front_foot_x, foot_y - sc(1), front_foot_w, max(2, sc(3))))
    pygame.draw.ellipse(surf, body_col, body)
    pygame.draw.ellipse(surf, body_col, rump)
    pygame.draw.ellipse(surf, chest_col, chest)
    pygame.draw.ellipse(surf, belly_col, belly)
    pygame.draw.ellipse(surf, wing_col, wing)
    pygame.draw.ellipse(surf, head_col, neck)
    pygame.draw.ellipse(surf, head_col, head)
    pygame.draw.polygon(surf, bill_col, bill_pts)
    pygame.draw.circle(surf, head_hi, (head.left + sc(4), head.top + sc(3)), max(1, sc(2)))
    pygame.draw.circle(surf, eye_col, (head.left + sc(7), head.top + sc(4)), max(1, sc(1)))

    if kind == 'hen':
        pygame.draw.line(surf, (82, 58, 34), (head.left + sc(2), head.top + sc(6)), (head.right - sc(2), head.top + sc(5)), max(1, sc(1)))
        for ox, oy in ((11, 15), (16, 18), (21, 14), (26, 18), (30, 15)):
            pygame.draw.line(surf, (92, 66, 40), (sc(ox), sc(oy) + bob), (sc(ox + 3), sc(oy + 1) + bob), 1)
    elif kind == 'duckling':
        pygame.draw.ellipse(surf, chest_col, (body.left + sc(4), body.top + sc(4), sc(13), sc(7)))
        pygame.draw.circle(surf, head_hi, (body.left + sc(9), body.top + sc(4)), max(1, sc(2)))
    else:
        pygame.draw.rect(surf, neck_ring, (neck.left + sc(1), neck.top + sc(7), max(1, sc(5)), max(1, sc(2))))
        speculum = pygame.Rect(wing.left + sc(4), wing.top + sc(3), sc(7), sc(3))
        pygame.draw.rect(surf, (52, 92, 182), speculum, border_radius=2)
        pygame.draw.rect(surf, (244, 246, 238), speculum.inflate(sc(2), sc(1)), 1, border_radius=2)
        pygame.draw.arc(surf, tail_col, (body.left - sc(4), body.top - sc(5), sc(10), sc(9)), 4.4, 6.0, max(1, sc(2)))

    if facing < 0:
        surf = pygame.transform.flip(surf, True, False)
    return surf


def _shade(col, delta):
    return tuple(max(0, min(255, c + delta)) for c in col)


def _mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _front_wall_point(roof, rise_x, rise_y, x, y):
    return int(roof.left + x), int(roof.bottom + y)


def _side_wall_point(roof, rise_x, rise_y, x, y):
    t = x / max(1, rise_x)
    return int(roof.right + x), int(roof.top + y + rise_y * t)


def _draw_front_window(surf, roof, rise_x, rise_y, x, y, w, h, col):
    pts = [
        _front_wall_point(roof, rise_x, rise_y, x, y),
        _front_wall_point(roof, rise_x, rise_y, x + w, y),
        _front_wall_point(roof, rise_x, rise_y, x + w, y + h),
        _front_wall_point(roof, rise_x, rise_y, x, y + h),
    ]
    pygame.draw.polygon(surf, (25, 28, 34), pts)
    inner = [
        _front_wall_point(roof, rise_x, rise_y, x + 1, y + 1),
        _front_wall_point(roof, rise_x, rise_y, x + w - 1, y + 1),
        _front_wall_point(roof, rise_x, rise_y, x + w - 1, y + h - 1),
        _front_wall_point(roof, rise_x, rise_y, x + 1, y + h - 1),
    ]
    pygame.draw.polygon(surf, col, inner)
    mid_a = _front_wall_point(roof, rise_x, rise_y, x + w // 2, y + 1)
    mid_b = _front_wall_point(roof, rise_x, rise_y, x + w // 2, y + h - 1)
    pygame.draw.line(surf, (40, 44, 50), mid_a, mid_b, 1)


def _draw_front_panel(surf, roof, rise_x, rise_y, rect, fill, border=(25, 28, 34)):
    x, y, w, h = rect
    if w < 3 or h < 3:
        return
    pts = [
        _front_wall_point(roof, rise_x, rise_y, x, y),
        _front_wall_point(roof, rise_x, rise_y, x + w, y),
        _front_wall_point(roof, rise_x, rise_y, x + w, y + h),
        _front_wall_point(roof, rise_x, rise_y, x, y + h),
    ]
    pygame.draw.polygon(surf, border, pts)
    inner = [
        _front_wall_point(roof, rise_x, rise_y, x + 1, y + 1),
        _front_wall_point(roof, rise_x, rise_y, x + w - 1, y + 1),
        _front_wall_point(roof, rise_x, rise_y, x + w - 1, y + h - 1),
        _front_wall_point(roof, rise_x, rise_y, x + 1, y + h - 1),
    ]
    pygame.draw.polygon(surf, fill, inner)


def _label_font(size):
    if not pygame.font.get_init():
        pygame.font.init()
    return pygame.font.Font(None, size)


def _draw_sign_text(surf, text, rect, bg, fg=(248, 242, 210)):
    if rect.w < 8 or rect.h < 6:
        return
    pygame.draw.rect(surf, (24, 22, 28), rect.move(2, 2), border_radius=2)
    pygame.draw.rect(surf, bg, rect, border_radius=2)
    font = _label_font(max(10, min(18, rect.h + 4)))
    label = font.render(text, True, fg)
    if label.get_width() > rect.w - 6:
        scale = (rect.w - 6) / label.get_width()
        label = pygame.transform.smoothscale(
            label,
            (max(1, int(label.get_width() * scale)), max(1, int(label.get_height() * scale))),
        )
    surf.blit(label, label.get_rect(center=rect.center))


def _draw_brick_courses(surf, roof, rise_x, rise_y, color):
    mortar = _shade(color, -22)
    for y in range(5, max(6, rise_y - 2), 6):
        pygame.draw.line(
            surf,
            mortar,
            _front_wall_point(roof, rise_x, rise_y, 3, y),
            _front_wall_point(roof, rise_x, rise_y, roof.w - 3, y),
            1,
        )
        off = 8 if (y // 6) % 2 else 0
        for x in range(off + 6, roof.w - 5, 18):
            pygame.draw.line(
                surf,
                _shade(color, -16),
                _front_wall_point(roof, rise_x, rise_y, x, y - 5),
                _front_wall_point(roof, rise_x, rise_y, x, y),
                1,
            )


def _draw_front_door(surf, roof, rise_x, rise_y, rect, fill=DOOR, trim=(48, 30, 22), double=False):
    _draw_front_panel(surf, roof, rise_x, rise_y, rect, fill, trim)
    if double and rect.w >= 10:
        pygame.draw.line(
            surf,
            _shade(trim, 20),
            _front_wall_point(roof, rise_x, rise_y, rect.centerx, rect.top + 2),
            _front_wall_point(roof, rise_x, rise_y, rect.centerx, rect.bottom - 2),
            1,
        )
    knob_x = rect.centerx + (rect.w // 4 if double else rect.w // 2 - 4)
    knob = _front_wall_point(roof, rise_x, rise_y, knob_x, rect.y + rect.h // 2)
    pygame.draw.circle(surf, (220, 196, 80), knob, 1)


def _draw_front_line(surf, roof, rise_x, rise_y, x1, y1, x2, y2, color, width=1):
    pygame.draw.line(
        surf,
        color,
        _front_wall_point(roof, rise_x, rise_y, x1, y1),
        _front_wall_point(roof, rise_x, rise_y, x2, y2),
        width,
    )


def _draw_side_window(surf, roof, rise_x, rise_y, x, y, w, h, col):
    pts = [
        _side_wall_point(roof, rise_x, rise_y, x, y),
        _side_wall_point(roof, rise_x, rise_y, x + w, y),
        _side_wall_point(roof, rise_x, rise_y, x + w, y + h),
        _side_wall_point(roof, rise_x, rise_y, x, y + h),
    ]
    pygame.draw.polygon(surf, (22, 24, 30), pts)
    inner = [
        _side_wall_point(roof, rise_x, rise_y, x + 1, y + 1),
        _side_wall_point(roof, rise_x, rise_y, x + w - 1, y + 1),
        _side_wall_point(roof, rise_x, rise_y, x + w - 1, y + h - 1),
        _side_wall_point(roof, rise_x, rise_y, x + 1, y + h - 1),
    ]
    pygame.draw.polygon(surf, col, inner)


def _draw_roof_detail(surf, rng, roof, roof_col, accent):
    detail = rng.choice(("hvac", "hut", "vents", "skylight"))
    if detail == "hvac":
        box_w = min(34, max(18, roof.w // 5))
        box_h = min(22, max(12, roof.h // 5))
        x = rng.randint(roof.left + 10, max(roof.left + 10, roof.right - box_w - 8))
        y = rng.randint(roof.top + 10, max(roof.top + 10, roof.bottom - box_h - 8))
        pygame.draw.rect(surf, (70, 74, 76), (x + 3, y + 4, box_w, box_h), border_radius=2)
        pygame.draw.rect(surf, (138, 144, 145), (x, y, box_w, box_h), border_radius=2)
        pygame.draw.rect(surf, (48, 50, 52), (x + 4, y + 4, box_w - 8, box_h - 8), 1)
        for lx in range(x + 6, x + box_w - 4, 5):
            pygame.draw.line(surf, (92, 96, 98), (lx, y + 5), (lx, y + box_h - 5), 1)
    elif detail == "hut":
        hut_w = min(36, max(22, roof.w // 4))
        hut_h = min(28, max(18, roof.h // 4))
        x = rng.randint(roof.left + 8, max(roof.left + 8, roof.right - hut_w - 8))
        y = rng.randint(roof.top + 8, max(roof.top + 8, roof.bottom - hut_h - 8))
        side = _shade(accent, -30)
        pygame.draw.rect(surf, side, (x + 4, y + 4, hut_w, hut_h))
        pygame.draw.rect(surf, accent, (x, y, hut_w, hut_h))
        pygame.draw.rect(surf, _shade(accent, -55), (x + hut_w - 8, y + 4, 5, hut_h - 7))
        pygame.draw.rect(surf, (48, 35, 28), (x + 6, y + hut_h - 12, 8, 12))
    elif detail == "vents":
        for _ in range(rng.randint(4, 7)):
            x = rng.randint(roof.left + 8, max(roof.left + 8, roof.right - 10))
            y = rng.randint(roof.top + 8, max(roof.top + 8, roof.bottom - 10))
            pygame.draw.rect(surf, (55, 58, 60), (x + 2, y + 2, 6, 5))
            pygame.draw.rect(surf, (118, 124, 126), (x, y, 6, 5))
            pygame.draw.line(surf, (185, 190, 190), (x + 1, y), (x + 5, y), 1)
    else:
        for _ in range(rng.randint(1, 3)):
            sw = min(30, max(18, roof.w // 5))
            sh = 9
            x = rng.randint(roof.left + 10, max(roof.left + 10, roof.right - sw - 8))
            y = rng.randint(roof.top + 10, max(roof.top + 10, roof.bottom - sh - 8))
            pygame.draw.polygon(surf, (42, 78, 94), [(x, y + 2), (x + sw - 4, y), (x + sw, y + sh - 2), (x + 4, y + sh)])
            pygame.draw.polygon(surf, (120, 205, 230), [(x + 3, y + 3), (x + sw - 5, y + 2), (x + sw - 3, y + sh - 3), (x + 5, y + sh - 2)])
    for _ in range(rng.randint(18, 34)):
        x = rng.randint(roof.left + 4, max(roof.left + 4, roof.right - 4))
        y = rng.randint(roof.top + 4, max(roof.top + 4, roof.bottom - 4))
        speck = _mix(roof_col, (255, 255, 255), rng.uniform(0.05, 0.18))
        surf.set_at((x, y), (*speck, 120))


def _draw_bar_front(surf, rng, roof, rise_x, rise_y, door_rect):
    _draw_brick_courses(surf, roof, rise_x, rise_y, (94, 48, 44))
    sign = pygame.Rect(roof.centerx - 24, roof.bottom + 4, 48, 12)
    _draw_sign_text(surf, "BAR", sign, (54, 20, 32), (255, 210, 90))
    _draw_front_panel(surf, roof, rise_x, rise_y, (8, 18, max(14, door_rect.left - 13), 14), (46, 26, 36), (22, 14, 16))
    _draw_front_panel(surf, roof, rise_x, rise_y, (door_rect.right + 8, 18, roof.w - door_rect.right - 16, 14), (46, 26, 36), (22, 14, 16))
    _draw_front_door(surf, roof, rise_x, rise_y, door_rect, (34, 20, 18), (190, 120, 52), double=True)
    for lx in (sign.left + 7, sign.right - 7):
        pygame.draw.circle(surf, (255, 210, 90), (lx, sign.centery), 2)
    for x in range(roof.left + 12, roof.right - 12, 28):
        pygame.draw.rect(surf, (68, 38, 30), (x, roof.top + 8, 14, 6), border_radius=3)
        pygame.draw.circle(surf, (180, 136, 64), (x + 4, roof.top + 11), 1)


def _draw_restaurant_front(surf, rng, roof, rise_x, rise_y, door_rect):
    sign_w = min(92, roof.w - 18)
    sign = pygame.Rect(roof.centerx - sign_w // 2, roof.bottom + 4, sign_w, 12)
    _draw_sign_text(surf, "RESTAURANT", sign, (82, 96, 52), (248, 232, 188))
    win_y = max(15, rise_y - 26)
    for rect in (
        (8, win_y, max(16, door_rect.left - 12), 14),
        (door_rect.right + 8, win_y, roof.w - door_rect.right - 16, 14),
    ):
        _draw_front_panel(surf, roof, rise_x, rise_y, rect, (122, 82, 56), (44, 30, 24))
        _draw_front_line(surf, roof, rise_x, rise_y, rect[0] + 3, rect[1] + 8, rect[0] + rect[2] - 3, rect[1] + 8, (226, 178, 104))
    _draw_front_door(surf, roof, rise_x, rise_y, door_rect, (72, 42, 30), (216, 172, 96))
    for side_x in (8, roof.w - 18):
        pot = pygame.Rect(roof.left + side_x, roof.bottom + rise_y - 11, 10, 7)
        pygame.draw.rect(surf, (104, 56, 40), pot)
        pygame.draw.circle(surf, (48, 132, 68), (pot.centerx, pot.top - 1), 4)
    vent = pygame.Rect(roof.right - 42, roof.top + 10, 24, 15)
    pygame.draw.rect(surf, (86, 88, 86), vent.move(3, 3), border_radius=2)
    pygame.draw.rect(surf, (158, 162, 158), vent, border_radius=2)
    pygame.draw.circle(surf, (70, 72, 72), (vent.centerx, vent.centery), 5)


def _draw_disco_front(surf, rng, roof, rise_x, rise_y, door_rect):
    pygame.draw.polygon(
        surf,
        (28, 22, 50),
        [
            _front_wall_point(roof, rise_x, rise_y, 2, 2),
            _front_wall_point(roof, rise_x, rise_y, roof.w - 2, 2),
            _front_wall_point(roof, rise_x, rise_y, roof.w - 2, rise_y - 2),
            _front_wall_point(roof, rise_x, rise_y, 2, rise_y - 2),
        ],
    )
    sign_w = min(82, roof.w - 18)
    sign = pygame.Rect(roof.centerx - sign_w // 2, roof.bottom + 4, sign_w, 13)
    _draw_sign_text(surf, "DISCO", sign, (18, 16, 36), (98, 236, 255))
    neon = [(240, 70, 190), (74, 216, 255), (255, 226, 70)]
    for idx, x in enumerate(range(10, roof.w - 8, 18)):
        _draw_front_line(surf, roof, rise_x, rise_y, x, 18, min(roof.w - 5, x + 10), rise_y - 5, neon[idx % len(neon)], 2)
    disco_ball = (roof.centerx, roof.centery)
    pygame.draw.circle(surf, (206, 210, 224), disco_ball, 11)
    pygame.draw.circle(surf, (78, 80, 96), disco_ball, 11, 1)
    for dx in (-5, 0, 5):
        pygame.draw.line(surf, (132, 136, 156), (disco_ball[0] + dx, disco_ball[1] - 9), (disco_ball[0] + dx, disco_ball[1] + 9))
    for dy in (-4, 2):
        pygame.draw.line(surf, (132, 136, 156), (disco_ball[0] - 9, disco_ball[1] + dy), (disco_ball[0] + 9, disco_ball[1] + dy))
    door = door_rect.inflate(10, 2)
    door.x = max(6, min(door.x, roof.w - door.w - 6))
    _draw_front_door(surf, roof, rise_x, rise_y, door, (14, 12, 20), (230, 70, 200), double=True)
    for _ in range(16):
        px = rng.randint(roof.left + 8, roof.right - 8)
        py = rng.randint(roof.top + 8, roof.bottom - 8)
        pygame.draw.circle(surf, rng.choice(neon), (px, py), 1)


def _draw_supermarket_front(surf, rng, roof, rise_x, rise_y, door_rect):
    sign = pygame.Rect(roof.left + 8, roof.bottom + 4, roof.w - 16, 13)
    _draw_sign_text(surf, "SUPERMARKT", sign, (28, 128, 72), (245, 248, 218))
    entry_w = min(42, max(28, roof.w // 3))
    entry = pygame.Rect(roof.w // 2 - entry_w // 2, max(16, rise_y - 23), entry_w, 20)
    _draw_front_panel(surf, roof, rise_x, rise_y, (8, entry.y, entry.left - 12, 17), (76, 132, 124), (34, 68, 62))
    _draw_front_panel(surf, roof, rise_x, rise_y, (entry.right + 8, entry.y, roof.w - entry.right - 16, 17), (76, 132, 124), (34, 68, 62))
    _draw_front_panel(surf, roof, rise_x, rise_y, entry, (120, 178, 188), (30, 70, 74))
    _draw_front_line(surf, roof, rise_x, rise_y, entry.centerx, entry.y + 1, entry.centerx, entry.bottom - 2, (236, 248, 248), 1)
    cart_x = roof.left + 14
    cart_y = roof.top + 15
    pygame.draw.rect(surf, (228, 232, 226), (cart_x, cart_y, 22, 12), 2)
    pygame.draw.line(surf, (228, 232, 226), (cart_x + 3, cart_y + 12), (cart_x + 18, cart_y + 17), 2)
    pygame.draw.circle(surf, (38, 42, 42), (cart_x + 7, cart_y + 18), 2)
    pygame.draw.circle(surf, (38, 42, 42), (cart_x + 19, cart_y + 18), 2)
    dock = pygame.Rect(roof.right - 44, roof.top + 12, 30, 18)
    pygame.draw.rect(surf, (54, 58, 60), dock)
    pygame.draw.rect(surf, (144, 150, 150), dock.inflate(-5, -5))


def _draw_fastfood_front(surf, rng, roof, rise_x, rise_y, door_rect):
    sign_w = min(82, roof.w - 18)
    sign = pygame.Rect(roof.centerx - sign_w // 2, roof.bottom + 4, sign_w, 13)
    _draw_sign_text(surf, "BURGER", sign, (198, 40, 36), (255, 232, 92))
    pygame.draw.circle(surf, (245, 184, 52), (sign.left + 10, sign.centery), 5)
    pygame.draw.rect(surf, (110, 54, 24), (sign.left + 5, sign.centery, 11, 2))
    _draw_front_panel(surf, roof, rise_x, rise_y, (8, max(14, rise_y - 24), max(16, door_rect.left - 14), 15), (118, 58, 42), (58, 28, 24))
    _draw_front_panel(surf, roof, rise_x, rise_y, (door_rect.right + 8, max(14, rise_y - 24), roof.w - door_rect.right - 16, 15), (118, 58, 42), (58, 28, 24))
    _draw_front_door(surf, roof, rise_x, rise_y, door_rect, (92, 30, 26), (252, 210, 58), double=True)
    lane_y = roof.top + roof.h // 2
    pygame.draw.line(surf, (248, 214, 64), (roof.left + 10, lane_y), (roof.right - 12, lane_y), 2)
    pygame.draw.polygon(surf, (248, 214, 64), [(roof.right - 18, lane_y - 5), (roof.right - 8, lane_y), (roof.right - 18, lane_y + 5)])
    board = pygame.Rect(roof.right - 28, roof.bottom - 22, 16, 11)
    pygame.draw.rect(surf, (42, 30, 24), board)
    pygame.draw.rect(surf, (230, 194, 66), board.inflate(-4, -4))


def _make_bank_building(w, h, seed):
    rng = random.Random(seed)
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    shadow = pygame.Rect(14, 12, w - 22, h - 14)
    pygame.draw.rect(surf, (0, 0, 0, 82), shadow, border_radius=2)

    roof = pygame.Rect(8, 6, w - 16, max(76, h - 70))
    facade = pygame.Rect(10, roof.bottom - 1, w - 20, h - roof.bottom - 15)
    stone = (218, 211, 190)
    stone_dark = (142, 134, 118)
    stone_mid = (184, 176, 156)

    pygame.draw.rect(surf, (56, 70, 78), roof)
    pygame.draw.rect(surf, (34, 42, 48), roof, 2)
    for y in range(roof.top + 14, roof.bottom - 8, 18):
        pygame.draw.line(surf, (46, 58, 66), (roof.left + 6, y), (roof.right - 6, y), 1)
    for x in range(roof.left + 18, roof.right - 8, 28):
        pygame.draw.line(surf, (48, 60, 68), (x, roof.top + 7), (x, roof.bottom - 7), 1)

    skylight = pygame.Rect(roof.centerx - 42, roof.top + 18, 84, 30)
    pygame.draw.rect(surf, (30, 40, 46), skylight.move(4, 4), border_radius=3)
    pygame.draw.rect(surf, (106, 146, 164), skylight, border_radius=3)
    pygame.draw.rect(surf, (36, 48, 54), skylight, 1, border_radius=3)
    pygame.draw.line(surf, (194, 214, 220), skylight.midleft, skylight.midright, 1)
    pygame.draw.line(surf, (194, 214, 220), skylight.midtop, skylight.midbottom, 1)

    for x in (roof.left + 24, roof.right - 58):
        plant = pygame.Rect(x, roof.bottom - 30, 34, 18)
        pygame.draw.rect(surf, (48, 54, 56), plant.move(3, 3), border_radius=2)
        pygame.draw.rect(surf, (128, 134, 132), plant, border_radius=2)
        for lx in range(plant.left + 6, plant.right - 4, 7):
            pygame.draw.line(surf, (84, 90, 90), (lx, plant.top + 4), (lx, plant.bottom - 4), 1)

    pygame.draw.rect(surf, (128, 120, 106), facade.move(5, 5))
    pygame.draw.rect(surf, stone, facade)
    pygame.draw.rect(surf, stone_dark, facade, 2)
    for y in range(facade.top + 9, facade.bottom - 4, 10):
        pygame.draw.line(surf, (198, 190, 170), (facade.left + 4, y), (facade.right - 4, y), 1)

    crown = pygame.Rect(facade.left - 6, facade.top - 8, facade.w + 12, 10)
    pygame.draw.rect(surf, stone_mid, crown)
    pygame.draw.line(surf, (112, 104, 92), crown.bottomleft, crown.bottomright, 1)
    pediment = [
        (facade.centerx, facade.top - 28),
        (facade.left + 24, facade.top - 8),
        (facade.right - 24, facade.top - 8),
    ]
    pygame.draw.polygon(surf, (232, 226, 204), pediment)
    pygame.draw.polygon(surf, (112, 104, 92), pediment, 2)
    seal = (facade.centerx, facade.top - 14)
    pygame.draw.circle(surf, (174, 144, 72), seal, 7)
    pygame.draw.circle(surf, (88, 76, 56), seal, 7, 1)

    sign = pygame.Rect(facade.centerx - 68, facade.top + 5, 136, 12)
    _draw_sign_text(surf, "ZENTRALBANK", sign, (35, 62, 82), (246, 240, 210))

    entrance = pygame.Rect(facade.centerx - 28, facade.bottom - 32, 56, 26)
    pygame.draw.rect(surf, (44, 48, 50), entrance.move(3, 3))
    pygame.draw.rect(surf, (42, 48, 52), entrance)
    pygame.draw.rect(surf, (102, 142, 158), entrance.inflate(-8, -6))
    pygame.draw.rect(surf, (34, 44, 50), entrance.inflate(-8, -6), 1)
    pygame.draw.line(surf, (226, 198, 112), entrance.midtop, entrance.midbottom, 2)
    pygame.draw.line(surf, (190, 214, 220), (entrance.left + 12, entrance.top + 8), (entrance.left + 26, entrance.top + 8), 1)
    pygame.draw.line(surf, (190, 214, 220), (entrance.right - 26, entrance.top + 8), (entrance.right - 12, entrance.top + 8), 1)
    pygame.draw.circle(surf, (238, 214, 130), (entrance.centerx - 5, entrance.centery + 5), 1)
    pygame.draw.circle(surf, (238, 214, 130), (entrance.centerx + 5, entrance.centery + 5), 1)

    for x in (facade.left + 18, facade.right - 78):
        bank_window = pygame.Rect(x, facade.top + 23, 60, 19)
        pygame.draw.rect(surf, (52, 66, 72), bank_window.move(2, 2))
        pygame.draw.rect(surf, (76, 110, 126), bank_window)
        pygame.draw.rect(surf, (34, 46, 52), bank_window, 1)
        for split in (bank_window.left + 20, bank_window.left + 40):
            pygame.draw.line(surf, (174, 194, 200), (split, bank_window.top + 3), (split, bank_window.bottom - 3), 1)
        pygame.draw.line(surf, (174, 194, 200), bank_window.midleft, bank_window.midright, 1)

    plinth = pygame.Rect(facade.left + 12, facade.bottom - 9, facade.w - 24, 5)
    pygame.draw.rect(surf, (166, 158, 140), plinth)
    pygame.draw.line(surf, (116, 108, 96), plinth.topleft, plinth.topright, 1)

    for step in range(3):
        y = facade.bottom - 2 + step * 4
        pygame.draw.rect(surf, (170, 162, 144), (facade.centerx - 96 + step * 14, y, 192 - step * 28, 4))

    for _ in range(26):
        x = rng.randint(roof.left + 5, roof.right - 5)
        y = rng.randint(roof.top + 5, roof.bottom - 5)
        surf.set_at((x, y), (*_mix((56, 70, 78), (255, 255, 255), rng.uniform(0.04, 0.12)), 120))
    return surf


def _draw_highrise_front(surf, rng, roof, rise_x, rise_y, door_rect):
    facade = (42, 62, 76)
    shine = (96, 132, 150)
    for x in range(9, roof.w - 10, 18):
        _draw_front_line(surf, roof, rise_x, rise_y, x, 4, x, rise_y - 5, _shade(facade, -18))
    for y in range(8, rise_y - 9, 12):
        _draw_front_line(surf, roof, rise_x, rise_y, 6, y, roof.w - 6, y, _shade(facade, -24))

    win_w = 9
    win_h = 6
    cols = max(2, min(10, (roof.w - 16) // 14))
    rows = max(3, (rise_y - 18) // 11)
    gap_x = max(5, (roof.w - cols * win_w) // (cols + 1))
    for row in range(rows):
        y = 8 + row * 11
        if y + win_h > rise_y - 8:
            continue
        for col in range(cols):
            x = gap_x + col * (win_w + gap_x)
            if door_rect and pygame.Rect(x, y, win_w, win_h).inflate(8, 4).colliderect(door_rect):
                continue
            lit = rng.random() < 0.22
            glass = (242, 218, 112) if lit else _mix((52, 92, 118), (24, 28, 36), 0.35)
            _draw_front_panel(surf, roof, rise_x, rise_y, (x, y, win_w, win_h), glass, (24, 32, 40))
            if not lit:
                _draw_front_line(surf, roof, rise_x, rise_y, x + 2, y + 1, x + win_w - 2, y + 1, shine)

    lobby = door_rect.inflate(10, 2)
    lobby.x = roof.w // 2 - lobby.w // 2
    lobby.y = min(lobby.y, rise_y - lobby.h - 2)
    _draw_front_door(surf, roof, rise_x, rise_y, lobby, (42, 74, 88), (180, 192, 190), double=True)
    canopy = pygame.Rect(roof.left + lobby.x - 4, roof.bottom + lobby.y - 5, lobby.w + 8, 5)
    pygame.draw.rect(surf, (166, 176, 172), canopy)
    pygame.draw.line(surf, (70, 78, 80), canopy.bottomleft, canopy.bottomright, 1)

    mast_x = roof.centerx + rng.randint(-12, 12)
    pygame.draw.line(surf, (68, 72, 74), (mast_x, roof.top + 26), (mast_x, roof.top + 4), 2)
    pygame.draw.circle(surf, (212, 60, 56), (mast_x, roof.top + 4), 2)
    plant = pygame.Rect(roof.left + 14, roof.top + 14, 30, 18)
    pygame.draw.rect(surf, (68, 72, 74), plant.move(3, 3), border_radius=2)
    pygame.draw.rect(surf, (128, 136, 138), plant, border_radius=2)
    for lx in range(plant.left + 5, plant.right - 4, 6):
        pygame.draw.line(surf, (82, 88, 90), (lx, plant.top + 4), (lx, plant.bottom - 4), 1)


def _draw_house_accents(surf, rng, roof, rise_x, rise_y, door_rect, wall, style):
    if style == "brick":
        chimney = pygame.Rect(roof.right - 28, roof.top + 10, 9, 16)
        pygame.draw.rect(surf, (84, 42, 36), chimney)
        pygame.draw.rect(surf, (46, 28, 26), chimney.inflate(-2, -2))
    elif style == "balconies":
        y = min(max(10, rise_y // 3), rise_y - 14)
        for x in range(13, roof.w - 24, 30):
            _draw_front_line(surf, roof, rise_x, rise_y, x, y + 12, x + 18, y + 12, (62, 64, 66), 2)
            _draw_front_line(surf, roof, rise_x, rise_y, x + 2, y + 9, x + 2, y + 13, (62, 64, 66))
            _draw_front_line(surf, roof, rise_x, rise_y, x + 16, y + 9, x + 16, y + 13, (62, 64, 66))
    elif style == "office":
        for x in range(18, roof.w - 10, 24):
            _draw_front_line(surf, roof, rise_x, rise_y, x, 4, x, rise_y - 4, _shade(wall, -28))
        antenna = (roof.centerx, roof.top + 10)
        pygame.draw.line(surf, (54, 56, 58), (antenna[0], antenna[1] + 14), antenna, 2)
        pygame.draw.circle(surf, (168, 174, 174), antenna, 2)
    else:
        segments = max(2, roof.w // 42)
        seg_w = roof.w // segments
        for i in range(1, segments):
            x = i * seg_w
            _draw_front_line(surf, roof, rise_x, rise_y, x, 3, x, rise_y - 4, _shade(wall, -45), 2)
        if door_rect:
            for i in range(3):
                pygame.draw.rect(surf, (132, 126, 112), (roof.left + door_rect.x - 4 - i * 2, roof.bottom + rise_y - 3 + i * 2, door_rect.w + 8 + i * 4, 2))


def _draw_business_front(surf, rng, roof, rise_x, rise_y, kind, door_rect):
    if not door_rect:
        return
    if kind == "bar":
        _draw_bar_front(surf, rng, roof, rise_x, rise_y, door_rect)
    elif kind == "restaurant":
        _draw_restaurant_front(surf, rng, roof, rise_x, rise_y, door_rect)
    elif kind == "disco":
        _draw_disco_front(surf, rng, roof, rise_x, rise_y, door_rect)
    elif kind == "supermarket":
        _draw_supermarket_front(surf, rng, roof, rise_x, rise_y, door_rect)
    elif kind == "fastfood":
        _draw_fastfood_front(surf, rng, roof, rise_x, rise_y, door_rect)
    elif kind == "highrise":
        _draw_highrise_front(surf, rng, roof, rise_x, rise_y, door_rect)


def make_building(w_cells, h_cells, seed, kind=None):
    """Generiert oder holt aus Cache ein Gebäude-Sprite."""
    # Cache-Key
    key = (w_cells, h_cells, seed, kind)
    if key in _building_cache:
        return _building_cache[key]
    
    rng = random.Random(seed)
    cell = 32
    w, h = w_cells * cell, h_cells * cell
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    if kind == "bank":
        result = _make_bank_building(w, h, seed)
        _building_cache[key] = result
        return result

    palettes = [
        ((172, 86, 72), (118, 55, 52), (74, 76, 78), (132, 128, 118)),
        ((194, 184, 164), (146, 136, 122), (88, 86, 82), (168, 158, 138)),
        ((126, 150, 160), (80, 104, 118), (48, 62, 70), (116, 134, 138)),
        ((168, 164, 150), (118, 112, 102), (88, 58, 54), (126, 96, 78)),
        ((WALL1, _shade(WALL1, -44), ROOF1, WALL2)),
        ((WALL2, _shade(WALL2, -42), ROOF2, WALL1)),
    ]
    if kind == "bar":
        wall, wall_side, roof_col, accent = (86, 48, 42), (56, 34, 32), (42, 36, 34), (190, 120, 52)
    elif kind == "restaurant":
        wall, wall_side, roof_col, accent = (174, 132, 92), (112, 86, 66), (96, 82, 62), (82, 96, 52)
    elif kind == "disco":
        wall, wall_side, roof_col, accent = (38, 32, 58), (24, 22, 38), (24, 24, 36), (240, 70, 190)
    elif kind == "supermarket":
        wall, wall_side, roof_col, accent = (170, 182, 174), (118, 128, 124), (58, 82, 76), (28, 128, 72)
    elif kind == "fastfood":
        wall, wall_side, roof_col, accent = (198, 62, 48), (132, 42, 36), (92, 54, 46), (248, 214, 64)
    elif kind == "highrise":
        wall, wall_side, roof_col, accent = (54, 76, 88), (38, 54, 64), (42, 48, 54), (128, 136, 138)
    else:
        wall, wall_side, roof_col, accent = rng.choice(palettes)
    if kind == "highrise":
        rise_y = max(64, min(104, h // 2))
    else:
        rise_y_max = max(30, min(58, h // 2))
        rise_y_min = min(rise_y_max, max(26, min(46, h // 4)))
        rise_y = rng.randint(rise_y_min, rise_y_max)
    rise_x = 0
    roof = pygame.Rect(4, 4, max(42, w - 8), max(38, h - rise_y - 10))
    base = roof.move(0, rise_y)
    base.bottom = min(base.bottom, h - 4)

    front_pts = [(roof.left, roof.bottom), (roof.right, roof.bottom),
                 (base.right, base.bottom), (base.left, base.bottom)]
    shadow_pts = [(base.left + 5, base.top + 8), (base.right + 5, base.top + 8),
                  (base.right + 5, base.bottom + 5), (base.left + 5, base.bottom + 5)]

    pygame.draw.polygon(s, (0, 0, 0, 80), shadow_pts)
    pygame.draw.polygon(s, wall, front_pts)
    pygame.draw.rect(s, _shade(wall_side, -18), (base.right - 6, base.top, 6, base.h))
    pygame.draw.rect(s, _shade(wall, 18), (base.left, base.top, 4, base.h))
    pygame.draw.rect(s, roof_col, roof)

    parapet_hi = _shade(roof_col, 30)
    parapet_lo = _shade(roof_col, -35)
    pygame.draw.line(s, parapet_hi, roof.topleft, roof.topright, 2)
    pygame.draw.line(s, parapet_hi, roof.topleft, roof.bottomleft, 2)
    pygame.draw.line(s, parapet_lo, roof.bottomleft, roof.bottomright, 2)
    pygame.draw.line(s, parapet_lo, roof.topright, roof.bottomright, 2)
    pygame.draw.polygon(s, _shade(wall, -55), front_pts, 1)
    pygame.draw.rect(s, _shade(roof_col, -55), roof, 1)

    house_style = rng.choice(("brick", "balconies", "office", "rowhouse")) if kind is None else None
    if house_style == "brick":
        _draw_brick_courses(s, roof, rise_x, rise_y, wall)

    if rng.random() < 0.65:
        seam_col = _shade(roof_col, -18)
        for y in range(roof.top + 12, roof.bottom - 6, 18):
            pygame.draw.line(s, seam_col, (roof.left + 5, y), (roof.right - 5, y), 1)
        for x in range(roof.left + 14, roof.right - 6, 24):
            pygame.draw.line(s, _shade(roof_col, -10), (x, roof.top + 5), (x, roof.bottom - 5), 1)

    door_rect = None
    if rise_y >= 34 and roof.w > 72:
        door_w = 24 if kind in ("bank", "highrise") else 16
        door_h = min(24 if kind in ("bank", "highrise") else 22, rise_y - 11)
        door_x = roof.w // 2 - door_w // 2 + (0 if kind in ("bank", "highrise") else rng.randint(-8, 8))
        door_y = rise_y - door_h - 2
        door_rect = pygame.Rect(door_x, door_y, door_w, door_h)

    if kind is None:
        win_w = 12 if w_cells <= 4 else 14
        win_h = 10
        front_cols = max(1, min(6, (roof.w - 14) // (win_w + 8)))
        front_rows = max(1, min(3, (rise_y - 9) // (win_h + 4)))
        gap_x = (roof.w - front_cols * win_w) // (front_cols + 1)
        for row in range(front_rows):
            y = 7 + row * (win_h + 4)
            if y + win_h > rise_y - 3:
                continue
            for col in range(front_cols):
                x = gap_x + col * (win_w + gap_x)
                if door_rect and pygame.Rect(x, y, win_w, win_h).inflate(10, 6).colliderect(door_rect):
                    continue
                lit = rng.random() < 0.32
                glass = WIN_LIT if lit else _mix(WIN, (30, 34, 46), 0.45)
                _draw_front_window(s, roof, rise_x, rise_y, x, y, win_w, win_h, glass)

        if door_rect:
            _draw_front_door(s, roof, rise_x, rise_y, door_rect)

    if kind not in ("bank", "restaurant"):
        _draw_roof_detail(s, rng, roof, roof_col, accent)

    if kind is None:
        _draw_house_accents(s, rng, roof, rise_x, rise_y, door_rect, wall, house_style)
    else:
        _draw_business_front(s, rng, roof, rise_x, rise_y, kind, door_rect)

    _building_cache[key] = s
    return s


import math as _math


def _outline(surf, pts, col, width=1):
    if len(pts) >= 2:
        pygame.draw.lines(surf, col, True, pts, width)


def _icon_armor(s):
    """Schutzweste (Body-Armor-Silhouette), 36×36."""
    # Schulterklappen (oben links/rechts)
    pygame.draw.rect(s, (62, 76, 92),  (5, 7, 8, 6),  border_radius=2)   # links
    pygame.draw.rect(s, (62, 76, 92),  (23, 7, 8, 6), border_radius=2)   # rechts
    pygame.draw.rect(s, (85, 102, 122),(6, 8, 6, 4),  border_radius=1)
    pygame.draw.rect(s, (85, 102, 122),(24, 8, 6, 4), border_radius=1)

    # Haupt-Weste (torso-förmig: oben breiter, unten schmaler)
    vest = [(8, 12), (28, 12), (30, 28), (25, 32), (11, 32), (6, 28)]
    pygame.draw.polygon(s, (52, 66, 80), [(x+1, y+1) for x, y in vest])  # Schatten
    pygame.draw.polygon(s, (76, 96, 118), vest)

    # Vorderseite (heller)
    front = [(10, 14), (26, 14), (27, 27), (23, 31), (13, 31), (9, 27)]
    pygame.draw.polygon(s, (95, 120, 148), front)

    # Plattensegmente (horizontale Rillen)
    for ly in (18, 22, 26):
        pygame.draw.line(s, (62, 80, 100), (10, ly), (26, ly), 1)

    # Mittlerer Verschluss (Reißverschluss / Klettverschluss)
    pygame.draw.rect(s, (42, 54, 66), (16, 13, 4, 18), border_radius=1)
    for zy in range(14, 30, 3):
        pygame.draw.rect(s, (105, 130, 158), (17, zy, 2, 2))

    # Kragen-Ausschnitt (V-Form)
    pygame.draw.polygon(s, (42, 54, 66), [(14, 12), (22, 12), (18, 18)])

    # Konturlinie außen
    pygame.draw.polygon(s, (38, 48, 60), vest, 1)


def _icon_heart(s):
    """Rotes Herz, 36×36."""
    cx, cy = 18, 19
    fill = (220, 35, 60)
    hi   = (255, 100, 120)
    dark = (140, 15, 30)
    pts = []
    for i in range(80):
        t = _math.pi * 2 * i / 80
        x =  9 * (_math.sin(t)**3)
        y = -8 * (_math.cos(t) - 0.3*_math.cos(2*t) - 0.1*_math.cos(3*t))
        pts.append((cx + x, cy + y + 1))
    pygame.draw.polygon(s, dark, pts)
    shrunk = [(cx + (x-cx)*0.85, cy + (y-cy)*0.85) for x,y in pts]
    pygame.draw.polygon(s, fill, shrunk)
    # Highlight-Fleck oben links
    hl_pts = [(cx-4, cy-5), (cx-1, cy-7), (cx+1, cy-5), (cx-1, cy-3)]
    pygame.draw.polygon(s, hi, hl_pts)


def _icon_smg(s):
    """SMG — Uzi-artig, kompakt mit Klappgriff."""
    # Schatten
    pygame.draw.rect(s, (20,20,20,180), (4,17,30,3), border_radius=1)
    # Lauf (dünn, vorne)
    pygame.draw.rect(s, (60,60,65),  (4,14,14,4),  border_radius=1)
    pygame.draw.rect(s, (90,90,95),  (5,15,12,2))
    # Körper (Receiver)
    pygame.draw.rect(s, (70,70,75),  (14,11,14,9), border_radius=2)
    pygame.draw.rect(s, (100,100,108),(15,12,12,4), border_radius=1)
    # Magazin senkrecht unten
    pygame.draw.rect(s, (55,55,58),  (17,19,6,12), border_radius=2)
    pygame.draw.rect(s, (80,80,85),  (18,20,4,5))
    # Pistolengriff (schräg rechts)
    pts_grip = [(26,18),(30,18),(31,26),(27,27)]
    pygame.draw.polygon(s, (65,65,70), pts_grip)
    # Visier
    pygame.draw.rect(s, (180,180,60), (14,11,2,2))
    pygame.draw.rect(s, (180,180,60), (24,11,2,2))
    # Outline
    pygame.draw.rect(s, (30,30,30),  (14,11,14,9), border_radius=2, width=1)
    pygame.draw.rect(s, (30,30,30),  (4,14,14,4),  border_radius=1, width=1)


def _icon_shotgun(s):
    """Pump-Action Schrotflinte — langer Lauf, Pumpe, Kolben."""
    # Schatten
    pygame.draw.rect(s, (20,20,20,180), (3,18,32,3), border_radius=1)
    # Lauf (oben, lang)
    pygame.draw.rect(s, (70,70,72),  (3,12,26,5),  border_radius=2)
    pygame.draw.rect(s, (110,110,115),(4,13,24,2))
    # Laufmündung
    pygame.draw.rect(s, (40,40,42),  (3,12,4,5))
    # Pump-Handschutz (helleres Segment)
    pygame.draw.rect(s, (130,95,55), (8,17,8,5),  border_radius=1)
    pygame.draw.rect(s, (170,130,75),(9,18,6,2))
    # Receiver
    pygame.draw.rect(s, (100,70,40), (16,11,10,11), border_radius=2)
    pygame.draw.rect(s, (140,105,60),(17,12,8,4))
    # Kolben (Schaft)
    pts_stock = [(26,13),(33,16),(33,22),(26,22)]
    pygame.draw.polygon(s, (110,75,35), pts_stock)
    pygame.draw.line(s,  (150,110,60), (27,14),(32,17), 1)
    # Pistolengriff
    pygame.draw.rect(s, (90,60,30),  (22,21,6,9),  border_radius=2)
    # Abzugsbügel
    pygame.draw.lines(s, (50,35,15), False, [(19,21),(19,27),(24,27),(24,21)], 1)
    # Outlines
    pygame.draw.rect(s, (30,20,10), (3,12,26,5),  border_radius=2, width=1)
    pygame.draw.rect(s, (30,20,10), (16,11,10,11),border_radius=2, width=1)


def _icon_mg(s):
    """Schweres MG — breiter Körper, Gurt-Magazin, Bipod."""
    # Schatten
    pygame.draw.rect(s, (20,20,20,180), (2,18,34,3), border_radius=1)
    # Bipod-Beine
    pygame.draw.line(s, (55,80,55), (6,17),(3,26), 2)
    pygame.draw.line(s, (55,80,55), (11,17),(8,26), 2)
    # Lauf (lang, dick)
    pygame.draw.rect(s, (60,85,60),  (3,13,22,6),  border_radius=2)
    pygame.draw.rect(s, (90,120,90), (4,14,20,2))
    # Laufmantel (Kühlrippen)
    for rx in range(5, 22, 3):
        pygame.draw.line(s, (50,70,50), (rx,13),(rx,19), 1)
    # Receiver / Körper
    pygame.draw.rect(s, (65,90,65),  (18,10,14,12), border_radius=2)
    pygame.draw.rect(s, (95,130,95), (19,11,12,4))
    # Gurt-Magazin (oben links)
    pygame.draw.rect(s, (80,60,40),  (10,7,10,7),  border_radius=1)
    for gy in range(8,14,2):
        pygame.draw.line(s, (110,85,55), (11,gy),(19,gy), 1)
    # Pistolengriff
    pts_grip = [(28,20),(32,20),(33,29),(29,30)]
    pygame.draw.polygon(s, (55,80,55), pts_grip)
    # Abzugsbügel
    pygame.draw.lines(s, (35,55,35), False, [(23,20),(23,27),(28,27),(28,20)], 1)
    # Kolben
    pts_stock = [(32,12),(36,15),(36,22),(32,22)]
    pygame.draw.polygon(s, (55,78,55), pts_stock)
    # Outlines
    pygame.draw.rect(s, (25,40,25), (3,13,22,6),  border_radius=2, width=1)
    pygame.draw.rect(s, (25,40,25), (18,10,14,12),border_radius=2, width=1)


def _icon_rpg(s):
    """RPG — dickes Rohr mit Rakete, Kimme, Korn."""
    # Schatten
    pygame.draw.rect(s, (20,20,20,180), (2,19,34,4), border_radius=2)
    # Rohr (offen hinten — trichterförmig)
    pygame.draw.rect(s, (55,80,55),  (4,14,28,8),  border_radius=3)
    pygame.draw.rect(s, (85,115,85), (5,15,26,3))
    # Hinteres Ende (trichter)
    pygame.draw.polygon(s, (40,60,40), [(4,14),(4,22),(1,24),(1,12)])
    # Rakete
    pygame.draw.rect(s, (200,80,30),  (6,16,22,4), border_radius=1)
    pygame.draw.rect(s, (230,120,50), (7,17,20,2))
    # Raketenspitze
    pygame.draw.polygon(s, (240,60,20), [(28,14),(28,22),(34,18)])
    pygame.draw.polygon(s, (255,150,80),[(28,16),(28,20),(32,18)])
    # Abzugsgruppe / Griff
    pygame.draw.rect(s, (50,75,50),  (14,21,7,10), border_radius=2)
    pygame.draw.lines(s, (30,50,30), False, [(12,21),(12,29),(14,29)], 1)
    # Kimme + Korn
    pygame.draw.rect(s, (200,200,80), (8,13,2,3))
    pygame.draw.rect(s, (200,200,80), (22,13,2,3))
    # Outlines
    pygame.draw.rect(s, (25,45,25), (4,14,28,8),  border_radius=3, width=1)


# Vorgerenderte Pickup-Icons (36×36 SRCALPHA), lazy-initialisiert
_PICKUP_ICONS: dict = {}

def get_pickup_icon(kind):
    """Gibt ein 36×36 SRCALPHA-Surface zurück (transparent, kein Hintergrund)."""
    if kind in _PICKUP_ICONS:
        return _PICKUP_ICONS[kind]

    s = pygame.Surface((36, 36), pygame.SRCALPHA)

    if kind == 'hp':
        _icon_heart(s)
    elif kind == 'armor':
        _icon_armor(s)
    elif kind == 2:
        _icon_smg(s)
    elif kind == 3:
        _icon_shotgun(s)
    elif kind == 4:
        _icon_mg(s)
    elif kind == 5:
        _icon_rpg(s)

    _PICKUP_ICONS[kind] = s
    return s
