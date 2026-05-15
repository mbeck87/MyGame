"""Einstiegspunkt: pygame init, Welt aufbauen, Hauptschleife starten."""
import math
import os
import random
import sys
import time

import pygame

from game2d.config import (
    W, H,
    WPN_NAMES, WPN_AUTO,
    PICKUP_AMMO, PICKUP_RESPAWN,
)
from game2d.persistence import name_input_screen
from game2d.render.hud import draw_hud_text, draw_star
from game2d.render.menus import draw_hint, draw_overlay_menu, draw_service_markers
from game2d.render.sprites import make_ped_frames, make_swim_frames, get_pickup_icon
from game2d.render.world_bg import draw_world_bg
from game2d.state import GameState, init as state_init, current
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
from game2d.systems.pooling import (
    init_pools, reset_pools,
    acquire_bullet, release_bullet, release_all_bullets,
    acquire_blood_particle, release_blood_particle, release_all_blood_particles,
    release_smoke_particle, release_all_smoke_particles,
    release_fire_particle, release_all_fire_particles,
    release_rocket, release_all_rockets,
)
from game2d.systems.spatial import (
    init_spatial_grid, reset_spatial_grid,
    register_entity, update_entity_position, unregister_entity,
    query_entities_radius, query_buildings_radius,
)
from game2d.systems.events import (
    emit_wanted_changed, emit_pickup_collected, emit_player_damaged,
    emit_entity_spawned,
)
from game2d.systems.profiling import profiler, timed, profile
from game2d.systems.di import provider
from game2d.systems.logging import get_logger, LogLevel
logger = get_logger('main')
# Basis-Logger für alle Warnings/Errors (immer aktiv)
base_logger = get_logger('base')
base_logger.set_level(LogLevel.WARNING)  # Warnings/Errors immer sichtbar
# Gruppen-Logger für INFO-Meldungen (nur mit --log Flag aktiv)
perf_logger = get_logger('performance')
event_logger = get_logger('events')
move_logger = get_logger('movement')
# Haupt-Logger und Gruppen-Logger standardmäßig deaktiviert (nur Basis-Logger aktiv)
logger.set_level(LogLevel.CRITICAL)
perf_logger.set_level(LogLevel.CRITICAL)
event_logger.set_level(LogLevel.CRITICAL)
move_logger.set_level(LogLevel.CRITICAL)
from game2d import settings as settings_mod
from game2d.ui.menu import MenuController

# Profiler UI - nur alle 500ms aktualisieren
_profiler_last_update = 0
_profiler_display = {}


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
    NUM_START_CARS = 50
    NUM_START_PEDS = 100
    NUM_AMUSEMENT_PEDS = 15

    for _ in range(NUM_START_CARS):
        kind = random_car_kind()
        x, y, angle = road_spawn(kind)
        car = Car(x, y, random_car_color(kind), kind=kind)
        car.angle = angle
        car.driver = True
        state.cars.append(car)
        register_entity(car)  # Spatial Grid Registrierung
        emit_entity_spawned(car, "car")

    player_x, player_y = safe_spawn()
    player = Ped(player_x, player_y)
    player.shirt = (40, 100, 200)
    register_entity(player)  # Spatial Grid Registrierung
    emit_entity_spawned(player, "player")
    player.gender = "m"
    player.hair_style = "short"
    player.hair_color = (30, 20, 15)
    player.frames = make_ped_frames(
        player.shirt, hair=player.hair_color, gender=player.gender, hair_style=player.hair_style
    )
    player.back_frames = make_ped_frames(
        player.shirt, hair=player.hair_color, gender=player.gender,
        hair_style=player.hair_style, back=True
    )
    player.swim_frames = make_swim_frames(
        player.shirt, hair=player.hair_color, gender=player.gender,
        hair_style=player.hair_style
    )
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

    for _ in range(NUM_START_PEDS):
        x, y = pedestrian_spawn(outside_view=True)
        ped = Ped(x, y)
        state.peds.append(ped)
        register_entity(ped)  # Spatial Grid Registrierung
        emit_entity_spawned(ped, "ped")

    # Katze spawnen (max 1, bevorzugt im Park, nie im Wasser)
    park = state.parks[0] if state.parks else None
    cx, cy = pedestrian_spawn(outside_view=True)   # sicherer Fallback
    if park:
        margin = 60
        for _ in range(40):
            px = random.randint(park.left + margin, park.right - margin)
            py = random.randint(park.top + margin, park.bottom - margin)
            if in_city(px, py, 20):
                cx, cy = px, py
                break
    cat = Cat(cx, cy)
    state.cats.append(cat)
    register_entity(cat)  # Spatial Grid Registrierung
    emit_entity_spawned(cat, "cat")

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

    # Spawn Amusement Park Peds
    amusement_nodes = list(state.amusement_park_nodes)
    num_amusement_peds = NUM_AMUSEMENT_PEDS
    if not amusement_nodes:
        # Fallback: try regular pedestrian nodes if no amusement nodes
        amusement_nodes = list(range(len(state.pedestrian_nodes)))
        num_amusement_peds = min(5, NUM_AMUSEMENT_PEDS)  # Reduce count as fallback
    for _ in range(num_amusement_peds):
        if not amusement_nodes:
            break
        x, y = state.pedestrian_nodes[random.choice(amusement_nodes)]
        ped = Ped(x + random.uniform(-10, 10), y + random.uniform(-10, 10))
        ped.route_replan = random.uniform(2.5, 5.5)  # Same as regular peds - reduced from 0.1-1.0
        ped.is_amusement = True  # Mark for simplified AI in background
        state.peds.append(ped)
        register_entity(ped)  # Spatial Grid Registrierung
        emit_entity_spawned(ped, "ped")


def _spawn_ped_replacement(state, player):
    """Spawn einen Ersatz-Passanten mit Mindestabstand zum Spieler."""
    min_dist = 500
    for _ in range(30):
        nx, ny = pedestrian_spawn()
        dist = math.hypot(nx - player.x, ny - player.y)
        if dist >= min_dist:
            break
    ped = Ped(nx, ny)
    state.peds.append(ped)
    register_entity(ped)
    emit_entity_spawned(ped, "ped")


def reset_game(state):
    # Zurücksetzen der Object Pools
    reset_pools()
    init_pools()  # Re-initialize pools after reset
    # Zurücksetzen des Spatial Grids
    reset_spatial_grid()
    # Zurücksetzen und neuaufbauen des Building Grids
    from game2d.systems.spatial import reset_building_grid, init_and_populate_building_grid, reset_park_grid, init_and_populate_park_grid
    reset_building_grid()
    init_and_populate_building_grid(state.buildings)
    # Neuaufbauen des Park Grids
    reset_park_grid()
    all_parks = list(state.parks) + list(state.amusement_parks)
    init_and_populate_park_grid(all_parks)
    # Zurücksetzen des EventBus
    from game2d.systems.events import EventBus as _EventBus
    _EventBus.reset()
    # Zurücksetzen des Profilers
    from game2d.systems.profiling import profiler
    profiler.clear()
    profiler.enabled = False
    # Re-install State im DI-Provider
    from game2d.systems.di import provider
    provider.install(state)
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
    release_all_bullets(state.bullets)
    state.bullets.clear()
    release_all_rockets(state.rockets)
    state.rockets.clear()
    state.blood_splats.clear()
    release_all_blood_particles(state.blood_particles)
    state.blood_particles.clear()
    release_all_smoke_particles(state.smoke_particles)
    state.smoke_particles.clear()
    release_all_fire_particles(state.fire_particles)
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
    state.traffic_time = 0.0
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


@profile
def _handle_events(state, menu_ctrl, dt):
    player = state.player
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            state.running = False
            continue
        # Profiling Toggle mit F12
        if e.type == pygame.KEYDOWN and e.key == pygame.K_F12 and not state.game_over:
            from game2d.systems.profiling import profiler
            profiler.enabled = not profiler.enabled
            perf_logger.info(f"[PROFILING] {'AKTIVIERT' if profiler.enabled else 'DEAKTIVIERT'}")
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
                                ex, ey = exit_car_position(c)
                                ejected = Ped(ex, ey)
                                ejected.state = 'flee'
                                state.peds.append(ejected)
                                register_entity(ejected)  # Spatial Grid Registrierung
                                emit_entity_spawned(ejected, "ped")
                            state.in_car = c
                            c.driver = player
                            c.signal_dir = 0
                            audio.play('door_open', pos=(c.x, c.y))
                            break
            if e.key == pygame.K_f and not state.in_car and not state.game_over:
                for p in state.peds:
                    dx = p.x - player.x
                    dy = p.y - player.y
                    if dx * dx + dy * dy < 1225:  # 35^2 = 1225
                        add_money(player, random.randint(15, 50))
                        p.state = 'flee'
                        add_wanted_heat(state, "robbery")
                        audio.play('robbery', pos=(p.x, p.y))
                        break
        if (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and
                not state.game_over and not state.paused and not state.menu):
            on_motorcycle = state.in_car and state.in_car.kind == "motorcycle"
            if state.fire_cd <= 0 and not WPN_AUTO[state.weapon] and (not state.in_car or on_motorcycle):
                if on_motorcycle:
                    player.aim_angle = aim_to_mouse()
                fire()


