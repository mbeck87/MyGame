"""Garage, shop and wanted escalation helpers."""
import math
import random

import pygame

from game2d.config import ROAD_LO, ROAD_HI_X, ROAD_HI_Y


SHOP_ITEMS = {
    1: ("Health +50", 120, "health"),
    2: ("SMG ammo +120", 180, "ammo_2"),
    3: ("Shotgun ammo +20", 240, "ammo_3"),
    4: ("MG ammo +200", 360, "ammo_4"),
    5: ("RPG ammo +5", 700, "ammo_5"),
    6: ("Wanted -1", 500, "wanted"),
    7: ("Lichtschwert", 850, "weapon_6"),
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
    state.AI_OBSTACLES[:] = list(state.buildings) + [(r, None) for r in state.WATER_RECTS]


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
    elif action == "weapon_6":
        state.unlocked_weapons.add(6)
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


def escalate_police(state):
    """Small wanted-level extras beyond normal cop spawns."""
    wanted = state.player.wanted
    if wanted < 3:
        state.roadblocks.clear()
        return
    active = [c for c in state.roadblocks if c in state.cars and not c.dead]
    state.roadblocks[:] = active
    limit = 1 if wanted == 3 else 2 if wanted == 4 else 3
    while len(state.roadblocks) < limit:
        from game2d.entities.car import Car
        from game2d.world.spawning import cop_car_spawn_near

        target = state.in_car if state.in_car else state.player
        x, y, angle = cop_car_spawn_near(target.x, target.y)
        car = Car(x, y, (245, 245, 250), is_cop=True)
        car.angle = (angle + 90) % 360
        car.spd = 0
        car.ai_spd = 0
        car.max_spd = 260
        car.yield_timer = 1.5
        car.is_roadblock = True
        state.cars.append(car)
        state.roadblocks.append(car)


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
            state.cars.remove(car)
    set_message(state, "Repainted - cops lost")


def cop_damage_for_wanted(wanted):
    return 12 + max(0, wanted - 2) * 4


def cop_fire_rate_for_wanted(wanted):
    return max(0.65, 1.5 - max(0, wanted - 2) * 0.2)
