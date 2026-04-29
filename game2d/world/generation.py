"""Weltgenerierung: Wasser-Ring, Straßenraster, Häuser, AI_OBSTACLES."""
import random
import pygame

from game2d.config import (
    WORLD_W, WORLD_H, WATER_W, BLOCK,
    INNER_LO, INNER_HI_X, INNER_HI_Y,
    ROAD_LO, ROAD_HI_X, ROAD_HI_Y,
    ROAD_W, SIDEWALK_W,
)
from game2d.render.sprites import make_building
from game2d.world.geometry import rect_overlaps_street_space


def build_world(state):
    """Initialisiert state.WATER_RECTS, roads_h/v, buildings, AI_OBSTACLES."""
    state.WATER_RECTS[:] = [
        pygame.Rect(0, 0, WORLD_W, WATER_W),
        pygame.Rect(0, WORLD_H - WATER_W, WORLD_W, WATER_W),
        pygame.Rect(0, 0, WATER_W, WORLD_H),
        pygame.Rect(WORLD_W - WATER_W, 0, WATER_W, WORLD_H),
    ]

    state.roads_h.clear()
    state.roads_v.clear()
    state.roads_h.extend([ROAD_LO, ROAD_HI_Y])
    state.roads_v.extend([ROAD_LO, ROAD_HI_X])
    for y in range(0, WORLD_H, BLOCK):
        if ROAD_LO < y < ROAD_HI_Y:
            state.roads_h.append(y)
    for x in range(0, WORLD_W, BLOCK):
        if ROAD_LO < x < ROAD_HI_X:
            state.roads_v.append(x)
    state.roads_h[:] = sorted(set(state.roads_h))
    state.roads_v[:] = sorted(set(state.roads_v))

    random.seed(7)
    seed = 0
    state.buildings.clear()
    for bx in range(0, WORLD_W, BLOCK):
        for by in range(0, WORLD_H, BLOCK):
            setback = ROAD_W//2 + SIDEWALK_W + 18
            x0 = max(bx + setback, INNER_LO + SIDEWALK_W + 12)
            y0 = max(by + setback, INNER_LO + SIDEWALK_W + 12)
            x1 = min(bx + BLOCK - setback, INNER_HI_X - SIDEWALK_W - 12)
            y1 = min(by + BLOCK - setback, INNER_HI_Y - SIDEWALK_W - 12)
            if x1 - x0 < 60 or y1 - y0 < 60:
                continue
            cur_y = y0
            while cur_y < y1 - 60:
                cur_x = x0
                row_h = random.randint(3, 5)
                while cur_x < x1 - 60:
                    bw_cells = random.randint(3, 6)
                    bh = row_h
                    bw = bw_cells * 32
                    bhp = bh * 32
                    if cur_x + bw > x1: break
                    if cur_y + bhp > y1: break
                    surf = make_building(bw_cells, bh, seed); seed += 1
                    rect = pygame.Rect(cur_x, cur_y, bw - 4, bhp - 4)
                    if not rect_overlaps_street_space(rect):
                        state.buildings.append((rect, surf))
                    cur_x += bw + random.randint(4, 14)
                cur_y += row_h * 32 + random.randint(8, 18)

    state.AI_OBSTACLES[:] = list(state.buildings) + [(r, None) for r in state.WATER_RECTS]
