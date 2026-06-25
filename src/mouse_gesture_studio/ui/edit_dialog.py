from __future__ import annotations

import json
import os
from pathlib import Path

from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QKeySequenceEdit,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..config import runtime_root
from ..constants import ACTION_KINDS, BUILTIN_ACTIONS, builtin_name
from ..models import ActionConfig, GestureTemplate
from .gesture_widgets import GesturePreview


WORKFLOW_STEP_KINDS = {
    "builtin",
    "choice",
    "clipboard",
    "date_picker",
    "delay",
    "foreach_line",
    "get_selected_text",
    "launch",
    "open_url",
    "open_urls",
    "paste",
    "set_var",
    "shortcut",
    "text",
}


class EditGestureDialog(QDialog):
    def __init__(self, gesture: GestureTemplate, parent=None) -> None:
        super().__init__(parent)
        self.gesture = gesture
        self.setWindowTitle("编辑手势动作")
        self.resize(720, 560)

        self.preview = GesturePreview(gesture.points)
        self.name_edit = QLineEdit(gesture.name)
        self.hint_edit = QLineEdit(gesture.hint)
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 600000)
        self.delay_spin.setSingleStep(100)
        self.delay_spin.setSuffix(" ms")
        self.delay_spin.setSpecialValueText("不延迟")
        self.show_hint_checkbox = QCheckBox("执行后显示提示")
        self.show_hint_checkbox.setChecked(gesture.action.show_hint)
        self.enabled_checkbox = QCheckBox("启用此手势")
        self.enabled_checkbox.setChecked(gesture.enabled)

        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self._build_action_tab(), "直接触发")
        self.tab_widget.addTab(self._build_placeholder_tab(), "按键触发")

        self.save_button = QPushButton("保存(S)")
        self.cancel_button = QPushButton("取消(C)")
        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        top = QHBoxLayout()
        top.setSpacing(18)
        top.addWidget(QLabel("手势轨迹"))
        top.addWidget(self.preview)
        top.addStretch(1)

        form = QFormLayout()
        form.addRow("操作名称", self.name_edit)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.cancel_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)
        layout.addLayout(top)
        layout.addLayout(form)
        layout.addWidget(self.tab_widget)
        layout.addLayout(buttons)

        self._load_action(gesture.action)

    def _build_action_tab(self) -> QWidget:
        tab = QWidget()
        self.kind_combo = QComboBox()
        for value, label in ACTION_KINDS:
            self.kind_combo.addItem(label, value)

        self.action_stack = QStackedWidget()
        self.builtin_combo = QComboBox()
        for action in BUILTIN_ACTIONS:
            self.builtin_combo.addItem(action["name"], action["id"])

        builtin_page = QWidget()
        builtin_form = QFormLayout(builtin_page)
        builtin_form.addRow("功能(操作)", self.builtin_combo)

        self.shortcut_edit = QKeySequenceEdit()
        self.shortcut_edit.setMaximumSequenceLength(4)
        shortcut_page = QWidget()
        shortcut_form = QFormLayout(shortcut_page)
        shortcut_form.addRow("按键组合", self.shortcut_edit)

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("输入手势触发后要自动键入的文本")
        text_page = QWidget()
        text_form = QFormLayout(text_page)
        text_form.addRow("键入内容", self.text_edit)

        self.target_edit = QLineEdit()
        self.args_edit = QLineEdit()
        browse_button = QPushButton("浏览...")
        browse_button.clicked.connect(self._browse_target)
        launch_row = QHBoxLayout()
        launch_row.addWidget(self.target_edit)
        launch_row.addWidget(browse_button)
        launch_target = QWidget()
        launch_target.setLayout(launch_row)
        launch_page = QWidget()
        launch_form = QFormLayout(launch_page)
        launch_form.addRow("目标", launch_target)
        launch_form.addRow("参数", self.args_edit)

        self.workflow_edit = QTextEdit()
        self.workflow_edit.setPlaceholderText(
            "例如：\n"
            "[\n"
            "  {\"kind\":\"date_picker\",\"paste\":true}\n"
            "]"
        )
        workflow_page = QWidget()
        workflow_form = QFormLayout(workflow_page)
        workflow_form.addRow("步骤 JSON", self.workflow_edit)
        import_workflow_button = QPushButton("导入 JSON...")
        format_workflow_button = QPushButton("格式化/校验")
        open_workflow_doc_button = QPushButton("打开规则文档")
        import_workflow_button.clicked.connect(self._import_workflow_json)
        format_workflow_button.clicked.connect(self._format_workflow_json)
        open_workflow_doc_button.clicked.connect(self._open_workflow_doc)
        workflow_button_row = QHBoxLayout()
        workflow_button_row.addWidget(import_workflow_button)
        workflow_button_row.addWidget(format_workflow_button)
        workflow_button_row.addWidget(open_workflow_doc_button)
        workflow_button_row.addStretch(1)
        workflow_buttons = QWidget()
        workflow_buttons.setLayout(workflow_button_row)
        workflow_form.addRow("", workflow_buttons)
        workflow_note = QLabel(
            "支持 kind: date_picker、choice、shortcut、text、clipboard、paste、delay、launch、builtin。\n"
            "也支持 open_url、open_urls、get_selected_text、foreach_line、set_var。\n"
            "可以让 AI 按 docs/workflow_json_spec.md 的规则生成 JSON 后粘贴或导入到这里。"
        )
        workflow_note.setWordWrap(True)
        workflow_note.setStyleSheet("color:#677487;padding-top:4px;")
        workflow_form.addRow("", workflow_note)

        self.action_stack.addWidget(builtin_page)
        self.action_stack.addWidget(shortcut_page)
        self.action_stack.addWidget(text_page)
        self.action_stack.addWidget(launch_page)
        self.action_stack.addWidget(workflow_page)

        self.kind_combo.currentIndexChanged.connect(self._sync_action_page)

        form = QFormLayout()
        form.addRow("操作类型", self.kind_combo)
        form.addRow(self.action_stack)
        form.addRow("触发后延迟", self.delay_spin)
        form.addRow("触发后提示", self.hint_edit)
        form.addRow("", self.show_hint_checkbox)
        form.addRow("", self.enabled_checkbox)

        wrapper = QVBoxLayout(tab)
        wrapper.addLayout(form)
        wrapper.addStretch(1)
        return tab

    def _build_placeholder_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        note = QLabel("当前版本优先实现直接触发。需要复杂组合键时，可先通过“发送快捷键”覆盖大多数场景。")
        note.setWordWrap(True)
        note.setStyleSheet("color:#677487;padding:12px;")
        layout.addWidget(note)
        layout.addStretch(1)
        return tab

    def _sync_action_page(self) -> None:
        mapping = {
            "builtin": 0,
            "shortcut": 1,
            "text": 2,
            "launch": 3,
            "workflow": 4,
        }
        kind = self.kind_combo.currentData()
        self.action_stack.setCurrentIndex(mapping.get(kind, 0))

    def _browse_target(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择文件")
        if path:
            self.target_edit.setText(path)

    def _import_workflow_json(self) -> None:
        start_dir = self._workflow_examples_dir()
        path, _ = QFileDialog.getOpenFileName(
            self,
            "导入组合动作 JSON",
            str(start_dir),
            "JSON 文件 (*.json);;所有文件 (*.*)",
        )
        if not path:
            return

        try:
            payload = Path(path).read_text(encoding="utf-8-sig")
            parsed = json.loads(payload)
            self._validate_workflow(parsed)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            QMessageBox.warning(self, "提示", f"导入失败：{exc}")
            return

        self.workflow_edit.setPlainText(json.dumps(parsed, ensure_ascii=False, indent=2))
        if isinstance(parsed, dict) and parsed.get("name") and not self.name_edit.text().strip():
            self.name_edit.setText(str(parsed["name"]))
        QMessageBox.information(self, "提示", "组合动作 JSON 已导入并通过基础校验。")

    def _format_workflow_json(self) -> None:
        try:
            parsed = self._parse_workflow_json()
            self._validate_workflow(parsed)
        except (ValueError, json.JSONDecodeError) as exc:
            QMessageBox.warning(self, "提示", f"组合动作 JSON 格式错误：{exc}")
            return

        self.workflow_edit.setPlainText(json.dumps(parsed, ensure_ascii=False, indent=2))
        QMessageBox.information(self, "提示", "JSON 已格式化，基础校验通过。")

    def _open_workflow_doc(self) -> None:
        for path in self._workflow_doc_candidates():
            if path.exists():
                os.startfile(path)
                return
        QMessageBox.warning(self, "提示", "没有找到 docs/workflow_json_spec.md，请确认项目文档是否存在。")

    def _workflow_examples_dir(self) -> Path:
        candidates = [
            runtime_root() / "docs" / "examples",
            runtime_root() / "_internal" / "docs" / "examples",
            Path.cwd() / "docs" / "examples",
        ]
        source_root = Path(__file__).resolve().parents[3]
        candidates.append(source_root / "docs" / "examples")
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return Path.home()

    def _workflow_doc_candidates(self) -> list[Path]:
        source_root = Path(__file__).resolve().parents[3]
        return [
            runtime_root() / "docs" / "workflow_json_spec.md",
            runtime_root() / "_internal" / "docs" / "workflow_json_spec.md",
            Path.cwd() / "docs" / "workflow_json_spec.md",
            source_root / "docs" / "workflow_json_spec.md",
        ]

    def _load_action(self, action: ActionConfig) -> None:
        kind_index = max(self.kind_combo.findData(action.kind), 0)
        self.kind_combo.setCurrentIndex(kind_index)

        builtin_index = max(self.builtin_combo.findData(action.builtin_name), 0)
        self.builtin_combo.setCurrentIndex(builtin_index)

        self.shortcut_edit.setKeySequence(QKeySequence(action.shortcut))
        self.text_edit.setPlainText(action.text)
        self.target_edit.setText(action.target)
        self.args_edit.setText(action.arguments)
        self.workflow_edit.setPlainText(action.workflow)
        self.delay_spin.setValue(action.delay_ms)
        self._sync_action_page()

    def accept(self) -> None:
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "提示", "请填写操作名称。")
            return

        kind = self.kind_combo.currentData()
        if kind == "shortcut" and not self.shortcut_edit.keySequence().toString():
            QMessageBox.warning(self, "提示", "请录入一个快捷键组合。")
            return

        if kind == "launch" and not self.target_edit.text().strip():
            QMessageBox.warning(self, "提示", "请填写要打开或运行的目标。")
            return

        if kind == "workflow":
            try:
                parsed = self._parse_workflow_json()
                self._validate_workflow(parsed)
            except (ValueError, json.JSONDecodeError) as exc:
                QMessageBox.warning(self, "提示", f"组合动作 JSON 格式错误：{exc}")
                return

        super().accept()

    def result_action(self) -> tuple[str, ActionConfig, str, bool]:
        kind = self.kind_combo.currentData()
        target = self.target_edit.text().strip()
        arguments = self.args_edit.text().strip()
        shortcut = self.shortcut_edit.keySequence().toString(
            QKeySequence.SequenceFormat.PortableText
        )

        action = ActionConfig(
            kind=kind,
            builtin_name=self.builtin_combo.currentData(),
            shortcut=shortcut,
            text=self.text_edit.toPlainText(),
            target=target,
            arguments=arguments,
            workflow=self.workflow_edit.toPlainText(),
            delay_ms=self.delay_spin.value(),
            show_hint=self.show_hint_checkbox.isChecked(),
        )

        hint = self.hint_edit.text().strip()
        if not hint and kind == "builtin":
            hint = builtin_name(action.builtin_name)
        if not hint and kind == "workflow":
            hint = "已执行组合动作"
        return self.name_edit.text().strip(), action, hint, self.enabled_checkbox.isChecked()

    def _parse_workflow_json(self) -> list | dict:
        text = self.workflow_edit.toPlainText().strip()
        if not text:
            raise ValueError("组合动作 JSON 不能为空。")
        parsed = json.loads(text)
        if not isinstance(parsed, (list, dict)):
            raise ValueError("组合动作必须是步骤数组，或包含 steps 数组的对象。")
        return parsed

    def _validate_workflow(self, parsed: list | dict) -> None:
        steps = parsed
        if isinstance(parsed, dict):
            steps = parsed.get("steps", [])
        if isinstance(steps, dict):
            steps = steps.get("steps", [])
        if not isinstance(steps, list):
            raise ValueError("顶层 steps 必须是数组。")
        self._validate_workflow_steps(steps)

    def _validate_workflow_steps(self, steps: list, prefix: str = "steps") -> None:
        for index, step in enumerate(steps, 1):
            if not isinstance(step, dict):
                raise ValueError(f"{prefix}[{index}] 必须是对象。")
            kind = str(step.get("kind", "")).strip()
            if not kind:
                raise ValueError(f"{prefix}[{index}] 缺少 kind。")
            if kind not in WORKFLOW_STEP_KINDS:
                raise ValueError(f"{prefix}[{index}] 使用了未支持的 kind：{kind}")
            if kind in {"foreach_line", "choice"} and "steps" in step:
                child_steps = step.get("steps")
                if not isinstance(child_steps, list):
                    raise ValueError(f"{prefix}[{index}].steps 必须是数组。")
                self._validate_workflow_steps(child_steps, f"{prefix}[{index}].steps")
