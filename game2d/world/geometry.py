"""Welt-Geometrie: Wasser-/Stadt-Tests, Straßen-Kollision, Lane-Helfer."""
from collections import deque
import math
import random

import pygame

from game2d.config import (
    WATER_W, WORLD_W, WORLD_H,
    INNER_LO, INNER_HI_X, INNER_HI_Y,
    ROAD_W, SIDEWALK_W,
    ROAD_LO, ROAD_HI_X, ROAD_HI_Y,
)
from game2d.state import current


PEDESTRIAN_OFFSET = ROAD_W // 2 + SIDEWALK_W // 2


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


def park_path_points(park):
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


def _ped_probe_rect(ax, ay, bx=None, by=None, radius=12):
    if bx is None or by is None:
        return pygame.Rect(int(ax - radius), int(ay - radius), radius * 2, radius * 2)
    left = min(ax, bx) - radius
    top = min(ay, by) - radius
    width = abs(ax - bx) + radius * 2
    height = abs(ay - by) + radius * 2
    return pygame.Rect(int(left), int(top), int(width), int(height))


def _ped_point_clear(x, y):
    s = current()
    probe = _ped_probe_rect(x, y, radius=11)
    if not in_city(x, y, 8):
        return False
    if any(probe.colliderect(b[0]) for b in s.buildings):
        return False
    if any(probe.colliderect(w) for w in s.WATER_RECTS):
        return False
    if rect_in_park_pond(probe):
        return False
    return True


def _ped_segment_clear(a, b, allow_park=False):
    s = current()
    probe = _ped_probe_rect(a[0], a[1], b[0], b[1], radius=12)
    if any(probe.colliderect(bd[0]) for bd in s.buildings):
        return False
    if any(probe.colliderect(w) for w in s.WATER_RECTS):
        return False
    if rect_in_park_pond(probe):
        return False
    if not allow_park and any(probe.colliderect(park) for park in s.parks):
        return False
    return True


def pedestrian_step_clear(x, y, allow_park=False):
    return _ped_point_clear(x, y) and (allow_park or not any(_ped_probe_rect(x, y, radius=11).colliderect(park) for park in current().parks))


def pedestrian_segment_clear(a, b, allow_park=False):
    return _ped_segment_clear(a, b, allow_park=allow_park)


