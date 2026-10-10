"""Compatibility entry point. Prefer: python -m orchestrator --manifest ..."""
from orchestrator.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
