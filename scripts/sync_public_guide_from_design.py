#!/usr/bin/env python3
from __future__ import annotations

import argparse
import filecmp
import json
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

OPTIONAL_SYNC_FILES = ("GLOSSARY.md",)
OPTIONAL_SYNC_DIRS = ("NOW", "UPDATES")

START_HERE_BLOCKS = {}

WRAPPERS = {}


def _copy_file(src: Path, dest: Path, check: bool, failures: list[str], optional: bool = False) -> None:
    if not src.exists():
        if optional:
            return
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


def _render_manifest(src: Path) -> str:
    if not src.exists():
        raise FileNotFoundError(src)
    manifest = json.loads(src.read_text(encoding="utf-8"))
    generated_from = manifest.get("generated_from")
    if isinstance(generated_from, str):
        # Normalize path separators and harmless dot prefixes before trimming to
        # the repo-relative products/chummer manifest path.
        parts = [part for part in generated_from.replace("\\", "/").split("/") if part and part != "."]
        for index in range(len(parts) - 1):
            if parts[index] == "products" and parts[index + 1] == "chummer":
                manifest["generated_from"] = "/".join(parts[index:])
                break
    return json.dumps(manifest, indent=2) + "\n"


START_HERE_TRANSFORMS = {
    "STATUS.md": ("\n## Current picture\n", "\n## Right now\n"),
    "DOWNLOAD.md": ("\n## Current public download\n", "\n## Current preview shelf\n", "\n## What is available today\n"),
    "HELP.md": ("\n## Start with the release page and download help\n", "\n## If install or update goes sideways\n"),
    "FAQ.md": "",
}

TEXT_REWRITES = {}


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


def _sync_manifest_file(
    src: Path,
    dest: Path,
    check: bool,
    failures: list[str],
) -> None:
    if not src.exists():
        failures.append(f"missing source file: {src}")
        return
    try:
        expected = _render_manifest(src)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
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


def _sync_dir(src: Path, dest: Path, check: bool, failures: list[str], optional: bool = False) -> None:
    if not src.exists():
        if optional:
            return
        failures.append(f"missing source directory: {src}")
        return
    if check:
        if not dest.exists():
            failures.append(f"missing destination directory: {dest}")
            return
        src_files = sorted(path.relative_to(src) for path in src.rglob("*") if path.is_file())
        for relative_path in src_files:
            if not (dest / relative_path).exists():
                failures.append(f"missing destination file: {dest / relative_path}")
                continue
            if not filecmp.cmp(src / relative_path, dest / relative_path, shallow=False):
                failures.append(f"file drift: {dest / relative_path} != {src / relative_path}")
        return
    if dest.exists():
        if not dest.is_dir():
            failures.append(f"destination path is not a directory: {dest}")
            return
    else:
        dest.mkdir(parents=True, exist_ok=True)
    for source_file in src.rglob("*"):
        relative_path = source_file.relative_to(src)
        destination_file = dest / relative_path
        if source_file.is_dir():
            destination_file.mkdir(parents=True, exist_ok=True)
            continue
        destination_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, destination_file)


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
        if relative_path == "manifest.generated.json":
            _sync_manifest_file(source_root / relative_path, REPO_ROOT / relative_path, args.check, failures)
            continue
        if relative_path in TEXT_REWRITES:
            _sync_rendered_file(source_root / relative_path, REPO_ROOT / relative_path, args.check, failures)
            continue
        _copy_file(
            source_root / relative_path,
            REPO_ROOT / relative_path,
            args.check,
            failures,
            optional=relative_path in OPTIONAL_SYNC_FILES,
        )

    for relative_path in SYNC_DIRS:
        _sync_dir(
            source_root / relative_path,
            REPO_ROOT / relative_path,
            args.check,
            failures,
            optional=relative_path in OPTIONAL_SYNC_DIRS,
        )

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
