from __future__ import annotations

import asyncio
import ctypes
import logging
import os
import subprocess
import sys
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

from .keepawake import KeepAwakeMethod

LOGGER = logging.getLogger(__name__)

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WORD = ctypes.c_uint16
DWORD = ctypes.c_uint32
LONG = ctypes.c_int32
UINT = ctypes.c_uint
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
VK_SHIFT = 0x10
VK_F15 = 0x7E
ERROR_ALREADY_EXISTS = 183
ERROR_INSUFFICIENT_BUFFER = 122
APPMODEL_ERROR_NO_PACKAGE = 15700
ULONG_PTR = ctypes.c_size_t
MB_OK = 0x00000000
MB_ICONERROR = 0x00000010
MB_ICONINFORMATION = 0x00000040
MB_ICONQUESTION = 0x00000020
MB_YESNO = 0x00000004
IDYES = 6
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
HWND_MESSAGE = wintypes.HWND(-3)
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002
ES_CONTINUOUS = 0x80000000
RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE_NAME = "Trayffeine"
STARTUP_TASK_ID = "TrayffeineStartup"


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", LONG),
        ("dy", LONG),
        ("mouseData", DWORD),
        ("dwFlags", DWORD),
        ("time", DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", WORD),
        ("wScan", WORD),
        ("dwFlags", DWORD),
        ("time", DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", DWORD),
        ("wParamL", WORD),
        ("wParamH", WORD),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [
        ("type", DWORD),
        ("u", _INPUTUNION),
    ]


LPINPUT = ctypes.POINTER(INPUT)

user32.SendInput.argtypes = (UINT, LPINPUT, ctypes.c_int)
user32.SendInput.restype = UINT
kernel32.SetThreadExecutionState.argtypes = (DWORD,)
kernel32.SetThreadExecutionState.restype = DWORD
kernel32.CreateMutexW.argtypes = (ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR)
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.ReleaseMutex.argtypes = (wintypes.HANDLE,)
kernel32.ReleaseMutex.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.GetCurrentPackageFullName.argtypes = (ctypes.POINTER(DWORD), wintypes.LPWSTR)
kernel32.GetCurrentPackageFullName.restype = LONG
user32.MessageBoxW.argtypes = (
    wintypes.HWND,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.UINT,
)
user32.MessageBoxW.restype = ctypes.c_int


class KeyboardInputBackend:
    def __init__(self, virtual_key: int, method: KeepAwakeMethod) -> None:
        self._virtual_key = virtual_key
        self._method = method

    @property
    def effective_method(self) -> KeepAwakeMethod:
        return self._method

    def on_session_start(self) -> None:
        return

    def send_keepawake(self) -> None:
        inputs = (INPUT * 2)(
            INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=self._virtual_key)),
            INPUT(
                type=INPUT_KEYBOARD,
                ki=KEYBDINPUT(wVk=self._virtual_key, dwFlags=KEYEVENTF_KEYUP),
            ),
        )
        sent = user32.SendInput(len(inputs), inputs, ctypes.sizeof(INPUT))
        if sent != len(inputs):
            error_code = ctypes.get_last_error()
            raise OSError(error_code, "SendInput failed")

    def on_session_stop(self) -> None:
        return


class ExecutionStateBackend:
    def __init__(self) -> None:
        self._active_flags = ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
        self._inactive_flags = ES_CONTINUOUS

    @property
    def effective_method(self) -> KeepAwakeMethod:
        return "execution-state"

    def on_session_start(self) -> None:
        self._apply(self._active_flags)

    def send_keepawake(self) -> None:
        self._apply(self._active_flags)

    def on_session_stop(self) -> None:
        self._apply(self._inactive_flags)

    def _apply(self, flags: int) -> None:
        result = kernel32.SetThreadExecutionState(flags)
        if result == 0:
            error_code = ctypes.get_last_error()
            raise OSError(error_code, "SetThreadExecutionState failed")


