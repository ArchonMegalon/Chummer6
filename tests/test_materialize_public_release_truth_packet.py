from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import tempfile
from pathlib import Path
from unittest import mock

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "materialize_public_release_truth_packet.py"
SPEC = importlib.util.spec_from_file_location("materialize_public_release_truth_packet", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_build_packet_uses_release_channel_published_at_and_receipts() -> None:
    packet = MODULE.build_packet(
        release_payload={
            "status": "published",
            "publishedAt": "2026-06-30T08:32:18Z",
            "knownIssueSummary": "Current release checks are clear, and the downloads page has recent install coverage.",
            "fixAvailabilitySummary": "Only send fixed notices after the affected install can receive the published channel artifact now on the shelf.",
            "releaseProof": {
                "status": "passed",
                "journeysPassed": ["install_claim_restore_continue"],
            },
            "desktopTupleCoverage": {
                "promotedInstallerTuples": [
                    {"artifactId": "avalonia-linux-x64-installer", "platform": "linux", "rid": "linux-x64", "arch": "x64"},
                    {"artifactId": "avalonia-win-x64-installer", "platform": "windows", "rid": "win-x64", "arch": "x64"},
                ]
            },
            "artifacts": [
                {"artifactId": "avalonia-linux-x64-installer", "platform": "linux", "arch": "x64", "rid": "linux-x64", "kind": "installer", "compatibilityState": "compatible", "installAccessClass": "open_public"},
                {"artifactId": "avalonia-win-x64-installer", "platform": "windows", "arch": "x64", "rid": "win-x64", "kind": "installer", "compatibilityState": "compatible", "installAccessClass": "open_public"},
            ],
        },
        linux_gate={
            "status": "passed",
            "docker_image": "debian:bookworm-slim",
            "generated_at_utc": "20260701T031940Z",
            "output": {
                "rid": "linux-x64",
                "archive_sha256": "a" * 64,
                "executable_sha256": "b" * 64,
            },
        },
        macos_source_build_contract={
            "status": "passed",
            "generated_at_utc": "2026-06-29T17:22:42Z",
            "scope": "script_contract_only",
            "runtime_coverage": "not_run_on_non_macos_host",
            "real_macos_runtime_proof_required": True,
            "policy": {
                "doc_marks_second_script_install": True,
                "maintenance_policy_marks_real_build_as_macos_only": True,
                "maintenance_policy_requires_two_step_install": True,
            },
        },
        release_source="/tmp/RELEASE_CHANNEL.generated.json",
        authority={"servedMirror": MODULE.CANONICAL_RELEASE_CHANNEL_SOURCE},
    )

    assert packet["published_line"] == "Published: June 30, 2026 at 8:32 UTC."
    assert packet["available_platforms"] == ["Windows", "Linux"]
    assert packet["missing_platforms"] == ["macOS"]
    assert packet["shelf_truth_line"] == "Windows and Linux downloads are posted."
    assert packet["architecture_scope_line"] == "Desktop downloads are available for Linux x64 and Windows x64 only. No public download is posted for Linux ARM64, Windows ARM64, and macOS yet."
    assert packet["missing_installer_lane_line"] == "macOS does not have a normal installer yet."
    assert packet["known_issue_summary"] == "No current download blocker is listed for these installers."
    assert packet["release_verification_summary"] == "This release covers installs and recovery, campaign session recovery, and support follow-up."
    assert packet["linux_source_build_gate"]["archive_sha256"] == "a" * 64
    assert packet["macos_source_build_contract"]["real_macos_runtime_proof_required"] is True
    assert packet["authority"]["servedMirror"] == MODULE.CANONICAL_RELEASE_CHANNEL_SOURCE


def test_release_channel_resolution_does_not_fall_back_to_mutable_siblings() -> None:
    with mock.patch.dict(os.environ, {}, clear=True):
        with pytest.raises(FileNotFoundError, match="explicit release authority"):
            MODULE._resolve_release_channel_path()


def test_release_mode_requires_explicit_immutable_authority_flags(capsys: pytest.CaptureFixture[str]) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "must-not-exist.json"
        original_output_path = MODULE.OUTPUT_PATH
        try:
            MODULE.OUTPUT_PATH = output_path
            with pytest.raises(SystemExit) as exc_info:
                MODULE.main(["--release"])
        finally:
            MODULE.OUTPUT_PATH = original_output_path

        assert exc_info.value.code == 2
        assert not output_path.exists()
    assert "public_release_truth_packet:ok" not in capsys.readouterr().out


def _write_git_authority_fixture(root: Path, *, decision_status: str = "stable_ready") -> tuple[Path, Path, str]:
    repo = root / "registry"
    manifest_path = repo / ".codex-studio" / "published" / "RELEASE_CHANNEL.generated.json"
    decision_path = repo / ".codex-studio" / "published" / "release-evidence" / "RELEASE_DECISION.generated.json"
    decision_path.parent.mkdir(parents=True)
    decision_bytes = (json.dumps({"releaseDecisionStatus": decision_status}, indent=2, sort_keys=True) + "\n").encode("utf-8")
    decision_path.write_bytes(decision_bytes)
    manifest = {
        "schemaVersion": 1,
        "generatedAt": "2026-07-18T12:00:00Z",
        "releaseVersion": "run-20260718-120000",
        "channel": "public_stable",
        "releaseStatus": "published",
        "rolloutState": "public_stable",
        "supportabilityState": "gold_supported",
        "knownIssueSummary": "No current blocker.",
        "releaseDecisionStatus": decision_status,
        "releaseDecisionSha256": hashlib.sha256(decision_bytes).hexdigest(),
        "desktopTupleCoverage": {
            "promotedInstallerTuples": [
                {"artifactId": "linux", "platform": "linux", "head": "avalonia"},
                {"artifactId": "windows", "platform": "windows", "head": "avalonia"},
            ]
        },
        "artifacts": [
            {
                "artifactId": "windows",
                "platform": "windows",
                "head": "avalonia",
                "kind": "installer",
                "compatibilityState": "compatible",
                "installAccessClass": "open_public",
            },
            {
                "artifactId": "linux",
                "platform": "linux",
                "head": "avalonia",
                "kind": "installer",
                "compatibilityState": "compatible",
                "installAccessClass": "account_recommended",
            },
            {
                "artifactId": "fallback-archive",
                "platform": "linux",
                "head": "blazor-desktop",
                "kind": "archive",
                "compatibilityState": "compatible",
                "installAccessClass": "account_required",
            },
        ],
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "authority@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Authority Test"], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "authority fixture"], check=True)
    commit = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    return manifest_path, decision_path, commit


