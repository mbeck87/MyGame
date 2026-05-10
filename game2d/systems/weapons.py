"""Waffenlogik: Schießen und Maus-Zielwinkel."""
import math
import random
import pygame

from game2d.config import WPN_RATE, WPN_DMG, WPN_PEL, WPN_SPRD
from game2d.state import current
from game2d.systems import audio
from game2d.systems.services import add_wanted_heat


LIGHTSABER_IDX = 0


_SHOT_SOUND = {
    1: 'shoot_pistol',
    2: 'shoot_smg',
    3: 'shoot_shotgun',
    4: 'shoot_mg',
}


def aim_to_mouse():
    """Maus → Spielwelt-Winkel (Grad). Spieler-zentriert."""
    s = current()
    mx, my = pygame.mouse.get_pos()
    cx = s.player.x - s.cam[0]
    cy = s.player.y - s.cam[1]
    return math.degrees(math.atan2(mx - cx, -(my - cy)))


def _angle_diff(a, b):
    return abs(((a - b + 180) % 360) - 180)


def _lightsaber_swing():
    s = current()
    if s.in_car:
        return
    p = s.player
    swing_range = 56
    swing_arc = 78
    s.lightsaber_swings.append([p.aim_angle, 0.0, 0.18])
    audio.play('lightsaber_swing', pos=(p.x, p.y))

    for car in s.cars:
        if car.dead or car is s.in_car:
            continue
        dx, dy = car.x - p.x, car.y - p.y
        dist = math.hypot(dx, dy)
        if dist <= swing_range + 12 and _angle_diff(math.degrees(math.atan2(dx, -dy)), p.aim_angle) <= swing_arc * 0.5:
            car.take_damage(WPN_DMG[LIGHTSABER_IDX], source_pos=(p.x, p.y))
            audio.play('hit_metal', volume=0.7, pos=(car.x, car.y))
            add_wanted_heat(s, "assault")

    for ped, group, reward in (
        *((ped, s.peds, (15, 45)) for ped in list(s.peds)),
        *((cop, s.cops, (50, 90)) for cop in list(s.cops)),
    ):
        dx, dy = ped.x - p.x, ped.y - p.y
        dist = math.hypot(dx, dy)
        if dist > swing_range or _angle_diff(math.degrees(math.atan2(dx, -dy)), p.aim_angle) > swing_arc * 0.5:
            continue
        from game2d.systems.effects import make_corpse, spawn_blood
        from game2d.systems.services import add_money

        ped.hp -= WPN_DMG[LIGHTSABER_IDX]
        ped.state = 'flee'
        spawn_blood(ped.x, ped.y, 8)
        audio.play('hit_flesh', pos=(ped.x, ped.y))
        if ped.hp <= 0 and ped in group:
            group.remove(ped)
            s.corpses.append((make_corpse(ped), ped.x, ped.y, ped.angle))
            spawn_blood(ped.x, ped.y, 20)
            add_money(p, random.randint(*reward))
            add_wanted_heat(s, "kill_cop" if ped.is_cop else "kill_ped")


def fire():
    """Aktuelle Waffe abfeuern (state.weapon). Setzt state.fire_cd."""
    s = current()
    weapon = s.weapon
    if weapon < 0 or weapon >= len(WPN_RATE):
        weapon = LIGHTSABER_IDX
        s.weapon = weapon
    if weapon != 0 and s.ammo[weapon] <= 0: return
    if weapon == 0:
        s.fire_cd = WPN_RATE[weapon]
        _lightsaber_swing()
        return
    s.ammo[weapon] -= 1
    s.fire_cd = WPN_RATE[weapon]
    if s.in_car and s.in_car.kind != "motorcycle":
        ax, ay = s.in_car.x, s.in_car.y
        ang = s.in_car.angle
    else:
        ax, ay = s.player.x, s.player.y
        ang = s.player.aim_angle
    snd = _SHOT_SOUND.get(weapon)
    if snd:
        audio.play(snd, pos=(ax, ay))
    if weapon == 5:
        rad = math.radians(ang)
        ch = audio.start_loop('shoot_rocket', pos=(ax, ay))
        s.rockets.append([ax, ay, math.sin(rad)*480, -math.cos(rad)*480, 2.0, ch])
        return
    for _ in range(WPN_PEL[weapon]):
        a = ang + random.uniform(-WPN_SPRD[weapon], WPN_SPRD[weapon]) * 57
        rad = math.radians(a)
        s.bullets.append([ax, ay, math.sin(rad)*900, -math.cos(rad)*900, 0.6, False, WPN_DMG[weapon]])
