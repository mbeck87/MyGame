"""Overlay panels for pause, shop, garage and barber."""
import pygame

from game2d.config import W, H
from game2d.systems.services import (
    barber_layout, barber_lines, garage_layout, garage_lines, shop_layout, shop_lines,
)


def _world_rect(rect, cam):
    return pygame.Rect(rect.x - cam[0], rect.y - cam[1], rect.w, rect.h)


def _draw_scissors_icon(screen, cx, cy, scale=1.0, col=(245, 245, 245)):
    r = max(2, int(3 * scale))
    left = (int(cx - 8 * scale), int(cy + 5 * scale))
    right = (int(cx + 8 * scale), int(cy + 5 * scale))
    pivot = (int(cx), int(cy))
    pygame.draw.circle(screen, col, left, r, 1)
    pygame.draw.circle(screen, col, right, r, 1)
    pygame.draw.circle(screen, col, pivot, max(1, int(2 * scale)))
    pygame.draw.line(screen, col, left, pivot, max(1, int(2 * scale)))
    pygame.draw.line(screen, col, right, pivot, max(1, int(2 * scale)))
    pygame.draw.line(screen, col, pivot, (int(cx - 10 * scale), int(cy - 8 * scale)), max(1, int(2 * scale)))
    pygame.draw.line(screen, col, pivot, (int(cx + 10 * scale), int(cy - 8 * scale)), max(1, int(2 * scale)))
    pygame.draw.line(screen, (180, 205, 218), (int(cx - 7 * scale), int(cy - 6 * scale)), (int(cx - 12 * scale), int(cy - 10 * scale)), 1)
    pygame.draw.line(screen, (180, 205, 218), (int(cx + 7 * scale), int(cy - 6 * scale)), (int(cx + 12 * scale), int(cy - 10 * scale)), 1)


