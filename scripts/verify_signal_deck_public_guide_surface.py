#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "SIGNAL_DECK.md"
CHECK_FILES = (
    ROOT / "README.md",
    ROOT / "BLACK_LEDGER_NEWSROOM.md",
    ROOT / "LIVING_WORLD.md",
    ROOT / "HORIZONS" / "table-pulse.md",
)
RECEIPT = ROOT / "CHUMMER6_GUIDE_GENERATOR_REGISTRY_ALIGNMENT.generated.json"


def main() -> int:
    if TARGET.exists():
        print("SIGNAL_DECK.md should not be present in the public guide", file=sys.stderr)
        return 1
    failures: list[str] = []
    forbidden = ("Signal Deck", "SIGNAL_DECK.md", "/signal-deck")
    for path in CHECK_FILES:
        text = path.read_text(encoding="utf-8")
        for marker in forbidden:
            if marker in text:
                failures.append(f"{path.relative_to(ROOT)} still contains {marker!r}")
    receipt_text = RECEIPT.read_text(encoding="utf-8")
    for marker in ('"id": "signal-deck"', '"public_guide_verdict": "design_canon_only"', '"representation_status": "omitted_with_receipt"'):
        if marker not in receipt_text:
            failures.append(f"receipt missing {marker}")
    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1
    print("signal_deck_public_guide_omission:ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
