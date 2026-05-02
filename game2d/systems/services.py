"""Garage, shop and wanted escalation helpers."""
import math
import random

import pygame

from game2d.config import ROAD_LO, ROAD_HI_X, ROAD_HI_Y, ROAD_W
from game2d.systems import audio


SHOP_ITEMS = {
    1: ("Health +50", 120, "health"),
    2: ("SMG ammo +120", 180, "ammo_2"),
    3: ("Shotgun ammo +20", 240, "ammo_3"),
    4: ("MG ammo +200", 360, "ammo_4"),
    5: ("RPG ammo +5", 700, "ammo_5"),
    6: ("Wanted -1", 500, "wanted"),
}

GARAGE_ITEMS = {
    1: ("Repair car", 150, "repair"),
    2: ("Repaint car", 80, "repaint"),
    3: ("Wanted -2", 300, "clear_wanted"),
}


def init_services(state):
    """Place service markers near reachable roads."""
    state.garages[:] = [
        (ROAD_LO + 160, ROAD_LO + 160),
        (ROAD_HI_X - 160, ROAD_HI_Y - 160),
    ]
    state.shops[:] = [
        (ROAD_HI_X - 45, ROAD_LO + 45),
        (ROAD_LO + 45, ROAD_HI_Y - 45),
    ]
    clear = []
    for gx, gy in state.garages:
        clear.extend(garage_layout(gx, gy))
    state.buildings[:] = [
        item for item in state.buildings
        if not any(item[0].colliderect(area.inflate(12, 12)) for area in clear)
    ]
    state.AI_OBSTACLES[:] = (
        list(state.buildings)
        + [(r, None) for r in state.WATER_RECTS]
        + [(r, None) for r in state.parks]
    )


def _pos(state):
    actor = state.in_car if state.in_car else state.player
    return actor.x, actor.y


def garage_layout(x, y):
    building = pygame.Rect(int(x - 58), int(y - 38), 116, 76)
    if x < (ROAD_LO + ROAD_HI_X) / 2:
        driveway = pygame.Rect(ROAD_LO + 44, int(y - 16), int(building.left - (ROAD_LO + 44)), 32)
        apron = pygame.Rect(int(x - 36), int(y + 30), 72, 28)
    else:
        driveway = pygame.Rect(building.right, int(y - 16), int((ROAD_HI_X - 44) - building.right), 32)
        apron = pygame.Rect(int(x - 36), int(y - 58), 72, 28)
    return building, driveway, apron


def nearby_service(state, radius=85):
    x, y = _pos(state)
    for gx, gy in state.garages:
        building, driveway, apron = garage_layout(gx, gy)
        if building.inflate(radius, radius).collidepoint(x, y) or driveway.inflate(18, 18).collidepoint(x, y) or apron.inflate(18, 18).collidepoint(x, y):
            return "garage"
    for sx, sy in state.shops:
        if math.hypot(x - sx, y - sy) <= radius:
            return "shop"
    return ""


def set_message(state, text, seconds=2.0):
    state.message = text
    state.message_timer = seconds


def add_money(player, amount):
    player.money += amount
    player.total_money_earned = getattr(player, "total_money_earned", 0) + amount


def spend(state, price):
    if state.player.money < price:
        set_message(state, "Not enough money")
        return False
    state.player.money -= price
    return True


def buy_shop_item(state, key):
    item = SHOP_ITEMS.get(key)
    if not item:
        return
    label, price, action = item
    if not spend(state, price):
        return
    if action == "health":
        state.player.hp = min(100, state.player.hp + 50)
    elif action == "wanted":
        state.player.wanted = max(0, state.player.wanted - 1)
        state.player.crime_timer = 25
    else:
        weapon = int(action.split("_")[1])
        state.unlocked_weapons.add(weapon)
        state.ammo[weapon] = state.ammo.get(weapon, 0) + {2: 120, 3: 20, 4: 200, 5: 5}[weapon]
    set_message(state, f"Bought {label}")


def use_garage_item(state, key):
    item = GARAGE_ITEMS.get(key)
    if not item:
        return
    label, price, action = item
    if action in ("repair", "repaint") and not state.in_car:
        set_message(state, "You need a car")
        return
    if not spend(state, price):
        return
    if action == "repair":
        state.in_car.hp = state.in_car.max_hp
        state.in_car.burning = False
        state.in_car.dents.clear()
    elif action == "repaint":
        from game2d.render.sprites import make_car_sprite

        state.in_car.sprite = make_car_sprite(
            (random.randint(70, 230), random.randint(70, 230), random.randint(70, 230))
        )
        state.in_car.dents.clear()
        lose_cops_after_repaint(state)
    elif action == "clear_wanted":
        state.player.wanted = max(0, state.player.wanted - 2)
        state.player.crime_timer = 25
    set_message(state, f"Done: {label}")


def shop_lines():
    return [f"{key}. {label} ${price}" for key, (label, price, _) in SHOP_ITEMS.items()]


def garage_lines(in_car):
    lines = [f"{key}. {label} ${price}" for key, (label, price, _) in GARAGE_ITEMS.items()]
    if not in_car:
        lines.insert(0, "Drive a car inside for repair/repaint")
    return lines