@profile
def _update_player_and_wanted(state, dt):
    player = state.player
    keys = pygame.key.get_pressed()
    state.fire_cd = max(0, state.fire_cd - dt)
    state.bank_robbery_cooldown = max(0.0, state.bank_robbery_cooldown - dt)
    if state.in_car:
        accel = (1 if keys[pygame.K_w] else 0) - (1 if keys[pygame.K_s] else 0)
        steer = (1 if keys[pygame.K_d] else 0) - (1 if keys[pygame.K_a] else 0)
        handbrake = bool(keys[pygame.K_SPACE])
        state.in_car.update(dt, accel, steer, handbrake=handbrake)
        update_entity_position(state.in_car)  # Spatial Grid Position update
        if state.in_car and not state.in_car.dead:
            player.x, player.y = state.in_car.x, state.in_car.y
            update_entity_position(player)  # Spatial Grid Position update
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
            mvx = dx / n * sp * dt
            mvy = dy / n * sp * dt
            solid_cars = [c for c in state.cars if not c.dead and not getattr(c, 'sunk', False)]

            def _blocked(rx, ry):
                pr = pygame.Rect(rx - 10, ry - 10, 20, 20)
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
            update_entity_position(player)  # Spatial Grid Position update
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
                a = random.uniform(0, 6.28)
                sp_ = random.uniform(40, 180)
                state.blood_particles.append(acquire_blood_particle(
                    player.x, player.y,
                    math.cos(a) * sp_, math.sin(a) * sp_,
                    random.uniform(0.3, 0.7), random.randint(2, 4)
                ))
            trigger_game_over()
    prev_duck_pos = state.duck_easter_last_pos
    duck_moved = 999.0 if prev_duck_pos is None else math.hypot(
        player.x - prev_duck_pos[0], player.y - prev_duck_pos[1]
    )
    _update_duck_easter(state, dt, duck_moved)
    state.duck_easter_last_pos = (player.x, player.y)
    tx = (state.in_car.x if state.in_car else player.x) - W // 2
    ty = (state.in_car.y if state.in_car else player.y) - H // 2
    state.cam[0] += (tx - state.cam[0]) * min(1, 6 * dt)
    state.cam[1] += (ty - state.cam[1]) * min(1, 6 * dt)
    if player.wanted > 0:
        player.crime_timer -= dt
        if player.crime_timer <= 0:
            old_wanted = player.wanted
            player.wanted = max(0, player.wanted - 1)
            emit_wanted_changed(state, old_wanted, player.wanted)
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
                    unregister_entity(cop)
                    if cop in state.cops:
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
                unregister_entity(car)
                if car in state.cars:
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
            state.cop_spawn = max(1.2, 8 - player.wanted * 1.35)
            spawn = cop_car_spawn_near(player.x, player.y, state.cam, law_kind)
            if spawn is not None:
                cx, cy, angle = spawn
                car = Car(cx, cy, law_color_for_kind(law_kind), is_cop=True, kind=law_kind)
                car.angle = angle
                car.max_spd += max(0, player.wanted - 3) * 30
                state.cars.append(car)
                register_entity(car)  # Spatial Grid Registrierung
                emit_entity_spawned(car, "cop_car")
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
                if c in state.cars:
                    state.cars.remove(c)


def _is_in_update_range(entity, cam_x, cam_y, update_range):
    """Check if entity is within the update range of the camera viewport.
    
    Args:
        entity: Object with x, y attributes
        cam_x: Camera x position
        cam_y: Camera y position  
        update_range: Distance from viewport edge to include (buffer)
        
    Returns:
        True if entity should be fully updated
    """
    # Viewport boundaries with buffer
    min_x = cam_x - update_range
    max_x = cam_x + W + update_range
    min_y = cam_y - update_range
    max_y = cam_y + H + update_range
    
    return (min_x <= entity.x <= max_x and 
            min_y <= entity.y <= max_y)


def _background_move_entity(entity, dt):
    """Simple position update for background entities: movement + building collision + road constraints.
    
    This keeps the world alive outside the viewport without expensive AI.
    Uses fast approximate road checks instead of full rect_on_road() for performance.
    """
    from game2d.systems.spatial import query_buildings_radius
    from game2d.config import ROAD_W, ROAD_LO, ROAD_HI_X, ROAD_HI_Y
    
    if isinstance(entity, Car):
        if entity.dead or entity.sunk or entity.driver is None:
            return
        # Move with current velocity
        rad = math.radians(entity.angle)
        new_x = entity.x + entity.spd * math.cos(rad) * dt
        new_y = entity.y + entity.spd * math.sin(rad) * dt
        
        # Fast approximate road check: check distance to nearest road center
        # Horizontal roads are at y positions, vertical at x positions
        # Get state for road data access
        s = current()
        half_road = ROAD_W // 2 + 15  # margin
        
        # Check if near any horizontal or vertical road
        nearest_v = min(s.roads_v, key=lambda rx: abs(rx - new_x)) if s.roads_v else new_x
        nearest_h = min(s.roads_h, key=lambda ry: abs(ry - new_y)) if s.roads_h else new_y
        on_road = (abs(new_x - nearest_v) < half_road or abs(new_y - nearest_h) < half_road)
        # Also check we're within road bounds
        on_road = on_road and (ROAD_LO - 20 <= new_x <= ROAD_HI_X + 20) and (ROAD_LO - 20 <= new_y <= ROAD_HI_Y + 20)
        
        # Check building collision using spatial grid
        test_rect = pygame.Rect(new_x - 20, new_y - 20, 40, 40)
        nearby_buildings = query_buildings_radius(new_x, new_y, 25)
        building_collision = False
        for b_rect in nearby_buildings:
            if test_rect.colliderect(b_rect):
                building_collision = True
                break
        
        if not building_collision and on_road:
            entity.x, entity.y = new_x, new_y
            # Decay speed slightly to avoid infinite movement
            entity.spd *= max(0, 1 - 0.3 * dt)
        else:
            # If hitting building or not on road, move towards nearest road center
            nearest_v = min(s.roads_v, key=lambda rx: abs(rx - entity.x)) if s.roads_v else entity.x
            nearest_h = min(s.roads_h, key=lambda ry: abs(ry - entity.y)) if s.roads_h else entity.y
            # Determine which direction to move based on angle
            heading = int(round(entity.angle / 90.0)) * 90 % 360
            if heading in (0, 180):
                # Moving horizontally - align to vertical road
                target_x = nearest_v + (28 if heading == 0 else -28)
                target_y = entity.y
            else:
                # Moving vertically - align to horizontal road  
                target_x = entity.x
                target_y = nearest_h + (28 if heading == 90 else -28)
            dx = target_x - entity.x
            dy = target_y - entity.y
            dist = math.hypot(dx, dy)
            if dist > 1:
                step = min(dist, abs(entity.spd) * dt * 0.5)
                entity.x += dx / dist * step
                entity.y += dy / dist * step
            entity.spd *= max(0, 1 - 0.5 * dt)
    
    elif isinstance(entity, Ped):
        # Do not let freshly spawned offscreen pedestrians drift with their
        # random initial angle. If they already have a route, keep them on it.
        if entity.is_cop or not entity.route:
            return
        node_idx = entity.route[0]
        tx, ty = current().pedestrian_nodes[node_idx]
        dx, dy = tx - entity.x, ty - entity.y
        dist = math.hypot(dx, dy) or 1
        step = entity.spd * 0.55 * dt
        entity.angle = math.degrees(math.atan2(dx, -dy))
        if dist <= step + 2:
            entity.x, entity.y = tx, ty
            entity.current_node = node_idx
            entity.route.pop(0)
        else:
            nx = entity.x + dx / dist * step
            ny = entity.y + dy / dist * step
            entity.try_follow_route(nx, ny, allow_park=True)

    elif isinstance(entity, Cat):
        # Cats keep their cheap background wander, but use the same angle basis
        # as pedestrian sprites: 0 degrees is north, 90 degrees is east.
        spd = getattr(entity, 'spd', 50)
        angle_rad = math.radians(getattr(entity, 'angle', 0))
        new_x = entity.x + spd * math.sin(angle_rad) * dt
        new_y = entity.y - spd * math.cos(angle_rad) * dt
        # Check building collision
        test_rect = pygame.Rect(new_x - 10, new_y - 10, 20, 20)
        nearby_buildings = query_buildings_radius(new_x, new_y, 25)
        collision = False
        for b_rect in nearby_buildings:
            if test_rect.colliderect(b_rect):
                collision = True
                break
        if not collision:
            entity.x, entity.y = new_x, new_y


