"""HUD-Hilfsfunktionen (Sterne, Zahlen). Volles HUD-Layout bleibt vorerst
in der Hauptschleife, da es eng mit Loop-State verzahnt ist."""
import math
import pygame


def draw_star(surf, x, y, outer_r, color, inner_color=(255, 235, 120)):
    pts = []
    inner_r = outer_r * 0.45
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        r = outer_r if i % 2 == 0 else inner_r
        pts.append((x + math.cos(ang) * r, y + math.sin(ang) * r))
    pygame.draw.polygon(surf, color, pts)
    pygame.draw.polygon(surf, inner_color, pts, 2)
