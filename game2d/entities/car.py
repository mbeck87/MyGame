"""Fahrzeug-Klasse: Spieler-/NPC-/Cop-Auto, Physik, KI, Kollisionen."""
import math
import random
import pygame

from game2d.config import (
    BLOCK, ROAD_LO, ROAD_HI_X, ROAD_HI_Y,
    WORLD_W, WORLD_H, TIRE_BLOOD, TIRE_SKID,
    DRIFT_MIN_SPEED, DRIFT_TURN_MIN_RATIO, SPEED_THRESHOLD_STEER,
    REVERSE_SPEED_RATIO, DRIFT_ANGLE_ALIGN, NORMAL_ANGLE_ALIGN,
    BUILDING_COLL_CHECK_DIST, PLAYER_BOUNDARY_MARGIN, PLAYER_PUSH_OFFSET,
    DUAL_HIT_DAMAGE_THRESHOLD, DUAL_HIT_DAMAGE_FACTOR,
    SINGLE_HIT_DAMAGE_THRESHOLD, SINGLE_HIT_DAMAGE_FACTOR, SINGLE_HIT_PERP_MIN,
    CAR_IDLE_DECAY, ROADBLOCK_LANE_SPEED, COP_LANE_SPEED, LANE_CENTER_SPD,
    COP_STEERING_DIV, COP_MIN_SPEED, COP_MAX_SPEED_BASE, COP_WANTED_SPEED_FACTOR,
    COP_FULL_SPEED_DIST, COP_SPEED_GUESS_MIN, COP_SPEED_GUESS_OFFSET,
    COP_STEER_ANG, COP_LOOKAHEAD_FACTOR, COP_BLOCKER_PADDING,
    COP_ALT_STEER_BASE, COP_TURN_CD_MIN, COP_TURN_CD_MAX,
    COP_TARGET_SLOW_SPD, COP_DEPLOY_MAX, COP_DEPLOY_DIST,
    COP_DEPLOY_FWD_BASE, COP_DEPLOY_FWD_STEP, COP_DEPLOY_SIDE_MIN, COP_DEPLOY_SIDE_OFFSET,
    AI_OBS_DIST_COP, AI_OBS_DIST_NORMAL,
    ARC_SPD_MIN, ARC_SPD_MAX, ARC_TIGHT_R, ARC_TIGHT_SPD, ARC_ACCEL,
    ARC_BLOCKER_DECEL, ARC_BLOCKER_YIELD,
    INTERSECTION_AHEAD, BRAKE_DECAY, INTERSECTION_PERP_TOL,
    INTERSECTION_ZONE_MIN, INTERSECTION_ZONE_MAX,
    BRAKE_DECAY_BLOCKED, YIELD_TIMER_BLOCKED,
    CAR_COLL_TURN_CD_MIN, CAR_COLL_TURN_CD_MAX,
)
from game2d.render.sprites import make_car_sprite, make_cop_car_sprite
from game2d.state import current
from game2d.systems.pooling import acquire_fire_particle, acquire_smoke_particle
from game2d.world.geometry import (
    in_city, lane_center_for_car, move_toward,
    intersection_zone_at, point_in_polygon, rect_in_park_pond, rect_on_road,
    nearest_road_x, nearest_road_y,
)
from game2d.world.traffic import intersection_has_sign_control, traffic_rule_allows
from game2d.systems.effects import spawn_blood, make_corpse, trigger_game_over
from game2d.systems.services import add_wanted_heat, on_kill
from game2d.systems import audio
from game2d.systems.spatial import register_entity
from game2d.systems.events import emit_entity_spawned
from game2d.entities.ped import Ped


# =============================================================================
# PERFORMANCE OPTIMIZATION: Cached building collision rects
# =============================================================================
def _get_building_colliders():
    """Holt alle Gebäude-Rects aus dem State. Wird für schnelle Kollisionstests genutzt."""
    s = current()
    # Einfacher Cache - wird bei jedem Frame Reset invalidiert
    # In Zukunft könnte man ein Spatial Grid für Gebäude nutzen
    return [rect for rect, surf in s.buildings if surf is not None]


CAR_PROFILES = {
    "sedan": {
        "label": "Auto",
        "sprite_size": (46, 78),
        "collision_size": (34, 62),
        "max_spd": 320,
        "max_hp": 500,
        "accel": 260,
        "brake": 260,
        "turn": 110,
        "drift_turn": 155,
        "drag": 1.4,
        "drift_drag": 0.7,
        "ai_spd": (80, 160),
        "look_distance": 82,
        "look_width": 46,
    },
    "limo": {
        "label": "Stretch-Limo",
        "sprite_size": (50, 132),
        "collision_size": (38, 112),
        "max_spd": 270,
        "max_hp": 780,
        "accel": 205,
        "brake": 230,
        "turn": 78,
        "drift_turn": 105,
        "drag": 1.25,
        "drift_drag": 0.9,
        "ai_spd": (70, 125),
        "look_distance": 134,
        "look_width": 52,
    },
    "sport": {
        "label": "Sportwagen",
        "sprite_size": (44, 72),
        "collision_size": (32, 58),
        "max_spd": 485,
        "max_hp": 430,
        "accel": 390,
        "brake": 320,
        "turn": 138,
        "drift_turn": 190,
        "drag": 1.6,
        "drift_drag": 0.62,
        "ai_spd": (130, 235),
        "look_distance": 88,
        "look_width": 44,
    },
    "lamborghini": {
        "label": "Lamborghini",
        "sprite_size": (48, 76),
        "collision_size": (34, 60),
        "max_spd": 545,
        "max_hp": 460,
        "accel": 430,
        "brake": 350,
        "turn": 148,
        "drift_turn": 205,
        "drag": 1.72,
        "drift_drag": 0.55,
        "ai_spd": (145, 260),
        "look_distance": 94,
        "look_width": 46,
    },
    "mini": {
        "label": "Mini",
        "sprite_size": (36, 58),
        "collision_size": (26, 46),
        "max_spd": 285,
        "max_hp": 330,
        "accel": 305,
        "brake": 300,
        "turn": 158,
        "drift_turn": 210,
        "drag": 1.75,
        "drift_drag": 0.58,
        "ai_spd": (75, 155),
        "look_distance": 72,
        "look_width": 36,
    },
    "semi": {
        "label": "Semi",
        "sprite_size": (58, 150),
        "collision_size": (44, 132),
        "max_spd": 235,
        "max_hp": 1150,
        "accel": 145,
        "brake": 210,
        "turn": 58,
        "drift_turn": 72,
        "drag": 1.05,
        "drift_drag": 1.0,
        "ai_spd": (55, 105),
        "look_distance": 170,
        "look_width": 66,
    },
    "bus": {
        "label": "Bus",
        "sprite_size": (56, 136),
        "collision_size": (42, 116),
        "max_spd": 255,
        "max_hp": 980,
        "accel": 165,
        "brake": 220,
        "turn": 70,
        "drift_turn": 88,
        "drag": 1.12,
        "drift_drag": 0.94,
        "ai_spd": (60, 115),
        "look_distance": 154,
        "look_width": 64,
    },
    "motorcycle": {
        "label": "Motorrad",
        "sprite_size": (24, 56),
        "collision_size": (18, 42),
        "max_spd": 470,
        "max_hp": 180,
        "accel": 420,
        "brake": 280,
        "turn": 175,
        "drift_turn": 220,
        "drag": 1.65,
        "drift_drag": 0.5,
        "ai_spd": (140, 240),
        "look_distance": 70,
        "look_width": 26,
    },
}

LAW_CAR_PROFILES = {
    "cop": {
        "label": "Polizei",
        "body": (245, 245, 250),
        "sprite_size": (46, 78),
        "collision_size": (34, 62),
        "max_spd": 400,
        "max_hp": 500,
        "accel": 300,
        "brake": 300,
        "turn": 115,
        "drift_turn": 160,
        "drag": 1.35,
        "drift_drag": 0.7,
        "ai_spd": (150, 240),
        "look_distance": 88,
        "look_width": 46,
        "deploy_count": 2,
    },
    "fbi": {
        "label": "FBI-Auto",
        "body": (24, 24, 28),
        "sprite_size": (48, 80),
        "collision_size": (36, 64),
        "max_spd": 430,
        "max_hp": 560,
        "accel": 330,
        "brake": 320,
        "turn": 120,
        "drift_turn": 168,
        "drag": 1.38,
        "drift_drag": 0.68,
        "ai_spd": (165, 250),
        "look_distance": 92,
        "look_width": 48,
        "deploy_count": 2,
    },
    "swat": {
        "label": "SWAT-Bus",
        "body": (18, 26, 42),
        "sprite_size": (58, 104),
        "collision_size": (44, 86),
        "max_spd": 335,
        "max_hp": 900,
        "accel": 245,
        "brake": 285,
        "turn": 88,
        "drift_turn": 118,
        "drag": 1.2,
        "drift_drag": 0.88,
        "ai_spd": (125, 195),
        "look_distance": 116,
        "look_width": 58,
        "deploy_count": 2,
    },
    "military": {
        "label": "Militär-Truck",
        "body": (78, 96, 56),
        "sprite_size": (60, 102),
        "collision_size": (46, 84),
        "max_spd": 360,
        "max_hp": 1050,
        "accel": 260,
        "brake": 290,
        "turn": 92,
        "drift_turn": 124,
        "drag": 1.22,
        "drift_drag": 0.86,
        "ai_spd": (135, 210),
        "look_distance": 116,
        "look_width": 60,
        "deploy_count": 2,
    },
}

CAR_KIND_WEIGHTS = (
    ("sedan", 40),
    ("mini", 19),
    ("sport", 15),
    ("lamborghini", 13),
    ("motorcycle", 10),
    ("limo", 8),
    ("bus", 7),
    ("semi", 5),
)


def normalize_car_kind(kind):
    if kind == "lamborgini":
        return "lamborghini"
    return kind if kind in CAR_PROFILES else "sedan"


