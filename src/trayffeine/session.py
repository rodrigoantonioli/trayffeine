from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Self

DEFAULT_KEEPAWAKE_INTERVAL = timedelta(seconds=59)


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class DurationPreset:
    key: str
    duration: timedelta | None


PRESETS = (
    DurationPreset(key="15m", duration=timedelta(minutes=15)),
    DurationPreset(key="30m", duration=timedelta(minutes=30)),
    DurationPreset(key="1h", duration=timedelta(hours=1)),
    DurationPreset(key="2h", duration=timedelta(hours=2)),
    DurationPreset(key="infinite", duration=None),
)

PRESET_BY_KEY = {preset.key: preset for preset in PRESETS}


@dataclass(frozen=True)
class SessionMode:
    kind: str
    ends_at: datetime | None = None
    preset_key: str | None = None

    @classmethod
    def off(cls) -> Self:
        return cls(kind="off")

    @classmethod
    def infinite(cls) -> Self:
        return cls(kind="infinite", preset_key="infinite")

    @classmethod
    def timed(cls, ends_at: datetime, preset_key: str) -> Self:
        return cls(kind="timed", ends_at=ends_at, preset_key=preset_key)

    def is_active(self, now: datetime | None = None) -> bool:
        if self.kind == "infinite":
            return True
        if self.kind != "timed" or self.ends_at is None:
            return False
        return now is None or now < self.ends_at

    def has_expired(self, now: datetime) -> bool:
        return self.kind == "timed" and self.ends_at is not None and now >= self.ends_at

    def remaining(self, now: datetime) -> timedelta:
        if self.kind != "timed" or self.ends_at is None:
            return timedelta(0)
        return max(timedelta(0), self.ends_at - now)


class SessionState:
    def __init__(self, now_fn: Callable[[], datetime] = utc_now) -> None:
        self._now_fn = now_fn
        self._mode = SessionMode.off()

    @property
    def mode(self) -> SessionMode:
        return self._mode

    def activate(self, duration: timedelta | None, preset_key: str) -> SessionMode:
        now = self._now_fn()
        if duration is None:
            self._mode = SessionMode.infinite()
        else:
            self._mode = SessionMode.timed(now + duration, preset_key)
        return self._mode

    def deactivate(self) -> SessionMode:
        self._mode = SessionMode.off()
        return self._mode

    def expire_if_needed(self, now: datetime | None = None) -> bool:
        current_now = now or self._now_fn()
        if self._mode.has_expired(current_now):
            self._mode = SessionMode.off()
            return True
        return False


def next_keepawake_at(
    now: datetime,
    last_sent_at: datetime | None,
    interval: timedelta = DEFAULT_KEEPAWAKE_INTERVAL,
) -> datetime:
    if last_sent_at is None:
        return now

    due_at = last_sent_at + interval
    if due_at <= now:
        return now
    return due_at
