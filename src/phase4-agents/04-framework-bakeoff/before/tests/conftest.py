"""Fail on the interpreter, not four layers down inside Chroma.

The bakeoff is pinned to Python 3.12 by one of the three frameworks it compares.
Run it on 3.13 and the first thing you see is `unable to infer type for attribute
"chroma_server_nofile"` — a Pydantic v1 shim complaining about something you did
not write, in a library you did not install directly. That message has cost
people an hour each. This one costs a line.

`uv sync` honours the `requires-python` pin in `pyproject.toml`, so the venv is
already right; this guard is for the other way in — an interpreter you brought
yourself, running pytest directly.
"""

import sys

import pytest

REQUIRED = (3, 12)


def pytest_configure(config: pytest.Config) -> None:
    if sys.version_info[:2] != REQUIRED:
        running = ".".join(str(n) for n in sys.version_info[:3])
        raise pytest.UsageError(
            f"this lesson needs Python {REQUIRED[0]}.{REQUIRED[1]}; you are on {running}.\n"
            "CrewAI's tree does not build on anything newer — that bound is itself a "
            "finding for your matrix, and it is why this lesson pins where the rest of "
            "the course says 3.11+.\n"
            "Run `make setup` (uv reads requires-python and fetches 3.12), or "
            "`uv run --python 3.12 pytest`."
        )
