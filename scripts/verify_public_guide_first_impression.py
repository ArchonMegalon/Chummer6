#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def main() -> int:
    failures: list[str] = []
    root_files = {path.name for path in ROOT.iterdir() if path.is_file()}

    for filename in root_files:
        if filename.endswith(".generated.json"):
            failures.append(f"root contains machine receipt: {filename}")
    if "FINAL_CHUMMER6_DOCS_GENERATION_VERDICT.md" in root_files:
        failures.append("root contains internal docs verdict")

    readme = _read("README.md")
    start_here = _read("START_HERE.md")
    horizons = _read("HORIZONS/README.md")
    onramp = _read("ONRAMP.md")

    required_readme = (
        "# Chummer6",
        "Build a Shadowrun runner",
        "[Start Here](START_HERE.md)",
        "[Onramp](ONRAMP.md)",
        "[Campaign tools](HORIZONS/README.md)",
    )
    for marker in required_readme:
        if marker not in readme:
            failures.append(f"README.md missing visitor-first marker: {marker}")

    forbidden_readme = (
        "# Chummer Public Guide",
        "clear public proof",
        "whole-product gold claim",
        "generated.json",
        "FINAL_CHUMMER6_DOCS_GENERATION_VERDICT",
    )
    for marker in forbidden_readme:
        if marker.lower() in readme.lower():
            failures.append(f"README.md contains internal marker: {marker}")

    if "## I am new or rusty" not in start_here:
        failures.append("START_HERE.md does not lead with the new/rusty user path")
    if "Start here: [Onramp](ONRAMP.md)" not in start_here:
        failures.append("START_HERE.md does not route new/rusty users to Onramp")

    if "onramp.md" in horizons.lower() or "ONRAMP" in horizons:
        failures.append("HORIZONS/README.md still lists Onramp")
    if (ROOT / "HORIZONS" / "onramp.md").exists():
        failures.append("HORIZONS/onramp.md still exists")

    if "It is not a horizon" not in onramp:
        failures.append("ONRAMP.md does not explicitly classify Onramp outside Horizons")
    if "guided-mastery horizon" in onramp.lower():
        failures.append("ONRAMP.md still uses horizon framing")

    internal_receipts = ROOT / ".guide-internal" / "receipts"
    for filename in (
        "CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json",
        "CHUMMER6_GUIDE_GENERATOR_REGISTRY_ALIGNMENT.generated.json",
        "FINAL_CHUMMER6_DOCS_GENERATION_VERDICT.md",
    ):
        if not (internal_receipts / filename).is_file():
            failures.append(f"missing internal receipt: {filename}")

    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1
    print("public_guide_first_impression:ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
