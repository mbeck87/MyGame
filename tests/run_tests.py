#!/usr/bin/env python
"""Test Runner für Mini GTA 2D Unit Tests.

Führt alle Tests im tests/ Verzeichnis aus.

Usage:
    python tests/run_tests.py        # Alle Tests
    python tests/run_tests.py -v     # Verbose Modus
    python -m unittest discover -s tests  # Alternative
"""
import argparse
import unittest
import sys
import os


def run_tests(verbose=False, pattern='test_*.py'):
    """Führt alle Tests aus.
    
    Args:
        verbose: Ausführliche Ausgabe
        pattern: Dateimuster für Testdateien
    
    Returns:
        True wenn alle Tests bestanden, sonst False
    """
    # Projekt-Root zum PYTHONPATH hinzufügen
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # Tests aus dem tests/ Verzeichnis laden
    loader = unittest.TestLoader()
    suite = loader.discover('tests', pattern=pattern)
    
    # Test Runner
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def main():
    parser = argparse.ArgumentParser(
        description='Führe Unit Tests für Mini GTA 2D aus'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Ausführliche Ausgabe'
    )
    parser.add_argument(
        '-p', '--pattern',
        default='test_*.py',
        help='Dateimuster für Testdateien (Default: test_*.py)'
    )
    
    args = parser.parse_args()
    success = run_tests(verbose=args.verbose, pattern=args.pattern)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
