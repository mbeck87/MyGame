"""Welt-Hintergrund: Wasser, Strand, Gras, Straßen, Gehsteige, Ampeln."""
import pygame

from game2d.config import (
    W, H,
    WORLD_W, WORLD_H, WATER_W,
    INNER_LO, INNER_HI_X, INNER_HI_Y,
    ROAD_W, SIDEWALK_W, ROAD_LO, ROAD_HI_X, ROAD_HI_Y,
    ASPHALT, GRASS, LINE, SIDEW,
    WATER_DEEP, WATER_MID, WATER_LITE, SAND,
)
from game2d.state import current
from game2d.world.traffic import traffic_light_state


def draw_signal_head(surf, x, y, active, vertical=True):
    pole_col = (55, 55, 58)
    housing = (28, 30, 32)
    rim = (8, 9, 10)
    dim_red = (75, 20, 18)
    dim_yellow = (78, 64, 22)
    dim_green = (18, 70, 28)
    red = (235, 40, 34) if active in ('red', 'red_yellow') else dim_red
    yellow = (240, 190, 45) if active in ('yellow', 'red_yellow') else dim_yellow
    green = (45, 225, 80) if active == 'green' else dim_green
    if vertical:
        pygame.draw.rect(surf, pole_col, (x - 2, y + 13, 4, 18))
        box = pygame.Rect(x - 8, y - 16, 16, 32)
        lights = [(x, y - 9, red), (x, y, yellow), (x, y + 9, green)]
    else:
        pygame.draw.rect(surf, pole_col, (x - 31, y - 2, 18, 4))
        box = pygame.Rect(x - 16, y - 8, 32, 16)
        lights = [(x - 9, y, red), (x, y, yellow), (x + 9, y, green)]
    pygame.draw.rect(surf, housing, box, border_radius=4)
    pygame.draw.rect(surf, rim, box, 1, border_radius=4)
    for lx, ly, col in lights:
        pygame.draw.circle(surf, rim, (int(lx), int(ly)), 4)
        pygame.draw.circle(surf, col, (int(lx), int(ly)), 3)
        if col not in (dim_red, dim_yellow, dim_green):
            pygame.draw.circle(surf, tuple(min(255, c + 35) for c in col), (int(lx - 1), int(ly - 1)), 1)


def draw_crosswalks(surf, cam):
    s = current()
    stripe = (232, 232, 220)
    stripe_w = 6
    gap = 8
    span = ROAD_W - 18
    offset = ROAD_W // 2 + 10
    for ix in s.roads_v:
        sx = ix - cam[0]
        if sx < -120 or sx > W + 120:
            continue
        has_west = ix != ROAD_LO
        has_east = ix != ROAD_HI_X
        for iy in s.roads_h:
            sy = iy - cam[1]
            if sy < -120 or sy > H + 120:
                continue
            has_north = iy != ROAD_LO
            has_south = iy != ROAD_HI_Y
            y_top = sy - offset
            y_bottom = sy + offset - stripe_w
            x_left = sx - span // 2
            for x in range(int(x_left), int(x_left + span), stripe_w + gap):
                if has_north:
                    pygame.draw.rect(surf, stripe, (x, y_top, stripe_w, 18))
                if has_south:
                    pygame.draw.rect(surf, stripe, (x, y_bottom, stripe_w, 18))
            x_left_side = sx - offset
            x_right_side = sx + offset - stripe_w
            y_top_side = sy - span // 2
            for y in range(int(y_top_side), int(y_top_side + span), stripe_w + gap):
                if has_west:
                    pygame.draw.rect(surf, stripe, (x_left_side, y, 18, stripe_w))
                if has_east:
                    pygame.draw.rect(surf, stripe, (x_right_side, y, 18, stripe_w))


