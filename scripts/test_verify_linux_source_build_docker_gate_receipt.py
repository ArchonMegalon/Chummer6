#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve().parent / "verify_linux_source_build_docker_gate_receipt.py"
SPEC = importlib.util.spec_from_file_location("verify_linux_source_build_docker_gate_receipt_module", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


EXECUTABLE_SHA = "0" * 64
ARCHIVE_SHA = "1" * 64
OTHER_SHA = "2" * 64


def _valid_receipt() -> dict[str, Any]:
    lock_bytes = MODULE.RELEASE_LOCK_PATH.read_bytes()
    lock = json.loads(lock_bytes)
    lock_sha256 = hashlib.sha256(lock_bytes).hexdigest()
    source_heads = {
        repository["directory"]: repository["commit"]
        for repository in lock["repositories"]
    }
    release_manifest = lock["releaseManifest"]
    sdk_descriptor = lock["dotnet"]["authority"]
    sdk_authority = json.loads((MODULE.REPO_ROOT / sdk_descriptor["path"]).read_bytes())
    sdk_archive = next(row for row in sdk_authority["archives"] if row["rid"] == "linux-x64")
    manifest = [
        "contract=chummer6.linux-source-build/v2",
        "scriptVersion=3.1.0",
        f"sourceLockSha256={lock_sha256}",
        f"sdkVersion={lock['dotnet']['sdkVersion']}",
        "pythonRequirement=>=3.11,<4",
        "pythonRole=authenticated-orchestrator",
        "targetRid=linux-x64",
        f"releaseManifestStatus={release_manifest['status']}",
        f"releaseManifestSha256={release_manifest['sha256']}",
        "releaseEvidenceEligible=false",
        "debugSymbols=none",
        "artifactPathPortability=passed",
        "artifactModeNormalization=passed",
        *(f"repository.{name}={commit}" for name, commit in source_heads.items()),
    ]
    archive_name = "chummer6-linux-x64-source-lock.tar.gz"
    retained_stage_inventory = [
        {
            "role": "installer_payload",
            "file_name": "chummer-avalonia-linux-x64-installer.deb",
            "size_bytes": 0,
            "sha256": hashlib.sha256(b"").hexdigest(),
        },
        {
            "role": "installer_request",
            "file_name": "installer-request.json",
            "size_bytes": 410,
            "sha256": "4" * 64,
        },
    ]
    retained_stage_inventory_sha256 = hashlib.sha256(
        json.dumps(
            retained_stage_inventory,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return {
        "contract_name": "ea.chummer6_linux_source_build_docker_gate.v2",
        "status": "passed",
        "execution_mode": "fresh_container",
        "generated_at_utc": "20260719T120000Z",
        "docker_image": "debian:bookworm-slim",
        "source_mode": "locked",
        "source_lock": "RELEASE.lock.json",
        "source_lock_sha256": lock_sha256,
        "git_ref": None,
        "release_manifest_status": release_manifest["status"],
        "release_manifest_sha256": release_manifest["sha256"],
        "release_evidence_eligible": False,
        "github_org": "ArchonMegalon",
        "repo_base_url": "https://github.com/ArchonMegalon",
        "proof_producers": MODULE._current_proof_producers(),
        "runtime_authority": {
            "status": "passed",
            "source_lock": "RELEASE.lock.json",
            "rid": "linux-x64",
            "sdk_version": lock["dotnet"]["sdkVersion"],
            "authority_path": sdk_descriptor["path"],
            "authority_sha256": sdk_descriptor["sha256"],
            "archive_url": sdk_archive["source"],
            "archive_name": sdk_archive["fileName"],
            "archive_sha256": sdk_archive["sha256"],
            "archive_sha512": sdk_archive["sha512"],
            "archive_size_bytes": sdk_archive["sizeBytes"],
            "dotnet_root_mode": "gate-owned-authenticated-sdk",
            "dotnet_root_x64_bound": True,
            "dotnet_host_path_bound": True,
            "path_precedence": "gate-owned-sdk-first",
            "multilevel_lookup": False,
            "system_runtime_fallback_allowed": False,
            "archive_reused_by_clean_builds": True,
        },
        "gate": {
            "name": "linux_source_build_fresh_container",
            "host_audit_wrapper": "scripts/check-host-chummer6-linux.sh",
            "build_script": "scripts/build-chummer6-linux.sh",
            "install_script": "scripts/install-chummer6-linux-local.sh",
            "container_flow": "audit_then_two_clean_builds_then_direct_startup_then_local_install_then_updater_dispatch_pending_state_clearing_simulation",
            "public_script_requires_sudo": False,
            "public_script_installs_system_packages": False,
            "build_temp_cleanup_default": True,
            "source_build_update_mode_default": "notify",
            "source_build_analytics_default": "off",
            "source_build_is_explicitly_two_step": True,
        },
        "output": {
            "rid": "linux-x64",
            "binary_name": "Chummer.Avalonia",
            "launcher_name": "run-chummer6.sh",
            "archive_name": archive_name,
            "archive_checksum_name": f"{archive_name}.sha256",
            "executable_sha256": EXECUTABLE_SHA,
            "archive_sha256": ARCHIVE_SHA,
            "debug_symbols": "none",
            "artifact_path_portability": "passed",
            "artifact_mode_normalization": "passed",
        },
        "reproducibility": {
            "status": "passed",
            "clean_build_count": 2,
            "python_requirement": ">=3.11,<4",
            "python_role": "authenticated-orchestrator",
            "observed_python_versions": ["3.11.2", "3.11.2"],
            "archive_sha256_first": ARCHIVE_SHA,
            "archive_sha256_repeat": ARCHIVE_SHA,
            "archives_byte_identical": True,
            "archive_payload_path_scan": "passed",
            "archive_member_modes": "passed",
            "independent_host_archive_sha256": ARCHIVE_SHA,
            "independent_host_python_version": "3.12.3",
            "cross_compatible_runtime_archive_identical": True,
            "scope": "cross-compatible-runtime-observed",
            "release_evidence_eligible": False,
        },
        "artifacts": {
            "build_manifest_excerpt": manifest,
            "source_heads": source_heads,
            "build_log_name": "linux-source-build-20260719T120000Z.log",
            "repeat_build_log_name": "linux-source-build-20260719T121500Z.log",
            "archive_checksum_name": f"{archive_name}.sha256",
            "repeat_archive_checksum_name": f"{archive_name}.sha256",
            "startup_smoke_receipt_name": "startup-smoke-20260719T123000Z.receipt.json",
            "installed_startup_smoke_receipt_name": "installed-startup-smoke-20260719T123001Z.receipt.json",
            "updater_special_mode_receipt_name": "updater-special-mode-20260719T123002Z.receipt.json",
            "updater_dispatch_simulation_receipt_name": "updater-dispatch-simulation-20260719T123003Z.receipt.json",
        },
        "runtime": {
            "startup_smoke": {
                "status": "pass",
                "head_id": "avalonia",
                "channel_id": "local",
                "rid": "linux-x64",
                "ready_checkpoint": "fresh_container_gate",
                "artifact_digest": f"sha256:{EXECUTABLE_SHA}",
                "artifact_digest_source": "process_path",
                "recorded_at_utc": "2026-07-19T12:30:00+00:00",
            },
            "installed_startup_smoke": {
                "status": "pass",
                "head_id": "avalonia",
                "channel_id": "local",
                "rid": "linux-x64",
                "ready_checkpoint": "fresh_container_installed_gate",
                "artifact_digest": f"sha256:{EXECUTABLE_SHA}",
                "artifact_digest_source": "process_path",
                "recorded_at_utc": "2026-07-19T12:30:01+00:00",
            },
            "updater_special_mode": {
                "status": "pass",
                "mode": "desktop_update_launch_installer",
                "head_id": "avalonia",
                "channel_id": "stable",
                "rid": "linux-x64",
                "exit_code": 1,
                "expected_exit_code": 1,
                "failure_reason": "installer_launch_failed",
                "last_error": "Installer payload was not found.",
                "last_error_sanitized": True,
                "pending_update_version": "run-20260618-051119",
                "pending_update_channel_id": "stable",
                "recorded_at_utc": "2026-07-19T12:30:02+00:00",
            },
            "updater_dispatch_simulation": {
                "status": "pass",
                "mode": "desktop_update_dispatch_pending_state_clearing_simulation",
                "head_id": "avalonia",
                "channel_id": "stable",
                "rid": "linux-x64",
                "exit_code": 0,
                "expected_exit_code": 0,
                "failure_reason": "",
                "last_error": "",
                "pending_update_version": "",
                "pending_update_channel_id": "",
                "execution_model": "simulated_nonprivileged_pkexec_dpkg",
                "privilege_escalation_performed": False,
                "native_package_manager_execution_proven": False,
                "invocation_contract_proven": True,
                "pkexec_shim_invoked": True,
                "dpkg_shim_invoked": True,
                "pkexec_invocation": {
                    "argv_count": 3,
                    "command_label": "dpkg",
                    "install_flag": "-i",
                    "installer_argument_binding": "sha256_of_utf8_gate_stage_installer_path",
                    "installer_argument_sha256": "3" * 64,
                },
                "dpkg_invocation": {
                    "argv_count": 2,
                    "install_flag": "-i",
                    "installer_argument_binding": "sha256_of_utf8_gate_stage_installer_path",
                    "installer_argument_sha256": "3" * 64,
                },
                "stage_retention_observed": True,
                "staged_payload_cleanup_proven": False,
                "retained_stage_inventory_exact": True,
                "retained_stage_inventory": retained_stage_inventory,
                "retained_stage_inventory_sha256": retained_stage_inventory_sha256,
                "gate_stage_location": "synthetic_gate_stage_outside_normal_ui_temp_root",
                "deferred_cleanup_phase": "outside_dispatch_simulation",
                "deferred_cleanup_policy": "new_release_startup_or_two_day_stale_temp_pruning",
                "deferred_cleanup_execution_proven": False,
                "recorded_at_utc": "2026-07-19T12:30:03+00:00",
            },
        },
    }


def _set(receipt: dict[str, Any], path: tuple[str | int, ...], value: object) -> None:
    target: Any = receipt
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value


class LinuxSourceBuildDockerGateReceiptVerifierTests(unittest.TestCase):
    def _assert_rejected(self, path: tuple[str | int, ...], value: object) -> None:
        receipt = _valid_receipt()
        _set(receipt, path, value)
        with self.assertRaises(ValueError):
            MODULE.verify(receipt)

    def test_main_accepts_exact_v2_production_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            receipt_path = Path(temp_dir) / "LINUX_SOURCE_BUILD_DOCKER_GATE.generated.json"
            receipt_path.write_text(json.dumps(_valid_receipt()) + "\n", encoding="utf-8")
            original = MODULE.RECEIPT_PATH
            try:
                MODULE.RECEIPT_PATH = receipt_path
                self.assertEqual(0, MODULE.main())
            finally:
                MODULE.RECEIPT_PATH = original

    def test_rejects_v1_or_synthetic_receipts(self) -> None:
        for path, value in (
            (("contract_name",), "ea.chummer6_linux_source_build_docker_gate.v1"),
            (("status",), "test_passed"),
            (("execution_mode",), "synthetic_fixture"),
        ):
            with self.subTest(path=path, value=value):
                self._assert_rejected(path, value)

    def test_rejects_mutable_or_stale_source_authority(self) -> None:
        for path, value in (
            (("source_mode",), "moving_ref"),
            (("source_lock",), "OTHER.lock.json"),
            (("source_lock_sha256",), OTHER_SHA),
            (("git_ref",), "main"),
            (("release_manifest_status",), "stable_ready"),
            (("release_manifest_sha256",), OTHER_SHA),
            (("release_evidence_eligible",), True),
            (("artifacts", "source_heads", "chummer6-ui"), OTHER_SHA[:40]),
        ):
            with self.subTest(path=path, value=value):
                self._assert_rejected(path, value)

    def test_rejects_every_proof_producer_digest_mutation(self) -> None:
        for name in MODULE.PROOF_PRODUCER_PATHS:
            with self.subTest(name=name):
                self._assert_rejected(
                    ("proof_producers", name, "sha256"),
                    OTHER_SHA,
                )

    def test_rejects_lock_bound_producer_descriptor_drift(self) -> None:
        original_lock_path = MODULE.RELEASE_LOCK_PATH
        original_lock = json.loads(original_lock_path.read_text(encoding="utf-8"))
        mutations = {
            "source_lock_verifier": lambda payload: payload["sourceLockVerifier"].__setitem__(
                "sha256", OTHER_SHA
            ),
            "build_script": lambda payload: payload["buildScript"].__setitem__(
                "sha256", OTHER_SHA
            ),
            "package_composer": lambda payload: payload["packagePlane"]["composer"].__setitem__(
                "sha256", OTHER_SHA
            ),
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            try:
                for name, mutate in mutations.items():
                    with self.subTest(name=name):
                        payload = copy.deepcopy(original_lock)
                        mutate(payload)
                        lock_path = root / f"{name}.lock.json"
                        lock_path.write_text(
                            json.dumps(payload, indent=2) + "\n",
                            encoding="utf-8",
                        )
                        MODULE.RELEASE_LOCK_PATH = lock_path
                        with self.assertRaises(ValueError):
                            MODULE.verify(_valid_receipt())
            finally:
                MODULE.RELEASE_LOCK_PATH = original_lock_path

    def test_rejects_weaker_reproducibility_claims(self) -> None:
        for path, value in (
            (("reproducibility", "clean_build_count"), 1),
            (("reproducibility", "archive_sha256_first"), OTHER_SHA),
            (("reproducibility", "archive_sha256_repeat"), OTHER_SHA),
            (("reproducibility", "archives_byte_identical"), False),
            (("reproducibility", "archive_payload_path_scan"), "skipped"),
            (("reproducibility", "archive_member_modes"), "skipped"),
            (("reproducibility", "independent_host_archive_sha256"), None),
            (("reproducibility", "independent_host_python_version"), "3.11.2"),
            (("reproducibility", "cross_compatible_runtime_archive_identical"), False),
            (("reproducibility", "scope"), "same-container-runtime-observed"),
            (("reproducibility", "release_evidence_eligible"), True),
        ):
            with self.subTest(path=path, value=value):
                self._assert_rejected(path, value)

    def test_rejects_nonportable_output_or_receipt_strings(self) -> None:
        cases = (
            (("output", "debug_symbols"), "portable"),
            (("output", "artifact_path_portability"), "skipped"),
            (("output", "artifact_mode_normalization"), "skipped"),
            (("runtime", "updater_special_mode", "last_error"), "/tmp/build/installer missing"),
            (("runtime", "updater_special_mode", "last_error"), "/var/tmp/build/installer missing"),
            (("runtime", "updater_special_mode", "last_error"), "/docker/chummer/build failed"),
            (("runtime", "updater_special_mode", "last_error"), "/workspace/chummer/build failed"),
            (("runtime", "updater_special_mode", "last_error"), "/work/base/artifacts/build failed"),
            (("runtime", "updater_special_mode", "last_error"), "/work/repro-base/artifacts/build failed"),
            (("runtime", "updater_special_mode", "last_error"), "/work/other/build failed"),
            (("runtime", "updater_special_mode", "last_error"), "/repo/private/build failed"),
            (("runtime", "updater_special_mode", "last_error"), "/home/alice/chummer/build failed"),
            (("runtime", "updater_special_mode", "last_error"), r"C:\Users\alice\chummer failed"),
            (("runtime", "updater_special_mode", "last_error"), r"\\server\share\chummer failed"),
        )
        for path, value in cases:
            with self.subTest(value=value):
                self._assert_rejected(path, value)

    def test_recursive_portability_rejects_deep_simulated_argv_path(self) -> None:
        receipt = _valid_receipt()
        _set(
            receipt,
            (
                "runtime",
                "updater_dispatch_simulation",
                "pkexec_invocation",
                "installer_argument_binding",
            ),
            "/work/base/artifacts/updater-stage/installer.deb",
        )
        with self.assertRaisesRegex(ValueError, "machine-local path marker"):
            MODULE.verify(receipt)

    def test_rejects_manifest_or_runtime_binding_drift(self) -> None:
        receipt = _valid_receipt()
        receipt["artifacts"]["build_manifest_excerpt"][2] = f"sourceLockSha256={OTHER_SHA}"
        with self.assertRaises(ValueError):
            MODULE.verify(receipt)

        for path, value in (
            (("runtime", "startup_smoke", "artifact_digest"), f"sha256:{OTHER_SHA}"),
            (("runtime", "startup_smoke", "artifact_digest_source"), "environment"),
            (("runtime", "installed_startup_smoke", "ready_checkpoint"), "fresh_container_gate"),
            (("runtime", "updater_special_mode", "rid"), "linux-arm64"),
            (("runtime", "updater_dispatch_simulation", "mode"), "desktop_update_install_success"),
            (("runtime", "updater_dispatch_simulation", "stage_retention_observed"), False),
            (("runtime", "updater_dispatch_simulation", "staged_payload_cleanup_proven"), True),
            (("runtime", "updater_dispatch_simulation", "retained_stage_inventory_exact"), False),
            (("runtime", "updater_dispatch_simulation", "retained_stage_inventory", 0, "size_bytes"), 1),
            (("runtime", "updater_dispatch_simulation", "retained_stage_inventory", 0, "role"), "installed_payload"),
            (("runtime", "updater_dispatch_simulation", "retained_stage_inventory", 0, "file_name"), "package.deb"),
            (("runtime", "updater_dispatch_simulation", "retained_stage_inventory", 1, "sha256"), OTHER_SHA),
            (("runtime", "updater_dispatch_simulation", "retained_stage_inventory_sha256"), OTHER_SHA),
            (("runtime", "updater_dispatch_simulation", "gate_stage_location"), "normal_ui_temp_root"),
            (("runtime", "updater_dispatch_simulation", "deferred_cleanup_phase"), "completed"),
            (("runtime", "updater_dispatch_simulation", "deferred_cleanup_policy"), "immediate"),
            (("runtime", "updater_dispatch_simulation", "deferred_cleanup_execution_proven"), True),
            (("runtime", "updater_dispatch_simulation", "execution_model"), "native_pkexec_dpkg"),
            (("runtime", "updater_dispatch_simulation", "privilege_escalation_performed"), True),
            (("runtime", "updater_dispatch_simulation", "native_package_manager_execution_proven"), True),
            (("runtime", "updater_dispatch_simulation", "invocation_contract_proven"), False),
            (("runtime", "updater_dispatch_simulation", "pkexec_shim_invoked"), False),
            (("runtime", "updater_dispatch_simulation", "dpkg_shim_invoked"), False),
            (("runtime", "updater_dispatch_simulation", "pkexec_invocation", "argv_count"), 2),
            (("runtime", "updater_dispatch_simulation", "pkexec_invocation", "command_label"), "apt"),
            (("runtime", "updater_dispatch_simulation", "pkexec_invocation", "install_flag"), "--install"),
            (("runtime", "updater_dispatch_simulation", "pkexec_invocation", "installer_argument_sha256"), OTHER_SHA),
            (("runtime", "updater_dispatch_simulation", "dpkg_invocation", "argv_count"), 3),
            (("runtime", "updater_dispatch_simulation", "dpkg_invocation", "installer_argument_sha256"), OTHER_SHA),
        ):
            with self.subTest(path=path, value=value):
                self._assert_rejected(path, value)

    def test_rejects_unlocked_or_ambient_runtime_authority(self) -> None:
        for path, value in (
            (("runtime_authority", "archive_sha256"), OTHER_SHA),
            (("runtime_authority", "sdk_version"), "10.0.999"),
            (("runtime_authority", "dotnet_root_x64_bound"), False),
            (("runtime_authority", "dotnet_host_path_bound"), False),
            (("runtime_authority", "path_precedence"), "system-first"),
            (("runtime_authority", "multilevel_lookup"), True),
            (("runtime_authority", "system_runtime_fallback_allowed"), True),
            (("runtime_authority", "archive_reused_by_clean_builds"), False),
        ):
            with self.subTest(path=path, value=value):
                self._assert_rejected(path, value)

    def test_rejects_nonexact_property_sets(self) -> None:
        receipt = _valid_receipt()
        receipt["synthetic"] = True
        with self.assertRaises(ValueError):
            MODULE.verify(receipt)


if __name__ == "__main__":
    unittest.main()
