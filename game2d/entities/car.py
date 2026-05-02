"""Fahrzeug-Klasse: Spieler-/NPC-/Cop-Auto, Physik, KI, Kollisionen."""
import math
import random
import pygame

from game2d.config import (
    BLOCK, ROAD_LO, ROAD_HI_X, ROAD_HI_Y,
    WORLD_W, WORLD_H, TIRE_BLOOD, TIRE_SKID,
)
from game2d.render.sprites import make_car_sprite, make_cop_car_sprite
from game2d.state import current
from game2d.world.geometry import (
    in_city, lane_center_for_car, move_toward,
    intersection_zone_at, point_in_polygon, rect_in_park_pond, rect_on_road,
    nearest_road_x, nearest_road_y,
)
from game2d.world.traffic import traffic_light_allows
from game2d.systems.effects import spawn_blood, make_corpse, trigger_game_over
from game2d.systems import audio
from game2d.entities.ped import Ped


class Car:
    def __init__(self, x, y, body, is_cop=False):
        self.x, self.y = x, y
        self.angle = random.choice([0, 90, 180, 270])
        self.spd = 0
        self.max_spd = 400 if is_cop else 320
        self.is_cop = is_cop
        self.driver = True if is_cop else None  # None = geparkt, True/Ped = hat Fahrer
        self.is_roadblock = False
        self.is_roadblock_support = False
        self.sprite = make_cop_car_sprite() if is_cop else make_car_sprite(body)
        self.w, self.h = self.sprite.get_size()
        self.max_hp = 500
        self.hp = 500
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
        self.yield_timer = 0.0
        self.ai_spd = random.uniform(150, 240) if is_cop else random.uniform(80, 160)
        self.turn_cd = random.uniform(2, 6)
        self.arc = None
        self.planned_turn = None
        self.signal_dir = 0
        self._siren_channel = None
        self._squeal_channel = None
        self._vel_angle = None   # tatsächliche Bewegungsrichtung (für Drift)
        self._drifting = False
        self._skid_cd = 0.0

    def take_damage(self, dmg):
        if self.dead or self.sunk or dmg <= 0: return
        self.hp -= dmg
        n = max(1, int(dmg // 18))
        for _ in range(min(n, 4)):
            if len(self.dents) >= 35: break
            rx = random.uniform(-self.w*0.42, self.w*0.42)
            ry = random.uniform(-self.h*0.42, self.h*0.42)
            self.dents.append((rx, ry, random.randint(3, 6)))
        if self.hp <= 0 and not self.burning:
            self.hp = 0
            self.burning = True
            self.burn_timer = random.uniform(2.5, 4.0)

    def explode(self):
        s = current()
        self.dead = True
        if self._siren_channel is not None:
            audio.stop_loop(self._siren_channel)
            self._siren_channel = None
        s.explosions.append([self.x, self.y, 0.0, 0.55, 150])
        audio.play('explosion', pos=(self.x, self.y))
        if s.in_car is self:
            audio.set_engine(False)
        R = 130
        for p in list(s.peds):
            if math.hypot(p.x-self.x, p.y-self.y) < R:
                p.hp -= 90
                spawn_blood(p.x, p.y, 6)
                if p.hp <= 0:
                    s.peds.remove(p)
                    s.corpses.append((make_corpse(p), p.x, p.y, p.angle))
                    spawn_blood(p.x, p.y, 18)
        for c in list(s.cops):
            if math.hypot(c.x-self.x, c.y-self.y) < R:
                c.hp -= 90
                spawn_blood(c.x, c.y, 6)
                if c.hp <= 0:
                    s.cops.remove(c)
                    s.corpses.append((make_corpse(c), c.x, c.y, c.angle))
                    spawn_blood(c.x, c.y, 20)
                    s.player.money += random.randint(40, 80)
        for c in s.cars:
            if c is self or c.dead: continue
            if math.hypot(c.x-self.x, c.y-self.y) < R + 10:
                c.take_damage(110)
        if math.hypot(s.player.x-self.x, s.player.y-self.y) < R:
            s.player.hp -= 95 if s.in_car is self else 60
            if s.player.hp <= 0:
                s.corpses.append((make_corpse(s.player), s.player.x, s.player.y, s.player.angle))
                spawn_blood(s.player.x, s.player.y, 24)
                trigger_game_over()
        if s.in_car is self:
            s.in_car = None
        for _ in range(45):
            a = random.uniform(0, 6.28); sp = random.uniform(80, 320)
            s.fire_particles.append([self.x, self.y, math.cos(a)*sp, math.sin(a)*sp,
                                     random.uniform(0.4, 0.9), 0.9, random.randint(4, 8)])
        for _ in range(35):
            a = random.uniform(0, 6.28); sp = random.uniform(40, 180)
            s.smoke_particles.append([self.x, self.y, math.cos(a)*sp, math.sin(a)*sp - 30,
                                      random.uniform(1.8, 3.5), 3.5, random.randint(6, 11)])
        wreck_surf = self.sprite.copy()
        scorch = pygame.Surface(wreck_surf.get_size(), pygame.SRCALPHA)
        scorch.fill((20, 20, 20, 200))
        wreck_surf.blit(scorch, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
        s.wrecks.append((wreck_surf, self.x, self.y, self.angle, list(self.dents)))
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
                s.fire_particles.append([self.x + random.uniform(-12, 12),
                                         self.y + random.uniform(-15, 15),
                                         random.uniform(-25, 25), random.uniform(-70, -25),
                                         random.uniform(0.3, 0.6), 0.6, random.randint(3, 6)])
            self._smoke_cd -= dt
            if self._smoke_cd <= 0:
                self._smoke_cd = 0.08
                s.smoke_particles.append([self.x, self.y, random.uniform(-15, 15),
                                          random.uniform(-55, -25), random.uniform(1.5, 2.8), 2.8,
                                          random.randint(5, 9)])
            if self.burn_timer <= 0:
                self.explode()
        elif self.hp < self.max_hp * 0.6:
            self._smoke_cd -= dt
            heavy = self.hp < self.max_hp * 0.3
            rate = 0.10 if heavy else 0.28
            if self._smoke_cd <= 0:
                self._smoke_cd = rate
                col_r = random.randint(4, 8) if heavy else random.randint(3, 6)
                s.smoke_particles.append([self.x, self.y, random.uniform(-10, 10),
                                          random.uniform(-45, -18), random.uniform(1.2, 2.2), 2.2, col_r])

    def rect_at_angle(self, x, y, angle):
        if abs(math.cos(math.radians(angle))) >= abs(math.sin(math.radians(angle))):
            w, h = 34, 62
        else:
            w, h = 62, 34
        return pygame.Rect(x - w//2, y - h//2, w, h)

    def rect_at(self, x, y):
        return self.rect_at_angle(x, y, self.angle)

    def rect(self):
        return self.rect_at(self.x, self.y)

    def look_rect(self, distance=78, width=44):
        rad = math.radians(self.angle)
        cx = self.x + math.sin(rad) * distance
        cy = self.y - math.cos(rad) * distance
        if self.is_vertical():
            return pygame.Rect(cx - width//2, cy - 34, width, 68)
        return pygame.Rect(cx - 34, cy - width//2, 68, width)

    def overlaps_other_car(self):
        own = self.rect()
        for other in current().cars:
            if other is self or other.dead or other.sunk:
                continue
            if own.colliderect(other.rect()):
                return other
        return None

    def car_blocking_rect(self, rect, padding=8):
        for other in current().cars:
            if other is self or other.dead or other.sunk:
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
            self.take_damage(impact * 0.05)
            audio.play('crash', volume=min(1.0, impact / 260.0), pos=(self.x, self.y))
        self.spd *= -0.18 if impact > 45 else 0

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
        push = max(1.5, min(overlap_x, overlap_y, 10.0))
        anchored_self = self.is_roadblock and not controlled
        anchored_other = other.is_roadblock and other is not s.in_car
        if anchored_self and anchored_other:
            anchored_self = False
        if anchored_self:
            self.x += nx * push * 0.08
            self.y += ny * push * 0.08
        elif anchored_other:
            other.x -= nx * push * 0.08
            other.y -= ny * push * 0.08
        elif controlled:
            self.x += nx * push * 0.2
            self.y += ny * push * 0.2
            other.x -= nx * push * 0.55
            other.y -= ny * push * 0.55
        else:
            if overlap_x < overlap_y:
                side = 1 if self.x >= other.x else -1
                sep = overlap_x + 2
                self.x += side * sep * 0.5
                other.x -= side * sep * 0.5
            else:
                side = 1 if self.y >= other.y else -1
                sep = overlap_y + 2
                self.y += side * sep * 0.5
                other.y -= side * sep * 0.5
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
            self.take_damage(dmg)
            other.take_damage(dmg * (0.85 if controlled else 1.0))
            cx = (self.x + other.x) * 0.5
            cy = (self.y + other.y) * 0.5
            audio.play('crash', volume=min(1.0, impact / 260.0), pos=(cx, cy))

    def _wheel_points(self):
        rad = math.radians(self.angle)
        cs, sn = math.cos(rad), math.sin(rad)
        pts = []
        for dx_, dy_ in ((-self.w*0.38, -self.h*0.28), (self.w*0.38, -self.h*0.28),
                         (-self.w*0.38, self.h*0.28), (self.w*0.38, self.h*0.28)):
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
        zone = self.upcoming_intersection()
        if not zone:
            return False
        ix, iy, _ = zone
        my_vertical = self.is_vertical()
        my_dist = math.hypot(self.x - ix, self.y - iy)
        for other in current().cars:
            if other is self or other.dead:
                continue
            other_zone = other.upcoming_intersection(65)
            if not other_zone:
                other_zone = intersection_zone_at(other.x, other.y, margin=18)
            if not other_zone:
                continue
            ox, oy, orect = other_zone
            if abs(ox - ix) > 6 or abs(oy - iy) > 6:
                continue
            if other.is_vertical() == my_vertical:
                continue
            other_dist = math.hypot(other.x - ix, other.y - iy)
            other_in_box = orect.collidepoint(other.x, other.y)
            if other_in_box or other_dist + 10 < my_dist or (abs(other_dist - my_dist) <= 10 and id(other) < id(self)):
                self.yield_timer = max(self.yield_timer, random.uniform(0.12, 0.28))
                return True
        return False

    def car_ahead(self):
        probe = self.look_rect(82, 46)
        rad = math.radians(self.angle)
        fx, fy = math.sin(rad), -math.cos(rad)
        for other in current().cars:
            if other is self or other.dead:
                continue
            diff = abs(((other.angle - self.angle + 180) % 360) - 180)
            if diff > 35:
                continue
            ox, oy = other.x - self.x, other.y - self.y
            ahead = ox * fx + oy * fy
            if 0 < ahead < 105 and probe.colliderect(other.rect()):
                return other
        return None

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
        if any(look.colliderect(park) for park in current().parks):
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
            tx = lx + math.sin(rad) * 120
            ty = ly - math.cos(rad) * 120
            if rect_on_road(self.rect_at_angle(lx, ly, angle)) and rect_on_road(self.rect_at_angle(tx, ty, angle)):
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
        radius = max(20.0, min(68.0 if diff > 0 else 92.0, depth))

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
        radius = 34.0
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
                s.player.wanted = min(5, s.player.wanted + 1)
                s.player.crime_timer = 30
                if not is_cop:
                    s.player.money += random.randint(10, 35)
        return True

    def _run_over_player(self, damage):
        s = current()
        if s.in_car is self or not self.rect().colliderect(s.player.rect()):
            return False
        s.player.hp -= damage
        self.blood_trail = max(self.blood_trail, 4.0)
        spawn_blood(s.player.x, s.player.y, 6)
        if s.player.hp <= 0:
            s.corpses.append((make_corpse(s.player), s.player.x, s.player.y, s.player.angle))
            spawn_blood(s.player.x, s.player.y, 22)
            trigger_game_over()
        return True

    def hit_pedestrians(self, speed_mag):
        if speed_mag < 85 or self.dead:
            return
        s = current()
        dmg = max(18, min(120, int(speed_mag * 0.45)))
        for p in list(s.peds):
            self._run_over_ped(p, s.peds, dmg, is_cop=False)
        for c in list(s.cops):
            self._run_over_ped(c, s.cops, dmg + 12, is_cop=True)
        self._run_over_player(dmg + 10)

    def update(self, dt, accel=0, steer=0, handbrake=False):
        if self.dead or self.sunk:
            self.spd = 0
            return
        s = current()
        controlled = (self is s.in_car)
        prev_spd = self.spd

        drift_active = handbrake and controlled and abs(self.spd) > 50
        self._drifting = drift_active

        if drift_active:
            # Handbremse: leichtes Abbremsen, damit Drift lang anhält
            self.spd *= max(0, 1 - 0.7 * dt)
            if abs(self.spd) > 5:
                self.angle += steer * 155 * dt * max(0.4, abs(self.spd) / self.max_spd)
            self._leave_skid_trail(dt)
        else:
            if accel > 0:
                self.spd = min(self.max_spd, self.spd + 260 * dt)
            elif accel < 0:
                self.spd = max(-self.max_spd*0.5, self.spd - 260 * dt)
            else:
                self.spd *= max(0, 1 - 1.4 * dt)
            if abs(self.spd) > 5:
                self.angle += steer * 110 * dt * (self.spd/self.max_spd)

        # Bewegungsrichtung: Spieler benutzt vel_angle (lags beim Driften)
        if controlled:
            if self._vel_angle is None or abs(self.spd) < 5:
                self._vel_angle = self.angle
            align = 1.5 if drift_active else 14.0
            diff = ((self.angle - self._vel_angle + 180) % 360) - 180
            self._vel_angle += diff * min(1.0, align * dt)
            rad = math.radians(self._vel_angle)
        else:
            self._vel_angle = self.angle
            rad = math.radians(self.angle)

        dx = math.sin(rad) * self.spd * dt
        dy = -math.cos(rad) * self.spd * dt
        nx, ny = self.x + dx, self.y + dy
        tx = self.rect_at(nx, self.y)
        hit_x = (any(tx.colliderect(b[0]) for b in s.buildings) or
                 self.roadblock_at(tx) is not None or
                 (not controlled and not rect_on_road(tx)))
        ty = self.rect_at(self.x, ny)
        hit_y = (any(ty.colliderect(b[0]) for b in s.buildings) or
                 self.roadblock_at(ty) is not None or
                 (not controlled and not rect_on_road(ty)))
        mag = math.hypot(dx, dy) or 1
        if hit_x and hit_y:
            self.spd *= -0.2
            if abs(prev_spd) > 60:
                self.take_damage(abs(prev_spd) * 0.09)
        elif hit_x or hit_y:
            if hit_x:
                perp, par = abs(dx) / mag, abs(dy) / mag
                self.y = ny
                target = 0 if dy < 0 else 180
            else:
                perp, par = abs(dy) / mag, abs(dx) / mag
                self.x = nx
                target = 90 if dx > 0 else 270
            self.spd *= 1.0 - 0.43 * perp
            diff = ((target - self.angle + 180) % 360) - 180
            self.angle += diff * min(1.0, perp * 6 * dt)
            if abs(prev_spd) > 80 and perp > 0.25:
                self.take_damage(abs(prev_spd) * perp * 0.045)
        else:
            self.x, self.y = nx, ny
        other = self.overlaps_other_car()
        if other:
            self.resolve_car_collision(other, controlled)
        roadblock = self.roadblock_at(self.rect())
        if roadblock:
            self.resolve_roadblock_collision(roadblock, prev_spd)
        if controlled:
            self.x = max(40, min(WORLD_W-40, self.x))
            self.y = max(40, min(WORLD_H-40, self.y))
        else:
            self.x = max(ROAD_LO, min(ROAD_HI_X, self.x))
            self.y = max(ROAD_LO, min(ROAD_HI_Y, self.y))
        self.hit_pedestrians(abs(self.spd))
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
        if not self.is_cop and self.driver is None:
            self.spd *= max(0, 1 - 2.5 * dt)
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
            self.x = move_toward(self.x, lane_x, 18 * dt)
            self.y = move_toward(self.y, lane_y, 18 * dt)
            return
        if self.is_cop:
            target = s.in_car if s.in_car else s.player
            dx = target.x - self.x
            dy = target.y - self.y
            dist = math.hypot(dx, dy) or 1
            lane_x, lane_y = lane_center_for_car(self.angle, self.x, self.y)
            self.x = move_toward(self.x, lane_x, 22 * dt)
            self.y = move_toward(self.y, lane_y, 22 * dt)
            desired = math.degrees(math.atan2(dx, -dy))
            diff = ((desired - self.angle + 180) % 360) - 180
            steer = max(-1, min(1, diff / 35))
            target_spd = max(155, min(self.max_spd, 175 + s.player.wanted * 34))
            if s.in_car and dist < 220:
                target_spd = self.max_spd
            accel = 1 if abs(self.spd) < target_spd else 0
            ahead = self.car_ahead()
            if ahead and ahead is not s.in_car:
                accel = -1
                steer *= 0.45
            red_light = not traffic_light_allows(self)
            if red_light or self.yield_timer > 0 or (dist > 110 and self.should_yield_at_intersection()) or not self.reserve_intersection(urgent=dist < 180):
                accel = -1
                steer *= 0.35
            if abs(diff) > 115 and dist < 140:
                accel = -1
            speed_guess = max(105, abs(self.spd) + 70)
            blocked = False
            if accel >= 0:
                forward_ang = self.angle + steer * 34
                rad = math.radians(forward_ang)
                nx = self.x + math.sin(rad) * speed_guess * dt * 1.2
                ny = self.y - math.cos(rad) * speed_guess * dt * 1.2
                test = self.rect_at(nx, ny)
                blocked = any(test.colliderect(b[0]) for b in s.AI_OBSTACLES) or not rect_on_road(test)
                if not blocked:
                    blocker = self.car_blocking_rect(test, padding=8)
                    if blocker and not (blocker.is_cop and s.in_car and blocker is not s.in_car and math.hypot(blocker.x - target.x, blocker.y - target.y) < 90):
                        blocked = True
                if blocked:
                    for alt in (-1.0, 1.0, -0.65, 0.65):
                        ang2 = self.angle + alt * 52
                        rad2 = math.radians(ang2)
                        nx2 = self.x + math.sin(rad2) * speed_guess * dt
                        ny2 = self.y - math.cos(rad2) * speed_guess * dt
                        test2 = self.rect_at(nx2, ny2)
                        clear = (not any(test2.colliderect(b[0]) for b in s.AI_OBSTACLES) and
                                 not any(test2.colliderect(rb.rect) for rb in s.roadblocks) and
                                 rect_on_road(test2))
                        if clear:
                            clear = self.car_blocking_rect(test2, padding=8) is None
                        if clear:
                            steer = alt
                            blocked = False
                            break
                if blocked:
                    accel = -1
                    steer = -1 if diff > 0 else 1
                    self.turn_cd = random.uniform(0.6, 1.2)
            self.update(dt, accel, steer)
            target_slow = (abs(s.in_car.spd) < 28) if s.in_car else True
            if dist < 120 and target_slow and self.deployed_cops < 2 and len(s.cops) < s.player.wanted * 3:
                side = -1 if random.random() < 0.5 else 1
                ang = math.radians(self.angle + 90 * side)
                px = self.x + math.sin(ang) * 34
                py = self.y - math.cos(ang) * 34
                pr = pygame.Rect(px - 10, py - 10, 20, 20)
                if in_city(px, py, 8) and not any(pr.colliderect(b[0]) for b in s.AI_OBSTACLES):
                    cop = Ped(px, py, is_cop=True)
                    cop.shoot_tick = 0.35
                    s.cops.append(cop)
                    self.deployed_cops += 1
                    self.spd *= 0.35
            return
        if self.arc is not None:
            arc = self.arc
            arc_spd = min(148.0, max(105.0, self.ai_spd * 0.82))
            if arc["r"] < 48:
                arc_spd = min(arc_spd, 122.0)
            self.spd = move_toward(max(0.0, self.spd), arc_spd, 420 * dt)
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
                self.spd = move_toward(max(0.0, self.spd), 0.0, 560 * dt)
                self.yield_timer = max(self.yield_timer, 0.16)
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
            return

        lane_x, lane_y = lane_center_for_car(self.angle, self.x, self.y)
        self.x = move_toward(self.x, lane_x, 26 * dt)
        self.y = move_toward(self.y, lane_y, 26 * dt)
        self.turn_cd -= dt
        if self.turn_cd <= 0 and self.upcoming_intersection(150):
            self.plan_intersection_turn(allow_reverse=self.near_road_end())
        if not traffic_light_allows(self) or self.yield_timer > 0 or self.should_yield_at_intersection() or self.car_ahead() or not self.reserve_intersection():
            self.spd *= max(0.0, 1 - 2.6 * dt)
            return
        rad = math.radians(self.angle)
        nx = self.x + math.sin(rad) * self.ai_spd * dt
        ny = self.y - math.cos(rad) * self.ai_spd * dt
        test = self.rect_at(nx, ny)
        blocked = (any(test.colliderect(b[0]) for b in s.AI_OBSTACLES) or
                   any(test.colliderect(rb.rect) for rb in s.roadblocks) or
                   not rect_on_road(test))
        if not blocked and self.car_blocking_rect(test, padding=10):
            blocked = True
        if blocked:
            self.spd *= max(0.0, 1 - 3.0 * dt)
            self.yield_timer = max(self.yield_timer, 0.12)
            return
        # Frühzeitige Kreuzungserkennung: Abstand zur nächsten Kreuzung in Fahrtrichtung
        _ix = nearest_road_x(self.x); _iy = nearest_road_y(self.y)
        _ar = math.radians(self.angle)
        _fwd_dist = ((_ix - self.x) * math.sin(_ar) + (_iy - self.y) * (-math.cos(_ar)))
        _perp_on_road = (abs(self.x - _ix) < 34 if self.is_vertical() else abs(self.y - _iy) < 34)
        at_intersection = _perp_on_road and 18 < _fwd_dist < 94
        if at_intersection and (self.turn_cd <= 0 or self.near_road_end()):
            self.choose_intersection_turn(allow_reverse=self.near_road_end())
        self.x, self.y = nx, ny
        other = self.overlaps_other_car()
        if other:
            self.resolve_car_collision(other, False)
            self.turn_cd = random.uniform(1.2, 2.6)
            self.arc = None
            self.planned_turn = None
            self.signal_dir = 0

    def draw(self, surf, cam):
        if self.sunk:
            self.draw_sunk(surf, cam)
            return
        rot = pygame.transform.rotate(self.sprite, -self.angle)
        r = rot.get_rect(center=(self.x - cam[0], self.y - cam[1]))
        surf.blit(rot, r)
        if self.is_roadblock:
            self.draw_roadblock_markers(surf, cam)
        if self.dents:
            rad = math.radians(self.angle)
            cs, sn = math.cos(rad), math.sin(rad)
            cx_ = self.x - cam[0]; cy_ = self.y - cam[1]
            for dx_, dy_, dr_ in self.dents:
                wx = dx_ * cs - dy_ * sn
                wy = dx_ * sn + dy_ * cs
                pygame.draw.circle(surf, (25, 25, 28), (int(cx_ + wx), int(cy_ + wy)), dr_)
        self.draw_turn_signal(surf, cam)

    def draw_turn_signal(self, surf, cam):
        if self.signal_dir == 0:
            return
        if self.arc is None and self.planned_turn is None:
            return
        if (pygame.time.get_ticks() // 280) % 2:
            return
        rad = math.radians(self.angle)
        cs, sn = math.cos(rad), math.sin(rad)
        cx = self.x - cam[0]
        cy = self.y - cam[1]
        front_y = -self.h * 0.34
        back_y = self.h * 0.34
        side_x = self.w * 0.34 * self.signal_dir
        lamp_col = (255, 180, 40)
        glow_col = (255, 220, 120)
        for dx_, dy_ in ((side_x, front_y), (side_x, back_y)):
            wx = dx_ * cs - dy_ * sn
            wy = dx_ * sn + dy_ * cs
            pos = (int(cx + wx), int(cy + wy))
            pygame.draw.circle(surf, glow_col, pos, 4)
            pygame.draw.circle(surf, lamp_col, pos, 2)

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
        pygame.draw.ellipse(surf, (35, 104, 145), (int(cx - 38), int(cy - 18), 76, 36))
        pygame.draw.ellipse(surf, (96, 168, 198), (int(cx - 44), int(cy - 22), 88, 44), 2)
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
