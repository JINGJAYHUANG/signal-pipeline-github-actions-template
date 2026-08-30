.PHONY: test audit check demo

test:
	PYTHONPATH=src python -m unittest discover -s tests -v

audit:
	PYTHONPATH=src python scripts/repo_audit.py

check:
	PYTHONPATH=src python scripts/release_check.py

demo:
	PYTHONPATH=src python -m signal_pipeline run --config config/pipeline.example.json --date 2026-08-30 --mode dry-run --state-file state/local-state.json --output-dir artifacts/demo
