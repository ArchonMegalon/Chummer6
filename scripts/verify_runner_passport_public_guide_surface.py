#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
README_PATH = REPO_ROOT / "README.md"
PASSPORT_PATH = REPO_ROOT / "RUNNER_PASSPORT.md"
VERDICT_PATH = REPO_ROOT / ".guide-internal" / "receipts" / "FINAL_CHUMMER6_DOCS_GENERATION_VERDICT.md"


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> int:
    if not PASSPORT_PATH.is_file():
        raise FileNotFoundError(PASSPORT_PATH)
    readme = _load_text(README_PATH)
    passport = _load_text(PASSPORT_PATH)
    verdict = _load_text(VERDICT_PATH)

    if "[Runner Passport](RUNNER_PASSPORT.md)" not in readme:
        raise ValueError("README.md is missing the Runner Passport route")
    if "`runner-passport`: `public_route_live` -> `public_route_live_page`" not in verdict:
        raise ValueError("docs verdict does not recognize Runner Passport as a live public page")
    for needle in (
        "## Connected lane",
        "signed-in Table Pulse inbox",
        "Living Newsroom watch framing",
        "governed aftermath return loops",
    ):
        if needle not in passport:
            raise ValueError(f"Runner Passport guide is missing connected-lane proof: {needle}")

    print("runner_passport_public_guide_surface:ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
