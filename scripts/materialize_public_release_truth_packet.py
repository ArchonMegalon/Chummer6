#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import json
import os
from datetime import timezone, datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RECEIPTS_ROOT = REPO_ROOT / ".guide-internal" / "receipts"
OUTPUT_PATH = RECEIPTS_ROOT / "CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json"
LINUX_GATE_PATH = RECEIPTS_ROOT / "LINUX_SOURCE_BUILD_DOCKER_GATE.generated.json"
MACOS_SOURCE_BUILD_CONTRACT_PATH = RECEIPTS_ROOT / "MACOS_SOURCE_BUILD_CONTRACT.generated.json"
HUB_REGISTRY_ROOT_ENV = "CHUMMER_HUB_REGISTRY_ROOT"
HUB_REGISTRY_PATHS_ENV = "CHUMMER_HUB_REGISTRY_PATHS"
PORTAL_RELEASE_CHANNEL_PATHS_ENV = "CHUMMER_PORTAL_RELEASE_CHANNEL_PATHS"
RELEASE_CHANNEL_RELATIVE_PATH = Path(".codex-studio/published/RELEASE_CHANNEL.generated.json")
RELEASE_CHANNEL_COMPAT_RELATIVE_PATH = Path(".codex-studio/published/releases.json")


PLATFORM_LABELS = {
    "windows": "Windows",
    "linux": "Linux",
    "macos": "macOS",
    "osx": "macOS",
}
PLATFORM_ORDER = ("windows", "linux", "macos")


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _public_source_label(path: Path) -> str:
    resolved = path.resolve()
    for base in (REPO_ROOT.parent.resolve(), REPO_ROOT.resolve()):
        try:
            return resolved.relative_to(base).as_posix()
        except ValueError:
            continue
    return path.name


def _split_path_list(env_name: str) -> list[Path]:
    raw = os.environ.get(env_name, "").strip()
    if not raw:
        return []
    return [Path(item).expanduser() for item in raw.split(os.pathsep) if item.strip()]


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    result: list[Path] = []
    for path in paths:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result


def _candidate_hub_registry_roots() -> list[Path]:
    roots: list[Path] = []
    env_root = os.environ.get(HUB_REGISTRY_ROOT_ENV, "").strip()
    if env_root:
        roots.append(Path(env_root).expanduser())
    roots.extend(_split_path_list(HUB_REGISTRY_PATHS_ENV))
    roots.extend(
        [
            REPO_ROOT.parent / "chummer-hub-registry",
            REPO_ROOT.parent / "chummer6-hub-registry",
        ]
    )
    return _dedupe_paths(roots)


def _load_release_channel() -> tuple[dict[str, object], str]:
    for candidate in _split_path_list(PORTAL_RELEASE_CHANNEL_PATHS_ENV):
        if candidate.is_file():
            return _load_json(candidate), _public_source_label(candidate)
    for root in _candidate_hub_registry_roots():
        canonical = root / RELEASE_CHANNEL_RELATIVE_PATH
        if canonical.is_file():
            return _load_json(canonical), _public_source_label(canonical)
        compat = root / RELEASE_CHANNEL_COMPAT_RELATIVE_PATH
        if compat.is_file():
            return _load_json(compat), _public_source_label(compat)
    raise FileNotFoundError("No release channel projection found. Set CHUMMER_PORTAL_RELEASE_CHANNEL_PATHS or CHUMMER_HUB_REGISTRY_ROOT.")


