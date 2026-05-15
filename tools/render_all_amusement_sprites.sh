#!/bin/bash
# Skript zum Rendern aller Amusement-Park Sprites
# Aufruf: ./tools/render_all_amusement_sprites.sh

cd "$(dirname "$0")/.."

echo "========================================"
echo "Rendere alle Amusement-Park Sprites..."
echo "========================================"
echo

# Standard: Einzelbilder mit 36 Frames
python tools/render_amusement_sprites.py \
    --ride alle \
    --frames 36 \
    --size 200 \
    --transparent \
    --verbose

echo
echo "✓ Fertig! Sprites in assets/sprites/amusement/ gespeichert"
