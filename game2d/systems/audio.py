"""Audio: Kenney-SFX laden, mit Distanz-Falloff abspielen.

Sound-Dateien liegen flach in ``game2d/assets/sfx/`` und folgen dem Schema
``<category>_<variant>.ogg`` (z.B. ``shoot_pistol_a.ogg``). Beim ``init()``
wird alles automatisch nach Kategorie gruppiert; ``play("shoot_pistol")``
wählt zufällig eine Variante.

Wichtig: pygame-CE's ``Channel.set_volume(left, right)`` (2-arg) setzt nur
das Stereo-Panning, NICHT die Master-Lautstärke des Kanals — der bleibt
dabei immer auf max. Daher arbeiten wir hier ausschließlich mit der
Single-Arg-Form ``Channel.set_volume(value)``. Stereo-Pan entfällt damit;
Distanz-Falloff bleibt aber erhalten. Außerdem muss ``set_volume`` NACH
``play`` aufgerufen werden, weil ``play`` die Channel-Volume auf MAX
zurücksetzt.

API:
- ``init()``: Mixer initialisieren und alle .ogg-Dateien laden.
- ``play(category, volume=1.0, pos=None)``: One-shot. ``pos=(x,y)`` aktiviert
  Distanz-Falloff relativ zum Spieler.
- ``start_loop(category, pos=None, volume=1.0)``: Loop-Sound (z.B. fliegende
  Rakete). Liefert den ``Channel`` zurück (oder ``None``).
- ``update_loop(channel, pos=None, volume=1.0)``: Lautstärke eines Loops
  aktualisieren (jeden Frame).
- ``stop_loop(channel)``: Loop beenden.
- ``set_engine(active, throttle=0.0, speed_norm=0.0)``: Auto-Motor steuern.
"""
import array as _array
import io as _io
import math
import os
import random
import wave as _wave
import pygame

from game2d.state import current


SFX_DIR = os.path.join(os.path.dirname(__file__), '..', 'assets', 'sfx')

# Hörradius in Welt-Pixeln. Außerhalb wird der Sound nicht gespielt.
MAX_HEARING_DIST = 1400.0
# Globaler Master-Volume-Multiplier (0..1). Wird von der Settings-Schicht
# (game2d/settings.py + ui/menu.py) zur Laufzeit überschrieben.
MASTER_VOL = 0.5

_sounds = {}        # str -> list[pygame.mixer.Sound]
_initialized = False

# Engine-State (zwei Loop-Channels + interne RPM-Simulation)
_engine_low_channel = None
_engine_high_channel = None
_engine_low_sound = None
_engine_high_sound = None
_engine_rpm = 0.0           # 0..1
_engine_last_tick = 0       # ms, für interne dt-Berechnung


def init():
    """Mixer hochfahren und alle SFX in ``_sounds`` einlesen."""
    global _initialized, _engine_low_sound, _engine_high_sound
    if _initialized:
        return
    pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
    pygame.mixer.init()
    pygame.mixer.set_num_channels(48)

    if not os.path.isdir(SFX_DIR):
        _initialized = True
        return

    for fn in sorted(os.listdir(SFX_DIR)):
        if not fn.endswith('.ogg'):
            continue
        base = fn[:-4]
        # Letztes Segment nach '_' ist die Variante (a, b, c, ...). Davor steht die Kategorie.
        idx = base.rfind('_')
        category = base[:idx] if idx > 0 else base
        try:
            snd = pygame.mixer.Sound(os.path.join(SFX_DIR, fn))
        except pygame.error:
            continue
        _sounds.setdefault(category, []).append(snd)

    if 'engine_low' in _sounds and _sounds['engine_low']:
        _engine_low_sound = _sounds['engine_low'][0]
    if 'engine_high' in _sounds and _sounds['engine_high']:
        _engine_high_sound = _sounds['engine_high'][0]

    # Reifenquietschen synthetisch generieren falls keine Datei vorhanden
    if 'squeal' not in _sounds:
        snd = _make_squeal_sound()
        if snd is not None:
            _sounds['squeal'] = [snd]

    _initialized = True


