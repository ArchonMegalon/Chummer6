#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
COMMUNITY_HUB = ROOT / "FEATURES" / "community-hub.md"

README_REQUIRED = (
    'href="https://chummer.run/media/promo/every-wonder-horizon-promo.mp4"',
    'src="assets/hero/chummer6-hero.png" alt="Chummer6 overview video preview"',
    "[Watch the Chummer6 overview video](https://chummer.run/media/promo/every-wonder-horizon-promo.mp4).",
)

COMMUNITY_HUB_REQUIRED = (
    "# Community Hub",
    "A GM opens a run, Chummer preflights the right players and rule environment, gets the table scheduled, and the world remembers the outcome.",
    "Use this when the hard part is no longer one legal character, but getting a real table together.",
    "A GM should be able to publish a beginner-friendly run and see who fits before the evening dissolves into chat archaeology.",
    "## The table problem",
    "## Can I use it?",
    "Parts of this already exist after sign-in",
    'href="https://chummer.run/media/horizons/community-hub-90s-deepdive.mp4"',
    '<img src="../assets/features/community-hub.png" alt="Community Hub video preview"',
)

FORBIDDEN = (
    "SHADOWCASTERS NETWORK",
    "Shadowcasters Network",
    "https://chummer.run/ledger#newsreel-player",
    "signed-in command lane",
    "governed open-run packets",
    "product name for that lane",
    "[Captions]",
    ".vtt",
    "<https://chummer.run",
)


def _require_markers(path: Path, markers: tuple[str, ...]) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [marker for marker in markers if marker not in text]


def main() -> int:
    failures: list[str] = []

    for marker in _require_markers(README, README_REQUIRED):
        failures.append(f"README.md missing marker: {marker}")
    for marker in _require_markers(COMMUNITY_HUB, COMMUNITY_HUB_REQUIRED):
        failures.append(f"FEATURES/community-hub.md missing marker: {marker}")

    readme_text = README.read_text(encoding="utf-8")
    community_text = COMMUNITY_HUB.read_text(encoding="utf-8")
    for marker in FORBIDDEN:
        if marker in readme_text:
            failures.append(f"README.md still contains forbidden marker: {marker}")
        if marker in community_text:
            failures.append(f"FEATURES/community-hub.md still contains forbidden marker: {marker}")

    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1

    print("community_hub_and_promo_surface:ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
