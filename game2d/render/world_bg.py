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
from game2d.world.geometry import amusement_path_segments as _amusement_path_segments
from game2d.world.geometry import amusement_stand_rect
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


def _draw_new_roller_coaster(surf, area, t):
    pygame.draw.rect(surf, (38, 92, 58), area.inflate(18, 18), border_radius=10)
    pygame.draw.rect(surf, (42, 104, 64), area.inflate(10, 10), border_radius=8)
    ground_y = area.bottom - 12
    pygame.draw.rect(surf, (52, 124, 70), (area.left - 4, ground_y - 8, area.w + 8, 20), border_radius=5)
    pygame.draw.line(surf, (92, 142, 74), (area.left - 2, ground_y - 8), (area.right + 2, ground_y - 8), 2)

    station = pygame.Rect(area.left + 14, area.bottom - 70, 116, 52)
    pygame.draw.rect(surf, (42, 30, 26), station.move(4, 5), border_radius=4)
    pygame.draw.rect(surf, (178, 62, 70), station, border_radius=4)
    pygame.draw.rect(surf, (100, 42, 48), station, 2, border_radius=4)
    pygame.draw.polygon(surf, (238, 194, 70), [
        (station.left - 8, station.top + 6),
        (station.centerx, station.top - 24),
        (station.right + 8, station.top + 6),
    ])
    pygame.draw.line(surf, (120, 74, 38), (station.left - 4, station.top + 6), (station.right + 4, station.top + 6), 2)
    for sx in range(station.left + 12, station.right - 8, 17):
        pygame.draw.line(surf, (230, 204, 118), (sx, station.top + 10), (sx, station.top + 23), 2)
    entry_door = pygame.Rect(station.left + 12, station.bottom - 24, 30, 24)
    exit_door = pygame.Rect(station.right - 42, station.bottom - 24, 30, 24)
    for door, label in ((entry_door, "EIN"), (exit_door, "AUS")):
        pygame.draw.rect(surf, (44, 34, 30), door, border_radius=2)
        pygame.draw.rect(surf, (238, 206, 118), (door.left + 4, door.top + 4, door.w - 8, 8), border_radius=1)
        _draw_centered_label(surf, label, (door.centerx, door.top + 8), 12, (82, 48, 32))
    platform = pygame.Rect(station.left + 8, station.top + 25, station.w - 16, 7)
    pygame.draw.rect(surf, (92, 48, 42), platform, border_radius=2)

    def p(rx, ry):
        return area.left + area.w * rx, area.top + area.h * ry

    def bezier_points(a, b, c, d, count=34):
        points = []
        for i in range(count):
            u = i / (count - 1)
            inv = 1 - u
            x = inv**3 * a[0] + 3 * inv**2 * u * b[0] + 3 * inv * u**2 * c[0] + u**3 * d[0]
            y = inv**3 * a[1] + 3 * inv**2 * u * b[1] + 3 * inv * u**2 * c[1] + u**3 * d[1]
            points.append((x, y))
        return points

    station_track_y = station.bottom - 6
    station_entry = (entry_door.centerx, station_track_y)
    station_exit = (exit_door.centerx, station_track_y)
    start = station_exit
    end = station_entry
    lcx, lcy = p(0.63, 0.45)
    loop_r = min(area.w * 0.086, area.h * 0.27)
    loop_bottom = (lcx, lcy + loop_r)
    loop_points = []
    for i in range(73):
        u = i / 72
        ang = math.radians(90) - math.tau * u
        loop_points.append((lcx + math.cos(ang) * loop_r, lcy + math.sin(ang) * loop_r))

    samples = [station_entry]
    curves = (
        (start, p(0.23, 0.83), p(0.26, 0.77), p(0.29, 0.70)),
        (p(0.29, 0.70), p(0.31, 0.39), p(0.34, 0.14), p(0.39, 0.16)),
        (p(0.39, 0.16), p(0.46, 0.15), p(0.47, 0.76), p(0.53, 0.75)),
        (p(0.53, 0.75), p(0.57, 0.76), p(0.59, 0.69), loop_bottom),
    )
    for curve_idx, curve in enumerate(curves):
        pts = bezier_points(*curve, count=30)
        if curve_idx:
            pts = pts[1:]
        samples.extend(pts)
    samples.extend(loop_points[1:])
    return_curves = (
        (loop_points[-1], p(0.72, 0.76), p(0.76, 0.23), p(0.83, 0.27)),
        (p(0.83, 0.27), p(0.92, 0.38), p(0.96, 0.70), p(0.90, 0.74)),
        (p(0.90, 0.74), p(0.72, 0.86), p(0.50, 0.82), p(0.34, 0.76)),
        (p(0.34, 0.76), p(0.24, 0.82), p(0.15, 0.86), end),
    )
    for curve in return_curves:
        samples.extend(bezier_points(*curve, count=30)[1:])

    pts_i = [(int(x), int(y)) for x, y in samples]
    support_points = []
    station_clear = station.inflate(18, 28)
    for i in range(6, len(pts_i) - 6, 15):
        x, y = pts_i[i]
        if station_clear.collidepoint(x, y) or ground_y - y < 22:
            continue
        support_points.append((x, y, ground_y))
    for x, y, base_y in support_points:
        pygame.draw.line(surf, (62, 62, 68), (x, y + 4), (x, base_y), 3)
        pygame.draw.line(surf, (142, 142, 150), (x + 1, y + 5), (x + 1, base_y - 2), 1)
        pygame.draw.ellipse(surf, (54, 54, 58), (x - 10, base_y - 3, 20, 6))
    for prev, cur in zip(support_points, support_points[1:]):
        ax, ay, abase = prev
        bx, by, bbase = cur
        if abs(bx - ax) > 42:
            continue
        pygame.draw.line(surf, (86, 86, 94), (ax, abase - 8), (bx, by + 8), 1)
        pygame.draw.line(surf, (86, 86, 94), (ax, ay + 8), (bx, bbase - 8), 1)

    pygame.draw.lines(surf, (34, 52, 34), False, pts_i, 9)
    pygame.draw.lines(surf, (82, 26, 32), False, pts_i, 7)
    pygame.draw.lines(surf, (220, 58, 66), False, pts_i, 4)
    pygame.draw.lines(surf, (252, 142, 132), False, pts_i, 1)
    for i in range(0, len(pts_i), 8):
        x, y = pts_i[i]
        pygame.draw.circle(surf, (100, 36, 42), (x, y), 2)
        pygame.draw.circle(surf, (248, 160, 144), (x, y - 1), 1)

    travel_points = samples
    if math.hypot(samples[-1][0] - samples[0][0], samples[-1][1] - samples[0][1]) > 0.01:
        travel_points = samples + [samples[0]]
    segment_lengths = []
    total_len = 0.0
    for a, b in zip(travel_points, travel_points[1:]):
        seg_len = math.hypot(b[0] - a[0], b[1] - a[1])
        segment_lengths.append(seg_len)
        total_len += seg_len

    def point_on_track(distance):
        distance %= total_len
        walked = 0.0
        for i, seg_len in enumerate(segment_lengths):
            if walked + seg_len >= distance:
                a = travel_points[i]
                b = travel_points[i + 1]
                frac = 0.0 if seg_len <= 0 else (distance - walked) / seg_len
                x = a[0] + (b[0] - a[0]) * frac
                y = a[1] + (b[1] - a[1]) * frac
                ang = math.atan2(b[1] - a[1], b[0] - a[0])
                return x, y, ang
            walked += seg_len
        a = travel_points[-2]
        b = travel_points[-1]
        return b[0], b[1], math.atan2(b[1] - a[1], b[0] - a[0])

    train_head = (t * 116) % total_len
    station_hide = pygame.Rect(station.left - 8, station.top - 20, station.w + 18, station.h + 36)
    car_cols = ((42, 92, 210), (58, 140, 226), (242, 186, 60), (220, 64, 78))
    for car_no, gap in enumerate((0, 26, 52, 78)):
        x, y, ang = point_on_track(train_head - gap)
        if station_hide.collidepoint(x, y):
            continue
        ux, uy = math.cos(ang), math.sin(ang)
        nx, ny = -uy, ux
        if ny > 0:
            nx, ny = -nx, -ny
        x += nx * 7
        y += ny * 7
        body = []
        for lx, ly in ((-12, -8), (13, -7), (14, 6), (-13, 7)):
            body.append((int(x + ux * lx + nx * ly), int(y + uy * lx + ny * ly)))
        pygame.draw.polygon(surf, (26, 24, 34), [(px + 2, py + 3) for px, py in body])
        pygame.draw.polygon(surf, car_cols[car_no], body)
        pygame.draw.lines(surf, (22, 24, 34), True, body, 1)
        pygame.draw.line(surf, (238, 238, 230),
                         (int(x + ux * -5 + nx * -4), int(y + uy * -5 + ny * -4)),
                         (int(x + ux * 8 + nx * -4), int(y + uy * 8 + ny * -4)), 2)
        for lx in (-8, 8):
            wx = int(x + ux * lx - nx * 7)
            wy = int(y + uy * lx - ny * 7)
            pygame.draw.circle(surf, (24, 24, 28), (wx, wy), 3)
            pygame.draw.circle(surf, (198, 198, 204), (wx, wy), 1)


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
    elif kind == "hotdog":
        pygame.draw.rect(surf, (236, 180, 80), (cx - 11, cy - 3, 22, 7), border_radius=4)
        pygame.draw.rect(surf, (210, 70, 55), (cx - 8, cy - 6, 16, 4), border_radius=2)
    elif kind == "pizza":
        pygame.draw.polygon(surf, (238, 190, 72), [(cx - 10, cy - 8), (cx + 12, cy - 2), (cx - 6, cy + 16)])
        pygame.draw.line(surf, (164, 92, 42), (cx - 10, cy - 8), (cx + 12, cy - 2), 3)
        for ox, oy in ((-2, 1), (4, 4), (-5, 8)):
            pygame.draw.circle(surf, (196, 50, 48), (cx + ox, cy + oy), 2)
    elif kind == "burger":
        bun = pygame.Rect(cx - 13, cy - 12, 26, 14)
        pygame.draw.ellipse(surf, (226, 158, 70), bun)
        pygame.draw.rect(surf, (226, 158, 70), (cx - 13, cy - 5, 26, 7))
        for ox, oy in ((-7, -7), (-1, -9), (6, -7)):
            pygame.draw.circle(surf, (252, 224, 126), (cx + ox, cy + oy), 1)
        pygame.draw.rect(surf, (88, 52, 34), (cx - 12, cy - 1, 24, 5), border_radius=2)
        pygame.draw.rect(surf, (80, 164, 74), (cx - 11, cy + 4, 22, 3), border_radius=1)
        pygame.draw.rect(surf, (226, 158, 70), (cx - 12, cy + 7, 24, 5), border_radius=2)
    elif kind == "fries":
        for ox in (-7, -3, 1, 5):
            pygame.draw.rect(surf, (248, 214, 72), (cx + ox, cy - 14, 3, 17))
        pygame.draw.polygon(surf, (214, 54, 58), [(cx - 10, cy - 2), (cx + 10, cy - 2), (cx + 7, cy + 15), (cx - 7, cy + 15)])
    elif kind == "coffee":
        pygame.draw.rect(surf, (238, 238, 228), (cx - 8, cy - 4, 16, 16), border_radius=3)
        pygame.draw.arc(surf, (238, 238, 228), (cx + 5, cy, 10, 8), -1.4, 1.4, 2)
        pygame.draw.rect(surf, (90, 58, 38), (cx - 6, cy - 1, 12, 5), border_radius=2)
        pygame.draw.line(surf, (222, 222, 216), (cx - 4, cy - 13), (cx - 7, cy - 20), 1)
        pygame.draw.line(surf, (222, 222, 216), (cx + 3, cy - 12), (cx + 5, cy - 20), 1)
    elif kind == "balloons":
        for ox, oy, col in ((-7, -8, (230, 70, 86)), (1, -12, (72, 156, 230)), (8, -6, (238, 202, 68))):
            pygame.draw.circle(surf, col, (cx + ox, cy + oy), 6)
            pygame.draw.line(surf, (230, 230, 220), (cx + ox, cy + oy + 6), (cx, cy + 15), 1)
    else:
        pygame.draw.rect(surf, (120, 80, 54), (cx - 12, cy - 5, 24, 16), border_radius=3)
        pygame.draw.rect(surf, (224, 188, 116), (cx - 8, cy - 12, 16, 9), border_radius=2)
        pygame.draw.circle(surf, (228, 80, 92), (cx - 4, cy - 7), 2)


