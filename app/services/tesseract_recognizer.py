from __future__ import annotations

"""Tesseract OCR backend (local, requires Tesseract binary + pytesseract)."""

import io
import logging
import re

from PyQt5.QtGui import QImage

from app.services.recognizer_backend import RecognizerBackend

log = logging.getLogger(__name__)

try:
    import pytesseract
    from PIL import Image as PILImage
except ImportError:  # pragma: no cover
    pytesseract = None  # type: ignore[assignment]
    PILImage = None  # type: ignore[assignment]


class TesseractRecognizer(RecognizerBackend):
    """Offline digit recognizer backed by Tesseract OCR."""

    def recognize(self, image: QImage) -> int | None:
        if not self.available:
            return None
        png = self._qimage_to_png_bytes(image)
        if not png:
            return None
        try:
            pil = PILImage.open(io.BytesIO(png))
            text: str = pytesseract.image_to_string(
                pil,
                config="--psm 7 -c tessedit_char_whitelist=0123456789",
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("Tesseract recognition failed: %s", exc)
            return None
        digits = re.sub(r"\D", "", text)
        if not digits:
            return None
        try:
            return int(digits)
        except ValueError:
            return None

    @property
    def name(self) -> str:
        return "tesseract"

    @property
    def available(self) -> bool:
        if pytesseract is None or PILImage is None:
            return False
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception:  # noqa: BLE001
            return False
