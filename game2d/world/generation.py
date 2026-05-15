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
from game2d.world.airport import airport_building_rects, build_airport_rect
from game2d.world.geometry import RoadSegment, rect_overlaps_street_space, rebuild_pedestrian_graph
from game2d.world.traffic import build_traffic_controls


COMMERCIAL_KINDS = {"bar", "restaurant", "disco", "supermarket", "fastfood"}
SPECIAL_LIMITS = {
    "bar": 8,
    "restaurant": 10,
    "disco": 4,
    "supermarket": 5,
    "fastfood": 8,
    "highrise": 16,
}


def _pre_render_amusement_park_sprites(state):
    """Pre-render static amusement park elements into sprites for faster rendering.
    This renders the base, paths, buildings, stands, and static decorations once
    instead of redrawing them every frame.
    """
    from game2d.render.world_bg import (
        _draw_flat_path, _draw_park_gate, _draw_ticket_building,
        _draw_wc_building, _draw_fountain, _draw_lottery_stand,
        _draw_claw_machine_base, _draw_strongman_base, _draw_pirate_ship_base,
        _draw_bumper_arena, _draw_swing_ride_base, _draw_planter, _draw_bench,
        _amusement_new_layout, _draw_food_stand
    )
    
    state.amusement_park_sprites[:] = []
    
    for park in state.amusement_parks:
        # Create a surface large enough to hold the entire park
        # No padding - surface size matches park size exactly for performance
        padding = 0
        surf = pygame.Surface(
            (int(park.w), int(park.h)),
            pygame.SRCALPHA
        )
        
        # Render offset: we render at (padding, padding) so elements at (0,0) in park space
        # go to (padding, padding) on the surface
        render_offset_x = padding
        render_offset_y = padding
        
        # Helper to adjust positions from world to sprite space
        def adjust_pos(rx, ry):
            return rx - park.x + render_offset_x, ry - park.y + render_offset_y
        
        # Draw base rectangle
        pygame.draw.rect(surf, (52, 122, 78), (render_offset_x, render_offset_y, park.w, park.h))
        pygame.draw.rect(surf, (174, 78, 92), (render_offset_x, render_offset_y, park.w, park.h), 5)
        
        # Get cached path segments
        park_idx = state.amusement_parks.index(park)
        if park_idx < len(state.amusement_path_segments):
            cached_segments = state.amusement_path_segments[park_idx]
            path_segments = cached_segments
        else:
            from game2d.world.geometry import amusement_path_segments
            path_segments = amusement_path_segments(park)
        
        # Draw paths (shifted by render offset)
        for path in path_segments:
            shifted_path = [(x + render_offset_x - park.x, y + render_offset_y - park.y) for x, y in path]
            _draw_flat_path(surf, shifted_path, (128, 86, 52), 42)
        for path in path_segments:
            shifted_path = [(x + render_offset_x - park.x, y + render_offset_y - park.y) for x, y in path]
            _draw_flat_path(surf, shifted_path, (214, 178, 118), 28)
        for path in path_segments:
            for i, (x, y) in enumerate(path[::10]):
                px = x + render_offset_x - park.x
                py = y + render_offset_y - park.y
                pygame.draw.circle(surf, (246, 216, 92), (int(px), int(py)), 4)
                pygame.draw.circle(surf, (78, 54, 42), (int(px), int(py + 7)), 2)
        
        # Draw stands for this park
        for x, y, kind in state.amusement_stands:
            if park.collidepoint(x, y):
                _draw_food_stand(surf, x - park.x + render_offset_x, y - park.y + render_offset_y, kind)
        
        # Calculate layout positions relative to park
        outer_right = park.right - int(park.w * 0.12)
        outer_bottom = park.bottom - int(park.h * 0.12)
        outer_left = park.left + int(park.w * 0.12)
        center_x = park.centerx
        center_y = park.top + int(park.h * 0.50)
        
        # Draw static park elements
        _draw_park_gate(surf, outer_right - park.x + render_offset_x, park.bottom - park.y + render_offset_y - 20)
        _draw_ticket_building(surf, 
            outer_right - park.x + render_offset_x - int((outer_right - outer_left) * 0.25), 
            outer_bottom - park.y + render_offset_y - 42)
        _draw_wc_building(surf, 
            outer_right - park.x + render_offset_x - int((outer_right - outer_left) * 0.50), 
            outer_bottom - park.y + render_offset_y - 42)
        
        # Draw fountain at center (static)
        _draw_fountain(surf, center_x - park.x + render_offset_x, center_y - park.y + render_offset_y, 0)
        
        # Get layout for ride area markers (but don't draw ride bases - they are replaced by animated sprites)
        layout = _amusement_new_layout(park)
        
        # Draw coaster area marker (static background)
        coaster_rect = layout['coaster_area'].copy()
        coaster_rect.x += render_offset_x - park.x
        coaster_rect.y += render_offset_y - park.y
        pygame.draw.rect(surf, (42, 104, 64), coaster_rect.inflate(16, 16), border_radius=10)
        
        # Draw lottery stand (static)
        ls_x, ls_y, ls_w, ls_h = layout['lottery_stand']
        _draw_lottery_stand(surf, ls_x - park.x + render_offset_x, ls_y - park.y + render_offset_y, ls_w, ls_h)
        
        # Note: Ride bases (ferris, carousel, swing, strongman, pirate_ship, bumper_arena, claw_machine)
        # are NOT drawn here anymore - they are replaced by the animated sprite frames
        
        for px, py, color, style, flower in layout['planters']:
            _draw_planter(surf, *adjust_pos(px, py), color, style, flower)
        for bx, by, vertical in layout['benches']:
            _draw_bench(surf, *adjust_pos(bx, by), vertical=vertical)
        
        state.amusement_park_sprites.append(surf)


