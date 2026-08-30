# Signal Pipeline — GitHub Actions Template

A public-safe reference implementation for a **scheduled, stateful and idempotent signal pipeline**. It demonstrates the operational layer around recurring analytical jobs without publishing any real trading strategy, proprietary factor, customer data, licensed market feed, private endpoint or performance claim.

> **Status:** `v0.1.0` reference implementation. The bundled provider and examples are synthetic by design.

## What this repository proves

The project turns a recurring signal job into an auditable sequence:

```text
deterministic synthetic observations
        ↓
strict configuration validation
        ↓
weighted threshold selection
        ↓
TTL-based duplicate suppression
        ↓
explicit dry-run or live delivery
        ↓
state update only after acknowledgement
        ↓
JSON artifacts + SHA-256 manifest
```

It is useful as a starting point for alerting, monitoring, scheduled research, operations checks and other recurring decision-support jobs. It is **not** a ready-made investment strategy.

## Safety defaults

- Scheduled runs use `dry-run`; they do not send network requests or mutate persistent state.
- Only a manually selected `live` run can use the webhook adapter.
- Webhooks must use HTTPS and are read from an Actions Secret.
- The repository contains no real destination URL.
- The only built-in provider is deterministic synthetic data.
- Persistent delivery state lives on a separate `pipeline-state` branch.
- A failed delivery writes failure evidence but never marks a signal delivered.
- External GitHub Actions are pinned to immutable commit SHAs.

## Capabilities

| Capability | Implementation |
|---|---|
| Deterministic input | Date-, seed-, subject- and metric-derived synthetic observations |
| Config validation | Strict JSON keys, types, ranges, supported adapters and criterion checks |
| Selection | Weighted `gte` / `lte` criteria with stable ordering and maximum output count |
| Idempotency | Stable signal IDs plus TTL-based delivered-ID registry |
| State isolation | Separate Git worktree and `pipeline-state` branch |
| Delivery | Console, atomic file and HTTPS webhook adapters |
| Retry | HTTP 429/5xx and transport failures with bounded exponential backoff |
| Artifacts | Inputs, selections, duplicates, message, report, failure and SHA-256 manifest |
| Health | State freshness check for monitoring jobs |
| CI | Python 3.11, 3.12 and 3.13; unit, integration, repository and end-to-end tests |

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -e .

signal-pipeline validate-config --config config/pipeline.example.json

signal-pipeline run   --config config/pipeline.example.json   --date 2026-08-30   --mode dry-run   --state-file state/local-state.json   --output-dir artifacts/demo
```

`dry-run` renders the complete decision and artifact path but deliberately does not deliver or change state.

## Local live demonstration without a webhook

The file adapter lets you test successful delivery and duplicate suppression locally:

```bash
signal-pipeline run   --config config/pipeline.example.json   --date 2026-08-30   --mode live   --delivery file   --state-file state/local-state.json   --output-dir artifacts/live-1

signal-pipeline run   --config config/pipeline.example.json   --date 2026-08-30   --mode live   --delivery file   --state-file state/local-state.json   --output-dir artifacts/live-2
```

The first acknowledged run records delivered signal IDs. The second identical run is `duplicate-suppressed`.

## GitHub Actions operation

### Automatic schedule

`.github/workflows/scheduled-signal.yml` runs at:

```text
23:00 UTC Sunday–Thursday
07:00 Asia/Shanghai Monday–Friday
```

Scheduled events are hard-coded to `dry-run`. GitHub cron uses UTC and can be delayed during platform congestion; it is not an exchange-grade scheduler.

### Manual live run

Use **Actions → Scheduled Synthetic Signal Pipeline → Run workflow**, choose `live`, and configure:

```text
Repository secret: SIGNAL_WEBHOOK_URL
```

The workflow:

1. checks out the source;
2. prepares an isolated `pipeline-state` worktree;
3. runs the pipeline;
4. delivers via HTTPS;
5. commits state only after acknowledgement;
6. uploads artifacts even if the job fails.

No secret value is printed or persisted in repository artifacts.

## Configuration

See [`config/pipeline.example.json`](config/pipeline.example.json).

The public contract supports:

- provider: `synthetic`;
- selector: `weighted_threshold`;
- criteria: `gte` and `lte`;
- destination: `console`, `file`, `webhook`;
- TTL retention for delivered IDs;
- bounded signal count and explicit timezone metadata.

Unknown keys fail closed. This prevents misspelled settings from silently falling back to unsafe defaults.

## State semantics

State records **delivery acknowledgement**, not analytical truth:

```json
{
  "schema_version": "1.0",
  "delivered": {
    "sig-example": "2026-08-30T00:00:00Z"
  },
  "last_success_at": "2026-08-30T00:00:00Z",
  "last_run_id": "run-example"
}
```

A state entry means the destination accepted a payload. It does not prove that a signal was correct, useful, profitable or acted upon.

## Failure semantics

| Failure point | State change | Evidence |
|---|---:|---|
| Invalid config | No | process error |
| Provider / selection error | No | `failure.json` when output directory exists |
| Webhook 4xx | No | failure artifact, no retry except 429 |
| Webhook 429 / 5xx | No until accepted | bounded retry evidence |
| State write error | delivery may have occurred | run fails visibly; use destination idempotency key |
| Artifact upload failure | state may already be committed | GitHub job fails; local run artifacts remain |

The webhook request sends an `Idempotency-Key` header. A production destination should enforce it because no distributed system can make delivery and local state persistence a single atomic transaction.

## Repository map

```text
config/                         public example configuration
src/signal_pipeline/            provider, selector, state, delivery and CLI
scripts/state_branch.py         isolated Git state-branch operations
scripts/repo_audit.py           privacy and immutable-action audit
scripts/release_check.py        complete release gate
tests/                          unit and integration tests
docs/                           architecture, security and operational contracts
.github/workflows/              CI, scheduled pipeline and release automation
```

## Verification

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python scripts/release_check.py
```

The tests verify software behavior and public-safety rules. They do not validate an external dataset, a real strategy or factual accuracy of future adapters.

## Extension contract

Replace the synthetic provider only after defining:

- lawful data access and redistribution rights;
- point-in-time and freshness semantics;
- deterministic fixture data;
- timeout, retry and fallback behavior;
- schema validation;
- confidential-field redaction;
- a clear statement of what the resulting signal does and does not mean.

See [`docs/adapters.md`](docs/adapters.md).

## License

MIT. Third-party data, APIs and notification services remain subject to their own terms.
