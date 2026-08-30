from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


def run(*args: str, env: dict[str, str] | None = None) -> None:
    subprocess.run(args, check=True, env=env)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    env = dict(__import__("os").environ)
    env["PYTHONPATH"] = str(root / "src")
    run(sys.executable, "-m", "compileall", "-q", str(root / "src"), str(root / "scripts"), str(root / "tests"))
    run(sys.executable, "-m", "unittest", "discover", "-s", str(root / "tests"), "-v", env=env)
    run(sys.executable, str(root / "scripts" / "repo_audit.py"))
    run(sys.executable, "-m", "signal_pipeline", "validate-config", "--config", str(root / "config" / "pipeline.example.json"), env=env)
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        state = work / "state.json"
        run(sys.executable, "-m", "signal_pipeline", "init-state", "--state-file", str(state), env=env)
        run(
            sys.executable, "-m", "signal_pipeline", "run",
            "--config", str(root / "config" / "pipeline.example.json"),
            "--date", "2026-08-30", "--mode", "dry-run",
            "--state-file", str(state), "--output-dir", str(work / "out"),
            env=env,
        )
    print("PASS: release checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
