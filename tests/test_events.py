"""Unit tests for the Event System (Observer Pattern)."""
import unittest
from unittest.mock import MagicMock, patch

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game2d.systems.events import (
    Event,
    EventBus,
    EventType,
    emit_kill,
    emit_player_damaged,
    emit_wanted_changed,
    emit_wanted_heat_added,
    emit_money_changed,
    emit_game_over,
    emit_entity_spawned,
    emit_pickup_collected,
)


class TestEvent(unittest.TestCase):
    """Tests for the Event dataclass."""

    def setUp(self):
        EventBus.reset()

    def test_event_creation(self):
        """Test basic event creation."""
        event = Event(EventType.PLAYER_DIED, {"reason": "test"})
        self.assertEqual(event.event_type, EventType.PLAYER_DIED)
        self.assertEqual(event.data, {"reason": "test"})
        self.assertIsNone(event.sender)
        self.assertIsNotNone(event.timestamp)

    def test_event_with_sender(self):
        """Test event with sender."""
        sender = MagicMock()
        event = Event(EventType.KILL, {"amount": 10}, sender=sender)
        self.assertEqual(event.sender, sender)

    def test_event_data_must_be_dict(self):
        """Test that event data must be a dictionary."""
        with self.assertRaises(TypeError):
            Event(EventType.PLAYER_DIED, "not a dict")

    def test_event_data_default(self):
        """Test event with default empty data."""
        event = Event(EventType.ENTITY_SPAWNED)
        self.assertEqual(event.data, {})


class TestEventBusSingleton(unittest.TestCase):
    """Tests for EventBus singleton pattern."""

    def setUp(self):
        EventBus.reset()

    def test_singleton(self):
        """Test that EventBus is a singleton."""
        bus1 = EventBus()
        bus2 = EventBus()
        self.assertIs(bus1, bus2)

    def test_reset(self):
        """Test resetting the EventBus."""
        bus = EventBus()
        
        def handler(event):
            pass
        
        bus.subscribe(EventType.PLAYER_DIED, handler)
        self.assertEqual(bus.listener_count, 1)
        
        EventBus.reset()
        self.assertEqual(bus.listener_count, 0)


class TestEventBusSubscribe(unittest.TestCase):
    """Tests for EventBus subscription methods."""

    def setUp(self):
        EventBus.reset()
        self.bus = EventBus()

    def test_subscribe_single(self):
        """Test subscribing to a single event type."""
        handler = MagicMock()
        self.bus.subscribe(EventType.PLAYER_DIED, handler)
        
        self.assertEqual(self.bus.listener_count, 1)
        self.assertIn(handler, self.bus.get_listeners(EventType.PLAYER_DIED))

    def test_subscribe_multiple(self):
        """Test subscribing to multiple event types."""
        handler = MagicMock()
        self.bus.subscribe(
            [EventType.PLAYER_DIED, EventType.ENTITY_DIED],
            handler
        )
        
        self.assertEqual(self.bus.listener_count, 2)
        self.assertIn(handler, self.bus.get_listeners(EventType.PLAYER_DIED))
        self.assertIn(handler, self.bus.get_listeners(EventType.ENTITY_DIED))

    def test_subscribe_with_priority(self):
        """Test subscribing with priority."""
        handler1 = MagicMock()
        handler2 = MagicMock()
        
        self.bus.subscribe(EventType.PLAYER_DIED, handler1, priority=1)
        self.bus.subscribe(EventType.PLAYER_DIED, handler2, priority=2)
        
        listeners = self.bus.get_listeners(EventType.PLAYER_DIED)
        # Higher priority should come first
        self.assertEqual(listeners[0], handler2)
        self.assertEqual(listeners[1], handler1)

    def test_subscribe_once(self):
        """Test subscribing with once=True."""
        handler = MagicMock()
        self.bus.subscribe(EventType.PLAYER_DIED, handler, once=True)
        
        self.bus.emit(EventType.PLAYER_DIED, {"test": 1})
        self.assertEqual(handler.call_count, 1)
        
        # Handler should be unsubscribed after first call
        self.bus.emit(EventType.PLAYER_DIED, {"test": 2})
        self.assertEqual(handler.call_count, 1)

    def test_subscribe_wildcard(self):
        """Test wildcard subscription."""
        handler = MagicMock()
        self.bus.subscribe_wildcard(handler)
        
        self.assertIn(handler, self.bus.get_wildcard_listeners())
        
        self.bus.emit(EventType.PLAYER_DIED, {})
        self.assertEqual(handler.call_count, 1)
        
        self.bus.emit(EventType.ENTITY_SPAWNED, {})
        self.assertEqual(handler.call_count, 2)

    def test_subscribe_duplicate(self):
        """Test subscribing the same handler multiple times."""
        handler = MagicMock()
        self.bus.subscribe(EventType.PLAYER_DIED, handler, priority=1)
        self.bus.subscribe(EventType.PLAYER_DIED, handler, priority=2)
        
        # Should only have one subscription (updated)
        self.assertEqual(len(self.bus.get_listeners(EventType.PLAYER_DIED)), 1)