def _make_squeal_sound():
    """Synthetisiert Reifenquietschen ohne externe Bibliothek."""
    try:
        sr = 22050
        dur = 1.4
        n = int(sr * dur)
        buf = _array.array('h')
        for i in range(n):
            t = i / sr
            f = 720 + 280 * math.sin(math.tau * 3.8 * t)
            v = (math.sin(math.tau * f * t) * 0.55
                 + math.sin(math.tau * f * 1.29 * t) * 0.24
                 + math.sin(math.tau * f * 1.71 * t) * 0.14
                 + math.sin(math.tau * f * 2.13 * t) * 0.07)
            fade = min(i / (0.04 * sr), 1.0, (n - i) / (0.07 * sr))
            buf.append(int(max(-32767, min(32767, v * fade * 25000))))
        wav_buf = _io.BytesIO()
        with _wave.open(wav_buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(buf.tobytes())
        wav_buf.seek(0)
        return pygame.mixer.Sound(wav_buf)
    except Exception:
        return None


def _volume_for(pos, base, max_dist=None):
    """Distanz-Falloff zum Spieler. ``pos=None`` → keine Abschwächung.

    ``max_dist`` überschreibt den globalen Hörradius pro Aufruf — z.B.
    für Sirenen, die einen kleineren Radius haben sollen als Schüsse.
    """
    if pos is None:
        return base
    s = current()
    if s is None or s.player is None:
        return base
    dx = pos[0] - s.player.x
    dy = pos[1] - s.player.y
    dist = math.hypot(dx, dy)
    md = max_dist if max_dist is not None else MAX_HEARING_DIST
    if dist >= md:
        return 0.0
    # Quadratischer Falloff: nahe Sounds bleiben laut, ferne fallen schneller.
    falloff = (1.0 - dist / md) ** 1.6
    return max(0.0, min(1.0, base * falloff))


def play(category, volume=1.0, pos=None, max_dist=None):
    """One-shot abspielen.

    Parameter:
    - ``category``: Kategorie-Name (Teil vor ``_<variant>`` im Dateinamen).
    - ``volume``: 0..1, lokaler Volume-Multiplier vor Master/Distanz.
    - ``pos``: ``(world_x, world_y)`` für Distanz-Falloff. ``None`` = UI-Sound,
      voller Volume * Master.
    - ``max_dist``: optionaler Hörradius in Welt-Pixeln (überschreibt
      ``MAX_HEARING_DIST`` für diesen Aufruf).
    """
    if not _initialized:
        return
    sounds = _sounds.get(category)
    if not sounds:
        return
    snd = random.choice(sounds)
    vol = _volume_for(pos, volume * MASTER_VOL, max_dist)
    if vol < 0.005:
        return
    ch = pygame.mixer.find_channel(True)
    if ch is None:
        return
    # WICHTIG: erst play, dann set_volume — play() resettet die Channel-Volume.
    ch.play(snd)
    ch.set_volume(vol)


def start_loop(category, pos=None, volume=1.0, max_dist=None):
    """Sound als Loop starten und ``Channel`` zurückgeben."""
    if not _initialized:
        return None
    sounds = _sounds.get(category)
    if not sounds:
        return None
    snd = random.choice(sounds)
    ch = pygame.mixer.find_channel(True)
    if ch is None:
        return None
    vol = _volume_for(pos, volume * MASTER_VOL, max_dist)
    ch.play(snd, loops=-1)
    ch.set_volume(vol)
    return ch


def update_loop(channel, pos=None, volume=1.0, max_dist=None):
    """Lautstärke eines laufenden Loops aktualisieren."""
    if channel is None or not _initialized:
        return
    vol = _volume_for(pos, volume * MASTER_VOL, max_dist)
    channel.set_volume(vol)


def stop_loop(channel):
    """Loop-Channel sauber beenden."""
    if channel is None:
        return
    try:
        channel.stop()
    except pygame.error:
        pass


def set_engine(active, throttle=0.0, speed_norm=0.0):
    """Auto-Motor steuern (zweistufig: Idle-Sample + High-Sample).

    Parameter:
    - ``active``: True wenn Spieler im fahrbaren Auto sitzt.
    - ``throttle``: Eingabe -1..0..1 (S-Taste / nichts / W-Taste).
    - ``speed_norm``: Aktuelle |Geschwindigkeit| als Bruchteil von max_spd.

    Intern wird ein RPM-Wert (0..1) gegen ein Ziel gelerpt: Throttle hebt
    schnell an, Loslassen lässt langsam abfallen — so klingt der Motor beim
    Gasgeben höher und beim Ausrollen wieder tiefer. RPM steuert dann das
    Crossfade zwischen Idle-Sample (low) und High-Sample (high).
    """
    global _engine_low_channel, _engine_high_channel
    global _engine_rpm, _engine_last_tick

    if not _initialized:
        return

    now = pygame.time.get_ticks()
    dt = max(0.0, min(0.1, (now - _engine_last_tick) / 1000.0)) if _engine_last_tick else 0.0
    _engine_last_tick = now

    if not active:
        if _engine_low_channel is not None:
            _engine_low_channel.stop()
            _engine_low_channel = None
        if _engine_high_channel is not None:
            _engine_high_channel.stop()
            _engine_high_channel = None
        _engine_rpm = 0.0
        return

    # Ziel-RPM: Geschwindigkeit liefert Basis, Throttle gibt Boost.
    target = max(0.0, min(1.0, speed_norm * 0.85 + (0.35 if throttle > 0 else 0.0)))
    rate = 4.0 if target > _engine_rpm else 1.6
    _engine_rpm += (target - _engine_rpm) * min(1.0, rate * dt)
    _engine_rpm = max(0.0, min(1.0, _engine_rpm))

    low_vol = ((1.0 - _engine_rpm) * 0.30 + 0.12) * MASTER_VOL
    high_vol = (_engine_rpm * 0.55) * MASTER_VOL

    if _engine_low_sound is not None:
        if _engine_low_channel is None or not _engine_low_channel.get_busy():
            _engine_low_channel = pygame.mixer.find_channel(True)
            if _engine_low_channel is not None:
                _engine_low_channel.play(_engine_low_sound, loops=-1)
        if _engine_low_channel is not None:
            _engine_low_channel.set_volume(low_vol)

    if _engine_high_sound is not None:
        if _engine_high_channel is None or not _engine_high_channel.get_busy():
            _engine_high_channel = pygame.mixer.find_channel(True)
            if _engine_high_channel is not None:
                _engine_high_channel.play(_engine_high_sound, loops=-1)
        if _engine_high_channel is not None:
            _engine_high_channel.set_volume(high_vol)
