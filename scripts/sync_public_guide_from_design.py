#!/usr/bin/env python3
from __future__ import annotations

import argparse
import filecmp
import json
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_CANDIDATES = (
    REPO_ROOT.parent / "chummer-design" / "products" / "chummer" / "public-guide",
    REPO_ROOT.parent / "chummer-design-m114" / "products" / "chummer" / "public-guide",
)

SYNC_FILES = (
    "README.md",
    "START_HERE.md",
    "ONRAMP.md",
    "BLACK_LEDGER_NEWSROOM.md",
    "FROM_CHUMMER5A_TO_CHUMMER6.md",
    "WHAT_CHUMMER6_IS.md",
    "RUNNER_PASSPORT.md",
    "LIVING_WORLD.md",
    "STATUS.md",
    "DOWNLOAD.md",
    "SOURCE_BUILD_LINUX.md",
    "HELP.md",
    "FAQ.md",
    "HOW_CAN_I_HELP.md",
    "WHERE_TO_GO_DEEPER.md",
    "CONTACT.md",
    "GLOSSARY.md",
)

# These files are canonical in the Chummer6 repo and may be mirrored into the
# generated public-guide bundle, but the sync step must never overwrite them
# silently. If the generated bundle drifts from the owner copy, fail closed.
#
# Keep this set deliberately small and back every entry with a design-side
# maintenance note or equivalent ownership policy.
SOURCE_OWNED_SYNC_METADATA = {
    "SOURCE_BUILD_LINUX.md": {
        "policy": "products/chummer/maintenance/LINUX_SOURCE_BUILD_PATH.md",
        "reason": "Linux source-build behavior and user-facing instructions are owned in Chummer6.",
    },
}
SOURCE_OWNED_SYNC_FILES = frozenset(SOURCE_OWNED_SYNC_METADATA)

INTERNAL_SYNC_FILES = {
    "manifest.generated.json": ".guide-internal/manifest.generated.json",
    "CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json": ".guide-internal/receipts/CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json",
    "CHUMMER6_PUBLIC_GUIDE_TRUTH_AUDIT.generated.json": ".guide-internal/receipts/CHUMMER6_PUBLIC_GUIDE_TRUTH_AUDIT.generated.json",
    "CHUMMER6_PUBLIC_GUIDE_NEW_SECTIONS.generated.json": ".guide-internal/receipts/CHUMMER6_PUBLIC_GUIDE_NEW_SECTIONS.generated.json",
    "CHUMMER6_GUIDE_GENERATOR_REGISTRY_ALIGNMENT.generated.json": ".guide-internal/receipts/CHUMMER6_GUIDE_GENERATOR_REGISTRY_ALIGNMENT.generated.json",
    "FINAL_CHUMMER6_DOCS_GENERATION_VERDICT.md": ".guide-internal/receipts/FINAL_CHUMMER6_DOCS_GENERATION_VERDICT.md",
}

SYNC_DIRS = (
    "FEATURES",
    "PARTS",
    "HORIZONS",
    "TRUST",
    "assets",
)

OPTIONAL_SYNC_FILES = ()
OPTIONAL_SYNC_DIRS = ("NOW", "UPDATES")
REMOVABLE_SYNC_FILES = (
    "SIGNAL_DECK.md",
    "HORIZONS/onramp.md",
)

STALE_ROOT_FILES = (
    "manifest.generated.json",
    "CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json",
    "CHUMMER6_PUBLIC_GUIDE_TRUTH_AUDIT.generated.json",
    "CHUMMER6_PUBLIC_GUIDE_NEW_SECTIONS.generated.json",
    "CHUMMER6_GUIDE_GENERATOR_REGISTRY_ALIGNMENT.generated.json",
    "FINAL_CHUMMER6_DOCS_GENERATION_VERDICT.md",
)

WRAPPERS = {}


def _default_source() -> Path:
    for candidate in DEFAULT_SOURCE_CANDIDATES:
        if candidate.exists():
            return candidate
    return DEFAULT_SOURCE_CANDIDATES[0]


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


def _sync_source_owned_file(src: Path, dest: Path, check: bool, failures: list[str]) -> None:
    if not src.exists():
        failures.append(f"missing source file: {src}")
        return
    if not dest.exists():
        if check:
            failures.append(f"missing destination file: {dest}")
            return
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        return
    if not filecmp.cmp(src, dest, shallow=False):
        failures.append(f"source-owned file drift: {dest} != {src}")
        return


