"""Pause-/Options-Menü als Overlay über dem laufenden Spiel.

Zwei Screens: ``state.menu == 'pause'`` (Resume / Options / Exit Game) und
``state.menu == 'options'`` (SFX-Volume-Slider + Back). Eingaben werden via
``MenuController.handle_event(event, state)`` verarbeitet, gezeichnet via
``draw(...)``. Slider-Drag aktualisiert Lautstärke live; gespeichert wird
beim Loslassen der Maustaste.
"""
import pygame

from game2d import settings as settings_mod
from game2d.systems import audio


class _Button:
    """Klickbarer Rechteck-Button mit Hover-Highlight."""

    def __init__(self, label, rect):
        self.label = label
        self.rect = pygame.Rect(rect)
        self.hovered = False

    def update_hover(self, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)

    def hits(self, pos):
        return self.rect.collidepoint(pos)

    def draw(self, surf, font):
        bg = (110, 130, 180) if self.hovered else (60, 65, 85)
        border = (240, 240, 250) if self.hovered else (160, 165, 185)
        pygame.draw.rect(surf, bg, self.rect, border_radius=10)
        pygame.draw.rect(surf, border, self.rect, 2, border_radius=10)
        t = font.render(self.label, 1, (255, 255, 255))
        surf.blit(t, t.get_rect(center=self.rect.center))


class _Slider:
    """Horizontaler Slider 0..1 mit Knob-Drag und Track-Click."""

    def __init__(self, rect, value):
        self.rect = pygame.Rect(rect)
        self.value = max(0.0, min(1.0, value))
        self.dragging = False

    def _knob_x(self):
        return self.rect.x + int(self.value * self.rect.w)

    def _knob_rect(self):
        # Großzügige Hitbox für Maus, damit der Knob leichter zu greifen ist.
        x = self._knob_x()
        return pygame.Rect(x - 12, self.rect.y - 10, 24, self.rect.h + 20)

    def _set_from_x(self, x):
        v = (x - self.rect.x) / max(1, self.rect.w)
        v = max(0.0, min(1.0, v))
        if abs(v - self.value) > 0.001:
            self.value = v
            return True
        return False

    def handle_event(self, event):
        """Liefert ('changed', 'released') wobei beide bool sind.

        - changed: True wenn ``self.value`` durch dieses Event verändert wurde.
        - released: True genau bei MOUSEBUTTONUP nach einem Drag — Caller
          nutzt das als Trigger zum Persistieren.
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            track = self.rect.inflate(0, 24)
            if self._knob_rect().collidepoint(event.pos) or track.collidepoint(event.pos):
                self.dragging = True
                return self._set_from_x(event.pos[0]), False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            return self._set_from_x(event.pos[0]), False
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was = self.dragging
            self.dragging = False
            return False, was
        return False, False

    def draw(self, surf):
        pygame.draw.rect(surf, (45, 48, 60), self.rect, border_radius=4)
        fill = self.rect.copy()
        fill.w = max(0, int(self.value * self.rect.w))
        if fill.w > 0:
            pygame.draw.rect(surf, (90, 170, 230), fill, border_radius=4)
        kx = self._knob_x()
        pygame.draw.circle(surf, (240, 245, 255), (kx, self.rect.centery), 11)
        pygame.draw.circle(surf, (40, 45, 60), (kx, self.rect.centery), 11, 2)


class MenuController:
    """Hält Buttons + Slider und routet Events.

    ``handle_event`` liefert einen Action-String, den ``main`` interpretiert:
    ``'resume'``, ``'open_options'``, ``'back'``, ``'exit'`` oder ``None``.
    Volume-Änderungen werden hier direkt auf ``audio.MASTER_VOL`` gespiegelt
    und beim Slider-Release in ``settings.json`` persistiert.
    """

    def __init__(self, screen_w, screen_h, settings):
        self.sw = screen_w
        self.sh = screen_h
        self.settings = settings
        cx, cy = screen_w // 2, screen_h // 2
        bw, bh, gap = 280, 56, 18
        x = cx - bw // 2
        top = cy - (3 * bh + 2 * gap) // 2
        self.btn_resume  = _Button("Resume",    (x, top,                       bw, bh))
        self.btn_options = _Button("Options",   (x, top + (bh + gap),          bw, bh))
        self.btn_exit    = _Button("Exit Game", (x, top + 2 * (bh + gap),      bw, bh))
        self.btn_back    = _Button("Back",      (x, cy + 110,                  bw, bh))
        self.slider = _Slider((cx - 170, cy - 10, 340, 10), settings.get('sfx_volume', 0.5))
        self._last_test_ms = 0

    def _pause_buttons(self):
        return (self.btn_resume, self.btn_options, self.btn_exit)

    def handle_event(self, event, state):
        mouse_pos = pygame.mouse.get_pos()
        if state.menu == 'pause':
            for b in self._pause_buttons():
                b.update_hover(mouse_pos)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.btn_resume.hits(event.pos):
                    return 'resume'
                if self.btn_options.hits(event.pos):
                    return 'open_options'
                if self.btn_exit.hits(event.pos):
                    return 'exit'
        elif state.menu == 'options':
            self.btn_back.update_hover(mouse_pos)
            changed, released = self.slider.handle_event(event)
            if changed:
                self.settings['sfx_volume'] = self.slider.value
                audio.MASTER_VOL = self.slider.value
            if released:
                self.settings['sfx_volume'] = self.slider.value
                audio.MASTER_VOL = self.slider.value
                settings_mod.save(self.settings)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.btn_back.hits(event.pos):
                    settings_mod.save(self.settings)
                    return 'back'
        return None

    def draw(self, screen, big_font, med_font, small_font, state):
        overlay = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 175))
        screen.blit(overlay, (0, 0))
        if state.menu == 'pause':
            self._draw_pause(screen, big_font, med_font)
        elif state.menu == 'options':
            self._draw_options(screen, big_font, med_font, small_font)

    def _draw_pause(self, screen, big_font, med_font):
        title = big_font.render("PAUSE", 1, (240, 240, 255))
        screen.blit(title, title.get_rect(center=(self.sw // 2, self.sh // 2 - 180)))
        for b in self._pause_buttons():
            b.draw(screen, med_font)

    def _draw_options(self, screen, big_font, med_font, small_font):
        title = big_font.render("OPTIONEN", 1, (240, 240, 255))
        screen.blit(title, title.get_rect(center=(self.sw // 2, self.sh // 2 - 180)))
        lbl = med_font.render("SFX Volume", 1, (220, 225, 240))
        screen.blit(lbl, lbl.get_rect(center=(self.sw // 2, self.sh // 2 - 60)))
        pct = small_font.render(f"{int(self.slider.value * 100)} %", 1, (180, 220, 255))
        screen.blit(pct, pct.get_rect(center=(self.sw // 2, self.sh // 2 + 18)))
        self.slider.draw(screen)
        self.btn_back.draw(screen, med_font)
