#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import json
from datetime import timezone, datetime
from pathlib import Path

try:
    from public_release_authority import (
        ALLOWED_RELEASE_DECISION_STATUSES,
        CANONICAL_RELEASE_CHANNEL_SOURCE,
        authority_artifacts,
        authority_platform_ids,
        resolve_release_authority,
    )
except ModuleNotFoundError:  # Imported as scripts.materialize_public_release_truth_packet in tests.
    from scripts.public_release_authority import (
        ALLOWED_RELEASE_DECISION_STATUSES,
        CANONICAL_RELEASE_CHANNEL_SOURCE,
        authority_artifacts,
        authority_platform_ids,
        resolve_release_authority,
    )


REPO_ROOT = Path(__file__).resolve().parents[1]
RECEIPTS_ROOT = REPO_ROOT / ".guide-internal" / "receipts"
OUTPUT_PATH = RECEIPTS_ROOT / "CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json"
LINUX_GATE_PATH = RECEIPTS_ROOT / "LINUX_SOURCE_BUILD_DOCKER_GATE.generated.json"
MACOS_SOURCE_BUILD_CONTRACT_PATH = RECEIPTS_ROOT / "MACOS_SOURCE_BUILD_CONTRACT.generated.json"


PLATFORM_LABELS = {
    "windows": "Windows",
    "linux": "Linux",
    "macos": "macOS",
    "osx": "macOS",
}
PLATFORM_ORDER = ("windows", "linux", "macos")
ARCHITECTURE_SCOPE_EXPECTATIONS = (
    ("linux", "linux-x64", "Linux x64"),
    ("windows", "win-x64", "Windows x64"),
    ("linux", "linux-arm64", "Linux ARM64"),
    ("windows", "win-arm64", "Windows ARM64"),
)


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def _release_tuple_coverage(release_payload: dict[str, object]) -> dict[str, object]:
    payload = release_payload.get("desktopTupleCoverage")
    return payload if isinstance(payload, dict) else {}


def _promoted_installer_tuples(release_payload: dict[str, object]) -> list[dict[str, object]]:
    raw = _release_tuple_coverage(release_payload).get("promotedInstallerTuples")
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


def _missing_public_platforms(available_platforms: list[str]) -> list[str]:
    present = {_platform_key(item) for item in available_platforms}
    labels: list[str] = []
    for key in PLATFORM_ORDER:
        if key not in present:
            labels.append(PLATFORM_LABELS[key])
    return labels


def _required_public_platforms(release_payload: dict[str, object]) -> list[str]:
    raw = _release_tuple_coverage(release_payload).get("requiredDesktopPlatforms")
    if not isinstance(raw, list):
        return [PLATFORM_LABELS[key] for key in PLATFORM_ORDER]
    required = {_platform_key(item) for item in raw}
    return [PLATFORM_LABELS[key] for key in PLATFORM_ORDER if key in required]


def _missing_required_public_platforms(
    release_payload: dict[str, object],
    available_platforms: list[str],
) -> list[str]:
    coverage = _release_tuple_coverage(release_payload)
    explicit = coverage.get("missingRequiredPlatforms")
    if isinstance(explicit, list):
        missing = {_platform_key(item) for item in explicit}
        return [PLATFORM_LABELS[key] for key in PLATFORM_ORDER if key in missing]

    available = {_platform_key(item) for item in available_platforms}
    return [label for label in _required_public_platforms(release_payload) if _platform_key(label) not in available]


def _gold_supported_release(
    release_payload: dict[str, object],
    available_platforms: list[str],
    authority: dict[str, object],
) -> bool:
    coverage = _release_tuple_coverage(release_payload)
    if (
        _release_status_slug(release_payload.get("releaseStatus") or release_payload.get("status")) != "published"
        or str(release_payload.get("channelId") or release_payload.get("channel") or "").strip()
        != "public_stable"
        or str(release_payload.get("rolloutState") or "").strip() != "public_stable"
        or str(release_payload.get("supportabilityState") or "").strip() != "gold_supported"
        or str(authority.get("releaseDecisionStatus") or "").strip() != "stable_ready"
        or coverage.get("complete") is not True
    ):
        return False

    for field_name in (
        "missingRequiredPlatforms",
        "missingRequiredHeads",
        "missingRequiredPlatformHeadPairs",
        "missingRequiredPlatformHeadRidTuples",
        "externalProofRequests",
    ):
        value = coverage.get(field_name)
        if not isinstance(value, list) or value:
            return False

    return bool(available_platforms)