def rebuild_pedestrian_graph(state):
    nodes = []
    edges = {}
    park_nodes = set()
    index_by_key = {}
    corner_nodes = {}

    def add_node(x, y, is_park=False):
        key = (int(round(x)), int(round(y)))
        if key in index_by_key:
            idx = index_by_key[key]
            if is_park:
                park_nodes.add(idx)
            return idx
        if not _ped_point_clear(key[0], key[1]):
            return None
        idx = len(nodes)
        nodes.append(key)
        edges[idx] = set()
        index_by_key[key] = idx
        if is_park:
            park_nodes.add(idx)
        return idx

    def connect(a, b, allow_park=False):
        if a is None or b is None or a == b:
            return
        if _ped_segment_clear(nodes[a], nodes[b], allow_park=allow_park):
            edges[a].add(b)
            edges[b].add(a)

    off = PEDESTRIAN_OFFSET
    for ix in state.roads_v:
        for iy in state.roads_h:
            for dx_sign in (-1, 1):
                for dy_sign in (-1, 1):
                    node_idx = add_node(ix + dx_sign * off, iy + dy_sign * off)
                    corner_nodes[(ix, iy, dx_sign, dy_sign)] = node_idx

    for iy in state.roads_h:
        for dy_sign in (-1, 1):
            for left_ix, right_ix in zip(state.roads_v, state.roads_v[1:]):
                connect(
                    corner_nodes[(left_ix, iy, 1, dy_sign)],
                    corner_nodes[(right_ix, iy, -1, dy_sign)],
                )

    for ix in state.roads_v:
        for dx_sign in (-1, 1):
            for top_iy, bottom_iy in zip(state.roads_h, state.roads_h[1:]):
                connect(
                    corner_nodes[(ix, top_iy, dx_sign, 1)],
                    corner_nodes[(ix, bottom_iy, dx_sign, -1)],
                )

    for ix in state.roads_v:
        has_west = ix != ROAD_LO
        has_east = ix != ROAD_HI_X
        for iy in state.roads_h:
            has_north = iy != ROAD_LO
            has_south = iy != ROAD_HI_Y
            if has_north:
                connect(corner_nodes[(ix, iy, -1, -1)], corner_nodes[(ix, iy, 1, -1)])
            if has_south:
                connect(corner_nodes[(ix, iy, -1, 1)], corner_nodes[(ix, iy, 1, 1)])
            if has_west:
                connect(corner_nodes[(ix, iy, -1, -1)], corner_nodes[(ix, iy, -1, 1)])
            if has_east:
                connect(corner_nodes[(ix, iy, 1, -1)], corner_nodes[(ix, iy, 1, 1)])

    street_node_ids = list(range(len(nodes)))
    for park in state.parks:
        sampled = park_path_points(park)
        sampled = sampled[::8] + ([sampled[-1]] if sampled[-1] != sampled[::8][-1] else [])
        path_ids = [add_node(x, y, is_park=True) for x, y in sampled]
        path_ids = [idx for idx in path_ids if idx is not None]
        for a, b in zip(path_ids, path_ids[1:]):
            connect(a, b, allow_park=True)
        for endpoint in (path_ids[:1] + path_ids[-1:]):
            ex, ey = nodes[endpoint]
            candidates = sorted(
                street_node_ids,
                key=lambda idx: math.hypot(nodes[idx][0] - ex, nodes[idx][1] - ey),
            )
            for candidate in candidates[:10]:
                if math.hypot(nodes[candidate][0] - ex, nodes[candidate][1] - ey) > 180:
                    continue
                if _ped_segment_clear(nodes[endpoint], nodes[candidate], allow_park=True):
                    edges[endpoint].add(candidate)
                    edges[candidate].add(endpoint)
                    break

    state.pedestrian_nodes[:] = nodes
    state.pedestrian_edges = {idx: sorted(neigh) for idx, neigh in edges.items()}
    state.pedestrian_park_nodes = park_nodes


def nearest_pedestrian_node(x, y):
    s = current()
    if not s.pedestrian_nodes:
        return None
    return min(
        range(len(s.pedestrian_nodes)),
        key=lambda idx: (s.pedestrian_nodes[idx][0] - x) ** 2 + (s.pedestrian_nodes[idx][1] - y) ** 2,
    )


def pedestrian_path(start_idx, goal_idx):
    s = current()
    if start_idx is None or goal_idx is None:
        return []
    if start_idx == goal_idx:
        return [start_idx]
    seen = {start_idx}
    prev = {}
    queue = deque([start_idx])
    while queue:
        node = queue.popleft()
        for nxt in s.pedestrian_edges.get(node, ()):
            if nxt in seen:
                continue
            seen.add(nxt)
            prev[nxt] = node
            if nxt == goal_idx:
                route = [goal_idx]
                while route[-1] != start_idx:
                    route.append(prev[route[-1]])
                route.reverse()
                return route
            queue.append(nxt)
    return [start_idx]


def random_pedestrian_destination(prefer_park=False, avoid_idx=None):
    s = current()
    if not s.pedestrian_nodes:
        return None
    if prefer_park and s.pedestrian_park_nodes:
        pool = [
            idx for idx in s.pedestrian_park_nodes
            if idx != avoid_idx and s.pedestrian_edges.get(idx)
        ]
        if pool:
            return random.choice(pool)
    pool = [
        idx for idx in range(len(s.pedestrian_nodes))
        if idx != avoid_idx and s.pedestrian_edges.get(idx)
    ]
    return random.choice(pool) if pool else avoid_idx
