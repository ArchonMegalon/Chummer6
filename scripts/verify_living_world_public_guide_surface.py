#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "LIVING_WORLD.md"
REQUIRED = (
    "# Living World",
    "- Live route: `/living-world`",
    "Living World now connects cleanly to:",
    "- the public-safe watch package",
    "- the signed-in Table Pulse inbox",
    "- leader briefing and faction command",
    "- Runner Passport continuity",
    "- governed aftermath return loops",
    "- `/living-world/receipts/watch_package_posture.md`",
)


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    missing = [marker for marker in REQUIRED if marker not in text]
    if missing:
        for marker in missing:
            print(f"LIVING_WORLD.md missing marker: {marker}", file=sys.stderr)
        return 1
    print("living_world_public_guide_surface:ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
