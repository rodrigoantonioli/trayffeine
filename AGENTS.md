# AGENTS.md

This file is for coding agents working in this repository. It explains the current product behavior, repository structure, architecture rules, and release workflow so another agent can continue work without rediscovering context.

## Product Summary

Trayffeine is a Windows system tray application that keeps the machine awake while a session is active.

Current product behavior:

- no main window
- active and inactive tray icons, including a pressed-looking active state
- presets: `15m`, `30m`, `1h`, `2h`, `infinite`
- timed sessions automatically return the app to inactive mode
- one notification when a timed session ends
- tray tooltip shows live elapsed and remaining time
- double-click on the tray icon toggles infinite mode
- single-instance guard on Windows
- runtime localization for `pt-BR`, `en`, and `es`
- persistent language selection
- persistent keep-awake method selection
- supported keep-awake methods: `smart`, `execution-state`, `f15`, `shift`
- persistent detailed logging toggle
- support actions for help, opening logs, and clearing logs
- persistent restore of infinite mode, while timed sessions always restart inactive
- first launch defaults to infinite restore plus detailed logging enabled
- per-user installer that always creates a Start Menu shortcut

## Environment Model

- Development and editing happen in WSL.
- Official Windows artifacts are built in GitHub Actions on `windows-latest`.
- Do not treat WSL as the place to produce final Windows distributables for users.
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

For real tray validation, run the app from a real Windows path.

## Repository Map

- `src/trayffeine/app.py`
  - runtime bootstrap
  - settings load
  - effective log-level selection
  - single-instance guard
  - crash boundary
  - tray/service wiring

- `src/trayffeine/app_logging.py`
  - rotating log configuration
  - env override handling
  - runtime log-level switching
  - log cleanup helpers

- `src/trayffeine/service.py`
  - background worker loop
  - keep-awake cadence
  - backend lifecycle
  - timer expiration
  - callback dispatch for state changes, timer completion, and tooltip ticks

- `src/trayffeine/session.py`
  - pure session state and timing math
  - stable preset keys only

- `src/trayffeine/keepawake.py`
  - stable keep-awake method ids
  - coercion helper for persisted settings

- `src/trayffeine/presenter.py`
  - tray summaries
  - tooltip text
  - notification payloads
  - presentation-only text assembly

- `src/trayffeine/i18n.py`
  - locale detection and normalization
  - runtime catalogs
  - language selection model

- `src/trayffeine/tray.py`
  - pystray integration
  - grouped menu construction
  - support actions
  - tooltip refresh and icon/menu refresh behavior
  - notification dispatch

- `src/trayffeine/settings.py`
  - JSON settings persistence
  - stores language, infinite restore, detailed logging, and keep-awake method
  - missing settings file is treated as first launch

- `src/trayffeine/win32_tray.py`
  - Windows-specific tray wrapper
  - intercepts tray double-click without breaking right-click behavior

- `src/trayffeine/windows.py`
  - Windows keep-awake backends
  - `SendInput` keyboard backends for `F15` and `Shift`
  - `SetThreadExecutionState` backend
  - smart fallback backend
  - mutex
  - dialogs
  - shell-open helper

- `packaging/windows/`
  - `trayffeine.spec`: PyInstaller bundle definition
  - `build.ps1`: manual packaging entrypoint
  - `Trayffeine.iss`: Inno Setup installer script

- `tests/`
  - unit and smoke-style coverage for session, presenter, i18n, logging, tray wiring, service behavior, and Windows integration helpers

- `CHANGELOG.md`
  - milestone summary from the start of the project through `1.0.0`

## Architecture Rules

- Keep state and presentation separate.
  - `session.py` owns keys and time math.
  - localized text belongs in `i18n.py` and `presenter.py`.

- Do not hardcode user-facing runtime text in `tray.py` or `app.py`.
  - tray labels, dialogs, tooltips, and notifications should go through the translator.

