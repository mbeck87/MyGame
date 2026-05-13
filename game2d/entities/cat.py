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


CAT_COLORS = [(230, 225, 215)]   # immer weiß (Pixel-Art-Stil)


def _shade(col, delta):
    return tuple(max(0, min(255, c + delta)) for c in col)


def make_cat_sprites(color=None):
    """Pixel-Art-Katze (weiß, 8-Bit-Stil). Vier Frames: [walk_a, walk_b, sitzen, pinkeln]."""
    # ── Pixel-Art-Farbpalette ────────────────────────────────────────────────
    K  = (18,  12,  10)      # Kontur (fast Schwarz)
    W  = (248, 248, 248)     # Weiß
    B  = (192, 168, 142)     # Beige (Ohren, Rücken, Schwanz)
    Bd = (148, 122,  96)     # Dunkles Beige
    Pi = (255, 155, 165)     # Rosa Innenohr
    Ey = ( 72, 148, 228)     # Blaues Auge
    Pu = ( 20,  20,  80)     # Pupille
    No = (224,  85, 105)     # Nase
    Wh = (255, 255, 255)     # Schnurrhaare

    frames = []

    # Hilfsfunktion: zeichnet einen logischen Pixel als PX×PX Rect
    PX = 3

    def px(s, col, gx, gy, gw=1, gh=1):
        pygame.draw.rect(s, col, (gx * PX, gy * PX, gw * PX, gh * PX))

    # ── Pixel-Kopf-Helper (gemeinsam für alle Frames) ────────────────────────
    def draw_head(s, ox, oy):
        """Zeichnet Pixel-Art-Kopf mit Ursprung (ox, oy) in logischen Pixeln."""
        # Ohren
        px(s, K,  ox+1, oy,   1, 2); px(s, B,  ox+2, oy,   1, 1)
        px(s, Pi, ox+2, oy+1, 1, 1); px(s, K,  ox+3, oy,   1, 1)
        px(s, K,  ox+5, oy,   1, 1); px(s, B,  ox+5, oy+1, 1, 1)
        px(s, Pi, ox+6, oy+1, 1, 1); px(s, K,  ox+6, oy,   1, 1)
        px(s, K,  ox+7, oy,   1, 2)
        # Kopfkontur oben
        px(s, K,  ox,   oy+2, 1, 5); px(s, K,  ox+8, oy+2, 1, 5)
        px(s, K,  ox+1, oy+7, 7, 1); px(s, K,  ox+1, oy+1, 7, 1)
        # Kopffüllung weiß
        px(s, W,  ox+1, oy+2, 7, 5)
        # Wangen (leicht rosa)
        px(s, Pi, ox+1, oy+5, 1, 1); px(s, Pi, ox+7, oy+5, 1, 1)
        # Augen (blau 2×2, Pupille 1×1 rechts oben, Glanzpunkt)
        px(s, Ey, ox+2, oy+3, 2, 2); px(s, Pu, ox+3, oy+3, 1, 1)
        px(s, W,  ox+2, oy+3, 1, 1)   # Glanzpunkt
        px(s, Ey, ox+5, oy+3, 2, 2); px(s, Pu, ox+6, oy+3, 1, 1)
        px(s, W,  ox+5, oy+3, 1, 1)   # Glanzpunkt
        # Nase
        px(s, No, ox+3, oy+5, 2, 1)
        # Maul (kleines W)
        px(s, K,  ox+3, oy+6, 1, 1); px(s, K,  ox+5, oy+6, 1, 1)

    def draw_whiskers(s, ox, oy):
        """Schnurrhaare (logische Pixel, 1px Linie)."""
        # links
        for i, (wx, wy) in enumerate([(-3, oy+5+0*PX), (-2, oy+5+1*PX)]):
            pygame.draw.line(s, Wh,
                             (ox*PX, (oy+5)*PX + i*PX),
                             ((ox-3)*PX, (oy+5)*PX + i*PX - i), 1)
        # rechts
        pygame.draw.line(s, Wh,
                         ((ox+8)*PX, (oy+5)*PX),
                         ((ox+11)*PX, (oy+5)*PX - 1), 1)
        pygame.draw.line(s, Wh,
                         ((ox+8)*PX, (oy+6)*PX),
                         ((ox+11)*PX, (oy+6)*PX + 1), 1)

    # ── WALK-Frames A & B (Seitenansicht, 18×12 Logik-Pixel = 54×36 px) ─────
    for leg_phase in (0, 1):
        s = pygame.Surface((18 * PX, 12 * PX), pygame.SRCALPHA)
        lp = leg_phase  # 0 oder 1

        # Schwanz (rechts, S-Form nach oben)
        for ty in range(5):
            tx = 17 - (ty % 2)
            px(s, K,  tx,   ty,  1, 1)
            px(s, B,  tx-1, ty,  1, 1)
        px(s, Bd, 15, 0, 1, 1)  # Schwanzspitze

        # Körper-Rücken (beige Streifen oben)
        px(s, K,  4, 2, 10, 1)
        px(s, B,  5, 3, 9,  1)
        px(s, K,  4, 3, 1,  5); px(s, K, 14, 3, 1, 5)
        px(s, W,  5, 4, 9,  4)  # weißer Rumpf
        px(s, B,  5, 7, 9,  1)  # Bauchstreifen
        px(s, K,  4, 8, 10, 1)  # untere Kontur

        # Hintere Beine (Pixel-Art, alternierend)
        for li, lx in enumerate((11, 13)):
            off = lp if li == 0 else 1 - lp
            px(s, Bd, lx, 9,     2, 1)   # Oberschenkel
            px(s, B,  lx, 9+off, 2, 1)   # Unterschenkel
            px(s, K,  lx-1, 10+off, 4, 1); px(s, W, lx, 10+off, 2, 1)  # Pfote

        # Vordere Beine
        for li, lx in enumerate((5, 7)):
            off = 1 - lp if li == 0 else lp
            px(s, W,  lx, 9,     2, 1)
            px(s, W,  lx, 9+off, 2, 1)
            px(s, K,  lx-1, 10+off, 4, 1); px(s, W, lx, 10+off, 2, 1)  # Pfote

        # Kopf (links, logische Pos (0,0))
        draw_head(s, 0, 0)
        draw_whiskers(s, 0, 0)

        # Hals-Verbindung
        px(s, W, 4, 4, 1, 3)

        frames.append(s)

    # ── SITTING-Frame (Pixel-Art, wie Referenz, 15×18 Logik-Px = 45×54) ─────
    s = pygame.Surface((15 * PX, 18 * PX), pygame.SRCALPHA)

    # Schwanz (rechts am Körper hinunter, dann vor den Pfoten)
    for ty in range(6, 14):
        px(s, K,  14, ty,  1, 1)
        px(s, B,  13, ty,  1, 1)
    for tx in range(6, 14):
        px(s, B,  tx, 14,  1, 1)
        px(s, K,  tx, 15,  1, 1)
    px(s, Bd, 6, 13, 1, 1)  # Ecke

    # Körper (breites Rechteck)
    px(s, K,  3,  7, 10, 1)   # oben
    px(s, B,  4,  8, 9,  1)   # beige Rückenstreifen
    px(s, K,  3,  8, 1,  6); px(s, K, 13, 8, 1, 6)   # Seiten
    px(s, W,  4,  9, 9,  5)   # weißer Körper
    px(s, K,  3, 14, 10, 1)   # unten

    # Vorderpfoten (unten, zwei Paare)
    px(s, K,  4, 15, 3, 1); px(s, W, 5, 15, 2, 1)
    px(s, K,  4, 16, 3, 1); px(s, W, 5, 16, 2, 1)
    px(s, K,  8, 15, 3, 1); px(s, W, 9, 15, 2, 1)
    px(s, K,  8, 16, 3, 1); px(s, W, 9, 16, 2, 1)

    # Kopf (oben, zentriert)
    draw_head(s, 3, 0)
    draw_whiskers(s, 3, 0)

    # Hals
    px(s, W, 6, 7, 3, 1)

    frames.append(s)

    # ── PEE-Frame (Schwanz hoch, geduckt, 16×14 Logik-Px = 48×42) ──────────
    s = pygame.Surface((16 * PX, 14 * PX), pygame.SRCALPHA)

    # Schwanz steil nach oben (rechts)
    for ty in range(7):
        tx = 15 - (ty > 3)
        px(s, K,  tx,   ty, 1, 1)
        px(s, B,  tx-1, ty, 1, 1)
    px(s, Bd, 14, 0, 1, 1)

    # Körper geduckt (niedrig, breit)
    px(s, K,  3, 5, 9, 1)
    px(s, B,  4, 6, 8, 1)
    px(s, K,  3, 6, 1, 4); px(s, K, 12, 6, 1, 4)
    px(s, W,  4, 7, 8, 3)
    px(s, K,  3, 10, 9, 1)

    # Beine geduckt (kurz, nach hinten)
    for lx in (4, 6, 9, 11):
        px(s, W,  lx, 11, 2, 1)
        px(s, K,  lx-1, 12, 4, 1); px(s, W, lx, 12, 2, 1)

    # Kopf
    draw_head(s, 0, 0)
    draw_whiskers(s, 0, 0)
    px(s, W, 3, 5, 1, 2)  # Hals

    # Pfütze
    pygame.draw.ellipse(s, (235, 215, 60, 140), (9*PX, 12*PX, 5*PX, 2*PX))
    pygame.draw.ellipse(s, (245, 230, 80, 200), (10*PX, 12*PX+1, 3*PX, PX))

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
