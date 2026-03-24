from __future__ import annotations

import ctypes
import importlib
import sys
from types import SimpleNamespace


class FakeFunction:
    def __init__(self, return_value=0) -> None:
        self.return_value = return_value
        self.calls: list[tuple[object, ...]] = []
        self.argtypes = None
        self.restype = None

    def __call__(self, *args):
        self.calls.append(args)
        return self.return_value


def test_windows_input_backend_uses_full_input_union(monkeypatch) -> None:
    send_input = FakeFunction(return_value=2)
    fake_user32 = SimpleNamespace(
        SendInput=send_input,
        MessageBoxW=FakeFunction(return_value=0),
    )
    fake_kernel32 = SimpleNamespace(
        CreateMutexW=FakeFunction(return_value=1),
        ReleaseMutex=FakeFunction(return_value=1),
        CloseHandle=FakeFunction(return_value=1),
    )

    def fake_windll(name: str, use_last_error: bool = True):  # noqa: ARG001
        if name == "user32":
            return fake_user32
        if name == "kernel32":
            return fake_kernel32
        raise AssertionError(name)

    monkeypatch.setattr(ctypes, "WinDLL", fake_windll, raising=False)
    monkeypatch.setattr(ctypes, "get_last_error", lambda: 0, raising=False)
    sys.modules.pop("trayffeine.windows", None)

    module = importlib.import_module("trayffeine.windows")
    field_names = {name for name, _ in module._INPUTUNION._fields_}

    assert field_names == {"mi", "ki", "hi"}
    assert ctypes.sizeof(module.INPUT) == (40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28)

    backend = module.WindowsInputBackend()
    backend.send_keepawake()

    count, inputs, size = send_input.calls[0]
    assert count == 2
    assert size == ctypes.sizeof(module.INPUT)
    assert inputs[0].type == module.INPUT_KEYBOARD
    assert inputs[0].ki.wVk == module.VK_F15
    assert inputs[1].ki.dwFlags == module.KEYEVENTF_KEYUP
