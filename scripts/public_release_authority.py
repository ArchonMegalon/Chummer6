#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse


AUTHORITY_CONTRACT = "chummer.release-authority-snapshot/v2"
EXPECTED_REGISTRY_REPOSITORY = "ArchonMegalon/chummer6-hub-registry"
CANONICAL_RELEASE_CHANNEL_SOURCE = "https://chummer.run/downloads/RELEASE_CHANNEL.generated.json"
ALLOWED_RELEASE_DECISION_STATUSES = frozenset({"review_required", "preview_ready", "stable_ready"})
PREVIEW_DECISION_CONTRACT = "chummer.preview-release-decision/v1"
STABLE_DECISION_CONTRACT = "chummer.final_gold_graph"
STABLE_DECISION_CONTRACT_VERSION = 2
MANIFEST_FILE_NAME = "RELEASE_CHANNEL.json"
DECISION_FILE_NAME = "RELEASE_DECISION.json"
SNAPSHOT_FILE_NAME = "SNAPSHOT.json"
_COMMIT_RE = re.compile(r"[0-9a-f]{40}")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_ACCESS_CLASSES = frozenset({"open_public", "account_recommended", "account_required"})
_INVALID_ID_TOKENS = frozenset({"unknown", "missing", "invalid"})
_SNAPSHOT_PROPERTIES = frozenset(
    {
        "authorityContract",
        "releaseVersion",
        "channel",
        "status",
        "rolloutState",
        "supportabilityState",
        "availablePlatforms",
        "primaryHeadByPlatform",
        "artifactCount",
        "downloadAccessPosture",
        "knownIssueSummary",
        "manifestSha256",
        "registryRepository",
        "registryCommit",
        "releaseDecisionStatus",
        "releaseDecisionSha256",
        "releaseDecisionPath",
        "supportOwner",
        "nextActions",
        "artifacts",
        "manifestPath",
    }
)
_SNAPSHOT_ARTIFACT_PROPERTIES = frozenset(
    {
        "artifactId",
        "head",
        "platform",
        "rid",
        "arch",
        "kind",
        "downloadUrl",
        "sha256",
        "sizeBytes",
        "compatibilityState",
        "promotionState",
        "publicationScope",
        "revokeState",
        "publicInstallRoute",
        "installAccessClass",
    }
)


@dataclass(frozen=True)
class ResolvedReleaseAuthority:
    release_payload: dict[str, object]
    decision_payload: dict[str, object]
    authority: dict[str, object]
    authority_source: dict[str, object]
    served_mirror: str


def _reject_constant(value: str) -> object:
    raise ValueError(f"non-finite JSON value is forbidden: {value}")


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON property is forbidden: {key}")
        result[key] = value
    return result


def _load_json_bytes(raw: bytes, source: Path) -> dict[str, object]:
    payload = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_strict_object,
        parse_constant=_reject_constant,
    )
    if not isinstance(payload, dict):
        raise TypeError(f"{source} must contain a JSON object")
    return payload


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _clean(value: object) -> str:
    return str(value or "").strip()


def _token(value: object) -> str:
    return _clean(value).lower()


def _require_exact_properties(payload: dict[str, object], expected: frozenset[str], source: str) -> None:
    actual = frozenset(payload)
    if actual != expected:
        missing = ", ".join(sorted(expected - actual))
        unexpected = ", ".join(sorted(actual - expected))
        raise ValueError(f"{source} property set is invalid (missing: [{missing}]; unexpected: [{unexpected}])")


