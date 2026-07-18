#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


AUTHORITY_CONTRACT = "chummer.release-truth-projection/v1"
CANONICAL_RELEASE_CHANNEL_SOURCE = "https://chummer.run/downloads/RELEASE_CHANNEL.generated.json"
ALLOWED_RELEASE_DECISION_STATUSES = frozenset({"review_required", "preview_ready", "stable_ready"})
_COMMIT_RE = re.compile(r"[0-9a-f]{40}")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_PUBLIC_ACCESS_CLASSES = frozenset({"open_public", "account_recommended"})
_KNOWN_ACCESS_CLASSES = _PUBLIC_ACCESS_CLASSES | {"account_required"}


@dataclass(frozen=True)
class ResolvedReleaseAuthority:
    release_payload: dict[str, object]
    authority: dict[str, object]


def _load_json_bytes(raw: bytes, source: Path) -> dict[str, object]:
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"{source} must contain a JSON object")
    return payload


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _clean(value: object) -> str:
    return str(value or "").strip()


def _platform_id(value: object) -> str:
    cleaned = _clean(value).lower()
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


def _promoted_installer_tuples(release_payload: dict[str, object]) -> list[dict[str, object]]:
    coverage = release_payload.get("desktopTupleCoverage")
    if not isinstance(coverage, dict):
        return []
    raw = coverage.get("promotedInstallerTuples")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _is_revoked(artifact: dict[str, object]) -> bool:
    if artifact.get("revoked") is True:
        return True
    return _clean(artifact.get("revokeState") or artifact.get("revocationState")).lower() in {
        "revoked",
        "blocked",
    }


def public_release_artifacts(release_payload: dict[str, object]) -> list[dict[str, object]]:
    """Return the promoted, compatible installer shelf used by every public projection."""

    artifacts = _release_artifacts(release_payload)
    promoted_ids = {
        _clean(item.get("artifactId") or item.get("id"))
        for item in _promoted_installer_tuples(release_payload)
        if _clean(item.get("artifactId") or item.get("id"))
    }
    if not promoted_ids:
        return []
    candidates = [
        item
        for item in artifacts
        if _clean(item.get("artifactId") or item.get("id")) in promoted_ids
    ]
    return [
        item
        for item in candidates
        if _clean(item.get("kind")).lower() == "installer"
        and _clean(item.get("compatibilityState")).lower() == "compatible"
        and not _is_revoked(item)
    ]


def _available_platforms(artifacts: list[dict[str, object]]) -> list[str]:
    values = {
        _platform_id(item.get("platformId") or item.get("platform") or item.get("rid"))
        for item in artifacts
    }
    return sorted(item for item in values if item)


def _primary_head_by_platform(
    release_payload: dict[str, object],
    artifacts: list[dict[str, object]],
) -> dict[str, str]:
    tuple_heads = {
        _clean(item.get("artifactId") or item.get("id")): _clean(item.get("head")).lower()
        for item in _promoted_installer_tuples(release_payload)
        if _clean(item.get("artifactId") or item.get("id"))
    }
    heads_by_platform: dict[str, set[str]] = {}
    for artifact in artifacts:
        platform = _platform_id(artifact.get("platformId") or artifact.get("platform") or artifact.get("rid"))
        if not platform:
            continue
        artifact_id = _clean(artifact.get("artifactId") or artifact.get("id"))
        head = _clean(artifact.get("head")).lower() or tuple_heads.get(artifact_id, "")
        heads_by_platform.setdefault(platform, set())
        if head:
            heads_by_platform[platform].add(head)

    result: dict[str, str] = {}
    for platform in sorted(heads_by_platform):
        heads = sorted(heads_by_platform[platform])
        result[platform] = "avalonia" if "avalonia" in heads else heads[0] if heads else "unknown"
    return result


def _download_access_posture(artifacts: list[dict[str, object]]) -> str:
    if not artifacts:
        return "unavailable"
    access_classes = {_clean(item.get("installAccessClass")).lower() for item in artifacts}
    if any(item not in _KNOWN_ACCESS_CLASSES for item in access_classes):
        return "unknown"
    has_public = bool(access_classes & _PUBLIC_ACCESS_CLASSES)
    has_required = "account_required" in access_classes
    if has_public and has_required:
        return "mixed"
    if has_required:
        return "account_required"
    return "public"


