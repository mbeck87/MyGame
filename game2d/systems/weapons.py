"""Waffenlogik: Schießen und Maus-Zielwinkel."""
import math
import random
import pygame

from game2d.config import WPN_RATE, WPN_DMG, WPN_PEL, WPN_SPRD
from game2d.state import current


def aim_to_mouse():
    """Maus → Spielwelt-Winkel (Grad). Spieler-zentriert."""
    s = current()
    mx, my = pygame.mouse.get_pos()
    cx = s.player.x - s.cam[0]
    cy = s.player.y - s.cam[1]
    return math.degrees(math.atan2(mx - cx, -(my - cy)))


def fire():
    """Aktuelle Waffe abfeuern (state.weapon). Setzt state.fire_cd."""
    s = current()
    weapon = s.weapon
    if weapon == 0: return
    if s.ammo[weapon] <= 0: return
    s.ammo[weapon] -= 1
    s.fire_cd = WPN_RATE[weapon]
    if s.in_car:
        ax, ay = s.in_car.x, s.in_car.y
        ang = s.in_car.angle
    else:
        ax, ay = s.player.x, s.player.y
        ang = s.player.aim_angle
    if weapon == 5:
        rad = math.radians(ang)
        s.rockets.append([ax, ay, math.sin(rad)*480, -math.cos(rad)*480, 2.0])
        return
    for _ in range(WPN_PEL[weapon]):
        a = ang + random.uniform(-WPN_SPRD[weapon], WPN_SPRD[weapon]) * 57
        rad = math.radians(a)
        s.bullets.append([ax, ay, math.sin(rad)*900, -math.cos(rad)*900, 0.6, False, WPN_DMG[weapon]])
