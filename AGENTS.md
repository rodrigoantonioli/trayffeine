# AGENTS.md

This file is for coding agents working in this repository. It explains the current architecture, operational constraints, and expected workflow so another agent can continue work without rediscovering the project.

## Product Summary

Trayffeine is a small Windows system tray application that keeps the machine awake while a session is active.

Primary product behavior:

- no main window
- tray icon with active/inactive states and a pressed-looking active variant
- presets: `15m`, `30m`, `1h`, `2h`, `infinite`
- tray menu shows stable summary rows while the live counter stays in the tooltip
- timer expiration returns the app to inactive mode
- one notification when a timed session ends
- single-instance guard on Windows
- runtime localization for `pt-BR`, `en`, and `es`
- persistent language selection
- persistent keep-awake method selection
- supported keep-awake methods: `smart`, `execution-state`, `f15`, `shift`
- infinite mode can be restored on relaunch, but timed sessions always start inactive
- double-click on the tray icon toggles infinite mode
- grouped tray menu with `Preferences` and `Support`
- persistent detailed logging toggle
- first launch defaults to infinite mode with detailed logging enabled until a settings file exists
- support actions to show help, open logs, or clear logs
- unhandled exceptions are logged and surfaced in a Windows error dialog

## Environment Model

- Development and editing happen in WSL.
- Official Windows artifacts are built in GitHub Actions on `windows-latest`.
- Do not treat WSL as a reliable place to produce final `.exe` files for Windows distribution.
- Python target is `3.12`.

