"""Spawn-Hilfen: Fußgänger, Auto, Cop-Auto, Ausstiegsposition."""
import math
import random
import pygame

from game2d.config import (
    W, H,
    INNER_LO, INNER_HI_X, INNER_HI_Y,
    ROAD_LO, ROAD_HI_X, ROAD_HI_Y,
    ROAD_W, SIDEWALK_W, WORLD_W, WORLD_H,
)
from game2d.state import current
from game2d.world.geometry import (
    in_city, rect_hits_city_edge, lane_center_for_car, random_pedestrian_destination,
)


def safe_spawn():
    s = current()
    for _ in range(300):
        if random.random() < 0.5:
            road_y = random.choice(s.roads_h)
            side = -1 if random.random() < 0.5 else 1
            x = random.randint(ROAD_LO + 30, ROAD_HI_X - 30)
            y = int(road_y + side * (ROAD_W//2 + SIDEWALK_W//2))
        else:
            road_x = random.choice(s.roads_v)
            side = -1 if random.random() < 0.5 else 1
            x = int(road_x + side * (ROAD_W//2 + SIDEWALK_W//2))
            y = random.randint(ROAD_LO + 30, ROAD_HI_Y - 30)
        r = pygame.Rect(x-12, y-12, 24, 24)
        if in_city(x, y, 20) and not any(r.colliderect(b[0]) for b in s.buildings):
            return x, y
    for _ in range(300):
        x = random.randint(INNER_LO + 30, INNER_HI_X - 30)
        y = random.randint(INNER_LO + 30, INNER_HI_Y - 30)
        r = pygame.Rect(x-15, y-15, 30, 30)
        if not any(r.colliderect(b[0]) for b in s.buildings):
            return x, y
    return ROAD_LO, ROAD_LO


def pedestrian_spawn():
    s = current()
    prefer_park = bool(s.pedestrian_park_nodes) and random.random() < 0.28
    node_idx = random_pedestrian_destination(prefer_park=prefer_park)
    if node_idx is not None:
        x, y = s.pedestrian_nodes[node_idx]
        r = pygame.Rect(x - 12, y - 12, 24, 24)
        if in_city(x, y, 20) and not any(r.colliderect(b[0]) for b in s.buildings):
            return x, y
    return safe_spawn()


def exit_car_position(car):
    s = current()
    candidates = []
    for side in (-1, 1):
        ang = math.radians(car.angle + 90 * side)
        candidates.append((car.x + math.sin(ang) * 48, car.y - math.cos(ang) * 48))
    for back in (42, -42):
        ang = math.radians(car.angle)
        candidates.append((car.x - math.sin(ang) * back, car.y + math.cos(ang) * back))
    for x, y in candidates:
        r = pygame.Rect(x - 10, y - 10, 20, 20)
        if in_city(x, y, 12) and not any(r.colliderect(b[0]) for b in s.buildings):
            return x, y
    return safe_spawn()


def car_spawn_clear(x, y, margin=22):
    s = current()
    r = pygame.Rect(x - 23, y - 39, 46, 78)
    if rect_hits_city_edge(r):
        return False
    probe = r.inflate(margin * 2, margin * 2)
    if any(probe.colliderect(b[0]) for b in s.buildings):
        return False
    if any(probe.colliderect(park) for park in s.parks):
        return False
    if any(probe.colliderect(c.rect()) for c in s.cars):
        return False
    return True


def road_spawn():
    s = current()
    for _ in range(200):
        if random.random() < 0.5:
            angle = random.choice([90, 270])
            x = random.randint(ROAD_LO + 50, ROAD_HI_X - 50)
            y = random.choice(s.roads_h) + (28 if angle == 90 else -28)
        else:
            angle = random.choice([0, 180])
            x = random.choice(s.roads_v) + (28 if angle == 0 else -28)
            y = random.randint(ROAD_LO + 50, ROAD_HI_Y - 50)
        if car_spawn_clear(x, y):
            return x, y, angle
    for _ in range(200):
        x = random.randint(INNER_LO + 60, INNER_HI_X - 60)
        y = random.randint(INNER_LO + 60, INNER_HI_Y - 60)
        if car_spawn_clear(x, y):
            angle = random.choice([0, 90, 180, 270])
            lx, ly = lane_center_for_car(angle, x, y)
            return lx, ly, angle
    return WORLD_W // 2, WORLD_H // 2, random.choice([0, 90, 180, 270])


def _outside_view(x, y, cam, margin=130):
    if cam is None:
        return True
    view = pygame.Rect(int(cam[0]), int(cam[1]), W, H).inflate(margin * 2, margin * 2)
    return not view.collidepoint(x, y)


def cop_car_spawn_near(tx, ty, cam=None):
    s = current()
    min_dist = max(W, H) * 0.65
    max_dist = max(W, H) * 1.15
    for _ in range(260):
        ang = random.uniform(0, math.tau)
        dist = random.uniform(min_dist, max_dist)
        sx = tx + math.cos(ang) * dist
        sy = ty + math.sin(ang) * dist
        sx = max(ROAD_LO + 50, min(ROAD_HI_X - 50, sx))
        sy = max(ROAD_LO + 50, min(ROAD_HI_Y - 50, sy))
        if random.random() < 0.5:
            angle = random.choice([90, 270])
            x = int(sx)
            y = random.choice(s.roads_h) + (28 if angle == 90 else -28)
        else:
            angle = random.choice([0, 180])
            x = random.choice(s.roads_v) + (28 if angle == 0 else -28)
            y = int(sy)
        if _outside_view(x, y, cam) and car_spawn_clear(x, y, margin=30):
            return x, y, angle
    if cam is not None:
        for _ in range(260):
            x, y, angle = road_spawn()
            if _outside_view(x, y, cam):
                return x, y, angle
    return road_spawn()
