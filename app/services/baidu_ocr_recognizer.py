from __future__ import annotations

"""Baidu OCR handwriting recognition backend (REST API)."""

import base64
import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request

from PyQt5.QtGui import QImage

from app.services.recognizer_backend import RecognizerBackend

log = logging.getLogger(__name__)

_TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
_HANDWRITING_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/handwriting"
_TIMEOUT = 10


class BaiduOcrRecognizer(RecognizerBackend):
    """Recognise handwritten integers via the Baidu OCR API."""

    def __init__(self, api_key: str, secret_key: str) -> None:
        self._api_key = api_key
        self._secret_key = secret_key
        self._access_token: str | None = None

    def recognize(self, image: QImage) -> int | None:
        token = self._ensure_access_token()
        if not token:
            return None
        png = self._qimage_to_png_bytes(image)
        if not png:
            return None
        b64 = base64.b64encode(png).decode("ascii")
        body = urllib.parse.urlencode({"image": b64}).encode("utf-8")
        try:
            req = urllib.request.Request(
                f"{_HANDWRITING_URL}?access_token={token}",
                data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                result: dict = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            log.warning("Baidu OCR request failed: %s", exc)
            return None
        return self._extract_integer(result)

    @property
    def name(self) -> str:
        return "baidu-ocr"

    @property
    def available(self) -> bool:
        return bool(self._api_key and self._secret_key)

    def _ensure_access_token(self) -> str | None:
        if self._access_token:
            return self._access_token
        params = urllib.parse.urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": self._api_key,
                "client_secret": self._secret_key,
            }
        )
        try:
            url = f"{_TOKEN_URL}?{params}"
            with urllib.request.urlopen(url, timeout=_TIMEOUT) as resp:
                data: dict = json.loads(resp.read().decode("utf-8"))
            self._access_token = data.get("access_token")
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            log.warning("Baidu token request failed: %s", exc)
        return self._access_token

    @staticmethod
    def _extract_integer(result: dict) -> int | None:
        words_result = result.get("words_result")
        if not words_result:
            return None
        raw = " ".join(item.get("words", "") for item in words_result)
        digits = re.sub(r"\D", "", raw)
        if not digits:
            return None
        try:
            return int(digits)
        except ValueError:
            return None
