"""Welt-Hintergrund: Wasser, Strand, Gras, Straßen, Gehsteige, Ampeln."""
import math

import pygame

from game2d.config import (
    W, H,
    WORLD_W, WORLD_H, WATER_W,
    INNER_LO, INNER_HI_X, INNER_HI_Y,
    ROAD_W, SIDEWALK_W, ROAD_LO, ROAD_HI_X, ROAD_HI_Y,
    ASPHALT, GRASS, LINE, SIDEW,
    WATER_DEEP, WATER_MID, WATER_LITE, SAND,
)
from game2d.render.sprites import make_duck_sprite
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
    crosswalk_len = 18
    half_crosswalk = crosswalk_len // 2
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
            for park in s.parks:
                margin = ROAD_W // 2 + SIDEWALK_W
                left_road = park.left - margin
                right_road = park.right + margin
                top_road = park.top - margin
                bottom_road = park.bottom + margin
                if park.left < ix < park.right:
                    if iy == top_road:
                        has_south = False
                    elif iy == bottom_road:
                        has_north = False
                if park.top < iy < park.bottom:
                    if ix == left_road:
                        has_east = False
                    elif ix == right_road:
                        has_west = False
            y_top = sy - offset - half_crosswalk
            y_bottom = sy + offset - half_crosswalk
            x_left = sx - span // 2
            for x in range(int(x_left), int(x_left + span), stripe_w + gap):
                if has_north:
                    pygame.draw.rect(surf, stripe, (x, y_top, stripe_w, crosswalk_len))
                if has_south:
                    pygame.draw.rect(surf, stripe, (x, y_bottom, stripe_w, crosswalk_len))
            x_left_side = sx - offset - half_crosswalk
            x_right_side = sx + offset - half_crosswalk
            y_top_side = sy - span // 2
            for y in range(int(y_top_side), int(y_top_side + span), stripe_w + gap):
                if has_west:
                    pygame.draw.rect(surf, stripe, (x_left_side, y, crosswalk_len, stripe_w))
                if has_east:
                    pygame.draw.rect(surf, stripe, (x_right_side, y, crosswalk_len, stripe_w))


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


def draw_center_line_dashes(surf, cam, horizontal, center, start, end):
    dash_len = 28
    dash_gap = 22
    pos = start
    while pos < end:
        dash_end = min(pos + dash_len, end)
        if dash_end > pos:
            if horizontal:
                sx = pos - cam[0]
                sy = center - cam[1]
                if -dash_len < sx < W:
                    pygame.draw.rect(surf, LINE, (sx, sy - 2, dash_end - pos, 4))
            else:
                sx = center - cam[0]
                sy = pos - cam[1]
                if -dash_len < sy < H:
                    pygame.draw.rect(surf, LINE, (sx - 2, sy, 4, dash_end - pos))
        pos += dash_len + dash_gap


def draw_center_lines(surf, cam):
    s = current()
    intersection_gap = ROAD_W // 2 + 12
    for y in s.roads_h:
        sy = y - cam[1]
        if not (-10 < sy < H + 10):
            continue
        for x0, x1 in zip(s.roads_v, s.roads_v[1:]):
            start = x0 + intersection_gap
            end = x1 - intersection_gap
            if end > start:
                draw_center_line_dashes(surf, cam, True, y, start, end)
    for x in s.roads_v:
        sx = x - cam[0]
        if not (-10 < sx < W + 10):
            continue
        for y0, y1 in zip(s.roads_h, s.roads_h[1:]):
            start = y0 + intersection_gap
            end = y1 - intersection_gap
            if end > start:
                draw_center_line_dashes(surf, cam, False, x, start, end)


def _smooth_points(points, rounds=3, closed=False):
    pts = [(float(x), float(y)) for x, y in points]
    for _ in range(rounds):
        source = pts + ([pts[0]] if closed else [])
        smoothed = []
        if not closed:
            smoothed.append(source[0])
        pairs = zip(source, source[1:])
        for p0, p1 in pairs:
            q = (p0[0] * 0.75 + p1[0] * 0.25, p0[1] * 0.75 + p1[1] * 0.25)
            r = (p0[0] * 0.25 + p1[0] * 0.75, p0[1] * 0.25 + p1[1] * 0.75)
            smoothed.extend([q, r])
        if not closed:
            smoothed.append(source[-1])
        pts = smoothed
    return [(int(x), int(y)) for x, y in pts]


