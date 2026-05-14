"""Object Pooling System für Performance-Optimierung.

Object Pooling reduziert die GC-Last durch Wiederverwendung von Objekten
statt ständig neue zu allozieren. Besonders nützlich für kurze lebende
Objekte wie Bullets und Particles.
"""
from typing import Any, Callable, Generic, Optional, TypeVar

T = TypeVar('T')


class ObjectPool(Generic[T]):
    """Generischer Object Pool für wiederverwendbare Objekte.
    
    Der Pool verwaltet eine Liste von inaktiven Objekten und erstellt
    neue Objekte bei Bedarf. Wenn ein Objekt zurückgegeben wird,
    wird es gereinigt und dem Pool hinzugefügt.
    
    Usage:
        pool = ObjectPool(
            factory=lambda: [0, 0, 0, 0, 0],  # Creates a bullet
            reset_fn=lambda obj: [obj[0], obj[1], 0, 0, 0],  # Reset bullet
            initial_size=100
        )
        
        # Get object from pool
        bullet = pool.acquire()
        bullet[0] = x
        bullet[1] = y
        # ... use bullet ...
        
        # Return object to pool when done
        pool.release(bullet)
    """
    
    def __init__(
        self,
        factory: Callable[[], T],
        reset_fn: Optional[Callable[[T], None]] = None,
        initial_size: int = 64
    ):
        """Initialisiert den Object Pool.
        
        Args:
            factory: Funktion die ein neues Objekt erstellt
            reset_fn: Funktion die ein Objekt zurücksetzt (optional)
            initial_size: Anzahl der vorab erstellten Objekte
        """
        self._factory = factory
        self._reset_fn = reset_fn
        self._pool: list[T] = []
        self._active: set[int] = set()
        self._next_id: int = 0
        
        # Vorab Objekte erstellen
        for _ in range(initial_size):
            self._pool.append(self._factory())
    
    def acquire(self) -> T:
        """Nimmt ein Objekt aus dem Pool.
        
        Returns:
            Ein Objekt aus dem Pool (neu oder wiederverwendet)
        """
        if self._pool:
            obj = self._pool.pop()
        else:
            # Pool ist leer, erstelle neues Objekt
            obj = self._factory()
        
        obj_id = self._next_id
        self._next_id += 1
        self._active.add(obj_id)
        
        # Objekt-ID speichern (für Tracking)
        if not hasattr(obj, '_pool_id'):
            object.__setattr__(obj, '_pool_id', None)
        object.__setattr__(obj, '_pool_id', obj_id)
        
        return obj
    
    def release(self, obj: T) -> None:
        """Gibt ein Objekt zurück in den Pool.
        
        Args:
            obj: Das zurückzugebende Objekt
        """
        if not hasattr(obj, '_pool_id'):
            return
        
        obj_id = object.__getattribute__(obj, '_pool_id')
        if obj_id is None:
            return
        
        # Reset das Objekt
        if self._reset_fn:
            self._reset_fn(obj)
        
        # Entferne aus Active
        self._active.discard(obj_id)
        object.__setattr__(obj, '_pool_id', None)
        
        # Zurück in den Pool
        self._pool.append(obj)
    
    def is_from_pool(self, obj: T) -> bool:
        """Prüft ob ein Objekt aus diesem Pool stammt.
        
        Args:
            obj: Das zu prüfende Objekt
            
        Returns:
            True wenn das Objekt aus diesem Pool ist
        """
        return hasattr(obj, '_pool_id') and object.__getattribute__(obj, '_pool_id') is not None
    
    @property
    def size(self) -> int:
        """Aktuelle Größe des Pools (verfügbare Objekte)."""
        return len(self._pool)
    
    @property
    def active_count(self) -> int:
        """Anzahl der aktiven Objekte (aus dem Pool entnommen)."""
        return len(self._active)
    
    @property
    def total_count(self) -> int:
        """Gesamtzahl der verwalteten Objekte."""
        return len(self._pool) + len(self._active)
    
    def clear(self) -> None:
        """Leert den Pool und setzt alle Objekte zurück."""
        for obj in self._pool:
            if self._reset_fn:
                self._reset_fn(obj)
        self._pool.clear()
        self._active.clear()
        self._next_id = 0
    
    def preallocate(self, count: int) -> None:
        """Alloziere zusätzliche Objekte im Voraus.
        
        Args:
            count: Anzahl der zusätzlich zu allozierenden Objekte
        """
        for _ in range(count):
            self._pool.append(self._factory())