def _require_string(payload: dict[str, object], field: str, source: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{source} {field} must be a nonempty string")
    return value.strip()


def _require_sha256(value: object, field: str) -> str:
    cleaned = _clean(value)
    if not _SHA256_RE.fullmatch(cleaned):
        raise ValueError(f"{field} must be an exact lowercase SHA-256 digest")
    return cleaned


def _require_commit(value: object, field: str) -> str:
    cleaned = _clean(value)
    if not _COMMIT_RE.fullmatch(cleaned):
        raise ValueError(f"{field} must be an exact lowercase 40-hex Git commit")
    return cleaned


def _string_list(value: object, field: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{field} must be an array of nonempty strings")
    result = [item.strip() for item in value]
    if not allow_empty and not result:
        raise ValueError(f"{field} must not be empty")
    if result != sorted(set(result)):
        raise ValueError(f"{field} must contain unique values in ordinal order")
    return result


def _head_map(value: object, field: str, *, allow_empty: bool = False) -> dict[str, str]:
    if not isinstance(value, dict) or (not allow_empty and not value):
        requirement = "an object" if allow_empty else "a nonempty object"
        raise ValueError(f"{field} must be {requirement}")
    result: dict[str, str] = {}
    for platform, head in value.items():
        if not isinstance(platform, str) or not platform.strip() or not isinstance(head, str) or not head.strip():
            raise ValueError(f"{field} must map nonempty platform IDs to nonempty head IDs")
        result[platform.strip()] = head.strip()
    if list(result) != sorted(result):
        raise ValueError(f"{field} keys must be in ordinal order")
    return result


def _require_https_url(value: object, field: str) -> str:
    cleaned = _clean(value)
    parsed = urlparse(cleaned)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or bool(parsed.fragment)
    ):
        raise ValueError(f"{field} must be a safe absolute HTTPS URL")
    return cleaned


def _require_public_install_route(value: object, field: str) -> str:
    cleaned = _clean(value)
    parsed = urlparse(cleaned)
    decoded_path = unquote(parsed.path)
    if (
        not cleaned.startswith("/")
        or cleaned.startswith("//")
        or parsed.scheme
        or parsed.netloc
        or parsed.query
        or parsed.fragment
        or parsed.path != cleaned
        or ".." in decoded_path.split("/")
        or "\\" in decoded_path
        or any(ord(character) < 32 for character in cleaned)
    ):
        raise ValueError(f"{field} must be a safe root-relative path without query, fragment, or traversal")
    return cleaned


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


def _normalize_github_remote(value: str) -> str:
    cleaned = value.strip()
    if cleaned.startswith("git@github.com:"):
        path = cleaned[len("git@github.com:") :]
    else:
        parsed = urlparse(cleaned)
        if parsed.hostname != "github.com":
            return ""
        path = parsed.path.lstrip("/")
    return path.removesuffix(".git").strip("/")


def _resolve_registry_repository(snapshot_path: Path, registry_commit: str) -> tuple[Path, str]:
    root_text = _git_output(snapshot_path.parent, "rev-parse", "--show-toplevel").decode("utf-8").strip()
    repo_root = Path(root_text).resolve(strict=True)
    try:
        relative_path = snapshot_path.relative_to(repo_root).as_posix()
    except ValueError as exc:
        raise ValueError("authority snapshot must be inside the Registry repository") from exc
    remote = _git_output(repo_root, "remote", "get-url", "origin").decode("utf-8").strip()
    if _normalize_github_remote(remote).casefold() != EXPECTED_REGISTRY_REPOSITORY.casefold():
        raise ValueError(f"authority repository must be {EXPECTED_REGISTRY_REPOSITORY}")
    resolved_commit = _git_output(repo_root, "rev-parse", "--verify", f"{registry_commit}^{{commit}}").decode("utf-8").strip()
    if resolved_commit != registry_commit:
        raise ValueError("Registry commit did not resolve to the exact requested commit")
    return repo_root, relative_path


def _snapshot_artifacts(snapshot: dict[str, object]) -> list[dict[str, object]]:
    raw = snapshot.get("artifacts")
    if not isinstance(raw, list):
        raise ValueError("SNAPSHOT.json artifacts must be an array")
    artifacts: list[dict[str, object]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"SNAPSHOT.json artifacts[{index}] must be an object")
        _require_exact_properties(item, _SNAPSHOT_ARTIFACT_PROPERTIES, f"SNAPSHOT.json artifacts[{index}]")
        for field in (
            "artifactId",
            "head",
            "platform",
            "rid",
            "arch",
            "kind",
            "downloadUrl",
            "compatibilityState",
            "promotionState",
            "publicationScope",
            "revokeState",
            "publicInstallRoute",
            "installAccessClass",
        ):
            _require_string(item, field, f"SNAPSHOT.json artifacts[{index}]")
        for field in (
            "head",
            "platform",
            "rid",
            "arch",
            "kind",
            "compatibilityState",
            "promotionState",
            "publicationScope",
            "revokeState",
            "installAccessClass",
        ):
            if _token(item.get(field)) != _clean(item.get(field)):
                raise ValueError(f"SNAPSHOT.json artifacts[{index}].{field} must be normalized lowercase")
        for field in ("artifactId", "head", "platform", "rid", "arch"):
            if _token(item.get(field)) in _INVALID_ID_TOKENS:
                raise ValueError(f"SNAPSHOT.json artifacts[{index}].{field} uses a forbidden sentinel ID")
        _require_sha256(item.get("sha256"), f"SNAPSHOT.json artifacts[{index}].sha256")
        size = item.get("sizeBytes")
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            raise ValueError(f"SNAPSHOT.json artifacts[{index}].sizeBytes must be a positive integer")
        if _token(item.get("kind")) != "installer":
            raise ValueError("SNAPSHOT.json public shelf may contain installer artifacts only")
        if _token(item.get("compatibilityState")) != "compatible":
            raise ValueError("SNAPSHOT.json public shelf artifacts must be compatibilityState=compatible")
        if _token(item.get("promotionState")) != "promoted":
            raise ValueError("SNAPSHOT.json public shelf artifacts must be promotionState=promoted")
        if _token(item.get("publicationScope")) != "signed-in-and-public":
            raise ValueError("SNAPSHOT.json public shelf artifacts must be publicationScope=signed-in-and-public")
        if _token(item.get("revokeState")) != "not_revoked":
            raise ValueError("SNAPSHOT.json public shelf artifacts must be revokeState=not_revoked")
        if _token(item.get("installAccessClass")) not in _ACCESS_CLASSES:
            raise ValueError("SNAPSHOT.json artifact installAccessClass is unsupported")
        download_url = _require_https_url(
            item.get("downloadUrl"),
            f"SNAPSHOT.json artifacts[{index}].downloadUrl",
        )
        public_route = _require_public_install_route(
            item.get("publicInstallRoute"),
            f"SNAPSHOT.json artifacts[{index}].publicInstallRoute",
        )
        if download_url == public_route:
            raise ValueError("SNAPSHOT.json downloadUrl and publicInstallRoute must be distinct")
        artifacts.append(dict(item))
    artifact_ids = [_clean(item.get("artifactId")) for item in artifacts]
    if artifact_ids != sorted(set(artifact_ids)):
        raise ValueError("SNAPSHOT.json artifacts must have unique artifactId values in ordinal order")
    return artifacts


def _manifest_artifacts(manifest: dict[str, object]) -> dict[str, dict[str, object]]:
    raw = manifest.get("artifacts")
    if not isinstance(raw, list):
        raise ValueError("RELEASE_CHANNEL.json artifacts must be an array")
    result: dict[str, dict[str, object]] = {}
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("RELEASE_CHANNEL.json artifacts must contain objects")
        artifact_id = _clean(item.get("artifactId") or item.get("id"))
        if not artifact_id or artifact_id in result:
            raise ValueError("RELEASE_CHANNEL.json artifactId values must be unique and nonempty")
        result[artifact_id] = item
    return result


def _route_truth(manifest: dict[str, object]) -> list[dict[str, object]]:
    coverage = manifest.get("desktopTupleCoverage")
    if not isinstance(coverage, dict):
        raise ValueError("RELEASE_CHANNEL.json desktopTupleCoverage is required")
    raw = coverage.get("desktopRouteTruth")
    if not isinstance(raw, list) or any(not isinstance(item, dict) for item in raw):
        raise ValueError("RELEASE_CHANNEL.json desktopRouteTruth is required")
    return [dict(item) for item in raw]


def _active_revoked_artifact_ids(manifest: dict[str, object]) -> tuple[bool, set[str]]:
    trust = manifest.get("publicTrustMetrics")
    trust = trust if isinstance(trust, dict) else {}
    revocations = trust.get("revocationFacts")
    revocations = revocations if isinstance(revocations, dict) else {}
    active = revocations.get("activeRevocations")
    if not isinstance(active, list) or any(not isinstance(item, dict) for item in active):
        raise ValueError("RELEASE_CHANNEL.json activeRevocations must be an array of objects")
    rows = active
    artifact_ids = [
        _clean(item.get("artifactId"))
        for item in rows
        if _clean(item.get("artifactId"))
    ]
    if len(artifact_ids) != len(rows) or len(set(artifact_ids)) != len(artifact_ids):
        raise ValueError("RELEASE_CHANNEL.json activeRevocations must name unique artifactId values")
    declared_count = revocations.get("activeRevocationCount")
    if (
        not isinstance(declared_count, int)
        or isinstance(declared_count, bool)
        or declared_count != len(rows)
    ):
        raise ValueError("RELEASE_CHANNEL.json activeRevocationCount does not match activeRevocations")
    if not isinstance(revocations.get("channelRevoked"), bool):
        raise ValueError("RELEASE_CHANNEL.json channelRevoked must be boolean")
    return (
        revocations.get("channelRevoked") is True,
        set(artifact_ids),
    )


def _eligible_manifest_artifacts(
    manifest: dict[str, object],
    primary_heads: dict[str, str],
    allowed_fallback_heads: dict[str, set[str]],
) -> list[dict[str, object]]:
    artifacts = _manifest_artifacts(manifest)
    coverage = manifest.get("desktopTupleCoverage")
    if not isinstance(coverage, dict):
        raise ValueError("RELEASE_CHANNEL.json desktopTupleCoverage is required")
    promoted = coverage.get("promotedInstallerTuples")
    if not isinstance(promoted, list):
        raise ValueError("RELEASE_CHANNEL.json promotedInstallerTuples is required")
    routes = _route_truth(manifest)
    channel_revoked, active_revocations = _active_revoked_artifact_ids(manifest)
    if channel_revoked:
        return []

    selected: list[dict[str, object]] = []
    seen: set[str] = set()
    for promoted_item in promoted:
        if not isinstance(promoted_item, dict):
            raise ValueError("promotedInstallerTuples must contain objects")
        artifact_id = _clean(promoted_item.get("artifactId") or promoted_item.get("id"))
        if not artifact_id or artifact_id in seen:
            raise ValueError("promotedInstallerTuples artifactId values must be unique and nonempty")
        seen.add(artifact_id)
        artifact = artifacts.get(artifact_id)
        if artifact is None:
            raise ValueError(f"promoted artifact {artifact_id!r} is absent from RELEASE_CHANNEL.json artifacts")
        platform = _token(artifact.get("platform"))
        head = _token(artifact.get("head") or promoted_item.get("head"))
        for field in ("platform", "head", "rid", "arch"):
            if _token(promoted_item.get(field)) != _token(artifact.get(field)):
                raise ValueError(f"promoted artifact {artifact_id!r} tuple does not match its {field}")
        route_matches = [
            route
            for route in routes
            if _clean(route.get("artifactId")) == artifact_id
            and _token(route.get("platform")) == platform
            and _token(route.get("head")) == head
        ]
        if len(route_matches) != 1:
            raise ValueError(f"artifact {artifact_id!r} must have exactly one matching desktopRouteTruth row")
        route = route_matches[0]
        route_role = _token(route.get("routeRole"))
        if head == primary_heads.get(platform):
            expected_role = "primary"
        elif head in allowed_fallback_heads.get(platform, set()):
            expected_role = "fallback"
        else:
            raise ValueError(f"artifact {artifact_id!r} head is neither approved primary nor explicit fallback")
        if route_role != expected_role:
            raise ValueError(f"artifact {artifact_id!r} routeRole must be {expected_role}")

        artifact_status = _token(artifact.get("status"))
        eligible = (
            _token(artifact.get("kind")) == "installer"
            and _token(artifact.get("compatibilityState")) == "compatible"
            and _token(route.get("promotionState")) == "promoted"
            and _token(route.get("publicationScope")) == "signed-in-and-public"
            and _token(route.get("revokeState")) == "not_revoked"
            and artifact_status not in {"revoked", "blocked"}
            and artifact_id not in active_revocations
        )
        if not eligible:
            continue
        _require_sha256(artifact.get("sha256"), f"artifact {artifact_id} sha256")
        size = artifact.get("sizeBytes")
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            raise ValueError(f"artifact {artifact_id} sizeBytes must be a positive integer")
        download_url = _require_https_url(artifact.get("downloadUrl"), f"artifact {artifact_id} downloadUrl")
        public_route = _require_public_install_route(
            route.get("publicInstallRoute"),
            f"artifact {artifact_id} publicInstallRoute",
        )
        if download_url == public_route:
            raise ValueError(f"artifact {artifact_id} downloadUrl and publicInstallRoute must be distinct")
        if _token(artifact.get("installAccessClass")) not in _ACCESS_CLASSES:
            raise ValueError(f"artifact {artifact_id} installAccessClass is unsupported")
        selected.append(
            {
                "artifactId": artifact_id,
                "head": _token(artifact.get("head")),
                "platform": platform,
                "rid": _token(artifact.get("rid")),
                "arch": _token(artifact.get("arch")),
                "kind": "installer",
                "downloadUrl": download_url,
                "sha256": _token(artifact.get("sha256")),
                "sizeBytes": size,
                "compatibilityState": "compatible",
                "promotionState": "promoted",
                "publicationScope": "signed-in-and-public",
                "revokeState": "not_revoked",
                "publicInstallRoute": public_route,
                "installAccessClass": _token(artifact.get("installAccessClass")),
            }
        )
    return sorted(selected, key=lambda item: _clean(item.get("artifactId")))


def _decision_scope(
    decision: dict[str, object],
    decision_status: str,
    snapshot: dict[str, object],
) -> tuple[dict[str, str], dict[str, set[str]]]:
    if decision_status in {"review_required", "preview_ready"}:
        if _clean(decision.get("contractName")) != PREVIEW_DECISION_CONTRACT:
            raise ValueError(f"{decision_status} requires decision contract {PREVIEW_DECISION_CONTRACT}")
        bindings = {
            "releaseVersion": _clean(decision.get("releaseVersion")),
            "channel": _token(decision.get("channel")),
            "manifestSha256": _token(decision.get("manifestSha256")),
            "registryCommit": _token(decision.get("registryCommit")),
        }
        allow_empty_scope = decision_status == "review_required"
        platforms = _string_list(
            decision.get("platforms"),
            "RELEASE_DECISION.json platforms",
            allow_empty=allow_empty_scope,
        )
        primary_heads = _head_map(
            decision.get("primaryHeadByPlatform"),
            "RELEASE_DECISION.json primaryHeadByPlatform",
            allow_empty=allow_empty_scope,
        )
        if any(_token(platform) != platform or _token(head) != head for platform, head in primary_heads.items()):
            raise ValueError("RELEASE_DECISION.json primaryHeadByPlatform must use normalized lowercase IDs")
        if _clean(decision.get("supportOwner")) != _clean(snapshot.get("supportOwner")):
            raise ValueError("release decision supportOwner does not match SNAPSHOT.json")
        artifact_access_class = _token(decision.get("artifactAccessClass"))
        expected_access_class = (
            "review_required"
            if decision_status == "review_required" and snapshot.get("artifactCount") == 0
            else _token(snapshot.get("downloadAccessPosture"))
        )
        if artifact_access_class != expected_access_class:
            raise ValueError("release decision artifactAccessClass does not match its exact release posture")
        raw_fallbacks = decision.get("fallbackHeadsByPlatform")
        if not isinstance(raw_fallbacks, dict):
            raise ValueError("RELEASE_DECISION.json fallbackHeadsByPlatform must be an object")
        if list(raw_fallbacks) != sorted(raw_fallbacks):
            raise ValueError("RELEASE_DECISION.json fallbackHeadsByPlatform keys must be in ordinal order")
        fallback_heads: dict[str, set[str]] = {}
        for platform, raw_heads in raw_fallbacks.items():
            normalized_platform = _token(platform)
            if normalized_platform != platform or normalized_platform not in platforms:
                raise ValueError("release decision fallback scope contains an invalid or out-of-scope platform")
            heads = _string_list(raw_heads, f"fallbackHeadsByPlatform.{platform}", allow_empty=True)
            if any(_token(head) != head for head in heads):
                raise ValueError("release decision fallback heads must use normalized lowercase IDs")
            if any(_token(head) in _INVALID_ID_TOKENS for head in heads):
                raise ValueError("release decision fallback heads must not use sentinel IDs")
            if primary_heads.get(normalized_platform) in heads:
                raise ValueError("release decision primary head cannot also be an explicit fallback")
            fallback_heads[normalized_platform] = set(heads)
    else:
        if _clean(decision.get("contract_name")) != STABLE_DECISION_CONTRACT or decision.get("contract_version") != 2:
            raise ValueError(
                f"stable_ready requires decision contract {STABLE_DECISION_CONTRACT} v{STABLE_DECISION_CONTRACT_VERSION}"
            )
        live = decision.get("live_release")
        authority = decision.get("release_authority")
        if not isinstance(live, dict) or not isinstance(authority, dict):
            raise ValueError("stable release decision requires live_release and release_authority bindings")
        bindings = {
            "releaseVersion": _clean(live.get("version")),
            "channel": _token(live.get("channel")),
            "manifestSha256": _token(live.get("manifest_sha256")),
            "registryCommit": _token(live.get("registry_commit")),
        }
        platforms = _string_list(live.get("available_platforms"), "live_release.available_platforms")
        primary_heads = _head_map(live.get("primary_head_by_platform"), "live_release.primary_head_by_platform")
        if any(_token(platform) != platform or _token(head) != head for platform, head in primary_heads.items()):
            raise ValueError("stable decision primary_head_by_platform must use normalized lowercase IDs")
        fallback_heads = {}
        if _clean(authority.get("contract")) != AUTHORITY_CONTRACT:
            raise ValueError("stable decision release_authority contract does not match SNAPSHOT.json")
        if _token(authority.get("manifest_sha256")) != bindings["manifestSha256"]:
            raise ValueError("stable decision release_authority manifest digest binding disagrees with live_release")
        if _token(authority.get("registry_commit")) != bindings["registryCommit"]:
            raise ValueError("stable decision release_authority registry commit binding disagrees with live_release")
        stable_bindings = {
            "status": _token(live.get("status")),
            "rolloutState": _token(live.get("rollout_state")),
            "supportabilityState": _token(live.get("supportability_state")),
            "artifactCount": live.get("artifact_count"),
            "downloadAccessPosture": _token(live.get("download_access_posture")),
            "knownIssueSummary": _clean(live.get("known_issue_summary")),
            "releaseDecisionStatus": _token(live.get("release_decision_status")),
        }
        expected_stable_bindings = {
            "status": _token(snapshot.get("status")),
            "rolloutState": _token(snapshot.get("rolloutState")),
            "supportabilityState": _token(snapshot.get("supportabilityState")),
            "artifactCount": snapshot.get("artifactCount"),
            "downloadAccessPosture": _token(snapshot.get("downloadAccessPosture")),
            "knownIssueSummary": _clean(snapshot.get("knownIssueSummary")),
            "releaseDecisionStatus": "stable_ready",
        }
        if stable_bindings != expected_stable_bindings:
            raise ValueError("stable decision live_release does not exactly bind the Registry snapshot projection")
        if _token(authority.get("release_decision_status")) != "stable_ready":
            raise ValueError("stable decision release_authority does not bind stable_ready posture")

    expected_bindings = {
        "releaseVersion": _clean(snapshot.get("releaseVersion")),
        "channel": _token(snapshot.get("channel")),
        "manifestSha256": _token(snapshot.get("manifestSha256")),
        "registryCommit": _token(snapshot.get("registryCommit")),
    }
    if bindings != expected_bindings:
        raise ValueError("release decision does not exactly bind releaseVersion, channel, manifestSha256, and registryCommit")
    if platforms != snapshot.get("availablePlatforms"):
        raise ValueError("release decision platform scope does not match SNAPSHOT.json")
    if primary_heads != snapshot.get("primaryHeadByPlatform"):
        raise ValueError("release decision primaryHeadByPlatform does not match SNAPSHOT.json")
    return primary_heads, fallback_heads


def _validate_snapshot(
    snapshot: dict[str, object],
    snapshot_sha256: str,
    explicit_registry_commit: str,
    expected_decision_status: str,
) -> tuple[list[dict[str, object]], list[str], dict[str, str]]:
    _require_exact_properties(snapshot, _SNAPSHOT_PROPERTIES, "SNAPSHOT.json")
    if _clean(snapshot.get("authorityContract")) != AUTHORITY_CONTRACT:
        raise ValueError(f"SNAPSHOT.json authorityContract must be {AUTHORITY_CONTRACT}")
    if _clean(snapshot.get("registryRepository")) != EXPECTED_REGISTRY_REPOSITORY:
        raise ValueError(f"SNAPSHOT.json registryRepository must be {EXPECTED_REGISTRY_REPOSITORY}")
    release_version = _require_string(snapshot, "releaseVersion", "SNAPSHOT.json")
    for field in ("channel", "status", "rolloutState", "supportabilityState", "knownIssueSummary", "supportOwner"):
        _require_string(snapshot, field, "SNAPSHOT.json")
    for field in ("channel", "status", "rolloutState", "supportabilityState"):
        if _token(snapshot.get(field)) != _clean(snapshot.get(field)):
            raise ValueError(f"SNAPSHOT.json {field} must be normalized lowercase")
    if _clean(snapshot.get("manifestPath")) != MANIFEST_FILE_NAME:
        raise ValueError(f"SNAPSHOT.json manifestPath must be {MANIFEST_FILE_NAME}")
    if _clean(snapshot.get("releaseDecisionPath")) != DECISION_FILE_NAME:
        raise ValueError(f"SNAPSHOT.json releaseDecisionPath must be {DECISION_FILE_NAME}")
    _require_sha256(snapshot.get("manifestSha256"), "SNAPSHOT.json manifestSha256")
    _require_sha256(snapshot.get("releaseDecisionSha256"), "SNAPSHOT.json releaseDecisionSha256")
    registry_commit = _require_commit(snapshot.get("registryCommit"), "SNAPSHOT.json registryCommit")
    if registry_commit != explicit_registry_commit:
        raise ValueError("SNAPSHOT.json registryCommit does not match the explicit Registry commit")
    decision_status = _token(snapshot.get("releaseDecisionStatus"))
    if (
        decision_status != _clean(snapshot.get("releaseDecisionStatus"))
        or decision_status not in ALLOWED_RELEASE_DECISION_STATUSES
        or decision_status != expected_decision_status
    ):
        raise ValueError("SNAPSHOT.json releaseDecisionStatus does not match the exact expected decision posture")
    allow_empty_shelf = decision_status == "review_required"
    platforms = _string_list(
        snapshot.get("availablePlatforms"),
        "SNAPSHOT.json availablePlatforms",
        allow_empty=allow_empty_shelf,
    )
    if any(_token(platform) != platform for platform in platforms):
        raise ValueError("SNAPSHOT.json availablePlatforms must contain normalized lowercase platform IDs")
    if any(_token(platform) in _INVALID_ID_TOKENS for platform in platforms):
        raise ValueError("SNAPSHOT.json availablePlatforms must not use sentinel IDs")
    heads = _head_map(
        snapshot.get("primaryHeadByPlatform"),
        "SNAPSHOT.json primaryHeadByPlatform",
        allow_empty=allow_empty_shelf,
    )
    if list(heads) != platforms:
        raise ValueError("SNAPSHOT.json primaryHeadByPlatform keys must exactly match availablePlatforms")
    if any(_token(platform) != platform or _token(head) != head for platform, head in heads.items()):
        raise ValueError("SNAPSHOT.json primaryHeadByPlatform must use normalized lowercase IDs")
    if any(
        _token(platform) in _INVALID_ID_TOKENS or _token(head) in _INVALID_ID_TOKENS
        for platform, head in heads.items()
    ):
        raise ValueError("SNAPSHOT.json primaryHeadByPlatform must not use sentinel IDs")
    artifacts = _snapshot_artifacts(snapshot)
    artifact_count = snapshot.get("artifactCount")
    if not isinstance(artifact_count, int) or isinstance(artifact_count, bool) or artifact_count != len(artifacts):
        raise ValueError("SNAPSHOT.json artifactCount must exactly equal artifacts.length")
    artifact_platforms = sorted({_token(item.get("platform")) for item in artifacts})
    if artifact_platforms != platforms:
        raise ValueError("SNAPSHOT.json availablePlatforms must equal exact artifact platforms")
    for platform, head in heads.items():
        matches = [item for item in artifacts if _token(item.get("platform")) == platform and _token(item.get("head")) == head]
        if not matches:
            raise ValueError(f"SNAPSHOT.json primary head {head!r} has no eligible artifact on {platform!r}")
    access_classes = sorted({_token(item.get("installAccessClass")) for item in artifacts})
    expected_access = "unavailable" if not access_classes else access_classes[0] if len(access_classes) == 1 else "mixed"
    if _token(snapshot.get("downloadAccessPosture")) != expected_access:
        raise ValueError("SNAPSHOT.json downloadAccessPosture does not match exact public shelf access classes")
    if not artifacts and not (
        decision_status == "review_required" and _token(snapshot.get("downloadAccessPosture")) == "unavailable"
    ):
        raise ValueError("an empty public shelf is valid only for review_required with unavailable posture")
    _string_list(
        snapshot.get("nextActions"),
        "SNAPSHOT.json nextActions",
        allow_empty=decision_status != "review_required",
    )
    return artifacts, platforms, heads


def resolve_release_authority(
    snapshot_path: Path,
    *,
    served_mirror: str = CANONICAL_RELEASE_CHANNEL_SOURCE,
    registry_commit: str,
    release_decision_path: Path,
    expected_release_decision_status: str,
) -> ResolvedReleaseAuthority:
    if expected_release_decision_status not in ALLOWED_RELEASE_DECISION_STATUSES:
        allowed = ", ".join(sorted(ALLOWED_RELEASE_DECISION_STATUSES))
        raise ValueError(f"expected release decision status must be one of: {allowed}")
    registry_commit = _require_commit(registry_commit, "explicit Registry commit")
    if not served_mirror.strip():
        raise ValueError("served mirror must be nonempty")

    snapshot_path = snapshot_path.expanduser().resolve(strict=True)
    snapshot_bytes = snapshot_path.read_bytes()
    snapshot_sha256 = _sha256(snapshot_bytes)
    if snapshot_path.name != SNAPSHOT_FILE_NAME:
        raise ValueError(f"authority snapshot must be named {SNAPSHOT_FILE_NAME}")
    expected_tail = ("snapshots", _clean(_load_json_bytes(snapshot_bytes, snapshot_path).get("releaseVersion")), snapshot_sha256, SNAPSHOT_FILE_NAME)
    if tuple(snapshot_path.parts[-4:]) != expected_tail:
        raise ValueError("authority snapshot path must be snapshots/<releaseVersion>/<snapshotSha256>/SNAPSHOT.json")
    snapshot = _load_json_bytes(snapshot_bytes, snapshot_path)
    snapshot_artifacts, _, snapshot_heads = _validate_snapshot(
        snapshot,
        snapshot_sha256,
        registry_commit,
        expected_release_decision_status,
    )

    repo_root, snapshot_relative_path = _resolve_registry_repository(snapshot_path, registry_commit)
    manifest_path = (snapshot_path.parent / _clean(snapshot.get("manifestPath"))).resolve(strict=True)
    decision_path_from_snapshot = (snapshot_path.parent / _clean(snapshot.get("releaseDecisionPath"))).resolve(strict=True)
    release_decision_path = release_decision_path.expanduser().resolve(strict=True)
    if manifest_path.parent != snapshot_path.parent or decision_path_from_snapshot.parent != snapshot_path.parent:
        raise ValueError("authority manifest and decision must be immutable siblings of SNAPSHOT.json")
    if release_decision_path != decision_path_from_snapshot:
        raise ValueError("explicit release decision path does not match SNAPSHOT.json releaseDecisionPath")

    manifest_bytes = manifest_path.read_bytes()
    decision_bytes = release_decision_path.read_bytes()
    if _sha256(manifest_bytes) != _token(snapshot.get("manifestSha256")):
        raise ValueError("SNAPSHOT.json manifestSha256 does not match exact sibling manifest bytes")
    if _sha256(decision_bytes) != _token(snapshot.get("releaseDecisionSha256")):
        raise ValueError("SNAPSHOT.json releaseDecisionSha256 does not match exact sibling decision bytes")
    manifest = _load_json_bytes(manifest_bytes, manifest_path)
    decision = _load_json_bytes(decision_bytes, release_decision_path)
    decision_status = _token(decision.get("status"))
    if decision_status != _clean(decision.get("status")) or decision_status != expected_release_decision_status:
        raise ValueError("release decision receipt status does not match exact expected posture")
    primary_heads, fallback_heads = _decision_scope(decision, decision_status, snapshot)

    for field, snapshot_value, manifest_value in (
        ("releaseVersion", _clean(snapshot.get("releaseVersion")), _clean(manifest.get("releaseVersion") or manifest.get("version"))),
        ("channel", _token(snapshot.get("channel")), _token(manifest.get("channel") or manifest.get("channelId"))),
        ("status", _token(snapshot.get("status")), _token(manifest.get("releaseStatus") or manifest.get("status"))),
        ("rolloutState", _token(snapshot.get("rolloutState")), _token(manifest.get("rolloutState"))),
        ("supportabilityState", _token(snapshot.get("supportabilityState")), _token(manifest.get("supportabilityState"))),
        ("knownIssueSummary", _clean(snapshot.get("knownIssueSummary")), _clean(manifest.get("knownIssueSummary"))),
        ("supportOwner", _clean(snapshot.get("supportOwner")), _clean(manifest.get("supportOwner"))),
    ):
        if snapshot_value != manifest_value:
            raise ValueError(f"SNAPSHOT.json {field} does not match exact RELEASE_CHANNEL.json bytes")

    eligible = _eligible_manifest_artifacts(manifest, primary_heads, fallback_heads)
    eligible_by_id = {_clean(item.get("artifactId") or item.get("id")): item for item in eligible}
    snapshot_by_id = {_clean(item.get("artifactId")): item for item in snapshot_artifacts}
    if list(snapshot_by_id) != sorted(eligible_by_id) or set(snapshot_by_id) != set(eligible_by_id):
        raise ValueError("SNAPSHOT.json artifacts do not equal the exact promoted compatible non-revoked public shelf")
    for artifact_id, snapshot_artifact in snapshot_by_id.items():
        if snapshot_artifact != eligible_by_id[artifact_id]:
            raise ValueError(
                f"SNAPSHOT.json artifact {artifact_id!r} does not exactly match its 15-field Registry projection"
            )

    authority_source = {
        "registryRepository": EXPECTED_REGISTRY_REPOSITORY,
        "registryCommit": registry_commit,
        "snapshotPath": snapshot_relative_path,
        "snapshotSha256": snapshot_sha256,
        "manifestPath": manifest_path.relative_to(repo_root).as_posix(),
        "manifestSha256": _sha256(manifest_bytes),
        "manifestVersion": manifest.get("schemaVersion"),
        "manifestGeneratedAt": _clean(manifest.get("generatedAt") or manifest.get("generated_at")),
        "releaseDecisionPath": release_decision_path.relative_to(repo_root).as_posix(),
        "releaseDecisionSha256": _sha256(decision_bytes),
    }
    return ResolvedReleaseAuthority(
        release_payload=manifest,
        decision_payload=decision,
        authority=dict(snapshot),
        authority_source=authority_source,
        served_mirror=served_mirror,
    )


def authority_platform_ids(authority: dict[str, object]) -> list[str]:
    return _string_list(
        authority.get("availablePlatforms"),
        "authority.availablePlatforms",
        allow_empty=_token(authority.get("releaseDecisionStatus")) == "review_required",
    )


def authority_artifacts(authority: dict[str, object]) -> list[dict[str, object]]:
    return _snapshot_artifacts(authority)


def require_authority_match(
    packet: dict[str, object],
    expected_authority: dict[str, object],
    expected_source: dict[str, object],
    expected_served_mirror: str,
) -> None:
    if packet.get("authority") != expected_authority:
        raise ValueError("release truth packet authority drifted from immutable Registry SNAPSHOT.json")
    if packet.get("authority_source") != expected_source:
        raise ValueError("release truth packet authority_source drifted from immutable Registry authority")
    if packet.get("served_mirror") != expected_served_mirror:
        raise ValueError("release truth packet served_mirror drifted from the configured public mirror")
