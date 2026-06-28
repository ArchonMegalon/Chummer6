#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MATERIALIZE_PATH = Path(__file__).resolve().parent / "materialize_macos_source_build_contract_receipt.py"
VERIFY_PATH = Path(__file__).resolve().parent / "verify_macos_source_build_contract_receipt.py"

materialize_spec = importlib.util.spec_from_file_location("materialize_macos_source_build_contract_receipt_module", MATERIALIZE_PATH)
assert materialize_spec and materialize_spec.loader
MATERIALIZE = importlib.util.module_from_spec(materialize_spec)
materialize_spec.loader.exec_module(MATERIALIZE)

verify_spec = importlib.util.spec_from_file_location("verify_macos_source_build_contract_receipt_module", VERIFY_PATH)
assert verify_spec and verify_spec.loader
VERIFY = importlib.util.module_from_spec(verify_spec)
verify_spec.loader.exec_module(VERIFY)


class _CompletedProcess:
    def __init__(self, returncode: int, stdout: str) -> None:
        self.returncode = returncode
        self.stdout = stdout


class MacOsSourceBuildContractReceiptTests(unittest.TestCase):
    def test_materialize_and_verify_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            build_script = root / "build-chummer6-macos-local.sh"
            audit_script = root / "check-host-chummer6-macos-local.sh"
            install_script = root / "install-chummer6-macos-local.sh"
            doc = root / "SOURCE_BUILD_MACOS.md"
            download = root / "DOWNLOAD.md"
            tests = root / "test_macos_source_build_script.py"
            maintenance = root / "MAC_SOURCE_BUILD_PATH.md"
            output = root / "MACOS_SOURCE_BUILD_CONTRACT.generated.json"

            audit_script.write_text("placeholder\n", encoding="utf-8")
            tests.write_text("placeholder\n", encoding="utf-8")
            build_script.write_text(
                "\n".join(
                    [
                        "#!/usr/bin/env bash",
                        'SOURCE="${BASH_SOURCE[0]}"',
                        'while [[ -L "$SOURCE" ]]; do',
                        "  break",
                        "done",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            install_script.write_text(
                "\n".join(
                    [
                        "#!/usr/bin/env bash",
                        'SOURCE="${BASH_SOURCE[0]}"',
                        'while [[ -L "$SOURCE" ]]; do',
                        "  break",
                        "done",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            doc.write_text(
                "\n".join(
                    [
                        "The binary is installed by a second script on purpose.",
                        "This is a local personal source build, not an official macOS release.",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            download.write_text("For a personal local Mac build, use [SOURCE_BUILD_MACOS.md](SOURCE_BUILD_MACOS.md).\n", encoding="utf-8")
            maintenance.write_text(
                "\n".join(
                    [
                        "split into a build step and a separate install step",
                        "notify-only for auto-update by default",
                        "analytics-off by default",
                        "A real binary build still has to happen on a Mac host.",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            original_build = MATERIALIZE.BUILD_SCRIPT_PATH
            original_audit = MATERIALIZE.AUDIT_SCRIPT_PATH
            original_install = MATERIALIZE.INSTALL_SCRIPT_PATH
            original_doc = MATERIALIZE.DOC_PATH
            original_download = MATERIALIZE.DOWNLOAD_PATH
            original_tests = MATERIALIZE.TEST_PATH
            original_maintenance = MATERIALIZE.MAINTENANCE_POLICY_PATH
            original_output = MATERIALIZE.OUTPUT_PATH
            original_verify = VERIFY.RECEIPT_PATH
            try:
                MATERIALIZE.BUILD_SCRIPT_PATH = build_script
                MATERIALIZE.AUDIT_SCRIPT_PATH = audit_script
                MATERIALIZE.INSTALL_SCRIPT_PATH = install_script
                MATERIALIZE.DOC_PATH = doc
                MATERIALIZE.DOWNLOAD_PATH = download
                MATERIALIZE.TEST_PATH = tests
                MATERIALIZE.MAINTENANCE_POLICY_PATH = maintenance
                MATERIALIZE.OUTPUT_PATH = output
                with patch.object(
                    MATERIALIZE.subprocess,
                    "run",
                    side_effect=[
                        _CompletedProcess(0, ""),
                        _CompletedProcess(0, ""),
                        _CompletedProcess(0, ""),
                        _CompletedProcess(0, ".......\n----------------------------------------------------------------------\nRan 7 tests in 0.030s\n\nOK\n"),
                    ],
                ):
                    self.assertEqual(MATERIALIZE.main(), 0)
                VERIFY.RECEIPT_PATH = output
                self.assertEqual(VERIFY.main(), 0)
            finally:
                MATERIALIZE.BUILD_SCRIPT_PATH = original_build
                MATERIALIZE.AUDIT_SCRIPT_PATH = original_audit
                MATERIALIZE.INSTALL_SCRIPT_PATH = original_install
                MATERIALIZE.DOC_PATH = original_doc
                MATERIALIZE.DOWNLOAD_PATH = original_download
                MATERIALIZE.TEST_PATH = original_tests
                MATERIALIZE.MAINTENANCE_POLICY_PATH = original_maintenance
                MATERIALIZE.OUTPUT_PATH = original_output
                VERIFY.RECEIPT_PATH = original_verify

    def test_verify_rejects_unbounded_runtime_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "MACOS_SOURCE_BUILD_CONTRACT.generated.json"
            output.write_text(
                json.dumps(
                    {
                        "contract_name": "ea.chummer6_macos_source_build_contract.v1",
                        "status": "passed",
                        "generated_at_utc": "2026-06-27T20:00:00Z",
                        "scope": "script_contract_only",
                        "runtime_coverage": "runtime_e2e",
                        "real_macos_runtime_proof_required": False,
                        "generated_from": ["a", "b", "c", "d", "e", "f", "g"],
                        "syntax_checks": [
                            {"path": "a", "command": ["bash", "-n", "a"], "exit_code": 0},
                            {"path": "b", "command": ["bash", "-n", "b"], "exit_code": 0},
                            {"path": "c", "command": ["bash", "-n", "c"], "exit_code": 0},
                        ],
                        "unit_test": {
                            "command": ["python3", "-m", "unittest", "tests/test_macos_source_build_script.py", "-q"],
                            "exit_code": 0,
                            "summary_lines": ["Ran 7 tests", "OK"],
                        },
                        "policy": {
                            "maintenance_policy_marks_real_build_as_macos_only": True,
                            "maintenance_policy_requires_two_step_install": True,
                            "maintenance_policy_requires_notify_default": True,
                            "maintenance_policy_requires_analytics_off_default": True,
                            "build_launcher_resolves_symlinks": True,
                            "install_launcher_resolves_symlinks": True,
                            "doc_marks_local_personal_build": True,
                            "doc_marks_not_public_release": True,
                            "doc_marks_second_script_install": True,
                        },
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            original_verify = VERIFY.RECEIPT_PATH
            try:
                VERIFY.RECEIPT_PATH = output
                with self.assertRaises(ValueError):
                    VERIFY.main()
            finally:
                VERIFY.RECEIPT_PATH = original_verify


if __name__ == "__main__":
    unittest.main()
