from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import ConfigError

_ALLOWED_ROOT = {"schema_version", "pipeline", "provider", "selector", "state", "delivery"}
_ALLOWED_PIPELINE = {"name", "timezone", "max_signals"}
_ALLOWED_PROVIDER = {"type", "seed", "subjects", "metrics"}
_ALLOWED_METRIC = {"name", "base", "jitter", "unit"}
_ALLOWED_SELECTOR = {"type", "min_score", "criteria"}
_ALLOWED_CRITERION = {"metric", "operator", "threshold", "weight"}
_ALLOWED_STATE = {"ttl_days"}
_ALLOWED_DELIVERY = {"type", "file_path", "webhook_env", "timeout_seconds", "max_attempts", "base_backoff_seconds"}


@dataclass(frozen=True, slots=True)
class MetricConfig:
    name: str
    base: float
    jitter: float
    unit: str


@dataclass(frozen=True, slots=True)
class Criterion:
    metric: str
    operator: str
    threshold: float
    weight: float


@dataclass(frozen=True, slots=True)
class DeliveryConfig:
    type: str
    file_path: str | None
    webhook_env: str
    timeout_seconds: float
    max_attempts: int
    base_backoff_seconds: float


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    schema_version: str
    name: str
    timezone: str
    max_signals: int
    seed: int
    subjects: tuple[str, ...]
    metrics: tuple[MetricConfig, ...]
    min_score: float
    criteria: tuple[Criterion, ...]
    ttl_days: int
    delivery: DeliveryConfig


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{label} must be an object")
    return value


def _reject_unknown(data: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise ConfigError(f"{label} has unknown keys: {', '.join(unknown)}")


def _required(data: dict[str, Any], key: str, label: str) -> Any:
    if key not in data:
        raise ConfigError(f"{label}.{key} is required")
    return data[key]


def load_config(path: str | Path) -> PipelineConfig:
    source = Path(path)
    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"cannot read configuration: {exc}") from exc

    root = _mapping(raw, "root")
    _reject_unknown(root, _ALLOWED_ROOT, "root")
    if _required(root, "schema_version", "root") != "1.0":
        raise ConfigError("schema_version must be '1.0'")

    pipeline = _mapping(_required(root, "pipeline", "root"), "pipeline")
    provider = _mapping(_required(root, "provider", "root"), "provider")
    selector = _mapping(_required(root, "selector", "root"), "selector")
    state = _mapping(_required(root, "state", "root"), "state")
    delivery = _mapping(_required(root, "delivery", "root"), "delivery")
    _reject_unknown(pipeline, _ALLOWED_PIPELINE, "pipeline")
    _reject_unknown(provider, _ALLOWED_PROVIDER, "provider")
    _reject_unknown(selector, _ALLOWED_SELECTOR, "selector")
    _reject_unknown(state, _ALLOWED_STATE, "state")
    _reject_unknown(delivery, _ALLOWED_DELIVERY, "delivery")

    if provider.get("type") != "synthetic":
        raise ConfigError("public template only supports provider.type='synthetic'")
    if selector.get("type") != "weighted_threshold":
        raise ConfigError("selector.type must be 'weighted_threshold'")

    subjects_raw = _required(provider, "subjects", "provider")
    if not isinstance(subjects_raw, list) or not subjects_raw or not all(isinstance(x, str) and x.strip() for x in subjects_raw):
        raise ConfigError("provider.subjects must be a non-empty string list")
    if len(set(subjects_raw)) != len(subjects_raw):
        raise ConfigError("provider.subjects must be unique")

    metric_items = _required(provider, "metrics", "provider")
    if not isinstance(metric_items, list) or not metric_items:
        raise ConfigError("provider.metrics must be a non-empty list")
    metrics: list[MetricConfig] = []
    for index, item in enumerate(metric_items):
        obj = _mapping(item, f"provider.metrics[{index}]")
        _reject_unknown(obj, _ALLOWED_METRIC, f"provider.metrics[{index}]")
        metric = MetricConfig(
            name=str(_required(obj, "name", "metric")).strip(),
            base=float(_required(obj, "base", "metric")),
            jitter=float(_required(obj, "jitter", "metric")),
            unit=str(_required(obj, "unit", "metric")).strip(),
        )
        if not metric.name or metric.jitter < 0:
            raise ConfigError("metric name must be non-empty and jitter must be non-negative")
        metrics.append(metric)
    metric_names = {item.name for item in metrics}
    if len(metric_names) != len(metrics):
        raise ConfigError("metric names must be unique")

    criterion_items = _required(selector, "criteria", "selector")
    if not isinstance(criterion_items, list) or not criterion_items:
        raise ConfigError("selector.criteria must be a non-empty list")
    criteria: list[Criterion] = []
    for index, item in enumerate(criterion_items):
        obj = _mapping(item, f"selector.criteria[{index}]")
        _reject_unknown(obj, _ALLOWED_CRITERION, f"selector.criteria[{index}]")
        criterion = Criterion(
            metric=str(_required(obj, "metric", "criterion")),
            operator=str(_required(obj, "operator", "criterion")),
            threshold=float(_required(obj, "threshold", "criterion")),
            weight=float(_required(obj, "weight", "criterion")),
        )
        if criterion.metric not in metric_names:
            raise ConfigError(f"criterion metric is not provided: {criterion.metric}")
        if criterion.operator not in {"gte", "lte"}:
            raise ConfigError("criterion operator must be 'gte' or 'lte'")
        if criterion.weight <= 0:
            raise ConfigError("criterion weight must be positive")
        criteria.append(criterion)

    max_signals = int(_required(pipeline, "max_signals", "pipeline"))
    min_score = float(_required(selector, "min_score", "selector"))
    ttl_days = int(_required(state, "ttl_days", "state"))
    if max_signals < 1 or not 0 <= min_score <= 1 or ttl_days < 1:
        raise ConfigError("max_signals>=1, 0<=min_score<=1, and ttl_days>=1 are required")

    delivery_type = str(delivery.get("type", "console"))
    if delivery_type not in {"console", "file", "webhook"}:
        raise ConfigError("delivery.type must be console, file, or webhook")
    if delivery_type == "file" and not delivery.get("file_path"):
        raise ConfigError("delivery.file_path is required for file delivery")
    timeout = float(delivery.get("timeout_seconds", 10))
    attempts = int(delivery.get("max_attempts", 3))
    backoff = float(delivery.get("base_backoff_seconds", 0.5))
    if timeout <= 0 or attempts < 1 or backoff < 0:
        raise ConfigError("delivery timeout/attempt/backoff values are invalid")

    return PipelineConfig(
        schema_version="1.0",
        name=str(_required(pipeline, "name", "pipeline")).strip(),
        timezone=str(_required(pipeline, "timezone", "pipeline")).strip(),
        max_signals=max_signals,
        seed=int(_required(provider, "seed", "provider")),
        subjects=tuple(subjects_raw),
        metrics=tuple(metrics),
        min_score=min_score,
        criteria=tuple(criteria),
        ttl_days=ttl_days,
        delivery=DeliveryConfig(
            type=delivery_type,
            file_path=delivery.get("file_path"),
            webhook_env=str(delivery.get("webhook_env", "SIGNAL_WEBHOOK_URL")),
            timeout_seconds=timeout,
            max_attempts=attempts,
            base_backoff_seconds=backoff,
        ),
    )
