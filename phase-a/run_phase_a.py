"""CLI wrapper for Phase A artifacts generation and evaluation."""

from __future__ import annotations

import sys
from pathlib import Path

PHASE_DIR = Path(__file__).resolve().parent
if str(PHASE_DIR) not in sys.path:
    sys.path.insert(0, str(PHASE_DIR))

from phase_a import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())

