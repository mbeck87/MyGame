"""Fußgänger und Cops zu Fuß."""
import math
import random
import pygame

from game2d.config import COP_BLUE
from game2d.render.sprites import make_ped_frames, make_swim_frames
from game2d.state import current
from game2d.world.geometry import (
    nearest_pedestrian_node,
    pedestrian_path,
    random_pedestrian_destination,
    pedestrian_step_clear,
    rect_in_park_pond,
)


COP_KIND_PROFILES = {
    "cop": {
        "shirt": COP_BLUE,
        "hp": 200,
        "speed": 110,
    },
    "fbi": {
        "shirt": (24, 24, 28),
        "hp": 220,
        "speed": 118,
    },
    "swat": {
        "shirt": (16, 24, 38),
        "hp": 280,
        "speed": 106,
    },
    "military": {
        "shirt": (70, 88, 48),
        "hp": 310,
        "speed": 112,
    },
}


def normalize_cop_kind(kind):
    aliases = {
        "police": "cop",
        "polizei": "cop",
        "army": "military",
        "militaer": "military",
        "militär": "military",
    }
    kind = aliases.get(kind, kind)
    return kind if kind in COP_KIND_PROFILES else "cop"


class Ped:
    def __init__(self, x, y, is_cop=False, cop_kind="cop"):
        self.x, self.y = x, y
        self.is_cop = is_cop
        self.cop_kind = normalize_cop_kind(cop_kind) if is_cop else None
        if is_cop:
            profile = COP_KIND_PROFILES[self.cop_kind]
            shirt = profile["shirt"]
            self.frames = make_ped_frames(shirt, is_cop=True, cop_kind=self.cop_kind)
            self.swim_frames = make_swim_frames(shirt, is_cop=True, cop_kind=self.cop_kind)
        else:
            shirt = (random.randint(80,220), random.randint(60,200), random.randint(60,200))
            self.frames = make_ped_frames(shirt)
            self.swim_frames = make_swim_frames(shirt)
        self.sprite = self.frames[0]
        self.anim_t = 0.0
        self.frame_idx = 0
        self.last_x, self.last_y = x, y
        self.hp = COP_KIND_PROFILES[self.cop_kind]["hp"] if is_cop else 60
        self.cop_speed = COP_KIND_PROFILES[self.cop_kind]["speed"] if is_cop else 0
        self.angle = random.uniform(0, 360)
        self.state = 'wander'
        self.tick = random.uniform(0, 3)
        self.spd = random.uniform(40, 70)
        self.shoot_tick = random.uniform(0.5, 2)
        self.route = []
        self.route_goal = None
        self.route_replan = 0.0
        self.current_node = None

    def animate(self, dt):
        moved = math.hypot(self.x - self.last_x, self.y - self.last_y)
        self.last_x, self.last_y = self.x, self.y
        swim = rect_in_park_pond(self.rect())
        if moved > 0.5:
            speed = 5.0 if swim else (8 + min(20, moved * 60))
            self.anim_t += dt * speed
            self.frame_idx = int(self.anim_t) % 4
        else:
            self.anim_t += dt * (1.8 if swim else 0.0)
            self.frame_idx = int(self.anim_t) % 4 if swim else 0
        self.sprite = (self.swim_frames if swim else self.frames)[self.frame_idx]

    def rect(self):
        return pygame.Rect(self.x-10, self.y-10, 20, 20)

    def try_move(self, nx, ny):
        obstacles = current().AI_OBSTACLES
        rx = pygame.Rect(nx-10, self.y-10, 20, 20)
        if not any(rx.colliderect(b[0]) for b in obstacles):
            self.x = nx
        ry = pygame.Rect(self.x-10, ny-10, 20, 20)
        if not any(ry.colliderect(b[0]) for b in obstacles):
            self.y = ny

    def try_follow_route(self, nx, ny, allow_park=False):
        if pedestrian_step_clear(nx, ny, allow_park=allow_park):
            self.x = nx
            self.y = ny
            return True
        return False

    def plan_route(self, prefer_park=False, flee_from=None):
        start_idx = nearest_pedestrian_node(self.x, self.y)
        self.current_node = start_idx
        if start_idx is None:
            self.route = []
            self.route_goal = None
            return
        if flee_from is not None:
            best_goal = None
            best_score = -1
            nodes = current().pedestrian_nodes
            for _ in range(8):
                candidate = random_pedestrian_destination(prefer_park=False, avoid_idx=start_idx)
                if candidate is None:
                    continue
                cx, cy = nodes[candidate]
                score = (cx - flee_from.x) ** 2 + (cy - flee_from.y) ** 2
                if score > best_score:
                    best_score = score
                    best_goal = candidate
            self.route_goal = best_goal
        else:
            self.route_goal = random_pedestrian_destination(prefer_park=prefer_park, avoid_idx=start_idx)
        path = pedestrian_path(start_idx, self.route_goal)
        self.route = path[1:] if len(path) > 1 else []

    def update(self, dt, target):
        if self.is_cop:
            dx, dy = target.x - self.x, target.y - self.y
            d = math.hypot(dx, dy) or 1
            self.angle = math.degrees(math.atan2(dx, -dy))
            if d > 60:
                self.try_move(self.x + dx/d * self.cop_speed * dt,
                              self.y + dy/d * self.cop_speed * dt)
            self.shoot_tick -= dt
            return d < 350 and self.shoot_tick <= 0

        self.route_replan = max(0.0, self.route_replan - dt)
        if self.state == 'flee':
            dx, dy = self.x - target.x, self.y - target.y
            d = math.hypot(dx, dy) or 1
            if d > 600:
                self.state = 'wander'
                self.route = []
                self.route_goal = None
            elif self.route_replan <= 0:
                self.route_replan = 0.55
                self.plan_route(flee_from=target)
        else:
            if self.route_replan <= 0:
                self.route_replan = random.uniform(2.5, 5.5)
                self.plan_route(prefer_park=random.random() < 0.22)

        if self.route:
            node_idx = self.route[0]
            tx, ty = current().pedestrian_nodes[node_idx]
            dx, dy = tx - self.x, ty - self.y
            d = math.hypot(dx, dy) or 1
            spd = self.spd * (1.45 if self.state == 'flee' else 0.72)
            step = spd * dt
            self.angle = math.degrees(math.atan2(dx, -dy))
            if d <= step + 2:
                self.x, self.y = tx, ty
                self.current_node = node_idx
                self.route.pop(0)
            else:
                nx = self.x + dx / d * step
                ny = self.y + dy / d * step
                if not self.try_follow_route(nx, ny, allow_park=True):
                    if d <= 18 and pedestrian_step_clear(tx, ty, allow_park=True):
                        self.x, self.y = tx, ty
                        self.current_node = node_idx
                        self.route.pop(0)
                    else:
                        self.route = []
                        self.route_goal = None
                        self.route_replan = 0.25
        return False

    def draw(self, surf, cam):
        rot = pygame.transform.rotate(self.sprite, -self.angle)
        r = rot.get_rect(center=(self.x - cam[0], self.y - cam[1]))
        surf.blit(rot, r)
