# Failure Semantics

The pipeline follows a fail-visible rule:

- configuration and state parsing fail closed;
- dry-run never mutates state;
- live delivery must return an acknowledgement before IDs are recorded;
- HTTP 400-class errors are not retried except 429;
- HTTP 429, 500-class and transport errors use bounded retry;
- failures write `failure.json` and an integrity manifest before returning nonzero where possible.

A destination can accept a request and the subsequent state commit can still fail. The stable delivery ID and `Idempotency-Key` header allow the destination to suppress a replay.
