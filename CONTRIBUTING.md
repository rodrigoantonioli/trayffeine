# Contributing

Trayffeine is developed in WSL, but the real product is a Windows tray app.
Keep that split in mind when changing runtime behavior, packaging, or tray UX.

## Local Setup

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e .[dev]
python scripts/generate_assets.py
```

For packaging work on Windows:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .[dev,build]
python scripts\generate_assets.py
```

## Expected Validation

Before considering a change complete, run:

```bash
. .venv/bin/activate
ruff check .
pytest
```

These checks do not prove real tray behavior on Windows. If you touch
`pystray`, dialogs, packaging, notifications, or startup integration, do a real
Windows run as the final confidence step.

## Development Notes

- Keep user-facing runtime text in `i18n.py` and `presenter.py`, not in `tray.py` or `app.py`.
- Preserve stable preset keys: `15m`, `30m`, `1h`, `2h`, `infinite`.
- Preserve stable keep-awake method ids: `smart`, `execution-state`, `f15`, `shift`.
- Keep backend lifecycle on the worker thread.
- Timed sessions must never restore after restart.
- `Start with Windows` is per-user and uses the current-user Windows `Run` key.

## Versioning And Releases

When bumping the version, update all runtime and packaging copies together:

- `pyproject.toml`
- `src/trayffeine/__init__.py`
- `packaging/windows/build.ps1`
- `packaging/windows/Trayffeine.iss`
- `packaging/winget/metadata.json`

Release automation:

- `CI` runs on pushes to `main` and on pull requests
- `Preview Build` runs on pull requests and `workflow_dispatch`, uploading a Windows installer artifact for review builds
- `Release` runs on tags matching `v*`
- stable tags publish regular releases
- `v*-beta*` tags publish prereleases and skip WinGet submission
