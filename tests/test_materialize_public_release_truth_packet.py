from __future__ import annotations

import importlib.util
from pathlib import Path


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


def test_public_source_label_keeps_workspace_paths_public_safe() -> None:
    source = MODULE.REPO_ROOT.parent / "chummer-hub-registry" / ".codex-studio" / "published" / "RELEASE_CHANNEL.generated.json"

    assert MODULE._public_source_label(source) == MODULE.CANONICAL_RELEASE_CHANNEL_SOURCE
    assert MODULE._public_source_label(Path("/tmp/RELEASE_CHANNEL.generated.json")) == MODULE.CANONICAL_RELEASE_CHANNEL_SOURCE
