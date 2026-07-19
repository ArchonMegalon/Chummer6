#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
RECEIPT_PATH = REPO_ROOT / ".guide-internal" / "receipts" / "LINUX_SOURCE_BUILD_DOCKER_GATE.generated.json"
RELEASE_LOCK_PATH = REPO_ROOT / "RELEASE.lock.json"

HEX_40 = re.compile(r"^[0-9a-f]{40}$")
HEX_64 = re.compile(r"^[0-9a-f]{64}$")
RUN_ID = re.compile(r"^\d{8}T\d{6}Z$")
PYTHON_VERSION = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
ISO_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?\+00:00$")
WINDOWS_DRIVE_PATH = re.compile(r"(?i)(?:^|[^a-z0-9])(?:[a-z]:[\\/])")
WINDOWS_UNC_PATH = re.compile(r"\\\\[^\\/\s]+[\\/][^\\/\s]+")
UNIX_USER_HOME = re.compile(r"(?:^|[\s\"'=])/(?:home|Users)/[^/\s]+(?:/|$)")
FORBIDDEN_PATH_MARKERS = (
    "/tmp/",
    "/var/tmp/",
    "/docker/",
    "/workspace/",
    "/work/",
    "/repo/",
    "/root/",
)
PROOF_PRODUCER_PATHS = {
    "docker_gate_script": "scripts/verify_linux_source_build_docker_gate.sh",
    "host_audit_wrapper": "scripts/check-host-chummer6-linux.sh",
    "build_script": "scripts/build-chummer6-linux.sh",
    "package_composer": "scripts/materialize_linux_package_plane.py",
    "install_script": "scripts/install-chummer6-linux-local.sh",
    "identity_validator": "scripts/validate_linux_source_build_gate_identity.sh",
    "source_lock_verifier": "scripts/verify_linux_source_lock.py",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _require_dict(value: object, field_name: str) -> dict[str, Any]:
    _require(isinstance(value, dict), f"{field_name} must be an object")
    return value


def _require_exact_keys(value: dict[str, Any], expected: set[str], field_name: str) -> None:
    _require(set(value) == expected, f"{field_name} property set differs from the v2 contract")


def _require_sha256(value: object, field_name: str) -> str:
    _require(
        isinstance(value, str) and bool(HEX_64.fullmatch(value)),
        f"{field_name} must be a 64-character lowercase SHA256 hex string",
    )
    return value


def _require_python_version(value: object, field_name: str) -> str:
    _require(isinstance(value, str), f"{field_name} must be a Python version")
    match = PYTHON_VERSION.fullmatch(value)
    _require(match is not None, f"{field_name} must use major.minor.patch")
    assert match is not None
    major, minor, _patch = (int(part) for part in match.groups())
    _require(major == 3 and minor >= 11, f"{field_name} must satisfy >=3.11,<4")
    return value


def _require_recorded_at(value: object, field_name: str) -> None:
    _require(
        isinstance(value, str) and bool(ISO_UTC.fullmatch(value)),
        f"{field_name} must use ISO UTC offset format",
    )


def _require_portable(value: object, field_name: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            _require_portable(item, f"{field_name}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _require_portable(item, f"{field_name}[{index}]")
        return
    if not isinstance(value, str):
        return
    _require(
        not any(marker in value for marker in FORBIDDEN_PATH_MARKERS),
        f"{field_name} contains a machine-local path marker",
    )
    _require(not WINDOWS_DRIVE_PATH.search(value), f"{field_name} contains a Windows absolute path")
    _require(not WINDOWS_UNC_PATH.search(value), f"{field_name} contains a Windows UNC path")
    _require(not UNIX_USER_HOME.search(value), f"{field_name} contains a user-home path")


def _current_proof_producers() -> dict[str, dict[str, str]]:
    producers: dict[str, dict[str, str]] = {}
    root = REPO_ROOT.resolve()
    for name, relative in PROOF_PRODUCER_PATHS.items():
        candidate = REPO_ROOT / relative
        _require(
            not candidate.is_symlink() and candidate.is_file(),
            f"current proof producer is missing or unsafe: {relative}",
        )
        try:
            candidate.resolve().relative_to(root)
        except ValueError as exc:
            raise ValueError(f"current proof producer escapes repository root: {relative}") from exc
        producers[name] = {
            "path": relative,
            "sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
        }
    return producers


def _load_lock_authority() -> tuple[str, dict[str, Any], dict[str, str]]:
    lock_bytes = RELEASE_LOCK_PATH.read_bytes()
    lock = _require_dict(json.loads(lock_bytes), "RELEASE.lock.json")
    repositories = lock.get("repositories")
    _require(isinstance(repositories, list) and repositories, "RELEASE.lock.json repositories are missing")
    source_heads: dict[str, str] = {}
    for item in repositories:
        repository = _require_dict(item, "RELEASE.lock.json repository")
        directory = repository.get("directory")
        commit = repository.get("commit")
        _require(isinstance(directory, str) and directory, "locked repository directory is missing")
        _require(isinstance(commit, str) and bool(HEX_40.fullmatch(commit)), "locked repository commit is invalid")
        _require(directory not in source_heads, f"duplicate locked repository directory: {directory}")
        source_heads[directory] = commit
    return hashlib.sha256(lock_bytes).hexdigest(), lock, source_heads


def _load_sdk_authority(lock: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    dotnet = _require_dict(lock.get("dotnet"), "RELEASE.lock.json dotnet")
    descriptor = _require_dict(dotnet.get("authority"), "RELEASE.lock.json dotnet.authority")
    _require_exact_keys(descriptor, {"path", "sha256"}, "RELEASE.lock.json dotnet.authority")
    relative = descriptor.get("path")
    _require(isinstance(relative, str), "SDK authority path is missing")
    pure_parts = Path(relative).parts
    _require(
        relative.startswith("release-locks/") and ".." not in pure_parts,
        "SDK authority path is not canonical",
    )
    authority_path = REPO_ROOT / relative
    authority_bytes = authority_path.read_bytes()
    _require(
        hashlib.sha256(authority_bytes).hexdigest() == descriptor.get("sha256"),
        "SDK authority bytes differ from RELEASE.lock.json",
    )
    authority = _require_dict(json.loads(authority_bytes), "SDK archive authority")
    _require(authority.get("sdkVersion") == dotnet.get("sdkVersion"), "SDK authority version differs")
    archives = authority.get("archives")
    _require(isinstance(archives, list), "SDK authority archives are missing")
    matches = [row for row in archives if isinstance(row, dict) and row.get("rid") == "linux-x64"]
    _require(len(matches) == 1, "SDK authority must contain one linux-x64 archive")
    return descriptor, matches[0]


def _parse_manifest_excerpt(value: object) -> dict[str, str]:
    _require(isinstance(value, list) and value, "artifacts.build_manifest_excerpt is missing")
    fields: dict[str, str] = {}
    for row in value:
        _require(isinstance(row, str) and "=" in row, "build manifest contains a non-canonical row")
        key, field_value = row.split("=", 1)
        _require(bool(key) and key not in fields, "build manifest contains a duplicate or empty key")
        fields[key] = field_value
    return fields


def _verify_startup_runtime(
    value: object,
    *,
    field_name: str,
    output_rid: str,
    executable_sha256: str,
    ready_checkpoint: str,
) -> None:
    runtime = _require_dict(value, field_name)
    _require_exact_keys(
        runtime,
        {
            "status",
            "head_id",
            "channel_id",
            "rid",
            "ready_checkpoint",
            "artifact_digest",
            "artifact_digest_source",
            "recorded_at_utc",
        },
        field_name,
    )
    _require(runtime["status"] == "pass", f"{field_name}.status must be pass")
    _require(runtime["head_id"] == "avalonia", f"{field_name}.head_id must be avalonia")
    _require(runtime["channel_id"] == "local", f"{field_name}.channel_id must be local")
    _require(runtime["rid"] == output_rid, f"{field_name}.rid must match output.rid")
    _require(runtime["ready_checkpoint"] == ready_checkpoint, f"{field_name}.ready_checkpoint is incorrect")
    _require(
        runtime["artifact_digest"] == f"sha256:{executable_sha256}",
        f"{field_name}.artifact_digest must bind output.executable_sha256",
    )
    _require(runtime["artifact_digest_source"] == "process_path", f"{field_name}.artifact_digest_source must be process_path")
    _require_recorded_at(runtime["recorded_at_utc"], f"{field_name}.recorded_at_utc")


def verify(receipt_value: object) -> None:
    receipt = _require_dict(receipt_value, "receipt")
    _require_portable(receipt, "receipt")
    _require_exact_keys(
        receipt,
        {
            "contract_name",
            "status",
            "execution_mode",
            "generated_at_utc",
            "docker_image",
            "source_mode",
            "source_lock",
            "source_lock_sha256",
            "git_ref",
            "release_manifest_status",
            "release_manifest_sha256",
            "release_evidence_eligible",
            "github_org",
            "repo_base_url",
            "proof_producers",
            "runtime_authority",
            "gate",
            "output",
            "reproducibility",
            "artifacts",
            "runtime",
        },
        "receipt",
    )
    _require(receipt["contract_name"] == "ea.chummer6_linux_source_build_docker_gate.v2", "unexpected contract_name")
    _require(receipt["status"] == "passed", "linux source-build docker gate did not pass")
    _require(receipt["execution_mode"] == "fresh_container", "receipt must come from fresh_container execution")
    _require(receipt["source_mode"] == "locked", "source_mode must be locked")
    _require(receipt["source_lock"] == "RELEASE.lock.json", "source_lock must be RELEASE.lock.json")
    _require(receipt["git_ref"] is None, "git_ref must be null for the locked v2 gate")
    _require(receipt["release_evidence_eligible"] is False, "release_evidence_eligible must remain false")
    _require(receipt["github_org"] == "ArchonMegalon", "github_org is incorrect")
    _require(receipt["repo_base_url"] == "https://github.com/ArchonMegalon", "repo_base_url must be the canonical authority")

    proof_producers = _require_dict(receipt["proof_producers"], "proof_producers")
    _require_exact_keys(proof_producers, set(PROOF_PRODUCER_PATHS), "proof_producers")
    for name, descriptor_value in proof_producers.items():
        descriptor = _require_dict(descriptor_value, f"proof_producers.{name}")
        _require_exact_keys(descriptor, {"path", "sha256"}, f"proof_producers.{name}")
        _require_sha256(descriptor["sha256"], f"proof_producers.{name}.sha256")
    expected_proof_producers = _current_proof_producers()
    _require(
        proof_producers == expected_proof_producers,
        "proof_producers differ from current checked producer bytes",
    )

    generated_at = receipt["generated_at_utc"]
    _require(isinstance(generated_at, str) and bool(RUN_ID.fullmatch(generated_at)), "generated_at_utc must use YYYYMMDDTHHMMSSZ")
    _require(receipt["docker_image"] == "debian:bookworm-slim", "docker_image must be the pinned gate image")

    lock_sha256, release_lock, expected_source_heads = _load_lock_authority()
    _require(receipt["source_lock_sha256"] == lock_sha256, "source_lock_sha256 does not match checked-in RELEASE.lock.json bytes")
    locked_source_verifier = _require_dict(
        release_lock.get("sourceLockVerifier"),
        "RELEASE.lock.json sourceLockVerifier",
    )
    _require_exact_keys(
        locked_source_verifier,
        {"path", "sha256"},
        "RELEASE.lock.json sourceLockVerifier",
    )
    _require(
        locked_source_verifier == expected_proof_producers["source_lock_verifier"],
        "RELEASE.lock.json does not bind the current source-lock verifier bytes",
    )
    locked_build_script = _require_dict(
        release_lock.get("buildScript"),
        "RELEASE.lock.json buildScript",
    )
    _require_exact_keys(
        locked_build_script,
        {"path", "sha256"},
        "RELEASE.lock.json buildScript",
    )
    _require(
        locked_build_script == expected_proof_producers["build_script"],
        "RELEASE.lock.json does not bind the current source-build script bytes",
    )
    package_plane = _require_dict(
        release_lock.get("packagePlane"),
        "RELEASE.lock.json packagePlane",
    )
    locked_composer = _require_dict(
        package_plane.get("composer"),
        "RELEASE.lock.json packagePlane.composer",
    )
    _require_exact_keys(
        locked_composer,
        {"path", "sha256", "normalizationContract"},
        "RELEASE.lock.json packagePlane.composer",
    )
    _require(
        {
            "path": locked_composer["path"],
            "sha256": locked_composer["sha256"],
        }
        == expected_proof_producers["package_composer"],
        "RELEASE.lock.json does not bind the current package-composer bytes",
    )
    release_manifest = _require_dict(release_lock.get("releaseManifest"), "RELEASE.lock.json releaseManifest")
    _require(receipt["release_manifest_status"] == release_manifest.get("status"), "release_manifest_status differs from RELEASE.lock.json")
    _require(receipt["release_manifest_sha256"] == release_manifest.get("sha256"), "release_manifest_sha256 differs from RELEASE.lock.json")
    _require_sha256(receipt["release_manifest_sha256"], "release_manifest_sha256")

    sdk_descriptor, sdk_archive = _load_sdk_authority(release_lock)
    runtime_authority = _require_dict(receipt["runtime_authority"], "runtime_authority")
    _require_exact_keys(
        runtime_authority,
        {
            "status",
            "source_lock",
            "rid",
            "sdk_version",
            "authority_path",
            "authority_sha256",
            "archive_url",
            "archive_name",
            "archive_sha256",
            "archive_sha512",
            "archive_size_bytes",
            "dotnet_root_mode",
            "dotnet_root_x64_bound",
            "dotnet_host_path_bound",
            "path_precedence",
            "multilevel_lookup",
            "system_runtime_fallback_allowed",
            "archive_reused_by_clean_builds",
        },
        "runtime_authority",
    )
    dotnet = _require_dict(release_lock.get("dotnet"), "RELEASE.lock.json dotnet")
    expected_runtime_authority = {
        "status": "passed",
        "source_lock": "RELEASE.lock.json",
        "rid": "linux-x64",
        "sdk_version": dotnet.get("sdkVersion"),
        "authority_path": sdk_descriptor.get("path"),
        "authority_sha256": sdk_descriptor.get("sha256"),
        "archive_url": sdk_archive.get("source"),
        "archive_name": sdk_archive.get("fileName"),
        "archive_sha256": sdk_archive.get("sha256"),
        "archive_sha512": sdk_archive.get("sha512"),
        "archive_size_bytes": sdk_archive.get("sizeBytes"),
        "dotnet_root_mode": "gate-owned-authenticated-sdk",
        "dotnet_root_x64_bound": True,
        "dotnet_host_path_bound": True,
        "path_precedence": "gate-owned-sdk-first",
        "multilevel_lookup": False,
        "system_runtime_fallback_allowed": False,
        "archive_reused_by_clean_builds": True,
    }
    _require(runtime_authority == expected_runtime_authority, "runtime_authority differs from exact locked SDK posture")

    gate = _require_dict(receipt["gate"], "gate")
    _require_exact_keys(
        gate,
        {
            "name",
            "host_audit_wrapper",
            "build_script",
            "install_script",
            "container_flow",
            "public_script_requires_sudo",
            "public_script_installs_system_packages",
            "build_temp_cleanup_default",
            "source_build_update_mode_default",
            "source_build_analytics_default",
            "source_build_is_explicitly_two_step",
        },
        "gate",
    )
    _require(gate["name"] == "linux_source_build_fresh_container", "gate.name is incorrect")
    _require(gate["host_audit_wrapper"] == "scripts/check-host-chummer6-linux.sh", "gate.host_audit_wrapper is incorrect")
    _require(gate["build_script"] == "scripts/build-chummer6-linux.sh", "gate.build_script is incorrect")
    _require(gate["install_script"] == "scripts/install-chummer6-linux-local.sh", "gate.install_script is incorrect")
    _require(
        gate["container_flow"] == "audit_then_two_clean_builds_then_direct_startup_then_local_install_then_updater_dispatch_pending_state_clearing_simulation",
        "gate.container_flow is incorrect",
    )
    _require(gate["public_script_requires_sudo"] is False, "gate.public_script_requires_sudo must be false")
    _require(gate["public_script_installs_system_packages"] is False, "gate.public_script_installs_system_packages must be false")
    _require(gate["build_temp_cleanup_default"] is True, "gate.build_temp_cleanup_default must be true")
    _require(gate["source_build_update_mode_default"] == "notify", "gate.source_build_update_mode_default must be notify")
    _require(gate["source_build_analytics_default"] == "off", "gate.source_build_analytics_default must be off")
    _require(gate["source_build_is_explicitly_two_step"] is True, "gate.source_build_is_explicitly_two_step must be true")

    output = _require_dict(receipt["output"], "output")
    _require_exact_keys(
        output,
        {
            "rid",
            "binary_name",
            "launcher_name",
            "archive_name",
            "archive_checksum_name",
            "executable_sha256",
            "archive_sha256",
            "debug_symbols",
            "artifact_path_portability",
            "artifact_mode_normalization",
        },
        "output",
    )
    _require(output["rid"] == "linux-x64", "output.rid must be linux-x64 for the native Docker gate")
    _require(output["binary_name"] == "Chummer.Avalonia", "output.binary_name is incorrect")
    _require(output["launcher_name"] == "run-chummer6.sh", "output.launcher_name is incorrect")
    expected_archive_name = "chummer6-linux-x64-source-lock.tar.gz"
    _require(output["archive_name"] == expected_archive_name, "output.archive_name is incorrect")
    _require(output["archive_checksum_name"] == f"{expected_archive_name}.sha256", "output.archive_checksum_name is incorrect")
    executable_sha256 = _require_sha256(output["executable_sha256"], "output.executable_sha256")
    archive_sha256 = _require_sha256(output["archive_sha256"], "output.archive_sha256")
    _require(output["debug_symbols"] == "none", "output.debug_symbols must be none")
    _require(output["artifact_path_portability"] == "passed", "output.artifact_path_portability must be passed")
    _require(output["artifact_mode_normalization"] == "passed", "output.artifact_mode_normalization must be passed")

    reproducibility = _require_dict(receipt["reproducibility"], "reproducibility")
    _require_exact_keys(
        reproducibility,
        {
            "status",
            "clean_build_count",
            "python_requirement",
            "python_role",
            "observed_python_versions",
            "archive_sha256_first",
            "archive_sha256_repeat",
            "archives_byte_identical",
            "archive_payload_path_scan",
            "archive_member_modes",
            "independent_host_archive_sha256",
            "independent_host_python_version",
            "cross_compatible_runtime_archive_identical",
            "scope",
            "release_evidence_eligible",
        },
        "reproducibility",
    )
    _require(reproducibility["status"] == "passed", "reproducibility.status must be passed")
    _require(reproducibility["clean_build_count"] == 2, "reproducibility.clean_build_count must be 2")
    _require(reproducibility["python_requirement"] == ">=3.11,<4", "reproducibility.python_requirement is incorrect")
    _require(reproducibility["python_role"] == "authenticated-orchestrator", "reproducibility.python_role is incorrect")
    observed_versions = reproducibility["observed_python_versions"]
    _require(isinstance(observed_versions, list) and len(observed_versions) == 2, "observed_python_versions must contain both clean builds")
    observed_versions = [
        _require_python_version(value, f"observed_python_versions[{index}]")
        for index, value in enumerate(observed_versions)
    ]
    _require(reproducibility["archive_sha256_first"] == archive_sha256, "first archive digest must equal output.archive_sha256")
    _require(reproducibility["archive_sha256_repeat"] == archive_sha256, "repeat archive digest must equal output.archive_sha256")
    _require(reproducibility["archives_byte_identical"] is True, "archives_byte_identical must be true")
    _require(reproducibility["archive_payload_path_scan"] == "passed", "archive_payload_path_scan must be passed")
    _require(reproducibility["archive_member_modes"] == "passed", "archive_member_modes must be passed")
    _require(
        reproducibility["independent_host_archive_sha256"] == archive_sha256,
        "independent host digest must equal both clean-container archive digests",
    )
    independent_python = _require_python_version(
        reproducibility["independent_host_python_version"],
        "independent_host_python_version",
    )
    _require(independent_python not in set(observed_versions), "independent host Python must differ from both container runtimes")
    _require(
        reproducibility["cross_compatible_runtime_archive_identical"] is True,
        "cross_compatible_runtime_archive_identical must be true",
    )
    _require(reproducibility["scope"] == "cross-compatible-runtime-observed", "reproducibility.scope is incorrect")
    _require(reproducibility["release_evidence_eligible"] is False, "reproducibility must remain evidence-ineligible")

    artifacts = _require_dict(receipt["artifacts"], "artifacts")
    _require_exact_keys(
        artifacts,
        {
            "build_manifest_excerpt",
            "source_heads",
            "build_log_name",
            "repeat_build_log_name",
            "archive_checksum_name",
            "repeat_archive_checksum_name",
            "startup_smoke_receipt_name",
            "installed_startup_smoke_receipt_name",
            "updater_special_mode_receipt_name",
            "updater_dispatch_simulation_receipt_name",
        },
        "artifacts",
    )
    _require(
        isinstance(artifacts["build_log_name"], str) and artifacts["build_log_name"].startswith("linux-source-build-") and artifacts["build_log_name"].endswith(".log"),
        "artifacts.build_log_name is incorrect",
    )
    _require(
        isinstance(artifacts["repeat_build_log_name"], str) and artifacts["repeat_build_log_name"].startswith("linux-source-build-") and artifacts["repeat_build_log_name"].endswith(".log"),
        "artifacts.repeat_build_log_name is incorrect",
    )
    _require(artifacts["archive_checksum_name"] == output["archive_checksum_name"], "archive checksum name must match output")
    _require(artifacts["repeat_archive_checksum_name"] == output["archive_checksum_name"], "repeat archive checksum name must match output")
    for field_name in (
        "startup_smoke_receipt_name",
        "installed_startup_smoke_receipt_name",
        "updater_special_mode_receipt_name",
        "updater_dispatch_simulation_receipt_name",
    ):
        _require(
            isinstance(artifacts[field_name], str) and artifacts[field_name].endswith(".receipt.json"),
            f"artifacts.{field_name} must end with .receipt.json",
        )
    source_heads = _require_dict(artifacts["source_heads"], "artifacts.source_heads")
    _require(source_heads == expected_source_heads, "artifacts.source_heads differs from exact RELEASE.lock repository authority")

    manifest_fields = _parse_manifest_excerpt(artifacts["build_manifest_excerpt"])
    expected_manifest_keys = {
        "contract",
        "scriptVersion",
        "sourceLockSha256",
        "sdkVersion",
        "pythonRequirement",
        "pythonRole",
        "targetRid",
        "releaseManifestStatus",
        "releaseManifestSha256",
        "releaseEvidenceEligible",
        "debugSymbols",
        "artifactPathPortability",
        "artifactModeNormalization",
        *(f"repository.{name}" for name in expected_source_heads),
    }
    _require(set(manifest_fields) == expected_manifest_keys, "build manifest property set differs from current v2 authority")
    dotnet = _require_dict(release_lock.get("dotnet"), "RELEASE.lock.json dotnet")
    _require(manifest_fields["contract"] == "chummer6.linux-source-build/v2", "build manifest contract is incorrect")
    _require(manifest_fields["scriptVersion"] == "3.1.0", "build manifest scriptVersion is incorrect")
    _require(manifest_fields["sourceLockSha256"] == lock_sha256, "build manifest sourceLockSha256 is stale")
    _require(manifest_fields["sdkVersion"] == dotnet.get("sdkVersion"), "build manifest SDK differs from RELEASE.lock.json")
    _require(manifest_fields["pythonRequirement"] == reproducibility["python_requirement"], "build manifest Python requirement differs")
    _require(manifest_fields["pythonRole"] == reproducibility["python_role"], "build manifest Python role differs")
    _require(manifest_fields["targetRid"] == output["rid"], "build manifest targetRid differs from output")
    _require(manifest_fields["releaseManifestStatus"] == receipt["release_manifest_status"], "build manifest release status differs")
    _require(manifest_fields["releaseManifestSha256"] == receipt["release_manifest_sha256"], "build manifest release digest differs")
    _require(manifest_fields["releaseEvidenceEligible"] == "false", "build manifest must remain evidence-ineligible")
    _require(manifest_fields["debugSymbols"] == output["debug_symbols"], "build manifest debug posture differs")
    _require(manifest_fields["artifactPathPortability"] == output["artifact_path_portability"], "build manifest portability differs")
    _require(manifest_fields["artifactModeNormalization"] == output["artifact_mode_normalization"], "build manifest mode normalization differs")
    _require(
        {key.removeprefix("repository."): value for key, value in manifest_fields.items() if key.startswith("repository.")}
        == expected_source_heads,
        "build manifest repository heads differ from RELEASE.lock.json",
    )

    runtime = _require_dict(receipt["runtime"], "runtime")
    _require_exact_keys(
        runtime,
        {"startup_smoke", "installed_startup_smoke", "updater_special_mode", "updater_dispatch_simulation"},
        "runtime",
    )
    _verify_startup_runtime(
        runtime["startup_smoke"],
        field_name="runtime.startup_smoke",
        output_rid=output["rid"],
        executable_sha256=executable_sha256,
        ready_checkpoint="fresh_container_gate",
    )
    _verify_startup_runtime(
        runtime["installed_startup_smoke"],
        field_name="runtime.installed_startup_smoke",
        output_rid=output["rid"],
        executable_sha256=executable_sha256,
        ready_checkpoint="fresh_container_installed_gate",
    )

    updater = _require_dict(runtime["updater_special_mode"], "runtime.updater_special_mode")
    _require_exact_keys(
        updater,
        {
            "status",
            "mode",
            "head_id",
            "channel_id",
            "rid",
            "exit_code",
            "expected_exit_code",
            "failure_reason",
            "last_error",
            "last_error_sanitized",
            "pending_update_version",
            "pending_update_channel_id",
            "recorded_at_utc",
        },
        "runtime.updater_special_mode",
    )
    _require(updater["status"] == "pass", "runtime.updater_special_mode.status must be pass")
    _require(updater["mode"] == "desktop_update_launch_installer", "runtime.updater_special_mode.mode is incorrect")
    _require(updater["head_id"] == "avalonia", "runtime.updater_special_mode.head_id must be avalonia")
    _require(updater["channel_id"] == "stable", "runtime.updater_special_mode.channel_id must be stable")
    _require(updater["rid"] == output["rid"], "runtime.updater_special_mode.rid must match output.rid")
    _require(updater["exit_code"] == 1 and updater["expected_exit_code"] == 1, "runtime.updater_special_mode exit code is incorrect")
    _require(updater["failure_reason"] == "installer_launch_failed", "runtime.updater_special_mode.failure_reason is incorrect")
    _require(updater["last_error"] == "Installer payload was not found.", "runtime.updater_special_mode.last_error is incorrect")
    _require(updater["last_error_sanitized"] is True, "runtime.updater_special_mode.last_error must be sanitized")
    _require(isinstance(updater["pending_update_version"], str) and updater["pending_update_version"].startswith("run-"), "pending update version is missing")
    _require(updater["pending_update_channel_id"] == "stable", "pending update channel must be stable")
    _require_recorded_at(updater["recorded_at_utc"], "runtime.updater_special_mode.recorded_at_utc")

    updater_simulation = _require_dict(runtime["updater_dispatch_simulation"], "runtime.updater_dispatch_simulation")
    _require_exact_keys(
        updater_simulation,
        {
            "status",
            "mode",
            "head_id",
            "channel_id",
            "rid",
            "exit_code",
            "expected_exit_code",
            "failure_reason",
            "last_error",
            "pending_update_version",
            "pending_update_channel_id",
            "execution_model",
            "privilege_escalation_performed",
            "native_package_manager_execution_proven",
            "invocation_contract_proven",
            "pkexec_shim_invoked",
            "dpkg_shim_invoked",
            "pkexec_invocation",
            "dpkg_invocation",
            "stage_retention_observed",
            "staged_payload_cleanup_proven",
            "retained_stage_inventory_exact",
            "retained_stage_inventory",
            "retained_stage_inventory_sha256",
            "gate_stage_location",
            "deferred_cleanup_phase",
            "deferred_cleanup_policy",
            "deferred_cleanup_execution_proven",
            "recorded_at_utc",
        },
        "runtime.updater_dispatch_simulation",
    )
    _require(updater_simulation["status"] == "pass", "runtime.updater_dispatch_simulation.status must be pass")
    _require(
        updater_simulation["mode"] == "desktop_update_dispatch_pending_state_clearing_simulation",
        "updater dispatch simulation mode is incorrect",
    )
    _require(updater_simulation["head_id"] == "avalonia", "updater dispatch simulation head_id must be avalonia")
    _require(updater_simulation["channel_id"] == "stable", "updater dispatch simulation channel_id must be stable")
    _require(updater_simulation["rid"] == output["rid"], "updater dispatch simulation rid must match output.rid")
    _require(
        updater_simulation["exit_code"] == 0 and updater_simulation["expected_exit_code"] == 0,
        "updater dispatch simulation exit code is incorrect",
    )
    _require(
        updater_simulation["failure_reason"] == "" and updater_simulation["last_error"] == "",
        "updater dispatch simulation must clear errors",
    )
    _require(
        updater_simulation["pending_update_version"] == ""
        and updater_simulation["pending_update_channel_id"] == "",
        "updater dispatch simulation must clear pending state",
    )
    _require(
        updater_simulation["execution_model"] == "simulated_nonprivileged_pkexec_dpkg",
        "updater dispatch execution_model must identify the nonprivileged shims",
    )
    _require(
        updater_simulation["privilege_escalation_performed"] is False,
        "updater dispatch simulation must not claim privilege escalation",
    )
    _require(
        updater_simulation["native_package_manager_execution_proven"] is False,
        "updater dispatch simulation must not claim native package-manager execution",
    )
    _require(updater_simulation["invocation_contract_proven"] is True, "updater invocation contract was not proven")
    _require(updater_simulation["pkexec_shim_invoked"] is True, "pkexec shim invocation was not proven")
    _require(updater_simulation["dpkg_shim_invoked"] is True, "dpkg shim invocation was not proven")

    pkexec_invocation = _require_dict(
        updater_simulation["pkexec_invocation"],
        "runtime.updater_dispatch_simulation.pkexec_invocation",
    )
    _require_exact_keys(
        pkexec_invocation,
        {
            "argv_count",
            "command_label",
            "install_flag",
            "installer_argument_binding",
            "installer_argument_sha256",
        },
        "runtime.updater_dispatch_simulation.pkexec_invocation",
    )
    installer_argument_sha256 = _require_sha256(
        pkexec_invocation["installer_argument_sha256"],
        "runtime.updater_dispatch_simulation.pkexec_invocation.installer_argument_sha256",
    )
    _require(
        pkexec_invocation == {
            "argv_count": 3,
            "command_label": "dpkg",
            "install_flag": "-i",
            "installer_argument_binding": "sha256_of_utf8_gate_stage_installer_path",
            "installer_argument_sha256": installer_argument_sha256,
        },
        "pkexec shim argv contract differs",
    )
    dpkg_invocation = _require_dict(
        updater_simulation["dpkg_invocation"],
        "runtime.updater_dispatch_simulation.dpkg_invocation",
    )
    _require_exact_keys(
        dpkg_invocation,
        {"argv_count", "install_flag", "installer_argument_binding", "installer_argument_sha256"},
        "runtime.updater_dispatch_simulation.dpkg_invocation",
    )
    _require(
        dpkg_invocation == {
            "argv_count": 2,
            "install_flag": "-i",
            "installer_argument_binding": "sha256_of_utf8_gate_stage_installer_path",
            "installer_argument_sha256": installer_argument_sha256,
        },
        "dpkg shim argv contract differs or is not bound to the pkexec installer argument",
    )
    _require(
        updater_simulation["stage_retention_observed"] is True,
        "updater dispatch simulation must observe the pinned UI stage-retention behavior",
    )
    _require(
        updater_simulation["staged_payload_cleanup_proven"] is False,
        "updater dispatch simulation must not claim staged-payload cleanup",
    )
    _require(
        updater_simulation["retained_stage_inventory_exact"] is True,
        "updater dispatch simulation must prove the exact retained stage inventory",
    )
    retained_inventory = updater_simulation["retained_stage_inventory"]
    _require(
        isinstance(retained_inventory, list) and len(retained_inventory) == 2,
        "retained_stage_inventory must contain the installer and request",
    )
    retained_inventory_sha256 = _require_sha256(
        updater_simulation["retained_stage_inventory_sha256"],
        "runtime.updater_dispatch_simulation.retained_stage_inventory_sha256",
    )
    _require(
        retained_inventory_sha256
        == hashlib.sha256(
            json.dumps(
                retained_inventory,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
        "retained stage inventory digest does not bind the exact inventory",
    )
    retained_by_role: dict[str, dict[str, Any]] = {}
    for index, item_value in enumerate(retained_inventory):
        item = _require_dict(
            item_value,
            f"runtime.updater_dispatch_simulation.retained_stage_inventory[{index}]",
        )
        _require_exact_keys(
            item,
            {"role", "file_name", "size_bytes", "sha256"},
            f"runtime.updater_dispatch_simulation.retained_stage_inventory[{index}]",
        )
        role = item["role"]
        _require(
            isinstance(role, str) and role not in retained_by_role,
            "retained stage inventory roles must be unique strings",
        )
        retained_by_role[role] = item
    _require(
        set(retained_by_role) == {"installer_payload", "installer_request"},
        "retained stage inventory roles differ",
    )
    installer_inventory = retained_by_role["installer_payload"]
    _require(
        installer_inventory["file_name"] == "chummer-avalonia-linux-x64-installer.deb"
        and installer_inventory["size_bytes"] == 0
        and installer_inventory["sha256"] == hashlib.sha256(b"").hexdigest(),
        "retained installer inventory differs",
    )
    request_inventory = retained_by_role["installer_request"]
    _require(request_inventory["file_name"] == "installer-request.json", "retained request file name differs")
    _require(
        isinstance(request_inventory["size_bytes"], int) and request_inventory["size_bytes"] > 0,
        "retained request size must be positive",
    )
    _require_sha256(
        request_inventory["sha256"],
        "runtime.updater_dispatch_simulation.retained_stage_inventory.installer_request.sha256",
    )
    _require(
        updater_simulation["gate_stage_location"] == "synthetic_gate_stage_outside_normal_ui_temp_root",
        "gate stage location scope is incorrect",
    )
    _require(
        updater_simulation["deferred_cleanup_phase"] == "outside_dispatch_simulation",
        "deferred cleanup phase must remain outside this simulation",
    )
    _require(
        updater_simulation["deferred_cleanup_policy"]
        == "new_release_startup_or_two_day_stale_temp_pruning",
        "deferred cleanup policy differs from the pinned UI posture",
    )
    _require(
        updater_simulation["deferred_cleanup_execution_proven"] is False,
        "the gate must not claim execution of deferred cleanup",
    )
    _require_recorded_at(
        updater_simulation["recorded_at_utc"],
        "runtime.updater_dispatch_simulation.recorded_at_utc",
    )


def main() -> int:
    verify(json.loads(RECEIPT_PATH.read_text(encoding="utf-8")))
    print("linux_source_build_docker_gate_receipt:ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
