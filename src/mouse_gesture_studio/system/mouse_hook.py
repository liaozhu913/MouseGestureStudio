from __future__ import annotations

import ctypes
import threading
import time

from PySide6.QtCore import QObject, Signal

from ..gesture.matcher import GestureMatcher, path_length
from ..models import AppSettings
from . import win32


class MouseHook(QObject):
    capture_started = Signal()
    gesture_triggered = Signal(object, float)
    gesture_unrecognized = Signal(float)
    hook_install_failed = Signal(str)

    def __init__(
        self,
        settings_provider: callable[[], AppSettings],
        click_passthrough: callable[[str], None],
    ) -> None:
        super().__init__()
        self._settings_provider = settings_provider
        self._click_passthrough = click_passthrough
        self._matcher = GestureMatcher()
        self._thread: threading.Thread | None = None
        self._state_lock = threading.Lock()
        self._hook_handle = None
        self._thread_id: int | None = None
        self._callback = None
        self._running = False
        self._capturing = False
        self._capture_button = "right"
        self._points: list[tuple[float, float]] = []
        self._last_emit = 0.0

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._message_loop, name="mouse-hook", daemon=True)
        self._thread.start()

    def is_capturing(self) -> bool:
        with self._state_lock:
            return self._capturing

    def stop(self) -> None:
        self._running = False
        if self._thread_id:
            win32.user32.PostThreadMessageW(self._thread_id, win32.WM_QUIT, 0, 0)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)

    def _message_loop(self) -> None:
        self._thread_id = win32.kernel32.GetCurrentThreadId()
        self._callback = win32.LowLevelMouseProc(self._mouse_proc)
        self._hook_handle = win32.user32.SetWindowsHookExW(
            win32.WH_MOUSE_LL,
            self._callback,
            None,
            0,
        )
        if not self._hook_handle:
            error = ctypes.get_last_error()
            self.hook_install_failed.emit(f"鼠标钩子安装失败，错误码 {error}")
            self._running = False
            return

        message = win32.MSG()
        while self._running:
            result = win32.user32.GetMessageW(ctypes.byref(message), None, 0, 0)
            if result == 0:
                break
            if result == -1:
                self.hook_install_failed.emit(f"鼠标消息循环失败，错误码 {ctypes.get_last_error()}")
                break
            win32.user32.TranslateMessage(ctypes.byref(message))
            win32.user32.DispatchMessageW(ctypes.byref(message))

        if self._hook_handle:
            win32.user32.UnhookWindowsHookEx(self._hook_handle)
            self._hook_handle = None

    def _mouse_proc(self, code: int, w_param: int, l_param: int):
        if code != win32.HC_ACTION:
            return win32.user32.CallNextHookEx(self._hook_handle, code, w_param, l_param)

        info = ctypes.cast(l_param, ctypes.POINTER(win32.MSLLHOOKSTRUCT)).contents
        if info.flags & win32.LLMHF_INJECTED:
            return win32.user32.CallNextHookEx(self._hook_handle, code, w_param, l_param)

        settings = self._settings_provider()
        if not settings.gestures_enabled:
            return win32.user32.CallNextHookEx(self._hook_handle, code, w_param, l_param)

        event_button = self._button_for_event(w_param, info.mouseData)
        if event_button == settings.trigger_button and self._is_button_down(w_param):
            with self._state_lock:
                self._capturing = True
                self._capture_button = event_button
                self._points = [(float(info.pt.x), float(info.pt.y))]
            self.capture_started.emit()
            return 1

        if self.is_capturing() and w_param == win32.WM_MOUSEMOVE:
            current = (float(info.pt.x), float(info.pt.y))
            with self._state_lock:
                if not self._points or current != self._points[-1]:
                    self._points.append(current)
            return 1

        if self.is_capturing() and event_button == self._capture_button and self._is_button_up(w_param):
            with self._state_lock:
                points = list(self._points)
                self._capturing = False
                self._points = []

            movement = path_length(points)
            if movement < settings.minimum_path_length:
                self._click_passthrough(self._capture_button)
                return 1

            enabled_templates = [gesture for gesture in settings.gestures if gesture.enabled]
            result = self._matcher.match(points, enabled_templates)
            if result.template and result.confidence >= settings.match_threshold:
                self.gesture_triggered.emit(result.template, result.confidence)
            elif time.time() - self._last_emit > 0.4:
                self._last_emit = time.time()
                self.gesture_unrecognized.emit(movement)
            return 1

        return win32.user32.CallNextHookEx(self._hook_handle, code, w_param, l_param)

    def _button_for_event(self, w_param: int, mouse_data: int) -> str | None:
        if w_param in {win32.WM_RBUTTONDOWN, win32.WM_RBUTTONUP}:
            return "right"
        if w_param in {win32.WM_MBUTTONDOWN, win32.WM_MBUTTONUP}:
            return "middle"
        if w_param in {win32.WM_XBUTTONDOWN, win32.WM_XBUTTONUP}:
            x_button = mouse_data >> 16
            if x_button == win32.XBUTTON1:
                return "x1"
            if x_button == win32.XBUTTON2:
                return "x2"
        return None

    @staticmethod
    def _is_button_down(w_param: int) -> bool:
        return w_param in {
            win32.WM_RBUTTONDOWN,
            win32.WM_MBUTTONDOWN,
            win32.WM_XBUTTONDOWN,
        }

    @staticmethod
    def _is_button_up(w_param: int) -> bool:
        return w_param in {
            win32.WM_RBUTTONUP,
            win32.WM_MBUTTONUP,
            win32.WM_XBUTTONUP,
        }
