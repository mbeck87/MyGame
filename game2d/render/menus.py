"""Overlay panels for pause, shop and garage."""
import pygame

from game2d.config import W, H
from game2d.systems.services import garage_layout, garage_lines, shop_lines


def _world_rect(rect, cam):
    return pygame.Rect(rect.x - cam[0], rect.y - cam[1], rect.w, rect.h)


def draw_service_markers(screen, state, cam, font):
    view = pygame.Rect(-120, -120, W + 240, H + 240)
    for x, y in state.garages:
        building, driveway, apron = garage_layout(x, y)
        b = _world_rect(building, cam)
        d = _world_rect(driveway, cam)
        a = _world_rect(apron, cam)
        if not (view.colliderect(b) or view.colliderect(d) or view.colliderect(a)):
            continue
        pygame.draw.rect(screen, (48, 50, 54), d)
        pygame.draw.rect(screen, (62, 64, 70), a, border_radius=3)
        pygame.draw.rect(screen, (34, 88, 128), b, border_radius=4)
        pygame.draw.rect(screen, (170, 205, 230), b, 2, border_radius=4)
        door = pygame.Rect(b.centerx - 24, b.bottom - 18, 48, 18)
        pygame.draw.rect(screen, (28, 32, 38), door)
        sign = font.render("GARAGE", 1, (245, 245, 255))
        screen.blit(sign, (b.centerx - sign.get_width() // 2, b.y + 8))

    for x, y in state.shops:
        sx, sy = int(x - cam[0]), int(y - cam[1])
        if -60 <= sx <= W + 60 and -60 <= sy <= H + 60:
            pygame.draw.circle(screen, (0, 0, 0), (sx, sy), 22)
            pygame.draw.circle(screen, (60, 220, 90), (sx, sy), 18)
            txt = font.render("S", 1, (255, 255, 255))
            screen.blit(txt, (sx - txt.get_width() // 2, sy - txt.get_height() // 2))


def draw_hint(screen, state, service, font):
    if state.message_timer > 0 and state.message:
        text = state.message
    elif service == "garage":
        text = "[G] Garage"
    elif service == "shop":
        text = "[B] Shop"
    else:
        text = "[P] Pause"
    img = font.render(text, 1, (245, 245, 245))
    pygame.draw.rect(screen, (0, 0, 0), (W // 2 - img.get_width() // 2 - 10, H - 58, img.get_width() + 20, 28))
    screen.blit(img, (W // 2 - img.get_width() // 2, H - 54))


def draw_overlay_menu(screen, state, big, med, font):
    if state.menu not in ("shop", "garage"):
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
    else:
        title = "PAUSE"
        lines = ["P/ESC Resume", "Near shop: B", "Near garage: G"]

    box = pygame.Rect(W // 2 - 260, H // 2 - 190, 520, 380)
    panel_col = (24, 26, 30)
    border_col = (90, 130, 165) if state.menu == "garage" else (70, 150, 92)
    text_col = (245, 245, 245)
    muted_col = (170, 176, 185)
    pygame.draw.rect(screen, panel_col, box, border_radius=6)
    pygame.draw.rect(screen, border_col, box, 3, border_radius=6)
    t = big.render(title, 1, text_col)
    screen.blit(t, (W // 2 - t.get_width() // 2, box.y + 24))
    money = med.render(f"Money ${state.player.money}", 1, (80, 230, 110))
    screen.blit(money, (W // 2 - money.get_width() // 2, box.y + 96))
    for i, line in enumerate(lines):
        img = font.render(line, 1, text_col)
        screen.blit(img, (box.x + 70, box.y + 150 + i * 30))
    foot = font.render("[1-6] Buy/use   [ESC/P] Close", 1, muted_col)
    screen.blit(foot, (W // 2 - foot.get_width() // 2, box.bottom - 42))
