# Security Model

## Trust boundaries

- Repository configuration and synthetic fixtures are trusted after review.
- A future external provider is untrusted input.
- Webhook URLs are secrets and must never be committed.
- Destination responses are untrusted and only selected metadata is retained.
- Pull requests are untrusted; no secret-bearing live workflow runs on pull-request code.

## Controls

- scheduled mode is dry-run;
- live mode is manual;
- least-privilege workflow permissions;
- immutable action SHAs;
- HTTPS-only webhook;
- bounded response time and attempts;
- secret and personal-data repository scan;
- no secret values in logs or artifacts;
- state branch contains delivery metadata only.

This is a reference security posture, not a formal certification.
