"""Spatial partitioning system for efficient collision detection.

Provides a uniform grid for fast range queries and collision tests.
Used for entities (cars, peds, cops, cats) and static obstacles (buildings).
"""
import math
from typing import Any, Dict, List, Optional, Set, Tuple

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
        cells_x = max(1, math.ceil(radius / self.cell_size))
        cells_y = max(1, math.ceil(radius / self.cell_size))
        
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
    global _entity_grid
    if _entity_grid is not None:
        _entity_grid.clear()
