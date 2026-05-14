# Repository Guidelines

## Project Structure & Module Organization

This repository is a `pygame` project structured as the `game2d/` Python package. The root `game2d.py` file is only a small shim that calls `game2d.main:main()`.

```text
game2d/
├── main.py              # pygame init, GameState setup, main loop
├── config.py            # window/world sizes, colors, weapon/pickup constants
├── state.py             # @dataclass GameState + singleton accessors
├── persistence.py       # scores.json and name input screen
├── settings.py          # persisted user settings
├── assets/sfx/          # .ogg/.wav sound effects
├── entities/            # Car and Ped classes
├── render/              # sprites, world background, HUD, minimap, menus
├── systems/             # audio, weapons, effects, services, pooling, spatial, events, logging, profiling, savegame, di, validation, utils
├── ui/                  # menu UI
└── world/               # geometry, generation, traffic, spawning
```

When adding code, follow this architecture and put functionality in the matching module under `game2d/`. Access shared runtime state through `from game2d.state import current`; `main.py` initializes the singleton with `state.init(GameState(...))`. Avoid bypassing the package split or moving state into ad hoc globals.

Contributor notes are also in `CLAUDE.md`. Local environments may appear as `venv/` or `.venv/` and should remain untracked.

---

## Build, Test, and Development Commands

There is no build step. Run the game directly from the project root.

```bash
python game2d.py
```

The package entrypoint is also supported.

```bash
python -m game2d.main
```