def draw_service_markers(screen, state, cam, font):
    view = pygame.Rect(-120, -120, W + 240, H + 240)
    for x, y in state.garages:
        building, driveway, apron = garage_layout(x, y)
        b = _world_rect(building, cam)
        d = _world_rect(driveway, cam)
        a = _world_rect(apron, cam)
        if not (view.colliderect(b) or view.colliderect(d) or view.colliderect(a)):
            continue
        pygame.draw.rect(screen, (116, 116, 112), d, border_radius=2)
        pygame.draw.rect(screen, (138, 138, 132), a, border_radius=3)
        if d.w > 14:
            for ty in (d.y + 9, d.bottom - 10):
                pygame.draw.line(screen, (72, 72, 72), (d.x + 4, ty), (d.right - 4, ty), 2)

        pygame.draw.rect(screen, (30, 34, 38), b.move(4, 5), border_radius=5)
        pygame.draw.rect(screen, (70, 84, 94), b, border_radius=5)
        pygame.draw.rect(screen, (38, 46, 54), (b.x, b.y, b.w, 18), border_radius=5)
        pygame.draw.rect(screen, (176, 184, 186), b, 2, border_radius=5)
        pygame.draw.line(screen, (210, 218, 220), (b.x + 6, b.y + 18), (b.right - 6, b.y + 18), 2)

        faces_left = d.centerx < b.centerx
        door = pygame.Rect(b.left + 5, b.centery - 22, 34, 44) if faces_left else pygame.Rect(b.right - 39, b.centery - 22, 34, 44)
        pygame.draw.rect(screen, (42, 48, 54), door, border_radius=2)
        for yy in range(door.y + 7, door.bottom - 4, 8):
            pygame.draw.line(screen, (92, 102, 110), (door.x + 3, yy), (door.right - 3, yy), 1)
        pygame.draw.rect(screen, (210, 190, 72), (door.x + 3, door.bottom - 7, door.w - 6, 3))

        window_x = b.right - 34 if faces_left else b.x + 10
        for wy in (b.y + 31, b.y + 55):
            win = pygame.Rect(window_x, wy, 24, 14)
            pygame.draw.rect(screen, (24, 36, 44), win, border_radius=2)
            pygame.draw.rect(screen, (96, 168, 198), win.inflate(-4, -4), border_radius=1)

        stripe_x = door.right + 4 if faces_left else door.left - 10
        for yy in range(door.y + 2, door.bottom - 4, 10):
            pygame.draw.line(screen, (230, 190, 58), (stripe_x, yy), (stripe_x + (7 if faces_left else -7), yy + 7), 2)
        sign = font.render("GARAGE", 1, (245, 245, 255))
        pygame.draw.rect(screen, (28, 32, 38), (b.centerx - sign.get_width() // 2 - 6, b.y + 4, sign.get_width() + 12, 18), border_radius=2)
        screen.blit(sign, (b.centerx - sign.get_width() // 2, b.y + 5))

    for x, y in state.shops:
        building, walk, sign_rect = shop_layout(x, y)
        b = _world_rect(building, cam)
        wlk = _world_rect(walk, cam)
        sign = _world_rect(sign_rect, cam)
        if not (view.colliderect(b) or view.colliderect(wlk)):
            continue
        pygame.draw.rect(screen, (134, 132, 124), wlk, border_radius=2)
        pygame.draw.rect(screen, (34, 42, 34), b.move(4, 5), border_radius=5)
        pygame.draw.rect(screen, (72, 142, 86), b, border_radius=5)
        pygame.draw.rect(screen, (204, 232, 172), b, 2, border_radius=5)
        pygame.draw.rect(screen, (42, 88, 54), (b.x, b.y, b.w, 19), border_radius=5)

        awning_y = b.y + 19
        stripe_w = 13
        for i, sx in enumerate(range(b.x + 4, b.right - 4, stripe_w)):
            col = (238, 246, 218) if i % 2 == 0 else (76, 188, 98)
            pygame.draw.polygon(screen, col, [(sx, awning_y), (sx + stripe_w, awning_y), (sx + stripe_w - 4, awning_y + 12), (sx + 4, awning_y + 12)])
        pygame.draw.line(screen, (42, 78, 48), (b.x + 4, awning_y + 12), (b.right - 4, awning_y + 12), 2)

        faces_left = wlk.centerx < b.centerx
        door = pygame.Rect(b.left + 7, b.centery - 15, 24, 31) if faces_left else pygame.Rect(b.right - 31, b.centery - 15, 24, 31)
        pygame.draw.rect(screen, (38, 56, 44), door, border_radius=2)
        pygame.draw.rect(screen, (116, 188, 166), door.inflate(-6, -7), border_radius=1)
        knob_x = door.right - 5 if faces_left else door.left + 5
        pygame.draw.circle(screen, (238, 214, 78), (knob_x, door.centery + 5), 2)

        win_x = b.right - 39 if faces_left else b.x + 12
        win = pygame.Rect(win_x, b.y + 40, 30, 25)
        pygame.draw.rect(screen, (32, 48, 42), win, border_radius=2)
        pygame.draw.rect(screen, (126, 202, 188), win.inflate(-4, -4), border_radius=2)
        pygame.draw.line(screen, (224, 250, 240), (win.x + 5, win.y + 6), (win.right - 5, win.y + 6), 1)
        pygame.draw.rect(screen, (238, 202, 72), (win.x + 5, win.bottom - 8, 6, 5), border_radius=1)
        pygame.draw.rect(screen, (220, 82, 74), (win.x + 14, win.bottom - 9, 7, 6), border_radius=1)

        pygame.draw.rect(screen, (28, 46, 34), sign.move(2, 3), border_radius=4)
        pygame.draw.rect(screen, (38, 84, 48), sign, border_radius=4)
        pygame.draw.rect(screen, (218, 242, 188), sign, 2, border_radius=4)
        txt = font.render("SHOP", 1, (250, 252, 238))
        screen.blit(txt, (sign.centerx - txt.get_width() // 2, sign.centery - txt.get_height() // 2))

    for x, y in state.barbers:
        building, walk, sign_rect = barber_layout(x, y)
        b = _world_rect(building, cam)
        wlk = _world_rect(walk, cam)
        sign = _world_rect(sign_rect, cam)
        if not (view.colliderect(b) or view.colliderect(wlk)):
            continue
        pygame.draw.rect(screen, (136, 132, 136), wlk, border_radius=2)
        pygame.draw.rect(screen, (44, 32, 42), b.move(4, 5), border_radius=5)
        pygame.draw.rect(screen, (154, 74, 112), b, border_radius=5)
        pygame.draw.rect(screen, (236, 170, 210), b, 2, border_radius=5)
        pygame.draw.rect(screen, (104, 42, 78), (b.x, b.y, b.w, 18), border_radius=5)
        pygame.draw.rect(screen, (238, 224, 230), (b.x + 4, b.y + 18, b.w - 8, 10))
        stripe_w = 12
        for i, sx in enumerate(range(b.x + 4, b.right - 5, stripe_w)):
            col = (210, 70, 170) if i % 2 == 0 else (245, 245, 245)
            pygame.draw.polygon(screen, col, [(sx, b.y + 18), (sx + 8, b.y + 18), (sx + 2, b.y + 28), (sx - 6, b.y + 28)])

        faces_left = wlk.centerx < b.centerx
        door = pygame.Rect(b.left + 5, b.centery - 15, 24, 30) if faces_left else pygame.Rect(b.right - 29, b.centery - 15, 24, 30)
        pygame.draw.rect(screen, (34, 24, 34), door, border_radius=2)
        pygame.draw.rect(screen, (84, 52, 72), door.inflate(-6, -7), border_radius=1)
        knob_x = door.right - 5 if faces_left else door.left + 5
        pygame.draw.circle(screen, (238, 210, 86), (knob_x, door.centery + 4), 2)
        win_a = pygame.Rect(b.right - 34, b.y + 35, 24, 22) if faces_left else pygame.Rect(b.x + 10, b.y + 35, 24, 22)
        win_b = pygame.Rect(b.centerx - 12, b.y + 54, 24, 16)
        for win in (win_a, win_b):
            pygame.draw.rect(screen, (34, 24, 38), win, border_radius=2)
            pygame.draw.rect(screen, (116, 176, 196), win.inflate(-4, -4), border_radius=2)
            pygame.draw.line(screen, (220, 245, 250), (win.x + 5, win.y + 5), (win.right - 5, win.y + 5), 1)

        pole_x = b.right - 12 if faces_left else b.x + 5
        pole = pygame.Rect(pole_x, b.y + 31, 7, 29)
        pygame.draw.rect(screen, (245, 245, 245), pole, border_radius=3)
        for sy in range(pole.y + 2, pole.bottom - 2, 6):
            pygame.draw.line(screen, (210, 70, 70), (pole.x + 1, sy + 4), (pole.right - 1, sy), 2)
        pygame.draw.rect(screen, (36, 42, 54), pole, 1, border_radius=3)

        pygame.draw.line(screen, (48, 38, 48), (b.centerx, b.y + 4), (sign.centerx, sign.y), 2)
        pygame.draw.rect(screen, (36, 26, 38), sign.move(2, 3), border_radius=4)
        pygame.draw.rect(screen, (54, 42, 56), sign, border_radius=4)
        pygame.draw.rect(screen, (232, 180, 218), sign, 2, border_radius=4)
        _draw_scissors_icon(screen, sign.centerx, sign.centery + 2, 0.85)


def draw_hint(screen, state, service, font):
    if state.message_timer > 0 and state.message:
        text = state.message
    elif service == "garage":
        text = "[F] Garage"
    elif service == "shop":
        text = "[F] Shop"
    elif service == "barber":
        text = "[F] Friseur"
    elif service == "bank":
        text = "[F] Zentralbank"
    else:
        text = "[P] Pause"
    img = font.render(text, 1, (245, 245, 245))
    pygame.draw.rect(screen, (0, 0, 0), (W // 2 - img.get_width() // 2 - 10, H - 58, img.get_width() + 20, 28))
    screen.blit(img, (W // 2 - img.get_width() // 2, H - 54))


def draw_overlay_menu(screen, state, big, med, font):
    if state.menu not in ("shop", "garage", "barber", "bank"):
        return
    overlay = pygame.Surface((W, H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 165))
    screen.blit(overlay, (0, 0))

    if state.menu == "shop":
        title = "SHOP"
        lines = shop_lines()
    elif state.menu == "garage":
        title = "GARAGE"
        lines = garage_lines(state.in_car)
    elif state.menu == "barber":
        title = "FRISUR" if state.barber_step == "style" else "HAARFARBE"
        lines = barber_lines(state)
    elif state.menu == "bank":
        title = "ZENTRALBANK"
        cd = getattr(state, "bank_robbery_cooldown", 0.0)
        if cd > 0:
            lines = [f"1. Bank ausrauben   (Sperre: {int(cd)}s)"]
        else:
            lines = ["1. Bank ausrauben   +$5000  (4 Sterne)"]
    else:
        title = "PAUSE"
        lines = ["P/ESC Resume", "Near shop/garage/barber: F"]

    box_h = 430 if state.menu == "barber" else 380
    box = pygame.Rect(W // 2 - 260, H // 2 - box_h // 2, 520, box_h)
    panel_col = (24, 26, 30)
    if state.menu == "garage":
        border_col = (90, 130, 165)
    elif state.menu == "barber":
        border_col = (210, 70, 170)
    elif state.menu == "bank":
        border_col = (220, 185, 30)
    else:
        border_col = (70, 150, 92)
    text_col = (245, 245, 245)
    muted_col = (170, 176, 185)
    pygame.draw.rect(screen, panel_col, box, border_radius=6)
    pygame.draw.rect(screen, border_col, box, 3, border_radius=6)
    t = big.render(title, 1, text_col)
    screen.blit(t, (W // 2 - t.get_width() // 2, box.y + 24))
    money = med.render(f"Money ${state.player.money}", 1, (80, 230, 110))
    screen.blit(money, (W // 2 - money.get_width() // 2, box.y + 96))
    line_step = 26 if state.menu == "barber" else 30
    line_y = box.y + (142 if state.menu == "barber" else 150)
    for i, line in enumerate(lines):
        img = font.render(line, 1, text_col)
        screen.blit(img, (box.x + 70, line_y + i * line_step))
    key_count = len(lines) - (1 if state.menu in ("garage", "barber") and ((state.menu == "garage" and not state.in_car) or (state.menu == "barber" and state.in_car)) else 0)
    foot_text = f"[1-{key_count}] Auswaehlen   [ESC/P] Schliessen"
    if state.menu == "barber" and state.barber_step == "color":
        foot_text = f"[1-{key_count}] Auswaehlen   [F] Frisur   [ESC/P] Schliessen"
    foot = font.render(foot_text, 1, muted_col)
    screen.blit(foot, (W // 2 - foot.get_width() // 2, box.bottom - 42))
