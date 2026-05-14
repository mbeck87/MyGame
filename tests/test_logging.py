"""Tests für das Logging-System."""
import unittest
import os
import tempfile
import shutil
from io import StringIO
from contextlib import redirect_stdout

from game2d.systems.logging import (
    Logger,
    LogLevel,
    get_logger,
    configure_logging,
    shutdown_logging,
)


class TestLogLevel(unittest.TestCase):
    """Testet die LogLevel-Enum."""

    def test_level_order(self):
        """Testet dass LogLevels in der richtigen Reihenfolge sind."""
        self.assertLess(LogLevel.DEBUG.value, LogLevel.INFO.value)
        self.assertLess(LogLevel.INFO.value, LogLevel.WARNING.value)
        self.assertLess(LogLevel.WARNING.value, LogLevel.ERROR.value)
        self.assertLess(LogLevel.ERROR.value, LogLevel.CRITICAL.value)

    def test_level_values(self):
        """Testet die konkreten Werte der LogLevels."""
        self.assertEqual(LogLevel.DEBUG.value, 10)
        self.assertEqual(LogLevel.INFO.value, 20)
        self.assertEqual(LogLevel.WARNING.value, 30)
        self.assertEqual(LogLevel.ERROR.value, 40)
        self.assertEqual(LogLevel.CRITICAL.value, 50)


class TestLogger(unittest.TestCase):
    """Testet den Logger."""

    def setUp(self):
        """Erstellt ein temporäres Verzeichnis für Test-Logdateien."""
        self.test_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.test_dir, 'test.log')

    def tearDown(self):
        """Bereinigt temporäre Dateien."""
        shutdown_logging()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_logger_creation(self):
        """Testet die Logger-Erstellung."""
        logger = Logger('test')
        self.assertEqual(logger.name, 'test')
        self.assertEqual(logger.level, LogLevel.INFO)

    def test_logger_with_file(self):
        """Testet Logger mit Dateiausgabe."""
        logger = Logger('test', file_path=self.log_file)
        self.assertTrue(os.path.exists(self.log_file))
        logger.info("Test message")
        logger.close()
        
        with open(self.log_file, 'r') as f:
            content = f.read()
        self.assertIn('Test message', content)
        self.assertIn('INFO', content)

    def test_log_level_filtering(self):
        """Testet dass Nachrichten unter dem LogLevel gefiltert werden."""
        logger = Logger('test', level=LogLevel.WARNING)
        
        # Diese sollten nicht ausgegeben werden
        with redirect_stdout(StringIO()) as f:
            logger.debug("Debug message")
            logger.info("Info message")
        self.assertEqual(f.getvalue(), '')
        
        # Diese sollten ausgegeben werden
        with redirect_stdout(StringIO()) as f:
            logger.warning("Warning message")
        output = f.getvalue()
        self.assertIn('Warning message', output)

    def test_set_level(self):
        """Testet das Setzen des LogLevels."""
        logger = Logger('test', level=LogLevel.INFO)
        logger.set_level(LogLevel.DEBUG)
        self.assertEqual(logger.level, LogLevel.DEBUG)

    def test_message_formatting(self):
        """Testet die Nachrichtenformatierung."""
        logger = Logger('test', level=LogLevel.DEBUG, use_colors=False)
        
        with redirect_stdout(StringIO()) as f:
            logger.info("Test message")
        
        output = f.getvalue()
        self.assertIn('[INFO]', output)
        self.assertIn('[test]', output)
        self.assertIn('Test message', output)

    def test_message_with_context(self):
        """Testet Nachrichten mit Kontext."""
        logger = Logger('test', level=LogLevel.DEBUG, use_colors=False)
        
        with redirect_stdout(StringIO()) as f:
            logger.info("Test message", key1='value1', key2='value2')
        
        output = f.getvalue()
        self.assertIn('key1=value1', output)
        self.assertIn('key2=value2', output)

    def test_all_log_levels(self):
        """Testet alle Log-Levels."""
        logger = Logger('test', level=LogLevel.DEBUG, use_colors=False)
        
        with redirect_stdout(StringIO()) as f:
            logger.debug("Debug")
            logger.info("Info")
            logger.warning("Warning")
            logger.error("Error")
            logger.critical("Critical")
        
        output = f.getvalue()
        self.assertIn('Debug', output)
        self.assertIn('Info', output)
        self.assertIn('Warning', output)
        self.assertIn('Error', output)
        self.assertIn('Critical', output)

    def test_exception_logging(self):
        """Testet das Logging von Ausnahmen."""
        logger = Logger('test', level=LogLevel.DEBUG, use_colors=False)
        
        try:
            raise ValueError("Test error")
        except ValueError as e:
            with redirect_stdout(StringIO()) as f:
                logger.exception("Exception occurred", exc=e)
        
        output = f.getvalue()
        self.assertIn('Exception occurred', output)
        self.assertIn('ValueError', output)
        self.assertIn('Test error', output)

    def test_close(self):
        """Testet das Schließen des Loggers."""
        logger = Logger('test', file_path=self.log_file)
        logger.close()
        self.assertIsNone(logger._file_handle)


