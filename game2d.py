#!/home/jixo/GTA/venv/bin/python3
"""Mini GTA 2D — Einstiegspunkt.

Die gesamte Spiellogik ist in das Paket `game2d/` ausgelagert.
Diese Datei delegiert nur an `game2d.main`.
"""
from game2d.main import main


if __name__ == "__main__":
    main()
