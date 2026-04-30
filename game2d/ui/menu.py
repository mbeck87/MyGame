"""Pause-/Options-Menü als Overlay über dem laufenden Spiel.

Zwei Screens: ``state.menu == 'pause'`` (Resume / Options / Exit Game) und
``state.menu == 'options'`` (SFX-Volume-Slider, Auflösungs-Cycle + Back).
Eingaben werden via ``MenuController.handle_event(event, state)``
verarbeitet, gezeichnet via ``draw(...)``. Slider-Drag aktualisiert
Lautstärke live; gespeichert wird beim Loslassen der Maustaste. Eine
Auflösungs-Änderung wird sofort persistiert, ist aber erst nach einem
Prozess-Neustart aktiv (``Apply``-Button → Action ``'apply_resolution'``).
"""
import pygame

from game2d import settings as settings_mod
from game2d.config import W as ACTIVE_W, H as ACTIVE_H
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


class _Cycle:
    """Wert-Auswahl mit Pfeilen links/rechts, zyklisch über ``options``."""

    def __init__(self, rect, options, value):
        self.rect = pygame.Rect(rect)
        self.options = list(options)
        self.idx = self.options.index(value) if value in self.options else 0
        self.hover_left = False
        self.hover_right = False

    @property
    def value(self):
        return self.options[self.idx]

    def _left_rect(self):
        return pygame.Rect(self.rect.x, self.rect.y, 40, self.rect.h)

    def _right_rect(self):
        return pygame.Rect(self.rect.right - 40, self.rect.y, 40, self.rect.h)

    def update_hover(self, mouse_pos):
        self.hover_left = self._left_rect().collidepoint(mouse_pos)
        self.hover_right = self._right_rect().collidepoint(mouse_pos)

    def handle_event(self, event):
        """``True`` zurückgeben, wenn der Wert durch dieses Event gewechselt wurde."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._left_rect().collidepoint(event.pos):
                self.idx = (self.idx - 1) % len(self.options)
                return True
            if self._right_rect().collidepoint(event.pos):
                self.idx = (self.idx + 1) % len(self.options)
                return True
        return False

    def draw(self, surf, font):
        pygame.draw.rect(surf, (45, 48, 60), self.rect, border_radius=8)
        pygame.draw.rect(surf, (160, 165, 185), self.rect, 2, border_radius=8)
        l = self._left_rect()
        r = self._right_rect()
        col_l = (255, 255, 255) if self.hover_left else (200, 205, 220)
        col_r = (255, 255, 255) if self.hover_right else (200, 205, 220)
        pygame.draw.polygon(surf, col_l, [
            (l.right - 12, l.y + 10),
            (l.right - 12, l.bottom - 10),
            (l.x + 14, l.centery),
        ])
        pygame.draw.polygon(surf, col_r, [
            (r.x + 12, r.y + 10),
            (r.x + 12, r.bottom - 10),
            (r.right - 14, r.centery),
        ])
        t = font.render(str(self.value), 1, (255, 255, 255))
        surf.blit(t, t.get_rect(center=self.rect.center))


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
        # Options-Layout: SFX-Slider oben, Auflösungs-Cycle darunter,
        # Apply (nur bei Pending) und Back unten.
        self.slider = _Slider((cx - 170, cy - 110, 340, 10),
                              settings.get('sfx_volume', 0.5))
        self.cycle_res = _Cycle((cx - 170, cy - 10, 340, 44),
                                settings_mod.RESOLUTIONS,
                                settings.get('resolution', f"{ACTIVE_W}x{ACTIVE_H}"))
        self.btn_apply   = _Button("Anwenden & Neustart",
                                   (x, cy + 70,  bw, bh))
        self.btn_back    = _Button("Back",        (x, cy + 140, bw, bh))
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
            self.cycle_res.update_hover(mouse_pos)
            if self._resolution_changed():
                self.btn_apply.update_hover(mouse_pos)
            changed, released = self.slider.handle_event(event)
            if changed:
                self.settings['sfx_volume'] = self.slider.value
                audio.MASTER_VOL = self.slider.value
            if released:
                self.settings['sfx_volume'] = self.slider.value
                audio.MASTER_VOL = self.slider.value
                settings_mod.save(self.settings)
            if self.cycle_res.handle_event(event):
                self.settings['resolution'] = self.cycle_res.value
                settings_mod.save(self.settings)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._resolution_changed() and self.btn_apply.hits(event.pos):
                    self.settings['resolution'] = self.cycle_res.value
                    settings_mod.save(self.settings)
                    return 'apply_resolution'
                if self.btn_back.hits(event.pos):
                    settings_mod.save(self.settings)
                    return 'back'
        return None

    def _resolution_changed(self):
        """``True`` wenn die im Cycle gewählte Auflösung nicht der aktiven entspricht."""
        return self.cycle_res.value != f"{ACTIVE_W}x{ACTIVE_H}"

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
        cx = self.sw // 2
        cy = self.sh // 2
        title = big_font.render("OPTIONEN", 1, (240, 240, 255))
        screen.blit(title, title.get_rect(center=(cx, cy - 220)))
        lbl_sfx = med_font.render("SFX Volume", 1, (220, 225, 240))
        screen.blit(lbl_sfx, lbl_sfx.get_rect(center=(cx, cy - 150)))
        pct = small_font.render(f"{int(self.slider.value * 100)} %", 1, (180, 220, 255))
        screen.blit(pct, pct.get_rect(center=(cx, cy - 80)))
        self.slider.draw(screen)
        lbl_res = med_font.render("Auflösung", 1, (220, 225, 240))
        screen.blit(lbl_res, lbl_res.get_rect(center=(cx, cy - 50)))
        self.cycle_res.draw(screen, med_font)
        if self._resolution_changed():
            hint = small_font.render(
                f"Aktiv: {ACTIVE_W}x{ACTIVE_H} – Anwenden startet das Spiel neu",
                1, (255, 200, 90))
            screen.blit(hint, hint.get_rect(center=(cx, cy + 50)))
            self.btn_apply.draw(screen, small_font)
        self.btn_back.draw(screen, med_font)
