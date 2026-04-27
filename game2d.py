#!/home/jixo/test/venv/bin/python3
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
    # phase: -1 (links vor), 0 (mitte), +1 (rechts vor); Arme gegengleich
    s = pygame.Surface((24, 26), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (0,0,0,90), (3, 20, 18, 6))
    # Beine: das vordere Bein länger / weiter unten
    l_off = 2 if phase < 0 else (-1 if phase > 0 else 0)
    r_off = 2 if phase > 0 else (-1 if phase < 0 else 0)
    l_h = 8 + (1 if phase != 0 else 0)
    r_h = 8 + (1 if phase != 0 else 0)
    pygame.draw.rect(s, (40,40,80), (7, 14 + l_off, 4, l_h))
    pygame.draw.rect(s, (40,40,80), (13, 14 + r_off, 4, r_h))
    pygame.draw.rect(s, (20,20,20), (6, 14 + l_off + l_h, 5, 3))
    pygame.draw.rect(s, (20,20,20), (13, 14 + r_off + r_h, 5, 3))
    # Torso
    pygame.draw.rect(s, shirt_col, (5, 8, 14, 8), border_radius=2)
    # Arme: gegenphasig schwingen
    al_off = -r_off  # gegengleich zu rechtem Bein
    ar_off = -l_off
    pygame.draw.rect(s, shirt_col, (3, 9 + al_off, 3, 6))
    pygame.draw.rect(s, shirt_col, (18, 9 + ar_off, 3, 6))
    pygame.draw.rect(s, skin, (3, 14 + al_off, 3, 2))
    pygame.draw.rect(s, skin, (18, 14 + ar_off, 3, 2))
    # Kopf
    pygame.draw.circle(s, skin, (12, 5), 4)
    pygame.draw.arc(s, hair, (8, 1, 8, 7), 3.14, 6.28, 2)
    if is_cop:
        pygame.draw.rect(s, COP_DARK, (8, 1, 8, 3))
        pygame.draw.rect(s, COP_DARK, (7, 3, 10, 1))
        pygame.draw.rect(s, (230,200,60), (10, 10, 2, 2))
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
buildings = []   # (rect, surface)
roads_h = []     # horizontale Straßen y-Koordinaten
roads_v = []     # vertikale Straßen x-Koordinaten

for y in range(0, WORLD_H, BLOCK):
    roads_h.append(y)
for x in range(0, WORLD_W, BLOCK):
    roads_v.append(x)

random.seed(7)
seed = 0
for bx in range(0, WORLD_W, BLOCK):
    for by in range(0, WORLD_H, BLOCK):
        # Block-Inneres bebauen mit 1-4 Häusern
        x0 = bx + ROAD_W//2 + 14
        y0 = by + ROAD_W//2 + 14
        x1 = bx + BLOCK - ROAD_W//2 - 14
        y1 = by + BLOCK - ROAD_W//2 - 14
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
        self.hp = 200
        # KI
        self.ai_spd = random.uniform(80, 160)
        self.turn_cd = random.uniform(2, 6)

    def rect(self):
        return pygame.Rect(self.x - self.w//2, self.y - self.h//2, self.w, self.h)

    def update(self, dt, accel=0, steer=0):
        if accel > 0:
            self.spd = min(self.max_spd, self.spd + 260 * dt)
        elif accel < 0:
            self.spd = max(-self.max_spd*0.5, self.spd - 260 * dt)
        else:
            self.spd *= max(0, 1 - 1.4 * dt)
        if abs(self.spd) > 5:
            self.angle += steer * 110 * dt * (self.spd/self.max_spd)
        rad = math.radians(self.angle)
        nx = self.x + math.sin(rad) * self.spd * dt
        ny = self.y - math.cos(rad) * self.spd * dt
        # Kollision mit Häusern
        old_rect = self.rect()
        test = pygame.Rect(nx - self.w//2, ny - self.h//2, self.w, self.h)
        hit = any(test.colliderect(b[0]) for b in buildings)
        if hit:
            self.spd *= -0.3
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
        blocked = any(test.colliderect(b[0]) for b in buildings)
        if not blocked:
            for c in cars:
                if c is self: continue
                if test.colliderect(c.rect()):
                    blocked = True; break
        # Auch Spieler/eigenes Auto meiden
        if not blocked and in_car and test.colliderect(in_car.rect()):
            blocked = True
        # Weltgrenzen
        if nx < 60 or nx > WORLD_W-60 or ny < 60 or ny > WORLD_H-60:
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
        rx = pygame.Rect(nx-10, self.y-10, 20, 20)
        if not any(rx.colliderect(b[0]) for b in buildings):
            self.x = nx
        ry = pygame.Rect(self.x-10, ny-10, 20, 20)
        if not any(ry.colliderect(b[0]) for b in buildings):
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
        x = random.randint(100, WORLD_W-100)
        y = random.randint(100, WORLD_H-100)
        r = pygame.Rect(x-15, y-15, 30, 30)
        if not any(r.colliderect(b[0]) for b in buildings):
            return x, y

def road_spawn():
    if random.random() < 0.5:
        x = random.randint(100, WORLD_W-100)
        y = random.choice(roads_h) + random.choice([-25, 25])
    else:
        x = random.choice(roads_v) + random.choice([-25, 25])
        y = random.randint(100, WORLD_H-100)
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
    surf.fill(GRASS)
    # Bürgersteige (horizontal & vertikal)
    for y in roads_h:
        sy = y - cam[1]
        if -ROAD_W-20 < sy < H+ROAD_W+20:
            pygame.draw.rect(surf, SIDEW, (-cam[0], sy - ROAD_W//2 - 8, WORLD_W, ROAD_W + 16))
    for x in roads_v:
        sx = x - cam[0]
        if -ROAD_W-20 < sx < W+ROAD_W+20:
            pygame.draw.rect(surf, SIDEW, (sx - ROAD_W//2 - 8, -cam[1], ROAD_W + 16, WORLD_H))
    # Asphalt
    for y in roads_h:
        sy = y - cam[1]
        if -ROAD_W < sy < H+ROAD_W:
            pygame.draw.rect(surf, ASPHALT, (-cam[0], sy - ROAD_W//2, WORLD_W, ROAD_W))
    for x in roads_v:
        sx = x - cam[0]
        if -ROAD_W < sx < W+ROAD_W:
            pygame.draw.rect(surf, ASPHALT, (sx - ROAD_W//2, -cam[1], ROAD_W, WORLD_H))
    # Mittellinien gestrichelt
    for y in roads_h:
        sy = y - cam[1]
        if -10 < sy < H+10:
            for dx in range(0, WORLD_W, 50):
                sx = dx - cam[0]
                if -30 < sx < W:
                    pygame.draw.rect(surf, LINE, (sx, sy - 2, 28, 4))
    for x in roads_v:
        sx = x - cam[0]
        if -10 < sx < W+10:
            for dy in range(0, WORLD_H, 50):
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
        ang = player.angle
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
            player.angle = aim_to_mouse()
            if keys[pygame.K_SPACE] or (pygame.mouse.get_pressed()[0] and WPN_AUTO[weapon]):
                if fire_cd <= 0: fire()

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
    # Häuser
    for rect, surf in buildings:
        if view.colliderect(rect):
            screen.blit(surf, (rect.x - icam[0], rect.y - icam[1]))
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
