"""Utility-Funktionen für häufige Operationen.

Enthält Hilfsfunktionen, die Code-Duplikate reduzieren und
Sicherheit erhöhen.
"""
from typing import Any, Callable, Iterable, List, Optional, Set, TypeVar

T = TypeVar('T')


def safe_remove(item: T, collection: List[T]) -> bool:
    """Entfernt ein Item sicher aus einer Liste.
    
    Diese Funktion vermeidet RuntimeError, der auftritt wenn man
    eine Liste während der Iteration modifiziert.
    
    Args:
        item: Das zu entfernende Item
        collection: Die Liste
        
    Returns:
        True wenn das Item entfernt wurde, False wenn es nicht in der Liste war
        
    Usage:
        # Statt: state.cars.remove(car)  # kann fehlschlagen
        safe_remove(car, state.cars)
    """
    try:
        collection.remove(item)
        return True
    except ValueError:
        return False


def safe_remove_by_index(index: int, collection: List[T]) -> bool:
    """Entfernt ein Item sicher aus einer Liste per Index.
    
    Args:
        index: Der Index des zu entfernenden Items
        collection: Die Liste
        
    Returns:
        True wenn das Item entfernt wurde, False wenn Index ungültig
    """
    if 0 <= index < len(collection):
        collection.pop(index)
        return True
    return False


def filter_in_place(collection: List[T], predicate: Callable[[T], bool]) -> int:
    """Filtert eine Liste in-place und gibt die Anzahl der entfernten Items zurück.
    
    Diese Funktion ist sicher für Iterationen und vermeidet
    ConcurrentModificationError.
    
    Args:
        collection: Die zu filternde Liste
        predicate: Funktion die True zurückgibt für Items die BEHALTEN werden sollen
        
    Returns:
        Anzahl der entfernten Items
        
    Usage:
        # Entferne alle toten Autos
        removed = filter_in_place(state.cars, lambda c: not c.dead)
    """
    original_len = len(collection)
    collection[:] = [item for item in collection if predicate(item)]
    return original_len - len(collection)


def remove_all_matching(collection: List[T], predicate: Callable[[T], bool]) -> int:
    """Entfernt alle Items aus einer Liste, die ein Prädikat erfüllen.
    
    Args:
        collection: Die Liste
        predicate: Funktion die True zurückgibt für Items die ENTFERNT werden sollen
        
    Returns:
        Anzahl der entfernten Items
        
    Usage:
        # Entferne alle toten Autos
        removed = remove_all_matching(state.cars, lambda c: c.dead)
    """
    original_len = len(collection)
    collection[:] = [item for item in collection if not predicate(item)]
    return original_len - len(collection)


def remove_by_condition(
    collection: List[T],
    condition: Callable[[T], bool]
) -> List[T]:
    """Entfernt und gibt alle Items zurück, die eine Bedingung erfüllen.
    
    Args:
        collection: Die Liste
        condition: Funktion die True zurückgibt für Items die ENTFERNT werden sollen
        
    Returns:
        Liste der entfernten Items
        
    Usage:
        dead_cars = remove_by_condition(state.cars, lambda c: c.dead)
    """
    removed = [item for item in collection if condition(item)]
    collection[:] = [item for item in collection if not condition(item)]
    return removed


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Begrenzt einen Wert auf einen Bereich.
    
    Args:
        value: Der Wert
        min_val: Minimum
        max_val: Maximum
        
    Returns:
        Der begezte Wert
        
    Usage:
        speed = clamp(speed, 0.0, max_speed)
    """
    return max(min_val, min(max_val, value))


def lerp(a: float, b: float, t: float) -> float:
    """Lineare Interpolation zwischen zwei Werten.
    
    Args:
        a: Startwert
        b: Endwert
        t: Interpolationsfaktor (0.0 = a, 1.0 = b)
        
    Returns:
        Interpolierter Wert
        
    Usage:
        alpha = lerp(0.0, 1.0, progress)
    """
    return a + (b - a) * t


def distance_sq(x1: float, y1: float, x2: float, y2: float) -> float:
    """Berechnet das Quadrat der Distanz zwischen zwei Punkten (ohne sqrt).
    
    Schnellere Variante von math.hypot(x2-x1, y2-y1) ** 2
    
    Args:
        x1, y1: Koordinaten des ersten Punkts
        x2, y2: Koordinaten des zweiten Punkts
        
    Returns:
        Quadrat der Distanz
        
    Usage:
        if distance_sq(x1, y1, x2, y2) < radius_sq:
            # Punkt ist im Kreis
    """
    dx = x2 - x1
    dy = y2 - y1
    return dx * dx + dy * dy


def distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Berechnet die Distanz zwischen zwei Punkten.
    
    Args:
        x1, y1: Koordinaten des ersten Punkts
        x2, y2: Koordinaten des zweiten Punkts
        
    Returns:
        Distanz
    """
    return distance_sq(x1, y1, x2, y2) ** 0.5


def normalize_angle(angle: float) -> float:
    """Normalisiert einen Winkel auf den Bereich 0-360 Grad.
    
    Args:
        angle: Der Winkel in Grad
        
    Returns:
        Normalisierter Winkel
    """
    return angle % 360.0


def angle_diff(a: float, b: float) -> float:
    """Berechnet die kleinste Winkeldifferenz zwischen zwei Winkeln.
    
    Args:
        a: Erster Winkel in Grad
        b: Zweiter Winkel in Grad
        
    Returns:
        Kleinste Differenz im Bereich [0, 180]
    """
    return abs(((a - b + 180) % 360) - 180)
