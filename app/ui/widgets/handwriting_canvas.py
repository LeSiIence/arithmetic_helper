from __future__ import annotations

from PyQt5.QtCore import QPoint, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QImage, QPainter, QPen
from PyQt5.QtWidgets import QWidget


class HandwritingCanvas(QWidget):
    """Handwriting board with 1:1 widget-coordinate drawing."""

    drawing_changed = pyqtSignal()
    stroke_finished = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(280)
        self.setStyleSheet("background: #ffffff; border: 2px solid #9aa4b2; border-radius: 8px;")

        self._image = QImage(1, 1, QImage.Format_RGB32)
        self._image.fill(QColor("white"))
        self._last_point = QPoint()
        self._drawing = False
        self._pen = QPen(Qt.black, 6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)

    def clear_canvas(self) -> None:
        self._image.fill(QColor("white"))
        self.update()
        self.drawing_changed.emit()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming style
        painter = QPainter(self)
        painter.drawImage(self.rect(), self._image)
        super().paintEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt naming style
        if event.button() == Qt.LeftButton:
            self._last_point = event.pos()
            self._drawing = True
            self._draw_point(self._last_point)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt naming style
        if self._drawing and (event.buttons() & Qt.LeftButton):
            current = self._clamp_to_canvas(event.pos())
            painter = QPainter(self._image)
            painter.setPen(self._pen)
            painter.drawLine(self._last_point, current)
            self._last_point = current
            self.update()
            self.drawing_changed.emit()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt naming style
        if event.button() == Qt.LeftButton:
            self._drawing = False
            self.stroke_finished.emit()
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt naming style
        # Keep image size synced with widget size to avoid coordinate mismatch.
        new_size = event.size()
        if new_size.width() <= 0 or new_size.height() <= 0:
            super().resizeEvent(event)
            return
        if self._image.size() == new_size:
            super().resizeEvent(event)
            return

        new_image = QImage(new_size, QImage.Format_RGB32)
        new_image.fill(QColor("white"))
        painter = QPainter(new_image)
        painter.drawImage(0, 0, self._image.scaled(new_size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation))
        painter.end()
        self._image = new_image
        super().resizeEvent(event)

    def to_image(self) -> QImage:
        """Export current canvas snapshot for recognition."""
        return self._image.copy()

    def _draw_point(self, point: QPoint) -> None:
        painter = QPainter(self._image)
        painter.setPen(self._pen)
        p = self._clamp_to_canvas(point)
        painter.drawPoint(p)
        self.update()
        self.drawing_changed.emit()

    def _clamp_to_canvas(self, point: QPoint) -> QPoint:
        x = max(0, min(point.x(), self._image.width() - 1))
        y = max(0, min(point.y(), self._image.height() - 1))
        return QPoint(x, y)
