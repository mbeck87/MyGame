"""Einstiegspunkt: pygame init, Welt aufbauen, Hauptschleife starten."""
import math
import os
import random
import sys

import pygame

from game2d.config import (
    W, H,
    WORLD_W, WORLD_H,
    WPN_NAMES, WPN_AUTO,
    PICKUP_AMMO, PICKUP_RESPAWN,
)
from game2d.persistence import name_input_screen
from game2d.render.hud import draw_star
from game2d.render.menus import draw_hint, draw_overlay_menu, draw_service_markers
from game2d.render.minimap import draw_minimap
from game2d.render.sprites import make_ped_frames, make_swim_frames, get_pickup_icon
from game2d.render.world_bg import draw_world_bg
from game2d.state import GameState, init as state_init
from game2d.world.generation import build_world
from game2d.world.geometry import in_city, in_water, point_in_polygon, rect_hits_amusement_stand
from game2d.world.spawning import (
    safe_spawn, sidewalk_spawn, pedestrian_spawn, exit_car_position, road_spawn, cop_car_spawn_near,
)
from game2d.entities.car import (
    Car,
    law_color_for_kind,
    law_kind_for_wanted,
    random_car_color,
    random_car_kind,
)
from game2d.entities.ped import Ped
from game2d.entities.cat import Cat
from game2d.systems.effects import (
    make_corpse, spawn_blood, trigger_game_over, do_explosion,
)
from game2d.systems.services import (
    add_money, add_wanted_heat, on_kill, cop_weapon_profile, sync_wanted_heat_after_drop,
    buy_shop_item, clear_roadblocks,
    escalate_police, init_services, nearby_service, use_barber_item, use_garage_item,
    SHOP_ITEMS, GARAGE_ITEMS, BARBER_COLORS, BARBER_STYLES,
)
from game2d.systems.weapons import fire, aim_to_mouse
from game2d.systems import audio
from game2d import settings as settings_mod
from game2d.ui.menu import MenuController


def _nearest_point_on_segment(px, py, ax, ay, bx, by):
    vx = bx - ax
    vy = by - ay
    seg_len_sq = vx * vx + vy * vy
    if seg_len_sq <= 0:
        return ax, ay, (px - ax) ** 2 + (py - ay) ** 2
    t = max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / seg_len_sq))
    x = ax + vx * t
    y = ay + vy * t
    return x, y, (px - x) ** 2 + (py - y) ** 2


def _nearest_pond_edge_point(state, x, y):
    best = None
    best_dist_sq = None
    for pond in state.park_ponds:
        for p0, p1 in zip(pond, pond[1:] + pond[:1]):
            px, py, dist_sq = _nearest_point_on_segment(x, y, p0[0], p0[1], p1[0], p1[1])
            if best_dist_sq is None or dist_sq < best_dist_sq:
                best = (px, py)
                best_dist_sq = dist_sq
    return best, math.sqrt(best_dist_sq) if best_dist_sq is not None else 999999


def _player_at_pond_shore(state):
    if state.in_car or not state.park_ponds:
        return False, None
    x, y = state.player.x, state.player.y
    if any(point_in_polygon(x, y, pond) for pond in state.park_ponds):
        return False, None
    edge, dist = _nearest_pond_edge_point(state, x, y)
    return dist <= 42, edge


def _update_duck_easter(state, dt, moved):
    if state.duck_easter_duck:
        duck = state.duck_easter_duck
        dx = duck[2] - duck[0]
        dy = duck[3] - duck[1]
        dist = math.hypot(dx, dy)
        if dist > 1:
            step = min(dist, 48 * dt)
            duck[0] += dx / dist * step
            duck[1] += dy / dist * step
        duck[4] -= dt
        if duck[4] <= 0:
            state.duck_easter_duck = None

    if state.duck_easter_done:
        return
    at_shore, edge = _player_at_pond_shore(state)
    if at_shore and moved < 1.0:
        state.duck_easter_timer += dt
    else:
        state.duck_easter_timer = 0.0
    if state.duck_easter_timer < 5.0 or edge is None:
        return

    px, py = state.player.x, state.player.y
    vx = px - edge[0]
    vy = py - edge[1]
    dist = math.hypot(vx, vy) or 1
    target_x = px - vx / dist * 22
    target_y = py - vy / dist * 22
    state.duck_easter_duck = [edge[0], edge[1], target_x, target_y, 8.0]
    state.duck_easter_done = True
    state.message = "Die Enten wissen Bescheid"
    state.message_timer = 3.5


