#!/usr/bin/env python3
"""Phase 4 — verify Snowflake connectivity (local)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.snowflake_connection import healthcheck  # noqa: E402


def main() -> int:
    info = healthcheck()
    print(json.dumps(info, indent=2, default=str))
    return 0 if info.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
