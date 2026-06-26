#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HORIZON_INDEX = ROOT / "HORIZONS" / "README.md"
RUNBOOK_PRESS = ROOT / "HORIZONS" / "runbook-press.md"
RUNBOOK_IMAGE = ROOT / "assets" / "horizons" / "runbook-press.png"

REQUIRED = (
    "# Runbook Press",
    "Long-form publishing becomes something you can actually reuse instead of a ten-tool scramble.",
    "## When this helps",
    "Use this when campaign material grows past a recap and starts becoming a handout, primer, or small book.",
    "Creators should be able to turn accepted Chummer material into something readable without stitching ten tools together by hand.",
    "## Can I use it?",
    "There is an early version you can try.",
)

FORBIDDEN = (
    "Subscribr",
    "First Book ai",
    "source packet",
    "source pack",
    "webhook",
    "generated file",
    "machine-generated harness",
    "## How to use this",
    "Watch the RUNBOOK PRESS",
)


def main() -> int:
    failures: list[str] = []
    text = RUNBOOK_PRESS.read_text(encoding="utf-8") if RUNBOOK_PRESS.is_file() else ""
    index = HORIZON_INDEX.read_text(encoding="utf-8") if HORIZON_INDEX.is_file() else ""

    if "[Runbook Press](runbook-press.md)" not in index:
        failures.append("HORIZONS/README.md missing Runbook Press index entry")
    if not RUNBOOK_IMAGE.is_file():
        failures.append("assets/horizons/runbook-press.png is missing")
    for marker in REQUIRED:
        if marker not in text:
            failures.append(f"HORIZONS/runbook-press.md missing marker: {marker}")
    for marker in FORBIDDEN:
        if marker.lower() in text.lower():
            failures.append(f"HORIZONS/runbook-press.md contains forbidden marker: {marker}")

    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1

    print("runbook_press_public_guide_surface:ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
