#!/usr/bin/env -S ./venv/bin/python
"""Mini GTA 2D — Einstiegspunkt.

Die gesamte Spiellogik ist in das Paket `game2d/` ausgelagert.
Diese Datei delegiert nur an `game2d.main`.
"""
import argparse
import logging
import os
import sys

parser = argparse.ArgumentParser(description='Mini GTA 2D')
parser.add_argument('-log', '--log', action='store_true', help='Enable logging output')
args = parser.parse_args()

# Konfiguriere Standard-Logging (Python's logging Modul)
if not args.log:
    # Deaktiviere alle Standard-LoggingAusgaben
    logging.disable(logging.CRITICAL)
else:
    # Stelle sicher, dass Standard-Logging aktiviert ist
    logging.disable(logging.NOTSET)
    # Setze den Standard-Level für root logger
    logging.basicConfig(level=logging.INFO)

# Konfiguriere benutzerdefiniertes Logging-System
if args.log:
    os.environ['LOG_LEVEL'] = 'INFO'

from game2d.main import main


if __name__ == "__main__":
    main()
