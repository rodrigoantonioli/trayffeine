from __future__ import annotations

import locale
import sys
from dataclasses import dataclass
from typing import Literal

LocaleCode = Literal["en", "pt-BR", "es"]

SUPPORTED_LOCALES: tuple[LocaleCode, ...] = ("en", "pt-BR", "es")
FALLBACK_LOCALE: LocaleCode = "en"

Catalog = dict[str, str]

CATALOGS: dict[LocaleCode, Catalog] = {
    "en": {
        "app.name": "Trayffeine",
        "app.crash.title": "Trayffeine",
        "app.crash.body": "Trayffeine hit an unexpected error.\n\nSee logs in:\n{log_dir}",
        "tray.tooltip.active_infinite": "Trayffeine: active for {elapsed} | infinite",
        "tray.tooltip.active_remaining": "Trayffeine: active for {elapsed} | {remaining} left",
        "tray.tooltip.inactive": "Trayffeine: inactive",
        "tray.menu.header": "Trayffeine v{version}",
        "tray.menu.infinite": "Infinite mode",
        "tray.menu.activate_for": "Activate for",
        "tray.menu.stop": "Stop",
        "tray.menu.preferences": "Preferences",
        "tray.menu.support": "Support",
        "tray.menu.keepawake_method": "Keep-awake method",
        "tray.menu.start_with_windows": "Start with Windows",
        "tray.menu.help": "How it works",
        "tray.menu.open_logs": "Open Logs Folder",
        "tray.menu.clear_logs": "Clear Logs",
        "tray.menu.detailed_logging": "Detailed logging",
        "tray.menu.quit": "Quit",
        "tray.menu.language": "Language",
        "tray.menu.language.auto": "Auto",
        "tray.keepawake_method.smart": "Smart",
        "tray.keepawake_method.execution-state": "Windows API",
        "tray.keepawake_method.f15": "F15",
        "tray.keepawake_method.shift": "Shift",
        "tray.logs.clear.title": "Clear Trayffeine logs?",
        "tray.logs.clear.body": (
            "This will remove trayffeine.log and all rotated backups.\n\nContinue?"
        ),
        "tray.help.title": "How Trayffeine works",
        "tray.help.body": (
            "Trayffeine keeps your PC awake while a session is active.\n"
            "\n"
            "Infinite mode stays on until you stop it.\n"
            "Timed presets stop automatically when time runs out.\n"
            "Double-click the tray icon to toggle infinite mode.\n"
            "\n"
            "Methods:\n"
            "- Smart: tries Windows API, then F15, then Shift.\n"
            "- Windows API: uses the native Windows execution state API.\n"
            "- F15: simulates F15 periodically.\n"
            "- Shift: simulates Shift periodically."
        ),
        "tray.summary.inactive": "Inactive",
        "tray.summary.infinite": "Infinite mode active",
        "tray.summary.timed": "Active until {time}",
        "tray.status.elapsed": "Elapsed: {value}",
        "tray.status.remaining": "Remaining: {value}",
        "tray.status.none": "-",
        "tray.status.infinite": "Infinite",
        "tray.notify.timer_finished.title": "Trayffeine",
        "tray.notify.timer_finished.body": "Session ended. Trayffeine returned to inactive mode.",
        "preset.15m": "15 min",
        "preset.30m": "30 min",
        "preset.1h": "1 h",
        "preset.2h": "2 h",
        "preset.infinite": "Infinite",
        "duration.hours_minutes": "{hours}h {minutes:02d}m",
        "duration.minutes_seconds": "{minutes}m {seconds:02d}s",
        "duration.seconds": "{seconds}s",
    },
    "pt-BR": {
        "app.name": "Trayffeine",
        "app.crash.title": "Trayffeine",
        "app.crash.body": (
            "O Trayffeine encontrou um erro inesperado.\n\nVeja os logs em:\n{log_dir}"
        ),
        "tray.tooltip.active_infinite": "Trayffeine: ativo há {elapsed} | infinito",
        "tray.tooltip.active_remaining": "Trayffeine: ativo há {elapsed} | faltam {remaining}",
        "tray.tooltip.inactive": "Trayffeine: inativo",
        "tray.menu.header": "Trayffeine v{version}",
        "tray.menu.infinite": "Modo infinito",
        "tray.menu.activate_for": "Ativar por",
        "tray.menu.stop": "Parar",
        "tray.menu.preferences": "Preferências",
        "tray.menu.support": "Suporte",
        "tray.menu.keepawake_method": "Método para manter acordado",
        "tray.menu.start_with_windows": "Iniciar com o Windows",
        "tray.menu.help": "Como funciona",
        "tray.menu.open_logs": "Abrir pasta de logs",
        "tray.menu.clear_logs": "Limpar logs",
        "tray.menu.detailed_logging": "Logs detalhados",
        "tray.menu.quit": "Sair",
        "tray.menu.language": "Idioma",
        "tray.menu.language.auto": "Auto",
        "tray.keepawake_method.smart": "Inteligente",
        "tray.keepawake_method.execution-state": "Windows API",
        "tray.keepawake_method.f15": "F15",
        "tray.keepawake_method.shift": "Shift",
        "tray.logs.clear.title": "Limpar logs do Trayffeine?",
        "tray.logs.clear.body": (
            "Isso apagará o arquivo trayffeine.log e todos os backups "
            "rotacionados.\n\nDeseja continuar?"
        ),
        "tray.help.title": "Como o Trayffeine funciona",
        "tray.help.body": (
            "O Trayffeine mantém o PC acordado enquanto uma sessão estiver ativa.\n"
            "\n"
            "O modo infinito fica ligado até você parar manualmente.\n"
            "Os presets temporizados desligam automaticamente no fim do tempo.\n"
            "Clique duas vezes no ícone da bandeja para alternar o modo infinito.\n"
            "\n"
            "Métodos:\n"
            "- Inteligente: tenta Windows API, depois F15 e por fim Shift.\n"
            "- Windows API: usa a API nativa de estado de execução do Windows.\n"
            "- F15: simula F15 periodicamente.\n"
            "- Shift: simula Shift periodicamente."
        ),
        "tray.summary.inactive": "Inativo",
        "tray.summary.infinite": "Modo infinito ativo",
        "tray.summary.timed": "Ativo até {time}",
        "tray.status.elapsed": "Tempo ativo: {value}",
        "tray.status.remaining": "Tempo restante: {value}",
        "tray.status.none": "-",
        "tray.status.infinite": "Infinito",
        "tray.notify.timer_finished.title": "Trayffeine",
        "tray.notify.timer_finished.body": "Sessão encerrada. O Trayffeine voltou ao modo inativo.",
        "preset.15m": "15 min",
        "preset.30m": "30 min",
        "preset.1h": "1 h",
        "preset.2h": "2 h",
        "preset.infinite": "Infinito",
        "duration.hours_minutes": "{hours}h {minutes:02d}m",
        "duration.minutes_seconds": "{minutes}m {seconds:02d}s",
        "duration.seconds": "{seconds}s",
    },
    "es": {
        "app.name": "Trayffeine",
        "app.crash.title": "Trayffeine",
        "app.crash.body": (
            "Trayffeine encontró un error inesperado.\n\nConsulta los logs en:\n{log_dir}"
        ),
        "tray.tooltip.active_infinite": "Trayffeine: activo hace {elapsed} | infinito",
        "tray.tooltip.active_remaining": "Trayffeine: activo hace {elapsed} | quedan {remaining}",
        "tray.tooltip.inactive": "Trayffeine: inactivo",
        "tray.menu.header": "Trayffeine v{version}",
        "tray.menu.infinite": "Modo infinito",
        "tray.menu.activate_for": "Activar por",
        "tray.menu.stop": "Detener",
        "tray.menu.preferences": "Preferencias",
        "tray.menu.support": "Soporte",
        "tray.menu.keepawake_method": "Método para mantener activo",
        "tray.menu.start_with_windows": "Iniciar con Windows",
        "tray.menu.help": "Cómo funciona",
        "tray.menu.open_logs": "Abrir carpeta de logs",
        "tray.menu.clear_logs": "Limpiar logs",
        "tray.menu.detailed_logging": "Logs detallados",
        "tray.menu.quit": "Salir",
        "tray.menu.language": "Idioma",
        "tray.menu.language.auto": "Auto",
        "tray.keepawake_method.smart": "Inteligente",
        "tray.keepawake_method.execution-state": "API de Windows",
        "tray.keepawake_method.f15": "F15",
        "tray.keepawake_method.shift": "Shift",
        "tray.logs.clear.title": "¿Limpiar los logs de Trayffeine?",
        "tray.logs.clear.body": (
            "Esto eliminará trayffeine.log y todas las copias rotadas.\n\n¿Deseas continuar?"
        ),
        "tray.help.title": "Cómo funciona Trayffeine",
        "tray.help.body": (
            "Trayffeine mantiene tu PC activo mientras haya una sesión en curso.\n"
            "\n"
            "El modo infinito sigue activo hasta que lo detengas.\n"
            "Los presets temporizados se detienen automáticamente al terminar.\n"
            "Haz doble clic en el icono de la bandeja para alternar el modo infinito.\n"
            "\n"
            "Métodos:\n"
            "- Inteligente: prueba API de Windows, luego F15 y después Shift.\n"
            "- API de Windows: usa la API nativa de estado de ejecución.\n"
            "- F15: simula F15 periódicamente.\n"
            "- Shift: simula Shift periódicamente."
        ),
        "tray.summary.inactive": "Inactivo",
        "tray.summary.infinite": "Modo infinito activo",
        "tray.summary.timed": "Activo hasta {time}",
        "tray.status.elapsed": "Tiempo activo: {value}",
        "tray.status.remaining": "Tiempo restante: {value}",
        "tray.status.none": "-",
        "tray.status.infinite": "Infinito",
        "tray.notify.timer_finished.title": "Trayffeine",
        "tray.notify.timer_finished.body": "La sesión terminó. Trayffeine volvió al modo inactivo.",
        "preset.15m": "15 min",
        "preset.30m": "30 min",
        "preset.1h": "1 h",
        "preset.2h": "2 h",
        "preset.infinite": "Infinito",
        "duration.hours_minutes": "{hours}h {minutes:02d}m",
        "duration.minutes_seconds": "{minutes}m {seconds:02d}s",
        "duration.seconds": "{seconds}s",
    },
}

