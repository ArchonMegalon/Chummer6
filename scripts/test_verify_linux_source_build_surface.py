from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "SOURCE_BUILD_LINUX.md"
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build-chummer6-linux.sh"
INSTALL_SCRIPT = REPO_ROOT / "scripts" / "install-chummer6-linux-local.sh"
AUDIT_SCRIPT = REPO_ROOT / "scripts" / "check-host-chummer6-linux.sh"
PREREQ_SCRIPT = REPO_ROOT / "scripts" / "list-chummer6-linux-prereqs.sh"
DOCKER_GATE_SCRIPT = REPO_ROOT / "scripts" / "verify_linux_source_build_docker_gate.sh"
GATE_IDENTITY_SCRIPT = REPO_ROOT / "scripts" / "validate_linux_source_build_gate_identity.sh"
SOURCE_LOCK_VERIFIER = REPO_ROOT / "scripts" / "verify_linux_source_lock.py"
PACKAGE_COMPOSER = REPO_ROOT / "scripts" / "materialize_linux_package_plane.py"


def _manifest() -> bytes:
    rows = [
        "contract=chummer6.linux-source-build/v2",
        "scriptVersion=3.1.0",
        f"sourceLockSha256={'a' * 64}",
        "sdkVersion=10.0.103",
        "pythonRequirement=>=3.11,<4",
        "pythonRole=authenticated-orchestrator",
        "targetRid=linux-x64",
        "releaseManifestStatus=review_required",
        f"releaseManifestSha256={'b' * 64}",
        "releaseEvidenceEligible=false",
        "debugSymbols=none",
        "artifactPathPortability=passed",
        "artifactModeNormalization=passed",
        f"repository.chummer-core-engine={'1' * 40}",
        f"repository.chummer.run-services={'2' * 40}",
        f"repository.chummer-hub-registry={'3' * 40}",
        f"repository.chummer-ui-kit={'4' * 40}",
        f"repository.chummer6-ui={'5' * 40}",
    ]
    return ("\n".join(rows) + "\n").encode()


def _write_normalized_archive(
    publish_dir: Path,
    manifest: bytes,
    binary: bytes,
    *,
    manifest_mode: int = 0o644,
) -> str:
    stage = publish_dir.parent / f"{publish_dir.name}-stage"
    stage.mkdir(parents=True, exist_ok=True)
    stage.chmod(0o755)
    (stage / "BUILD-MANIFEST.txt").write_bytes(manifest)
    (stage / "BUILD-MANIFEST.txt").chmod(manifest_mode)
    (stage / "Chummer.Avalonia").write_bytes(binary)
    (stage / "Chummer.Avalonia").chmod(0o755)
    publish_dir.mkdir(parents=True, exist_ok=True)
    (publish_dir / "BUILD-MANIFEST.txt").write_bytes(manifest)
    (publish_dir / "Chummer.Avalonia").write_bytes(binary)
    (publish_dir / "Chummer.Avalonia").chmod(0o755)
    archive = publish_dir / "chummer6-linux-x64-source-lock.tar.gz"
    tar_process = subprocess.Popen(
        [
            "tar",
            "--sort=name",
            "--mtime=@1700000000",
            "--owner=0",
            "--group=0",
            "--numeric-owner",
            "-cf",
            "-",
            ".",
        ],
        cwd=stage,
        stdout=subprocess.PIPE,
    )
    assert tar_process.stdout is not None
    with archive.open("wb") as output:
        gzip_process = subprocess.run(
            ["gzip", "-n"],
            stdin=tar_process.stdout,
            stdout=output,
            check=False,
        )
    tar_process.stdout.close()
    self_status = tar_process.wait()
    if self_status or gzip_process.returncode:
        raise RuntimeError("could not create normalized synthetic source archive")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (publish_dir / f"{archive.name}.sha256").write_text(
        f"{digest}  {archive.name}\n",
        encoding="utf-8",
    )
    return digest


