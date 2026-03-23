from __future__ import annotations

import sys

from trayffeine.app import run_app


def main() -> None:
    if sys.platform != "win32":
        raise SystemExit("Trayffeine only runs on Windows.")
    run_app()


if __name__ == "__main__":
    main()
