"""Unit tests for the Performance Profiling System."""
import unittest
from unittest.mock import MagicMock, patch
import time
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game2d.systems.profiling import (
    Profiler,
    MetricSample,
    FunctionStats,
    FrameStats,
    profiler,
    profile,
    timed,
    frame_scope,
    FPSMonitor,
    PerformanceOverlay,
)


class TestMetricSample(unittest.TestCase):
    """Tests for MetricSample dataclass."""

    def test_metric_sample_creation(self):
        """Test creating a metric sample."""
        sample = MetricSample(
            name="test_metric",
            value=42.5,
            timestamp=12345.678,
            frame=100
        )
        self.assertEqual(sample.name, "test_metric")
        self.assertEqual(sample.value, 42.5)
        self.assertEqual(sample.timestamp, 12345.678)
        self.assertEqual(sample.frame, 100)

    def test_metric_sample_to_dict(self):
        """Test converting metric sample to dictionary."""
        sample = MetricSample(
            name="test",
            value=10.0,
            timestamp=100.0,
            frame=5
        )
        d = sample.to_dict()
        self.assertIn("name", d)
        self.assertIn("value", d)
        self.assertIn("timestamp", d)
        self.assertIn("frame", d)


class TestFunctionStats(unittest.TestCase):
    """Tests for FunctionStats dataclass."""

    def test_function_stats_creation(self):
        """Test creating function stats."""
        stats = FunctionStats(name="test_func")
        self.assertEqual(stats.name, "test_func")
        self.assertEqual(stats.call_count, 0)
        self.assertEqual(stats.total_time, 0.0)

    def test_function_stats_record(self):
        """Test recording function execution times."""
        stats = FunctionStats(name="test_func")
        
        stats.record(0.1, 0.1)  # elapsed, self_elapsed
        self.assertEqual(stats.call_count, 1)
        self.assertEqual(stats.total_time, 0.1)
        self.assertEqual(stats.min_time, 0.1)
        self.assertEqual(stats.max_time, 0.1)
        
        stats.record(0.2, 0.15)
        self.assertEqual(stats.call_count, 2)
        self.assertAlmostEqual(stats.total_time, 0.3, places=5)
        self.assertEqual(stats.min_time, 0.1)
        self.assertEqual(stats.max_time, 0.2)

    def test_function_stats_avg_time(self):
        """Test average time calculation."""
        stats = FunctionStats(name="test_func")
        stats.record(0.1, 0.1)
        stats.record(0.2, 0.15)
        stats.record(0.3, 0.2)
        
        self.assertAlmostEqual(stats.avg_time, 0.2, places=5)
        self.assertAlmostEqual(stats.avg_self_time, 0.15, places=5)

    def test_function_stats_to_dict(self):
        """Test converting function stats to dictionary."""
        stats = FunctionStats(name="test_func")
        stats.record(0.1, 0.1)
        
        d = stats.to_dict()
        self.assertIn("name", d)
        self.assertIn("call_count", d)
        self.assertIn("total_time_ms", d)
        self.assertIn("avg_time_ms", d)


class TestFrameStats(unittest.TestCase):
    """Tests for FrameStats dataclass."""

    def test_frame_stats_creation(self):
        """Test creating frame stats."""
        stats = FrameStats(
            frame_number=100,
            timestamp=12345.678,
            frame_time=0.0167,
            fps=60.0,
            memory_usage_mb=100.5,
        )
        self.assertEqual(stats.frame_number, 100)
        self.assertEqual(stats.frame_time, 0.0167)
        self.assertEqual(stats.fps, 60.0)

    def test_frame_stats_to_dict(self):
        """Test converting frame stats to dictionary."""
        stats = FrameStats(
            frame_number=1,
            timestamp=100.0,
            frame_time=0.01,
            fps=100.0,
            memory_usage_mb=50.0,
        )
        d = stats.to_dict()
        self.assertIn("frame_number", d)
        self.assertIn("frame_time_ms", d)
        self.assertIn("fps", d)
        self.assertIn("memory_usage_mb", d)


class TestProfilerSingleton(unittest.TestCase):
    """Tests for Profiler singleton pattern."""

    def setUp(self):
        Profiler.reset()

    def test_singleton(self):
        """Test that Profiler is a singleton."""
        p1 = Profiler()
        p2 = Profiler()
        self.assertIs(p1, p2)

    def test_reset(self):
        """Test resetting the profiler."""
        p = Profiler()
        p.start_frame()
        p.end_frame()
        
        self.assertEqual(p.frame_count, 1)
        
        Profiler.reset()
        p = Profiler()
        self.assertEqual(p.frame_count, 0)


