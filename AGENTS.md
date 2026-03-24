# AGENTS.md

This file is for coding agents working in this repository. It explains the current architecture, operational constraints, and the expected workflow so another AI can continue work without rediscovering the project.

## Product Summary

Trayffeine is a small Windows system tray application that keeps the machine awake by simulating `F15` every 59 seconds while a session is active.

Primary product behavior:

- no main window
- tray icon with active/inactive states and a pressed-looking active variant
- presets: `15m`, `30m`, `1h`, `2h`, `infinite`
- tray menu shows app name/version plus live elapsed and remaining status rows
- timer expiration returns the app to inactive mode
- one notification when a timed session ends
- single-instance guard on Windows
- runtime localization for `pt-BR`, `en`, and `es`
- persistent language selection
- infinite mode can be restored on relaunch, but timed sessions always start inactive
- double-click on the tray icon toggles infinite mode

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
  - acquires the Windows single-instance mutex
  - detects the system locale
  - loads persisted settings and wires the service to the tray controller

- `src/trayffeine/service.py`
  - background worker loop
  - owns keep-awake scheduling, timer expiration, and live UI refresh cadence
  - state changes are surfaced through callbacks

- `src/trayffeine/session.py`
  - pure session state
  - stable preset keys and durations only
  - no localized labels should live here

- `src/trayffeine/presenter.py`
  - presentation-only logic
  - owns tooltip text, menu labels, timer-finished notification payload, and language menu entries
  - this is the right place for text assembly, not `service.py` or `session.py`

- `src/trayffeine/i18n.py`
  - locale detection and normalization
  - translation catalogs
  - language selection model (`auto` vs explicit locale)
  - English is the fallback/source language

- `src/trayffeine/tray.py`
  - pystray integration
  - menu rebuilding
  - persistent language selection
  - double-click toggle handling
  - icon refresh and notification dispatch

- `src/trayffeine/settings.py`
  - persisted settings storage
  - stores language selection and infinite-mode restore flag only

- `src/trayffeine/win32_tray.py`
  - Windows-specific tray icon wrapper
  - intercepts tray icon double-click without changing right-click menu behavior

- `src/trayffeine/windows.py`
  - Windows-specific backend only
  - `SendInput` for `F15`
  - named mutex handling

- `packaging/windows/`
  - `trayffeine.spec`: PyInstaller bundle definition
  - `build.ps1`: manual Windows packaging entrypoint
  - `Trayffeine.iss`: Inno Setup installer script

## Current Architecture Rules

- Keep state and presentation separate.
  - `session.py` should contain stable keys and time math.
  - localized strings belong in `i18n.py` and `presenter.py`.

- Do not hardcode user-facing strings in `tray.py` or `app.py` if they are part of the runtime UI.
  - new tray labels, tooltip text, and notifications should go through the translator.

- Preserve stable preset keys.
  - `15m`, `30m`, `1h`, `2h`, `infinite`
  - these keys are internal contracts and should not be translated

- English is the default fallback language.
  - if locale resolution fails or a translation key is missing, the code should still produce English text

- Manual language selection persists across launches.
  - `Auto` still follows the system locale
  - timed sessions still start inactive on relaunch

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
- add or update presenter tests
- avoid leaking localized text into state or backend code

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
- tray controller smoke construction
- Windows tray double-click wrapper routing

What tests do not guarantee:

- actual interactive tray behavior on Windows
- Windows notifications rendering
- final PyInstaller runtime behavior on a user desktop

For changes touching `pystray`, the final confidence step is a manual Windows run.

## Release and Versioning

- Project version is currently `0.3.4`.
- Runtime version lives in:
  - `pyproject.toml`
  - `src/trayffeine/__init__.py`
  - `packaging/windows/build.ps1`
  - `packaging/windows/Trayffeine.iss`

GitHub workflows:

- `CI` runs on push to `main` and on pull requests.
- `Release` runs only on tags `v*`.
- Windows installers are produced only by the release workflow.

If you change packaging or release behavior, verify that:

- tag pushes do not trigger redundant CI runs
- the Windows workflow still uploads the installer artifact
- the release workflow publishes via `gh` rather than a deprecated JS release action

## Known Constraints

- No signing pipeline is integrated yet.
- SmartScreen reputation is not solved by the current repo state.
- Installer localization is still separate from runtime localization.
- The app is Windows-only at runtime even though development happens in WSL.
- Runtime diagnostics are written to `%LOCALAPPDATA%\Trayffeine\logs\trayffeine.log`.

## Practical Guidance For Future Agents

- If the task is UI text, start in `i18n.py` and `presenter.py`.
- If the task is timing/behavior, start in `service.py` and `session.py`.
- If the task is system tray/menu behavior, start in `tray.py`.
- If the task is packaging or artifact generation, start in `packaging/windows/` and `.github/workflows/`.
- Do not remove the Windows smoke assumptions from the docs unless you have actually validated the behavior on Windows.
