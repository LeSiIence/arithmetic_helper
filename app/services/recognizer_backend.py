from __future__ import annotations

"""Abstract interface for handwriting / OCR recognition backends."""

from abc import ABC, abstractmethod

from PyQt5.QtCore import QBuffer, QIODevice
from PyQt5.QtGui import QImage


class RecognizerBackend(ABC):
    """Minimal contract: take a canvas snapshot, return an integer or *None*."""

    @abstractmethod
    def recognize(self, image: QImage) -> int | None:
        """Recognize handwritten digits and return the integer value.

        Returns ``None`` when recognition fails or no input is detected.
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable backend name shown in the UI / logs."""

    @property
    @abstractmethod
    def available(self) -> bool:
        """Whether this backend is ready (dependencies loaded, API reachable, etc.)."""

    @staticmethod
    def _qimage_to_png_bytes(image: QImage) -> bytes | None:
        """Encode a QImage as PNG bytes (shared helper for cloud backends)."""
        buf = QBuffer()
        buf.open(QIODevice.WriteOnly)
        if not image.save(buf, "PNG"):
            return None
        return bytes(buf.data())
