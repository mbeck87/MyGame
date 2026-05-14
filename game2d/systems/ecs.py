"""Entity-Component-System (ECS) Basisimplementierung.

Dieses Modul bietet eine einfache ECS-Infrastruktur für zukünftige
Erweiterungen des Spiels. Das aktuelle Spiel verwendet noch keine
ECS-Architektur, aber dieses Modul dient als Grundlage für eine
schrittweise Migration.

ECS-Konzept:
- Entities: Einfache Identifier (Integer oder UUID)
- Components: Datencontainer (keine Logik)
- Systems: Funktionen/Objekte die auf Components operieren

Usage:
    # Erstelle einen ECS-Manager
    ecs = ECSManager()
    
    # Erstelle eine Entity
    entity = ecs.create_entity()
    
    # Füge Components hinzu
    ecs.add_component(entity, Position(x=100, y=200))
    ecs.add_component(entity, Velocity(vx=10, vy=5))
    
    # Hole Components
    pos = ecs.get_component(entity, Position)
    
    # Iteriere über Entities mit bestimmten Components
    for entity in ecs.get_entities_with(Position, Velocity):
        pos = ecs.get_component(entity, Position)
        vel = ecs.get_component(entity, Velocity)
        # Verarbeite Entity...
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Generic,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union
)

# Typen für Entity-IDs
EntityID = Union[int, str, uuid.UUID]

# Typ-Variable für Components
C = TypeVar('C', bound='Component')


class Component:
    """Basisklasse für alle Components.
    
    Components sind einfache Datencontainer ohne Logik.
    Sie sollten als Dataclasses definiert werden.
    """
    pass


@dataclass
class Position(Component):
    """Position-Komponente: 2D-Koordinaten."""
    x: float = 0.0
    y: float = 0.0


@dataclass
class Velocity(Component):
    """Geschwindigkeit-Komponente: 2D-Geschwindigkeit."""
    vx: float = 0.0
    vy: float = 0.0


@dataclass
class Acceleration(Component):
    """Beschleunigung-Komponente: 2D-Beschleunigung."""
    ax: float = 0.0
    ay: float = 0.0


@dataclass
class Health(Component):
    """Gesundheit-Komponente."""
    hp: int = 100
    max_hp: int = 100


@dataclass
class Sprite(Component):
    """Sprite-Komponente für Rendering."""
    surface: Any = None
    rect: Any = None
    angle: float = 0.0


@dataclass
class Collider(Component):
    """Kollisions-Komponente."""
    width: float = 0.0
    height: float = 0.0
    offset_x: float = 0.0
    offset_y: float = 0.0


class ECSManager(Generic[C]):
    """Manager für Entities und Components.
    
    Verwaltet die Zuordnung von Components zu Entities und bietet
    Methoden zum Abfragen von Entities mit bestimmten Components.
    """
    
    def __init__(self):
        """Initialisiert den ECS-Manager."""
        self._entities: Set[EntityID] = set()
        self._components: Dict[Type[Component], Dict[EntityID, Component]] = {}
        self._entity_components: Dict[EntityID, Dict[Type[Component], Component]] = {}
        self._next_id: int = 1
        self._systems: List[Tuple[int, Callable[[float], None]]] = []
    
    def create_entity(self) -> EntityID:
        """Erstellt eine neue Entity.
        
        Returns:
            Die neue Entity-ID
        """
        entity_id = self._next_id
        self._next_id += 1
        self._entities.add(entity_id)
        self._entity_components[entity_id] = {}
        return entity_id
    
    def create_entity_with_uuid(self) -> EntityID:
        """Erstellt eine neue Entity mit UUID.
        
        Returns:
            Die neue Entity-ID (UUID)
        """
        entity_id = uuid.uuid4()
        self._entities.add(entity_id)
        self._entity_components[entity_id] = {}
        return entity_id
    
    def destroy_entity(self, entity: EntityID) -> None:
        """Zerstört eine Entity und alle ihre Components.
        
        Args:
            entity: Die zu zerstörende Entity-ID
        """
        if entity not in self._entities:
            return
        
        # Entferne alle Components dieser Entity
        if entity in self._entity_components:
            for component_type, component in self._entity_components[entity].items():
                if component_type in self._components:
                    self._components[component_type].pop(entity, None)
            del self._entity_components[entity]
        
        self._entities.discard(entity)
    
    def add_component(self, entity: EntityID, component: Component) -> None:
        """Fügt eine Component zu einer Entity hinzu.
        
        Args:
            entity: Die Entity-ID
            component: Die Component-Instanz
        """
        if entity not in self._entities:
            raise ValueError(f"Entity {entity} existiert nicht")
        
        component_type = type(component)
        
        # Füge zur Entity-spezifischen Component-Liste hinzu
        self._entity_components[entity][component_type] = component
        
        # Füge zur Typ-spezifischen Component-Liste hinzu
        if component_type not in self._components:
            self._components[component_type] = {}
        self._components[component_type][entity] = component
    
    def remove_component(self, entity: EntityID, component_type: Type[Component]) -> Optional[Component]:
        """Entfernt eine Component von einer Entity.
        
        Args:
            entity: Die Entity-ID
            component_type: Der Component-Typ
            
        Returns:
            Die entfernte Component oder None
        """
        if entity not in self._entities:
            return None
        
        if component_type in self._entity_components.get(entity, {}):
            component = self._entity_components[entity].pop(component_type)
            if component_type in self._components:
                self._components[component_type].pop(entity, None)
            return component
        return None
    
    def get_component(self, entity: EntityID, component_type: Type[Component]) -> Optional[Component]:
        """Holt eine Component von einer Entity.
        
        Args:
            entity: Die Entity-ID
            component_type: Der Component-Typ
            
        Returns:
            Die Component oder None
        """
        return self._entity_components.get(entity, {}).get(component_type)
    
    def has_component(self, entity: EntityID, component_type: Type[Component]) -> bool:
        """Prüft ob eine Entity eine bestimmte Component hat.
        
        Args:
            entity: Die Entity-ID
            component_type: Der Component-Typ
            
        Returns:
            True wenn die Entity die Component hat
        """
        return component_type in self._entity_components.get(entity, {})
    
    def has_components(self, entity: EntityID, *component_types: Type[Component]) -> bool:
        """Prüft ob eine Entity alle angegebenen Components hat.
        
        Args:
            entity: Die Entity-ID
            *component_types: Die Component-Typen
            
        Returns:
            True wenn die Entity alle Components hat
        """
        entity_components = self._entity_components.get(entity, {})
        return all(ct in entity_components for ct in component_types)
    
    def get_entities_with(self, *component_types: Type[Component]) -> Iterator[EntityID]:
        """Gibt ein Iterator über alle Entities zurück, die alle angegebenen Components haben.
        
        Args:
            *component_types: Die Component-Typen
            
        Yields:
            Entity-IDs
        """
        if not component_types:
            yield from self._entities
            return
        
        # Finde Entities mit dem ersten Component-Typ
        first_type = component_types[0]
        if first_type not in self._components:
            return
        
        candidates = set(self._components[first_type].keys())
        
        # Filtere nach weiteren Component-Typen
        for ct in component_types[1:]:
            if ct not in self._components:
                candidates.clear()
                break
            candidates &= set(self._components[ct].keys())
        
        for entity in candidates:
            yield entity
    
    def get_all_components(self, entity: EntityID) -> Dict[Type[Component], Component]:
        """Gibt alle Components einer Entity zurück.
        
        Args:
            entity: Die Entity-ID
            
        Returns:
            Dictionary von Component-Typen zu Component-Instanzen
        """
        return dict(self._entity_components.get(entity, {}))
    
    def get_entities_count(self) -> int:
        """Gibt die Anzahl der Entities zurück.
        
        Returns:
            Anzahl der Entities
        """
        return len(self._entities)
    
    def get_component_count(self, component_type: Type[Component]) -> int:
        """Gibt die Anzahl der Entities mit einer bestimmten Component zurück.
        
        Args:
            component_type: Der Component-Typ
            
        Returns:
            Anzahl der Entities mit dieser Component
        """
        return len(self._components.get(component_type, {}))
    
    def clear(self) -> None:
        """Löscht alle Entities und Components."""
        self._entities.clear()
        self._components.clear()
        self._entity_components.clear()
        self._next_id = 1
    
    # =========================================================================
    # System Management
    # =========================================================================
    
    def add_system(self, system: Callable[[float], None], priority: int = 0) -> None:
        """Fügt ein System hinzu.
        
        Args:
            system: Die System-Funktion (dt -> None)
            priority: Ausführungsreihenfolge (niedrigere Werte werden zuerst ausgeführt)
        """
        self._systems.append((priority, system))
        self._systems.sort(key=lambda x: x[0])
    
    def remove_system(self, system: Callable[[float], None]) -> bool:
        """Entfernt ein System.
        
        Args:
            system: Die zu entfernende System-Funktion
            
        Returns:
            True wenn das System entfernt wurde
        """
        for i, (_, s) in enumerate(self._systems):
            if s is system:
                self._systems.pop(i)
                return True
        return False
    
    def update(self, dt: float) -> None:
        """Führt alle Systeme aus.
        
        Args:
            dt: Delta-Time seit dem letzten Frame
        """
        for _, system in self._systems:
            system(dt)


# =============================================================================
# System-Beispiele
# =============================================================================

class MovementSystem:
    """System für Bewegungs-Updates.
    
    Aktualisiert die Position von Entities basierend auf ihrer
    Geschwindigkeit.
    """
    
    def __init__(self, ecs: ECSManager):
        self.ecs = ecs
    
    def __call__(self, dt: float) -> None:
        """Führt das System aus.
        
        Args:
            dt: Delta-Time
        """
        for entity in self.ecs.get_entities_with(Position, Velocity):
            pos = self.ecs.get_component(entity, Position)
            vel = self.ecs.get_component(entity, Velocity)
            
            if pos and vel:
                pos.x += vel.vx * dt
                pos.y += vel.vy * dt


class GravitySystem:
    """System für Schwerkraft.
    
    Wendet Schwerkraft auf Entities mit Velocity an.
    """
    
    def __init__(self, ecs: ECSManager, gravity: float = 9.8):
        self.ecs = ecs
        self.gravity = gravity
    
    def __call__(self, dt: float) -> None:
        """Führt das System aus.
        
        Args:
            dt: Delta-Time
        """
        for entity in self.ecs.get_entities_with(Velocity):
            vel = self.ecs.get_component(entity, Velocity)
            if vel:
                vel.vy += self.gravity * dt


# =============================================================================
# Globale ECS-Instanz (optional)
# =============================================================================

_global_ecs: Optional[ECSManager] = None


def get_ecs() -> ECSManager:
    """Gibt die globale ECS-Instanz zurück oder erstellt eine neue.
    
    Returns:
        Die globale ECS-Instanz
    """
    global _global_ecs
    if _global_ecs is None:
        _global_ecs = ECSManager()
    return _global_ecs


def set_ecs(ecs: ECSManager) -> None:
    """Setzt die globale ECS-Instanz.
    
    Args:
        ecs: Die neue ECS-Instanz
    """
    global _global_ecs
    _global_ecs = ecs


def reset_ecs() -> None:
    """Setzt die globale ECS-Instanz zurück."""
    global _global_ecs
    if _global_ecs is not None:
        _global_ecs.clear()
    _global_ecs = None