def _draw_food_stand(surf, x, y, kind):
    body = amusement_stand_rect(x, y)
    pygame.draw.rect(surf, (54, 42, 44), body.move(3, 4), border_radius=4)
    pygame.draw.rect(surf, (236, 214, 156), body, border_radius=4)
    pygame.draw.rect(surf, (178, 54, 64), (body.x, body.y, body.w, 10), border_radius=4)
    for sx in range(body.x + 4, body.right - 4, 10):
        pygame.draw.rect(surf, (248, 244, 224), (sx, body.y, 5, 10))
    pygame.draw.rect(surf, (60, 46, 40), (body.x + 8, body.y + 18, 32, 13), border_radius=2)
    _draw_food_icon(surf, kind, body.centerx, body.y - 9)


def _draw_bench(surf, x, y, vertical=True):
    if vertical:
        pygame.draw.rect(surf, (44, 30, 22), (x - 14, y - 3, 28, 10), border_radius=2)
        pygame.draw.rect(surf, (124, 88, 56), (x - 14, y - 3, 28, 5), border_radius=2)
        for sx in (x - 11, x - 4, x + 3, x + 10):
            pygame.draw.line(surf, (74, 50, 32), (sx, y - 2), (sx, y + 6), 1)
        pygame.draw.rect(surf, (54, 38, 26), (x - 14, y - 8, 28, 4), border_radius=2)
    else:
        pygame.draw.rect(surf, (44, 30, 22), (x - 3, y - 14, 10, 28), border_radius=2)
        pygame.draw.rect(surf, (124, 88, 56), (x - 3, y - 14, 5, 28), border_radius=2)
        pygame.draw.rect(surf, (54, 38, 26), (x - 8, y - 14, 4, 28), border_radius=2)