NATIVE_LANGUAGE_NAMES: dict[LocaleCode, str] = {
    "en": "English",
    "pt-BR": "Português (Brasil)",
    "es": "Español",
}


@dataclass(frozen=True)
class LanguageSelection:
    mode: Literal["auto", "manual"]
    locale: LocaleCode | None = None

    @classmethod
    def auto(cls) -> LanguageSelection:
        return cls(mode="auto")

    @classmethod
    def explicit(cls, locale_code: LocaleCode) -> LanguageSelection:
        return cls(mode="manual", locale=locale_code)


@dataclass(frozen=True)
class LanguageOption:
    key: str
    label: str
    checked: bool


class Translator:
    def __init__(
        self,
        locale_code: LocaleCode,
        fallback_locale: LocaleCode = FALLBACK_LOCALE,
    ) -> None:
        self.locale = locale_code
        self.fallback_locale = fallback_locale

    def t(self, message_id: str, **params: object) -> str:
        message = CATALOGS[self.locale].get(message_id)
        if message is None:
            message = CATALOGS[self.fallback_locale].get(message_id, message_id)
        return message.format(**params)


def resolve_system_locale(raw_locale: str | None) -> LocaleCode:
    if raw_locale is None:
        return FALLBACK_LOCALE

    normalized = raw_locale.replace("_", "-").lower()
    if normalized.startswith("pt"):
        return "pt-BR"
    if normalized.startswith("es"):
        return "es"
    if normalized.startswith("en"):
        return "en"
    return FALLBACK_LOCALE


