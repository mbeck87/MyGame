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
from game2d.world.geometry import amusement_path_points as _amusement_path_points
from game2d.world.geometry import road_connections_at
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

    def segment_covers(axis, fixed, lo, hi):
        for seg in s.road_segments:
            if seg.axis == axis and int(seg.fixed) == int(fixed) and seg.lo <= lo and seg.hi >= hi:
                return True
        return False

    def draw_vertical_crosswalk(y):
        top = y - half_crosswalk
        x_left = sx - span // 2
        for x in range(int(x_left), int(x_left + span), stripe_w + gap):
            pygame.draw.rect(surf, stripe, (x, top, stripe_w, crosswalk_len))

    def draw_horizontal_crosswalk(x):
        left = x - half_crosswalk
        y_top = sy - span // 2
        for y in range(int(y_top), int(y_top + span), stripe_w + gap):
            pygame.draw.rect(surf, stripe, (left, y, crosswalk_len, stripe_w))

    for ix in s.roads_v:
        sx = ix - cam[0]
        if sx < -120 or sx > W + 120:
            continue
        for iy in s.roads_h:
            sy = iy - cam[1]
            if sy < -120 or sy > H + 120:
                continue
            has_north, has_south, has_west, has_east = road_connections_at(ix, iy, s)
            if not ((has_north or has_south) and (has_west or has_east)):
                continue
            north_lo = iy - offset - half_crosswalk
            north_hi = iy - offset + half_crosswalk
            south_lo = iy + offset - half_crosswalk
            south_hi = iy + offset + half_crosswalk
            west_lo = ix - offset - half_crosswalk
            west_hi = ix - offset + half_crosswalk
            east_lo = ix + offset - half_crosswalk
            east_hi = ix + offset + half_crosswalk
            if has_north and segment_covers("v", ix, north_lo, north_hi):
                draw_vertical_crosswalk(sy - offset)
            if has_south and segment_covers("v", ix, south_lo, south_hi):
                draw_vertical_crosswalk(sy + offset)
            if has_west and segment_covers("h", iy, west_lo, west_hi):
                draw_horizontal_crosswalk(sx - offset)
            if has_east and segment_covers("h", iy, east_lo, east_hi):
                draw_horizontal_crosswalk(sx + offset)


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
            has_north, has_south, has_west, has_east = road_connections_at(ix, iy, s)
            if not ((has_north or has_south) and (has_west or has_east)):
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
    for seg in s.road_segments:
        if seg.axis == "h":
            y = seg.fixed
            sy = y - cam[1]
            if not (-10 < sy < H + 10):
                continue
            start = seg.lo
            for ix in [x for x in s.roads_v if seg.lo < x < seg.hi]:
                end = ix - intersection_gap
                if end > start:
                    draw_center_line_dashes(surf, cam, True, y, start, end)
                start = ix + intersection_gap
            if seg.hi > start:
                draw_center_line_dashes(surf, cam, True, y, start, seg.hi)
        else:
            x = seg.fixed
            sx = x - cam[0]
            if not (-10 < sx < W + 10):
                continue
            start = seg.lo
            for iy in [y for y in s.roads_h if seg.lo < y < seg.hi]:
                end = iy - intersection_gap
                if end > start:
                    draw_center_line_dashes(surf, cam, False, x, start, end)
                start = iy + intersection_gap
            if seg.hi > start:
                draw_center_line_dashes(surf, cam, False, x, start, seg.hi)


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


def _draw_ferris_wheel(surf, cx, cy, t):
    pygame.draw.line(surf, (96, 92, 104), (cx - 48, cy + 76), (cx, cy - 4), 5)
    pygame.draw.line(surf, (96, 92, 104), (cx + 48, cy + 76), (cx, cy - 4), 5)
    pygame.draw.rect(surf, (88, 78, 74), (cx - 58, cy + 72, 116, 10), border_radius=3)
    radius = 74
    pygame.draw.circle(surf, (226, 226, 236), (cx, cy - 10), radius, 4)
    pygame.draw.circle(surf, (92, 104, 122), (cx, cy - 10), 7)
    for i in range(12):
        ang = t * 0.32 + i * math.tau / 12
        x = cx + math.cos(ang) * radius
        y = cy - 10 + math.sin(ang) * radius
        pygame.draw.line(surf, (170, 178, 188), (cx, cy - 10), (x, y), 1)
        gondola = pygame.Rect(int(x - 9), int(y + 6), 18, 12)
        col = ((230, 68, 82), (245, 204, 72), (72, 172, 222), (96, 200, 112))[i % 4]
        pygame.draw.rect(surf, col, gondola, border_radius=3)
        pygame.draw.rect(surf, (34, 34, 40), gondola, 1, border_radius=3)


