"""Spawn-Hilfen: Fußgänger, Auto, Cop-Auto, Ausstiegsposition."""
import math
import random
import pygame

from game2d.config import (
    W, H,
    INNER_LO, INNER_HI_X, INNER_HI_Y,
    ROAD_W, SIDEWALK_W, WORLD_W, WORLD_H,
)
from game2d.state import current
from game2d.entities.car import car_collision_size, car_rect_at
from game2d.world.geometry import (
    in_city, rect_hits_city_edge, lane_center_for_car, random_pedestrian_destination,
    rect_in_airport, rect_in_park_pond, rect_on_road,
)


def safe_spawn():
    s = current()
    for _ in range(300):
        segments = [seg for seg in s.road_segments if seg.length > 90]
        if not segments:
            break
        seg = random.choice(segments)
        if seg.axis == "h":
            side = -1 if random.random() < 0.5 else 1
            x = random.randint(int(seg.lo + 30), int(seg.hi - 30))
            y = int(seg.fixed + side * (ROAD_W//2 + SIDEWALK_W//2))
        else:
            side = -1 if random.random() < 0.5 else 1
            x = int(seg.fixed + side * (ROAD_W//2 + SIDEWALK_W//2))
            y = random.randint(int(seg.lo + 30), int(seg.hi - 30))
        r = pygame.Rect(x-12, y-12, 24, 24)
        if (
            in_city(x, y, 20)
            and not any(r.colliderect(b[0]) for b in s.buildings)
            and not any(r.colliderect(park) for park in s.amusement_parks)
            and not rect_in_park_pond(r)
            and not rect_in_airport(r)
        ):
            return x, y
    for _ in range(300):
        x = random.randint(INNER_LO + 30, INNER_HI_X - 30)
        y = random.randint(INNER_LO + 30, INNER_HI_Y - 30)
        r = pygame.Rect(x-15, y-15, 30, 30)
        if (
            not any(r.colliderect(b[0]) for b in s.buildings)
            and not any(r.colliderect(park) for park in s.amusement_parks)
            and not rect_in_park_pond(r)
            and not rect_in_airport(r)
        ):
            return x, y
    return ROAD_LO, ROAD_LO


def sidewalk_spawn():
    """Spawn nur auf Gehwegen (für Armor-Pickups)."""
    s = current()
    for _ in range(300):
        segments = [seg for seg in s.road_segments if seg.length > 90]
        if not segments:
            break
        seg = random.choice(segments)
        if seg.axis == "h":
            side = -1 if random.random() < 0.5 else 1
            x = random.randint(int(seg.lo + 30), int(seg.hi - 30))
            y = int(seg.fixed + side * (ROAD_W//2 + SIDEWALK_W//2))
        else:
            side = -1 if random.random() < 0.5 else 1
            x = int(seg.fixed + side * (ROAD_W//2 + SIDEWALK_W//2))
            y = random.randint(int(seg.lo + 30), int(seg.hi - 30))
        r = pygame.Rect(x-12, y-12, 24, 24)
        if (
            in_city(x, y, 20)
            and not any(r.colliderect(b[0]) for b in s.buildings)
            and not any(r.colliderect(park) for park in s.amusement_parks)
            and not rect_in_park_pond(r)
            and not rect_in_airport(r)
        ):
            return x, y
    # Fallback: irgendwo auf der Straße
    return safe_spawn()


def pedestrian_spawn():
    s = current()
    prefer_park = bool(s.pedestrian_park_nodes) and random.random() < 0.28
    node_idx = random_pedestrian_destination(prefer_park=prefer_park)
    if node_idx is not None:
        x, y = s.pedestrian_nodes[node_idx]
        r = pygame.Rect(x - 12, y - 12, 24, 24)
        if (
            in_city(x, y, 20)
            and not any(r.colliderect(b[0]) for b in s.buildings)
            and not rect_in_airport(r)
        ):
            return x, y
    return safe_spawn()


def exit_car_position(car):
    s = current()
    candidates = []
    side_dist = max(40, getattr(car, "coll_w", 34) / 2 + 24)
    back_dist = max(40, getattr(car, "coll_h", 62) / 2 + 24)
    for side in (-1, 1):
        ang = math.radians(car.angle + 90 * side)
        candidates.append((car.x + math.sin(ang) * side_dist, car.y - math.cos(ang) * side_dist))
    for back in (back_dist, -back_dist):
        ang = math.radians(car.angle)
        candidates.append((car.x - math.sin(ang) * back, car.y + math.cos(ang) * back))
    for x, y in candidates:
        r = pygame.Rect(x - 10, y - 10, 20, 20)
        if in_city(x, y, 12) and not any(r.colliderect(b[0]) for b in s.buildings):
            return x, y
    return safe_spawn()


def car_spawn_clear(x, y, margin=22, angle=0, kind="sedan", is_cop=False):
    s = current()
    r = car_rect_at(x, y, angle, kind, is_cop=is_cop)
    if rect_hits_city_edge(r):
        return False
    if not rect_on_road(r):
        return False
    probe = r.inflate(margin * 2, margin * 2)
    if any(probe.colliderect(b[0]) for b in s.buildings):
        return False
    if any(probe.colliderect(park) for park in s.parks):
        return False
    if any(probe.colliderect(park) for park in s.amusement_parks):
        return False
    if rect_in_airport(probe):
        return False
    if any(probe.colliderect(c.rect()) for c in s.cars):
        return False
    return True


def road_spawn(kind="sedan", is_cop=False):
    s = current()
    for _ in range(200):
        _coll_w, coll_h = car_collision_size(kind, is_cop=is_cop)
        buffer = max(70, coll_h // 2 + 24)
        segments = [seg for seg in s.road_segments if seg.length > buffer * 2]
        if not segments:
            break
        seg = random.choice(segments)
        if seg.axis == "h":
            angle = random.choice([90, 270])
            x = random.randint(int(seg.lo + buffer), int(seg.hi - buffer))
            y = seg.fixed + (28 if angle == 90 else -28)
        else:
            angle = random.choice([0, 180])
            x = seg.fixed + (28 if angle == 0 else -28)
            y = random.randint(int(seg.lo + buffer), int(seg.hi - buffer))
        if car_spawn_clear(x, y, angle=angle, kind=kind, is_cop=is_cop):
            return x, y, angle
    for _ in range(200):
        x = random.randint(INNER_LO + 60, INNER_HI_X - 60)
        y = random.randint(INNER_LO + 60, INNER_HI_Y - 60)
        angle = random.choice([0, 90, 180, 270])
        lx, ly = lane_center_for_car(angle, x, y)
        if car_spawn_clear(lx, ly, angle=angle, kind=kind, is_cop=is_cop):
            return lx, ly, angle
    return WORLD_W // 2, WORLD_H // 2, random.choice([0, 90, 180, 270])


def _outside_view(x, y, cam, margin=130):
    if cam is None:
        return True
    view = pygame.Rect(int(cam[0]), int(cam[1]), W, H).inflate(margin * 2, margin * 2)
    return not view.collidepoint(x, y)


def cop_car_spawn_near(tx, ty, cam=None, kind="cop"):
    s = current()
    min_dist = max(W, H) * 0.65
    max_dist = max(W, H) * 1.15
    for _ in range(260):
        _coll_w, coll_h = car_collision_size(kind, is_cop=True)
        buffer = max(70, coll_h // 2 + 24)
        segments = [seg for seg in s.road_segments if seg.length > buffer * 2]
        if not segments:
            break
        seg = random.choice(segments)
        if seg.axis == "h":
            angle = random.choice([90, 270])
            x = random.randint(int(seg.lo + buffer), int(seg.hi - buffer))
            y = seg.fixed + (28 if angle == 90 else -28)
        else:
            angle = random.choice([0, 180])
            x = seg.fixed + (28 if angle == 0 else -28)
            y = random.randint(int(seg.lo + buffer), int(seg.hi - buffer))
        dist = math.hypot(x - tx, y - ty)
        if dist < min_dist or dist > max_dist:
            continue
        if _outside_view(x, y, cam) and car_spawn_clear(x, y, margin=30, angle=angle, kind=kind, is_cop=True):
            return x, y, angle
    if cam is not None:
        for _ in range(260):
            x, y, angle = road_spawn(kind, is_cop=True)
            if _outside_view(x, y, cam):
                return x, y, angle
        return None
    return road_spawn(kind, is_cop=True)
