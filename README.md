# Trayffeine

Trayffeine is a small Windows tray app that keeps the computer awake by simulating `F15` every 59 seconds while a session is active.

It is developed from WSL, but the official Windows build is produced in GitHub Actions on `windows-latest`.

## Current Status

- Windows tray app with no main window
- Tray menu shows a stable status summary, while the live counter stays in the tray tooltip
- Presets for `15 min`, `30 min`, `1 h`, `2 h`, and `Infinite`
- Automatic shutdown when a timed session expires
- Toast notification only when the timer ends
- Single-instance guard on Windows
- Runtime localization with `Auto`, `pt-BR`, `en`, and `es`
- Persistent language selection from the tray menu, with fallback to English
- Infinite mode can be restored on the next launch, while timed sessions still start inactive
- Double-clicking the tray icon toggles infinite mode on and off
- The tray menu can open the logs folder for support and bug reports

## Project Layout

- `src/trayffeine/app.py`: runtime bootstrap and single-instance startup flow
- `src/trayffeine/tray.py`: tray icon, menu, language switching, double-click handling, notifications, support actions
- `src/trayffeine/service.py`: background worker that drives keep-awake timing and live status refresh
- `src/trayffeine/session.py`: session state and stable preset keys
- `src/trayffeine/presenter.py`: presentation helpers for menu, tooltip, live status, and notifications
- `src/trayffeine/i18n.py`: locale detection, catalogs, translation helpers
- `src/trayffeine/settings.py`: persisted settings storage for language selection and infinite restore
- `src/trayffeine/win32_tray.py`: Windows-specific tray icon wrapper for real double-click handling
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
powershell -ExecutionPolicy Bypass -File packaging\windows\build.ps1 -Version 0.5.0-beta2 -Clean
```

## GitHub Actions

- `CI`: runs on pushes to `main` and on pull requests
- `Release`: runs only on tags matching `v*`
- Official releases are generated from the Windows workflow and uploaded as GitHub release assets
- Release publishing uses the `gh` CLI on the Windows runner, which avoids the old Node 20 release action warning
- Tags matching `v*-beta*` are published as GitHub prereleases

## Localization Notes

- English is the source and fallback language in code
- Supported locales: `en`, `pt-BR`, `es`
- Locale is auto-detected at startup
- Manual selection in the tray menu persists across launches
- `Auto` keeps following the system locale
- Timed sessions still start inactive on relaunch; only infinite mode is restored
- Installer localization is not part of the runtime i18n layer

## Validation

Current expected local validation:

```bash
. .venv/bin/activate
ruff check .
pytest
```

Tray behavior itself must still be verified interactively on Windows because `pystray` runtime behavior is only partially covered by unit tests.

Runtime logs are written to `%LOCALAPPDATA%\Trayffeine\logs\trayffeine.log` on Windows.
They rotate automatically at `256 KB` with `3` backups.
The default log level is `WARNING`; use `TRAYFFEINE_LOG_LEVEL=INFO` only when diagnosing tray issues.
The native Windows tray menu does not live-refresh while it is open, so Trayffeine keeps the precise live counter in the icon tooltip instead.

## Beta Notes

- Beta builds are Windows-only and currently intended for a small closed group of testers.
- The installer is unsigned, so Windows and SmartScreen warnings are expected.
- Use the tray action `Open Logs Folder` to reach `%LOCALAPPDATA%\Trayffeine\logs`.
- If the app crashes, it writes the traceback to the log file and shows a small dialog pointing to the logs folder.
- Report bugs with:
  - the exact Trayffeine version
  - your Windows version
  - steps to reproduce
  - the contents of `%LOCALAPPDATA%\Trayffeine\logs\trayffeine.log`
- Known limitation: the native Windows tray menu does not live-refresh while it is open.