class TestEventBusUnsubscribe(unittest.TestCase):
    """Tests for EventBus unsubscribe methods."""

    def setUp(self):
        EventBus.reset()
        self.bus = EventBus()

    def test_unsubscribe_single(self):
        """Test unsubscribing from a single event type."""
        handler = MagicMock()
        self.bus.subscribe(EventType.PLAYER_DIED, handler)
        
        result = self.bus.unsubscribe(EventType.PLAYER_DIED, handler)
        
        self.assertTrue(result)
        self.assertEqual(self.bus.listener_count, 0)

    def test_unsubscribe_multiple(self):
        """Test unsubscribing from multiple event types."""
        handler = MagicMock()
        self.bus.subscribe(
            [EventType.PLAYER_DIED, EventType.ENTITY_DIED],
            handler
        )
        
        result = self.bus.unsubscribe(
            [EventType.PLAYER_DIED, EventType.ENTITY_DIED],
            handler
        )
        
        self.assertTrue(result)
        self.assertEqual(self.bus.listener_count, 0)

    def test_unsubscribe_wildcard(self):
        """Test unsubscribing wildcard handler."""
        handler = MagicMock()
        self.bus.subscribe_wildcard(handler)
        
        result = self.bus.unsubscribe_wildcard(handler)
        
        self.assertTrue(result)
        self.assertEqual(len(self.bus.get_wildcard_listeners()), 0)

    def test_unsubscribe_all(self):
        """Test unsubscribing from all event types."""
        handler = MagicMock()
        self.bus.subscribe(EventType.PLAYER_DIED, handler)
        self.bus.subscribe(EventType.ENTITY_DIED, handler)
        self.bus.subscribe_wildcard(handler)
        
        count = self.bus.unsubscribe_all(handler)
        
        self.assertEqual(count, 3)
        self.assertEqual(self.bus.listener_count, 0)

    def test_unsubscribe_nonexistent(self):
        """Test unsubscribing a handler that's not subscribed."""
        handler = MagicMock()
        result = self.bus.unsubscribe(EventType.PLAYER_DIED, handler)
        self.assertFalse(result)


class TestEventBusEmit(unittest.TestCase):
    """Tests for EventBus emit methods."""

    def setUp(self):
        EventBus.reset()
        self.bus = EventBus()

    def test_emit_no_listeners(self):
        """Test emitting an event with no listeners."""
        event = self.bus.emit(EventType.PLAYER_DIED, {"reason": "test"})
        
        self.assertEqual(event.event_type, EventType.PLAYER_DIED)
        self.assertEqual(event.data, {"reason": "test"})

    def test_emit_with_listeners(self):
        """Test emitting an event with listeners."""
        handler = MagicMock()
        self.bus.subscribe(EventType.PLAYER_DIED, handler)
        
        self.bus.emit(EventType.PLAYER_DIED, {"reason": "test"})
        
        self.assertEqual(handler.call_count, 1)
        self.assertEqual(handler.call_args[0][0].event_type, EventType.PLAYER_DIED)
        self.assertEqual(handler.call_args[0][0].data, {"reason": "test"})

    def test_emit_with_sender(self):
        """Test emitting an event with a sender."""
        handler = MagicMock()
        sender = MagicMock()
        self.bus.subscribe(EventType.KILL, handler)
        
        self.bus.emit(EventType.KILL, {"amount": 10}, sender=sender)
        
        self.assertEqual(handler.call_args[0][0].sender, sender)

    def test_emit_nested(self):
        """Test nested event emission."""
        handler1 = MagicMock()
        handler2 = MagicMock()
        
        def nested_handler(event):
            handler1()
            self.bus.emit(EventType.ENTITY_DIED, {})
        
        self.bus.subscribe(EventType.PLAYER_DIED, nested_handler)
        self.bus.subscribe(EventType.ENTITY_DIED, handler2)
        
        self.bus.emit(EventType.PLAYER_DIED, {})
        
        self.assertEqual(handler1.call_count, 1)
        self.assertEqual(handler2.call_count, 1)

    def test_emit_queue_processing(self):
        """Test that events are queued during processing."""
        handler = MagicMock()
        
        def recursive_handler(event):
            handler()
            if handler.call_count < 5:
                self.bus.emit(EventType.PLAYER_DIED, {})
        
        self.bus.subscribe(EventType.PLAYER_DIED, recursive_handler)
        self.bus.emit(EventType.PLAYER_DIED, {})
        
        # All events should be processed
        self.assertEqual(handler.call_count, 5)


