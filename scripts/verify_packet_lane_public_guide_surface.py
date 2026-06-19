#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JACKPOINT = ROOT / "HORIZONS" / "jackpoint.md"
RUNSITE = ROOT / "HORIZONS" / "runsite.md"

JACKPOINT_REQUIRED = (
    "# Jackpoint",
    "Use this when a recap, dossier, or briefing needs to look finished enough to share.",
    "The writing can be polished, but the facts still have to come from the session material the GM accepted.",
    "## The table problem",
    "## Can I use it?",
    "https://chummer.run/media/horizons/jackpoint-90s-deepdive.mp4",
)

RUNSITE_REQUIRED = (
    "# Runsite",
    "Use this before a mission when the players keep misreading the space.",
    "It is not a VTT replacement.",
    "## The table problem",
    "## Can I use it?",
    "https://chummer.run/media/horizons/runsite-90s-deepdive.mp4",
)


def _check(path: Path, required: tuple[str, ...], failures: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    for marker in required:
        if marker not in text:
            failures.append(f"{path.name} missing marker: {marker}")
    for marker in ("signed-in command lane", "first-party briefing packets", "JSON routes", "connected-lane proof"):
        if marker in text:
            failures.append(f"{path.name} still contains internal marker: {marker}")


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