class Roadblock:
    def __init__(self, x, y, road_axis):
        self.x = x
        self.y = y
        self.road_axis = road_axis
        self.road_key = (road_axis, int(x if road_axis == "v" else y))
        if road_axis == "v":
            self.rect = pygame.Rect(0, 0, ROAD_W + 34, 24)
        else:
            self.rect = pygame.Rect(0, 0, 24, ROAD_W + 34)
        self.rect.center = (int(x), int(y))

    def draw(self, surf, cam):
        cx = self.x - cam[0]
        cy = self.y - cam[1]
        barrier = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
        pygame.draw.rect(barrier, (238, 238, 230), barrier.get_rect(), border_radius=3)
        pygame.draw.rect(barrier, (55, 55, 60), barrier.get_rect().inflate(-6, -14), border_radius=2)
        if self.road_axis == "v":
            for x in range(-18, self.rect.w + 8, 26):
                pygame.draw.polygon(barrier, (220, 40, 35), [(x, self.rect.h), (x + 15, self.rect.h), (x + 35, 0), (x + 20, 0)])
            cone_offsets = [(-self.rect.w // 2 - 8, 0), (self.rect.w // 2 + 8, 0)]
        else:
            for y in range(-18, self.rect.h + 8, 26):
                pygame.draw.polygon(barrier, (220, 40, 35), [(0, y + 20), (0, y + 35), (self.rect.w, y + 15), (self.rect.w, y)])
            cone_offsets = [(0, -self.rect.h // 2 - 8), (0, self.rect.h // 2 + 8)]
        surf.blit(barrier, barrier.get_rect(center=(cx, cy)))
        for ox, oy in cone_offsets:
            x = int(cx + ox)
            y = int(cy + oy)
            pygame.draw.polygon(surf, (245, 120, 25), [(x, y - 10), (x - 8, y + 9), (x + 8, y + 9)])
            pygame.draw.rect(surf, (245, 245, 245), (x - 6, y + 2, 12, 3))


def _near_intersection(x, y, state, margin=105):
    return any(abs(x - rx) < margin for rx in state.roads_v) and any(abs(y - ry) < margin for ry in state.roads_h)


def _roadblock_spawn_near(state, tx, ty):
    for _ in range(220):
        road_axis = "v" if random.random() < 0.5 else "h"
        dist = random.uniform(300, 850)
        sign = -1 if random.random() < 0.5 else 1
        if road_axis == "v":
            roads = [rx for rx in state.roads_v if abs(rx - tx) <= 900] or sorted(state.roads_v, key=lambda rx: abs(rx - tx))[:4]
            x = random.choice(roads)
            y = max(ROAD_LO + 80, min(ROAD_HI_Y - 80, ty + sign * dist))
        else:
            x = max(ROAD_LO + 80, min(ROAD_HI_X - 80, tx + sign * dist))
            roads = [ry for ry in state.roads_h if abs(ry - ty) <= 900] or sorted(state.roads_h, key=lambda ry: abs(ry - ty))[:4]
            y = random.choice(roads)
        road_key = (road_axis, int(x if road_axis == "v" else y))
        if any(other.road_key == road_key for other in state.roadblocks):
            continue
        roadblock = Roadblock(x, y, road_axis)
        probe = roadblock.rect.inflate(70, 70)
        if _near_intersection(x, y, state):
            continue
        if any(probe.colliderect(other.rect) for other in state.roadblocks):
            continue
        if any(probe.colliderect(c.rect()) for c in state.cars if not c.dead):
            continue
        if any(probe.colliderect(b[0]) for b in state.buildings):
            continue
        if any(probe.colliderect(park) for park in state.parks):
            continue
        return roadblock
    return None


def _spawn_roadblock_cop_car(state, roadblock):
    from game2d.entities.car import Car

    car = Car(roadblock.x, roadblock.y, (245, 245, 250), is_cop=True)
    side = -1 if random.random() < 0.5 else 1
    if roadblock.road_axis == "v":
        car.x = roadblock.x + random.choice([-28, 28])
        car.y = roadblock.y + side * 96
        car.angle = 0 if side < 0 else 180
    else:
        car.x = roadblock.x + side * 96
        car.y = roadblock.y + random.choice([-28, 28])
        car.angle = 90 if side < 0 else 270
    car.spd = 0
    car.ai_spd = 0
    car.yield_timer = 2.0
    car.is_roadblock_support = True
    return car


def escalate_police(state):
    """Small wanted-level extras beyond normal cop spawns."""
    wanted = state.player.wanted
    if wanted < 3:
        state.roadblocks.clear()
        for car in list(state.cars):
            if getattr(car, "is_roadblock_support", False) and car is not state.in_car:
                if car._siren_channel is not None:
                    audio.stop_loop(car._siren_channel)
                    car._siren_channel = None
                state.cars.remove(car)
        return
    limit = 4 if wanted == 3 else 7 if wanted == 4 else 10
    while len(state.roadblocks) < limit:
        target = state.in_car if state.in_car else state.player
        roadblock = _roadblock_spawn_near(state, target.x, target.y)
        if roadblock is None:
            break
        car = _spawn_roadblock_cop_car(state, roadblock)
        state.cars.append(car)
        state.roadblocks.append(roadblock)


def lose_cops_after_repaint(state):
    """Repaint hides the player while they stay in the repainted car."""
    if not state.in_car:
        return
    state.player.wanted = 0
    state.player.crime_timer = 0
    state.cops.clear()
    state.roadblocks.clear()
    for car in list(state.cars):
        if car.is_cop and car is not state.in_car:
            if car._siren_channel is not None:
                audio.stop_loop(car._siren_channel)
                car._siren_channel = None
            state.cars.remove(car)
    set_message(state, "Repainted - cops lost")


def cop_damage_for_wanted(wanted):
    return 12 + max(0, wanted - 2) * 4


def cop_fire_rate_for_wanted(wanted):
    return max(0.65, 1.5 - max(0, wanted - 2) * 0.2)
