Grand Vibe Auto
==============

A 2D open-world game inspired by GTA.

## Usage

```bash
usage: game2d.py [-h] [-log [LOG_GROUPS]]

options:
  -h, --help            show this help message and exit
  -log [LOG_GROUPS], --log [LOG_GROUPS]
                        Enable logging output. Options: p (performance), e (events), m (movement).
                        Combine: -log pe or -log pem (default: p)
```

### Logging Options

You can enable specific logging groups to get detailed debug information:

- **`-log p`** or **`--log p`**: Enable performance logging (FPS, frame times, profiling)
- **`-log e`** or **`--log e`**: Enable events logging (entity spawns, kills, damage)
- **`-log m`** or **`--log m`**: Enable movement logging (AI pathfinding, collisions)
- **`-log pem`** or **`--log pem`**: Enable all logging groups

If no group is specified, performance logging (`p`) is enabled by default.
