"""Tests für das Entity-Component-System."""
import unittest

from game2d.systems.ecs import (
    ECSManager,
    Component,
    Position,
    Velocity,
    Health,
    Collider,
    MovementSystem,
    GravitySystem,
    get_ecs,
    set_ecs,
    reset_ecs,
)


class TestECSManager(unittest.TestCase):
    """Testet den ECSManager."""

    def setUp(self):
        """Erstellt einen neuen ECSManager für jeden Test."""
        self.ecs = ECSManager()

    def tearDown(self):
        """Bereinigt."""
        reset_ecs()

    def test_create_entity(self):
        """Testet das Erstellen einer Entity."""
        entity = self.ecs.create_entity()
        self.assertEqual(entity, 1)
        self.assertIn(entity, self.ecs._entities)

    def test_create_multiple_entities(self):
        """Testet das Erstellen mehrerer Entities."""
        e1 = self.ecs.create_entity()
        e2 = self.ecs.create_entity()
        e3 = self.ecs.create_entity()
        
        self.assertEqual(e1, 1)
        self.assertEqual(e2, 2)
        self.assertEqual(e3, 3)

    def test_create_entity_with_uuid(self):
        """Testet das Erstellen einer Entity mit UUID."""
        import uuid
        entity = self.ecs.create_entity_with_uuid()
        self.assertIn(entity, self.ecs._entities)
        # UUIDs sind einzigartig und nicht vorhersagbar
        self.assertIsInstance(entity, uuid.UUID)

    def test_destroy_entity(self):
        """Testet das Zerstören einer Entity."""
        entity = self.ecs.create_entity()
        self.assertIn(entity, self.ecs._entities)
        
        self.ecs.destroy_entity(entity)
        self.assertNotIn(entity, self.ecs._entities)

    def test_destroy_nonexistent_entity(self):
        """Testet das Zerstören einer nicht existierenden Entity."""
        # Sollte keinen Fehler verursachen
        self.ecs.destroy_entity(999)

    def test_add_component(self):
        """Testet das Hinzufügen einer Component."""
        entity = self.ecs.create_entity()
        pos = Position(x=100, y=200)
        
        self.ecs.add_component(entity, pos)
        
        retrieved = self.ecs.get_component(entity, Position)
        self.assertIs(retrieved, pos)
        self.assertEqual(retrieved.x, 100)
        self.assertEqual(retrieved.y, 200)

    def test_add_multiple_components(self):
        """Testet das Hinzufügen mehrerer Components zu einer Entity."""
        entity = self.ecs.create_entity()
        
        self.ecs.add_component(entity, Position(x=100, y=200))
        self.ecs.add_component(entity, Velocity(vx=10, vy=5))
        self.ecs.add_component(entity, Health(hp=50, max_hp=100))
        
        all_components = self.ecs.get_all_components(entity)
        self.assertEqual(len(all_components), 3)

    def test_add_component_to_nonexistent_entity(self):
        """Testet das Hinzufügen einer Component zu einer nicht existierenden Entity."""
        pos = Position(x=100, y=200)
        
        with self.assertRaises(ValueError):
            self.ecs.add_component(999, pos)

    def test_remove_component(self):
        """Testet das Entfernen einer Component."""
        entity = self.ecs.create_entity()
        pos = Position(x=100, y=200)
        self.ecs.add_component(entity, pos)
        
        removed = self.ecs.remove_component(entity, Position)
        self.assertIs(removed, pos)
        
        self.assertIsNone(self.ecs.get_component(entity, Position))

    def test_remove_nonexistent_component(self):
        """Testet das Entfernen einer nicht existierenden Component."""
        entity = self.ecs.create_entity()
        
        removed = self.ecs.remove_component(entity, Position)
        self.assertIsNone(removed)

    def test_has_component(self):
        """Testet das Prüfen auf Components."""
        entity = self.ecs.create_entity()
        
        self.assertFalse(self.ecs.has_component(entity, Position))
        
        self.ecs.add_component(entity, Position(x=100, y=200))
        
        self.assertTrue(self.ecs.has_component(entity, Position))
        self.assertFalse(self.ecs.has_component(entity, Velocity))

    def test_has_components(self):
        """Testet das Prüfen auf mehrere Components."""
        entity = self.ecs.create_entity()
        
        self.ecs.add_component(entity, Position(x=100, y=200))
        self.ecs.add_component(entity, Velocity(vx=10, vy=5))
        
        self.assertTrue(self.ecs.has_components(entity, Position, Velocity))
        self.assertFalse(self.ecs.has_components(entity, Position, Health))

    def test_get_entities_with(self):
        """Testet das Abfragen von Entities mit bestimmten Components."""
        e1 = self.ecs.create_entity()
        e2 = self.ecs.create_entity()
        e3 = self.ecs.create_entity()
        
        self.ecs.add_component(e1, Position(x=100, y=200))
        self.ecs.add_component(e2, Position(x=300, y=400))
        self.ecs.add_component(e2, Velocity(vx=10, vy=5))
        self.ecs.add_component(e3, Health(hp=50))
        
        entities = list(self.ecs.get_entities_with(Position))
        self.assertEqual(len(entities), 2)
        self.assertIn(e1, entities)
        self.assertIn(e2, entities)

    def test_get_entities_with_multiple_components(self):
        """Testet das Abfragen von Entities mit mehreren Components."""
        e1 = self.ecs.create_entity()
        e2 = self.ecs.create_entity()
        e3 = self.ecs.create_entity()
        
        self.ecs.add_component(e1, Position(x=100, y=200))
        self.ecs.add_component(e2, Position(x=300, y=400))
        self.ecs.add_component(e2, Velocity(vx=10, vy=5))
        self.ecs.add_component(e3, Position(x=500, y=600))
        self.ecs.add_component(e3, Velocity(vx=5, vy=10))
        
        entities = list(self.ecs.get_entities_with(Position, Velocity))
        self.assertEqual(len(entities), 2)
        self.assertIn(e2, entities)
        self.assertIn(e3, entities)

    def test_get_entities_count(self):
        """Testet das Zählen von Entities."""
        self.assertEqual(self.ecs.get_entities_count(), 0)
        
        self.ecs.create_entity()
        self.ecs.create_entity()
        self.ecs.create_entity()
        
        self.assertEqual(self.ecs.get_entities_count(), 3)

    def test_get_component_count(self):
        """Testet das Zählen von Components."""
        self.assertEqual(self.ecs.get_component_count(Position), 0)
        
        e1 = self.ecs.create_entity()
        e2 = self.ecs.create_entity()
        
        self.ecs.add_component(e1, Position(x=100, y=200))
        self.ecs.add_component(e2, Position(x=300, y=400))
        
        self.assertEqual(self.ecs.get_component_count(Position), 2)

    def test_clear(self):
        """Testet das Löschen aller Entities und Components."""
        e1 = self.ecs.create_entity()
        e2 = self.ecs.create_entity()
        
        self.ecs.add_component(e1, Position(x=100, y=200))
        self.ecs.add_component(e2, Velocity(vx=10, vy=5))
        
        self.ecs.clear()
        
        self.assertEqual(self.ecs.get_entities_count(), 0)
        self.assertEqual(self.ecs.get_component_count(Position), 0)


