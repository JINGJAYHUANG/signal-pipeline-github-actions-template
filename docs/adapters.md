# Adapter Contract

A real provider or destination should be introduced behind an explicit adapter, not patched into selector logic.

A provider must document input schema, timestamps, freshness, missing values, retries, rate limits, licensing and deterministic fixtures. A destination must document acknowledgement rules, idempotency behavior, payload size, authentication and failure codes.

Do not add real credentials, customer identifiers, account numbers, proprietary factors or licensed raw data to examples or tests.
