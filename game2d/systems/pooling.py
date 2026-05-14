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
        # Mapping von id(obj) zu pool_id für alle Objekte (funktioniert auch mit Listen)
        self._object_to_id: dict[int, int] = {}
        
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
        
        # Objekt-ID speichern (für Tracking) - funktioniert mit allen Objekten inkl. Listen
        obj_key = id(obj)
        self._object_to_id[obj_key] = obj_id
        
        return obj
    
    def release(self, obj: T) -> None:
        """Gibt ein Objekt zurück in den Pool.
        
        Args:
            obj: Das zurückzugebende Objekt
        """
        obj_key = id(obj)
        obj_id = self._object_to_id.get(obj_key)
        if obj_id is None:
            return
        
        # Reset das Objekt
        if self._reset_fn:
            self._reset_fn(obj)
        
        # Entferne aus Active und Mapping
        self._active.discard(obj_id)
        del self._object_to_id[obj_key]
        
        # Zurück in den Pool
        self._pool.append(obj)
    
    def is_from_pool(self, obj: T) -> bool:
        """Prüft ob ein Objekt aus diesem Pool stammt.
        
        Args:
            obj: Das zu prüfende Objekt
            
        Returns:
            True wenn das Objekt aus diesem Pool ist
        """
        return id(obj) in self._object_to_id
    
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
        self._object_to_id.clear()
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


# =============================================================================
# Helferfunktionen für einfache Pool-Nutzung
# =============================================================================

def acquire_bullet(x: float = 0.0, y: float = 0.0, vx: float = 0.0, vy: float = 0.0, 
                   ttl: float = 0.8, from_cop: bool = False, damage: int = 0) -> list:
    """Holt einen Bullet aus dem Pool und initialisiert ihn.
    
    Returns:
        Initialisierter Bullet als Liste: [x, y, vx, vy, ttl, from_cop, damage]
    """
    if bullet_pool is None:
        # Fallback: erstelle neuen Bullet (für den Fall dass Pools nicht initialisiert sind)
        return [x, y, vx, vy, ttl, from_cop, damage]
    bullet = bullet_pool.acquire()
    bullet[0] = x
    bullet[1] = y
    bullet[2] = vx
    bullet[3] = vy
    bullet[4] = ttl
    bullet[5] = from_cop
    bullet[6] = damage
    return bullet


def release_bullet(bullet: list) -> None:
    """Gibt einen Bullet zurück in den Pool."""
    if bullet_pool is not None:
        bullet_pool.release(bullet)


def acquire_blood_particle(x: float = 0.0, y: float = 0.0, vx: float = 0.0, vy: float = 0.0,
                           ttl: float = 0.0, radius: float = 0.0) -> list:
    """Holt einen Blood-Particle aus dem Pool und initialisiert ihn."""
    if blood_particle_pool is None:
        return [x, y, vx, vy, ttl, radius]
    p = blood_particle_pool.acquire()
    p[0] = x
    p[1] = y
    p[2] = vx
    p[3] = vy
    p[4] = ttl
    p[5] = radius
    return p


def release_blood_particle(p: list) -> None:
    """Gibt einen Blood-Particle zurück in den Pool."""
    if blood_particle_pool is not None:
        blood_particle_pool.release(p)


def acquire_smoke_particle(x: float = 0.0, y: float = 0.0, vx: float = 0.0, vy: float = 0.0,
                           ttl: float = 0.0, max_ttl: float = 0.0, radius: float = 0.0) -> list:
    """Holt einen Smoke-Particle aus dem Pool und initialisiert ihn."""
    if smoke_particle_pool is None:
        return [x, y, vx, vy, ttl, max_ttl, radius]
    p = smoke_particle_pool.acquire()
    p[0] = x
    p[1] = y
    p[2] = vx
    p[3] = vy
    p[4] = ttl
    p[5] = max_ttl
    p[6] = radius
    return p


def release_smoke_particle(p: list) -> None:
    """Gibt einen Smoke-Particle zurück in den Pool."""
    if smoke_particle_pool is not None:
        smoke_particle_pool.release(p)


def acquire_fire_particle(x: float = 0.0, y: float = 0.0, vx: float = 0.0, vy: float = 0.0,
                          ttl: float = 0.0, max_ttl: float = 0.0, radius: float = 0.0) -> list:
    """Holt einen Fire-Particle aus dem Pool und initialisiert ihn."""
    if fire_particle_pool is None:
        return [x, y, vx, vy, ttl, max_ttl, radius]
    p = fire_particle_pool.acquire()
    p[0] = x
    p[1] = y
    p[2] = vx
    p[3] = vy
    p[4] = ttl
    p[5] = max_ttl
    p[6] = radius
    return p


def release_fire_particle(p: list) -> None:
    """Gibt einen Fire-Particle zurück in den Pool."""
    if fire_particle_pool is not None:
        fire_particle_pool.release(p)


def acquire_rocket(x: float = 0.0, y: float = 0.0, vx: float = 0.0, vy: float = 0.0,
                   ttl: float = 0.0, audio_channel=None) -> list:
    """Holt eine Rocket aus dem Pool und initialisiert sie."""
    if rocket_pool is None:
        return [x, y, vx, vy, ttl, audio_channel]
    r = rocket_pool.acquire()
    r[0] = x
    r[1] = y
    r[2] = vx
    r[3] = vy
    r[4] = ttl
    r[5] = audio_channel
    return r


def release_rocket(r: list) -> None:
    """Gibt eine Rocket zurück in den Pool."""
    if rocket_pool is not None:
        rocket_pool.release(r)


def release_all_bullets(bullets: list) -> None:
    """Gibt alle Bullets aus einer Liste zurück in den Pool."""
    for bullet in bullets:
        release_bullet(bullet)


def release_all_blood_particles(particles: list) -> None:
    """Gibt alle Blood Particles aus einer Liste zurück in den Pool."""
    for p in particles:
        release_blood_particle(p)


def release_all_smoke_particles(particles: list) -> None:
    """Gibt alle Smoke Particles aus einer Liste zurück in den Pool."""
    for p in particles:
        release_smoke_particle(p)


def release_all_fire_particles(particles: list) -> None:
    """Gibt alle Fire Particles aus einer Liste zurück in den Pool."""
    for p in particles:
        release_fire_particle(p)


def release_all_rockets(rockets: list) -> None:
    """Gibt alle Rockets aus einer Liste zurück in den Pool."""
    for r in rockets:
        release_rocket(r)