def _git_output(repo_root: Path, *args: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"git {' '.join(args)} failed: {detail}")
    return completed.stdout


def _verify_git_blob(path: Path, registry_commit: str, expected_bytes: bytes) -> tuple[Path, str]:
    if not _COMMIT_RE.fullmatch(registry_commit):
        raise ValueError("registry commit must be an exact lowercase 40-hex commit ID")

    resolved_path = path.expanduser().resolve(strict=True)
    root_text = _git_output(resolved_path.parent, "rev-parse", "--show-toplevel").decode("utf-8").strip()
    repo_root = Path(root_text).resolve(strict=True)
    try:
        relative_path = resolved_path.relative_to(repo_root).as_posix()
    except ValueError as exc:
        raise ValueError(f"authority path is outside its registry repository: {resolved_path}") from exc

    resolved_commit = _git_output(repo_root, "rev-parse", "--verify", f"{registry_commit}^{{commit}}").decode("utf-8").strip()
    if resolved_commit != registry_commit:
        raise ValueError("registry commit did not resolve to the exact requested commit")
    committed_bytes = _git_output(repo_root, "show", f"{registry_commit}:{relative_path}")
    if committed_bytes != expected_bytes:
        raise ValueError(f"authority bytes do not match {registry_commit}:{relative_path}")
    return repo_root, relative_path


def _required_release_value(release_payload: dict[str, object], *field_names: str) -> str:
    for field_name in field_names:
        value = _clean(release_payload.get(field_name))
        if value:
            return value
    raise ValueError(f"release authority manifest is missing required field: {' or '.join(field_names)}")


