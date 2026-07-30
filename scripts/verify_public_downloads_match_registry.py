#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


REPO_ROOT = Path(__file__).resolve().parents[1]
DOWNLOAD_PATH = REPO_ROOT / "DOWNLOAD.md"
STATUS_PATH = REPO_ROOT / "STATUS.md"
PACKET_PATH = REPO_ROOT / ".guide-internal" / "receipts" / "CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json"
REGISTRY_ENV = "CHUMMER_REGISTRY_RELEASE_CHANNEL"
CANONICAL_RELEASE_CHANNEL_SOURCE = "https://chummer.run/downloads/RELEASE_CHANNEL.generated.json"

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
SAFE_GENERATION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$")
SAFE_DOWNLOAD_FILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,199}$")


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


def _english_join(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def _public_source_label(path: Path) -> str:
    del path
    return CANONICAL_RELEASE_CHANNEL_SOURCE


def _resolve_registry_manifest() -> Path:
    override = os.environ.get(REGISTRY_ENV, "").strip()
    if override:
        candidate = Path(override).expanduser()
        if candidate.is_file():
            return candidate
        raise FileNotFoundError(f"{REGISTRY_ENV} does not point to a file: {candidate}")

    candidates = (
        REPO_ROOT.parent / "chummer-hub-registry" / ".codex-studio" / "published" / "RELEASE_CHANNEL.generated.json",
        REPO_ROOT.parent / "chummer6-hub-registry" / ".codex-studio" / "published" / "RELEASE_CHANNEL.generated.json",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("Could not resolve the canonical registry release channel manifest.")


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


def _public_registry_artifacts(release_payload: dict[str, object]) -> list[dict[str, object]]:
    artifacts = _release_artifacts(release_payload)
    promoted_ids = {
        str(item.get("artifactId") or item.get("id") or "").strip()
        for item in _promoted_installer_tuples(release_payload)
        if str(item.get("artifactId") or item.get("id") or "").strip()
    }
    if promoted_ids:
        selected = [
            item
            for item in artifacts
            if str(item.get("artifactId") or item.get("id") or "").strip() in promoted_ids
        ]
        if selected:
            return selected
    return artifacts


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


def _missing_platforms(release_payload: dict[str, object], available_platforms: list[str]) -> list[str]:
    coverage = _release_tuple_coverage(release_payload)
    explicit = coverage.get("missingRequiredPlatforms")
    if isinstance(explicit, list):
        missing = {_platform_key(item) for item in explicit}
        return [PLATFORM_LABELS[key] for key in PLATFORM_ORDER if key in missing]
    present = {_platform_key(item) for item in available_platforms}
    return [label for label in _required_platforms(release_payload) if _platform_key(label) not in present]


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


def _architecture_scope_line(release_payload: dict[str, object]) -> str:
    promoted = _promoted_installer_tuples(release_payload)
    promoted_keys = {
        (_platform_key(item.get("platform")), str(item.get("rid") or "").strip())
        for item in promoted
    }

    available_labels: list[str] = []
    missing_labels: list[str] = []
    for platform_key_value, rid, label in ARCHITECTURE_SCOPE_EXPECTATIONS:
        if (platform_key_value, rid) in promoted_keys:
            available_labels.append(label)
        else:
            missing_labels.append(label)

    macos_labels = [
        _macos_architecture_label(str(item.get("rid") or ""), str(item.get("arch") or ""))
        for item in promoted
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


def _download_delivery_identity(value: object) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None

    parsed = urlsplit(raw)
    if parsed.query or parsed.fragment or parsed.username or parsed.password:
        return None
    if parsed.scheme:
        if parsed.scheme.lower() != "https" or (parsed.hostname or "").lower() != "chummer.run":
            return None
        if parsed.port not in (None, 443):
            return None
    elif parsed.netloc or not parsed.path.startswith("/") or parsed.path.startswith("//"):
        return None

    if unquote(parsed.path) != parsed.path or "\\" in parsed.path:
        return None
    segments = parsed.path.split("/")
    if any(segment in {".", ".."} for segment in segments):
        return None

    stable_match = re.fullmatch(r"/downloads/files/([^/]+)", parsed.path)
    generation_match = re.fullmatch(r"/downloads/g/([^/]+)/files/([^/]+)", parsed.path)
    if stable_match:
        file_name = stable_match.group(1)
    elif generation_match and SAFE_GENERATION_ID_RE.fullmatch(generation_match.group(1)):
        file_name = generation_match.group(2)
    else:
        return None
    return file_name if SAFE_DOWNLOAD_FILE_RE.fullmatch(file_name) else None


def _download_urls_are_delivery_equivalent(
    documented_url: object,
    registry_url: object,
    expected_file_name: str,
) -> bool:
    documented_identity = _download_delivery_identity(documented_url)
    registry_identity = _download_delivery_identity(registry_url)
    return (
        documented_identity == expected_file_name
        and registry_identity == expected_file_name
    )


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


def _verify_download_artifacts(download_text: str, release_payload: dict[str, object]) -> None:
    docs_artifacts = _parse_download_artifacts(download_text)
    registry_by_filename = _registry_artifacts_by_filename(release_payload)
    promoted_artifact_ids = _promoted_artifact_ids(release_payload)
    sha_lines = _parse_sha256_lines(download_text)

    for artifact in docs_artifacts:
        file_name = str(artifact.get("fileName") or "").strip()
        if file_name not in registry_by_filename:
            raise ValueError(f"DOWNLOAD.md artifact {file_name!r} does not exist in the canonical registry manifest")
        registry_artifact = registry_by_filename[file_name]
        registry_label = str(registry_artifact.get("platformLabel") or "").strip()
        expected_label = (
            f"{registry_label} archive package"
            if str(registry_artifact.get("kind") or "").strip() == "archive"
            else registry_label
        )
        docs_label = str(artifact.get("label") or "").strip()
        if expected_label != docs_label:
            raise ValueError(f"DOWNLOAD.md label for {file_name} does not match registry platformLabel")
        if not _download_urls_are_delivery_equivalent(
            artifact.get("downloadUrl"),
            registry_artifact.get("downloadUrl"),
            file_name,
        ):
            raise ValueError(f"DOWNLOAD.md URL for {file_name} does not match registry downloadUrl")
        if int(registry_artifact.get("sizeBytes") or 0) != int(artifact.get("sizeBytes") or 0):
            raise ValueError(f"DOWNLOAD.md size for {file_name} does not match registry sizeBytes")
        documented_sha256 = sha_lines.get(docs_label) or sha_lines.get(registry_label)
        if not documented_sha256:
            raise ValueError(f"DOWNLOAD.md is missing a SHA256 row for {docs_label!r}")
        if str(registry_artifact.get("sha256") or "").strip().lower() != documented_sha256.lower():
            raise ValueError(f"DOWNLOAD.md SHA256 for {file_name} does not match registry sha256")
        if str(registry_artifact.get("compatibilityState") or "").strip() != "compatible":
            raise ValueError(f"Registry artifact {file_name} is not compatibilityState=compatible")
        access_class = str(registry_artifact.get("installAccessClass") or "").strip()
        expected_access = {
            "open_public": "Public download",
            "account_required": "Sign-in required",
        }.get(access_class)
        if expected_access is None:
            raise ValueError(f"Registry artifact {file_name} has unsupported installAccessClass={access_class!r}")
        if str(artifact.get("access") or "").strip() != expected_access:
            raise ValueError(f"DOWNLOAD.md access for {file_name} does not match registry installAccessClass")
        artifact_id = str(registry_artifact.get("artifactId") or registry_artifact.get("id") or "").strip()
        if (
            str(registry_artifact.get("kind") or "").strip() == "installer"
            and promoted_artifact_ids
            and artifact_id not in promoted_artifact_ids
        ):
            raise ValueError(f"Registry artifact {file_name} is not in desktopTupleCoverage.promotedInstallerTuples")


def _verify_packet(packet: dict[str, object], release_payload: dict[str, object], registry_path: Path) -> None:
    artifacts = _public_registry_artifacts(release_payload)
    available_platforms = _available_platforms(artifacts)
    required_platforms = _required_platforms(release_payload)
    missing_platforms = _missing_platforms(release_payload, available_platforms)
    expected_source = _public_source_label(registry_path)
    expected_shelf_truth = _shelf_truth_line(release_payload.get("status"), available_platforms)
    expected_architecture_line = _architecture_scope_line(release_payload)
    expected_missing_line = _missing_installer_lane_line(missing_platforms)

    if str(packet.get("generated_from") or "").strip() != expected_source:
        raise ValueError("release truth packet generated_from does not point at the canonical registry manifest")
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


def main() -> int:
    registry_path = _resolve_registry_manifest()
    release_payload = _load_json(registry_path)
    packet = _load_json(PACKET_PATH)
    download_text = _load_text(DOWNLOAD_PATH)
    status_text = _load_text(STATUS_PATH)

    _verify_packet(packet, release_payload, registry_path)
    _verify_download_artifacts(download_text, release_payload)

    artifacts = _public_registry_artifacts(release_payload)
    available_platforms = _available_platforms(artifacts)
    missing_platforms = _missing_platforms(release_payload, available_platforms)
    expected_shelf_truth = _shelf_truth_line(release_payload.get("status"), available_platforms)
    expected_architecture_line = _architecture_scope_line(release_payload)
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