def _draw_planter_flower(surf, x, y, color, kind):
    leaf_col = (70, 142, 70)
    if kind == "tulip":
        pygame.draw.line(surf, leaf_col, (x, y + 5), (x, y - 2), 2)
        pygame.draw.polygon(surf, color, [(x - 4, y - 2), (x, y - 8), (x + 4, y - 2), (x + 2, y + 2), (x - 2, y + 2)])
        pygame.draw.line(surf, (248, 226, 124), (x, y - 6), (x, y - 2), 1)
    elif kind == "star":
        for i in range(5):
            ang = -math.pi / 2 + i * math.tau / 5
            px = int(x + math.cos(ang) * 4)
            py = int(y + math.sin(ang) * 4)
            pygame.draw.circle(surf, color, (px, py), 2)
        pygame.draw.circle(surf, (250, 230, 110), (x, y), 2)
    elif kind == "grass":
        for ox in (-4, -1, 2, 5):
            pygame.draw.line(surf, leaf_col, (x + ox, y + 5), (x + ox - 2, y - 6), 2)
        pygame.draw.circle(surf, color, (x + 1, y - 7), 2)
    elif kind == "mixed":
        for ox, oy, col in ((-3, 0, color), (2, -4, (244, 202, 68)), (5, 1, (86, 172, 230))):
            pygame.draw.circle(surf, leaf_col, (x + ox - 1, y + oy + 2), 3)
            pygame.draw.circle(surf, col, (x + ox, y + oy), 2)
            pygame.draw.circle(surf, (250, 230, 110), (x + ox, y + oy), 1)
    else:
        pygame.draw.circle(surf, leaf_col, (x - 2, y + 1), 4)
        pygame.draw.circle(surf, leaf_col, (x + 2, y + 1), 4)
        pygame.draw.circle(surf, color, (x, y), 3)
        pygame.draw.circle(surf, (250, 230, 110), (x, y), 1)


