#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MATERIALIZE_PATH = Path(__file__).resolve().parent / "materialize_installer_update_truth_receipt.py"
VERIFY_PATH = Path(__file__).resolve().parent / "verify_installer_update_truth_receipt.py"

materialize_spec = importlib.util.spec_from_file_location("materialize_installer_update_truth_receipt_module", MATERIALIZE_PATH)
assert materialize_spec and materialize_spec.loader
MATERIALIZE = importlib.util.module_from_spec(materialize_spec)
materialize_spec.loader.exec_module(MATERIALIZE)

verify_spec = importlib.util.spec_from_file_location("verify_installer_update_truth_receipt_module", VERIFY_PATH)
assert verify_spec and verify_spec.loader
VERIFY = importlib.util.module_from_spec(verify_spec)
verify_spec.loader.exec_module(VERIFY)


class InstallerUpdateTruthReceiptTests(unittest.TestCase):
    def test_materialize_and_verify_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            public_policy = root / "PUBLIC_AUTO_UPDATE_POLICY.md"
            desktop_system = root / "DESKTOP_AUTO_UPDATE_SYSTEM.md"
            source_build_doc = root / "SOURCE_BUILD_LINUX.md"
            source_build_script = root / "build-chummer6-linux.sh"
            release_packet = root / "CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json"
            output = root / "INSTALLER_UPDATE_TRUTH.generated.json"

            public_policy.write_text(
                "* `full auto-update`\n* `notify only`\n* `off`\n",
                encoding="utf-8",
            )
            desktop_system.write_text(
                "\n".join(
                    [
                        "* `full`: check, download, install in place, and relaunch when a compatible promoted update is available",
                        "* `notify`: check and show that a newer build exists, without downloading or applying it automatically",
                        "* `off`: do not check for updates on startup",
                        "Packaged Windows, macOS, and Linux binaries default to `full` when update truth is available.",
                        "Linked accounts also default to `full` unless the user changes the setting.",
                        "Linux source-build launchers default to `notify` so source-built copies never silently replace themselves with a published binary.",
                    ]
                ),
                encoding="utf-8",
            )
            source_build_doc.write_text(
                "\n".join(
                    [
                        "Source-built copies check for newer published builds in notify-only mode by default.",
                        "The generated launcher sets `CHUMMER_DESKTOP_UPDATE_MODE=notify` only when you have not already chosen another mode.",
                    ]
                ),
                encoding="utf-8",
            )
            source_build_script.write_text(
                'export CHUMMER_DESKTOP_UPDATE_MODE="${CHUMMER_DESKTOP_UPDATE_MODE:-notify}"\n',
                encoding="utf-8",
            )
            release_packet.write_text(
                json.dumps(
                    {
                        "public_download_authority": "https://chummer.run/downloads",
                        "available_platforms": ["Windows", "Linux"],
                        "missing_platforms": [],
                        "shelf_truth_line": "Windows and Linux downloads are posted.",
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            original_public_policy = MATERIALIZE.PUBLIC_AUTO_UPDATE_POLICY_PATH
            original_desktop_system = MATERIALIZE.DESKTOP_AUTO_UPDATE_SYSTEM_PATH
            original_source_build_doc = MATERIALIZE.SOURCE_BUILD_DOC_PATH
            original_source_build_script = MATERIALIZE.SOURCE_BUILD_SCRIPT_PATH
            original_release_packet = MATERIALIZE.RELEASE_PACKET_PATH
            original_output = MATERIALIZE.OUTPUT_PATH
            original_verify = VERIFY.RECEIPT_PATH
            try:
                MATERIALIZE.PUBLIC_AUTO_UPDATE_POLICY_PATH = public_policy
                MATERIALIZE.DESKTOP_AUTO_UPDATE_SYSTEM_PATH = desktop_system
                MATERIALIZE.SOURCE_BUILD_DOC_PATH = source_build_doc
                MATERIALIZE.SOURCE_BUILD_SCRIPT_PATH = source_build_script
                MATERIALIZE.RELEASE_PACKET_PATH = release_packet
                MATERIALIZE.OUTPUT_PATH = output
                self.assertEqual(MATERIALIZE.main(), 0)
                VERIFY.RECEIPT_PATH = output
                self.assertEqual(VERIFY.main(), 0)
            finally:
                MATERIALIZE.PUBLIC_AUTO_UPDATE_POLICY_PATH = original_public_policy
                MATERIALIZE.DESKTOP_AUTO_UPDATE_SYSTEM_PATH = original_desktop_system
                MATERIALIZE.SOURCE_BUILD_DOC_PATH = original_source_build_doc
                MATERIALIZE.SOURCE_BUILD_SCRIPT_PATH = original_source_build_script
                MATERIALIZE.RELEASE_PACKET_PATH = original_release_packet
                MATERIALIZE.OUTPUT_PATH = original_output
                VERIFY.RECEIPT_PATH = original_verify

    def test_verify_rejects_wrong_source_build_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "INSTALLER_UPDATE_TRUTH.generated.json"
            output.write_text(
                json.dumps(
                    {
                        "contract_name": "ea.chummer6_installer_update_truth.v1",
                        "status": "passed",
                        "generated_at_utc": "2026-06-22T21:10:00Z",
                        "generated_from": ["a", "b", "c", "d", "e"],
                        "policy": {
                            "update_modes": ["full", "notify", "off"],
                            "installer_first_platforms": ["Windows", "Linux"],
                            "packaged_default_mode": "full",
                            "linked_account_default_mode": "full",
                            "source_build_default_mode": "full",
                            "public_policy_mentions_modes": True,
                            "desktop_system_mentions_exact_modes": True,
                            "desktop_system_mentions_packaged_full_default": True,
                            "desktop_system_mentions_linked_account_full_default": True,
                            "desktop_system_mentions_source_build_notify_default": True,
                            "source_build_doc_mentions_notify_default": True,
                            "source_build_doc_mentions_launcher_override": True,
                            "source_build_script_sets_notify_default": True,
                        },
                        "release_truth": {
                            "public_download_authority": "https://chummer.run/downloads",
                            "available_platforms": ["Windows", "Linux"],
                            "missing_platforms": [],
                            "shelf_truth_line": "Windows and Linux downloads are posted.",
                        },
                        "coherence": {
                            "source_build_default_matches_policy": True,
                            "release_packet_matches_installer_first_platforms": True,
                            "public_download_authority_is_chummer_run": True,
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