def _spawn_traffic_and_player(state):
    # Reduzierte Start-Anzahl für bessere Performance
    # Original: 50 Autos, 60 Peds, 38 Amusement-Peds
    NUM_START_CARS = 50
    NUM_START_PEDS = 40  # Reduziert von 60
    NUM_AMUSEMENT_PEDS = 20  # Reduziert von 38
    
    for _ in range(NUM_START_CARS):
        kind = random_car_kind()
        x, y, angle = road_spawn(kind)
        car = Car(x, y, random_car_color(kind), kind=kind)
        car.angle = angle
        car.driver = True
        state.cars.append(car)

    for _ in range(NUM_START_PEDS):
        x, y = pedestrian_spawn()
        state.peds.append(Ped(x, y))
    
    # Katze spawnen (max 1, bevorzugt im Park, nie im Wasser)
    park = state.parks[0] if state.parks else None
    cx, cy = pedestrian_spawn()   # sicherer Fallback
    if park:
        margin = 60
        for _ in range(40):  # Reduziert von 60
            px = random.randint(park.left + margin, park.right - margin)
            py = random.randint(park.top + margin, park.bottom - margin)
            if in_city(px, py, 20):
                cx, cy = px, py
                break
    state.cats.append(Cat(cx, cy))

    player_x, player_y = safe_spawn()
    player = Ped(player_x, player_y)
    player.shirt = (40, 100, 200)
    player.gender = "m"
    player.hair_style = "short"
    player.hair_color = (30, 20, 15)
    player.frames = make_ped_frames(player.shirt, hair=player.hair_color, gender=player.gender, hair_style=player.hair_style)
    player.back_frames = make_ped_frames(player.shirt, hair=player.hair_color, gender=player.gender, hair_style=player.hair_style, back=True)
    player.swim_frames = make_swim_frames(player.shirt, hair=player.hair_color, gender=player.gender, hair_style=player.hair_style)
    player.sprite = player.back_frames[0]
    player.hp = 100
    player.armor = 0
    player.money = 0
    player.total_money_earned = 0
    player.wanted = 0
    player.crime_timer = 0
    player.aim_angle = 0
    player.step_cd = 0.0
    state.player = player
    state.in_car = None
    state.weapon = 0
    state.ammo = {1: 80, 2: 0, 3: 0, 4: 0, 5: 0}
    state.unlocked_weapons = {0, 1}
    state.fire_cd = 0
    state.cam = [player.x - W // 2, player.y - H // 2]

    pickup_defs = (
        [('hp', None)] * 22 +
        [('armor', None)] * 8 +
        [(2,   None)] * 6 +
        [(3,   None)] * 4 +
        [(4,   None)] * 3 +
        [(5,   None)] * 2
    )
    for kind, _ in pickup_defs:
        spawn_fn = sidewalk_spawn if kind == 'armor' else safe_spawn
        px, py = spawn_fn()
        state.pickups.append([px, py, kind, 0.0])

    amusement_nodes = list(state.amusement_park_nodes)
    for _ in range(NUM_AMUSEMENT_PEDS):
        if not amusement_nodes:
            break
        x, y = state.pedestrian_nodes[random.choice(amusement_nodes)]
        ped = Ped(x + random.uniform(-10, 10), y + random.uniform(-10, 10))
        ped.route_replan = random.uniform(0.1, 1.0)
        state.peds.append(ped)


def reset_game(state):
    # Stop alle Loop-Sounds von allen Cars
    for car in list(state.cops) + list(state.cars):
        for attr in ['_siren_channel', '_engine_channel', '_squeal_channel']:
            ch = getattr(car, attr, None)
            if ch is not None:
                audio.stop_loop(ch)
                setattr(car, attr, None)
    for r in state.rockets:
        if len(r) > 5 and r[5] is not None:
            audio.stop_loop(r[5])
    state.cars.clear()
    state.peds.clear()
    state.cops.clear()
    state.cats.clear()
    state.intersection_claims.clear()
    state.bullets.clear()
    state.rockets.clear()
    state.blood_splats.clear()
    state.blood_particles.clear()
    state.smoke_particles.clear()
    state.fire_particles.clear()
    state.explosions.clear()
    state.lightsaber_swings.clear()
    state.wrecks.clear()
    state.corpses.clear()
    state.pickups.clear()
    state.roadblocks.clear()
    state.cop_spawn = 0.0
    state.wanted_heat = 0.0
    state.last_wanted_level = 0
    state.roadblock_wanted_level = 0
    state.roadblocks_cleared_on_drop = False
    state.duck_easter_timer = 0.0
    state.duck_easter_done = False
    state.duck_easter_duck = None
    state.duck_easter_last_pos = None
    state.message = ""
    state.message_timer = 0.0
    state.game_over = False
    state.score_saved = False
    state.paused = False
    state.menu = None
    state.final_scores = []
    _spawn_traffic_and_player(state)


def main():
    pygame.init()
    audio.init()
    settings = settings_mod.load()
    audio.MASTER_VOL = settings['sfx_volume']
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Mini GTA 2D")
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()
    FONT = pygame.font.SysFont("arial", 20, bold=True)
    BIG  = pygame.font.SysFont("arial", 64, bold=True)
    MED  = pygame.font.SysFont("arial", 32, bold=True)

    def draw_hud_text(text, pos, color):
        shadow = FONT.render(text, 1, (0, 0, 0))
        label = FONT.render(text, 1, color)
        screen.blit(shadow, (pos[0] + 2, pos[1] + 2))
        screen.blit(label, pos)

    player_name = name_input_screen(screen, W, H, BIG, MED, FONT)

    state = GameState(player_name=player_name)
    state.settings = settings
    state_init(state)
    build_world(state)
    init_services(state)
    menu_ctrl = MenuController(W, H, settings)

    _spawn_traffic_and_player(state)
    player = state.player

    while state.running:
        dt = clock.tick(60) / 1000
        player = state.player
        if state.message_timer > 0:
            state.message_timer = max(0.0, state.message_timer - dt)
        if not state.menu:
            state.traffic_time += dt

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                state.running = False
                continue

            if state.menu in ("pause", "options"):
                if e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_p):
                    state.menu = None if state.menu == "pause" else "pause"
                    continue
                action = menu_ctrl.handle_event(e, state)
                if action == 'resume':
                    state.menu = None
                elif action == 'open_options':
                    state.menu = 'options'
                elif action == 'back':
                    state.menu = 'pause'
                elif action == 'apply_resolution':
                    pygame.quit()
                    os.execv(sys.executable, [sys.executable] + sys.argv)
                elif action == 'exit':
                    state.running = False
                continue

            if state.menu in ("shop", "garage", "barber", "bank"):
                if e.type == pygame.KEYDOWN and state.menu == "barber" and e.key == pygame.K_f:
                    state.barber_step = "style"
                    continue
                if e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_p, pygame.K_f):
                    state.menu = None
                    continue
                if state.menu == "shop":
                    max_key = max(SHOP_ITEMS)
                elif state.menu == "garage":
                    max_key = max(GARAGE_ITEMS)
                elif state.menu == "bank":
                    max_key = 1
                else:
                    max_key = len(BARBER_COLORS if state.barber_step == "color" else BARBER_STYLES)
                if e.type == pygame.KEYDOWN and pygame.K_1 <= e.key < pygame.K_1 + max_key:
                    if state.menu == "shop":
                        buy_shop_item(state, e.key - pygame.K_0)
                    elif state.menu == "garage":
                        use_garage_item(state, e.key - pygame.K_0)
                    elif state.menu == "bank":
                        if state.bank_robbery_cooldown <= 0:
                            add_money(state.player, 5000)
                            add_wanted_heat(state, heat=350, timer=60)
                            state.bank_robbery_cooldown = 300.0  # 5 Minuten Sperre
                        state.menu = None
                    else:
                        use_barber_item(state, e.key - pygame.K_0)
                    continue
                continue

            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    if state.game_over:
                        state.running = False
                    else:
                        state.menu = "pause"
                        audio.set_engine(False)
                    continue
                if e.key == pygame.K_p and not state.game_over:
                    state.menu = "pause"
                    audio.set_engine(False)
                    continue
                if state.game_over and e.key == pygame.K_SPACE:
                    reset_game(state)
                    continue
                if e.key == pygame.K_f and not state.game_over:
                    _svc = nearby_service(state)
                    if _svc == "shop":
                        state.menu = "shop"
                        continue
                    if _svc == "garage":
                        state.menu = "garage"
                        continue
                    if _svc == "barber":
                        state.menu = "barber"
                        state.barber_step = "style"
                        continue
                    if _svc == "bank":
                        state.menu = "bank"
                        continue
                if pygame.K_1 <= e.key < pygame.K_1 + len(WPN_NAMES):
                    w = e.key - pygame.K_1
                    if w in state.unlocked_weapons:
                        state.weapon = w
                if e.key == pygame.K_e and not state.game_over:
                    if state.in_car:
                        player.x, player.y = exit_car_position(state.in_car)
                        state.in_car.driver = None
                        state.in_car = None
                        audio.play('door_close', pos=(player.x, player.y))
                        audio.set_engine(False)
                    else:
                        for c in state.cars:
                            if c.dead or getattr(c, "sunk", False):
                                continue
                            if c.rect().inflate(36, 36).collidepoint(player.x, player.y):
                                if c.driver is not None and not c.is_cop:
                                    # Fahrer rauswerfen
                                    ex, ey = exit_car_position(c)
                                    ejected = Ped(ex, ey)
                                    ejected.state = 'flee'
                                    state.peds.append(ejected)
                                state.in_car = c
                                c.driver = player
                                c.signal_dir = 0
                                audio.play('door_open', pos=(c.x, c.y))
                                break
                if e.key == pygame.K_f and not state.in_car and not state.game_over:
                    for p in state.peds:
                        if math.hypot(p.x-player.x, p.y-player.y) < 35:
                            add_money(player, random.randint(15, 50))
                            p.state = 'flee'
                            add_wanted_heat(state, "robbery")
                            audio.play('robbery', pos=(p.x, p.y))
                            break
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and not state.game_over and not state.paused and not state.menu:
                on_motorcycle = state.in_car and state.in_car.kind == "motorcycle"
                if state.fire_cd <= 0 and not WPN_AUTO[state.weapon] and (not state.in_car or on_motorcycle):
                    if on_motorcycle:
                        player.aim_angle = aim_to_mouse()
                    fire()

        if not state.game_over and not state.menu:
            keys = pygame.key.get_pressed()
            state.fire_cd = max(0, state.fire_cd - dt)
            state.bank_robbery_cooldown = max(0.0, state.bank_robbery_cooldown - dt)

            if state.in_car:
                accel = (1 if keys[pygame.K_w] else 0) - (1 if keys[pygame.K_s] else 0)
                steer = (1 if keys[pygame.K_d] else 0) - (1 if keys[pygame.K_a] else 0)
                handbrake = bool(keys[pygame.K_SPACE])
                state.in_car.update(dt, accel, steer, handbrake=handbrake)
                if state.in_car and not state.in_car.dead:
                    player.x, player.y = state.in_car.x, state.in_car.y
                    audio.set_engine(True, throttle=accel,
                                     speed_norm=abs(state.in_car.spd) / state.in_car.max_spd)
                else:
                    audio.set_engine(False)
                if state.in_car and in_water(state.in_car.x, state.in_car.y):
                    state.in_car.explode()
                if state.in_car and state.in_car.kind == "motorcycle":
                    player.aim_angle = aim_to_mouse()
                    if pygame.mouse.get_pressed()[0] and WPN_AUTO[state.weapon]:
                        if state.fire_cd <= 0:
                            fire()
            else:
                audio.set_engine(False)
                sp = 220
                dx = (1 if keys[pygame.K_d] else 0) - (1 if keys[pygame.K_a] else 0)
                dy = (1 if keys[pygame.K_s] else 0) - (1 if keys[pygame.K_w] else 0)
                if dx or dy:
                    n = math.hypot(dx, dy)
                    mvx = dx/n * sp * dt
                    mvy = dy/n * sp * dt
                    solid_cars = [c for c in state.cars
                                  if not c.dead and not getattr(c, 'sunk', False)]
                    def _blocked(rx, ry):
                        pr = pygame.Rect(rx-10, ry-10, 20, 20)
                        if any(pr.colliderect(b[0]) for b in state.buildings):
                            return True
                        if rect_hits_amusement_stand(pr):
                            return True
                        return any(pr.colliderect(c.rect()) for c in solid_cars)
                    nx = player.x + mvx
                    if not _blocked(nx, player.y):
                        player.x = nx
                    ny = player.y + mvy
                    if not _blocked(player.x, ny):
                        player.y = ny
                    player.angle = math.degrees(math.atan2(dx, -dy))
                    player.step_cd -= dt
                    if player.step_cd <= 0:
                        player.step_cd = 0.34
                        audio.play('footstep', volume=0.45, pos=(player.x, player.y))
                else:
                    player.step_cd = 0.0
                player.aim_angle = aim_to_mouse()
                if pygame.mouse.get_pressed()[0] and WPN_AUTO[state.weapon]:
                    if state.fire_cd <= 0:
                        fire()
                if in_water(player.x, player.y):
                    player.hp = 0
                    state.corpses.append((make_corpse(player), player.x, player.y, player.angle))
                    for _ in range(20):
                        a = random.uniform(0, 6.28); sp_ = random.uniform(40, 180)
                        state.blood_particles.append([player.x, player.y,
                                                math.cos(a)*sp_, math.sin(a)*sp_,
                                                random.uniform(0.3, 0.7), random.randint(2,4)])
                    trigger_game_over()

            prev_duck_pos = state.duck_easter_last_pos
            duck_moved = 999.0 if prev_duck_pos is None else math.hypot(player.x - prev_duck_pos[0], player.y - prev_duck_pos[1])
            _update_duck_easter(state, dt, duck_moved)
            state.duck_easter_last_pos = (player.x, player.y)

            tx = (state.in_car.x if state.in_car else player.x) - W//2
            ty = (state.in_car.y if state.in_car else player.y) - H//2
            state.cam[0] += (tx - state.cam[0]) * min(1, 6*dt)
            state.cam[1] += (ty - state.cam[1]) * min(1, 6*dt)

            if player.wanted > 0:
                player.crime_timer -= dt
                if player.crime_timer <= 0:
                    player.wanted = max(0, player.wanted - 1)
                    sync_wanted_heat_after_drop(state)
                    player.crime_timer = 25
                state.cop_spawn -= dt
                law_kind = law_kind_for_wanted(player.wanted)
                wanted_increased = player.wanted > state.last_wanted_level
                view = pygame.Rect(int(state.cam[0]), int(state.cam[1]), W, H)
                if not wanted_increased and any(
                    getattr(car, "is_roadblock_support", False) and getattr(car, "kind", "cop") != law_kind
                    for car in state.cars
                ):
                    clear_roadblocks(state)
                for cop in list(state.cops):
                    if getattr(cop, "cop_kind", "cop") != law_kind:
                        if wanted_increased and view.colliderect(cop.rect()):
                            cop.keep_after_tier_change = True
                        elif not getattr(cop, "keep_after_tier_change", False):
                            state.cops.remove(cop)
                for car in list(state.cars):
                    if (
                        car.is_cop
                        and car is not state.in_car
                        and getattr(car, "kind", "cop") != law_kind
                        and not getattr(car, "is_roadblock_support", False)
                        and not getattr(car, "keep_after_tier_change", False)
                    ):
                        if wanted_increased and view.colliderect(car.rect()):
                            car.keep_after_tier_change = True
                            continue
                        if car._siren_channel is not None:
                            audio.stop_loop(car._siren_channel)
                            car._siren_channel = None
                        state.cars.remove(car)
                active_tier_cars = sum(
                    1 for c in state.cars
                    if (
                        c.is_cop
                        and getattr(c, "kind", "cop") == law_kind
                        and not c.dead
                        and not getattr(c, "sunk", False)
                        and not getattr(c, "is_roadblock_support", False)
                    )
                )
                cop_limit_by_wanted = {1: 20, 2: 20, 3: 20, 4: 20, 5: 20}
                cop_limit = cop_limit_by_wanted.get(player.wanted, max(1, player.wanted))
                if state.cop_spawn <= 0 and active_tier_cars < cop_limit:
                    state.cop_spawn = max(1.2, 8 - player.wanted*1.35)
                    spawn = cop_car_spawn_near(player.x, player.y, state.cam, law_kind)
                    if spawn is not None:
                        cx, cy, angle = spawn
                        car = Car(cx, cy, law_color_for_kind(law_kind), is_cop=True, kind=law_kind)
                        car.angle = angle
                        car.max_spd += max(0, player.wanted - 3) * 30
                        state.cars.append(car)
                escalate_police(state)
                state.last_wanted_level = player.wanted
            else:
                state.cops.clear()
                state.roadblocks.clear()
                state.roadblock_wanted_level = 0
                state.roadblocks_cleared_on_drop = False
                state.last_wanted_level = 0
                for c in list(state.cars):
                    if c.is_cop and c is not state.in_car:
                        if c._siren_channel is not None:
                            audio.stop_loop(c._siren_channel)
                            c._siren_channel = None
                        state.cars.remove(c)

            state.intersection_claims.clear()
            for c in state.cars:
                if c is state.in_car: continue
                if c in state.roadblocks: continue
                c.ai_update(dt)

            player.animate(dt)

            for p in state.peds:
                p.update(dt, player)
                p.animate(dt)
            for cat in state.cats:
                cat.update(dt, player)
                cat.animate(dt)
            for c in list(state.cops):
                wants_shoot = c.update(dt, player)
                c.animate(dt)
                if wants_shoot:
                    profile = cop_weapon_profile(getattr(c, "cop_kind", "cop"), player.wanted)
                    c.shoot_tick = profile["rate"]
                    dx, dy = player.x - c.x, player.y - c.y
                    d = math.hypot(dx, dy) or 1
                    base = math.atan2(dy, dx)
                    spread = random.uniform(-profile["spread"], profile["spread"])
                    vx = math.cos(base + spread) * profile["speed"]
                    vy = math.sin(base + spread) * profile["speed"]
                    state.bullets.append([c.x, c.y, vx, vy, 0.8, True, profile["damage"]])
                    audio.play(profile["sound"], pos=(c.x, c.y))

            for b in list(state.bullets):
                b[0] += b[2]*dt; b[1] += b[3]*dt; b[4] -= dt
                if b[4] <= 0:
                    state.bullets.remove(b); continue
                br = pygame.Rect(b[0]-3, b[1]-3, 6, 6)
                bx, by = b[0], b[1]
                
                # Optimiert: Nur nahe Gebäude prüfen (Bullets bewegen sich schnell, also kleiner Radius)
                bullet_hit_building = False
                for bd_rect, bd_surf in state.buildings:
                    if abs(bd_rect.centerx - bx) > 50 or abs(bd_rect.centery - by) > 50:
                        continue
                    if br.colliderect(bd_rect):
                        bullet_hit_building = True
                        break
                if bullet_hit_building:
                    state.bullets.remove(b); continue
                
                if b[5]:
                    # Cop-Bullets: Player und in_car prüfen
                    if state.in_car:
                        car_rect = state.in_car.rect()
                        if abs(car_rect.centerx - bx) < 30 and abs(car_rect.centery - by) < 30 and br.colliderect(car_rect):
                            state.in_car.take_damage(b[6] * 0.6, world_pos=(b[0], b[1]))
                            audio.play('hit_metal', volume=0.6, pos=(b[0], b[1]))
                            state.bullets.remove(b)
                            continue
                    player_rect = player.rect()
                    if abs(player_rect.centerx - bx) < 30 and abs(player_rect.centery - by) < 30 and br.colliderect(player_rect):
                        damage = b[6]
                        if player.armor > 0:
                            armor_dmg = min(player.armor, damage)
                            player.armor -= armor_dmg
                            damage -= armor_dmg
                        player.hp -= damage
                        spawn_blood(player.x, player.y, 6)
                        audio.play('hurt', pos=(player.x, player.y))
                        state.bullets.remove(b)
                        if player.hp <= 0:
                            state.corpses.append((make_corpse(player), player.x, player.y, player.angle))
                            spawn_blood(player.x, player.y, 22)
                            trigger_game_over()
                        continue
                else:
                    hit_any = False
                    # Nur Autos in der Nähe prüfen
                    for c in state.cars:
                        if c is state.in_car or c.dead: continue
                        if abs(c.x - bx) > 40 or abs(c.y - by) > 40: continue
                        if br.colliderect(c.rect()):
                            c.take_damage(b[6] * 0.5, world_pos=(b[0], b[1]))
                            audio.play('hit_metal', volume=0.55, pos=(b[0], b[1]))
                            state.bullets.remove(b); hit_any = True; break
                    if hit_any: continue
                    # Nur Peds in der Nähe prüfen
                    for p in list(state.peds):
                        if abs(p.x - bx) > 30 or abs(p.y - by) > 30: continue
                        if br.colliderect(p.rect()):
                            p.hp -= b[6]; p.state = 'flee'
                            spawn_blood(p.x, p.y, 4)
                            audio.play('hit_flesh', pos=(p.x, p.y))
                            audio.play('scream', pos=(p.x, p.y))
                            if p.hp <= 0:
                                state.peds.remove(p)
                                state.corpses.append((make_corpse(p), p.x, p.y, p.angle))
                                spawn_blood(p.x, p.y, 20)
                                add_money(player, random.randint(15, 60))
                                on_kill(state, p, is_cop=False)
                            state.bullets.remove(b); hit_any=True; break
                    if hit_any: continue
                    # Nur Cats in der Nähe prüfen
                    for cat in list(state.cats):
                        if abs(cat.x - bx) > 30 or abs(cat.y - by) > 30: continue
                        if br.colliderect(cat.rect()):
                            cat.hp -= b[6]
                            spawn_blood(cat.x, cat.y, 3)
                            audio.play('hit_flesh', pos=(cat.x, cat.y))
                            audio.play('scream', pos=(cat.x, cat.y))
                            if cat.hp <= 0:
                                state.cats.remove(cat)
                                state.corpses.append((cat.sprite.copy(), cat.x, cat.y, cat.angle))
                                spawn_blood(cat.x, cat.y, 10)
                                # 5 Sterne wanted für Katzen-Tötung
                                player.wanted = 5
                                player.crime_timer = 30
                                state.wanted_heat = 5 * 100  # MAX
                                add_money(player, random.randint(50, 100))
                            state.bullets.remove(b); hit_any=True; break
                    if hit_any: continue
                    # Nur Cops in der Nähe prüfen
                    for c in list(state.cops):
                        if abs(c.x - bx) > 30 or abs(c.y - by) > 30: continue
                        if br.colliderect(c.rect()):
                            c.hp -= b[6]
                            spawn_blood(c.x, c.y, 5)
                            audio.play('hit_flesh', pos=(c.x, c.y))
                            audio.play('scream', pos=(c.x, c.y))
                            if c.hp <= 0:
                                state.cops.remove(c)
                                state.corpses.append((make_corpse(c), c.x, c.y, c.angle))
                                spawn_blood(c.x, c.y, 24)
                                on_kill(state, c, is_cop=True)
                            state.bullets.remove(b); break

            for c in list(state.cars):
                c.update_fx(dt)
                if c.dead:
                    state.cars.remove(c)
                    if not c.is_cop:
                        kind = random_car_kind()
                        # Spawn weit entfernt vom Spieler
                        min_dist = 800
                        for _ in range(50):
                            nx, ny, angle = road_spawn(kind)
                            dist = math.hypot(nx - player.x, ny - player.y)
                            if dist >= min_dist:
                                break
                        car = Car(nx, ny, random_car_color(kind), kind=kind)
                        car.angle = angle
                        car.driver = True
                        state.cars.append(car)

            for sp_ in list(state.smoke_particles):
                sp_[4] -= dt
                if sp_[4] <= 0:
                    state.smoke_particles.remove(sp_); continue
                sp_[0] += sp_[2]*dt; sp_[1] += sp_[3]*dt
                sp_[2] *= 0.96; sp_[3] = sp_[3]*0.96 - 8*dt
            for fp in list(state.fire_particles):
                fp[4] -= dt
                if fp[4] <= 0:
                    state.fire_particles.remove(fp); continue
                fp[0] += fp[2]*dt; fp[1] += fp[3]*dt
                fp[2] *= 0.90; fp[3] *= 0.90
            for ex in list(state.explosions):
                ex[2] += dt
                if ex[2] >= ex[3]:
                    state.explosions.remove(ex)
            for sw in list(state.lightsaber_swings):
                sw[1] += dt
                if sw[1] >= sw[2]:
                    state.lightsaber_swings.remove(sw)

            for r in list(state.rockets):
                r[0] += r[2]*dt; r[1] += r[3]*dt; r[4] -= dt
                hit = r[4] <= 0
                rr = pygame.Rect(r[0]-5, r[1]-5, 10, 10)
                if not hit and any(rr.colliderect(b[0]) for b in state.buildings):
                    hit = True
                if not hit:
                    for c in state.cars:
                        if c is not state.in_car and not c.dead and rr.colliderect(c.rect()):
                            hit = True; break
                    for p in state.peds:
                        if rr.colliderect(p.rect()): hit = True; break
                    for c in state.cops:
                        if rr.colliderect(c.rect()): hit = True; break
                    for cat in state.cats:
                        if rr.colliderect(cat.rect()): hit = True; break
                if hit:
                    audio.stop_loop(r[5])
                    do_explosion(r[0], r[1])
                    state.rockets.remove(r)
                    add_wanted_heat(state, "explosion")
                else:
                    audio.update_loop(r[5], pos=(r[0], r[1]))

            for pk in state.pickups:
                if pk[3] > 0:
                    pk[3] = max(0.0, pk[3] - dt)
                    continue
                if math.hypot(player.x - pk[0], player.y - pk[1]) < 22:
                    kind = pk[2]
                    if kind == 'hp':
                        player.hp = min(100, player.hp + 30)
                        audio.play('pickup_hp')
                    elif kind == 'armor':
                        armor_amount = random.randint(100, 200)
                        player.armor = min(200, player.armor + armor_amount)
                        audio.play('pickup_hp')
                    elif isinstance(kind, int) and kind < 0:
                        # Magazine drop: negative weapon index = 10 bullets
                        weapon_idx = -kind
                        state.unlocked_weapons.add(weapon_idx)
                        state.ammo[weapon_idx] = state.ammo.get(weapon_idx, 0) + 10
                        audio.play('pickup_weapon')
                    else:
                        state.unlocked_weapons.add(kind)
                        state.ammo[kind] = state.ammo.get(kind, 0) + PICKUP_AMMO[kind]
                        audio.play('pickup_weapon')
                    pk[3] = PICKUP_RESPAWN

            for bp in list(state.blood_particles):
                bp[4] -= dt
                if bp[4] <= 0:
                    state.blood_splats.append((bp[0], bp[1], bp[5],
                                               (random.randint(110,160), 0, 0)))
                    state.blood_particles.remove(bp); continue
                bp[0] += bp[2]*dt; bp[1] += bp[3]*dt
                bp[2] *= 0.92; bp[3] *= 0.92

        # ── Rendern ──────────────────────────────────────────
        icam = (int(state.cam[0]), int(state.cam[1]))
        draw_world_bg(screen, icam)
        
        # Viewport für Culling - etwas größer als Screen für Objekte am Rand
        view = pygame.Rect(icam[0]-40, icam[1]-40, W+80, H+80)
        
        # Blood splats (bereits optimiert mit Koordinaten-Check)
        for bs in state.blood_splats:
            sx, sy = int(bs[0]-icam[0]), int(bs[1]-icam[1])
            if -20 < sx < W+20 and -20 < sy < H+20:
                pygame.draw.circle(screen, bs[3], (sx, sy), bs[2])
        
        # Pickups (mit Viewport Culling)
        for pk in state.pickups:
            if pk[3] > 0:
                continue
            # Schnell prüfen ob im Viewport
            if not view.collidepoint(pk[0], pk[1]):
                continue
            sx, sy = int(pk[0] - icam[0]), int(pk[1] - icam[1])
            if -40 < sx < W+40 and -40 < sy < H+40:
                icon = get_pickup_icon(pk[2])
                screen.blit(icon, (sx - 18, sy - 18))
        
        # Corpses (mit Viewport Culling)
        for cs, cx, cy, ca in state.corpses:
            if view.collidepoint(cx, cy):
                rot = pygame.transform.rotate(cs, -ca)
                r = rot.get_rect(center=(cx - icam[0], cy - icam[1]))
                screen.blit(rot, r)
        
        # Buildings (bereits mit view.colliderect optimiert)
        for rect, surf in state.buildings:
            if surf is None: continue
            if view.colliderect(rect):
                screen.blit(surf, (rect.x - icam[0], rect.y - icam[1]))
        
        draw_service_markers(screen, state, icam, FONT)
        
        # Wrecks (mit Viewport Culling)
        for ws, wx, wy, wa, wd in state.wrecks:
            if view.collidepoint(wx, wy):
                rot = pygame.transform.rotate(ws, -wa)
                r = rot.get_rect(center=(wx - icam[0], wy - icam[1]))
                screen.blit(rot, r)
                rad = math.radians(wa); cs_, sn_ = math.cos(rad), math.sin(rad)
                for dent in wd:
                    if len(dent) == 3:
                        dx_, dy_, dr_ = dent
                    else:
                        dx_, dy_, dr_ = dent[0], dent[1], max(3, int(dent[2] * 0.7))
                    wxr = dx_ * cs_ - dy_ * sn_
                    wyr = dx_ * sn_ + dy_ * cs_
                    pygame.draw.circle(screen, (10,10,12),
                                       (int(wx + wxr - icam[0]), int(wy + wyr - icam[1])), dr_)
        
        # Entities mit Viewport Culling - nur zeichnen wenn in Viewport
        # Autos
        for c in state.cars:
            if view.collidepoint(c.x, c.y):
                c.draw(screen, icam)
        
        # Roadblocks
        for roadblock in state.roadblocks:
            if hasattr(roadblock, 'x') and hasattr(roadblock, 'y'):
                if view.collidepoint(roadblock.x, roadblock.y):
                    roadblock.draw(screen, icam)
            else:
                roadblock.draw(screen, icam)
        
        # Peds
        for p in state.peds:
            if view.collidepoint(p.x, p.y):
                p.draw(screen, icam)
        
        # Cats
        for cat in state.cats:
            if view.collidepoint(cat.x, cat.y):
                cat.draw(screen, icam)
        
        # Cops
        for c in state.cops:
            if view.collidepoint(c.x, c.y):
                c.draw(screen, icam)
        # Player (immer zeichnen wenn nicht in Car)
        if not state.in_car:
            player.draw(screen, icam)
        
        # Lightsaber swings (immer am Player-Position, also prüfen)
        for sw in state.lightsaber_swings:
            sx, sy = int(player.x - icam[0]), int(player.y - icam[1])
            # Nur zeichnen wenn Player im Viewport
            if -50 < sx < W+50 and -50 < sy < H+50:
                t = max(0.0, min(1.0, sw[1] / sw[2]))
                center = sw[0]
                blade_ang = math.radians(center - 42 + 84 * t)
                base_x = sx + math.sin(math.radians(center)) * 16
                base_y = sy - math.cos(math.radians(center)) * 16
                tip_x = sx + math.sin(blade_ang) * 58
                tip_y = sy - math.cos(blade_ang) * 58
                start_ang = center - 42 + 84 * max(0.0, t - 0.42)
                end_ang = center - 42 + 84 * t
                outer = []
                inner = []
                for i in range(10):
                    a = math.radians(start_ang + (end_ang - start_ang) * (i / 9))
                    outer.append((int(sx + math.sin(a) * 58), int(sy - math.cos(a) * 58)))
                    inner.append((int(sx + math.sin(a) * 18), int(sy - math.cos(a) * 18)))
                trail = outer + list(reversed(inner))
                pygame.draw.polygon(screen, (30, 205, 255), trail)
                pygame.draw.lines(screen, (140, 245, 255), False, outer, 3)
                pygame.draw.line(screen, (120, 245, 255), (base_x, base_y), (tip_x, tip_y), 5)
                pygame.draw.line(screen, (250, 255, 255), (base_x, base_y), (tip_x, tip_y), 2)
        
        # Blood particles (mit Viewport Culling)
        for bp in state.blood_particles:
            sx = int(bp[0] - icam[0])
            sy = int(bp[1] - icam[1])
            if -10 < sx < W+10 and -10 < sy < H+10:
                pygame.draw.circle(screen, (180, 0, 0), (sx, sy), bp[5])
        
        # Bullets (mit Viewport Culling)
        for b in state.bullets:
            sx = int(b[0] - icam[0])
            sy = int(b[1] - icam[1])
            if -10 < sx < W+10 and -10 < sy < H+10:
                pygame.draw.circle(screen, (255,230,80), (sx, sy), 3)
        
        # Rockets (mit Viewport Culling)
        for r in state.rockets:
            sx = int(r[0] - icam[0])
            sy = int(r[1] - icam[1])
            if -20 < sx < W+20 and -20 < sy < H+20:
                ang_r = math.degrees(math.atan2(r[2], -r[3]))
                rsurf = pygame.Surface((18, 8), pygame.SRCALPHA)
                pygame.draw.ellipse(rsurf, (255,140,30), (0,0,18,8))
                pygame.draw.ellipse(rsurf, (255,240,100), (0,1,10,6))
                rot = pygame.transform.rotate(rsurf, -ang_r)
                screen.blit(rot, rot.get_rect(center=(sx, sy)))
        # =========================================================================
        # PARTIKEL BATCHING: Alle Partikel in eine Surface rendern,
        # dann 1x blitten statt viele einzelne Draw-Calls
        # =========================================================================
        
        # Fire + Smoke + Explosions in eine Batch-Surface
        # Nur wenn Partikel im Viewport sind
        has_particles = (len(state.fire_particles) + len(state.smoke_particles) + len(state.explosions)) > 0
        if has_particles:
            particle_batch = pygame.Surface((W, H), pygame.SRCALPHA)
            
            # Fire particles
            for fp in state.fire_particles:
                sx = int(fp[0] - icam[0])
                sy = int(fp[1] - icam[1])
                if -20 < sx < W+20 and -20 < sy < H+20:
                    t = max(0.0, fp[4] / fp[5])
                    col = (255, int(80 + 175 * t), int(40 * t))
                    r = max(1, int(fp[6] * (0.5 + 0.5*t)))
                    pygame.draw.circle(particle_batch, col, (sx, sy), r)
            
            # Smoke particles
            for sp_ in state.smoke_particles:
                sx = int(sp_[0] - icam[0])
                sy = int(sp_[1] - icam[1])
                r_part = max(1, int(sp_[6] * (1.4 - 0.4 * (sp_[4] / sp_[5]))))
                if -30 - r_part < sx < W+30 + r_part and -30 - r_part < sy < H+30 + r_part:
                    t = max(0.0, sp_[4] / sp_[5])
                    gv = int(60 + 110 * (1 - t))
                    alpha = int(200 * t)
                    r = max(1, int(sp_[6] * (1.4 - 0.4*t)))
                    # Smoke in Batch-Surface
                    if r > 0:
                        smoke_srf = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
                        pygame.draw.circle(smoke_srf, (gv, gv, gv, alpha), (r, r), r)
                        particle_batch.blit(smoke_srf, (sx - r, sy - r))
            
            # Explosions
            for ex in state.explosions:
                sx = int(ex[0] - icam[0])
                sy = int(ex[1] - icam[1])
                r = int(ex[4] * (0.3 + 0.7 * (ex[2] / ex[3])))
                if -50 - r < sx < W+50 + r and -50 - r < sy < H+50 + r:
                    t = ex[2] / ex[3]
                    r = int(ex[4] * (0.3 + 0.7*t))
                    a = int(220 * (1 - t))
                    exp_srf = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
                    pygame.draw.circle(exp_srf, (255, 200, 80, a), (r, r), r)
                    pygame.draw.circle(exp_srf, (255, 240, 180, min(255, a+30)), (r, r), int(r*0.6))
                    particle_batch.blit(exp_srf, (sx - r, sy - r))
            
            # Batch-Surface auf Screen blitten (1 Draw-Call statt viele)
            screen.blit(particle_batch, (0, 0))

        # HUD
        service = nearby_service(state)
        hud_panel = pygame.Surface((246, 236), pygame.SRCALPHA)
        hud_panel.fill((0, 0, 0, 185))
        pygame.draw.rect(hud_panel, (255, 255, 255, 45), hud_panel.get_rect(), 1, border_radius=4)
        screen.blit(hud_panel, (6, 6))

        bar_x, bar_w = 10, 226
        # HP bar
        hp_y = 11
        pygame.draw.rect(screen, (26, 10, 10), (bar_x, hp_y, bar_w, 22), border_radius=4)
        fill_w = int(bar_w * max(0.0, player.hp) / 100)
        if fill_w > 0:
            hp_col = (210, 36, 36) if player.hp > 30 else (255, 75, 20)
            pygame.draw.rect(screen, hp_col, (bar_x, hp_y, fill_w, 22), border_radius=4)
        pygame.draw.rect(screen, (100, 100, 100), (bar_x, hp_y, bar_w, 22), 1, border_radius=4)
        draw_hud_text("HP", (bar_x + 6, hp_y + 2), (255, 255, 255))
        hp_surf = FONT.render(str(int(player.hp)), 1, (255, 255, 255))
        screen.blit(hp_surf, (bar_x + bar_w - hp_surf.get_width() - 6, hp_y + 2))

        # Armor bar
        arm_y = hp_y + 28
        pygame.draw.rect(screen, (14, 14, 30), (bar_x, arm_y, bar_w, 22), border_radius=4)
        arm_fill = int(bar_w * max(0.0, player.armor) / 200)
        if arm_fill > 0:
            pygame.draw.rect(screen, (130, 155, 215), (bar_x, arm_y, arm_fill, 22), border_radius=4)
        pygame.draw.rect(screen, (90, 95, 115), (bar_x, arm_y, bar_w, 22), 1, border_radius=4)
        draw_hud_text("ARMOR", (bar_x + 6, arm_y + 2), (195, 210, 255))
        arm_surf = FONT.render(str(int(player.armor)), 1, (195, 210, 255))
        screen.blit(arm_surf, (bar_x + bar_w - arm_surf.get_width() - 6, arm_y + 2))

        # Geld
        money_y = arm_y + 25
        draw_hud_text(f"$ {player.money:,}", (bar_x + 6, money_y), (68, 228, 105))

        for wi, wname in enumerate(WPN_NAMES):
            wy = 88 + wi * 22
            selected = wi == state.weapon
            unlocked = wi in state.unlocked_weapons
            if not unlocked:
                col = (80, 80, 80)
                ammo_txt = ""
            elif wi == 0:
                col = (100, 220, 255)
                ammo_txt = "∞"
            else:
                ammo = state.ammo.get(wi, 0)
                col = (60, 220, 80) if ammo > 0 else (220, 60, 60)
                ammo_txt = str(ammo)
            prefix = f"{wi+1} "
            label = f"{prefix}{wname}" + (f"  {ammo_txt}" if ammo_txt else "")
            if selected:
                tw = FONT.size(label)[0]
                pygame.draw.rect(screen, (95, 88, 0), (8, wy - 1, tw + 6, 20))
            draw_hud_text(label, (10, wy), col)
        for i in range(player.wanted):
            draw_star(screen, W//2 - 36 + i * 20, 23, 9, (255, 200, 40))
        screen.blit(FONT.render("WASD | Maus/LMB | E Auto | F Aktion/Shop/Garage | SPACE Handbremse | P Pause | 1-6 Waffe",
                                1, (230,230,230)), (10, H-26))
        draw_minimap(screen, state, FONT)
        fps_val = int(clock.get_fps())
        draw_hud_text(f"FPS {fps_val}", (W - 236, 232), (220, 220, 220))
        if state.in_car:
            kmh = int(abs(state.in_car.spd) * 0.5)
            screen.blit(FONT.render(f"{kmh} km/h", 1, (255,255,255)), (W-140, 238))
            pygame.draw.rect(screen, (0,0,0), (W-230, 272, 220, 22))
            frac = max(0, state.in_car.hp) / state.in_car.max_hp
            col = (60,200,60) if frac > 0.6 else ((230,180,40) if frac > 0.3 else (220,40,40))
            pygame.draw.rect(screen, col, (W-228, 274, 216*frac, 18))
            car_label = getattr(state.in_car, "label", "Auto")
            label = "BRENNT!" if state.in_car.burning else f"{car_label} {int(state.in_car.hp)}/{state.in_car.max_hp}"
            screen.blit(FONT.render(label, 1, (255,255,255)), (W-225, 274))
        draw_hint(screen, state, service, FONT)
        if not state.in_car or (state.in_car and state.in_car.kind == "motorcycle"):
            mx, my = pygame.mouse.get_pos()
            pygame.draw.circle(screen, (255,255,255), (mx,my), 8, 1)
            pygame.draw.line(screen, (255,255,255), (mx-12,my), (mx+12,my), 1)
            pygame.draw.line(screen, (255,255,255), (mx,my-12), (mx,my+12), 1)

        if state.game_over:
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 185))
            screen.blit(overlay, (0, 0))
            t = BIG.render("GAME OVER", 1, (240, 60, 60))
            screen.blit(t, (W//2 - t.get_width()//2, 30))
            hdr = MED.render("── Highscores ──", 1, (255, 210, 40))
            screen.blit(hdr, (W//2 - hdr.get_width()//2, 130))
            for i, entry in enumerate(state.final_scores[:10]):
                is_me = (entry.get("_just_added"))
                col = (255, 230, 80) if is_me else ((255,255,255) if i < 3 else (190,190,190))
                rank_sym = ["1.", "2.", "3."][i] if i < 3 else f"{i+1}."
                line = f"{rank_sym:<4} {entry['name']:<18} ${entry['money']:>8}"
                lt = FONT.render(line, 1, col)
                screen.blit(lt, (W//2 - lt.get_width()//2, 175 + i * 30))
            t2 = FONT.render("[LEERTASTE] Neu starten   [ESC] Beenden", 1, (200, 200, 200))
            screen.blit(t2, (W//2 - t2.get_width()//2, H - 50))
        else:
            draw_overlay_menu(screen, state, BIG, MED, FONT)

        if state.menu in ("pause", "options"):
            menu_ctrl.draw(screen, BIG, MED, FONT, state)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
