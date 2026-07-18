#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
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
CURRENT_FILE_NAME = "CURRENT.json"
_COMMIT_RE = re.compile(r"[0-9a-f]{40}")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_ACCESS_CLASSES = frozenset({"open_public", "account_recommended", "account_required"})
_INVALID_ID_TOKENS = frozenset({"unknown", "missing", "invalid"})
_CURRENT_PROPERTIES = frozenset({"releaseVersion", "snapshotSha256", "decisionSha256", "status"})
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
    current_pointer: dict[str, object]


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
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{source} {field} must be a nonempty string")
    return value


def _optional_exact_string(value: object, field: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str) or value != value.strip():
        raise ValueError(f"{field} must be an exact string when present")
    return value


def _require_sha256(value: object, field: str) -> str:
    if not isinstance(value, str) or value != value.strip() or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{field} must be an exact lowercase SHA-256 digest")
    return value


def _require_commit(value: object, field: str) -> str:
    if not isinstance(value, str) or value != value.strip() or not _COMMIT_RE.fullmatch(value):
        raise ValueError(f"{field} must be an exact lowercase 40-hex Git commit")
    return value


def _string_list(value: object, field: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item or item != item.strip()
        for item in value
    ):
        raise ValueError(f"{field} must be an array of nonempty strings")
    result = list(value)
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
        if (
            not isinstance(platform, str)
            or not platform
            or platform != platform.strip()
            or not isinstance(head, str)
            or not head
            or head != head.strip()
        ):
            raise ValueError(f"{field} must map nonempty platform IDs to nonempty head IDs")
        result[platform] = head
    if list(result) != sorted(result):
        raise ValueError(f"{field} keys must be in ordinal order")
    return result


def _require_https_url(value: object, field: str) -> str:
    if not isinstance(value, str) or value != value.strip():
        raise ValueError(f"{field} must be a safe absolute HTTPS URL")
    cleaned = value
    parsed = urlparse(cleaned)
    decoded_path = unquote(parsed.path)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or bool(parsed.query)
        or bool(parsed.fragment)
        or not parsed.path.startswith("/")
        or ".." in decoded_path.split("/")
        or "\\" in decoded_path
        or any(ord(character) < 32 for character in cleaned)
    ):
        raise ValueError(f"{field} must be a safe absolute HTTPS URL")
    return cleaned


def _require_immutable_download_url(value: object, field: str) -> str:
    cleaned = _require_https_url(value, field)
    path = urlparse(cleaned).path
    match = re.fullmatch(r"/downloads/g/([A-Za-z0-9._+-]+)/files/([^/]+)", path)
    if (
        match is None
        or match.group(1) in {".", ".."}
        or unquote(path) != path
        or not match.group(2).strip()
    ):
        raise ValueError(
            f"{field} must use immutable /downloads/g/<generation>/files/<file> HTTPS routing"
        )
    return cleaned


