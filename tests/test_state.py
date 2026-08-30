from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from signal_pipeline.errors import StateError
from signal_pipeline.state import PipelineState, load_state, save_state_atomic


class StateTests(unittest.TestCase):
    def test_missing_state_returns_empty(self):
        with tempfile.TemporaryDirectory() as temp:
            state = load_state(Path(temp) / "missing.json")
            self.assertEqual(state.delivered, {})

    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "state.json"
            state = PipelineState()
            state.mark_delivered(["sig-1"], datetime(2026, 8, 30, tzinfo=timezone.utc), "run-1")
            save_state_atomic(path, state)
            self.assertEqual(load_state(path).last_run_id, "run-1")

    def test_invalid_state_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "state.json"
            path.write_text("{not-json", encoding="utf-8")
            with self.assertRaises(StateError):
                load_state(path)

    def test_prune_removes_expired_ids(self):
        now = datetime(2026, 8, 30, tzinfo=timezone.utc)
        state = PipelineState(
            delivered={
                "old": (now - timedelta(days=40)).isoformat(),
                "new": (now - timedelta(days=2)).isoformat(),
            }
        )
        state.prune(now, 30)
        self.assertEqual(set(state.delivered), {"new"})

    def test_unseen_preserves_order(self):
        state = PipelineState(delivered={"seen": "2026-08-30T00:00:00Z"})
        self.assertEqual(state.unseen(["new-a", "seen", "new-b"]), ["new-a", "new-b"])


if __name__ == "__main__":
    unittest.main()
