"""Small world overview rendered into the HUD."""
import pygame

from game2d.config import W, WORLD_W, WORLD_H, ROAD_W, WATER_W
from game2d.systems.services import garage_layout


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


def draw_minimap(screen, state, font):
    rect = pygame.Rect(W - 236, 10, 216, 216)
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    panel.fill((30, 68, 36, 220))

    water_px = max(2, int((WATER_W / WORLD_W) * rect.w))
    pygame.draw.rect(panel, (24, 62, 115), (0, 0, rect.w, water_px))
    pygame.draw.rect(panel, (24, 62, 115), (0, rect.h - water_px, rect.w, water_px))
    pygame.draw.rect(panel, (24, 62, 115), (0, 0, water_px, rect.h))
    pygame.draw.rect(panel, (24, 62, 115), (rect.w - water_px, 0, water_px, rect.h))

    road_px = max(3, int((ROAD_W / WORLD_W) * rect.w))

    for x in state.roads_v:
        mx, _ = _local_point(x, 0, rect)
        pygame.draw.rect(panel, (64, 64, 68), (mx - road_px // 2, 0, road_px, rect.h))
    for y in state.roads_h:
        _, my = _local_point(0, y, rect)
        pygame.draw.rect(panel, (64, 64, 68), (0, my - road_px // 2, rect.w, road_px))

    line_col = (205, 190, 70)
    for x in state.roads_v:
        mx, _ = _local_point(x, 0, rect)
        pygame.draw.line(panel, line_col, (mx, 0), (mx, rect.h), 1)
    for y in state.roads_h:
        _, my = _local_point(0, y, rect)
        pygame.draw.line(panel, line_col, (0, my), (rect.w, my), 1)

    for building_rect, _ in state.buildings:
        br = _local_rect(building_rect, rect)
        pygame.draw.rect(panel, (120, 100, 80), br)
        if br.w > 2 and br.h > 2:
            pygame.draw.rect(panel, (165, 145, 112), br, 1)

    for gx, gy in state.garages:
        building, driveway, apron = garage_layout(gx, gy)
        pygame.draw.rect(panel, (82, 84, 88), _local_rect(driveway, rect))
        pygame.draw.rect(panel, (90, 96, 104), _local_rect(apron, rect))
        pygame.draw.rect(panel, (34, 100, 148), _local_rect(building, rect))

    screen.blit(panel, rect.topleft)
    pygame.draw.rect(screen, (70, 76, 84), rect, 2)

    for gx, gy in state.garages:
        pygame.draw.circle(screen, (80, 180, 255), _map_point(gx, gy, rect), 4)
    for sx, sy in state.shops:
        pygame.draw.circle(screen, (60, 220, 90), _map_point(sx, sy, rect), 4)
    for c in state.cars:
        if c.is_cop and not c.dead:
            pygame.draw.circle(screen, (80, 120, 255), _map_point(c.x, c.y, rect), 2)

    actor = state.in_car if state.in_car else state.player
    pygame.draw.circle(screen, (255, 235, 70), _map_point(actor.x, actor.y, rect), 5)
    title = font.render("MAP", 1, (220, 220, 220))
    screen.blit(title, (rect.x + 8, rect.y + 6))
