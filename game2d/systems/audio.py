"""Audio: SFX laden, mit Distanz-Falloff abspielen.

Sound-Dateien liegen flach in ``game2d/assets/sfx/`` und folgen dem Schema
``<category>_<variant>.ogg`` oder ``.wav``. Beim ``init()`` wird alles
automatisch nach Kategorie gruppiert; ``play("shoot_pistol")`` wählt zufällig
eine Variante.

Motor-Sounds kommen von OpenGameArt (CC0): ``engine_band_0.wav`` bis
``engine_band_3.wav`` (Leerlauf → Vollgas). Sie werden im 4-Band-Crossfade
per ``set_engine()`` übergeblendet.

Wichtig: pygame-CE's ``Channel.set_volume(left, right)`` (2-arg) setzt nur
das Stereo-Panning, NICHT die Master-Lautstärke des Kanals — der bleibt
dabei immer auf max. Daher arbeiten wir hier ausschließlich mit der
Single-Arg-Form ``Channel.set_volume(value)``. Stereo-Pan entfällt damit;
Distanz-Falloff bleibt aber erhalten. Außerdem muss ``set_volume`` NACH
``play`` aufgerufen werden, weil ``play`` die Channel-Volume auf MAX
zurücksetzt.

API:
- ``init()``: Mixer hochfahren und alle .ogg/.wav-Dateien laden.
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

# Motor: 4 RPM-Bänder (Leerlauf → Vollgas).
# Dateien: engine_band_0.wav (Idle) … engine_band_3.wav (Vollgas), CC0 von
# OpenGameArt (https://opengameart.org/content/racing-car-engine-sound-loops).
_ENGINE_SOUNDS  = [None, None, None, None]
_ENGINE_CHANS   = [None, None, None, None]
_engine_rpm     = 0.0   # 0..1
_engine_last_tick = 0   # ms


def init():
    """Mixer hochfahren und alle SFX in ``_sounds`` einlesen."""
    global _initialized
    if _initialized:
        return
    pygame.mixer.pre_init(frequency=22050, size=-16, channels=1, buffer=512)
    pygame.mixer.init()
    pygame.mixer.set_num_channels(52)

    if os.path.isdir(SFX_DIR):
        for fn in sorted(os.listdir(SFX_DIR)):
            if not (fn.endswith('.ogg') or fn.endswith('.wav')):
                continue
            ext_len = 4  # '.ogg' oder '.wav'
            base = fn[:-ext_len]
            idx = base.rfind('_')
            category = base[:idx] if idx > 0 else base
            try:
                snd = pygame.mixer.Sound(os.path.join(SFX_DIR, fn))
            except pygame.error:
                continue
            _sounds.setdefault(category, []).append(snd)

    # Motor-Bänder aus heruntergeladenen Dateien befüllen (sortiert: 0=Idle … 3=Vollgas)
    for i, snd in enumerate(_sounds.get('engine_band', [])[:4]):
        _ENGINE_SOUNDS[i] = snd

    # Reifenquietschen (synthetisch, kein geeignetes Asset verfügbar)
    if 'squeal' not in _sounds:
        snd = _make_squeal_sound()
        if snd is not None:
            _sounds['squeal'] = [snd]

    _initialized = True


def _biquad_bp(freq, Q, sr):
    """Biquad-Bandpass-Koeffizienten (b0, b2, a1, a2) – normalisiert auf a0=1."""
    w0 = math.tau * freq / sr
    alpha = math.sin(w0) / (2.0 * Q)
    a0 = 1.0 + alpha
    return (alpha / a0, -alpha / a0,
            -2.0 * math.cos(w0) / a0, (1.0 - alpha) / a0)


def _make_squeal_sound():
    """Reifenquietschen: weißes Rauschen durch Resonanzfilter.

    Echtes Reifenquietschen ist Reibungsrauschen, das durch die
    Reifenresonanz gefärbt wird – kein Sinuston. Zwei leicht
    verstimmte Bandpässe erzeugen ein natürliches Schwebungs-Timbre.
    """
    try:
        import random as _rnd
        sr = 22050
        dur = 1.5
        n = int(sr * dur)

        # Zwei leicht verstimmte Resonanzen (~1100 Hz + ~1350 Hz) + eine höhere
        b0a, b2a, a1a, a2a = _biquad_bp(1100, 9.0, sr)
        b0b, b2b, a1b, a2b = _biquad_bp(1350, 7.0, sr)
        b0c, b2c, a1c, a2c = _biquad_bp(2600, 5.0, sr)

        x1a=x2a=y1a=y2a = 0.0
        x1b=x2b=y1b=y2b = 0.0
        x1c=x2c=y1c=y2c = 0.0

        buf = _array.array('h')
        for i in range(n):
            noise = _rnd.gauss(0, 1.0)

            ya = b0a*noise + b2a*x2a - a1a*y1a - a2a*y2a
            x2a=x1a; x1a=noise; y2a=y1a; y1a=ya

            yb = b0b*noise + b2b*x2b - a1b*y1b - a2b*y2b
            x2b=x1b; x1b=noise; y2b=y1b; y1b=yb

            yc = b0c*noise + b2c*x2c - a1c*y1c - a2c*y2c
            x2c=x1c; x1c=noise; y2c=y1c; y1c=yc

            v = ya * 0.50 + yb * 0.35 + yc * 0.15
            fade = min(i / (0.04 * sr), 1.0, (n - i) / (0.06 * sr))
            buf.append(int(max(-32767, min(32767, v * fade * 32000))))

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
    """Auto-Motor steuern (4-Band-Crossfade mit Tonhöhenänderung).

    Jedes Band hat eine eigene Grundfrequenz; durch den Crossfade entsteht
    der Eindruck steigender Drehzahl, ohne dass Echtzeit-Pitchshifting nötig ist.

    Parameter:
    - ``active``: True wenn Spieler im fahrbaren Auto sitzt.
    - ``throttle``: Eingabe -1..0..1 (S-Taste / nichts / W-Taste).
    - ``speed_norm``: |Geschwindigkeit| als Bruchteil von max_spd.
    """
    global _ENGINE_CHANS, _engine_rpm, _engine_last_tick

    if not _initialized:
        return

    now = pygame.time.get_ticks()
    dt = max(0.0, min(0.1, (now - _engine_last_tick) / 1000.0)) if _engine_last_tick else 0.0
    _engine_last_tick = now

    if not active:
        for i in range(4):
            if _ENGINE_CHANS[i] is not None:
                _ENGINE_CHANS[i].stop()
                _ENGINE_CHANS[i] = None
        _engine_rpm = 0.0
        return

    # RPM-Ziel: Gasstellung + Geschwindigkeit
    target = max(0.0, min(1.0, speed_norm * 0.82 + (0.28 if throttle > 0 else 0.0)))
    rate = 5.0 if target > _engine_rpm else 1.5
    _engine_rpm += (target - _engine_rpm) * min(1.0, rate * dt)
    _engine_rpm = max(0.0, min(1.0, _engine_rpm))

    # Dreieck-Crossfade: rpm_pos 0..3 → je Band ein Zelt-Gewicht
    rpm_pos = _engine_rpm * 3.0
    for i in range(4):
        snd = _ENGINE_SOUNDS[i]
        if snd is None:
            continue
        weight = max(0.0, 1.0 - abs(rpm_pos - i))
        vol = weight * 0.48 * MASTER_VOL

        ch = _ENGINE_CHANS[i]
        if vol < 0.006:
            if ch is not None and ch.get_busy():
                ch.set_volume(0.0)
            continue
        if ch is None or not ch.get_busy():
            ch = pygame.mixer.find_channel(True)
            if ch is None:
                continue
            _ENGINE_CHANS[i] = ch
            ch.play(snd, loops=-1)
        ch.set_volume(vol)
