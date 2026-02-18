from __future__ import annotations

"""Sklearn-based local digit recognizer (fallback backend).

Trains a small SVM classifier from ``sklearn.datasets.load_digits`` and
performs vertical-projection segmentation to recognise multi-digit integers
drawn on a canvas.
"""

from PyQt5.QtGui import QImage

from app.services.recognizer_backend import RecognizerBackend

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None  # type: ignore[assignment]

try:
    from sklearn.datasets import load_digits
    from sklearn.svm import SVC
except ImportError:  # pragma: no cover
    load_digits = None  # type: ignore[assignment]
    SVC = None  # type: ignore[assignment]


class HandwritingRecognizer(RecognizerBackend):
    """Offline digit recognizer backed by an sklearn SVM on 8x8 patches."""

    _FOREGROUND_THRESHOLD = 200
    _MIN_REGION_AREA = 20
    _MERGE_GAP_RATIO = 0.6
    _PADDING_RATIO = 0.3

    def __init__(self) -> None:
        self._classifier = self._build_classifier()

    # -- RecognizerBackend interface ----------------------------------------

    def recognize(self, image: QImage) -> int | None:
        if not self.available or np is None:
            return None
        gray = self._qimage_to_grayscale_array(image)
        if gray is None:
            return None

        foreground = gray < self._FOREGROUND_THRESHOLD
        if not foreground.any():
            return None

        boxes = self._segment_digit_regions(foreground)
        if not boxes:
            return None

        digits: list[str] = []
        for x1, x2, y1, y2 in boxes:
            patch = gray[y1:y2, x1:x2]
            vector = self._prepare_patch_vector(patch)
            predicted = int(self._classifier.predict([vector])[0])  # type: ignore[union-attr]
            digits.append(str(predicted))

        text = "".join(digits).lstrip("0") or "0"
        try:
            return int(text)
        except ValueError:
            return None

    @property
    def name(self) -> str:
        return "sklearn-svm"

    @property
    def available(self) -> bool:
        return self._classifier is not None

    # -- Internal -----------------------------------------------------------

    @staticmethod
    def _build_classifier():
        if load_digits is None or SVC is None:
            return None
        data = load_digits()
        clf = SVC(gamma=0.001)
        clf.fit(data.data, data.target)
        return clf

    @staticmethod
    def _qimage_to_grayscale_array(image: QImage) -> np.ndarray | None:
        if np is None:
            raise RuntimeError("numpy is required for handwriting recognition")
        gray = image.convertToFormat(QImage.Format_Grayscale8)
        w, h = gray.width(), gray.height()
        if w <= 0 or h <= 0:
            return None
        ptr = gray.bits()
        if ptr is None:
            return None
        try:
            buf_size = gray.sizeInBytes()
        except AttributeError:
            buf_size = gray.byteCount()
        ptr.setsize(buf_size)
        arr = np.frombuffer(ptr, dtype=np.uint8).reshape((h, gray.bytesPerLine()))
        return arr[:, :w].copy()

    def _segment_digit_regions(self, foreground: np.ndarray) -> list[tuple[int, int, int, int]]:
        col_sum = foreground.sum(axis=0)
        active = col_sum > 0
        spans: list[tuple[int, int]] = []
        start: int | None = None
        for idx, val in enumerate(active):
            if val and start is None:
                start = idx
            elif not val and start is not None:
                spans.append((start, idx))
                start = None
        if start is not None:
            spans.append((start, len(active)))
        if not spans:
            return []

        spans = self._merge_close_spans(spans)

        boxes: list[tuple[int, int, int, int]] = []
        for x1, x2 in spans:
            region = foreground[:, x1:x2]
            rows = np.where(region.sum(axis=1) > 0)[0]
            if rows.size == 0:
                continue
            y1, y2 = int(rows[0]), int(rows[-1] + 1)
            if (x2 - x1) * (y2 - y1) < self._MIN_REGION_AREA:
                continue
            boxes.append((x1, x2, y1, y2))
        return boxes

    @classmethod
    def _merge_close_spans(cls, spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
        if len(spans) <= 1:
            return spans
        avg_w = sum(b - a for a, b in spans) / len(spans)
        threshold = avg_w * cls._MERGE_GAP_RATIO
        merged: list[tuple[int, int]] = [spans[0]]
        for s, e in spans[1:]:
            ps, pe = merged[-1]
            if s - pe < threshold:
                merged[-1] = (ps, e)
            else:
                merged.append((s, e))
        return merged

    def _prepare_patch_vector(self, patch_gray: np.ndarray) -> np.ndarray:
        ink = (255 - patch_gray).astype(np.float32)
        if not np.any(ink > 0):
            return np.zeros(64, dtype=np.float32)

        h, w = ink.shape
        total = ink.sum()
        if total > 0:
            gy = float(np.sum(np.arange(h).reshape(-1, 1) * ink) / total)
            gx = float(np.sum(np.arange(w).reshape(1, -1) * ink) / total)
        else:
            gy, gx = h / 2.0, w / 2.0

        side = max(h, w)
        padded = max(int(side * (1.0 + 2 * self._PADDING_RATIO)), 4)
        canvas = np.zeros((padded, padded), dtype=np.float32)
        center = padded / 2.0
        yo = max(0, min(int(round(center - gy)), padded - h))
        xo = max(0, min(int(round(center - gx)), padded - w))
        canvas[yo : yo + h, xo : xo + w] = ink

        resized = self._resize_to_8(canvas)
        mx = float(np.max(resized))
        if mx <= 1e-6:
            return np.zeros(64, dtype=np.float32)
        return ((resized / mx) * 16.0).reshape(64)

    @staticmethod
    def _resize_to_8(image: np.ndarray) -> np.ndarray:
        sh, sw = image.shape
        if sh == 8 and sw == 8:
            return image.copy()
        out = np.zeros((8, 8), dtype=np.float32)
        rb = np.linspace(0, sh, 9).astype(int)
        cb = np.linspace(0, sw, 9).astype(int)
        for r in range(8):
            for c in range(8):
                blk = image[rb[r] : rb[r + 1], cb[c] : cb[c + 1]]
                if blk.size > 0:
                    out[r, c] = blk.mean()
        return out
