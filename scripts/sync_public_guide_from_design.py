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
    "FROM_CHUMMER5A_TO_CHUMMER6.md",
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

START_HERE_BLOCK = """## Start here now

- [README](README.md)
- [STATUS](STATUS.md)
- [DOWNLOAD](DOWNLOAD.md)
- [HELP](HELP.md)

"""

WRAPPERS = {
    "START_HERE.md": """# Start Here

If you only want one answer fast, start with the question in front of you.

- I want to try Chummer6 right now: [Download](DOWNLOAD.md)
- I want the honest current picture: [Status](STATUS.md)
- I am moving from Chummer5a: [From Chummer5a to Chummer6](FROM_CHUMMER5A_TO_CHUMMER6.md)
- I want the two-minute product story: [What Chummer6 Is](WHAT_CHUMMER6_IS.md)
- I need help or want to report a problem: [Help](HELP.md) and [Contact](CONTACT.md)
- I only care about future ideas: [Horizons](HORIZONS/README.md)

You do not need the technical breakdown to decide whether Chummer6 is worth your time.
If you want that later, use [Where to go deeper](WHERE_TO_GO_DEEPER.md).
""",
    "WHAT_CHUMMER6_IS.md": """# What Chummer6 Is

Chummer6 is Shadowrun character software built around one simple idea: the answer should be visible, not mysterious.

The point is to help you:

- build a character without mystery math
- inspect why a pool or modifier changed
- keep continuity readable when devices or connectivity drift

This guide is here to help you decide quickly whether the current preview is real enough for you, whether the product fits how you play, and where to go for help next.

Start with [README.md](README.md), [Status](STATUS.md), and [Download](DOWNLOAD.md).
If you are coming from Chummer5a, also read [From Chummer5a to Chummer6](FROM_CHUMMER5A_TO_CHUMMER6.md).
If you want future ideas after that, use [Horizons](HORIZONS/README.md).
If you want the deeper technical map, use [Where To Go Deeper](WHERE_TO_GO_DEEPER.md).
""",
    "HOW_CAN_I_HELP.md": """# How Can I Help?

If you hit a bug, confusing rules math, or rough wording, start with the normal help path first.

- [Help](HELP.md) covers install help, updates, sign-in, and private crash reporting.
- [Contact](CONTACT.md) is the main place to report product trouble or give feedback.
- If you want to help more directly, there is also an optional guided contribution path at `/participate/codex`.
- Use the public issue tracker when you specifically want a public technical discussion: <https://github.com/ArchonMegalon/Chummer6/issues>

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

- [Horizons index](HORIZONS/README.md): future ideas and research.
- [Parts index](PARTS/README.md): the technical breakdown of the product.
- The design notes and code repositories carry the deeper planning and implementation trail once the public guide stops being enough.

The point of this guide is to save normal readers from having to reverse-engineer the project just to decide whether Chummer6 is for them.
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
- [../FROM_CHUMMER5A_TO_CHUMMER6.md](../FROM_CHUMMER5A_TO_CHUMMER6.md)
- [../STATUS.md](../STATUS.md)
- [../DOWNLOAD.md](../DOWNLOAD.md)
- [../HELP.md](../HELP.md)
- [../CONTACT.md](../CONTACT.md)

Use those pages as the current public reference set.
""",
    "UPDATES/README.md": """# Updates

This folder tracks notable public-guide refreshes for Chummer6.

## Start here now

- [../README.md](../README.md)
- [../STATUS.md](../STATUS.md)
- [../DOWNLOAD.md](../DOWNLOAD.md)
- [../HELP.md](../HELP.md)

Status, download, and help pages stay aligned with the current public guide.

## Latest substantial pushes

- The public guide now leads with a clearer product story, support paths, and first-contact art.
- The first-contact images have been refreshed to feel more like Shadowrun and less like placeholders.
- Status, download, and support pages now answer the practical user questions faster.

## Monthly archive

- Monthly refresh notes will live here as the public guide evolves.
- [2026-03](2026-03.md)
""",
    "UPDATES/2026-03.md": """# 2026-03

The March 2026 refresh sharpened the public guide for Chummer6.

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


START_HERE_TRANSFORMS = {
    "README.md": "\n## What Chummer6 is\n",
    "STATUS.md": "\n## Right now\n",
    "DOWNLOAD.md": "\n## What is available today\n",
    "HELP.md": "\n## If install or update goes sideways\n",
}

TEXT_REWRITES = {
    "DOWNLOAD.md": (),
}


def _render_with_start_here(src: Path, relative_path: str, anchor: str) -> str:
    if not src.exists():
        raise FileNotFoundError(src)
    source_text = src.read_text(encoding="utf-8")
    for old, new in TEXT_REWRITES.get(relative_path, ()):
        source_text = source_text.replace(old, new)
    if START_HERE_BLOCK in source_text:
        return source_text if source_text.endswith("\n") else source_text + "\n"
    if anchor not in source_text:
        raise ValueError(f"unable to place Start here block in {src}")
    rendered = source_text.replace(anchor, f"\n{START_HERE_BLOCK}{anchor.lstrip()}", 1)
    return rendered if rendered.endswith("\n") else rendered + "\n"


def _sync_transformed_file(
    src: Path,
    dest: Path,
    anchor: str,
    check: bool,
    failures: list[str],
) -> None:
    if not src.exists():
        failures.append(f"missing source file: {src}")
        return
    try:
        expected = _render_with_start_here(src, dest.name, anchor)
    except (FileNotFoundError, ValueError) as exc:
        failures.append(str(exc))
        return
    if check:
        if not dest.exists():
            failures.append(f"missing destination file: {dest}")
            return
        actual = dest.read_text(encoding="utf-8")
        if actual != expected:
            failures.append(f"file drift: {dest} != rendered {src}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(expected, encoding="utf-8")


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

    for relative_path, anchor in START_HERE_TRANSFORMS.items():
        _sync_transformed_file(
            source_root / relative_path,
            REPO_ROOT / relative_path,
            anchor,
            args.check,
            failures,
        )

    for relative_path in SYNC_FILES:
        if relative_path in START_HERE_TRANSFORMS:
            continue
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
