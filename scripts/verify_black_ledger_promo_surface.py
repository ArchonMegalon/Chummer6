#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BLACK_LEDGER = ROOT / "HORIZONS" / "black-ledger.md"

REQUIRED = (
    "## Faction promo rails",
    "BLACK LEDGER is not only a map and a board. It also has public-safe faction promo rails that show how each banner sells itself to the city.",
    "- Today: Signed-in command lane is live.",
    "- Next: Expand bounded coaching and fallout follow-through.",
    "* a first-party motion-video file",
    "* captions",
    "* a route-backed JSON brief",
    "* a storyboard fallback",
    "* a validation route back into the ledger",
)

FORBIDDEN = (
    "* a playable faction video",
)


def main() -> int:
    text = BLACK_LEDGER.read_text(encoding="utf-8")
    failures: list[str] = []

    for marker in REQUIRED:
        if marker not in text:
            failures.append(f"HORIZONS/black-ledger.md missing marker: {marker}")

    for marker in FORBIDDEN:
        if marker in text:
            failures.append(f"HORIZONS/black-ledger.md still contains forbidden marker: {marker}")

    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1

    print("black_ledger_promo_surface:ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
