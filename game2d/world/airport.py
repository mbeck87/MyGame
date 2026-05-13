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
    return {
        "runway": runway,
        "taxiway": taxiway,
        "apron": apron,
        "terminal": terminal,
        "hangars": (hangar_west, hangar_east),
        "tower": tower,
        "gate": gate,
    }


def airport_building_rects(airport):
    layout = airport_layout(airport)
    return [
        layout["terminal"],
        *layout["hangars"],
        layout["tower"],
    ]