def resolve_release_authority(
    manifest_path: Path,
    *,
    served_mirror: str = CANONICAL_RELEASE_CHANNEL_SOURCE,
    registry_commit: str = "",
    release_decision_path: Path | None = None,
    expected_release_decision_status: str = "",
    release_mode: bool = False,
) -> ResolvedReleaseAuthority:
    manifest_path = manifest_path.expanduser().resolve(strict=True)
    manifest_bytes = manifest_path.read_bytes()
    release_payload = _load_json_bytes(manifest_bytes, manifest_path)
    manifest_sha256 = _sha256(manifest_bytes)

    if release_mode:
        if not registry_commit:
            raise ValueError("release mode requires an explicit registry commit")
        if release_decision_path is None:
            raise ValueError("release mode requires an explicit release decision receipt")
        if expected_release_decision_status not in ALLOWED_RELEASE_DECISION_STATUSES:
            allowed = ", ".join(sorted(ALLOWED_RELEASE_DECISION_STATUSES))
            raise ValueError(f"release mode requires one exact release decision posture: {allowed}")

    manifest_repo_root: Path | None = None
    manifest_relative_path = manifest_path.name
    if registry_commit:
        manifest_repo_root, manifest_relative_path = _verify_git_blob(manifest_path, registry_commit, manifest_bytes)

    manifest_decision_status = _clean(release_payload.get("releaseDecisionStatus"))
    manifest_decision_sha256 = _clean(release_payload.get("releaseDecisionSha256")).lower()
    decision_status = manifest_decision_status or "missing"
    decision_sha256 = manifest_decision_sha256 if _SHA256_RE.fullmatch(manifest_decision_sha256) else "missing"
    decision_relative_path = ""

    if release_decision_path is not None:
        release_decision_path = release_decision_path.expanduser().resolve(strict=True)
        decision_bytes = release_decision_path.read_bytes()
        decision_payload = _load_json_bytes(decision_bytes, release_decision_path)
        decision_status = _clean(decision_payload.get("releaseDecisionStatus"))
        if decision_status not in ALLOWED_RELEASE_DECISION_STATUSES:
            raise ValueError("release decision receipt has an unsupported or ambiguous releaseDecisionStatus")
        decision_sha256 = _sha256(decision_bytes)
        if registry_commit:
            decision_repo_root, decision_relative_path = _verify_git_blob(
                release_decision_path,
                registry_commit,
                decision_bytes,
            )
            if manifest_repo_root != decision_repo_root:
                raise ValueError("manifest and release decision must be immutable blobs in the same registry repository")
        else:
            decision_relative_path = release_decision_path.name

        if manifest_decision_status != decision_status:
            raise ValueError("manifest releaseDecisionStatus does not exactly match the release decision receipt")
        if manifest_decision_sha256 != decision_sha256:
            raise ValueError("manifest releaseDecisionSha256 does not match the exact release decision receipt bytes")

    if expected_release_decision_status and decision_status != expected_release_decision_status:
        raise ValueError(
            "release decision posture mismatch: "
            f"expected {expected_release_decision_status!r}, found {decision_status!r}"
        )

    if release_mode:
        _required_release_value(release_payload, "releaseVersion", "version")
        _required_release_value(release_payload, "channel", "channelId")
        _required_release_value(release_payload, "releaseStatus", "status")
        _required_release_value(release_payload, "rolloutState")
        _required_release_value(release_payload, "supportabilityState")
        _required_release_value(release_payload, "generatedAt", "generated_at")
        if release_payload.get("schemaVersion") is None:
            raise ValueError("release authority manifest is missing required field: schemaVersion")
        embedded_commit = _clean(release_payload.get("registryCommit"))
        if embedded_commit and embedded_commit != registry_commit:
            raise ValueError("manifest registryCommit does not match the explicit immutable authority commit")
        embedded_manifest_sha = _clean(release_payload.get("manifestSha256")).lower()
        if embedded_manifest_sha and embedded_manifest_sha != manifest_sha256:
            raise ValueError("manifest manifestSha256 does not match the exact authority bytes")

    artifacts = public_release_artifacts(release_payload)
    authority_source: dict[str, object]
    if registry_commit:
        authority_source = {
            "kind": "git_blob",
            "manifestPath": manifest_relative_path,
            "registryCommit": registry_commit,
        }
        if decision_relative_path:
            authority_source["releaseDecisionPath"] = decision_relative_path
    else:
        authority_source = {
            "kind": "explicit_manifest",
            "manifestPath": manifest_path.name,
        }

    release_status = _clean(release_payload.get("releaseStatus") or release_payload.get("status")) or "unknown"
    authority = {
        "artifactCount": len(artifacts),
        "authoritySource": authority_source,
        "availablePlatforms": _available_platforms(artifacts),
        "channel": _clean(release_payload.get("channel") or release_payload.get("channelId")) or "unknown",
        "contract": AUTHORITY_CONTRACT,
        "downloadAccessPosture": _download_access_posture(artifacts),
        "knownIssueSummary": _clean(release_payload.get("knownIssueSummary")),
        "manifestGeneratedAt": _clean(release_payload.get("generatedAt") or release_payload.get("generated_at")),
        "manifestSha256": manifest_sha256,
        "manifestVersion": release_payload.get("schemaVersion"),
        "primaryHeadByPlatform": _primary_head_by_platform(release_payload, artifacts),
        "registryCommit": registry_commit or _clean(release_payload.get("registryCommit")) or "missing",
        "releaseDecisionSha256": decision_sha256,
        "releaseDecisionStatus": decision_status,
        "releaseStatus": release_status,
        "releaseVersion": _clean(release_payload.get("releaseVersion") or release_payload.get("version")) or "unknown",
        "rolloutState": _clean(release_payload.get("rolloutState")) or "unknown",
        "servedMirror": served_mirror,
        "supportabilityState": _clean(release_payload.get("supportabilityState")) or "unknown",
    }
    return ResolvedReleaseAuthority(release_payload=release_payload, authority=authority)


def require_authority_match(packet: dict[str, object], expected: dict[str, object]) -> None:
    packet_authority = packet.get("authority")
    if not isinstance(packet_authority, dict):
        raise ValueError("release truth packet is missing the authority projection")
    for field_name, expected_value in expected.items():
        if packet_authority.get(field_name) != expected_value:
            raise ValueError(f"release truth packet authority.{field_name} drifted from immutable Registry authority")
