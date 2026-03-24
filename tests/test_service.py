from __future__ import annotations

import threading
import time
from datetime import UTC, datetime, timedelta

from trayffeine.service import TrayffeineService


class BackendSpy:
    def __init__(self) -> None:
        self.start_calls = 0
        self.send_calls = 0
        self.stop_calls = 0
        self.start_event = threading.Event()
        self.stop_event = threading.Event()

    def on_session_start(self) -> None:
        self.start_calls += 1
        self.start_event.set()

    def send_keepawake(self) -> None:
        self.send_calls += 1

    def on_session_stop(self) -> None:
        self.stop_calls += 1
        self.stop_event.set()


class ThreadTrackingBackend(BackendSpy):
    def __init__(self) -> None:
        super().__init__()
        self.thread_ids: list[int] = []

    def on_session_start(self) -> None:
        self.thread_ids.append(threading.get_ident())
        super().on_session_start()

    def send_keepawake(self) -> None:
        self.thread_ids.append(threading.get_ident())
        super().send_keepawake()

    def on_session_stop(self) -> None:
        self.thread_ids.append(threading.get_ident())
        super().on_session_stop()


class Clock:
    def __init__(self, initial: datetime) -> None:
        self.current = initial
        self._lock = threading.Lock()

    def now(self) -> datetime:
        with self._lock:
            return self.current

    def advance(self, delta: timedelta) -> None:
        with self._lock:
            self.current += delta


def test_service_activation_and_deactivation_call_backend_hooks() -> None:
    backend = BackendSpy()
    service = TrayffeineService(backend=backend)

    try:
        service.activate(timedelta(minutes=15), "15m")
        assert backend.start_event.wait(timeout=0.5) is True

        service.deactivate()
        assert backend.stop_event.wait(timeout=0.5) is True
    finally:
        service.quit()

    assert backend.start_calls == 1
    assert backend.stop_calls == 1


def test_service_set_backend_restarts_active_session() -> None:
    first_backend = BackendSpy()
    second_backend = BackendSpy()
    service = TrayffeineService(backend=first_backend)

    try:
        service.activate(None, "infinite")
        assert first_backend.start_event.wait(timeout=0.5) is True

        service.set_backend(second_backend)

        assert first_backend.stop_event.wait(timeout=0.5) is True
        assert second_backend.start_event.wait(timeout=0.5) is True
    finally:
        service.quit()

    assert first_backend.start_calls == 1
    assert first_backend.stop_calls == 1
    assert second_backend.start_calls == 1
    assert second_backend.stop_calls == 1


def test_service_quit_stops_active_backend() -> None:
    backend = BackendSpy()
    service = TrayffeineService(backend=backend)

    service.activate(None, "infinite")
    assert backend.start_event.wait(timeout=0.5) is True
    service.quit()

    assert backend.start_calls == 1
    assert backend.stop_event.wait(timeout=0.5) is True
    assert backend.stop_calls == 1


def test_service_timer_expiration_stops_backend() -> None:
    clock = Clock(datetime(2026, 3, 24, 12, 0, tzinfo=UTC))
    backend = BackendSpy()
    service = TrayffeineService(backend=backend, now_fn=clock.now)

    try:
        service.activate(timedelta(seconds=1), "15m")
        assert backend.start_event.wait(timeout=0.5) is True

        clock.advance(timedelta(seconds=2))
        service._wake_event.set()

        assert backend.stop_event.wait(timeout=0.5) is True
        assert _wait_until(lambda: service.snapshot().mode.kind == "off")
    finally:
        service.quit()


def test_service_runs_backend_lifecycle_on_the_worker_thread() -> None:
    backend = ThreadTrackingBackend()
    service = TrayffeineService(backend=backend)

    try:
        service.activate(None, "infinite")
        assert backend.start_event.wait(timeout=0.5) is True
        assert _wait_until(lambda: backend.send_calls >= 1)

        service.deactivate()
        assert backend.stop_event.wait(timeout=0.5) is True
    finally:
        service.quit()

    assert len(set(backend.thread_ids)) == 1


def _wait_until(predicate, timeout: float = 0.5) -> bool:  # noqa: ANN001
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False