def _require_public_install_route(value: object, field: str) -> str:
    if not isinstance(value, str) or value != value.strip():
        raise ValueError(f"{field} must be a safe root-relative path without query, fragment, or traversal")
    cleaned = value
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
        or re.fullmatch(r"/downloads/install/[^/]+", decoded_path) is None
        or "//" in cleaned
        or ".." in decoded_path.split("/")
        or "\\" in decoded_path
        or any(ord(character) < 32 for character in cleaned)
    ):
        raise ValueError(f"{field} must be a safe root-relative path without query, fragment, or traversal")
    return cleaned


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
            "artifactId",
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
        download_url = _require_immutable_download_url(
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
        artifact_id = _require_string(item, "artifactId", "RELEASE_CHANNEL.json artifact")
        compatibility_id = _clean(item.get("id"))
        if compatibility_id and compatibility_id != artifact_id:
            raise ValueError("RELEASE_CHANNEL.json artifact id alias disagrees with artifactId")
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
    rows = [dict(item) for item in raw]
    tuple_ids = [_clean(item.get("tupleId")) for item in rows]
    if any(not item for item in tuple_ids) or len(tuple_ids) != len(set(tuple_ids)):
        raise ValueError("RELEASE_CHANNEL.json desktopRouteTruth tupleId values must be unique and nonempty")
    return rows


def _publication_bindings(manifest: dict[str, object]) -> list[dict[str, object]]:
    raw = manifest.get("artifactPublicationBindings")
    if not isinstance(raw, list) or any(not isinstance(item, dict) for item in raw):
        raise ValueError("RELEASE_CHANNEL.json artifactPublicationBindings must be an array of objects")
    rows = [dict(item) for item in raw]
    binding_ids = [_clean(item.get("bindingId")) for item in rows]
    if any(not item for item in binding_ids) or len(binding_ids) != len(set(binding_ids)):
        raise ValueError("RELEASE_CHANNEL.json artifactPublicationBindings bindingId values must be unique and nonempty")
    return rows


def _active_revocations(manifest: dict[str, object]) -> tuple[bool, set[str], set[str]]:
    trust = manifest.get("publicTrustMetrics")
    trust = trust if isinstance(trust, dict) else {}
    revocations = trust.get("revocationFacts")
    revocations = revocations if isinstance(revocations, dict) else {}
    active = revocations.get("activeRevocations")
    if not isinstance(active, list) or any(not isinstance(item, dict) for item in active):
        raise ValueError("RELEASE_CHANNEL.json activeRevocations must be an array of objects")
    rows = active
    artifact_ids = [_clean(item.get("artifactId")) for item in rows if _clean(item.get("artifactId"))]
    tuple_ids = [_clean(item.get("tupleId")) for item in rows if _clean(item.get("tupleId"))]
    if len(set(artifact_ids)) != len(artifact_ids) or len(set(tuple_ids)) != len(tuple_ids):
        raise ValueError("RELEASE_CHANNEL.json activeRevocations identifiers must be unique")
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
        _clean(revocations.get("status")) == "clear" and revocations.get("channelRevoked") is False,
        set(artifact_ids),
        set(tuple_ids),
    )


