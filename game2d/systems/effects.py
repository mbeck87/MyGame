"""Blut, Leichen, Explosionen, Game-Over-Trigger."""
import math
import random
import pygame

from game2d.state import current
from game2d.persistence import save_score
from game2d.systems import audio
from game2d.systems.services import add_money, add_wanted_heat


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


def do_explosion(x, y, radius=140, dmg=500):
    state = current()
    state.explosions.append([x, y, 0, 0.5, radius])
    audio.play('explosion', pos=(x, y))
    spawn_blood(x, y, 28)
    for c in list(state.cars):
        if c.dead: continue
        if math.hypot(c.x-x, c.y-y) < radius:
            c.take_damage(dmg, source_pos=(x, y))
    for p in list(state.peds):
        if math.hypot(p.x-x, p.y-y) < radius:
            p.hp -= dmg
            if p.hp <= 0:
                state.peds.remove(p)
                state.corpses.append((make_corpse(p), p.x, p.y, p.angle))
                spawn_blood(p.x, p.y, 20)
                add_money(state.player, random.randint(20, 55))
                add_wanted_heat(state, "kill_ped")
    for cat in list(state.cats):
        if math.hypot(cat.x-x, cat.y-y) < radius:
            cat.hp -= dmg
            if cat.hp <= 0:
                state.cats.remove(cat)
                state.corpses.append((cat.sprite.copy(), cat.x, cat.y, cat.angle))
                spawn_blood(cat.x, cat.y, 10)
                # 5 Sterne für Katzen-Tötung
                state.player.wanted = 5
                state.player.crime_timer = 30
                state.wanted_heat = 5 * 100
                add_money(state.player, random.randint(50, 100))
    for c in list(state.cops):
        if math.hypot(c.x-x, c.y-y) < radius:
            c.hp -= dmg
            if c.hp <= 0:
                state.cops.remove(c)
                state.corpses.append((make_corpse(c), c.x, c.y, c.angle))
                spawn_blood(c.x, c.y, 24)
                add_money(state.player, random.randint(50, 100))
                add_wanted_heat(state, "kill_cop")
    dist = math.hypot(state.player.x-x, state.player.y-y)
    if dist < radius and not state.game_over:
        damage = int(dmg * max(0.0, 1 - dist/radius))
        if state.player.armor > 0:
            armor_dmg = min(state.player.armor, damage)
            state.player.armor -= armor_dmg
            damage -= armor_dmg
        state.player.hp -= damage
        spawn_blood(state.player.x, state.player.y, 8)
