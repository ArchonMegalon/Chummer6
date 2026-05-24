#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JACKPOINT = ROOT / "HORIZONS" / "jackpoint.md"
RUNSITE = ROOT / "HORIZONS" / "runsite.md"

JACKPOINT_REQUIRED = (
    "- Today: Signed-in command lane is live.",
    "- Next: Expand bounded coaching and fallout follow-through.",
    "The signed-in command lane is already live at `https://chummer.run/jackpoint`.",
    "That lane currently carries first-party briefing packets on real markdown and JSON routes without pretending the whole long-form publishing roadmap is done.",
)

RUNSITE_REQUIRED = (
    "- Today: Signed-in command lane is live.",
    "- Next: Expand bounded coaching and fallout follow-through.",
    "The signed-in command lane is already live at `https://chummer.run/runsites`.",
    "That lane currently carries first-party runsite packs on real markdown and JSON routes without pretending the whole spatial roadmap is done.",
)


def _check(path: Path, required: tuple[str, ...], failures: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    for marker in required:
        if marker not in text:
            failures.append(f"{path.name} missing marker: {marker}")


def main() -> int:
    failures: list[str] = []
    _check(JACKPOINT, JACKPOINT_REQUIRED, failures)
    _check(RUNSITE, RUNSITE_REQUIRED, failures)
    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1
    print("packet_lane_public_guide_surface:ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