def detect_system_locale() -> LocaleCode:
    return resolve_system_locale(_raw_system_locale())


def effective_locale(selection: LanguageSelection, system_locale: LocaleCode) -> LocaleCode:
    if selection.mode == "manual" and selection.locale is not None:
        return selection.locale
    return system_locale


def build_language_options(
    selection: LanguageSelection,
    system_locale: LocaleCode,
    translator: Translator,
) -> tuple[LanguageOption, ...]:
    return (
        LanguageOption(
            key="auto",
            label=translator.t("tray.menu.language.auto"),
            checked=selection.mode == "auto",
        ),
        *(
            LanguageOption(
                key=locale_code,
                label=NATIVE_LANGUAGE_NAMES[locale_code],
                checked=selection.mode == "manual" and selection.locale == locale_code,
            )
            for locale_code in SUPPORTED_LOCALES
        ),
    )


def _raw_system_locale() -> str | None:
    if sys.platform == "win32":
        windows_locale = _windows_locale_name()
        if windows_locale is not None:
            return windows_locale

    current_locale = locale.getlocale()[0]
    if current_locale is not None:
        return current_locale

    return locale.getdefaultlocale()[0]


def _windows_locale_name() -> str | None:
    if sys.platform != "win32":
        return None

    import ctypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    buffer = ctypes.create_unicode_buffer(85)
    result = kernel32.GetUserDefaultLocaleName(buffer, len(buffer))
    if result <= 0:
        return None
    return buffer.value
