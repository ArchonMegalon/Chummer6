#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RECEIPT_PATH = REPO_ROOT / ".guide-internal" / "receipts" / "LINUX_SOURCE_BUILD_DOCKER_GATE.generated.json"

HEX_64 = re.compile(r"^[0-9a-f]{64}$")
RUN_ID = re.compile(r"^\d{8}T\d{6}Z$")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _require_sha256(value: object, field_name: str) -> None:
    _require(isinstance(value, str) and bool(HEX_64.fullmatch(value)), f"{field_name} must be a 64-character lowercase SHA256 hex string")


def main() -> int:
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))

    _require(receipt.get("contract_name") == "ea.chummer6_linux_source_build_docker_gate.v1", "unexpected contract_name")
    _require(receipt.get("status") == "passed", "linux source-build docker gate did not pass")

    generated_at = receipt.get("generated_at_utc")
    _require(isinstance(generated_at, str) and bool(RUN_ID.fullmatch(generated_at)), "generated_at_utc must use the gate run-id format YYYYMMDDTHHMMSSZ")

    docker_image = receipt.get("docker_image")
    _require(isinstance(docker_image, str) and docker_image.strip(), "docker_image is missing")

    gate = receipt.get("gate")
    _require(isinstance(gate, dict), "gate block is missing")
    _require(gate.get("name") == "linux_source_build_fresh_container", "gate.name is incorrect")
    _require(gate.get("host_audit_wrapper") == "scripts/check-host-chummer6-linux.sh", "gate.host_audit_wrapper is incorrect")
    _require(gate.get("build_script") == "scripts/build-chummer6-linux.sh", "gate.build_script is incorrect")
    _require(gate.get("container_flow") == "audit_then_full_build", "gate.container_flow is incorrect")
    _require(gate.get("public_script_requires_sudo") is False, "gate.public_script_requires_sudo must be false")
    _require(gate.get("public_script_installs_system_packages") is False, "gate.public_script_installs_system_packages must be false")
    _require(gate.get("build_temp_cleanup_default") is True, "gate.build_temp_cleanup_default must be true")
    _require(gate.get("source_build_update_mode_default") == "notify", "gate.source_build_update_mode_default must be notify")

    output = receipt.get("output")
    _require(isinstance(output, dict), "output block is missing")
    _require(isinstance(output.get("rid"), str) and output["rid"].startswith("linux-"), "output.rid must be a linux RID")
    _require(output.get("binary_name") == "Chummer.Avalonia", "output.binary_name is incorrect")
    _require(output.get("launcher_name") == "run-chummer6.sh", "output.launcher_name is incorrect")
    _require(isinstance(output.get("archive_name"), str) and output["archive_name"].endswith(".tar.gz"), "output.archive_name must end with .tar.gz")
    _require_sha256(output.get("executable_sha256"), "output.executable_sha256")
    _require_sha256(output.get("archive_sha256"), "output.archive_sha256")

    artifacts = receipt.get("artifacts")
    _require(isinstance(artifacts, dict), "artifacts block is missing")
    _require(isinstance(artifacts.get("build_log_name"), str) and artifacts["build_log_name"].endswith(".log"), "artifacts.build_log_name must end with .log")
    _require(isinstance(artifacts.get("startup_smoke_receipt_name"), str) and artifacts["startup_smoke_receipt_name"].endswith(".receipt.json"), "artifacts.startup_smoke_receipt_name must end with .receipt.json")
    _require(isinstance(artifacts.get("updater_special_mode_receipt_name"), str) and artifacts["updater_special_mode_receipt_name"].endswith(".receipt.json"), "artifacts.updater_special_mode_receipt_name must end with .receipt.json")
    _require(isinstance(artifacts.get("updater_special_mode_success_receipt_name"), str) and artifacts["updater_special_mode_success_receipt_name"].endswith(".receipt.json"), "artifacts.updater_special_mode_success_receipt_name must end with .receipt.json")
    manifest_excerpt = artifacts.get("build_manifest_excerpt")
    _require(isinstance(manifest_excerpt, list) and len(manifest_excerpt) >= 5, "artifacts.build_manifest_excerpt is too small")
    source_heads = artifacts.get("source_heads")
    _require(isinstance(source_heads, dict) and source_heads, "artifacts.source_heads is missing")
    for repo_name in ("chummer6-core", "chummer6-hub", "chummer6-hub-registry", "chummer6-ui", "chummer6-ui-kit"):
        _require(repo_name in source_heads, f"source_heads is missing {repo_name}")
        _require(isinstance(source_heads[repo_name], str) and re.fullmatch(r"[0-9a-f]{40}", source_heads[repo_name]), f"source_heads[{repo_name}] must be a 40-char git SHA")

    runtime = receipt.get("runtime")
    _require(isinstance(runtime, dict), "runtime block is missing")
    startup_smoke = runtime.get("startup_smoke")
    _require(isinstance(startup_smoke, dict), "runtime.startup_smoke is missing")
    _require(str(startup_smoke.get("status") or "").strip() == "pass", "runtime.startup_smoke.status must be pass")
    _require(str(startup_smoke.get("head_id") or "").strip() == "avalonia", "runtime.startup_smoke.head_id must be avalonia")
    _require(str(startup_smoke.get("channel_id") or "").strip() == "source-build", "runtime.startup_smoke.channel_id must be source-build")
    _require(str(startup_smoke.get("rid") or "").strip() == str(output.get("rid") or "").strip(), "runtime.startup_smoke.rid must match output.rid")
    _require(str(startup_smoke.get("ready_checkpoint") or "").strip() == "fresh_container_gate", "runtime.startup_smoke.ready_checkpoint must be fresh_container_gate")
    artifact_digest = str(startup_smoke.get("artifact_digest") or "").strip()
    _require(bool(re.fullmatch(r"sha256:[0-9a-f]{64}", artifact_digest)), "runtime.startup_smoke.artifact_digest must be a sha256 digest")
    _require(str(startup_smoke.get("artifact_digest_source") or "").strip() in {"process_path", "environment"}, "runtime.startup_smoke.artifact_digest_source is invalid")
    recorded_at_utc = str(startup_smoke.get("recorded_at_utc") or "").strip()
    _require(bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?\+00:00", recorded_at_utc)), "runtime.startup_smoke.recorded_at_utc must be ISO UTC offset format")

    updater_special_mode = runtime.get("updater_special_mode")
    _require(isinstance(updater_special_mode, dict), "runtime.updater_special_mode is missing")
    _require(str(updater_special_mode.get("status") or "").strip() == "pass", "runtime.updater_special_mode.status must be pass")
    _require(str(updater_special_mode.get("mode") or "").strip() == "desktop_update_launch_installer", "runtime.updater_special_mode.mode must be desktop_update_launch_installer")
    _require(str(updater_special_mode.get("head_id") or "").strip() == "avalonia", "runtime.updater_special_mode.head_id must be avalonia")
    _require(str(updater_special_mode.get("channel_id") or "").strip() == "stable", "runtime.updater_special_mode.channel_id must be stable")
    _require(str(updater_special_mode.get("rid") or "").strip() == str(output.get("rid") or "").strip(), "runtime.updater_special_mode.rid must match output.rid")
    _require(updater_special_mode.get("exit_code") == 1, "runtime.updater_special_mode.exit_code must be 1")
    _require(updater_special_mode.get("expected_exit_code") == 1, "runtime.updater_special_mode.expected_exit_code must be 1")
    _require(str(updater_special_mode.get("failure_reason") or "").strip() == "installer_launch_failed", "runtime.updater_special_mode.failure_reason must be installer_launch_failed")
    _require("Installer payload was not found" in str(updater_special_mode.get("last_error") or ""), "runtime.updater_special_mode.last_error must mention the missing installer payload")
    _require(str(updater_special_mode.get("pending_update_version") or "").strip() == "run-20260618-051119", "runtime.updater_special_mode.pending_update_version mismatch")
    _require(str(updater_special_mode.get("pending_update_channel_id") or "").strip() == "stable", "runtime.updater_special_mode.pending_update_channel_id must be stable")
    updater_recorded_at_utc = str(updater_special_mode.get("recorded_at_utc") or "").strip()
    _require(bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?\+00:00", updater_recorded_at_utc)), "runtime.updater_special_mode.recorded_at_utc must be ISO UTC offset format")

    updater_special_mode_success = runtime.get("updater_special_mode_success")
    _require(isinstance(updater_special_mode_success, dict), "runtime.updater_special_mode_success is missing")
    _require(str(updater_special_mode_success.get("status") or "").strip() == "pass", "runtime.updater_special_mode_success.status must be pass")
    _require(str(updater_special_mode_success.get("mode") or "").strip() == "desktop_update_launch_installer_success", "runtime.updater_special_mode_success.mode must be desktop_update_launch_installer_success")
    _require(str(updater_special_mode_success.get("head_id") or "").strip() == "avalonia", "runtime.updater_special_mode_success.head_id must be avalonia")
    _require(str(updater_special_mode_success.get("channel_id") or "").strip() == "stable", "runtime.updater_special_mode_success.channel_id must be stable")
    _require(str(updater_special_mode_success.get("rid") or "").strip() == str(output.get("rid") or "").strip(), "runtime.updater_special_mode_success.rid must match output.rid")
    _require(updater_special_mode_success.get("exit_code") == 0, "runtime.updater_special_mode_success.exit_code must be 0")
    _require(updater_special_mode_success.get("expected_exit_code") == 0, "runtime.updater_special_mode_success.expected_exit_code must be 0")
    _require(str(updater_special_mode_success.get("failure_reason") or "").strip() == "", "runtime.updater_special_mode_success.failure_reason must be empty")
    _require(str(updater_special_mode_success.get("last_error") or "").strip() == "", "runtime.updater_special_mode_success.last_error must be empty")
    _require(str(updater_special_mode_success.get("pending_update_version") or "").strip() == "", "runtime.updater_special_mode_success.pending_update_version must be cleared")
    _require(str(updater_special_mode_success.get("pending_update_channel_id") or "").strip() == "", "runtime.updater_special_mode_success.pending_update_channel_id must be cleared")
    _require(updater_special_mode_success.get("dpkg_invoked") is True, "runtime.updater_special_mode_success.dpkg_invoked must be true")
    _require(updater_special_mode_success.get("stage_deleted") is True, "runtime.updater_special_mode_success.stage_deleted must be true")
    updater_success_recorded_at_utc = str(updater_special_mode_success.get("recorded_at_utc") or "").strip()
    _require(bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?\+00:00", updater_success_recorded_at_utc)), "runtime.updater_special_mode_success.recorded_at_utc must be ISO UTC offset format")

    print("linux_source_build_docker_gate_receipt:ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
