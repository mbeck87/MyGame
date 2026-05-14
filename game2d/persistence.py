"""Score-Persistenz und Namenseingabe."""
import json
import os
import re
import sys
import pygame

from game2d.systems.validation import validate_scores, ValidationError

SCORES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scores.json")
MAX_HIGH_SCORES = 10
MAX_NAME_LENGTH = 18
MIN_NAME_LENGTH = 1
# Erlaubte Zeichen: Buchstaben, Zahlen, Leerzeichen, Bindestriche, Unterstriche
ALLOWED_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9 \-_]+$')
# Verbotenes Muster für Path Traversal
FORBIDDEN_PATH_PATTERN = re.compile(r'[/\\:*?"<>|]')


def load_data():
    """Lädt die Scores-Daten mit Validierung."""
    try:
        with open(SCORES_FILE) as f:
            data = json.load(f)
        # Validierung durchführen und Defaults anwenden
        validated, _ = validate_scores(data)
        return validated
    except Exception:
        return {"scores": [], "last_name": "Spieler"}


def save_score(name, money):
    data = load_data()
    if isinstance(data, list):
        data = {"scores": data, "last_name": name}
    data["last_name"] = name
    data.setdefault("scores", []).append({"name": name, "money": money})
    data["scores"].sort(key=lambda s: s["money"], reverse=True)
    data["scores"] = data["scores"][:MAX_HIGH_SCORES]
    with open(SCORES_FILE, "w") as f:
        json.dump(data, f)
    return data["scores"]


def load_scores():
    data = load_data()
    if isinstance(data, list):
        return data
    return data.get("scores", [])


def load_last_name():
    data = load_data()
    if isinstance(data, dict):
        return data.get("last_name", "Spieler")
    return "Spieler"


def save_last_name(name):
    """Speichert den letzten verwendeten Namen (mit Sanitizing)."""
    sanitized = sanitize_name(name) if name else "Spieler"
    data = load_data()
    if isinstance(data, list):
        data = {"scores": data, "last_name": sanitized}
    data["last_name"] = sanitized
    with open(SCORES_FILE, "w") as f:
        json.dump(data, f)


def validate_name(name: str) -> bool:
    """Validiert einen Spielernamen.
    
    Args:
        name: Der zu validierende Name
        
    Returns:
        True wenn der Name gültig ist, sonst False
    """
    if not isinstance(name, str):
        return False
    # Länge prüfen
    stripped = name.strip()
    if len(stripped) < MIN_NAME_LENGTH:
        return False
    if len(stripped) > MAX_NAME_LENGTH:
        return False
    # Erlaubte Zeichen prüfen
    if not ALLOWED_NAME_PATTERN.match(stripped):
        return False
    # Path Traversal Schutz
    if FORBIDDEN_PATH_PATTERN.search(stripped):
        return False
    return True


def sanitize_name(name: str) -> str:
    """Bereinigt einen Namen von gefährlichen Zeichen.
    
    Args:
        name: Der zu bereinigende Name
        
    Returns:
        Der bereinigte Name
    """
    if not isinstance(name, str):
        return "Spieler"
    # Entferne verbotene Zeichen
    sanitized = FORBIDDEN_PATH_PATTERN.sub("", name)
    # Entferne nicht erlaubte Zeichen
    sanitized = "".join(c for c in sanitized if c.isalnum() or c in " _- ")
    # Trimme und begrenze Länge
    sanitized = sanitized.strip()[:MAX_NAME_LENGTH]
    return sanitized if sanitized else "Spieler"


def name_input_screen(screen, W, H, BIG, MED, FONT):
    """Zeigt Namenseingabe; gibt eingegebenen Namen zurück."""
    name = load_last_name()
    cursor_vis = True
    cursor_timer = 0.0
    clk = pygame.time.Clock()
    while True:
        dt = clk.tick(60) / 1000
        cursor_timer += dt
        if cursor_timer >= 0.5:
            cursor_timer = 0.0
            cursor_vis = not cursor_vis
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_RETURN:
                    sanitized = sanitize_name(name)
                    if validate_name(sanitized):
                        save_last_name(sanitized)
                        return sanitized
                elif e.key == pygame.K_BACKSPACE:
                    name = name[:-1]
                elif e.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                elif len(name) < MAX_NAME_LENGTH:
                    # Nur erlaubte druckbare Zeichen akzeptieren
                    if e.unicode and e.unicode.isprintable():
                        char = e.unicode
                        # Prüfe ob das einzelne Zeichen erlaubt ist
                        if char.isalnum() or char in " _- ":
                            name += char
        screen.fill((20, 20, 30))
        t = BIG.render("Mini GTA 2D", 1, (220, 60, 60))
        screen.blit(t, (W//2 - t.get_width()//2, H//2 - 180))
        t2 = MED.render("Dein Name:", 1, (200, 200, 200))
        screen.blit(t2, (W//2 - t2.get_width()//2, H//2 - 80))
        disp = name + ("|" if cursor_vis else " ")
        box_w = 340
        pygame.draw.rect(screen, (50, 50, 70), (W//2 - box_w//2, H//2 - 30, box_w, 48), border_radius=6)
        pygame.draw.rect(screen, (120, 120, 200), (W//2 - box_w//2, H//2 - 30, box_w, 48), 2, border_radius=6)
        nt = MED.render(disp, 1, (255, 255, 255))
        screen.blit(nt, (W//2 - nt.get_width()//2, H//2 - 22))
        hint = FONT.render("[ENTER] Starten   [ESC] Beenden", 1, (140, 140, 160))
        screen.blit(hint, (W//2 - hint.get_width()//2, H//2 + 40))
        pygame.display.flip()
