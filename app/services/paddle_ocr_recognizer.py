from __future__ import annotations

"""PaddleOCR backend (local, requires paddleocr + paddlepaddle)."""

import io
import logging
import re

from PyQt5.QtGui import QImage

from app.services.recognizer_backend import RecognizerBackend

log = logging.getLogger(__name__)

try:
    import numpy as np
    from PIL import Image as PILImage
except ImportError:  # pragma: no cover
    np = None  # type: ignore[assignment]
    PILImage = None  # type: ignore[assignment]

try:
    from paddleocr import PaddleOCR
except ImportError:  # pragma: no cover
    PaddleOCR = None  # type: ignore[assignment]


class PaddleOcrRecognizer(RecognizerBackend):
    """Offline digit recognizer backed by PaddleOCR."""

    def __init__(self) -> None:
        self._ocr = self._build_ocr()

    def recognize(self, image: QImage) -> int | None:
        if not self.available:
            return None
        png = self._qimage_to_png_bytes(image)
        if not png:
            return None
        try:
            pil = PILImage.open(io.BytesIO(png)).convert("RGB")
            arr = np.array(pil)
            results = self._ocr.ocr(arr, det=True, rec=True, cls=False)  # type: ignore[union-attr]
        except Exception as exc:  # noqa: BLE001
            log.warning("PaddleOCR recognition failed: %s", exc)
            return None
        return self._extract_integer(results)

    @property
    def name(self) -> str:
        return "paddle-ocr"

    @property
    def available(self) -> bool:
        return self._ocr is not None

    @staticmethod
    def _build_ocr():
        if PaddleOCR is None or np is None or PILImage is None:
            return None
        try:
            return PaddleOCR(use_angle_cls=False, lang="en", show_log=False)
        except Exception as exc:  # noqa: BLE001
            log.warning("PaddleOCR init failed: %s", exc)
            return None

    @staticmethod
    def _extract_integer(results) -> int | None:
        if not results:
            return None
        texts: list[str] = []
        for line in results:
            if not line:
                continue
            for item in line:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    text_part = item[1]
                    if isinstance(text_part, (list, tuple)):
                        texts.append(str(text_part[0]))
                    else:
                        texts.append(str(text_part))
        raw = " ".join(texts)
        digits = re.sub(r"\D", "", raw)
        if not digits:
            return None
        try:
            return int(digits)
        except ValueError:
            return None
