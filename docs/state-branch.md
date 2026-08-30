# State Branch Contract

Production-like GitHub Actions runs store `state.json` on `pipeline-state`, not on `main`.

The helper creates an isolated Git worktree. If the remote state branch is missing, it creates an orphan branch containing only state. If it exists, the exact remote branch is checked out. A commit occurs only when the live pipeline changed the state file.

The workflow uses a concurrency group so two live runs cannot update the state branch concurrently. This is repository-level serialization, not a distributed lock across multiple repositories.
