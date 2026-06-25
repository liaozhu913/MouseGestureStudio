from __future__ import annotations

import sys
import subprocess
import winreg
from pathlib import Path

from . import win32


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE_NAME = "MouseGestureStudio"
TASK_NAME = "MouseGestureStudio"


def executable_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()
    return Path(sys.argv[0]).resolve()


def startup_command() -> str:
    return f'"{executable_path()}"'


def _task_command() -> str:
    return f'"{executable_path()}"'


def _task_exists() -> bool:
    result = subprocess.run(
        ["schtasks", "/Query", "/TN", TASK_NAME],
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return result.returncode == 0


def _create_startup_task() -> None:
    result = subprocess.run(
        [
            "schtasks",
            "/Create",
            "/TN",
            TASK_NAME,
            "/TR",
            _task_command(),
            "/SC",
            "ONLOGON",
            "/RL",
            "HIGHEST",
            "/F",
        ],
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if result.returncode != 0:
        raise OSError((result.stderr or result.stdout or "创建计划任务失败").strip())


def _delete_startup_task() -> None:
    subprocess.run(
        ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


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
    return _task_exists() or startup_target() is not None


def is_startup_enabled() -> bool:
    if _task_exists():
        return True
    target = startup_target()
    if target is None:
        return False
    return str(target.resolve()).lower() == str(executable_path()).lower()


def set_startup_enabled(enabled: bool) -> None:
    if enabled and win32.is_user_admin():
        _create_startup_task()
        _delete_run_value()
        return

    if not enabled:
        _delete_startup_task()
        _delete_run_value()
        return

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        RUN_KEY,
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        winreg.SetValueEx(key, RUN_VALUE_NAME, 0, winreg.REG_SZ, startup_command())


def _delete_run_value() -> None:
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            RUN_KEY,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.DeleteValue(key, RUN_VALUE_NAME)
    except FileNotFoundError:
        pass
