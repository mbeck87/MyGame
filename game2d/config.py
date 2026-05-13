"""Globale Konstanten: Fenstergröße, Welt-Geometrie, Farben."""
from game2d import settings as _settings

# ── Fenster ──────────────────────────────────────────────
# Fenstergröße wird beim Import aus ``settings.json`` gelesen, damit alle
# Module, die ``W``/``H`` direkt importieren, einen konsistenten Wert sehen.
# Änderungen über das Options-Menü erfordern einen Neustart des Prozesses.
W, H = _settings.parse_resolution(_settings.load().get('resolution', '1280x800'))

# ── Farben ───────────────────────────────────────────────
ASPHALT  = (55, 55, 60)
GRASS    = (60, 130, 55)
LINE     = (235, 215, 70)
SIDEW    = (170, 170, 175)
ROOF1    = (140, 90, 70)
ROOF2    = (110, 70, 60)
WALL1    = (210, 195, 165)
WALL2    = (180, 160, 130)
WIN      = (120, 200, 240)
WIN_LIT  = (250, 220, 110)
DOOR     = (90, 55, 35)
COP_BLUE = (30, 60, 180)
COP_DARK = (15, 30, 90)
SKIN     = (235, 195, 160)

WATER_DEEP = (28, 70, 130)
WATER_MID  = (40, 100, 160)
WATER_LITE = (95, 160, 210)
SAND       = (225, 205, 155)
TIRE_BLOOD = (135, 0, 0)
TIRE_SKID  = (22, 20, 18)

# ── Welt-Geometrie ───────────────────────────────────────
WORLD_W, WORLD_H = 6000, 6000
BLOCK       = 600    # Stadtblockgröße
ROAD_W      = 118    # Fahrbahnbreite
SIDEWALK_W  = 34     # Gehsteigbreite je Straßenseite
WATER_W     = 220    # Wasserring-Breite am Kartenrand
BEACH_W     = 110    # Sandstrand-Breite zwischen Wasser und Stadt

INNER_LO   = WATER_W + BEACH_W
INNER_HI_X = WORLD_W - WATER_W - BEACH_W
INNER_HI_Y = WORLD_H - WATER_W - BEACH_W
ROAD_EDGE_MARGIN = BLOCK // 2
ROAD_LO    = INNER_LO + ROAD_EDGE_MARGIN
ROAD_HI_X  = INNER_HI_X - ROAD_EDGE_MARGIN
ROAD_HI_Y  = INNER_HI_Y - ROAD_EDGE_MARGIN

# ── Waffen-Definitionen ──────────────────────────────────
WPN_NAMES = ['Lichtschwert', 'Pistole', 'SMG', 'Schrotflinte', 'MG', 'Raketenwerfer']
WPN_RATE  = [0.55, 0.4, 0.08, 0.85, 0.05, 1.6]
WPN_DMG   = [145, 35, 15, 80, 28, 0]   # Rakete: Schaden in do_explosion()
WPN_PEL   = [1, 1, 1, 6, 1, 1]
WPN_SPRD  = [0, 0.03, 0.08, 0.22, 0.06, 0]
WPN_AUTO  = [False, False, True, False, True, False]

# ── Pickup-Definitionen ──────────────────────────────────
PICKUP_AMMO    = {2: 60, 3: 10, 4: 120, 5: 3}
PICKUP_COLOR   = {'hp': (40,220,80), 'armor': (200,200,200), 2: (220,210,40), 3: (220,120,40), 4: (210,40,40), 5: (180,60,255)}
PICKUP_LABEL   = {'hp': 'HP', 'armor': 'ARMOR', 2: 'SMG', 3: 'SG', 4: 'MG', 5: 'RPG'}
PICKUP_RESPAWN = 20.0   # Sekunden bis zur Wiederkehr
