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
    in_city,
)


CAT_COLORS = [
    (210, 160, 100),   # Tabby-Orange
    ( 65,  65,  65),   # Dunkelgrau
    (230, 225, 215),   # Crème-weiß
    (150, 110,  70),   # Braun-Tabby
    ( 90,  90, 115),   # Blaugrau
    (190,  80,  28),   # Ingwer
]


def _shade(col, delta):
    return tuple(max(0, min(255, c + delta)) for c in col)


def make_cat_sprites(color=(150, 110, 70)):
    """Vier Frames: [laufen_a, laufen_b, sitzen, pinkeln]."""
    dark    = _shade(color, -50)
    darker  = _shade(color, -85)
    light   = _shade(color,  60)
    lighter = _shade(color,  95)
    stripe  = _shade(color, -70)
    pink    = (255, 150, 160)
    pink_d  = (200,  95, 110)
    amber   = (255, 178,   0)
    black   = (  0,   0,   0)
    white   = (255, 255, 255)
    wh_col  = (240, 240, 240) if sum(color) < 430 else (50, 50, 60)

    frames = []

    # ── Lauf-Frames (0 = Schritt-A, 1 = Schritt-B) ──────────────────────────
    for leg_phase in (0, 1):
        W, H = 52, 36
        s = pygame.Surface((W, H), pygame.SRCALPHA)
        la = 3 if leg_phase else 0

        # Schwanz (zuerst, hinter Körper) — S-Kurve mit fluffiger Spitze
        tail = [(44, 26), (48, 19), (49, 12), (46, 7), (43, 6)]
        pygame.draw.lines(s, darker, False, tail, 6)
        pygame.draw.lines(s, dark,   False, tail, 4)
        pygame.draw.lines(s, color,  False, tail, 2)
        pygame.draw.circle(s, dark,  (43, 6), 4)
        pygame.draw.circle(s, light, (42, 5), 2)
        pygame.draw.circle(s, white, (41, 4), 1)

        # Körper — mehrschichtig für Tiefenwirkung
        pygame.draw.ellipse(s, darker, (14, 17, 32, 17))   # Schatten
        pygame.draw.ellipse(s, color,  (14, 15, 32, 17))   # Hauptkörper
        pygame.draw.ellipse(s, light,  (19, 19, 20, 10))   # Bauch
        pygame.draw.ellipse(s, lighter,(22, 20, 12,  7))   # Bauch-Highlight
        for ox in range(17, 44, 5):
            pygame.draw.line(s, stripe, (ox, 15), (ox + 2, 26), 1)

        # Hintere Beine (dunkler, dahinter)
        pygame.draw.line(s, darker, (37, 29), (35 - la, 35), 4)
        pygame.draw.line(s, darker, (41, 29), (43 + la, 35), 4)
        pygame.draw.ellipse(s, darker, (27 - la, 33, 11, 4))
        pygame.draw.ellipse(s, dark,   (28 - la, 32,  8, 3))
        pygame.draw.ellipse(s, darker, (39 + la, 33, 11, 4))
        pygame.draw.ellipse(s, dark,   (40 + la, 32,  8, 3))

        # Vordere Beine (vorne, Körperfarbe)
        pygame.draw.line(s, color, (21, 29), (19 + la, 35), 4)
        pygame.draw.line(s, color, (25, 29), (27 - la, 35), 4)
        pygame.draw.ellipse(s, dark,  (11 + la, 33, 11, 4))
        pygame.draw.ellipse(s, color, (12 + la, 32,  8, 3))
        pygame.draw.ellipse(s, dark,  (21 - la, 33, 11, 4))
        pygame.draw.ellipse(s, color, (22 - la, 32,  8, 3))

        # Hals
        pygame.draw.polygon(s, color, [(9, 22), (9, 29), (19, 31), (20, 26)])
        pygame.draw.polygon(s, light, [(10, 23), (10, 27), (18, 29), (18, 26)])

        # Kopf
        hx, hy, hr = 10, 13, 11
        pygame.draw.circle(s, darker, (hx,     hy + 1), hr)
        pygame.draw.circle(s, color,  (hx,     hy),     hr)
        pygame.draw.circle(s, light,  (hx - 2, hy - 1), hr - 3)
        pygame.draw.circle(s, lighter,(hx - 3, hy - 2), hr - 6)

        # Ohren (Kontur + Farbe + Innenohr)
        pygame.draw.polygon(s, dark,  [( 2, 6), ( 4, -2), (10,  5)])
        pygame.draw.polygon(s, color, [( 3, 6), ( 4, -1), ( 9,  5)])
        pygame.draw.polygon(s, pink,  [( 3, 5), ( 4,  0), ( 8,  5)])
        pygame.draw.polygon(s, dark,  [( 9, 4), (12, -2), (17,  4)])
        pygame.draw.polygon(s, color, [(10, 4), (12, -1), (16,  4)])
        pygame.draw.polygon(s, pink,  [(10, 4), (12,  0), (15,  4)])

        # Auge — große Iris (amber), vertikaler Schlitz-Pupille, zwei Glanzpunkte
        pygame.draw.circle(s, amber, (15, 12), 5)
        pygame.draw.ellipse(s, black, (14,  9, 3, 7))
        pygame.draw.circle(s, white, (17, 10), 1)
        pygame.draw.circle(s, white, (14, 14), 1)
        pygame.draw.arc(s, darker, (10, 7, 10, 9), 0, math.pi, 1)

        # Nase (herzförmig) + Maul
        pygame.draw.polygon(s, pink,  [(4, 16), (7, 18), (9, 16)])
        pygame.draw.polygon(s, pink_d,[(5, 17), (7, 18), (8, 17)])
        pygame.draw.line(s, darker, (7, 18), (5, 21), 1)
        pygame.draw.line(s, darker, (7, 18), (9, 21), 1)

        # Schnurrhaare — 3 Stück, varierende Länge
        for i, dy in enumerate((-2, 0, 2)):
            length = 12 - abs(dy) * 2
            pygame.draw.line(s, wh_col, (4, 18 + dy), (4 - length, 17 + dy // 2), 1)

        frames.append(s)

    # ── Sitzen-Frame (2) ─────────────────────────────────────────────────────
    W, H = 52, 36
    s = pygame.Surface((W, H), pygame.SRCALPHA)

    # Schwanz eingerollt vor dem Körper
    tail_s = [(18, 29), (12, 31), (9, 35), (17, 36), (26, 35), (32, 31)]
    pygame.draw.lines(s, darker, False, tail_s, 5)
    pygame.draw.lines(s, dark,   False, tail_s, 3)
    pygame.draw.lines(s, color,  False, tail_s, 1)

    # Flanke/Hinterteil (groß, rund)
    pygame.draw.ellipse(s, darker, (22, 14, 28, 22))
    pygame.draw.ellipse(s, color,  (22, 12, 28, 22))
    pygame.draw.ellipse(s, light,  (26, 16, 18, 14))
    for ox in (25, 30, 35, 40):
        pygame.draw.line(s, stripe, (ox, 12), (ox + 2, 24), 1)

    # Brust/Vorderkörper
    pygame.draw.ellipse(s, darker, ( 9, 18, 20, 16))
    pygame.draw.ellipse(s, color,  ( 9, 16, 20, 16))
    pygame.draw.ellipse(s, light,  (11, 19, 14, 11))
    pygame.draw.ellipse(s, lighter,(13, 21,  9,  7))

    # Eingeknickte Vorderpfoten mit Zehen
    pygame.draw.ellipse(s, darker, ( 9, 30, 13, 5))
    pygame.draw.ellipse(s, color,  (10, 29, 10, 4))
    pygame.draw.ellipse(s, darker, (20, 30, 13, 5))
    pygame.draw.ellipse(s, color,  (21, 29, 10, 4))
    for tx in (11, 13, 15):
        pygame.draw.line(s, dark, (tx, 32), (tx, 34), 1)
    for tx in (22, 24, 26):
        pygame.draw.line(s, dark, (tx, 32), (tx, 34), 1)

    # Hals
    pygame.draw.polygon(s, color, [(8, 22), (8, 28), (17, 29), (18, 24)])
    pygame.draw.polygon(s, light, [(9, 23), (9, 27), (16, 28), (16, 24)])

    # Kopf (aufrecht, aufmerksam)
    hx, hy, hr = 9, 12, 11
    pygame.draw.circle(s, darker, (hx,     hy + 1), hr)
    pygame.draw.circle(s, color,  (hx,     hy),     hr)
    pygame.draw.circle(s, light,  (hx - 2, hy - 1), hr - 3)
    pygame.draw.circle(s, lighter,(hx - 3, hy - 2), hr - 6)

    # Ohren besonders steil (wach/aufmerksam)
    pygame.draw.polygon(s, dark,  [(1, 5), ( 3, -3), ( 9,  4)])
    pygame.draw.polygon(s, color, [(2, 5), ( 3, -2), ( 8,  4)])
    pygame.draw.polygon(s, pink,  [(2, 5), ( 3, -1), ( 7,  4)])
    pygame.draw.polygon(s, dark,  [(9, 4), (12, -3), (17,  4)])
    pygame.draw.polygon(s, color, [(10, 4), (12, -2), (16, 4)])
    pygame.draw.polygon(s, pink,  [(10, 4), (12, -1), (15, 4)])

    # Auge weit geöffnet (neugierig)
    pygame.draw.circle(s, amber, (15, 12), 5)
    pygame.draw.ellipse(s, black, (14,  9, 3, 7))
    pygame.draw.circle(s, white, (17, 10), 1)
    pygame.draw.circle(s, white, (14, 14), 1)
    pygame.draw.arc(s, darker, (10, 7, 10, 9), 0, math.pi, 1)

    # Nase + Maul
    pygame.draw.polygon(s, pink,  [(3, 16), (6, 18), (8, 16)])
    pygame.draw.polygon(s, pink_d,[(4, 17), (6, 18), (7, 17)])
    pygame.draw.line(s, darker, (6, 18), (4, 21), 1)
    pygame.draw.line(s, darker, (6, 18), (8, 21), 1)

    # Schnurrhaare
    for i, dy in enumerate((-2, 0, 2)):
        length = 11 - abs(dy) * 2
        pygame.draw.line(s, wh_col, (3, 18 + dy), (3 - length, 17 + dy // 2), 1)

    frames.append(s)

    # ── Pinkeln-Frame (3) ────────────────────────────────────────────────────
    W, H = 52, 38
    s = pygame.Surface((W, H), pygame.SRCALPHA)

    # Schwanz steil nach oben
    tail_p = [(30, 22), (32, 14), (30, 7), (26, 4)]
    pygame.draw.lines(s, darker, False, tail_p, 6)
    pygame.draw.lines(s, dark,   False, tail_p, 4)
    pygame.draw.lines(s, color,  False, tail_p, 2)
    pygame.draw.circle(s, dark,  (26, 4), 4)
    pygame.draw.circle(s, light, (25, 3), 2)

    # Körper geduckt
    pygame.draw.ellipse(s, darker, (10, 19, 30, 17))
    pygame.draw.ellipse(s, color,  (10, 17, 30, 17))
    pygame.draw.ellipse(s, light,  (14, 21, 20, 11))
    pygame.draw.ellipse(s, lighter,(17, 22, 12,  7))
    for ox in range(13, 38, 5):
        pygame.draw.line(s, stripe, (ox, 17), (ox + 2, 28), 1)

    # Hintere Beine (geduckt)
    pygame.draw.line(s, darker, (32, 30), (30, 37), 4)
    pygame.draw.line(s, darker, (36, 30), (38, 37), 4)
    pygame.draw.ellipse(s, darker, (23, 35, 11, 4))
    pygame.draw.ellipse(s, dark,   (24, 34,  8, 3))
    pygame.draw.ellipse(s, darker, (34, 35, 11, 4))
    pygame.draw.ellipse(s, dark,   (35, 34,  8, 3))

    # Vordere Beine (geduckt)
    pygame.draw.line(s, color, (18, 30), (16, 37), 4)
    pygame.draw.line(s, color, (22, 30), (24, 37), 4)
    pygame.draw.ellipse(s, dark,  (10, 35, 11, 4))
    pygame.draw.ellipse(s, color, (11, 34,  8, 3))
    pygame.draw.ellipse(s, dark,  (20, 35, 11, 4))
    pygame.draw.ellipse(s, color, (21, 34,  8, 3))

    # Hals + Kopf (leicht gesenkt, konzentriert)
    pygame.draw.rect(s, color, (7, 22, 10, 8), border_radius=3)
    pygame.draw.rect(s, light, (8, 23,  7, 6), border_radius=2)
    hx, hy, hr = 9, 14, 10
    pygame.draw.circle(s, darker, (hx,     hy + 1), hr)
    pygame.draw.circle(s, color,  (hx,     hy),     hr)
    pygame.draw.circle(s, light,  (hx - 2, hy - 1), hr - 3)

    # Ohren
    pygame.draw.polygon(s, dark,  [(2,  7), ( 3,  0), ( 9,  6)])
    pygame.draw.polygon(s, color, [(3,  7), ( 3,  1), ( 8,  6)])
    pygame.draw.polygon(s, pink,  [(3,  6), ( 3,  1), ( 7,  6)])
    pygame.draw.polygon(s, dark,  [(9,  5), (12,  0), (16,  5)])
    pygame.draw.polygon(s, color, [(10, 5), (12,  1), (15,  5)])
    pygame.draw.polygon(s, pink,  [(10, 5), (12,  1), (14,  5)])

    # Auge halb geschlossen (konzentriert)
    pygame.draw.circle(s, amber,  (14, 13), 4)
    pygame.draw.ellipse(s, black, (13, 10,  2,  5))
    pygame.draw.ellipse(s, darker,(10,  9,  8,  5))   # schweres Augenlid
    pygame.draw.circle(s, white,  (16, 12), 1)

    # Nase + Maul
    pygame.draw.polygon(s, pink,  [(4, 17), (7, 19), (9, 17)])
    pygame.draw.polygon(s, pink_d,[(5, 18), (7, 19), (8, 18)])
    pygame.draw.line(s, darker, (7, 19), (5, 22), 1)
    pygame.draw.line(s, darker, (7, 19), (9, 22), 1)

    # Schnurrhaare
    for i, dy in enumerate((-2, 0, 2)):
        length = 11 - abs(dy) * 2
        pygame.draw.line(s, wh_col, (4, 19 + dy), (4 - length, 18 + dy // 2), 1)

    # Pfütze (halbtransparent, zwei Schichten)
    pygame.draw.ellipse(s, (235, 215, 60, 130), (22, 34, 14, 5))
    pygame.draw.ellipse(s, (245, 228, 80, 180), (24, 35, 10, 3))

    frames.append(s)

    return frames


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

        self.spd = random.uniform(20, 40)
        self.target_x = None
        self.target_y = None
        self.route = []
        self.route_replan = random.uniform(2.0, 6.0)
        self.current_node = None

        self.pee_timer = 0.0
        self.pee_particles = []

        self.meow_timer = random.uniform(5.0, 15.0)

        self.last_x, self.last_y = x, y

    def rect(self):
        return pygame.Rect(self.x - 26, self.y - 18, 52, 36)

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
                    # Wasser-Schutz: pedestrian_step_clear prüft in_city intern
                    if not self.try_follow_route(nx, ny):
                        self.route = []
                        self.route_replan = 0.5

        elif self.state == 'peeing':
            self.pee_timer += dt
            if self.pee_timer >= 2.0:
                self.state = 'lying'
                self.state_timer = random.uniform(3.0, 6.0)
                self.pee_timer = 0.0
                for _ in range(3):
                    self.pee_particles.append({
                        'x': self.x + random.uniform(-5, 5),
                        'y': self.y + 18,
                        'ttl': random.uniform(5.0, 10.0),
                    })

        for p in list(self.pee_particles):
            p['ttl'] -= dt
            if p['ttl'] <= 0:
                self.pee_particles.remove(p)

        self.meow_timer -= dt
        if self.meow_timer <= 0:
            audio.play('cat_meow', pos=(self.x, self.y), volume=0.5)
            self.meow_timer = random.uniform(5.0, 15.0)

        # Spieler ausweichen (pedestrian_step_clear verhindert Wasser)
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
            self.frame_idx = 2
        elif self.state == 'walking':
            self.anim_t += dt * 8
            self.frame_idx = int(self.anim_t) % 2
        elif self.state == 'peeing':
            self.frame_idx = 3

        self.sprite = self.frames[self.frame_idx]

    def draw(self, surf, cam):
        rot = pygame.transform.rotate(self.sprite, -self.angle)
        r = rot.get_rect(center=(self.x - cam[0], self.y - cam[1]))
        surf.blit(rot, r)

        for p in self.pee_particles:
            alpha = int(255 * min(1.0, p['ttl'] / 10.0))
            if alpha > 0:
                ps = pygame.Surface((4, 4), pygame.SRCALPHA)
                ps.fill((255, 255, 150, alpha))
                surf.blit(ps, (int(p['x'] - cam[0] - 2), int(p['y'] - cam[1] - 2)))

    def take_damage(self, amount):
        self.hp -= amount
        return self.hp <= 0
