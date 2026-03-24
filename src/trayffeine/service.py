from __future__ import annotations

import logging
import threading
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from .session import (
    DEFAULT_KEEPAWAKE_INTERVAL,
    SessionMode,
    SessionState,
    next_keepawake_at,
    utc_now,
)

LOGGER = logging.getLogger(__name__)


class InputBackend(Protocol):
    def on_session_start(self) -> None: ...

    def send_keepawake(self) -> None: ...

    def on_session_stop(self) -> None: ...


@dataclass(frozen=True)
class ServiceSnapshot:
    mode: SessionMode
    now: datetime


class TrayffeineService:
    def __init__(
        self,
        backend: InputBackend,
        *,
        now_fn: Callable[[], datetime] = utc_now,
        keepawake_interval: timedelta = DEFAULT_KEEPAWAKE_INTERVAL,
        on_state_change: Callable[[], None] | None = None,
        on_timer_finished: Callable[[], None] | None = None,
        on_tick: Callable[[], None] | None = None,
    ) -> None:
        self._backend = backend
        self._now_fn = now_fn
        self._keepawake_interval = keepawake_interval
        self._on_state_change = on_state_change
        self._on_timer_finished = on_timer_finished
        self._on_tick = on_tick
        self._state = SessionState(now_fn=now_fn)
        self._last_sent_at: datetime | None = None
        self._pending_backend_ops: deque[tuple[str, InputBackend]] = deque()
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()
        self._worker = threading.Thread(
            target=self._run,
            daemon=True,
            name="trayffeine-worker",
        )
        self._worker.start()

    def set_callbacks(
        self,
        *,
        on_state_change: Callable[[], None] | None,
        on_timer_finished: Callable[[], None] | None,
        on_tick: Callable[[], None] | None = None,
    ) -> None:
        self._on_state_change = on_state_change
        self._on_timer_finished = on_timer_finished
        self._on_tick = on_tick

    def snapshot(self) -> ServiceSnapshot:
        with self._lock:
            return ServiceSnapshot(mode=self._state.mode, now=self._now_fn())

    def activate(self, duration: timedelta | None, preset_key: str) -> None:
        with self._lock:
            if self._state.mode.is_active(self._now_fn()):
                self._queue_backend_stop_locked(self._backend)
            self._state.activate(duration, preset_key)
            self._last_sent_at = None
            self._queue_backend_start_locked(self._backend)
        self._wake_event.set()
        self._emit_state_change()

    def deactivate(self) -> None:
        with self._lock:
            if self._state.mode.is_active(self._now_fn()):
                self._queue_backend_stop_locked(self._backend)
            self._state.deactivate()
            self._last_sent_at = None
        self._wake_event.set()
        self._emit_state_change()

    def toggle_infinite(self) -> None:
        with self._lock:
            now = self._now_fn()
            if self._state.mode.is_active(now):
                self._queue_backend_stop_locked(self._backend)
                self._state.deactivate()
            else:
                self._state.activate(None, "infinite")
                self._queue_backend_start_locked(self._backend)
            self._last_sent_at = None
        self._wake_event.set()
        self._emit_state_change()

    def set_backend(self, backend: InputBackend) -> None:
        with self._lock:
            was_active = self._state.mode.is_active(self._now_fn())
            old_backend = self._backend
            if was_active:
                self._queue_backend_stop_locked(old_backend)
            self._backend = backend
            self._last_sent_at = None
            if was_active:
                self._queue_backend_start_locked(backend)
        self._wake_event.set()

    def quit(self) -> None:
        with self._lock:
            if self._state.mode.is_active(self._now_fn()):
                self._queue_backend_stop_locked(self._backend)
        self._stop_event.set()
        self._wake_event.set()
        if self._worker.is_alive():
            self._worker.join(timeout=2)

    def _run(self) -> None:
        while True:
            self._process_pending_backend_ops()
            if self._stop_event.is_set():
                return

            timeout = 1.0
            send_keepawake = False
            timer_finished = False

            with self._lock:
                now = self._now_fn()
                if self._state.expire_if_needed(now):
                    self._stop_backend_on_worker(self._backend)
                    self._last_sent_at = None
                    timer_finished = True
                mode = self._state.mode

                if mode.is_active(now):
                    due_at = next_keepawake_at(
                        now=now,
                        last_sent_at=self._last_sent_at,
                        interval=self._keepawake_interval,
                    )
                    timeout = max(0.0, (due_at - now).total_seconds())
                    if mode.kind == "timed" and mode.ends_at is not None:
                        expires_in = max(0.0, (mode.ends_at - now).total_seconds())
                        timeout = min(timeout, expires_in)
                    timeout = min(timeout, 1.0)
                    send_keepawake = due_at <= now
                else:
                    self._last_sent_at = None

            if timer_finished:
                self._emit_state_change()
                self._emit_timer_finished()
                continue

            if send_keepawake:
                with self._lock:
                    try:
                        self._backend.send_keepawake()
                    except OSError:
                        LOGGER.exception("Failed to send keep-awake input")
                    finally:
                        self._last_sent_at = self._now_fn()
                continue

            woke_early = self._wake_event.wait(timeout=timeout)
            self._wake_event.clear()
            if not woke_early and self.snapshot().mode.is_active():
                self._emit_tick()

    def _emit_state_change(self) -> None:
        if self._on_state_change is None:
            return
        try:
            self._on_state_change()
        except Exception:
            LOGGER.exception("State change callback failed")

    def _emit_timer_finished(self) -> None:
        if self._on_timer_finished is None:
            return
        try:
            self._on_timer_finished()
        except Exception:
            LOGGER.exception("Timer finished callback failed")

    def _emit_tick(self) -> None:
        if self._on_tick is None:
            return
        try:
            self._on_tick()
        except Exception:
            LOGGER.exception("Tick callback failed")

    def _process_pending_backend_ops(self) -> None:
        while True:
            with self._lock:
                if not self._pending_backend_ops:
                    return
                operation, backend = self._pending_backend_ops.popleft()

            if operation == "start":
                self._start_backend_on_worker(backend)
            else:
                self._stop_backend_on_worker(backend)

    def _queue_backend_start_locked(self, backend: InputBackend) -> None:
        self._pending_backend_ops.append(("start", backend))

    def _queue_backend_stop_locked(self, backend: InputBackend) -> None:
        self._pending_backend_ops.append(("stop", backend))

    def _start_backend_on_worker(self, backend: InputBackend) -> None:
        try:
            backend.on_session_start()
        except OSError:
            LOGGER.exception("Failed to start keep-awake backend")

    def _stop_backend_on_worker(self, backend: InputBackend) -> None:
        try:
            backend.on_session_stop()
        except OSError:
            LOGGER.exception("Failed to stop keep-awake backend")
