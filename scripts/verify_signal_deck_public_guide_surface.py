#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "SIGNAL_DECK.md"
REQUIRED = (
    "# Signal Deck",
    "- Live route: `/signal-deck`",
    "Signal Deck is the command-facing continuity rail for the signed-in Table Pulse loop.",
    "- the signed-in Table Pulse inbox",
    "- leader briefing and GM cockpit",
    "- Living Newsroom watch framing",
    "- governed aftermath return loops",
    "- Runner Passport continuity",
    "- `/signal-deck/receipts/pressure_posture.md`",
)


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    missing = [marker for marker in REQUIRED if marker not in text]
    if missing:
        for marker in missing:
            print(f"SIGNAL_DECK.md missing marker: {marker}", file=sys.stderr)
        return 1
    print("signal_deck_public_guide_surface:ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