def _draw_planter(surf, x, y, color=(220, 80, 90), style="round", flower="dot"):
    if style == "box":
        pygame.draw.rect(surf, (54, 38, 24), (x - 18, y - 5, 38, 17), border_radius=4)
        pygame.draw.rect(surf, (128, 82, 48), (x - 20, y - 8, 38, 16), border_radius=4)
        pygame.draw.rect(surf, (170, 112, 64), (x - 18, y - 6, 34, 5), border_radius=2)
        spots = ((-12, -12), (-4, -15), (5, -13), (13, -11))
    elif style == "tall":
        pygame.draw.ellipse(surf, (54, 38, 24), (x - 12, y + 4, 26, 8))
        pygame.draw.polygon(surf, (120, 78, 50), [(x - 10, y - 7), (x + 10, y - 7), (x + 7, y + 11), (x - 7, y + 11)])
        pygame.draw.ellipse(surf, (164, 108, 70), (x - 12, y - 11, 24, 9))
        pygame.draw.ellipse(surf, (76, 56, 34), (x - 9, y - 9, 18, 5))
        spots = ((-5, -18), (0, -22), (6, -17))
    elif style == "bowl":
        pygame.draw.ellipse(surf, (54, 38, 24), (x - 16, y + 4, 34, 10))
        pygame.draw.ellipse(surf, (134, 90, 56), (x - 17, y - 6, 34, 18))
        pygame.draw.arc(surf, (190, 124, 76), (x - 16, y - 8, 32, 18), 0, math.pi, 3)
        spots = ((-10, -10), (-3, -13), (5, -12), (11, -9))
    else:
        pygame.draw.circle(surf, (54, 38, 24), (x + 2, y + 3), 14)
        pygame.draw.circle(surf, (118, 80, 48), (x, y), 13)
        pygame.draw.circle(surf, (158, 110, 70), (x, y), 13, 2)
        spots = []
        for i in range(5):
            ang = i * math.tau / 5
            spots.append((math.cos(ang) * 6, math.sin(ang) * 6))

    for ox, oy in spots:
        fx = int(x + ox)
        fy = int(y + oy)
        _draw_planter_flower(surf, fx, fy, color, flower)


def _draw_lottery_stand(surf, x, y, w, h):
    body = pygame.Rect(x, y, w, h)
    pygame.draw.rect(surf, (42, 30, 26), body.move(4, 5), border_radius=4)
    pygame.draw.rect(surf, (232, 208, 154), body, border_radius=4)
    pygame.draw.rect(surf, (118, 76, 46), body, 2, border_radius=4)

    roof = pygame.Rect(x - 7, y - 17, w + 14, 21)
    pygame.draw.rect(surf, (48, 34, 28), roof.move(3, 4), border_radius=4)
    pygame.draw.rect(surf, (248, 236, 174), roof, border_radius=4)
    stripe_w = 12
    for sx in range(roof.left, roof.right, stripe_w * 2):
        pygame.draw.rect(surf, (210, 52, 62), (sx, roof.top, stripe_w, roof.h), border_radius=3)
    pygame.draw.rect(surf, (90, 48, 40), roof, 2, border_radius=4)

    sign = pygame.Rect(x + 16, y - 33, w - 32, 19)
    pygame.draw.rect(surf, (238, 196, 64), sign, border_radius=3)
    pygame.draw.rect(surf, (98, 48, 36), sign, 2, border_radius=3)
    _draw_centered_label(surf, "LOSE", sign.center, 18, (84, 42, 34))

    shelf = pygame.Rect(x + 8, y + 12, w - 16, 17)
    pygame.draw.rect(surf, (70, 44, 34), shelf, border_radius=2)
    for i, col in enumerate(((232, 62, 74), (70, 154, 220), (242, 200, 68), (90, 190, 110))):
        px = shelf.left + 12 + i * 21
        pygame.draw.circle(surf, col, (px, shelf.centery), 6)
        pygame.draw.circle(surf, (248, 242, 222), (px - 2, shelf.centery - 2), 2)

    counter = pygame.Rect(x + 6, y + h - 23, w - 12, 17)
    pygame.draw.rect(surf, (130, 76, 44), counter, border_radius=3)
    pygame.draw.rect(surf, (84, 48, 32), counter, 2, border_radius=3)
    for i in range(5):
        tx = counter.left + 10 + i * 16
        ticket = pygame.Rect(tx, counter.top - 8 + (i % 2), 11, 12)
        pygame.draw.rect(surf, (248, 230, 132), ticket, border_radius=1)
        pygame.draw.line(surf, (182, 80, 62), (ticket.left + 3, ticket.top + 3), (ticket.right - 3, ticket.top + 3), 1)
        pygame.draw.line(surf, (182, 80, 62), (ticket.left + 3, ticket.top + 7), (ticket.right - 3, ticket.top + 7), 1)

    drum_cx = x + w - 24
    drum_cy = y + h - 35
    pygame.draw.circle(surf, (90, 50, 38), (drum_cx, drum_cy), 15)
    pygame.draw.circle(surf, (230, 84, 76), (drum_cx, drum_cy), 13)
    pygame.draw.circle(surf, (248, 214, 94), (drum_cx, drum_cy), 6)
    pygame.draw.line(surf, (70, 44, 34), (drum_cx - 14, drum_cy + 15), (drum_cx + 14, drum_cy + 15), 2)