Recommended local loop:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e .[dev]
python scripts/generate_assets.py
ruff check .
pytest
```

For real tray validation, run the app from Windows in a real Windows path.

## Repository Map

- `src/trayffeine/app.py`
  - runtime bootstrap
  - loads persisted settings before final log-level selection
  - applies env-override vs persisted detailed-logging preference
  - acquires the Windows single-instance mutex
  - wires service, tray callbacks, keep-awake method changes, help/support actions, and crash boundary

- `src/trayffeine/app_logging.py`
  - rotating file logger configuration
  - log-level resolution
  - env override detection
  - runtime log-level switching without duplicating handlers
  - log-file cleanup helpers

- `src/trayffeine/service.py`
  - background worker loop
  - owns keep-awake scheduling, backend lifecycle, timer expiration, and live UI refresh cadence
  - backend lifecycle and keep-awake pulses must stay on the worker thread so `SetThreadExecutionState` is started, refreshed, and cleared on the same thread
  - state changes are surfaced through callbacks

- `src/trayffeine/keepawake.py`
  - stable keep-awake method ids
  - coercion helper for persisted settings

- `src/trayffeine/session.py`
  - pure session state
  - stable preset keys and durations only
  - no localized labels should live here

- `src/trayffeine/presenter.py`
  - presentation-only logic
  - owns tooltip text, stable menu summary text, timer-finished notification payload, and language menu entries
  - this is the right place for text assembly, not `service.py` or `session.py`

- `src/trayffeine/i18n.py`
  - locale detection and normalization
  - translation catalogs
  - language selection model (`auto` vs explicit locale)
  - English is the fallback/source language

- `src/trayffeine/tray.py`
  - pystray integration
  - grouped menu rebuilding
  - persistent language and detailed-logging preferences
  - double-click toggle handling
  - icon refresh and notification dispatch
  - support actions for help, detailed logging, opening logs, and clearing logs

- `src/trayffeine/settings.py`
  - persisted settings storage
  - stores language selection, infinite-mode restore flag, detailed-logging preference, and keep-awake method
  - missing settings file is treated as first launch and defaults to infinite restore plus detailed logging enabled

- `src/trayffeine/win32_tray.py`
  - Windows-specific tray icon wrapper
  - intercepts tray icon double-click without changing right-click menu behavior

- `src/trayffeine/windows.py`
  - Windows-specific backend only
  - keyboard backends for `F15` and `Shift`
  - `SetThreadExecutionState` backend
  - smart fallback backend: `execution-state -> f15 -> shift`
  - named mutex handling
  - message-box helper
  - confirmation-dialog helper
  - shell-open helper for logs

- `packaging/windows/`
  - `trayffeine.spec`: PyInstaller bundle definition
  - `build.ps1`: manual Windows packaging entrypoint
  - `Trayffeine.iss`: Inno Setup installer script

## Current Architecture Rules

- Keep state and presentation separate.
  - `session.py` should contain stable keys and time math.
  - localized strings belong in `i18n.py` and `presenter.py`.

- Do not hardcode user-facing runtime text in `tray.py` or `app.py`.
  - tray labels, confirmation text, tooltip text, and notifications should go through the translator.

- Preserve stable preset keys.
  - `15m`, `30m`, `1h`, `2h`, `infinite`
  - these keys are internal contracts and should not be translated

- English is the default fallback language.
  - if locale resolution fails or a translation key is missing, the code should still produce English text

- Manual language selection persists across launches.
  - `Auto` still follows the system locale
  - timed sessions still start inactive on relaunch

- Keep-awake method selection persists across launches.
  - default is `smart`
  - restored infinite mode uses the persisted method
  - smart fallback is technical only, not semantic detection of idle prevention

- On first launch with no settings file:
  - `restore_infinite` defaults to `true`
  - `detailed_logging_enabled` defaults to `true`
  - `keepawake_method` defaults to `smart`
  - `language_selection` defaults to `auto`

- Detailed logging persists across launches unless the process is locked by `TRAYFFEINE_LOG_LEVEL`.
  - env override wins for that process
  - when env override is present, the tray toggle should be disabled to avoid lying about the effective level

## Localization Model

Supported runtime locales:

- `en`
- `pt-BR`
- `es`

Locale behavior:

- startup resolves the system locale to the nearest supported locale
- unsupported locales fall back to `en`
- the tray menu exposes:
  - `Auto`
  - `Português (Brasil)`
  - `English`
  - `Español`
- explicit selection is persisted between launches

When extending localization:

- add new message ids to the catalogs in `i18n.py`
- keep ids stable and presentation-oriented
- add or update presenter and tray tests
- avoid leaking localized text into state or backend code
- keep correct accents and natural spelling in every language

## Logging Model

Current runtime log file:

- `%LOCALAPPDATA%\Trayffeine\logs\trayffeine.log`

Rotation defaults:

- `256 KB`
- `3` backups

Logging policy:

- default runtime level is `WARNING`
- detailed logging maps to `INFO`
- meaningful user and lifecycle actions may be logged at `INFO`
- high-frequency internal events must not be logged at `INFO`
  - do not log every tick
  - do not log every menu rebuild
  - do not log every tray refresh callback

Useful `INFO` events:

- app start and exit
- preset selection
- infinite enable/disable
- timer expiration
- language changes
- opening logs folder
- enabling or disabling detailed logging
- clearing logs

When changing logging:

- do not duplicate root handlers
- keep `TRAYFFEINE_LOG_LEVEL` precedence intact
- if logs are cleared, recreate a fresh current log file immediately

## Tray UX Notes

- The Windows tray menu is a native popup built through `pystray` and `TrackPopupMenuEx`.
- Once that popup is open, its contents are effectively static until it closes.
- Because of that platform limitation, volatile values such as per-second timers should live in the tray tooltip, not in the open menu.
- The menu itself should prefer stable summary rows and grouped actions.

Current menu layout:

- header row
- stable summary row
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

## Testing Expectations

Before considering work complete, run:

```bash
. .venv/bin/activate
ruff check .
pytest
```

Current tests cover:

- locale resolution and language selection helpers
- settings persistence
- presenter output across locales
- session timing behavior
- `__main__` packaging regression
- tray controller smoke construction and grouped menu wiring
- runtime log configuration and log cleanup helpers
- Windows tray double-click wrapper routing

What tests do not guarantee:

- actual interactive tray behavior on Windows
- Windows notifications rendering
- final PyInstaller runtime behavior on a user desktop

For changes touching `pystray`, the final confidence step is a manual Windows run.

## Release and Versioning

- Project version is currently `0.7.2`.
- Runtime version lives in:
  - `pyproject.toml`
  - `src/trayffeine/__init__.py`
  - `packaging/windows/build.ps1`
  - `packaging/windows/Trayffeine.iss`

GitHub workflows:

- `CI` runs on push to `main` and on pull requests.
- `Release` runs only on tags `v*`.
- Windows installers are produced only by the release workflow.
- stable tags such as `v0.7.2` publish normal releases
- tags matching `v*-beta*` publish GitHub prereleases

Current hotfix notes:

- `0.7.2` moves the support help dialog off the tray menu callback flow so `OK` and the window close button behave normally.
- The tray test suite explicitly covers the inactive icon/title path after a timed session expires.

If you change packaging or release behavior, verify that:

- tag pushes do not trigger redundant CI runs
- the Windows workflow still uploads the installer artifact
- the release workflow still publishes via `gh`

## Known Constraints

- No signing pipeline is integrated yet.
- SmartScreen reputation is not solved by the current repo state.
- Installer localization is still separate from runtime localization.
- The app is Windows-only at runtime even though development happens in WSL.
- Runtime diagnostics are written to `%LOCALAPPDATA%\Trayffeine\logs\trayffeine.log`.

## Practical Guidance For Future Agents

- If the task is UI text, start in `i18n.py` and `presenter.py`.
- If the task is timing/behavior, start in `service.py` and `session.py`.
- If the task is tray/menu behavior, start in `tray.py`.
- If the task is logging behavior, start in `app_logging.py` and `app.py`.
- If the task is packaging or artifact generation, start in `packaging/windows/` and `.github/workflows/`.
- Do not remove the Windows smoke assumptions from the docs unless you have actually validated the behavior on Windows.