def _pre_render_amusement_park_ride_sprites(state):
    """Pre-render animated ride sprites as sprite sheets for faster rendering.
    Renders multiple frames for each ride animation (ferris wheel, carousel, swing, etc.)
    and stores them for later blitting instead of redrawing every frame.
    """
    import math
    from game2d.render.world_bg import (
        _draw_ferris_wheel, _draw_carousel, _draw_new_roller_coaster,
        _draw_strongman_dynamic, _draw_pirate_ship_dynamic,
        _draw_bumper_cars_dynamic, _draw_swing_ride_dynamic,
        _draw_claw_machine_dynamic, _amusement_new_layout
    )
    
    # Number of frames to pre-render for each animation (36 = 10 degree steps)
    NUM_FRAMES = 36
    
    # Get the first amusement park (we assume there's only one)
    if not state.amusement_parks:
        return
    
    park = state.amusement_parks[0]
    layout = _amusement_new_layout(park)
    
    # Pre-render Ferris Wheel frames
    fw_x, fw_y = layout['ferris']
    fw_frames = []
    for i in range(NUM_FRAMES):
        t = (i / NUM_FRAMES) * math.tau  # 0 to 2*pi
        surf = pygame.Surface((200, 200), pygame.SRCALPHA)
        # Render at center of surface
        _draw_ferris_wheel(surf, 100, 100, t)
        fw_frames.append(surf)
    state.amusement_park_ride_sprites['ferris_wheel'] = fw_frames
    
    # Pre-render Carousel frames
    car_x, car_y = layout['carousel']
    car_frames = []
    for i in range(NUM_FRAMES):
        t = (i / NUM_FRAMES) * math.tau
        surf = pygame.Surface((200, 200), pygame.SRCALPHA)
        _draw_carousel(surf, 100, 100, t)
        car_frames.append(surf)
    state.amusement_park_ride_sprites['carousel'] = car_frames
    
    # Pre-render Swing Ride frames
    sw_x, sw_y = layout['swing']
    swing_frames = []
    for i in range(NUM_FRAMES):
        t = (i / NUM_FRAMES) * math.tau
        surf = pygame.Surface((200, 200), pygame.SRCALPHA)
        _draw_swing_ride_dynamic(surf, 100, 100, t)
        swing_frames.append(surf)
    state.amusement_park_ride_sprites['swing'] = swing_frames
    
    # Pre-render Strongman frames
    sm_x, sm_y = layout['strongman']
    strongman_frames = []
    for i in range(NUM_FRAMES):
        t = (i / NUM_FRAMES) * math.tau
        surf = pygame.Surface((200, 200), pygame.SRCALPHA)
        _draw_strongman_dynamic(surf, 100, 100, t)
        strongman_frames.append(surf)
    state.amusement_park_ride_sprites['strongman'] = strongman_frames
    
    # Pre-render Pirate Ship frames
    ps_x, ps_y = layout['pirate_ship']
    pirate_frames = []
    for i in range(NUM_FRAMES):
        t = (i / NUM_FRAMES) * math.tau
        surf = pygame.Surface((200, 200), pygame.SRCALPHA)
        _draw_pirate_ship_dynamic(surf, 100, 100, t)
        pirate_frames.append(surf)
    state.amusement_park_ride_sprites['pirate_ship'] = pirate_frames
    
    # Pre-render Bumper Cars frames
    ba = layout['bumper_arena']
    bumper_frames = []
    for i in range(NUM_FRAMES):
        t = (i / NUM_FRAMES) * math.tau
        surf = pygame.Surface((400, 250), pygame.SRCALPHA)
        _draw_bumper_cars_dynamic(surf, pygame.Rect(50, 50, 300, 150), t)
        bumper_frames.append(surf)
    state.amusement_park_ride_sprites['bumper_cars'] = bumper_frames
    
    # Pre-render Claw Machine frames
    cm_x, cm_y, cm_w, cm_h = layout['claw_machine']
    claw_frames = []
    for i in range(NUM_FRAMES):
        t = (i / NUM_FRAMES) * math.tau
        surf = pygame.Surface((150, 150), pygame.SRCALPHA)
        _draw_claw_machine_dynamic(surf, 25, 25, cm_w, cm_h, t)
        claw_frames.append(surf)
    state.amusement_park_ride_sprites['claw_machine'] = claw_frames