def normalize_law_kind(kind):
    aliases = {
        "police": "cop",
        "polizei": "cop",
        "army": "military",
        "militaer": "military",
        "militär": "military",
    }
    kind = aliases.get(kind, kind)
    return kind if kind in LAW_CAR_PROFILES else "cop"


def law_kind_for_wanted(wanted):
    if wanted >= 5:
        return "military"
    if wanted >= 4:
        return "swat"
    if wanted >= 3:
        return "fbi"
    return "cop"


def law_color_for_kind(kind):
    return LAW_CAR_PROFILES[normalize_law_kind(kind)]["body"]


def random_car_kind():
    kinds, weights = zip(*CAR_KIND_WEIGHTS)
    return random.choices(kinds, weights=weights, k=1)[0]


def random_car_color(kind=None):
    kind = normalize_car_kind(kind)
    palettes = {
        "limo": [(18, 18, 24), (235, 235, 230), (40, 44, 52), (92, 26, 26)],
        "sport": [(210, 40, 35), (245, 190, 40), (40, 125, 225), (35, 200, 110), (235, 235, 235)],
        "lamborghini": [(245, 190, 35), (225, 85, 35), (35, 210, 110), (35, 120, 230), (230, 230, 225)],
        "mini": [(220, 70, 55), (55, 145, 215), (245, 210, 75), (80, 190, 110), (230, 230, 230)],
        "semi": [(180, 38, 34), (235, 235, 225), (38, 98, 168), (54, 132, 82), (215, 150, 58)],
        "bus": [(238, 190, 44), (220, 72, 58), (52, 134, 196), (70, 166, 94)],
        "motorcycle": [(28, 28, 32), (210, 40, 40), (240, 200, 50), (40, 130, 220), (40, 180, 110), (220, 220, 220)],
    }
    if kind in palettes and random.random() < 0.85:
        return random.choice(palettes[kind])
    return random.randint(60, 230), random.randint(60, 230), random.randint(60, 230)


def car_collision_size(kind="sedan", is_cop=False):
    if is_cop:
        return LAW_CAR_PROFILES[normalize_law_kind(kind)]["collision_size"]
    return CAR_PROFILES[normalize_car_kind(kind)]["collision_size"]


