#!/home/jixo/GTA/venv/bin/python3
import pygame, random, math, sys

pygame.init()
W, H = 1280, 800
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Mini GTA 2D")
clock = pygame.time.Clock()
FONT = pygame.font.SysFont("arial", 20, bold=True)
BIG  = pygame.font.SysFont("arial", 64, bold=True)

# ── Farben ───────────────────────────────────────────────
ASPHALT = (55, 55, 60)
GRASS   = (60, 130, 55)
LINE    = (235, 215, 70)
SIDEW   = (170, 170, 175)
ROOF1   = (140, 90, 70)
ROOF2   = (110, 70, 60)
WALL1   = (210, 195, 165)
WALL2   = (180, 160, 130)
WIN     = (120, 200, 240)
WIN_LIT = (250, 220, 110)
DOOR    = (90, 55, 35)
COP_BLUE= (30, 60, 180)
COP_DARK= (15, 30, 90)
SKIN    = (235, 195, 160)

WORLD_W, WORLD_H = 4000, 4000
BLOCK   = 400      # Stadtblockgröße
ROAD_W  = 90       # Straßenbreite
WATER_W = 220      # Wasserring-Breite am Kartenrand
BEACH_W = 110      # Sandstrand-Breite zwischen Wasser und Stadt
INNER_LO   = WATER_W + BEACH_W
INNER_HI_X = WORLD_W - WATER_W - BEACH_W
INNER_HI_Y = WORLD_H - WATER_W - BEACH_W

WATER_DEEP = (28, 70, 130)
WATER_MID  = (40, 100, 160)
WATER_LITE = (95, 160, 210)
SAND       = (225, 205, 155)

