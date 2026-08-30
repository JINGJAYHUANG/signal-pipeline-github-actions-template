from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

from signal_pipeline.errors import DeliveryError
from signal_pipeline.pipeline import run_pipeline
from tests.common import config, read_json


class PipelineTests(unittest.TestCase):
    def test_dry_run_writes_artifacts_without_state_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = root / "state.json"
            result = run_pipeline(
                config(),
                effective_date=date(2026, 8, 30),
                mode="dry-run",
                state_path=state,
                output_dir=root / "out",
                now=datetime(2026, 8, 30, tzinfo=timezone.utc),
            )
            self.assertEqual(result.status, "dry-run")
            self.assertFalse(result.state_mutated)
            self.assertFalse(state.exists())
            self.assertTrue((root / "out/artifact-manifest.json").exists())

    def test_live_delivery_mutates_state_after_success(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch("signal_pipeline.pipeline.dispatch") as dispatch:
                dispatch.return_value.to_dict.return_value = {"status": "accepted"}
                result = run_pipeline(
                    config(),
                    effective_date=date(2026, 8, 30),
                    mode="live",
                    state_path=root / "state.json",
                    output_dir=root / "out",
                    now=datetime(2026, 8, 30, tzinfo=timezone.utc),
                )
            self.assertTrue(result.state_mutated)
            self.assertEqual(read_json(root / "state.json")["last_run_id"], result.run_id)

    def test_second_live_run_is_duplicate_suppressed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch("signal_pipeline.pipeline.dispatch") as dispatch:
                dispatch.return_value.to_dict.return_value = {"status": "accepted"}
                first = run_pipeline(
                    config(), effective_date=date(2026, 8, 30), mode="live",
                    state_path=root / "state.json", output_dir=root / "first",
                    now=datetime(2026, 8, 30, tzinfo=timezone.utc),
                )
                second = run_pipeline(
                    config(), effective_date=date(2026, 8, 30), mode="live",
                    state_path=root / "state.json", output_dir=root / "second",
                    now=datetime(2026, 8, 30, tzinfo=timezone.utc),
                )
            self.assertGreaterEqual(first.delivered_count, 1)
            self.assertEqual(second.status, "duplicate-suppressed")
            self.assertEqual(dispatch.call_count, 1)

    def test_failed_delivery_never_mutates_state(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = root / "state.json"
            with patch("signal_pipeline.pipeline.dispatch", side_effect=DeliveryError("failed")):
                with self.assertRaises(DeliveryError):
                    run_pipeline(
                        config(), effective_date=date(2026, 8, 30), mode="live",
                        state_path=state, output_dir=root / "out",
                        now=datetime(2026, 8, 30, tzinfo=timezone.utc),
                    )
            self.assertFalse(state.exists())
            failure = read_json(root / "out/failure.json")
            self.assertFalse(failure["state_mutated"])


if __name__ == "__main__":
    unittest.main()