For a local virtual environment on Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install pygame-ce
.\.venv\Scripts\python.exe game2d.py
```

For Linux/macOS-style venv usage:

```bash
source venv/bin/activate
python game2d.py
```

For a quick syntax check:

```bash
python -m py_compile game2d.py
```

---

## Coding Style & Naming Conventions

Use 4-space indentation and keep changes ASCII unless the file already requires otherwise. Match the existing style: constants in `UPPER_SNAKE_CASE`, functions and variables in `snake_case`, and classes in `PascalCase`. Prefer small, local edits over broad refactors, since the game is stateful.

---

## Architecture Notes

`game2d/state.py` defines `GameState`, including lists for cars, peds, cops, bullets, rockets, particles, corpses, wrecks, pickups, world geometry, camera, traffic timing, and game-over state. Player-specific data lives on `state.player`, a `Ped` instance with extra fields such as `hp`, `money`, `wanted`, `crime_timer`, and `aim_angle`.

`main.py` owns the top-level flow: initialize pygame, show `name_input_screen()`, create and register `GameState`, call `build_world(state)`, spawn initial traffic/NPCs, initialize player and pickups, then run the 60 FPS event/update/render loop.

**Infrastructure Systems (integrated):**
- `systems/pooling.py` - Object pooling for bullets, rockets, particles (memory optimization)
- `systems/spatial.py` - Spatial grid for collision detection (performance optimization)
- `systems/events.py` - Event bus for game events (KILL, DAMAGE, WANTED, etc.)
- `systems/profiling.py` - Performance profiling with F12 toggle

Render order in `main.py` is world background, permanent blood splats, pickups, corpses, buildings, wrecks, cars, peds/cops/player, particles/projectiles/explosions, then HUD.

---

## Sound Assets

Sound effects live in `game2d/assets/sfx/` as `.ogg` or `.wav` files named `<category>_<variant>.ogg`, for example `door_open_a.ogg`. `audio.init()` loads `.ogg` and `.wav` automatically, and multiple variants are selected randomly by `audio.play(...)`.

When new sounds are needed, check Kenney's audio assets for general SFX and OpenGameArt with a CC0 filter for vehicle or engine sounds. Implement playback through `game2d/systems/audio.py`, usually `audio.play("category", pos=(x, y))`.

Engine sounds are the CC0 files `engine_band_0.wav` through `engine_band_3.wav` and are blended by `set_engine()` using a 4-band crossfade. Do not replace them with synthetic engine generation.

For looped sounds, use `audio.start_loop(...)` / `audio.update_loop(...)` / `audio.stop_loop(...)`.

**Important pygame-CE detail:** in `audio.py`, use `Channel.set_volume(value)` with one argument after `Channel.play(snd)`. The two-argument form sets panning rather than master channel volume, and `play()` resets channel volume.

---

## Gameplay Systems

World generation uses `WORLD_W, WORLD_H = 6000, 6000`, `BLOCK = 600`, `ROAD_W = 118`, `SIDEWALK_W = 34`, `WATER_W = 220`, `BEACH_W = 110`, and window size `W, H = 1280, 800`.

Sprites are generated procedurally at runtime. Current sprite sizes are normal/cop cars at 46x78 px, pedestrian frames at 20x24 px, and building cells at 32x32 px. Sprite coordinates use a downward Y axis; pedestrian "front" faces `-y`.

Controls: WASD moves/drives, mouse aims, LMB/SPACE shoots, E enters/exits cars, F robs pedestrians, 1-6 switch weapons, R restarts after game over, and ESC opens quit/options flow. **F12 toggles profiling display.**

Weapons are configured in `config.py`: lightsaber, pistol, SMG, shotgun, MG, and rocket launcher. Weapons 0 and 1 are available from the start; weapons 2-5 unlock through pickups. The lightsaber has infinite ammo.

Pickups are stored as `[x, y, kind, respawn_cd]` in `state.pickups`, respawn after 20 seconds, and use constants such as `PICKUP_AMMO`, `PICKUP_COLOR`, `PICKUP_LABEL`, and `PICKUP_RESPAWN`.

Wanted level ranges from 0-5 stars via `player.wanted` and `player.crime_timer`. Cops spawn through `cop_car_spawn_near()` near the player, and all cops/cop cars are removed when wanted reaches 0. Crimes include killing or running over pedestrians, killing cops, robberies, and explosions.

`trigger_game_over()` in `systems/effects.py` sets `state.game_over = True` and stores scores in `scores.json`. The scoreboard keeps the top 20 entries and `last_name`; restart uses `os.execv(sys.executable, ...)` for a full process restart.

---

## Spawning and Particle Data

Use `world/spawning.py` helpers for placement: `safe_spawn()` for pedestrians, `road_spawn()` for traffic, `cop_car_spawn_near(tx, ty)` for police vehicles, and `exit_car_position(car)` for leaving cars.

Common mutable list/tuple formats on `state`:

```python
bullets          = [x, y, vx, vy, ttl, from_cop, dmg]
blood_particles  = [x, y, vx, vy, ttl, radius]
smoke_particles  = [x, y, vx, vy, ttl, max_ttl, radius]
fire_particles   = [x, y, vx, vy, ttl, max_ttl, radius]
explosions       = [x, y, t, max_t, max_radius]
rockets          = [x, y, vx, vy, ttl, audio_channel]
wrecks           = (sprite, x, y, angle, dents_list)
corpses          = (sprite, x, y, angle)
blood_splats     = (x, y, radius, color)
```

---

## Quality Checks

Run linters after **complex changes or refactorings**:

- **Refactoring** (renaming functions, moving code): Always run `pyflakes game2d/` to find old references
- **Multiple files changed**: Run `pyflakes game2d/` and `flake8 game2d/ --max-line-length=120`
- **Single small change** (1-2 lines, value tweaks): Manual verification is sufficient

### Quick Commands

```bash
# After refactoring - find old function names
pyflakes game2d/
grep -r "old_function_name" game2d/

# Before commit
python -m py_compile game2d.py && echo "Syntax OK"
```

---

## Testing Guidelines

Automated tests are not set up yet. Before opening a PR, run `python -m py_compile game2d.py` and launch the game to verify the main loop, movement, shooting, audio, and restart flow. If you add tests later, place them under `tests/` and use names like `test_player_movement.py`.

The DI system in `systems/di.py` provides `create_test_state()` and `with_state()` context manager for isolated testing.

---

## Commit & Pull Request Guidelines

Recent commits use short, imperative messages such as `explosive autos` and `update fahrverhalten`. Follow that pattern: one clear subject line, focused on the gameplay or technical change. Pull requests should describe the behavior change, list manual verification steps, and include screenshots or a short clip for visible gameplay changes.

---

## Environment Notes

Do not commit local runtime artifacts such as `.venv/`, `venv/`, `.tmp/`, `.run.*`, `__pycache__/`, `scores.json`, or `settings.json`. Prefer `pygame-ce` on current Windows Python versions, since it provides compatible wheels earlier than classic `pygame`.