def _format_public_datetime(value: object) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        return ""
    try:
        parsed = datetime.fromisoformat(cleaned.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return cleaned
    rendered = parsed.strftime("%B %d, %Y at %H:%M UTC")
    return rendered.replace(" 0", " ")


def _release_status_slug(value: object) -> str:
    return str(value or "").strip().lower()


def _release_status_label(value: object) -> str:
    slug = _release_status_slug(value)
    if slug == "published":
        return "Published"
    if slug == "unpublished":
        return "Not currently published"
    return slug.replace("_", " ").title() if slug else ""


def _platform_key(value: object) -> str:
    cleaned = str(value or "").strip().lower()
    if "windows" in cleaned or cleaned.startswith("win"):
        return "windows"
    if "linux" in cleaned:
        return "linux"
    if "macos" in cleaned or "osx" in cleaned or "darwin" in cleaned:
        return "macos"
    return cleaned


def _release_artifacts(release_payload: dict[str, object]) -> list[dict[str, object]]:
    raw = release_payload.get("artifacts")
    if not isinstance(raw, list):
        raw = release_payload.get("downloads")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _available_platforms(artifacts: list[dict[str, object]]) -> list[str]:
    present = {_platform_key(item.get("platform") or item.get("platformLabel")) for item in artifacts}
    labels: list[str] = []
    for key in PLATFORM_ORDER:
        if key in present:
            labels.append(PLATFORM_LABELS[key])
    return labels


def _english_join(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def _shelf_truth_line(status: object, available_platforms: list[str]) -> str:
    if _release_status_slug(status) == "published" and available_platforms:
        return f"{_english_join(available_platforms)} downloads are posted."
    if _release_status_slug(status) == "published":
        return "The release is published, but no downloadable files are posted right now."
    if available_platforms:
        return f"Preview downloads are visible for {_english_join(available_platforms)}, but the main release is not published yet."
    return "No public downloads are posted right now."


def _public_known_issue_summary(release_payload: dict[str, object]) -> str:
    cleaned = str(release_payload.get("knownIssueSummary") or "").strip()
    if not cleaned:
        return ""
    lowered = cleaned.lower()
    if "current release checks are clear" in lowered:
        return "No current download blocker is listed for these installers."
    return cleaned


def _release_verification_summary(release_payload: dict[str, object]) -> str:
    proof = release_payload.get("releaseProof")
    if isinstance(proof, dict):
        journeys = proof.get("journeysPassed")
        if str(proof.get("status") or "").strip().lower() == "passed" and isinstance(journeys, list) and journeys:
            return "This release covers installs and recovery, campaign session recovery, and support follow-up."
    return str(release_payload.get("supportabilitySummary") or "").strip()


def _fix_availability_summary(release_payload: dict[str, object]) -> str:
    cleaned = str(release_payload.get("fixAvailabilitySummary") or "").strip()
    if "published channel artifact" in cleaned.lower():
        return "Fix notices appear after the corrected download is live on the download page."
    return cleaned


def _linux_gate_projection(linux_gate: dict[str, object]) -> dict[str, object]:
    output = linux_gate.get("output") if isinstance(linux_gate.get("output"), dict) else {}
    return {
        "archive_sha256": str(output.get("archive_sha256") or "").strip(),
        "docker_image": str(linux_gate.get("docker_image") or "").strip(),
        "executable_sha256": str(output.get("executable_sha256") or "").strip(),
        "generated_at_utc": str(linux_gate.get("generated_at_utc") or "").strip(),
        "rid": str(output.get("rid") or "").strip(),
        "status": str(linux_gate.get("status") or "").strip(),
    }


def _macos_contract_projection(contract: dict[str, object]) -> dict[str, object]:
    policy = contract.get("policy") if isinstance(contract.get("policy"), dict) else {}
    return {
        "doc_marks_second_script_install": policy.get("doc_marks_second_script_install") is True,
        "generated_at_utc": str(contract.get("generated_at_utc") or "").strip(),
        "maintenance_policy_marks_real_build_as_macos_only": policy.get("maintenance_policy_marks_real_build_as_macos_only") is True,
        "maintenance_policy_requires_two_step_install": policy.get("maintenance_policy_requires_two_step_install") is True,
        "real_macos_runtime_proof_required": contract.get("real_macos_runtime_proof_required") is True,
        "runtime_coverage": str(contract.get("runtime_coverage") or "").strip(),
        "scope": str(contract.get("scope") or "").strip(),
        "status": str(contract.get("status") or "").strip(),
    }


def build_packet(
    release_payload: dict[str, object],
    linux_gate: dict[str, object],
    macos_source_build_contract: dict[str, object],
    release_source: str,
) -> dict[str, object]:
    artifacts = _release_artifacts(release_payload)
    available_platforms = _available_platforms(artifacts)
    status_slug = _release_status_slug(release_payload.get("status") or "unpublished")
    release_status = _release_status_label(status_slug)
    published_at = _format_public_datetime(release_payload.get("publishedAt") or release_payload.get("generatedAt") or "")
    shelf_truth_line = _shelf_truth_line(status_slug, available_platforms)
    published_line = f"Published: {published_at}." if published_at and status_slug == "published" else ""

    return {
        "architecture_scope_line": "Desktop downloads are available for Linux x64 and Windows x64 only. No download is posted for Windows ARM64, Linux ARM64, and macOS x64 yet.",
        "available_platforms": available_platforms,
        "build_label": "",
        "desktop_pick_line": "For today, start with Avalonia. Treat Blazor Desktop as the alternate only when a support page points you there.",
        "fallback_heads": ["Chummer.Blazor.Desktop"],
        "fix_availability_summary": _fix_availability_summary(release_payload),
        "generated_from": release_source,
        "known_issue_summary": _public_known_issue_summary(release_payload),
        "linux_source_build_gate": _linux_gate_projection(linux_gate),
        "macos_source_build_contract": _macos_contract_projection(macos_source_build_contract),
        "missing_installer_lane_line": "Normal installers are available on the desktop platforms that are currently offered.",
        "missing_platforms": [],
        "phase_label": "Current release build",
        "primary_head": "Chummer.Avalonia",
        "public_download_authority": "https://chummer.run/downloads",
        "published_at": published_at,
        "published_line": published_line,
        "quality_gap_line": "The core app is usable. The remaining work is desktop parity, installer polish, update polish, and deeper table continuity.",
        "release_status": release_status,
        "release_status_slug": status_slug,
        "release_verification_summary": _release_verification_summary(release_payload),
        "shelf_truth_line": shelf_truth_line,
        "short_release_summary": "Use the files linked on [Download](DOWNLOAD.md). If your platform is missing or preview-only, wait before switching full time.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize the Chummer6 public release truth packet from the release channel and local receipts.")
    parser.add_argument("--check", action="store_true", help="Validate the packet without rewriting it.")
    args = parser.parse_args()

    release_payload, release_source = _load_release_channel()
    linux_gate = _load_json(LINUX_GATE_PATH)
    macos_source_build_contract = _load_json(MACOS_SOURCE_BUILD_CONTRACT_PATH)
    packet = build_packet(release_payload, linux_gate, macos_source_build_contract, release_source)
    rendered = json.dumps(packet, indent=2, sort_keys=True) + "\n"
    if args.check:
        current = OUTPUT_PATH.read_text(encoding="utf-8") if OUTPUT_PATH.is_file() else ""
        if current != rendered:
            for line in difflib.unified_diff(
                current.splitlines(keepends=True),
                rendered.splitlines(keepends=True),
                fromfile=str(OUTPUT_PATH),
                tofile="expected-public-release-truth-packet",
            ):
                print(line.rstrip())
            return 1
        print("public_release_truth_packet:ok")
        return 0

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(rendered, encoding="utf-8")
    print("public_release_truth_packet:ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
