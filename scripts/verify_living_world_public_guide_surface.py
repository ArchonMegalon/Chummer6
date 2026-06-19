#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "LIVING_WORLD.md"
REQUIRED = (
    "# Living World",
    "## When you use it",
    "[chummer.run/living-world](https://chummer.run/living-world)",
    "keep the consequences together so the GM does not rebuild them from chat fragments",
    "## What it gives the table",
    "Runner Passport continuity",
    "half a brain's worth of memory",
    "## What it is not",
    "It does not replace the GM, reveal secrets, or run the campaign by itself.",
)
FORBIDDEN = (
    "## Open it",
    "Open it at",
    "Live route:",
    "public-safe watch package",
    "watch_package_posture",
    "governed aftermath return loops",
)


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    missing = [marker for marker in REQUIRED if marker not in text]
    forbidden = [marker for marker in FORBIDDEN if marker.lower() in text.lower()]
    if missing:
        for marker in missing:
            print(f"LIVING_WORLD.md missing marker: {marker}", file=sys.stderr)
        return 1
    if forbidden:
        for marker in forbidden:
            print(f"LIVING_WORLD.md still contains route-card marker: {marker}", file=sys.stderr)
        return 1
    print("living_world_public_guide_surface:ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
