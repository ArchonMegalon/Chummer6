#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BLACK_LEDGER = ROOT / "HORIZONS" / "black-ledger.md"
README = ROOT / "README.md"
HORIZONS_INDEX = ROOT / "HORIZONS" / "README.md"
NEWSROOM = ROOT / "BLACK_LEDGER_NEWSROOM.md"

FORBIDDEN = (
    "Open the Black Ledger command map",
    "[BLACK LEDGER](black-ledger.md)",
    "[Black Ledger](HORIZONS/black-ledger.md)",
    "[Black Ledger Newsroom](BLACK_LEDGER_NEWSROOM.md)",
    "## Watch and inspect",
    "Latest bulletins:",
    "Watch the episode:",
    "Read the transcript:",
    "Open supporting details:",
    "## Hard boundaries",
)


def main() -> int:
    failures: list[str] = []

    if BLACK_LEDGER.exists():
        failures.append("HORIZONS/black-ledger.md should stay out of the public guide until Black Ledger is ready.")

    checked_files = (README, HORIZONS_INDEX, NEWSROOM)
    for path in checked_files:
        text = path.read_text(encoding="utf-8")
        for marker in FORBIDDEN:
            if marker in text:
                failures.append(f"{path.relative_to(ROOT)} still exposes Black Ledger primary navigation: {marker}")

    newsroom_text = NEWSROOM.read_text(encoding="utf-8")
    for marker in (
        "## Where to watch",
        "https://chummer.run/ledger/newsroom",
        "## What to look for",
        "## What stays out",
    ):
        if marker not in newsroom_text:
            failures.append(f"BLACK_LEDGER_NEWSROOM.md is missing visitor-facing marker: {marker}")

    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1

    print("black_ledger_public_guide_visibility:ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
