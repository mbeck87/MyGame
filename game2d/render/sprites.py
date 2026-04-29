"""Prozedurale Sprite-Generatoren (Autos, Fußgänger, Gebäude)."""
import random
import pygame

from game2d.config import (
    SKIN, COP_BLUE, COP_DARK,
    WALL1, WALL2, ROOF1, ROOF2,
    WIN, WIN_LIT, DOOR,
)


def make_car_sprite(body_col, w=46, h=78):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(s, (0,0,0,80), (3, 6, w-2, h-2), border_radius=8)
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


def make_ped_sprite(shirt_col, skin=SKIN, hair=(60,40,30)):
    return make_ped_frames(shirt_col, skin, hair)[0]


def make_cop_sprite():
    return make_ped_frames(COP_BLUE, is_cop=True)[0]


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
