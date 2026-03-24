# Trayffeine

Trayffeine is a small Windows tray app that keeps the computer awake by simulating `F15` every 59 seconds while a session is active.

It is developed from WSL, but the official Windows build is produced in GitHub Actions on `windows-latest`.

## Current Status

- Windows tray app with no main window
- Presets for `15 min`, `30 min`, `1 h`, `2 h`, and `Infinite`
- Automatic shutdown when a timed session expires
- Toast notification only when the timer ends
- Single-instance guard on Windows
- Runtime localization with `Auto`, `pt-BR`, `en`, and `es`
- In-memory language override from the tray menu, with fallback to English

## Project Layout

- `src/trayffeine/app.py`: runtime bootstrap and single-instance startup flow
- `src/trayffeine/tray.py`: tray icon, menu, language switching, notifications
- `src/trayffeine/service.py`: background worker that drives keep-awake timing
- `src/trayffeine/session.py`: session state and stable preset keys
- `src/trayffeine/presenter.py`: presentation helpers for menu, tooltip, notifications
- `src/trayffeine/i18n.py`: locale detection, catalogs, translation helpers
- `tests/`: unit and smoke-style tests for session, i18n, presenter, tray bootstrap
- `packaging/windows/`: PyInstaller spec, build script, and Inno Setup installer script

## Local Development

### WSL workflow

Use WSL for editing, linting, and tests:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e .[dev]
python scripts/generate_assets.py
ruff check .
pytest
```

### Windows workflow

Run the app locally from a real Windows path when you need to validate tray behavior:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .[dev,build]
python scripts\generate_assets.py
python -m trayffeine
```

## Packaging

The release workflow builds:

1. A PyInstaller `onedir` bundle
2. An Inno Setup installer `.exe`

Manual Windows packaging:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .[build]
python scripts\generate_assets.py
powershell -ExecutionPolicy Bypass -File packaging\windows\build.ps1 -Version 0.2.0 -Clean
```

## GitHub Actions

- `CI`: runs on pushes to `main` and on pull requests
- `Release`: runs only on tags matching `v*`
- Official releases are generated from the Windows workflow and uploaded as GitHub release assets

## Localization Notes

- English is the source and fallback language in code
- Supported locales: `en`, `pt-BR`, `es`
- Locale is auto-detected at startup
- Manual selection in the tray menu does not persist across launches
- Installer localization is not part of the runtime i18n layer

## Validation

Current expected local validation:

```bash
. .venv/bin/activate
ruff check .
pytest
```

Tray behavior itself must still be verified interactively on Windows because `pystray` runtime behavior is only partially covered by unit tests.