def _draw_flat_path(surf, points, color, width):
    half = width / 2
    left = []
    right = []
    for i, point in enumerate(points):
        if i == 0:
            tx = points[1][0] - point[0]
            ty = points[1][1] - point[1]
        elif i == len(points) - 1:
            tx = point[0] - points[i - 1][0]
            ty = point[1] - points[i - 1][1]
        else:
            tx = points[i + 1][0] - points[i - 1][0]
            ty = points[i + 1][1] - points[i - 1][1]
        length = math.hypot(tx, ty) or 1
        nx = -ty / length
        ny = tx / length
        left.append((int(point[0] + nx * half), int(point[1] + ny * half)))
        right.append((int(point[0] - nx * half), int(point[1] - ny * half)))
    pygame.draw.polygon(surf, color, left + right[::-1])


def _park_path_points(rect):
    cell_w = rect.w / 2
    cell_h = rect.h / 3
    start = (rect.left + 120, rect.bottom)
    c1 = (rect.left + 120, rect.bottom - cell_h * 0.95)
    c2 = (rect.right - cell_w * 0.55, rect.top + cell_h * 0.95)
    end = (rect.right, rect.top + cell_h * 0.95)
    points = []
    for i in range(72):
        t = i / 71
        mt = 1 - t
        x = mt**3 * start[0] + 3 * mt**2 * t * c1[0] + 3 * mt * t**2 * c2[0] + t**3 * end[0]
        y = mt**3 * start[1] + 3 * mt**2 * t * c1[1] + 3 * mt * t**2 * c2[1] + t**3 * end[1]
        points.append((x, y))
    return points


def _draw_pond_plant(surf, x, y, size=1.0, flower=None):
    radius = max(3, int(7 * size))
    pygame.draw.circle(surf, (44, 128, 66), (int(x), int(y)), radius)
    if flower is not None and abs(size - 1.0) < 0.01:
        pygame.draw.circle(surf, flower, (int(x + 7), int(y - 3)), 4)


def _draw_reeds(surf, x, y, lean=1):
    base = (int(x), int(y))
    for i, height in enumerate((18, 24, 15, 21)):
        ox = (i - 1.5) * 5
        top = (int(x + ox + lean * (height * 0.18)), int(y - height))
        pygame.draw.line(surf, (54, 116, 48), (int(x + ox), base[1]), top, 2)
        pygame.draw.ellipse(surf, (133, 102, 48), (top[0] - 2, top[1] - 5, 4, 9))


def _draw_pond_plant_group(surf, x, y, items):
    flower_cols = [(232, 216, 74), (210, 64, 58), (238, 238, 220)]
    for ox, oy, size, flower_idx in items:
        flower = flower_cols[flower_idx % len(flower_cols)] if flower_idx is not None else None
        _draw_pond_plant(surf, x + ox, y + oy, size, flower)


def _draw_reed_group(surf, x, y, leans):
    offsets = ((0, 0), (13, 4), (-12, 5), (5, -6))
    for i, lean in enumerate(leans):
        ox, oy = offsets[i]
        _draw_reeds(surf, x + ox, y + oy, lean)