def _public_head_label(value: object) -> str:
    cleaned = str(value or "").strip().lower()
    return {
        "avalonia": "Chummer.Avalonia",
        "chummer.avalonia": "Chummer.Avalonia",
        "blazor-desktop": "Chummer.Blazor.Desktop",
        "chummer.blazor.desktop": "Chummer.Blazor.Desktop",
    }.get(cleaned, str(value or "").strip())


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


def _missing_installer_lane_line(missing_platforms: list[str]) -> str:
    if not missing_platforms:
        return "Normal installers are available on the desktop platforms that are currently offered."
    verb = "does" if len(missing_platforms) == 1 else "do"
    return f"{_english_join(missing_platforms)} {verb} not have a normal installer yet."


def _macos_architecture_label(rid: str, arch: str) -> str:
    rid_clean = str(rid or "").strip().lower()
    arch_clean = str(arch or "").strip().lower()
    if "arm64" in rid_clean or arch_clean == "arm64":
        return "macOS ARM64"
    return "macOS x64"


def _architecture_scope_line(artifacts: list[dict[str, object]]) -> str:
    artifact_keys = {
        (_platform_key(item.get("platform")), str(item.get("arch") or "").strip().lower())
        for item in artifacts
    }

    available_labels: list[str] = []
    missing_labels: list[str] = []
    for platform_key_value, rid, label in ARCHITECTURE_SCOPE_EXPECTATIONS:
        expected_arch = "arm64" if "arm64" in rid else "x64"
        if (platform_key_value, expected_arch) in artifact_keys:
            available_labels.append(label)
        else:
            missing_labels.append(label)

    macos_labels = [
        _macos_architecture_label("", str(item.get("arch") or ""))
        for item in artifacts
        if _platform_key(item.get("platform")) == "macos"
    ]
    for label in macos_labels:
        if label not in available_labels:
            available_labels.append(label)

    if not macos_labels:
        missing_labels.append("macOS")

    if available_labels:
        line = f"Desktop downloads are available for {_english_join(available_labels)} only."
    else:
        line = "No public desktop downloads are posted today."
    if missing_labels:
        line = f"{line} No public download is posted for {_english_join(missing_labels)} yet."
    return line


