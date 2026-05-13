"""Katzen-Entities mit typischem Katzenverhalten."""
import math
import random
import pygame

from game2d.state import current
from game2d.systems import audio
from game2d.world.geometry import (
    pedestrian_step_clear,
    random_pedestrian_destination,
    nearest_pedestrian_node,
    pedestrian_path,
    rect_in_park_pond,
)


# Katzenfarben
CAT_COLORS = [
    (200, 150, 100),   # Tabby
    (80, 80, 80),      # Schwarz
    (200, 200, 200),   # Weiss
    (150, 120, 80),    # Braun
    (100, 100, 120),   # Grau
    (220, 180, 140),   # Orange
]


def make_cat_sprites(color=(150, 120, 80)):
    """Erzeugt schöne Katzen-Sprites (2 Frames: idle, walking)."""
    frames = []
    
    # Frame 0: Stehen/Sitzen (idle)
    s = pygame.Surface((36, 28), pygame.SRCALPHA)
    
    # Körper - Ellipse
    body_col = color
    pygame.draw.ellipse(s, body_col, (6, 10, 24, 14))
    
    # Kopf - Kreis
    head_col = color
    pygame.draw.circle(s, head_col, (14, 12), 10)
    
    # Ohren - Dreiecke
    ear_col = color
    pygame.draw.polygon(s, ear_col, [(10, 7), (14, 4), (18, 7)])  # Linkes Ohr
    pygame.draw.polygon(s, ear_col, [(12, 8), (16, 5), (20, 8)])  # Rechtes Ohr
    
    # Innere Ohren (heller)
    inner_ear = _shade(color, 40)
    pygame.draw.polygon(s, inner_ear, [(11, 7), (14, 5), (17, 7)])
    
    # Augen - gelb mit schwarzen Pupillen
    pygame.draw.circle(s, (255, 215, 0), (11, 11), 3)
    pygame.draw.circle(s, (255, 215, 0), (17, 11), 3)
    pygame.draw.circle(s, (0, 0, 0), (11, 11), 1)
    pygame.draw.circle(s, (0, 0, 0), (17, 11), 1)
    
    # Nase - rosa Dreieck
    pygame.draw.polygon(s, (255, 180, 190), [(13, 14), (14, 15), (15, 14)])
    
    # Schnurrhaare
    pygame.draw.line(s, (0, 0, 0), (9, 13), (4, 12), 1)
    pygame.draw.line(s, (0, 0, 0), (9, 14), (4, 14), 1)
    pygame.draw.line(s, (0, 0, 0), (19, 13), (24, 12), 1)
    pygame.draw.line(s, (0, 0, 0), (19, 14), (24, 14), 1)
    
    # Pfoten
    pygame.draw.ellipse(s, body_col, (10, 20, 6, 4))
    pygame.draw.ellipse(s, body_col, (20, 20, 6, 4))
    
    # Schwanz - gebogen
    pygame.draw.ellipse(s, body_col, (26, 12, 10, 6))
    
    # Streifen (für Tabby-Look)
    stripe_col = _shade(color, -30)
    pygame.draw.line(s, stripe_col, (12, 16), (8, 14), 2)
    pygame.draw.line(s, stripe_col, (16, 16), (22, 14), 2)
    pygame.draw.line(s, stripe_col, (20, 16), (28, 18), 2)
    
    frames.append(s)
    
    # Frame 1: Gehen
    s = pygame.Surface((36, 28), pygame.SRCALPHA)
    
    # Körper
    pygame.draw.ellipse(s, body_col, (6, 10, 24, 14))
    
    # Kopf
    pygame.draw.circle(s, head_col, (14, 12), 10)
    
    # Ohren
    pygame.draw.polygon(s, ear_col, [(10, 7), (14, 4), (18, 7)])
    pygame.draw.polygon(s, ear_col, [(12, 8), (16, 5), (20, 8)])
    pygame.draw.polygon(s, inner_ear, [(11, 7), (14, 5), (17, 7)])
    
    # Augen
    pygame.draw.circle(s, (255, 215, 0), (11, 11), 3)
    pygame.draw.circle(s, (255, 215, 0), (17, 11), 3)
    pygame.draw.circle(s, (0, 0, 0), (11, 11), 1)
    pygame.draw.circle(s, (0, 0, 0), (17, 11), 1)
    
    # Nase
    pygame.draw.polygon(s, (255, 180, 190), [(13, 14), (14, 15), (15, 14)])
    
    # Schnurrhaare
    pygame.draw.line(s, (0, 0, 0), (9, 13), (4, 12), 1)
    pygame.draw.line(s, (0, 0, 0), (9, 14), (4, 14), 1)
    pygame.draw.line(s, (0, 0, 0), (19, 13), (24, 12), 1)
    pygame.draw.line(s, (0, 0, 0), (19, 14), (24, 14), 1)
    
    # Pfoten (leicht versetzt für Laufanimation)
    pygame.draw.ellipse(s, body_col, (8, 20, 6, 4))
    pygame.draw.ellipse(s, body_col, (22, 20, 6, 4))
    
    # Schwanz - leicht hoch
    pygame.draw.ellipse(s, body_col, (26, 10, 10, 6))
    
    # Streifen
    pygame.draw.line(s, stripe_col, (12, 16), (8, 14), 2)
    pygame.draw.line(s, stripe_col, (16, 16), (22, 14), 2)
    pygame.draw.line(s, stripe_col, (20, 16), (28, 18), 2)
    
    frames.append(s)
    
    # Frame 2: Pinkeln
    s = pygame.Surface((36, 28), pygame.SRCALPHA)
    
    # Körper
    pygame.draw.ellipse(s, body_col, (6, 10, 24, 14))
    
    # Kopf (leicht nach unten)
    pygame.draw.circle(s, head_col, (14, 13), 10)
    
    # Ohren
    pygame.draw.polygon(s, ear_col, [(10, 8), (14, 5), (18, 8)])
    pygame.draw.polygon(s, ear_col, [(12, 9), (16, 6), (20, 9)])
    pygame.draw.polygon(s, inner_ear, [(11, 8), (14, 6), (17, 8)])
    
    # Augen (halb geschlossen)
    pygame.draw.ellipse(s, (255, 215, 0), (10, 11, 4, 2), 0)
    pygame.draw.ellipse(s, (255, 215, 0), (16, 11, 4, 2), 0)
    
    # Nase
    pygame.draw.polygon(s, (255, 180, 190), [(13, 15), (14, 16), (15, 15)])
    
    # Schnurrhaare
    pygame.draw.line(s, (0, 0, 0), (9, 14), (4, 13), 1)
    pygame.draw.line(s, (0, 0, 0), (9, 15), (4, 15), 1)
    pygame.draw.line(s, (0, 0, 0), (19, 14), (24, 13), 1)
    pygame.draw.line(s, (0, 0, 0), (19, 15), (24, 15), 1)
    
    # Pfoten
    pygame.draw.ellipse(s, body_col, (10, 22, 6, 3))
    pygame.draw.ellipse(s, body_col, (20, 22, 6, 3))
    
    # Schwanz hoch
    pygame.draw.ellipse(s, body_col, (26, 8, 10, 5))
    
    # Streifen
    pygame.draw.line(s, stripe_col, (12, 16), (8, 14), 2)
    pygame.draw.line(s, stripe_col, (16, 16), (22, 14), 2)
    
    # Pinkel-Animation
    pygame.draw.circle(s, (255, 255, 150), (15, 26), 2)
    pygame.draw.circle(s, (255, 255, 150), (17, 26), 2)
    
    frames.append(s)
    
    return frames