class TestMovementSystem(unittest.TestCase):
    """Testet das MovementSystem."""

    def test_movement_system(self):
        """Testet das MovementSystem."""
        ecs = ECSManager()
        
        entity = ecs.create_entity()
        ecs.add_component(entity, Position(x=0, y=0))
        ecs.add_component(entity, Velocity(vx=10, vy=5))
        
        system = MovementSystem(ecs)
        
        # Führe System für 1 Sekunde aus
        system(1.0)
        
        pos = ecs.get_component(entity, Position)
        self.assertEqual(pos.x, 10)
        self.assertEqual(pos.y, 5)


class TestGravitySystem(unittest.TestCase):
    """Testet das GravitySystem."""

    def test_gravity_system(self):
        """Testet das GravitySystem."""
        ecs = ECSManager()
        
        entity = ecs.create_entity()
        ecs.add_component(entity, Velocity(vx=0, vy=0))
        
        system = GravitySystem(ecs, gravity=10.0)
        
        # Führe System für 1 Sekunde aus
        system(1.0)
        
        vel = ecs.get_component(entity, Velocity)
        self.assertEqual(vel.vx, 0)
        self.assertEqual(vel.vy, 10.0)


class TestGlobalECS(unittest.TestCase):
    """Testet die globale ECS-Instanz."""

    def setUp(self):
        """Setzt die globale ECS zurück."""
        reset_ecs()

    def tearDown(self):
        """Bereinigt."""
        reset_ecs()

    def test_get_ecs(self):
        """Testet das Holen der globalen ECS-Instanz."""
        ecs1 = get_ecs()
        ecs2 = get_ecs()
        
        self.assertIs(ecs1, ecs2)

    def test_set_ecs(self):
        """Testet das Setzen der globalen ECS-Instanz."""
        custom_ecs = ECSManager()
        set_ecs(custom_ecs)
        
        self.assertIs(get_ecs(), custom_ecs)

    def test_reset_ecs(self):
        """Testet das Zurücksetzen der globalen ECS-Instanz."""
        custom_ecs = ECSManager()
        set_ecs(custom_ecs)
        
        reset_ecs()
        
        # Nach dem Reset sollte eine neue Instanz erstellt werden
        ecs = get_ecs()
        self.assertIsNot(ecs, custom_ecs)


