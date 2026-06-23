#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RECEIPT_PATH = REPO_ROOT / ".guide-internal" / "receipts" / "RELEASE_VERIFICATION_CONVERGENCE.generated.json"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> int:
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    _require(receipt.get("contract_name") == "ea.chummer6_release_verification_convergence.v1", "unexpected contract_name")
    _require(receipt.get("status") == "passed", "release verification convergence is not passed")
    generated_at = str(receipt.get("generated_at_utc") or "").strip()
    _require(bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", generated_at)), "generated_at_utc must be ISO UTC")

    generated_from = receipt.get("generated_from")
    _require(isinstance(generated_from, list) and len(generated_from) == 3, "generated_from must list the source receipts")

    checks = receipt.get("checks")
    _require(isinstance(checks, dict), "checks block missing")
    linux_gate = checks.get("linux_source_build_gate")
    installer_update_truth = checks.get("installer_update_truth")
    release_truth_packet = checks.get("release_truth_packet")
    updater_startup_window = checks.get("updater_startup_window")
    install_link_browser_fallback = checks.get("install_link_browser_fallback")
    _require(isinstance(linux_gate, dict), "linux_source_build_gate check missing")
    _require(isinstance(installer_update_truth, dict), "installer_update_truth check missing")
    _require(isinstance(release_truth_packet, dict), "release_truth_packet check missing")
    _require(isinstance(updater_startup_window, dict), "updater_startup_window check missing")
    _require(isinstance(install_link_browser_fallback, dict), "install_link_browser_fallback check missing")
    _require(str(linux_gate.get("status") or "").strip() == "passed", "linux_source_build_gate status must be passed")
    _require(str(linux_gate.get("docker_image") or "").strip() == "debian:bookworm-slim", "linux_source_build_gate docker image mismatch")
    _require(str(linux_gate.get("rid") or "").strip().startswith("linux-"), "linux_source_build_gate rid must be linux")
    _require(str(linux_gate.get("startup_smoke_status") or "").strip() == "pass", "linux_source_build_gate startup smoke must pass")
    _require(str(linux_gate.get("startup_smoke_ready_checkpoint") or "").strip() == "fresh_container_gate", "linux_source_build_gate startup smoke checkpoint mismatch")
    _require(str(linux_gate.get("updater_special_mode_status") or "").strip() == "pass", "linux_source_build_gate updater special-mode smoke must pass")
    _require(str(linux_gate.get("updater_special_mode_mode") or "").strip() == "desktop_update_launch_installer", "linux_source_build_gate updater special-mode mode mismatch")
    _require(str(linux_gate.get("updater_special_mode_failure_reason") or "").strip() == "installer_launch_failed", "linux_source_build_gate updater special-mode failure reason mismatch")
    _require(str(linux_gate.get("updater_special_mode_success_status") or "").strip() == "pass", "linux_source_build_gate updater success special-mode smoke must pass")
    _require(str(linux_gate.get("updater_special_mode_success_mode") or "").strip() == "desktop_update_launch_installer_success", "linux_source_build_gate updater success special-mode mode mismatch")
    _require(str(installer_update_truth.get("status") or "").strip() == "passed", "installer_update_truth status must be passed")
    _require(installer_update_truth.get("update_modes") == ["full", "notify", "off"], "installer_update_truth update_modes mismatch")
    _require(str(installer_update_truth.get("source_build_default_mode") or "").strip() == "notify", "installer_update_truth source-build default must be notify")
    _require(str(installer_update_truth.get("packaged_default_mode") or "").strip() == "full", "installer_update_truth packaged default must be full")
    _require(str(installer_update_truth.get("public_download_authority") or "").strip() == "https://chummer.run/downloads", "installer_update_truth public download authority mismatch")
    _require(str(release_truth_packet.get("release_status") or "").strip(), "release_truth_packet release_status missing")
    _require(isinstance(release_truth_packet.get("available_platforms"), list), "release_truth_packet available_platforms missing")
    _require(updater_startup_window.get("has_view_state_mapping") is True, "updater_startup_window must expose a deterministic view-state mapping")
    _require(updater_startup_window.get("has_visibility_delay_policy") is True, "updater_startup_window must expose a deterministic visibility delay policy")
    _require(updater_startup_window.get("has_interruption_warning") is True, "updater_startup_window interruption warning missing")
    _require(updater_startup_window.get("has_manual_macos_recovery_copy") is True, "updater_startup_window macOS recovery copy missing")
    _require(updater_startup_window.get("has_progress_mapping_tests") is True, "updater_startup_window progress mapping tests missing")
    _require(updater_startup_window.get("has_delay_policy_tests") is True, "updater_startup_window delay policy tests missing")
    _require(install_link_browser_fallback.get("has_dedicated_fallback_panel") is True, "install_link_browser_fallback dedicated panel missing")
    _require(install_link_browser_fallback.get("has_fallback_heading") is True, "install_link_browser_fallback heading missing")
    _require(install_link_browser_fallback.get("has_fallback_detail") is True, "install_link_browser_fallback detail copy missing")
    _require(install_link_browser_fallback.get("has_fallback_url_surface") is True, "install_link_browser_fallback claim-link surface missing")
    _require(install_link_browser_fallback.get("has_copy_claim_link_button") is True, "install_link_browser_fallback copy button missing")
    _require(install_link_browser_fallback.get("has_linux_failure_runtime_test") is True, "install_link_browser_fallback runtime failure test missing")
    _require(install_link_browser_fallback.get("has_window_fallback_copy_test") is True, "install_link_browser_fallback window copy test missing")

    coherence = receipt.get("coherence")
    _require(isinstance(coherence, dict), "coherence block missing")
    for key in (
        "linux_gate_status_matches_packet",
        "linux_gate_rid_matches_packet",
        "linux_gate_archive_sha_matches_packet",
        "linux_gate_executable_sha_matches_packet",
        "linux_gate_startup_smoke_passed",
        "linux_gate_updater_special_mode_passed",
        "linux_gate_updater_special_mode_success_passed",
        "installer_update_truth_matches_release_authority",
        "installer_update_truth_keeps_source_build_notify_default",
        "updater_startup_window_has_view_state_mapping",
        "updater_startup_window_has_visibility_delay_policy",
        "updater_startup_window_has_progress_mapping_tests",
        "updater_startup_window_has_delay_policy_tests",
        "install_link_browser_fallback_has_panel",
        "install_link_browser_fallback_has_detail_copy",
        "install_link_browser_fallback_has_runtime_failure_test",
        "install_link_browser_fallback_has_window_copy_test",
    ):
        _require(coherence.get(key) is True, f"{key} must be true")

    print("release_verification_convergence_receipt:ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
