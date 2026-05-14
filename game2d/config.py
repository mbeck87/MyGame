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

# ── Fahrzeugphysik: Car.update() ─────────────────────
DRIFT_MIN_SPEED             = 50      # Mindestgeschwindigkeit für Drift
DRIFT_TURN_MIN_RATIO        = 0.4     # Minimum Lenkeinfluss beim Driften
SPEED_THRESHOLD_STEER       = 5       # Mindestgeschwindigkeit für Lenkung/Angle
REVERSE_SPEED_RATIO         = 0.5     # Rückwärts: max 50% der max_spd
DRIFT_ANGLE_ALIGN           = 1.5     # Angle-Tracking-Rate beim Driften
NORMAL_ANGLE_ALIGN          = 14.0    # Angle-Tracking-Rate normal
BUILDING_COLL_CHECK_DIST    = 80      # Spatial-Optimierung: Gebäude-Check-Radius
PLAYER_BOUNDARY_MARGIN      = 40      # Pixel-Abstand zur Weltkante (Spieler)
PLAYER_PUSH_OFFSET          = 12      # Zusatz-Radius beim Spieler-Rausschieben
DUAL_HIT_DAMAGE_THRESHOLD   = 60      # Mindest-Impact für Schaden (beide Achsen)
DUAL_HIT_DAMAGE_FACTOR      = 0.09    # Schadensfaktor bei beidachsiger Kollision
SINGLE_HIT_DAMAGE_THRESHOLD = 80      # Mindest-Impact für Schaden (eine Achse)
SINGLE_HIT_DAMAGE_FACTOR    = 0.045   # Schadensfaktor bei einachsiger Kollision
SINGLE_HIT_PERP_MIN         = 0.25    # Min. Querkomponente für Schaden

# ── Fahrzeug-KI: Car.ai_update() ─────────────────────
CAR_IDLE_DECAY              = 2.5     # Geschwindigkeitsabbau ohne Fahrer
ROADBLOCK_LANE_SPEED        = 18      # Lane-Centering-Speed für Straßensperre
COP_LANE_SPEED              = 22      # Lane-Centering-Speed für Cop-Auto
LANE_CENTER_SPD             = 26      # Lane-Centering-Speed normale Autos
COP_STEERING_DIV            = 35      # Lenkung = Winkeldiff / divisor
COP_MIN_SPEED               = 155     # Mindest-Verfolgungsgeschwindigkeit
COP_MAX_SPEED_BASE          = 175     # Basis für Max-Verfolgungsgeschwindigkeit
COP_WANTED_SPEED_FACTOR     = 34      # Geschwindigkeitsbonus pro Wanted-Stern
COP_FULL_SPEED_DIST         = 220     # Unter dieser Distanz: Vollgas
COP_SPEED_GUESS_MIN         = 105     # Min. für Vorausschau-Geschwindigkeit
COP_SPEED_GUESS_OFFSET      = 70      # Vorausschau = max(min, abs(spd) + offset)
COP_STEER_ANG               = 34      # Winkeloffset für Lenkvorausschau
COP_LOOKAHEAD_FACTOR        = 1.2     # Skalierung für Zukunftsposition
COP_BLOCKER_PADDING         = 8       # Padding für Blockierungs-Kollisionstest
COP_ALT_STEER_BASE          = 52      # Basiswinkel für alternative Lenkung
COP_TURN_CD_MIN             = 0.6     # Min. Turn-Cooldown nach Blockierung
COP_TURN_CD_MAX             = 1.2     # Max. Turn-Cooldown nach Blockierung
COP_TARGET_SLOW_SPD         = 90      # Geschwindigkeitsschwelle "Ziel langsam"
COP_DEPLOY_MAX              = {3: 12, 4: 16, 5: 20}  # Max Cops per Wanted-Level
COP_DEPLOY_DIST             = 230     # Einsatzdistanz für Fußgänger-Cops
COP_DEPLOY_FWD_BASE         = -12     # Basis-Vorwärtsversatz beim Einsatz
COP_DEPLOY_FWD_STEP         = 24      # Schrittweite pro eingesetztem Cop
COP_DEPLOY_SIDE_MIN         = 34      # Mindest-Seitenabstand beim Einsatz
COP_DEPLOY_SIDE_OFFSET      = 14      # Zusatz-Seitenabstand (coll_w/2 + offset)
AI_OBS_DIST_COP             = 80      # Obstacle-Check-Radius für Cop-Autos
AI_OBS_DIST_NORMAL          = 120     # Obstacle-Check-Radius normale Autos
ARC_SPD_MIN                 = 105.0   # Mindestgeschwindigkeit Kurvennavigation
ARC_SPD_MAX                 = 148.0   # Maximalgeschwindigkeit Kurvennavigation
ARC_TIGHT_R                 = 48      # Radius-Schwelle für enge Kurve
ARC_TIGHT_SPD               = 122.0   # Maximalgeschwindigkeit bei enger Kurve
ARC_ACCEL                   = 420     # Beschleunigungsrate in Kurvennavigation
ARC_BLOCKER_DECEL           = 560     # Bremsrate bei Blockierung in Kurve
ARC_BLOCKER_YIELD           = 0.16    # Yield-Timer bei Blockierung in Kurve
INTERSECTION_AHEAD          = 150     # Vorausschau-Distanz für Kreuzungen
BRAKE_DECAY                 = 2.6     # Bremsrate bei roter Ampel / Yield
INTERSECTION_PERP_TOL       = 34      # Quer-Toleranz für Kreuzungserkennung
INTERSECTION_ZONE_MIN       = 18      # Kreuzungszone: Mindestabstand
INTERSECTION_ZONE_MAX       = 94      # Kreuzungszone: Maximalabstand
BRAKE_DECAY_BLOCKED         = 3.0     # Bremsrate bei Blockierung
YIELD_TIMER_BLOCKED         = 0.12    # Yield-Timer bei Blockierung
CAR_COLL_TURN_CD_MIN        = 1.2     # Min. Turn-Cooldown nach Fahrzeugkollision
CAR_COLL_TURN_CD_MAX        = 2.6     # Max. Turn-Cooldown nach Fahrzeugkollision