def _draw_carousel(surf, cx, cy, t):
    pygame.draw.ellipse(surf, (92, 48, 72), (cx - 64, cy + 36, 128, 28))
    pygame.draw.ellipse(surf, (232, 198, 86), (cx - 58, cy + 28, 116, 24))
    pygame.draw.rect(surf, (120, 70, 54), (cx - 8, cy - 24, 16, 68))
    pygame.draw.polygon(surf, (222, 62, 86), [(cx - 76, cy - 18), (cx, cy - 70), (cx + 76, cy - 18)])
    pygame.draw.polygon(surf, (250, 220, 112), [(cx - 54, cy - 18), (cx, cy - 70), (cx + 54, cy - 18)])
    pygame.draw.line(surf, (120, 70, 54), (cx - 68, cy - 18), (cx + 68, cy - 18), 3)
    for i in range(6):
        ang = t * 1.3 + i * math.tau / 6
        x = cx + math.cos(ang) * 42
        y = cy + 18 + math.sin(ang) * 9
        pole_top = cy - 12
        pygame.draw.line(surf, (226, 226, 220), (int(x), pole_top), (int(x), int(y + 11)), 2)
        horse_col = ((245, 245, 238), (205, 168, 120), (92, 164, 218))[i % 3]
        pygame.draw.ellipse(surf, horse_col, (int(x - 13), int(y), 26, 12))
        pygame.draw.circle(surf, horse_col, (int(x + 11), int(y + 1)), 6)
        pygame.draw.circle(surf, (40, 34, 30), (int(x + 13), int(y - 1)), 1)


