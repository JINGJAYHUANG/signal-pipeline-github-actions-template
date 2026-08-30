from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def evaluate_health(state_path: str | Path, *, max_age_hours: int, now: datetime | None = None) -> dict[str, Any]:
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    path = Path(state_path)
    if not path.exists():
        return {"healthy": False, "reason": "state-missing", "last_success_at": None}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        raw = data.get("last_success_at")
        if not raw:
            return {"healthy": False, "reason": "success-never-recorded", "last_success_at": None}
        last = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return {"healthy": False, "reason": "state-invalid", "last_success_at": None}
    healthy = current - last <= timedelta(hours=max_age_hours)
    return {
        "healthy": healthy,
        "reason": "within-threshold" if healthy else "success-too-old",
        "last_success_at": last.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "max_age_hours": max_age_hours,
    }
