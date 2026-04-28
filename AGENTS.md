# Repository Guidelines

## Project Structure & Module Organization
This repository is a small `pygame` project centered on a single source file: `game2d.py`. Game logic, rendering, world generation, and input handling all live there. Contributor notes are in `CLAUDE.md`. There is currently no `tests/` or `assets/` directory; sprites are generated procedurally at runtime. Local environments may appear as `venv/` (Linux-style) or `.venv/` (Windows-style) and should remain untracked.

## Build, Test, and Development Commands
There is no build step. Run the game directly from the project root.

```powershell
python game2d.py
```

For a local virtual environment on Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install pygame-ce
.\.venv\Scripts\python.exe game2d.py
```

For a quick syntax check:

```powershell
python -m py_compile game2d.py
```

## Coding Style & Naming Conventions
Use 4-space indentation and keep changes ASCII unless the file already requires otherwise. Match the existing style in `game2d.py`: constants in `UPPER_SNAKE_CASE`, functions and variables in `snake_case`, and classes in `PascalCase`. Prefer small, local edits over broad refactors, since the codebase is intentionally single-file and stateful.

## Testing Guidelines
Automated tests are not set up yet. Before opening a PR, run `python -m py_compile game2d.py` and launch the game to verify the main loop, movement, shooting, and restart flow. If you add tests later, place them under `tests/` and use names like `test_player_movement.py`.

## Commit & Pull Request Guidelines
Recent commits use short, imperative messages such as `explosive autos` and `update fahrverhalten`. Follow that pattern: one clear subject line, focused on the gameplay or technical change. Pull requests should describe the behavior change, list manual verification steps, and include screenshots or a short clip for visible gameplay changes.

## Environment Notes
Do not commit local runtime artifacts such as `.venv/`, `venv/`, `.tmp/`, `.run.*`, or `__pycache__/`. Prefer `pygame-ce` on current Windows Python versions, since it provides compatible wheels earlier than classic `pygame`.
