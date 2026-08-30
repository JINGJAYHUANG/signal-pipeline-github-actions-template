# Contributing

Contributions should preserve the public-safe boundary.

Before opening a pull request:

```bash
PYTHONPATH=src python scripts/release_check.py
```

A provider contribution requires deterministic fixtures, schema and freshness documentation, failure-path tests and data-rights notes. A destination contribution requires acknowledgement, retry, timeout and idempotency tests.

Never commit secrets, real recipients, proprietary signals, licensed datasets or personal data.