def _draw_roller_coaster(surf, rect, t):
    area = pygame.Rect(rect.left + 410, rect.top + 34, 560, 218)
    ground_y = area.bottom - 12

    station = pygame.Rect(area.left + 24, ground_y - 50, 132, 44)
    pygame.draw.rect(surf, (66, 50, 46), station.move(4, 5), border_radius=3)
    pygame.draw.rect(surf, (166, 56, 62), station, border_radius=3)
    pygame.draw.polygon(
        surf,
        (238, 190, 58),
        [
            (station.left - 8, station.top + 4),
            (station.centerx, station.top - 26),
            (station.right + 8, station.top + 4),
        ],
    )
    pygame.draw.rect(surf, (52, 42, 40), (station.x + 15, station.bottom - 22, station.w - 30, 22), border_radius=2)
    for x in range(station.left + 18, station.right - 8, 24):
        pygame.draw.line(surf, (248, 226, 118), (x, station.top + 9), (x + 12, station.top + 9), 3)

    def catmull(points, steps=16):
        samples = []
        padded = [points[0]] + points + [points[-1]]
        for i in range(1, len(padded) - 2):
            p0, p1, p2, p3 = padded[i - 1], padded[i], padded[i + 1], padded[i + 2]
            for j in range(steps):
                u = j / steps
                u2 = u * u
                u3 = u2 * u
                x = 0.5 * (
                    2 * p1[0]
                    + (-p0[0] + p2[0]) * u
                    + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * u2
                    + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * u3
                )
                y = 0.5 * (
                    2 * p1[1]
                    + (-p0[1] + p2[1]) * u
                    + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * u2
                    + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * u3
                )
                samples.append((int(x), int(y)))
        samples.append(points[-1])
        return samples

    base = ground_y - 26
    control = [
        (station.left + 18, station.top + 19),
        (area.left + 170, base - 28),
        (area.left + 245, area.top + 20),
        (area.left + 328, area.top + 108),
        (area.left + 392, area.top + 56),
        (area.left + 484, area.top + 128),
        (area.right - 48, base - 8),
        (area.right - 152, base + 2),
        (area.left + 322, base - 6),
        (area.left + 185, base + 8),
        (station.right - 16, station.top + 18),
    ]
    pts = catmull(control)

    loop = (area.left + 388, area.top + 126)
    loop_rx, loop_ry = 42, 58
    loop_rect = pygame.Rect(loop[0] - loop_rx, loop[1] - loop_ry, loop_rx * 2, loop_ry * 2)

    support_col = (76, 78, 82)
    support_shadow = (50, 54, 58)
    concrete = (126, 126, 116)
    rail_dark = (74, 68, 70)
    rail_mid = (178, 40, 48)
    rail_light = (238, 82, 72)
    tie_col = (56, 54, 58)

    pygame.draw.line(surf, (90, 84, 78), (area.left + 12, ground_y), (area.right - 14, ground_y), 3)
    for sx in (area.left + 78, area.left + 164, area.left + 238, area.left + 314, area.left + 480, area.right - 78):
        pygame.draw.ellipse(surf, concrete, (sx - 13, ground_y - 3, 26, 8))

    for idx in range(12, len(pts) - 8, 18):
        x, y = pts[idx]
        foot = ground_y - (idx % 3) * 3
        pygame.draw.line(surf, support_shadow, (x + 4, y + 6), (x - 18, foot), 5)
        pygame.draw.line(surf, support_col, (x - 1, y + 4), (x - 22, foot), 3)
        pygame.draw.line(surf, support_col, (x + 7, y + 4), (x + 18, foot), 3)
        pygame.draw.line(surf, support_col, (x - 13, (y + foot) // 2), (x + 13, (y + foot) // 2 - 10), 2)

    for x in (loop_rect.left + 8, loop_rect.centerx, loop_rect.right - 8):
        pygame.draw.line(surf, support_shadow, (x + 3, loop_rect.bottom - 3), (x + 18, ground_y), 5)
        pygame.draw.line(surf, support_col, (x, loop_rect.bottom - 6), (x + 15, ground_y), 3)
    pygame.draw.line(
        surf,
        support_col,
        (loop_rect.left + 12, loop_rect.centery + 8),
        (loop_rect.right - 12, loop_rect.centery - 8),
        2,
    )

    rail_shadow = [(x + 3, y + 4) for x, y in pts]
    pygame.draw.lines(surf, rail_dark, False, rail_shadow, 11)
    pygame.draw.lines(surf, rail_mid, False, pts, 9)
    pygame.draw.lines(surf, rail_light, False, pts, 3)
    pygame.draw.ellipse(surf, rail_dark, loop_rect.move(3, 4), 11)
    pygame.draw.ellipse(surf, rail_mid, loop_rect, 9)
    pygame.draw.ellipse(surf, rail_light, loop_rect, 3)

    for idx in range(4, len(pts) - 5, 7):
        x, y = pts[idx]
        nx, ny = pts[idx + 1]
        ang = math.atan2(ny - y, nx - x)
        px, py = -math.sin(ang), math.cos(ang)
        pygame.draw.line(surf, tie_col, (int(x - px * 8), int(y - py * 8)), (int(x + px * 8), int(y + py * 8)), 2)
    for i in range(28):
        ang = i * math.tau / 28
        x = loop[0] + math.cos(ang) * loop_rx
        y = loop[1] + math.sin(ang) * loop_ry
        px, py = math.cos(ang), math.sin(ang)
        pygame.draw.line(surf, tie_col, (int(x - px * 7), int(y - py * 7)), (int(x + px * 7), int(y + py * 7)), 2)

    chain_start = (area.left + 174, base - 29)
    chain_end = (area.left + 246, area.top + 22)
    pygame.draw.line(surf, (42, 46, 50), chain_start, chain_end, 2)
    for i in range(7):
        u = i / 6
        x = int(chain_start[0] + (chain_end[0] - chain_start[0]) * u)
        y = int(chain_start[1] + (chain_end[1] - chain_start[1]) * u)
        pygame.draw.circle(surf, (224, 214, 116), (x, y), 2)

    car_idx = int((t * 42) % max(1, len(pts) - 3))
    x, y = pts[car_idx]
    nx, ny = pts[min(car_idx + 2, len(pts) - 1)]
    ang = math.atan2(ny - y, nx - x)
    ux, uy = math.cos(ang), math.sin(ang)
    vx, vy = -uy, ux
    train_cols = ((36, 92, 194), (44, 124, 208), (238, 174, 48))
    for car_no, offset in enumerate((24, 0, -24)):
        cx = x - ux * offset
        cy = y - uy * offset
        body = []
        for lx, ly in ((-11, -8), (12, -7), (15, 7), (-13, 8)):
            body.append((int(cx + ux * lx + vx * ly), int(cy + uy * lx + vy * ly)))
        pygame.draw.polygon(surf, train_cols[car_no], body)
        pygame.draw.lines(surf, (24, 30, 56), True, body, 1)
        pygame.draw.line(
            surf,
            (238, 238, 226),
            (int(cx + ux * -5 + vx * -5), int(cy + uy * -5 + vy * -5)),
            (int(cx + ux * 7 + vx * -4), int(cy + uy * 7 + vy * -4)),
            2,
        )
        for lx in (-6, 8):
            wx = int(cx + ux * lx + vx * 7)
            wy = int(cy + uy * lx + vy * 7)
            pygame.draw.circle(surf, (32, 34, 38), (wx, wy), 3)


def _draw_food_icon(surf, kind, cx, cy):
    if kind == "popcorn":
        pygame.draw.rect(surf, (238, 238, 232), (cx - 8, cy - 6, 16, 18))
        pygame.draw.polygon(surf, (220, 42, 50), [(cx - 8, cy - 6), (cx - 2, cy - 6), (cx - 5, cy + 12), (cx - 8, cy + 12)])
        pygame.draw.polygon(surf, (220, 42, 50), [(cx + 2, cy - 6), (cx + 8, cy - 6), (cx + 8, cy + 12), (cx + 5, cy + 12)])
        for ox in (-5, 0, 5):
            pygame.draw.circle(surf, (255, 232, 104), (cx + ox, cy - 9), 4)
    elif kind == "pretzel":
        col = (176, 102, 40)
        pygame.draw.circle(surf, col, (cx - 6, cy), 7, 3)
        pygame.draw.circle(surf, col, (cx + 6, cy), 7, 3)
        pygame.draw.arc(surf, col, (cx - 11, cy - 2, 22, 16), 0.2, 2.9, 3)
    elif kind == "icecream":
        pygame.draw.polygon(surf, (196, 126, 64), [(cx - 7, cy + 1), (cx + 7, cy + 1), (cx, cy + 17)])
        pygame.draw.circle(surf, (246, 218, 232), (cx - 3, cy - 2), 6)
        pygame.draw.circle(surf, (150, 215, 230), (cx + 4, cy - 3), 6)
    elif kind == "candy":
        pygame.draw.circle(surf, (238, 70, 145), (cx, cy), 8)
        pygame.draw.polygon(surf, (245, 210, 230), [(cx - 8, cy), (cx - 16, cy - 5), (cx - 16, cy + 5)])
        pygame.draw.polygon(surf, (245, 210, 230), [(cx + 8, cy), (cx + 16, cy - 5), (cx + 16, cy + 5)])
    elif kind == "soda":
        pygame.draw.rect(surf, (80, 160, 220), (cx - 7, cy - 10, 14, 22), border_radius=2)
        pygame.draw.rect(surf, (245, 245, 245), (cx - 5, cy - 4, 10, 6))
        pygame.draw.line(surf, (245, 245, 245), (cx + 3, cy - 10), (cx + 10, cy - 18), 2)
    else:
        pygame.draw.rect(surf, (236, 180, 80), (cx - 11, cy - 3, 22, 7), border_radius=4)
        pygame.draw.rect(surf, (210, 70, 55), (cx - 8, cy - 6, 16, 4), border_radius=2)


def _draw_food_stand(surf, x, y, kind):
    body = pygame.Rect(int(x - 24), int(y - 18), 48, 36)
    pygame.draw.rect(surf, (54, 42, 44), body.move(3, 4), border_radius=4)
    pygame.draw.rect(surf, (236, 214, 156), body, border_radius=4)
    pygame.draw.rect(surf, (178, 54, 64), (body.x, body.y, body.w, 10), border_radius=4)
    for sx in range(body.x + 4, body.right - 4, 10):
        pygame.draw.rect(surf, (248, 244, 224), (sx, body.y, 5, 10))
    pygame.draw.rect(surf, (60, 46, 40), (body.x + 8, body.y + 18, 32, 13), border_radius=2)
    _draw_food_icon(surf, kind, body.centerx, body.y - 9)


def draw_amusement_park(surf, cam):
    s = current()
    for park in s.amusement_parks:
        rect = pygame.Rect(park.x - cam[0], park.y - cam[1], park.w, park.h)
        if rect.right < -120 or rect.left > W + 120 or rect.bottom < -120 or rect.top > H + 120:
            continue
        pygame.draw.rect(surf, (52, 122, 78), rect)
        pygame.draw.rect(surf, (174, 78, 92), rect, 5)
        gate = pygame.Rect(rect.left + 34, rect.bottom - 70, 76, 50)
        pygame.draw.rect(surf, (112, 48, 66), gate, border_radius=4)
        pygame.draw.polygon(surf, (236, 198, 78), [(gate.left - 8, gate.top), (gate.centerx, gate.top - 36), (gate.right + 8, gate.top)])
        pygame.draw.rect(surf, (42, 36, 40), (gate.centerx - 12, gate.bottom - 28, 24, 28))
        pygame.draw.circle(surf, (244, 214, 86), (gate.centerx, gate.top - 12), 9)

        path = [(x - cam[0], y - cam[1]) for x, y in _amusement_path_points(park)]
        _draw_flat_path(surf, path, (128, 86, 52), 42)
        _draw_flat_path(surf, path, (214, 178, 118), 28)
        for idx, (x, y) in enumerate(path[::10]):
            pygame.draw.circle(surf, (246, 216, 92), (int(x), int(y)), 4)
            pygame.draw.circle(surf, (78, 54, 42), (int(x), int(y + 7)), 2)

        t = s.traffic_time
        _draw_roller_coaster(surf, rect, t)
        _draw_ferris_wheel(surf, rect.right - 235, rect.top + 245, t)
        _draw_carousel(surf, rect.left + 245, rect.top + 285, t)

        for x, y, kind in s.amusement_stands:
            if park.collidepoint(x, y):
                _draw_food_stand(surf, x - cam[0], y - cam[1], kind)

        for i in range(20):
            px = rect.left + 60 + (i * 97) % max(1, rect.w - 120)
            py = rect.top + 64 + (i * 151) % max(1, rect.h - 128)
            if i % 5 == 0:
                pygame.draw.circle(surf, (238, 82, 92), (int(px), int(py)), 5)
                pygame.draw.line(surf, (235, 235, 230), (int(px), int(py + 5)), (int(px), int(py + 21)), 1)
            else:
                pygame.draw.circle(surf, (46, 96, 58), (int(px), int(py)), 10)
                pygame.draw.circle(surf, (84, 150, 82), (int(px - 4), int(py - 4)), 6)


def draw_park_street_closures(surf, cam):
    s = current()
    road_half = ROAD_W // 2
    margin = ROAD_W // 2 + SIDEWALK_W
    for park in list(s.parks) + list(s.amusement_parks):
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
    road_half = ROAD_W // 2

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

    for seg in s.road_segments:
        if seg.axis == "h":
            sy = seg.fixed - cam[1]
            if -sidewalk_total - 20 < sy < H + sidewalk_total + 20:
                pygame.draw.rect(surf, SIDEW, (seg.lo - cam[0], sy - sidewalk_total // 2, seg.length, sidewalk_total))
        else:
            sx = seg.fixed - cam[0]
            if -sidewalk_total - 20 < sx < W + sidewalk_total + 20:
                pygame.draw.rect(surf, SIDEW, (sx - sidewalk_total // 2, seg.lo - cam[1], sidewalk_total, seg.length))
    for seg in s.road_segments:
        if seg.axis == "h":
            sy = seg.fixed - cam[1]
            if -ROAD_W < sy < H + ROAD_W:
                pygame.draw.rect(surf, ASPHALT, (seg.lo - cam[0], sy - ROAD_W // 2, seg.length, ROAD_W))
                draw_h_curb(seg.fixed - road_half, seg.lo, seg.hi)
                draw_h_curb(seg.fixed + road_half, seg.lo, seg.hi)
        else:
            sx = seg.fixed - cam[0]
            if -ROAD_W < sx < W + ROAD_W:
                pygame.draw.rect(surf, ASPHALT, (sx - ROAD_W // 2, seg.lo - cam[1], ROAD_W, seg.length))
                draw_v_curb(seg.fixed - road_half, seg.lo, seg.hi)
                draw_v_curb(seg.fixed + road_half, seg.lo, seg.hi)
    draw_center_lines(surf, cam)
    draw_crosswalks(surf, cam)
    draw_traffic_lights(surf, cam)
    draw_park_street_closures(surf, cam)
    draw_amusement_park(surf, cam)
    draw_parks(surf, cam)
