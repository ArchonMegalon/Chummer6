#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MATERIALIZE_PATH = Path(__file__).resolve().parent / "materialize_desktop_update_runtime_receipt.py"
VERIFY_PATH = Path(__file__).resolve().parent / "verify_desktop_update_runtime_receipt.py"

materialize_spec = importlib.util.spec_from_file_location("materialize_desktop_update_runtime_receipt_module", MATERIALIZE_PATH)
assert materialize_spec and materialize_spec.loader
MATERIALIZE = importlib.util.module_from_spec(materialize_spec)
materialize_spec.loader.exec_module(MATERIALIZE)

verify_spec = importlib.util.spec_from_file_location("verify_desktop_update_runtime_receipt_module", VERIFY_PATH)
assert verify_spec and verify_spec.loader
VERIFY = importlib.util.module_from_spec(verify_spec)
verify_spec.loader.exec_module(VERIFY)


class _CompletedProcess:
    def __init__(self, returncode: int, stdout: str) -> None:
        self.returncode = returncode
        self.stdout = stdout


class DesktopUpdateRuntimeReceiptTests(unittest.TestCase):
    def test_materialize_and_verify_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fake_repo_root = root / "Chummer6"
            fake_repo_root.mkdir()
            desktop_repo = root / "chummer-presentation"
            project = desktop_repo / "Chummer.Tests"
            project.mkdir(parents=True)
            (project / "Chummer.Tests.csproj").write_text("<Project />\n", encoding="utf-8")
            (project / "DesktopUpdateRuntimeTests.cs").write_text("public sealed class DesktopUpdateRuntimeTests {}\n", encoding="utf-8")
            (root / "chummer-hub-registry" / "Chummer.Hub.Registry.Contracts").mkdir(parents=True)
            (root / "chummer-hub-registry" / "Chummer.Hub.Registry.Contracts" / "Chummer.Hub.Registry.Contracts.csproj").write_text("<Project />\n", encoding="utf-8")
            (root / "chummer.run-services" / "Chummer.Run.Contracts").mkdir(parents=True)
            (root / "chummer.run-services" / "Chummer.Run.Contracts" / "Chummer.Run.Contracts.csproj").write_text("<Project />\n", encoding="utf-8")
            (root / "fleet" / "repos" / "chummer-media-factory" / "src" / "Chummer.Media.Contracts").mkdir(parents=True)
            (root / "fleet" / "repos" / "chummer-media-factory" / "src" / "Chummer.Media.Contracts" / "Chummer.Media.Contracts.csproj").write_text("<Project />\n", encoding="utf-8")
            output = root / "DESKTOP_UPDATE_RUNTIME.generated.json"

            original_repo_root = MATERIALIZE.REPO_ROOT
            original_output = MATERIALIZE.OUTPUT_PATH
            original_resolve = MATERIALIZE._resolve_desktop_repo_root
            original_verify = VERIFY.RECEIPT_PATH
            try:
                MATERIALIZE.REPO_ROOT = fake_repo_root
                MATERIALIZE.OUTPUT_PATH = output
                MATERIALIZE._resolve_desktop_repo_root = lambda: desktop_repo
                with patch.object(
                    MATERIALIZE.subprocess,
                    "run",
                    side_effect=[
                        _CompletedProcess(0, "Build succeeded.\n"),
                        _CompletedProcess(0, "Build succeeded.\n"),
                        _CompletedProcess(0, "Build succeeded.\n"),
                        _CompletedProcess(
                            0,
                            "\n".join(
                                [
                                    "Test run for /tmp/Chummer.Tests.dll (.NETCoreApp,Version=v10.0)",
                                    "Passed!  - Failed:     0, Passed:    43, Skipped:     0, Total:    43, Duration: 2 s",
                                ]
                            ),
                        ),
                    ],
                ):
                    self.assertEqual(MATERIALIZE.main(), 0)
                VERIFY.RECEIPT_PATH = output
                self.assertEqual(VERIFY.main(), 0)
            finally:
                MATERIALIZE.REPO_ROOT = original_repo_root
                MATERIALIZE.OUTPUT_PATH = original_output
                MATERIALIZE._resolve_desktop_repo_root = original_resolve
                VERIFY.RECEIPT_PATH = original_verify

    def test_verify_rejects_failed_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "DESKTOP_UPDATE_RUNTIME.generated.json"
            output.write_text(
                json.dumps(
                    {
                        "contract_name": "ea.chummer6_desktop_update_runtime.v1",
                        "status": "failed",
                        "generated_at_utc": "2026-06-24T10:00:00Z",
                        "tested_repo_name": "chummer-presentation",
                        "generated_from": ["a", "b"],
                        "command": [
                            "dotnet",
                            "test",
                            "--project",
                            "Chummer.Tests/Chummer.Tests.csproj",
                            "-p:RunDesktopUpdateTestsOnly=true",
                            "--filter",
                            "FullyQualifiedName~DesktopUpdateRuntimeTests",
                            "-v",
                            "minimal",
                        ],
                        "timeout_seconds": 900,
                        "run_desktop_update_tests_only": True,
                        "filter": "FullyQualifiedName~DesktopUpdateRuntimeTests",
                        "result": {
                            "exit_code": 1,
                            "summary_lines": ["Failed!  - Failed:     1, Passed:    42, Skipped:     0, Total:    43, Duration: 2 s"],
                            "mentions_passed_banner": False,
                            "mentions_desktop_update_runtime_tests": True,
                            "mentions_total": True,
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
