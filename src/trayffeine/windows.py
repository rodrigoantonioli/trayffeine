from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WORD = ctypes.c_uint16
DWORD = ctypes.c_uint32
LONG = ctypes.c_int32
UINT = ctypes.c_uint
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
VK_F15 = 0x7E
ERROR_ALREADY_EXISTS = 183
ULONG_PTR = ctypes.c_size_t
MB_OK = 0x00000000
MB_ICONERROR = 0x00000010


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
kernel32.CreateMutexW.argtypes = (ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR)
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.ReleaseMutex.argtypes = (wintypes.HANDLE,)
kernel32.ReleaseMutex.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
kernel32.CloseHandle.restype = wintypes.BOOL
user32.MessageBoxW.argtypes = (
    wintypes.HWND,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.UINT,
)
user32.MessageBoxW.restype = ctypes.c_int


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


def show_message_box(title: str, message: str) -> None:
    user32.MessageBoxW(None, message, title, MB_OK | MB_ICONERROR)


def open_path_in_shell(path: str | Path) -> None:
    os.startfile(str(path))  # type: ignore[attr-defined]


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