# =============================================================================
# Spezialisierte Pools für häufige Objekttypen
# =============================================================================

class BulletPool(ObjectPool[list]):
    """Object Pool für Bullet-Objekte.
    
    Bullets sind Listen mit: [x, y, vx, vy, ttl, from_cop, damage]
    """
    
    def __init__(self, initial_size: int = 512):
        def factory():
            return [0.0, 0.0, 0.0, 0.0, 0.0, False, 0]
        
        def reset_fn(bullet: list):
            bullet[0] = 0.0
            bullet[1] = 0.0
            bullet[2] = 0.0
            bullet[3] = 0.0
            bullet[4] = 0.0
            bullet[5] = False
            bullet[6] = 0
        
        super().__init__(factory, reset_fn, initial_size)


class ParticlePool(ObjectPool[list]):
    """Object Pool für Particle-Objekte.
    
    Particles sind Listen. Das Format variiert je nach Typ:
    - blood_particles: [x, y, vx, vy, ttl, radius]
    - smoke_particles: [x, y, vx, vy, ttl, max_ttl, radius]
    - fire_particles: [x, y, vx, vy, ttl, max_ttl, radius]
    """
    
    def __init__(self, particle_type: str = "blood", initial_size: int = 1024):
        if particle_type == "blood":
            def factory():
                return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            def reset_fn(p: list):
                for i in range(len(p)):
                    p[i] = 0.0
        elif particle_type == "smoke":
            def factory():
                return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            def reset_fn(p: list):
                for i in range(len(p)):
                    p[i] = 0.0
        elif particle_type == "fire":
            def factory():
                return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            def reset_fn(p: list):
                for i in range(len(p)):
                    p[i] = 0.0
        else:
            def factory():
                return [0.0, 0.0, 0.0, 0.0, 0.0]
            def reset_fn(p: list):
                for i in range(len(p)):
                    p[i] = 0.0
        
        super().__init__(factory, reset_fn, initial_size)


class RocketPool(ObjectPool[list]):
    """Object Pool für Rocket-Objekte.
    
    Rockets sind Listen mit: [x, y, vx, vy, ttl, audio_channel]
    """
    
    def __init__(self, initial_size: int = 64):
        def factory():
            return [0.0, 0.0, 0.0, 0.0, 0.0, None]
        
        def reset_fn(rocket: list):
            rocket[0] = 0.0
            rocket[1] = 0.0
            rocket[2] = 0.0
            rocket[3] = 0.0
            rocket[4] = 0.0
            rocket[5] = None
        
        super().__init__(factory, reset_fn, initial_size)


# =============================================================================
# Globale Pool-Instanzen
# =============================================================================

bullet_pool: Optional[BulletPool] = None
blood_particle_pool: Optional[ParticlePool] = None
smoke_particle_pool: Optional[ParticlePool] = None
fire_particle_pool: Optional[ParticlePool] = None
rocket_pool: Optional[RocketPool] = None


def init_pools():
    """Initialisiert alle Object Pools."""
    global bullet_pool, blood_particle_pool, smoke_particle_pool, fire_particle_pool, rocket_pool
    
    bullet_pool = BulletPool(initial_size=512)
    blood_particle_pool = ParticlePool(particle_type="blood", initial_size=1024)
    smoke_particle_pool = ParticlePool(particle_type="smoke", initial_size=1024)
    fire_particle_pool = ParticlePool(particle_type="fire", initial_size=512)
    rocket_pool = RocketPool(initial_size=64)


def reset_pools():
    """Setzt alle Pools zurück und leert sie."""
    if bullet_pool:
        bullet_pool.clear()
    if blood_particle_pool:
        blood_particle_pool.clear()
    if smoke_particle_pool:
        smoke_particle_pool.clear()
    if fire_particle_pool:
        fire_particle_pool.clear()
    if rocket_pool:
        rocket_pool.clear()
