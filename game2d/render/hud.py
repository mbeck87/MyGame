"""HUD-Hilfsfunktionen (Sterne, Zahlen, Text)."""
import math
import pygame


# HUD Text Cache für Performance-Optimierung
# Key: (text, font_key, color) -> (shadow_surf, label_surf)
# font_key = id(font) um verschiedene Fonts zu unterscheiden
_hud_text_cache: dict = {}


def _get_font_key(font):
    """Erzeuge einen stabilen Key für Font-Objekte."""
    return (id(font), font.get_height(), font.get_bold())


def clear_hud_text_cache():
    """Leert den HUD-Text-Cache (z.B. bei Font-Aenderung oder Resolution Change)."""
    global _hud_text_cache, _simple_text_cache
    _hud_text_cache.clear()
    _simple_text_cache.clear()


# Einfacher Text Cache (ohne Schatten) für FONT.render() Aufrufe
_simple_text_cache: dict = {}


def cached_render(font, text, color):
    """Gecachtes font.render() für einfache Texte ohne Schatten.
    
    Usage:
        surf = cached_render(FONT, "Hello", (255, 255, 255))
        screen.blit(surf, pos)
    """
    font_key = _get_font_key(font)
    cache_key = (text, font_key, color)
    
    if cache_key in _simple_text_cache:
        return _simple_text_cache[cache_key]
    
    surf = font.render(text, 1, color)
    _simple_text_cache[cache_key] = surf
    
    # Cache-Groesse begrenzen
    if len(_simple_text_cache) > 256:
        oldest_key = next(iter(_simple_text_cache))
        del _simple_text_cache[oldest_key]
    
    return surf


def draw_hud_text(surf, font, text, pos, color):
    """Zeichnet Text mit Schatten. Nutzt Caching für Performance."""
    font_key = _get_font_key(font)
    cache_key = (text, font_key, color)
    
    if cache_key in _hud_text_cache:
        shadow_surf, label_surf = _hud_text_cache[cache_key]
    else:
        shadow_surf = font.render(text, 1, (0, 0, 0))
        label_surf = font.render(text, 1, color)
        _hud_text_cache[cache_key] = (shadow_surf, label_surf)
        
        # Cache-Groesse begrenzen (max 256 Einträge)
        if len(_hud_text_cache) > 256:
            # Entferne den aeltesten Eintrag (einfache FIFO-Approximation)
            oldest_key = next(iter(_hud_text_cache))
            del _hud_text_cache[oldest_key]
    
    surf.blit(shadow_surf, (pos[0] + 2, pos[1] + 2))
    surf.blit(label_surf, pos)


def draw_star(surf, x, y, outer_r, color, inner_color=(255, 235, 120)):
    pts = []
    inner_r = outer_r * 0.45
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        r = outer_r if i % 2 == 0 else inner_r
        pts.append((x + math.cos(ang) * r, y + math.sin(ang) * r))
    pygame.draw.polygon(surf, color, pts)
    pygame.draw.polygon(surf, inner_color, pts, 2)
