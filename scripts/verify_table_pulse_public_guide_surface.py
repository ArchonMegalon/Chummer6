#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TABLE_PULSE_PATH = REPO_ROOT / "HORIZONS" / "table-pulse.md"


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> int:
    if not TABLE_PULSE_PATH.is_file():
        raise FileNotFoundError(TABLE_PULSE_PATH)
    text = _load_text(TABLE_PULSE_PATH)

    for needle in (
        "- Today: Signed-in command lane is live.",
        "- Next: Expand bounded coaching and fallout follow-through.",
        "live heat-and-reaction rail today and a separate private aftermath coaching rail",
        "## The two rails",
        "### Table Pulse Live",
        "### Table Pulse Aftermath",
        "### World heat",
        "### Table-dynamics heat",
        "## What is live now",
        "Table Pulse Live on the signed-in command lane",
        "Black Ledger notifications route",
        "bounded remote reaction mini-games",
        "Living Newsroom watch framing",
        "governed aftermath return loops",
        "GM-private",
        "not surveillance",
    ):
        if needle not in text:
            raise ValueError(f"Table Pulse guide is missing connected-lane proof: {needle}")

    print("table_pulse_public_guide_surface:ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
