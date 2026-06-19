#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HORIZON_INDEX = ROOT / "HORIZONS" / "README.md"
ORIGIN_DOSSIER = ROOT / "HORIZONS" / "origin-dossier.md"
ORIGIN_IMAGE = ROOT / "assets" / "horizons" / "origin-dossier.png"

REQUIRED = (
    "# Origin Dossier",
    "The player gets an accepted origin story, portraits, narration, and later ALICE context without letting backstory prose rewrite the sheet.",
    "## When this helps",
    "Open Origin Dossier when a legal sheet still feels unfinished as a person.",
    "contacts, debts, enemies, scars, secrets, portraits, narration",
    "the accepted origin can become a private audiobook for that runner",
    "EA-issued player link",
    "must never rewrite the sheet",
    "global Audiobookshelf login",
    "decide who the character is",
    "## Can I use it?",
    "There is an early version you can try.",
)

FORBIDDEN = (
    "approved origin canon",
    "dossier media",
    "## How to use this",
    "machine-generated harness",
    "generated file",
    "MagicFit rendered video",
    "Watch the ORIGIN DOSSIER",
    "may auto-apply",
    "can auto-apply",
    "Audiobookshelf admin token",
    "global Audiobookshelf login for the desktop",
)


def main() -> int:
    failures: list[str] = []
    text = ORIGIN_DOSSIER.read_text(encoding="utf-8") if ORIGIN_DOSSIER.is_file() else ""
    index = HORIZON_INDEX.read_text(encoding="utf-8") if HORIZON_INDEX.is_file() else ""

    if "[Origin Dossier](origin-dossier.md)" not in index:
        failures.append("HORIZONS/README.md missing ORIGIN DOSSIER index entry")
    if not ORIGIN_IMAGE.is_file():
        failures.append("assets/horizons/origin-dossier.png is missing")
    for marker in REQUIRED:
        if marker not in text:
            failures.append(f"HORIZONS/origin-dossier.md missing marker: {marker}")
    for marker in FORBIDDEN:
        if marker.lower() in text.lower():
            failures.append(f"HORIZONS/origin-dossier.md contains forbidden marker: {marker}")

    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1

    print("origin_dossier_public_guide_surface:ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
