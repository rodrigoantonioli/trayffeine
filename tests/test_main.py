from __future__ import annotations

import runpy
from pathlib import Path

import pytest


def test_main_script_runs_without_relative_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    script_path = Path(__file__).resolve().parents[1] / "src" / "trayffeine" / "__main__.py"
    monkeypatch.syspath_prepend(str(script_path.parents[1]))

    with pytest.raises(SystemExit, match="Trayffeine only runs on Windows."):
        runpy.run_path(str(script_path), run_name="__main__")
