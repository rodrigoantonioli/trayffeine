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
    module, send_input, _ = _load_windows_module(monkeypatch, send_input_result=2)
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


def test_shift_backend_uses_shift_virtual_key(monkeypatch) -> None:
    module, send_input, _ = _load_windows_module(monkeypatch, send_input_result=2)

    backend = module.create_keepawake_backend("shift")
    backend.send_keepawake()

    _, inputs, _ = send_input.calls[0]
    assert inputs[0].ki.wVk == module.VK_SHIFT
    assert inputs[1].ki.wVk == module.VK_SHIFT


def test_execution_state_backend_calls_windows_api_on_start_and_stop(monkeypatch) -> None:
    module, _, set_thread_execution_state = _load_windows_module(
        monkeypatch,
        send_input_result=2,
        execution_state_result=1,
    )

    backend = module.create_keepawake_backend("execution-state")
    backend.on_session_start()
    backend.send_keepawake()
    backend.on_session_stop()

    assert set_thread_execution_state.calls == [
        ((module.ES_CONTINUOUS | module.ES_SYSTEM_REQUIRED | module.ES_DISPLAY_REQUIRED),),
        ((module.ES_CONTINUOUS | module.ES_SYSTEM_REQUIRED | module.ES_DISPLAY_REQUIRED),),
        (module.ES_CONTINUOUS,),
    ]


def test_smart_backend_falls_back_in_fixed_order_on_technical_failure(monkeypatch) -> None:
    module, _, _ = _load_windows_module(monkeypatch, send_input_result=2)
    calls: list[str] = []

    class FakeBackend:
        def __init__(self, name: str, fail_start: bool = False, fail_send: bool = False) -> None:
            self.name = name
            self.fail_start = fail_start
            self.fail_send = fail_send

        def on_session_start(self) -> None:
            calls.append(f"{self.name}:start")
            if self.fail_start:
                raise OSError(1, f"{self.name} failed")

        def send_keepawake(self) -> None:
            calls.append(f"{self.name}:send")
            if self.fail_send:
                raise OSError(2, f"{self.name} send failed")

        def on_session_stop(self) -> None:
            calls.append(f"{self.name}:stop")

    backend = module.SmartKeepAwakeBackend(
        candidates=(
            ("execution-state", FakeBackend("execution-state", fail_start=True)),
            ("f15", FakeBackend("f15", fail_send=True)),
            ("shift", FakeBackend("shift")),
        )
    )

    backend.on_session_start()
    backend.send_keepawake()

    assert calls == [
        "execution-state:start",
        "f15:start",
        "f15:send",
        "f15:stop",
        "shift:start",
        "shift:send",
    ]


def test_start_with_windows_writes_run_key(monkeypatch) -> None:
    module, _, _ = _load_windows_module(monkeypatch, send_input_result=2)
    fake_winreg = _install_fake_winreg(monkeypatch)
    monkeypatch.setattr(
        module,
        "startup_launch_command",
        lambda: '"C:\\Program Files\\Trayffeine.exe"',
    )

    module.set_start_with_windows_enabled(True)

    assert fake_winreg.values[module.RUN_VALUE_NAME] == '"C:\\Program Files\\Trayffeine.exe"'
    assert module.is_start_with_windows_enabled() is True


def test_start_with_windows_delete_ignores_missing_value(monkeypatch) -> None:
    module, _, _ = _load_windows_module(monkeypatch, send_input_result=2)
    fake_winreg = _install_fake_winreg(monkeypatch)

    module.set_start_with_windows_enabled(False)
    assert fake_winreg.values == {}

    fake_winreg.values[module.RUN_VALUE_NAME] = '"C:\\Program Files\\Trayffeine.exe"'
    module.set_start_with_windows_enabled(False)

    assert fake_winreg.values == {}
    assert module.is_start_with_windows_enabled() is False


def test_startup_launch_command_uses_python_module_when_not_frozen(monkeypatch) -> None:
    module, _, _ = _load_windows_module(monkeypatch, send_input_result=2)

    monkeypatch.setattr(module.sys, "executable", r"C:\Python312\pythonw.exe")
    monkeypatch.delattr(module.sys, "frozen", raising=False)

    assert module.startup_launch_command() == r"C:\Python312\pythonw.exe -m trayffeine"


def _load_windows_module(
    monkeypatch,
    *,
    send_input_result: int,
    execution_state_result: int = 1,
):
    send_input = FakeFunction(return_value=send_input_result)
    set_thread_execution_state = FakeFunction(return_value=execution_state_result)
    fake_user32 = SimpleNamespace(
        SendInput=send_input,
        MessageBoxW=FakeFunction(return_value=0),
    )
    fake_kernel32 = SimpleNamespace(
        SetThreadExecutionState=set_thread_execution_state,
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
    return module, send_input, set_thread_execution_state


def _install_fake_winreg(monkeypatch):
    class FakeKey:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
            return None

    class FakeWinreg:
        HKEY_CURRENT_USER = object()
        KEY_SET_VALUE = 0x0002
        REG_SZ = 1

        def __init__(self) -> None:
            self.values: dict[str, str] = {}

        def CreateKey(self, root, path):  # noqa: ANN001, N802
            assert root is self.HKEY_CURRENT_USER
            assert path == r"Software\Microsoft\Windows\CurrentVersion\Run"
            return FakeKey()

        def OpenKey(self, root, path, reserved=0, access=None):  # noqa: ANN001, N802
            assert root is self.HKEY_CURRENT_USER
            assert path == r"Software\Microsoft\Windows\CurrentVersion\Run"
            return FakeKey()

        def SetValueEx(self, key, name, reserved, kind, value):  # noqa: ANN001, N802
            assert kind == self.REG_SZ
            self.values[name] = value

        def QueryValueEx(self, key, name):  # noqa: ANN001, N802
            if name not in self.values:
                raise FileNotFoundError(name)
            return self.values[name], self.REG_SZ

        def DeleteValue(self, key, name):  # noqa: ANN001, N802
            if name not in self.values:
                raise FileNotFoundError(name)
            del self.values[name]

    fake_winreg = FakeWinreg()
    monkeypatch.setitem(sys.modules, "winreg", fake_winreg)
    return fake_winreg
