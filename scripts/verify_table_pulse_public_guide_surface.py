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
        "# Table Pulse",
        "GMs get a live heat-and-reaction tool today, plus private aftermath notes that stay away from player scoring.",
        "Use Table Pulse when the table needs live pressure without a surveillance dashboard.",
        "Private aftermath, remote reactions, quiet hours, and opt-outs are part of the feature",
        "## The table problem",
        "## Can I use it?",
        "Parts of this already exist after sign-in",
        "https://chummer.run/media/horizons/table-pulse-90s-deepdive.mp4",
        "without a surveillance dashboard",
    ):
        if needle not in text:
            raise ValueError(f"Table Pulse guide is missing humanized marker: {needle}")
    for forbidden in ("signed-in command lane", "connected-lane proof", "governed aftermath", "bounded remote reaction"):
        if forbidden in text:
            raise ValueError(f"Table Pulse guide still contains internal marker: {forbidden}")

    print("table_pulse_public_guide_surface:ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
