from __future__ import annotations

import json
from pathlib import Path

from signal_pipeline.config import load_config


ROOT = Path(__file__).resolve().parents[1]


def config():
    return load_config(ROOT / "config" / "pipeline.example.json")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))
