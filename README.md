# Trayffeine

Trayffeine is a small Windows tray app that keeps the computer awake by simulating `F15` every 59 seconds while a session is active.

## Features

- Windows system tray app with no main window
- Presets for `15 min`, `30 min`, `1 h`, `2 h`, and `Infinite`
- Automatic shutdown when a timed session expires
- Toast notification only when the timer ends
- Single-instance guard on Windows

## Local development

Use WSL for editing, linting, and tests:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e .[dev]
python scripts/generate_assets.py
ruff check .
pytest
```

The Windows executable is not built from WSL. The official build runs in GitHub Actions on `windows-latest`.

## Running locally on Windows

From a Windows shell in a real Windows path:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .[dev,build]
python scripts\generate_assets.py
python -m trayffeine
```

## Windows packaging

The release workflow builds:

1. A PyInstaller `onedir` bundle
2. An Inno Setup installer `.exe`

The same steps can be run manually on Windows:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .[build]
python scripts\generate_assets.py
powershell -ExecutionPolicy Bypass -File packaging\windows\build.ps1 -Version 0.1.0 -Clean
```