def _draw_ducks(surf, cam):
    s = current()
    ducks = []
    hens = {}
    duck_entries = []
    for kind, family, follow_slot, base_x, base_y, rx, ry, speed, phase in s.park_ducks:
        t = s.traffic_time * speed + phase
        x = base_x + math.cos(t) * rx
        y = base_y + math.sin(t * 0.92) * ry
        vx = -math.sin(t) * rx * speed
        facing = 1 if vx >= 0 else -1
        entry = {
            'kind': kind,
            'family': family,
            'follow_slot': follow_slot,
            'x': x,
            'y': y,
            'vx': vx,
            'vy': math.cos(t * 0.92) * ry * 0.92 * speed,
            'facing': facing,
            'phase': t,
        }
        duck_entries.append(entry)
        if kind == 'hen':
            hens[family] = entry

    for entry in duck_entries:
        kind = entry['kind']
        x = entry['x']
        y = entry['y']
        facing = entry['facing']
        phase = entry['phase']
        if kind == 'duckling' and entry['family'] in hens:
            mother = hens[entry['family']]
            slot = entry['follow_slot'] or 0
            mvx = mother['vx']
            mvy = mother['vy']
            md = math.hypot(mvx, mvy) or 1
            back_x = -mvx / md
            back_y = -mvy / md
            side_x = -back_y
            side_y = back_x
            stagger = slot - 1
            follow_dist = 30 + slot * 14
            wiggle = math.sin(s.traffic_time * 2.8 + slot) * 3
            x = mother['x'] + back_x * follow_dist + side_x * (stagger * 13 + wiggle)
            y = mother['y'] + back_y * follow_dist + side_y * (stagger * 8)
            facing = mother['facing']
            phase = mother['phase'] + slot * 0.9
        ducks.append((y, kind, x, y, facing, phase))

    ducks.sort(key=lambda item: item[0])
    for _, kind, x, y, facing, phase in ducks:
        sx = x - cam[0]
        sy = y - cam[1]
        if not (-50 < sx < W + 50 and -50 < sy < H + 50):
            continue
        wake_w, wake_h = (13, 5) if kind == 'duckling' else (40, 12)
        wake_y = sy + (1 if kind == 'duckling' else 2)
        wake_base_x = sx - 13 if kind == 'duckling' else sx - 32
        if kind == 'duckling':
            wake_base_x = sx - 13 if facing > 0 else sx + 1
        elif facing < 0:
            wake_base_x = sx - 8
        for wake_shift, alpha in ((0, 105), (8, 58), (16, 28)):
            wake = pygame.Surface((wake_w, wake_h), pygame.SRCALPHA)
            pygame.draw.arc(wake, (220, 242, 248, alpha), (0, 0, wake_w, wake_h), 3.45, 5.95, 1)
            wake_x = wake_base_x - wake_shift if facing > 0 else wake_base_x + wake_shift
            wake_pos = (int(wake_x), int(wake_y))
            surf.blit(wake, wake_pos)
        swim_phase = int(math.sin(s.traffic_time * 4.0 + x * 0.01 + y * 0.01) * 1.6)
        duck = make_duck_sprite(
            kind,
            swim_phase=swim_phase,
            facing=facing,
            paddle_phase=s.traffic_time * 8.0 + phase,
        )
        surf.blit(duck, duck.get_rect(center=(int(sx), int(sy))))

    special = s.duck_easter_duck
    if special:
        x, y, target_x, target_y, ttl = special
        sx = x - cam[0]
        sy = y - cam[1]
        if -50 < sx < W + 50 and -50 < sy < H + 50:
            facing = 1 if target_x >= x else -1
            duck = make_duck_sprite(
                "hen",
                swim_phase=int(math.sin(s.traffic_time * 5.0) * 1.5),
                facing=facing,
                paddle_phase=s.traffic_time * 8.0,
            )
            surf.blit(duck, duck.get_rect(center=(int(sx), int(sy))))
            crown_y = int(sy - 22)
            crown = [
                (int(sx - 8), crown_y + 8),
                (int(sx - 5), crown_y),
                (int(sx), crown_y + 6),
                (int(sx + 5), crown_y),
                (int(sx + 8), crown_y + 8),
            ]
            pygame.draw.polygon(surf, (245, 205, 52), crown)
            pygame.draw.line(surf, (136, 92, 22), crown[0], crown[-1], 2)
            for px, py in crown[1:4]:
                pygame.draw.circle(surf, (255, 236, 112), (px, py), 2)


def draw_park_street_closures(surf, cam):
    s = current()
    road_half = ROAD_W // 2
    margin = ROAD_W // 2 + SIDEWALK_W
    for park in s.parks:
        left_road = park.left - margin
        right_road = park.right + margin
        top_road = park.top - margin
        bottom_road = park.bottom + margin
        for x in s.roads_v:
            if park.left < x < park.right:
                top_h = park.top - (top_road + road_half)
                bot_h = (bottom_road - road_half) - park.bottom
                pygame.draw.rect(surf, SIDEW, (x - road_half - cam[0], top_road + road_half - cam[1], ROAD_W, top_h))
                pygame.draw.rect(surf, SIDEW, (x - road_half - cam[0], park.bottom - cam[1], ROAD_W, bot_h))
        for y in s.roads_h:
            if park.top < y < park.bottom:
                left_w = park.left - (left_road + road_half)
                right_w = (right_road - road_half) - park.right
                pygame.draw.rect(surf, SIDEW, (left_road + road_half - cam[0], y - road_half - cam[1], left_w, ROAD_W))
                pygame.draw.rect(surf, SIDEW, (park.right - cam[0], y - road_half - cam[1], right_w, ROAD_W))


