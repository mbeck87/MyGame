"""Blut, Leichen, Explosionen, Game-Over-Trigger."""
import math
import random
import pygame

from game2d.state import current
from game2d.persistence import save_score
from game2d.systems import audio


def make_corpse(ped):
    s = ped.sprite.copy()
    overlay = pygame.Surface(s.get_size(), pygame.SRCALPHA)
    overlay.fill((140, 0, 0, 110))
    s.blit(overlay, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
    return s


def spawn_blood(x, y, amount=14):
    state = current()
    for _ in range(amount):
        a = random.uniform(0, 6.28)
        sp = random.uniform(40, 220)
        state.blood_particles.append([x, y, math.cos(a)*sp, math.sin(a)*sp,
                                      random.uniform(0.3, 0.7), random.randint(2,4)])
    for _ in range(random.randint(3, 6)):
        ox = x + random.uniform(-12, 12)
        oy = y + random.uniform(-12, 12)
        state.blood_splats.append((ox, oy, random.randint(4, 9),
                                   (random.randint(110,160), 0, 0)))


def trigger_game_over():
    state = current()
    if state.game_over:
        return
    state.game_over = True
    audio.set_engine(False)
    # Stop alle Loop-Sounds von allen Cars und Rockets
    for car in list(state.cops) + list(state.cars):
        for attr in ['_siren_channel', '_engine_channel', '_squeal_channel']:
            ch = getattr(car, attr, None)
            if ch is not None:
                audio.stop_loop(ch)
                setattr(car, attr, None)
    for r in state.rockets:
        if len(r) > 5 and r[5] is not None:
            audio.stop_loop(r[5])
    audio.play('game_over')
    if not state.score_saved:
        state.score_saved = True
        score_money = getattr(state.player, "total_money_earned", state.player.money)
        scores = save_score(state.player_name, score_money)
        marked = False
        for e in reversed(scores):
            if not marked and e["name"] == state.player_name and e["money"] == score_money:
                e["_just_added"] = True
                marked = True
        state.final_scores = scores


def do_explosion(x, y, radius=175, dmg=500):
    from game2d.systems.services import add_money, add_wanted_heat, on_kill
    state = current()
    state.explosions.append([x, y, 0, 0.5, radius])
    audio.play('explosion', pos=(x, y))
    spawn_blood(x, y, 28)
    
    def calc_damage(dist, rad):
        ratio = dist / rad
        if ratio <= 0.2:
            return 530
        else:
            return max(30, int(530 - 500 * ((ratio - 0.2) / 0.8)))
    
    for c in list(state.cars):
        if c.dead: continue
        dist = math.hypot(c.x-x, c.y-y)
        if dist < radius:
            c.take_damage(calc_damage(dist, radius), source_pos=(x, y))
    for p in list(state.peds):
        dist = math.hypot(p.x-x, p.y-y)
        if dist < radius:
            p.hp -= calc_damage(dist, radius)
            if p.hp <= 0:
                state.peds.remove(p)
                state.corpses.append((make_corpse(p), p.x, p.y, p.angle))
                spawn_blood(p.x, p.y, 20)
                add_money(state.player, random.randint(20, 55))
                on_kill(state, p, is_cop=False)
    for cat in list(state.cats):
        dist = math.hypot(cat.x-x, cat.y-y)
        if dist < radius:
            cat.hp -= calc_damage(dist, radius)
            if cat.hp <= 0:
                state.cats.remove(cat)
                state.corpses.append((cat.sprite.copy(), cat.x, cat.y, cat.angle))
                spawn_blood(cat.x, cat.y, 10)
                # Katzen-Tötung zählt als Kill für Wanted-Level
                on_kill(state, cat, is_cop=False)
                # Aber zusätzlich: 5 Sterne für Katzen-Tötung
                state.player.wanted = 5
                state.player.crime_timer = 30
                state.wanted_heat = 5 * 100
                add_money(state.player, random.randint(50, 100))
    for c in list(state.cops):
        dist = math.hypot(c.x-x, c.y-y)
        if dist < radius:
            c.hp -= calc_damage(dist, radius)
            if c.hp <= 0:
                if c._siren_channel is not None:
                    audio.stop_loop(c._siren_channel)
                    c._siren_channel = None
                state.cops.remove(c)
                state.corpses.append((make_corpse(c), c.x, c.y, c.angle))
                spawn_blood(c.x, c.y, 24)
                add_money(state.player, random.randint(50, 100))
                on_kill(state, c, is_cop=True)
    dist = math.hypot(state.player.x-x, state.player.y-y)
    if dist < radius and not state.game_over:
        damage = calc_damage(dist, radius)
        if state.player.armor > 0:
            armor_dmg = min(state.player.armor, damage)
            state.player.armor -= armor_dmg
            damage -= armor_dmg
        state.player.hp -= damage
        spawn_blood(state.player.x, state.player.y, 8)
