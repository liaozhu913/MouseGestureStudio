from __future__ import annotations

import math

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from ..constants import ACTION_KINDS, builtin_name
from ..models import GestureTemplate, Point


ACTION_KIND_LABELS = dict(ACTION_KINDS)


def fit_points_to_box(
    points: list[Point],
    width: int,
    height: int,
    margin: int = 12,
) -> list[Point]:
    if not points:
        return []

    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max(max_x - min_x, 1e-6)
    span_y = max(max_y - min_y, 1e-6)
    usable_w = max(width - margin * 2, 1)
    usable_h = max(height - margin * 2, 1)
    scale = min(usable_w / span_x, usable_h / span_y)
    scaled_w = span_x * scale
    scaled_h = span_y * scale
    offset_x = (width - scaled_w) / 2 - min_x * scale
    offset_y = (height - scaled_h) / 2 - min_y * scale
    return [(x * scale + offset_x, y * scale + offset_y) for x, y in points]


def build_path(points: list[Point], width: int, height: int, margin: int = 12) -> QPainterPath:
    path = QPainterPath()
    mapped = fit_points_to_box(points, width, height, margin)
    if not mapped:
        return path

    start = QPointF(*mapped[0])
    path.moveTo(start)
    for point in mapped[1:]:
        path.lineTo(QPointF(*point))
    return path


def draw_arrow_head(
    painter: QPainter,
    start: QPointF,
    end: QPointF,
    color: QColor,
    size: float = 12.0,
) -> None:
    dx = end.x() - start.x()
    dy = end.y() - start.y()
    length = math.hypot(dx, dy)
    if length < 1e-6:
        return

    ux = dx / length
    uy = dy / length
    px = -uy
    py = ux

    tip = end
    left = QPointF(
        end.x() - ux * size + px * size * 0.45,
        end.y() - uy * size + py * size * 0.45,
    )
    right = QPointF(
        end.x() - ux * size - px * size * 0.45,
        end.y() - uy * size - py * size * 0.45,
    )

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawPolygon([tip, left, right])


class GesturePreview(QWidget):
    def __init__(self, points: list[Point] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._points = points or []
        self.setMinimumSize(88, 88)
        self.setMaximumSize(120, 120)

    def set_points(self, points: list[Point]) -> None:
        self._points = list(points)
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), QColor("#F8FBF7"))
        painter.setPen(QPen(QColor("#DDE8E1"), 1))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 18, 18)

        if len(self._points) < 2:
            return

        path = build_path(self._points, self.width(), self.height())
        pen = QPen(QColor("#E8754F"), 3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPath(path)
        mapped = fit_points_to_box(self._points, self.width(), self.height())
        if len(mapped) >= 2:
            draw_arrow_head(
                painter,
                QPointF(*mapped[-2]),
                QPointF(*mapped[-1]),
                QColor("#E8754F"),
                size=11,
            )


class GestureCard(QFrame):
    clicked = Signal(object)
    double_clicked = Signal(object)

    def __init__(self, gesture: GestureTemplate, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("GestureCard")
        self.gesture = gesture
        self.preview = GesturePreview(gesture.points)
        self.name_label = QLabel(gesture.name)
        self.hint_label = QLabel(gesture.hint or "未设置提示")
        self.kind_label = QLabel(self._action_summary(gesture))

        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.kind_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setStyleSheet("font-size:15px;font-weight:800;background:transparent;")
        self.hint_label.setStyleSheet("color:#738178;font-size:12px;background:transparent;")
        self.kind_label.setStyleSheet(
            "color:#315247;background:#EAF3EE;border:1px solid #D6E3DC;"
            "border-radius:10px;padding:5px 9px;font-size:12px;font-weight:700;"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        layout.addWidget(self.preview, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.kind_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.name_label)
        layout.addWidget(self.hint_label)

        self.set_selected(False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedWidth(164)
        self.setMinimumHeight(230)

    def refresh(self, gesture: GestureTemplate) -> None:
        self.gesture = gesture
        self.preview.set_points(gesture.points)
        self.name_label.setText(gesture.name)
        self.hint_label.setText(gesture.hint or "未设置提示")
        self.kind_label.setText(self._action_summary(gesture))

    def set_selected(self, selected: bool) -> None:
        border = "#E8754F" if selected else "#D8E4DD"
        background = "#FFF4EC" if selected else "#FFFFFF"
        title_color = "#16231F" if self.gesture.enabled else "#8B9891"
        hint_color = "#738178" if self.gesture.enabled else "#9AA59F"
        self.name_label.setStyleSheet(
            f"color:{title_color};font-size:15px;font-weight:800;background:transparent;"
        )
        self.hint_label.setStyleSheet(f"color:{hint_color};font-size:12px;background:transparent;")
        self.kind_label.setStyleSheet(
            "color:#315247;background:#EAF3EE;border:1px solid #D6E3DC;"
            "border-radius:10px;padding:5px 9px;font-size:12px;font-weight:700;"
        )
        if selected:
            self.setStyleSheet(
                f"QFrame#GestureCard{{background:{background};border:2px solid {border};border-radius:22px;}}"
            )
        else:
            self.setStyleSheet(
                f"QFrame#GestureCard{{background:{background};border:1px solid {border};border-radius:22px;}}"
            )

    def _action_summary(self, gesture: GestureTemplate) -> str:
        action = gesture.action
        if action.kind == "builtin":
            return builtin_name(action.builtin_name)
        if action.kind == "workflow":
            return "JSON 组合动作"
        return ACTION_KIND_LABELS.get(action.kind, action.kind)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self.gesture)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        self.double_clicked.emit(self.gesture)
        super().mouseDoubleClickEvent(event)
