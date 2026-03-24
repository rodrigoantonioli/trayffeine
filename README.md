# Trayffeine

Trayffeine is a small Windows tray app that keeps the computer awake while a session is active. It supports a configurable keep-awake method with a smart fallback order inspired by Caffeine.

Development happens in WSL, but the official Windows build is produced in GitHub Actions on `windows-latest`.

## Current Status

- Windows tray app with no main window
- Presets for `15 min`, `30 min`, `1 h`, `2 h`, and `Infinite`
- Automatic shutdown when a timed session expires
- Toast notification only when the timer ends
- Single-instance guard on Windows
- Runtime localization with `Auto`, `pt-BR`, `en`, and `es`
- Persistent language selection from the tray menu, with fallback to English
- Infinite mode can be restored on the next launch, while timed sessions still start inactive
- Persistent keep-awake method selection with `Smart`, `Windows API`, `F15`, and `Shift`
- Double-clicking the tray icon toggles infinite mode on and off
- Grouped tray menu with `Preferences` and `Support` submenus
- Persistent `Detailed logging` toggle
- Support actions to open or clear the logs folder

## Tray Menu UX

The menu is intentionally split into stable sections:

- top status rows
  - `Trayffeine v0.7.0`
  - a stable summary such as `Inactive`, `Active until 14:32`, or `Infinite mode active`
- primary actions
  - `Infinite mode`
  - `Activate for >`
  - `Stop`
- `Preferences >`
  - `Keep-awake method >`
  - `Language >`
  - `Detailed logging`
- `Support >`
  - `Open Logs Folder`
  - `Clear Logs`
- final action
  - `Quit`

The native Windows tray menu does not live-refresh while it is open. Trayffeine therefore keeps volatile counters in the icon tooltip and uses the open menu for stable summaries and direct actions.

## Keep-Awake Methods

Trayffeine supports four methods:

- `Smart`
  - tries `Windows API` first
  - if that method fails technically, falls back to `F15`
  - if `F15` also fails technically, falls back to `Shift`
- `Windows API`
  - uses `SetThreadExecutionState` while the session is active
- `F15`
  - simulates `F15` periodically
- `Shift`
  - simulates `Shift` periodically

Notes:

- the selected method is persisted in `settings.json`
- restored infinite mode uses the persisted method on startup
- the smart mode fallback is technical only; it does not try to prove that Windows really avoided idle

## Logging and Support

Runtime logs are written to `%LOCALAPPDATA%\Trayffeine\logs\trayffeine.log` on Windows.

Logging behavior:

- default level is `WARNING`
- logs rotate automatically at `256 KB` with `3` backups
- `Detailed logging` persists across restarts through `settings.json`
- when detailed logging is enabled, Trayffeine records meaningful user and app actions at `INFO`
- high-frequency internal refreshes such as per-second UI ticks are intentionally not logged

Detailed logging captures actions such as:

- app start and exit
- preset selection
- infinite mode toggle
- session stop
- timer expiration
- language changes
- opening the logs folder
- enabling or disabling detailed logging
- clearing logs

Environment overrides:

- `TRAYFFEINE_LOG_LEVEL` still takes precedence over the persisted menu preference
- if the environment variable is set, the tray `Detailed logging` toggle is disabled for that process

Support actions:

- `Open Logs Folder` opens `%LOCALAPPDATA%\Trayffeine\logs`
- `Clear Logs` asks for confirmation, deletes `trayffeine.log` and rotated backups, and immediately recreates a fresh current log file

If the app crashes, it writes the traceback to the log file and shows a small Windows dialog that points to the logs folder.

## Project Layout

- `src/trayffeine/app.py`: runtime bootstrap, single-instance startup flow, log-level wiring, crash boundary
- `src/trayffeine/tray.py`: tray icon, grouped menu, language switching, detailed logging toggle, support actions, notifications
- `src/trayffeine/service.py`: background worker that drives keep-awake timing and live status refresh
- `src/trayffeine/keepawake.py`: stable method ids and coercion helpers
- `src/trayffeine/session.py`: session state and stable preset keys
- `src/trayffeine/presenter.py`: presentation helpers for menu, tooltip, status summary, and notifications
- `src/trayffeine/i18n.py`: locale detection, catalogs, translation helpers
- `src/trayffeine/settings.py`: persisted settings storage for language selection, infinite restore, detailed logging, and keep-awake method
- `src/trayffeine/app_logging.py`: rotating file logger setup, runtime log-level switching, log cleanup helpers
- `src/trayffeine/win32_tray.py`: Windows-specific tray icon wrapper for real double-click handling
- `src/trayffeine/windows.py`: Windows keep-awake backends for `SendInput`, `SetThreadExecutionState`, smart fallback, dialogs, and shell open
- `tests/`: unit and smoke-style tests for session, i18n, presenter, logging, tray bootstrap, and runtime wiring
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
powershell -ExecutionPolicy Bypass -File packaging\windows\build.ps1 -Version 0.7.0 -Clean
```

## GitHub Actions

- `CI`: runs on pushes to `main` and on pull requests
- `Release`: runs only on tags matching `v*`
- official releases are generated from the Windows workflow and uploaded as GitHub release assets
- release publishing uses the `gh` CLI on the Windows runner
- tags matching `v*-beta*` are still published as GitHub prereleases, but `0.7.0` is a normal stable release

## Localization Notes

- English is the source and fallback language in code
- supported locales are `en`, `pt-BR`, and `es`
- locale is auto-detected at startup
- manual selection in the tray menu persists across launches
- `Auto` keeps following the system locale
- timed sessions still start inactive on relaunch; only infinite mode is restored
- installer localization is not part of the runtime i18n layer

## Validation

Current expected local validation:

```bash
. .venv/bin/activate
ruff check .
pytest
```

Tray behavior itself must still be verified interactively on Windows because `pystray` runtime behavior is only partially covered by unit tests.

## Support Notes

- The installer is still unsigned, so Windows and SmartScreen warnings are expected.
- When reporting a bug, include:
  - the exact Trayffeine version
  - your Windows version
  - steps to reproduce
  - the contents of `%LOCALAPPDATA%\Trayffeine\logs\trayffeine.log`
