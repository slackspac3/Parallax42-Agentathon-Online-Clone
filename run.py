#!/usr/bin/env python3
"""Agentathon FastAPI entry point.

The product runtime remains the existing Node/CommonJS application. This file
starts the evaluator-facing FastAPI wrapper on 0.0.0.0:8000 by default and the
wrapper delegates deterministic case execution to the Node bridge.
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    try:
        port = int(os.environ.get("PORT", "8000"))
    except ValueError:
        sys.stderr.write("Invalid PORT value; expected an integer.\n")
        return 2

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        log_level=os.environ.get("UVICORN_LOG_LEVEL", "info"),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
