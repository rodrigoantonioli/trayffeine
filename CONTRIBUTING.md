# Contributing

Trayffeine can be developed from Windows or WSL, but the real product is a
Windows tray app. Keep that split in mind when changing runtime behavior,
packaging, or tray UX.

## Local Setup

For WSL or Linux-style shells:

```bash
python3.13 -m venv .venv
. .venv/bin/activate
python -m pip install -e .[dev]
python scripts/generate_assets.py
```

For Windows PowerShell and packaging work:

```powershell
py -3.13 -m venv .venv
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

On Windows PowerShell, use `.venv\Scripts\Activate.ps1` before running the same
`ruff check .` and `pytest` commands.

These checks do not prove real tray behavior on Windows. If you touch
`pystray`, dialogs, packaging, notifications, or startup integration, do a real
Windows run as the final confidence step.

## Development Notes

- Keep user-facing runtime text in `i18n.py` and `presenter.py`, not in `tray.py` or `app.py`.
- Preserve stable preset keys: `15m`, `30m`, `1h`, `2h`, `infinite`.
- Preserve stable keep-awake method ids: `smart`, `execution-state`, `f15`, `shift`.
- Keep backend lifecycle on the worker thread.
- Timed sessions must never restore after restart.
- `Start with Windows` is per-user. The EXE/Inno Setup path uses the current-user Windows `Run` key;
  the MSIX path uses the declared Windows startup task when package identity is present.
- `Presence compatibility` is a separate persisted preference, not a keep-awake method id.
- When presence compatibility is enabled, the saved normal method remains unchanged and the effective backend is `f15`.
- Do not promise Teams or app-presence status. Document this as best effort and keep the stronger sleep-prevention language tied to `Windows API`.
- Keep diagnostics stable and support-oriented. The clipboard payload should remain plain English key-value text so it is easy to paste into issues.
- Keep diagnostic paths profile-neutral. Known user-profile prefixes must be rendered as
  `%LOCALAPPDATA%` or `%USERPROFILE%` before the text is copied.

## Documentation Notes

When changing user-facing behavior, update public and maintainer docs together:

- `README.md` for install, usage, limitations, and support behavior
- `CHANGELOG.md` for release-facing highlights
- `docs/ROADMAP.md` when a planned bucket moves or a backlog item is delivered
- `AGENTS.md` when future coding agents need the behavior or architecture rule
- `docs/msix.md` when changing the MSIX package or Store-submission preparation

For tray or support features, include the real Windows validation caveat unless the behavior was actually tested in a real tray session.

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
- `Release` accepts only three-component stable tags such as `v1.2.0` and beta forms such as
  `v1.2.0-beta1`, `v1.2.0-beta.1`, or `v1.2.0-beta-1`
- stable tags publish regular releases
- validated beta tags publish prereleases and skip WinGet submission
- `MSIX Preview Build` creates an unsigned preflight artifact only; it is isolated from tag releases

Release security requirements:

- keep GitHub Actions pinned to reviewed full commit SHAs
- install artifact-build dependencies from `requirements-windows-build.lock` or
  `requirements-msix-build.lock` with `--require-hashes`
- keep the Inno Setup and WingetCreate version, digest, and signer checks intact
- pass Git refs into PowerShell through environment variables, never by interpolating an Actions
  expression directly into script source
- keep artifact construction in a read-only job and credentialed publication behind the protected
  `release` GitHub Environment

To intentionally refresh the build locks on Windows with Python 3.13:

```powershell
python -m pip install pip==25.3 pip-tools==7.5.2
python -m piptools compile pyproject.toml --extra build --generate-hashes --strip-extras --allow-unsafe --output-file requirements-windows-build.lock
python -m piptools compile pyproject.toml --extra build --extra msix --generate-hashes --strip-extras --allow-unsafe --output-file requirements-msix-build.lock
```

Review every resolved version and hash change before committing regenerated locks.