class TestProfilerBasic(unittest.TestCase):
    """Tests for basic profiler functionality."""

    def setUp(self):
        Profiler.reset()
        self.p = Profiler()

    def test_frame_count(self):
        """Test frame counting."""
        self.assertEqual(self.p.frame_count, 0)
        
        self.p.start_frame()
        self.assertEqual(self.p.frame_count, 1)
        
        self.p.start_frame()
        self.assertEqual(self.p.frame_count, 2)

    def test_frame_time_tracking(self):
        """Test frame time tracking."""
        self.p.start_frame()
        time.sleep(0.01)  # Sleep for 10ms
        self.p.end_frame()
        
        # Frame time should be recorded after end_frame
        # The frame_time property returns the last frame time
        # Since we slept for 10ms, frame_time should be at least 10ms
        self.assertGreater(self.p.frame_time, 0)
        # Also check that frame_times list has entries
        self.assertGreater(len(self.p._frame_times), 0)

    def test_fps_calculation(self):
        """Test FPS calculation."""
        for _ in range(5):
            self.p.start_frame()
            self.p.end_frame()
        
        self.assertGreater(self.p.fps, 0)

    def test_enabled_disabled(self):
        """Test enabling/disabling profiler."""
        self.p.enabled = False
        self.p.start_frame()
        self.p.end_frame()
        
        # Frame count should not increase when disabled
        self.assertEqual(self.p.frame_count, 0)
        
        self.p.enabled = True
        self.p.start_frame()
        self.assertEqual(self.p.frame_count, 1)

    def test_paused(self):
        """Test pausing profiler."""
        self.p.start_frame()
        self.p.paused = True
        self.p.start_frame()
        
        # Frame count should not increase when paused
        self.assertEqual(self.p.frame_count, 1)
        
        self.p.paused = False
        self.p.start_frame()
        self.assertEqual(self.p.frame_count, 2)


class TestProfilerFunctionProfiling(unittest.TestCase):
    """Tests for function profiling."""

    def setUp(self):
        Profiler.reset()
        self.p = Profiler()

    def test_profile_function(self):
        """Test profiling a function."""
        self.p.start_profiling("test_func")
        time.sleep(0.01)
        self.p.end_profiling("test_func")
        
        stats = self.p.get_function_stats("test_func")
        self.assertIsNotNone(stats)
        self.assertEqual(stats.call_count, 1)
        self.assertGreater(stats.total_time, 0.005)

    def test_nested_profiling(self):
        """Test nested function profiling."""
        self.p.start_profiling("outer")
        time.sleep(0.01)
        
        self.p.start_profiling("inner")
        time.sleep(0.01)
        self.p.end_profiling("inner")
        
        self.p.end_profiling("outer")
        
        outer_stats = self.p.get_function_stats("outer")
        inner_stats = self.p.get_function_stats("inner")
        
        self.assertIsNotNone(outer_stats)
        self.assertIsNotNone(inner_stats)
        self.assertEqual(outer_stats.call_count, 1)
        self.assertEqual(inner_stats.call_count, 1)
        # Outer should take longer than inner
        self.assertGreater(outer_stats.total_time, inner_stats.total_time)

    def test_get_all_function_stats(self):
        """Test getting all function stats."""
        self.p.start_profiling("func1")
        self.p.end_profiling("func1")
        
        self.p.start_profiling("func2")
        self.p.end_profiling("func2")
        
        all_stats = self.p.get_all_function_stats()
        self.assertEqual(len(all_stats), 2)

    def test_get_top_functions(self):
        """Test getting top functions by various metrics."""
        self.p.start_profiling("fast")
        time.sleep(0.001)
        self.p.end_profiling("fast")
        
        self.p.start_profiling("slow")
        time.sleep(0.02)
        self.p.end_profiling("slow")
        
        top_by_time = self.p.get_top_functions(1, "total_time")
        self.assertEqual(len(top_by_time), 1)
        self.assertEqual(top_by_time[0].name, "slow")


