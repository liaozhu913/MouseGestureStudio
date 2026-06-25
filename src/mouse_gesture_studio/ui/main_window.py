from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QCloseEvent, QCursor, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from ..config import ConfigManager, resource_path
from ..constants import TRIGGER_BUTTONS
from ..models import ActionConfig, AppSettings, GestureTemplate
from ..system import ActionExecutor, MouseHook
from ..system import win32
from ..system.startup import has_startup_entry, is_startup_enabled, set_startup_enabled
from .edit_dialog import EditGestureDialog
from .gesture_overlay import GestureOverlay
from .gesture_widgets import GestureCard
from .redraw_dialog import RedrawDialog


class MainWindow(QMainWindow):
    def __init__(self, config_manager: ConfigManager) -> None:
        super().__init__()
        self.config_manager = config_manager
        self.settings = config_manager.settings
        self.selected_id: str | None = None
        self.cards: dict[str, GestureCard] = {}
        self.capture_path_points: list[tuple[float, float]] = []
        self._capture_timer_active = False

        self.setWindowTitle(f"MouseGestureStudio {__version__}")
        self.setWindowIcon(QIcon(str(resource_path("assets", "logo.ico"))))
        self.resize(1180, 780)
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background: #EEF3F0;
                color: #15211D;
                font-family: "Microsoft YaHei UI", "Segoe UI Variable Display";
                font-size: 14px;
            }
            QFrame#HeroCard {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #16382F, stop:0.55 #24584A, stop:1 #D9895B);
                border: 0;
                border-radius: 24px;
            }
            QLabel#HeroTitle {
                background: transparent;
                color: #FFF7EC;
                font-size: 30px;
                font-weight: 800;
                letter-spacing: 0.4px;
            }
            QLabel#HeroSubtitle {
                background: transparent;
                color: #D8EEE5;
                font-size: 14px;
                line-height: 1.4;
            }
            QLabel#HeroBadge {
                background: rgba(255, 247, 236, 0.16);
                color: #FFF7EC;
                border: 1px solid rgba(255, 247, 236, 0.26);
                border-radius: 14px;
                padding: 7px 12px;
                font-size: 12px;
            }
            QFrame#Panel {
                background: transparent;
                border: 0;
            }
            QPushButton {
                background: #FFFFFF;
                border: 1px solid #D4DED8;
                border-radius: 13px;
                padding: 10px 15px;
                font-weight: 600;
            }
            QPushButton:hover { border-color: #D9895B; background: #FFF8F1; }
            QPushButton#PrimaryButton {
                background: #E8754F;
                color: white;
                border: 1px solid #E8754F;
            }
            QPushButton#PrimaryButton:hover { background: #D76542; }
            QComboBox, QLineEdit, QTextEdit {
                background: #FFFFFF;
                border: 1px solid #D4DED8;
                border-radius: 10px;
                padding: 8px;
            }
            QCheckBox { background: transparent; spacing: 7px; }
            QLabel { background: transparent; }
            QScrollArea { background: transparent; }
            QStatusBar { background: transparent; color: #68766F; }
            """
        )

        self.executor = ActionExecutor(self._notify)
        self.mouse_hook = MouseHook(self._current_settings, self.executor.click_button)
        self.mouse_hook.capture_started.connect(self._ensure_capture_timer)
        self.mouse_hook.gesture_triggered.connect(self._on_gesture_triggered)
        self.mouse_hook.gesture_unrecognized.connect(self._on_unrecognized)
        self.mouse_hook.hook_install_failed.connect(self._on_hook_install_failed)

        self.capture_overlay = GestureOverlay()
        self.capture_timer = QTimer(self)
        self.capture_timer.setInterval(33)
        self.capture_timer.timeout.connect(self._tick_capture_overlay)

        self.tray_icon = self._create_tray_icon()

        self.enable_checkbox = QCheckBox("默认启用手势")
        self.enable_checkbox.setChecked(self.settings.gestures_enabled)
        self.enable_checkbox.stateChanged.connect(self._save_general_settings)

        self.startup_checkbox = QCheckBox("开机启动")
        self.startup_checkbox.setChecked(self._startup_enabled())
        self.settings.start_on_boot = self.startup_checkbox.isChecked()
        self.startup_checkbox.stateChanged.connect(self._save_startup_setting)

        self.trigger_combo = QComboBox()
        for value, label in TRIGGER_BUTTONS:
            self.trigger_combo.addItem(label, value)
        self.trigger_combo.setCurrentIndex(max(self.trigger_combo.findData(self.settings.trigger_button), 0))
        self.trigger_combo.currentIndexChanged.connect(self._save_general_settings)

        self.add_button = QPushButton("添加手势轨迹")
        self.add_button.setObjectName("PrimaryButton")
        self.import_button = QPushButton("导入存档")
        self.export_button = QPushButton("导出存档")
        self.edit_button = QPushButton("编辑动作")
        self.redraw_button = QPushButton("重绘轨迹")
        self.copy_button = QPushButton("复制")
        self.delete_button = QPushButton("删除")
        self.apply_button = QPushButton("应用设置")

        self.add_button.clicked.connect(self._add_gesture)
        self.import_button.clicked.connect(self._import_archive)
        self.export_button.clicked.connect(self._export_archive)
        self.edit_button.clicked.connect(self._edit_selected)
        self.redraw_button.clicked.connect(self._redraw_selected)
        self.copy_button.clicked.connect(self._duplicate_selected)
        self.delete_button.clicked.connect(self._delete_selected)
        self.apply_button.clicked.connect(self._persist)

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(4, 4, 4, 4)
        self.grid_layout.setHorizontalSpacing(18)
        self.grid_layout.setVerticalSpacing(18)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll.setWidget(self.grid_container)

        help_label = QLabel("双击动作卡片可编辑；按住触发键绘制手势，松开后执行匹配动作。组合动作支持导入 AI 生成的 JSON。")
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color:#68766F;padding:4px 2px;")

        hero = QFrame()
        hero.setObjectName("HeroCard")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(28, 24, 28, 24)
        hero_layout.setSpacing(22)

        title_col = QVBoxLayout()
        title_col.setSpacing(7)
        title = QLabel("MouseGestureStudio")
        title.setObjectName("HeroTitle")
        subtitle = QLabel("一个可运行 AI 生成 JSON 动作的鼠标手势壳：手势、选择器、批量网址、快捷键和组合步骤都能收进你的动作库。")
        subtitle.setObjectName("HeroSubtitle")
        subtitle.setWordWrap(True)
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        hero_layout.addLayout(title_col, stretch=1)

        self.count_label = QLabel()
        self.count_label.setObjectName("HeroBadge")
        self.trigger_label = QLabel()
        self.trigger_label.setObjectName("HeroBadge")
        hero_layout.addWidget(self.count_label)
        hero_layout.addWidget(self.trigger_label)

        control_panel = QFrame()
        control_panel.setObjectName("Panel")
        control_layout = QHBoxLayout(control_panel)
        control_layout.setContentsMargins(4, 2, 4, 2)
        control_layout.setSpacing(12)
        control_layout.addWidget(self.enable_checkbox)
        control_layout.addWidget(self.startup_checkbox)
        control_layout.addWidget(QLabel("触发键"))
        control_layout.addWidget(self.trigger_combo)
        control_layout.addStretch(1)
        control_layout.addWidget(self.import_button)
        control_layout.addWidget(self.export_button)
        control_layout.addWidget(self.add_button)

        bottom_bar = QHBoxLayout()
        bottom_bar.addWidget(self.copy_button)
        bottom_bar.addWidget(self.delete_button)
        bottom_bar.addStretch(1)
        bottom_bar.addWidget(self.edit_button)
        bottom_bar.addWidget(self.redraw_button)
        bottom_bar.addWidget(self.apply_button)

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(22, 22, 22, 18)
        layout.setSpacing(14)
        layout.addWidget(hero)
        layout.addWidget(control_panel)
        layout.addWidget(self.scroll, stretch=1)
        layout.addWidget(help_label)
        layout.addLayout(bottom_bar)
        self.setCentralWidget(root)

        self._refresh_cards()
        self.mouse_hook.start()
        self.tray_icon.show()
        self._warn_if_not_admin()

    def _create_tray_icon(self) -> QSystemTrayIcon:
        tray = QSystemTrayIcon(self)
        tray.setToolTip(f"MouseGestureStudio {__version__}")
        tray.setIcon(QIcon(str(resource_path("assets", "logo.ico"))))

        menu = QMenu()
        show_action = QAction("显示主界面", self)
        quit_action = QAction("退出", self)
        show_action.triggered.connect(self.showNormal)
        quit_action.triggered.connect(self._quit_app)
        menu.addAction(show_action)
        menu.addSeparator()
        menu.addAction(quit_action)

        tray.setContextMenu(menu)
        tray.activated.connect(self._on_tray_activated)
        return tray

    def _on_tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.showNormal()
            self.raise_()
            self.activateWindow()

    def _current_settings(self):
        return self.settings

    def _save_general_settings(self) -> None:
        self.settings.gestures_enabled = self.enable_checkbox.isChecked()
        self.settings.trigger_button = self.trigger_combo.currentData()
        self._update_header_stats()
        self._persist()

    def _save_startup_setting(self) -> None:
        enabled = self.startup_checkbox.isChecked()
        try:
            set_startup_enabled(enabled)
        except OSError as exc:
            self.startup_checkbox.blockSignals(True)
            self.startup_checkbox.setChecked(not enabled)
            self.startup_checkbox.blockSignals(False)
            QMessageBox.warning(self, "开机启动设置失败", f"无法写入开机启动项：{exc}")
            return
        self.settings.start_on_boot = enabled
        self._persist()

    def _startup_enabled(self) -> bool:
        registry_enabled = is_startup_enabled()
        if self.settings.start_on_boot and not registry_enabled:
            try:
                set_startup_enabled(True)
                return True
            except OSError:
                pass
        if not self.settings.start_on_boot and has_startup_entry():
            self.settings.start_on_boot = True
            return True
        if self.settings.start_on_boot != registry_enabled:
            self.settings.start_on_boot = registry_enabled
        return registry_enabled

    def _persist(self) -> None:
        self.config_manager.save(self.settings)
        self.statusBar().showMessage("设置已保存", 2500)

    def _refresh_cards(self) -> None:
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.cards.clear()

        columns = self._card_columns()
        for index, gesture in enumerate(self.settings.gestures):
            card = GestureCard(gesture)
            card.clicked.connect(self._select_gesture)
            card.double_clicked.connect(self._open_edit_for_gesture)
            row, col = divmod(index, columns)
            self.grid_layout.addWidget(card, row, col)
            self.cards[gesture.id] = card

        if self.settings.gestures and self.selected_id not in self.cards:
            self.selected_id = self.settings.gestures[0].id
        self._update_header_stats()
        self._update_selection_styles()

    def _card_columns(self) -> int:
        viewport_width = self.scroll.viewport().width() if hasattr(self, "scroll") else self.width()
        card_width = 184
        return max(1, viewport_width // card_width)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        QTimer.singleShot(0, self._relayout_cards)

    def _relayout_cards(self) -> None:
        if not self.cards:
            return
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
        columns = self._card_columns()
        for column in range(max(columns, 1)):
            self.grid_layout.setColumnStretch(column, 0)
        for index, gesture in enumerate(self.settings.gestures):
            card = self.cards.get(gesture.id)
            if not card:
                continue
            row, col = divmod(index, columns)
            self.grid_layout.addWidget(card, row, col)
        self.grid_layout.setColumnStretch(columns, 1)

    def _select_gesture(self, gesture: GestureTemplate) -> None:
        self.selected_id = gesture.id
        self._update_selection_styles()

    def _update_selection_styles(self) -> None:
        for gesture_id, card in self.cards.items():
            card.set_selected(gesture_id == self.selected_id)

    def _selected_gesture(self) -> GestureTemplate | None:
        if not self.selected_id:
            return None
        for gesture in self.settings.gestures:
            if gesture.id == self.selected_id:
                return gesture
        return None

    def _add_gesture(self) -> None:
        dialog = RedrawDialog("新建手势", parent=self)
        if dialog.exec():
            name, points = dialog.result_data()
            gesture = GestureTemplate(
                id=f"gesture-{uuid.uuid4().hex[:8]}",
                name=name,
                points=points,
                action=ActionConfig(),
                hint=name,
            )
            edit_dialog = EditGestureDialog(gesture, self)
            if edit_dialog.exec():
                gesture.name, gesture.action, gesture.hint, gesture.enabled = edit_dialog.result_action()
                self.settings.gestures.append(gesture)
                self.selected_id = gesture.id
                self._refresh_cards()
                self._persist()

    def _open_edit_for_gesture(self, gesture: GestureTemplate) -> None:
        self.selected_id = gesture.id
        self._update_selection_styles()
        self._edit_selected()

    def _edit_selected(self) -> None:
        gesture = self._selected_gesture()
        if not gesture:
            return
        dialog = EditGestureDialog(gesture, self)
        if dialog.exec():
            gesture.name, gesture.action, gesture.hint, gesture.enabled = dialog.result_action()
            self.cards[gesture.id].refresh(gesture)
            self._update_selection_styles()
            self._persist()

    def _redraw_selected(self) -> None:
        gesture = self._selected_gesture()
        if not gesture:
            return
        dialog = RedrawDialog(gesture.name, gesture.points, self)
        if dialog.exec():
            gesture.name, gesture.points = dialog.result_data()
            self.cards[gesture.id].refresh(gesture)
            self._persist()

    def _duplicate_selected(self) -> None:
        gesture = self._selected_gesture()
        if not gesture:
            return
        clone = GestureTemplate.from_dict(gesture.to_dict())
        clone.id = f"gesture-{uuid.uuid4().hex[:8]}"
        clone.name = f"{gesture.name} 副本"
        self.settings.gestures.append(clone)
        self.selected_id = clone.id
        self._refresh_cards()
        self._persist()

    def _export_archive(self) -> None:
        default_name = f"MouseGestureStudio-actions-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        default_path = Path.home() / "Desktop" / default_name
        if not default_path.parent.exists():
            default_path = Path.home() / default_name
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出动作存档",
            str(default_path),
            "MouseGestureStudio 存档 (*.json);;所有文件 (*.*)",
        )
        if not path:
            return

        payload = {
            "format": "MouseGestureStudio.archive",
            "archive_version": 1,
            "exported_at": datetime.now().isoformat(timespec="seconds"),
            "app_version": __version__,
            "settings": self.settings.to_dict(),
        }
        try:
            Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, "导出失败", f"无法写入存档：{exc}")
            return
        self.statusBar().showMessage(f"已导出动作存档：{path}", 4000)

    def _import_archive(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "导入动作存档",
            str(Path.home()),
            "MouseGestureStudio 存档 (*.json);;所有文件 (*.*)",
        )
        if not path:
            return

        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
            imported = self._settings_from_archive(payload)
        except (OSError, ValueError, json.JSONDecodeError, KeyError) as exc:
            QMessageBox.warning(self, "导入失败", f"无法读取动作存档：{exc}")
            return

        answer = QMessageBox.question(
            self,
            "导入方式",
            "选择“是”会合并到当前动作库；选择“否”会用存档替换当前全部动作。",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes,
        )
        if answer == QMessageBox.StandardButton.Cancel:
            return
        if answer == QMessageBox.StandardButton.Yes:
            imported_count = self._merge_settings(imported)
            message = f"已合并导入 {imported_count} 个动作。"
        else:
            self.settings = imported
            self._sync_general_controls()
            message = f"已替换为存档中的 {len(self.settings.gestures)} 个动作。"

        self._refresh_cards()
        self._persist()
        self.statusBar().showMessage(message, 4000)
        self._notify("MouseGestureStudio", message)

    def _settings_from_archive(self, payload) -> AppSettings:
        if isinstance(payload, dict) and isinstance(payload.get("settings"), dict):
            return AppSettings.from_dict(payload["settings"])
        if isinstance(payload, dict) and isinstance(payload.get("gestures"), list):
            return AppSettings.from_dict(payload)
        if isinstance(payload, list):
            return AppSettings(gestures=[GestureTemplate.from_dict(item) for item in payload])
        raise ValueError("不支持的存档格式。")

    def _merge_settings(self, imported: AppSettings) -> int:
        existing_ids = {gesture.id for gesture in self.settings.gestures}
        for gesture in imported.gestures:
            clone = GestureTemplate.from_dict(gesture.to_dict())
            if clone.id in existing_ids:
                clone.id = f"gesture-{uuid.uuid4().hex[:8]}"
            existing_ids.add(clone.id)
            self.settings.gestures.append(clone)
        return len(imported.gestures)

    def _sync_general_controls(self) -> None:
        self.enable_checkbox.blockSignals(True)
        self.startup_checkbox.blockSignals(True)
        self.trigger_combo.blockSignals(True)
        self.enable_checkbox.setChecked(self.settings.gestures_enabled)
        self.startup_checkbox.setChecked(self._startup_enabled())
        self.trigger_combo.setCurrentIndex(max(self.trigger_combo.findData(self.settings.trigger_button), 0))
        self.enable_checkbox.blockSignals(False)
        self.startup_checkbox.blockSignals(False)
        self.trigger_combo.blockSignals(False)

    def _update_header_stats(self) -> None:
        enabled_count = sum(1 for gesture in self.settings.gestures if gesture.enabled)
        self.count_label.setText(f"{enabled_count}/{len(self.settings.gestures)} 个动作启用")
        self.trigger_label.setText(f"触发键：{self.trigger_combo.currentText()}")

    def _delete_selected(self) -> None:
        gesture = self._selected_gesture()
        if not gesture:
            return
        if len(self.settings.gestures) <= 1:
            QMessageBox.warning(self, "提示", "至少保留一个手势模板。")
            return
        answer = QMessageBox.question(self, "删除确认", f"确认删除手势“{gesture.name}”吗？")
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.settings.gestures = [item for item in self.settings.gestures if item.id != gesture.id]
        self.selected_id = self.settings.gestures[0].id if self.settings.gestures else None
        self._refresh_cards()
        self._persist()

    def _tick_capture_overlay(self) -> None:
        if not self.mouse_hook.is_capturing():
            if self.capture_path_points:
                self.capture_path_points = []
                self.capture_overlay.clear()
            if self.capture_timer.isActive():
                self.capture_timer.stop()
            self._capture_timer_active = False
            return

        cursor = QCursor.pos()
        point = (float(cursor.x()), float(cursor.y()))
        if not self.capture_path_points or point != self.capture_path_points[-1]:
            self.capture_path_points.append(point)
        self.capture_overlay.show_points(self.capture_path_points)

    def _on_hook_install_failed(self, message: str) -> None:
        self.enable_checkbox.setChecked(False)
        self.settings.gestures_enabled = False
        self.statusBar().showMessage(message, 6000)
        self._notify("MouseGestureStudio", message)

    def _on_gesture_triggered(self, gesture: GestureTemplate, confidence: float) -> None:
        if gesture.action.delay_ms > 0:
            action = ActionConfig.from_dict(gesture.action.to_dict())
            action.delay_ms = 0
            hint = gesture.hint or gesture.name
            QTimer.singleShot(
                gesture.action.delay_ms,
                lambda action=action, hint=hint: self.executor.execute(
                    action,
                    hint,
                    respect_delay=False,
                ),
            )
            self.statusBar().showMessage(
                f"已触发: {gesture.name}，{gesture.action.delay_ms}ms 后执行 ({confidence:.0%})",
                2500,
            )
            return

        self.executor.execute(gesture.action, gesture.hint or gesture.name)
        self.statusBar().showMessage(f"已触发: {gesture.name} ({confidence:.0%})", 2500)

    def _on_unrecognized(self, movement: float) -> None:
        self.statusBar().showMessage(f"未识别的手势，轨迹长度 {movement:.0f}", 2000)

    def _ensure_capture_timer(self) -> None:
        if not self.capture_timer.isActive():
            self.capture_timer.start()
        self._capture_timer_active = True

    def _notify(self, title: str, message: str) -> None:
        self.tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 1800)

    def _warn_if_not_admin(self) -> None:
        if win32.is_user_admin():
            return
        message = "当前未以管理员运行；在管理员权限软件上可能无法触发手势。安装版会请求管理员权限以增强全局覆盖。"
        self.statusBar().showMessage(message, 8000)
        self.tray_icon.showMessage(
            "MouseGestureStudio",
            message,
            QSystemTrayIcon.MessageIcon.Information,
            3000,
        )

    def _quit_app(self) -> None:
        self.capture_overlay.clear()
        self.mouse_hook.stop()
        self.tray_icon.hide()
        self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.tray_icon.isVisible():
            self.hide()
            self.tray_icon.showMessage(
                "MouseGestureStudio",
                "程序已最小化到托盘，右击托盘图标可退出。",
                QSystemTrayIcon.MessageIcon.Information,
                1800,
            )
            event.ignore()
            return
        super().closeEvent(event)
