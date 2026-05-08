"""Small world overview rendered into the HUD."""
import pygame

from game2d.config import (
    W, WORLD_W, WORLD_H, ROAD_W, WATER_W,
    INNER_LO, INNER_HI_X, INNER_HI_Y,
)
from game2d.systems.services import garage_layout, shop_layout
from game2d.world.geometry import amusement_path_segments


def _map_point(x, y, rect):
    return (
        rect.x + int((x / WORLD_W) * rect.w),
        rect.y + int((y / WORLD_H) * rect.h),
    )


def _local_point(x, y, rect):
    return int((x / WORLD_W) * rect.w), int((y / WORLD_H) * rect.h)


def _local_rect(world_rect, rect):
    x, y = _local_point(world_rect.x, world_rect.y, rect)
    w = max(1, int((world_rect.w / WORLD_W) * rect.w))
    h = max(1, int((world_rect.h / WORLD_H) * rect.h))
    return pygame.Rect(x, y, w, h)


def _world_rect(x, y, w, h, rect):
    lx, ly = _local_point(x, y, rect)
    lw = max(1, int((w / WORLD_W) * rect.w))
    lh = max(1, int((h / WORLD_H) * rect.h))
    return pygame.Rect(lx, ly, lw, lh)


def _local_polyline(points, rect):
    return [_local_point(x, y, rect) for x, y in points]


def _park_path_points(park):
    cell_w = park.w / 2
    cell_h = park.h / 3
    start = (park.left + 120, park.bottom)
    c1 = (park.left + 120, park.bottom - cell_h * 0.95)
    c2 = (park.right - cell_w * 0.55, park.top + cell_h * 0.95)
    end = (park.right, park.top + cell_h * 0.95)
    points = []
    for i in range(36):
        t = i / 35
        mt = 1 - t
        x = mt**3 * start[0] + 3 * mt**2 * t * c1[0] + 3 * mt * t**2 * c2[0] + t**3 * end[0]
        y = mt**3 * start[1] + 3 * mt**2 * t * c1[1] + 3 * mt * t**2 * c2[1] + t**3 * end[1]
        points.append((x, y))
    return points


