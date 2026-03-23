from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
VK_F15 = 0x7E
ERROR_ALREADY_EXISTS = 183
ULONG_PTR = wintypes.WPARAM


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("u", _INPUTUNION),
    ]


LPINPUT = ctypes.POINTER(INPUT)

user32.SendInput.argtypes = (wintypes.UINT, LPINPUT, ctypes.c_int)
user32.SendInput.restype = wintypes.UINT
kernel32.CreateMutexW.argtypes = (ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR)
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.ReleaseMutex.argtypes = (wintypes.HANDLE,)
kernel32.ReleaseMutex.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
kernel32.CloseHandle.restype = wintypes.BOOL


class WindowsInputBackend:
    def send_keepawake(self) -> None:
        inputs = (INPUT * 2)(
            INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=VK_F15)),
            INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=VK_F15, dwFlags=KEYEVENTF_KEYUP)),
        )
        sent = user32.SendInput(len(inputs), inputs, ctypes.sizeof(INPUT))
        if sent != len(inputs):
            error_code = ctypes.get_last_error()
            raise OSError(error_code, "SendInput failed")


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

