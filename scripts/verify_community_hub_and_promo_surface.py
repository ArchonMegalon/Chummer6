#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
COMMUNITY_HUB = ROOT / "HORIZONS" / "community-hub.md"

README_REQUIRED = (
    "- [Watch the Chummer6 promo video](https://chummer.run/media/promo/chummer6-flagship-promo.mp4)",
)

COMMUNITY_HUB_REQUIRED = (
    "# COMMUNITY HUB",
    "A GM opens a run, Chummer preflights the right players and rule environment, gets the table scheduled, and the world remembers the outcome.",
    "- Today: Future concept.",
    "- Next: Research and prototypes.",
    "COMMUNITY HUB would turn BLACK LEDGER and campaign prep into a practical recruitment, scheduling, prep, and closeout layer.",
    "COMMUNITY HUB is the product name for that lane.",
    "Until those boundaries are strong enough, COMMUNITY HUB should remain a horizon rather than a shipped community promise.",
)

FORBIDDEN = (
    "SHADOWCASTERS NETWORK",
    "Shadowcasters Network",
    "https://chummer.run/ledger#newsreel-player",
)


def _require_markers(path: Path, markers: tuple[str, ...]) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [marker for marker in markers if marker not in text]


def main() -> int:
    failures: list[str] = []

    for marker in _require_markers(README, README_REQUIRED):
        failures.append(f"README.md missing marker: {marker}")
    for marker in _require_markers(COMMUNITY_HUB, COMMUNITY_HUB_REQUIRED):
        failures.append(f"HORIZONS/community-hub.md missing marker: {marker}")

    readme_text = README.read_text(encoding="utf-8")
    community_text = COMMUNITY_HUB.read_text(encoding="utf-8")
    for marker in FORBIDDEN:
        if marker in readme_text:
            failures.append(f"README.md still contains forbidden marker: {marker}")
        if marker in community_text:
            failures.append(f"HORIZONS/community-hub.md still contains forbidden marker: {marker}")

    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1

    print("community_hub_and_promo_surface:ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
