"""Prozedurale Sprite-Generatoren (Autos, Fußgänger, Gebäude)."""
import math
import random
import pygame

from game2d.config import (
    SKIN, COP_BLUE, COP_DARK,
    WALL1, WALL2, ROOF1, ROOF2,
    WIN, WIN_LIT, DOOR,
)


def make_car_sprite(body_col, w=46, h=78):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (0, 0, 0, 70), (6, 9, w - 12, h - 18))
    pygame.draw.rect(s, body_col, (2, 4, w-4, h-8), border_radius=8)
    hl = tuple(min(255, c+35) for c in body_col)
    pygame.draw.rect(s, hl, (4, 6, w-8, 4), border_radius=4)
    pygame.draw.polygon(s, (60,80,100), [(6,16),(w-6,16),(w-10,30),(10,30)])
    pygame.draw.polygon(s, (130,180,220), [(8,17),(w-8,17),(w-12,28),(12,28)])
    pygame.draw.polygon(s, (60,80,100), [(8,h-22),(w-8,h-22),(w-12,h-12),(12,h-12)])
    pygame.draw.polygon(s, (130,180,220), [(10,h-21),(w-10,21+h-42) if False else (w-10,h-21),(w-13,h-13),(13,h-13)])
    pygame.draw.rect(s, tuple(max(0,c-25) for c in body_col), (10, 30, w-20, h-60))
    pygame.draw.line(s, (0,0,0,180), (4, h//2), (w-4, h//2), 1)
    pygame.draw.rect(s, (255,250,200), (5, 6, 8, 5), border_radius=2)
    pygame.draw.rect(s, (255,250,200), (w-13, 6, 8, 5), border_radius=2)
    pygame.draw.rect(s, (200,30,30), (5, h-10, 8, 5), border_radius=2)
    pygame.draw.rect(s, (200,30,30), (w-13, h-10, 8, 5), border_radius=2)
    pygame.draw.rect(s, (20,20,20), (0, 14, 4, 14), border_radius=2)
    pygame.draw.rect(s, (20,20,20), (w-4, 14, 4, 14), border_radius=2)
    pygame.draw.rect(s, (20,20,20), (0, h-28, 4, 14), border_radius=2)
    pygame.draw.rect(s, (20,20,20), (w-4, h-28, 4, 14), border_radius=2)
    return s


def make_cop_car_sprite():
    s = make_car_sprite((245,245,250))
    w, h = s.get_size()
    pygame.draw.rect(s, (20,20,25), (2, h//2 - 14, w-4, 28))
    pygame.draw.rect(s, (245,245,250), (2, h//2 - 4, w-4, 8))
    pygame.draw.rect(s, (40,40,45), (10, 32, w-20, 6))
    pygame.draw.rect(s, (220,40,40), (12, 33, (w-24)//2, 4))
    pygame.draw.rect(s, (40,80,220), (12+(w-24)//2, 33, (w-24)//2, 4))
    return s


def _draw_ped_frame(shirt_col, skin, hair, phase, is_cop=False):
    s = pygame.Surface((20, 24), pygame.SRCALPHA)
    cx, cy = 10, 12
    pants = (40, 40, 80)
    boot  = (20, 20, 20)
    pygame.draw.ellipse(s, (0, 0, 0, 90), (3, cy + 3, 14, 7))
    leg_l_y = cy + 3 - phase * 3
    leg_r_y = cy + 3 + phase * 3
    pygame.draw.rect(s, pants, (cx - 3, leg_l_y, 2, 5))
    pygame.draw.rect(s, pants, (cx + 1, leg_r_y, 2, 5))
    pygame.draw.rect(s, boot,  (cx - 3, leg_l_y + 5, 2, 2))
    pygame.draw.rect(s, boot,  (cx + 1, leg_r_y + 5, 2, 2))
    pygame.draw.ellipse(s, shirt_col, (cx - 5, cy - 3, 10, 9))
    hl = tuple(min(255, c + 30) for c in shirt_col)
    pygame.draw.ellipse(s, hl, (cx - 4, cy - 2, 8, 3))
    arm_l_y = cy + phase * 2
    arm_r_y = cy - phase * 2
    pygame.draw.rect(s, shirt_col, (cx - 7, arm_l_y, 2, 4))
    pygame.draw.rect(s, shirt_col, (cx + 5, arm_r_y, 2, 4))
    pygame.draw.rect(s, skin,      (cx - 7, arm_l_y + 4, 2, 2))
    pygame.draw.rect(s, skin,      (cx + 5, arm_r_y + 4, 2, 2))
    head_y = cy - 5
    pygame.draw.circle(s, hair, (cx, head_y), 4)
    pygame.draw.circle(s, skin, (cx, head_y - 1), 3)
    if is_cop:
        pygame.draw.circle(s, COP_DARK, (cx, head_y), 4)
        pygame.draw.rect(s, COP_DARK, (cx - 4, head_y - 4, 8, 3))
        pygame.draw.rect(s, (230, 200, 60), (cx - 1, head_y - 1, 2, 2))
    return s


def make_ped_frames(shirt_col, skin=SKIN, hair=(60,40,30), is_cop=False):
    return [
        _draw_ped_frame(shirt_col, skin, hair, 0, is_cop),
        _draw_ped_frame(shirt_col, skin, hair, 1, is_cop),
        _draw_ped_frame(shirt_col, skin, hair, 0, is_cop),
        _draw_ped_frame(shirt_col, skin, hair, -1, is_cop),
    ]


def _draw_swim_frame(shirt_col, skin, hair, phase, is_cop=False):
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
    pygame.draw.circle(s, hair if not is_cop else COP_DARK, (cx, torso_y - 4), 4)
    if is_cop:
        pygame.draw.rect(s, COP_DARK, (cx - 4, torso_y - 7, 8, 2))
        pygame.draw.rect(s, (230, 200, 60), (cx - 1, torso_y - 4, 2, 2))

    for wx in range(3, 18, 4):
        pygame.draw.arc(s, wave_col, (wx - 3, water_y - 1, 7, 5), 3.2, 6.1, 2)
    pygame.draw.arc(s, foam_col, (cx - 8, water_y - 2, 16, 5), 3.35, 5.95, 1)
    return s


def make_swim_frames(shirt_col, skin=SKIN, hair=(60,40,30), is_cop=False):
    return [
        _draw_swim_frame(shirt_col, skin, hair, 0, is_cop),
        _draw_swim_frame(shirt_col, skin, hair, 1, is_cop),
        _draw_swim_frame(shirt_col, skin, hair, 0, is_cop),
        _draw_swim_frame(shirt_col, skin, hair, -1, is_cop),
    ]


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


def make_building(w_cells, h_cells, seed):
    rng = random.Random(seed)
    cell = 32
    w, h = w_cells * cell, h_cells * cell
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    wall = rng.choice([WALL1, WALL2, (200,180,150), (165,140,115), (190,170,140)])
    roof = rng.choice([ROOF1, ROOF2, (90,90,95), (130,80,70), (70,80,90)])
    pygame.draw.rect(s, (0,0,0,90), (4, 4, w, h))
    pygame.draw.rect(s, wall, (0, 0, w-4, h-4))
    for y in range(0, h-4, 6):
        off = (y//6) % 2 * 3
        for x in range(-3, w-4, 12):
            pygame.draw.line(s, tuple(max(0,c-15) for c in wall),
                             (x+off, y), (x+off+10, y), 1)
    pygame.draw.rect(s, roof, (0, 0, w-4, 6))
    pygame.draw.rect(s, tuple(max(0,c-25) for c in roof), (0, 6, w-4, 2))
    pad = 8
    win_w, win_h = 14, 18
    cols = (w - 16) // (win_w + 6)
    rows = (h - 18) // (win_h + 8)
    for r in range(rows):
        for c in range(cols):
            x = pad + c * (win_w + 6)
            y = 12 + r * (win_h + 8)
            lit = rng.random() < 0.35
            col = WIN_LIT if lit else WIN
            pygame.draw.rect(s, (30,30,40), (x-1, y-1, win_w+2, win_h+2))
            pygame.draw.rect(s, col, (x, y, win_w, win_h))
            pygame.draw.line(s, (40,40,50), (x+win_w//2, y), (x+win_w//2, y+win_h), 1)
            pygame.draw.line(s, (40,40,50), (x, y+win_h//2), (x+win_w, y+win_h//2), 1)
    dx = w//2 - 10
    dy = h - 28
    pygame.draw.rect(s, DOOR, (dx, dy, 20, 24))
    pygame.draw.rect(s, (50,30,15), (dx, dy, 20, 24), 2)
    pygame.draw.circle(s, (220,200,80), (dx+16, dy+12), 1)
    return s


import math as _math


def _outline(surf, pts, col, width=1):
    if len(pts) >= 2:
        pygame.draw.lines(surf, col, True, pts, width)


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