class TestECSSystemManagement(unittest.TestCase):
    """Testet das System-Management."""

    def test_add_system(self):
        """Testet das Hinzufügen eines Systems."""
        ecs = ECSManager()
        
        call_count = [0]
        def test_system(dt):
            call_count[0] += 1
        
        ecs.add_system(test_system)
        
        self.assertEqual(len(ecs._systems), 1)

    def test_add_system_with_priority(self):
        """Testet das Hinzufügen von Systemen mit Priorität."""
        ecs = ECSManager()
        
        calls = []
        
        def system_a(dt):
            calls.append('a')
        
        def system_b(dt):
            calls.append('b')
        
        ecs.add_system(system_a, priority=10)
        ecs.add_system(system_b, priority=0)
        
        ecs.update(0.1)
        
        # System mit niedrigerer Priorität sollte zuerst ausgeführt werden
        self.assertEqual(calls, ['b', 'a'])

    def test_remove_system(self):
        """Testet das Entfernen eines Systems."""
        ecs = ECSManager()
        
        def test_system(dt):
            pass
        
        ecs.add_system(test_system)
        self.assertEqual(len(ecs._systems), 1)
        
        result = ecs.remove_system(test_system)
        self.assertTrue(result)
        self.assertEqual(len(ecs._systems), 0)

    def test_remove_nonexistent_system(self):
        """Testet das Entfernen eines nicht existierenden Systems."""
        ecs = ECSManager()
        
        def test_system(dt):
            pass
        
        result = ecs.remove_system(test_system)
        self.assertFalse(result)

    def test_update_systems(self):
        """Testet das Ausführen von Systemen."""
        ecs = ECSManager()
        
        call_count = [0]
        def test_system(dt):
            call_count[0] += 1
        
        ecs.add_system(test_system)
        
        ecs.update(0.1)
        self.assertEqual(call_count[0], 1)
        
        ecs.update(0.1)
        self.assertEqual(call_count[0], 2)


if __name__ == '__main__':
    unittest.main()
