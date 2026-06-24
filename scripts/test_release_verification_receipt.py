#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MATERIALIZE_PATH = Path(__file__).resolve().parent / "materialize_release_verification_receipt.py"
VERIFY_PATH = Path(__file__).resolve().parent / "verify_release_verification_receipt.py"

materialize_spec = importlib.util.spec_from_file_location("materialize_release_verification_receipt_module", MATERIALIZE_PATH)
assert materialize_spec and materialize_spec.loader
MATERIALIZE = importlib.util.module_from_spec(materialize_spec)
materialize_spec.loader.exec_module(MATERIALIZE)

verify_spec = importlib.util.spec_from_file_location("verify_release_verification_receipt_module", VERIFY_PATH)
assert verify_spec and verify_spec.loader
VERIFY = importlib.util.module_from_spec(verify_spec)
verify_spec.loader.exec_module(VERIFY)


class ReleaseVerificationReceiptTests(unittest.TestCase):
    def _write_inputs(self, root: Path) -> tuple[Path, Path, Path, Path, Path]:
        linux_gate = root / "LINUX_SOURCE_BUILD_DOCKER_GATE.generated.json"
        installer_update_truth = root / "INSTALLER_UPDATE_TRUTH.generated.json"
        desktop_update_runtime = root / "DESKTOP_UPDATE_RUNTIME.generated.json"
        release_packet = root / "CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json"
        output = root / "RELEASE_VERIFICATION_CONVERGENCE.generated.json"
        startup_window_source = root / "DesktopStartupUpdateWindow.cs"
        startup_window_tests = root / "DesktopStartupUpdateWindowTests.cs"
        install_link_window_source = root / "DesktopInstallLinkingWindow.cs"
        install_link_window_tests = root / "DesktopInstallLinkingShellChromeTests.cs"
        install_link_runtime_tests = root / "DesktopInstallLinkingRuntimeTests.cs"

        linux_gate.write_text(
            json.dumps(
                {
                    "status": "passed",
                    "docker_image": "debian:bookworm-slim",
                    "output": {
                        "rid": "linux-x64",
                        "archive_sha256": "a" * 64,
                        "executable_sha256": "b" * 64,
                    },
                    "runtime": {
                        "startup_smoke": {
                            "status": "pass",
                            "ready_checkpoint": "fresh_container_gate",
                        },
                        "updater_special_mode": {
                            "status": "pass",
                            "mode": "desktop_update_launch_installer",
                            "failure_reason": "installer_launch_failed",
                        },
                        "updater_special_mode_success": {
                            "status": "pass",
                            "mode": "desktop_update_launch_installer_success",
                        }
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        installer_update_truth.write_text(
            json.dumps(
                {
                    "status": "passed",
                    "policy": {
                        "update_modes": ["full", "notify", "off"],
                        "packaged_default_mode": "full",
                        "source_build_default_mode": "notify",
                    },
                    "release_truth": {
                        "public_download_authority": "https://chummer.run/downloads",
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        release_packet.write_text(
            json.dumps(
                {
                    "release_status": "Published",
                    "published_at": "June 21, 2026 at 5:53 UTC",
                    "public_download_authority": "https://chummer.run/downloads",
                    "available_platforms": ["Windows", "Linux"],
                    "missing_platforms": [],
                    "shelf_truth_line": "Windows and Linux downloads are posted.",
                    "linux_source_build_gate": {
                        "status": "passed",
                        "docker_image": "debian:bookworm-slim",
                        "rid": "linux-x64",
                        "archive_sha256": "a" * 64,
                        "executable_sha256": "b" * 64,
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        desktop_update_runtime.write_text(
            json.dumps(
                {
                    "status": "passed",
                    "tested_repo_name": "chummer-presentation",
                    "run_desktop_update_tests_only": True,
                    "filter": "FullyQualifiedName~DesktopUpdateRuntimeTests",
                    "timeout_seconds": 900,
                    "result": {
                        "exit_code": 0,
                        "mentions_passed_banner": True,
                        "mentions_desktop_update_runtime_tests": True,
                        "mentions_total": True,
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        startup_window_source.write_text(
            """
internal sealed class DesktopStartupUpdateWindow
{
    internal static DesktopStartupUpdateViewState BuildViewState(object update) => default!;
    internal static int GetCompletionDisplayDelayMs(bool exitRequested, string? reason) => 0;
    private const string Interruption = "Keep this window open. Starting another copy can interrupt the update.";
    private const string Mac = "A macOS update is ready. Open Downloads to install it manually; this copy will stay usable.";
}

internal sealed record DesktopStartupUpdateViewState(
    string Title,
    string Body,
    bool ShowWaitText,
    bool IsIndeterminate,
    int ProgressMaximum,
    int ProgressValue);
""".strip()
            + "\n",
            encoding="utf-8",
        )
        startup_window_tests.write_text(
            """
[TestClass]
public sealed class DesktopStartupUpdateWindowTests
{
    [TestMethod]
    public void BuildViewState_maps_progress_stage_to_visible_copy_and_determinate_progress() {}

    [TestMethod]
    public void GetCompletionDisplayDelayMs_keeps_relaunch_and_failures_visible_long_enough_to_perceive() {}
}
""".strip()
            + "\n",
            encoding="utf-8",
        )
        install_link_window_source.write_text(
            """
internal sealed class DesktopInstallLinkingWindow
{
    private readonly object _browserFallbackPanel;
    private readonly object _browserFallbackUrlText;
    private void ShowManualBrowserFallback(string loginUrl, string? failureReason) {}
    internal static string BuildBrowserFallbackHeading(string language) => "";
    internal static string BuildBrowserFallbackDetail(string language, string? failureReason) => "";
    private const string Copy = "desktop.install_link.button.copy_login_url";
}
""".strip()
            + "\n",
            encoding="utf-8",
        )
        install_link_window_tests.write_text(
            """
[TestClass]
public sealed class DesktopInstallLinkingShellChromeTests
{
    [TestMethod]
    public void Browser_fallback_copy_stays_clear_and_user_facing() {}
}
""".strip()
            + "\n",
            encoding="utf-8",
        )
        install_link_runtime_tests.write_text(
            """
[TestClass]
public sealed class DesktopInstallLinkingRuntimeTests
{
    [TestMethod]
    public async Task TryHandleHeadlessInstallLinkModeAsync_persists_browser_dispatch_failure() {}
}
""".strip()
            + "\n",
            encoding="utf-8",
        )
        return linux_gate, installer_update_truth, desktop_update_runtime, release_packet, output, startup_window_source, startup_window_tests, install_link_window_source, install_link_window_tests, install_link_runtime_tests

    def test_materialize_and_verify_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            linux_gate, installer_update_truth, desktop_update_runtime, release_packet, output, startup_window_source, startup_window_tests, install_link_window_source, install_link_window_tests, install_link_runtime_tests = self._write_inputs(root)

            original_linux = MATERIALIZE.LINUX_GATE_PATH
            original_installer_update = MATERIALIZE.INSTALLER_UPDATE_TRUTH_PATH
            original_desktop_update_runtime = MATERIALIZE.DESKTOP_UPDATE_RUNTIME_PATH
            original_packet = MATERIALIZE.RELEASE_PACKET_PATH
            original_output = MATERIALIZE.OUTPUT_PATH
            original_startup_window_source = MATERIALIZE.STARTUP_WINDOW_SOURCE_PATH
            original_startup_window_tests = MATERIALIZE.STARTUP_WINDOW_TEST_PATH
            original_install_link_window_source = MATERIALIZE.INSTALL_LINK_WINDOW_SOURCE_PATH
            original_install_link_window_tests = MATERIALIZE.INSTALL_LINK_WINDOW_TEST_PATH
            original_install_link_runtime_tests = MATERIALIZE.INSTALL_LINK_RUNTIME_TEST_PATH
            original_verify = VERIFY.RECEIPT_PATH
            try:
                MATERIALIZE.LINUX_GATE_PATH = linux_gate
                MATERIALIZE.INSTALLER_UPDATE_TRUTH_PATH = installer_update_truth
                MATERIALIZE.DESKTOP_UPDATE_RUNTIME_PATH = desktop_update_runtime
                MATERIALIZE.RELEASE_PACKET_PATH = release_packet
                MATERIALIZE.OUTPUT_PATH = output
                MATERIALIZE.STARTUP_WINDOW_SOURCE_PATH = startup_window_source
                MATERIALIZE.STARTUP_WINDOW_TEST_PATH = startup_window_tests
                MATERIALIZE.INSTALL_LINK_WINDOW_SOURCE_PATH = install_link_window_source
                MATERIALIZE.INSTALL_LINK_WINDOW_TEST_PATH = install_link_window_tests
                MATERIALIZE.INSTALL_LINK_RUNTIME_TEST_PATH = install_link_runtime_tests
                self.assertEqual(MATERIALIZE.main(), 0)
                VERIFY.RECEIPT_PATH = output
                self.assertEqual(VERIFY.main(), 0)
            finally:
                MATERIALIZE.LINUX_GATE_PATH = original_linux
                MATERIALIZE.INSTALLER_UPDATE_TRUTH_PATH = original_installer_update
                MATERIALIZE.DESKTOP_UPDATE_RUNTIME_PATH = original_desktop_update_runtime
                MATERIALIZE.RELEASE_PACKET_PATH = original_packet
                MATERIALIZE.OUTPUT_PATH = original_output
                MATERIALIZE.STARTUP_WINDOW_SOURCE_PATH = original_startup_window_source
                MATERIALIZE.STARTUP_WINDOW_TEST_PATH = original_startup_window_tests
                MATERIALIZE.INSTALL_LINK_WINDOW_SOURCE_PATH = original_install_link_window_source
                MATERIALIZE.INSTALL_LINK_WINDOW_TEST_PATH = original_install_link_window_tests
                MATERIALIZE.INSTALL_LINK_RUNTIME_TEST_PATH = original_install_link_runtime_tests
                VERIFY.RECEIPT_PATH = original_verify

    def test_verify_rejects_mismatched_coherence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _, _, _, _, output, _, _, _, _, _ = self._write_inputs(root)
            output.write_text(
                json.dumps(
                    {
                        "contract_name": "ea.chummer6_release_verification_convergence.v1",
                        "status": "passed",
                        "generated_at_utc": "2026-06-22T20:30:00Z",
                        "generated_from": ["a", "b", "c", "d"],
                        "checks": {
                            "linux_source_build_gate": {
                            "status": "passed",
                            "docker_image": "debian:bookworm-slim",
                            "rid": "linux-x64",
                            "startup_smoke_status": "pass",
                            "startup_smoke_ready_checkpoint": "fresh_container_gate",
                            "updater_special_mode_status": "pass",
                            "updater_special_mode_mode": "desktop_update_launch_installer",
                            "updater_special_mode_failure_reason": "installer_launch_failed",
                            "updater_special_mode_success_status": "pass",
                            "updater_special_mode_success_mode": "desktop_update_launch_installer_success",
                        },
                            "installer_update_truth": {
                                "status": "passed",
                                "update_modes": ["full", "notify", "off"],
                                "source_build_default_mode": "notify",
                                "packaged_default_mode": "full",
                                "public_download_authority": "https://chummer.run/downloads",
                            },
                            "desktop_update_runtime": {
                                "status": "passed",
                                "tested_repo_name": "chummer-presentation",
                                "run_desktop_update_tests_only": True,
                                "filter": "FullyQualifiedName~DesktopUpdateRuntimeTests",
                                "exit_code": 0,
                                "mentions_passed_banner": True,
                                "mentions_desktop_update_runtime_tests": True,
                                "mentions_total": True,
                            },
                            "release_truth_packet": {
                                "release_status": "Published",
                                "available_platforms": ["Windows", "Linux"],
                            },
                            "updater_startup_window": {
                                "has_view_state_mapping": True,
                                "has_visibility_delay_policy": True,
                                "has_interruption_warning": True,
                                "has_manual_macos_recovery_copy": True,
                                "has_progress_mapping_tests": True,
                                "has_delay_policy_tests": True,
                            },
                            "install_link_browser_fallback": {
                                "has_dedicated_fallback_panel": True,
                                "has_fallback_heading": True,
                                "has_fallback_detail": True,
                                "has_fallback_url_surface": True,
                                "has_copy_claim_link_button": True,
                                "has_linux_failure_runtime_test": True,
                                "has_window_fallback_copy_test": True,
                            },
                        },
                        "coherence": {
                            "linux_gate_status_matches_packet": True,
                            "linux_gate_rid_matches_packet": False,
                            "linux_gate_archive_sha_matches_packet": True,
                            "linux_gate_executable_sha_matches_packet": True,
                            "linux_gate_startup_smoke_passed": True,
                            "linux_gate_updater_special_mode_passed": True,
                            "linux_gate_updater_special_mode_success_passed": True,
                            "installer_update_truth_matches_release_authority": True,
                            "installer_update_truth_keeps_source_build_notify_default": True,
                            "desktop_update_runtime_passed": True,
                            "desktop_update_runtime_runs_reduced_lane": True,
                            "desktop_update_runtime_targets_update_tests": True,
                            "desktop_update_runtime_exit_code_zero": True,
                            "desktop_update_runtime_mentions_passed_banner": True,
                            "updater_startup_window_has_view_state_mapping": True,
                            "updater_startup_window_has_visibility_delay_policy": True,
                            "updater_startup_window_has_progress_mapping_tests": True,
                            "updater_startup_window_has_delay_policy_tests": True,
                            "install_link_browser_fallback_has_panel": True,
                            "install_link_browser_fallback_has_detail_copy": True,
                            "install_link_browser_fallback_has_runtime_failure_test": True,
                            "install_link_browser_fallback_has_window_copy_test": True,
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