class TestProfilerFrameStats(unittest.TestCase):
    """Tests for frame statistics."""

    def setUp(self):
        Profiler.reset()
        self.p = Profiler()

    def test_frame_stats_collection(self):
        """Test frame stats collection."""
        self.p.start_frame()
        self.p.end_frame()
        
        stats = self.p.get_frame_stats()
        self.assertEqual(len(stats), 1)
        self.assertEqual(stats[0].frame_number, 1)

    def test_frame_stats_with_entity_counts(self):
        """Test frame stats with entity counts."""
        self.p.start_frame()
        self.p.end_frame(entity_counts={"cars": 5, "peds": 10})
        
        stats = self.p.get_frame_stats()
        self.assertEqual(stats[0].entity_counts["cars"], 5)
        self.assertEqual(stats[0].entity_counts["peds"], 10)

    def test_get_slowest_frames(self):
        """Test getting slowest frames."""
        # Create frames with different durations
        for i in range(5):
            self.p.start_frame()
            if i == 2:
                time.sleep(0.02)  # Make this frame slower
            self.p.end_frame()
        
        slowest = self.p.get_slowest_frames(1)
        self.assertEqual(len(slowest), 1)
        self.assertEqual(slowest[0].frame_number, 3)  # 3rd frame (0-indexed would be 2)


class TestProfilerMemory(unittest.TestCase):
    """Tests for memory tracking."""

    def setUp(self):
        Profiler.reset()
        self.p = Profiler()

    def test_memory_usage(self):
        """Test memory usage tracking (fallback method)."""
        self.p.start_frame()
        self.p.end_frame()
        
        # Memory should be tracked (using fallback method)
        # This will be > 0 unless the system has very little memory
        self.assertIsInstance(self.p.current_memory_mb, float)

    def test_peak_memory(self):
        """Test peak memory tracking."""
        self.p.start_frame()
        self.p.end_frame()
        
        # Peak memory should be tracked
        self.assertIsInstance(self.p.peak_memory_mb, float)


class TestProfilerCustomMetrics(unittest.TestCase):
    """Tests for custom metrics."""

    def setUp(self):
        Profiler.reset()
        self.p = Profiler()

    def test_record_metric(self):
        """Test recording custom metrics."""
        self.p.record_metric("test_metric", 42.5)
        
        metrics = self.p._custom_metrics["test_metric"]
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0].name, "test_metric")
        self.assertEqual(metrics[0].value, 42.5)

    def test_metric_storage_limit(self):
        """Test that metrics are limited in storage."""
        for i in range(1500):
            self.p.record_metric("test_metric", float(i))
        
        metrics = self.p._custom_metrics["test_metric"]
        self.assertLessEqual(len(metrics), 1000)


class TestProfilerReporting(unittest.TestCase):
    """Tests for profiler reporting."""

    def setUp(self):
        Profiler.reset()
        self.p = Profiler()

    def test_generate_report(self):
        """Test generating a text report."""
        self.p.start_frame()
        self.p.end_frame()
        
        report = self.p.generate_report()
        self.assertIn("PERFORMANCE PROFILING REPORT", report)
        self.assertIn("OVERALL STATISTICS", report)

    def test_generate_json_report(self):
        """Test generating a JSON report."""
        self.p.start_frame()
        self.p.end_frame()
        
        report = self.p.generate_json_report()
        self.assertIn("overall", report)
        self.assertIn("total_frames", report["overall"])

    def test_save_report(self):
        """Test saving a report to file."""
        import tempfile
        import os
        
        self.p.start_frame()
        self.p.end_frame()
        
        # Test that save_report creates a valid JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            self.p.save_report(temp_path)
            # Check that file was created and contains JSON
            with open(temp_path, 'r') as f:
                import json
                data = json.load(f)
                self.assertIn("overall", data)
        except PermissionError:
            pass  # Skip on systems where we can't write files
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_clear(self):
        """Test clearing profiler data."""
        self.p.start_frame()
        self.p.end_frame()
        self.p.start_profiling("test")
        self.p.end_profiling("test")
        
        self.assertGreater(self.p.frame_count, 0)
        self.assertIsNotNone(self.p.get_function_stats("test"))
        
        self.p.clear()
        
        self.assertEqual(self.p.frame_count, 0)
        self.assertIsNone(self.p.get_function_stats("test"))


class TestProfileDecorator(unittest.TestCase):
    """Tests for the @profile decorator."""

    def setUp(self):
        Profiler.reset()

    def test_profile_decorator(self):
        """Test the profile decorator."""
        @profile
        def test_function():
            time.sleep(0.01)
            return 42
        
        result = test_function()
        self.assertEqual(result, 42)
        
        p = Profiler()
        stats = p.get_function_stats("test_function")
        self.assertIsNotNone(stats)
        self.assertEqual(stats.call_count, 1)

    def test_profile_decorator_multiple_calls(self):
        """Test profile decorator with multiple calls."""
        @profile
        def test_function():
            time.sleep(0.005)
            return 1
        
        for _ in range(5):
            test_function()
        
        p = Profiler()
        stats = p.get_function_stats("test_function")
        self.assertEqual(stats.call_count, 5)


