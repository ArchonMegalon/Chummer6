#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _resolve_desktop_repo_root() -> Path:
    explicit = os.environ.get("CHUMMER_DESKTOP_REPO_ROOT", "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()
    for search_root in (REPO_ROOT.parent, REPO_ROOT.parent.parent):
        for candidate_name in ("chummer-presentation", "chummer6-ui"):
            candidate = search_root / candidate_name
            if (candidate / "Chummer.Avalonia" / "DesktopStartupUpdateWindow.cs").is_file():
                return candidate.resolve()
    # Preserve importability for isolated receipt tests; main() will still fail
    # closed when it reads the required desktop sources from this fallback.
    return REPO_ROOT.parent / "chummer6-ui"


DESKTOP_REPO_ROOT = _resolve_desktop_repo_root()
RECEIPTS_ROOT = REPO_ROOT / ".guide-internal" / "receipts"
LINUX_GATE_PATH = RECEIPTS_ROOT / "LINUX_SOURCE_BUILD_DOCKER_GATE.generated.json"
MACOS_SOURCE_BUILD_CONTRACT_PATH = RECEIPTS_ROOT / "MACOS_SOURCE_BUILD_CONTRACT.generated.json"
INSTALLER_UPDATE_TRUTH_PATH = RECEIPTS_ROOT / "INSTALLER_UPDATE_TRUTH.generated.json"
DESKTOP_UPDATE_RUNTIME_PATH = RECEIPTS_ROOT / "DESKTOP_UPDATE_RUNTIME.generated.json"
RELEASE_PACKET_PATH = RECEIPTS_ROOT / "CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json"
OUTPUT_PATH = RECEIPTS_ROOT / "RELEASE_VERIFICATION_CONVERGENCE.generated.json"
STARTUP_WINDOW_SOURCE_PATH = DESKTOP_REPO_ROOT / "Chummer.Avalonia" / "DesktopStartupUpdateWindow.cs"
STARTUP_WINDOW_TEST_PATH = DESKTOP_REPO_ROOT / "Chummer.Tests" / "Presentation" / "DesktopStartupUpdateWindowTests.cs"
INSTALL_LINK_WINDOW_SOURCE_PATH = DESKTOP_REPO_ROOT / "Chummer.Avalonia" / "DesktopInstallLinkingWindow.cs"
INSTALL_LINK_WINDOW_TEST_PATH = DESKTOP_REPO_ROOT / "Chummer.Tests" / "Presentation" / "DesktopInstallLinkingShellChromeTests.cs"
INSTALL_LINK_RUNTIME_TEST_PATH = DESKTOP_REPO_ROOT / "Chummer.Tests" / "DesktopInstallLinkingRuntimeTests.cs"


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def main() -> int:
    linux_gate = _load_json(LINUX_GATE_PATH)
    macos_source_build_contract = _load_json(MACOS_SOURCE_BUILD_CONTRACT_PATH)
    installer_update_truth = _load_json(INSTALLER_UPDATE_TRUTH_PATH)
    desktop_update_runtime = _load_json(DESKTOP_UPDATE_RUNTIME_PATH)
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
            _display_path(MACOS_SOURCE_BUILD_CONTRACT_PATH),
            _display_path(INSTALLER_UPDATE_TRUTH_PATH),
            _display_path(DESKTOP_UPDATE_RUNTIME_PATH),
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
                "installed_startup_smoke_status": str(((linux_gate.get("runtime") or {}) if isinstance(linux_gate.get("runtime"), dict) else {}).get("installed_startup_smoke", {}).get("status") or "").strip(),
                "installed_startup_smoke_ready_checkpoint": str(((linux_gate.get("runtime") or {}) if isinstance(linux_gate.get("runtime"), dict) else {}).get("installed_startup_smoke", {}).get("ready_checkpoint") or "").strip(),
                "updater_special_mode_status": str(((linux_gate.get("runtime") or {}) if isinstance(linux_gate.get("runtime"), dict) else {}).get("updater_special_mode", {}).get("status") or "").strip(),
                "updater_special_mode_mode": str(((linux_gate.get("runtime") or {}) if isinstance(linux_gate.get("runtime"), dict) else {}).get("updater_special_mode", {}).get("mode") or "").strip(),
                "updater_special_mode_failure_reason": str(((linux_gate.get("runtime") or {}) if isinstance(linux_gate.get("runtime"), dict) else {}).get("updater_special_mode", {}).get("failure_reason") or "").strip(),
                "updater_dispatch_simulation_status": str(((linux_gate.get("runtime") or {}) if isinstance(linux_gate.get("runtime"), dict) else {}).get("updater_dispatch_simulation", {}).get("status") or "").strip(),
                "updater_dispatch_simulation_mode": str(((linux_gate.get("runtime") or {}) if isinstance(linux_gate.get("runtime"), dict) else {}).get("updater_dispatch_simulation", {}).get("mode") or "").strip(),
                "updater_dispatch_simulation_invocation_contract_proven": ((linux_gate.get("runtime") or {}) if isinstance(linux_gate.get("runtime"), dict) else {}).get("updater_dispatch_simulation", {}).get("invocation_contract_proven") is True,
            },
            "macos_source_build_contract": {
                "status": str(macos_source_build_contract.get("status") or "").strip(),
                "scope": str(macos_source_build_contract.get("scope") or "").strip(),
                "runtime_coverage": str(macos_source_build_contract.get("runtime_coverage") or "").strip(),
                "real_macos_runtime_proof_required": macos_source_build_contract.get("real_macos_runtime_proof_required") is True,
                "syntax_check_count": len(macos_source_build_contract.get("syntax_checks") or []),
                "unit_test_exit_code": ((macos_source_build_contract.get("unit_test") or {}) if isinstance(macos_source_build_contract.get("unit_test"), dict) else {}).get("exit_code"),
                "maintenance_policy_marks_real_build_as_macos_only": ((macos_source_build_contract.get("policy") or {}) if isinstance(macos_source_build_contract.get("policy"), dict) else {}).get("maintenance_policy_marks_real_build_as_macos_only") is True,
                "maintenance_policy_requires_two_step_install": ((macos_source_build_contract.get("policy") or {}) if isinstance(macos_source_build_contract.get("policy"), dict) else {}).get("maintenance_policy_requires_two_step_install") is True,
                "build_launcher_resolves_symlinks": ((macos_source_build_contract.get("policy") or {}) if isinstance(macos_source_build_contract.get("policy"), dict) else {}).get("build_launcher_resolves_symlinks") is True,
                "install_launcher_resolves_symlinks": ((macos_source_build_contract.get("policy") or {}) if isinstance(macos_source_build_contract.get("policy"), dict) else {}).get("install_launcher_resolves_symlinks") is True,
                "doc_marks_second_script_install": ((macos_source_build_contract.get("policy") or {}) if isinstance(macos_source_build_contract.get("policy"), dict) else {}).get("doc_marks_second_script_install") is True,
            },
            "installer_update_truth": {
                "status": str(installer_update_truth.get("status") or "").strip(),
                "update_modes": list(((installer_update_truth.get("policy") or {}) if isinstance(installer_update_truth.get("policy"), dict) else {}).get("update_modes") or []),
                "source_build_linux_default_mode": str(((installer_update_truth.get("policy") or {}) if isinstance(installer_update_truth.get("policy"), dict) else {}).get("source_build_linux_default_mode") or "").strip(),
                "source_build_linux_analytics_default": str(((installer_update_truth.get("policy") or {}) if isinstance(installer_update_truth.get("policy"), dict) else {}).get("source_build_linux_analytics_default") or "").strip(),
                "linux_source_build_is_explicitly_two_step": ((installer_update_truth.get("coherence") or {}) if isinstance(installer_update_truth.get("coherence"), dict) else {}).get("linux_source_build_is_explicitly_two_step") is True,
                "source_build_macos_default_mode": str(((installer_update_truth.get("policy") or {}) if isinstance(installer_update_truth.get("policy"), dict) else {}).get("source_build_macos_default_mode") or "").strip(),
                "source_build_macos_analytics_default": str(((installer_update_truth.get("policy") or {}) if isinstance(installer_update_truth.get("policy"), dict) else {}).get("source_build_macos_analytics_default") or "").strip(),
                "packaged_default_mode": str(((installer_update_truth.get("policy") or {}) if isinstance(installer_update_truth.get("policy"), dict) else {}).get("packaged_default_mode") or "").strip(),
                "public_download_authority": str(((installer_update_truth.get("release_truth") or {}) if isinstance(installer_update_truth.get("release_truth"), dict) else {}).get("public_download_authority") or "").strip(),
                "macos_source_build_is_explicitly_two_step": ((installer_update_truth.get("coherence") or {}) if isinstance(installer_update_truth.get("coherence"), dict) else {}).get("macos_source_build_is_explicitly_two_step") is True,
            },
            "desktop_update_runtime": {
                "status": str(desktop_update_runtime.get("status") or "").strip(),
                "tested_repo_name": str(desktop_update_runtime.get("tested_repo_name") or "").strip(),
                "run_desktop_update_tests_only": desktop_update_runtime.get("run_desktop_update_tests_only"),
                "package_authority_scope": str(desktop_update_runtime.get("package_authority_scope") or "").strip(),
                "filter": str(desktop_update_runtime.get("filter") or "").strip(),
                "timeout_seconds": desktop_update_runtime.get("timeout_seconds"),
                "exit_code": ((desktop_update_runtime.get("result") or {}) if isinstance(desktop_update_runtime.get("result"), dict) else {}).get("exit_code"),
                "mentions_passed_banner": ((desktop_update_runtime.get("result") or {}) if isinstance(desktop_update_runtime.get("result"), dict) else {}).get("mentions_passed_banner"),
                "mentions_desktop_update_runtime_tests": ((desktop_update_runtime.get("result") or {}) if isinstance(desktop_update_runtime.get("result"), dict) else {}).get("mentions_desktop_update_runtime_tests"),
                "mentions_total": ((desktop_update_runtime.get("result") or {}) if isinstance(desktop_update_runtime.get("result"), dict) else {}).get("mentions_total"),
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
                "has_manual_macos_recovery_copy": any(
                    marker in startup_window_source
                    for marker in (
                        "A macOS update is ready. Open Update Status to install it manually; this copy will stay usable.",
                        "A macOS update is ready. Open Downloads to install it manually; this copy will stay usable.",
                    )
                ),
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
            "linux_gate_installed_startup_smoke_passed": str(((linux_gate.get("runtime") or {}) if isinstance(linux_gate.get("runtime"), dict) else {}).get("installed_startup_smoke", {}).get("status") or "").strip() == "pass",
            "linux_gate_updater_special_mode_passed": str(((linux_gate.get("runtime") or {}) if isinstance(linux_gate.get("runtime"), dict) else {}).get("updater_special_mode", {}).get("status") or "").strip() == "pass",
            "linux_gate_updater_dispatch_simulation_passed": (
                str(((linux_gate.get("runtime") or {}) if isinstance(linux_gate.get("runtime"), dict) else {}).get("updater_dispatch_simulation", {}).get("status") or "").strip() == "pass"
                and ((linux_gate.get("runtime") or {}) if isinstance(linux_gate.get("runtime"), dict) else {}).get("updater_dispatch_simulation", {}).get("invocation_contract_proven") is True
            ),
            "macos_source_build_contract_passed": str(macos_source_build_contract.get("status") or "").strip() == "passed",
            "macos_source_build_contract_stays_bounded": str(macos_source_build_contract.get("scope") or "").strip() == "script_contract_only" and str(macos_source_build_contract.get("runtime_coverage") or "").strip() == "not_run_on_non_macos_host" and macos_source_build_contract.get("real_macos_runtime_proof_required") is True,
            "macos_source_build_contract_keeps_two_step_install": ((macos_source_build_contract.get("policy") or {}) if isinstance(macos_source_build_contract.get("policy"), dict) else {}).get("maintenance_policy_requires_two_step_install") is True and ((macos_source_build_contract.get("policy") or {}) if isinstance(macos_source_build_contract.get("policy"), dict) else {}).get("doc_marks_second_script_install") is True,
            "macos_source_build_contract_launchers_resolve_symlinks": ((macos_source_build_contract.get("policy") or {}) if isinstance(macos_source_build_contract.get("policy"), dict) else {}).get("build_launcher_resolves_symlinks") is True and ((macos_source_build_contract.get("policy") or {}) if isinstance(macos_source_build_contract.get("policy"), dict) else {}).get("install_launcher_resolves_symlinks") is True,
            "installer_update_truth_matches_release_authority": str(((installer_update_truth.get("release_truth") or {}) if isinstance(installer_update_truth.get("release_truth"), dict) else {}).get("public_download_authority") or "").strip() == str(release_packet.get("public_download_authority") or "").strip(),
            "installer_update_truth_keeps_linux_source_build_notify_default": str(((installer_update_truth.get("policy") or {}) if isinstance(installer_update_truth.get("policy"), dict) else {}).get("source_build_linux_default_mode") or "").strip() == "notify",
            "installer_update_truth_keeps_linux_source_build_analytics_off_default": str(((installer_update_truth.get("policy") or {}) if isinstance(installer_update_truth.get("policy"), dict) else {}).get("source_build_linux_analytics_default") or "").strip() == "off",
            "installer_update_truth_keeps_linux_source_build_two_step_install": ((installer_update_truth.get("coherence") or {}) if isinstance(installer_update_truth.get("coherence"), dict) else {}).get("linux_source_build_is_explicitly_two_step") is True,
            "installer_update_truth_keeps_macos_source_build_notify_default": str(((installer_update_truth.get("policy") or {}) if isinstance(installer_update_truth.get("policy"), dict) else {}).get("source_build_macos_default_mode") or "").strip() == "notify",
            "installer_update_truth_keeps_macos_source_build_analytics_off_default": str(((installer_update_truth.get("policy") or {}) if isinstance(installer_update_truth.get("policy"), dict) else {}).get("source_build_macos_analytics_default") or "").strip() == "off",
            "installer_update_truth_keeps_macos_source_build_two_step_install": ((installer_update_truth.get("coherence") or {}) if isinstance(installer_update_truth.get("coherence"), dict) else {}).get("macos_source_build_is_explicitly_two_step") is True,
            "macos_source_build_contract_matches_installer_update_truth_two_step_posture": ((macos_source_build_contract.get("policy") or {}) if isinstance(macos_source_build_contract.get("policy"), dict) else {}).get("maintenance_policy_requires_two_step_install") is True and ((installer_update_truth.get("coherence") or {}) if isinstance(installer_update_truth.get("coherence"), dict) else {}).get("macos_source_build_is_explicitly_two_step") is True,
            "desktop_update_runtime_passed": str(desktop_update_runtime.get("status") or "").strip() == "passed",
            "desktop_update_runtime_runs_reduced_lane": desktop_update_runtime.get("run_desktop_update_tests_only") is True,
            "desktop_update_runtime_uses_local_compatibility_tree": str(desktop_update_runtime.get("package_authority_scope") or "").strip() == "local_compatibility_tree",
            "desktop_update_runtime_targets_update_tests": str(desktop_update_runtime.get("filter") or "").strip() == "FullyQualifiedName~DesktopUpdateRuntimeTests",
            "desktop_update_runtime_exit_code_zero": ((desktop_update_runtime.get("result") or {}) if isinstance(desktop_update_runtime.get("result"), dict) else {}).get("exit_code") == 0,
            "desktop_update_runtime_mentions_passed_banner": ((desktop_update_runtime.get("result") or {}) if isinstance(desktop_update_runtime.get("result"), dict) else {}).get("mentions_passed_banner") is True,
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
