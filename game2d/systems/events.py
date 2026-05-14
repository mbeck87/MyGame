"""Event System - Observer Pattern implementation for game2d.

Provides a centralized event bus for decoupled communication between game systems.
Usage:
    from game2d.systems.events import EventBus, EventType, Event
    
    # Subscribe to events
    def on_player_died(event: Event):
        print(f"Player died at {event.data['position']}")
    
    EventBus.subscribe(EventType.PLAYER_DIED, on_player_died)
    
    # Emit events
    EventBus.emit(EventType.PLAYER_DIED, {"position": (x, y), "killer": entity})
    
    # Unsubscribe
    EventBus.unsubscribe(EventType.PLAYER_DIED, on_player_died)
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


class EventType(Enum):
    """All game event types."""
    
    # Player events
    PLAYER_SPAWNED = auto()
    PLAYER_DIED = auto()
    PLAYER_DAMAGED = auto()
    PLAYER_HEALED = auto()
    PLAYER_ENTERED_CAR = auto()
    PLAYER_EXITED_CAR = auto()
    PLAYER_WEAPON_CHANGED = auto()
    PLAYER_MONEY_CHANGED = auto()
    PLAYER_WANTED_CHANGED = auto()
    
    # Entity events
    ENTITY_SPAWNED = auto()
    ENTITY_DIED = auto()
    ENTITY_DAMAGED = auto()
    
    # Combat events
    KILL = auto()
    SHOT_FIRED = auto()
    EXPLOSION = auto()
    
    # Crime events
    CRIME_COMMITTED = auto()
    WANTED_LEVEL_CHANGED = auto()
    WANTED_HEAT_ADDED = auto()
    
    # Vehicle events
    CAR_SPAWNED = auto()
    CAR_DESTROYED = auto()
    CAR_ENTERED = auto()
    CAR_EXITED = auto()
    CAR_DAMAGED = auto()
    
    # Pickup events
    PICKUP_COLLECTED = auto()
    PICKUP_SPAWNED = auto()
    
    # World events
    WORLD_LOADED = auto()
    GAME_STARTED = auto()
    GAME_OVER = auto()
    GAME_RESTARTED = auto()
    
    # Audio events
    AUDIO_PLAYED = auto()
    
    # UI events
    MENU_OPENED = auto()
    MENU_CLOSED = auto()
    SETTINGS_CHANGED = auto()
    
    # Service events
    SHOP_PURCHASE = auto()
    GARAGE_SERVICE = auto()
    BARBER_STYLE_CHANGED = auto()
    
    # Traffic events
    TRAFFIC_SPAWNED = auto()
    ROADBLOCK_CREATED = auto()
    ROADBLOCK_CLEARED = auto()


@dataclass
class Event:
    """Represents a game event."""
    event_type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    sender: Optional[Any] = None
    timestamp: float = field(default_factory=lambda: __import__('pygame').time.get_ticks() / 1000.0)
    
    def __post_init__(self):
        if not isinstance(self.data, dict):
            raise TypeError("Event data must be a dictionary")


# Type alias for event handlers
EventHandler = Callable[[Event], None]


class EventBus:
    """Centralized event bus for the Observer Pattern.
    
    Thread-safe event dispatching with support for:
    - Multiple listeners per event type
    - Wildcard listeners (all events)
    - One-time listeners
    - Priority-based ordering
    """
    
    _instance: Optional['EventBus'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'EventBus':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._listeners: Dict[EventType, List[Tuple[EventHandler, int, bool]]] = {}
        self._wildcard_listeners: List[Tuple[EventHandler, int, bool]] = []
        self._queue: List[Event] = []
        self._processing = False
        self._initialized = True
    
    @classmethod
    def reset(cls):
        """Reset the singleton instance (useful for testing)."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance._listeners.clear()
                cls._instance._wildcard_listeners.clear()
                cls._instance._queue.clear()
                cls._instance._processing = False
    
    def subscribe(
        self,
        event_type: Union[EventType, List[EventType]],
        handler: EventHandler,
        priority: int = 0,
        once: bool = False
    ) -> None:
        """Subscribe a handler to one or more event types.
        
        Args:
            event_type: Single EventType or list of EventTypes to subscribe to
            handler: Function to call when event is emitted
            priority: Higher priority handlers are called first (default: 0)
            once: If True, handler is automatically unsubscribed after first call
        """
        if isinstance(event_type, list):
            for et in event_type:
                self.subscribe(et, handler, priority, once)
            return
        
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        
        # Check if handler is already registered
        for i, (h, p, o) in enumerate(self._listeners[event_type]):
            if h == handler:
                # Update existing registration
                self._listeners[event_type][i] = (handler, priority, once or o)
                return
        
        self._listeners[event_type].append((handler, priority, once))
        self._listeners[event_type].sort(key=lambda x: -x[1])  # Sort by priority (descending)
    
    def subscribe_wildcard(
        self,
        handler: EventHandler,
        priority: int = 0,
        once: bool = False
    ) -> None:
        """Subscribe a handler to all event types (wildcard).
        
        Args:
            handler: Function to call for every event
            priority: Higher priority handlers are called first
            once: If True, handler is automatically unsubscribed after first call
        """
        # Check if handler is already registered
        for i, (h, p, o) in enumerate(self._wildcard_listeners):
            if h == handler:
                self._wildcard_listeners[i] = (handler, priority, once or o)
                return
        
        self._wildcard_listeners.append((handler, priority, once))
        self._wildcard_listeners.sort(key=lambda x: -x[1])
    
    def unsubscribe(
        self,
        event_type: Union[EventType, List[EventType]],
        handler: EventHandler
    ) -> bool:
        """Unsubscribe a handler from event type(s).
        
        Returns:
            True if handler was found and removed, False otherwise
        """
        if isinstance(event_type, list):
            result = False
            for et in event_type:
                result = self.unsubscribe(et, handler) or result
            return result
        
        if event_type in self._listeners:
            self._listeners[event_type] = [
                (h, p, o) for (h, p, o) in self._listeners[event_type] if h != handler
            ]
            if not self._listeners[event_type]:
                del self._listeners[event_type]
            return True
        return False
    
    def unsubscribe_wildcard(self, handler: EventHandler) -> bool:
        """Unsubscribe a wildcard handler.
        
        Returns:
            True if handler was found and removed, False otherwise
        """
        self._wildcard_listeners = [
            (h, p, o) for (h, p, o) in self._wildcard_listeners if h != handler
        ]
        return len(self._wildcard_listeners) < len(self._wildcard_listeners) + 1
    
    def unsubscribe_all(self, handler: EventHandler) -> int:
        """Unsubscribe a handler from all event types and wildcard.
        
        Returns:
            Number of subscriptions removed
        """
        count = 0
        for event_type in list(self._listeners.keys()):
            count += len([
                (h, p, o) for (h, p, o) in self._listeners[event_type] if h == handler
            ])
            self._listeners[event_type] = [
                (h, p, o) for (h, p, o) in self._listeners[event_type] if h != handler
            ]
            if not self._listeners[event_type]:
                del self._listeners[event_type]
        
        wildcard_count = len([
            (h, p, o) for (h, p, o) in self._wildcard_listeners if h == handler
        ])
        self._wildcard_listeners = [
            (h, p, o) for (h, p, o) in self._wildcard_listeners if h != handler
        ]
        count += wildcard_count
        return count
    
    def emit(self, event_type: EventType, data: Optional[Dict[str, Any]] = None, sender: Any = None) -> Event:
        """Emit an event of the given type.
        
        Args:
            event_type: The type of event to emit
            data: Optional dictionary of event data
            sender: Optional sender/origin of the event
            
        Returns:
            The created Event object
        """
        event = Event(event_type=event_type, data=data or {}, sender=sender)
        
        if self._processing:
            # Queue events if we're already processing
            self._queue.append(event)
        else:
            self._process_event(event)
        
        return event
    
    def emit_delayed(self, event_type: EventType, data: Optional[Dict[str, Any]] = None, sender: Any = None, delay_ms: float = 0) -> None:
        """Emit an event after a delay.
        
        Args:
            event_type: The type of event to emit
            data: Optional dictionary of event data
            sender: Optional sender/origin of the event
            delay_ms: Delay in milliseconds before emitting
        """
        import pygame
        
        def delayed_emit():
            pygame.time.delay(int(delay_ms))
            self.emit(event_type, data, sender)
        
        thread = threading.Thread(target=delayed_emit, daemon=True)
        thread.start()
    
    def _process_event(self, event: Event) -> None:
        """Process a single event, calling all registered handlers."""
        self._processing = True
        
        try:
            # Process wildcard listeners first
            for handler, _, once in self._wildcard_listeners[:]:
                try:
                    handler(event)
                except Exception as e:
                    import logging as std_logging
                    std_logging.getLogger("game2d.events").exception(
                        f"Error in wildcard handler for {event.event_type}: {e}"
                    )
                if once:
                    self.unsubscribe_wildcard(handler)
            
            # Process specific listeners
            if event.event_type in self._listeners:
                for handler, _, once in self._listeners[event.event_type][:]:
                    try:
                        handler(event)
                    except Exception as e:
                        import logging as std_logging
                        std_logging.getLogger("game2d.events").exception(
                            f"Error in handler for {event.event_type}: {e}"
                        )
                    if once:
                        self.unsubscribe(event.event_type, handler)
            
            # Process queued events
            while self._queue:
                queued_event = self._queue.pop(0)
                self._process_event(queued_event)
        
        finally:
            self._processing = False
    
    def clear_queue(self) -> int:
        """Clear all queued events.
        
        Returns:
            Number of events cleared
        """
        count = len(self._queue)
        self._queue.clear()
        return count
    
    def get_listeners(self, event_type: EventType) -> List[EventHandler]:
        """Get all handlers subscribed to an event type.
        
        Returns:
            List of handler functions
        """
        if event_type in self._listeners:
            return [h for h, _, _ in self._listeners[event_type]]
        return []
    
    def get_wildcard_listeners(self) -> List[EventHandler]:
        """Get all wildcard handlers.
        
        Returns:
            List of wildcard handler functions
        """
        return [h for h, _, _ in self._wildcard_listeners]
    
    @property
    def listener_count(self) -> int:
        """Get total number of active listeners."""
        count = sum(len(handlers) for handlers in self._listeners.values())
        count += len(self._wildcard_listeners)
        return count
    
    @property
    def queue_size(self) -> int:
        """Get number of queued events."""
        return len(self._queue)


