from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..models import Point
from .gesture_widgets import GesturePreview, draw_arrow_head, fit_points_to_box


class DrawCaptureWidget(QWidget):
    def __init__(self, points: list[Point] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.points: list[Point] = []
        self._initial_points = list(points or [])
        self._drawing = False
        self.setMinimumSize(560, 560)
        self.setStyleSheet("background:#F7F8FE;border:1px solid #E2E8F1;border-radius:10px;")

    def clear(self) -> None:
        self.points.clear()
        self._initial_points = []
        self.update()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._initial_points and not self.points:
            self.points = self._fit_points(self._initial_points)
            self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drawing = True
            self.points = [(event.position().x(), event.position().y())]
            self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drawing:
            point = (event.position().x(), event.position().y())
            if not self.points or point != self.points[-1]:
                self.points.append(point)
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drawing = False
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if len(self.points) < 2:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(QColor("#141A22"), 3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        start = QPointF(*self.points[0])
        for point in self.points[1:]:
            end = QPointF(*point)
            painter.drawLine(start, end)
            start = end
        draw_arrow_head(painter, QPointF(*self.points[-2]), QPointF(*self.points[-1]), QColor("#141A22"), size=16)

    def _fit_points(self, points: list[Point]) -> list[Point]:
        return fit_points_to_box(points, self.width(), self.height(), margin=60)


class RedrawDialog(QDialog):
    def __init__(self, name: str = "", points: list[Point] | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("重绘手势轨迹")
        self.resize(860, 700)

        self.canvas = DrawCaptureWidget(points)
        self.preview = GesturePreview(points or [])
        self.name_edit = QLineEdit(name)
        self.save_button = QPushButton("保存手势轨迹(S)")
        self.cancel_button = QPushButton("取消(C)")
        self.clear_button = QPushButton("清空")

        self.canvas.mouseReleaseEvent = self._wrap_mouse_release(self.canvas.mouseReleaseEvent)
        self.clear_button.clicked.connect(self._clear)
        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        side = QVBoxLayout()
        side.setSpacing(14)
        side.addWidget(self.preview, alignment=Qt.AlignmentFlag.AlignCenter)
        side.addWidget(QLabel("名称:"))
        side.addWidget(self.name_edit)
        side.addStretch(1)

        buttons = QHBoxLayout()
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.cancel_button)
        side.addLayout(buttons)

        root = QHBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(20)
        left = QVBoxLayout()
        left.addWidget(QLabel("请按住左键绘制手势轨迹:"))
        left.addWidget(self.canvas, stretch=1)
        left_buttons = QHBoxLayout()
        left_buttons.addWidget(self.clear_button)
        left_buttons.addStretch(1)
        left.addLayout(left_buttons)
        root.addLayout(left, stretch=1)
        root.addLayout(side)

    def _wrap_mouse_release(self, original):
        def handler(event):
            original(event)
            self.preview.set_points(self.canvas.points)

        return handler

    def _clear(self) -> None:
        self.canvas.clear()
        self.preview.set_points([])

    def accept(self) -> None:
        if len(self.canvas.points) < 4:
            QMessageBox.warning(self, "提示", "请先绘制一个有效的手势轨迹。")
            return
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "提示", "请填写手势名称。")
            return
        super().accept()

    def result_data(self) -> tuple[str, list[Point]]:
        return self.name_edit.text().strip(), list(self.canvas.points)
