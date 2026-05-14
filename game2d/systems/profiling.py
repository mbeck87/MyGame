"""Performance Profiling System for game2d.

Provides comprehensive performance monitoring and analysis tools:
- FPS tracking and frame time measurement
- Function timing with decorators
- Memory usage tracking
- Performance metrics sampling
- Profiling reports and visualization

Usage:
    from game2d.systems.profiling import profiler, profile, timed, FPSMonitor
    
    # Decorate functions for timing
    @profile
    def update_entities(state):
        pass
    
    # Or use timed context manager
    with timed("update_entities"):
        pass
    
    # Access metrics
    fps = profiler.fps
    frame_time = profiler.frame_time
    avg_frame_time = profiler.average_frame_time
    
    # Get report
    print(profiler.generate_report())
"""
from __future__ import annotations

import functools
import gc
import sys
import threading
import time
import traceback
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union

import pygame

# Type variable for generic function signatures
F = TypeVar('F', bound=Callable[..., Any])


@dataclass
class MetricSample:
    """A single performance metric sample."""
    name: str
    value: float
    timestamp: float
    frame: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp,
            "frame": self.frame,
        }


@dataclass
class FunctionStats:
    """Statistics for a profiled function."""
    name: str
    call_count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    total_self_time: float = 0.0  # Time excluding nested profiled calls
    
    @property
    def avg_time(self) -> float:
        return self.total_time / self.call_count if self.call_count > 0 else 0.0
    
    @property
    def avg_self_time(self) -> float:
        return self.total_self_time / self.call_count if self.call_count > 0 else 0.0
    
    def record(self, elapsed: float, self_elapsed: float) -> None:
        self.call_count += 1
        self.total_time += elapsed
        self.min_time = min(self.min_time, elapsed)
        self.max_time = max(self.max_time, elapsed)
        self.total_self_time += self_elapsed
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "call_count": self.call_count,
            "total_time_ms": round(self.total_time * 1000, 3),
            "avg_time_ms": round(self.avg_time * 1000, 3),
            "min_time_ms": round(self.min_time * 1000, 3) if self.call_count > 0 else 0,
            "max_time_ms": round(self.max_time * 1000, 3),
            "avg_self_time_ms": round(self.avg_self_time * 1000, 3),
        }


@dataclass
class FrameStats:
    """Statistics for a single frame."""
    frame_number: int
    timestamp: float
    frame_time: float  # Time to render this frame
    fps: float
    memory_usage_mb: float
    entity_counts: Dict[str, int] = field(default_factory=dict)
    custom_metrics: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_number": self.frame_number,
            "timestamp": self.timestamp,
            "frame_time_ms": round(self.frame_time * 1000, 3),
            "fps": round(self.fps, 1),
            "memory_usage_mb": round(self.memory_usage_mb, 2),
            "entity_counts": self.entity_counts,
            "custom_metrics": self.custom_metrics,
        }


