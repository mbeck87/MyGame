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
from game2d.world.geometry import rect_overlaps_street_space, rebuild_pedestrian_graph


def _build_park_rect():
    start_x = BLOCK * 3
    start_y = BLOCK * 3
    margin = ROAD_W // 2 + SIDEWALK_W
    return pygame.Rect(
        start_x + margin,
        start_y + margin,
        BLOCK * 2 - margin * 2,
        BLOCK * 3 - margin * 2,
    )


def _smooth_points(points, rounds=4, closed=True):
    pts = [(float(x), float(y)) for x, y in points]
    for _ in range(rounds):
        source = pts + ([pts[0]] if closed else [])
        smoothed = []
        if not closed:
            smoothed.append(source[0])
        for p0, p1 in zip(source, source[1:]):
            smoothed.append((p0[0] * 0.75 + p1[0] * 0.25, p0[1] * 0.75 + p1[1] * 0.25))
            smoothed.append((p0[0] * 0.25 + p1[0] * 0.75, p0[1] * 0.25 + p1[1] * 0.75))
        if not closed:
            smoothed.append(source[-1])
        pts = smoothed
    return pts


def _point_in_polygon(x, y, points):
    inside = False
    px, py = points[-1]
    for nx, ny in points:
        if ((ny > y) != (py > y)) and x < (px - nx) * (y - ny) / ((py - ny) or 1) + nx:
            inside = not inside
        px, py = nx, ny
    return inside


def _park_pond_points(park):
    cell_w = park.w / 2
    cell_h = park.h / 3
    return _smooth_points([
        (park.left + 42, park.top + 78),
        (park.left + cell_w * 0.48, park.top + 28),
        (park.right - 105, park.top + 55),
        (park.right - 64, park.top + cell_h * 0.48),
        (park.left + cell_w * 1.0, park.top + cell_h * 0.92),
        (park.left + cell_w * 0.58, park.top + cell_h * 1.66),
        (park.left + 86, park.top + cell_h * 1.76),
        (park.left + 44, park.top + cell_h * 1.04),
    ], closed=True)


def _park_path_points(park):
    cell_w = park.w / 2
    cell_h = park.h / 3
    start = (park.left + 120, park.bottom)
    c1 = (park.left + 120, park.bottom - cell_h * 0.95)
    c2 = (park.right - cell_w * 0.55, park.top + cell_h * 0.95)
    end = (park.right, park.top + cell_h * 0.95)
    points = []
    for i in range(72):
        t = i / 71
        mt = 1 - t
        x = mt**3 * start[0] + 3 * mt**2 * t * c1[0] + 3 * mt * t**2 * c2[0] + t**3 * end[0]
        y = mt**3 * start[1] + 3 * mt**2 * t * c1[1] + 3 * mt * t**2 * c2[1] + t**3 * end[1]
        points.append((x, y))
    return points


def _point_near_polyline(x, y, points, max_dist):
    max_dist_sq = max_dist * max_dist
    for p0, p1 in zip(points, points[1:]):
        vx = p1[0] - p0[0]
        vy = p1[1] - p0[1]
        seg_len_sq = vx * vx + vy * vy
        if seg_len_sq == 0:
            continue
        t = max(0.0, min(1.0, ((x - p0[0]) * vx + (y - p0[1]) * vy) / seg_len_sq))
        px = p0[0] + vx * t
        py = p0[1] + vy * t
        if (x - px) ** 2 + (y - py) ** 2 <= max_dist_sq:
            return True
    return False


def _point_in_park_pond(park, x, y):
    return _point_in_polygon(x, y, _park_pond_points(park))


def _build_park_trees(park):
    rng = random.Random(41)
    trees = []
    attempts = 0
    path = _park_path_points(park)
    while len(trees) < 54 and attempts < 500:
        attempts += 1
        x = rng.randint(int(park.left + 35), int(park.right - 35))
        y = rng.randint(int(park.top + 35), int(park.bottom - 35))
        if _point_in_park_pond(park, x, y):
            continue
        if _point_near_polyline(x, y, path, 58):
            continue
        crown = rng.randint(13, 27)
        trunk = rng.randint(4, 7)
        dark_g = rng.randint(92, 142)
        light_g = rng.randint(145, 190)
        trees.append((x, y, crown, trunk, dark_g, light_g))
    return trees


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
    state.parks[:] = [_build_park_rect()]
    state.park_ponds[:] = [_park_pond_points(park) for park in state.parks]
    state.park_trees[:] = []
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
                    if any(rect.colliderect(park) for park in state.parks):
                        cur_x += bw + random.randint(4, 14)
                        continue
                    if not rect_overlaps_street_space(rect):
                        state.buildings.append((rect, surf))
                    cur_x += bw + random.randint(4, 14)
                cur_y += row_h * 32 + random.randint(8, 18)

    for park in state.parks:
        state.park_trees.extend(_build_park_trees(park))

    state.AI_OBSTACLES[:] = (
        list(state.buildings)
        + [(r, None) for r in state.WATER_RECTS]
        + [(r, None) for r in state.parks]
    )
    rebuild_pedestrian_graph(state)
