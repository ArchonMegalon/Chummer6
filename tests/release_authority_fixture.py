from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


JsonObject = dict[str, object]
Mutator = Callable[[JsonObject], None]


@dataclass(frozen=True)
class AuthorityFixture:
    repo_root: Path
    current_path: Path
    snapshot_path: Path
    manifest_path: Path
    decision_path: Path
    registry_commit: str
    snapshot: JsonObject
    manifest: JsonObject
    decision: JsonObject
    current: JsonObject


def _json_bytes(payload: JsonObject) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _run_git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.strip()


def default_artifacts() -> list[JsonObject]:
    return [
        {
            "artifactId": "avalonia-linux-x64-installer",
            "arch": "x64",
            "compatibilityState": "compatible",
            "downloadUrl": "https://chummer.run/downloads/g/generation-1/files/chummer-avalonia-linux-x64-installer.deb",
            "fileName": "chummer-avalonia-linux-x64-installer.deb",
            "head": "avalonia",
            "installAccessClass": "open_public",
            "kind": "installer",
            "platform": "linux",
            "platformLabel": "Avalonia Desktop Linux X64 Installer",
            "rid": "linux-x64",
            "sha256": "5c8518f0f7f24b3f7101ff6fcea0fe33f012b4dfb03704f5bdf0067571f2d70b",
            "sizeBytes": 37024862,
            "status": "available",
        },
        {
            "artifactId": "avalonia-win-x64-installer",
            "arch": "x64",
            "compatibilityState": "compatible",
            "downloadUrl": "https://chummer.run/downloads/g/generation-1/files/chummer-avalonia-win-x64-installer.exe",
            "fileName": "chummer-avalonia-win-x64-installer.exe",
            "head": "avalonia",
            "installAccessClass": "open_public",
            "kind": "installer",
            "platform": "windows",
            "platformLabel": "Avalonia Desktop Windows X64 Installer",
            "rid": "win-x64",
            "sha256": "80655fd79a096cd7714910d7b38f7741eea01f82ada96dc6a2a097951997d91a",
            "sizeBytes": 2734106,
            "status": "available",
        },
    ]


