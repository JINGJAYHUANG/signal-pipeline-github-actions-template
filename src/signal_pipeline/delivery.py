from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Callable

from .config import DeliveryConfig
from .errors import DeliveryError
from .models import DeliveryReceipt


def _payload_bytes(message: dict[str, object]) -> bytes:
    return json.dumps(message, sort_keys=True, separators=(",", ":")).encode("utf-8")


def deliver_console(message: dict[str, object]) -> DeliveryReceipt:
    print(json.dumps(message, indent=2, sort_keys=True))
    return DeliveryReceipt(destination="console", status="accepted", attempts=1)


def deliver_file(message: dict[str, object], path: str) -> DeliveryReceipt:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_bytes(_payload_bytes(message) + b"\n")
    os.replace(temporary, target)
    return DeliveryReceipt(destination="file", status="accepted", attempts=1, external_id=str(target))


def deliver_webhook(
    message: dict[str, object],
    url: str,
    config: DeliveryConfig,
    *,
    opener: Callable[..., object] = urllib.request.urlopen,
    sleeper: Callable[[float], None] = time.sleep,
) -> DeliveryReceipt:
    if not url.startswith("https://"):
        raise DeliveryError("webhook URL must use HTTPS")
    body = _payload_bytes(message)
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "synthetic-signal-pipeline/0.1.0",
            "Idempotency-Key": str(message["delivery_id"]),
        },
        method="POST",
    )
    last_error: Exception | None = None
    for attempt in range(1, config.max_attempts + 1):
        try:
            with opener(request, timeout=config.timeout_seconds) as response:
                status = int(getattr(response, "status", response.getcode()))
                if 200 <= status < 300:
                    external_id = response.headers.get("X-Request-Id") if response.headers else None
                    return DeliveryReceipt("webhook", "accepted", attempt, external_id)
                if status != 429 and status < 500:
                    raise DeliveryError(f"webhook rejected request with HTTP {status}")
                last_error = DeliveryError(f"retryable webhook HTTP {status}")
                retry_after = response.headers.get("Retry-After") if response.headers else None
        except urllib.error.HTTPError as exc:
            if exc.code != 429 and exc.code < 500:
                raise DeliveryError(f"webhook rejected request with HTTP {exc.code}") from exc
            last_error = exc
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            retry_after = None

        if attempt >= config.max_attempts:
            break
        delay = config.base_backoff_seconds * (2 ** (attempt - 1))
        if retry_after:
            try:
                delay = max(delay, float(retry_after))
            except ValueError:
                pass
        sleeper(delay)
    raise DeliveryError(
        f"webhook delivery failed after {config.max_attempts} attempts: {type(last_error).__name__}"
    )


def dispatch(
    message: dict[str, object],
    config: DeliveryConfig,
    *,
    override: str | None = None,
    webhook_url: str | None = None,
) -> DeliveryReceipt:
    destination = override or config.type
    if destination == "console":
        return deliver_console(message)
    if destination == "file":
        if not config.file_path:
            raise DeliveryError("file destination requires delivery.file_path")
        return deliver_file(message, config.file_path)
    if destination == "webhook":
        if not webhook_url:
            raise DeliveryError(f"webhook URL is missing from environment variable {config.webhook_env}")
        return deliver_webhook(message, webhook_url, config)
    raise DeliveryError(f"unsupported destination: {destination}")
