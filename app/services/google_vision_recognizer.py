from __future__ import annotations

"""Google Cloud Vision OCR backend (REST API with API key)."""

import base64
import json
import logging
import re
import urllib.error
import urllib.request

from PyQt5.QtGui import QImage

from app.services.recognizer_backend import RecognizerBackend

log = logging.getLogger(__name__)

_ENDPOINT = "https://vision.googleapis.com/v1/images:annotate"
_TIMEOUT = 10


class GoogleVisionRecognizer(RecognizerBackend):
    """Recognise handwritten integers via the Google Cloud Vision API."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def recognize(self, image: QImage) -> int | None:
        png = self._qimage_to_png_bytes(image)
        if not png:
            return None
        payload = {
            "requests": [
                {
                    "image": {"content": base64.b64encode(png).decode("ascii")},
                    "features": [{"type": "TEXT_DETECTION"}],
                }
            ]
        }
        try:
            req = urllib.request.Request(
                f"{_ENDPOINT}?key={self._api_key}",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                result: dict = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            log.warning("Google Vision request failed: %s", exc)
            return None
        return self._extract_integer(result)

    @property
    def name(self) -> str:
        return "google-vision"

    @property
    def available(self) -> bool:
        return bool(self._api_key)

    @staticmethod
    def _extract_integer(result: dict) -> int | None:
        try:
            annotations = result["responses"][0].get("textAnnotations")
            if not annotations:
                return None
            raw = annotations[0].get("description", "")
        except (KeyError, IndexError):
            return None
        digits = re.sub(r"\D", "", raw)
        if not digits:
            return None
        try:
            return int(digits)
        except ValueError:
            return None
