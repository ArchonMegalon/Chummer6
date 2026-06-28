#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

PUBLIC_INTERNAL_MARKERS = (
    "public route",
    "connected lane",
    "control plane",
    "source packet",
    "source-of-truth",
    "canonical",
    "governed",
    "bounded",
    "truth",
    "proof",
    "receipt",
    "receipts",
    "posture",
    "projection",
    "generated.json",
    "ai harness",
    "public participation door",
    "product story",
    "expansion bets",
    "folded-in infrastructure",
    "can i use it now?",
    "read more:",
    "why players care",
    "where it stands",
    "next up:",
    "what you notice",
    "current limits",
    "open it at",
    "share it when someone needs",
    "provider branding",
    "unproven product claims",
    "chummer-owned",
    "community-ledger",
)


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _iter_public_markdown() -> list[Path]:
    ignored = {".git", ".pytest_cache", ".guide-internal"}
    source_owned_public_docs = {"SOURCE_BUILD_LINUX.md", "SOURCE_BUILD_MACOS.md"}
    return [
        path
        for path in sorted(ROOT.rglob("*.md"))
        if not any(part in ignored for part in path.relative_to(ROOT).parts)
        and path.name not in source_owned_public_docs
    ]


def main() -> int:
    failures: list[str] = []
    root_files = {path.name for path in ROOT.iterdir() if path.is_file()}

    for filename in root_files:
        if filename.endswith(".generated.json"):
            failures.append(f"root contains machine receipt: {filename}")
    if "FINAL_CHUMMER6_DOCS_GENERATION_VERDICT.md" in root_files:
        failures.append("root contains internal docs verdict")

    for markdown_path in _iter_public_markdown():
        text = markdown_path.read_text(encoding="utf-8").lower()
        relative_path = markdown_path.relative_to(ROOT)
        for marker in PUBLIC_INTERNAL_MARKERS:
            if marker in text:
                failures.append(f"{relative_path} contains internal/public-guide marker: {marker}")

    readme = _read("README.md")
    start_here = _read("START_HERE.md")
    horizons = _read("HORIZONS/README.md")
    onramp = _read("ONRAMP.md")
    runner_passport = _read("RUNNER_PASSPORT.md")
    living_world = _read("LIVING_WORLD.md")
    newsroom = _read("BLACK_LEDGER_NEWSROOM.md")

    required_readme = (
        "# Chummer6",
        "Build a Shadowrun runner",
        "honest pitch",
        "Start here if you just want the answer",
        "[Download](DOWNLOAD.md)",
        "[Status](STATUS.md)",
        "[From Chummer5a to Chummer6](FROM_CHUMMER5A_TO_CHUMMER6.md)",
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
        "Guide fit",
        "Short answers",
    )
    for marker in forbidden_readme:
        if marker.lower() in readme.lower():
            failures.append(f"README.md contains internal marker: {marker}")

    if "## I want to try it" not in start_here:
        failures.append("START_HERE.md does not lead with the try-it-now user path")
    if "[first session guide](ONRAMP.md)" not in start_here:
        failures.append("START_HERE.md does not route new/rusty users to the first session guide")
    if "starter help, not another grand product shelf" not in start_here:
        failures.append("START_HERE.md does not keep starter help out of product-area framing")
    if "overloaded-reader problem" not in start_here:
        failures.append("START_HERE.md does not acknowledge overloaded readers plainly")
    for stale_phrase in (
        "finger-count problem",
        "functioning fingers",
        "half your brain",
        "Character math is already solid",
        "gold-ready",
        "Release status is missing or stale",
        "portable package",
        "portable builds",
        "https://chummer.run/partizipate",
    ):
        combined_public_copy = "\n".join(
            [
                readme,
                start_here,
                _read("STATUS.md"),
                _read("DOWNLOAD.md"),
                _read("HELP.md"),
                _read("HOW_CAN_I_HELP.md"),
                _read("FROM_CHUMMER5A_TO_CHUMMER6.md"),
            ]
        )
        if stale_phrase.lower() in combined_public_copy.lower():
            failures.append(f"public guide contains stale or noisy phrase: {stale_phrase}")

    if "onramp.md" in horizons.lower() or "ONRAMP" in horizons:
        failures.append("HORIZONS/README.md still lists Onramp")
    if (ROOT / "HORIZONS" / "onramp.md").exists():
        failures.append("HORIZONS/onramp.md still exists")

    if "practical first-run guide" not in onramp:
        failures.append("ONRAMP.md does not read as starter help")
    if "horizon" in onramp.lower():
        failures.append("ONRAMP.md still drags the reader into Horizon taxonomy")
    if "guided-mastery horizon" in onramp.lower():
        failures.append("ONRAMP.md still uses horizon framing")

    route_card_markers = (
        "## Open it",
        "Open it at",
        "Share it when someone needs",
        "Live route:",
        "connected-lane proof",
        "public-safe watch package",
        "watch_package_posture",
        "## Watch and inspect",
        "Latest bulletins:",
        "Watch the episode:",
        "Read the transcript:",
        "Open supporting details:",
    )
    for filename, text in (
        ("RUNNER_PASSPORT.md", runner_passport),
        ("LIVING_WORLD.md", living_world),
        ("BLACK_LEDGER_NEWSROOM.md", newsroom),
    ):
        for marker in route_card_markers:
            if marker.lower() in text.lower():
                failures.append(f"{filename} still reads like a route card: {marker}")

    if "Can this runner sit at my table without turning setup into homework?" not in runner_passport:
        failures.append("RUNNER_PASSPORT.md does not lead with the GM/player decision")
    if "](https://chummer.run/passport)" not in runner_passport:
        failures.append("RUNNER_PASSPORT.md is missing the public Runner Passport link")
    if "A player sends one link for Kestrel" not in runner_passport:
        failures.append("RUNNER_PASSPORT.md is missing a concrete human example")
    if "keep the consequences together so the GM does not rebuild them from chat fragments" not in living_world:
        failures.append("LIVING_WORLD.md does not explain the real user benefit")
    if "## Where to watch" not in newsroom or "https://chummer.run/ledger/newsroom" not in newsroom:
        failures.append("BLACK_LEDGER_NEWSROOM.md does not give a clean viewer path")

    campaign_tools = _read("HORIZONS/README.md")
    for marker in (
        "This page is not a shelf for every named capability",
        "Base-client support work belongs in [Features](../FEATURES/README.md)",
        "[Origin Dossier](origin-dossier.md)",
        "[Table Pulse](table-pulse.md)",
    ):
        if marker not in campaign_tools:
            failures.append(f"HORIZONS/README.md missing humanized campaign marker: {marker}")
    for marker in (
        "NEXUS-PAN",
        "Run Control",
        "Edition Studio",
        "Community Hub",
        "Ghostwire",
        "Local Co-Processor",
        "Quicksilver",
    ):
        if marker in campaign_tools:
            failures.append(f"HORIZONS/README.md still lists base-client feature: {marker}")
    features = _read("FEATURES/README.md")
    for marker in (
        "[NEXUS-PAN](nexus-pan.md)",
        "[Community Hub](community-hub.md)",
        "[Edition Studio](edition-studio.md)",
    ):
        if marker not in features:
            failures.append(f"FEATURES/README.md missing base-client feature marker: {marker}")

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