def _draw_centered_label(surf, text, center, size=22, color=(44, 32, 24)):
    font = pygame.font.Font(None, size)
    label = font.render(text, True, color)
    surf.blit(label, label.get_rect(center=center))


def _draw_park_gate(surf, x, y):
    pygame.draw.rect(surf, (72, 42, 36), (x - 72, y - 74, 14, 98), border_radius=3)
    pygame.draw.rect(surf, (72, 42, 36), (x + 58, y - 74, 14, 98), border_radius=3)
    pygame.draw.rect(surf, (128, 58, 64), (x - 78, y - 82, 156, 24), border_radius=5)
    pygame.draw.rect(surf, (238, 198, 76), (x - 84, y - 104, 168, 30), border_radius=4)
    pygame.draw.rect(surf, (96, 48, 42), (x - 84, y - 104, 168, 30), 2, border_radius=4)
    _draw_centered_label(surf, "Freizeit Park", (x, y - 88), 24, (74, 36, 32))
    for ox in (-48, -16, 16, 48):
        pygame.draw.circle(surf, (248, 220, 96), (x + ox, y - 59), 4)


def _draw_ticket_building(surf, x, y):
    body = pygame.Rect(int(x - 34), int(y - 24), 68, 48)
    pygame.draw.rect(surf, (44, 34, 28), body.move(4, 5), border_radius=4)
    pygame.draw.rect(surf, (228, 206, 164), body, border_radius=4)
    pygame.draw.rect(surf, (118, 82, 58), body, 2, border_radius=4)
    roof = pygame.Rect(body.left - 5, body.top - 10, body.w + 10, 15)
    pygame.draw.rect(surf, (176, 56, 58), roof, border_radius=4)
    pygame.draw.rect(surf, (92, 34, 34), roof, 2, border_radius=4)
    win = pygame.Rect(body.left + 10, body.top + 10, body.w - 20, 18)
    pygame.draw.rect(surf, (40, 62, 82), win, border_radius=2)
    pygame.draw.rect(surf, (130, 190, 220), win.inflate(-3, -3), border_radius=2)
    pygame.draw.rect(surf, (82, 48, 32), (win.left + 19, win.top + 11, 10, 5), border_radius=2)
    _draw_centered_label(surf, "KASSE", (body.centerx, body.bottom - 8), 14, (72, 44, 30))


def _draw_wc_building(surf, x, y):
    body = pygame.Rect(int(x - 38), int(y - 25), 76, 50)
    pygame.draw.rect(surf, (36, 34, 36), body.move(4, 5), border_radius=4)
    pygame.draw.rect(surf, (206, 214, 214), body, border_radius=4)
    pygame.draw.rect(surf, (82, 92, 96), body, 2, border_radius=4)
    pygame.draw.rect(surf, (68, 92, 128), (body.left - 4, body.top - 10, body.w + 8, 15), border_radius=4)
    _draw_centered_label(surf, "WC", (body.centerx, body.top - 2), 16, (238, 238, 232))
    doors = (pygame.Rect(body.left + 10, body.top + 15, 22, 29), pygame.Rect(body.right - 32, body.top + 15, 22, 29))
    for door in doors:
        pygame.draw.rect(surf, (66, 70, 76), door, border_radius=2)
    _draw_centered_label(surf, "M", doors[0].center, 18, (88, 158, 238))
    _draw_centered_label(surf, "W", doors[1].center, 18, (238, 96, 170))


