from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path

from .config import load_config
from .health import evaluate_health
from .pipeline import run_pipeline
from .state import PipelineState, save_state_atomic


def _date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must use YYYY-MM-DD") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="signal-pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate-config", help="validate a pipeline configuration")
    validate.add_argument("--config", required=True)

    init = sub.add_parser("init-state", help="create an empty state file")
    init.add_argument("--state-file", required=True)

    run = sub.add_parser("run", help="execute one deterministic pipeline run")
    run.add_argument("--config", required=True)
    run.add_argument("--date", required=True, type=_date)
    run.add_argument("--mode", choices=["dry-run", "live"], default="dry-run")
    run.add_argument("--state-file", required=True)
    run.add_argument("--output-dir", required=True)
    run.add_argument("--delivery", choices=["console", "file", "webhook"])
    run.add_argument("--webhook-env")

    health = sub.add_parser("health", help="evaluate state freshness")
    health.add_argument("--state-file", required=True)
    health.add_argument("--max-age-hours", type=int, default=36)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "validate-config":
        config = load_config(args.config)
        print(json.dumps({"valid": True, "pipeline": config.name}, sort_keys=True))
        return 0
    if args.command == "init-state":
        target = Path(args.state_file)
        if target.exists():
            raise SystemExit(f"refusing to overwrite existing state: {target}")
        save_state_atomic(target, PipelineState())
        print(target)
        return 0
    if args.command == "health":
        result = evaluate_health(args.state_file, max_age_hours=args.max_age_hours)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["healthy"] else 1

    config = load_config(args.config)
    env_name = args.webhook_env or config.delivery.webhook_env
    webhook_url = os.environ.get(env_name)
    result = run_pipeline(
        config,
        effective_date=args.date,
        mode=args.mode,
        state_path=args.state_file,
        output_dir=args.output_dir,
        delivery_override=args.delivery,
        webhook_url=webhook_url,
    )
    print(json.dumps(result.to_dict(), sort_keys=True))
    return 0
