from __future__ import annotations

from typing import Literal

KeepAwakeMethod = Literal["smart", "execution-state", "f15", "shift"]

DEFAULT_KEEPAWAKE_METHOD: KeepAwakeMethod = "smart"
SUPPORTED_KEEPAWAKE_METHODS: tuple[KeepAwakeMethod, ...] = (
    "smart",
    "execution-state",
    "f15",
    "shift",
)


def coerce_keepawake_method(value: object) -> KeepAwakeMethod:
    if isinstance(value, str) and value in SUPPORTED_KEEPAWAKE_METHODS:
        return value
    return DEFAULT_KEEPAWAKE_METHOD