# Convenience functions for common events
def emit_kill(state, entity: Any, is_cop: bool = False, killer: Any = None) -> Event:
    """Emit a kill event."""
    import pygame
    from game2d.state import current
    actual_state = state or current()
    
    return EventBus().emit(
        EventType.KILL,
        {
            "entity": entity,
            "is_cop": is_cop,
            "killer": killer,
            "position": (getattr(entity, 'x', 0), getattr(entity, 'y', 0)),
            "kill_count": getattr(actual_state, 'kill_count', 0) + 1,
        },
        sender=entity
    )


def emit_player_damaged(state, amount: float, source: Any = None) -> Event:
    """Emit a player damaged event."""
    from game2d.state import current
    actual_state = state or current()
    
    return EventBus().emit(
        EventType.PLAYER_DAMAGED,
        {
            "amount": amount,
            "source": source,
            "remaining_hp": getattr(actual_state.player, 'hp', 0) - amount,
        },
        sender=actual_state.player if actual_state else None
    )


def emit_wanted_changed(state, old_level: int, new_level: int) -> Event:
    """Emit a wanted level changed event."""
    return EventBus().emit(
        EventType.WANTED_LEVEL_CHANGED,
        {
            "old_level": old_level,
            "new_level": new_level,
        },
        sender=state.player if state else None
    )