class SmartKeepAwakeBackend:
    def __init__(
        self,
        candidates: tuple[tuple[KeepAwakeMethod, object], ...] | None = None,
    ) -> None:
        self._candidates = candidates or (
            ("execution-state", ExecutionStateBackend()),
            ("f15", KeyboardInputBackend(VK_F15, "f15")),
            ("shift", KeyboardInputBackend(VK_SHIFT, "shift")),
        )
        self._active_index: int | None = None

    @property
    def effective_method(self) -> KeepAwakeMethod | None:
        if self._active_index is None:
            return None
        return self._candidates[self._active_index][0]

    def on_session_start(self) -> None:
        self._active_index = None
        self._activate_from(0)

    def send_keepawake(self) -> None:
        if self._active_index is None:
            self._activate_from(0)

        while self._active_index is not None:
            index = self._active_index
            backend = self._candidates[index][1]
            try:
                backend.send_keepawake()
                return
            except OSError as exc:
                self._fallback_from(index, exc)

        raise OSError(0, "No keep-awake backend succeeded")

    def on_session_stop(self) -> None:
        if self._active_index is None:
            return

        backend = self._candidates[self._active_index][1]
        try:
            backend.on_session_stop()
        finally:
            self._active_index = None

    def _activate_from(self, start_index: int) -> None:
        self._active_index = None
        last_error: OSError | None = None

        for index in range(start_index, len(self._candidates)):
            backend = self._candidates[index][1]
            try:
                backend.on_session_start()
                self._active_index = index
                return
            except OSError as exc:
                last_error = exc
                self._log_fallback(index, exc)

        if last_error is not None:
            raise last_error
        raise OSError(0, "No keep-awake backend configured")

    def _fallback_from(self, current_index: int, error: OSError) -> None:
        self._log_fallback(current_index, error)
        backend = self._candidates[current_index][1]
        try:
            backend.on_session_stop()
        except OSError:
            LOGGER.exception("Failed to stop keep-awake backend during fallback")
        self._activate_from(current_index + 1)

    def _log_fallback(self, index: int, error: OSError) -> None:
        method = self._candidates[index][0]
        LOGGER.warning(
            "Keep-awake method %s failed; trying the next fallback",
            method,
            exc_info=(type(error), error, error.__traceback__),
        )


class WindowsInputBackend(KeyboardInputBackend):
    def __init__(self) -> None:
        super().__init__(VK_F15, "f15")


def create_keepawake_backend(method: KeepAwakeMethod):
    if method == "execution-state":
        return ExecutionStateBackend()
    if method == "f15":
        return KeyboardInputBackend(VK_F15, "f15")
    if method == "shift":
        return KeyboardInputBackend(VK_SHIFT, "shift")
    return SmartKeepAwakeBackend()


def show_message_box(title: str, message: str) -> None:
    user32.MessageBoxW(None, message, title, MB_OK | MB_ICONERROR)


def show_info_message_box(title: str, message: str) -> None:
    user32.MessageBoxW(None, message, title, MB_OK | MB_ICONINFORMATION)


def confirm_message_box(title: str, message: str) -> bool:
    result = user32.MessageBoxW(None, message, title, MB_YESNO | MB_ICONQUESTION)
    return result == IDYES


def copy_text_to_clipboard(text: str) -> None:
    kernel32.GlobalAlloc.argtypes = (UINT, ctypes.c_size_t)
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = (ctypes.c_void_p,)
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = (ctypes.c_void_p,)
    kernel32.GlobalUnlock.restype = wintypes.BOOL
    user32.OpenClipboard.argtypes = (wintypes.HWND,)
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.EmptyClipboard.argtypes = ()
    user32.EmptyClipboard.restype = wintypes.BOOL
    user32.SetClipboardData.argtypes = (UINT, ctypes.c_void_p)
    user32.SetClipboardData.restype = ctypes.c_void_p
    user32.CloseClipboard.argtypes = ()
    user32.CloseClipboard.restype = wintypes.BOOL
    user32.DestroyWindow.argtypes = (wintypes.HWND,)
    user32.DestroyWindow.restype = wintypes.BOOL

    buffer = ctypes.create_unicode_buffer(text)
    byte_count = ctypes.sizeof(buffer)
    handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, byte_count)
    if not handle:
        error_code = ctypes.get_last_error()
        raise OSError(error_code, "GlobalAlloc failed")

    locked = kernel32.GlobalLock(handle)
    if not locked:
        error_code = ctypes.get_last_error()
        raise OSError(error_code, "GlobalLock failed")

    try:
        ctypes.memmove(locked, ctypes.addressof(buffer), byte_count)
    finally:
        kernel32.GlobalUnlock(handle)

    owner_window = _create_clipboard_owner_window()
    clipboard_opened = False

    try:
        if not user32.OpenClipboard(owner_window):
            error_code = ctypes.get_last_error()
            raise OSError(error_code, "OpenClipboard failed")
        clipboard_opened = True
        if not user32.EmptyClipboard():
            error_code = ctypes.get_last_error()
            raise OSError(error_code, "EmptyClipboard failed")
        if not user32.SetClipboardData(CF_UNICODETEXT, handle):
            error_code = ctypes.get_last_error()
            raise OSError(error_code, "SetClipboardData failed")
    finally:
        if clipboard_opened:
            user32.CloseClipboard()
        user32.DestroyWindow(owner_window)


def _create_clipboard_owner_window() -> wintypes.HWND:
    user32.CreateWindowExW.argtypes = (
        DWORD,
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        DWORD,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.HWND,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
    )
    user32.CreateWindowExW.restype = wintypes.HWND

    owner_window = user32.CreateWindowExW(
        0,
        "STATIC",
        "Trayffeine Clipboard Owner",
        0,
        0,
        0,
        0,
        0,
        HWND_MESSAGE,
        None,
        None,
        None,
    )
    if not owner_window:
        error_code = ctypes.get_last_error()
        raise OSError(error_code, "CreateWindowExW failed")
    return owner_window