def _eligible_manifest_artifacts(
    manifest: dict[str, object],
) -> tuple[list[dict[str, object]], dict[str, str], dict[str, set[str]]]:
    artifacts = _manifest_artifacts(manifest)
    routes = _route_truth(manifest)
    bindings = _publication_bindings(manifest)
    revocation_facts_clear, active_artifact_revocations, active_tuple_revocations = _active_revocations(manifest)
    generation_id = _require_string(manifest, "generationId", "RELEASE_CHANNEL.json")
    if len(generation_id) > 128 or re.fullmatch(r"[A-Za-z0-9._+-]+", generation_id) is None:
        raise ValueError("RELEASE_CHANNEL.json generationId must be one portable identifier")
    manifest_channel = _require_string(manifest, "channelId", "RELEASE_CHANNEL.json")
    manifest_version = _require_string(manifest, "version", "RELEASE_CHANNEL.json")

    eligible_rows: list[tuple[dict[str, object], str]] = []
    for artifact_id, artifact in artifacts.items():
        promoted_routes = [
            route
            for route in routes
            if route.get("artifactId") == artifact_id
            and route.get("promotionState") == "promoted"
        ]
        approved_bindings = [
            binding
            for binding in bindings
            if binding.get("artifactId") == artifact_id
            and binding.get("publicationScope") == "signed-in-and-public"
            and binding.get("publicationState") == "published"
        ]
        if not promoted_routes or not approved_bindings:
            continue
        if len(promoted_routes) != 1 or len(approved_bindings) != 1:
            raise ValueError(f"artifact {artifact_id!r} has ambiguous promoted route or public binding rows")
        route = promoted_routes[0]
        binding = approved_bindings[0]
        route_role = _require_string(route, "routeRole", f"route for artifact {artifact_id}")
        tuple_id = _require_string(route, "tupleId", f"route for artifact {artifact_id}")
        artifact_status = _optional_exact_string(artifact.get("status"), f"artifact {artifact_id} status")
        artifact_rollout = _optional_exact_string(
            artifact.get("rolloutState"),
            f"artifact {artifact_id} rolloutState",
        )
        if (
            _require_string(artifact, "kind", f"artifact {artifact_id}") != "installer"
            or _require_string(artifact, "compatibilityState", f"artifact {artifact_id}") != "compatible"
            or artifact_status in {"revoked", "blocked"}
            or artifact_rollout == "revoked"
            or artifact_status != _token(artifact_status)
            or artifact_rollout != _token(artifact_rollout)
            or _optional_exact_string(artifact.get("revokeReason"), f"artifact {artifact_id} revokeReason")
            or route.get("revokeState") != "not_revoked"
            or not revocation_facts_clear
            or artifact_id in active_artifact_revocations
            or tuple_id in active_tuple_revocations
        ):
            raise ValueError(f"promoted public artifact {artifact_id!r} must be compatible and non-revoked")
        if (
            route_role not in {"primary", "fallback"}
            or route.get("updateEligibility") != "eligible"
            or route.get("installPosture") != "installer_first"
        ):
            raise ValueError(f"promoted public artifact {artifact_id!r} has an invalid explicit route posture")
        public_route = _require_public_install_route(
            route.get("publicInstallRoute"),
            f"artifact {artifact_id} publicInstallRoute",
        )
        for field in ("head", "platform", "rid", "arch"):
            artifact_value = _require_string(artifact, field, f"artifact {artifact_id}")
            if (
                artifact_value != _require_string(route, field, f"route for artifact {artifact_id}")
                or artifact_value != _require_string(binding, field, f"binding for artifact {artifact_id}")
            ):
                raise ValueError(f"artifact {artifact_id!r} tuple does not match {field} across route and binding")
        if _require_string(artifact, "kind", f"artifact {artifact_id}") != _require_string(
            binding,
            "kind",
            f"binding for artifact {artifact_id}",
        ):
            raise ValueError(f"artifact {artifact_id!r} kind does not match its publication binding")
        if (
            manifest_channel != _require_string(binding, "channelId", f"binding for artifact {artifact_id}")
            or manifest_version != _require_string(binding, "releaseVersion", f"binding for artifact {artifact_id}")
            or tuple_id != _require_string(binding, "tupleId", f"binding for artifact {artifact_id}")
            or public_route != _require_string(binding, "publicInstallRoute", f"binding for artifact {artifact_id}")
            or not _require_string(binding, "publicShelfRef", f"binding for artifact {artifact_id}")
        ):
            raise ValueError(f"artifact {artifact_id!r} publication binding does not match its release and route")
        _require_sha256(artifact.get("sha256"), f"artifact {artifact_id} sha256")
        size = artifact.get("sizeBytes")
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            raise ValueError(f"artifact {artifact_id} sizeBytes must be a positive integer")
        file_name = _require_string(artifact, "fileName", f"artifact {artifact_id}")
        download_url = _require_immutable_download_url(artifact.get("downloadUrl"), f"artifact {artifact_id} downloadUrl")
        expected_path = f"/downloads/g/{generation_id}/files/{file_name}"
        if urlparse(download_url).path != expected_path:
            raise ValueError(f"artifact {artifact_id!r} downloadUrl must bind generationId and fileName")
        if _token(artifact.get("installAccessClass")) not in _ACCESS_CLASSES:
            raise ValueError(f"artifact {artifact_id} installAccessClass is unsupported")
        projection = {
            "artifactId": artifact_id,
            "head": _require_string(artifact, "head", f"artifact {artifact_id}"),
            "platform": _require_string(artifact, "platform", f"artifact {artifact_id}"),
            "rid": _require_string(artifact, "rid", f"artifact {artifact_id}"),
            "arch": _require_string(artifact, "arch", f"artifact {artifact_id}"),
            "kind": _require_string(artifact, "kind", f"artifact {artifact_id}"),
            "downloadUrl": download_url,
            "sha256": _require_sha256(artifact.get("sha256"), f"artifact {artifact_id} sha256"),
            "sizeBytes": size,
            "compatibilityState": _require_string(artifact, "compatibilityState", f"artifact {artifact_id}"),
            "promotionState": _require_string(route, "promotionState", f"route for artifact {artifact_id}"),
            "publicationScope": _require_string(binding, "publicationScope", f"binding for artifact {artifact_id}"),
            "revokeState": _require_string(route, "revokeState", f"route for artifact {artifact_id}"),
            "publicInstallRoute": public_route,
            "installAccessClass": _require_string(artifact, "installAccessClass", f"artifact {artifact_id}"),
        }
        _snapshot_artifacts({"artifacts": [projection]})
        eligible_rows.append((projection, route_role))

    eligible_rows.sort(key=lambda row: _clean(row[0].get("artifactId")))
    selected = [row[0] for row in eligible_rows]
    platforms = sorted({_clean(item.get("platform")) for item in selected})
    primary_heads: dict[str, str] = {}
    fallback_heads: dict[str, set[str]] = {}
    for platform in platforms:
        primary_rows = [
            item for item, role in eligible_rows if role == "primary" and _clean(item.get("platform")) == platform
        ]
        if len(primary_rows) != 1:
            raise ValueError(f"RELEASE_CHANNEL.json must identify exactly one eligible primary route for {platform!r}")
        primary_heads[platform] = _clean(primary_rows[0].get("head"))
        fallback = {
            _clean(item.get("head"))
            for item, role in eligible_rows
            if role == "fallback" and _clean(item.get("platform")) == platform
        }
        if primary_heads[platform] in fallback:
            raise ValueError(f"RELEASE_CHANNEL.json primary head cannot also be a fallback on {platform!r}")
        if fallback:
            fallback_heads[platform] = fallback
    return selected, primary_heads, fallback_heads


