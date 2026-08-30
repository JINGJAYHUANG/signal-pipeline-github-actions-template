from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from signal_pipeline.config import ConfigError, load_config
from signal_pipeline.providers import generate_synthetic_observations
from signal_pipeline.selectors import select_signals
from tests.common import ROOT, config


class ConfigProviderSelectorTests(unittest.TestCase):
    def test_example_config_loads(self):
        value = config()
        self.assertEqual(value.schema_version, "1.0")
        self.assertEqual(len(value.subjects), 6)

    def test_unknown_root_key_fails(self):
        raw = json.loads((ROOT / "config/pipeline.example.json").read_text())
        raw["unexpected"] = True
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaises(ConfigError):
                load_config(path)

    def test_non_synthetic_provider_fails(self):
        raw = json.loads((ROOT / "config/pipeline.example.json").read_text())
        raw["provider"]["type"] = "market"
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaises(ConfigError):
                load_config(path)

    def test_provider_is_deterministic(self):
        value = config()
        first = generate_synthetic_observations(value, date(2026, 8, 30))
        second = generate_synthetic_observations(value, date(2026, 8, 30))
        self.assertEqual(first, second)
        self.assertTrue(all(item.attributes["synthetic"] for item in first))

    def test_different_dates_change_observations(self):
        value = config()
        first = generate_synthetic_observations(value, date(2026, 8, 30))
        second = generate_synthetic_observations(value, date(2026, 8, 31))
        self.assertNotEqual(first, second)

    def test_selector_is_stable_and_bounded(self):
        value = config()
        observations = generate_synthetic_observations(value, date(2026, 8, 30))
        first = select_signals(value, observations, date(2026, 8, 30))
        second = select_signals(value, observations, date(2026, 8, 30))
        self.assertEqual(first, second)
        self.assertLessEqual(len(first), value.max_signals)
        self.assertTrue(all(item.score >= value.min_score for item in first))


if __name__ == "__main__":
    unittest.main()