def draw_parks(surf, cam):
    s = current()
    for park in s.parks:
        rect = pygame.Rect(park.x - cam[0], park.y - cam[1], park.w, park.h)
        if rect.right < -80 or rect.left > W + 80 or rect.bottom < -80 or rect.top > H + 80:
            continue
        pygame.draw.rect(surf, (43, 145, 62), rect)
        pygame.draw.rect(surf, (27, 92, 41), rect, 4)

        cell_w = rect.w / 2
        cell_h = rect.h / 3
        pond = [(int(x - cam[0]), int(y - cam[1])) for x, y in s.park_ponds[s.parks.index(park)]]
        pygame.draw.polygon(surf, (38, 105, 150), pond)
        pygame.draw.lines(surf, (91, 166, 196), True, pond, 5)
        plant_groups = (
            (rect.left + 118, rect.top + 132, ((0, 0, 1.0, 0), (18, 9, 0.72, None), (-14, 12, 0.55, None))),
            (rect.left + 226, rect.top + 190, ((0, 0, 1.0, 1), (15, -10, 0.62, None), (-18, 8, 0.82, None), (30, 12, 0.48, None))),
            (rect.left + cell_w + 96, rect.top + 128, ((0, 0, 1.0, 2), (-16, 12, 0.68, None), (20, 10, 0.52, None))),
            (rect.right - 220, rect.top + 96, ((0, 0, 1.0, 0), (18, -4, 0.58, None), (-20, 11, 0.76, None))),
            (rect.right - 145, rect.top + 185, ((0, 0, 1.0, 1), (-16, 8, 0.64, None), (17, 12, 0.44, None))),
            (rect.left + cell_w - 110, rect.top + cell_h + 118, ((0, 0, 1.0, 2), (16, 12, 0.65, None), (-20, 8, 0.54, None))),
        )
        for px, py, items in plant_groups:
            _draw_pond_plant_group(surf, px, py, items)
        reed_groups = (
            (rect.left + 62, rect.top + 120, (-1, 1, -1)),
            (rect.left + 94, rect.top + cell_h * 1.05, (1, -1, 1, -1)),
            (rect.left + cell_w * 0.45, rect.top + 42, (1, 1, -1)),
            (rect.left + cell_w * 1.03, rect.top + 58, (-1, 1, -1, 1)),
            (rect.right - 124, rect.top + 78, (-1, -1, 1)),
            (rect.right - 70, rect.top + cell_h * 0.46, (1, -1, 1, -1)),
            (rect.left + cell_w * 0.62, rect.top + cell_h * 1.55, (-1, 1, -1)),
            (rect.left + 86, rect.top + cell_h * 1.66, (1, -1, 1)),
        )
        for px, py, leans in reed_groups:
            _draw_reed_group(surf, px, py, leans)

        _draw_ducks(surf, cam)

        path_points = _park_path_points(rect)
        _draw_flat_path(surf, path_points, (118, 83, 43), 34)
        _draw_flat_path(surf, path_points, (179, 139, 82), 22)

        for x, y, crown, trunk, dark_g, light_g in s.park_trees:
            if not park.collidepoint(x, y):
                continue
            sx = x - cam[0]
            sy = y - cam[1]
            if -45 < sx < W + 45 and -45 < sy < H + 45:
                pygame.draw.rect(surf, (94, 58, 34), (sx - trunk // 2, sy + crown - 3, trunk, 12))
                pygame.draw.circle(surf, (22, dark_g, 42), (int(sx), int(sy)), crown)
                pygame.draw.circle(surf, (52, light_g, 62), (int(sx - crown * 0.28), int(sy - crown * 0.32)), max(6, crown // 2))


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

    curb_col = (125, 125, 130)
    curb_gap = ROAD_W // 2 + 28

    def draw_h_curb(edge_y, start, end):
        seg_start = start
        for crossing_x in s.roads_v:
            if crossing_x <= start or crossing_x >= end:
                continue
            seg_end = min(end, crossing_x - curb_gap)
            if seg_end > seg_start:
                pygame.draw.line(surf, curb_col,
                                 (seg_start - cam[0], edge_y - cam[1]),
                                 (seg_end - cam[0], edge_y - cam[1]), 2)
            seg_start = max(seg_start, crossing_x + curb_gap)
        if end > seg_start:
            pygame.draw.line(surf, curb_col,
                             (seg_start - cam[0], edge_y - cam[1]),
                             (end - cam[0], edge_y - cam[1]), 2)

    def draw_v_curb(edge_x, start, end):
        seg_start = start
        for crossing_y in s.roads_h:
            if crossing_y <= start or crossing_y >= end:
                continue
            seg_end = min(end, crossing_y - curb_gap)
            if seg_end > seg_start:
                pygame.draw.line(surf, curb_col,
                                 (edge_x - cam[0], seg_start - cam[1]),
                                 (edge_x - cam[0], seg_end - cam[1]), 2)
            seg_start = max(seg_start, crossing_y + curb_gap)
        if end > seg_start:
            pygame.draw.line(surf, curb_col,
                             (edge_x - cam[0], seg_start - cam[1]),
                             (edge_x - cam[0], end - cam[1]), 2)

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
            draw_h_curb(y - road_half, a0, a1)
            draw_h_curb(y + road_half, a0, a1)
    for x in s.roads_v:
        sx = x - cam[0]
        if -ROAD_W < sx < W+ROAD_W:
            a0, a1, _, _ = v_extents(x)
            ay = a0 - cam[1]
            ah = a1 - a0
            pygame.draw.rect(surf, ASPHALT, (sx - ROAD_W//2, ay, ROAD_W, ah))
            draw_v_curb(x - road_half, a0, a1)
            draw_v_curb(x + road_half, a0, a1)
    draw_crosswalks(surf, cam)
    draw_center_lines(surf, cam)
    draw_traffic_lights(surf, cam)
    draw_park_street_closures(surf, cam)
    draw_parks(surf, cam)