def open_path_in_shell(path: str | Path) -> None:
    os.startfile(str(path))  # type: ignore[attr-defined]


def startup_launch_command() -> str:
    executable = str(Path(sys.executable))
    if getattr(sys, "frozen", False):
        return subprocess.list2cmdline([executable])
    return subprocess.list2cmdline([_windowless_python_executable(executable), "-m", "trayffeine"])


def _windowless_python_executable(executable: str) -> str:
    normalized = PureWindowsPath(executable)
    if normalized.name.lower() == "pythonw.exe":
        return executable
    if normalized.suffix.lower() == ".exe" and normalized.stem.lower().startswith("python"):
        return str(normalized.with_name("pythonw.exe"))
    return executable


def is_start_with_windows_enabled() -> bool:
    if is_packaged_app():
        return _is_packaged_startup_task_enabled()
    return _is_run_key_startup_enabled()


def set_start_with_windows_enabled(enabled: bool) -> bool:
    if is_packaged_app():
        return _set_packaged_startup_task_enabled(enabled)
    if enabled:
        _enable_start_with_windows()
    else:
        _disable_start_with_windows()
    return _is_run_key_startup_enabled()


def is_packaged_app() -> bool:
    length = DWORD()
    result = kernel32.GetCurrentPackageFullName(ctypes.byref(length), None)
    if result == APPMODEL_ERROR_NO_PACKAGE:
        return False
    if result in (0, ERROR_INSUFFICIENT_BUFFER):
        return True
    raise OSError(result, "GetCurrentPackageFullName failed")


def _is_run_key_startup_enabled() -> bool:
    winreg = _winreg_module()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH) as key:
            value, _ = winreg.QueryValueEx(key, RUN_VALUE_NAME)
    except FileNotFoundError:
        return False
    return isinstance(value, str) and bool(value.strip())


def _is_packaged_startup_task_enabled() -> bool:
    task = _get_packaged_startup_task()
    return _startup_task_state_name(task.state) in {"ENABLED", "ENABLED_BY_POLICY"}


def _set_packaged_startup_task_enabled(enabled: bool) -> bool:
    task = _get_packaged_startup_task()
    state_name = _startup_task_state_name(task.state)

    if not enabled:
        if state_name in {"DISABLED", "DISABLED_BY_USER", "DISABLED_BY_POLICY"}:
            return False
        if state_name == "ENABLED_BY_POLICY":
            return True
        task.disable()
        return False

    if state_name in {"ENABLED", "ENABLED_BY_POLICY"}:
        return True
    if state_name in {"DISABLED_BY_USER", "DISABLED_BY_POLICY"}:
        return False

    state = _await_winrt_operation(task.request_enable_async())
    return _startup_task_state_name(state) in {"ENABLED", "ENABLED_BY_POLICY"}


def _get_packaged_startup_task():  # noqa: ANN202
    try:
        from winrt.windows.applicationmodel import StartupTask
    except ImportError as exc:
        raise RuntimeError(
            "MSIX startup support is unavailable. Rebuild the package with the msix dependency."
        ) from exc
    return _await_winrt_operation(StartupTask.get_async(STARTUP_TASK_ID))


async def _await_operation(operation):  # noqa: ANN001, ANN202
    return await operation


def _await_winrt_operation(operation):  # noqa: ANN001, ANN202
    return asyncio.run(_await_operation(operation))


def _startup_task_state_name(state: object) -> str:
    return getattr(state, "name", str(state))


def _enable_start_with_windows() -> None:
    winreg = _winreg_module()
    command = startup_launch_command()
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH) as key:
        winreg.SetValueEx(key, RUN_VALUE_NAME, 0, winreg.REG_SZ, command)


def _disable_start_with_windows() -> None:
    winreg = _winreg_module()
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            RUN_KEY_PATH,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.DeleteValue(key, RUN_VALUE_NAME)
    except FileNotFoundError:
        return


def _winreg_module():
    import importlib

    return importlib.import_module("winreg")


@dataclass
class SingleInstanceGuard:
    handle: int | None
    acquired: bool

    @classmethod
    def acquire(cls, name: str) -> SingleInstanceGuard:
        handle = kernel32.CreateMutexW(None, False, name)
        if not handle:
            error_code = ctypes.get_last_error()
            raise OSError(error_code, "CreateMutexW failed")

        if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(handle)
            return cls(handle=None, acquired=False)

        return cls(handle=handle, acquired=True)

    def release(self) -> None:
        if self.handle is None:
            return
        kernel32.ReleaseMutex(self.handle)
        kernel32.CloseHandle(self.handle)
        self.handle = None
