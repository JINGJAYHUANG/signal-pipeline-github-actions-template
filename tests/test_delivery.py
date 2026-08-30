from __future__ import annotations

import io
import tempfile
import unittest
import urllib.error
from pathlib import Path

from signal_pipeline.config import DeliveryConfig
from signal_pipeline.delivery import deliver_file, deliver_webhook
from signal_pipeline.errors import DeliveryError


class Response:
    def __init__(self, status: int, headers=None):
        self.status = status
        self.headers = headers or {}

    def getcode(self):
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.config = DeliveryConfig("webhook", None, "URL", 1, 3, 0.01)
        self.message = {"delivery_id": "run-1", "signals": [], "synthetic": True}

    def test_file_delivery_is_atomic(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "delivery.json"
            receipt = deliver_file(self.message, str(path))
            self.assertEqual(receipt.status, "accepted")
            self.assertTrue(path.exists())

    def test_webhook_requires_https(self):
        with self.assertRaises(DeliveryError):
            deliver_webhook(self.message, "http://example.invalid", self.config)

    def test_webhook_retries_500_then_succeeds(self):
        responses = iter([Response(500), Response(200, {"X-Request-Id": "ok"})])
        sleeps = []
        receipt = deliver_webhook(
            self.message,
            "https://example.invalid/hook",
            self.config,
            opener=lambda *args, **kwargs: next(responses),
            sleeper=sleeps.append,
        )
        self.assertEqual(receipt.attempts, 2)
        self.assertEqual(receipt.external_id, "ok")
        self.assertEqual(len(sleeps), 1)

    def test_webhook_does_not_retry_400(self):
        error = urllib.error.HTTPError("https://example.invalid", 400, "bad", {}, io.BytesIO())
        with self.assertRaises(DeliveryError):
            deliver_webhook(
                self.message,
                "https://example.invalid/hook",
                self.config,
                opener=lambda *args, **kwargs: (_ for _ in ()).throw(error),
                sleeper=lambda _: None,
            )


if __name__ == "__main__":
    unittest.main()
