from __future__ import annotations

import hashlib
import random
from datetime import date

from .config import PipelineConfig
from .models import Observation


def _stable_seed(*parts: object) -> int:
    material = "|".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def generate_synthetic_observations(config: PipelineConfig, effective_date: date) -> list[Observation]:
    """Generate deterministic synthetic observations for demonstrations and tests."""
    observations: list[Observation] = []
    observed_at = f"{effective_date.isoformat()}T00:00:00Z"
    for subject in config.subjects:
        for metric in config.metrics:
            rng = random.Random(_stable_seed(config.seed, effective_date.isoformat(), subject, metric.name))
            value = round(metric.base + rng.uniform(-metric.jitter, metric.jitter), 6)
            observation_id = hashlib.sha256(
                f"{effective_date}|{subject}|{metric.name}|{value}".encode("utf-8")
            ).hexdigest()[:20]
            observations.append(
                Observation(
                    observation_id=f"obs-{observation_id}",
                    subject=subject,
                    metric=metric.name,
                    value=value,
                    unit=metric.unit,
                    observed_at=observed_at,
                    attributes={"synthetic": True, "provider": "deterministic-synthetic-v1"},
                )
            )
    return observations
