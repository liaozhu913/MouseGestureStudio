from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import time
import winreg
from datetime import datetime
from urllib.parse import quote, urlparse

from PySide6.QtWidgets import QApplication

from ..models import ActionConfig
from . import win32


SPECIAL_KEYS = {
    "CTRL": win32.VK_CONTROL,
    "CONTROL": win32.VK_CONTROL,
    "SHIFT": win32.VK_SHIFT,
    "ALT": win32.VK_MENU,
    "WIN": win32.VK_LWIN,
    "META": win32.VK_LWIN,
    "ENTER": win32.VK_RETURN,
    "RETURN": win32.VK_RETURN,
    "TAB": win32.VK_TAB,
    "ESC": win32.VK_ESCAPE,
    "ESCAPE": win32.VK_ESCAPE,
    "BACKSPACE": win32.VK_BACK,
    "DELETE": win32.VK_DELETE,
    "DEL": win32.VK_DELETE,
    "INSERT": win32.VK_INSERT,
    "HOME": win32.VK_HOME,
    "END": win32.VK_END,
    "PGUP": win32.VK_PRIOR,
    "PAGEUP": win32.VK_PRIOR,
    "PGDOWN": win32.VK_NEXT,
    "PAGEDOWN": win32.VK_NEXT,
    "LEFT": win32.VK_LEFT,
    "RIGHT": win32.VK_RIGHT,
    "UP": win32.VK_UP,
    "DOWN": win32.VK_DOWN,
    "SPACE": win32.VK_SPACE,
    "PRINT": win32.VK_SNAPSHOT,
    "PRINTSCREEN": win32.VK_SNAPSHOT,
    "F1": 0x70,
    "F2": 0x71,
    "F3": 0x72,
    "F4": 0x73,
    "F5": 0x74,
    "F6": 0x75,
    "F7": 0x76,
    "F8": 0x77,
    "F9": 0x78,
    "F10": 0x79,
    "F11": 0x7A,
    "F12": 0x7B,
}


BUILTIN_SHORTCUTS = {
    "copy": "Ctrl+C",
    "paste": "Ctrl+V",
    "cut": "Ctrl+X",
    "undo": "Ctrl+Z",
    "redo": "Ctrl+Y",
    "select_all": "Ctrl+A",
    "browser_back": "Alt+Left",
    "browser_forward": "Alt+Right",
    "close_tab": "Ctrl+W",
    "reopen_tab": "Ctrl+Shift+T",
    "new_tab": "Ctrl+T",
    "close_window": "Alt+F4",
    "show_desktop": "Win+D",
    "task_view": "Win+Tab",
    "snip": "Win+Shift+S",
}


