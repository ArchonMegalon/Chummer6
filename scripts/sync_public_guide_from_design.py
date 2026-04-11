#!/usr/bin/env python3
from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPO_ROOT.parent / "chummer-design" / "products" / "chummer" / "public-guide"

SYNC_FILES = (
    "README.md",
    "STATUS.md",
    "DOWNLOAD.md",
    "HELP.md",
    "FAQ.md",
    "CONTACT.md",
    "manifest.generated.json",
)

SYNC_DIRS = (
    "PARTS",
    "HORIZONS",
    "TRUST",
    "assets",
)

WRAPPERS = {
    "START_HERE.md": """# Start Here

If you only want one answer fast, start with the question in front of you.

- I want to try Chummer6 right now: [Download](DOWNLOAD.md)
- I want the honest current picture: [Status](STATUS.md)
- I want the two-minute product story: [What Chummer6 Is](WHAT_CHUMMER6_IS.md)
- I need help or want to report a problem: [Help](HELP.md) and [Contact](CONTACT.md)
- I only care about future ideas: [Horizons](HORIZONS/README.md)

You do not need the parts map to decide whether Chummer6 is relevant to you.
If you want the behind-the-scenes map after the friendly tour, use [Where to go deeper](WHERE_TO_GO_DEEPER.md).
""",
    "WHAT_CHUMMER6_IS.md": """# What Chummer6 Is

Chummer6 is Shadowrun character software built around one public promise: the answer should be visible, not mysterious.

The point is to help you:

- build a character without mystery math
- inspect why a pool or modifier changed
- keep continuity readable when devices or connectivity drift

This repo should help you decide quickly whether the current preview is real enough for you, whether the product fits how you play, and where to go for help next.

Start with [README.md](README.md), [Status](STATUS.md), and [Download](DOWNLOAD.md).
If you want future bets after that, use [Horizons](HORIZONS/README.md).
If you want the behind-the-scenes map, use [Where To Go Deeper](WHERE_TO_GO_DEEPER.md).
""",
    "HOW_CAN_I_HELP.md": """# How Can I Help?

Use the first-party path that matches the kind of help you need.

- [Help](HELP.md) explains install support, private crash reporting, and participation guidance.
- [Contact](CONTACT.md) is the first-party intake for practical product trouble and feedback.
- The public issue tracker is still available when you intentionally want a public technical trail: <https://github.com/ArchonMegalon/Chummer6/issues>

If you want the short product picture before opening anything, read [What Chummer6 Is](WHAT_CHUMMER6_IS.md) and [Status](STATUS.md).
""",
    "WHERE_TO_GO_DEEPER.md": """# Where To Go Deeper

If you are still deciding whether Chummer6 is useful to you, stay on the public guide first.

Start there:

- [README.md](README.md)
- [What Chummer6 Is](WHAT_CHUMMER6_IS.md)
- [Status](STATUS.md)
- [Download](DOWNLOAD.md)
- [Help](HELP.md)
- [FAQ](FAQ.md)
- [Contact](CONTACT.md)

Go deeper only when you want more than the friendly tour:

- [Horizons index](HORIZONS/README.md): future product bets and research lanes.
- [Parts index](PARTS/README.md)
- The design workspace and owning code repos carry the planning and implementation trail once the public guide stops being enough.

The point of this repo is to save normal readers from having to reverse-engineer the product from internal project structure.
""",
    "NOW/current-phase.md": """# Current Phase

The current public status lives in the main guide.

Read [../STATUS.md](../STATUS.md) for the current product picture and [../DOWNLOAD.md](../DOWNLOAD.md) for the current release shelf.
""",
    "NOW/current-status.md": """# Current Status

The current public status page lives at [../STATUS.md](../STATUS.md).

Use that page for the current picture, release status, and first-party support guidance.
""",
    "NOW/public-surfaces.md": """# Public Surfaces

The core public guide pages in this repo are:

- [../README.md](../README.md)
- [../STATUS.md](../STATUS.md)
- [../DOWNLOAD.md](../DOWNLOAD.md)
- [../HELP.md](../HELP.md)
- [../CONTACT.md](../CONTACT.md)

Use those pages as the current public reference set.
""",
    "UPDATES/README.md": """# Updates

The March 2026 refresh sharpened this repo as a public guide surface for Chummer6.

## Start here now

- [../README.md](../README.md)
- [../STATUS.md](../STATUS.md)
- [../DOWNLOAD.md](../DOWNLOAD.md)
- [../HELP.md](../HELP.md)

Status, release, and help pages stay aligned with the current product guide.

## Latest substantial pushes

- The public guide now leads with a clearer product story, support paths, and first-contact trust surface.
- Flagship art direction is being tightened around short Shadowrun story beats plus anticipatory AR overlays that surface the next useful runner question.
- Status, horizons, and proof surfaces are being pushed toward a harder flagship bar instead of settling for placeholder preview language.

## Monthly archive

- Monthly update rollups and deeper push summaries will live here as the public proof trail thickens.
- [2026-03](2026-03.md)
""",
    "UPDATES/2026-03.md": """# 2026-03

The March 2026 refresh sharpened this repo as a public guide surface for Chummer6.

Start here now:

- [../README.md](../README.md)
- [../STATUS.md](../STATUS.md)
- [../DOWNLOAD.md](../DOWNLOAD.md)
- [../HELP.md](../HELP.md)
""",
}