def write_authority_fixture(
    root: Path,
    *,
    decision_status: str = "preview_ready",
    artifacts: list[JsonObject] | None = None,
    primary_heads: dict[str, str] | None = None,
    fallback_heads: dict[str, list[str]] | None = None,
    remote: str = "https://github.com/ArchonMegalon/chummer6-hub-registry.git",
    manifest_mutator: Mutator | None = None,
    decision_mutator: Mutator | None = None,
    snapshot_mutator: Mutator | None = None,
    current_mutator: Mutator | None = None,
    path_release_version: str | None = None,
    path_digest: str | None = None,
) -> AuthorityFixture:
    repo = root / "registry"
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    _run_git(repo, "config", "user.email", "authority@example.invalid")
    _run_git(repo, "config", "user.name", "Authority Test")
    _run_git(repo, "remote", "add", "origin", remote)
    (repo / "SEED.md").write_text("Registry identity fixture.\n", encoding="utf-8")
    _run_git(repo, "add", "SEED.md")
    _run_git(repo, "commit", "-qm", "seed registry fixture")
    registry_commit = _run_git(repo, "rev-parse", "HEAD")

    selected_artifacts = [dict(item) for item in (default_artifacts() if artifacts is None else artifacts)]
    selected_artifacts.sort(key=lambda item: str(item["artifactId"]))
    platforms = sorted({str(item["platform"]) for item in selected_artifacts})
    if primary_heads is None:
        primary_heads = {
            platform: str(next(item["head"] for item in selected_artifacts if item["platform"] == platform))
            for platform in platforms
        }
    primary_heads = dict(sorted(primary_heads.items()))
    fallback_heads = {
        platform: sorted(heads)
        for platform, heads in sorted((fallback_heads or {}).items())
    }

    release_version = "run-20260718-120000"
    stable = decision_status == "stable_ready"
    channel = "public_stable" if stable else "preview"
    rollout_state = "public_stable" if stable else "public_preview"
    supportability_state = "gold_supported" if stable else "preview_supported"
    release_status = "published" if selected_artifacts else "unpublished"
    access_classes = sorted({str(item["installAccessClass"]) for item in selected_artifacts})
    access_posture = (
        "unavailable"
        if not access_classes
        else access_classes[0]
        if len(access_classes) == 1
        else "mixed"
    )
    known_issue_summary = "No current blocker."
    support_owner = "Chummer release engineering"

    promoted = [
        {
            "artifactId": item["artifactId"],
            "arch": item["arch"],
            "head": item["head"],
            "platform": item["platform"],
            "rid": item["rid"],
        }
        for item in selected_artifacts
    ]
    routes = [
        {
            "artifactId": item["artifactId"],
            "head": item["head"],
            "platform": item["platform"],
            "promotionState": "promoted",
            "publicationScope": "signed-in-and-public",
            "publicInstallRoute": f"/downloads/files/{item['fileName']}",
            "revokeState": "not_revoked",
            "routeRole": (
                "primary"
                if primary_heads.get(str(item["platform"])) == item["head"]
                else "fallback"
            ),
        }
        for item in selected_artifacts
    ]
    manifest: JsonObject = {
        "artifacts": selected_artifacts,
        "channel": channel,
        "desktopTupleCoverage": {
            "complete": bool(selected_artifacts),
            "desktopRouteTruth": routes,
            "externalProofRequests": [],
            "missingRequiredHeads": [],
            "missingRequiredPlatformHeadPairs": [],
            "missingRequiredPlatformHeadRidTuples": [],
            "missingRequiredPlatforms": [],
            "promotedInstallerTuples": promoted,
            "requiredDesktopHeads": sorted(set(primary_heads.values())),
            "requiredDesktopPlatforms": platforms,
        },
        "generatedAt": "2026-07-18T12:00:00Z",
        "knownIssueSummary": known_issue_summary,
        "publicTrustMetrics": {
            "revocationFacts": {
                "activeRevocationCount": 0,
                "activeRevocations": [],
                "channelRevoked": False,
            }
        },
        "releaseStatus": release_status,
        "releaseVersion": release_version,
        "rolloutState": rollout_state,
        "schemaVersion": 2,
        "supportOwner": support_owner,
        "supportabilityState": supportability_state,
    }
    if manifest_mutator is not None:
        manifest_mutator(manifest)
    manifest_bytes = _json_bytes(manifest)
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()

    if stable:
        decision: JsonObject = {
            "contract_name": "chummer.final_gold_graph",
            "contract_version": 2,
            "live_release": {
                "artifact_count": len(selected_artifacts),
                "available_platforms": platforms,
                "channel": channel,
                "download_access_posture": access_posture,
                "known_issue_summary": known_issue_summary,
                "manifest_sha256": manifest_sha256,
                "primary_head_by_platform": primary_heads,
                "registry_commit": registry_commit,
                "release_decision_sha256": "",
                "release_decision_status": decision_status,
                "rollout_state": rollout_state,
                "status": release_status,
                "supportability_state": supportability_state,
                "version": release_version,
            },
            "release_authority": {
                "contract": "chummer.release-authority-snapshot/v2",
                "manifest_sha256": manifest_sha256,
                "registry_commit": registry_commit,
                "release_decision_sha256": "",
                "release_decision_status": decision_status,
                "snapshot_path": "",
                "snapshot_sha256": "",
            },
            "releaseDecisionStatus": decision_status,
            "releaseVersion": release_version,
            "status": "pass",
        }
    else:
        decision = {
            "artifactAccessClass": (
                "review_required"
                if decision_status == "review_required" and not selected_artifacts
                else access_posture
            ),
            "channel": channel,
            "contractName": "chummer.preview-release-decision/v1",
            "fallbackHeadsByPlatform": fallback_heads,
            "manifestSha256": manifest_sha256,
            "platforms": platforms,
            "primaryHeadByPlatform": primary_heads,
            "registryCommit": registry_commit,
            "releaseDecisionStatus": decision_status,
            "releaseVersion": release_version,
            "status": decision_status,
            "supportOwner": support_owner,
            "authoritySnapshotSha256": "" if decision_status == "review_required" else "a" * 64,
            "candidateDecisionStatus": "" if decision_status == "review_required" else "review_required",
            "candidateDecisionSha256": "" if decision_status == "review_required" else "b" * 64,
        }
    if decision_mutator is not None:
        decision_mutator(decision)
    decision_bytes = _json_bytes(decision)
    decision_sha256 = hashlib.sha256(decision_bytes).hexdigest()

    snapshot_artifacts = [
        {
            "arch": item["arch"],
            "artifactId": item["artifactId"],
            "compatibilityState": item["compatibilityState"],
            "downloadUrl": item["downloadUrl"],
            "head": item["head"],
            "installAccessClass": item["installAccessClass"],
            "kind": item["kind"],
            "platform": item["platform"],
            "promotionState": "promoted",
            "publicationScope": "signed-in-and-public",
            "publicInstallRoute": f"/downloads/files/{item['fileName']}",
            "revokeState": "not_revoked",
            "rid": item["rid"],
            "sha256": item["sha256"],
            "sizeBytes": item["sizeBytes"],
        }
        for item in selected_artifacts
    ]
    snapshot: JsonObject = {
        "artifactCount": len(snapshot_artifacts),
        "artifacts": snapshot_artifacts,
        "authorityContract": "chummer.release-authority-snapshot/v2",
        "availablePlatforms": platforms,
        "channel": channel,
        "downloadAccessPosture": access_posture,
        "knownIssueSummary": known_issue_summary,
        "manifestPath": "RELEASE_CHANNEL.json",
        "manifestSha256": manifest_sha256,
        "nextActions": [] if stable else ["Complete the current release review."],
        "primaryHeadByPlatform": primary_heads,
        "registryCommit": registry_commit,
        "registryRepository": "ArchonMegalon/chummer6-hub-registry",
        "releaseDecisionPath": "RELEASE_DECISION.json",
        "releaseDecisionSha256": decision_sha256,
        "releaseDecisionStatus": decision_status,
        "releaseVersion": release_version,
        "rolloutState": rollout_state,
        "status": release_status,
        "supportOwner": support_owner,
        "supportabilityState": supportability_state,
    }
    if snapshot_mutator is not None:
        snapshot_mutator(snapshot)
    snapshot_bytes = _json_bytes(snapshot)
    snapshot_sha256 = hashlib.sha256(snapshot_bytes).hexdigest()
    snapshot_dir = (
        repo
        / "snapshots"
        / (path_release_version or str(snapshot["releaseVersion"]))
        / (path_digest or snapshot_sha256)
    )
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = snapshot_dir / "SNAPSHOT.json"
    manifest_path = snapshot_dir / "RELEASE_CHANNEL.json"
    decision_path = snapshot_dir / "RELEASE_DECISION.json"
    snapshot_path.write_bytes(snapshot_bytes)
    manifest_path.write_bytes(manifest_bytes)
    decision_path.write_bytes(decision_bytes)
    current: JsonObject = {
        "releaseVersion": str(snapshot["releaseVersion"]),
        "snapshotSha256": snapshot_sha256,
        "decisionSha256": decision_sha256,
        "status": str(snapshot["releaseDecisionStatus"]),
    }
    if current_mutator is not None:
        current_mutator(current)
    current_path = repo / "CURRENT.json"
    current_path.write_bytes(_json_bytes(current))
    return AuthorityFixture(
        repo_root=repo,
        current_path=current_path,
        snapshot_path=snapshot_path,
        manifest_path=manifest_path,
        decision_path=decision_path,
        registry_commit=registry_commit,
        snapshot=snapshot,
        manifest=manifest,
        decision=decision,
        current=current,
    )
