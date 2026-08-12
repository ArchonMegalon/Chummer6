#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

try:
    from public_release_authority import (
        ALLOWED_RELEASE_DECISION_STATUSES,
        CANONICAL_RELEASE_CHANNEL_SOURCE,
        authority_artifacts,
        authority_platform_ids,
        require_authority_match,
        resolve_release_authority,
    )
except ModuleNotFoundError:  # Imported as scripts.verify_public_downloads_match_registry in tests.
    from scripts.public_release_authority import (
        ALLOWED_RELEASE_DECISION_STATUSES,
        CANONICAL_RELEASE_CHANNEL_SOURCE,
        authority_artifacts,
        authority_platform_ids,
        require_authority_match,
        resolve_release_authority,
    )


REPO_ROOT = Path(__file__).resolve().parents[1]
DOWNLOAD_PATH = REPO_ROOT / "DOWNLOAD.md"
STATUS_PATH = REPO_ROOT / "STATUS.md"
PACKET_PATH = REPO_ROOT / ".guide-internal" / "receipts" / "CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json"
PUBLIC_DOWNLOAD_ORIGIN = "https://chummer.run"

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


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return payload


def _platform_key(value: object) -> str:
    cleaned = str(value or "").strip().lower()
    if "windows" in cleaned or cleaned.startswith("win"):
        return "windows"
    if "linux" in cleaned:
        return "linux"
    if "macos" in cleaned or "osx" in cleaned or "darwin" in cleaned:
        return "macos"
    return cleaned


def _authority_artifact_labels(item: dict[str, object]) -> tuple[str, str]:
    platform = _platform_key(item.get("platform"))
    platform_label = PLATFORM_LABELS.get(platform, platform.title())
    arch = str(item.get("arch") or "").strip()
    base_label = " ".join(part for part in (platform_label, arch) if part)
    kind = str(item.get("kind") or "").strip().lower()
    kind_label = "installer" if kind in {"installer", "dmg", "pkg", "msix"} else kind
    artifact_label = base_label
    if kind_label and kind_label not in base_label.lower():
        artifact_label = f"{base_label} {kind_label}".strip()
    return base_label, artifact_label