class TestConvenienceFunctions(unittest.TestCase):
    """Tests for convenience event emission functions."""

    def setUp(self):
        EventBus.reset()
        self.bus = EventBus()

    @patch('game2d.systems.events.pygame')
    def test_emit_kill(self, mock_pygame):
        """Test emit_kill convenience function."""
        mock_pygame.time.get_ticks.return_value = 1000
        
        entity = MagicMock()
        entity.x = 100
        entity.y = 200
        
        state = MagicMock()
        state.kill_count = 10
        
        event = emit_kill(state, entity, is_cop=True, killer=MagicMock())
        
        self.assertEqual(event.event_type, EventType.KILL)
        self.assertEqual(event.data["is_cop"], True)
        self.assertEqual(event.data["position"], (100, 200))

    @patch('game2d.systems.events.pygame')
    def test_emit_player_damaged(self, mock_pygame):
        """Test emit_player_damaged convenience function."""
        mock_pygame.time.get_ticks.return_value = 1000
        
        state = MagicMock()
        state.player.hp = 100
        
        event = emit_player_damaged(state, 10.0, source=MagicMock())
        
        self.assertEqual(event.event_type, EventType.PLAYER_DAMAGED)
        self.assertEqual(event.data["amount"], 10.0)
        self.assertEqual(event.data["remaining_hp"], 90)

    def test_emit_wanted_changed(self):
        """Test emit_wanted_changed convenience function."""
        state = MagicMock()
        state.player = MagicMock()
        
        event = emit_wanted_changed(state, 2, 3)
        
        self.assertEqual(event.event_type, EventType.WANTED_LEVEL_CHANGED)
        self.assertEqual(event.data["old_level"], 2)
        self.assertEqual(event.data["new_level"], 3)

    def test_emit_wanted_heat_added(self):
        """Test emit_wanted_heat_added convenience function."""
        state = MagicMock()
        state.wanted_heat = 100
        
        event = emit_wanted_heat_added(state, "kill_ped", 50)
        
        self.assertEqual(event.event_type, EventType.WANTED_HEAT_ADDED)
        self.assertEqual(event.data["crime"], "kill_ped")
        self.assertEqual(event.data["amount"], 50)

    def test_emit_money_changed(self):
        """Test emit_money_changed convenience function."""
        state = MagicMock()
        state.player.money = 1000
        
        event = emit_money_changed(state, 50, reason="shop_purchase")
        
        self.assertEqual(event.event_type, EventType.PLAYER_MONEY_CHANGED)
        self.assertEqual(event.data["amount"], 50)
        self.assertEqual(event.data["reason"], "shop_purchase")
        self.assertEqual(event.data["new_total"], 1050)

    def test_emit_game_over(self):
        """Test emit_game_over convenience function."""
        state = MagicMock()
        state.player.score = 5000
        state.kill_count = 25
        
        event = emit_game_over(state, reason="killed_by_cop")
        
        self.assertEqual(event.event_type, EventType.GAME_OVER)
        self.assertEqual(event.data["reason"], "killed_by_cop")
        self.assertEqual(event.data["score"], 5000)
        self.assertEqual(event.data["kill_count"], 25)

    def test_emit_entity_spawned(self):
        """Test emit_entity_spawned convenience function."""
        entity = MagicMock()
        entity.x = 50
        entity.y = 60
        
        event = emit_entity_spawned(entity, "pedestrian")
        
        self.assertEqual(event.event_type, EventType.ENTITY_SPAWNED)
        self.assertEqual(event.data["entity"], entity)
        self.assertEqual(event.data["entity_type"], "pedestrian")
        self.assertEqual(event.data["position"], (50, 60))

    def test_emit_pickup_collected(self):
        """Test emit_pickup_collected convenience function."""
        pickup = [100, 200, 1, 20]
        
        event = emit_pickup_collected(MagicMock(), pickup, "health")
        
        self.assertEqual(event.event_type, EventType.PICKUP_COLLECTED)
        self.assertEqual(event.data["pickup"], pickup)
        self.assertEqual(event.data["type"], "health")
        self.assertEqual(event.data["position"], (100, 200))


class TestEventBusClearQueue(unittest.TestCase):
    """Tests for queue management."""

    def setUp(self):
        EventBus.reset()
        self.bus = EventBus()

    def test_clear_queue(self):
        """Test clearing the event queue."""
        # Emit events without listeners to queue them
        self.bus.emit(EventType.PLAYER_DIED, {})
        
        # The event is processed immediately, so queue should be empty
        self.assertEqual(self.bus.queue_size, 0)

    def test_queue_size(self):
        """Test queue_size property."""
        self.assertEqual(self.bus.queue_size, 0)


class TestEventTypeEnum(unittest.TestCase):
    """Tests for EventType enum."""

    def test_all_event_types_unique(self):
        """Test that all event types are unique."""
        values = set()
        for event_type in EventType:
            self.assertNotIn(event_type.value, values)
            values.add(event_type.value)

    def test_event_type_count(self):
        """Test that we have a reasonable number of event types."""
        self.assertGreater(len(EventType), 20)


if __name__ == "__main__":
    unittest.main()
