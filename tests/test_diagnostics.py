from __future__ import annotations

from trayffeine.diagnostics import DiagnosticsInfo, build_diagnostics_text


def test_build_diagnostics_text_uses_stable_support_output() -> None:
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
            settings_path=r"C:\Users\me\AppData\Local\Trayffeine\settings.json",
            log_path=r"C:\Users\me\AppData\Local\Trayffeine\logs\trayffeine.log",
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
        r"Settings path: C:\Users\me\AppData\Local\Trayffeine\settings.json"
        "\n"
        r"Log path: C:\Users\me\AppData\Local\Trayffeine\logs\trayffeine.log"
    )
