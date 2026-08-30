from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Observation:
    observation_id: str
    subject: str
    metric: str
    value: float
    unit: str
    observed_at: str
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Signal:
    signal_id: str
    subject: str
    score: float
    reasons: tuple[str, ...]
    observation_ids: tuple[str, ...]
    effective_date: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["reasons"] = list(self.reasons)
        data["observation_ids"] = list(self.observation_ids)
        return data


@dataclass(frozen=True, slots=True)
class DeliveryReceipt:
    destination: str
    status: str
    attempts: int
    external_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