def draw_minimap(screen, state, font):
    rect = pygame.Rect(W - 236, 10, 216, 216)
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    panel.fill((24, 62, 115, 220))
    pygame.draw.rect(panel, (195, 175, 120), _world_rect(WATER_W, WATER_W, WORLD_W - 2 * WATER_W, WORLD_H - 2 * WATER_W, rect))
    pygame.draw.rect(panel, (30, 68, 36), _world_rect(INNER_LO, INNER_LO, INNER_HI_X - INNER_LO, INNER_HI_Y - INNER_LO, rect))

    road_px = max(3, int((ROAD_W / WORLD_W) * rect.w))
    for seg in state.road_segments:
        if seg.axis == "h":
            _, my = _local_point(0, seg.fixed, rect)
            mx0, _ = _local_point(seg.lo, 0, rect)
            mx1, _ = _local_point(seg.hi, 0, rect)
            pygame.draw.rect(panel, (64, 64, 68), (mx0, my - road_px // 2, mx1 - mx0, road_px))
        else:
            mx, _ = _local_point(seg.fixed, 0, rect)
            _, my0 = _local_point(0, seg.lo, rect)
            _, my1 = _local_point(0, seg.hi, rect)
            pygame.draw.rect(panel, (64, 64, 68), (mx - road_px // 2, my0, road_px, my1 - my0))

    line_col = (205, 190, 70)
    gap = max(2, road_px // 2 + 1)
    for seg in state.road_segments:
        if seg.axis == "h":
            _, my = _local_point(0, seg.fixed, rect)
            mx0, _ = _local_point(seg.lo, 0, rect)
            mx1, _ = _local_point(seg.hi, 0, rect)
            if mx1 - gap > mx0 + gap:
                pygame.draw.line(panel, line_col, (mx0 + gap, my), (mx1 - gap, my), 1)
        else:
            mx, _ = _local_point(seg.fixed, 0, rect)
            _, my0 = _local_point(0, seg.lo, rect)
            _, my1 = _local_point(0, seg.hi, rect)
            if my1 - gap > my0 + gap:
                pygame.draw.line(panel, line_col, (mx, my0 + gap), (mx, my1 - gap), 1)

    for i, park in enumerate(state.parks):
        pr = _local_rect(park, rect)
        pygame.draw.rect(panel, (42, 135, 56), pr)
        if i < len(state.park_ponds):
            pond = _local_polyline(state.park_ponds[i], rect)
            pygame.draw.polygon(panel, (42, 115, 165), pond)
        path = _local_polyline(_park_path_points(park), rect)
        pygame.draw.lines(panel, (150, 105, 56), False, path, 1)

    for park in state.amusement_parks:
        pr = _local_rect(park, rect)
        pygame.draw.rect(panel, (78, 150, 92), pr)
        for segment in amusement_path_segments(park):
            path = _local_polyline(segment, rect)
            if len(path) >= 2:
                pygame.draw.lines(panel, (214, 178, 118), False, path, 2)
        for x, y, _kind in state.amusement_stands:
            if park.collidepoint(x, y):
                pygame.draw.circle(panel, (238, 204, 84), _local_point(x, y, rect), 1)
        pygame.draw.rect(panel, (210, 88, 110), pr, 1)

    for building_rect, _ in state.buildings:
        br = _local_rect(building_rect, rect)
        pygame.draw.rect(panel, (120, 100, 80), br)
        if br.w > 2 and br.h > 2:
            pygame.draw.rect(panel, (165, 145, 112), br, 1)

    bank_rect = getattr(state, "central_bank_rect", None)
    if bank_rect:
        br = _local_rect(bank_rect, rect)
        pygame.draw.rect(panel, (220, 206, 148), br)
        pygame.draw.rect(panel, (74, 94, 122), br, 1)
        if br.w >= 4 and br.h >= 4:
            pygame.draw.circle(panel, (74, 94, 122), br.center, max(2, min(br.w, br.h) // 4))

    for gx, gy in state.garages:
        building, driveway, apron = garage_layout(gx, gy)
        pygame.draw.rect(panel, (82, 84, 88), _local_rect(driveway, rect))
        pygame.draw.rect(panel, (90, 96, 104), _local_rect(apron, rect))
        pygame.draw.rect(panel, (34, 100, 148), _local_rect(building, rect))
    for sx, sy in state.shops:
        building, walk, _ = shop_layout(sx, sy)
        pygame.draw.rect(panel, (90, 94, 78), _local_rect(walk, rect))
        pygame.draw.rect(panel, (50, 150, 78), _local_rect(building, rect))

    screen.blit(panel, rect.topleft)
    pygame.draw.rect(screen, (70, 76, 84), rect, 2)

    for gx, gy in state.garages:
        pygame.draw.circle(screen, (80, 180, 255), _map_point(gx, gy, rect), 4)
    for sx, sy in state.shops:
        pygame.draw.circle(screen, (60, 220, 90), _map_point(sx, sy, rect), 4)
    for bx, by in state.barbers:
        pygame.draw.circle(screen, (220, 80, 180), _map_point(bx, by, rect), 4)
    for c in state.cars:
        if c.is_cop and not c.dead:
            kind = getattr(c, "kind", "cop")
            col = {
                "cop": (80, 120, 255),
                "fbi": (235, 235, 235),
                "swat": (70, 95, 140),
                "military": (105, 145, 70),
            }.get(kind, (80, 120, 255))
            pygame.draw.circle(screen, col, _map_point(c.x, c.y, rect), 2)
    for roadblock in state.roadblocks:
        pygame.draw.circle(screen, (235, 70, 55), _map_point(roadblock.x, roadblock.y, rect), 3)

    actor = state.in_car if state.in_car else state.player
    pygame.draw.circle(screen, (255, 235, 70), _map_point(actor.x, actor.y, rect), 5)
    title = font.render("MAP", 1, (220, 220, 220))
    screen.blit(title, (rect.x + 8, rect.y + 6))
