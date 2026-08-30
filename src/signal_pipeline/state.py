from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .errors import StateError


@dataclass(slots=True)
class PipelineState:
    schema_version: str = "1.0"
    delivered: dict[str, str] = field(default_factory=dict)
    last_success_at: str | None = None
    last_run_id: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PipelineState":
        if data.get("schema_version") != "1.0":
            raise StateError("unsupported state schema_version")
        delivered = data.get("delivered", {})
        if not isinstance(delivered, dict) or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in delivered.items()
        ):
            raise StateError("state.delivered must be a string map")
        return cls(
            schema_version="1.0",
            delivered=dict(delivered),
            last_success_at=data.get("last_success_at"),
            last_run_id=data.get("last_run_id"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "delivered": dict(sorted(self.delivered.items())),
            "last_success_at": self.last_success_at,
            "last_run_id": self.last_run_id,
        }

    def prune(self, now: datetime, ttl_days: int) -> None:
        cutoff = now - timedelta(days=ttl_days)
        retained: dict[str, str] = {}
        for signal_id, timestamp in self.delivered.items():
            try:
                value = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except ValueError:
                continue
            if value >= cutoff:
                retained[signal_id] = timestamp
        self.delivered = retained

    def unseen(self, signal_ids: list[str]) -> list[str]:
        return [signal_id for signal_id in signal_ids if signal_id not in self.delivered]

    def mark_delivered(self, signal_ids: list[str], now: datetime, run_id: str) -> None:
        timestamp = now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        for signal_id in signal_ids:
            self.delivered[signal_id] = timestamp
        self.last_success_at = timestamp
        self.last_run_id = run_id


def load_state(path: str | Path) -> PipelineState:
    source = Path(path)
    if not source.exists():
        return PipelineState()
    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StateError(f"cannot read state: {exc}") from exc
    if not isinstance(raw, dict):
        raise StateError("state root must be an object")
    return PipelineState.from_dict(raw)


def save_state_atomic(path: str | Path, state: PipelineState) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(state.to_dict(), indent=2, sort_keys=True) + "\n"
    try:
        descriptor, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except OSError as exc:
        raise StateError(f"cannot save state atomically: {exc}") from exc