def car_rect_at(x, y, angle, kind="sedan", is_cop=False):
    coll_w, coll_h = car_collision_size(kind, is_cop=is_cop)
    if abs(math.cos(math.radians(angle))) >= abs(math.sin(math.radians(angle))):
        w, h = coll_w, coll_h
    else:
        w, h = coll_h, coll_w
    return pygame.Rect(x - w // 2, y - h // 2, w, h)


class Car:
    def __init__(self, x, y, body, is_cop=False, kind="sedan"):
        self.x, self.y = x, y
        self.angle = random.choice([0, 90, 180, 270])
        self.spd = 0
        self.is_cop = is_cop
        self.kind = normalize_law_kind(kind) if is_cop else normalize_car_kind(kind)
        self.profile = LAW_CAR_PROFILES[self.kind] if is_cop else CAR_PROFILES[self.kind]
        self.label = self.profile["label"]
        self.body = body if body is not None else self.profile.get("body")
        self.max_spd = self.profile["max_spd"]
        self.driver = True if is_cop else None  # None = geparkt, True/Ped = hat Fahrer
        self.is_roadblock = False
        self.is_roadblock_support = False
        if is_cop:
            sw, sh = self.profile["sprite_size"]
            self.sprite = make_cop_car_sprite(self.kind, sw, sh)
        else:
            sw, sh = self.profile["sprite_size"]
            self.sprite = make_car_sprite(self.body, sw, sh, kind=self.kind)
        self.w, self.h = self.sprite.get_size()
        self.coll_w, self.coll_h = car_collision_size(self.kind, is_cop=is_cop)
        self.max_hp = self.profile["max_hp"]
        self.hp = self.max_hp
        
        # Rotated Sprite Cache: angle -> rotated_surface
        # Reduziert teure pygame.transform.rotate() Aufrufe pro Frame
        self._rotated_sprite_cache = {}
        self._last_rotated_angle = None
        self._last_rotated_sprite = None
        # Rect Caching für Performance
        self._cached_rect = None
        self._cached_rect_x = None
        self._cached_rect_y = None
        self._cached_rect_angle = None
        self.accel_rate = self.profile["accel"]
        self.brake_rate = self.profile["brake"]
        self.turn_rate = self.profile["turn"]
        self.drift_turn_rate = self.profile["drift_turn"]
        self.drag = self.profile["drag"]
        self.drift_drag = self.profile["drift_drag"]
        self.look_distance = self.profile["look_distance"]
        self.look_width = self.profile["look_width"]
        self.dents = []
        self.burning = False
        self.burn_timer = 0.0
        self.dead = False
        self.sunk = False
        self._smoke_cd = 0.0
        self._fire_cd = 0.0
        self.blood_trail = 0.0
        self._trail_cd = 0.0
        self.deployed_cops = 0
        self.deploy_count = self.profile.get("deploy_count", 0)
        self.yield_timer = 0.0
        self.ai_spd = random.uniform(*self.profile["ai_spd"])
        self.turn_cd = random.uniform(2, 6)
        self.arc = None
        self.planned_turn = None
        self.signal_dir = 0
        self._siren_channel = None
        self._squeal_channel = None
        self._vel_angle = None   # tatsächliche Bewegungsrichtung (für Drift)
        self._drifting = False
        self._skid_cd = 0.0
        self._traffic_rule_key = None
        self._traffic_stop_timer = 0.0

    def _local_from_world(self, wx, wy):
        rad = math.radians(self.angle)
        cs, sn = math.cos(rad), math.sin(rad)
        dx = wx - self.x
        dy = wy - self.y
        return dx * cs + dy * sn, -dx * sn + dy * cs

    def _local_impact_from_source(self, sx, sy):
        lx, ly = self._local_from_world(sx, sy)
        if abs(lx) < 0.001 and abs(ly) < 0.001:
            ly = -1.0
        half_w = self.w * 0.42
        half_h = self.h * 0.42
        scale = max(abs(lx) / half_w if half_w else 0, abs(ly) / half_h if half_h else 0, 0.001)
        return max(-half_w, min(half_w, lx / scale)), max(-half_h, min(half_h, ly / scale))

    def _clamp_damage_local(self, lx, ly):
        return (
            max(-self.w * 0.42, min(self.w * 0.42, lx)),
            max(-self.h * 0.42, min(self.h * 0.42, ly)),
        )

    def _add_dents(self, dmg, local_pos=None):
        n = max(1, int(dmg // 18))
        if local_pos is None:
            base_x = random.uniform(-self.w * 0.30, self.w * 0.30)
            base_y = random.uniform(-self.h * 0.30, self.h * 0.30)
        else:
            base_x, base_y = self._clamp_damage_local(*local_pos)
        for _ in range(min(n, 5)):
            if len(self.dents) >= 45:
                break
            spread = max(2.0, min(12.0, dmg * 0.09))
            lx = base_x + random.uniform(-spread, spread)
            ly = base_y + random.uniform(-spread, spread)
            lx, ly = self._clamp_damage_local(lx, ly)
            severity = max(0.35, min(1.0, dmg / 85.0 + random.uniform(-0.08, 0.18)))
            rx = random.uniform(5.0, 9.0) * (0.75 + severity)
            ry = random.uniform(2.5, 5.0) * (0.85 + severity * 0.55)
            angle = random.uniform(-28.0, 28.0)
            self.dents.append((lx, ly, rx, ry, angle, severity))
        # Cache ungültig machen, da sich der Schadenszustand geändert hat
        self.clear_rotation_cache()

    def repaint(self, body):
        self.body = body
        if self.is_cop:
            sw, sh = self.profile["sprite_size"]
            self.sprite = make_cop_car_sprite(self.kind, sw, sh)
        else:
            sw, sh = self.profile["sprite_size"]
            self.sprite = make_car_sprite(self.body, sw, sh, kind=self.kind)
        self.w, self.h = self.sprite.get_size()
        # Cache ungültig machen, da sich das Basissprite geändert hat
        self._rotated_sprite_cache.clear()
        self._last_rotated_angle = None
        self._last_rotated_sprite = None

    def clear_rotation_cache(self):
        """Cache für rotierte Sprites löschen (z.B. bei Schadensänderung)."""
        self._rotated_sprite_cache.clear()
        self._last_rotated_angle = None
        self._last_rotated_sprite = None

    def take_damage(self, dmg, world_pos=None, local_pos=None, source_pos=None):
        if self.dead or self.sunk or dmg <= 0: return
        self.hp -= dmg
        if local_pos is None and world_pos is not None:
            local_pos = self._local_from_world(*world_pos)
        if local_pos is None and source_pos is not None:
            local_pos = self._local_impact_from_source(*source_pos)
        self._add_dents(dmg, local_pos)
        if self.hp <= 0 and not self.burning:
            self.hp = 0
            self.burning = True
            self.burn_timer = random.uniform(2.5, 4.0)

    def _damage_overlay(self):
        overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        for dent in self.dents:
            if len(dent) == 3:
                lx, ly, old_r = dent
                rx, ry, angle, severity = old_r * 1.7, old_r * 0.8, 0.0, 0.65
            else:
                lx, ly, rx, ry, angle, severity = dent
            pw = max(8, int(rx * 2 + 8))
            ph = max(8, int(ry * 2 + 8))
            patch = pygame.Surface((pw, ph), pygame.SRCALPHA)
            rect = pygame.Rect(4, 4, pw - 8, ph - 8)
            shade = int(95 + 70 * severity)
            pygame.draw.ellipse(patch, (18, 17, 19, shade), rect)
            pygame.draw.ellipse(patch, (8, 8, 10, int(35 + 45 * severity)), rect.inflate(-max(1, pw // 4), -max(1, ph // 4)))
            hi = rect.move(-1, -1).inflate(-max(1, pw // 5), -max(1, ph // 4))
            pygame.draw.arc(patch, (235, 235, 220, int(35 + 45 * severity)), hi, math.radians(190), math.radians(330), 1)
            pygame.draw.arc(patch, (0, 0, 0, int(35 + 45 * severity)), rect.move(1, 1), math.radians(20), math.radians(160), 1)
            if abs(angle) > 0.1:
                patch = pygame.transform.rotate(patch, angle)
            pr = patch.get_rect(center=(int(self.w * 0.5 + lx), int(self.h * 0.5 + ly)))
            overlay.blit(patch, pr)
        return overlay

    def _sprite_with_damage(self):
        if not self.dents:
            return self.sprite
        surf = self.sprite.copy()
        surf.blit(self._damage_overlay(), (0, 0))
        return surf

    def explode(self):
        s = current()
        self.dead = True
        if self._siren_channel is not None:
            audio.stop_loop(self._siren_channel)
            self._siren_channel = None
        s.explosions.append([self.x, self.y, 0.0, 0.55, 188])
        audio.play('explosion', pos=(self.x, self.y))
        if s.in_car is self:
            audio.set_engine(False)
        R = 163
        
        def calc_damage(dist, rad):
            ratio = dist / rad
            if ratio <= 0.2:
                return 530
            else:
                return max(30, int(530 - 500 * ((ratio - 0.2) / 0.8)))
        
        for p in list(s.peds):
            dist = math.hypot(p.x-self.x, p.y-self.y)
            if dist < R:
                p.hp -= calc_damage(dist, R)
                spawn_blood(p.x, p.y, 6)
                if p.hp <= 0:
                    s.peds.remove(p)
                    s.corpses.append((make_corpse(p), p.x, p.y, p.angle))
                    spawn_blood(p.x, p.y, 18)
                    # Nachspawnen eines Ersatz-Passanten
                    from game2d.entities.ped import Ped
                    from game2d.world.spawning import pedestrian_spawn
                    from game2d.systems.spatial import register_entity
                    from game2d.systems.events import emit_entity_spawned
                    min_dist = 500
                    for _ in range(30):
                        nx, ny = pedestrian_spawn()
                        dist = math.hypot(nx - s.player.x, ny - s.player.y)
                        if dist >= min_dist:
                            break
                    new_ped = Ped(nx, ny)
                    s.peds.append(new_ped)
                    register_entity(new_ped)
                    emit_entity_spawned(new_ped, "ped")
        for c in list(s.cops):
            dist = math.hypot(c.x-self.x, c.y-self.y)
            if dist < R:
                c.hp -= calc_damage(dist, R)
                spawn_blood(c.x, c.y, 6)
                if c.hp <= 0:
                    s.cops.remove(c)
                    s.corpses.append((make_corpse(c), c.x, c.y, c.angle))
                    spawn_blood(c.x, c.y, 20)
                    s.player.money += random.randint(40, 80)
        for c in s.cars:
            if c is self or c.dead: continue
            dist = math.hypot(c.x-self.x, c.y-self.y)
            if dist < R + 13:
                c.take_damage(calc_damage(dist, R + 13), source_pos=(self.x, self.y))
        if math.hypot(s.player.x-self.x, s.player.y-self.y) < R:
            dist = math.hypot(s.player.x-self.x, s.player.y-self.y)
            damage = calc_damage(dist, R)
            if s.player.armor > 0:
                armor_dmg = min(s.player.armor, damage)
                s.player.armor -= armor_dmg
                damage -= armor_dmg
            s.player.hp -= damage
            if s.player.hp <= 0:
                s.corpses.append((make_corpse(s.player), s.player.x, s.player.y, s.player.angle))
                spawn_blood(s.player.x, s.player.y, 24)
                trigger_game_over()
        if s.in_car is self:
            s.in_car = None
        for _ in range(45):
            a = random.uniform(0, 6.28); sp = random.uniform(80, 320)
            s.fire_particles.append(acquire_fire_particle(
                self.x, self.y, math.cos(a)*sp, math.sin(a)*sp,
                random.uniform(0.4, 0.9), 0.9, random.randint(4, 8)
            ))
        for _ in range(35):
            a = random.uniform(0, 6.28); sp = random.uniform(40, 180)
            s.smoke_particles.append(acquire_smoke_particle(
                self.x, self.y, math.cos(a)*sp, math.sin(a)*sp - 30,
                random.uniform(1.8, 3.5), 3.5, random.randint(6, 11)
            ))
        wreck_surf = self._sprite_with_damage().copy()
        scorch = pygame.Surface(wreck_surf.get_size(), pygame.SRCALPHA)
        scorch.fill((20, 20, 20, 200))
        wreck_surf.blit(scorch, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
        s.wrecks.append((wreck_surf, self.x, self.y, self.angle, []))
        if not self.is_cop:
            s.player.money += random.randint(20, 50)

    def _pond_sink_point(self):
        s = current()
        rect = self.rect()
        probes = (
            rect.center, rect.midtop, rect.midbottom, rect.midleft, rect.midright,
            rect.topleft, rect.topright, rect.bottomleft, rect.bottomright,
        )
        for pond in s.park_ponds:
            inside = [p for p in probes if point_in_polygon(p[0], p[1], pond)]
            if not inside:
                continue
            x, y = inside[0]
            cx = sum(p[0] for p in pond) / len(pond)
            cy = sum(p[1] for p in pond) / len(pond)
            dx = cx - x
            dy = cy - y
            dist = math.hypot(dx, dy) or 1
            return x + dx / dist * 64, y + dy / dist * 64
        return self.x, self.y

    def sink_in_pond(self):
        if self.sunk:
            return
        s = current()
        self.x, self.y = self._pond_sink_point()
        self.sunk = True
        self.spd = 0
        self.ai_spd = 0
        self.hp = 0
        self.burning = False
        if self._siren_channel is not None:
            audio.stop_loop(self._siren_channel)
            self._siren_channel = None
        if s.in_car is self:
            audio.set_engine(False)
            s.in_car = None
        for _ in range(18):
            a = random.uniform(0, math.tau)
            sp = random.uniform(25, 95)
            s.smoke_particles.append([self.x, self.y, math.cos(a) * sp, math.sin(a) * sp,
                                      random.uniform(0.5, 1.0), 1.0, random.randint(3, 7)])

    def update_fx(self, dt):
        if self.dead or self.sunk:
            if self._siren_channel is not None:
                audio.stop_loop(self._siren_channel)
                self._siren_channel = None
            if self._squeal_channel is not None:
                audio.stop_loop(self._squeal_channel)
                self._squeal_channel = None
            return
        # Reifenquietschen beim Driften
        if self._drifting:
            if self._squeal_channel is None or not self._squeal_channel.get_busy():
                self._squeal_channel = audio.start_loop('squeal', pos=(self.x, self.y), volume=0.7, max_dist=650)
            else:
                audio.update_loop(self._squeal_channel, pos=(self.x, self.y), volume=0.7, max_dist=650)
        else:
            if self._squeal_channel is not None:
                audio.stop_loop(self._squeal_channel)
                self._squeal_channel = None
        s = current()
        if self.is_cop and s.in_car is not self:
            if self._siren_channel is None or not self._siren_channel.get_busy():
                self._siren_channel = audio.start_loop('siren', pos=(self.x, self.y), volume=0.55, max_dist=600)
            else:
                audio.update_loop(self._siren_channel, pos=(self.x, self.y), volume=0.55, max_dist=600)
        elif self._siren_channel is not None:
            audio.stop_loop(self._siren_channel)
            self._siren_channel = None
        if self.burning:
            self.burn_timer -= dt
            self._fire_cd -= dt
            if self._fire_cd <= 0:
                self._fire_cd = 0.04
                s.fire_particles.append(acquire_fire_particle(
                    self.x + random.uniform(-12, 12),
                    self.y + random.uniform(-15, 15),
                    random.uniform(-25, 25), random.uniform(-70, -25),
                    random.uniform(0.3, 0.6), 0.6, random.randint(3, 6)
                ))
            self._smoke_cd -= dt
            if self._smoke_cd <= 0:
                self._smoke_cd = 0.08
                s.smoke_particles.append(acquire_smoke_particle(
                    self.x, self.y, random.uniform(-15, 15),
                    random.uniform(-55, -25), random.uniform(1.5, 2.8), 2.8,
                    random.randint(5, 9)
                ))
            if self.burn_timer <= 0:
                self.explode()
        elif self.hp < self.max_hp * 0.6:
            self._smoke_cd -= dt
            heavy = self.hp < self.max_hp * 0.3
            rate = 0.10 if heavy else 0.28
            if self._smoke_cd <= 0:
                self._smoke_cd = rate
                col_r = random.randint(4, 8) if heavy else random.randint(3, 6)
                s.smoke_particles.append(acquire_smoke_particle(
                    self.x, self.y, random.uniform(-10, 10),
                    random.uniform(-45, -18), random.uniform(1.2, 2.2), 2.2, col_r
                ))

    def rect_at_angle(self, x, y, angle):
        return car_rect_at(x, y, angle, self.kind, is_cop=self.is_cop)

    def rect_at(self, x, y):
        return self.rect_at_angle(x, y, self.angle)

    def rect(self):
        """Gibt das aktuelle Rect des Autos zurück. Nutzt Caching für Performance."""
        # Cache prüfen
        if (self._cached_rect is not None and 
            self._cached_rect_x == self.x and 
            self._cached_rect_y == self.y and
            self._cached_rect_angle == self.angle):
            return self._cached_rect
        
        # Neu berechnen
        new_rect = self.rect_at(self.x, self.y)
        self._cached_rect = new_rect
        self._cached_rect_x = self.x
        self._cached_rect_y = self.y
        self._cached_rect_angle = self.angle
        return new_rect

    def look_rect(self, distance=None, width=None):
        distance = self.look_distance if distance is None else distance
        width = self.look_width if width is None else width
        rad = math.radians(self.angle)
        cx = self.x + math.sin(rad) * distance
        cy = self.y - math.cos(rad) * distance
        length = max(68, self.coll_h + 8)
        if self.is_vertical():
            return pygame.Rect(cx - width//2, cy - length//2, width, length)
        return pygame.Rect(cx - length//2, cy - width//2, length, width)

    def overlaps_other_car(self):
        """Optimiert: Nutzt räumliche Nähe für schnellere Suche."""
        own = self.rect()
        s = current()
        
        # Schnell-Path: Prüfe nur Autos in der Nähe (einfache Distanzprüfung)
        # Dies reduziert die Anzahl der colliderect-Aufrufe deutlich
        search_radius = max(self.coll_w, self.coll_h) * 1.5 + 20
        
        for other in s.cars:
            if other is self or other.dead or other.sunk:
                continue
            # Schnell prüfen: Distance squared
            dx = other.x - self.x
            dy = other.y - self.y
            if dx * dx + dy * dy > search_radius * search_radius:
                continue
            if own.colliderect(other.rect()):
                return other
        return None

    def car_blocking_rect(self, rect, padding=8):
        """Optimiert: Nutzt räumliche Nähe für schnellere Suche."""
        s = current()
        rect_center_x = rect.centerx
        rect_center_y = rect.centery
        half_diag = math.hypot(rect.w, rect.h) * 0.5 + padding + 10
        
        for other in s.cars:
            if other is self or other.dead or other.sunk:
                continue
            # Schnell prüfen: Distance squared
            dx = other.x - rect_center_x
            dy = other.y - rect_center_y
            if dx * dx + dy * dy > half_diag * half_diag:
                continue
            if rect.colliderect(other.rect().inflate(padding, padding)):
                return other
        return None

    def roadblock_at(self, rect):
        for roadblock in current().roadblocks:
            if rect.colliderect(roadblock.rect):
                return roadblock
        return None

    def resolve_roadblock_collision(self, roadblock, prev_spd):
        own = self.rect()
        overlap_x = min(own.right, roadblock.rect.right) - max(own.left, roadblock.rect.left)
        overlap_y = min(own.bottom, roadblock.rect.bottom) - max(own.top, roadblock.rect.top)
        if overlap_x <= 0 or overlap_y <= 0:
            return
        dx = self.x - roadblock.x
        dy = self.y - roadblock.y
        if overlap_x < overlap_y:
            push = overlap_x + 1
            self.x += push if dx >= 0 else -push
        else:
            push = overlap_y + 1
            self.y += push if dy >= 0 else -push
        impact = abs(prev_spd)
        if impact > 55:
            self.take_damage(impact * 0.05, source_pos=(roadblock.x, roadblock.y))
            audio.play('crash_metal', volume=min(0.25, impact / 1040.0), pos=(self.x, self.y))
        self.spd *= -0.18 if impact > 45 else 0

    def resolve_building_collisions(self, prev_spd):
        """Optimiert: Reduziert die Anzahl der Kollisionstests mit Gebäuden."""
        s = current()
        impact = abs(prev_spd)
        resolved = False

        def overlap_area(rect, building_rect):
            overlap_x = min(rect.right, building_rect.right) - max(rect.left, building_rect.left)
            overlap_y = min(rect.bottom, building_rect.bottom) - max(rect.top, building_rect.top)
            if overlap_x <= 0 or overlap_y <= 0:
                return 0
            return overlap_x * overlap_y

        def total_overlap(rect):
            # Use spatial grid for building collision
            from game2d.systems.spatial import query_buildings_radius
            nearby = query_buildings_radius(rect.centerx, rect.centery, 200)
            return sum(overlap_area(rect, br) for br in nearby if rect.colliderect(br))

        # Maximal 4 Iterationen statt 8 - reicht meist aus
        from game2d.systems.spatial import query_buildings_radius
        for _ in range(4):
            own = self.rect()
            # Use spatial grid for building collision
            nearby_buildings = query_buildings_radius(own.centerx, own.centery, 150)
            nearby_buildings = [br for br in nearby_buildings if own.colliderect(br)]
            
            if not nearby_buildings:
                break
            
            candidates = []
            for building_rect in nearby_buildings:
                candidates.extend((
                    (self.x - (own.right - building_rect.left + 1), self.y),
                    (self.x + (building_rect.right - own.left + 1), self.y),
                    (self.x, self.y - (own.bottom - building_rect.top + 1)),
                    (self.x, self.y + (building_rect.bottom - own.top + 1)),
                ))
            best_x, best_y = min(
                candidates,
                key=lambda pos: (
                    total_overlap(self.rect_at(pos[0], pos[1])),
                    (pos[0] - self.x) ** 2 + (pos[1] - self.y) ** 2,
                ),
            )
            self.x, self.y = best_x, best_y
            resolved = True
        if not resolved:
            return
        if impact > 65:
            self.take_damage(impact * 0.055, source_pos=(self.x, self.y))
            audio.play('crash_metal', volume=min(0.28, impact / 980.0), pos=(self.x, self.y))
        self.spd *= -0.16 if impact > 45 else 0.0

    def resolve_car_collision(self, other, controlled):
        s = current()
        dx = self.x - other.x
        dy = self.y - other.y
        dist = math.hypot(dx, dy)
        if dist < 0.001:
            ang = math.radians(self.angle)
            dx = math.sin(ang) or 0.001
            dy = -math.cos(ang) or -0.001
            dist = math.hypot(dx, dy)
        nx = dx / dist
        ny = dy / dist
        own_rect = self.rect()
        other_rect = other.rect()
        overlap_x = min(own_rect.right, other_rect.right) - max(own_rect.left, other_rect.left)
        overlap_y = min(own_rect.bottom, other_rect.bottom) - max(own_rect.top, other_rect.top)
        if overlap_x <= 0 or overlap_y <= 0:
            return
        anchored_self = self.is_roadblock and not controlled
        anchored_other = other.is_roadblock and other is not s.in_car
        if anchored_self and anchored_other:
            anchored_self = False
        if overlap_x < overlap_y:
            side = 1 if self.x >= other.x else -1
            move_x, move_y = side * (overlap_x + 2), 0
        else:
            side = 1 if self.y >= other.y else -1
            move_x, move_y = 0, side * (overlap_y + 2)
        if anchored_self:
            other.x -= move_x
            other.y -= move_y
        elif anchored_other:
            self.x += move_x
            self.y += move_y
        elif controlled:
            self.x += move_x * 0.45
            self.y += move_y * 0.45
            other.x -= move_x * 0.65
            other.y -= move_y * 0.65
        else:
            self.x += move_x * 0.55
            self.y += move_y * 0.55
            other.x -= move_x * 0.55
            other.y -= move_y * 0.55
            self.yield_timer = max(self.yield_timer, 0.28)
            self.spd *= 0.18
            if other is not s.in_car:
                other.yield_timer = max(other.yield_timer, 0.22)
                other.spd *= 0.35
                if id(self) < id(other):
                    self.yield_timer = max(self.yield_timer, 0.36)
                else:
                    other.yield_timer = max(other.yield_timer, 0.36)
        rel = self.spd - other.spd
        impulse = max(16.0, abs(rel) * 0.28 + abs(self.spd) * 0.08)
        self.spd = max(-self.max_spd * 0.4, min(self.max_spd, self.spd - impulse * 0.14))
        other.spd = max(-other.max_spd * 0.4, min(other.max_spd, other.spd + impulse * (0.32 if controlled else 0.18)))
        if self.is_roadblock:
            self.spd = 0
        if other.is_roadblock:
            other.spd = 0
        if controlled:
            other.angle += max(-10, min(10, math.degrees(math.atan2(nx, -ny)) - other.angle)) * 0.05
        impact = max(abs(self.spd), abs(other.spd), abs(rel))
        if impact > 75:
            dmg = impact * (0.022 if controlled else 0.02)
            self.take_damage(dmg, source_pos=(other.x, other.y))
            other.take_damage(dmg * (0.85 if controlled else 1.0), source_pos=(self.x, self.y))
            cx = (self.x + other.x) * 0.5
            cy = (self.y + other.y) * 0.5
            audio.play('crash_metal', volume=min(0.25, impact / 1040.0), pos=(cx, cy))

    def _wheel_points(self):
        rad = math.radians(self.angle)
        cs, sn = math.cos(rad), math.sin(rad)
        pts = []
        if self.kind == "motorcycle":
            offsets = ((0, -self.h*0.28), (0, self.h*0.28))
        else:
            offsets = ((-self.w*0.38, -self.h*0.28), (self.w*0.38, -self.h*0.28),
                       (-self.w*0.38, self.h*0.28), (self.w*0.38, self.h*0.28))
        for dx_, dy_ in offsets:
            wx = self.x + dx_ * cs - dy_ * sn
            wy = self.y + dx_ * sn + dy_ * cs
            pts.append((wx, wy))
        return pts

    def is_vertical(self):
        return abs(math.cos(math.radians(self.angle))) >= abs(math.sin(math.radians(self.angle)))

    def upcoming_intersection(self, look_ahead=85):
        rad = math.radians(self.angle)
        px = self.x + math.sin(rad) * look_ahead
        py = self.y - math.cos(rad) * look_ahead
        return intersection_zone_at(px, py, margin=12)

    def should_yield_at_intersection(self):
        """Optimiert: Nutzt räumliche Nähe für schnellere Suche."""
        zone = self.upcoming_intersection(118)
        if not zone:
            return False
        ix, iy, _ = zone
        if intersection_has_sign_control(ix, iy):
            return False
        my_dist = math.hypot(self.x - ix, self.y - iy)
        s = current()
        
        # Nur Autos in der Nähe der Kreuzung prüfen
        for other in s.cars:
            if other is self or other.dead or other.sunk:
                continue
            # Schnell prüfen: Ist das Auto in der Nähe der Kreuzung?
            other_dist_to_intersection = math.hypot(other.x - ix, other.y - iy)
            if other_dist_to_intersection > 150:  # Nicht in der Nähe
                continue
                
            other_zone = other.upcoming_intersection(132)
            if not other_zone:
                other_zone = intersection_zone_at(other.x, other.y, margin=34)
            if not other_zone:
                continue
            ox, oy, orect = other_zone
            if abs(ox - ix) > 6 or abs(oy - iy) > 6:
                continue
            other_dist = math.hypot(other.x - ix, other.y - iy)
            other_in_box = orect.inflate(54, 54).colliderect(other.rect())
            if other_in_box or other_dist + 28 < my_dist or (abs(other_dist - my_dist) <= 28 and id(other) < id(self)):
                self.yield_timer = max(self.yield_timer, random.uniform(0.28, 0.56))
                return True
        return False

    def car_ahead(self):
        """Optimiert: Nutzt räumliche Nähe für schnellere Suche."""
        rad = math.radians(self.angle)
        fx, fy = math.sin(rad), -math.cos(rad)
        rx, ry = math.cos(rad), math.sin(rad)
        look_ahead = self.look_distance + max(55, abs(self.spd) * 0.42)
        s = current()
        
        # Such-Radius für schnelle Filterung
        search_radius_sq = look_ahead * look_ahead + 200 * 200  # Etwas größer als look_ahead
        
        for other in s.cars:
            if other is self or other.dead or other.sunk:
                continue
            # Schnell prüfen: Distance squared
            dx = other.x - self.x
            dy = other.y - self.y
            if dx * dx + dy * dy > search_radius_sq:
                continue
            
            diff = abs(((other.angle - self.angle + 180) % 360) - 180)
            if diff > 55:
                continue
            ox, oy = dx, dy  # other.x - self.x, other.y - self.y
            ahead = ox * fx + oy * fy
            lateral = abs(ox * rx + oy * ry)
            lane_width = (self.coll_w + other.coll_w) * 0.5 + 16
            if 0 < ahead < look_ahead and lateral <= lane_width:
                return other
        return None

    def civilian_ahead(self, look_ahead=None, width=None):
        """Optimiert: Nutzt räumliche Nähe für schnellere Suche."""
        look_ahead = look_ahead if look_ahead is not None else self.look_distance + 24
        width = width if width is not None else self.look_width + 28
        probe = self.look_rect(distance=look_ahead, width=width)
        rad = math.radians(self.angle)
        fx, fy = math.sin(rad), -math.cos(rad)
        s = current()
        
        # Such-Radius für Peds in Fahrtrichtung
        search_radius_sq = look_ahead * look_ahead + width * width
        
        for ped in s.peds:
            if getattr(ped, "dead", False):
                continue
            # Schnell prüfen: Distance squared
            dx = ped.x - self.x
            dy = ped.y - self.y
            if dx * dx + dy * dy > search_radius_sq:
                continue
            
            ox, oy = dx, dy
            ahead = ox * fx + oy * fy
            if 0 < ahead < look_ahead and probe.colliderect(ped.rect()):
                return ped
        return None

    def cop_rect_clear(self, rect):
        if not in_city(rect.centerx, rect.centery, 12):
            return False
        if any(rect.colliderect(b[0]) for b in current().buildings):
            return False
        if any(rect.colliderect(rb.rect) for rb in current().roadblocks):
            return False
        return not rect_in_park_pond(rect)

    def reserve_intersection(self, urgent=False):
        zone = self.upcoming_intersection(92)
        if not zone:
            return True
        ix, iy, _ = zone
        key = (ix, iy)
        claims = current().intersection_claims
        owner = claims.get(key)
        if owner is None or owner is self or owner.dead:
            claims[key] = self
            return True
        if urgent and math.hypot(self.x - ix, self.y - iy) + 20 < math.hypot(owner.x - ix, owner.y - iy):
            claims[key] = self
            return True
        self.yield_timer = max(self.yield_timer, 0.18)
        return False

    def near_road_end(self, margin=BLOCK):
        heading = int(round(self.angle / 90.0)) * 90 % 360
        rad = math.radians(heading)
        look = self.rect_at(
            self.x + math.sin(rad) * 220,
            self.y - math.cos(rad) * 220,
        )
        blocked_areas = list(current().parks) + list(current().amusement_parks)
        if any(look.colliderect(park) for park in blocked_areas):
            return True
        if heading == 0:
            return self.y < ROAD_LO + margin
        if heading == 180:
            return self.y > ROAD_HI_Y - margin
        if heading == 90:
            return self.x > ROAD_HI_X - margin
        return self.x < ROAD_LO + margin

    def _turn_signal_dir(self, start_angle, end_angle):
        diff = self._turn_delta(start_angle, end_angle)
        if diff == 0:
            return 0
        return 1 if diff > 0 else -1

    def _turn_delta(self, start_angle, end_angle):
        return ((end_angle - start_angle + 180) % 360) - 180

    def _valid_turn_choices(self, heading, allow_reverse=False):
        reverse = (heading + 180) % 360
        choices = []
        for angle in (0, 90, 180, 270):
            if not allow_reverse and angle == reverse:
                continue
            lx, ly = lane_center_for_car(angle, self.x, self.y)
            rad = math.radians(angle)
            probes = [self.rect_at_angle(lx, ly, angle)]
            for dist in (120, 260, 420):
                tx = lx + math.sin(rad) * dist
                ty = ly - math.cos(rad) * dist
                probes.append(self.rect_at_angle(tx, ty, angle))
            if all(rect_on_road(probe) for probe in probes):
                choices.append(angle)
        return choices

    def choose_intersection_turn(self, allow_reverse=False):
        heading = int(round(self.angle / 90.0)) * 90 % 360
        choices = self._valid_turn_choices(heading, allow_reverse=allow_reverse)
        if not choices:
            return False

        new_angle = self.planned_turn if self.planned_turn in choices else random.choice(choices)
        self.planned_turn = None
        self.signal_dir = self._turn_signal_dir(heading, new_angle)
        if new_angle == heading:
            self.signal_dir = 0
            self.turn_cd = random.uniform(2.5, 6.0)
            return True

        if not self.start_turn_arc(heading, new_angle):
            self.planned_turn = new_angle
            self.turn_cd = 0.2
            return False
        self.turn_cd = random.uniform(2.5, 6.0)
        return True

    def plan_intersection_turn(self, allow_reverse=False):
        if self.arc is not None or self.planned_turn is not None:
            return
        heading = int(round(self.angle / 90.0)) * 90 % 360
        choices = self._valid_turn_choices(heading, allow_reverse=allow_reverse)
        if not choices:
            return
        self.planned_turn = random.choice(choices)
        self.signal_dir = self._turn_signal_dir(heading, self.planned_turn)

    def start_turn_arc(self, heading, new_angle):
        diff = self._turn_delta(heading, new_angle)
        if diff == 0:
            self.arc = None
            return True
        if abs(diff) == 180:
            return self.start_u_turn_arc(heading, new_angle)

        a_rad = math.radians(heading)
        b_rad = math.radians(new_angle)
        lane_off = 28
        fwd_a = (math.sin(a_rad), -math.cos(a_rad))
        right_a = (math.cos(a_rad), math.sin(a_rad))
        fwd_b = (math.sin(b_rad), -math.cos(b_rad))
        right_b = (math.cos(b_rad), math.sin(b_rad))
        ix = nearest_road_x(self.x)
        iy = nearest_road_y(self.y)

        corner_x = ix + lane_off * right_a[0] + lane_off * right_b[0]
        corner_y = iy + lane_off * right_a[1] + lane_off * right_b[1]
        depth = (corner_x - self.x) * fwd_a[0] + (corner_y - self.y) * fwd_a[1]
        min_radius = max(20.0, self.coll_h * 0.42)
        radius = max(min_radius, min(68.0 if diff > 0 else 92.0, depth))

        arc_sx = corner_x - radius * fwd_a[0]
        arc_sy = corner_y - radius * fwd_a[1]
        arc_ex = corner_x + radius * fwd_b[0]
        arc_ey = corner_y + radius * fwd_b[1]

        if diff > 0:
            cx = arc_sx + radius * right_a[0]
            cy = arc_sy + radius * right_a[1]
            omega = 1
        else:
            cx = arc_sx - radius * right_a[0]
            cy = arc_sy - radius * right_a[1]
            omega = -1

        theta_s = math.atan2(arc_sy - cy, arc_sx - cx)
        theta_e = theta_s + omega * math.pi / 2
        arc = {
            "cx": cx,
            "cy": cy,
            "r": radius,
            "theta": theta_s,
            "theta_end": theta_e,
            "omega": omega,
            "end_x": arc_ex,
            "end_y": arc_ey,
            "target": float(new_angle),
        }
        return self.begin_turn_arc(arc, arc_sx, arc_sy, heading)

    def start_u_turn_arc(self, heading, new_angle):
        a_rad = math.radians(heading)
        radius = max(34.0, self.coll_h * 0.46)
        right_a = (math.cos(a_rad), math.sin(a_rad))
        if heading in (0, 180):
            cx = nearest_road_x(self.x)
            cy = self.y
        else:
            cx = self.x
            cy = nearest_road_y(self.y)

        arc_sx = cx + radius * right_a[0]
        arc_sy = cy + radius * right_a[1]
        arc_ex = cx - radius * right_a[0]
        arc_ey = cy - radius * right_a[1]
        theta_s = math.atan2(arc_sy - cy, arc_sx - cx)
        theta_e = theta_s - math.pi
        arc = {
            "cx": cx,
            "cy": cy,
            "r": radius,
            "theta": theta_s,
            "theta_end": theta_e,
            "omega": -1,
            "end_x": arc_ex,
            "end_y": arc_ey,
            "target": float(new_angle),
        }
        return self.begin_turn_arc(arc, arc_sx, arc_sy, heading)

    def arc_pose(self, arc, theta):
        x = arc["cx"] + arc["r"] * math.cos(theta)
        y = arc["cy"] + arc["r"] * math.sin(theta)
        vx = -math.sin(theta) * arc["omega"]
        vy = math.cos(theta) * arc["omega"]
        angle = math.degrees(math.atan2(vx, -vy))
        return x, y, angle

    def turn_path_blocker(self, arc, samples=7):
        for i in range(1, samples + 1):
            t = i / samples
            theta = arc["theta"] + (arc["theta_end"] - arc["theta"]) * t
            x, y, angle = self.arc_pose(arc, theta)
            blocker = self.car_blocking_rect(self.rect_at_angle(x, y, angle), padding=12)
            if blocker:
                return blocker
        return None

    def begin_turn_arc(self, arc, start_x, start_y, heading):
        start_rect = self.rect_at_angle(start_x, start_y, heading)
        if self.car_blocking_rect(start_rect, padding=10) or self.turn_path_blocker(arc):
            self.arc = None
            self.yield_timer = max(self.yield_timer, 0.22)
            self.spd *= 0.35
            return False
        self.x, self.y = start_x, start_y
        self.arc = arc
        return True

    def _leave_tire_trail(self, dt):
        if self.blood_trail <= 0 or abs(self.spd) < 35:
            self._trail_cd = 0
            return
        self.blood_trail = max(0.0, self.blood_trail - dt)
        self._trail_cd -= dt
        if self._trail_cd > 0:
            return
        self._trail_cd = 0.045
        splats = current().blood_splats
        for wx, wy in self._wheel_points():
            splats.append((wx + random.uniform(-1.2, 1.2),
                           wy + random.uniform(-1.2, 1.2),
                           random.randint(2, 4), TIRE_BLOOD))

    def _leave_skid_trail(self, dt):
        if abs(self.spd) < 45:
            self._skid_cd = 0.0
            return
        self._skid_cd -= dt
        if self._skid_cd > 0:
            return
        self._skid_cd = 0.025
        splats = current().blood_splats
        for wx, wy in self._wheel_points():
            splats.append((wx + random.uniform(-1.5, 1.5),
                           wy + random.uniform(-1.5, 1.5),
                           random.randint(2, 4), TIRE_SKID))

    def _run_over_ped(self, ped, group, damage, is_cop=False):
        s = current()
        if not self.rect().colliderect(ped.rect()):
            return False
        ped.hp -= damage
        ped.state = 'flee'
        self.blood_trail = max(self.blood_trail, 3.5)
        spawn_blood(ped.x, ped.y, 5 if is_cop else 4)
        audio.play('scream', pos=(ped.x, ped.y))
        if ped.hp <= 0:
            if ped in group:
                group.remove(ped)
            s.corpses.append((make_corpse(ped), ped.x, ped.y, ped.angle))
            spawn_blood(ped.x, ped.y, 18 if is_cop else 16)
            if self is s.in_car:
                on_kill(s, ped, is_cop=is_cop)
                if not is_cop:
                    s.player.money += random.randint(10, 35)
            # Nachspawnen wenn es ein normaler Passant war
            if group is s.peds:
                from game2d.entities.ped import Ped as _Ped
                from game2d.world.spawning import pedestrian_spawn
                from game2d.systems.spatial import register_entity
                from game2d.systems.events import emit_entity_spawned
                min_dist = 500
                for _ in range(30):
                    nx, ny = pedestrian_spawn()
                    dist = math.hypot(nx - s.player.x, ny - s.player.y)
                    if dist >= min_dist:
                        break
                new_ped = _Ped(nx, ny)
                s.peds.append(new_ped)
                register_entity(new_ped)
                emit_entity_spawned(new_ped, "ped")
        return True

    def _run_over_cat(self, cat, group, damage):
        s = current()
        if not self.rect().colliderect(cat.rect()):
            return False
        cat.hp -= damage
        self.blood_trail = max(self.blood_trail, 2.0)
        spawn_blood(cat.x, cat.y, 3)
        audio.play('scream', pos=(cat.x, cat.y))
        if cat.hp <= 0:
            if cat in group:
                group.remove(cat)
            s.corpses.append((cat.sprite.copy(), cat.x, cat.y, cat.angle))
            spawn_blood(cat.x, cat.y, 8)
            if self is s.in_car:
                # Katzen-Tötung zählt als Kill für Wanted-Level
                on_kill(s, cat, is_cop=False)
                # Aber zusätzlich: 5 Sterne für Katzen-Tötung
                s.player.wanted = 5
                s.player.crime_timer = 30
                s.wanted_heat = 5 * 100
                s.player.money += random.randint(50, 100)
        return True

    def _run_over_player(self, damage):
        s = current()
        if s.in_car is self or not self.rect().colliderect(s.player.rect()):
            return False
        # Spieler aus dem Auto-Rect herausschieben (kein Durchgleiten)
        cr = self.rect()
        dx = s.player.x - self.x
        dy = s.player.y - self.y
        dist = math.hypot(dx, dy) or 1
        nx, ny = dx / dist, dy / dist
        overlap_x = (cr.w / 2 + 12) - abs(dx)
        overlap_y = (cr.h / 2 + 12) - abs(dy)
        if overlap_x > 0 and overlap_y > 0:
            if overlap_x < overlap_y:
                s.player.x += nx * overlap_x * 1.2
            else:
                s.player.y += ny * overlap_y * 1.2
        s.player.hp -= damage
        self.blood_trail = max(self.blood_trail, 4.0)
        spawn_blood(s.player.x, s.player.y, 6)
        if s.player.hp <= 0:
            s.corpses.append((make_corpse(s.player), s.player.x, s.player.y, s.player.angle))
            spawn_blood(s.player.x, s.player.y, 22)
            trigger_game_over()
        return True

    def hit_pedestrians(self, speed_mag):
        """Optimiert: Nutzt Spatial Grid für schnelle Suche nach Entitäten."""
        if speed_mag < 85 or self.dead:
            return
        s = current()
        dmg = max(18, min(120, int(speed_mag * 0.45)))
        
        # Such-Radius basierend auf Geschwindigkeit und Collider-Größe
        search_radius = speed_mag * 0.5 + 60
        
        # Use spatial grid to get all nearby entities
        from game2d.systems.spatial import query_entities_radius
        nearby_entities = query_entities_radius(self.x, self.y, search_radius)
        
        for entity in nearby_entities:
            if entity is self:
                continue
            # Check if entity is Ped
            if hasattr(entity, 'hp') and not getattr(entity, 'dead', False):
                if isinstance(entity, Ped) and entity in s.peds:
                    if not self.is_cop:
                        self._run_over_ped(entity, s.peds, dmg, is_cop=False)
                elif hasattr(entity, 'is_cop') and entity.is_cop and entity in s.cops:
                    self._run_over_ped(entity, s.cops, dmg + 12, is_cop=True)
                elif hasattr(entity, 'hp') and not entity.is_cop and entity not in s.peds:
                    # Cats and other entities
                    if not self.is_cop:
                        # Try to handle as cat
                        from game2d.entities.cat import Cat
                        if isinstance(entity, Cat) and entity in s.cats:
                            self._run_over_cat(entity, s.cats, dmg)
        
        self._run_over_player(dmg + 10)

    def update(self, dt, accel=0, steer=0, handbrake=False):
        if self.dead or self.sunk:
            self.spd = 0
            return
        s = current()
        controlled = (self is s.in_car)
        prev_spd = self.spd
        dx, dy = self._apply_physics(dt, accel, steer, handbrake, controlled)
        self._move_with_collision(dx, dy, prev_spd, controlled, dt)
        self._clamp_world_bounds(controlled)
        self._update_interactions(dt)

    def _apply_physics(self, dt, accel, steer, handbrake, controlled):
        drift_active = handbrake and controlled and abs(self.spd) > DRIFT_MIN_SPEED
        self._drifting = drift_active
        if drift_active:
            self.spd *= max(0, 1 - self.drift_drag * dt)
            if abs(self.spd) > SPEED_THRESHOLD_STEER:
                self.angle += steer * self.drift_turn_rate * dt * max(DRIFT_TURN_MIN_RATIO, abs(self.spd) / self.max_spd)
            self._leave_skid_trail(dt)
        else:
            if accel > 0:
                self.spd = min(self.max_spd, self.spd + self.accel_rate * dt)
            elif accel < 0:
                self.spd = max(-self.max_spd * REVERSE_SPEED_RATIO, self.spd - self.brake_rate * dt)
            else:
                self.spd *= max(0, 1 - self.drag * dt)
            if abs(self.spd) > SPEED_THRESHOLD_STEER:
                self.angle += steer * self.turn_rate * dt * (self.spd / self.max_spd)
        if controlled:
            if self._vel_angle is None or abs(self.spd) < SPEED_THRESHOLD_STEER:
                self._vel_angle = self.angle
            align = DRIFT_ANGLE_ALIGN if drift_active else NORMAL_ANGLE_ALIGN
            diff = ((self.angle - self._vel_angle + 180) % 360) - 180
            self._vel_angle += diff * min(1.0, align * dt)
            rad = math.radians(self._vel_angle)
        else:
            self._vel_angle = self.angle
            rad = math.radians(self.angle)
        return math.sin(rad) * self.spd * dt, -math.cos(rad) * self.spd * dt

    def _move_with_collision(self, dx, dy, prev_spd, controlled, dt):
        s = current()
        from game2d.config import BUILDING_COLL_CHECK_DIST
        from game2d.systems.spatial import query_buildings_radius
        
        nx, ny = self.x + dx, self.y + dy
        tx = self.rect_at(nx, self.y)
        x_clear = self.cop_rect_clear(tx) if self.is_cop and not controlled else rect_on_road(tx)
        hit_x = False
        # Use spatial grid for building collision
        nearby_x = query_buildings_radius(tx.centerx, tx.centery, BUILDING_COLL_CHECK_DIST)
        for b_rect in nearby_x:
            if tx.colliderect(b_rect):
                hit_x = True
                break
        if not hit_x:
            hit_x = (self.roadblock_at(tx) is not None or (not controlled and not x_clear))
        ty = self.rect_at(self.x, ny)
        y_clear = self.cop_rect_clear(ty) if self.is_cop and not controlled else rect_on_road(ty)
        hit_y = False
        # Use spatial grid for building collision
        nearby_y = query_buildings_radius(ty.centerx, ty.centery, BUILDING_COLL_CHECK_DIST)
        for b_rect in nearby_y:
            if ty.colliderect(b_rect):
                hit_y = True
                break
        if not hit_y:
            hit_y = (self.roadblock_at(ty) is not None or (not controlled and not y_clear))
        mag = math.hypot(dx, dy) or 1
        if hit_x and hit_y:
            self.spd *= -0.2
            if abs(prev_spd) > DUAL_HIT_DAMAGE_THRESHOLD:
                self.take_damage(abs(prev_spd) * DUAL_HIT_DAMAGE_FACTOR, source_pos=(nx, ny))
        elif hit_x or hit_y:
            if hit_x:
                perp = abs(dx) / mag
                self.y = ny
                target = 0 if dy < 0 else 180
                source_pos = (self.x + (1 if dx > 0 else -1) * self.w, self.y)
            else:
                perp = abs(dy) / mag
                self.x = nx
                target = 90 if dx > 0 else 270
                source_pos = (self.x, self.y + (1 if dy > 0 else -1) * self.h)
            self.spd *= 1.0 - 0.43 * perp
            diff = ((target - self.angle + 180) % 360) - 180
            self.angle += diff * min(1.0, perp * 6 * dt)
            if abs(prev_spd) > SINGLE_HIT_DAMAGE_THRESHOLD and perp > SINGLE_HIT_PERP_MIN:
                self.take_damage(abs(prev_spd) * perp * SINGLE_HIT_DAMAGE_FACTOR, source_pos=source_pos)
        else:
            self.x, self.y = nx, ny
        for _ in range(4):
            other = self.overlaps_other_car()
            if not other:
                break
            self.resolve_car_collision(other, controlled)
        self.resolve_building_collisions(prev_spd)
        roadblock = self.roadblock_at(self.rect())
        if roadblock:
            self.resolve_roadblock_collision(roadblock, prev_spd)

    def _clamp_world_bounds(self, controlled):
        if controlled:
            self.x = max(PLAYER_BOUNDARY_MARGIN, min(WORLD_W - PLAYER_BOUNDARY_MARGIN, self.x))
            self.y = max(PLAYER_BOUNDARY_MARGIN, min(WORLD_H - PLAYER_BOUNDARY_MARGIN, self.y))
        else:
            self.x = max(ROAD_LO, min(ROAD_HI_X, self.x))
            self.y = max(ROAD_LO, min(ROAD_HI_Y, self.y))

    def _update_interactions(self, dt):
        self.hit_pedestrians(abs(self.spd))
        s = current()
        if s.in_car is not self and not self.dead:
            cr = self.rect()
            pr = s.player.rect()
            if cr.colliderect(pr):
                dx = s.player.x - self.x
                dy = s.player.y - self.y
                nx = dx / (math.hypot(dx, dy) or 1)
                ny = dy / (math.hypot(dx, dy) or 1)
                ox = (cr.w / 2 + PLAYER_PUSH_OFFSET) - abs(dx)
                oy = (cr.h / 2 + PLAYER_PUSH_OFFSET) - abs(dy)
                if ox > 0 and oy > 0:
                    if ox < oy:
                        s.player.x += nx * (ox + 1)
                    else:
                        s.player.y += ny * (oy + 1)
        if rect_in_park_pond(self.rect()):
            self.sink_in_pond()
            return
        self._leave_tire_trail(dt)

    def ai_update(self, dt):
        s = current()
        if self.sunk:
            self.spd = 0
            self.ai_spd = 0
            return
        if self.driver is None:
            self.spd *= max(0, 1 - CAR_IDLE_DECAY * dt)
            return
        self.yield_timer = max(0.0, self.yield_timer - dt)
        if self.is_roadblock_support:
            self.spd = 0
            self.ai_spd = 0
            return
        if self.is_roadblock:
            self.spd = 0
            self.ai_spd = 0
            lane_x, lane_y = lane_center_for_car(self.angle, self.x, self.y)
            self.x = move_toward(self.x, lane_x, ROADBLOCK_LANE_SPEED * dt)
            self.y = move_toward(self.y, lane_y, ROADBLOCK_LANE_SPEED * dt)
            return
        if self.is_cop:
            self._ai_cop_pursuit(dt)
            return
        if self.arc is not None:
            self._ai_arc_navigate(dt)
            return
        self._ai_normal_drive(dt)

    def _ai_cop_pursuit(self, dt):
        s = current()
        target = s.in_car if s.in_car else s.player
        dx = target.x - self.x
        dy = target.y - self.y
        dist = math.hypot(dx, dy) or 1
        lane_x, lane_y = lane_center_for_car(self.angle, self.x, self.y)
        self.x = move_toward(self.x, lane_x, COP_LANE_SPEED * dt)
        self.y = move_toward(self.y, lane_y, COP_LANE_SPEED * dt)
        desired = math.degrees(math.atan2(dx, -dy))
        diff = ((desired - self.angle + 180) % 360) - 180
        steer = max(-1, min(1, diff / COP_STEERING_DIV))
        target_spd = max(COP_MIN_SPEED, min(self.max_spd, COP_MAX_SPEED_BASE + s.player.wanted * COP_WANTED_SPEED_FACTOR))
        if s.in_car and dist < COP_FULL_SPEED_DIST:
            target_spd = self.max_spd
        accel = 1 if abs(self.spd) < target_spd else 0
        ahead = self.car_ahead()
        if ahead and ahead is not s.in_car:
            accel = -1
            steer *= 0.45
        if self.civilian_ahead():
            accel = -1
            steer *= 0.35
        if self.yield_timer > 0:
            accel = -1
            steer *= 0.35
        if abs(diff) > 115 and dist < 140:
            accel = -1
        speed_guess = max(COP_SPEED_GUESS_MIN, abs(self.spd) + COP_SPEED_GUESS_OFFSET)
        blocked = False
        if accel >= 0:
            forward_ang = self.angle + steer * COP_STEER_ANG
            rad = math.radians(forward_ang)
            nx = self.x + math.sin(rad) * speed_guess * dt * COP_LOOKAHEAD_FACTOR
            ny = self.y - math.cos(rad) * speed_guess * dt * COP_LOOKAHEAD_FACTOR
            test = self.rect_at(nx, ny)
            blocked = not self.cop_rect_clear(test)
            if not blocked:
                blocker = self.car_blocking_rect(test, padding=COP_BLOCKER_PADDING)
                if blocker and not (blocker.is_cop and s.in_car and blocker is not s.in_car and math.hypot(blocker.x - target.x, blocker.y - target.y) < 90):
                    blocked = True
            if blocked:
                for alt in (-1.0, 1.0, -0.65, 0.65):
                    ang2 = self.angle + alt * COP_ALT_STEER_BASE
                    rad2 = math.radians(ang2)
                    nx2 = self.x + math.sin(rad2) * speed_guess * dt
                    ny2 = self.y - math.cos(rad2) * speed_guess * dt
                    test2 = self.rect_at(nx2, ny2)
                    clear = self.cop_rect_clear(test2)
                    if clear:
                        clear = self.car_blocking_rect(test2, padding=COP_BLOCKER_PADDING) is None
                    if clear:
                        steer = alt
                        blocked = False
                        break
            if blocked:
                accel = -1
                steer = -1 if diff > 0 else 1
                self.turn_cd = random.uniform(COP_TURN_CD_MIN, COP_TURN_CD_MAX)
        self.update(dt, accel, steer)
        target_slow = (abs(s.in_car.spd) < COP_TARGET_SLOW_SPD) if s.in_car else True
        max_active_cops = COP_DEPLOY_MAX.get(s.player.wanted, max(2, s.player.wanted * 3))
        if dist < COP_DEPLOY_DIST and target_slow and self.deployed_cops < self.deploy_count and len(s.cops) < max_active_cops:
            for _ in range(10):
                if self.deployed_cops >= self.deploy_count or len(s.cops) >= max_active_cops:
                    break
                side = -1 if self.deployed_cops % 2 == 0 else 1
                forward = COP_DEPLOY_FWD_BASE + self.deployed_cops * COP_DEPLOY_FWD_STEP
                side_ang = math.radians(self.angle + 90 * side)
                forward_ang = math.radians(self.angle)
                side_dist = max(COP_DEPLOY_SIDE_MIN, self.coll_w / 2 + COP_DEPLOY_SIDE_OFFSET)
                px = self.x + math.sin(side_ang) * side_dist + math.sin(forward_ang) * forward
                py = self.y - math.cos(side_ang) * side_dist - math.cos(forward_ang) * forward
                pr = pygame.Rect(px - 10, py - 10, 20, 20)
                blocked = False
                for b_rect, b_surf in s.AI_OBSTACLES:
                    if abs(b_rect.centerx - px) > AI_OBS_DIST_COP or abs(b_rect.centery - py) > AI_OBS_DIST_COP:
                        continue
                    if pr.colliderect(b_rect):
                        blocked = True
                        break
                if not blocked:
                    blocked = any(pr.colliderect(car.rect()) for car in s.cars if car is not self and not car.dead)
                if in_city(px, py, 8) and not blocked:
                    cop = Ped(px, py, is_cop=True, cop_kind=self.kind)
                    cop.shoot_tick = 0.25
                    s.cops.append(cop)
                    register_entity(cop)  # Spatial Grid Registrierung
                    emit_entity_spawned(cop, "cop")
                    self.deployed_cops += 1
                    self.spd *= 0.35
            if self.deployed_cops >= self.deploy_count:
                self.driver = None
                self.spd = 0

    def _ai_arc_navigate(self, dt):
        arc = self.arc
        arc_spd = min(ARC_SPD_MAX, max(ARC_SPD_MIN, self.ai_spd * 0.82))
        if arc["r"] < ARC_TIGHT_R:
            arc_spd = min(arc_spd, ARC_TIGHT_SPD)
        self.spd = move_toward(max(0.0, self.spd), arc_spd, ARC_ACCEL * dt)
        theta_next = arc["theta"] + (self.spd / arc["r"]) * arc["omega"] * dt
        if arc["omega"] > 0:
            theta_next = min(theta_next, arc["theta_end"])
            done = theta_next >= arc["theta_end"]
        else:
            theta_next = max(theta_next, arc["theta_end"])
            done = theta_next <= arc["theta_end"]
        if done:
            next_x = arc["end_x"]
            next_y = arc["end_y"]
            next_angle = arc["target"]
        else:
            next_x, next_y, next_angle = self.arc_pose(arc, theta_next)
        blocker = self.car_blocking_rect(self.rect_at_angle(next_x, next_y, next_angle), padding=10)
        if blocker:
            self.spd = move_toward(max(0.0, self.spd), 0.0, ARC_BLOCKER_DECEL * dt)
            self.yield_timer = max(self.yield_timer, ARC_BLOCKER_YIELD)
            return
        arc["theta"] = theta_next
        if done:
            self.angle = arc["target"]
            self.x = next_x
            self.y = next_y
            self.arc = None
            self.signal_dir = 0
        else:
            self.x = next_x
            self.y = next_y
            self.angle = next_angle

    def _ai_normal_drive(self, dt):
        s = current()
        lane_x, lane_y = lane_center_for_car(self.angle, self.x, self.y)
        self.x = move_toward(self.x, lane_x, LANE_CENTER_SPD * dt)
        self.y = move_toward(self.y, lane_y, LANE_CENTER_SPD * dt)
        self.turn_cd -= dt
        if self.turn_cd <= 0 and self.upcoming_intersection(INTERSECTION_AHEAD):
            self.plan_intersection_turn(allow_reverse=self.near_road_end())
        if (not traffic_rule_allows(self, dt) or self.yield_timer > 0 or
                self.should_yield_at_intersection() or self.car_ahead() or
                not self.reserve_intersection()):
            self.spd *= max(0.0, 1 - BRAKE_DECAY * dt)
            return
        rad = math.radians(self.angle)
        nx = self.x + math.sin(rad) * self.ai_spd * dt
        ny = self.y - math.cos(rad) * self.ai_spd * dt
        test = self.rect_at(nx, ny)
        blocked = False
        for b_rect, b_surf in s.AI_OBSTACLES:
            if abs(b_rect.centerx - test.centerx) > AI_OBS_DIST_NORMAL or abs(b_rect.centery - test.centery) > AI_OBS_DIST_NORMAL:
                continue
            if test.colliderect(b_rect):
                blocked = True
                break
        if not blocked:
            blocked = (any(test.colliderect(rb.rect) for rb in s.roadblocks) or
                       not rect_on_road(test))
        if not blocked and self.car_blocking_rect(test, padding=10):
            blocked = True
        _ix = nearest_road_x(self.x)
        _iy = nearest_road_y(self.y)
        _ar = math.radians(self.angle)
        _fwd_dist = ((_ix - self.x) * math.sin(_ar) + (_iy - self.y) * (-math.cos(_ar)))
        _perp_on_road = (abs(self.x - _ix) < INTERSECTION_PERP_TOL if self.is_vertical() else abs(self.y - _iy) < INTERSECTION_PERP_TOL)
        at_intersection = _perp_on_road and INTERSECTION_ZONE_MIN < _fwd_dist < INTERSECTION_ZONE_MAX
        road_end = self.near_road_end()
        if at_intersection and road_end:
            self.choose_intersection_turn(allow_reverse=True)
        if blocked:
            if at_intersection and self.arc is None:
                self.choose_intersection_turn(allow_reverse=road_end)
            self.spd *= max(0.0, 1 - BRAKE_DECAY_BLOCKED * dt)
            self.yield_timer = max(self.yield_timer, YIELD_TIMER_BLOCKED)
            return
        if at_intersection and self.turn_cd <= 0 and not road_end:
            self.choose_intersection_turn(allow_reverse=False)
        self.x, self.y = nx, ny
        for _ in range(4):
            other = self.overlaps_other_car()
            if not other:
                break
            self.resolve_car_collision(other, False)
            self.turn_cd = random.uniform(CAR_COLL_TURN_CD_MIN, CAR_COLL_TURN_CD_MAX)
            self.arc = None
            self.planned_turn = None
            self.signal_dir = 0

    def get_rotated_sprite(self, angle):
        """Holt oder generiert ein rotiertes Sprite aus dem Cache.
        
        Reduziert teure pygame.transform.rotate() Aufrufe.
        """
        # Normalisiere Winkel auf 0-360 für besseren Cache-Hit
        norm_angle = angle % 360
        
        if norm_angle == self._last_rotated_angle:
            return self._last_rotated_sprite
        
        if norm_angle in self._rotated_sprite_cache:
            self._last_rotated_angle = norm_angle
            self._last_rotated_sprite = self._rotated_sprite_cache[norm_angle]
            return self._last_rotated_sprite
        
        # Generieren und cachen
        rotated = pygame.transform.rotate(self._sprite_with_damage(), -norm_angle)
        self._rotated_sprite_cache[norm_angle] = rotated
        self._last_rotated_angle = norm_angle
        self._last_rotated_sprite = rotated
        
        # Cache-Größe begrenzen (vermeide Speicherlecks)
        if len(self._rotated_sprite_cache) > 36:  # Max 36 verschiedene Winkel
            # Lösche ältesten Eintrag (einfach: ersten löschen)
            oldest_key = next(iter(self._rotated_sprite_cache))
            del self._rotated_sprite_cache[oldest_key]
        
        return rotated

    def draw(self, surf, cam):
        if self.sunk:
            self.draw_sunk(surf, cam)
            return
        rot = self.get_rotated_sprite(self.angle)
        r = rot.get_rect(center=(self.x - cam[0], self.y - cam[1]))
        surf.blit(rot, r)
        if self.is_roadblock:
            self.draw_roadblock_markers(surf, cam)
        if self.hazard_lights_active():
            self.draw_indicator_lamps(surf, cam, (-1, 1))
            return
        self.draw_turn_signal(surf, cam)

    def hazard_lights_active(self):
        return self.driver is None and not self.is_roadblock and abs(self.spd) < 8 and not self.burning

    def draw_indicator_lamps(self, surf, cam, sides):
        if (pygame.time.get_ticks() // 280) % 2:
            return
        rad = math.radians(self.angle)
        cs, sn = math.cos(rad), math.sin(rad)
        cx = self.x - cam[0]
        cy = self.y - cam[1]
        front_y = -self.h * 0.34
        back_y = self.h * 0.34
        lamp_col = (255, 180, 40)
        glow_col = (255, 220, 120)
        for side in sides:
            side_x = self.w * 0.34 * side
            for dx_, dy_ in ((side_x, front_y), (side_x, back_y)):
                wx = dx_ * cs - dy_ * sn
                wy = dx_ * sn + dy_ * cs
                pos = (int(cx + wx), int(cy + wy))
                pygame.draw.circle(surf, glow_col, pos, 4)
                pygame.draw.circle(surf, lamp_col, pos, 2)

    def draw_turn_signal(self, surf, cam):
        if self.signal_dir == 0:
            return
        if self.arc is None and self.planned_turn is None:
            return
        self.draw_indicator_lamps(surf, cam, (self.signal_dir,))

    def draw_sunk(self, surf, cam):
        rear_h = max(18, int(self.h * 0.34))
        rear = self.sprite.subsurface((0, self.h - rear_h, self.w, rear_h)).copy()
        shade = pygame.Surface(rear.get_size(), pygame.SRCALPHA)
        shade.fill((55, 75, 85, 115))
        rear.blit(shade, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        rot = pygame.transform.rotate(rear, -self.angle)
        cx = self.x - cam[0]
        cy = self.y - cam[1]
        r = rot.get_rect(center=(cx, cy))
        pool_w = max(76, int(self.w * 1.55))
        pool_h = max(36, int(self.w * 0.82))
        pygame.draw.ellipse(surf, (35, 104, 145), (int(cx - pool_w / 2), int(cy - pool_h / 2), pool_w, pool_h))
        pygame.draw.ellipse(
            surf,
            (96, 168, 198),
            (int(cx - pool_w / 2 - 6), int(cy - pool_h / 2 - 4), pool_w + 12, pool_h + 8),
            2,
        )
        surf.blit(rot, r)

    def draw_roadblock_markers(self, surf, cam):
        marker_angle = (self.angle + 90) % 360
        rad = math.radians(marker_angle)
        cs, sn = math.cos(rad), math.sin(rad)
        cx = self.x - cam[0]
        cy = self.y - cam[1]
        barrier = pygame.Surface((132, 18), pygame.SRCALPHA)
        pygame.draw.rect(barrier, (238, 238, 230), (0, 0, 132, 18), border_radius=3)
        pygame.draw.rect(barrier, (55, 55, 60), (0, 7, 132, 4), border_radius=2)
        for x in range(-16, 134, 24):
            pygame.draw.polygon(barrier, (220, 40, 35), [(x, 18), (x + 14, 18), (x + 34, 0), (x + 20, 0)])
        rot_barrier = pygame.transform.rotate(barrier, -marker_angle)
        normal_x = math.sin(math.radians(self.angle))
        normal_y = -math.cos(math.radians(self.angle))
        for lateral in (-20, 20):
            bx = cx + normal_x * lateral
            by = cy + normal_y * lateral
            surf.blit(rot_barrier, rot_barrier.get_rect(center=(bx, by)))
        for offset in (-78, -52, 52, 78):
            wx = offset * cs
            wy = offset * sn
            x = int(cx + wx)
            y = int(cy + wy)
            pygame.draw.polygon(surf, (245, 120, 25), [(x, y - 9), (x - 7, y + 8), (x + 7, y + 8)])
            pygame.draw.rect(surf, (245, 245, 245), (x - 5, y + 1, 10, 3))