- Preserve stable preset keys.
  - `15m`, `30m`, `1h`, `2h`, `infinite`
  - these are internal contracts and should not be translated

- Preserve stable keep-awake method ids.
  - `smart`, `execution-state`, `f15`, `shift`

- Keep backend lifecycle on the worker thread.
  - `SetThreadExecutionState` must be started, refreshed, and cleared on the same worker thread

- Prefer stable tray menu summaries.
  - the menu should not depend on live-refresh while open
  - live counters belong in the tooltip, not in the open menu
  - per-second tick refreshes should update only what is necessary

- English is the fallback language.
  - missing or unsupported locale resolution should still produce English text

- Keep correct accents and natural spelling in localized text.

## Persistence Model

Stored settings currently include:

- language selection
- `restore_infinite`
- `detailed_logging_enabled`
- `keepawake_method`

Current first-run defaults:

- `restore_infinite = true`
- `detailed_logging_enabled = true`
- `keepawake_method = smart`
- `language_selection = auto`

Timed sessions must never resume after restart.

## Logging Model

Current log file:

- `%LOCALAPPDATA%\Trayffeine\logs\trayffeine.log`

Rotation defaults:

- `256 KB`
- `3` backups

Logging policy:

- default runtime level is `WARNING`
- detailed logging maps to `INFO`
- meaningful lifecycle and user actions may be logged at `INFO`
- high-frequency internal events must not be logged at `INFO`

Examples of useful `INFO` events:

- app start and exit
- preset selection
- infinite mode enable or disable
- language change
- keep-awake method change
- timer expiration
- opening logs folder
- toggling detailed logging
- clearing logs

When changing logging:

- do not duplicate root handlers
- keep `TRAYFFEINE_LOG_LEVEL` precedence intact
- if logs are cleared, recreate the current file immediately

## Installer and Packaging Rules

- Installation is per-user under `%LocalAppData%\Programs\Trayffeine`.
- The installer always creates a current-user Start Menu shortcut.
- The installer is unsigned.
- Installer changes belong in `packaging/windows/Trayffeine.iss`.
- Keep the release workflow Windows-only for artifact generation.

## Testing Expectations

Before considering work complete, run:

```bash
. .venv/bin/activate
ruff check .
pytest
```

What tests do not guarantee:

- real interactive tray behavior on Windows
- actual Windows notification rendering
- full packaged runtime behavior on an end-user desktop

For changes touching `pystray`, dialogs, or installer behavior, the final confidence step is still a real Windows run.

## Release and Versioning

- Project version is currently `1.0.0`.
- Runtime version lives in:
  - `pyproject.toml`
  - `src/trayffeine/__init__.py`
  - `packaging/windows/build.ps1`
  - `packaging/windows/Trayffeine.iss`

GitHub workflows:

- `CI` runs on push to `main` and on pull requests
- `Release` runs only on tags `v*`
- stable tags such as `v1.0.0` publish normal releases
- tags matching `v*-beta*` publish GitHub prereleases

If changing packaging or release behavior, verify:

- tag pushes do not trigger redundant CI runs
- the Windows workflow still uploads the installer artifact
- the release workflow still publishes through `gh`

## Known Constraints

- No signing pipeline is integrated yet.
- SmartScreen reputation is not solved in the current repo state.
- Installer localization is still separate from runtime localization.
- The app is Windows-only at runtime even though development happens in WSL.
- Teams or similar presence behavior is not guaranteed by the keep-awake methods.

## Practical Guidance For Future Agents

- If the task is UI text, start in `i18n.py` and `presenter.py`.
- If the task is timing or keep-awake behavior, start in `service.py`, `session.py`, and `windows.py`.
- If the task is tray/menu behavior, start in `tray.py` and `win32_tray.py`.
- If the task is logging behavior, start in `app_logging.py` and `app.py`.
- If the task is packaging or release behavior, start in `packaging/windows/` and `.github/workflows/`.
- Do not remove the Windows validation caveats from the docs unless the behavior has actually been tested on Windows.
