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
    PICKUP_AMMO, PICKUP_COLOR, PICKUP_LABEL, PICKUP_RESPAWN,
)
from game2d.persistence import name_input_screen
from game2d.render.hud import draw_star
from game2d.render.sprites import make_ped_frames
from game2d.render.world_bg import draw_world_bg
from game2d.state import GameState, init as state_init
from game2d.world.generation import build_world
from game2d.world.geometry import in_water
from game2d.world.spawning import (
    safe_spawn, exit_car_position, road_spawn, cop_car_spawn_near,
)
from game2d.entities.car import Car
from game2d.entities.ped import Ped
from game2d.systems.effects import (
    make_corpse, spawn_blood, trigger_game_over, do_explosion,
)
from game2d.systems.weapons import fire, aim_to_mouse


def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Mini GTA 2D")
    clock = pygame.time.Clock()
    FONT = pygame.font.SysFont("arial", 20, bold=True)
    BIG  = pygame.font.SysFont("arial", 64, bold=True)
    MED  = pygame.font.SysFont("arial", 32, bold=True)

    player_name = name_input_screen(screen, W, H, BIG, MED, FONT)

    state = GameState(player_name=player_name)
    state_init(state)
    build_world(state)

    # Initial-Verkehr und NPCs
    for _ in range(50):
        x, y, angle = road_spawn()
        col = (random.randint(60,230), random.randint(60,230), random.randint(60,230))
        car = Car(x, y, col)
        car.angle = angle
        state.cars.append(car)

    for _ in range(60):
        x, y = safe_spawn()
        state.peds.append(Ped(x, y))

    # Spieler
    player_x, player_y = safe_spawn()
    player = Ped(player_x, player_y)
    player.frames = make_ped_frames((40, 100, 200), hair=(30,20,15))
    player.sprite = player.frames[0]
    player.hp = 100
    player.money = 0
    player.wanted = 0
    player.crime_timer = 0
    player.aim_angle = 0
    state.player = player
    state.in_car = None
    state.weapon = 1
    state.ammo = {1: 80, 2: 0, 3: 0, 4: 0, 5: 0}
    state.unlocked_weapons = {0, 1}
    state.fire_cd = 0

    # Pickups
    pickup_defs = (
        [('hp', None)] * 22 +
        [(2,   None)] * 6 +
        [(3,   None)] * 4 +
        [(4,   None)] * 3 +
        [(5,   None)] * 2
    )
    for kind, _ in pickup_defs:
        px, py = safe_spawn()
        state.pickups.append([px, py, kind, 0.0])

    cop_spawn = 0.0

    while state.running:
        dt = clock.tick(60) / 1000
        state.traffic_time += dt

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                state.running = False
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    state.running = False
                if state.game_over and e.key == pygame.K_r:
                    os.execv(sys.executable, [sys.executable] + sys.argv)
                if e.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6):
                    w = e.key - pygame.K_1
                    if w in state.unlocked_weapons:
                        state.weapon = w
                if e.key == pygame.K_e and not state.game_over:
                    if state.in_car:
                        player.x, player.y = exit_car_position(state.in_car)
                        state.in_car = None
                    else:
                        for c in state.cars:
                            if math.hypot(c.x-player.x, c.y-player.y) < 60:
                                state.in_car = c
                                break
                if e.key == pygame.K_f and not state.in_car and not state.game_over:
                    for p in state.peds:
                        if math.hypot(p.x-player.x, p.y-player.y) < 35:
                            player.money += random.randint(15, 50)
                            p.state = 'flee'
                            player.wanted = min(5, player.wanted + 1)
                            player.crime_timer = 30
                            break
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and not state.game_over:
                if state.fire_cd <= 0 and not WPN_AUTO[state.weapon]:
                    fire()

        if not state.game_over:
            keys = pygame.key.get_pressed()
            state.fire_cd = max(0, state.fire_cd - dt)

            if state.in_car:
                accel = (1 if keys[pygame.K_w] else 0) - (1 if keys[pygame.K_s] else 0)
                steer = (1 if keys[pygame.K_d] else 0) - (1 if keys[pygame.K_a] else 0)
                state.in_car.update(dt, accel, steer)
                player.x, player.y = state.in_car.x, state.in_car.y
                if in_water(state.in_car.x, state.in_car.y):
                    state.in_car.explode()
            else:
                sp = 220
                dx = (1 if keys[pygame.K_d] else 0) - (1 if keys[pygame.K_a] else 0)
                dy = (1 if keys[pygame.K_s] else 0) - (1 if keys[pygame.K_w] else 0)
                if dx or dy:
                    n = math.hypot(dx, dy)
                    nx = player.x + dx/n * sp * dt
                    ny = player.y + dy/n * sp * dt
                    pr = pygame.Rect(nx-10, ny-10, 20, 20)
                    if not any(pr.colliderect(b[0]) for b in state.buildings):
                        player.x, player.y = nx, ny
                    player.angle = math.degrees(math.atan2(dx, -dy))
                player.aim_angle = aim_to_mouse()
                if keys[pygame.K_SPACE] or (pygame.mouse.get_pressed()[0] and WPN_AUTO[state.weapon]):
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

            tx = (state.in_car.x if state.in_car else player.x) - W//2
            ty = (state.in_car.y if state.in_car else player.y) - H//2
            state.cam[0] += (tx - state.cam[0]) * min(1, 6*dt)
            state.cam[1] += (ty - state.cam[1]) * min(1, 6*dt)

            if player.wanted > 0:
                player.crime_timer -= dt
                if player.crime_timer <= 0:
                    player.wanted = max(0, player.wanted - 1)
                    player.crime_timer = 25
                cop_spawn -= dt
                active_cop_cars = sum(1 for c in state.cars if c.is_cop and not c.dead)
                if cop_spawn <= 0 and active_cop_cars < max(1, player.wanted):
                    cop_spawn = max(2, 8 - player.wanted*1.5)
                    cx, cy, angle = cop_car_spawn_near(player.x, player.y)
                    car = Car(cx, cy, (245,245,250), is_cop=True)
                    car.angle = angle
                    state.cars.append(car)
            else:
                state.cops.clear()
                for c in list(state.cars):
                    if c.is_cop and c is not state.in_car:
                        state.cars.remove(c)

            state.intersection_claims.clear()
            for c in state.cars:
                if c is state.in_car: continue
                c.ai_update(dt)

            player.animate(dt)

            for p in state.peds:
                p.update(dt, player)
                p.animate(dt)
            for c in list(state.cops):
                wants_shoot = c.update(dt, player)
                c.animate(dt)
                if wants_shoot:
                    c.shoot_tick = 1.5
                    dx, dy = player.x - c.x, player.y - c.y
                    d = math.hypot(dx, dy) or 1
                    state.bullets.append([c.x, c.y, dx/d*700, dy/d*700, 0.8, True, 12])

            for b in list(state.bullets):
                b[0] += b[2]*dt; b[1] += b[3]*dt; b[4] -= dt
                if b[4] <= 0:
                    state.bullets.remove(b); continue
                br = pygame.Rect(b[0]-3, b[1]-3, 6, 6)
                if any(br.colliderect(bd[0]) for bd in state.buildings):
                    state.bullets.remove(b); continue
                if b[5]:
                    if state.in_car and br.colliderect(state.in_car.rect()):
                        state.in_car.take_damage(b[6] * 0.6)
                        state.bullets.remove(b)
                        continue
                    if br.colliderect(player.rect()):
                        player.hp -= b[6]
                        spawn_blood(player.x, player.y, 6)
                        state.bullets.remove(b)
                        if player.hp <= 0:
                            state.corpses.append((make_corpse(player), player.x, player.y, player.angle))
                            spawn_blood(player.x, player.y, 22)
                            trigger_game_over()
                        continue
                else:
                    hit_any = False
                    for c in state.cars:
                        if c is state.in_car or c.dead: continue
                        if br.colliderect(c.rect()):
                            c.take_damage(b[6] * 0.5)
                            state.bullets.remove(b); hit_any = True; break
                    if hit_any: continue
                    for p in list(state.peds):
                        if br.colliderect(p.rect()):
                            p.hp -= b[6]; p.state = 'flee'
                            spawn_blood(p.x, p.y, 4)
                            if p.hp <= 0:
                                state.peds.remove(p)
                                state.corpses.append((make_corpse(p), p.x, p.y, p.angle))
                                spawn_blood(p.x, p.y, 20)
                                player.money += random.randint(15, 60)
                                player.wanted = min(5, player.wanted + 1)
                                player.crime_timer = 30
                            state.bullets.remove(b); hit_any=True; break
                    if hit_any: continue
                    for c in list(state.cops):
                        if br.colliderect(c.rect()):
                            c.hp -= b[6]
                            spawn_blood(c.x, c.y, 5)
                            if c.hp <= 0:
                                state.cops.remove(c)
                                state.corpses.append((make_corpse(c), c.x, c.y, c.angle))
                                spawn_blood(c.x, c.y, 24)
                                player.wanted = min(5, player.wanted + 1)
                                player.crime_timer = 30
                            state.bullets.remove(b); break

            for c in list(state.cars):
                c.update_fx(dt)
                if c.dead:
                    state.cars.remove(c)
                    if not c.is_cop:
                        nx, ny, angle = road_spawn()
                        col = (random.randint(60,230), random.randint(60,230), random.randint(60,230))
                        car = Car(nx, ny, col)
                        car.angle = angle
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
                if hit:
                    do_explosion(r[0], r[1])
                    state.rockets.remove(r)
                    player.wanted = min(5, player.wanted + 1)
                    player.crime_timer = 30

            for pk in state.pickups:
                if pk[3] > 0:
                    pk[3] = max(0.0, pk[3] - dt)
                    continue
                if math.hypot(player.x - pk[0], player.y - pk[1]) < 22:
                    kind = pk[2]
                    if kind == 'hp':
                        player.hp = min(100, player.hp + 30)
                    else:
                        state.unlocked_weapons.add(kind)
                        state.ammo[kind] = state.ammo.get(kind, 0) + PICKUP_AMMO[kind]
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
        view = pygame.Rect(icam[0]-20, icam[1]-20, W+40, H+40)
        for bs in state.blood_splats:
            sx, sy = int(bs[0]-icam[0]), int(bs[1]-icam[1])
            if -20 < sx < W+20 and -20 < sy < H+20:
                pygame.draw.circle(screen, bs[3], (sx, sy), bs[2])
        for pk in state.pickups:
            if pk[3] > 0:
                continue
            sx, sy = int(pk[0] - icam[0]), int(pk[1] - icam[1])
            if -30 < sx < W+30 and -30 < sy < H+30:
                col = PICKUP_COLOR[pk[2]]
                pygame.draw.rect(screen, (0,0,0), (sx-13, sy-13, 26, 26), border_radius=5)
                pygame.draw.rect(screen, col,     (sx-11, sy-11, 22, 22), border_radius=4)
                lbl = FONT.render(PICKUP_LABEL[pk[2]], 1, (255,255,255))
                screen.blit(lbl, (sx - lbl.get_width()//2, sy - lbl.get_height()//2))
        for cs, cx, cy, ca in state.corpses:
            if view.collidepoint(cx, cy):
                rot = pygame.transform.rotate(cs, -ca)
                r = rot.get_rect(center=(cx - icam[0], cy - icam[1]))
                screen.blit(rot, r)
        for rect, surf in state.buildings:
            if surf is None: continue
            if view.colliderect(rect):
                screen.blit(surf, (rect.x - icam[0], rect.y - icam[1]))
        for ws, wx, wy, wa, wd in state.wrecks:
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
        for c in state.cars: c.draw(screen, icam)
        for p in state.peds: p.draw(screen, icam)
        for c in state.cops: c.draw(screen, icam)
        if not state.in_car:
            player.draw(screen, icam)
        for bp in state.blood_particles:
            pygame.draw.circle(screen, (180, 0, 0),
                               (int(bp[0]-icam[0]), int(bp[1]-icam[1])), bp[5])
        for b in state.bullets:
            pygame.draw.circle(screen, (255,230,80), (int(b[0]-icam[0]), int(b[1]-icam[1])), 3)
        for r in state.rockets:
            ang_r = math.degrees(math.atan2(r[2], -r[3]))
            rsurf = pygame.Surface((18, 8), pygame.SRCALPHA)
            pygame.draw.ellipse(rsurf, (255,140,30), (0,0,18,8))
            pygame.draw.ellipse(rsurf, (255,240,100), (0,1,10,6))
            rot = pygame.transform.rotate(rsurf, -ang_r)
            screen.blit(rot, rot.get_rect(center=(int(r[0]-icam[0]), int(r[1]-icam[1]))))
        for fp in state.fire_particles:
            t = max(0.0, fp[4] / fp[5])
            col = (255, int(80 + 175 * t), int(40 * t))
            r = max(1, int(fp[6] * (0.5 + 0.5*t)))
            pygame.draw.circle(screen, col, (int(fp[0]-icam[0]), int(fp[1]-icam[1])), r)
        for sp_ in state.smoke_particles:
            t = max(0.0, sp_[4] / sp_[5])
            gv = int(60 + 110 * (1 - t))
            alpha = int(200 * t)
            r = max(1, int(sp_[6] * (1.4 - 0.4*t)))
            srf = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
            pygame.draw.circle(srf, (gv, gv, gv, alpha), (r, r), r)
            screen.blit(srf, (int(sp_[0]-icam[0]-r), int(sp_[1]-icam[1]-r)))
        for ex in state.explosions:
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
        screen.blit(FONT.render(WPN_NAMES[state.weapon], 1, (240,220,80)), (10, 75))
        a = state.ammo.get(state.weapon, 0) if state.weapon != 0 else "∞"
        screen.blit(FONT.render(f"Munition {a}", 1, (255,255,255)), (10, 100))
        for i in range(player.wanted):
            draw_star(screen, W//2 - 36 + i * 20, 23, 9, (255, 200, 40))
        screen.blit(FONT.render("WASD bewegen | Maus zielen | LMB/SPACE schießen | E Auto | F rauben | 1-6 Waffe (6=RPG)",
                                1, (230,230,230)), (10, H-26))
        if state.in_car:
            screen.blit(FONT.render(f"{int(abs(state.in_car.spd)*0.36*10)} km/h", 1, (255,255,255)), (W-140, 14))
            pygame.draw.rect(screen, (0,0,0), (W-230, 50, 220, 22))
            frac = max(0, state.in_car.hp) / state.in_car.max_hp
            col = (60,200,60) if frac > 0.6 else ((230,180,40) if frac > 0.3 else (220,40,40))
            pygame.draw.rect(screen, col, (W-228, 52, 216*frac, 18))
            label = "BRENNT!" if state.in_car.burning else f"Auto {int(state.in_car.hp)}/{state.in_car.max_hp}"
            screen.blit(FONT.render(label, 1, (255,255,255)), (W-225, 52))
        if not state.in_car:
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
            t2 = FONT.render("[R] Neu starten   [ESC] Beenden", 1, (200, 200, 200))
            screen.blit(t2, (W//2 - t2.get_width()//2, H - 50))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
