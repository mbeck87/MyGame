"""Spatial partitioning system for efficient collision detection.

Provides a uniform grid for fast range queries and collision tests.
Used for entities (cars, peds, cops, cats) and static obstacles (buildings).
"""
from typing import Any, Dict, List, Optional, Tuple

from game2d.config import WORLD_W, WORLD_H


class SpatialGrid:
    """Uniform grid for spatial partitioning.
    
    Divides the world into cells of fixed size. Objects are stored in cells
    based on their position. Queries return objects in relevant cells only.
    """
    
    def __init__(self, world_w: int = WORLD_W, world_h: int = WORLD_H, 
                 cell_size: int = 200):
        """Initialize spatial grid.
        
        Args:
            world_w: Width of the world
            world_h: Height of the world
            cell_size: Size of each grid cell (square)
        """
        self.cell_size = cell_size
        self.cols = max(1, (world_w + cell_size - 1) // cell_size)
        self.rows = max(1, (world_h + cell_size - 1) // cell_size)
        self._cells: Dict[Tuple[int, int], List[Any]] = {}
        self._obj_to_cell: Dict[int, Tuple[int, int]] = {}
        self._next_id = 0
    
    def _cell_coords(self, x: float, y: float) -> Tuple[int, int]:
        """Get cell coordinates for a point."""
        cx = max(0, min(self.cols - 1, int(x // self.cell_size)))
        cy = max(0, min(self.rows - 1, int(y // self.cell_size)))
        return (cx, cy)
    
    def _cell_key(self, cx: int, cy: int) -> Tuple[int, int]:
        """Create hashable cell key."""
        return (cx, cy)
    
    def add(self, obj: Any, x: float, y: float, radius: float = 0) -> int:
        """Add an object to the grid.
        
        Args:
            obj: The object to add
            x: X coordinate of the object
            y: Y coordinate of the object
            radius: Approximate radius for range queries (optional)
            
        Returns:
            Unique ID for the object (used for removal/update)
        """
        obj_id = self._next_id
        self._next_id += 1
        
        cx, cy = self._cell_coords(x, y)
        cell_key = self._cell_key(cx, cy)
        
        if cell_key not in self._cells:
            self._cells[cell_key] = []
        self._cells[cell_key].append(obj)
        
        self._obj_to_cell[obj_id] = cell_key
        
        # Store position on object if it doesn't have one
        if not hasattr(obj, '_spatial_x'):
            obj._spatial_x = x
            obj._spatial_y = y
        obj._spatial_x = x
        obj._spatial_y = y
        obj._spatial_radius = radius
        obj._spatial_id = obj_id
        
        return obj_id
    
    def update(self, obj: Any, x: float, y: float) -> None:
        """Update an object's position in the grid.
        
        Args:
            obj: The object to update (must have been added with add())
            x: New X coordinate
            y: New Y coordinate
        """
        if not hasattr(obj, '_spatial_id'):
            return
        
        obj_id = obj._spatial_id
        if obj_id not in self._obj_to_cell:
            return
        
        old_cell = self._obj_to_cell[obj_id]
        new_cell = self._cell_coords(x, y)
        new_cell_key = self._cell_key(new_cell[0], new_cell[1])
        
        if old_cell != new_cell_key:
            # Remove from old cell
            if old_cell in self._cells:
                if obj in self._cells[old_cell]:
                    self._cells[old_cell].remove(obj)
            
            # Add to new cell
            if new_cell_key not in self._cells:
                self._cells[new_cell_key] = []
            self._cells[new_cell_key].append(obj)
            self._obj_to_cell[obj_id] = new_cell_key
        
        obj._spatial_x = x
        obj._spatial_y = y
    
    def remove(self, obj: Any) -> None:
        """Remove an object from the grid.
        
        Args:
            obj: The object to remove
        """
        if not hasattr(obj, '_spatial_id'):
            return
        
        obj_id = obj._spatial_id
        if obj_id not in self._obj_to_cell:
            return
        
        cell_key = self._obj_to_cell[obj_id]
        if cell_key in self._cells:
            if obj in self._cells[cell_key]:
                self._cells[cell_key].remove(obj)
        
        del self._obj_to_cell[obj_id]
        
        # Clean up attributes
        for attr in ('_spatial_id', '_spatial_x', '_spatial_y', '_spatial_radius'):
            if hasattr(obj, attr):
                delattr(obj, attr)
    
    def query_radius(self, x: float, y: float, radius: float) -> List[Any]:
        """Query all objects within a radius.
        
        Args:
            x: Center X coordinate
            y: Center Y coordinate
            radius: Search radius
            
        Returns:
            List of objects within the radius
        """
        result = []
        r_sq = radius * radius
        
        # Calculate cell range to search
        start_cx = max(0, int((x - radius) // self.cell_size))
        end_cx = min(self.cols - 1, int((x + radius) // self.cell_size))
        start_cy = max(0, int((y - radius) // self.cell_size))
        end_cy = min(self.rows - 1, int((y + radius) // self.cell_size))
        
        # Check all cells in the range
        for cx in range(start_cx, end_cx + 1):
            for cy in range(start_cy, end_cy + 1):
                cell_key = self._cell_key(cx, cy)
                if cell_key in self._cells:
                    for obj in self._cells[cell_key]:
                        # Check actual distance
                        if hasattr(obj, 'x') and hasattr(obj, 'y'):
                            ox, oy = obj.x, obj.y
                        elif hasattr(obj, '_spatial_x'):
                            ox, oy = obj._spatial_x, obj._spatial_y
                        else:
                            continue
                        
                        dx = ox - x
                        dy = oy - y
                        if dx * dx + dy * dy <= r_sq:
                            result.append(obj)
        
        return result
    
    def query_rect(self, rect) -> List[Any]:
        """Query all objects that might intersect with a rectangle.
        
        Args:
            rect: pygame.Rect or similar with x, y, w, h attributes
            
        Returns:
            List of objects whose cells overlap with the rect's cells
        """
        result = []
        
        # Get cell range covered by rect
        start_cx = max(0, int(rect.x // self.cell_size))
        end_cx = min(self.cols - 1, int((rect.x + rect.w) // self.cell_size))
        start_cy = max(0, int(rect.y // self.cell_size))
        end_cy = min(self.rows - 1, int((rect.y + rect.h) // self.cell_size))
        
        # Collect all objects in overlapping cells
        for cx in range(start_cx, end_cx + 1):
            for cy in range(start_cy, end_cy + 1):
                cell_key = self._cell_key(cx, cy)
                if cell_key in self._cells:
                    result.extend(self._cells[cell_key])
        
        return result
    
    def query_point_cell(self, x: float, y: float) -> List[Any]:
        """Get all objects in the same cell as a point.
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            List of objects in the same cell
        """
        cx, cy = self._cell_coords(x, y)
        cell_key = self._cell_key(cx, cy)
        return self._cells.get(cell_key, [])
    
    def clear(self) -> None:
        """Clear all objects from the grid."""
        self._cells.clear()
        self._obj_to_cell.clear()
        self._next_id = 0
    
    def get_nearby(self, obj: Any, max_dist: float = 100.0) -> List[Any]:
        """Get objects near a given object.
        
        Args:
            obj: Object with x, y attributes
            max_dist: Maximum distance
            
        Returns:
            List of nearby objects (excluding self)
        """
        if not hasattr(obj, 'x') or not hasattr(obj, 'y'):
            return []
        
        objects = self.query_radius(obj.x, obj.y, max_dist)
        # Remove self if present
        return [o for o in objects if o is not obj]


# Global spatial grid instance for the game world
# Initialized by state.py or main.py
_entity_grid: Optional[SpatialGrid] = None


def init_spatial_grid():
    """Initialize the global spatial grid."""
    global _entity_grid
    if _entity_grid is None:
        _entity_grid = SpatialGrid(cell_size=150)
    return _entity_grid


def get_spatial_grid() -> SpatialGrid:
    """Get the global spatial grid instance."""
    if _entity_grid is None:
        init_spatial_grid()
    return _entity_grid


def reset_spatial_grid() -> None:
    """Reset/clear the global spatial grid."""
    if _entity_grid is not None:
        _entity_grid.clear()


# Entity registration helpers
# These functions provide convenient wrappers for adding/removing entities with rect() method

def register_entity(obj: Any, x: float = None, y: float = None, radius: float = None) -> int:
    """Register an entity with the spatial grid.
    
    Args:
        obj: Entity object (should have x, y attributes and rect() method)
        x: Optional X coordinate (uses obj.x if not provided)
        y: Optional Y coordinate (uses obj.y if not provided)
        radius: Optional radius for range queries (uses approx size from rect if not provided)
        
    Returns:
        Spatial grid ID for the object (used for removal)
    """
    if obj is None:
        return -1
    grid = get_spatial_grid()
    if x is None:
        x = getattr(obj, 'x', 0)
    if y is None:
        y = getattr(obj, 'y', 0)
    if radius is None:
        # Approximate radius from rect
        if hasattr(obj, 'rect'):
            r = obj.rect()
            radius = max(r.w, r.h) / 2
        else:
            radius = 30  # Default radius
    obj_id = grid.add(obj, x, y, radius)
    # Initialize last position for optimized updates
    obj._last_spatial_x = x
    obj._last_spatial_y = y
    return obj_id


def update_entity_position(obj: Any) -> None:
    """Update an entity's position in the spatial grid.
    
    Only updates if position has changed significantly (> 0.1px threshold).
    This avoids unnecessary grid operations for static entities.
    
    Args:
        obj: Entity object with x, y attributes
    """
    if obj is None:
        return
    grid = get_spatial_grid()
    x = getattr(obj, 'x', 0)
    y = getattr(obj, 'y', 0)
    # Only update if position has changed significantly
    if not (hasattr(obj, '_last_spatial_x') and 
            abs(x - obj._last_spatial_x) < 0.1 and
            abs(y - obj._last_spatial_y) < 0.1):
        grid.update(obj, x, y)
        obj._last_spatial_x = x
        obj._last_spatial_y = y


def unregister_entity(obj: Any) -> None:
    """Remove an entity from the spatial grid.
    
    Args:
        obj: Entity object to remove
    """
    if obj is None:
        return
    grid = get_spatial_grid()
    grid.remove(obj)
    # Clean up last position tracking attributes
    for attr in ('_last_spatial_x', '_last_spatial_y'):
        if hasattr(obj, attr):
            delattr(obj, attr)


def query_entities_radius(x: float, y: float, radius: float) -> List[Any]:
    """Query all entities within a radius.
    
    Args:
        x: Center X coordinate
        y: Center Y coordinate
        radius: Search radius
        
    Returns:
        List of entities within the radius
    """
    return get_spatial_grid().query_radius(x, y, radius)


def query_entities_rect(rect) -> List[Any]:
    """Query all entities that might intersect with a rectangle.
    
    Args:
        rect: pygame.Rect or similar with x, y, w, h attributes
        
    Returns:
        List of entities in overlapping cells
    """
    return get_spatial_grid().query_rect(rect)


# =============================================================================
# Building Grid Functions
# =============================================================================


class SpatialRect:
    """Wrapper for pygame.Rect that allows spatial grid attributes.
    
    pygame.Rect objects use __slots__ and cannot have arbitrary attributes set.
    This wrapper allows the spatial grid to store metadata on the rect.
    """
    __slots__ = ('rect', '_spatial_x', '_spatial_y', '_spatial_radius', '_spatial_id')
    
    def __init__(self, rect):
        self.rect = rect
        self._spatial_x = None
        self._spatial_y = None
        self._spatial_radius = None
        self._spatial_id = None
    
    def __getattr__(self, name):
        """Forward attribute access to the underlying rect."""
        return getattr(self.rect, name)


# Global building grid for static collision detection
_building_grid: Optional[SpatialGrid] = None


def init_building_grid():
    """Initialize the global building grid for static collision detection."""
    global _building_grid
    if _building_grid is None:
        from game2d.config import WORLD_W, WORLD_H
        _building_grid = SpatialGrid(world_w=WORLD_W, world_h=WORLD_H, cell_size=300)
    return _building_grid


def get_building_grid() -> Optional[SpatialGrid]:
    """Get the global building grid instance."""
    return _building_grid


def register_building(rect, x=None, y=None, radius=None) -> int:
    """Register a building with the building spatial grid.
    
    Args:
        rect: Building rectangle (pygame.Rect)
        x: Optional X coordinate (uses rect.centerx if not provided)
        y: Optional Y coordinate (uses rect.centery if not provided)
        radius: Optional radius (uses max(rect.w, rect.h)/2 if not provided)
        
    Returns:
        Spatial grid ID for the building
    """
    grid = init_building_grid()
    if x is None:
        x = rect.centerx
    if y is None:
        y = rect.centery
    if radius is None:
        radius = max(rect.w, rect.h) / 2
    return grid.add(SpatialRect(rect), x, y, radius)


def query_buildings_radius(x: float, y: float, radius: float) -> List[Any]:
    """Query all buildings within a radius.
    
    Args:
        x: Center X coordinate
        y: Center Y coordinate
        radius: Search radius
        
    Returns:
        List of building rects within the radius
    """
    grid = get_building_grid()
    if grid is None:
        return []
    return grid.query_radius(x, y, radius)


def query_buildings_rect(rect) -> List[Any]:
    """Query all buildings that might intersect with a rectangle.
    
    Args:
        rect: pygame.Rect or similar with x, y, w, h attributes
        
    Returns:
        List of building rects in overlapping cells
    """
    grid = get_building_grid()
    if grid is None:
        return []
    return grid.query_rect(rect)


def reset_building_grid() -> None:
    """Reset/clear the building spatial grid."""
    global _building_grid
    if _building_grid is not None:
        _building_grid.clear()
    _building_grid = None


def init_and_populate_building_grid(buildings) -> None:
    """Initialize building grid and populate with all buildings.
    
    Args:
        buildings: List of (rect, surf) tuples
    """
    reset_building_grid()
    grid = init_building_grid()
    for rect, surf in buildings:
        if surf is not None:
            register_building(rect)


# =============================================================================
# Park Grid Functions (for amusement parks, parks - collision optimization)
# =============================================================================

_park_grid: Optional[SpatialGrid] = None


def init_park_grid():
    """Initialize the global park grid for park collision detection."""
    global _park_grid
    if _park_grid is None:
        from game2d.config import WORLD_W, WORLD_H
        _park_grid = SpatialGrid(world_w=WORLD_W, world_h=WORLD_H, cell_size=300)
    return _park_grid


def get_park_grid() -> Optional[SpatialGrid]:
    """Get the global park grid instance."""
    return _park_grid


def register_park(rect) -> int:
    """Register a park rectangle with the park spatial grid.
    
    Args:
        rect: Park rectangle (pygame.Rect)
        
    Returns:
        Spatial grid ID for the park
    """
    grid = init_park_grid()
    return grid.add(SpatialRect(rect), rect.centerx, rect.centery)


def query_parks_radius(x: float, y: float, radius: float) -> List[Any]:
    """Query all parks within a radius.
    
    Args:
        x: Center X coordinate
        y: Center Y coordinate
        radius: Search radius
        
    Returns:
        List of park rects within the radius
    """
    grid = get_park_grid()
    if grid is None:
        return []
    return grid.query_radius(x, y, radius)


def query_parks_rect(rect) -> List[Any]:
    """Query all parks that might intersect with a rectangle.
    
    Args:
        rect: pygame.Rect or similar with x, y, w, h attributes
        
    Returns:
        List of park rects in overlapping cells
    """
    grid = get_park_grid()
    if grid is None:
        return []
    return grid.query_rect(rect)


def reset_park_grid() -> None:
    """Reset/clear the park spatial grid."""
    global _park_grid
    if _park_grid is not None:
        _park_grid.clear()
    _park_grid = None


def init_and_populate_park_grid(parks) -> None:
    """Initialize park grid and populate with all park rects.
    
    Args:
        parks: List of park rectangles
    """
    reset_park_grid()
    grid = init_park_grid()
    for park_rect in parks:
        register_park(park_rect)