# Update range buffer in world units (pixels) - scales with resolution
UPDATE_RANGE_BUFFER = max(300, W // 4)
# Background update range - entities beyond this only get simple movement (no building collision)
BACKGROUND_RANGE = UPDATE_RANGE_BUFFER * 2


def _capture_state_snapshot(state):
    """Erstellt einen Snapshot des aktuellen Zustands für Interpolation.
    
    Speichert nur Positionen und Winkel (keine komplexen Datenstrukturen).
    Rückgabe: dict mit Tuples für schnellen Zugriff.
    Optimiert für Performance - keine Dicts, nur Tuples.
    """
    # Player: (x, y, angle)
    p = state.player
    player_in_car = state.in_car is not None
    
    # Player Car: (x, y, angle) oder None
    if state.in_car:
        c = state.in_car
        player_car_snap = (c.x, c.y, c.angle)
    else:
        player_car_snap = None
    
    # Schnellere Version: nutze List Comprehensions mit Tuples
    # Cars: Liste von (entity, x, y, angle)
    cars_snap = [(c, c.x, c.y, c.angle) for c in state.cars if c is not state.in_car]
    
    # Peds: Liste von (entity, x, y, angle)
    peds_snap = [(p, p.x, p.y, p.angle) for p in state.peds]
    
    # Cats: Liste von (entity, x, y, angle)
    cats_snap = [(cat, cat.x, cat.y, cat.angle) for cat in state.cats]
    
    # Cops: Liste von (entity, x, y, angle)
    cops_snap = [(c, c.x, c.y, c.angle) for c in state.cops]
    
    # Bullets: Liste von (x, y)
    bullets_snap = [(b[0], b[1]) for b in state.bullets]
    
    # Rockets: Liste von (x, y)
    rockets_snap = [(r[0], r[1]) for r in state.rockets]
    
    # Camera: (x, y)
    cam_snap = (state.cam[0], state.cam[1])
    
    return {
        'player': (p.x, p.y, p.angle, player_in_car),
        'player_car': player_car_snap,
        'cars': cars_snap,
        'peds': peds_snap,
        'cats': cats_snap,
        'cops': cops_snap,
        'bullets': bullets_snap,
        'rockets': rockets_snap,
        'cam': cam_snap,
    }


@profile
def _update_entities_and_physics(state, dt):
    player = state.player
    state.intersection_claims.clear()
    
    # Calculate camera viewport for culling
    cam_x, cam_y = state.cam[0], state.cam[1]
    
    # Update Cars
    for c in state.cars:
        if c is state.in_car:
            continue
        if c in state.roadblocks:
            continue
        in_full_range = _is_in_update_range(c, cam_x, cam_y, UPDATE_RANGE_BUFFER)
        if in_full_range:
            # Full update: AI + everything
            c.ai_update(dt)
        else:
            # Background update: simple movement + building collision
            _background_move_entity(c, dt)
        update_entity_position(c)  # Spatial Grid Position update
    
    player.animate(dt)
    
    # Update Peds
    for p in state.peds:
        in_full_range = _is_in_update_range(p, cam_x, cam_y, UPDATE_RANGE_BUFFER)
        if in_full_range:
            p.update(dt, player)
            p.animate(dt)
        else:
            _background_move_entity(p, dt)
        update_entity_position(p)  # Spatial Grid Position update
    
    # Update Cats
    for cat in state.cats:
        in_full_range = _is_in_update_range(cat, cam_x, cam_y, UPDATE_RANGE_BUFFER)
        if in_full_range:
            cat.update(dt, player)
            cat.animate(dt)
        else:
            _background_move_entity(cat, dt)
        update_entity_position(cat)  # Spatial Grid Position update
    
    # Update Cops - full update in range, simplified background movement
    for c in list(state.cops):
        in_full_range = _is_in_update_range(c, cam_x, cam_y, UPDATE_RANGE_BUFFER)
        if in_full_range:
            wants_shoot = c.update(dt, player)
            c.animate(dt)
        else:
            _background_move_entity(c, dt)  # Simplified movement for background cops
        update_entity_position(c)  # Spatial Grid Position update
        if in_full_range and wants_shoot:
            profile = cop_weapon_profile(getattr(c, "cop_kind", "cop"), player.wanted)
            c.shoot_tick = profile["rate"]
            dx, dy = player.x - c.x, player.y - c.y
            base = math.atan2(dy, dx)
            spread = random.uniform(-profile["spread"], profile["spread"])
            vx = math.cos(base + spread) * profile["speed"]
            vy = math.sin(base + spread) * profile["speed"]
            state.bullets.append(acquire_bullet(c.x, c.y, vx, vy, 0.8, True, profile["damage"]))
            audio.play(profile["sound"], pos=(c.x, c.y))
    for b in list(state.bullets):
        b[0] += b[2] * dt
        b[1] += b[3] * dt
        b[4] -= dt
        if b[4] <= 0:
            release_bullet(b)
            state.bullets.remove(b)
            continue
        br = pygame.Rect(b[0] - 3, b[1] - 3, 6, 6)
        bx, by = b[0], b[1]
        bullet_hit_building = False
        # Use spatial grid for optimized building collision
        nearby_buildings = query_buildings_radius(bx, by, 50)
        for bd_rect in nearby_buildings:
            if br.colliderect(bd_rect):
                bullet_hit_building = True
                break
        if bullet_hit_building:
            state.bullets.remove(b)
            continue
        if b[5]:
            # Cop bullet - check player and player car
            if state.in_car:
                car_rect = state.in_car.rect()
                if abs(car_rect.centerx - bx) < 30 and abs(car_rect.centery - by) < 30 and br.colliderect(car_rect):
                    state.in_car.take_damage(b[6] * 0.6, world_pos=(b[0], b[1]))
                    audio.play('hit_metal', volume=0.6, pos=(b[0], b[1]))
                    state.bullets.remove(b)
                    continue
            player_rect = player.rect()
            if (abs(player_rect.centerx - bx) < 30 and
                    abs(player_rect.centery - by) < 30 and br.colliderect(player_rect)):
                damage = b[6]
                if player.armor > 0:
                    armor_dmg = min(player.armor, damage)
                    player.armor -= armor_dmg
                    damage -= armor_dmg
                player.hp -= damage
                emit_player_damaged(state, damage, source=b)
                spawn_blood(player.x, player.y, 6)
                audio.play('hurt', pos=(player.x, player.y))
                release_bullet(b)
                state.bullets.remove(b)
                if player.hp <= 0:
                    state.corpses.append((make_corpse(player), player.x, player.y, player.angle))
                    spawn_blood(player.x, player.y, 22)
                    trigger_game_over()
                continue
        else:
            # Player bullet - check all entities using spatial grid
            # Query radius of 50 covers all max distances (40 for cars, 30 for others)
            nearby_entities = query_entities_radius(bx, by, 50)
            for entity in nearby_entities:
                if isinstance(entity, Car):
                    if entity is state.in_car or entity.dead:
                        continue
                    if abs(entity.x - bx) > 40 or abs(entity.y - by) > 40:
                        continue
                    if br.colliderect(entity.rect()):
                        entity.take_damage(b[6] * 0.5, world_pos=(b[0], b[1]))
                        audio.play('hit_metal', volume=0.55, pos=(b[0], b[1]))
                        state.bullets.remove(b)
                        break
                elif isinstance(entity, Ped):
                    # Handle both cops and regular peds - cops first for priority
                    if abs(entity.x - bx) > 30 or abs(entity.y - by) > 30:
                        continue
                    if not br.colliderect(entity.rect()):
                        continue
                    if entity.is_cop:
                        entity.hp -= b[6]
                        spawn_blood(entity.x, entity.y, 5)
                        audio.play('hit_flesh', pos=(entity.x, entity.y))
                        audio.play('scream', pos=(entity.x, entity.y))
                        if entity.hp <= 0:
                            if entity._siren_channel is not None:
                                audio.stop_loop(entity._siren_channel)
                                entity._siren_channel = None
                            unregister_entity(entity)
                            if entity in state.cops:
                                state.cops.remove(entity)
                            state.corpses.append((make_corpse(entity), entity.x, entity.y, entity.angle))
                            spawn_blood(entity.x, entity.y, 24)
                            on_kill(state, entity, is_cop=True)
                        release_bullet(b)
                        state.bullets.remove(b)
                        break
                    else:
                        entity.hp -= b[6]
                        entity.state = 'flee'
                        spawn_blood(entity.x, entity.y, 4)
                        audio.play('hit_flesh', pos=(entity.x, entity.y))
                        audio.play('scream', pos=(entity.x, entity.y))
                        if entity.hp <= 0:
                            unregister_entity(entity)
                            if entity in state.peds:
                                state.peds.remove(entity)
                            state.corpses.append((make_corpse(entity), entity.x, entity.y, entity.angle))
                            spawn_blood(entity.x, entity.y, 20)
                            add_money(player, random.randint(15, 60))
                            on_kill(state, entity, is_cop=False)
                            _spawn_ped_replacement(state, player)
                        release_bullet(b)
                        state.bullets.remove(b)
                        break
                elif isinstance(entity, Cat):
                    if abs(entity.x - bx) > 30 or abs(entity.y - by) > 30:
                        continue
                    if br.colliderect(entity.rect()):
                        entity.hp -= b[6]
                        spawn_blood(entity.x, entity.y, 3)
                        audio.play('hit_flesh', pos=(entity.x, entity.y))
                        audio.play('scream', pos=(entity.x, entity.y))
                        if entity.hp <= 0:
                            unregister_entity(entity)
                            if entity in state.cats:
                                state.cats.remove(entity)
                            state.corpses.append((entity.sprite.copy(), entity.x, entity.y, entity.angle))
                            spawn_blood(entity.x, entity.y, 10)
                            player.wanted = 5
                            player.crime_timer = 30
                            state.wanted_heat = 5 * 100
                            add_money(player, random.randint(50, 100))
                        release_bullet(b)
                        state.bullets.remove(b)
                        break
    for c in list(state.cars):
        c.update_fx(dt)
        if c.dead:
            if c._siren_channel is not None:
                audio.stop_loop(c._siren_channel)
                c._siren_channel = None
            unregister_entity(c)
            if c in state.cars:
                state.cars.remove(c)
            if not c.is_cop:
                kind = random_car_kind()
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
                register_entity(car)  # Spatial Grid Registrierung
                emit_entity_spawned(car, "car")
    for sp_ in list(state.smoke_particles):
        sp_[4] -= dt
        if sp_[4] <= 0:
            release_smoke_particle(sp_)
            state.smoke_particles.remove(sp_)
            continue
        sp_[0] += sp_[2] * dt
        sp_[1] += sp_[3] * dt
        sp_[2] *= 0.96
        sp_[3] = sp_[3] * 0.96 - 8 * dt
    for fp in list(state.fire_particles):
        fp[4] -= dt
        if fp[4] <= 0:
            release_fire_particle(fp)
            state.fire_particles.remove(fp)
            continue
        fp[0] += fp[2] * dt
        fp[1] += fp[3] * dt
        fp[2] *= 0.90
        fp[3] *= 0.90
    for ex in list(state.explosions):
        ex[2] += dt
        if ex[2] >= ex[3]:
            state.explosions.remove(ex)
    for sw in list(state.lightsaber_swings):
        sw[1] += dt
        if sw[1] >= sw[2]:
            state.lightsaber_swings.remove(sw)
    for r in list(state.rockets):
        r[0] += r[2] * dt
        r[1] += r[3] * dt
        r[4] -= dt
        hit = r[4] <= 0
        rr = pygame.Rect(r[0] - 5, r[1] - 5, 10, 10)
        rx, ry = r[0], r[1]
        if not hit:
            # Use spatial grid for building collision
            nearby_buildings = query_buildings_radius(rx, ry, 50)
            for bd_rect in nearby_buildings:
                if rr.colliderect(bd_rect):
                    hit = True
                    break
        if not hit:
            # Use spatial grid for entity collision - radius 50 covers rocket size + entity sizes
            nearby_entities = query_entities_radius(rx, ry, 50)
            for entity in nearby_entities:
                if isinstance(entity, Car):
                    if entity is not state.in_car and not entity.dead and rr.colliderect(entity.rect()):
                        hit = True
                        break
                elif isinstance(entity, Ped):
                    # Both regular peds and cops (which are Ped instances with is_cop=True)
                    if rr.colliderect(entity.rect()):
                        hit = True
                        break
                elif isinstance(entity, Cat):
                    if rr.colliderect(entity.rect()):
                        hit = True
                        break
        if hit:
            audio.stop_loop(r[5])
            do_explosion(r[0], r[1])
            release_rocket(r)
            state.rockets.remove(r)
            add_wanted_heat(state, "explosion")
        else:
            audio.update_loop(r[5], pos=(r[0], r[1]))
    for pk in state.pickups:
        if pk[3] > 0:
            pk[3] = max(0.0, pk[3] - dt)
            continue
        dx = player.x - pk[0]
        dy = player.y - pk[1]
        if dx * dx + dy * dy < 484:  # 22^2 = 484
            kind = pk[2]
            if kind == 'hp':
                player.hp = min(100, player.hp + 30)
                audio.play('pickup_hp')
            elif kind == 'armor':
                armor_amount = random.randint(100, 200)
                player.armor = min(200, player.armor + armor_amount)
                audio.play('pickup_hp')
            elif isinstance(kind, int) and kind < 0:
                weapon_idx = -kind
                state.unlocked_weapons.add(weapon_idx)
                state.ammo[weapon_idx] = state.ammo.get(weapon_idx, 0) + 10
                audio.play('pickup_weapon')
            else:
                state.unlocked_weapons.add(kind)
                state.ammo[kind] = state.ammo.get(kind, 0) + PICKUP_AMMO[kind]
                audio.play('pickup_weapon')
            emit_pickup_collected(state, pk, kind)
            pk[3] = PICKUP_RESPAWN
    for bp in list(state.blood_particles):
        bp[4] -= dt
        if bp[4] <= 0:
            state.blood_splats.append((bp[0], bp[1], bp[5], (random.randint(110, 160), 0, 0)))
            release_blood_particle(bp)
            state.blood_particles.remove(bp)
            continue
        bp[0] += bp[2] * dt
        bp[1] += bp[3] * dt
        bp[2] *= 0.92
        bp[3] *= 0.92


def _get_interpolated_entity(snapshot_list, entity, alpha):
    """Finde eine Entity im Snapshot und gib interpolierte Position/Winkel zurück.
    
    Args:
        snapshot_list: Liste der Entity-Snapshots als (entity, x, y, angle) Tuples
        entity: Die aktuelle Entity
        alpha: Interpolationsfaktor
        
    Returns:
        (x, y, angle) oder (entity.x, entity.y, entity.angle) wenn nicht gefunden
    """
    for snap in snapshot_list:
        # snap = (entity, x, y, angle)
        if snap[0] is entity:
            x = snap[1] + (entity.x - snap[1]) * alpha
            y = snap[2] + (entity.y - snap[2]) * alpha
            angle = snap[3] + (entity.angle - snap[3]) * alpha
            return x, y, angle
    return entity.x, entity.y, entity.angle


def _get_interpolated_player(snapshot, player, alpha):
    """Gib interpolierte Player-Position zurück.
    
    Snapshot-Format: 'player': (x, y, angle, in_car)
    """
    if not snapshot or not snapshot.get('player'):
        return player.x, player.y, player.angle
    prev = snapshot['player']
    # prev = (x, y, angle, in_car)
    x = prev[0] + (player.x - prev[0]) * alpha
    y = prev[1] + (player.y - prev[1]) * alpha
    angle = prev[2] + (player.angle - prev[2]) * alpha
    return x, y, angle


def _get_interpolated_player_car(snapshot, car, alpha):
    """Gib interpolierte Player-Car-Position zurück.
    
    Snapshot-Format: 'player_car': (x, y, angle) oder None
    """
    if not snapshot or not snapshot.get('player_car'):
        return car.x, car.y, car.angle
    prev = snapshot['player_car']
    # prev = (x, y, angle)
    x = prev[0] + (car.x - prev[0]) * alpha
    y = prev[1] + (car.y - prev[1]) * alpha
    angle = prev[2] + (car.angle - prev[2]) * alpha
    return x, y, angle


def _draw_entity_interpolated(entity, screen, icam, snapshot_list, alpha):
    """Zeichne eine Entity mit interpolierter Position/Winkel.
    
    Temporär überscheibt die Entity-Position für das Zeichnen.
    """
    if alpha <= 0 or alpha >= 1 or not snapshot_list:
        entity.draw(screen, icam)
        return
    
    x, y, angle = _get_interpolated_entity(snapshot_list, entity, alpha)
    # Temporär speichern und überschreiben
    old_x, old_y, old_angle = entity.x, entity.y, entity.angle
    entity.x, entity.y, entity.angle = x, y, angle
    try:
        entity.draw(screen, icam)
    finally:
        # Immer zurücksetzen
        entity.x, entity.y, entity.angle = old_x, old_y, old_angle


def _draw_player_interpolated(player, screen, icam, snapshot, alpha):
    """Zeichne Player mit interpolierter Position/Winkel."""
    if alpha <= 0 or alpha >= 1 or not snapshot:
        player.draw(screen, icam)
        return
    
    x, y, angle = _get_interpolated_player(snapshot, player, alpha)
    old_x, old_y, old_angle = player.x, player.y, player.angle
    player.x, player.y, player.angle = x, y, angle
    try:
        player.draw(screen, icam)
    finally:
        player.x, player.y, player.angle = old_x, old_y, old_angle


def _draw_player_car_interpolated(car, screen, icam, snapshot, alpha):
    """Zeichne Player-Car mit interpolierter Position/Winkel."""
    if alpha <= 0 or alpha >= 1 or not snapshot:
        car.draw(screen, icam)
        return
    
    x, y, angle = _get_interpolated_player_car(snapshot, car, alpha)
    old_x, old_y, old_angle = car.x, car.y, car.angle
    car.x, car.y, car.angle = x, y, angle
    try:
        car.draw(screen, icam)
    finally:
        car.x, car.y, car.angle = old_x, old_y, old_angle


@profile
def _render_frame(screen, state, clock, menu_ctrl, FONT, BIG, MED, profiler_obj=None, dt=0.0, fps_val=None, minimap_static=None, minimap_dynamic=None, prev_snapshot=None, alpha=0.0, physics_fps=None):
    """Render the game frame with optional interpolation for smooth rendering.
    
    Args:
        prev_snapshot: Previous state snapshot for interpolation (or None)
        alpha: Interpolation factor between prev and current state (0 = prev, 1 = current)
        physics_fps: Physics FPS (separate from render FPS)
    """
    # Interpolierte Kamera-Position
    if prev_snapshot and alpha > 0:
        cam_x = prev_snapshot['cam'][0] + (state.cam[0] - prev_snapshot['cam'][0]) * alpha
        cam_y = prev_snapshot['cam'][1] + (state.cam[1] - prev_snapshot['cam'][1]) * alpha
        icam = (int(cam_x), int(cam_y))
    else:
        icam = (int(state.cam[0]), int(state.cam[1]))
    
    player = state.player
    draw_world_bg(screen, icam)
    view = pygame.Rect(icam[0] - 40, icam[1] - 40, W + 80, H + 80)
    for bs in state.blood_splats:
        sx, sy = int(bs[0] - icam[0]), int(bs[1] - icam[1])
        if -20 < sx < W + 20 and -20 < sy < H + 20:
            pygame.draw.circle(screen, bs[3], (sx, sy), bs[2])
    for pk in state.pickups:
        if pk[3] > 0:
            continue
        if not view.collidepoint(pk[0], pk[1]):
            continue
        sx, sy = int(pk[0] - icam[0]), int(pk[1] - icam[1])
        if -40 < sx < W + 40 and -40 < sy < H + 40:
            icon = get_pickup_icon(pk[2])
            screen.blit(icon, (sx - 18, sy - 18))
    for cs, cx, cy, ca in state.corpses:
        if view.collidepoint(cx, cy):
            rot = pygame.transform.rotate(cs, -ca)
            r = rot.get_rect(center=(cx - icam[0], cy - icam[1]))
            screen.blit(rot, r)
    # Visibility-Culling: nur sichtbare Gebäude zeichnen
    visible_buildings = [
        (rect, surf) for rect, surf in state.buildings
        if surf is not None and view.colliderect(rect)
    ]
    # Sortieren nach Y-Position für korrektes Overlap-Rendering
    visible_buildings.sort(key=lambda x: x[0].y)
    for rect, surf in visible_buildings:
        screen.blit(surf, (rect.x - icam[0], rect.y - icam[1]))
    draw_service_markers(screen, state, icam, FONT)
    for ws, wx, wy, wa, wd in state.wrecks:
        if view.collidepoint(wx, wy):
            rot = pygame.transform.rotate(ws, -wa)
            r = rot.get_rect(center=(wx - icam[0], wy - icam[1]))
            screen.blit(rot, r)
            rad = math.radians(wa)
            cs_, sn_ = math.cos(rad), math.sin(rad)
            for dent in wd:
                if len(dent) == 3:
                    dx_, dy_, dr_ = dent
                else:
                    dx_, dy_, dr_ = dent[0], dent[1], max(3, int(dent[2] * 0.7))
                wxr = dx_ * cs_ - dy_ * sn_
                wyr = dx_ * sn_ + dy_ * cs_
                pygame.draw.circle(screen, (10, 10, 12),
                                   (int(wx + wxr - icam[0]), int(wy + wyr - icam[1])), dr_)
    # Cars - mit Interpolation
    for c in state.cars:
        if view.collidepoint(c.x, c.y):
            if c is state.in_car:
                # Player Car wird separat behandelt
                if prev_snapshot and alpha > 0 and alpha < 1:
                    _draw_player_car_interpolated(c, screen, icam, prev_snapshot, alpha)
                else:
                    c.draw(screen, icam)
            else:
                if prev_snapshot and alpha > 0 and alpha < 1:
                    _draw_entity_interpolated(c, screen, icam, prev_snapshot.get('cars', []), alpha)
                else:
                    c.draw(screen, icam)
    for roadblock in state.roadblocks:
        if hasattr(roadblock, 'x') and hasattr(roadblock, 'y'):
            if view.collidepoint(roadblock.x, roadblock.y):
                roadblock.draw(screen, icam)
        else:
            roadblock.draw(screen, icam)
    # Peds - mit Interpolation
    for p in state.peds:
        if view.collidepoint(p.x, p.y):
            if prev_snapshot and alpha > 0 and alpha < 1:
                _draw_entity_interpolated(p, screen, icam, prev_snapshot.get('peds', []), alpha)
            else:
                p.draw(screen, icam)
    # Cats - mit Interpolation
    for cat in state.cats:
        if view.collidepoint(cat.x, cat.y):
            if prev_snapshot and alpha > 0 and alpha < 1:
                _draw_entity_interpolated(cat, screen, icam, prev_snapshot.get('cats', []), alpha)
            else:
                cat.draw(screen, icam)
    # Cops - mit Interpolation
    for c in state.cops:
        if view.collidepoint(c.x, c.y):
            if prev_snapshot and alpha > 0 and alpha < 1:
                _draw_entity_interpolated(c, screen, icam, prev_snapshot.get('cops', []), alpha)
            else:
                c.draw(screen, icam)
    # Player - mit Interpolation
    if not state.in_car:
        if prev_snapshot and alpha > 0 and alpha < 1:
            _draw_player_interpolated(player, screen, icam, prev_snapshot, alpha)
        else:
            player.draw(screen, icam)
    else:
        # Player im Auto - Auto wurde bereits oben gezeichnet
        pass
    
    # Interpolierte Player-Position für Lightsaber und andere Player-abhängige Effekte
    if prev_snapshot and alpha > 0 and alpha < 1:
        if state.in_car:
            # Player ist im Auto - nutze Auto-Position
            player_x, player_y, _ = _get_interpolated_player_car(prev_snapshot, state.in_car, alpha)
        else:
            player_x, player_y, _ = _get_interpolated_player(prev_snapshot, player, alpha)
    else:
        player_x, player_y = player.x, player.y
    
    for sw in state.lightsaber_swings:
        sx, sy = int(player_x - icam[0]), int(player_y - icam[1])
        if -50 < sx < W + 50 and -50 < sy < H + 50:
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
    for bp in state.blood_particles:
        sx = int(bp[0] - icam[0])
        sy = int(bp[1] - icam[1])
        if -10 < sx < W + 10 and -10 < sy < H + 10:
            pygame.draw.circle(screen, (180, 0, 0), (sx, sy), bp[5])
    # Bullets - mit Interpolation (Index-basiert)
    # Snapshot-Format: bullets = [(x, y), ...]
    bullet_snapshots = prev_snapshot.get('bullets', []) if prev_snapshot else []
    for i, b in enumerate(state.bullets):
        bx, by = b[0], b[1]
        if prev_snapshot and alpha > 0 and alpha < 1 and i < len(bullet_snapshots):
            b_snap = bullet_snapshots[i]
            bx = b_snap[0] + (bx - b_snap[0]) * alpha
            by = b_snap[1] + (by - b_snap[1]) * alpha
        sx = int(bx - icam[0])
        sy = int(by - icam[1])
        if -10 < sx < W + 10 and -10 < sy < H + 10:
            pygame.draw.circle(screen, (255, 230, 80), (sx, sy), 3)
    
    # Rockets - mit Interpolation (Index-basiert)
    # Snapshot-Format: rockets = [(x, y), ...]
    rocket_snapshots = prev_snapshot.get('rockets', []) if prev_snapshot else []
    for i, r in enumerate(state.rockets):
        rx, ry = r[0], r[1]
        if prev_snapshot and alpha > 0 and alpha < 1 and i < len(rocket_snapshots):
            r_snap = rocket_snapshots[i]
            rx = r_snap[0] + (rx - r_snap[0]) * alpha
            ry = r_snap[1] + (ry - r_snap[1]) * alpha
        sx = int(rx - icam[0])
        sy = int(ry - icam[1])
        if -20 < sx < W + 20 and -20 < sy < H + 20:
            ang_r = math.degrees(math.atan2(r[2], -r[3]))
            # Use cached rocket sprite
            from game2d.render.sprites import get_rocket_sprite
            rsurf = get_rocket_sprite()
            rot = pygame.transform.rotate(rsurf, -ang_r)
            screen.blit(rot, rot.get_rect(center=(sx, sy)))
    has_particles = (len(state.fire_particles) + len(state.smoke_particles) + len(state.explosions)) > 0
    if has_particles:
        particle_batch = pygame.Surface((W, H), pygame.SRCALPHA)
        for fp in state.fire_particles:
            sx = int(fp[0] - icam[0])
            sy = int(fp[1] - icam[1])
            if -20 < sx < W + 20 and -20 < sy < H + 20:
                t = max(0.0, fp[4] / fp[5])
                col = (255, int(80 + 175 * t), int(40 * t))
                r = max(1, int(fp[6] * (0.5 + 0.5 * t)))
                pygame.draw.circle(particle_batch, col, (sx, sy), r)
        for sp_ in state.smoke_particles:
            sx = int(sp_[0] - icam[0])
            sy = int(sp_[1] - icam[1])
            r_part = max(1, int(sp_[6] * (1.4 - 0.4 * (sp_[4] / sp_[5]))))
            if -30 - r_part < sx < W + 30 + r_part and -30 - r_part < sy < H + 30 + r_part:
                t = max(0.0, sp_[4] / sp_[5])
                gv = int(60 + 110 * (1 - t))
                alpha = int(200 * t)
                r = max(1, int(sp_[6] * (1.4 - 0.4 * t)))
                if r > 0:
                    # Draw directly on particle_batch instead of creating temp surface
                    pygame.draw.circle(particle_batch, (gv, gv, gv, alpha), (sx, sy), r)
        for ex in state.explosions:
            sx = int(ex[0] - icam[0])
            sy = int(ex[1] - icam[1])
            r = int(ex[4] * (0.3 + 0.7 * (ex[2] / ex[3])))
            if -50 - r < sx < W + 50 + r and -50 - r < sy < H + 50 + r:
                t = ex[2] / ex[3]
                r = int(ex[4] * (0.3 + 0.7 * t))
                a = int(220 * (1 - t))
                # Draw directly on particle_batch instead of creating temp surface
                pygame.draw.circle(particle_batch, (255, 200, 80, a), (sx, sy), r)
                pygame.draw.circle(particle_batch, (255, 240, 180, min(255, a + 30)), (sx, sy), int(r * 0.6))
        screen.blit(particle_batch, (0, 0))
    service = nearby_service(state)
    hud_panel = pygame.Surface((246, 236), pygame.SRCALPHA)
    hud_panel.fill((0, 0, 0, 185))
    pygame.draw.rect(hud_panel, (255, 255, 255, 45), hud_panel.get_rect(), 1, border_radius=4)
    screen.blit(hud_panel, (6, 6))
    bar_x, bar_w = 10, 226
    hp_y = 11
    pygame.draw.rect(screen, (26, 10, 10), (bar_x, hp_y, bar_w, 22), border_radius=4)
    fill_w = int(bar_w * max(0.0, player.hp) / 100)
    if fill_w > 0:
        hp_col = (210, 36, 36) if player.hp > 30 else (255, 75, 20)
        pygame.draw.rect(screen, hp_col, (bar_x, hp_y, fill_w, 22), border_radius=4)
    pygame.draw.rect(screen, (100, 100, 100), (bar_x, hp_y, bar_w, 22), 1, border_radius=4)
    draw_hud_text(screen, FONT, "HP", (bar_x + 6, hp_y + 2), (255, 255, 255))
    from game2d.render.hud import cached_render
    hp_surf = cached_render(FONT, str(int(player.hp)), (255, 255, 255))
    screen.blit(hp_surf, (bar_x + bar_w - hp_surf.get_width() - 6, hp_y + 2))
    arm_y = hp_y + 28
    pygame.draw.rect(screen, (14, 14, 30), (bar_x, arm_y, bar_w, 22), border_radius=4)
    arm_fill = int(bar_w * max(0.0, player.armor) / 200)
    if arm_fill > 0:
        pygame.draw.rect(screen, (130, 155, 215), (bar_x, arm_y, arm_fill, 22), border_radius=4)
    pygame.draw.rect(screen, (90, 95, 115), (bar_x, arm_y, bar_w, 22), 1, border_radius=4)
    draw_hud_text(screen, FONT, "ARMOR", (bar_x + 6, arm_y + 2), (195, 210, 255))
    arm_surf = cached_render(FONT, str(int(player.armor)), (195, 210, 255))
    screen.blit(arm_surf, (bar_x + bar_w - arm_surf.get_width() - 6, arm_y + 2))
    money_y = arm_y + 25
    draw_hud_text(screen, FONT, f"$ {player.money:,}", (bar_x + 6, money_y), (68, 228, 105))
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
        prefix = f"{wi + 1} "
        label = f"{prefix}{wname}" + (f"  {ammo_txt}" if ammo_txt else "")
        if selected:
            tw = FONT.size(label)[0]
            pygame.draw.rect(screen, (95, 88, 0), (8, wy - 1, tw + 6, 20))
        draw_hud_text(screen, FONT, label, (10, wy), col)
    for i in range(player.wanted):
        draw_star(screen, W // 2 - 36 + i * 20, 23, 9, (255, 200, 40))
    controls_surf = cached_render(FONT,
        "WASD | Maus/LMB | E Auto | F Aktion/Shop/Garage | SPACE Handbremse | "
        "P Pause | 1-6 Waffe | F12 Profiling",
        (230, 230, 230))
    screen.blit(controls_surf, (10, H - 26))
    # Minimap mit Cache-Panels zeichnen (optimiert: statisch einmal, dynamisch alle 3 Frames)
    from game2d.render.minimap import draw_minimap
    draw_minimap(screen, state, FONT, minimap_static, minimap_dynamic)

    # FPS und Profiling-Infos anzeigen (fps_val wird aus Hauptloop übergeben)
    if profiler_obj and profiler_obj.enabled:
        # Immer Standard-FPS anzeigen (korrekte FPS die der Spieler sieht)
        frame_time = profiler_obj.frame_time * 1000  # in ms
        avg_frame_time = profiler_obj.average_frame_time * 1000  # in ms
        memory = profiler_obj.current_memory_mb
        
        # Zeiten der drei Hauptphasen aus Profiler
        event_stats = profiler_obj.get_function_stats("handle_events")
        update_stats = profiler_obj.get_function_stats("update_logic")
        render_stats = profiler_obj.get_function_stats("render")
        
        event_time = event_stats.avg_time * 1000 if event_stats else 0
        update_time = update_stats.avg_time * 1000 if update_stats else 0
        render_time = render_stats.avg_time * 1000 if render_stats else 0

        # Profiling-Anzeige mit Standard-FPS und Phasenzeiten - links neben der Minimap
        # Minimap: linker Rand bei W-236, Breite 216, also Bereich [W-236, W-20]
        # Profiling: rechter Rand bei W-236-20 = W-256 (20px Abstand links von Minimap)
        # Tabelle ist 420px breit (col3_x + 30 - col1_x = 390 + 30 = 420)
        # Also profile_x = (W-256) - 420 = W-676, dann +20px nach rechts = W-656, dann -40px nach links = W-696
        profile_x = W - 696
        
        # ===== Profiler UI - nur alle 500ms aktualisieren =====
        global _profiler_last_update, _profiler_display
        current_time = time.time()
        update_interval = 0.5  # 500ms
        
        # Sammel-Daten für Mittelwert
        if '_profiler_accum' not in _profiler_display:
            _profiler_display['_profiler_accum'] = {
                'fps_vals': [], 'phys_vals': [], 'frame_vals': [], 'mem_vals': [],
                'evt_vals': [], 'upd_vals': [], 'rnd_vals': [],
                'cars_vals': [], 'peds_vals': [], 'cops_vals': [],
                'full_cars_vals': [], 'full_peds_vals': [], 'full_cops_vals': []
            }
        accum = _profiler_display['_profiler_accum']
        
        # Aktuelle Werte sammeln
        accum['fps_vals'].append(fps_val)
        accum['phys_vals'].append(physics_fps if physics_fps else 0)
        accum['frame_vals'].append(frame_time)
        accum['mem_vals'].append(memory)
        accum['evt_vals'].append(event_time)
        accum['upd_vals'].append(update_time)
        accum['rnd_vals'].append(render_time)
        
        cam_x, cam_y = state.cam[0], state.cam[1]
        update_range = max(300, W // 4)
        full_cars = sum(1 for c in state.cars if _is_in_update_range(c, cam_x, cam_y, update_range))
        full_peds = sum(1 for p in state.peds if _is_in_update_range(p, cam_x, cam_y, update_range))
        full_cops = sum(1 for c in state.cops if _is_in_update_range(c, cam_x, cam_y, update_range))
        accum['cars_vals'].append(len(state.cars))
        accum['peds_vals'].append(len(state.peds))
        accum['cops_vals'].append(len(state.cops))
        accum['full_cars_vals'].append(full_cars)
        accum['full_peds_vals'].append(full_peds)
        accum['full_cops_vals'].append(full_cops)
        
        # Alle 500ms: Mittelwerte berechnen und Display-Werte aktualisieren
        if current_time - _profiler_last_update >= update_interval:
            def calc_avg(values):
                return sum(values) / len(values) if values else 0
            
            _profiler_display['fps'] = int(calc_avg(accum['fps_vals']))
            _profiler_display['phys'] = int(calc_avg(accum['phys_vals'])) or "N/A"
            _profiler_display['frame'] = calc_avg(accum['frame_vals'])
            _profiler_display['mem'] = calc_avg(accum['mem_vals'])
            _profiler_display['evt'] = calc_avg(accum['evt_vals'])
            _profiler_display['upd'] = calc_avg(accum['upd_vals'])
            _profiler_display['rnd'] = calc_avg(accum['rnd_vals'])
            _profiler_display['cars'] = int(calc_avg(accum['cars_vals']))
            _profiler_display['peds'] = int(calc_avg(accum['peds_vals']))
            _profiler_display['cops'] = int(calc_avg(accum['cops_vals']))
            _profiler_display['full_cars'] = int(calc_avg(accum['full_cars_vals']))
            _profiler_display['full_peds'] = int(calc_avg(accum['full_peds_vals']))
            _profiler_display['full_cops'] = int(calc_avg(accum['full_cops_vals']))
            

            # Zurücksetzen für nächste Sammelperiode
            for key in accum:
                accum[key] = []
            _profiler_last_update = current_time
        
        # Feste Schrittweiten pro Paar (basierend auf max moeglicher Textbreite)
        fps_step = FONT.render("FPS: 999", 1, (0,0,0)).get_width() + 10
        phys_step = FONT.render("Phys: 999", 1, (0,0,0)).get_width() + 10
        frame_step = FONT.render("Frame: 999.9ms", 1, (0,0,0)).get_width() + 10
        mem_step = FONT.render("Mem: 9999.9MB", 1, (0,0,0)).get_width() + 10
        time_step = FONT.render("Rnd: 999.9ms", 1, (0,0,0)).get_width() + 10
        entity_step = FONT.render("Cars: 999/999", 1, (0,0,0)).get_width() + 10
        
        # Helper: format value with padding to prevent layout shift
        def format_padded(value, min_chars):
            """Formatiert Wert mit Leerzeichen, damit die Laenge konstant bleibt."""
            return str(value).rjust(min_chars)
        
        # Zeile 1: FPS, Phys, Frame, Mem - mit Display-Werten
        x = profile_x
        phys_str = _profiler_display.get('phys', "N/A")
        draw_hud_text(screen, FONT, f"FPS: {format_padded(_profiler_display.get('fps', fps_val), 3)}", (x, 10), (220, 200, 100))
        x += fps_step
        draw_hud_text(screen, FONT, f"Phys: {format_padded(phys_str, 3)}", (x, 10), (220, 200, 100))
        x += phys_step
        frame_avg = _profiler_display.get('frame', frame_time)
        draw_hud_text(screen, FONT, f"Frame: {format_padded(f'{frame_avg:.1f}ms', 7)}", (x, 10), (220, 200, 100))
        x += frame_step
        mem_avg = _profiler_display.get('mem', memory)
        draw_hud_text(screen, FONT, f"Mem: {format_padded(f'{mem_avg:.1f}MB', 7)}", (x, 10), (220, 200, 100))
        
        # Zeile 2: Evt, Upd, Rnd
        x = profile_x
        evt_avg = _profiler_display.get('evt', event_time)
        draw_hud_text(screen, FONT, f"Evt: {format_padded(f'{evt_avg:.1f}ms', 6)}", (x, 30), (180, 200, 100))
        x += time_step
        upd_avg = _profiler_display.get('upd', update_time)
        draw_hud_text(screen, FONT, f"Upd: {format_padded(f'{upd_avg:.1f}ms', 6)}", (x, 30), (180, 200, 100))
        x += time_step
        rnd_avg = _profiler_display.get('rnd', render_time)
        draw_hud_text(screen, FONT, f"Rnd: {format_padded(f'{rnd_avg:.1f}ms', 6)}", (x, 30), (180, 200, 100))
        
        # Zeile 3: Entity Counts (Gesamt/Full)
        x = profile_x
        cars_total = _profiler_display.get('cars', len(state.cars))
        full_cars_disp = _profiler_display.get('full_cars', full_cars)
        draw_hud_text(screen, FONT, f"Cars: {format_padded(f'{cars_total}/{full_cars_disp}', 8)}", (x, 50), (150, 180, 100))
        x += entity_step
        peds_total = _profiler_display.get('peds', len(state.peds))
        full_peds_disp = _profiler_display.get('full_peds', full_peds)
        draw_hud_text(screen, FONT, f"Peds: {format_padded(f'{peds_total}/{full_peds_disp}', 8)}", (x, 50), (150, 180, 100))
        x += entity_step
        cops_total = _profiler_display.get('cops', len(state.cops))
        full_cops_disp = _profiler_display.get('full_cops', full_cops)
        draw_hud_text(screen, FONT, f"Cops: {format_padded(f'{cops_total}/{full_cops_disp}', 8)}", (x, 50), (150, 180, 100))
        
        # Top 3 langsamste Funktionen - jede Zelle an fester Position
        if profiler_obj._function_stats:
            top_funcs = profiler_obj.get_top_functions(3, "total_time")
            if top_funcs:
                # Feste Spaltenpositionen
                col1_x = profile_x      # Function Name
                col2_x = profile_x + 240  # Avg Time (ms)
                col3_x = profile_x + 390  # Calls (150px Abstand von col2: 145px + 5px)
                
                # Tabellenkopf - jede Spalte einzeln rendern (20px nach unten verschoben)
                draw_hud_text(screen, FONT, "Function Name", (col1_x, 80), (220, 200, 100))
                draw_hud_text(screen, FONT, "Avg Time (ms)", (col2_x, 80), (220, 200, 100))
                draw_hud_text(screen, FONT, "Calls", (col3_x, 80), (220, 200, 100))
                
                # Trennlinie über alle Spalten (bei col1_x beginnend, 20px nach unten verschoben)
                line_surface = pygame.Surface((430, 1))
                line_surface.fill((180, 180, 180))
                screen.blit(line_surface, (profile_x, 98))
                
                # Funktionen - jede Zelle einzeln an ihrer Position (20px nach unten verschoben)
                for i, stat in enumerate(top_funcs):
                    y_pos = 110 + i * 20
                    
                    # Function Name (left-aligned, max 25 chars)
                    name = stat.name
                    if len(name) > 22:
                        name = name[:19] + "..."
                    draw_hud_text(screen, FONT, name, (col1_x, y_pos), (180, 180, 180))
                    
                    # Avg Time (right-aligned)
                    avg_time = stat.avg_time * 1000
                    draw_hud_text(screen, FONT, f"{avg_time:.2f}", (col2_x, y_pos), (180, 180, 180))
                    
                    # Calls (right-aligned)
                    calls = stat.call_count
                    draw_hud_text(screen, FONT, f"{calls}", (col3_x, y_pos), (180, 180, 180))

    else:
        # Standard FPS-Anzeige - zeige Render-FPS und Physik-FPS
        if physics_fps is not None:
            draw_hud_text(screen, FONT, f"FPS {fps_val} | Phys {physics_fps}", (W - 236, 232), (220, 220, 220))
        else:
            draw_hud_text(screen, FONT, f"FPS {fps_val}", (W - 236, 232), (220, 220, 220))
    if state.in_car:
        kmh = int(abs(state.in_car.spd) * 0.5)
        screen.blit(FONT.render(f"{kmh} km/h", 1, (255, 255, 255)), (W - 140, 238))
        pygame.draw.rect(screen, (0, 0, 0), (W - 230, 272, 220, 22))
        frac = max(0, state.in_car.hp) / state.in_car.max_hp
        col = (60, 200, 60) if frac > 0.6 else ((230, 180, 40) if frac > 0.3 else (220, 40, 40))
        pygame.draw.rect(screen, col, (W - 228, 274, 216 * frac, 18))
        car_label = getattr(state.in_car, "label", "Auto")
        label = "BRENNT!" if state.in_car.burning else f"{car_label} {int(state.in_car.hp)}/{state.in_car.max_hp}"
        screen.blit(FONT.render(label, 1, (255, 255, 255)), (W - 225, 274))
    draw_hint(screen, state, service, FONT)
    if not state.in_car or (state.in_car and state.in_car.kind == "motorcycle"):
        mx, my = pygame.mouse.get_pos()
        pygame.draw.circle(screen, (255, 255, 255), (mx, my), 8, 1)
        pygame.draw.line(screen, (255, 255, 255), (mx - 12, my), (mx + 12, my), 1)
        pygame.draw.line(screen, (255, 255, 255), (mx, my - 12), (mx, my + 12), 1)
    if state.game_over:
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        screen.blit(overlay, (0, 0))
        t = BIG.render("GAME OVER", 1, (240, 60, 60))
        screen.blit(t, (W // 2 - t.get_width() // 2, 30))
        hdr = MED.render("── Highscores ──", 1, (255, 210, 40))
        screen.blit(hdr, (W // 2 - hdr.get_width() // 2, 130))
        for i, entry in enumerate(state.final_scores[:10]):
            is_me = (entry.get("_just_added"))
            col = (255, 230, 80) if is_me else ((255, 255, 255) if i < 3 else (190, 190, 190))
            rank_sym = ["1.", "2.", "3."][i] if i < 3 else f"{i + 1}."
            line = f"{rank_sym:<4} {entry['name']:<18} ${entry['money']:>8}"
            lt = FONT.render(line, 1, col)
            screen.blit(lt, (W // 2 - lt.get_width() // 2, 175 + i * 30))
        t2 = FONT.render("[LEERTASTE] Neu starten   [ESC] Beenden", 1, (200, 200, 200))
        screen.blit(t2, (W // 2 - t2.get_width() // 2, H - 50))
    else:
        draw_overlay_menu(screen, state, BIG, MED, FONT)
    if state.menu in ("pause", "options"):
        menu_ctrl.draw(screen, BIG, MED, FONT, state)
    pygame.display.flip()


def _setup_event_handlers(state):
    """Registriere Event-Handler für das EventBus-System."""
    from game2d.systems.events import EventBus as _EventBus, EventType as _EventType
    bus = _EventBus()

    # Debug-Handler: Logge wichtige Events (kann später entfernt werden)
    def debug_event_logger(event):
        # Nur wichtige Events loggen, nicht alle
        important_types = {
            _EventType.KILL, _EventType.PLAYER_DIED, _EventType.GAME_OVER,
            _EventType.WANTED_LEVEL_CHANGED, _EventType.PICKUP_COLLECTED,
            _EventType.PLAYER_DAMAGED, _EventType.ENTITY_SPAWNED
        }
        if event.event_type in important_types:
            event_logger.info(f"[EVENT] {event.event_type.name}: {event.data}")

    # Registriere Debug-Logger für alle Events (niedrige Priorität)
    bus.subscribe_wildcard(debug_event_logger, priority=-10, once=False)

    # Handler für Game Over: Reset EventBus
    def on_game_over(event):
        # Reset EventBus bei Game Over
        _EventBus.reset()
        # Re-registriere Handler nach Reset
        _setup_event_handlers(state)

    bus.subscribe(_EventType.GAME_OVER, on_game_over, priority=100)

    # Handler für Entity Spawned: Logge Spawns
    def on_entity_spawned(event):
        # Kann später für Statistiken, Achievements, etc. genutzt werden
        pass

    bus.subscribe(_EventType.ENTITY_SPAWNED, on_entity_spawned, priority=0)

    # Handler für Kills: Statistiken
    def on_kill(event):
        # Kann später für Kill-Counter, Achievements, etc. genutzt werden
        pass

    bus.subscribe(_EventType.KILL, on_kill, priority=0)


def main():
    # CLI-Flag Parsing für Logging-Gruppen
    import sys
    log_groups = ''
    if '--log' in sys.argv:
        log_idx = sys.argv.index('--log')
        if log_idx + 1 < len(sys.argv):
            log_groups = sys.argv[log_idx + 1]
        else:
            log_groups = 'p'  # Standardgruppe: Performance
        # Gruppen-Logger basierend auf CLI-Flag aktivieren (nur INFO-Meldungen)
        # Basis-Logger bleibt immer auf WARNING für Warnings/Errors
        perf_logger.set_level(LogLevel.INFO if 'p' in log_groups else LogLevel.CRITICAL)
        event_logger.set_level(LogLevel.INFO if 'e' in log_groups else LogLevel.CRITICAL)
        move_logger.set_level(LogLevel.INFO if 'm' in log_groups else LogLevel.CRITICAL)
    
    pygame.init()
    audio.init()
    settings = settings_mod.load()
    audio.MASTER_VOL = settings['sfx_volume']
    # Initialisiere Object Pools für Performance-Optimierung
    init_pools()
    # Initialisiere Spatial Grid für Kollisionsdetektion
    init_spatial_grid()
    # Initialisiere Profiler (standardmäßig deaktiviert, kann per Taste aktiviert werden)
    profiler.enabled = False
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Mini GTA 2D")
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()
    FONT = pygame.font.SysFont("arial", 20, bold=True)
    BIG = pygame.font.SysFont("arial", 64, bold=True)
    MED = pygame.font.SysFont("arial", 32, bold=True)
    # Minimap-Optimierung: Separate Surfaces für statische und dynamische Elemente
    minimap_static = None  # Wird einmalig erstellt (Straßen, Gebäude, etc.)
    minimap_dynamic = None  # Wird alle 3 Frames aktualisiert (Cars, Player, etc.)
    frame_counter = 0  # Counter für Minimap-Update-Rhythmus

    # --- Fixed Timestep Physics Separation ---
    # Physik läuft bei festen 60Hz, Rendering so schnell wie möglich
    PHYSICS_RATE = 60  # Physik: 60 Updates pro Sekunde
    physics_dt = 1.0 / PHYSICS_RATE  # Fixed timestep für Physik
    MAX_PHYSICS_UPDATES_PER_FRAME = 5  # Max Physik-Updates pro Frame (verhindert Spikes)
    physics_accumulator = 0.0  # Akkumuliert Zeit für Physik-Updates
    physics_frame_count = 0  # Zählt Physik-Updates für FPS-Berechnung
    physics_fps = PHYSICS_RATE  # Ziel-Physik-FPS
    # Für State-Interpolation: speichere vorherigen Zustand
    prev_state_snapshot = None
    # Timer für Physik-FPS-Berechnung
    physics_fps_timer = 0.0
    physics_fps_count = 0
    # Für Player-Positions-Logging
    last_player_x, last_player_y = 0, 0
    last_player_move_frame = 0

    player_name = name_input_screen(screen, W, H, BIG, MED, FONT)

    # State über DI-Provider erstellen und installieren
    state = provider.create(player_name=player_name)
    state.settings = settings
    provider.install(state)
    build_world(state)
    init_services(state)
    
    # Lade Amusement-Park Sprites
    from game2d.render.amusement_sprites import load_amusement_sprites
    try:
        state.amusement_sprites = load_amusement_sprites()
    except Exception as e:
        import sys
        print(f"[WARNING] Konnte Amusement-Sprites nicht laden: {e}", file=sys.stderr)
        state.amusement_sprites = {'static': None, 'rides': {}}
    
    # Initialize building spatial grid for optimized collision detection
    from game2d.systems.spatial import init_and_populate_building_grid, init_and_populate_park_grid
    init_and_populate_building_grid(state.buildings)
    # Initialize park spatial grid (parks + amusement_parks) for pedestrian collision
    all_parks = list(state.parks) + list(state.amusement_parks)
    init_and_populate_park_grid(all_parks)
    menu_ctrl = MenuController(W, H, settings)

    # EventBus Handler registrieren
    _setup_event_handlers(state)

    _spawn_traffic_and_player(state)
    while state.running:
        # FPS-Limit für Rendering auf 200Hz (verhindert extreme Spikes bei Start/Respawn)
        raw_dt = clock.tick(200) / 1000
        frame_counter += 1
        
        # Physik-Akkumulator aktualisieren
        physics_accumulator += raw_dt
        
        # Profiling: Frame Start markieren (VOR Physik, damit Physik in Frame-Zeit enthalten ist)
        # Entity Counts immer berechnen (nicht nur alle 10 Frames) für bessere Profiling-Daten
        entity_counts = {
            "cars": len(state.cars),
            "peds": len(state.peds),
            "cops": len(state.cops),
            "bullets": len(state.bullets),
            "rockets": len(state.rockets),
            "wrecks": len(state.wrecks),
            "corpses": len(state.corpses),
            "particles": len(state.smoke_particles) + len(state.fire_particles) + len(state.blood_particles),
            "cats": len(state.cats),
        }
        # Zähle voll berechnete Entities (im Update-Range)
        if profiler.enabled:
            update_range = UPDATE_RANGE_BUFFER
            cam_x, cam_y = state.cam[0], state.cam[1]
            full_cars = sum(1 for c in state.cars if _is_in_update_range(c, cam_x, cam_y, update_range))
            full_peds = sum(1 for p in state.peds if _is_in_update_range(p, cam_x, cam_y, update_range))
            full_cops = sum(1 for c in state.cops if _is_in_update_range(c, cam_x, cam_y, update_range))
            full_cats = sum(1 for cat in state.cats if _is_in_update_range(cat, cam_x, cam_y, update_range))
            full_bullets = sum(1 for b in state.bullets if _is_in_update_range({"x": b[0], "y": b[1]}, cam_x, cam_y, update_range))
            entity_counts["full_cars"] = full_cars
            entity_counts["full_peds"] = full_peds
            entity_counts["full_cops"] = full_cops
            entity_counts["full_cats"] = full_cats
            entity_counts["full_bullets"] = full_bullets
            profiler.start_frame()
        
        # --- Fester Physik-Timestep: UPDATE so oft wie nötig ---
        # Begrenze auf max 5 Physik-Updates pro Frame, um Spikes beim Start/Respawn zu vermeiden
        # (z.B. wenn raw_dt sehr groß ist nach Ladezeit oder Pause)
        physics_updates_this_frame = 0
        phys_logic_time_total = 0.0  # Gesamtzeit für update_logic + _update_entities_and_physics
        while physics_accumulator >= physics_dt and physics_updates_this_frame < MAX_PHYSICS_UPDATES_PER_FRAME:
            # State-Snapshot für Interpolation (nur erste Iteration pro Frame)
            if physics_updates_this_frame == 0:
                prev_state_snapshot = _capture_state_snapshot(state)
            
            # Physik-Update mit festem Timestep
            if not state.game_over and not state.menu:
                t0 = time.perf_counter()
                if profiler.enabled:
                    with timed("update_logic"):
                        _update_player_and_wanted(state, physics_dt)
                        _update_entities_and_physics(state, physics_dt)
                else:
                    _update_player_and_wanted(state, physics_dt)
                    _update_entities_and_physics(state, physics_dt)
                phys_logic_time_total += time.perf_counter() - t0
            
            physics_accumulator -= physics_dt
            physics_updates_this_frame += 1
            physics_frame_count += 1
        
        # Begrenze physics_accumulator VOR Alpha-Berechnung, um alpha im Bereich [0, 1] zu halten
        # (verhindert Explosion von alpha bei großem raw_dt z.B. nach Ladezeit/Respawn)
        max_accumulator = physics_dt * MAX_PHYSICS_UPDATES_PER_FRAME
        if physics_accumulator > max_accumulator:
            physics_accumulator = max_accumulator
        
        # --- Interpolationsfaktor berechnen ---
        # alpha = wie weit wir zwischen prev_state und current_state sind (0 = prev, 1 = current)
        interpolation_alpha = physics_accumulator / physics_dt if physics_dt > 0 else 0.0
        # Clamp alpha auf [0, 1] für sichere Interpolation (verhindert Extrapolation)
        interpolation_alpha = min(1.0, max(0.0, interpolation_alpha))
        
        # FPS berechnen: Render-FPS von Pygame Clock, Physik-FPS separat
        # Physik-FPS: wir wissen, dass wir PHYSICS_RATE anstreben, aber wir tracken es für Genauigkeit
        # Einfacher: Physik-FPS = physics_updates_this_frame / raw_dt (für diesen Frame)
        # Aber wir wollen einen gleitenden Durchschnitt
        physics_fps_timer += raw_dt
        physics_fps_count += physics_updates_this_frame
        if physics_fps_timer >= 1.0:  # Alle Sekunden aktualisieren
            physics_fps = int(physics_fps_count / physics_fps_timer) if physics_fps_timer > 0 else PHYSICS_RATE
            physics_fps_timer = 0.0
            physics_fps_count = 0
        
        # Render-FPS von Pygame Clock
        clock_fps = clock.get_fps()
        if clock_fps > 0:
            fps_val = int(clock_fps)
        else:
            fps_val = int(1.0 / max(raw_dt, 0.0001))
        
        # Berechne durchschnittliche Physik-Update-Zeit (für späteres Logging)
        avg_phys_ms = (phys_logic_time_total / physics_updates_this_frame * 1000) if physics_updates_this_frame > 0 else 0.0
        
        # Minimap: Statisches Surface einmalig erstellen (nachdem die Welt gebaut ist)
        if minimap_static is None:
            from game2d.render.minimap import create_minimap_static
            minimap_static = create_minimap_static(state)
        
        # Minimap: Dynamisches Surface alle 15 Frames aktualisieren (Performance-Optimierung)
        if frame_counter % 15 == 0:
            from game2d.render.minimap import update_minimap_dynamic
            if minimap_dynamic is None:
                minimap_dynamic = pygame.Surface((216, 216), pygame.SRCALPHA)
            minimap_dynamic.blit(minimap_static, (0, 0))
            update_minimap_dynamic(minimap_dynamic, state)
        
        # Non-physics updates: nutzen geclamptes raw_dt (verhindert Sprünge nach Respawn/Pause)
        effective_dt = min(raw_dt, 0.05)  # Max 50ms für Nicht-Physik-Updates
        if state.message_timer > 0:
            state.message_timer = max(0.0, state.message_timer - effective_dt)
        if not state.menu:
            state.traffic_time += effective_dt
        
        # Player-Positions-Logging (nur wenn sich Position signifikant ändert)
        player = state.player
        player_moved = False
        if abs(player.x - last_player_x) > 5 or abs(player.y - last_player_y) > 5:
            last_player_x, last_player_y = player.x, player.y
            move_logger.info(f"[MOVE] frame={frame_counter} pos=({player.x:.0f},{player.y:.0f}) "
                           f"in_car={'Yes' if state.in_car else 'No'}")
            last_player_move_frame = frame_counter
        
        # Event Handling - mit Profiling nur wenn enabled
        if profiler.enabled:
            with timed("handle_events"):
                _handle_events(state, menu_ctrl, raw_dt)
        else:
            _handle_events(state, menu_ctrl, raw_dt)
        
        # Render - mit Timing für Performance-Analyse
        # Übergebe prev_state_snapshot, interpolation_alpha und physics_fps für glattes Rendering
        t0 = time.perf_counter()
        if profiler.enabled:
            with timed("render"):
                _render_frame(screen, state, clock, menu_ctrl, FONT, BIG, MED, profiler, raw_dt, fps_val, minimap_static, minimap_dynamic, prev_state_snapshot, interpolation_alpha, physics_fps)
        else:
            _render_frame(screen, state, clock, menu_ctrl, FONT, BIG, MED, profiler, raw_dt, fps_val, minimap_static, minimap_dynamic, prev_state_snapshot, interpolation_alpha, physics_fps)
        render_time = time.perf_counter() - t0
        
        # Frame Logging via existing logger (aktivierbar mit -log Flag)
        render_ms = render_time * 1000  # Render-Zeit in ms
        if frame_counter % 10 == 0:
            # Full-Counts berechnen für Logging
            cam_x, cam_y = state.cam[0], state.cam[1]
            update_range = max(300, W // 4)
            full_cars = sum(1 for c in state.cars if _is_in_update_range(c, cam_x, cam_y, update_range))
            full_peds = sum(1 for p in state.peds if _is_in_update_range(p, cam_x, cam_y, update_range))
            full_cops = sum(1 for c in state.cops if _is_in_update_range(c, cam_x, cam_y, update_range))
            perf_logger.info(f"Frame {frame_counter:5d} | dt={raw_dt*1000:7.2f}ms | phys={physics_updates_this_frame} | "
                          f"phys_avg={avg_phys_ms:6.2f}ms | render={render_ms:6.2f}ms | "
                          f"E:{len(state.cars)}/{len(state.peds)}/{len(state.cops)} | "
                          f"F:{full_cars}/{full_peds}/{full_cops} | fps={fps_val} | alpha={interpolation_alpha:.3f}")

        # Profiling: Frame end markieren
        if profiler.enabled and entity_counts is not None:
            profiler.end_frame(entity_counts)
    pygame.quit()


if __name__ == "__main__":
    main()
