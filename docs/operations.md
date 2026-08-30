# Operations Guide

1. Keep the scheduled path in dry-run until several artifact sets have been reviewed.
2. Configure a protected GitHub Environment for any real live destination.
3. Add `SIGNAL_WEBHOOK_URL` as a repository or environment secret.
4. Run manual live mode against a test destination.
5. Confirm `pipeline-state` contains only `state.json`.
6. Monitor the `health` command and failed workflow runs.
7. Rotate the webhook if logs or external systems indicate exposure.
8. Treat any change to provider, selector, retry or state semantics as a reviewed release.