def _draw_fountain(surf, cx, cy, t):
    pygame.draw.ellipse(surf, (132, 118, 98), (cx - 118, cy - 72, 236, 144))
    pygame.draw.ellipse(surf, (180, 150, 104), (cx - 108, cy - 62, 216, 124))
    pygame.draw.ellipse(surf, (72, 142, 180), (cx - 68, cy - 32, 136, 64))
    pygame.draw.ellipse(surf, (126, 198, 224), (cx - 52, cy - 23, 104, 42))
    pygame.draw.rect(surf, (164, 156, 138), (cx - 13, cy - 42, 26, 44), border_radius=4)
    pygame.draw.ellipse(surf, (200, 194, 176), (cx - 24, cy - 51, 48, 18))
    spray_layers = (
        (8, 22, 15, 16, 1.6, 0.0),
        (10, 35, 26, 27, 1.25, 0.18),
        (12, 52, 38, 39, 1.0, 0.08),
    )
    for count, reach, lift, fall, speed, phase in spray_layers:
        for i in range(count):
            ang = t * speed + phase + i * math.tau / count
            side = math.cos(ang)
            depth = math.sin(ang)
            sx = cx + side * 6
            sy = cy - 49 + depth * 3
            mx = cx + side * reach * 0.55
            my = cy - 50 - lift + depth * 8
            ex = cx + side * reach
            ey = cy - 48 + fall + depth * 13
            pts = []
            for step in range(7):
                u = step / 6
                inv = 1 - u
                x = inv * inv * sx + 2 * inv * u * mx + u * u * ex
                y = inv * inv * sy + 2 * inv * u * my + u * u * ey
                pts.append((int(x), int(y)))
            pygame.draw.lines(surf, (190, 234, 248), False, pts, 1 if reach < 30 else 2)
    pygame.draw.circle(surf, (232, 248, 255), (cx, cy - 60 - int(math.sin(t * 3) * 3)), 4)


def _amusement_new_layout(rect):
    w = rect.w
    h = rect.h
    outer_left = rect.left + int(w * 0.12)
    outer_right = rect.right - int(w * 0.12)
    outer_bottom = rect.bottom - int(h * 0.12)
    center_x = rect.centerx
    center_y = rect.top + int(h * 0.50)
    return {
        'carousel': (outer_left + int(w * 0.10), center_y + int(h * 0.11)),
        'ferris': (outer_left + int(w * 0.22), outer_bottom - 120),
        'swing': (outer_right - int(w * 0.16), outer_bottom - 135),
        'bumper_arena': pygame.Rect(outer_right - 390, rect.top + int(h * 0.16), 310, 170),
        'coaster_area': pygame.Rect(outer_left + 54, rect.top + int(h * 0.17), 500, 160),
        'lottery_stand': (outer_right - 148, center_y + int(h * 0.15), 118, 68),
        'planters': (
            (center_x - 150, center_y - 88, (86, 172, 230), "box", "tulip"),
            (center_x, center_y - 118, (96, 194, 112), "box", "grass"),
            (center_x + 150, center_y - 88, (238, 112, 76), "tall", "tulip"),
            (center_x - 150, center_y + 88, (244, 210, 70), "tall", "star"),
            (center_x, center_y + 118, (218, 92, 196), "bowl", "mixed"),
            (center_x + 150, center_y + 88, (242, 236, 110), "bowl", "grass"),
        ),
        'benches': (
            (outer_left + 180, rect.top + int(h * 0.12) + 30, True),
            (outer_right - 180, rect.top + int(h * 0.12) + 30, True),
            (outer_left + 180, outer_bottom - 30, True),
            (outer_right - 180, outer_bottom - 30, True),
        ),
    }


def _draw_bumper_arena(surf, rect):
    pygame.draw.rect(surf, (38, 26, 18), rect.move(5, 6), border_radius=10)
    pygame.draw.rect(surf, (148, 102, 64), rect, border_radius=10)
    inner = rect.inflate(-14, -14)
    pygame.draw.rect(surf, (94, 64, 40), inner, border_radius=8)
    pygame.draw.rect(surf, (188, 142, 90), inner, 2, border_radius=8)
    plank_h = 18
    for py in range(inner.top + 8, inner.bottom - 4, plank_h):
        pygame.draw.line(surf, (66, 44, 28), (inner.left + 6, py), (inner.right - 6, py), 1)
    for i in range(0, rect.w, 22):
        for ly in (rect.top + 4, rect.bottom - 4):
            cx = rect.left + 6 + i
            if cx >= rect.right - 4:
                break
            pygame.draw.circle(surf, (252, 240, 130), (cx, ly), 3)
            pygame.draw.circle(surf, (255, 255, 220), (cx - 1, ly - 1), 1)
    for i in range(0, rect.h, 22):
        for lx in (rect.left + 4, rect.right - 4):
            cy = rect.top + 6 + i
            if cy >= rect.bottom - 4:
                break
            pygame.draw.circle(surf, (252, 240, 130), (lx, cy), 3)
            pygame.draw.circle(surf, (255, 255, 220), (lx - 1, cy - 1), 1)