def _english_join(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def _release_artifacts(release_payload: dict[str, object]) -> list[dict[str, object]]:
    raw = release_payload.get("artifacts")
    if not isinstance(raw, list):
        raw = release_payload.get("downloads")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _promoted_installer_tuples(release_payload: dict[str, object]) -> list[dict[str, object]]:
    coverage = release_payload.get("desktopTupleCoverage")
    if not isinstance(coverage, dict):
        return []
    raw = coverage.get("promotedInstallerTuples")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _release_tuple_coverage(release_payload: dict[str, object]) -> dict[str, object]:
    coverage = release_payload.get("desktopTupleCoverage")
    return coverage if isinstance(coverage, dict) else {}


def _available_platforms(artifacts: list[dict[str, object]]) -> list[str]:
    present = {_platform_key(item.get("platform") or item.get("platformLabel")) for item in artifacts}
    labels: list[str] = []
    for key in PLATFORM_ORDER:
        if key in present:
            labels.append(PLATFORM_LABELS[key])
    return labels


def _required_platforms(release_payload: dict[str, object]) -> list[str]:
    raw = _release_tuple_coverage(release_payload).get("requiredDesktopPlatforms")
    if not isinstance(raw, list):
        return [PLATFORM_LABELS[key] for key in PLATFORM_ORDER]
    required = {_platform_key(item) for item in raw}
    return [PLATFORM_LABELS[key] for key in PLATFORM_ORDER if key in required]


def _missing_platforms(available_platforms: list[str]) -> list[str]:
    present = {_platform_key(item) for item in available_platforms}
    return [PLATFORM_LABELS[key] for key in PLATFORM_ORDER if key not in present]


def _shelf_truth_line(status: object, available_platforms: list[str]) -> str:
    status_slug = str(status or "").strip().lower()
    if status_slug == "published" and available_platforms:
        return f"{_english_join(available_platforms)} downloads are posted."
    if status_slug == "published":
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


def _require_contains(name: str, haystack: str, needle: str) -> None:
    if needle and needle not in haystack:
        raise ValueError(f"{name} is missing required registry-aligned line: {needle!r}")


def _size_bytes_from_line(value: str) -> int:
    match = re.search(r"\((\d+)\s+bytes\)", value)
    if match:
        return int(match.group(1))
    digits = re.sub(r"[^0-9]", "", value)
    if digits:
        return int(digits)
    raise ValueError(f"Could not parse byte size from: {value!r}")


def _parse_download_artifacts(download_text: str) -> list[dict[str, object]]:
    lines = download_text.splitlines()
    artifacts: list[dict[str, object]] = []
    in_matrix = False
    current_platform = ""
    current_artifact: dict[str, object] | None = None
    for line in lines:
        if line == "## Current build matrix":
            in_matrix = True
            continue
        if in_matrix and line.startswith("## ") and line != "## Current build matrix":
            break
        if not in_matrix:
            continue
        if line.startswith("### "):
            current_platform = line[4:].strip()
            current_artifact = None
            continue
        if not current_platform or not line.startswith("- "):
            continue

        body = line[2:].strip()
        if body.startswith("There is no public "):
            current_artifact = None
            continue
        if body.startswith("Download: "):
            if current_artifact is None:
                raise ValueError("DOWNLOAD.md contains a download URL before an artifact label")
            match = re.search(r"\(([^)]+)\)", body)
            if not match:
                raise ValueError(f"DOWNLOAD.md could not parse download URL from {body!r}")
            current_artifact["downloadUrl"] = match.group(1).strip()
            continue
        if body.startswith("File: "):
            if current_artifact is None:
                raise ValueError("DOWNLOAD.md contains a file row before an artifact label")
            match = re.search(r"`([^`]+)`", body)
            if not match:
                raise ValueError(f"DOWNLOAD.md could not parse file name from {body!r}")
            current_artifact["fileName"] = match.group(1).strip()
            continue
        if body.startswith("Size: "):
            if current_artifact is None:
                raise ValueError("DOWNLOAD.md contains a size row before an artifact label")
            current_artifact["sizeBytes"] = _size_bytes_from_line(body)
            continue
        if body.startswith("Access: "):
            if current_artifact is None:
                raise ValueError("DOWNLOAD.md contains an access row before an artifact label")
            current_artifact["access"] = body[len("Access: ") :].rstrip(".").strip()
            continue
        if body.startswith("Update feed: "):
            continue
        if body.lower().startswith("status: "):
            continue
        if body.endswith("."):
            current_artifact = {
                "platformHeading": current_platform,
                "label": body[:-1].strip(),
            }
            artifacts.append(current_artifact)

    return artifacts


def _parse_sha256_lines(download_text: str) -> dict[str, str]:
    lines = download_text.splitlines()
    in_section = False
    values: dict[str, str] = {}
    for line in lines:
        if line == "## SHA256":
            in_section = True
            continue
        if in_section and line.startswith("## ") and line != "## SHA256":
            break
        if not in_section or not line.startswith("- "):
            continue
        match = re.match(r"- (.+?): `([0-9a-fA-F]{64})`$", line.strip())
        if not match:
            continue
        values[match.group(1).strip()] = match.group(2).lower()
    return values


def _registry_artifacts_by_filename(release_payload: dict[str, object]) -> dict[str, dict[str, object]]:
    artifacts: dict[str, dict[str, object]] = {}
    for item in _release_artifacts(release_payload):
        file_name = str(item.get("fileName") or "").strip()
        if file_name:
            artifacts[file_name] = item
    return artifacts


def _promoted_artifact_ids(release_payload: dict[str, object]) -> set[str]:
    return {
        str(item.get("artifactId") or item.get("id") or "").strip()
        for item in _promoted_installer_tuples(release_payload)
        if str(item.get("artifactId") or item.get("id") or "").strip()
    }


def _verify_download_artifacts(
    download_text: str,
    release_payload: dict[str, object],
    expected_authority_artifacts: list[dict[str, object]],
) -> None:
    docs_artifacts = _parse_download_artifacts(download_text)
    sha_lines = _parse_sha256_lines(download_text)
    documented_artifact_ids: set[str] = set()
    authority_by_id = {
        str(item.get("artifactId") or "").strip(): item
        for item in expected_authority_artifacts
        if str(item.get("artifactId") or "").strip()
    }
    authority_by_url: dict[str, dict[str, object]] = {}
    for authority_artifact in expected_authority_artifacts:
        public_route = str(authority_artifact.get("publicInstallRoute") or "").strip()
        public_url = f"{PUBLIC_DOWNLOAD_ORIGIN}{public_route}"
        if not public_route or public_url in authority_by_url:
            raise ValueError("immutable Registry public shelf contains a missing or ambiguous publicInstallRoute")
        authority_by_url[public_url] = authority_artifact
    if len(docs_artifacts) != len(authority_by_id):
        raise ValueError("DOWNLOAD.md artifact row count does not exactly match immutable Registry public shelf")

    for artifact in docs_artifacts:
        file_name = str(artifact.get("fileName") or "").strip()
        documented_url = str(artifact.get("downloadUrl") or "").strip()
        authority_artifact = authority_by_url.get(documented_url)
        if authority_artifact is None:
            raise ValueError("DOWNLOAD.md URL is outside the immutable Registry publicInstallRoute shelf")
        artifact_id = str(authority_artifact.get("artifactId") or "").strip()
        registry_matches = [
            item
            for item in _release_artifacts(release_payload)
            if str(item.get("artifactId") or item.get("id") or "").strip() == artifact_id
        ]
        if len(registry_matches) != 1:
            raise ValueError(f"canonical registry manifest artifactId {artifact_id!r} is missing or ambiguous")
        registry_artifact = registry_matches[0]
        registry_file_name = str(registry_artifact.get("fileName") or "").strip()
        if file_name and file_name != registry_file_name:
            raise ValueError(f"DOWNLOAD.md file {file_name!r} does not match the canonical registry manifest")
        artifact_label = file_name or artifact_id
        documented_artifact_ids.add(artifact_id)
        registry_label = str(registry_artifact.get("platformLabel") or "").strip()
        checksum_label, expected_label = _authority_artifact_labels(authority_artifact)
        docs_label = str(artifact.get("label") or "").strip()
        if expected_label != docs_label:
            raise ValueError(f"DOWNLOAD.md label for {artifact_label} does not match registry platformLabel")
        public_install_route = str(authority_artifact.get("publicInstallRoute") or "").strip()
        expected_public_url = f"{PUBLIC_DOWNLOAD_ORIGIN}{public_install_route}"
        if expected_public_url != documented_url:
            raise ValueError(
                f"DOWNLOAD.md URL for {artifact_label} does not match the absolute Registry publicInstallRoute"
            )
        if int(authority_artifact.get("sizeBytes") or 0) != int(artifact.get("sizeBytes") or 0):
            raise ValueError(f"DOWNLOAD.md size for {artifact_label} does not match registry sizeBytes")
        documented_sha256 = (
            sha_lines.get(checksum_label)
            or sha_lines.get(docs_label)
            or sha_lines.get(registry_label)
        )
        if not documented_sha256:
            raise ValueError(f"DOWNLOAD.md is missing a SHA256 row for {docs_label!r}")
        if str(authority_artifact.get("sha256") or "").strip().lower() != documented_sha256.lower():
            raise ValueError(f"DOWNLOAD.md SHA256 for {artifact_label} does not match registry sha256")
        if str(authority_artifact.get("compatibilityState") or "").strip() != "compatible":
            raise ValueError(f"Registry artifact {artifact_label} is not compatibilityState=compatible")
        access_class = str(authority_artifact.get("installAccessClass") or "").strip()
        expected_access = {
            "open_public": "Public download",
            "account_recommended": "Public download",
            "account_required": "Sign-in required",
        }.get(access_class)
        if expected_access is None:
            raise ValueError(f"Registry artifact {artifact_label} has unsupported installAccessClass={access_class!r}")
        if str(artifact.get("access") or "").strip() != expected_access:
            raise ValueError(f"DOWNLOAD.md access for {artifact_label} does not match registry installAccessClass")
    expected_artifact_ids = set(authority_by_id)
    if documented_artifact_ids != expected_artifact_ids:
        raise ValueError("DOWNLOAD.md artifact set does not exactly match immutable Registry public shelf authority")


def _verify_packet(
    packet: dict[str, object],
    release_payload: dict[str, object],
    expected_authority: dict[str, object],
    expected_authority_source: dict[str, object],
    expected_served_mirror: str,
) -> None:
    artifacts = authority_artifacts(expected_authority)
    platform_ids = authority_platform_ids(expected_authority)
    available_platforms = [PLATFORM_LABELS.get(platform, platform) for platform in platform_ids]
    required_platforms = list(available_platforms)
    missing_platforms = _missing_platforms(available_platforms)
    expected_source = expected_served_mirror
    expected_shelf_truth = _shelf_truth_line(
        release_payload.get("releaseStatus") or release_payload.get("status"),
        available_platforms,
    )
    expected_architecture_line = _architecture_scope_line(artifacts)
    expected_missing_line = _missing_installer_lane_line(missing_platforms)

    require_authority_match(
        packet,
        expected_authority,
        expected_authority_source,
        expected_served_mirror,
    )
    if str(packet.get("generated_from") or "").strip() != expected_source:
        raise ValueError("release truth packet generated_from does not point at the served release mirror")
    if list(packet.get("available_platforms") or []) != available_platforms:
        raise ValueError("release truth packet available_platforms drifted from the canonical registry manifest")
    if list(packet.get("required_platforms") or []) != required_platforms:
        raise ValueError("release truth packet required_platforms drifted from the canonical registry manifest")
    if list(packet.get("missing_platforms") or []) != missing_platforms:
        raise ValueError("release truth packet missing_platforms drifted from the canonical registry manifest")
    if str(packet.get("shelf_truth_line") or "").strip() != expected_shelf_truth:
        raise ValueError("release truth packet shelf_truth_line drifted from the canonical registry manifest")
    if str(packet.get("architecture_scope_line") or "").strip() != expected_architecture_line:
        raise ValueError("release truth packet architecture_scope_line drifted from the canonical registry manifest")
    if str(packet.get("missing_installer_lane_line") or "").strip() != expected_missing_line:
        raise ValueError("release truth packet missing_installer_lane_line drifted from the canonical registry manifest")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify public downloads against an immutable Registry release-authority snapshot."
    )
    parser.add_argument(
        "--release",
        action="store_true",
        help="Mark this strict authority verification as a release workflow invocation.",
    )
    parser.add_argument(
        "--authority-current",
        type=Path,
        required=True,
        help="Explicit Registry CURRENT.json pointer; the immutable generation is derived from it.",
    )
    parser.add_argument(
        "--registry-commit",
        required=True,
        help="Exact lowercase 40-hex Registry commit bound by SNAPSHOT.json.",
    )
    parser.add_argument(
        "--expected-release-decision-status",
        choices=sorted(ALLOWED_RELEASE_DECISION_STATUSES),
        required=True,
        help="Exact decision posture required from both manifest and receipt.",
    )
    parser.add_argument(
        "--served-mirror",
        default=CANONICAL_RELEASE_CHANNEL_SOURCE,
        help="Public served mirror URL, recorded separately from immutable authority.",
    )
    args = parser.parse_args(argv)

    resolved = resolve_release_authority(
        args.authority_current,
        served_mirror=args.served_mirror,
        registry_commit=args.registry_commit,
        expected_release_decision_status=args.expected_release_decision_status,
    )
    release_payload = resolved.release_payload
    packet = _load_json(PACKET_PATH)
    download_text = _load_text(DOWNLOAD_PATH)
    status_text = _load_text(STATUS_PATH)

    _verify_packet(
        packet,
        release_payload,
        resolved.authority,
        resolved.authority_source,
        resolved.served_mirror,
    )
    artifacts = authority_artifacts(resolved.authority)
    _verify_download_artifacts(download_text, release_payload, artifacts)

    available_platforms = [
        PLATFORM_LABELS.get(platform, platform)
        for platform in authority_platform_ids(resolved.authority)
    ]
    missing_platforms = _missing_platforms(available_platforms)
    expected_shelf_truth = _shelf_truth_line(
        release_payload.get("releaseStatus") or release_payload.get("status"),
        available_platforms,
    )
    expected_architecture_line = _architecture_scope_line(artifacts)
    expected_missing_line = _missing_installer_lane_line(missing_platforms)

    _require_contains("DOWNLOAD.md", download_text, expected_shelf_truth)
    _require_contains("STATUS.md", status_text, expected_shelf_truth)
    _require_contains("STATUS.md", status_text, expected_architecture_line)
    if missing_platforms:
        _require_contains("STATUS.md", status_text, expected_missing_line)
    if "macOS" in missing_platforms:
        _require_contains("DOWNLOAD.md", download_text, "There is no public macOS download today.")

    print("public_downloads_match_registry:ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