def _write_gate_fixture(root: Path) -> str:
    manifest = _manifest()
    binary = b"synthetic portable Chummer.Avalonia\n"
    digests: list[str] = []
    for base_name in ("base", "repro-base"):
        base = root / base_name
        publish = base / "artifacts" / "chummer6-linux-x64"
        digests.append(_write_normalized_archive(publish, manifest, binary))
        logs = base / "logs"
        logs.mkdir(parents=True)
        (logs / "linux-source-build-20260719T000000Z-1.log").write_text(
            "[00:00:00] Python runtime: 3.12.10 (requirement >=3.11,<4)\n",
            encoding="utf-8",
        )
    if len(set(digests)) != 1:
        raise RuntimeError("synthetic clean archives unexpectedly differ")
    artifacts = root / "base" / "artifacts"
    digest = hashlib.sha256(binary).hexdigest()
    installer_argument_sha256 = "3" * 64
    retained_stage_inventory = [
        {
            "role": "installer_payload",
            "fileName": "chummer-avalonia-linux-x64-installer.deb",
            "sizeBytes": 0,
            "sha256": hashlib.sha256(b"").hexdigest(),
        },
        {
            "role": "installer_request",
            "fileName": "installer-request.json",
            "sizeBytes": 410,
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
    receipts = {
        "startup-smoke-000.receipt.json": {
            "status": "pass",
            "headId": "avalonia",
            "channelId": "local",
            "rid": "linux-x64",
            "readyCheckpoint": "fresh_container_gate",
            "artifactDigest": f"sha256:{digest}",
            "artifactDigestSource": "process_path",
            "recordedAtUtc": "2026-07-19T00:00:00Z",
        },
        "installed-startup-smoke-000.receipt.json": {
            "status": "pass",
            "headId": "avalonia",
            "channelId": "local",
            "rid": "linux-x64",
            "readyCheckpoint": "fresh_container_installed_gate",
            "artifactDigest": f"sha256:{digest}",
            "artifactDigestSource": "process_path",
            "recordedAtUtc": "2026-07-19T00:00:01Z",
        },
        "updater-special-mode-000.receipt.json": {
            "status": "pass",
            "mode": "desktop_update_launch_installer",
            "headId": "avalonia",
            "channelId": "stable",
            "rid": "linux-x64",
            "exitCode": 1,
            "expectedExitCode": 1,
            "failureReason": "installer_launch_failed",
            "lastError": "Installer payload was not found.",
            "lastErrorSanitized": True,
            "pendingUpdateVersion": "run-test",
            "pendingUpdateChannelId": "stable",
            "recordedAtUtc": "2026-07-19T00:00:02Z",
        },
        "updater-dispatch-simulation-000.receipt.json": {
            "status": "pass",
            "mode": "desktop_update_dispatch_pending_state_clearing_simulation",
            "headId": "avalonia",
            "channelId": "stable",
            "rid": "linux-x64",
            "exitCode": 0,
            "expectedExitCode": 0,
            "failureReason": "",
            "lastError": "",
            "pendingUpdateVersion": "",
            "pendingUpdateChannelId": "",
            "executionModel": "simulated_nonprivileged_pkexec_dpkg",
            "privilegeEscalationPerformed": False,
            "nativePackageManagerExecutionProven": False,
            "invocationContractProven": True,
            "pkexecShimInvoked": True,
            "dpkgShimInvoked": True,
            "pkexecInvocation": {
                "argvCount": 3,
                "commandLabel": "dpkg",
                "installFlag": "-i",
                "installerArgumentBinding": "sha256_of_utf8_gate_stage_installer_path",
                "installerArgumentSha256": installer_argument_sha256,
            },
            "dpkgInvocation": {
                "argvCount": 2,
                "installFlag": "-i",
                "installerArgumentBinding": "sha256_of_utf8_gate_stage_installer_path",
                "installerArgumentSha256": installer_argument_sha256,
            },
            "stageRetentionObserved": True,
            "stagedPayloadCleanupProven": False,
            "retainedStageInventoryExact": True,
            "retainedStageInventory": retained_stage_inventory,
            "retainedStageInventorySha256": retained_stage_inventory_sha256,
            "gateStageLocation": "synthetic_gate_stage_outside_normal_ui_temp_root",
            "deferredCleanupPhase": "outside_dispatch_simulation",
            "deferredCleanupPolicy": "new_release_startup_or_two_day_stale_temp_pruning",
            "deferredCleanupExecutionProven": False,
            "recordedAtUtc": "2026-07-19T00:00:03Z",
        },
    }
    for name, payload in receipts.items():
        (artifacts / name).write_text(
            json.dumps(payload, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    launcher = root / "base" / "installed" / "chummer6-source-build" / "run-chummer6.sh"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    launcher.chmod(0o755)
    return digests[0]


class VerifyLinuxSourceBuildSurfaceTests(unittest.TestCase):
    def test_public_doc_references_checked_in_helper_scripts(self) -> None:
        doc_text = DOC.read_text(encoding="utf-8")
        self.assertIn("bash scripts/list-chummer6-linux-prereqs.sh", doc_text)
        self.assertIn("bash scripts/check-host-chummer6-linux.sh", doc_text)
        self.assertIn("bash scripts/build-chummer6-linux.sh --base", doc_text)
        self.assertIn("bash scripts/install-chummer6-linux-local.sh --base", doc_text)
        self.assertIn("CHUMMER_LINUX_SOURCE_BUILD_GATE_EXPECTED_ARCHIVE_SHA256", doc_text)
        self.assertIn("CHUMMER_LINUX_SOURCE_BUILD_GATE_EXPECTED_ARCHIVE_PYTHON_VERSION", doc_text)
        self.assertIn("linux-docker-gate-diagnostic.json", doc_text)
        self.assertIn("updater dispatch/pending-state-clearing", doc_text)
        self.assertIn("stage_retention_observed=true", doc_text)
        self.assertIn("staged_payload_cleanup_proven=false", doc_text)

    def test_helper_scripts_exist_and_are_executable(self) -> None:
        for path in (
            BUILD_SCRIPT,
            INSTALL_SCRIPT,
            AUDIT_SCRIPT,
            PREREQ_SCRIPT,
            DOCKER_GATE_SCRIPT,
            GATE_IDENTITY_SCRIPT,
        ):
            self.assertTrue(path.exists(), f"Missing helper script: {path}")
            self.assertTrue(os.access(path, os.X_OK), f"Helper script is not executable: {path}")

    def test_v2_docker_gate_rejects_stale_v1_selectors_and_parser(self) -> None:
        text = DOCKER_GATE_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("chummer6-linux-*-source-lock.tar.gz", text)
        self.assertIn("linux-source-build-*.log", text)
        self.assertIn('line.split("=", 1)', text)
        self.assertIn('"$PUBLISH_DIR/Chummer.Avalonia" --startup-smoke', text)
        self.assertIn('manifest_fields["pythonRequirement"]', text)
        self.assertIn('manifest_fields["artifactPathPortability"]', text)
        self.assertIn('(cd / && git lfs install --skip-repo', text)
        self.assertIn('repository_uid="$(stat -c %u /repo)"', text)
        self.assertIn('((repository_uid > 0))', text)
        self.assertIn('mapfile -t repository_group_rows', text)
        self.assertIn('mapfile -t repository_passwd_rows', text)
        self.assertIn('(${#repository_group_rows[@]} == 1)', text)
        self.assertIn('(${#repository_passwd_rows[@]} == 1)', text)
        self.assertIn('checkout GID does not resolve to exactly one group record', text)
        self.assertIn('checkout UID does not resolve to exactly one passwd record', text)
        self.assertIn('validate_linux_source_build_gate_identity.sh', text)
        self.assertIn('CHUMMER_GATE_SDK_ARCHIVE_URL', text)
        self.assertIn('CHUMMER_SDK_ARCHIVE="$GATE_SDK_ARCHIVE"', text)
        self.assertIn('DOTNET_ROOT="$GATE_SDK_ROOT"', text)
        self.assertIn('DOTNET_ROOT_X64="$GATE_SDK_ROOT"', text)
        self.assertIn('DOTNET_HOST_PATH="$GATE_SDK_ROOT/dotnet"', text)
        self.assertIn('DOTNET_MULTILEVEL_LOOKUP=0', text)
        self.assertIn('system_runtime_fallback_allowed', text)
        self.assertIn('source archive member has non-canonical mode', text)
        self.assertIn('[[ "\\$1" == "dpkg" ]]', text)
        self.assertIn('[[ "\\$2" == "-i" ]]', text)
        self.assertIn('[[ "\\$#" -eq 2 ]]', text)
        self.assertIn('[[ "\\$#" -eq 3 ]]', text)
        self.assertIn('simulated_nonprivileged_pkexec_dpkg', text)
        self.assertIn('nativePackageManagerExecutionProven', text)
        self.assertIn('sha256_of_utf8_gate_stage_installer_path', text)
        self.assertIn('stageRetentionObserved', text)
        self.assertIn('stagedPayloadCleanupProven', text)
        self.assertIn('retainedStageInventoryExact', text)
        self.assertIn('retainedStageInventorySha256', text)
        self.assertIn('synthetic_gate_stage_outside_normal_ui_temp_root', text)
        self.assertIn('exec "\\$@"', text)
        self.assertNotIn('"\\$*"', text)
        self.assertNotIn('stageDeleted', text)
        self.assertIn('tracked Docker-gate receipt requires independent host archive SHA256', text)
        self.assertIn("'chummer-gate:x:%s:%s:Chummer source gate:/work/home:/bin/bash", text)
        self.assertIn('--reuid="$repository_uid"', text)
        self.assertIn('--regid="$repository_gid"', text)
        self.assertIn('--clear-groups', text)
        self.assertIn('--bounding-set=-all', text)
        self.assertIn('--no-new-privs', text)
        self.assertIn(
            'env HOME=/work/home USER="$repository_user" LOGNAME="$repository_user" bash -lc "$1"',
            text,
        )
        self.assertIn(
            'bash -lc "$ROOT_SETUP_COMMAND" chummer-linux-source-gate "$INNER_COMMAND"',
            text,
        )
        self.assertIn('rev-parse --path-format=absolute --git-common-dir', text)
        self.assertIn('docker_args+=(-v "$git_common_dir:$git_common_dir:ro")', text)
        self.assertNotIn('safe.directory /repo', text)
        self.assertNotIn("linux-desktop-build-", text)
        self.assertNotIn('line.split(": ", 1)', text)
        self.assertNotIn('"$PUBLISH_DIR/run-chummer6.sh" --startup-smoke', text)

    def test_bare_gate_cannot_replace_the_tracked_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env = os.environ.copy()
            env.pop("CHUMMER_LINUX_SOURCE_BUILD_GATE_RECEIPT_PATH", None)
            env.pop("CHUMMER_LINUX_SOURCE_BUILD_GATE_EXPECTED_ARCHIVE_SHA256", None)
            env.pop("CHUMMER_LINUX_SOURCE_BUILD_GATE_EXPECTED_ARCHIVE_PYTHON_VERSION", None)
            env["CHUMMER_LINUX_SOURCE_BUILD_GATE_WORK_ROOT"] = temp_dir
            env["CHUMMER_KEEP_DOCKER_GATE_WORKDIR"] = "1"
            completed = subprocess.run(
                ["bash", str(DOCKER_GATE_SCRIPT)],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            self.assertNotEqual(0, completed.returncode, completed.stdout)
            self.assertIn("tracked Docker-gate receipt requires independent host archive", completed.stdout)
            self.assertNotIn("Docker image:", completed.stdout)

    def test_gate_identity_validator_rejects_conflicting_container_records(self) -> None:
        valid_group = "chummer-gate:x:1001:"
        valid_passwd = "chummer-gate:x:1001:1001:Chummer source gate:/work/home:/bin/bash"

        def command(group_rows: list[str], passwd_rows: list[str]) -> list[str]:
            result = [
                "bash",
                str(GATE_IDENTITY_SCRIPT),
                "--uid",
                "1001",
                "--gid",
                "1001",
            ]
            for row in group_rows:
                result.extend(("--group-record", row))
            for row in passwd_rows:
                result.extend(("--passwd-record", row))
            return result

        valid = command([valid_group], [valid_passwd])
        accepted = subprocess.run(valid, text=True, capture_output=True, check=False)
        self.assertEqual(0, accepted.returncode, accepted.stderr)
        self.assertEqual("chummer-gate", accepted.stdout.strip())

        conflicts = (
            (
                [valid_group, "shadow:x:1001:"],
                [valid_passwd],
                "exactly one group record",
            ),
            (
                [valid_group],
                ["runner:x:1001:1001:Runner:/home/runner:/bin/bash"],
                "home must be exactly /work/home",
            ),
            (
                [valid_group],
                ["runner:x:1001:1002:Runner:/work/home:/bin/bash"],
                "primary group differs",
            ),
            (
                [valid_group],
                ["runner:x:1001:1001:Runner:/work/home:/bin/sh"],
                "shell must be exactly /bin/bash",
            ),
        )
        for group_rows, passwd_rows, expected_error in conflicts:
            with self.subTest(expected_error=expected_error):
                rejected = subprocess.run(
                    command(group_rows, passwd_rows),
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertNotEqual(0, rejected.returncode, rejected.stdout)
                self.assertIn(expected_error, rejected.stderr)

    def test_v2_docker_gate_receipt_binds_two_clean_archives_and_canonical_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            expected_digest = _write_gate_fixture(root)
            receipt = root / "receipt.json"
            env = os.environ.copy()
            env.update(
                {
                    "CHUMMER_LINUX_SOURCE_BUILD_GATE_TEST_MODE": "receipt",
                    "CHUMMER_LINUX_SOURCE_BUILD_GATE_WORK_ROOT": str(root),
                    "CHUMMER_KEEP_DOCKER_GATE_WORKDIR": "1",
                    "CHUMMER_LINUX_SOURCE_BUILD_GATE_RECEIPT_PATH": str(receipt),
                    "CHUMMER_LINUX_SOURCE_BUILD_GATE_EXPECTED_ARCHIVE_SHA256": expected_digest,
                    "CHUMMER_LINUX_SOURCE_BUILD_GATE_EXPECTED_ARCHIVE_PYTHON_VERSION": "3.11.9",
                }
            )
            completed = subprocess.run(
                ["bash", str(DOCKER_GATE_SCRIPT)],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stdout)
            payload = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual("ea.chummer6_linux_source_build_docker_gate.v2", payload["contract_name"])
            self.assertEqual("test_passed", payload["status"])
            self.assertEqual("synthetic_fixture", payload["execution_mode"])
            self.assertNotEqual("passed", payload["status"])
            self.assertFalse(payload["release_evidence_eligible"])
            self.assertEqual("none", payload["output"]["debug_symbols"])
            self.assertEqual("passed", payload["output"]["artifact_path_portability"])
            self.assertEqual("passed", payload["output"]["artifact_mode_normalization"])
            self.assertEqual("passed", payload["reproducibility"]["archive_member_modes"])
            self.assertFalse(payload["runtime_authority"]["system_runtime_fallback_allowed"])
            self.assertTrue(payload["runtime_authority"]["archive_reused_by_clean_builds"])
            expected_producers = {
                "docker_gate_script": DOCKER_GATE_SCRIPT,
                "host_audit_wrapper": AUDIT_SCRIPT,
                "build_script": BUILD_SCRIPT,
                "package_composer": PACKAGE_COMPOSER,
                "install_script": INSTALL_SCRIPT,
                "identity_validator": GATE_IDENTITY_SCRIPT,
                "source_lock_verifier": SOURCE_LOCK_VERIFIER,
            }
            self.assertEqual(set(expected_producers), set(payload["proof_producers"]))
            for name, path in expected_producers.items():
                with self.subTest(producer=name):
                    self.assertEqual(
                        hashlib.sha256(path.read_bytes()).hexdigest(),
                        payload["proof_producers"][name]["sha256"],
                    )
            proof = payload["reproducibility"]
            self.assertEqual(2, proof["clean_build_count"])
            self.assertTrue(proof["archives_byte_identical"])
            self.assertTrue(proof["cross_compatible_runtime_archive_identical"])
            self.assertEqual(expected_digest, proof["independent_host_archive_sha256"])
            self.assertEqual("3.11.9", proof["independent_host_python_version"])
            self.assertEqual(["3.12.10", "3.12.10"], proof["observed_python_versions"])
            updater_simulation = payload["runtime"]["updater_dispatch_simulation"]
            self.assertEqual(
                "simulated_nonprivileged_pkexec_dpkg",
                updater_simulation["execution_model"],
            )
            self.assertFalse(updater_simulation["privilege_escalation_performed"])
            self.assertFalse(updater_simulation["native_package_manager_execution_proven"])
            self.assertTrue(updater_simulation["invocation_contract_proven"])
            self.assertTrue(updater_simulation["pkexec_shim_invoked"])
            self.assertTrue(updater_simulation["dpkg_shim_invoked"])
            self.assertTrue(updater_simulation["stage_retention_observed"])
            self.assertFalse(updater_simulation["staged_payload_cleanup_proven"])
            self.assertTrue(updater_simulation["retained_stage_inventory_exact"])
            self.assertFalse(updater_simulation["deferred_cleanup_execution_proven"])
            self.assertEqual(
                hashlib.sha256(
                    json.dumps(
                        updater_simulation["retained_stage_inventory"],
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode("utf-8")
                ).hexdigest(),
                updater_simulation["retained_stage_inventory_sha256"],
            )

            startup_path = root / "base" / "artifacts" / "startup-smoke-000.receipt.json"
            startup = json.loads(startup_path.read_text(encoding="utf-8"))
            startup["status"] = "fail"
            startup_path.write_text(json.dumps(startup) + "\n", encoding="utf-8")
            failed_runtime = subprocess.run(
                ["bash", str(DOCKER_GATE_SCRIPT)],
                cwd=REPO_ROOT,
                env={
                    **env,
                    "CHUMMER_LINUX_SOURCE_BUILD_GATE_RECEIPT_PATH": str(root / "runtime-fail.json"),
                },
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            self.assertNotEqual(0, failed_runtime.returncode, failed_runtime.stdout)
            self.assertIn("startup smoke runtime receipt differs", failed_runtime.stdout)
            self.assertFalse((root / "runtime-fail.json").exists())
            startup["status"] = "pass"
            startup_path.write_text(json.dumps(startup) + "\n", encoding="utf-8")

            success_path = root / "base" / "artifacts" / "updater-dispatch-simulation-000.receipt.json"
            success = json.loads(success_path.read_text(encoding="utf-8"))
            success["stageRetentionObserved"] = False
            success_path.write_text(json.dumps(success) + "\n", encoding="utf-8")
            failed_retention = subprocess.run(
                ["bash", str(DOCKER_GATE_SCRIPT)],
                cwd=REPO_ROOT,
                env={
                    **env,
                    "CHUMMER_LINUX_SOURCE_BUILD_GATE_RECEIPT_PATH": str(root / "retention-fail.json"),
                },
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            self.assertNotEqual(0, failed_retention.returncode, failed_retention.stdout)
            self.assertIn("updater dispatch/pending-state-clearing simulation receipt differs", failed_retention.stdout)
            self.assertFalse((root / "retention-fail.json").exists())
            success["stageRetentionObserved"] = True
            success_path.write_text(json.dumps(success) + "\n", encoding="utf-8")

            success["pkexecInvocation"]["argvCount"] = 2
            success_path.write_text(json.dumps(success) + "\n", encoding="utf-8")
            failed_argv = subprocess.run(
                ["bash", str(DOCKER_GATE_SCRIPT)],
                cwd=REPO_ROOT,
                env={
                    **env,
                    "CHUMMER_LINUX_SOURCE_BUILD_GATE_RECEIPT_PATH": str(root / "argv-fail.json"),
                },
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            self.assertNotEqual(0, failed_argv.returncode, failed_argv.stdout)
            self.assertIn("updater dispatch/pending-state-clearing simulation receipt differs", failed_argv.stdout)
            self.assertFalse((root / "argv-fail.json").exists())
            success["pkexecInvocation"]["argvCount"] = 3
            success_path.write_text(json.dumps(success) + "\n", encoding="utf-8")

            missing_path = root / "base" / "artifacts" / "updater-special-mode-000.receipt.json"
            missing = json.loads(missing_path.read_text(encoding="utf-8"))
            missing["lastError"] = "/work/base/artifacts/private-installer.deb was not found"
            missing_path.write_text(json.dumps(missing) + "\n", encoding="utf-8")
            failed_portability = subprocess.run(
                ["bash", str(DOCKER_GATE_SCRIPT)],
                cwd=REPO_ROOT,
                env={
                    **env,
                    "CHUMMER_LINUX_SOURCE_BUILD_GATE_RECEIPT_PATH": str(root / "portability-fail.json"),
                },
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            self.assertNotEqual(0, failed_portability.returncode, failed_portability.stdout)
            self.assertIn("machine-local path marker", failed_portability.stdout)
            self.assertFalse((root / "portability-fail.json").exists())
            missing["lastError"] = "Installer payload was not found."
            missing_path.write_text(json.dumps(missing) + "\n", encoding="utf-8")

            bad_mode_digests: list[str] = []
            for base_name in ("base", "repro-base"):
                publish = root / base_name / "artifacts" / "chummer6-linux-x64"
                bad_mode_digests.append(
                    _write_normalized_archive(
                        publish,
                        _manifest(),
                        b"synthetic portable Chummer.Avalonia\n",
                        manifest_mode=0o600,
                    )
                )
            self.assertEqual(1, len(set(bad_mode_digests)))
            bad_mode = subprocess.run(
                ["bash", str(DOCKER_GATE_SCRIPT)],
                cwd=REPO_ROOT,
                env={
                    **env,
                    "CHUMMER_LINUX_SOURCE_BUILD_GATE_RECEIPT_PATH": str(root / "mode-fail.json"),
                    "CHUMMER_LINUX_SOURCE_BUILD_GATE_EXPECTED_ARCHIVE_SHA256": bad_mode_digests[0],
                },
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            self.assertNotEqual(0, bad_mode.returncode, bad_mode.stdout)
            self.assertIn("source archive member has non-canonical mode", bad_mode.stdout)
            self.assertFalse((root / "mode-fail.json").exists())

            stale = _manifest().replace(
                b"pythonRequirement=>=3.11,<4\n",
                b"pythonVersion=3.12.10\n",
            ).replace(
                b"pythonRole=authenticated-orchestrator\n",
                b"",
            )
            stale_digests: list[str] = []
            for base_name in ("base", "repro-base"):
                publish = root / base_name / "artifacts" / "chummer6-linux-x64"
                stale_digests.append(
                    _write_normalized_archive(
                        publish,
                        stale,
                        b"synthetic portable Chummer.Avalonia\n",
                    )
                )
            self.assertEqual(1, len(set(stale_digests)))
            rejected = subprocess.run(
                ["bash", str(DOCKER_GATE_SCRIPT)],
                cwd=REPO_ROOT,
                env={
                    **env,
                    "CHUMMER_LINUX_SOURCE_BUILD_GATE_RECEIPT_PATH": str(root / "rejected.json"),
                    "CHUMMER_LINUX_SOURCE_BUILD_GATE_EXPECTED_ARCHIVE_SHA256": stale_digests[0],
                },
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            self.assertNotEqual(0, rejected.returncode, rejected.stdout)
            self.assertIn("missing v2 authority fields", rejected.stdout)


if __name__ == "__main__":
    unittest.main()
