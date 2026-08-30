from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


def run(*args: str, cwd: str | Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, check=check, text=True, capture_output=True)


def remote_exists(branch: str) -> bool:
    result = run("git", "ls-remote", "--exit-code", "--heads", "origin", branch, check=False)
    return result.returncode == 0


def prepare(branch: str, worktree: Path, state_file: str) -> None:
    shutil.rmtree(worktree, ignore_errors=True)
    run("git", "fetch", "origin", "--prune")
    if remote_exists(branch):
        run("git", "worktree", "add", "--detach", str(worktree), f"origin/{branch}")
        run("git", "switch", "-C", branch, cwd=worktree)
        return
    run("git", "worktree", "add", "--detach", str(worktree), "HEAD")
    run("git", "switch", "--orphan", branch, cwd=worktree)
    run("git", "rm", "-rf", ".", cwd=worktree, check=False)
    target = worktree / state_file
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {"schema_version": "1.0", "delivered": {}, "last_success_at": None, "last_run_id": None},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    run("git", "add", state_file, cwd=worktree)
    run("git", "commit", "-m", "chore: initialize pipeline state", cwd=worktree)
    run("git", "push", "-u", "origin", f"HEAD:{branch}", cwd=worktree)


def commit(branch: str, worktree: Path, state_file: str) -> bool:
    run("git", "add", state_file, cwd=worktree)
    changed = run("git", "diff", "--cached", "--quiet", cwd=worktree, check=False).returncode != 0
    if not changed:
        return False
    run("git", "commit", "-m", "chore: persist signal delivery state", cwd=worktree)
    run("git", "push", "origin", f"HEAD:{branch}", cwd=worktree)
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "commit"):
        command = sub.add_parser(name)
        command.add_argument("--branch", default="pipeline-state")
        command.add_argument("--worktree", type=Path, default=Path(".pipeline-state"))
        command.add_argument("--state-file", default="state.json")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.branch, args.worktree, args.state_file)
    else:
        print(json.dumps({"committed": commit(args.branch, args.worktree, args.state_file)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
