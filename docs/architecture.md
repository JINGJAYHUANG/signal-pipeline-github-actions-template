# Architecture

The system separates analytical decisions from operational side effects.

1. **Provider boundary** produces typed observations. The public provider is deterministic and synthetic.
2. **Selector boundary** evaluates declared criteria and emits stable signal IDs.
3. **State boundary** reads acknowledgement history and suppresses already delivered IDs.
4. **Delivery boundary** is invoked only in explicit live mode.
5. **Commit boundary** persists state only after destination acknowledgement.
6. **Evidence boundary** writes JSON artifacts and a SHA-256 manifest.

This separation makes it possible to test selection without network access and to test delivery without a real analytical strategy.
