from __future__ import annotations

from datetime import UTC, datetime, timedelta

from trayffeine.session import SessionState, next_keepawake_at


def test_activate_timed_session_sets_expected_end_time() -> None:
    now = datetime(2026, 3, 23, 12, 0, tzinfo=UTC)
    state = SessionState(now_fn=lambda: now)

    mode = state.activate(timedelta(minutes=30), preset_key="30m")

    assert mode.kind == "timed"
    assert mode.started_at == now
    assert mode.ends_at == now + timedelta(minutes=30)
    assert mode.preset_key == "30m"
    assert mode.elapsed(now + timedelta(minutes=5)) == timedelta(minutes=5)


def test_activate_infinite_and_deactivate() -> None:
    now = datetime(2026, 3, 23, 12, 0, tzinfo=UTC)
    state = SessionState(now_fn=lambda: now)

    mode = state.activate(None, preset_key="infinite")
    assert mode.kind == "infinite"
    assert mode.started_at == now
    assert mode.elapsed(now + timedelta(seconds=20)) == timedelta(seconds=20)

    off = state.deactivate()
    assert off.kind == "off"


def test_expire_if_needed_turns_timed_session_off() -> None:
    now = datetime(2026, 3, 23, 12, 0, tzinfo=UTC)
    state = SessionState(now_fn=lambda: now)
    state.activate(timedelta(minutes=15), preset_key="15m")

    expired = state.expire_if_needed(now + timedelta(minutes=15))

    assert expired is True
    assert state.mode.kind == "off"


def test_next_keepawake_is_immediate_when_session_just_started() -> None:
    now = datetime(2026, 3, 23, 12, 0, tzinfo=UTC)

    assert next_keepawake_at(now=now, last_sent_at=None) == now


def test_next_keepawake_uses_59_second_interval() -> None:
    now = datetime(2026, 3, 23, 12, 0, tzinfo=UTC)
    last_sent = now - timedelta(seconds=10)

    assert next_keepawake_at(now=now, last_sent_at=last_sent) == last_sent + timedelta(seconds=59)
