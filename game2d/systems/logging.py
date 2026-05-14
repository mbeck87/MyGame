"""Logging-System für Mini GTA 2D.

Bietet ein einfaches, strukturiertes Logging ohne externe Dependencies.
Log-Nachrichten können in Datei, Konsole oder beides ausgegeben werden.

Usage:
    from game2d.systems.logging import get_logger, LogLevel
    
    logger = get_logger('module_name')
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")
"""
import os
import sys
from datetime import datetime
from enum import IntEnum
from typing import Optional, TextIO


class LogLevel(IntEnum):
    """Log-Level Konstanten."""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


# Farbcodes für Terminal-Ausgabe (ANSI)
COLORS = {
    LogLevel.DEBUG: '\033[36m',    # Cyan
    LogLevel.INFO: '\033[32m',     # Grün
    LogLevel.WARNING: '\033[33m',  # Gelb
    LogLevel.ERROR: '\033[31m',    # Rot
    LogLevel.CRITICAL: '\033[35;1m',  # Magenta + Fett
}

RESET_COLOR = '\033[0m'


class Logger:
    """Einfacher Logger für strukturierte Log-Nachrichten.
    
    Unterstützt verschiedene Log-Levels und Ausgabeziele (Datei, Konsole).
    """
    
    def __init__(
        self,
        name: str,
        level: LogLevel = LogLevel.INFO,
        file_path: Optional[str] = None,
        use_colors: bool = True
    ):
        """Initialisiert den Logger.
        
        Args:
            name: Name des Loggers (z.B. Modulname)
            level: Mindest-LogLevel für Ausgabe
            file_path: Pfad zur Log-Datei (optional)
            use_colors: Farbige Ausgabe in Konsole (Default: True)
        """
        self.name = name
        self.level = level
        self.use_colors = use_colors
        self.file_path = file_path
        
        # Datei-Handle für persistentes Logging
        self._file_handle: Optional[TextIO] = None
        if file_path:
            try:
                self._file_handle = open(file_path, 'a', encoding='utf-8')
            except OSError as e:
                print(f"WARNING: Konnte Log-Datei {file_path} nicht öffnen: {e}", 
                      file=sys.stderr)
    
    def set_level(self, level: LogLevel) -> None:
        """Setzt das Log-Level."""
        self.level = level
    
    def set_file(self, file_path: Optional[str]) -> None:
        """Setzt oder entfernt die Log-Datei."""
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None
        
        self.file_path = file_path
        if file_path:
            try:
                self._file_handle = open(file_path, 'a', encoding='utf-8')
            except OSError as e:
                print(f"WARNING: Konnte Log-Datei {file_path} nicht öffnen: {e}", 
                      file=sys.stderr)
    
    def _format_message(self, level: LogLevel, message: str, context: Optional[dict] = None) -> str:
        """Formatiert eine Log-Nachricht."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        level_name = level.name
        
        if context:
            context_str = ' ' + ' '.join(f"{k}={v}" for k, v in context.items())
        else:
            context_str = ''
        
        return f"[{timestamp}] [{level_name}] [{self.name}] {message}{context_str}"
    
    def _get_color(self, level: LogLevel) -> str:
        """Holt den Farbcode für ein Log-Level."""
        if self.use_colors:
            return COLORS.get(level, '')
        return ''
    
    def _write(self, level: LogLevel, message: str, context: Optional[dict] = None) -> None:
        """Schreibt eine Log-Nachricht."""
        if level.value < self.level.value:
            return
        
        formatted = self._format_message(level, message, context)
        color = self._get_color(level)
        
        # Konsole
        if color:
            print(f"{color}{formatted}{RESET_COLOR}", file=sys.stdout)
        else:
            print(formatted, file=sys.stdout)
        
        # Datei
        if self._file_handle:
            self._file_handle.write(formatted + '\n')
            self._file_handle.flush()
    
    def debug(self, message: str, **context) -> None:
        """Loggt eine Debug-Nachricht."""
        self._write(LogLevel.DEBUG, message, context)
    
    def info(self, message: str, **context) -> None:
        """Loggt eine Info-Nachricht."""
        self._write(LogLevel.INFO, message, context)
    
    def warning(self, message: str, **context) -> None:
        """Loggt eine Warnung."""
        self._write(LogLevel.WARNING, message, context)
    
    def error(self, message: str, **context) -> None:
        """Loggt einen Fehler."""
        self._write(LogLevel.ERROR, message, context)
    
    def critical(self, message: str, **context) -> None:
        """Loggt eine kritische Nachricht."""
        self._write(LogLevel.CRITICAL, message, context)
    
    def exception(self, message: str, exc: Exception, **context) -> None:
        """Loggt eine Ausnahme mit Stacktrace."""
        import traceback
        tb_str = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        self._write(LogLevel.ERROR, f"{message}\n{tb_str}", context)
    
    def close(self) -> None:
        """Schließt den Logger und die Datei-Handles."""
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None


# =============================================================================
# Globale Logger-Instanzen und Helfer
# =============================================================================

# Standard-Log-Level (kann über Umgebungsvariable überschrieben werden)
_DEFAULT_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
_LEVEL_MAP = {
    'DEBUG': LogLevel.DEBUG,
    'INFO': LogLevel.INFO,
    'WARNING': LogLevel.WARNING,
    'ERROR': LogLevel.ERROR,
    'CRITICAL': LogLevel.CRITICAL,
}
DEFAULT_LOG_LEVEL = _LEVEL_MAP.get(_DEFAULT_LEVEL, LogLevel.INFO)

# Log-Datei-Pfad (kann über Umgebungsvariable überschrieben werden)
_LOG_FILE = os.environ.get('LOG_FILE', None)

# Globale Logger-Cache
_loggers: dict[str, Logger] = {}


def get_logger(name: str, file_path: Optional[str] = None) -> Logger:
    """Holt oder erstellt einen Logger mit dem gegebenen Namen.
    
    Args:
        name: Name des Loggers
        file_path: Pfad zur Log-Datei (überschreibt Standard)
    
    Returns:
        Logger-Instanz
    """
    if name not in _loggers:
        effective_file = file_path if file_path is not None else _LOG_FILE
        _loggers[name] = Logger(
            name=name,
            level=DEFAULT_LOG_LEVEL,
            file_path=effective_file
        )
    return _loggers[name]


def configure_logging(
    level: Optional[LogLevel] = None,
    file_path: Optional[str] = None,
    use_colors: bool = True
) -> None:
    """Konfiguriert die globalen Logging-Einstellungen.
    
    Args:
        level: Standard-LogLevel für neue Logger
        file_path: Standard-LogDatei-Pfad
        use_colors: Farbige Ausgabe aktivieren/deaktivieren
    """
    global DEFAULT_LOG_LEVEL, _LOG_FILE
    
    if level is not None:
        DEFAULT_LOG_LEVEL = level
    
    if file_path is not None:
        _LOG_FILE = file_path
    
    # Aktualisiere alle existierenden Logger
    for logger in _loggers.values():
        if level is not None:
            logger.set_level(level)
        if file_path is not None and logger.file_path is None:
            logger.set_file(file_path)
        logger.use_colors = use_colors


def shutdown_logging() -> None:
    """Schließt alle Logger und bereinigt Ressourcen."""
    for logger in _loggers.values():
        logger.close()
    _loggers.clear()


# =============================================================================
# Modul-Level Convenience Functions
# =============================================================================

# Standard-Logger für generelle Nachrichten
_general_logger = None


def get_general_logger() -> Logger:
    """Holt den generellen Logger."""
    global _general_logger
    if _general_logger is None:
        _general_logger = get_logger('general')
    return _general_logger


def debug(message: str, **context) -> None:
    """Loggt eine Debug-Nachricht (generell)."""
    get_general_logger().debug(message, **context)


def info(message: str, **context) -> None:
    """Loggt eine Info-Nachricht (generell)."""
    get_general_logger().info(message, **context)


def warning(message: str, **context) -> None:
    """Loggt eine Warnung (generell)."""
    get_general_logger().warning(message, **context)


def error(message: str, **context) -> None:
    """Loggt einen Fehler (generell)."""
    get_general_logger().error(message, **context)


def critical(message: str, **context) -> None:
    """Loggt eine kritische Nachricht (generell)."""
    get_general_logger().critical(message, **context)