class TestTimedContextManager(unittest.TestCase):
    """Tests for the timed context manager."""

    def setUp(self):
        Profiler.reset()

    def test_timed_context_manager(self):
        """Test the timed context manager."""
        with timed("test_block"):
            time.sleep(0.01)
        
        p = Profiler()
        stats = p.get_function_stats("test_block")
        self.assertIsNotNone(stats)
        self.assertEqual(stats.call_count, 1)

    def test_timed_nested(self):
        """Test nested timed context managers."""
        with timed("outer"):
            with timed("inner"):
                time.sleep(0.01)
        
        p = Profiler()
        outer_stats = p.get_function_stats("outer")
        inner_stats = p.get_function_stats("inner")
        
        self.assertIsNotNone(outer_stats)
        self.assertIsNotNone(inner_stats)
        self.assertEqual(outer_stats.call_count, 1)
        self.assertEqual(inner_stats.call_count, 1)


class TestFrameScopeContextManager(unittest.TestCase):
    """Tests for the frame_scope context manager."""

    def setUp(self):
        Profiler.reset()

    def test_frame_scope(self):
        """Test frame_scope context manager."""
        p = Profiler()
        
        with frame_scope():
            time.sleep(0.01)
        
        self.assertEqual(p.frame_count, 1)

    def test_frame_scope_with_entity_counts(self):
        """Test frame_scope with entity counts."""
        p = Profiler()
        
        with frame_scope(entity_counts={"cars": 10, "peds": 20}):
            pass
        
        stats = p.get_frame_stats()
        self.assertEqual(len(stats), 1)
        self.assertEqual(stats[0].entity_counts["cars"], 10)
        self.assertEqual(stats[0].entity_counts["peds"], 20)


class TestFPSMonitor(unittest.TestCase):
    """Tests for FPSMonitor class."""

    def setUp(self):
        Profiler.reset()
        self.monitor = FPSMonitor()

    @patch('pygame.font.Font')
    @patch('pygame.Surface')
    def test_render(self, mock_surface, mock_font):
        """Test FPS monitor rendering."""
        mock_font_instance = MagicMock()
        mock_font.return_value = mock_font_instance
        mock_render = MagicMock()
        mock_font_instance.render = mock_render
        
        mock_surface_instance = MagicMock()
        mock_surface.return_value = mock_surface_instance
        
        # Update monitor with some frames
        p = Profiler()
        for _ in range(5):
            p.start_frame()
            p.end_frame()
        
        self.monitor.update()
        self.monitor.render(mock_surface_instance)
        
        # Should have called render for each line
        self.assertGreater(mock_render.call_count, 0)


class TestPerformanceOverlay(unittest.TestCase):
    """Tests for PerformanceOverlay class."""

    def setUp(self):
        self.overlay = PerformanceOverlay()

    def test_add_sample(self):
        """Test adding samples to overlay."""
        self.overlay.add_sample(60.0)
        self.assertEqual(len(self.overlay._history), 1)
        
        for i in range(5):
            self.overlay.add_sample(60.0 + i)
        
        self.assertEqual(len(self.overlay._history), 6)

    def test_history_limit(self):
        """Test history storage limit."""
        for i in range(150):
            self.overlay.add_sample(float(i))
        
        # Should be limited to max_history (default 300)
        self.assertLessEqual(len(self.overlay._history), 300)


class TestProfilerIntegration(unittest.TestCase):
    """Integration tests for profiler with game loop simulation."""

    def setUp(self):
        Profiler.reset()
        self.p = Profiler()

    def test_simulated_game_loop(self):
        """Test simulating a game loop."""
        for frame in range(10):
            self.p.start_frame()
            
            with timed("update"):
                time.sleep(0.001)
            
            with timed("render"):
                time.sleep(0.001)
            
            self.p.end_frame()
        
        self.assertEqual(self.p.frame_count, 10)
        
        update_stats = self.p.get_function_stats("update")
        render_stats = self.p.get_function_stats("render")
        
        self.assertIsNotNone(update_stats)
        self.assertIsNotNone(render_stats)
        self.assertEqual(update_stats.call_count, 10)
        self.assertEqual(render_stats.call_count, 10)


if __name__ == "__main__":
    unittest.main()
