"""Welt-Geometrie: Wasser-/Stadt-Tests, Straßen-Kollision, Lane-Helfer."""
import pygame

from game2d.config import (
    WATER_W, WORLD_W, WORLD_H,
    INNER_LO, INNER_HI_X, INNER_HI_Y,
    ROAD_W, SIDEWALK_W,
    ROAD_LO, ROAD_HI_X, ROAD_HI_Y,
)
from game2d.state import current


def in_water(x, y):
    return x < WATER_W or x > WORLD_W - WATER_W or y < WATER_W or y > WORLD_H - WATER_W


def in_city(x, y, margin=0):
    return (INNER_LO + margin <= x <= INNER_HI_X - margin and
            INNER_LO + margin <= y <= INNER_HI_Y - margin)


def rect_hits_city_edge(rect):
    return (rect.left < INNER_LO or rect.right > INNER_HI_X or
            rect.top < INNER_LO or rect.bottom > INNER_HI_Y)


def rect_on_road(rect, margin=10):
    s = current()
    if any(rect.colliderect(park) for park in s.parks):
        return False
    cx, cy = rect.center
    half = ROAD_W * 0.5 - margin
    for y in s.roads_h:
        if ROAD_LO <= cx <= ROAD_HI_X and abs(cy - y) <= half:
            return True
    for x in s.roads_v:
        if ROAD_LO <= cy <= ROAD_HI_Y and abs(cx - x) <= half:
            return True
    return False


def point_in_polygon(x, y, points):
    inside = False
    px, py = points[-1]
    for nx, ny in points:
        if ((ny > y) != (py > y)) and x < (px - nx) * (y - ny) / ((py - ny) or 1) + nx:
            inside = not inside
        px, py = nx, ny
    return inside


def rect_in_park_pond(rect):
    s = current()
    probes = (
        rect.center,
        rect.midtop,
        rect.midbottom,
        rect.midleft,
        rect.midright,
        rect.topleft,
        rect.topright,
        rect.bottomleft,
        rect.bottomright,
    )
    for pond in s.park_ponds:
        if any(point_in_polygon(x, y, pond) for x, y in probes):
            return True
    return False


def rect_hits_road_edge(rect):
    return (rect.right < ROAD_LO or rect.left > ROAD_HI_X or
            rect.bottom < ROAD_LO or rect.top > ROAD_HI_Y)


def lane_center_for_car(angle, x, y):
    s = current()
    heading = int(round(angle / 90.0)) * 90 % 360
    lane_off = 28
    if heading in (0, 180):
        base = min(s.roads_v, key=lambda rx: abs(rx - x))
        side = lane_off if heading == 0 else -lane_off
        return base + side, y
    base = min(s.roads_h, key=lambda ry: abs(ry - y))
    side = lane_off if heading == 90 else -lane_off
    return x, base + side


def move_toward(current_, target, max_step):
    delta = target - current_
    if delta > max_step:
        return current_ + max_step
    if delta < -max_step:
        return current_ - max_step
    return target


def nearest_road_x(x):
    s = current()
    return min(s.roads_v, key=lambda rx: abs(rx - x))


def nearest_road_y(y):
    s = current()
    return min(s.roads_h, key=lambda ry: abs(ry - y))


def intersection_zone_at(x, y, margin=18):
    ix = nearest_road_x(x)
    iy = nearest_road_y(y)
    half = ROAD_W * 0.5 + margin
    if abs(x - ix) <= half and abs(y - iy) <= half:
        size = int(half * 2)
        return ix, iy, pygame.Rect(int(ix - half), int(iy - half), size, size)
    return None


def rect_overlaps_street_space(rect, buffer=14):
    s = current()
    half = ROAD_W // 2 + SIDEWALK_W + buffer
    road_x0 = ROAD_LO - half
    road_x1 = ROAD_HI_X + half
    road_y0 = ROAD_LO - half
    road_y1 = ROAD_HI_Y + half
    for y in s.roads_h:
        if rect.right > road_x0 and rect.left < road_x1 and rect.bottom > y - half and rect.top < y + half:
            return True
    for x in s.roads_v:
        if rect.bottom > road_y0 and rect.top < road_y1 and rect.right > x - half and rect.left < x + half:
            return True
    return False