# ── Sprite-Generatoren ───────────────────────────────────
def make_car_sprite(body_col, w=46, h=78):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    # Schatten
    pygame.draw.rect(s, (0,0,0,80), (3, 6, w-2, h-2), border_radius=8)
    # Karosserie
    pygame.draw.rect(s, body_col, (2, 4, w-4, h-8), border_radius=8)
    # Kotflügel-Highlight
    hl = tuple(min(255, c+35) for c in body_col)
    pygame.draw.rect(s, hl, (4, 6, w-8, 4), border_radius=4)
    # Frontscheibe
    pygame.draw.polygon(s, (60,80,100), [(6,16),(w-6,16),(w-10,30),(10,30)])
    pygame.draw.polygon(s, (130,180,220), [(8,17),(w-8,17),(w-12,28),(12,28)])
    # Heckscheibe
    pygame.draw.polygon(s, (60,80,100), [(8,h-22),(w-8,h-22),(w-12,h-12),(12,h-12)])
    pygame.draw.polygon(s, (130,180,220), [(10,h-21),(w-10,21+h-42) if False else (w-10,h-21),(w-13,h-13),(13,h-13)])
    # Dach
    pygame.draw.rect(s, tuple(max(0,c-25) for c in body_col), (10, 30, w-20, h-60))
    # Türlinie
    pygame.draw.line(s, (0,0,0,180), (4, h//2), (w-4, h//2), 1)
    # Scheinwerfer
    pygame.draw.rect(s, (255,250,200), (5, 6, 8, 5), border_radius=2)
    pygame.draw.rect(s, (255,250,200), (w-13, 6, 8, 5), border_radius=2)
    # Rücklichter
    pygame.draw.rect(s, (200,30,30), (5, h-10, 8, 5), border_radius=2)
    pygame.draw.rect(s, (200,30,30), (w-13, h-10, 8, 5), border_radius=2)
    # Räder (seitlich sichtbar)
    pygame.draw.rect(s, (20,20,20), (0, 14, 4, 14), border_radius=2)
    pygame.draw.rect(s, (20,20,20), (w-4, 14, 4, 14), border_radius=2)
    pygame.draw.rect(s, (20,20,20), (0, h-28, 4, 14), border_radius=2)
    pygame.draw.rect(s, (20,20,20), (w-4, h-28, 4, 14), border_radius=2)
    return s

def make_cop_car_sprite():
    s = make_car_sprite((245,245,250))
    w, h = s.get_size()
    # Schwarze Türen
    pygame.draw.rect(s, (20,20,25), (2, h//2 - 14, w-4, 28))
    # POLICE Streifen
    pygame.draw.rect(s, (245,245,250), (2, h//2 - 4, w-4, 8))
    # Sirenen-Lichtbalken
    pygame.draw.rect(s, (40,40,45), (10, 32, w-20, 6))
    pygame.draw.rect(s, (220,40,40), (12, 33, (w-24)//2, 4))
    pygame.draw.rect(s, (40,80,220), (12+(w-24)//2, 33, (w-24)//2, 4))
    return s

def _draw_ped_frame(shirt_col, skin, hair, phase, is_cop=False):
    # GTA2-Style Top-Down: "vorn" = -y (oben). Sprite kann beliebig rotiert werden,
    # ohne dass der Passant je auf dem Kopf steht.
    # phase: -1 / 0 / +1  -> Bein/Arm-Swing
    s = pygame.Surface((20, 24), pygame.SRCALPHA)
    cx, cy = 10, 12
    pants = (40, 40, 80)
    boot  = (20, 20, 20)

    # Schatten unter der Figur
    pygame.draw.ellipse(s, (0, 0, 0, 90), (3, cy + 3, 14, 7))

    # Beine schwingen in Laufrichtung (vor/zurück) — gegenphasig
    leg_l_y = cy + 3 - phase * 3
    leg_r_y = cy + 3 + phase * 3
    pygame.draw.rect(s, pants, (cx - 3, leg_l_y, 2, 5))
    pygame.draw.rect(s, pants, (cx + 1, leg_r_y, 2, 5))
    pygame.draw.rect(s, boot,  (cx - 3, leg_l_y + 5, 2, 2))
    pygame.draw.rect(s, boot,  (cx + 1, leg_r_y + 5, 2, 2))

    # Torso als Oval (Schultern von oben)
    pygame.draw.ellipse(s, shirt_col, (cx - 5, cy - 3, 10, 9))
    hl = tuple(min(255, c + 30) for c in shirt_col)
    pygame.draw.ellipse(s, hl, (cx - 4, cy - 2, 8, 3))

    # Arme schwingen gegenphasig zu den Beinen
    arm_l_y = cy + phase * 2
    arm_r_y = cy - phase * 2
    pygame.draw.rect(s, shirt_col, (cx - 7, arm_l_y, 2, 4))
    pygame.draw.rect(s, shirt_col, (cx + 5, arm_r_y, 2, 4))
    pygame.draw.rect(s, skin,      (cx - 7, arm_l_y + 4, 2, 2))
    pygame.draw.rect(s, skin,      (cx + 5, arm_r_y + 4, 2, 2))

    # Kopf von oben: Haarkranz, davor Gesichts-/Hautstreifen nach vorn
    head_y = cy - 5
    pygame.draw.circle(s, hair, (cx, head_y), 4)
    pygame.draw.circle(s, skin, (cx, head_y - 1), 3)

    if is_cop:
        # Polizeimütze von oben + Schirm nach vorn
        pygame.draw.circle(s, COP_DARK, (cx, head_y), 4)
        pygame.draw.rect(s, COP_DARK, (cx - 4, head_y - 4, 8, 3))
        pygame.draw.rect(s, (230, 200, 60), (cx - 1, head_y - 1, 2, 2))
    return s

def make_ped_frames(shirt_col, skin=SKIN, hair=(60,40,30), is_cop=False):
    # 4-Frame Walk: mitte, rechts vor, mitte, links vor
    return [
        _draw_ped_frame(shirt_col, skin, hair, 0, is_cop),
        _draw_ped_frame(shirt_col, skin, hair, 1, is_cop),
        _draw_ped_frame(shirt_col, skin, hair, 0, is_cop),
        _draw_ped_frame(shirt_col, skin, hair, -1, is_cop),
    ]

def make_ped_sprite(shirt_col, skin=SKIN, hair=(60,40,30)):
    return make_ped_frames(shirt_col, skin, hair)[0]

def make_cop_sprite():
    return make_ped_frames(COP_BLUE, is_cop=True)[0]

def make_building(w_cells, h_cells, seed):
    rng = random.Random(seed)
    cell = 32
    w, h = w_cells * cell, h_cells * cell
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    wall = rng.choice([WALL1, WALL2, (200,180,150), (165,140,115), (190,170,140)])
    roof = rng.choice([ROOF1, ROOF2, (90,90,95), (130,80,70), (70,80,90)])
    # Schatten unten/rechts
    pygame.draw.rect(s, (0,0,0,90), (4, 4, w, h))
    # Wand
    pygame.draw.rect(s, wall, (0, 0, w-4, h-4))
    # Ziegel-Textur
    for y in range(0, h-4, 6):
        off = (y//6) % 2 * 3
        for x in range(-3, w-4, 12):
            pygame.draw.line(s, tuple(max(0,c-15) for c in wall),
                             (x+off, y), (x+off+10, y), 1)
    # Dachkante
    pygame.draw.rect(s, roof, (0, 0, w-4, 6))
    pygame.draw.rect(s, tuple(max(0,c-25) for c in roof), (0, 6, w-4, 2))
    # Fenster-Raster
    pad = 8
    win_w, win_h = 14, 18
    cols = (w - 16) // (win_w + 6)
    rows = (h - 18) // (win_h + 8)
    for r in range(rows):
        for c in range(cols):
            x = pad + c * (win_w + 6)
            y = 12 + r * (win_h + 8)
            lit = rng.random() < 0.35
            col = WIN_LIT if lit else WIN
            pygame.draw.rect(s, (30,30,40), (x-1, y-1, win_w+2, win_h+2))
            pygame.draw.rect(s, col, (x, y, win_w, win_h))
            pygame.draw.line(s, (40,40,50), (x+win_w//2, y), (x+win_w//2, y+win_h), 1)
            pygame.draw.line(s, (40,40,50), (x, y+win_h//2), (x+win_w, y+win_h//2), 1)
    # Tür unten mittig
    dx = w//2 - 10
    dy = h - 28
    pygame.draw.rect(s, DOOR, (dx, dy, 20, 24))
    pygame.draw.rect(s, (50,30,15), (dx, dy, 20, 24), 2)
    pygame.draw.circle(s, (220,200,80), (dx+16, dy+12), 1)
    return s

# ── Welt: Kacheln & Kollisionsboxen ──────────────────────
buildings = []   # (rect, surface)  — nur Häuser (surface immer gesetzt)
roads_h = []     # horizontale Straßen y-Koordinaten
roads_v = []     # vertikale Straßen x-Koordinaten

# Wasser-Ring (tödlich, NICHT-festes Hindernis: Spieler/Autos können reinfahren und sterben)
WATER_RECTS = [
    pygame.Rect(0, 0, WORLD_W, WATER_W),
    pygame.Rect(0, WORLD_H - WATER_W, WORLD_W, WATER_W),
    pygame.Rect(0, 0, WATER_W, WORLD_H),
    pygame.Rect(WORLD_W - WATER_W, 0, WATER_W, WORLD_H),
]
def in_water(x, y):
    return x < WATER_W or x > WORLD_W - WATER_W or y < WATER_W or y > WORLD_H - WATER_W

# Straßen nur innerhalb der Stadt (vor dem Strand)
for y in range(0, WORLD_H, BLOCK):
    if INNER_LO <= y <= INNER_HI_Y:
        roads_h.append(y)
for x in range(0, WORLD_W, BLOCK):
    if INNER_LO <= x <= INNER_HI_X:
        roads_v.append(x)

random.seed(7)
seed = 0
for bx in range(0, WORLD_W, BLOCK):
    for by in range(0, WORLD_H, BLOCK):
        # Block-Inneres bebauen mit 1-4 Häusern
        x0 = max(bx + ROAD_W//2 + 14, INNER_LO + 12)
        y0 = max(by + ROAD_W//2 + 14, INNER_LO + 12)
        x1 = min(bx + BLOCK - ROAD_W//2 - 14, INNER_HI_X - 12)
        y1 = min(by + BLOCK - ROAD_W//2 - 14, INNER_HI_Y - 12)
        if x1 - x0 < 60 or y1 - y0 < 60:
            continue
        cur_y = y0
        while cur_y < y1 - 60:
            cur_x = x0
            row_h = random.randint(3, 5)
            while cur_x < x1 - 60:
                bw_cells = random.randint(3, 6)
                bh = row_h
                bw = bw_cells * 32
                bhp = bh * 32
                if cur_x + bw > x1: break
                if cur_y + bhp > y1: break
                surf = make_building(bw_cells, bh, seed); seed += 1
                rect = pygame.Rect(cur_x, cur_y, bw - 4, bhp - 4)
                buildings.append((rect, surf))
                cur_x += bw + random.randint(4, 14)
            cur_y += row_h * 32 + random.randint(8, 18)

# Hindernisse für KI/NPCs: Häuser + Wasser (NPCs sollen nicht ins Wasser laufen)
AI_OBSTACLES = list(buildings) + [(r, None) for r in WATER_RECTS]

# ── Spieler / Fahrzeug / NPCs ────────────────────────────
class Car:
    def __init__(self, x, y, body, is_cop=False):
        self.x, self.y = x, y
        self.angle = random.choice([0, 90, 180, 270])  # Straßen-aligned
        self.spd = 0
        self.max_spd = 380 if is_cop else 320
        self.is_cop = is_cop
        self.sprite = make_cop_car_sprite() if is_cop else make_car_sprite(body)
        self.w, self.h = self.sprite.get_size()
        self.max_hp = 200
        self.hp = 200
        self.dents = []          # (relx, rely, radius)
        self.burning = False
        self.burn_timer = 0.0
        self.dead = False
        self._smoke_cd = 0.0
        self._fire_cd = 0.0
        # KI
        self.ai_spd = random.uniform(80, 160)
        self.turn_cd = random.uniform(2, 6)

    def take_damage(self, dmg):
        if self.dead or dmg <= 0: return
        self.hp -= dmg
        # Beulen / Schmauchspuren bei Treffern
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
        global in_car, game_over
        self.dead = True
        explosions.append([self.x, self.y, 0.0, 0.55, 150])
        # Druckwelle
        R = 130
        for p in list(peds):
            if math.hypot(p.x-self.x, p.y-self.y) < R:
                p.hp -= 90
                spawn_blood(p.x, p.y, 6)
                if p.hp <= 0:
                    peds.remove(p)
                    corpses.append((make_corpse(p), p.x, p.y, p.angle))
                    spawn_blood(p.x, p.y, 18)
        for c in list(cops):
            if math.hypot(c.x-self.x, c.y-self.y) < R:
                c.hp -= 90
                spawn_blood(c.x, c.y, 6)
                if c.hp <= 0:
                    cops.remove(c)
                    corpses.append((make_corpse(c), c.x, c.y, c.angle))
                    spawn_blood(c.x, c.y, 20)
        for c in cars:
            if c is self or c.dead: continue
            if math.hypot(c.x-self.x, c.y-self.y) < R + 10:
                c.take_damage(110)
        # Spielerschaden / Auswurf
        if math.hypot(player.x-self.x, player.y-self.y) < R:
            player.hp -= 95 if in_car is self else 60
            if player.hp <= 0:
                corpses.append((make_corpse(player), player.x, player.y, player.angle))
                spawn_blood(player.x, player.y, 24)
                game_over = True
        if in_car is self:
            in_car = None
        # Feuer- und Rauchwolke
        for _ in range(45):
            a = random.uniform(0, 6.28); s = random.uniform(80, 320)
            fire_particles.append([self.x, self.y, math.cos(a)*s, math.sin(a)*s,
                                   random.uniform(0.4, 0.9), 0.9, random.randint(4, 8)])
        for _ in range(35):
            a = random.uniform(0, 6.28); s = random.uniform(40, 180)
            smoke_particles.append([self.x, self.y, math.cos(a)*s, math.sin(a)*s - 30,
                                    random.uniform(1.8, 3.5), 3.5, random.randint(6, 11)])
        # Wrack zurücklassen
        wreck_surf = self.sprite.copy()
        scorch = pygame.Surface(wreck_surf.get_size(), pygame.SRCALPHA)
        scorch.fill((20, 20, 20, 200))
        wreck_surf.blit(scorch, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
        wrecks.append((wreck_surf, self.x, self.y, self.angle, list(self.dents)))

    def update_fx(self, dt):
        if self.dead: return
        if self.burning:
            self.burn_timer -= dt
            self._fire_cd -= dt
            if self._fire_cd <= 0:
                self._fire_cd = 0.04
                fire_particles.append([self.x + random.uniform(-12, 12),
                                       self.y + random.uniform(-15, 15),
                                       random.uniform(-25, 25), random.uniform(-70, -25),
                                       random.uniform(0.3, 0.6), 0.6, random.randint(3, 6)])
            self._smoke_cd -= dt
            if self._smoke_cd <= 0:
                self._smoke_cd = 0.08
                smoke_particles.append([self.x, self.y, random.uniform(-15, 15),
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
                smoke_particles.append([self.x, self.y, random.uniform(-10, 10),
                                        random.uniform(-45, -18), random.uniform(1.2, 2.2), 2.2, col_r])

    def rect(self):
        return pygame.Rect(self.x - self.w//2, self.y - self.h//2, self.w, self.h)

    def update(self, dt, accel=0, steer=0):
        if self.dead:
            self.spd = 0
            return
        prev_spd = self.spd
        if accel > 0:
            self.spd = min(self.max_spd, self.spd + 260 * dt)
        elif accel < 0:
            self.spd = max(-self.max_spd*0.5, self.spd - 260 * dt)
        else:
            self.spd *= max(0, 1 - 1.4 * dt)
        if abs(self.spd) > 5:
            self.angle += steer * 110 * dt * (self.spd/self.max_spd)
        rad = math.radians(self.angle)
        dx = math.sin(rad) * self.spd * dt
        dy = -math.cos(rad) * self.spd * dt
        nx, ny = self.x + dx, self.y + dy
        # GTA-Style Wand-Sliding: Velocity wird auf Wand projiziert, Auto richtet sich an Wand aus
        tx = pygame.Rect(nx - self.w//2, self.y - self.h//2, self.w, self.h)
        hit_x = any(tx.colliderect(b[0]) for b in buildings)
        ty = pygame.Rect(self.x - self.w//2, ny - self.h//2, self.w, self.h)
        hit_y = any(ty.colliderect(b[0]) for b in buildings)
        mag = math.hypot(dx, dy) or 1
        if hit_x and hit_y:
            # Frontalcrash (Ecke / direkt): hart bremsen + leichter Rückstoß
            self.spd *= -0.2
            if abs(prev_spd) > 60:
                self.take_damage(abs(prev_spd) * 0.09)
        elif hit_x or hit_y:
            # Senkrechter Anteil zur Wand (perp), parallel-Anteil bleibt erhalten
            if hit_x:
                perp, par = abs(dx) / mag, abs(dy) / mag
                # Auto in Y-Richtung weiterfahren lassen
                self.y = ny
                # Winkel sanft zur Wand-Richtung (vertikal) drehen
                target = 0 if dy < 0 else 180
            else:
                perp, par = abs(dy) / mag, abs(dx) / mag
                self.x = nx
                target = 90 if dx > 0 else 270
            # Reibung: nur leichter Verlust beim Streifen, härter bei steilem Winkel
            # perp=0 (parallel) → spd*0.98, perp=1 (frontal) → spd*0.55
            self.spd *= 1.0 - 0.43 * perp
            # Winkel langsam zur Wandrichtung ziehen (wie an Leitplanke abgleiten)
            diff = ((target - self.angle + 180) % 360) - 180
            self.angle += diff * min(1.0, perp * 6 * dt)
            if abs(prev_spd) > 80 and perp > 0.25:
                self.take_damage(abs(prev_spd) * perp * 0.045)
        else:
            self.x, self.y = nx, ny
        # Weltgrenzen
        self.x = max(40, min(WORLD_W-40, self.x))
        self.y = max(40, min(WORLD_H-40, self.y))

    def ai_update(self, dt):
        # Auf Straße snappen-Test: in der Nähe einer Straße fahren
        rad = math.radians(self.angle)
        nx = self.x + math.sin(rad) * self.ai_spd * dt
        ny = self.y - math.cos(rad) * self.ai_spd * dt
        test = pygame.Rect(nx - self.w//2, ny - self.h//2, self.w, self.h)
        # Hindernisse: Häuser + andere Autos
        blocked = any(test.colliderect(b[0]) for b in AI_OBSTACLES)
        if not blocked:
            for c in cars:
                if c is self: continue
                if test.colliderect(c.rect()):
                    blocked = True; break
        # Auch Spieler/eigenes Auto meiden
        if not blocked and in_car and test.colliderect(in_car.rect()):
            blocked = True
        self.turn_cd -= dt
        if blocked or self.turn_cd <= 0:
            self.angle = random.choice([0, 90, 180, 270])
            self.turn_cd = random.uniform(3, 8)
            return
        self.x, self.y = nx, ny

    def draw(self, surf, cam):
        rot = pygame.transform.rotate(self.sprite, -self.angle)
        r = rot.get_rect(center=(self.x - cam[0], self.y - cam[1]))
        surf.blit(rot, r)
        if self.dents:
            rad = math.radians(self.angle)
            cs, sn = math.cos(rad), math.sin(rad)
            cx_ = self.x - cam[0]; cy_ = self.y - cam[1]
            for dx_, dy_, dr_ in self.dents:
                wx = dx_ * cs - dy_ * sn
                wy = dx_ * sn + dy_ * cs
                pygame.draw.circle(surf, (25, 25, 28), (int(cx_ + wx), int(cy_ + wy)), dr_)

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
        # Achsen-getrennte Kollision -> kann an Wänden entlang gleiten
        # NPCs meiden auch Wasser
        rx = pygame.Rect(nx-10, self.y-10, 20, 20)
        if not any(rx.colliderect(b[0]) for b in AI_OBSTACLES):
            self.x = nx
        ry = pygame.Rect(self.x-10, ny-10, 20, 20)
        if not any(ry.colliderect(b[0]) for b in AI_OBSTACLES):
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
        # NPC wandern / fliehen
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

# ── Spawning ─────────────────────────────────────────────
def safe_spawn():
    while True:
        x = random.randint(INNER_LO + 30, INNER_HI_X - 30)
        y = random.randint(INNER_LO + 30, INNER_HI_Y - 30)
        r = pygame.Rect(x-15, y-15, 30, 30)
        if not any(r.colliderect(b[0]) for b in buildings):
            return x, y

def road_spawn():
    if random.random() < 0.5:
        x = random.randint(INNER_LO + 30, INNER_HI_X - 30)
        y = random.choice(roads_h) + random.choice([-25, 25])
    else:
        x = random.choice(roads_v) + random.choice([-25, 25])
        y = random.randint(INNER_LO + 30, INNER_HI_Y - 30)
    return x, y

cars = []
for _ in range(50):
    x, y = road_spawn()
    col = (random.randint(60,230), random.randint(60,230), random.randint(60,230))
    cars.append(Car(x, y, col))

peds = []
for _ in range(60):
    x, y = safe_spawn()
    peds.append(Ped(x, y))

cops = []
bullets = []  # (x, y, vx, vy, ttl, from_cop)

# ── Spieler ──────────────────────────────────────────────
player = Ped(WORLD_W//2, WORLD_H//2)
player.frames = make_ped_frames((40, 100, 200), hair=(30,20,15))
player.sprite = player.frames[0]
player.hp = 100
player.money = 0
player.wanted = 0
player.crime_timer = 0
player.aim_angle = 0  # separater Zielwinkel (Maus) — dreht den Sprite NICHT
in_car = None
weapon = 1  # 0 Fäuste, 1 Pistole, 2 SMG, 3 Schrot, 4 MG
ammo = {1: 80, 2: 200, 3: 30, 4: 400}
WPN_NAMES = ['Fäuste','Pistole','SMG','Schrotflinte','MG']
WPN_RATE  = [0.5, 0.4, 0.08, 0.85, 0.05]
WPN_DMG   = [25, 35, 15, 80, 28]
WPN_PEL   = [1, 1, 1, 6, 1]
WPN_SPRD  = [0, 0.03, 0.08, 0.22, 0.06]
WPN_AUTO  = [False, False, True, False, True]
fire_cd = 0
cop_spawn = 0

# ── Blut & Leichen ───────────────────────────────────────
blood_splats = []   # (x, y, radius, color) — persistent auf Boden
corpses = []        # (sprite, x, y, angle)
blood_particles = [] # (x, y, vx, vy, ttl, r)
smoke_particles = [] # [x, y, vx, vy, ttl, max_ttl, r]
fire_particles  = [] # [x, y, vx, vy, ttl, max_ttl, r]
explosions      = [] # [x, y, t, max_t, max_r]
wrecks          = [] # (sprite, x, y, angle, dents)  — ausgebrannte Karosserien

def make_corpse(ped):
    s = ped.sprite.copy()
    # Rote Lasur über Sprite
    overlay = pygame.Surface(s.get_size(), pygame.SRCALPHA)
    overlay.fill((140, 0, 0, 110))
    s.blit(overlay, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
    return s

def spawn_blood(x, y, amount=14):
    for _ in range(amount):
        a = random.uniform(0, 6.28)
        sp = random.uniform(40, 220)
        blood_particles.append([x, y, math.cos(a)*sp, math.sin(a)*sp,
                                random.uniform(0.3, 0.7), random.randint(2,4)])
    # permanente Pfütze
    for _ in range(random.randint(3, 6)):
        ox = x + random.uniform(-12, 12)
        oy = y + random.uniform(-12, 12)
        blood_splats.append((ox, oy, random.randint(4, 9),
                             (random.randint(110,160), 0, 0)))

# ── Hintergrund vorrendern ───────────────────────────────
def draw_world_bg(surf, cam):
    surf.fill(WATER_DEEP)
    # Strand-Ring (zwischen Wasser und Stadt)
    beach_rect = pygame.Rect(WATER_W - cam[0], WATER_W - cam[1],
                             WORLD_W - 2*WATER_W, WORLD_H - 2*WATER_W)
    pygame.draw.rect(surf, SAND, beach_rect)
    # Innere Stadt: Gras
    inner_rect = pygame.Rect(INNER_LO - cam[0], INNER_LO - cam[1],
                             INNER_HI_X - INNER_LO, INNER_HI_Y - INNER_LO)
    pygame.draw.rect(surf, GRASS, inner_rect)
    # Wellen (statisches Muster, nur im Wasser)
    wx0 = max(0, int(cam[0]))
    wy0 = max(0, int(cam[1]))
    wx1 = min(WORLD_W, int(cam[0]) + W)
    wy1 = min(WORLD_H, int(cam[1]) + H)
    for wy in range(wy0 - (wy0 % 28), wy1, 28):
        for wx in range(wx0 - (wx0 % 36), wx1, 36):
            if WATER_W < wx < WORLD_W - WATER_W and WATER_W < wy < WORLD_H - WATER_W:
                continue
            sx, sy = wx - cam[0], wy - cam[1]
            off = 6 if (wy // 28) % 2 else 0
            pygame.draw.line(surf, WATER_LITE,
                             (sx + 4 + off, sy + 12), (sx + 14 + off, sy + 12), 2)
            pygame.draw.line(surf, WATER_MID,
                             (sx + 18 + off, sy + 18), (sx + 26 + off, sy + 18), 1)
    # Sand-Textur (vereinzelte dunklere Flecken am Strand)
    for i in range(0, WORLD_W, 60):
        if not (WATER_W <= i <= WORLD_W - WATER_W): continue
        for edge in (WATER_W + 25, WORLD_H - WATER_W - 28):
            sx, sy = i - cam[0], edge - cam[1]
            if -10 < sx < W and -10 < sy < H:
                pygame.draw.circle(surf, (200, 180, 130), (int(sx), int(sy)), 2)
    # Straßen (Bürgersteig + Asphalt + Linien) — strikt innerhalb der Stadt
    rx = INNER_LO - cam[0]
    rw = INNER_HI_X - INNER_LO
    ry = INNER_LO - cam[1]
    rh = INNER_HI_Y - INNER_LO
    for y in roads_h:
        sy = y - cam[1]
        if -ROAD_W-20 < sy < H+ROAD_W+20:
            pygame.draw.rect(surf, SIDEW, (rx, sy - ROAD_W//2 - 8, rw, ROAD_W + 16))
    for x in roads_v:
        sx = x - cam[0]
        if -ROAD_W-20 < sx < W+ROAD_W+20:
            pygame.draw.rect(surf, SIDEW, (sx - ROAD_W//2 - 8, ry, ROAD_W + 16, rh))
    for y in roads_h:
        sy = y - cam[1]
        if -ROAD_W < sy < H+ROAD_W:
            pygame.draw.rect(surf, ASPHALT, (rx, sy - ROAD_W//2, rw, ROAD_W))
    for x in roads_v:
        sx = x - cam[0]
        if -ROAD_W < sx < W+ROAD_W:
            pygame.draw.rect(surf, ASPHALT, (sx - ROAD_W//2, ry, ROAD_W, rh))
    for y in roads_h:
        sy = y - cam[1]
        if -10 < sy < H+10:
            for dx in range(INNER_LO, INNER_HI_X, 50):
                sx = dx - cam[0]
                if -30 < sx < W:
                    pygame.draw.rect(surf, LINE, (sx, sy - 2, 28, 4))
    for x in roads_v:
        sx = x - cam[0]
        if -10 < sx < W+10:
            for dy in range(INNER_LO, INNER_HI_Y, 50):
                sy = dy - cam[1]
                if -30 < sy < H:
                    pygame.draw.rect(surf, LINE, (sx - 2, sy, 4, 28))

# ── Spielschleife ────────────────────────────────────────
def fire():
    global fire_cd
    if weapon == 0: return
    if ammo[weapon] <= 0: return
    ammo[weapon] -= 1
    fire_cd = WPN_RATE[weapon]
    if in_car:
        ax, ay = in_car.x, in_car.y
        ang = in_car.angle
    else:
        ax, ay = player.x, player.y
        ang = player.aim_angle
    for _ in range(WPN_PEL[weapon]):
        a = ang + random.uniform(-WPN_SPRD[weapon], WPN_SPRD[weapon]) * 57
        rad = math.radians(a)
        bullets.append([ax, ay, math.sin(rad)*900, -math.cos(rad)*900, 0.6, False, WPN_DMG[weapon]])

def aim_to_mouse():
    mx, my = pygame.mouse.get_pos()
    cx = player.x - cam[0]
    cy = player.y - cam[1]
    return math.degrees(math.atan2(mx - cx, -(my - cy)))

cam = [0, 0]
running = True
game_over = False

while running:
    dt = clock.tick(60) / 1000

    for e in pygame.event.get():
        if e.type == pygame.QUIT: running = False
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE: running = False
            if game_over and e.key == pygame.K_r:
                import os
                os.execv(sys.executable, [sys.executable] + sys.argv)
            if e.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5):
                weapon = e.key - pygame.K_1
            if e.key == pygame.K_e and not game_over:
                if in_car:
                    player.x = in_car.x + 40
                    player.y = in_car.y
                    in_car = None
                else:
                    for c in cars:
                        if math.hypot(c.x-player.x, c.y-player.y) < 60:
                            in_car = c
                            break
            if e.key == pygame.K_f and not in_car and not game_over:
                for p in peds:
                    if math.hypot(p.x-player.x, p.y-player.y) < 35:
                        player.money += random.randint(15, 50)
                        p.state = 'flee'
                        player.wanted = min(5, player.wanted + 1)
                        player.crime_timer = 30
                        break
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and not game_over:
            if fire_cd <= 0 and not WPN_AUTO[weapon]:
                fire()

    if not game_over:
        keys = pygame.key.get_pressed()
        fire_cd = max(0, fire_cd - dt)

        if in_car:
            accel = (1 if keys[pygame.K_w] else 0) - (1 if keys[pygame.K_s] else 0)
            steer = (1 if keys[pygame.K_d] else 0) - (1 if keys[pygame.K_a] else 0)
            in_car.update(dt, accel, steer)
            player.x, player.y = in_car.x, in_car.y
            # Wasser tötet: Auto explodiert beim Eintauchen
            if in_water(in_car.x, in_car.y):
                in_car.explode()
        else:
            sp = 220
            dx = (1 if keys[pygame.K_d] else 0) - (1 if keys[pygame.K_a] else 0)
            dy = (1 if keys[pygame.K_s] else 0) - (1 if keys[pygame.K_w] else 0)
            if dx or dy:
                n = math.hypot(dx, dy)
                nx = player.x + dx/n * sp * dt
                ny = player.y + dy/n * sp * dt
                pr = pygame.Rect(nx-10, ny-10, 20, 20)
                if not any(pr.colliderect(b[0]) for b in buildings):
                    player.x, player.y = nx, ny
                # Sprite folgt der Laufrichtung (GTA2-Style), nicht dem Mauszeiger
                player.angle = math.degrees(math.atan2(dx, -dy))
            player.aim_angle = aim_to_mouse()
            if keys[pygame.K_SPACE] or (pygame.mouse.get_pressed()[0] and WPN_AUTO[weapon]):
                if fire_cd <= 0: fire()
            # Ertrinken im Wasser
            if in_water(player.x, player.y):
                player.hp = 0
                corpses.append((make_corpse(player), player.x, player.y, player.angle))
                # blaue Spritzer statt Blut
                for _ in range(20):
                    a = random.uniform(0, 6.28); sp_ = random.uniform(40, 180)
                    blood_particles.append([player.x, player.y,
                                            math.cos(a)*sp_, math.sin(a)*sp_,
                                            random.uniform(0.3, 0.7), random.randint(2,4)])
                game_over = True

        # Kamera
        tx = (in_car.x if in_car else player.x) - W//2
        ty = (in_car.y if in_car else player.y) - H//2
        cam[0] += (tx - cam[0]) * min(1, 6*dt)
        cam[1] += (ty - cam[1]) * min(1, 6*dt)

        # Wanted/Cops
        if player.wanted > 0:
            player.crime_timer -= dt
            if player.crime_timer <= 0:
                player.wanted = max(0, player.wanted - 1)
                player.crime_timer = 25
            cop_spawn -= dt
            if cop_spawn <= 0 and len(cops) < player.wanted * 3:
                cop_spawn = max(2, 8 - player.wanted*1.5)
                ang = random.uniform(0, 6.28)
                cx = player.x + math.cos(ang) * 600
                cy = player.y + math.sin(ang) * 600
                cops.append(Ped(cx, cy, is_cop=True))
        else:
            cops.clear()

        # Verkehr
        for c in cars:
            if c is in_car: continue
            c.ai_update(dt)

        # Spieler-Animation
        player.animate(dt)

        # NPCs
        for p in peds:
            p.update(dt, player)
            p.animate(dt)
        for c in list(cops):
            wants_shoot = c.update(dt, player)
            c.animate(dt)
            if wants_shoot:
                c.shoot_tick = 1.5
                dx, dy = player.x - c.x, player.y - c.y
                d = math.hypot(dx, dy) or 1
                bullets.append([c.x, c.y, dx/d*700, dy/d*700, 0.8, True, 12])

        # Bullets
        for b in list(bullets):
            b[0] += b[2]*dt; b[1] += b[3]*dt; b[4] -= dt
            if b[4] <= 0:
                bullets.remove(b); continue
            br = pygame.Rect(b[0]-3, b[1]-3, 6, 6)
            if any(br.colliderect(bd[0]) for bd in buildings):
                bullets.remove(b); continue
            if b[5]:  # cop bullet -> player
                if in_car and br.colliderect(in_car.rect()):
                    in_car.take_damage(b[6] * 0.6)
                    bullets.remove(b)
                    continue
                if br.colliderect(player.rect()):
                    player.hp -= b[6]
                    spawn_blood(player.x, player.y, 6)
                    bullets.remove(b)
                    if player.hp <= 0:
                        corpses.append((make_corpse(player), player.x, player.y, player.angle))
                        spawn_blood(player.x, player.y, 22)
                        game_over = True
                    continue
            else:
                hit_any = False
                # Auto-Treffer (außer das Auto, in dem der Spieler sitzt)
                for c in cars:
                    if c is in_car or c.dead: continue
                    if br.colliderect(c.rect()):
                        c.take_damage(b[6] * 0.5)
                        bullets.remove(b); hit_any = True; break
                if hit_any: continue
                for p in list(peds):
                    if br.colliderect(p.rect()):
                        p.hp -= b[6]; p.state = 'flee'
                        spawn_blood(p.x, p.y, 4)
                        if p.hp <= 0:
                            peds.remove(p)
                            corpses.append((make_corpse(p), p.x, p.y, p.angle))
                            spawn_blood(p.x, p.y, 20)
                            player.money += random.randint(15, 60)
                            player.wanted = min(5, player.wanted + 1)
                            player.crime_timer = 30
                        bullets.remove(b); hit_any=True; break
                if hit_any: continue
                for c in list(cops):
                    if br.colliderect(c.rect()):
                        c.hp -= b[6]
                        spawn_blood(c.x, c.y, 5)
                        if c.hp <= 0:
                            cops.remove(c)
                            corpses.append((make_corpse(c), c.x, c.y, c.angle))
                            spawn_blood(c.x, c.y, 24)
                            player.wanted = min(5, player.wanted + 1)
                            player.crime_timer = 30
                        bullets.remove(b); break

        # Auto-FX (Rauch, Feuer, Explosion)
        for c in list(cars):
            c.update_fx(dt)
            if c.dead:
                cars.remove(c)
                # Ersatz spawnen, damit Verkehr nicht ausstirbt
                nx, ny = road_spawn()
                col = (random.randint(60,230), random.randint(60,230), random.randint(60,230))
                cars.append(Car(nx, ny, col))
        # Rauch-Partikel
        for sp_ in list(smoke_particles):
            sp_[4] -= dt
            if sp_[4] <= 0:
                smoke_particles.remove(sp_); continue
            sp_[0] += sp_[2]*dt; sp_[1] += sp_[3]*dt
            sp_[2] *= 0.96; sp_[3] = sp_[3]*0.96 - 8*dt
        # Feuer-Partikel
        for fp in list(fire_particles):
            fp[4] -= dt
            if fp[4] <= 0:
                fire_particles.remove(fp); continue
            fp[0] += fp[2]*dt; fp[1] += fp[3]*dt
            fp[2] *= 0.90; fp[3] *= 0.90
        # Explosionen
        for ex in list(explosions):
            ex[2] += dt
            if ex[2] >= ex[3]:
                explosions.remove(ex)

        # Blut-Partikel updaten
        for bp in list(blood_particles):
            bp[4] -= dt
            if bp[4] <= 0:
                # Bei Aufschlag permanenten Splat hinterlassen
                blood_splats.append((bp[0], bp[1], bp[5],
                                     (random.randint(110,160), 0, 0)))
                blood_particles.remove(bp); continue
            bp[0] += bp[2]*dt; bp[1] += bp[3]*dt
            bp[2] *= 0.92; bp[3] *= 0.92

    # ── Rendern ──────────────────────────────────────────
    icam = (int(cam[0]), int(cam[1]))
    draw_world_bg(screen, icam)
    view = pygame.Rect(icam[0]-20, icam[1]-20, W+40, H+40)
    # Blut-Pfützen (auf Boden, unter allem)
    for bs in blood_splats:
        sx, sy = int(bs[0]-icam[0]), int(bs[1]-icam[1])
        if -20 < sx < W+20 and -20 < sy < H+20:
            pygame.draw.circle(screen, bs[3], (sx, sy), bs[2])
    # Leichen
    for cs, cx, cy, ca in corpses:
        if view.collidepoint(cx, cy):
            rot = pygame.transform.rotate(cs, -ca)
            r = rot.get_rect(center=(cx - icam[0], cy - icam[1]))
            screen.blit(rot, r)
    # Häuser (Wasser-Rects haben surf=None und werden übersprungen)
    for rect, surf in buildings:
        if surf is None: continue
        if view.colliderect(rect):
            screen.blit(surf, (rect.x - icam[0], rect.y - icam[1]))
    # Wracks (unter Autos)
    for ws, wx, wy, wa, wd in wrecks:
        if view.collidepoint(wx, wy):
            rot = pygame.transform.rotate(ws, -wa)
            r = rot.get_rect(center=(wx - icam[0], wy - icam[1]))
            screen.blit(rot, r)
            rad = math.radians(wa); cs_, sn_ = math.cos(rad), math.sin(rad)
            for dx_, dy_, dr_ in wd:
                wxr = dx_ * cs_ - dy_ * sn_
                wyr = dx_ * sn_ + dy_ * cs_
                pygame.draw.circle(screen, (10,10,12),
                                   (int(wx + wxr - icam[0]), int(wy + wyr - icam[1])), dr_)
    # Autos
    for c in cars: c.draw(screen, icam)
    # NPCs
    for p in peds: p.draw(screen, icam)
    # Cops
    for c in cops: c.draw(screen, icam)
    # Spieler
    if not in_car:
        player.draw(screen, icam)
    # Blut-Partikel
    for bp in blood_particles:
        pygame.draw.circle(screen, (180, 0, 0),
                           (int(bp[0]-icam[0]), int(bp[1]-icam[1])), bp[5])
    # Bullets
    for b in bullets:
        pygame.draw.circle(screen, (255,230,80), (int(b[0]-icam[0]), int(b[1]-icam[1])), 3)
    # Feuer-Partikel
    for fp in fire_particles:
        t = max(0.0, fp[4] / fp[5])
        # heiß (gelb) → kalt (rot)
        col = (255, int(80 + 175 * t), int(40 * t))
        r = max(1, int(fp[6] * (0.5 + 0.5*t)))
        pygame.draw.circle(screen, col, (int(fp[0]-icam[0]), int(fp[1]-icam[1])), r)
    # Rauch-Partikel
    for sp_ in smoke_particles:
        t = max(0.0, sp_[4] / sp_[5])
        gv = int(60 + 110 * (1 - t))   # frisch dunkel, alt heller
        alpha = int(200 * t)
        r = max(1, int(sp_[6] * (1.4 - 0.4*t)))
        srf = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pygame.draw.circle(srf, (gv, gv, gv, alpha), (r, r), r)
        screen.blit(srf, (int(sp_[0]-icam[0]-r), int(sp_[1]-icam[1]-r)))
    # Explosions-Blitz
    for ex in explosions:
        t = ex[2] / ex[3]
        r = int(ex[4] * (0.3 + 0.7*t))
        a = int(220 * (1 - t))
        srf = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pygame.draw.circle(srf, (255, 200, 80, a), (r, r), r)
        pygame.draw.circle(srf, (255, 240, 180, min(255, a+30)), (r, r), int(r*0.6))
        screen.blit(srf, (int(ex[0]-icam[0]-r), int(ex[1]-icam[1]-r)))

    # HUD
    pygame.draw.rect(screen, (0,0,0), (10, 10, 220, 30))
    pygame.draw.rect(screen, (200,40,40), (12, 12, 216*max(0,player.hp)/100, 26))
    screen.blit(FONT.render(f"HP {int(player.hp)}", 1, (255,255,255)), (16, 14))
    screen.blit(FONT.render(f"${player.money}", 1, (60,230,80)), (10, 50))
    screen.blit(FONT.render(WPN_NAMES[weapon], 1, (240,220,80)), (10, 75))
    a = ammo.get(weapon, 0) if weapon != 0 else "∞"
    screen.blit(FONT.render(f"Munition {a}", 1, (255,255,255)), (10, 100))
    screen.blit(FONT.render("★"*player.wanted, 1, (255,200,40)), (W//2-40, 14))
    screen.blit(FONT.render("WASD bewegen | Maus zielen | LMB / SPACE schießen | E Auto | F rauben | 1-5 Waffe (5=MG)",
                            1, (230,230,230)), (10, H-26))
    if in_car:
        screen.blit(FONT.render(f"{int(abs(in_car.spd)*0.36*10)} km/h", 1, (255,255,255)), (W-140, 14))
        # Auto-HP-Balken
        pygame.draw.rect(screen, (0,0,0), (W-230, 50, 220, 22))
        frac = max(0, in_car.hp) / in_car.max_hp
        col = (60,200,60) if frac > 0.6 else ((230,180,40) if frac > 0.3 else (220,40,40))
        pygame.draw.rect(screen, col, (W-228, 52, 216*frac, 18))
        label = "BRENNT!" if in_car.burning else f"Auto {int(in_car.hp)}/{in_car.max_hp}"
        screen.blit(FONT.render(label, 1, (255,255,255)), (W-225, 52))
    # Fadenkreuz
    if not in_car:
        mx, my = pygame.mouse.get_pos()
        pygame.draw.circle(screen, (255,255,255), (mx,my), 8, 1)
        pygame.draw.line(screen, (255,255,255), (mx-12,my), (mx+12,my), 1)
        pygame.draw.line(screen, (255,255,255), (mx,my-12), (mx,my+12), 1)

    if game_over:
        s = pygame.Surface((W,H), pygame.SRCALPHA); s.fill((0,0,0,160))
        screen.blit(s, (0,0))
        t = BIG.render("GAME OVER", 1, (240,60,60))
        screen.blit(t, (W//2 - t.get_width()//2, H//2 - 60))
        t2 = FONT.render("[R] Neu starten   [ESC] Beenden", 1, (255,255,255))
        screen.blit(t2, (W//2 - t2.get_width()//2, H//2 + 10))

    pygame.display.flip()

pygame.quit()
