# Trayffeine

Trayffeine is a small Windows tray application that keeps the computer awake while a session is active. It is inspired by tools such as Caffeine, but focuses on a native tray workflow, configurable keep-awake methods, persistent preferences, and a simple installer pipeline.

Development happens in WSL, but official Windows installers are produced in GitHub Actions on `windows-latest`.

## Version 1.0.0

Trayffeine 1.0.0 is the first stable release. At this point the app provides:

- a tray-only Windows experience with no main window
- active and inactive tray icons, including a pressed visual state while active
- presets for `15 min`, `30 min`, `1 h`, `2 h`, and `Infinite`
- automatic shutdown when a timed session expires
- a single toast notification when a timed session ends
- double-click on the tray icon to toggle infinite mode
- persistent language, logging, and keep-awake method preferences
- persistent restore of infinite mode across launches
- configurable keep-awake methods: `Smart`, `Windows API`, `F15`, and `Shift`
- runtime localization for `pt-BR`, `en`, and `es`
- rotating log files and support actions from the tray menu
- a per-user Windows installer built with PyInstaller and Inno Setup

## Installation

Download the latest installer from the GitHub Releases page and run it on Windows.

Installer behavior:

- installs to `%LocalAppData%\Programs\Trayffeine`
- always creates a Start Menu shortcut for the current user
- offers to launch Trayffeine after installation
- closes a running `Trayffeine.exe` during install or uninstall when needed

Notes:

- the installer is unsigned, so Windows and SmartScreen warnings are expected
- this is normal for the current release and does not indicate malware by itself
- code signing is not part of the repository yet, so plan for that warning during installation
- the Start Menu shortcut is created in the current-user Start Menu, not in `ProgramData`
- searching for `Trayffeine` from the Windows Start menu should find the app normally

## How It Works

Trayffeine keeps the machine awake only while a session is active.

Session modes:

- `Infinite`: stays active until you stop it manually
- timed presets: stop automatically when time runs out

While active:

- the tray icon switches to the active state
- the tooltip shows elapsed and remaining time
- the menu keeps stable summary rows and direct actions

When a timed session ends:

- the app returns to inactive mode
- the keep-awake backend is stopped
- the tray icon returns to the inactive state
- a notification is shown once

Double-click behavior:

- if Trayffeine is inactive, double-click enables infinite mode
- if Trayffeine is already active, double-click turns the session off

## Tray Menu

The tray menu is organized into stable sections:

- status rows
  - `Trayffeine v1.0.0`
  - a stable summary such as `Inactive`, `Active until 14:32`, or `Infinite mode active`
- primary actions
  - `Infinite mode`
  - `Activate for >`
  - `Stop`
- `Preferences >`
  - `Keep-awake method >`
  - `Language >`
- `Support >`
  - `How it works`
  - `Detailed logging`
  - `Open Logs Folder`
  - `Clear Logs`
- `Quit`

The Windows tray menu is a native popup, so its contents do not live-refresh while it stays open. Trayffeine therefore keeps the menu focused on stable summaries and uses the tooltip for the live counter.

## Keep-Awake Methods

Trayffeine supports four methods:

- `Smart`
  - tries `Windows API`
  - if that fails technically, falls back to `F15`
  - if `F15` fails technically, falls back to `Shift`
- `Windows API`
  - uses `SetThreadExecutionState` while the session is active
- `F15`
  - simulates `F15` periodically
- `Shift`
  - simulates `Shift` periodically

Notes:

- `Smart` fallback is technical only; it does not try to prove that Windows or Teams stayed active
- if your main goal is preventing sleep/display idle, `Windows API` is the strongest option
- if your main goal is presence-style activity in apps, `F15` may work better depending on the environment

## Preferences and Persistence

Trayffeine persists settings in `%LOCALAPPDATA%\Trayffeine\settings.json`.

Persisted preferences:

- language selection
- detailed logging preference
- keep-awake method
- whether infinite mode should be restored on next launch

Startup behavior:

- timed sessions never resume after a restart
- infinite mode can resume if it was active when the app last saved state

First launch defaults, when no settings file exists:

- infinite mode restored immediately
- detailed logging enabled
- keep-awake method set to `Smart`
- language set to `Auto`

## Localization

Supported runtime locales:

- `en`
- `pt-BR`
- `es`

Localization behavior:

- English is the source and fallback language in code
- the app detects the system locale at startup
- `Auto` follows the system locale
- explicit language selection persists across launches

## Logging and Support

Runtime logs live in `%LOCALAPPDATA%\Trayffeine\logs\trayffeine.log`.

Logging behavior:

- default level is `WARNING`
- detailed logging maps to `INFO`
- log files rotate automatically at `256 KB` with `3` backups
- high-frequency internal tray events are intentionally not logged at `INFO`

Detailed logging captures useful actions such as:

- app start and exit
- preset selection
- infinite mode toggles
- language changes
- keep-awake method changes
- timer expiration
- opening the logs folder
- clearing logs

Support actions:

- `How it works` opens a short help dialog
- `Detailed logging` enables or disables persistent `INFO` logging
- `Open Logs Folder` opens the logs directory
- `Clear Logs` asks for confirmation, removes the current log and rotated backups, and recreates a fresh current log file

Crash behavior:

- unexpected exceptions are logged
- the app shows a small Windows error dialog pointing to the logs folder

Environment override:

- `TRAYFFEINE_LOG_LEVEL` takes precedence over the persisted detailed logging preference for that process

## Limitations

- Trayffeine is Windows-only at runtime
- the installer is still unsigned
- SmartScreen reputation is not solved in this repository
- the app does not bypass `Win + L`, corporate lock policies, or other enforced security controls
- Teams or similar presence indicators are not guaranteed, because they do not depend only on Windows idle state
- tray behavior is partially unit-tested, but final confidence for UI behavior still comes from real Windows validation

## Project Layout

- `src/trayffeine/app.py`: bootstrap, settings load, single-instance guard, crash boundary
- `src/trayffeine/tray.py`: tray icon, menu, support actions, notifications
- `src/trayffeine/service.py`: background worker, timer expiration, keep-awake cadence
- `src/trayffeine/session.py`: session state and preset timing
- `src/trayffeine/presenter.py`: tooltip, summaries, and notification text assembly
- `src/trayffeine/i18n.py`: runtime localization
- `src/trayffeine/settings.py`: persisted settings model and JSON storage
- `src/trayffeine/app_logging.py`: rotating file logging and cleanup helpers
- `src/trayffeine/keepawake.py`: stable keep-awake method ids
- `src/trayffeine/win32_tray.py`: Windows-specific tray wrapper for double-click handling
- `src/trayffeine/windows.py`: Windows keep-awake backends, dialogs, mutex, shell helpers
- `packaging/windows/`: PyInstaller spec, build script, Inno Setup installer script
- `tests/`: unit and smoke-style tests
- [CHANGELOG.md](/home/rodrigoantonioli/trayffeine/CHANGELOG.md): project history and milestone summary

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

Run the app from a real Windows path when you need interactive tray validation:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .[dev,build]
python scripts\generate_assets.py
python -m trayffeine
```

## Packaging and Releases

The release workflow builds:

1. a PyInstaller `onedir` bundle
2. an Inno Setup installer `.exe`

Manual Windows packaging:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .[build]
python scripts\generate_assets.py
powershell -ExecutionPolicy Bypass -File packaging\windows\build.ps1 -Version 1.0.0 -Clean
```

GitHub Actions:

- `CI` runs on pushes to `main` and on pull requests
- `Release` runs only on tags matching `v*`
- tags matching `v*-beta*` publish prereleases
- stable tags such as `v1.0.0` publish normal releases

## Validation

Expected local validation:

```bash
. .venv/bin/activate
ruff check .
pytest
```

## Support

When reporting a bug, include:

- the exact Trayffeine version
- your Windows version
- steps to reproduce
- the contents of `%LOCALAPPDATA%\Trayffeine\logs\trayffeine.log`

## License

Trayffeine is available under the [MIT License](/home/rodrigoantonioli/trayffeine/LICENSE).
