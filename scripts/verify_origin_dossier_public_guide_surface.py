#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HORIZON_INDEX = ROOT / "HORIZONS" / "README.md"
ORIGIN_DOSSIER = ROOT / "HORIZONS" / "origin-dossier.md"
ORIGIN_IMAGE = ROOT / "assets" / "horizons" / "origin-dossier.png"

REQUIRED = (
    "# ORIGIN DOSSIER",
    "The player gets approved origin canon, dossier media, and later ALICE context without letting story prose rewrite the sheet.",
    "The desktop ALICE workbench already exposes `Origin Dossier` as a named mode beside `Build help` and `Rules coach`.",
    "That makes Origin Dossier more than a subfeature of ALICE.",
    "Origin Dossier is the runner identity, approval, and media-packet lane that ALICE can reference after the player or GM approves it.",
    "If the player asks for it, the approved origin story can also become an audiobook through EA's governed audiobook lane.",
    "gives Chummer only a scoped reference for that player and runner.",
    "That reference is not a global Audiobookshelf login, admin token, raw pCloud path, or access to another player's library.",
    "ALICE may open the player's scoped origin-story audiobook when the approved dossier has one.",
    "ALICE must not treat dossier prose as permission to auto-apply ware, nuyen, qualities, addiction, magic, or availability exceptions.",
    "Origin canon can guide suggestions. It cannot overrule the engine.",
    "The media is downstream.",
)

FORBIDDEN = (
    "AI harness",
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

    if "- [ORIGIN DOSSIER](origin-dossier.md)" not in index:
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