def _copy_file(src: Path, dest: Path, check: bool, failures: list[str]) -> None:
    if not src.exists():
        failures.append(f"missing source file: {src}")
        return
    if check:
        if not dest.exists():
            failures.append(f"missing destination file: {dest}")
            return
        if not filecmp.cmp(src, dest, shallow=False):
            failures.append(f"file drift: {dest} != {src}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def _sync_dir(src: Path, dest: Path, check: bool, failures: list[str]) -> None:
    if not src.exists():
        failures.append(f"missing source directory: {src}")
        return
    if check:
        if not dest.exists():
            failures.append(f"missing destination directory: {dest}")
            return
        src_files = sorted(path.relative_to(src) for path in src.rglob("*") if path.is_file())
        dest_files = sorted(path.relative_to(dest) for path in dest.rglob("*") if path.is_file())
        if src_files != dest_files:
            failures.append(f"directory drift: {dest} file set != {src}")
            return
        for relative_path in src_files:
            if not filecmp.cmp(src / relative_path, dest / relative_path, shallow=False):
                failures.append(f"file drift: {dest / relative_path} != {src / relative_path}")
        return
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def _sync_wrapper(relative_path: str, content: str, check: bool, failures: list[str]) -> None:
    destination = REPO_ROOT / relative_path
    expected = content.rstrip() + "\n"
    if check:
        if not destination.exists():
            failures.append(f"missing wrapper file: {destination}")
            return
        actual = destination.read_text(encoding="utf-8")
        if actual != expected:
            failures.append(f"wrapper drift: {destination}")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(expected, encoding="utf-8")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Sync the Chummer6 public guide repo from the generated design public-guide bundle.",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help=f"Path to the generated design public-guide bundle (default: {DEFAULT_SOURCE})",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check whether the repo matches the source bundle and wrapper templates without modifying files.",
    )
    args = parser.parse_args(argv)

    source_root = args.source.resolve()
    failures: list[str] = []

    for relative_path in SYNC_FILES:
        _copy_file(source_root / relative_path, REPO_ROOT / relative_path, args.check, failures)

    for relative_path in SYNC_DIRS:
        _sync_dir(source_root / relative_path, REPO_ROOT / relative_path, args.check, failures)

    for relative_path, content in WRAPPERS.items():
        _sync_wrapper(relative_path, content, args.check, failures)

    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1

    print("public guide sync ok" if args.check else "public guide synced")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
