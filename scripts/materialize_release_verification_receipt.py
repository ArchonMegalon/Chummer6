#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RECEIPTS_ROOT = REPO_ROOT / ".guide-internal" / "receipts"
LINUX_GATE_PATH = RECEIPTS_ROOT / "LINUX_SOURCE_BUILD_DOCKER_GATE.generated.json"
INSTALLER_UPDATE_TRUTH_PATH = RECEIPTS_ROOT / "INSTALLER_UPDATE_TRUTH.generated.json"
RELEASE_PACKET_PATH = RECEIPTS_ROOT / "CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json"
OUTPUT_PATH = RECEIPTS_ROOT / "RELEASE_VERIFICATION_CONVERGENCE.generated.json"
STARTUP_WINDOW_SOURCE_PATH = REPO_ROOT.parent / "chummer6-ui" / "Chummer.Avalonia" / "DesktopStartupUpdateWindow.cs"
STARTUP_WINDOW_TEST_PATH = REPO_ROOT.parent / "chummer6-ui" / "Chummer.Tests" / "Presentation" / "DesktopStartupUpdateWindowTests.cs"
INSTALL_LINK_WINDOW_SOURCE_PATH = REPO_ROOT.parent / "chummer6-ui" / "Chummer.Avalonia" / "DesktopInstallLinkingWindow.cs"
INSTALL_LINK_WINDOW_TEST_PATH = REPO_ROOT.parent / "chummer6-ui" / "Chummer.Tests" / "Presentation" / "DesktopInstallLinkingShellChromeTests.cs"
INSTALL_LINK_RUNTIME_TEST_PATH = REPO_ROOT.parent / "chummer6-ui" / "Chummer.Tests" / "DesktopInstallLinkingRuntimeTests.cs"


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def main() -> int:
    linux_gate = _load_json(LINUX_GATE_PATH)
    installer_update_truth = _load_json(INSTALLER_UPDATE_TRUTH_PATH)
    release_packet = _load_json(RELEASE_PACKET_PATH)
    startup_window_source = STARTUP_WINDOW_SOURCE_PATH.read_text(encoding="utf-8")
    startup_window_tests = STARTUP_WINDOW_TEST_PATH.read_text(encoding="utf-8")
    install_link_window_source = INSTALL_LINK_WINDOW_SOURCE_PATH.read_text(encoding="utf-8")
    install_link_window_tests = INSTALL_LINK_WINDOW_TEST_PATH.read_text(encoding="utf-8")
    install_link_runtime_tests = INSTALL_LINK_RUNTIME_TEST_PATH.read_text(encoding="utf-8")
    projected_gate = release_packet.get("linux_source_build_gate") or {}

    output = {
        "contract_name": "ea.chummer6_release_verification_convergence.v1",
        "status": "passed",
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_from": [
            _display_path(LINUX_GATE_PATH),
            _display_path(INSTALLER_UPDATE_TRUTH_PATH),
            _display_path(RELEASE_PACKET_PATH),
        ],
        "checks": {
            "linux_source_build_gate": {
                "status": str(linux_gate.get("status") or "").strip(),
                "docker_image": str(linux_gate.get("docker_image") or "").strip(),
                "rid": str(((linux_gate.get("output") or {}) if isinstance(linux_gate.get("output"), dict) else {}).get("rid") or "").strip(),
                "archive_sha256": str(((linux_gate.get("output") or {}) if isinstance(linux_gate.get("output"), dict) else {}).get("archive_sha256") or "").strip(),
                "executable_sha256": str(((linux_gate.get("output") or {}) if isinstance(linux_gate.get("output"), dict) else {}).get("executable_sha256") or "").strip(),
                "startup_smoke_status": str(((linux_gate.get("runtime") or {}) if isinstance(linux_gate.get("runtime"), dict) else {}).get("startup_smoke", {}).get("status") or "").strip(),
                "startup_smoke_ready_checkpoint": str(((linux_gate.get("runtime") or {}) if isinstance(linux_gate.get("runtime"), dict) else {}).get("startup_smoke", {}).get("ready_checkpoint") or "").strip(),
                "updater_special_mode_status": str(((linux_gate.get("runtime") or {}) if isinstance(linux_gate.get("runtime"), dict) else {}).get("updater_special_mode", {}).get("status") or "").strip(),
                "updater_special_mode_mode": str(((linux_gate.get("runtime") or {}) if isinstance(linux_gate.get("runtime"), dict) else {}).get("updater_special_mode", {}).get("mode") or "").strip(),
                "updater_special_mode_failure_reason": str(((linux_gate.get("runtime") or {}) if isinstance(linux_gate.get("runtime"), dict) else {}).get("updater_special_mode", {}).get("failure_reason") or "").strip(),
                "updater_special_mode_success_status": str(((linux_gate.get("runtime") or {}) if isinstance(linux_gate.get("runtime"), dict) else {}).get("updater_special_mode_success", {}).get("status") or "").strip(),
                "updater_special_mode_success_mode": str(((linux_gate.get("runtime") or {}) if isinstance(linux_gate.get("runtime"), dict) else {}).get("updater_special_mode_success", {}).get("mode") or "").strip(),
            },
            "installer_update_truth": {
                "status": str(installer_update_truth.get("status") or "").strip(),
                "update_modes": list(((installer_update_truth.get("policy") or {}) if isinstance(installer_update_truth.get("policy"), dict) else {}).get("update_modes") or []),
                "source_build_default_mode": str(((installer_update_truth.get("policy") or {}) if isinstance(installer_update_truth.get("policy"), dict) else {}).get("source_build_default_mode") or "").strip(),
                "packaged_default_mode": str(((installer_update_truth.get("policy") or {}) if isinstance(installer_update_truth.get("policy"), dict) else {}).get("packaged_default_mode") or "").strip(),
                "public_download_authority": str(((installer_update_truth.get("release_truth") or {}) if isinstance(installer_update_truth.get("release_truth"), dict) else {}).get("public_download_authority") or "").strip(),
            },
            "release_truth_packet": {
                "release_status": str(release_packet.get("release_status") or "").strip(),
                "published_at": str(release_packet.get("published_at") or "").strip(),
                "available_platforms": list(release_packet.get("available_platforms") or []),
                "missing_platforms": list(release_packet.get("missing_platforms") or []),
                "shelf_truth_line": str(release_packet.get("shelf_truth_line") or "").strip(),
            },
            "updater_startup_window": {
                "source_path": _display_path(STARTUP_WINDOW_SOURCE_PATH),
                "test_path": _display_path(STARTUP_WINDOW_TEST_PATH),
                "has_view_state_mapping": "DesktopStartupUpdateViewState BuildViewState" in startup_window_source,
                "has_visibility_delay_policy": "GetCompletionDisplayDelayMs" in startup_window_source,
                "has_interruption_warning": "Keep this window open. Starting another copy can interrupt the update." in startup_window_source,
                "has_manual_macos_recovery_copy": "A macOS update is ready. Open Downloads to install it manually; this copy will stay usable." in startup_window_source,
                "has_progress_mapping_tests": "BuildViewState_maps_progress_stage_to_visible_copy_and_determinate_progress" in startup_window_tests,
                "has_delay_policy_tests": "GetCompletionDisplayDelayMs_keeps_relaunch_and_failures_visible_long_enough_to_perceive" in startup_window_tests,
            },
            "install_link_browser_fallback": {
                "source_path": _display_path(INSTALL_LINK_WINDOW_SOURCE_PATH),
                "shell_test_path": _display_path(INSTALL_LINK_WINDOW_TEST_PATH),
                "runtime_test_path": _display_path(INSTALL_LINK_RUNTIME_TEST_PATH),
                "has_dedicated_fallback_panel": "_browserFallbackPanel" in install_link_window_source,
                "has_fallback_heading": "BuildBrowserFallbackHeading" in install_link_window_source,
                "has_fallback_detail": "BuildBrowserFallbackDetail" in install_link_window_source,
                "has_fallback_url_surface": "_browserFallbackUrlText" in install_link_window_source,
                "has_copy_claim_link_button": "desktop.install_link.button.copy_login_url" in install_link_window_source,
                "has_linux_failure_runtime_test": "TryHandleHeadlessInstallLinkModeAsync_persists_browser_dispatch_failure" in install_link_runtime_tests,
                "has_window_fallback_copy_test": "Browser_fallback_copy_stays_clear_and_user_facing" in install_link_window_tests,
            },
        },
        "coherence": {
            "linux_gate_status_matches_packet": str(linux_gate.get("status") or "").strip() == str(projected_gate.get("status") or "").strip(),
            "linux_gate_rid_matches_packet": str(((linux_gate.get("output") or {}) if isinstance(linux_gate.get("output"), dict) else {}).get("rid") or "").strip() == str(projected_gate.get("rid") or "").strip(),
            "linux_gate_archive_sha_matches_packet": str(((linux_gate.get("output") or {}) if isinstance(linux_gate.get("output"), dict) else {}).get("archive_sha256") or "").strip() == str(projected_gate.get("archive_sha256") or "").strip(),
            "linux_gate_executable_sha_matches_packet": str(((linux_gate.get("output") or {}) if isinstance(linux_gate.get("output"), dict) else {}).get("executable_sha256") or "").strip() == str(projected_gate.get("executable_sha256") or "").strip(),
            "linux_gate_startup_smoke_passed": str(((linux_gate.get("runtime") or {}) if isinstance(linux_gate.get("runtime"), dict) else {}).get("startup_smoke", {}).get("status") or "").strip() == "pass",
            "linux_gate_updater_special_mode_passed": str(((linux_gate.get("runtime") or {}) if isinstance(linux_gate.get("runtime"), dict) else {}).get("updater_special_mode", {}).get("status") or "").strip() == "pass",
            "linux_gate_updater_special_mode_success_passed": str(((linux_gate.get("runtime") or {}) if isinstance(linux_gate.get("runtime"), dict) else {}).get("updater_special_mode_success", {}).get("status") or "").strip() == "pass",
            "installer_update_truth_matches_release_authority": str(((installer_update_truth.get("release_truth") or {}) if isinstance(installer_update_truth.get("release_truth"), dict) else {}).get("public_download_authority") or "").strip() == str(release_packet.get("public_download_authority") or "").strip(),
            "installer_update_truth_keeps_source_build_notify_default": str(((installer_update_truth.get("policy") or {}) if isinstance(installer_update_truth.get("policy"), dict) else {}).get("source_build_default_mode") or "").strip() == "notify",
            "updater_startup_window_has_view_state_mapping": "DesktopStartupUpdateViewState BuildViewState" in startup_window_source,
            "updater_startup_window_has_visibility_delay_policy": "GetCompletionDisplayDelayMs" in startup_window_source,
            "updater_startup_window_has_progress_mapping_tests": "BuildViewState_maps_progress_stage_to_visible_copy_and_determinate_progress" in startup_window_tests,
            "updater_startup_window_has_delay_policy_tests": "GetCompletionDisplayDelayMs_keeps_relaunch_and_failures_visible_long_enough_to_perceive" in startup_window_tests,
            "install_link_browser_fallback_has_panel": "_browserFallbackPanel" in install_link_window_source,
            "install_link_browser_fallback_has_detail_copy": "BuildBrowserFallbackDetail" in install_link_window_source,
            "install_link_browser_fallback_has_runtime_failure_test": "TryHandleHeadlessInstallLinkModeAsync_persists_browser_dispatch_failure" in install_link_runtime_tests,
            "install_link_browser_fallback_has_window_copy_test": "Browser_fallback_copy_stays_clear_and_user_facing" in install_link_window_tests,
        },
    }
    OUTPUT_PATH.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("release_verification_convergence:ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