def _shade(col, delta):
    return tuple(max(0, min(255, c + delta)) for c in col)


class Cat:
    """Katzen-Entity mit typischem Verhalten."""
    
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.color = random.choice(CAT_COLORS)
        self.frames = make_cat_sprites(self.color)
        self.sprite = self.frames[0]
        
        self.hp = 30
        self.angle = random.uniform(0, 360)
        self.state = random.choice(['lying', 'sitting', 'walking', 'peeing'])
        self.state_timer = random.uniform(2.0, 8.0)
        self.anim_t = 0.0
        self.frame_idx = 0
        
        # Bewegung
        self.spd = random.uniform(20, 40)
        self.target_x = None
        self.target_y = None
        self.route = []
        self.route_replan = random.uniform(2.0, 6.0)
        self.current_node = None
        
        # Pee-State
        self.pee_timer = 0.0
        self.pee_particles = []
        
        # Meow
        self.meow_timer = random.uniform(5.0, 15.0)
        
        self.last_x, self.last_y = x, y
    
    def rect(self):
        return pygame.Rect(self.x - 18, self.y - 14, 36, 28)
    
    def plan_route(self):
        start_idx = nearest_pedestrian_node(self.x, self.y)
        self.current_node = start_idx
        if start_idx is None:
            self.route = []
            return
        self.route_replan = random.uniform(2.0, 8.0)
        goal_idx = random_pedestrian_destination(avoid_idx=start_idx)
        if goal_idx is None:
            self.route = []
            return
        path = pedestrian_path(start_idx, goal_idx)
        self.route = path[1:] if len(path) > 1 else []
    
    def try_follow_route(self, nx, ny):
        if pedestrian_step_clear(nx, ny, allow_park=True):
            self.x = nx
            self.y = ny
            return True
        return False
    
    def update(self, dt, player):
        # State Machine
        self.state_timer -= dt
        
        if self.state == 'lying':
            if self.state_timer <= 0:
                self.state = random.choice(['sitting', 'walking'])
                self.state_timer = random.uniform(2.0, 6.0)
        
        elif self.state == 'sitting':
            if self.state_timer <= 0:
                self.state = random.choice(['lying', 'walking', 'peeing'])
                self.state_timer = random.uniform(2.0, 8.0)
        
        elif self.state == 'walking':
            if self.state_timer <= 0:
                self.state = random.choice(['lying', 'sitting'])
                self.state_timer = random.uniform(3.0, 10.0)
            
            self.route_replan -= dt
            if self.route_replan <= 0:
                self.route_replan = random.uniform(2.0, 6.0)
                self.plan_route()
            
            if self.route:
                node_idx = self.route[0]
                tx, ty = current().pedestrian_nodes[node_idx]
                dx, dy = tx - self.x, ty - self.y
                d = math.hypot(dx, dy) or 1
                spd = self.spd * 0.6
                step = spd * dt
                self.angle = math.degrees(math.atan2(dx, -dy))
                if d <= step + 2:
                    self.x, self.y = tx, ty
                    self.current_node = node_idx
                    self.route.pop(0)
                    if self.route:
                        tx, ty = current().pedestrian_nodes[self.route[0]]
                        self.target_x, self.target_y = tx, ty
                else:
                    nx = self.x + dx / d * step
                    ny = self.y + dy / d * step
                    if not self.try_follow_route(nx, ny):
                        self.route = []
                        self.route_replan = 0.5
        
        elif self.state == 'peeing':
            self.pee_timer += dt
            if self.pee_timer >= 2.0:
                self.state = 'lying'
                self.state_timer = random.uniform(3.0, 6.0)
                self.pee_timer = 0.0
                
                # Pinkel-Partikel hinterlassen
                for _ in range(3):
                    self.pee_particles.append({
                        'x': self.x + random.uniform(-5, 5),
                        'y': self.y + 18,
                        'ttl': random.uniform(5.0, 10.0)
                    })
        
        # Pee-Partikel cleanup
        for p in list(self.pee_particles):
            p['ttl'] -= dt
            if p['ttl'] <= 0:
                self.pee_particles.remove(p)
        
        # Meow Sound zufaellig
        self.meow_timer -= dt
        if self.meow_timer <= 0:
            audio.play('cat_meow', pos=(self.x, self.y), volume=0.5)
            self.meow_timer = random.uniform(5.0, 15.0)
        
        # Player избегать
        dx, dy = player.x - self.x, player.y - self.y
        dist = math.hypot(dx, dy)
        if dist < 40 and self.state != 'peeing':
            self.state = 'walking'
            self.state_timer = 1.0
            if self.route_replan <= 0:
                self.route_replan = 1.0
                away_x = self.x - dx / (dist or 1) * 30
                away_y = self.y - dy / (dist or 1) * 30
                if pedestrian_step_clear(away_x, away_y, allow_park=True):
                    self.x = away_x
                    self.y = away_y
    
    def animate(self, dt):
        self.last_x, self.last_y = self.x, self.y
        
        if self.state == 'lying':
            self.frame_idx = 0
        elif self.state == 'sitting':
            self.frame_idx = 0
        elif self.state == 'walking':
            self.anim_t += dt * 8
            self.frame_idx = 0 + int(self.anim_t) % 2
        elif self.state == 'peeing':
            self.frame_idx = 2
        
        self.sprite = self.frames[self.frame_idx]
    
    def draw(self, surf, cam):
        rot = pygame.transform.rotate(self.sprite, -self.angle)
        r = rot.get_rect(center=(self.x - cam[0], self.y - cam[1]))
        surf.blit(rot, r)
        
        # Pee-Partikel zeichnen
        for p in self.pee_particles:
            alpha = int(255 * (p['ttl'] / 10.0))
            if alpha > 0:
                s = pygame.Surface((4, 4), pygame.SRCALPHA)
                s.fill((255, 255, 150, alpha))
                surf.blit(s, (int(p['x'] - cam[0] - 2), int(p['y'] - cam[1] - 2)))
    
    def take_damage(self, amount):
        self.hp -= amount
        return self.hp <= 0
