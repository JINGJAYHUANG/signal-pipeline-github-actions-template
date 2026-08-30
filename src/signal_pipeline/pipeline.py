from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from .artifacts import write_json, write_manifest
from .config import PipelineConfig
from .delivery import dispatch
from .models import Signal
from .providers import generate_synthetic_observations
from .selectors import select_signals
from .state import load_state, save_state_atomic


@dataclass(frozen=True, slots=True)
class PipelineResult:
    run_id: str
    status: str
    selected_count: int
    new_count: int
    duplicate_count: int
    delivered_count: int
    state_mutated: bool
    output_dir: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "selected_count": self.selected_count,
            "new_count": self.new_count,
            "duplicate_count": self.duplicate_count,
            "delivered_count": self.delivered_count,
            "state_mutated": self.state_mutated,
            "output_dir": self.output_dir,
        }


def _run_id(name: str, effective_date: date, signals: list[Signal]) -> str:
    material = "|".join([name, effective_date.isoformat(), *(item.signal_id for item in signals)])
    return "run-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


def run_pipeline(
    config: PipelineConfig,
    *,
    effective_date: date,
    mode: str,
    state_path: str | Path,
    output_dir: str | Path,
    delivery_override: str | None = None,
    webhook_url: str | None = None,
    now: datetime | None = None,
) -> PipelineResult:
    if mode not in {"dry-run", "live"}:
        raise ValueError("mode must be dry-run or live")
    started_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    try:
        observations = generate_synthetic_observations(config, effective_date)
        selected = select_signals(config, observations, effective_date)
        state = load_state(state_path)
        state.prune(started_at, config.ttl_days)
        selected_ids = [item.signal_id for item in selected]
        new_ids = set(state.unseen(selected_ids))
        new_signals = [item for item in selected if item.signal_id in new_ids]
        duplicates = [item for item in selected if item.signal_id not in new_ids]
        run_id = _run_id(config.name, effective_date, selected)

        message = {
            "schema_version": "1.0",
            "pipeline": config.name,
            "delivery_id": run_id,
            "effective_date": effective_date.isoformat(),
            "synthetic": True,
            "signals": [item.to_dict() for item in new_signals],
        }
        write_json(output / "observations.json", [item.to_dict() for item in observations])
        write_json(output / "selected-signals.json", [item.to_dict() for item in selected])
        write_json(output / "new-signals.json", [item.to_dict() for item in new_signals])
        write_json(output / "duplicate-signals.json", [item.to_dict() for item in duplicates])
        write_json(output / "message.json", message)

        receipt = None
        state_mutated = False
        if mode == "live" and new_signals:
            receipt = dispatch(
                message,
                config.delivery,
                override=delivery_override,
                webhook_url=webhook_url,
            )
            state.mark_delivered([item.signal_id for item in new_signals], started_at, run_id)
            save_state_atomic(state_path, state)
            state_mutated = True

        status = (
            "dry-run"
            if mode == "dry-run"
            else "duplicate-suppressed"
            if not new_signals
            else "delivered"
        )
        result = PipelineResult(
            run_id=run_id,
            status=status,
            selected_count=len(selected),
            new_count=len(new_signals),
            duplicate_count=len(duplicates),
            delivered_count=len(new_signals) if receipt else 0,
            state_mutated=state_mutated,
            output_dir=str(output),
        )
        write_json(
            output / "run-report.json",
            {
                **result.to_dict(),
                "started_at": started_at.isoformat().replace("+00:00", "Z"),
                "mode": mode,
                "receipt": receipt.to_dict() if receipt else None,
            },
        )
        write_manifest(output)
        return result
    except Exception as exc:
        write_json(
            output / "failure.json",
            {
                "error_type": type(exc).__name__,
                "message": str(exc),
                "mode": mode,
                "effective_date": effective_date.isoformat(),
                "state_mutated": False,
            },
        )
        write_manifest(output)
        raise