def _public_known_issue_summary(release_payload: dict[str, object]) -> str:
    cleaned = str(release_payload.get("knownIssueSummary") or "").strip()
    if "current release checks are clear" in cleaned.lower():
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
    authority: dict[str, object],
    authority_source: dict[str, object],
    served_mirror: str,
) -> dict[str, object]:
    artifacts = authority_artifacts(authority)
    platform_ids = authority_platform_ids(authority)
    available_platforms = [PLATFORM_LABELS.get(platform, platform) for platform in platform_ids]
    required_platforms = list(available_platforms)
    missing_platforms = _missing_public_platforms(available_platforms)
    status_slug = _release_status_slug(
        release_payload.get("releaseStatus") or release_payload.get("status") or "unpublished"
    )
    release_status = _release_status_label(status_slug)
    published_at = _format_public_datetime(release_payload.get("publishedAt") or release_payload.get("generatedAt") or "")
    shelf_truth_line = _shelf_truth_line(status_slug, available_platforms)
    published_line = f"Published: {published_at}." if published_at and status_slug == "published" else ""
    gold_supported = _gold_supported_release(release_payload, available_platforms, authority)
    decision_status = str(authority.get("releaseDecisionStatus") or "").strip().lower()
    review_required = decision_status == "review_required"
    raw_primary_heads = authority.get("primaryHeadByPlatform")
    raw_primary_heads = raw_primary_heads if isinstance(raw_primary_heads, dict) else {}
    unique_primary_heads = sorted({_public_head_label(item) for item in raw_primary_heads.values() if item})
    primary_head = unique_primary_heads[0] if len(unique_primary_heads) == 1 else _english_join(unique_primary_heads)
    primary_head_by_platform = {
        str(platform): str(head)
        for platform, head in sorted(raw_primary_heads.items())
        if str(platform).strip() and str(head).strip()
    }
    primary_head_routes = _english_join(
        [
            f"{PLATFORM_LABELS.get(platform, platform)}: {_public_head_label(head)}"
            for platform, head in primary_head_by_platform.items()
        ]
    )
    fallback_heads = sorted(
        {
            _public_head_label(item.get("head"))
            for item in artifacts
            if str(item.get("head") or "").strip()
            and str(item.get("head") or "").strip()
            != str(raw_primary_heads.get(str(item.get("platform") or "")) or "").strip()
        }
    )
    platform_scope = _english_join(required_platforms) or "the currently supported desktop platforms"

    return {
        "architecture_scope_line": _architecture_scope_line(artifacts),
        "authority": dict(authority),
        "authority_binding_status": "bound",
        "authority_source": dict(authority_source),
        "available_platforms": available_platforms,
        "build_label": "",
        "channel_id": str(release_payload.get("channelId") or release_payload.get("channel") or "").strip(),
        "desktop_pick_line": (
            f"Primary desktop heads by platform: {primary_head_routes}."
            if primary_head_routes and len(unique_primary_heads) > 1
            else
            f"Use the {primary_head} installer listed for your platform; unpromoted fallback heads remain support-only."
            if gold_supported and fallback_heads
            else f"Use the {primary_head} installer listed for your platform."
            if gold_supported
            else f"For today, start with {primary_head}. Use another desktop head only when the release shelf lists it explicitly."
            if primary_head
            else "No desktop head is approved for the current public shelf."
        ),
        "desktop_tuple_coverage_complete": _release_tuple_coverage(release_payload).get("complete") is True,
        "fallback_heads": fallback_heads,
        "fix_availability_summary": _fix_availability_summary(release_payload),
        "generated_from": served_mirror,
        "known_issue_summary": _public_known_issue_summary(release_payload),
        "linux_source_build_gate": _linux_gate_projection(linux_gate),
        "macos_source_build_contract": _macos_contract_projection(macos_source_build_contract),
        "missing_installer_lane_line": _missing_installer_lane_line(missing_platforms),
        "missing_platforms": missing_platforms,
        "phase_label": (
            "Release review required"
            if review_required
            else "Gold-supported release"
            if gold_supported
            else "Preview-ready release"
        ),
        "primary_head": primary_head,
        "primary_head_by_platform": primary_head_by_platform,
        "public_download_authority": "https://chummer.run/downloads",
        "published_at": published_at,
        "published_line": published_line,
        "quality_gap_line": (
            "Release review is required. Stable and gold claims remain paused until the immutable authority and public routes converge."
            if review_required
            else
            f"The current promoted {platform_scope} release is gold-supported for its stated platform and desktop-head scope."
            if gold_supported
            else "The core app is usable. The remaining work is desktop parity, installer polish, update polish, and deeper table continuity."
        ),
        "release_decision_status": decision_status,
        "release_posture": decision_status,
        "review_required_banner": (
            "Release review required. Public availability claims remain paused until one immutable snapshot converges."
            if review_required
            else ""
        ),
        "release_status": release_status,
        "release_status_slug": status_slug,
        "release_verification_summary": _release_verification_summary(release_payload),
        "required_platforms": required_platforms,
        "rollout_state": str(release_payload.get("rolloutState") or "").strip(),
        "shelf_truth_line": shelf_truth_line,
        "served_mirror": served_mirror,
        "short_release_summary": (
            f"Use the files linked on [Download](DOWNLOAD.md). The current {platform_scope} shelf is the supported release; platforms not listed there remain outside this release scope."
            if gold_supported
            else "Release review is required. Do not rely on platform availability claims until the current immutable snapshot converges."
            if review_required
            else "Use the files linked on [Download](DOWNLOAD.md). This is a preview-ready release, not a stable or gold claim."
        ),
        "supportability_state": str(release_payload.get("supportabilityState") or "").strip(),
    }