def draw_traffic_lights(surf, cam):
    s = current()
    for ix in s.roads_v:
        sx = ix - cam[0]
        if sx < -80 or sx > W + 80:
            continue
        for iy in s.roads_h:
            sy = iy - cam[1]
            if sy < -80 or sy > H + 80:
                continue
            is_corner = (ix in (ROAD_LO, ROAD_HI_X)) and (iy in (ROAD_LO, ROAD_HI_Y))
            if is_corner:
                continue
            axis, phase = traffic_light_state(ix, iy)
            ns_state = phase if axis == 'NS' else 'red'
            ew_state = phase if axis == 'EW' else 'red'
            ns_pos = (int(sx - ROAD_W//2 - SIDEWALK_W//2), int(sy - ROAD_W//2 - SIDEWALK_W//2))
            ew_pos = (int(sx + ROAD_W//2 + SIDEWALK_W//2), int(sy - ROAD_W//2 - SIDEWALK_W//2))
            draw_signal_head(surf, ns_pos[0], ns_pos[1], ns_state, vertical=True)
            draw_signal_head(surf, ew_pos[0], ew_pos[1], ew_state, vertical=False)


def draw_world_bg(surf, cam):
    s = current()
    surf.fill(WATER_DEEP)
    beach_rect = pygame.Rect(WATER_W - cam[0], WATER_W - cam[1],
                             WORLD_W - 2*WATER_W, WORLD_H - 2*WATER_W)
    pygame.draw.rect(surf, SAND, beach_rect)
    inner_rect = pygame.Rect(INNER_LO - cam[0], INNER_LO - cam[1],
                             INNER_HI_X - INNER_LO, INNER_HI_Y - INNER_LO)
    pygame.draw.rect(surf, GRASS, inner_rect)
    wx0 = max(0, int(cam[0]))
    wy0 = max(0, int(cam[1]))
    wx1 = min(WORLD_W, int(cam[0]) + W)
    wy1 = min(WORLD_H, int(cam[1]) + H)
    for wy in range(wy0 - (wy0 % 28), wy1, 28):
        for wx in range(wx0 - (wx0 % 36), wx1, 36):
            if WATER_W < wx < WORLD_W - WATER_W and WATER_W < wy < WORLD_H - WATER_W:
                continue
            sx, sy = wx - cam[0], wy - cam[1]
            off = 6 if (wy // 28) % 2 else 0
            pygame.draw.line(surf, WATER_LITE,
                             (sx + 4 + off, sy + 12), (sx + 14 + off, sy + 12), 2)
            pygame.draw.line(surf, WATER_MID,
                             (sx + 18 + off, sy + 18), (sx + 26 + off, sy + 18), 1)
    for i in range(0, WORLD_W, 60):
        if not (WATER_W <= i <= WORLD_W - WATER_W): continue
        for edge in (WATER_W + 25, WORLD_H - WATER_W - 28):
            sx, sy = i - cam[0], edge - cam[1]
            if -10 < sx < W and -10 < sy < H:
                pygame.draw.circle(surf, (200, 180, 130), (int(sx), int(sy)), 2)
    sidewalk_total = ROAD_W + SIDEWALK_W * 2
    road_ext = sidewalk_total // 2
    road_half = ROAD_W // 2

    def h_extents(y):
        if y == ROAD_LO or y == ROAD_HI_Y:
            return (ROAD_LO - road_half, ROAD_HI_X + road_half,
                    ROAD_LO - road_ext, ROAD_HI_X + road_ext)
        return (ROAD_LO + road_half, ROAD_HI_X - road_half,
                ROAD_LO + road_half, ROAD_HI_X - road_half)

    def v_extents(x):
        if x == ROAD_LO or x == ROAD_HI_X:
            return (ROAD_LO - road_half, ROAD_HI_Y + road_half,
                    ROAD_LO - road_ext, ROAD_HI_Y + road_ext)
        return (ROAD_LO + road_half, ROAD_HI_Y - road_half,
                ROAD_LO + road_half, ROAD_HI_Y - road_half)

    for y in s.roads_h:
        sy = y - cam[1]
        if -sidewalk_total-20 < sy < H+sidewalk_total+20:
            _, _, s0, s1 = h_extents(y)
            pygame.draw.rect(surf, SIDEW, (s0 - cam[0], sy - sidewalk_total//2, s1 - s0, sidewalk_total))
    for x in s.roads_v:
        sx = x - cam[0]
        if -sidewalk_total-20 < sx < W+sidewalk_total+20:
            _, _, s0, s1 = v_extents(x)
            pygame.draw.rect(surf, SIDEW, (sx - sidewalk_total//2, s0 - cam[1], sidewalk_total, s1 - s0))
    for y in s.roads_h:
        sy = y - cam[1]
        if -ROAD_W < sy < H+ROAD_W:
            a0, a1, _, _ = h_extents(y)
            ax = a0 - cam[0]
            aw = a1 - a0
            pygame.draw.rect(surf, ASPHALT, (ax, sy - ROAD_W//2, aw, ROAD_W))
            pygame.draw.line(surf, (125, 125, 130), (ax, sy - ROAD_W//2), (ax + aw, sy - ROAD_W//2), 2)
            pygame.draw.line(surf, (125, 125, 130), (ax, sy + ROAD_W//2), (ax + aw, sy + ROAD_W//2), 2)
    for x in s.roads_v:
        sx = x - cam[0]
        if -ROAD_W < sx < W+ROAD_W:
            a0, a1, _, _ = v_extents(x)
            ay = a0 - cam[1]
            ah = a1 - a0
            pygame.draw.rect(surf, ASPHALT, (sx - ROAD_W//2, ay, ROAD_W, ah))
            pygame.draw.line(surf, (125, 125, 130), (sx - ROAD_W//2, ay), (sx - ROAD_W//2, ay + ah), 2)
            pygame.draw.line(surf, (125, 125, 130), (sx + ROAD_W//2, ay), (sx + ROAD_W//2, ay + ah), 2)
    draw_crosswalks(surf, cam)
    for y in s.roads_h:
        sy = y - cam[1]
        if -10 < sy < H+10:
            a0, a1, _, _ = h_extents(y)
            for dx in range(a0, a1, 50):
                sx = dx - cam[0]
                if -30 < sx < W:
                    pygame.draw.rect(surf, LINE, (sx, sy - 2, 28, 4))
    for x in s.roads_v:
        sx = x - cam[0]
        if -10 < sx < W+10:
            a0, a1, _, _ = v_extents(x)
            for dy in range(a0, a1, 50):
                sy = dy - cam[1]
                if -30 < sy < H:
                    pygame.draw.rect(surf, LINE, (sx - 2, sy, 4, 28))
    draw_traffic_lights(surf, cam)
