"""HUD-Hilfsfunktionen (Sterne, Zahlen, Text)."""
import math
import pygame


def draw_hud_text(surf, font, text, pos, color):
    shadow = font.render(text, 1, (0, 0, 0))
    label = font.render(text, 1, color)
    surf.blit(shadow, (pos[0] + 2, pos[1] + 2))
    surf.blit(label, pos)


def draw_star(surf, x, y, outer_r, color, inner_color=(255, 235, 120)):
    pts = []
    inner_r = outer_r * 0.45
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        r = outer_r if i % 2 == 0 else inner_r
        pts.append((x + math.cos(ang) * r, y + math.sin(ang) * r))
    pygame.draw.polygon(surf, color, pts)
    pygame.draw.polygon(surf, inner_color, pts, 2)