def _draw_swing_ride_base(surf, cx, cy):
    pygame.draw.ellipse(surf, (30, 22, 16), (cx - 38, cy + 22, 76, 24))
    pygame.draw.ellipse(surf, (148, 102, 64), (cx - 34, cy + 18, 68, 20))
    pygame.draw.ellipse(surf, (200, 158, 100), (cx - 30, cy + 16, 60, 14))
    pygame.draw.rect(surf, (44, 42, 46), (cx - 8, cy - 30, 16, 50))
    pygame.draw.rect(surf, (108, 108, 116), (cx - 6, cy - 30, 12, 50))
    pygame.draw.rect(surf, (60, 60, 66), (cx - 7, cy - 30, 14, 4))
    pygame.draw.circle(surf, (180, 50, 60), (cx, cy - 32), 24)
    pygame.draw.circle(surf, (228, 100, 110), (cx, cy - 32), 20)
    pygame.draw.circle(surf, (88, 30, 36), (cx, cy - 32), 24, 2)
    for i in range(8):
        ang = i * math.tau / 8
        rx = int(cx + math.cos(ang) * 20)
        ry = int(cy - 32 + math.sin(ang) * 20)
        pygame.draw.circle(surf, (250, 220, 90), (rx, ry), 2)


def _draw_swing_ride_dynamic(surf, cx, cy, t):
    spin = t * 1.5
    chairs = 8
    cable_origin_y = cy - 32
    for i in range(chairs):
        ang = spin + i * math.tau / chairs
        ux = math.cos(ang)
        uy = math.sin(ang) * 0.42
        bx = cx + ux * 14
        by = cable_origin_y + uy * 14
        cx_chair = cx + ux * 50
        cy_chair = cy - 18 + uy * 50
        pygame.draw.line(surf, (160, 160, 168), (int(bx), int(by)), (int(cx_chair), int(cy_chair) - 4), 1)
        col = ((230, 80, 70), (245, 200, 70), (60, 152, 220), (90, 200, 110))[i % 4]
        pygame.draw.rect(surf, (40, 30, 26),
                         (int(cx_chair - 5), int(cy_chair - 3), 10, 8), border_radius=1)
        pygame.draw.rect(surf, col,
                         (int(cx_chair - 4), int(cy_chair - 2), 8, 7), border_radius=1)
        pygame.draw.circle(surf, (240, 200, 160),
                           (int(cx_chair), int(cy_chair - 5)), 2)


def _draw_bumper_cars_dynamic(surf, rect, t):
    car_data = (
        (0.0, (230, 80, 70)),
        (1.7, (245, 200, 70)),
        (3.1, (60, 152, 220)),
        (4.6, (96, 200, 110)),
        (5.9, (240, 130, 60)),
        (7.4, (200, 90, 220)),
    )
    inner = rect.inflate(-32, -32)
    cx = inner.centerx
    cy = inner.centery
    rx = inner.w / 2 - 14
    ry = inner.h / 2 - 14
    for phase, col in car_data:
        u = t * 0.9 + phase
        x = cx + math.cos(u * 0.83 + phase) * rx * 0.9
        y = cy + math.sin(u * 1.17 + phase * 1.4) * ry * 0.9
        ang = u * 1.6 + phase
        ux, uy = math.cos(ang), math.sin(ang)
        vx, vy = -uy, ux
        body = []
        for lx, ly in ((-9, -8), (10, -7), (12, 7), (-11, 8)):
            body.append((int(x + ux * lx + vx * ly), int(y + uy * lx + vy * ly)))
        nose = (int(x + ux * 14), int(y + uy * 14))
        mast_base = (int(x - ux * 7), int(y - uy * 7))
        mast_top = (mast_base[0], mast_base[1] - 18)
        pygame.draw.polygon(surf, (28, 18, 14), [(p[0] + 2, p[1] + 3) for p in body])
        pygame.draw.polygon(surf, col, body)
        pygame.draw.lines(surf, (24, 24, 28), True, body, 2)
        pygame.draw.line(surf, (245, 226, 132), body[0], body[1], 2)
        pygame.draw.line(surf, (240, 240, 220),
                         (int(x + ux * -4 + vx * -3), int(y + uy * -4 + vy * -3)),
                         (int(x + ux * 6 + vx * -3), int(y + uy * 6 + vy * -3)), 2)
        pygame.draw.circle(surf, (246, 214, 174), (int(x - ux * 1), int(y - uy * 1)), 4)
        pygame.draw.circle(surf, (34, 34, 38), (int(x + ux * 5), int(y + uy * 5)), 3)
        pygame.draw.line(surf, (34, 34, 38),
                         (int(x + ux * 5 + vx * -4), int(y + uy * 5 + vy * -4)),
                         (int(x + ux * 5 + vx * 4), int(y + uy * 5 + vy * 4)), 1)
        pygame.draw.circle(surf, (250, 236, 124), nose, 2)
        pygame.draw.line(surf, (188, 188, 196), mast_base, mast_top, 1)
        pygame.draw.circle(surf, (245, 245, 235), mast_top, 2)


