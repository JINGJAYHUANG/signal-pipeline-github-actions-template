from __future__ import annotations

import hashlib
from datetime import date

from .config import PipelineConfig
from .models import Observation, Signal


def _criterion_passes(operator: str, value: float, threshold: float) -> bool:
    return value >= threshold if operator == "gte" else value <= threshold


def select_signals(
    config: PipelineConfig,
    observations: list[Observation],
    effective_date: date,
) -> list[Signal]:
    by_subject: dict[str, dict[str, Observation]] = {}
    for observation in observations:
        by_subject.setdefault(observation.subject, {})[observation.metric] = observation

    total_weight = sum(item.weight for item in config.criteria)
    selected: list[Signal] = []
    for subject, metrics in sorted(by_subject.items()):
        earned = 0.0
        reasons: list[str] = []
        ids: list[str] = []
        for criterion in config.criteria:
            observation = metrics[criterion.metric]
            ids.append(observation.observation_id)
            if _criterion_passes(criterion.operator, observation.value, criterion.threshold):
                earned += criterion.weight
                symbol = ">=" if criterion.operator == "gte" else "<="
                reasons.append(
                    f"{criterion.metric} {observation.value:g} {symbol} {criterion.threshold:g}"
                )
        score = round(earned / total_weight, 6)
        if score < config.min_score:
            continue
        identity = "|".join(
            [effective_date.isoformat(), subject, f"{score:.6f}", *sorted(reasons)]
        )
        signal_id = "sig-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
        selected.append(
            Signal(
                signal_id=signal_id,
                subject=subject,
                score=score,
                reasons=tuple(reasons),
                observation_ids=tuple(sorted(ids)),
                effective_date=effective_date.isoformat(),
            )
        )
    selected.sort(key=lambda item: (-item.score, item.subject, item.signal_id))
    return selected[: config.max_signals]
