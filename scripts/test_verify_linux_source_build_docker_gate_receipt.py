#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parent / "verify_linux_source_build_docker_gate_receipt.py"
SPEC = importlib.util.spec_from_file_location("verify_linux_source_build_docker_gate_receipt_module", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class LinuxSourceBuildDockerGateReceiptVerifierTests(unittest.TestCase):
    def _write_receipt(self, root: Path, **overrides: object) -> Path:
        receipt = {
            "contract_name": "ea.chummer6_linux_source_build_docker_gate.v1",
            "status": "passed",
            "generated_at_utc": "20260622T201728Z",
            "docker_image": "debian:bookworm-slim",
            "git_ref": "main",
            "github_org": "ArchonMegalon",
            "repo_base_url": "https://github.com/ArchonMegalon",
            "gate": {
                "name": "linux_source_build_fresh_container",
                "host_audit_wrapper": "scripts/check-host-chummer6-linux.sh",
                "build_script": "scripts/build-chummer6-linux.sh",
                "container_flow": "audit_then_full_build",
            },
            "output": {
                "rid": "linux-x64",
                "binary_name": "Chummer.Avalonia",
                "launcher_name": "run-chummer6.sh",
                "archive_name": "chummer6-linux-x64-20260622T201755Z.tar.gz",
                "executable_sha256": "0744cbfbaac51ceeed13aaa376224000a50f984cf52cb7ee036d1670e343f786",
                "archive_sha256": "c045d341fd0a64b862e1546db188c5fd4ebb728fac0521133908e7724ecf44d7",
            },
            "artifacts": {
                "build_log_name": "linux-desktop-build-20260622T201755Z.log",
                "startup_smoke_receipt_name": "startup-smoke-20260622T201801Z.receipt.json",
                "updater_special_mode_receipt_name": "updater-special-mode-20260622T201803Z.receipt.json",
                "updater_special_mode_success_receipt_name": "updater-special-mode-success-20260622T201804Z.receipt.json",
                "build_manifest_excerpt": [
                    "Chummer6 Linux desktop source build",
                    "Generated UTC: 2026-06-22T20:21:08Z",
                    "Script version: 1.3.0",
                    "Distribution: Debian GNU/Linux 12 (bookworm)",
                    "Architecture: x86_64",
                ],
                "source_heads": {
                    "chummer6-core": "493a7961e38bde4a49fc3ab2db5d4db5cc9cc8ee",
                    "chummer6-hub": "fdb9b2417023cecebe5d3349dd602c68f6f3233c",
                    "chummer6-hub-registry": "fedf0f9a5c6fadcb6f2ce7bb9562d72a5c62d1f3",
                    "chummer6-ui": "4f48a3066e8cdfa9de24fac89fedd6576ed3efd9",
                    "chummer6-ui-kit": "54cf5c2fc5d180cc972a3988ca72ea0ac4cb6820",
                },
            },
            "runtime": {
                "startup_smoke": {
                    "status": "pass",
                    "head_id": "avalonia",
                    "channel_id": "source-build",
                    "rid": "linux-x64",
                    "ready_checkpoint": "fresh_container_gate",
                    "artifact_digest": "sha256:0744cbfbaac51ceeed13aaa376224000a50f984cf52cb7ee036d1670e343f786",
                    "artifact_digest_source": "process_path",
                    "recorded_at_utc": "2026-06-22T20:18:01+00:00",
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
                    "pending_update_version": "run-20260618-051119",
                    "pending_update_channel_id": "stable",
                    "recorded_at_utc": "2026-06-22T20:18:03+00:00",
                },
                "updater_special_mode_success": {
                    "status": "pass",
                    "mode": "desktop_update_launch_installer_success",
                    "head_id": "avalonia",
                    "channel_id": "stable",
                    "rid": "linux-x64",
                    "exit_code": 0,
                    "expected_exit_code": 0,
                    "failure_reason": "",
                    "last_error": "",
                    "pending_update_version": "",
                    "pending_update_channel_id": "",
                    "dpkg_invoked": True,
                    "stage_deleted": True,
                    "recorded_at_utc": "2026-06-22T20:18:04+00:00",
                }
            },
        }
        receipt.update(overrides)
        path = root / "LINUX_SOURCE_BUILD_DOCKER_GATE.generated.json"
        path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        return path

    def test_main_accepts_valid_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            receipt_path = self._write_receipt(root)
            original = MODULE.RECEIPT_PATH
            try:
                MODULE.RECEIPT_PATH = receipt_path
                self.assertEqual(MODULE.main(), 0)
            finally:
                MODULE.RECEIPT_PATH = original

    def test_main_rejects_wrong_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            receipt_path = self._write_receipt(root, status="failed")
            original = MODULE.RECEIPT_PATH
            try:
                MODULE.RECEIPT_PATH = receipt_path
                with self.assertRaises(ValueError):
                    MODULE.main()
            finally:
                MODULE.RECEIPT_PATH = original

    def test_main_rejects_missing_source_head(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            receipt_path = self._write_receipt(
                root,
                artifacts={
                    "build_log_name": "linux-desktop-build-20260622T201755Z.log",
                    "startup_smoke_receipt_name": "startup-smoke-20260622T201801Z.receipt.json",
                    "updater_special_mode_receipt_name": "updater-special-mode-20260622T201803Z.receipt.json",
                    "updater_special_mode_success_receipt_name": "updater-special-mode-success-20260622T201804Z.receipt.json",
                    "build_manifest_excerpt": [
                        "Chummer6 Linux desktop source build",
                        "Generated UTC: 2026-06-22T20:21:08Z",
                        "Script version: 1.3.0",
                        "Distribution: Debian GNU/Linux 12 (bookworm)",
                        "Architecture: x86_64",
                    ],
                    "source_heads": {
                        "chummer6-core": "493a7961e38bde4a49fc3ab2db5d4db5cc9cc8ee",
                        "chummer6-hub": "fdb9b2417023cecebe5d3349dd602c68f6f3233c",
                        "chummer6-hub-registry": "fedf0f9a5c6fadcb6f2ce7bb9562d72a5c62d1f3",
                        "chummer6-ui": "4f48a3066e8cdfa9de24fac89fedd6576ed3efd9",
                    },
                },
            )
            original = MODULE.RECEIPT_PATH
            try:
                MODULE.RECEIPT_PATH = receipt_path
                with self.assertRaises(ValueError):
                    MODULE.main()
            finally:
                MODULE.RECEIPT_PATH = original


if __name__ == "__main__":
    unittest.main()
