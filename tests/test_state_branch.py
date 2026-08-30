from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.state_branch import commit, prepare


def git(*args: str, cwd: Path):
    return subprocess.run(("git", *args), cwd=cwd, check=True, text=True, capture_output=True)


class StateBranchTests(unittest.TestCase):
    def test_prepare_and_commit_isolated_state_branch(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            remote = base / "remote.git"
            repo = base / "repo"
            git("init", "--bare", str(remote), cwd=base)
            git("init", "-b", "main", str(repo), cwd=base)
            git("config", "user.name", "Test", cwd=repo)
            git("config", "user.email", "test@example.invalid", cwd=repo)
            (repo / "README.md").write_text("main\n", encoding="utf-8")
            git("add", ".", cwd=repo)
            git("commit", "-m", "initial", cwd=repo)
            git("remote", "add", "origin", str(remote), cwd=repo)
            git("push", "-u", "origin", "main", cwd=repo)

            worktree = repo / ".pipeline-state"
            old = Path.cwd()
            try:
                __import__("os").chdir(repo)
                prepare("pipeline-state", worktree, "state.json")
                data = json.loads((worktree / "state.json").read_text())
                data["last_run_id"] = "run-test"
                (worktree / "state.json").write_text(json.dumps(data), encoding="utf-8")
                self.assertTrue(commit("pipeline-state", worktree, "state.json"))
            finally:
                __import__("os").chdir(old)
            self.assertIn("refs/heads/pipeline-state", git("show-ref", cwd=remote).stdout)


if __name__ == "__main__":
    unittest.main()
