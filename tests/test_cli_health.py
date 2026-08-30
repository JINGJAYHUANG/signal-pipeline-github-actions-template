from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.common import ROOT


class CLIHealthTests(unittest.TestCase):
    def env(self):
        value = dict(os.environ)
        value["PYTHONPATH"] = str(ROOT / "src")
        return value

    def test_cli_end_to_end_dry_run(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = root / "state.json"
            subprocess.run(
                [sys.executable, "-m", "signal_pipeline", "init-state", "--state-file", str(state)],
                check=True, env=self.env(), capture_output=True, text=True,
            )
            completed = subprocess.run(
                [
                    sys.executable, "-m", "signal_pipeline", "run",
                    "--config", str(ROOT / "config/pipeline.example.json"),
                    "--date", "2026-08-30", "--mode", "dry-run",
                    "--state-file", str(state), "--output-dir", str(root / "out"),
                ],
                check=True, env=self.env(), capture_output=True, text=True,
            )
            self.assertEqual(json.loads(completed.stdout.splitlines()[-1])["status"], "dry-run")

    def test_health_fails_when_never_successful(self):
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "state.json"
            state.write_text('{"schema_version":"1.0","delivered":{},"last_success_at":null,"last_run_id":null}', encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, "-m", "signal_pipeline", "health", "--state-file", str(state)],
                env=self.env(), capture_output=True, text=True,
            )
            self.assertEqual(completed.returncode, 1)
            self.assertEqual(json.loads(completed.stdout)["reason"], "success-never-recorded")


if __name__ == "__main__":
    unittest.main()
