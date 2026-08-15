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
            linux_source_build_policy = root / "LINUX_SOURCE_BUILD_PATH.md"
            mac_source_build_policy = root / "MAC_SOURCE_BUILD_PATH.md"
            source_build_linux_doc = root / "SOURCE_BUILD_LINUX.md"
            source_build_linux_script = root / "build-chummer6-linux.sh"
            source_build_linux_install_script = root / "install-chummer6-linux-local.sh"
            source_build_macos_doc = root / "SOURCE_BUILD_MACOS.md"
            source_build_macos_build_script = root / "build-chummer6-macos-local.sh"
            source_build_macos_install_script = root / "install-chummer6-macos-local.sh"
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
                        "Linux local-source-build launchers default to `notify` so source-built copies never silently replace themselves with a published binary.",
                        "The Linux local-source-build lane stays split into a build step plus a separate user-local install step.",
                        "The personal macOS local-source-build lane follows the same update default.",
                        "It remains a separate build step plus install step, stays outside the public installer shelf, and defaults the installed app bundle to `notify` rather than silently switching itself onto a published binary lane.",
                    ]
                ),
                encoding="utf-8",
            )
            linux_source_build_policy.write_text(
                "split into a build step and a separate user-local install step\n",
                encoding="utf-8",
            )
            mac_source_build_policy.write_text(
                "split into a build step and a separate install step\n",
                encoding="utf-8",
            )
            source_build_linux_doc.write_text(
                "\n".join(
                    [
                        "The binary is installed by a second script on purpose. Source-built copies check",
                        "for newer published builds in notify-only mode by default. The generated launcher",
                        "sets `CHUMMER_DESKTOP_UPDATE_MODE=notify` only when you have not already chosen",
                        "another mode. Analytics also default to `off` through",
                        "`CHUMMER_DESKTOP_ANALYTICS_DEFAULT=off` unless you already chose another value.",
                    ]
                ),
                encoding="utf-8",
            )
            source_build_linux_script.write_text(
                "This script only builds the binary and archive artifacts.\n",
                encoding="utf-8",
            )
            source_build_linux_install_script.write_text(
                "\n".join(
                    [
                        'export CHUMMER_DESKTOP_UPDATE_MODE="${CHUMMER_DESKTOP_UPDATE_MODE:-notify}"',
                        'export CHUMMER_DESKTOP_ANALYTICS_DEFAULT="${CHUMMER_DESKTOP_ANALYTICS_DEFAULT:-off}"',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            source_build_macos_doc.write_text(
                "\n".join(
                    [
                        "The binary is installed by a second script on purpose.",
                        "CHUMMER_DESKTOP_UPDATE_MODE=notify",
                        "CHUMMER_DESKTOP_ANALYTICS_DEFAULT=off",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            source_build_macos_build_script.write_text(
                "\n".join(
                    [
                        "This script only builds the binary and archive artifacts. Install the result later with ./install-chummer6-macos-local.sh.",
                        'export CHUMMER_DESKTOP_UPDATE_MODE="${CHUMMER_DESKTOP_UPDATE_MODE:-notify}"',
                        'export CHUMMER_DESKTOP_ANALYTICS_DEFAULT="${CHUMMER_DESKTOP_ANALYTICS_DEFAULT:-off}"',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            source_build_macos_install_script.write_text(
                "\n".join(
                    [
                        'export CHUMMER_DESKTOP_UPDATE_MODE="${CHUMMER_DESKTOP_UPDATE_MODE:-notify}"',
                        'export CHUMMER_DESKTOP_ANALYTICS_DEFAULT="${CHUMMER_DESKTOP_ANALYTICS_DEFAULT:-off}"',
                    ]
                )
                + "\n",
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
            original_linux_source_build_policy = MATERIALIZE.LINUX_SOURCE_BUILD_POLICY_PATH
            original_mac_source_build_policy = MATERIALIZE.MAC_SOURCE_BUILD_POLICY_PATH
            original_source_build_linux_doc = MATERIALIZE.SOURCE_BUILD_LINUX_DOC_PATH
            original_source_build_linux_script = MATERIALIZE.SOURCE_BUILD_LINUX_SCRIPT_PATH
            original_source_build_linux_install_script = MATERIALIZE.SOURCE_BUILD_LINUX_INSTALL_SCRIPT_PATH
            original_source_build_macos_doc = MATERIALIZE.SOURCE_BUILD_MACOS_DOC_PATH
            original_source_build_macos_build_script = MATERIALIZE.SOURCE_BUILD_MACOS_BUILD_SCRIPT_PATH
            original_source_build_macos_install_script = MATERIALIZE.SOURCE_BUILD_MACOS_INSTALL_SCRIPT_PATH
            original_release_packet = MATERIALIZE.RELEASE_PACKET_PATH
            original_output = MATERIALIZE.OUTPUT_PATH
            original_verify = VERIFY.RECEIPT_PATH
            try:
                MATERIALIZE.PUBLIC_AUTO_UPDATE_POLICY_PATH = public_policy
                MATERIALIZE.DESKTOP_AUTO_UPDATE_SYSTEM_PATH = desktop_system
                MATERIALIZE.LINUX_SOURCE_BUILD_POLICY_PATH = linux_source_build_policy
                MATERIALIZE.MAC_SOURCE_BUILD_POLICY_PATH = mac_source_build_policy
                MATERIALIZE.SOURCE_BUILD_LINUX_DOC_PATH = source_build_linux_doc
                MATERIALIZE.SOURCE_BUILD_LINUX_SCRIPT_PATH = source_build_linux_script
                MATERIALIZE.SOURCE_BUILD_LINUX_INSTALL_SCRIPT_PATH = source_build_linux_install_script
                MATERIALIZE.SOURCE_BUILD_MACOS_DOC_PATH = source_build_macos_doc
                MATERIALIZE.SOURCE_BUILD_MACOS_BUILD_SCRIPT_PATH = source_build_macos_build_script
                MATERIALIZE.SOURCE_BUILD_MACOS_INSTALL_SCRIPT_PATH = source_build_macos_install_script
                MATERIALIZE.RELEASE_PACKET_PATH = release_packet
                MATERIALIZE.OUTPUT_PATH = output
                self.assertEqual(MATERIALIZE.main(), 0)
                VERIFY.RECEIPT_PATH = output
                self.assertEqual(VERIFY.main(), 0)
            finally:
                MATERIALIZE.PUBLIC_AUTO_UPDATE_POLICY_PATH = original_public_policy
                MATERIALIZE.DESKTOP_AUTO_UPDATE_SYSTEM_PATH = original_desktop_system
                MATERIALIZE.LINUX_SOURCE_BUILD_POLICY_PATH = original_linux_source_build_policy
                MATERIALIZE.MAC_SOURCE_BUILD_POLICY_PATH = original_mac_source_build_policy
                MATERIALIZE.SOURCE_BUILD_LINUX_DOC_PATH = original_source_build_linux_doc
                MATERIALIZE.SOURCE_BUILD_LINUX_SCRIPT_PATH = original_source_build_linux_script
                MATERIALIZE.SOURCE_BUILD_LINUX_INSTALL_SCRIPT_PATH = original_source_build_linux_install_script
                MATERIALIZE.SOURCE_BUILD_MACOS_DOC_PATH = original_source_build_macos_doc
                MATERIALIZE.SOURCE_BUILD_MACOS_BUILD_SCRIPT_PATH = original_source_build_macos_build_script
                MATERIALIZE.SOURCE_BUILD_MACOS_INSTALL_SCRIPT_PATH = original_source_build_macos_install_script
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
                        "generated_from": ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k"],
                        "policy": {
                            "update_modes": ["full", "notify", "off"],
                            "installer_first_platforms": ["Windows", "Linux"],
                            "packaged_default_mode": "full",
                            "linked_account_default_mode": "full",
                            "source_build_linux_default_mode": "full",
                            "source_build_linux_analytics_default": "off",
                            "source_build_macos_default_mode": "notify",
                            "source_build_macos_analytics_default": "off",
                            "public_policy_mentions_modes": True,
                            "desktop_system_mentions_exact_modes": True,
                            "desktop_system_mentions_packaged_full_default": True,
                            "desktop_system_mentions_linked_account_full_default": True,
                            "desktop_system_mentions_linux_source_build_notify_default": True,
                            "desktop_system_mentions_linux_source_build_split": True,
                            "desktop_system_mentions_macos_local_source_build_notify_default": True,
                            "desktop_system_mentions_macos_local_source_build_split": True,
                            "linux_source_build_policy_mentions_split": True,
                            "mac_source_build_policy_mentions_split": True,
                            "source_build_linux_doc_mentions_notify_default": True,
                            "source_build_linux_doc_mentions_second_script_install": True,
                            "source_build_linux_doc_mentions_launcher_override": True,
                            "source_build_linux_doc_mentions_analytics_default_off": True,
                            "source_build_linux_build_script_does_not_invoke_local_installer": True,
                            "source_build_linux_build_script_avoids_runtime_default_exports": True,
                            "source_build_linux_install_script_sets_notify_default": True,
                            "source_build_linux_install_script_sets_analytics_default_off": True,
                            "source_build_macos_doc_mentions_second_script_install": True,
                            "source_build_macos_doc_mentions_notify_default": True,
                            "source_build_macos_doc_mentions_analytics_default_off": True,
                            "source_build_macos_build_script_mentions_second_script_install": True,
                            "source_build_macos_build_script_sets_notify_default": True,
                            "source_build_macos_build_script_sets_analytics_default_off": True,
                            "source_build_macos_install_script_sets_notify_default": True,
                            "source_build_macos_install_script_sets_analytics_default_off": True,
                        },
                        "release_truth": {
                            "public_download_authority": "https://chummer.run/downloads",
                            "available_platforms": ["Windows", "Linux"],
                            "missing_platforms": [],
                            "shelf_truth_line": "Windows and Linux downloads are posted.",
                        },
                        "coherence": {
                            "linux_source_build_defaults_match_policy": True,
                            "linux_source_build_is_explicitly_two_step": True,
                            "macos_source_build_defaults_match_policy": True,
                            "macos_source_build_is_explicitly_two_step": True,
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