def _draw_amusement_static(surf, cam):
    s = current()
    for park in s.amusement_parks:
        rect = pygame.Rect(park.x - cam[0], park.y - cam[1], park.w, park.h)
        if rect.right < -120 or rect.left > W + 120 or rect.bottom < -120 or rect.top > H + 120:
            continue
        pygame.draw.rect(surf, (52, 122, 78), rect)
        pygame.draw.rect(surf, (174, 78, 92), rect, 5)

        path_segments = [[(x - cam[0], y - cam[1]) for x, y in segment] for segment in _amusement_path_segments(park)]
        for path in path_segments:
            _draw_flat_path(surf, path, (128, 86, 52), 42)
        for path in path_segments:
            _draw_flat_path(surf, path, (214, 178, 118), 28)
        for path in path_segments:
            for idx, (x, y) in enumerate(path[::10]):
                pygame.draw.circle(surf, (246, 216, 92), (int(x), int(y)), 4)
                pygame.draw.circle(surf, (78, 54, 42), (int(x), int(y + 7)), 2)

        for x, y, kind in s.amusement_stands:
            if park.collidepoint(x, y):
                _draw_food_stand(surf, x - cam[0], y - cam[1], kind)

        outer_right = rect.right - int(rect.w * 0.12)
        outer_bottom = rect.bottom - int(rect.h * 0.12)
        outer_left = rect.left + int(rect.w * 0.12)
        center_x = rect.centerx
        center_y = rect.top + int(rect.h * 0.50)
        _draw_park_gate(surf, outer_right, rect.bottom - 20)
        _draw_ticket_building(surf, outer_right - int((outer_right - outer_left) * 0.25), outer_bottom - 42)
        _draw_wc_building(surf, outer_right - int((outer_right - outer_left) * 0.50), outer_bottom - 42)
        _draw_fountain(surf, center_x, center_y, current().traffic_time)
        layout = _amusement_new_layout(rect)
        pygame.draw.rect(surf, (42, 104, 64), layout['coaster_area'].inflate(16, 16), border_radius=10)
        _draw_lottery_stand(surf, *layout['lottery_stand'])
        _draw_bumper_arena(surf, layout['bumper_arena'])
        _draw_swing_ride_base(surf, layout['swing'][0], layout['swing'][1])
        for px, py, color, style, flower in layout['planters']:
            _draw_planter(surf, px, py, color, style, flower)
        for bx, by, vertical in layout['benches']:
            _draw_bench(surf, bx, by, vertical=vertical)


def _draw_amusement_dynamic(surf, cam):
    s = current()
    for park in s.amusement_parks:
        rect = pygame.Rect(park.x - cam[0], park.y - cam[1], park.w, park.h)
        if rect.right < -120 or rect.left > W + 120 or rect.bottom < -120 or rect.top > H + 120:
            continue
        layout = _amusement_new_layout(rect)
        t = s.traffic_time
        _draw_new_roller_coaster(surf, layout['coaster_area'], t)
        _draw_carousel(surf, layout['carousel'][0], layout['carousel'][1], t)
        _draw_ferris_wheel(surf, layout['ferris'][0], layout['ferris'][1], t)
        _draw_bumper_cars_dynamic(surf, layout['bumper_arena'], t)
        _draw_swing_ride_dynamic(surf, layout['swing'][0], layout['swing'][1], t)


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


def _draw_parks_static(surf, cam):
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


def _draw_parks_dynamic(surf, cam):
    s = current()
    if s.parks:
        _draw_ducks(surf, cam)


_BG_TILE = 600
_bg_tiles = {}


def _draw_static_layers(surf, cam):
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
    draw_park_street_closures(surf, cam)
    _draw_amusement_static(surf, cam)
    _draw_parks_static(surf, cam)


def _bake_tile(tx, ty):
    tw = min(_BG_TILE, WORLD_W - tx)
    th = min(_BG_TILE, WORLD_H - ty)
    tile = pygame.Surface((tw, th)).convert()
    _draw_static_layers(tile, (tx, ty))
    return tile


def invalidate_world_bg_cache():
    _bg_tiles.clear()


def draw_world_bg(surf, cam):
    surf.fill(WATER_DEEP)
    view_left = int(cam[0])
    view_top = int(cam[1])
    view_right = view_left + W
    view_bottom = view_top + H
    tx_start = max(0, (view_left // _BG_TILE) * _BG_TILE)
    ty_start = max(0, (view_top // _BG_TILE) * _BG_TILE)
    ty = ty_start
    while ty < view_bottom and ty < WORLD_H:
        tx = tx_start
        while tx < view_right and tx < WORLD_W:
            tile = _bg_tiles.get((tx, ty))
            if tile is None:
                tile = _bake_tile(tx, ty)
                _bg_tiles[(tx, ty)] = tile
            surf.blit(tile, (tx - cam[0], ty - cam[1]))
            tx += _BG_TILE
        ty += _BG_TILE
    draw_traffic_lights(surf, cam)
    _draw_amusement_dynamic(surf, cam)
    _draw_parks_dynamic(surf, cam)
