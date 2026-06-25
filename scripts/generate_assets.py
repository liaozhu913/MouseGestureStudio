from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SVG_PATH = ASSETS / "logo.svg"
PNG_PATH = ASSETS / "logo.png"
ICO_PATH = ASSETS / "logo.ico"


def render_svg(size: int) -> QImage:
    renderer = QSvgRenderer(str(SVG_PATH))
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    renderer.render(painter)
    painter.end()
    return image


def main() -> None:
    QApplication.instance() or QApplication([])
    ASSETS.mkdir(parents=True, exist_ok=True)

    image = render_svg(1024)
    image.save(str(PNG_PATH), "PNG")

    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        pixmap = QPixmap.fromImage(render_svg(size))
        icon.addPixmap(pixmap, QIcon.Mode.Normal, QIcon.State.Off)
    icon.pixmap(QSize(256, 256), QIcon.Mode.Normal, QIcon.State.Off).save(str(ICO_PATH), "ICO")

    print(f"generated {PNG_PATH}")
    print(f"generated {ICO_PATH}")


if __name__ == "__main__":
    main()