SPECIAL_MINIMUMS = {
    "disco": 2,
    "supermarket": 3,
    "highrise": 7,
}


def _block_zone(bx, by):
    cx = bx + BLOCK / 2
    cy = by + BLOCK / 2
    center_blocks = max(abs(cx - WORLD_W / 2), abs(cy - WORLD_H / 2)) / BLOCK
    if center_blocks <= 1.7:
        return "downtown"
    if center_blocks <= 3.3:
        return "mixed"
    return "residential"


def _near_same_special(kind, rect, placed_specials):
    margin = BLOCK if kind == "disco" else 170
    if kind == "highrise":
        margin = 120
    probe = rect.inflate(margin, margin)
    return any(other_kind == kind and probe.colliderect(other_rect) for other_kind, other_rect in placed_specials)


def _weighted_choice(weighted):
    total = sum(weight for _, weight in weighted)
    pick = random.uniform(0, total)
    upto = 0
    for kind, weight in weighted:
        upto += weight
        if pick <= upto:
            return kind
    return weighted[-1][0]


def _choose_building_kind(w_cells, h_cells, zone, block_counts, city_counts, rect, placed_specials):
    highrise_chance = {"downtown": 0.30, "mixed": 0.05, "residential": 0.0}[zone]
    if city_counts.get("highrise", 0) < SPECIAL_MINIMUMS["highrise"]:
        highrise_chance = {"downtown": 0.58, "mixed": 0.12, "residential": 0.0}[zone]
    highrise_block_limit = 2 if zone == "downtown" else 1
    if (
        w_cells >= 4 and h_cells >= 5
        and block_counts.get("highrise", 0) < highrise_block_limit
        and city_counts.get("highrise", 0) < SPECIAL_LIMITS["highrise"]
        and not _near_same_special("highrise", rect, placed_specials)
        and random.random() < highrise_chance
    ):
        return "highrise"

    commercial_budget = 2 if zone == "downtown" else 1
    commercial_chance = {"downtown": 0.18, "mixed": 0.09, "residential": 0.02}[zone]
    missing_amenity = (
        zone != "residential"
        and (
            city_counts.get("disco", 0) < SPECIAL_MINIMUMS["disco"]
            or city_counts.get("supermarket", 0) < SPECIAL_MINIMUMS["supermarket"]
        )
    )
    if missing_amenity:
        commercial_chance = max(commercial_chance, 0.22)
    if block_counts.get("commercial", 0) >= commercial_budget or random.random() > commercial_chance:
        return None

    if zone == "downtown":
        weighted = [("restaurant", 3), ("bar", 2), ("fastfood", 2), ("disco", 2), ("supermarket", 1)]
    elif zone == "mixed":
        weighted = [("restaurant", 3), ("bar", 2), ("fastfood", 2), ("supermarket", 2)]
    else:
        weighted = [("restaurant", 2), ("bar", 1), ("fastfood", 1), ("supermarket", 1)]

    min_size = {
        "bar": (3, 3),
        "restaurant": (4, 3),
        "fastfood": (4, 3),
        "supermarket": (5, 4),
        "disco": (5, 4),
    }
    priority = []
    for kind in ("disco", "supermarket"):
        if (
            city_counts.get(kind, 0) < SPECIAL_MINIMUMS.get(kind, 0)
            and w_cells >= min_size[kind][0]
            and h_cells >= min_size[kind][1]
            and city_counts.get(kind, 0) < SPECIAL_LIMITS[kind]
            and not _near_same_special(kind, rect, placed_specials)
            and (kind != "disco" or zone == "downtown")
        ):
            priority.append(kind)
    if priority and random.random() < 0.9:
        return random.choice(priority)

    candidates = [
        (kind, weight + (5 if city_counts.get(kind, 0) < SPECIAL_MINIMUMS.get(kind, 0) else 0))
        for kind, weight in weighted
        if w_cells >= min_size[kind][0]
        and h_cells >= min_size[kind][1]
        and city_counts.get(kind, 0) < SPECIAL_LIMITS[kind]
        and not _near_same_special(kind, rect, placed_specials)
    ]
    if not candidates:
        return None
    return _weighted_choice(candidates)


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


