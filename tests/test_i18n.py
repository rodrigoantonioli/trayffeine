from __future__ import annotations

import pytest

from trayffeine.i18n import (
    LanguageSelection,
    Translator,
    build_language_options,
    effective_locale,
    resolve_system_locale,
)


@pytest.mark.parametrize(
    ("raw_locale", "expected"),
    [
        ("pt-BR", "pt-BR"),
        ("pt_PT", "pt-BR"),
        ("en-US", "en"),
        ("en_GB", "en"),
        ("es-MX", "es"),
        ("es_ES", "es"),
        ("fr-FR", "en"),
        (None, "en"),
    ],
)
def test_resolve_system_locale_maps_variants(raw_locale: str | None, expected: str) -> None:
    assert resolve_system_locale(raw_locale) == expected


def test_effective_locale_uses_system_locale_in_auto_mode() -> None:
    assert effective_locale(LanguageSelection.auto(), "pt-BR") == "pt-BR"


def test_effective_locale_uses_manual_override() -> None:
    assert effective_locale(LanguageSelection.explicit("es"), "pt-BR") == "es"


def test_build_language_options_uses_native_language_names() -> None:
    options = build_language_options(LanguageSelection.explicit("pt-BR"), "en", Translator("es"))

    assert [option.label for option in options] == [
        "Auto",
        "English",
        "Português (Brasil)",
        "Español",
    ]
    assert next(option for option in options if option.key == "pt-BR").checked is True
