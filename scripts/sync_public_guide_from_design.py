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

START_HERE_BLOCKS = {
    "STATUS.md": "Quick links: [Home](README.md) | [Download](DOWNLOAD.md) | [Help](HELP.md)\n\n",
    "DOWNLOAD.md": "Quick links: [Home](README.md) | [Status](STATUS.md) | [Help](HELP.md)\n\n",
    "HELP.md": "Quick links: [Home](README.md) | [Status](STATUS.md) | [Download](DOWNLOAD.md)\n\n",
}

WRAPPERS = {
    "START_HERE.md": """# Start Here

If you only want one answer fast, start with the question in front of you.

- I want to try Chummer6 right now: [Download](DOWNLOAD.md)
- I want the honest current picture: [Status](STATUS.md)
- I am moving from Chummer5a: [From Chummer5a to Chummer6](FROM_CHUMMER5A_TO_CHUMMER6.md)
- I want the two-minute product story: [What Chummer6 Is](WHAT_CHUMMER6_IS.md)
- I need help or want to report a problem: [Help](HELP.md) and [Contact](CONTACT.md)
- I only care about future ideas: [Horizons](HORIZONS/README.md)

You do not need the deeper breakdown to decide whether Chummer6 is worth your time.
If you want that later, use [Where to go deeper](WHERE_TO_GO_DEEPER.md).
""",
    "WHAT_CHUMMER6_IS.md": """# What Chummer6 Is

Chummer6 is Shadowrun character software built around one simple idea: the answer should be visible, not mysterious.

The point is to help you:

- build a character without mystery math
- inspect why a pool or modifier changed
- keep continuity readable when devices or connectivity drift

This guide is here to help you decide quickly whether Chummer6 is worth your time right now and where to go for help next.

Start with [README.md](README.md), [Status](STATUS.md), and [Download](DOWNLOAD.md).
If you are coming from Chummer5a, also read [From Chummer5a to Chummer6](FROM_CHUMMER5A_TO_CHUMMER6.md).
If you want future ideas after that, use [Horizons](HORIZONS/README.md).
If you want the deeper guide after that, use [Where To Go Deeper](WHERE_TO_GO_DEEPER.md).
""",
    "HOW_CAN_I_HELP.md": """# How Can I Help?

If you hit a bug, confusing rules math, or rough wording, start with the normal help path first.

- [Help](HELP.md) covers install help, updates, sign-in, and private crash reporting.
- [Contact](CONTACT.md) is the main place to report product trouble or give feedback.
- If you want to help more directly, there is also an optional guided contribution and booster path at <https://chummer.run/participate>.
- Use the public issue tracker when you specifically want a public bug thread: <https://github.com/ArchonMegalon/Chummer6/issues>

## Participation safety

- the cheap baseline remains the default path
- guided contribution is not a merge bypass
- final landing still goes through review
- people can stop or revoke later
- private recognition settings remain valid even when badges or leaderboards exist

Some guided-preview lanes are resource-heavy today, but the long-run intent is free later rather than keeping the useful parts locked behind a permanent paywall.

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

Go deeper only when you want more than the main public pages:

- [Horizons index](HORIZONS/README.md): future ideas and experiments.
- [Parts index](PARTS/README.md): an inside view of how the app is put together.
- Most readers can stop there. The rest of the repo is only for people who want extra detail.

The point of this guide is that normal readers should not have to dig through internal detail just to decide whether Chummer6 is for them.
""",
    "NOW/current-phase.md": """# Current Phase

The current public status lives in the main guide.

Read [../STATUS.md](../STATUS.md) for the current product picture and [../DOWNLOAD.md](../DOWNLOAD.md) for the current release shelf.
""",
    "NOW/current-status.md": """# Current Status

The current public status page lives at [../STATUS.md](../STATUS.md).

Use that page for the current picture, release status, and help links.
""",
    "NOW/public-surfaces.md": """# Public Surfaces

If you only want the main public pages, use these:

- [../README.md](../README.md)
- [../FROM_CHUMMER5A_TO_CHUMMER6.md](../FROM_CHUMMER5A_TO_CHUMMER6.md)
- [../STATUS.md](../STATUS.md)
- [../DOWNLOAD.md](../DOWNLOAD.md)
- [../HELP.md](../HELP.md)
- [../CONTACT.md](../CONTACT.md)

Those pages are the main public guide.
""",
    "UPDATES/README.md": """# Updates

This folder keeps short notes on the bigger guide refreshes.

## Start with the live pages

- [../README.md](../README.md)
- [../STATUS.md](../STATUS.md)
- [../DOWNLOAD.md](../DOWNLOAD.md)
- [../HELP.md](../HELP.md)

If you only care about what works right now, those pages matter more than this archive.

## Latest substantial pushes

- The front door now answers the basic product questions faster.
- The cover art is stronger and less placeholder-looking than before.
- Status, download, and help pages are easier to skim when you just want an answer.

## Monthly archive

- [2026-03](2026-03.md)
""",
    "UPDATES/2026-03.md": """# 2026-03

This archive note marks the March 2026 pass that pushed the guide toward a clearer product-facing front door.

For the live version instead of the archive, start with:

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
    "STATUS.md": ("\n## Current picture\n", "\n## Right now\n"),
    "DOWNLOAD.md": ("\n## Current public download\n", "\n## Current preview shelf\n", "\n## What is available today\n"),
    "HELP.md": ("\n## Start with the release page and download help\n", "\n## If install or update goes sideways\n"),
    "FAQ.md": "",
}

TEXT_REWRITES = {
    "README.md": (
        (
            "- [From Chummer5a to Chummer6](FROM_CHUMMER5A_TO_CHUMMER6.md)\n- [How can I help](HOW_CAN_I_HELP.md)\n- [From Chummer5a to Chummer6](FROM_CHUMMER5A_TO_CHUMMER6.md)\n",
            "- [From Chummer5a to Chummer6](FROM_CHUMMER5A_TO_CHUMMER6.md)\n- [How can I help](HOW_CAN_I_HELP.md)\n",
        ),
    ),
    "DOWNLOAD.md": (),
    "FAQ.md": (
        (
            "## If you want the behind-the-scenes details",
            "## If you want more detail",
        ),
        (
            "In the planning notes that shape the roadmap and the public guide.",
            "Start with [Where To Go Deeper](WHERE_TO_GO_DEEPER.md). It points to the optional deeper guide pages without sending most readers through internal planning material first.",
        ),
    ),
}


def _render_with_start_here(src: Path, relative_path: str, anchor: str) -> str:
    if not src.exists():
        raise FileNotFoundError(src)
    source_text = src.read_text(encoding="utf-8")
    for old, new in TEXT_REWRITES.get(relative_path, ()):
        source_text = source_text.replace(old, new)
    start_here_block = START_HERE_BLOCKS.get(relative_path, "")
    if not start_here_block:
        return source_text if source_text.endswith("\n") else source_text + "\n"
    if start_here_block in source_text:
        return source_text if source_text.endswith("\n") else source_text + "\n"
    anchors = anchor if isinstance(anchor, tuple) else (anchor,)
    selected_anchor = next((candidate for candidate in anchors if candidate in source_text), "")
    if not selected_anchor:
        raise ValueError(f"unable to place Start here block in {src}")
    rendered = source_text.replace(selected_anchor, f"\n{start_here_block}{selected_anchor.lstrip()}", 1)
    return rendered if rendered.endswith("\n") else rendered + "\n"


def _sync_rendered_file(
    src: Path,
    dest: Path,
    check: bool,
    failures: list[str],
) -> None:
    if not src.exists():
        failures.append(f"missing source file: {src}")
        return
    try:
        expected = _render_with_start_here(src, dest.name, "")
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
        if relative_path in TEXT_REWRITES:
            _sync_rendered_file(source_root / relative_path, REPO_ROOT / relative_path, args.check, failures)
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