class TestGetLogger(unittest.TestCase):
    """Testet die get_logger Funktion."""

    def setUp(self):
        """Setzt den Logger-Cache zurück."""
        # da shutdown_logging den Cache löscht
        shutdown_logging()

    def tearDown(self):
        """Bereinigt."""
        shutdown_logging()

    def test_get_logger_creates_new(self):
        """Testet dass get_logger einen neuen Logger erstellt."""
        logger = get_logger('test_module')
        self.assertIsInstance(logger, Logger)
        self.assertEqual(logger.name, 'test_module')

    def test_get_logger_returns_cached(self):
        """Testet dass get_logger den gecachten Logger zurückgibt."""
        logger1 = get_logger('test_module')
        logger2 = get_logger('test_module')
        self.assertIs(logger1, logger2)

    def test_get_logger_different_names(self):
        """Testet dass verschiedene Namen verschiedene Logger ergeben."""
        logger1 = get_logger('module1')
        logger2 = get_logger('module2')
        self.assertIsNot(logger1, logger2)


class TestConfigureLogging(unittest.TestCase):
    """Testet die configure_logging Funktion."""

    def setUp(self):
        """Setzt zurück."""
        shutdown_logging()

    def tearDown(self):
        """Bereinigt."""
        shutdown_logging()

    def test_configure_level(self):
        """Testet die Konfiguration des LogLevels."""
        configure_logging(level=LogLevel.DEBUG)
        logger = get_logger('test')
        self.assertEqual(logger.level, LogLevel.DEBUG)

    def test_configure_file(self):
        """Testet die Konfiguration der Logdatei."""
        test_dir = tempfile.mkdtemp()
        log_file = os.path.join(test_dir, 'configured.log')
        
        try:
            configure_logging(file_path=log_file)
            logger = get_logger('test')
            logger.info("Test message")
            logger.close()
            
            self.assertTrue(os.path.exists(log_file))
            with open(log_file, 'r') as f:
                content = f.read()
            self.assertIn('Test message', content)
        finally:
            shutdown_logging()
            shutil.rmtree(test_dir, ignore_errors=True)


class TestShutdownLogging(unittest.TestCase):
    """Testet die shutdown_logging Funktion."""

    def test_shutdown_clears_cache(self):
        """Testet dass shutdown_logging den Cache leert."""
        logger = get_logger('test')
        shutdown_logging()
        # Der Cache sollte leer sein
        from game2d.systems.logging import _loggers
        self.assertEqual(len(_loggers), 0)


class TestConvenienceFunctions(unittest.TestCase):
    """Testet die Convenience-Funktionen."""

    def setUp(self):
        """Setzt zurück."""
        shutdown_logging()

    def tearDown(self):
        """Bereinigt."""
        shutdown_logging()

    def test_convenience_functions(self):
        """Testet die Modul-Level Convenience-Funktionen."""
        from game2d.systems.logging import debug, info, warning, error, critical
        
        with redirect_stdout(StringIO()) as f:
            debug("Debug")
            info("Info")
            warning("Warning")
            error("Error")
            critical("Critical")
        
        output = f.getvalue()
        self.assertIn('Debug', output)
        self.assertIn('Info', output)
        self.assertIn('Warning', output)
        self.assertIn('Error', output)
        self.assertIn('Critical', output)


if __name__ == '__main__':
    unittest.main()