def _decision_scope(
    decision: dict[str, object],
    decision_status: str,
    snapshot: dict[str, object],
) -> tuple[dict[str, str], dict[str, set[str]]]:
    preview_contract = decision.get("contractName") == PREVIEW_DECISION_CONTRACT
    stable_contract = (
        decision.get("contract_name") == STABLE_DECISION_CONTRACT
        and decision.get("contract_version") == STABLE_DECISION_CONTRACT_VERSION
    )
    if preview_contract:
        if decision_status not in {"review_required", "preview_ready"}:
            raise ValueError(f"{PREVIEW_DECISION_CONTRACT} cannot assert {decision_status}")
        release_version = _require_string(decision, "releaseVersion", "RELEASE_DECISION.json")
        channel = _require_string(decision, "channel", "RELEASE_DECISION.json")
        if channel != _token(channel):
            raise ValueError("RELEASE_DECISION.json channel must be normalized lowercase")
        manifest_sha256 = _require_sha256(decision.get("manifestSha256"), "RELEASE_DECISION.json manifestSha256")
        registry_commit = _require_commit(decision.get("registryCommit"), "RELEASE_DECISION.json registryCommit")
        bindings = {
            "releaseVersion": release_version,
            "channel": channel,
            "manifestSha256": manifest_sha256,
            "registryCommit": registry_commit,
        }
        candidate_values: list[str] = []
        for field in ("authoritySnapshotSha256", "candidateDecisionStatus", "candidateDecisionSha256"):
            value = decision.get(field)
            if not isinstance(value, str):
                raise ValueError(f"RELEASE_DECISION.json {field} must be a string")
            candidate_values.append(value)
        all_candidate_values_empty = not any(candidate_values)
        if not (decision_status == "review_required" and all_candidate_values_empty):
            _require_sha256(candidate_values[0], "RELEASE_DECISION.json authoritySnapshotSha256")
            if candidate_values[1] not in {"review_required", "preview_ready"}:
                raise ValueError("RELEASE_DECISION.json candidateDecisionStatus is invalid")
            _require_sha256(candidate_values[2], "RELEASE_DECISION.json candidateDecisionSha256")
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
        support_owner = _require_string(decision, "supportOwner", "RELEASE_DECISION.json")
        if support_owner != snapshot.get("supportOwner"):
            raise ValueError("release decision supportOwner does not match SNAPSHOT.json")
        artifact_access_class = _require_string(
            decision,
            "artifactAccessClass",
            "RELEASE_DECISION.json",
        )
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
    elif stable_contract:
        if decision_status != "stable_ready":
            raise ValueError(
                f"{STABLE_DECISION_CONTRACT} can assert stable_ready only; review_required must use the preview contract"
            )
        if _require_string(decision, "status", "RELEASE_DECISION.json") != "pass":
            raise ValueError("stable release decision status must be pass")
        live = decision.get("live_release")
        authority = decision.get("release_authority")
        if not isinstance(live, dict) or not isinstance(authority, dict):
            raise ValueError("stable release decision requires live_release and release_authority bindings")
        live_version = _require_string(live, "version", "RELEASE_DECISION.json live_release")
        live_channel = _require_string(live, "channel", "RELEASE_DECISION.json live_release")
        if live_channel != _token(live_channel):
            raise ValueError("stable decision live_release channel must be normalized lowercase")
        bindings = {
            "releaseVersion": live_version,
            "channel": live_channel,
            "manifestSha256": _require_sha256(
                live.get("manifest_sha256"),
                "RELEASE_DECISION.json live_release manifest_sha256",
            ),
            "registryCommit": _require_commit(
                live.get("registry_commit"),
                "RELEASE_DECISION.json live_release registry_commit",
            ),
        }
        platforms = _string_list(live.get("available_platforms"), "live_release.available_platforms")
        primary_heads = _head_map(live.get("primary_head_by_platform"), "live_release.primary_head_by_platform")
        if any(_token(platform) != platform or _token(head) != head for platform, head in primary_heads.items()):
            raise ValueError("stable decision primary_head_by_platform must use normalized lowercase IDs")
        fallback_heads = {}
        if _require_string(authority, "contract", "RELEASE_DECISION.json release_authority") != AUTHORITY_CONTRACT:
            raise ValueError("stable decision release_authority contract does not match SNAPSHOT.json")
        authority_manifest_sha256 = _require_sha256(
            authority.get("manifest_sha256"),
            "RELEASE_DECISION.json release_authority manifest_sha256",
        )
        authority_registry_commit = _require_commit(
            authority.get("registry_commit"),
            "RELEASE_DECISION.json release_authority registry_commit",
        )
        if authority_manifest_sha256 != bindings["manifestSha256"]:
            raise ValueError("stable decision release_authority manifest digest binding disagrees with live_release")
        if authority_registry_commit != bindings["registryCommit"]:
            raise ValueError("stable decision release_authority registry commit binding disagrees with live_release")
        stable_bindings = {
            "status": _require_string(live, "status", "RELEASE_DECISION.json live_release"),
            "rolloutState": _require_string(
                live,
                "rollout_state",
                "RELEASE_DECISION.json live_release",
            ),
            "supportabilityState": _require_string(
                live,
                "supportability_state",
                "RELEASE_DECISION.json live_release",
            ),
            "artifactCount": live.get("artifact_count"),
            "downloadAccessPosture": _require_string(
                live,
                "download_access_posture",
                "RELEASE_DECISION.json live_release",
            ),
            "knownIssueSummary": _require_string(
                live,
                "known_issue_summary",
                "RELEASE_DECISION.json live_release",
            ),
            "releaseDecisionStatus": _require_string(
                live,
                "release_decision_status",
                "RELEASE_DECISION.json live_release",
            ),
        }
        if not isinstance(stable_bindings["artifactCount"], int) or isinstance(
            stable_bindings["artifactCount"], bool
        ):
            raise ValueError("stable decision live_release artifact_count must be an integer")
        expected_stable_bindings = {
            "status": snapshot.get("status"),
            "rolloutState": snapshot.get("rolloutState"),
            "supportabilityState": snapshot.get("supportabilityState"),
            "artifactCount": snapshot.get("artifactCount"),
            "downloadAccessPosture": snapshot.get("downloadAccessPosture"),
            "knownIssueSummary": snapshot.get("knownIssueSummary"),
            "releaseDecisionStatus": decision_status,
        }
        if stable_bindings != expected_stable_bindings:
            raise ValueError("stable decision live_release does not exactly bind the Registry snapshot projection")
        if _require_string(
            authority,
            "release_decision_status",
            "RELEASE_DECISION.json release_authority",
        ) != decision_status:
            raise ValueError("stable decision release_authority does not bind its exact decision posture")
        if _require_string(decision, "releaseVersion", "RELEASE_DECISION.json") != snapshot.get("releaseVersion"):
            raise ValueError("stable decision top-level releaseVersion does not match SNAPSHOT.json")
    else:
        raise ValueError("release decision contract is unsupported")

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
    if _require_string(snapshot, "authorityContract", "SNAPSHOT.json") != AUTHORITY_CONTRACT:
        raise ValueError(f"SNAPSHOT.json authorityContract must be {AUTHORITY_CONTRACT}")
    if _require_string(snapshot, "registryRepository", "SNAPSHOT.json") != EXPECTED_REGISTRY_REPOSITORY:
        raise ValueError(f"SNAPSHOT.json registryRepository must be {EXPECTED_REGISTRY_REPOSITORY}")
    release_version = _require_string(snapshot, "releaseVersion", "SNAPSHOT.json")
    for field in ("channel", "status", "rolloutState", "supportabilityState", "knownIssueSummary", "supportOwner"):
        _require_string(snapshot, field, "SNAPSHOT.json")
    for field in ("channel", "status", "rolloutState", "supportabilityState"):
        if _token(snapshot.get(field)) != _clean(snapshot.get(field)):
            raise ValueError(f"SNAPSHOT.json {field} must be normalized lowercase")
    if _require_string(snapshot, "manifestPath", "SNAPSHOT.json") != MANIFEST_FILE_NAME:
        raise ValueError(f"SNAPSHOT.json manifestPath must be {MANIFEST_FILE_NAME}")
    if _require_string(snapshot, "releaseDecisionPath", "SNAPSHOT.json") != DECISION_FILE_NAME:
        raise ValueError(f"SNAPSHOT.json releaseDecisionPath must be {DECISION_FILE_NAME}")
    _require_sha256(snapshot.get("manifestSha256"), "SNAPSHOT.json manifestSha256")
    _require_sha256(snapshot.get("releaseDecisionSha256"), "SNAPSHOT.json releaseDecisionSha256")
    registry_commit = _require_commit(snapshot.get("registryCommit"), "SNAPSHOT.json registryCommit")
    if registry_commit != explicit_registry_commit:
        raise ValueError("SNAPSHOT.json registryCommit does not match the explicit Registry commit")
    raw_decision_status = _require_string(snapshot, "releaseDecisionStatus", "SNAPSHOT.json")
    decision_status = _token(raw_decision_status)
    if (
        decision_status != raw_decision_status
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
    download_access_posture = _require_string(snapshot, "downloadAccessPosture", "SNAPSHOT.json")
    if download_access_posture != expected_access:
        raise ValueError("SNAPSHOT.json downloadAccessPosture does not match exact public shelf access classes")
    if not artifacts and not (
        decision_status == "review_required" and download_access_posture == "unavailable"
    ):
        raise ValueError("an empty public shelf is valid only for review_required with unavailable posture")
    _string_list(
        snapshot.get("nextActions"),
        "SNAPSHOT.json nextActions",
        allow_empty=decision_status != "review_required",
    )
    return artifacts, platforms, heads


def resolve_release_authority(
    current_path: Path,
    *,
    served_mirror: str = CANONICAL_RELEASE_CHANNEL_SOURCE,
    registry_commit: str,
    expected_release_decision_status: str,
) -> ResolvedReleaseAuthority:
    if expected_release_decision_status not in ALLOWED_RELEASE_DECISION_STATUSES:
        allowed = ", ".join(sorted(ALLOWED_RELEASE_DECISION_STATUSES))
        raise ValueError(f"expected release decision status must be one of: {allowed}")
    registry_commit = _require_commit(registry_commit, "explicit Registry commit")
    served_mirror = _require_https_url(served_mirror, "served mirror")

    current_path = current_path.expanduser().resolve(strict=True)
    if current_path.name != CURRENT_FILE_NAME:
        raise ValueError(f"release authority pointer must be named {CURRENT_FILE_NAME}")
    authority_root = current_path.parent
    current_bytes = current_path.read_bytes()
    current = _load_json_bytes(current_bytes, current_path)
    _require_exact_properties(current, _CURRENT_PROPERTIES, CURRENT_FILE_NAME)
    release_version = _require_string(current, "releaseVersion", CURRENT_FILE_NAME)
    if (
        release_version in {".", ".."}
        or len(release_version) > 128
        or re.fullmatch(r"[A-Za-z0-9._-]+", release_version) is None
    ):
        raise ValueError("CURRENT.json releaseVersion must be one portable path segment")
    current_snapshot_sha256 = _require_sha256(current.get("snapshotSha256"), "CURRENT.json snapshotSha256")
    current_decision_sha256 = _require_sha256(current.get("decisionSha256"), "CURRENT.json decisionSha256")
    raw_current_status = _require_string(current, "status", CURRENT_FILE_NAME)
    current_status = _token(raw_current_status)
    if (
        current_status != raw_current_status
        or current_status not in ALLOWED_RELEASE_DECISION_STATUSES
        or current_status != expected_release_decision_status
    ):
        raise ValueError("CURRENT.json status does not match the exact expected release decision posture")

    expected_snapshot_path = (
        authority_root / "snapshots" / release_version / current_snapshot_sha256 / SNAPSHOT_FILE_NAME
    )
    snapshot_path = expected_snapshot_path.resolve(strict=True)
    try:
        snapshot_relative_path = snapshot_path.relative_to(authority_root).as_posix()
    except ValueError as exc:
        raise ValueError("CURRENT.json derived snapshot escapes the release authority root") from exc
    expected_relative_path = (
        f"snapshots/{release_version}/{current_snapshot_sha256}/{SNAPSHOT_FILE_NAME}"
    )
    if snapshot_relative_path != expected_relative_path:
        raise ValueError("CURRENT.json must derive the exact content-addressed snapshot path")
    snapshot_bytes = snapshot_path.read_bytes()
    snapshot_sha256 = _sha256(snapshot_bytes)
    if snapshot_sha256 != current_snapshot_sha256:
        raise ValueError("CURRENT.json snapshotSha256 does not match exact SNAPSHOT.json bytes")
    snapshot = _load_json_bytes(snapshot_bytes, snapshot_path)
    snapshot_artifacts, _, snapshot_heads = _validate_snapshot(
        snapshot,
        snapshot_sha256,
        registry_commit,
        expected_release_decision_status,
    )
    if (
        _clean(snapshot.get("releaseVersion")) != release_version
        or _token(snapshot.get("releaseDecisionSha256")) != current_decision_sha256
        or _token(snapshot.get("releaseDecisionStatus")) != current_status
    ):
        raise ValueError(
            "CURRENT.json releaseVersion, decisionSha256, and status must match SNAPSHOT.json"
        )

    manifest_path = (snapshot_path.parent / _clean(snapshot.get("manifestPath"))).resolve(strict=True)
    decision_path_from_snapshot = (snapshot_path.parent / _clean(snapshot.get("releaseDecisionPath"))).resolve(strict=True)
    if manifest_path.parent != snapshot_path.parent or decision_path_from_snapshot.parent != snapshot_path.parent:
        raise ValueError("authority manifest and decision must be immutable siblings of SNAPSHOT.json")

    manifest_bytes = manifest_path.read_bytes()
    decision_bytes = decision_path_from_snapshot.read_bytes()
    if _sha256(manifest_bytes) != _token(snapshot.get("manifestSha256")):
        raise ValueError("SNAPSHOT.json manifestSha256 does not match exact sibling manifest bytes")
    if _sha256(decision_bytes) != current_decision_sha256:
        raise ValueError("SNAPSHOT.json releaseDecisionSha256 does not match exact sibling decision bytes")
    manifest = _load_json_bytes(manifest_bytes, manifest_path)
    decision = _load_json_bytes(decision_bytes, decision_path_from_snapshot)
    for canonical, compatibility in (
        ("version", "releaseVersion"),
        ("channelId", "channel"),
        ("status", "releaseStatus"),
    ):
        compatibility_value = _optional_exact_string(
            manifest.get(compatibility),
            f"RELEASE_CHANNEL.json {compatibility}",
        )
        if compatibility_value and compatibility_value != _clean(manifest.get(canonical)):
            raise ValueError(
                f"RELEASE_CHANNEL.json compatibility field {compatibility} disagrees with canonical {canonical}"
            )
    raw_decision_status = _require_string(
        decision,
        "releaseDecisionStatus",
        "RELEASE_DECISION.json",
    )
    decision_status = _token(raw_decision_status)
    if (
        decision_status != raw_decision_status
        or decision_status != expected_release_decision_status
    ):
        raise ValueError("release decision releaseDecisionStatus does not match exact expected posture")
    if decision.get("contractName") == PREVIEW_DECISION_CONTRACT:
        if _require_string(decision, "status", "RELEASE_DECISION.json") != decision_status:
            raise ValueError("preview decision status must equal releaseDecisionStatus")
    elif (
        decision.get("contract_name") == STABLE_DECISION_CONTRACT
        and decision.get("contract_version") == STABLE_DECISION_CONTRACT_VERSION
    ):
        expected_graph_status = "pass" if decision_status == "stable_ready" else "review_required"
        if _require_string(decision, "status", "RELEASE_DECISION.json") != expected_graph_status:
            raise ValueError("stable decision status must be pass iff releaseDecisionStatus is stable_ready")
    primary_heads, fallback_heads = _decision_scope(decision, decision_status, snapshot)

    for field, snapshot_value, manifest_value in (
        (
            "releaseVersion",
            snapshot.get("releaseVersion"),
            _require_string(manifest, "version", "RELEASE_CHANNEL.json"),
        ),
        (
            "channel",
            snapshot.get("channel"),
            _require_string(manifest, "channelId", "RELEASE_CHANNEL.json"),
        ),
        (
            "status",
            snapshot.get("status"),
            _require_string(manifest, "status", "RELEASE_CHANNEL.json"),
        ),
        (
            "rolloutState",
            snapshot.get("rolloutState"),
            _require_string(manifest, "rolloutState", "RELEASE_CHANNEL.json"),
        ),
        (
            "supportabilityState",
            snapshot.get("supportabilityState"),
            _require_string(manifest, "supportabilityState", "RELEASE_CHANNEL.json"),
        ),
        (
            "knownIssueSummary",
            snapshot.get("knownIssueSummary"),
            _require_string(manifest, "knownIssueSummary", "RELEASE_CHANNEL.json"),
        ),
        (
            "supportOwner",
            snapshot.get("supportOwner"),
            _require_string(manifest, "supportOwner", "RELEASE_CHANNEL.json"),
        ),
    ):
        if snapshot_value != manifest_value:
            raise ValueError(f"SNAPSHOT.json {field} does not match exact RELEASE_CHANNEL.json bytes")

    eligible, manifest_primary_heads, manifest_fallback_heads = _eligible_manifest_artifacts(manifest)
    if primary_heads != manifest_primary_heads:
        raise ValueError("release decision primary-head scope does not equal the canonical Registry manifest projection")
    if fallback_heads != manifest_fallback_heads:
        raise ValueError("release decision fallback-head scope does not equal the canonical Registry manifest projection")
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
        "currentPath": CURRENT_FILE_NAME,
        "currentSha256": _sha256(current_bytes),
        "currentStatus": current_status,
        "snapshotPath": snapshot_relative_path,
        "snapshotSha256": snapshot_sha256,
        "manifestPath": manifest_path.relative_to(authority_root).as_posix(),
        "manifestSha256": _sha256(manifest_bytes),
        "manifestVersion": _clean(manifest.get("version")),
        "manifestSchemaVersion": manifest.get("schemaVersion"),
        "manifestGeneratedAt": _clean(manifest.get("generatedAt") or manifest.get("generated_at")),
        "releaseDecisionPath": decision_path_from_snapshot.relative_to(authority_root).as_posix(),
        "releaseDecisionSha256": _sha256(decision_bytes),
    }
    return ResolvedReleaseAuthority(
        release_payload=manifest,
        decision_payload=decision,
        authority=dict(snapshot),
        authority_source=authority_source,
        served_mirror=served_mirror,
        current_pointer=dict(current),
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
