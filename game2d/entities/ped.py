"""Fußgänger und Cops zu Fuß."""
import math
import random
import pygame

from game2d.config import COP_BLUE
from game2d.render.sprites import make_ped_frames
from game2d.state import current


class Ped:
    def __init__(self, x, y, is_cop=False):
        self.x, self.y = x, y
        self.is_cop = is_cop
        if is_cop:
            self.frames = make_ped_frames(COP_BLUE, is_cop=True)
        else:
            shirt = (random.randint(80,220), random.randint(60,200), random.randint(60,200))
            self.frames = make_ped_frames(shirt)
        self.sprite = self.frames[0]
        self.anim_t = 0.0
        self.frame_idx = 0
        self.last_x, self.last_y = x, y
        self.hp = 200 if is_cop else 60
        self.angle = random.uniform(0, 360)
        self.state = 'wander'
        self.tick = random.uniform(0, 3)
        self.spd = random.uniform(40, 70)
        self.shoot_tick = random.uniform(0.5, 2)

    def animate(self, dt):
        moved = math.hypot(self.x - self.last_x, self.y - self.last_y)
        self.last_x, self.last_y = self.x, self.y
        if moved > 0.5:
            self.anim_t += dt * (8 + min(20, moved * 60))
            self.frame_idx = int(self.anim_t) % 4
        else:
            self.frame_idx = 0
        self.sprite = self.frames[self.frame_idx]

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

    def update(self, dt, target):
        if self.is_cop:
            dx, dy = target.x - self.x, target.y - self.y
            d = math.hypot(dx, dy) or 1
            self.angle = math.degrees(math.atan2(dx, -dy))
            if d > 60:
                self.try_move(self.x + dx/d * 110 * dt,
                              self.y + dy/d * 110 * dt)
            self.shoot_tick -= dt
            return d < 350 and self.shoot_tick <= 0
        if self.state == 'flee':
            dx, dy = self.x - target.x, self.y - target.y
            d = math.hypot(dx, dy) or 1
            self.try_move(self.x + dx/d * self.spd * 1.6 * dt,
                          self.y + dy/d * self.spd * 1.6 * dt)
            self.angle = math.degrees(math.atan2(dx/d, -dy/d))
            if d > 600: self.state = 'wander'
        else:
            self.tick -= dt
            if self.tick <= 0:
                self.angle = random.uniform(0, 360)
                self.tick = random.uniform(1.5, 4)
            rad = math.radians(self.angle)
            self.try_move(self.x + math.sin(rad) * self.spd * 0.5 * dt,
                          self.y - math.cos(rad) * self.spd * 0.5 * dt)
        return False

    def draw(self, surf, cam):
        rot = pygame.transform.rotate(self.sprite, -self.angle)
        r = rot.get_rect(center=(self.x - cam[0], self.y - cam[1]))
        surf.blit(rot, r)
