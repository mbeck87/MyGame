"""Airport layout helpers."""
import pygame

from game2d.config import BLOCK, ROAD_HI_X, ROAD_HI_Y, ROAD_W, SIDEWALK_W


def build_airport_rect():
    margin = ROAD_W // 2 + SIDEWALK_W
    left = BLOCK * 7 + margin
    top = BLOCK * 7 + margin
    right = ROAD_HI_X - margin
    bottom = ROAD_HI_Y - margin
    return pygame.Rect(left, top, right - left, bottom - top)


def airport_layout(airport):
    """Return stable airport feature rectangles for rendering and collision."""
    runway = pygame.Rect(
        airport.left + 82,
        airport.top + 120,
        airport.w - 164,
        128,
    )
    taxiway = pygame.Rect(
        airport.left + 128,
        runway.bottom + 72,
        airport.w - 256,
        54,
    )
    apron = pygame.Rect(
        airport.left + 190,
        taxiway.bottom + 34,
        airport.w - 310,
        250,
    )
    terminal = pygame.Rect(
        airport.left + 230,
        airport.bottom - 170,
        430,
        116,
    )
    hangar_west = pygame.Rect(
        airport.left + 78,
        airport.bottom - 315,
        150,
        120,
    )
    hangar_east = pygame.Rect(
        airport.right - 300,
        airport.bottom - 360,
        220,
        150,
    )
    tower = pygame.Rect(
        airport.left + 118,
        airport.bottom - 175,
        62,
        62,
    )
    gate = pygame.Rect(
        airport.centerx - 65,
        airport.bottom - 22,
        130,
        44,
    )
    # Airplane parking positions (center x, center y) on apron
    plane_positions = [
        (apron.x + 130, apron.y + 55),
        (apron.x + 240, apron.y + 55),
        (apron.right - 170, apron.y + 55),
        (apron.right - 80, apron.y + 55),
    ]
    # Bounding rects for parked planes (88×68 px, wings span ±44, body ±34)
    airplane_rects = [
        pygame.Rect(px - 44, py - 34, 88, 68) for px, py in plane_positions
    ]

    return {
        "runway": runway,
        "taxiway": taxiway,
        "apron": apron,
        "terminal": terminal,
        "hangars": (hangar_west, hangar_east),
        "tower": tower,
        "gate": gate,
        "airplane_rects": airplane_rects,
        "plane_positions": plane_positions,
    }


def airport_building_rects(airport):
    layout = airport_layout(airport)
    return [
        layout["terminal"],
        *layout["hangars"],
        layout["tower"],
        *layout["airplane_rects"],
    ]
