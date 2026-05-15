"""Amusement Park Sprite Loading and Management.

Lädt vorgerenderte Sprites für den Vergnügungspark und stellt
Funktionen zum Zeichnen der Fahrgeschäfte mit diesen Sprites bereit.
"""

import os
import json
import pygame


def load_amusement_sprites(sprite_dir=None):
    """Lade alle Amusement-Park Sprites aus dem angegebenen Verzeichnis.
    
    Args:
        sprite_dir: Verzeichnis mit den Sprite-Dateien (default: assets/sprites/amusement/)
        
    Returns:
        dict: Dictionary mit geladenen Sprites und Metadaten, strukturiert nach Fahrgeschäft
              {
                  'static': pygame.Surface,  # Statisches Park-Sprite (optional)
                  'rides': {
                      'ferris_wheel': {
                          'frames': [frame0, frame1, ...],
                          'speed': 0.05,  # Animationsgeschwindigkeit
                          'frame_width': 200,
                          'frame_height': 200
                      },
                      'carousel': {...},
                      ...
                  },
                  'ride_info': {
                      'ferris_wheel': {'speed': 0.05, 'frame_width': 200, 'frame_height': 200},
                      ...
                  }
              }
    """
    if sprite_dir is None:
        # Standard-Verzeichnis relativ zum Projekt-Root
        sprite_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                "assets", "sprites", "amusement")
    
    sprites = {
        'static': None,
        'rides': {},
        'ride_info': {}
    }
    
    # Prüfe ob Verzeichnis existiert
    if not os.path.isdir(sprite_dir):
        print(f"[WARNING] Sprite-Verzeichnis nicht gefunden: {sprite_dir}")
        return sprites
    
    # Lade alle Ride-Sprites
    for filename in os.listdir(sprite_dir):
        if filename.endswith('_meta.json'):
            ride_name = filename.replace('_meta.json', '')
            meta_path = os.path.join(sprite_dir, filename)
            
            try:
                with open(meta_path, 'r') as f:
                    meta = json.load(f)
                
                ride_type = meta.get('type', 'frames')
                num_frames = meta.get('frames', 0)
                frame_width = meta.get('frame_width', 200)
                frame_height = meta.get('frame_height', 200)
                speed = meta.get('speed', 0.1)  # Default Geschwindigkeit
                
                frames = []
                if ride_type == 'frames':
                    # Lade Einzel-Frames
                    for i in range(num_frames):
                        frame_file = os.path.join(sprite_dir, f"{ride_name}_frame_{i:03d}.png")
                        if os.path.isfile(frame_file):
                            try:
                                # Lade ohne convert_alpha() - das erfordert pygame.display
                                # Die PNGs haben bereits Transparenz, also einfach laden
                                surf = pygame.image.load(frame_file)
                                frames.append(surf)
                            except Exception as e:
                                print(f"[ERROR] Konnte {frame_file} nicht laden: {e}")
                        else:
                            print(f"[WARNING] Frame-Datei nicht gefunden: {frame_file}")
                elif ride_type == 'sheet':
                    # Lade Sprite-Sheet und zerlege in Frames
                    sheet_file = os.path.join(sprite_dir, f"{ride_name}_sheet_{num_frames}f.png")
                    if os.path.isfile(sheet_file):
                        try:
                            # Lade ohne convert_alpha() - das erfordert pygame.display
                            sheet = pygame.image.load(sheet_file)
                            sheet_width = meta.get('sheet_width', frame_width * num_frames)
                            sheet_height = meta.get('sheet_height', frame_height)
                            
                            for i in range(num_frames):
                                frame = sheet.subsurface(
                                    (i * frame_width, 0, frame_width, frame_height)
                                ).copy()
                                frames.append(frame)
                        except Exception as e:
                            print(f"[ERROR] Konnte Sprite-Sheet {sheet_file} nicht laden: {e}")
                
                if frames:
                    sprites['rides'][ride_name] = {
                        'frames': frames,
                        'speed': speed,
                        'frame_width': frame_width,
                        'frame_height': frame_height
                    }
                    sprites['ride_info'][ride_name] = {
                        'speed': speed,
                        'frame_width': frame_width,
                        'frame_height': frame_height,
                        'num_frames': len(frames)
                    }
                # else: Keine Frames geladen (leise ignorieren)
                    
            except Exception as e:
                import sys
                print(f"[WARNING] Konnte Metadaten {meta_path} nicht lesen: {e}", file=sys.stderr)
    
    return sprites


def get_amusement_sprite_path():
    """Gibe den Pfad zum Amusement-Sprite-Verzeichnis zurück."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                       "assets", "sprites", "amusement")