def _sync_removable_file(src: Path, dest: Path, check: bool, failures: list[str]) -> None:
    if not src.exists():
        if check:
            if dest.exists():
                failures.append(f"stale destination file: {dest}")
            return
        if dest.exists():
            dest.unlink()
        return
    _copy_file(src, dest, check, failures)


def _remove_stale_file(dest: Path, check: bool, failures: list[str]) -> None:
    if check:
        if dest.exists():
            failures.append(f"stale destination file: {dest}")
        return
    if dest.exists():
        dest.unlink()


def _remove_stale_dir(dest: Path, check: bool, failures: list[str]) -> None:
    if check:
        if dest.exists():
            failures.append(f"stale destination directory: {dest}")
        return
    if not dest.exists():
        return
    if not dest.is_dir():
        failures.append(f"destination path is not a directory: {dest}")
        return
    shutil.rmtree(dest)


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
        dest_files = sorted(path.relative_to(dest) for path in dest.rglob("*") if path.is_file())
        for relative_path in src_files:
            if not (dest / relative_path).exists():
                failures.append(f"missing destination file: {dest / relative_path}")
                continue
            if not filecmp.cmp(src / relative_path, dest / relative_path, shallow=False):
                failures.append(f"file drift: {dest / relative_path} != {src / relative_path}")
        for relative_path in dest_files:
            if not (src / relative_path).exists():
                failures.append(f"stale destination file: {dest / relative_path}")
        return
    if dest.exists():
        if not dest.is_dir():
            failures.append(f"destination path is not a directory: {dest}")
            return
    else:
        dest.mkdir(parents=True, exist_ok=True)
    if dest.name == "assets":
        source_screenshots = src / "screenshots"
        dest_screenshots = dest / "screenshots"
        if not source_screenshots.exists() and dest_screenshots.exists():
            shutil.rmtree(dest_screenshots)
    source_entries = {path.relative_to(src) for path in src.rglob("*")}
    dest_entries = sorted(
        path.relative_to(dest)
        for path in dest.rglob("*")
    )
    for relative_path in reversed(dest_entries):
        if relative_path not in source_entries:
            stale_path = dest / relative_path
            if stale_path.is_dir():
                shutil.rmtree(stale_path)
            else:
                stale_path.unlink()
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
        default=_default_source(),
        help=f"Path to the generated design public-guide bundle (default: {_default_source()})",
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
        if relative_path in SOURCE_OWNED_SYNC_FILES:
            _sync_source_owned_file(
                source_root / relative_path,
                REPO_ROOT / relative_path,
                args.check,
                failures,
            )
            continue
        _copy_file(
            source_root / relative_path,
            REPO_ROOT / relative_path,
            args.check,
            failures,
            optional=relative_path in OPTIONAL_SYNC_FILES,
        )

    for source_relative_path, destination_relative_path in INTERNAL_SYNC_FILES.items():
        if source_relative_path == "manifest.generated.json":
            _sync_manifest_file(
                source_root / source_relative_path,
                REPO_ROOT / destination_relative_path,
                args.check,
                failures,
            )
            continue
        _copy_file(
            source_root / source_relative_path,
            REPO_ROOT / destination_relative_path,
            args.check,
            failures,
        )

    for relative_path in REMOVABLE_SYNC_FILES:
        _sync_removable_file(source_root / relative_path, REPO_ROOT / relative_path, args.check, failures)

    for relative_path in STALE_ROOT_FILES:
        _remove_stale_file(REPO_ROOT / relative_path, args.check, failures)

    for relative_path in SYNC_DIRS:
        _sync_dir(
            source_root / relative_path,
            REPO_ROOT / relative_path,
            args.check,
            failures,
            optional=relative_path in OPTIONAL_SYNC_DIRS,
        )

    for relative_path in OPTIONAL_SYNC_DIRS:
        source_dir = source_root / relative_path
        destination_dir = REPO_ROOT / relative_path
        if source_dir.exists():
            _sync_dir(source_dir, destination_dir, args.check, failures, optional=True)
        else:
            _remove_stale_dir(destination_dir, args.check, failures)

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
