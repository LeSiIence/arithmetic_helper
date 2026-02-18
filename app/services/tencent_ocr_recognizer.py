from __future__ import annotations

"""Tencent Cloud OCR handwriting recognition backend (REST API with TC3 signing)."""

import base64
import hashlib
import hmac
import json
import logging
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

from PyQt5.QtGui import QImage

from app.services.recognizer_backend import RecognizerBackend

log = logging.getLogger(__name__)

_SERVICE = "ocr"
_HOST = "ocr.tencentcloudapi.com"
_ACTION = "GeneralHandwritingOCR"
_VERSION = "2018-11-19"
_TIMEOUT = 10


class TencentOcrRecognizer(RecognizerBackend):
    """Recognise handwritten integers via the Tencent Cloud OCR API."""

    def __init__(self, secret_id: str, secret_key: str) -> None:
        self._secret_id = secret_id
        self._secret_key = secret_key

    def recognize(self, image: QImage) -> int | None:
        png = self._qimage_to_png_bytes(image)
        if not png:
            return None
        b64 = base64.b64encode(png).decode("ascii")
        payload = json.dumps({"ImageBase64": b64})
        headers = self._build_signed_headers(payload)
        try:
            req = urllib.request.Request(
                f"https://{_HOST}",
                data=payload.encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                result: dict = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            log.warning("Tencent OCR request failed: %s", exc)
            return None
        return self._extract_integer(result)

    @property
    def name(self) -> str:
        return "tencent-ocr"

    @property
    def available(self) -> bool:
        return bool(self._secret_id and self._secret_key)

    # -- TC3-HMAC-SHA256 signing -------------------------------------------

    def _build_signed_headers(self, payload: str) -> dict[str, str]:
        timestamp = int(time.time())
        date = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d")

        ct = "application/json; charset=utf-8"
        canonical_headers = f"content-type:{ct}\nhost:{_HOST}\n"
        signed_headers = "content-type;host"
        payload_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        canonical_request = (
            f"POST\n/\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
        )

        credential_scope = f"{date}/{_SERVICE}/tc3_request"
        string_to_sign = (
            f"TC3-HMAC-SHA256\n{timestamp}\n{credential_scope}\n"
            + hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        )

        def _hmac(key: bytes, msg: str) -> bytes:
            return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

        secret_date = _hmac(("TC3" + self._secret_key).encode("utf-8"), date)
        secret_service = _hmac(secret_date, _SERVICE)
        secret_signing = _hmac(secret_service, "tc3_request")
        signature = hmac.new(
            secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        authorization = (
            f"TC3-HMAC-SHA256 Credential={self._secret_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )
        return {
            "Authorization": authorization,
            "Content-Type": ct,
            "Host": _HOST,
            "X-TC-Action": _ACTION,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Version": _VERSION,
        }

    # -- Response parsing ---------------------------------------------------

    @staticmethod
    def _extract_integer(result: dict) -> int | None:
        try:
            items = result["Response"]["TextDetections"]
            if not items:
                return None
            raw = " ".join(item.get("DetectedText", "") for item in items)
        except (KeyError, TypeError):
            return None
        digits = re.sub(r"\D", "", raw)
        if not digits:
            return None
        try:
            return int(digits)
        except ValueError:
            return None