class Profiler:
    """Main profiler class for performance monitoring.
    
    Singleton that tracks:
    - FPS and frame times
    - Function execution times
    - Memory usage
    - Custom metrics
    - Frame-by-frame statistics
    """
    
    _instance: Optional['Profiler'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'Profiler':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._frame_count = 0
        self._last_frame_time = time.time()
        self._frame_times: List[float] = []
        self._fps_samples: List[float] = []
        
        # Function profiling
        self._function_stats: Dict[str, FunctionStats] = {}
        self._profiling_stack: List[Tuple[str, float]] = []  # (name, start_time)
        
        # Frame statistics
        self._frame_stats: List[FrameStats] = []
        self._max_frame_stats = 1000  # Keep last 1000 frames
        
        # Memory tracking
        self._memory_samples: List[Tuple[float, float]] = []  # (timestamp, mb)
        self._peak_memory = 0.0
        self._cached_memory = 0.0  # Cached current memory value
        self._last_memory_update_frame = 0  # Frame count when memory was last updated
        
        # Custom metrics
        self._custom_metrics: Dict[str, List[MetricSample]] = defaultdict(list)
        
        # State
        self._enabled = True
        self._paused = False
        self._profiling_enabled = True
        
        # Sampling
        self._sample_interval = 1.0  # seconds
        self._last_sample_time = time.time()
        
        self._initialized = True
    
    @classmethod
    def reset(cls) -> None:
        """Reset the profiler singleton."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance = None
    
    @property
    def enabled(self) -> bool:
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value
        # Clear samples when enabling to get fresh measurements
        if value:
            self._frame_times.clear()
            self._fps_samples.clear()
    
    @property
    def paused(self) -> bool:
        return self._paused
    
    @paused.setter
    def paused(self, value: bool) -> None:
        self._paused = value
    
    @property
    def frame_count(self) -> int:
        return self._frame_count
    
    @property
    def fps(self) -> float:
        """Current FPS (average of recent frames)."""
        if not self._fps_samples:
            return 0.0
        return sum(self._fps_samples) / len(self._fps_samples)
    
    @property
    def frame_time(self) -> float:
        """Last frame time in seconds."""
        if not self._frame_times:
            return 0.0
        return self._frame_times[-1]
    
    @property
    def average_frame_time(self) -> float:
        """Average frame time over recent frames."""
        if not self._frame_times:
            return 0.0
        return sum(self._frame_times) / len(self._frame_times)
    
    @property
    def min_fps(self) -> float:
        """Minimum FPS recorded."""
        if not self._fps_samples:
            return 0.0
        return min(self._fps_samples)
    
    @property
    def max_fps(self) -> float:
        """Maximum FPS recorded."""
        if not self._fps_samples:
            return 0.0
        return max(self._fps_samples)
    
    @property
    def current_memory_mb(self) -> float:
        """Current memory usage in megabytes. Cached and updated every 10 frames for performance."""
        # Update cached memory every 10 frames
        if self._frame_count != self._last_memory_update_frame and self._frame_count % 10 == 0:
            self._cached_memory = self._get_memory_usage()
            self._peak_memory = max(self._peak_memory, self._cached_memory)
            self._last_memory_update_frame = self._frame_count
        return self._cached_memory
    
    @property
    def peak_memory_mb(self) -> float:
        """Peak memory usage in megabytes."""
        return self._peak_memory
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB. Optimized to avoid expensive gc.get_objects()."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except ImportError:
            # Fallback: Use a fast estimate (process memory via /proc on Linux)
            try:
                import os
                # On Linux, read /proc/self/status for VmRSS
                if os.path.exists('/proc/self/status'):
                    with open('/proc/self/status', 'r') as f:
                        for line in f:
                            if line.startswith('VmRSS:'):
                                # VmRSS is in kB
                                return int(line.split()[1]) / 1024.0
            except:
                pass
            # Last resort: return 0 (memory tracking disabled in fallback)
            return 0.0
    
    def start_frame(self) -> None:
        """Mark the start of a new frame."""
        if not self._enabled or self._paused:
            return
        
        self._last_frame_time = time.time()
        self._frame_count += 1
    
    def end_frame(self, entity_counts: Optional[Dict[str, int]] = None) -> None:
        """Mark the end of a frame and record statistics. Optimized for minimal overhead."""
        if not self._enabled or self._paused:
            return
        
        now = time.time()
        frame_time = now - self._last_frame_time
        fps = 1.0 / frame_time if frame_time > 0 else 0.0
        
        # Store frame time for FPS calculation (use deque for O(1) append)
        self._frame_times.append(frame_time)
        
        # Store FPS sample
        self._fps_samples.append(fps)
        
        # Memory usage: use cached value, update every 10 frames
        memory = self._cached_memory
        if self._frame_count % 10 == 0:
            memory = self._get_memory_usage()
            self._cached_memory = memory
            self._peak_memory = max(self._peak_memory, memory)
        
        # Record frame stats
        frame_stat = FrameStats(
            frame_number=self._frame_count,
            timestamp=now,
            frame_time=frame_time,
            fps=fps,
            memory_usage_mb=memory,
            entity_counts=entity_counts or {},
        )
        self._frame_stats.append(frame_stat)
        
        # Limit storage by slicing only when needed (every 60 frames)
        if self._frame_count % 60 == 0:
            if len(self._frame_times) > 240:
                self._frame_times = self._frame_times[-120:]
            if len(self._fps_samples) > 60:
                self._fps_samples = self._fps_samples[-60:]
            if len(self._frame_stats) > self._max_frame_stats:
                self._frame_stats = self._frame_stats[-self._max_frame_stats:]
        
        # Sample custom metrics periodically
        if now - self._last_sample_time >= self._sample_interval:
            self._sample_custom_metrics()
            self._last_sample_time = now
    
    def record_metric(self, name: str, value: float) -> None:
        """Record a custom metric sample."""
        if not self._enabled or self._paused:
            return
        
        sample = MetricSample(
            name=name,
            value=value,
            timestamp=time.time(),
            frame=self._frame_count,
        )
        self._custom_metrics[name].append(sample)
        
        # Limit storage
        for name_key in self._custom_metrics:
            if len(self._custom_metrics[name_key]) > 1000:
                self._custom_metrics[name_key] = self._custom_metrics[name_key][-500:]
    
    def _sample_custom_metrics(self) -> None:
        """Sample all registered custom metrics."""
        # This can be extended to automatically sample certain metrics
        pass
    
    def start_profiling(self, function_name: str) -> None:
        """Start profiling a function (internal use)."""
        if not self._enabled or self._paused or not self._profiling_enabled:
            return
        
        # Check if we're already profiling this (nested calls)
        if self._profiling_stack and self._profiling_stack[-1][0] == function_name:
            # This shouldn't happen with proper usage
            return
        
        self._profiling_stack.append((function_name, time.time()))
    
    def end_profiling(self, function_name: str) -> None:
        """End profiling a function (internal use)."""
        if not self._profiling_stack:
            return
        
        start_name, start_time = self._profiling_stack.pop()
        elapsed = time.time() - start_time
        
        # Calculate self time (excluding nested profiled calls)
        self_time = elapsed
        while self._profiling_stack:
            # Pop nested calls to calculate self time
            nested_name, nested_start = self._profiling_stack.pop()
            self_time -= (time.time() - nested_start)
            self._profiling_stack.append((nested_name, nested_start))
            break  # Only subtract the most recent nested call
        
        # Record stats
        if start_name not in self._function_stats:
            self._function_stats[start_name] = FunctionStats(name=start_name)
        self._function_stats[start_name].record(elapsed, self_time)
    
    def get_function_stats(self, name: str) -> Optional[FunctionStats]:
        """Get statistics for a specific function."""
        return self._function_stats.get(name)
    
    def get_all_function_stats(self) -> List[FunctionStats]:
        """Get statistics for all profiled functions."""
        return list(self._function_stats.values())
    
    def get_frame_stats(self, count: Optional[int] = None) -> List[FrameStats]:
        """Get recent frame statistics."""
        if count is None:
            return list(self._frame_stats)
        return list(self._frame_stats[-count:])
    
    def get_top_functions(self, n: int = 10, sort_by: str = "total_time") -> List[FunctionStats]:
        """Get top N functions by a specific metric."""
        stats = list(self._function_stats.values())
        
        if sort_by == "total_time":
            stats.sort(key=lambda x: x.total_time, reverse=True)
        elif sort_by == "call_count":
            stats.sort(key=lambda x: x.call_count, reverse=True)
        elif sort_by == "avg_time":
            stats.sort(key=lambda x: x.avg_time, reverse=True)
        elif sort_by == "max_time":
            stats.sort(key=lambda x: x.max_time, reverse=True)
        
        return stats[:n]
    
    def get_slowest_frames(self, n: int = 10) -> List[FrameStats]:
        """Get the slowest frames."""
        stats = sorted(self._frame_stats, key=lambda x: x.frame_time, reverse=True)
        return stats[:n]
    
    def generate_report(self, detailed: bool = False) -> str:
        """Generate a human-readable performance report."""
        lines = []
        lines.append("=" * 60)
        lines.append("PERFORMANCE PROFILING REPORT")
        lines.append("=" * 60)
        lines.append("")
        
        # Overall stats
        lines.append("OVERALL STATISTICS")
        lines.append("-" * 40)
        lines.append(f"Total frames: {self._frame_count}")
        lines.append(f"Current FPS: {self.fps:.1f}")
        lines.append(f"Average FPS: {sum(self._fps_samples) / len(self._fps_samples):.1f}" if self._fps_samples else "Average FPS: N/A")
        lines.append(f"FPS range: {self.min_fps:.1f} - {self.max_fps:.1f}")
        lines.append(f"Current memory: {self.current_memory_mb:.2f} MB")
        lines.append(f"Peak memory: {self.peak_memory_mb:.2f} MB")
        lines.append("")
        
        # Top functions by total time
        if self._function_stats:
            lines.append("TOP FUNCTIONS BY TOTAL TIME")
            lines.append("-" * 40)
            for i, stat in enumerate(self.get_top_functions(10, "total_time"), 1):
                pct = (stat.total_time / sum(s.total_time for s in self._function_stats.values())) * 100 if self._function_stats else 0
                lines.append(f"  {i:2d}. {stat.name}: {stat.total_time * 1000:8.2f}ms ({stat.call_count} calls, {pct:.1f}%)")
            lines.append("")
        
        # Slowest frames
        if self._frame_stats:
            lines.append("SLOWEST FRAMES")
            lines.append("-" * 40)
            for i, stat in enumerate(self.get_slowest_frames(5), 1):
                lines.append(f"  {i:2d}. Frame {stat.frame_number}: {stat.frame_time * 1000:.2f}ms ({stat.fps:.1f} FPS)")
            lines.append("")
        
        if detailed and self._function_stats:
            lines.append("DETAILED FUNCTION STATISTICS")
            lines.append("-" * 40)
            for stat in sorted(self._function_stats.values(), key=lambda x: x.total_time, reverse=True):
                lines.append(f"\n{stat.name}:")
                lines.append(f"  Calls: {stat.call_count}")
                lines.append(f"  Total time: {stat.total_time * 1000:.2f}ms")
                lines.append(f"  Avg time: {stat.avg_time * 1000:.3f}ms")
                lines.append(f"  Min time: {stat.min_time * 1000:.3f}ms")
                lines.append(f"  Max time: {stat.max_time * 1000:.3f}ms")
                lines.append(f"  Avg self time: {stat.avg_self_time * 1000:.3f}ms")
        
        lines.append("=" * 60)
        return "\n".join(lines)
    
    def generate_json_report(self) -> Dict[str, Any]:
        """Generate a JSON-serializable performance report."""
        return {
            "overall": {
                "total_frames": self._frame_count,
                "current_fps": round(self.fps, 2),
                "avg_fps": round(sum(self._fps_samples) / len(self._fps_samples), 2) if self._fps_samples else 0,
                "min_fps": round(self.min_fps, 2),
                "max_fps": round(self.max_fps, 2),
                "current_memory_mb": round(self.current_memory_mb, 2),
                "peak_memory_mb": round(self.peak_memory_mb, 2),
            },
            "top_functions": [
                stat.to_dict() for stat in self.get_top_functions(20, "total_time")
            ],
            "slowest_frames": [
                stat.to_dict() for stat in self.get_slowest_frames(10)
            ],
            "recent_frame_stats": [
                stat.to_dict() for stat in self.get_frame_stats(100)
            ],
        }
    
    def save_report(self, filename: str = "profile_report.json") -> None:
        """Save profiling report to a JSON file."""
        import json
        report = self.generate_json_report()
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
    
    def clear(self) -> None:
        """Clear all collected data."""
        self._frame_count = 0
        self._last_frame_time = time.time()
        self._frame_times.clear()
        self._fps_samples.clear()
        self._function_stats.clear()
        self._profiling_stack.clear()
        self._frame_stats.clear()
        self._memory_samples.clear()
        self._peak_memory = 0.0
        self._custom_metrics.clear()
    
    def set_max_frame_stats(self, count: int) -> None:
        """Set maximum number of frame stats to keep."""
        self._max_frame_stats = count
        if len(self._frame_stats) > self._max_frame_stats:
            self._frame_stats = self._frame_stats[-self._max_frame_stats:]


# Global profiler instance
profiler = Profiler()


def profile(func: F) -> F:
    """Decorator to profile a function.
    
    Usage:
        @profile
        def my_function():
            pass
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        p = Profiler()
        p.start_profiling(func.__name__)
        try:
            result = func(*args, **kwargs)
        finally:
            p.end_profiling(func.__name__)
        return result
    return wrapper  # type: ignore


@contextmanager
def timed(name: str):
    """Context manager to time a block of code.
    
    Usage:
        with timed("my_operation"):
            # code to profile
            pass
    """
    p = Profiler()
    p.start_profiling(name)
    try:
        yield
    finally:
        p.end_profiling(name)


@contextmanager
def frame_scope(entity_counts: Optional[Dict[str, int]] = None):
    """Context manager to mark a frame boundary.
    
    Usage:
        with frame_scope(entity_counts={"cars": len(cars), "peds": len(peds)}):
            # render frame
            pass
    """
    p = Profiler()
    p.start_frame()
    try:
        yield
    finally:
        p.end_frame(entity_counts)


class FPSMonitor:
    """Lightweight FPS monitor that can be displayed on screen."""
    
    def __init__(self, x: int = 10, y: int = 10, font_size: int = 20, color: Tuple[int, int, int] = (255, 255, 255)):
        self.x = x
        self.y = y
        self.font_size = font_size
        self.color = color
        self._font = None
        self._fps_history: List[float] = []
        self._max_history = 100
    
    def get_font(self):
        if self._font is None:
            self._font = pygame.font.Font(None, self.font_size)
        return self._font
    
    def update(self) -> None:
        """Update FPS history."""
        fps = profiler.fps
        self._fps_history.append(fps)
        if len(self._fps_history) > self._max_history:
            self._fps_history = self._fps_history[-self._max_history:]
    
    def render(self, surface: pygame.Surface) -> None:
        """Render FPS display on the given surface."""
        font = self.get_font()
        
        fps = profiler.fps
        avg_fps = sum(self._fps_history) / len(self._fps_history) if self._fps_history else 0
        frame_time = profiler.frame_time * 1000
        
        lines = [
            f"FPS: {fps:.1f}",
            f"Avg: {avg_fps:.1f}",
            f"Frame: {frame_time:.2f}ms",
        ]
        
        for i, line in enumerate(lines):
            text = font.render(line, True, self.color)
            surface.blit(text, (self.x, self.y + i * (self.font_size + 2)))
    
    def render_detailed(self, surface: pygame.Surface, width: int = 300) -> None:
        """Render detailed performance info."""
        font = self.get_font()
        small_font = pygame.font.Font(None, 16)
        
        fps = profiler.fps
        avg_fps = sum(self._fps_samples) / len(profiler._fps_samples) if profiler._fps_samples else 0
        frame_time = profiler.frame_time * 1000
        memory = profiler.current_memory_mb
        
        # Background
        background = pygame.Surface((width, 120), pygame.SRCALPHA)
        background.fill((0, 0, 0, 180))
        surface.blit(background, (self.x - 5, self.y - 5))
        
        # Header
        header = font.render("PERFORMANCE", True, (200, 200, 200))
        surface.blit(header, (self.x, self.y))
        
        # Stats
        stats = [
            ("FPS:", f"{fps:.1f}"),
            ("Avg FPS:", f"{avg_fps:.1f}"),
            ("Frame:", f"{frame_time:.2f}ms"),
            ("Memory:", f"{memory:.1f}MB"),
        ]
        
        for i, (label, value) in enumerate(stats):
            label_text = small_font.render(label, True, (180, 180, 180))
            value_text = small_font.render(value, True, self.color)
            surface.blit(label_text, (self.x, self.y + 30 + i * 20))
            surface.blit(value_text, (self.x + 70, self.y + 30 + i * 20))
        
        # Top functions
        if self.y + 130 < surface.get_height():
            top_funcs = profiler.get_top_functions(3, "total_time")
            if top_funcs:
                surface.blit(small_font.render("Top Functions:", True, (180, 180, 180)), (self.x, self.y + 110))
                for i, func in enumerate(top_funcs):
                    text = small_font.render(f"{func.name}: {func.total_time * 1000:.1f}ms", True, self.color)
                    surface.blit(text, (self.x, self.y + 130 + i * 16))


class PerformanceOverlay:
    """Advanced performance overlay with graph visualization."""
    
    def __init__(
        self,
        x: int = 10,
        y: int = 10,
        width: int = 300,
        height: int = 200,
        bg_color: Tuple[int, int, int] = (0, 0, 0, 200),
        line_color: Tuple[int, int, int] = (0, 255, 0),
    ):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.bg_color = bg_color
        self.line_color = line_color
        self._font = pygame.font.Font(None, 14)
        self._history: List[float] = []
        self._max_history = width
    
    def add_sample(self, value: float) -> None:
        self._history.append(value)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
    
    def render(self, surface: pygame.Surface) -> None:
        """Render the overlay with FPS graph."""
        # Background
        background = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        if len(self.bg_color) == 4:
            background.fill(self.bg_color)
        else:
            background.fill(self.bg_color + (200,))
        surface.blit(background, (self.x, self.y))
        
        # Draw graph
        if len(self._history) > 1:
            max_val = max(self._history) if self._history else 1
            min_val = min(self._history) if self._history else 0
            val_range = max_val - min_val if max_val != min_val else 1
            
            points = []
            for i, val in enumerate(self._history):
                x = self.x + int(i * (self.width - 20) / len(self._history))
                y = self.y + self.height - 20 - int((val - min_val) / val_range * (self.height - 40))
                points.append((x, y))
            
            if len(points) > 1:
                pygame.draw.lines(surface, self.line_color, False, points, 2)
        
        # Draw axes
        pygame.draw.line(surface, (100, 100, 100), 
                        (self.x, self.y + self.height - 20), 
                        (self.x + self.width, self.y + self.height - 20), 1)
        
        # Draw labels
        title = self._font.render("FPS History", True, (255, 255, 255))
        surface.blit(title, (self.x + 5, self.y + 5))
        
        if self._history:
            current_text = self._font.render(f"Current: {self._history[-1]:.1f}", True, (255, 255, 255))
            surface.blit(current_text, (self.x + 5, self.y + self.height - 18))


# Initialize pygame if not already initialized
try:
    if not pygame.get_init():
        pygame.init()
except:
    pass
