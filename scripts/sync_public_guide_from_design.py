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
    "RUNNER_PASSPORT.md",
    "LIVING_WORLD.md",
    "STATUS.md",
    "DOWNLOAD.md",
    "HELP.md",
    "FAQ.md",
    "CONTACT.md",
)

INTERNAL_SYNC_FILES = {
    "manifest.generated.json": ".guide-internal/manifest.generated.json",
    "CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json": ".guide-internal/receipts/CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json",
    "CHUMMER6_PUBLIC_GUIDE_TRUTH_AUDIT.generated.json": ".guide-internal/receipts/CHUMMER6_PUBLIC_GUIDE_TRUTH_AUDIT.generated.json",
    "CHUMMER6_PUBLIC_GUIDE_NEW_SECTIONS.generated.json": ".guide-internal/receipts/CHUMMER6_PUBLIC_GUIDE_NEW_SECTIONS.generated.json",
    "CHUMMER6_GUIDE_GENERATOR_REGISTRY_ALIGNMENT.generated.json": ".guide-internal/receipts/CHUMMER6_GUIDE_GENERATOR_REGISTRY_ALIGNMENT.generated.json",
    "FINAL_CHUMMER6_DOCS_GENERATION_VERDICT.md": ".guide-internal/receipts/FINAL_CHUMMER6_DOCS_GENERATION_VERDICT.md",
}

SYNC_DIRS = (
    "PARTS",
    "HORIZONS",
    "TRUST",
    "assets",
)

OPTIONAL_SYNC_FILES = ("GLOSSARY.md",)
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

START_HERE_BLOCKS = {}

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

