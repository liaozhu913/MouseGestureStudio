from __future__ import annotations

from PySide6.QtCore import QPointF, QRect, Qt
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from ..models import Point
from .gesture_widgets import draw_arrow_head


def _virtual_geometry() -> QRect:
    screens = QGuiApplication.screens()
    if not screens:
        return QRect(0, 0, 1920, 1080)

    left = min(screen.geometry().left() for screen in screens)
    top = min(screen.geometry().top() for screen in screens)
    right = max(screen.geometry().right() for screen in screens)
    bottom = max(screen.geometry().bottom() for screen in screens)
    return QRect(left, top, right - left + 1, bottom - top + 1)


class GestureOverlay(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._points: list[Point] = []
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.hide()

    def show_points(self, points: list[Point]) -> None:
        self._points = list(points)
        if not self._points:
            self.hide()
            return

        geometry = _virtual_geometry()
        if self.geometry() != geometry:
            self.setGeometry(geometry)
        if not self.isVisible():
            self.show()
        self.update()

    def clear(self) -> None:
        self._points = []
        self.hide()

    def paintEvent(self, event) -> None:
        if len(self._points) < 1:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        translated = [
            QPointF(point[0] - self.geometry().x(), point[1] - self.geometry().y())
            for point in self._points
        ]

        glow_pen = QPen(QColor(47, 124, 246, 90), 10)
        glow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        glow_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)

        line_pen = QPen(QColor("#2F7CF6"), 4)
        line_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        line_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)

        if len(translated) >= 2:
            path = QPainterPath()
            path.moveTo(translated[0])
            for point in translated[1:]:
                path.lineTo(point)
            painter.setPen(glow_pen)
            painter.drawPath(path)
            painter.setPen(line_pen)
            painter.drawPath(path)

        end = translated[-1]
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#2F7CF6"))
        painter.drawEllipse(end, 4, 4)
        if len(translated) >= 2:
            draw_arrow_head(painter, translated[-2], translated[-1], QColor("#2F7CF6"), size=18)