def _build_amusement_park_rect():
    margin = ROAD_W // 2 + SIDEWALK_W
    left = BLOCK * 7 + margin
    top = INNER_LO
    right = INNER_HI_X
    bottom = BLOCK * 3 - margin
    return pygame.Rect(left, top, right - left, bottom - top)


def _central_bank_layout():
    bx = (WORLD_W // 2 // BLOCK) * BLOCK
    by = (WORLD_H // 2 // BLOCK) * BLOCK
    setback = ROAD_W // 2 + SIDEWALK_W + 18
    x0 = max(bx + setback, INNER_LO + SIDEWALK_W + 12)
    y0 = max(by + setback, INNER_LO + SIDEWALK_W + 12)
    x1 = min(bx + BLOCK - setback, INNER_HI_X - SIDEWALK_W - 12)
    y1 = min(by + BLOCK - setback, INNER_HI_Y - SIDEWALK_W - 12)
    w, h = 10 * 32, 6 * 32
    return pygame.Rect(x0 + (x1 - x0 - w) // 2, y0 + (y1 - y0 - h) // 2, w - 4, h - 4)


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


def _build_park_ducks(park):
    cell_w = park.w / 2
    cell_h = park.h / 3
    pond = _park_pond_points(park)

    def fit_to_pond(x, y):
        if _point_in_polygon(x, y, pond):
            return x, y
        for radius in range(6, 120, 6):
            for ox, oy in (
                (radius, 0), (-radius, 0), (0, radius), (0, -radius),
                (radius, radius), (radius, -radius), (-radius, radius), (-radius, -radius),
                (radius * 0.5, radius), (radius * 0.5, -radius),
                (-radius * 0.5, radius), (-radius * 0.5, -radius),
            ):
                px = x + ox
                py = y + oy
                if _point_in_polygon(px, py, pond):
                    return px, py
        return x, y

    ducks = [
        ('drake',    0, None, park.left + cell_w * 0.66, park.top + cell_h * 0.62, 58, 34, 0.36, 0.10),
        ('hen',      0, None, park.left + cell_w * 0.70, park.top + cell_h * 0.68, 54, 32, 0.40, 1.35),
        ('duckling', 0,    0, park.left + cell_w * 0.70, park.top + cell_h * 0.68,  0,  0, 0.40, 1.35),
        ('duckling', 0,    1, park.left + cell_w * 0.70, park.top + cell_h * 0.68,  0,  0, 0.40, 1.35),
        ('duckling', 0,    2, park.left + cell_w * 0.70, park.top + cell_h * 0.68,  0,  0, 0.40, 1.35),
        ('drake',    1, None, park.left + cell_w * 1.12, park.top + cell_h * 0.50, 52, 30, 0.34, 2.20),
        ('hen',      1, None, park.left + cell_w * 1.06, park.top + cell_h * 0.58, 48, 28, 0.38, 4.60),
        ('duckling', 1,    0, park.left + cell_w * 1.06, park.top + cell_h * 0.58,  0,  0, 0.38, 4.60),
        ('duckling', 1,    1, park.left + cell_w * 1.06, park.top + cell_h * 0.58,  0,  0, 0.38, 4.60),
    ]
    fitted = []
    for kind, family, follow_slot, x, y, rx, ry, speed, phase in ducks:
        px, py = fit_to_pond(x, y)
        if _point_in_polygon(px, py, pond):
            fitted.append((kind, family, follow_slot, px, py, rx, ry, speed, phase))
    return fitted


def _build_amusement_stands(park):
    w = park.w
    h = park.h
    outer_left = park.left + w * 0.12
    outer_right = park.right - w * 0.12
    outer_top = park.top + h * 0.12
    outer_bottom = park.bottom - h * 0.12
    offset = 48
    return [
        (outer_right - w * 0.18, outer_bottom + offset, "popcorn"),
        (outer_right - w * 0.38, outer_bottom + offset, "pretzel"),
        (outer_right - w * 0.58, outer_bottom + offset, "icecream"),
        (outer_left - offset, outer_bottom - h * 0.24, "candy"),
        (outer_left - offset, outer_bottom - h * 0.44, "soda"),
        (outer_left - offset, outer_bottom - h * 0.64, "hotdog"),
        (outer_left + w * 0.18, outer_top - offset, "pizza"),
        (outer_left + w * 0.38, outer_top - offset, "burger"),
        (outer_left + w * 0.58, outer_top - offset, "fries"),
        (outer_right + offset, outer_top + h * 0.24, "coffee"),
        (outer_right + offset, outer_top + h * 0.44, "balloons"),
        (outer_right + offset, outer_top + h * 0.64, "souvenirs"),
    ]


def _road_axis_extents(axis, coord):
    road_half = ROAD_W // 2
    if axis == "h":
        if coord == ROAD_LO or coord == ROAD_HI_Y:
            return ROAD_LO - road_half, ROAD_HI_X + road_half
        return ROAD_LO + road_half, ROAD_HI_X - road_half
    if coord == ROAD_LO or coord == ROAD_HI_X:
        return ROAD_LO - road_half, ROAD_HI_Y + road_half
    return ROAD_LO + road_half, ROAD_HI_Y - road_half


def _subtract_ranges(start, end, cuts, min_len=ROAD_W):
    ranges = [(start, end)]
    for cut_start, cut_end in sorted(cuts):
        next_ranges = []
        for lo, hi in ranges:
            c0 = max(lo, cut_start)
            c1 = min(hi, cut_end)
            if c1 <= lo or c0 >= hi:
                next_ranges.append((lo, hi))
                continue
            if c0 - lo >= min_len:
                next_ranges.append((lo, c0))
            if hi - c1 >= min_len:
                next_ranges.append((c1, hi))
        ranges = next_ranges
    return ranges


def _build_road_segments(state):
    road_half = ROAD_W // 2
    blockers = list(state.parks) + list(state.amusement_parks) + list(state.airports)
    segments = []
    for y in state.roads_h:
        start, end = _road_axis_extents("h", y)
        cuts = [
            (park.left, park.right)
            for park in blockers
            if y + road_half > park.top and y - road_half < park.bottom
        ]
        for x0, x1 in _subtract_ranges(start, end, cuts):
            segments.append(RoadSegment("h", (int(x0), int(y)), (int(x1), int(y))))
    for x in state.roads_v:
        start, end = _road_axis_extents("v", x)
        cuts = [
            (park.top, park.bottom)
            for park in blockers
            if x + road_half > park.left and x - road_half < park.right
        ]
        for y0, y1 in _subtract_ranges(start, end, cuts):
            segments.append(RoadSegment("v", (int(x), int(y0)), (int(x), int(y1))))
    return segments


def build_world(state):
    """Initialisiert Wasser, StraÃŸenachsen/-segmente, GebÃ¤ude und AI_OBSTACLES."""
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
    state.amusement_parks[:] = [_build_amusement_park_rect()]
    state.airports[:] = [build_airport_rect()]
    # Cache amusement path segments for performance
    from game2d.world.geometry import amusement_path_segments
    state.amusement_path_segments[:] = [amusement_path_segments(park) for park in state.amusement_parks]
    # Cache amusement park layouts for performance (avoid recalculating every frame)
    from game2d.render.world_bg import _amusement_new_layout
    state.amusement_park_layouts[:] = [_amusement_new_layout(park) for park in state.amusement_parks]
    state.road_segments[:] = _build_road_segments(state)
    build_traffic_controls(state)
    state.park_ponds[:] = [_park_pond_points(park) for park in state.parks]
    state.park_trees[:] = []
    state.park_ducks[:] = []
    state.amusement_stands[:] = []
    bank_rect = _central_bank_layout()
    state.central_bank_rect = None
    city_counts = {}
    placed_specials = []
    for bx in range(0, WORLD_W, BLOCK):
        for by in range(0, WORLD_H, BLOCK):
            zone = _block_zone(bx, by)
            block_counts = {}
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
                if zone == "downtown" and random.random() < 0.45:
                    row_h = random.randint(5, 8)
                elif zone == "mixed" and random.random() < 0.16:
                    row_h = random.randint(4, 6)
                else:
                    row_h = random.randint(3, 5)
                while cur_x < x1 - 60:
                    bw_cells = random.randint(4, 7) if zone == "downtown" and random.random() < 0.35 else random.randint(3, 6)
                    bh = row_h
                    bw = bw_cells * 32
                    bhp = bh * 32
                    if cur_x + bw > x1: break
                    if cur_y + bhp > y1: break
                    rect = pygame.Rect(cur_x, cur_y, bw - 4, bhp - 4)
                    reserved = list(state.parks) + list(state.amusement_parks) + list(state.airports)
                    if any(rect.colliderect(park) for park in reserved) or rect.colliderect(bank_rect.inflate(18, 18)):
                        cur_x += bw + random.randint(4, 14)
                        continue
                    if not rect_overlaps_street_space(rect):
                        kind = _choose_building_kind(bw_cells, bh, zone, block_counts, city_counts, rect, placed_specials)
                        surf = make_building(bw_cells, bh, seed, kind); seed += 1
                        state.buildings.append((rect, surf))
                        if kind:
                            city_counts[kind] = city_counts.get(kind, 0) + 1
                            block_counts[kind] = block_counts.get(kind, 0) + 1
                            placed_specials.append((kind, rect.copy()))
                            if kind in COMMERCIAL_KINDS:
                                block_counts["commercial"] = block_counts.get("commercial", 0) + 1
                    cur_x += bw + random.randint(4, 14)
                cur_y += row_h * 32 + random.randint(8, 18)

    bank_surf = make_building(10, 6, 9001, "bank")
    reserved = list(state.parks) + list(state.amusement_parks) + list(state.airports)
    if not rect_overlaps_street_space(bank_rect) and not any(bank_rect.colliderect(park) for park in reserved):
        state.buildings.append((bank_rect, bank_surf))
        state.central_bank_rect = bank_rect.copy()

    for airport in state.airports:
        for rect in airport_building_rects(airport):
            state.buildings.append((rect, None))

    for park in state.parks:
        state.park_trees.extend(_build_park_trees(park))
        state.park_ducks.extend(_build_park_ducks(park))
    for park in state.amusement_parks:
        state.amusement_stands.extend(_build_amusement_stands(park))

    # Pre-render statischen Amusement Park (wird in _draw_amusement_static verwendet)
    # Die dynamischen Rides werden aus PNG-Sprites geladen (siehe load_amusement_sprites)
    _pre_render_amusement_park_sprites(state)
    # _pre_render_amusement_park_ride_sprites(state)  # Nicht nötig - wir laden PNGs

    state.AI_OBSTACLES[:] = (
        list(state.buildings)
        + [(r, None) for r in state.WATER_RECTS]
        + [(r, None) for r in state.parks]
        + [(r, None) for r in state.amusement_parks]
    )
    rebuild_pedestrian_graph(state)