URL_PATTERN = re.compile(
    r"""
    (?:
        https?://[^\s<>"'`，。！？；、]+
        | www\.[^\s<>"'`，。！？；、]+
        | localhost(?::\d{2,5})?(?:/[^\s<>"'`，。！？；、]*)?
        | 127(?:\.\d{1,3}){3}(?::\d{2,5})?(?:/[^\s<>"'`，。！？；、]*)?
        | (?<!@)\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+
          (?:com|net|org|cn|io|ai|dev|app|top|xyz|edu|gov|co|me|info|biz|tv|cc|site|online|shop|tech|wiki|work|cloud|vip|pro|ink|link|store|news)
          (?::\d{1,5})?(?:[/?#][^\s<>"'`，。！？；、]*)?
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)
URL_WRAP_CHARS = " \t\r\n\"'`“”‘’()[]{}<>《》【】"
URL_TRAILING_CHARS = " \t\r\n\"'`“”‘’.,;:!?，。；：！？、)]}＞》】"


class ActionExecutor:
    def __init__(self, notifier: callable | None = None) -> None:
        self._notifier = notifier

    def execute(self, action: ActionConfig, hint: str = "", *, respect_delay: bool = True) -> None:
        if respect_delay and action.delay_ms > 0:
            time.sleep(action.delay_ms / 1000)

        if action.kind == "builtin":
            self._execute_builtin(action.builtin_name)
        elif action.kind == "shortcut":
            self._execute_shortcut(action.shortcut)
        elif action.kind == "text":
            self._type_text(action.text)
        elif action.kind == "launch":
            self._launch(action.target, action.arguments)
        elif action.kind == "workflow":
            self._execute_workflow(action.workflow)
        elif action.kind == "quicker":
            self._run_quicker_action(action.target, action.arguments, action.shortcut)

        if action.show_hint and hint and self._notifier:
            self._notifier("MouseGestureStudio", hint)

    def _execute_builtin(self, builtin_name: str) -> None:
        if builtin_name == "snip":
            self._open_screen_clip()
            return
        self._execute_shortcut(BUILTIN_SHORTCUTS.get(builtin_name, ""))

    def _open_screen_clip(self) -> None:
        try:
            subprocess.Popen(["explorer.exe", "ms-screenclip:"], shell=False)
            return
        except OSError:
            pass

        try:
            subprocess.Popen(["SnippingTool.exe", "/clip"], shell=False)
            return
        except OSError:
            pass

        time.sleep(0.15)
        self._execute_shortcut(BUILTIN_SHORTCUTS["snip"])

    def click_button(self, button: str) -> None:
        if button == "right":
            win32.send_inputs(
                [
                    win32.make_mouse_input(win32.MOUSEEVENTF_RIGHTDOWN),
                    win32.make_mouse_input(win32.MOUSEEVENTF_RIGHTUP),
                ]
            )
        elif button == "middle":
            win32.send_inputs(
                [
                    win32.make_mouse_input(win32.MOUSEEVENTF_MIDDLEDOWN),
                    win32.make_mouse_input(win32.MOUSEEVENTF_MIDDLEUP),
                ]
            )
        elif button == "x1":
            win32.send_inputs(
                [
                    win32.make_mouse_input(win32.MOUSEEVENTF_XDOWN, win32.XBUTTON1),
                    win32.make_mouse_input(win32.MOUSEEVENTF_XUP, win32.XBUTTON1),
                ]
            )
        elif button == "x2":
            win32.send_inputs(
                [
                    win32.make_mouse_input(win32.MOUSEEVENTF_XDOWN, win32.XBUTTON2),
                    win32.make_mouse_input(win32.MOUSEEVENTF_XUP, win32.XBUTTON2),
                ]
            )

    def _execute_shortcut(self, shortcut: str) -> None:
        if not shortcut:
            return

        parts = [item.strip() for item in shortcut.split("+") if item.strip()]
        modifiers: list[int] = []
        regular: list[int] = []

        for part in parts:
            virtual_key = self._parse_virtual_key(part)
            if virtual_key is None:
                continue
            if virtual_key in {win32.VK_CONTROL, win32.VK_SHIFT, win32.VK_MENU, win32.VK_LWIN}:
                modifiers.append(virtual_key)
            else:
                regular.append(virtual_key)

        inputs = [win32.make_key_input(vk) for vk in modifiers]
        inputs.extend(win32.make_key_input(vk) for vk in regular)
        inputs.extend(win32.make_key_input(vk, key_up=True) for vk in reversed(regular))
        inputs.extend(win32.make_key_input(vk, key_up=True) for vk in reversed(modifiers))
        win32.send_inputs(inputs)

    def _parse_virtual_key(self, token: str) -> int | None:
        normalized = token.strip().upper()
        if normalized in SPECIAL_KEYS:
            return SPECIAL_KEYS[normalized]
        if len(normalized) == 1:
            if "A" <= normalized <= "Z" or "0" <= normalized <= "9":
                return ord(normalized)
            code = win32.user32.VkKeyScanW(normalized)
            if code != -1:
                return code & 0xFF
        return None

    def _type_text(self, text: str) -> None:
        inputs: list[win32.INPUT] = []
        for character in text:
            code_point = ord(character)
            inputs.append(win32.make_key_input(0, scan=code_point, unicode=True))
            inputs.append(win32.make_key_input(0, scan=code_point, unicode=True, key_up=True))
        win32.send_inputs(inputs)

    def _execute_workflow(self, workflow_text: str) -> None:
        if not workflow_text.strip():
            return

        workflow = json.loads(workflow_text)
        steps = workflow
        initial_vars: dict[str, str] = {}
        if isinstance(workflow, dict):
            raw_vars = workflow.get("vars", {})
            if isinstance(raw_vars, dict):
                initial_vars = {str(key): str(value) for key, value in raw_vars.items()}
            steps = workflow.get("steps", [])
        if isinstance(steps, dict):
            steps = steps.get("steps", [])
        if not isinstance(steps, list):
            raise ValueError("workflow must be a list or an object with a steps list")

        context: dict[str, str] = dict(initial_vars)
        self._execute_workflow_steps(steps, context)

    def _execute_workflow_steps(self, steps: list, context: dict[str, str]) -> None:
        for step in steps:
            if not isinstance(step, dict) or step.get("disabled"):
                continue
            self._execute_workflow_step(step, context)

    def _execute_workflow_step(self, step: dict, context: dict[str, str]) -> None:
        kind = str(step.get("kind", "")).strip()
        if kind == "shortcut":
            self._execute_shortcut(self._render_template(str(step.get("keys", "")), context))
        elif kind == "text":
            self._type_text(self._render_template(str(step.get("value", "")), context))
        elif kind == "clipboard":
            self._set_clipboard_text(self._render_template(str(step.get("value", "")), context))
        elif kind == "paste":
            self._execute_shortcut("Ctrl+V")
        elif kind == "delay":
            milliseconds = int(float(step.get("ms", 100)))
            time.sleep(max(milliseconds, 0) / 1000)
        elif kind == "launch":
            self._launch(
                self._render_template(str(step.get("target", "")), context),
                self._render_template(str(step.get("arguments", "")), context),
            )
        elif kind == "open_url":
            self._open_url(self._render_template(str(step.get("url", "")), context))
        elif kind == "open_urls":
            self._open_urls(
                step.get("urls", []),
                context,
                interval_ms=int(float(step.get("interval_ms", 150))),
            )
        elif kind == "builtin":
            self._execute_builtin(str(step.get("name", "")))
        elif kind == "date_picker":
            self._run_date_picker_step(step, context)
        elif kind == "choice":
            self._run_choice_step(step, context)
        elif kind == "set_var":
            name = str(step.get("name", "")).strip()
            if name:
                context[name] = self._render_template(str(step.get("value", "")), context)
        elif kind == "get_selected_text":
            name = str(step.get("var", "selected_text")).strip() or "selected_text"
            context[name] = self._get_selected_text(
                delay_ms=int(float(step.get("delay_ms", 120))),
                restore_clipboard=bool(step.get("restore_clipboard", False)),
            )
        elif kind == "foreach_line":
            self._foreach_line(step, context)

    def _open_url(self, url: str) -> bool:
        urls = self._extract_urls(url)
        if not urls:
            return False
        return self._start_url(urls[0])

    def _open_urls(self, raw_urls, context: dict[str, str], interval_ms: int = 150) -> None:
        if isinstance(raw_urls, str):
            source_text = self._render_template(raw_urls, context)
        elif isinstance(raw_urls, list):
            source_text = "\n".join(self._render_template(str(item), context) for item in raw_urls)
        else:
            return

        opened = 0
        for url in self._extract_urls(source_text):
            if self._start_url(url):
                opened += 1
            if interval_ms > 0 and opened:
                time.sleep(interval_ms / 1000)

        if opened == 0 and self._notifier:
            self._notifier("MouseGestureStudio", "没有找到可打开的网址。")

    def _extract_urls(self, text: str) -> list[str]:
        urls: list[str] = []
        seen: set[str] = set()
        for match in URL_PATTERN.finditer(text or ""):
            normalized = self._normalize_url(match.group(0))
            if normalized and normalized not in seen:
                urls.append(normalized)
                seen.add(normalized)
        return urls

    def _normalize_url(self, raw_url: str) -> str:
        url = raw_url.strip(URL_WRAP_CHARS).rstrip(URL_TRAILING_CHARS)
        if not url:
            return ""

        lower = url.lower()
        if "://" not in url and not lower.startswith(("mailto:", "file:", "quicker:")):
            if lower.startswith(("localhost", "127.0.0.1")):
                return f"http://{url}"
            return f"https://{url}"
        return url

    def _start_url(self, url: str) -> bool:
        try:
            os.startfile(url)
            return True
        except OSError:
            if self._notifier:
                self._notifier("MouseGestureStudio", f"打开网址失败，已跳过：{url}")
            return False

    def _foreach_line(self, step: dict, context: dict[str, str]) -> None:
        source_name = str(step.get("var", "selected_text"))
        item_name = str(step.get("as", "item"))
        raw_steps = step.get("steps", [])
        if not isinstance(raw_steps, list):
            return

        lines = [line.strip() for line in context.get(source_name, "").splitlines() if line.strip()]
        for index, line in enumerate(lines, 1):
            child_context = dict(context)
            child_context[item_name] = line
            child_context["index"] = str(index)
            self._execute_workflow_steps(raw_steps, child_context)

    def _get_selected_text(self, delay_ms: int = 120, restore_clipboard: bool = False) -> str:
        clipboard = QApplication.clipboard()
        previous = clipboard.text() if clipboard else ""
        self._execute_shortcut("Ctrl+C")
        time.sleep(max(delay_ms, 0) / 1000)
        selected = clipboard.text() if clipboard else ""
        if restore_clipboard and clipboard:
            clipboard.setText(previous)
        return selected

    def _run_date_picker_step(self, step: dict, context: dict[str, str]) -> None:
        from ..ui.date_format_dialog import DateFormatDialog

        options = self._date_picker_options(step.get("formats"))
        dialog = DateFormatDialog(options)
        if not dialog.exec():
            context["cancelled"] = "1"
            return

        value = dialog.selected_value()
        context[str(step.get("var", "selected"))] = value
        if bool(step.get("clipboard", True)):
            self._set_clipboard_text(value)
        if bool(step.get("paste", True)):
            self._execute_shortcut("Ctrl+V")

    def _run_choice_step(self, step: dict, context: dict[str, str]) -> None:
        from ..ui.date_format_dialog import DateFormatDialog, DateFormatOption

        raw_options = step.get("options", [])
        if not isinstance(raw_options, list):
            return

        options: list[DateFormatOption] = []
        for index, item in enumerate(raw_options, 1):
            if isinstance(item, str):
                value = self._render_template(item, context)
                label = f"{index} {value}"
            elif isinstance(item, dict):
                value = self._render_template(str(item.get("value", "")), context)
                label = self._render_template(str(item.get("label") or f"{index} {value}"), context)
            else:
                continue
            options.append(DateFormatOption(label=label, value=value))

        if not options:
            return

        title = str(step.get("title", "请选择"))
        dialog = DateFormatDialog(options, title=title)
        if not dialog.exec():
            context["cancelled"] = "1"
            return

        value = dialog.selected_value()
        context[str(step.get("var", "selected"))] = value
        if bool(step.get("clipboard", False)):
            self._set_clipboard_text(value)
        if bool(step.get("paste", False)):
            self._set_clipboard_text(value)
            self._execute_shortcut("Ctrl+V")

        next_steps = step.get("steps", [])
        if isinstance(next_steps, list):
            self._execute_workflow_steps(next_steps, context)

    def _date_picker_options(self, raw_formats) -> list[DateFormatOption] | None:
        from ..ui.date_format_dialog import DateFormatOption

        if not isinstance(raw_formats, list):
            return None

        now = datetime.now()
        options: list[DateFormatOption] = []
        for index, item in enumerate(raw_formats, 1):
            if isinstance(item, str):
                value = self._render_template(item, {}, now)
                label = f"{index} {value}"
            elif isinstance(item, dict):
                value = self._render_template(str(item.get("value", "")), {}, now)
                label = str(item.get("label") or f"{index} {value}")
            else:
                continue
            options.append(DateFormatOption(label=label, value=value))
        return options or None

    def _render_template(
        self,
        template: str,
        context: dict[str, str] | None = None,
        now: datetime | None = None,
    ) -> str:
        current = now or datetime.now()
        values = {
            "date": current.strftime("%Y-%m-%d"),
            "date_dot": current.strftime("%Y.%m.%d"),
            "date_slash": current.strftime("%Y/%m/%d"),
            "date_short": current.strftime("%y%m%d"),
            "date_cn": current.strftime("%Y年%m月%d日"),
            "time": current.strftime("%H:%M:%S"),
            "time_short": current.strftime("%H:%M"),
            "datetime": current.strftime("%Y-%m-%d %H:%M:%S"),
            "clipboard": self._clipboard_text(),
        }
        values.update(context or {})
        result = template
        for key, value in values.items():
            result = result.replace("{" + key + "}", value)
        return result

    def _clipboard_text(self) -> str:
        clipboard = QApplication.clipboard()
        return clipboard.text() if clipboard else ""

    def _set_clipboard_text(self, text: str) -> None:
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(text)

    def _launch(self, target: str, arguments: str) -> None:
        if not target:
            return

        parsed = urlparse(target)
        if parsed.scheme and len(parsed.scheme) > 1:
            os.startfile(target)
            return

        if os.path.exists(target):
            os.startfile(target)
            return

        command = [target]
        if arguments.strip():
            command.extend(shlex.split(arguments, posix=False))
        subprocess.Popen(command, shell=False)

    def _run_quicker_action(self, action_id: str, input_param: str, fallback_shortcut: str = "") -> None:
        action_id = action_id.strip()
        if not action_id and fallback_shortcut.strip():
            self._execute_shortcut(fallback_shortcut)
            return
        if not action_id:
            return

        uri = f"runaction:{action_id}"
        if input_param.strip():
            uri = f"{uri}?{quote(input_param, safe='')}"

        starter_path = self._find_quicker_starter()
        if starter_path:
            subprocess.Popen([starter_path, uri], shell=False)
            return

        os.startfile(f"quicker:{uri}")

    def _find_quicker_starter(self) -> str | None:
        from_registry = self._quicker_starter_from_registry()
        if from_registry:
            return from_registry

        for candidate in [
            shutil.which("QuickerStarter.exe"),
            r"C:\Program Files\Quicker\QuickerStarter.exe",
            r"C:\Program Files (x86)\Quicker\QuickerStarter.exe",
        ]:
            if candidate and os.path.exists(candidate):
                return candidate
        return None

    def _quicker_starter_from_registry(self) -> str | None:
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"quicker\shell\open\command") as key:
                command, _ = winreg.QueryValueEx(key, "")
        except OSError:
            return None

        parts = shlex.split(command, posix=False)
        if not parts:
            return None

        executable = parts[0].strip().strip('"')
        if os.path.exists(executable):
            return executable
        return None
