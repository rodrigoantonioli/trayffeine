from __future__ import annotations

from trayffeine.diagnostics import DiagnosticsInfo, build_diagnostics_text


def test_build_diagnostics_text_uses_stable_support_output(monkeypatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\ExampleUser\AppData\Local")
    diagnostics = build_diagnostics_text(
        DiagnosticsInfo(
            version="1.2.0",
            language_selection="manual:pt-BR",
            effective_locale="pt-BR",
            session_state="Inactive",
            configured_keepawake_method="smart",
            effective_keepawake_method="f15",
            presence_compatibility_enabled=True,
            detailed_logging_enabled=True,
            start_with_windows=False,
            settings_path=r"C:\Users\ExampleUser\AppData\Local\Trayffeine\settings.json",
            log_path=(
                r"C:\Users\ExampleUser\AppData\Local\Trayffeine\logs\trayffeine.log"
            ),
        )
    )

    assert diagnostics == (
        "Trayffeine diagnostics\n"
        "Version: 1.2.0\n"
        "Language selection: manual:pt-BR\n"
        "Effective locale: pt-BR\n"
        "Session state: Inactive\n"
        "Configured keep-awake method: smart\n"
        "Effective keep-awake method: f15\n"
        "Presence compatibility: enabled\n"
        "Detailed logging: enabled\n"
        "Start with Windows: disabled\n"
        r"Settings path: %LOCALAPPDATA%\Trayffeine\settings.json"
        "\n"
        r"Log path: %LOCALAPPDATA%\Trayffeine\logs\trayffeine.log"
    )


def test_build_diagnostics_text_does_not_replace_unrelated_prefix(monkeypatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\ExampleUser\AppData\Local")

    diagnostics = build_diagnostics_text(
        DiagnosticsInfo(
            version="1.2.0",
            language_selection="auto",
            effective_locale="en",
            session_state="Inactive",
            configured_keepawake_method="smart",
            effective_keepawake_method=None,
            presence_compatibility_enabled=False,
            detailed_logging_enabled=False,
            start_with_windows=False,
            settings_path=r"D:\Portable\Trayffeine\settings.json",
            log_path=r"D:\Portable\Trayffeine\trayffeine.log",
        )
    )

    assert r"Settings path: D:\Portable\Trayffeine\settings.json" in diagnostics
    assert r"Log path: D:\Portable\Trayffeine\trayffeine.log" in diagnostics
