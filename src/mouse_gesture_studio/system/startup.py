from __future__ import annotations

import sys
import winreg
from pathlib import Path


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE_NAME = "MouseGestureStudio"


def executable_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()
    return Path(sys.argv[0]).resolve()


def startup_command() -> str:
    return f'"{executable_path()}"'


def startup_target() -> Path | None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, RUN_VALUE_NAME)
    except FileNotFoundError:
        return None
    except OSError:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if raw.startswith('"'):
        end_quote = raw.find('"', 1)
        if end_quote > 1:
            return Path(raw[1:end_quote])
    return Path(raw.split()[0].strip('"'))


def has_startup_entry() -> bool:
    return startup_target() is not None


def is_startup_enabled() -> bool:
    target = startup_target()
    if target is None:
        return False
    return str(target.resolve()).lower() == str(executable_path()).lower()


def set_startup_enabled(enabled: bool) -> None:
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        RUN_KEY,
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        if enabled:
            winreg.SetValueEx(key, RUN_VALUE_NAME, 0, winreg.REG_SZ, startup_command())
            return
        try:
            winreg.DeleteValue(key, RUN_VALUE_NAME)
        except FileNotFoundError:
            pass