def emit_wanted_heat_added(state, crime: str, amount: float) -> Event:
    """Emit a wanted heat added event."""
    return EventBus().emit(
        EventType.WANTED_HEAT_ADDED,
        {
            "crime": crime,
            "amount": amount,
            "total_heat": getattr(state, 'wanted_heat', 0),
        },
        sender=state.player if state else None
    )


def emit_money_changed(state, amount: float, reason: str = "unknown") -> Event:
    """Emit a player money changed event."""
    from game2d.state import current
    actual_state = state or current()
    
    return EventBus().emit(
        EventType.PLAYER_MONEY_CHANGED,
        {
            "amount": amount,
            "reason": reason,
            "new_total": getattr(actual_state.player, 'money', 0) + amount,
        },
        sender=actual_state.player if actual_state else None
    )


def emit_game_over(state, reason: str = "unknown") -> Event:
    """Emit a game over event."""
    return EventBus().emit(
        EventType.GAME_OVER,
        {
            "reason": reason,
            "score": getattr(state.player, 'score', 0) if state else 0,
            "kill_count": getattr(state, 'kill_count', 0) if state else 0,
        },
        sender=state
    )


def emit_entity_spawned(entity: Any, entity_type: str) -> Event:
    """Emit an entity spawned event."""
    return EventBus().emit(
        EventType.ENTITY_SPAWNED,
        {
            "entity": entity,
            "entity_type": entity_type,
            "position": (getattr(entity, 'x', 0), getattr(entity, 'y', 0)),
        },
        sender=entity
    )


def emit_pickup_collected(state, pickup: Any, pickup_type: str) -> Event:
    """Emit a pickup collected event."""
    return EventBus().emit(
        EventType.PICKUP_COLLECTED,
        {
            "pickup": pickup,
            "type": pickup_type,
            "position": (pickup[0], pickup[1]) if isinstance(pickup, (list, tuple)) else (0, 0),
        },
        sender=pickup
    )


# Initialize pygame for timestamp support
try:
    import pygame
    pygame.init()
except ImportError:
    pass