def build_unbound_review_packet(
    linux_gate: dict[str, object],
    macos_source_build_contract: dict[str, object],
) -> dict[str, object]:
    banner = (
        "Release review required. Public availability claims remain paused until one immutable snapshot converges."
    )
    return {
        "architecture_scope_line": "No desktop platform is currently claimed by this unbound repository projection.",
        "authority": {"artifacts": [], "status": "unavailable"},
        "authority_binding_status": "unbound_review_placeholder",
        "authority_source": {
            "status": "unbound",
            "reason": "No Registry CURRENT.json was supplied to this repository projection.",
        },
        "available_platforms": [],
        "build_label": "",
        "channel_id": "",
        "desktop_pick_line": "No desktop head is approved by this unbound repository projection.",
        "desktop_tuple_coverage_complete": False,
        "fallback_heads": [],
        "fix_availability_summary": "Wait for a Registry-bound release decision before relying on fix availability.",
        "generated_from": "unbound repository review placeholder",
        "known_issue_summary": "The repository has no bound current release authority; live availability must not be inferred from stale guide text.",
        "linux_source_build_gate": _linux_gate_projection(linux_gate),
        "macos_source_build_contract": _macos_contract_projection(macos_source_build_contract),
        "missing_installer_lane_line": "Windows, Linux, and macOS remain unclaimed until immutable authority is supplied.",
        "missing_platforms": ["Windows", "Linux", "macOS"],
        "phase_label": "Release review required",
        "primary_head": "",
        "primary_head_by_platform": {},
        "public_download_authority": "https://chummer.run/downloads",
        "published_at": "",
        "published_line": "",
        "quality_gap_line": "Release review is required. Stable and gold claims remain paused until the immutable authority and public routes converge.",
        "release_decision_status": "review_required",
        "release_posture": "review_required",
        "release_status": "Review required",
        "release_status_slug": "review_required",
        "release_verification_summary": "No Registry-bound current release verification is available in this checkout.",
        "required_platforms": [],
        "review_required_banner": banner,
        "rollout_state": "review_required",
        "served_mirror": CANONICAL_RELEASE_CHANNEL_SOURCE,
        "shelf_truth_line": "No public platform availability is claimed by this unbound repository projection.",
        "short_release_summary": "Release review is required. Do not rely on platform availability claims until the current immutable snapshot converges.",
        "supportability_state": "review_required",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Materialize the Chummer6 public release truth packet from the release channel and local receipts.")
    parser.add_argument("--check", action="store_true", help="Validate the packet without rewriting it.")
    parser.add_argument(
        "--unbound-review-placeholder",
        action="store_true",
        help="Generate the deterministic checked-in review-required placeholder; never valid release evidence.",
    )
    parser.add_argument(
        "--release",
        action="store_true",
        help="Mark this strict authority materialization as a release workflow invocation.",
    )
    parser.add_argument(
        "--authority-current",
        type=Path,
        help="Explicit Registry CURRENT.json pointer; the immutable generation is derived from it.",
    )
    parser.add_argument(
        "--registry-commit",
        default="",
        help="Exact lowercase 40-hex Registry commit bound by SNAPSHOT.json.",
    )
    parser.add_argument(
        "--expected-release-decision-status",
        choices=sorted(ALLOWED_RELEASE_DECISION_STATUSES),
        default="",
        help="Exact decision posture required from both manifest and receipt.",
    )
    parser.add_argument(
        "--served-mirror",
        default=CANONICAL_RELEASE_CHANNEL_SOURCE,
        help="Public served mirror URL, recorded separately from immutable authority.",
    )
    args = parser.parse_args(argv)

    if args.unbound_review_placeholder and args.release:
        parser.error("the unbound review placeholder cannot be used in release mode")
    if args.unbound_review_placeholder and any(
        (args.authority_current, args.registry_commit, args.expected_release_decision_status)
    ):
        parser.error("the unbound review placeholder cannot be combined with authority arguments")

    missing_flags = [
        flag
        for flag, value in (
            ("--authority-current", args.authority_current),
            ("--registry-commit", args.registry_commit),
            ("--expected-release-decision-status", args.expected_release_decision_status),
        )
        if not value
    ]
    if missing_flags and not args.unbound_review_placeholder:
        parser.error(
            "canonical release truth output requires explicit immutable authority flags: "
            f"{', '.join(missing_flags)}"
        )

    linux_gate = _load_json(LINUX_GATE_PATH)
    macos_source_build_contract = _load_json(MACOS_SOURCE_BUILD_CONTRACT_PATH)
    if args.unbound_review_placeholder:
        packet = build_unbound_review_packet(linux_gate, macos_source_build_contract)
    else:
        resolved = resolve_release_authority(
            args.authority_current,
            served_mirror=args.served_mirror,
            registry_commit=args.registry_commit,
            expected_release_decision_status=args.expected_release_decision_status,
        )
        packet = build_packet(
            resolved.release_payload,
            linux_gate,
            macos_source_build_contract,
            resolved.authority,
            resolved.authority_source,
            resolved.served_mirror,
        )
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