def test_release_authority_records_exact_projection_and_tolerates_unrelated_dirty_files() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        manifest_path, decision_path, commit = _write_git_authority_fixture(root)
        (manifest_path.parents[2] / "unrelated.txt").write_text("dirty but unrelated\n", encoding="utf-8")

        resolved = MODULE.resolve_release_authority(
            manifest_path,
            registry_commit=commit,
            release_decision_path=decision_path,
            expected_release_decision_status="stable_ready",
            release_mode=True,
        )

        authority = resolved.authority
        assert authority["contract"] == "chummer.release-truth-projection/v1"
        assert authority["releaseVersion"] == "run-20260718-120000"
        assert authority["channel"] == "public_stable"
        assert authority["releaseStatus"] == "published"
        assert authority["rolloutState"] == "public_stable"
        assert authority["supportabilityState"] == "gold_supported"
        assert authority["availablePlatforms"] == ["linux", "windows"]
        assert authority["primaryHeadByPlatform"] == {"linux": "avalonia", "windows": "avalonia"}
        assert authority["artifactCount"] == 2
        assert authority["downloadAccessPosture"] == "public"
        assert authority["knownIssueSummary"] == "No current blocker."
        assert authority["registryCommit"] == commit
        assert authority["manifestVersion"] == 1
        assert authority["manifestGeneratedAt"] == "2026-07-18T12:00:00Z"
        assert authority["manifestSha256"] == hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        assert authority["releaseDecisionStatus"] == "stable_ready"
        assert authority["releaseDecisionSha256"] == hashlib.sha256(decision_path.read_bytes()).hexdigest()
        assert authority["authoritySource"]["kind"] == "git_blob"
        assert authority["servedMirror"] == MODULE.CANONICAL_RELEASE_CHANNEL_SOURCE
        assert authority["authoritySource"] != authority["servedMirror"]


def test_release_authority_rejects_manifest_bytes_that_drift_from_commit() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        manifest_path, decision_path, commit = _write_git_authority_fixture(Path(temp_dir))
        manifest_path.write_text(manifest_path.read_text(encoding="utf-8") + " ", encoding="utf-8")

        with pytest.raises(ValueError, match="authority bytes do not match"):
            MODULE.resolve_release_authority(
                manifest_path,
                registry_commit=commit,
                release_decision_path=decision_path,
                expected_release_decision_status="stable_ready",
                release_mode=True,
            )


def test_release_authority_requires_exact_decision_posture() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        manifest_path, decision_path, commit = _write_git_authority_fixture(
            Path(temp_dir),
            decision_status="preview_ready",
        )

        with pytest.raises(ValueError, match="posture mismatch"):
            MODULE.resolve_release_authority(
                manifest_path,
                registry_commit=commit,
                release_decision_path=decision_path,
                expected_release_decision_status="stable_ready",
                release_mode=True,
            )