TEXT_REWRITES = {
    "README.md": (
        (
            "Preview proof, fallback routes, artifact explainers, and packet-detail artifacts can show real progress, but flagship wording is reserved for surfaces that independently clear the flagship acceptance bar.",
            "Preview notes, fallback routes, artifact explainers, and packet details can show real progress, but we only use flagship wording on pages a visitor can actually inspect and use.",
        ),
        (
            "Preview proof, fallback routes, and artifact explainers can show real progress, but flagship wording is reserved for surfaces that independently clear the flagship acceptance bar.",
            "Preview notes, fallback routes, and artifact explainers can show real progress, but we only use flagship wording on pages a visitor can actually inspect and use.",
        ),
        (
            "Preview evidence and fallback routes can show real progress, but flagship wording is reserved for surfaces that independently clear the flagship acceptance bar.",
            "Preview evidence and fallback routes can show real progress, but we only use flagship wording on pages a visitor can actually inspect and use.",
        ),
        (
            "Use this guide to answer the practical questions first: what Chummer6 is, what is real today, what to download, and where to get help.",
            "Use this guide to answer the practical questions first: what Chummer6 is, what is real today, what to download, how account and recovery fit together, and where to get help.",
        ),
        (
            "## Start here\n\n- [Download](DOWNLOAD.md)\n- [Status](STATUS.md)\n- [What Chummer6 Is](WHAT_CHUMMER6_IS.md)\n- [From Chummer5a to Chummer6](FROM_CHUMMER5A_TO_CHUMMER6.md)\n- [How can I help](HOW_CAN_I_HELP.md)\n- [Help](HELP.md)\n- [FAQ](FAQ.md)\n- [Contact](CONTACT.md)\n- [Future ideas](HORIZONS/README.md)\n",
            "## Flagship guide map\n\n- [Home](README.md)\n- [Get Chummer](DOWNLOAD.md)\n- [What works today](STATUS.md)\n- [What Chummer6 Is](WHAT_CHUMMER6_IS.md)\n- [Campaign tools](HORIZONS/README.md)\n- [From Chummer5a to Chummer6](FROM_CHUMMER5A_TO_CHUMMER6.md)\n- [Account](HELP.md#account-keep-access-and-recovery-on-one-calm-path)\n- [Help](HELP.md)\n- [FAQ](FAQ.md)\n- [Contact](CONTACT.md)\n",
        ),
        ("## How can I help?\n", "## Account and contribution paths\n"),
        ("## Product parts\n", "## Campaign tools\n"),
        ("[Worlds and future work](HORIZONS/README.md)", "[Campaign tools](HORIZONS/README.md)"),
        ("How can I help](HOW_CAN_I_HELP.md)", "Contact](CONTACT.md)"),
        ("## Need help\n", "## Help\n"),
    ),
    "DOWNLOAD.md": (
        (
            "Claim boundary: Flagship wording is reserved for surfaces that currently satisfy FLAGSHIP_RELEASE_ACCEPTANCE.yaml; preview artifacts, proof cards, captions, packet siblings, artifact-factory explainers, and fallback routes do not earn that claim by proximity.",
            "Claim boundary: That stronger wording only belongs on the main release surfaces after they have earned enough public proof; preview artifacts, proof cards, captions, packet siblings, artifact-factory explainers, and fallback routes do not inherit it just by sitting nearby.",
        ),
        (
            "This page tells you what you can download right now and which file to start with.\n",
            "This page tells you what you can download right now and which file to start with.\n\nGuide fit: this is the `Get Chummer` page in the flagship shell.\n",
        ),
    ),
    "STATUS.md": (
        (
            "This is the blunt answer on what you can use today.\n",
            "This is the blunt answer on what you can use today.\n\nGuide fit: this is the `What works today` page in the flagship shell.\n",
        ),
        (
            "## Start with the release page and download help\n",
            "## Get Chummer, then use Help if setup goes sideways\n",
        ),
    ),
    "HELP.md": (
        (
            "Start here if installation, updates, sign-in, or bugs are getting in the way.\n",
            "Start here if installation, updates, sign-in, or bugs are getting in the way.\n\nGuide fit: this is the `Help` page in the flagship shell, with the account and recovery path kept adjacent instead of treated as a separate old-style section.\n",
        ),
        (
            "## Start with the release page and download help\n",
            "## Start with Get Chummer and What works today\n",
        ),
        (
            "## Keep access and recovery on one calm path\n",
            "## Account: keep access and recovery on one calm path\n",
        ),
        (
            "## Product help should become a support case, not a rumor\n",
            "## Help should become a support case, not a rumor\n",
        ),
        (
            "## Ask from inside Chummer first\n",
            "## Ask Chummer first\n",
        ),
    ),
    "FAQ.md": (
        (
            "# FAQ\n\n## Using Chummer6\n",
            "# FAQ\n\nThis page supports the flagship shell by answering the normal questions around `Home`, `Get Chummer`, `What works today`, `Worlds`, `Account`, and `Help`.\n\n## Home, Get Chummer, and What works today\n",
        ),
        (
            "## If you want the behind-the-scenes details",
            "## If you want more detail",
        ),
        (
            "In the planning notes that shape the roadmap and the public guide.",
            "Start with [Where To Go Deeper](WHERE_TO_GO_DEEPER.md). It points to the optional deeper guide pages without sending most readers through internal planning material first.",
        ),
        (
            "## Helping and feedback\n",
            "## Worlds, Account, and Help\n",
        ),
    ),
}


def _render_with_start_here(src: Path, relative_path: str, anchor: str) -> str:
    if not src.exists():
        raise FileNotFoundError(src)
    source_text = src.read_text(encoding="utf-8")
    for old, new in TEXT_REWRITES.get(relative_path, ()):
        source_text = source_text.replace(old, new)
    if relative_path == "README.md":
        duplicated = "[From Chummer5a to Chummer6](FROM_CHUMMER5A_TO_CHUMMER6.md)"
        seen = False
        deduped: list[str] = []
        for line in source_text.splitlines():
            if line.strip() == f"- {duplicated}":
                if seen:
                    continue
                seen = True
            deduped.append(line)
        source_text = "\n".join(deduped)
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
