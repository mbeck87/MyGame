"""Garage, shop and wanted escalation helpers."""
import math
import random

import pygame

from game2d.config import ROAD_LO, ROAD_HI_X, ROAD_HI_Y, ROAD_W, SIDEWALK_W, W, H
from game2d.systems import audio


SHOP_ITEMS = {
    1: ("Health +50", 120, "health"),
    2: ("SMG ammo +120", 180, "ammo_2"),
    3: ("Shotgun ammo +20", 240, "ammo_3"),
    4: ("MG ammo +200", 360, "ammo_4"),
    5: ("RPG ammo +5", 700, "ammo_5"),
    6: ("Wanted -1", 500, "wanted"),
}

WANTED_HEAT_PER_STAR = 100
WANTED_HEAT = {
    "assault": 25,
    "carjack": 55,
    "robbery": 65,
    "kill_ped": 38,
    "kill_cop": 75,
    "explosion": 85,
}


def _wanted_from_heat(heat):
    if heat <= 0:
        return 0
    return min(5, 1 + int(heat // WANTED_HEAT_PER_STAR))


def add_wanted_heat(state, crime="kill_ped", heat=None, timer=30):
    """Raise wanted level by accumulated heat instead of one star per crime."""
    amount = WANTED_HEAT.get(crime, WANTED_HEAT["kill_ped"]) if heat is None else heat
    if state.wanted_heat <= 0 and state.player.wanted > 0:
        state.wanted_heat = state.player.wanted * WANTED_HEAT_PER_STAR
    state.wanted_heat = min(5 * WANTED_HEAT_PER_STAR, state.wanted_heat + amount)
    old_wanted = state.player.wanted
    state.player.wanted = max(state.player.wanted, _wanted_from_heat(state.wanted_heat))
    state.player.crime_timer = max(state.player.crime_timer, timer)
    if state.player.wanted > old_wanted:
        state.roadblock_wanted_level = min(state.roadblock_wanted_level, state.player.wanted)


def sync_wanted_heat_after_drop(state):
    state.wanted_heat = min(state.wanted_heat, state.player.wanted * WANTED_HEAT_PER_STAR)

GARAGE_ITEMS = {
    1: ("Repair car", 150, "repair"),
    2: ("Repaint car", 80, "repaint"),
    3: ("Wanted -2", 300, "clear_wanted"),
}

BARBER_STYLES = (
    ("Short hair", 20, "short"),
    ("Buzz cut", 20, "buzz"),
    ("Side part", 20, "parted"),
    ("Mohawk", 20, "mohawk"),
    ("Bald", 20, "bald"),
    ("Bob", 20, "bob"),
    ("Long hair", 20, "long"),
    ("Ponytail", 20, "ponytail"),
)

BARBER_COLORS = (
    ("Black", 5, (28, 22, 18)),
    ("Brown", 5, (58, 38, 24)),
    ("Auburn", 5, (96, 58, 28)),
    ("Copper", 5, (154, 104, 48)),
    ("Blond", 5, (214, 176, 92)),
    ("Silver", 5, (188, 188, 176)),
    ("Red", 5, (126, 42, 34)),
    ("Jet black", 5, (18, 18, 20)),
)


def init_services(state):
    """Place service markers near reachable roads."""
    from game2d.world.geometry import rebuild_pedestrian_graph

    state.garages[:] = [
        (ROAD_LO + 230, ROAD_LO + 160),
        (ROAD_HI_X - 230, ROAD_HI_Y - 160),
    ]
    state.shops[:] = [
        (ROAD_LO + 45, ROAD_HI_Y - 45),
    ]
    state.barbers[:] = [
        (ROAD_LO + 220, ROAD_LO + 410),
    ]
    clear = []
    for gx, gy in state.garages:
        clear.extend(garage_layout(gx, gy))
    for bx, by in state.barbers:
        clear.extend(barber_layout(bx, by))
    state.buildings[:] = [
        item for item in state.buildings
        if not any(item[0].colliderect(area.inflate(12, 12)) for area in clear)
    ]
    for gx, gy in state.garages:
        state.buildings.append((garage_layout(gx, gy)[0], None))
    for bx, by in state.barbers:
        state.buildings.append((barber_layout(bx, by)[0], None))
    state.AI_OBSTACLES[:] = (
        list(state.buildings)
        + [(r, None) for r in state.WATER_RECTS]
        + [(r, None) for r in state.parks]
        + [(r, None) for r in state.amusement_parks]
    )
    rebuild_pedestrian_graph(state)


def _pos(state):
    actor = state.in_car if state.in_car else state.player
    return actor.x, actor.y


def garage_layout(x, y):
    building = pygame.Rect(int(x - 62), int(y - 42), 124, 84)
    road_margin = ROAD_W // 2 + SIDEWALK_W
    if x < (ROAD_LO + ROAD_HI_X) / 2:
        sidewalk_edge = ROAD_LO + road_margin
        apron = pygame.Rect(building.left - 18, int(y - 28), 28, 56)
        driveway = pygame.Rect(sidewalk_edge, int(y - 18), max(1, apron.left - sidewalk_edge), 36)
    else:
        sidewalk_edge = ROAD_HI_X - road_margin
        apron = pygame.Rect(building.right - 10, int(y - 28), 28, 56)
        driveway = pygame.Rect(apron.right, int(y - 18), max(1, sidewalk_edge - apron.right), 36)
    return building, driveway, apron


def barber_layout(x, y):
    building = pygame.Rect(int(x - 54), int(y - 42), 108, 84)
    road_margin = ROAD_W // 2 + SIDEWALK_W
    if x < (ROAD_LO + ROAD_HI_X) / 2:
        sidewalk_edge = ROAD_LO + road_margin
        walk = pygame.Rect(sidewalk_edge, int(y - 14), max(1, building.left - sidewalk_edge), 28)
    else:
        sidewalk_edge = ROAD_HI_X - road_margin
        walk = pygame.Rect(building.right, int(y - 14), max(1, sidewalk_edge - building.right), 28)
    sign = pygame.Rect(int(x - 34), int(y - 34), 68, 18)
    return building, walk, sign


def nearby_service(state, radius=85):
    x, y = _pos(state)
    for gx, gy in state.garages:
        building, driveway, apron = garage_layout(gx, gy)
        if building.inflate(radius, radius).collidepoint(x, y) or driveway.inflate(18, 18).collidepoint(x, y) or apron.inflate(18, 18).collidepoint(x, y):
            return "garage"
    for sx, sy in state.shops:
        if math.hypot(x - sx, y - sy) <= radius:
            return "shop"
    for bx, by in state.barbers:
        building, walk, _ = barber_layout(bx, by)
        if building.inflate(radius, radius).collidepoint(x, y) or walk.inflate(18, 18).collidepoint(x, y):
            return "barber"
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
        old_wanted = state.player.wanted
        state.player.wanted = max(0, state.player.wanted - 1)
        sync_wanted_heat_after_drop(state)
        state.player.crime_timer = 25
        if state.player.wanted < old_wanted:
            clear_roadblocks(state)
            state.roadblock_wanted_level = state.player.wanted
            state.roadblocks_cleared_on_drop = True
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
        from game2d.entities.car import random_car_color

        state.in_car.repaint(random_car_color(getattr(state.in_car, "kind", "sedan")))
        state.in_car.dents.clear()
        lose_cops_after_repaint(state)
    elif action == "clear_wanted":
        old_wanted = state.player.wanted
        state.player.wanted = max(0, state.player.wanted - 2)
        sync_wanted_heat_after_drop(state)
        state.player.crime_timer = 25
        if state.player.wanted < old_wanted:
            clear_roadblocks(state)
            state.roadblock_wanted_level = state.player.wanted
            state.roadblocks_cleared_on_drop = True
    set_message(state, f"Done: {label}")


def _rebuild_player_appearance(player):
    from game2d.render.sprites import make_ped_frames, make_swim_frames

    shirt = getattr(player, "shirt", (40, 100, 200))
    skin = getattr(player, "skin", (236, 190, 150))
    hair = getattr(player, "hair_color", (30, 20, 15))
    gender = getattr(player, "gender", "m")
    hair_style = getattr(player, "hair_style", "short")
    player.frames = make_ped_frames(shirt, skin=skin, hair=hair, gender=gender, hair_style=hair_style)
    player.back_frames = make_ped_frames(shirt, skin=skin, hair=hair, gender=gender, hair_style=hair_style, back=True)
    player.swim_frames = make_swim_frames(shirt, skin=skin, hair=hair, gender=gender, hair_style=hair_style)
    player.sprite = player.back_frames[getattr(player, "frame_idx", 0) % len(player.back_frames)]


def use_barber_item(state, key):
    if state.in_car:
        set_message(state, "Leave the car first")
        return
    if state.barber_step == "color":
        if not 1 <= key <= len(BARBER_COLORS):
            return
        label, price, color = BARBER_COLORS[key - 1]
        if not spend(state, price):
            return
        state.player.hair_color = color
        _rebuild_player_appearance(state.player)
        set_message(state, f"Hair color: {label}")
        return
    if not 1 <= key <= len(BARBER_STYLES):
        return
    label, price, style = BARBER_STYLES[key - 1]
    if not spend(state, price):
        return
    state.player.hair_style = style
    _rebuild_player_appearance(state.player)
    state.barber_step = "color"
    set_message(state, f"Haircut: {label}")


def shop_lines():
    return [f"{key}. {label} ${price}" for key, (label, price, _) in SHOP_ITEMS.items()]


def garage_lines(in_car):
    lines = [f"{key}. {label} ${price}" for key, (label, price, _) in GARAGE_ITEMS.items()]
    if not in_car:
        lines.insert(0, "Drive a car inside for repair/repaint")
    return lines


def barber_lines(state):
    in_car = state.in_car
    items = BARBER_COLORS if state.barber_step == "color" else BARBER_STYLES
    lines = [f"{idx}. {label} ${price}" for idx, (label, price, _) in enumerate(items, start=1)]
    if in_car:
        lines.insert(0, "Leave the car first")
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


def _rect_outside_view(state, rect, margin=130):
    view = pygame.Rect(int(state.cam[0]), int(state.cam[1]), W, H).inflate(margin * 2, margin * 2)
    return not view.colliderect(rect)


def clear_roadblocks(state):
    state.roadblocks.clear()
    for car in list(state.cars):
        if getattr(car, "is_roadblock_support", False) and car is not state.in_car:
            if car._siren_channel is not None:
                audio.stop_loop(car._siren_channel)
                car._siren_channel = None
            state.cars.remove(car)


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
        if not _rect_outside_view(state, roadblock.rect):
            continue
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
    from game2d.entities.car import Car, law_color_for_kind, law_kind_for_wanted

    law_kind = law_kind_for_wanted(state.player.wanted)
    car = Car(roadblock.x, roadblock.y, law_color_for_kind(law_kind), is_cop=True, kind=law_kind)
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
        clear_roadblocks(state)
        state.roadblock_wanted_level = wanted
        state.roadblocks_cleared_on_drop = False
        return
    if wanted < state.roadblock_wanted_level:
        clear_roadblocks(state)
        state.roadblock_wanted_level = wanted
        state.roadblocks_cleared_on_drop = True
        return
    if wanted > state.roadblock_wanted_level:
        state.roadblocks_cleared_on_drop = False
    state.roadblock_wanted_level = wanted
    if state.roadblocks_cleared_on_drop:
        return
    limit = 4 if wanted == 3 else 7 if wanted == 4 else 10
    while len(state.roadblocks) < limit:
        target = state.in_car if state.in_car else state.player
        roadblock = _roadblock_spawn_near(state, target.x, target.y)
        if roadblock is None:
            break
        car = _spawn_roadblock_cop_car(state, roadblock)
        if not _rect_outside_view(state, car.rect(), margin=80):
            continue
        state.cars.append(car)
        state.roadblocks.append(roadblock)


def lose_cops_after_repaint(state):
    """Repaint hides the player while they stay in the repainted car."""
    if not state.in_car:
        return
    state.player.wanted = 0
    state.player.crime_timer = 0
    state.wanted_heat = 0
    state.cops.clear()
    clear_roadblocks(state)
    state.roadblock_wanted_level = 0
    state.roadblocks_cleared_on_drop = False
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


COP_WEAPON_PROFILES = {
    "cop": {"rate": 1.35, "damage": 13, "speed": 700, "spread": 0.025, "sound": "cop_shoot"},
    "fbi": {"rate": 1.05, "damage": 16, "speed": 760, "spread": 0.035, "sound": "cop_shoot"},
    "swat": {"rate": 0.16, "damage": 15, "speed": 820, "spread": 0.075, "sound": "shoot_smg"},
    "military": {"rate": 0.09, "damage": 24, "speed": 860, "spread": 0.06, "sound": "shoot_mg"},
}


def cop_weapon_profile(cop_kind, wanted):
    profile = COP_WEAPON_PROFILES.get(cop_kind, COP_WEAPON_PROFILES["cop"]).copy()
    if cop_kind in ("cop", "fbi"):
        profile["rate"] = cop_fire_rate_for_wanted(wanted)
        profile["damage"] = cop_damage_for_wanted(wanted)
    return profile
