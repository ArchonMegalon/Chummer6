#!/usr/bin/env python3
"""Validate and expose the immutable inputs for the Linux source build."""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


CONTRACT = "chummer6.release-source-lock/v1"
REQUIRED_REPOSITORIES = {
    "chummer-core-engine": "chummer6-core",
    "chummer.run-services": "chummer6-hub",
    "chummer-hub-registry": "chummer6-hub-registry",
    "chummer-ui-kit": "chummer6-ui-kit",
    "chummer6-ui": "chummer6-ui",
}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SDK_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$")
SAFE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
PACKAGE_VERSION_PATTERN = re.compile(r"^[0-9A-Za-z][0-9A-Za-z.+-]*$")
SUPPORTED_RIDS = {"linux-x64", "linux-arm64"}
EXPECTED_DIRECT_PACKAGES = {
    "Avalonia": "11.3.7",
    "Avalonia.Desktop": "11.3.7",
    "Avalonia.Fonts.Inter": "11.3.7",
    "Avalonia.Themes.Fluent": "11.3.7",
    "Microsoft.Extensions.DependencyInjection": "10.0.0",
    "Tmds.DBus.Protocol": "0.21.3",
}
EXPECTED_PROJECTS = {
    "chummer.application",
    "chummer.campaign.contracts",
    "chummer.desktop.runtime",
    "Chummer.Engine.Contracts",
    "chummer.hub.registry.contracts",
    "chummer.infrastructure",
    "chummer.play.contracts",
    "chummer.presentation",
    "chummer.rulesets.hosting",
    "chummer.rulesets.sr4",
    "chummer.rulesets.sr5",
    "chummer.rulesets.sr6",
    "chummer.run.contracts",
    "chummer.ui.kit",
}


class LockError(ValueError):
    pass


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LockError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_json(path: Path, label: str = "source lock") -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise LockError(f"cannot read {label} {path}: {exc}") from exc
    try:
        value = json.loads(raw, object_pairs_hook=_strict_object)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise LockError(f"invalid {label} JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise LockError(f"{label} root must be an object")
    return value


def _exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise LockError(f"{label} keys mismatch; missing={missing}, extra={extra}")


def _required_string(value: dict[str, Any], key: str, label: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item or item != item.strip():
        raise LockError(f"{label}.{key} must be a non-empty, unpadded string")
    if "\n" in item or "\r" in item or "\t" in item:
        raise LockError(f"{label}.{key} contains a control character")
    return item


def _required_sha(value: dict[str, Any], key: str, label: str, pattern: re.Pattern[str] = SHA256_PATTERN) -> str:
    item = _required_string(value, key, label)
    if not pattern.fullmatch(item):
        raise LockError(f"{label}.{key} is not a canonical digest")
    return item


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha512(value: Any, label: str) -> str:
    if not isinstance(value, str) or value != value.strip():
        raise LockError(f"{label} must be a canonical base64 SHA512 string")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise LockError(f"{label} is not canonical base64") from exc
    if len(decoded) != 64 or base64.b64encode(decoded).decode("ascii") != value:
        raise LockError(f"{label} is not a canonical SHA512 digest")
    return value


def _archive_sha512(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return base64.b64encode(digest.digest()).decode("ascii")


def _resolve_repo_file(repo_root: Path, relative: str, label: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise LockError(f"{label} must be a repository-relative path")
    resolved_root = repo_root.resolve()
    resolved = (resolved_root / path).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise LockError(f"{label} escapes the repository root") from exc
    if not resolved.is_file():
        raise LockError(f"{label} does not exist: {relative}")
    return resolved


def _git_blob_sha256(repo_root: Path, commit: str, relative: str) -> str:
    completed = subprocess.run(
        ["git", "-c", "gc.auto=0", "-c", "maintenance.auto=0", "-C", str(repo_root), "show", f"{commit}:{relative}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise LockError(f"cannot read release manifest provenance {commit}:{relative}: {detail}")
    return hashlib.sha256(completed.stdout).hexdigest()


def _validate_dependency_map(value: Any, label: str) -> None:
    if not isinstance(value, dict):
        raise LockError(f"{label} must be an object")
    for name, version in value.items():
        if not isinstance(name, str) or not SAFE_NAME_PATTERN.fullmatch(name):
            raise LockError(f"{label} contains an unsafe dependency name")
        if not isinstance(version, str) or not version or version != version.strip():
            raise LockError(f"{label}.{name} must be a non-empty version expression")


def _validate_package_lock(path: Path, rid: str) -> dict[tuple[str, str], dict[str, str]]:
    payload = _load_json(path, f"NuGet package lock for {rid}")
    _exact_keys(payload, {"version", "dependencies"}, f"NuGet package lock for {rid}")
    if payload.get("version") != 1:
        raise LockError(f"NuGet package lock for {rid} must use version 1")
    targets = payload.get("dependencies")
    if not isinstance(targets, dict):
        raise LockError(f"NuGet package lock for {rid}.dependencies must be an object")
    expected_targets = {"net10.0", f"net10.0/{rid}"}
    if set(targets) != expected_targets:
        raise LockError(
            f"NuGet package lock for {rid} target mismatch; expected={sorted(expected_targets)}, got={sorted(targets)}"
        )

    packages: dict[tuple[str, str], dict[str, str]] = {}
    direct_packages: dict[str, str] = {}
    projects: set[str] = set()
    for target_name, nodes in targets.items():
        target_label = f"NuGet package lock for {rid}.{target_name}"
        if not isinstance(nodes, dict):
            raise LockError(f"{target_label} must be an object")
        seen_casefolded: set[str] = set()
        for package_name, node in nodes.items():
            label = f"{target_label}.{package_name}"
            if not isinstance(package_name, str) or not SAFE_NAME_PATTERN.fullmatch(package_name):
                raise LockError(f"{target_label} contains an unsafe package or project identity")
            folded_name = package_name.casefold()
            if folded_name in seen_casefolded:
                raise LockError(f"{target_label} contains a case-insensitive duplicate: {package_name}")
            seen_casefolded.add(folded_name)
            if not isinstance(node, dict):
                raise LockError(f"{label} must be an object")
            allowed_keys = {"type", "requested", "resolved", "contentHash", "dependencies"}
            if not set(node).issubset(allowed_keys):
                raise LockError(f"{label} has unsupported keys: {sorted(set(node) - allowed_keys)}")
            node_type = node.get("type")
            if node_type not in {"Direct", "Transitive", "Project"}:
                raise LockError(f"{label}.type is not supported")
            if "dependencies" in node:
                _validate_dependency_map(node["dependencies"], f"{label}.dependencies")
            if node_type == "Project":
                if target_name != "net10.0" or set(node) - {"type", "dependencies"}:
                    raise LockError(f"{label} is not a canonical project node")
                projects.add(package_name)
                continue

            required_keys = {"type", "resolved", "contentHash"}
            if node_type == "Direct":
                required_keys.add("requested")
            if not required_keys.issubset(node):
                raise LockError(f"{label} is missing required locked-package fields")
            if node_type == "Transitive" and "requested" in node:
                raise LockError(f"{label} transitive node must not carry requested")
            resolved = node.get("resolved")
            if not isinstance(resolved, str) or not PACKAGE_VERSION_PATTERN.fullmatch(resolved):
                raise LockError(f"{label}.resolved is not a canonical package version")
            if node_type == "Direct":
                requested = node.get("requested")
                if not isinstance(requested, str) or not requested or requested != requested.strip():
                    raise LockError(f"{label}.requested is not canonical")
                direct_packages[package_name] = resolved
            content_hash = _canonical_sha512(node.get("contentHash"), f"{label}.contentHash")
            identity = (folded_name, resolved.casefold())
            package = {"id": package_name, "version": resolved, "contentHash": content_hash}
            previous = packages.get(identity)
            if previous is not None and previous != package:
                raise LockError(f"{label} disagrees with another target for the same package identity")
            packages[identity] = package

    if direct_packages != EXPECTED_DIRECT_PACKAGES:
        raise LockError(
            f"NuGet package lock for {rid} direct package graph drift; "
            f"expected={EXPECTED_DIRECT_PACKAGES}, got={direct_packages}"
        )
    if projects != EXPECTED_PROJECTS:
        raise LockError(
            f"NuGet package lock for {rid} project graph drift; "
            f"missing={sorted(EXPECTED_PROJECTS - projects)}, extra={sorted(projects - EXPECTED_PROJECTS)}"
        )
    if not packages:
        raise LockError(f"NuGet package lock for {rid} resolves no packages")
    return packages


def _package_lock_entry(payload: dict[str, Any], rid: str) -> dict[str, Any]:
    for entry in payload["nuget"]["packageLocks"]:
        if entry["runtimeIdentifier"] == rid:
            return entry
    raise LockError(f"source lock has no NuGet package lock for {rid}")


def _locked_packages(payload: dict[str, Any], repo_root: Path, rid: str) -> dict[tuple[str, str], dict[str, str]]:
    entry = _package_lock_entry(payload, rid)
    path = _resolve_repo_file(repo_root, entry["path"], f"NuGet package lock for {rid}.path")
    packages = _validate_package_lock(path, rid)
    for index, implicit in enumerate(entry["implicitPackages"]):
        identity = (implicit["id"].casefold(), implicit["version"].casefold())
        if identity in packages:
            raise LockError(f"NuGet package lock for {rid} duplicates implicit package {implicit['id']}")
        packages[identity] = {
            "id": implicit["id"],
            "version": implicit["version"],
            "contentHash": implicit["contentHash"],
            "archiveSha512": implicit["archiveSha512"],
        }
    return packages


def validate_lock(path: Path, repo_root: Path) -> dict[str, Any]:
    payload = _load_json(path)
    _exact_keys(
        payload,
        {"contract", "schemaVersion", "repositories", "dotnet", "nuget", "releaseManifest", "buildScript"},
        "source lock",
    )
    if payload.get("contract") != CONTRACT or payload.get("schemaVersion") != 1:
        raise LockError(f"source lock must use {CONTRACT} schemaVersion 1")

    repositories = payload.get("repositories")
    if not isinstance(repositories, list) or len(repositories) != len(REQUIRED_REPOSITORIES):
        raise LockError(f"repositories must contain exactly {len(REQUIRED_REPOSITORIES)} entries")
    seen_directories: set[str] = set()
    seen_names: set[str] = set()
    for index, repository in enumerate(repositories):
        label = f"repositories[{index}]"
        if not isinstance(repository, dict):
            raise LockError(f"{label} must be an object")
        _exact_keys(repository, {"directory", "name", "url", "commit", "globalJsonSdkVersion"}, label)
        directory = _required_string(repository, "directory", label)
        name = _required_string(repository, "name", label)
        url = _required_string(repository, "url", label)
        _required_sha(repository, "commit", label, COMMIT_PATTERN)
        if not SAFE_NAME_PATTERN.fullmatch(directory) or not SAFE_NAME_PATTERN.fullmatch(name):
            raise LockError(f"{label} contains an unsafe repository identity")
        if REQUIRED_REPOSITORIES.get(directory) != name:
            raise LockError(f"{label} is not a required Linux source-build repository")
        if url != f"https://github.com/ArchonMegalon/{name}.git":
            raise LockError(f"{label}.url must be the canonical owner repository URL")
        declared_sdk = repository.get("globalJsonSdkVersion")
        if declared_sdk is not None and (not isinstance(declared_sdk, str) or not SDK_PATTERN.fullmatch(declared_sdk)):
            raise LockError(f"{label}.globalJsonSdkVersion must be null or a canonical SDK version")
        if directory in seen_directories or name in seen_names:
            raise LockError(f"{label} duplicates a repository identity")
        seen_directories.add(directory)
        seen_names.add(name)
    if seen_directories != set(REQUIRED_REPOSITORIES):
        raise LockError("repositories do not cover the exact Linux source-build owner set")

    dotnet = payload.get("dotnet")
    if not isinstance(dotnet, dict):
        raise LockError("dotnet must be an object")
    _exact_keys(dotnet, {"sdkVersion", "installScript"}, "dotnet")
    sdk_version = _required_string(dotnet, "sdkVersion", "dotnet")
    if not SDK_PATTERN.fullmatch(sdk_version):
        raise LockError("dotnet.sdkVersion is not canonical")
    install_script = dotnet.get("installScript")
    if not isinstance(install_script, dict):
        raise LockError("dotnet.installScript must be an object")
    _exact_keys(install_script, {"url", "sha256"}, "dotnet.installScript")
    install_url = _required_string(install_script, "url", "dotnet.installScript")
    if install_url != "https://dot.net/v1/dotnet-install.sh":
        raise LockError("dotnet.installScript.url is not the approved HTTPS endpoint")
    _required_sha(install_script, "sha256", "dotnet.installScript")

    nuget = payload.get("nuget")
    if not isinstance(nuget, dict):
        raise LockError("nuget must be an object")
    _exact_keys(nuget, {"packageResolution", "serviceIndexes", "packageLocks"}, "nuget")
    if nuget.get("packageResolution") != "nuget-lock-v1-content-hash":
        raise LockError("nuget.packageResolution must require the NuGet v1 locked content-hash contract")
    service_indexes = nuget.get("serviceIndexes")
    if not isinstance(service_indexes, list) or len(service_indexes) != 1:
        raise LockError("nuget.serviceIndexes must contain exactly the approved nuget.org service index")
    seen_feed_keys: set[str] = set()
    seen_feed_urls: set[str] = set()
    for index, service_index in enumerate(service_indexes):
        label = f"nuget.serviceIndexes[{index}]"
        if not isinstance(service_index, dict):
            raise LockError(f"{label} must be an object")
        _exact_keys(service_index, {"key", "url", "sha256"}, label)
        key = _required_string(service_index, "key", label)
        url = _required_string(service_index, "url", label)
        _required_sha(service_index, "sha256", label)
        if key != "nuget.org" or url != "https://api.nuget.org/v3/index.json":
            raise LockError(f"{label} is not the exact approved nuget.org source")
        if key in seen_feed_keys or url in seen_feed_urls:
            raise LockError(f"{label} duplicates a NuGet source")
        seen_feed_keys.add(key)
        seen_feed_urls.add(url)

    package_locks = nuget.get("packageLocks")
    if not isinstance(package_locks, list) or len(package_locks) != len(SUPPORTED_RIDS):
        raise LockError(f"nuget.packageLocks must contain exactly {sorted(SUPPORTED_RIDS)}")
    seen_rids: set[str] = set()
    for index, package_lock in enumerate(package_locks):
        label = f"nuget.packageLocks[{index}]"
        if not isinstance(package_lock, dict):
            raise LockError(f"{label} must be an object")
        _exact_keys(
            package_lock,
            {"runtimeIdentifier", "project", "targetFramework", "path", "sha256", "implicitPackages"},
            label,
        )
        rid = _required_string(package_lock, "runtimeIdentifier", label)
        if rid not in SUPPORTED_RIDS or rid in seen_rids:
            raise LockError(f"{label}.runtimeIdentifier must be a unique supported RID")
        seen_rids.add(rid)
        if _required_string(package_lock, "project", label) != "Chummer.Avalonia/Chummer.Avalonia.csproj":
            raise LockError(f"{label}.project must identify the Avalonia root project")
        if _required_string(package_lock, "targetFramework", label) != "net10.0":
            raise LockError(f"{label}.targetFramework must be net10.0")
        relative = _required_string(package_lock, "path", label)
        expected_digest = _required_sha(package_lock, "sha256", label)
        lock_file = _resolve_repo_file(repo_root, relative, f"{label}.path")
        if _sha256(lock_file) != expected_digest:
            raise LockError(f"{label}.sha256 does not match the checked NuGet package lock")
        _validate_package_lock(lock_file, rid)

        implicit_packages = package_lock.get("implicitPackages")
        if not isinstance(implicit_packages, list) or len(implicit_packages) != 2:
            raise LockError(f"{label}.implicitPackages must contain exactly the two SDK runtime packs")
        expected_implicit = {
            f"microsoft.aspnetcore.app.runtime.{rid}",
            f"microsoft.netcore.app.runtime.{rid}",
        }
        seen_implicit: set[str] = set()
        for implicit_index, implicit in enumerate(implicit_packages):
            implicit_label = f"{label}.implicitPackages[{implicit_index}]"
            if not isinstance(implicit, dict):
                raise LockError(f"{implicit_label} must be an object")
            _exact_keys(implicit, {"id", "version", "contentHash", "archiveSha512"}, implicit_label)
            package_id = _required_string(implicit, "id", implicit_label)
            version = _required_string(implicit, "version", implicit_label)
            if package_id not in expected_implicit or package_id in seen_implicit:
                raise LockError(f"{implicit_label}.id is not a unique SDK runtime pack for {rid}")
            if version != "10.0.3":
                raise LockError(f"{implicit_label}.version must match SDK 10.0.103 runtime pack 10.0.3")
            _canonical_sha512(implicit.get("contentHash"), f"{implicit_label}.contentHash")
            _canonical_sha512(implicit.get("archiveSha512"), f"{implicit_label}.archiveSha512")
            seen_implicit.add(package_id)
        if seen_implicit != expected_implicit:
            raise LockError(f"{label}.implicitPackages does not cover the exact SDK runtime packs")
    if seen_rids != SUPPORTED_RIDS:
        raise LockError("nuget.packageLocks does not cover the exact supported Linux RIDs")

    release_manifest = payload.get("releaseManifest")
    if not isinstance(release_manifest, dict):
        raise LockError("releaseManifest must be an object")
    _exact_keys(
        release_manifest,
        {"authorityContract", "sourceRepository", "sourceCommit", "path", "sha256", "status", "releaseEvidenceEligible"},
        "releaseManifest",
    )
    authority_contract = _required_string(release_manifest, "authorityContract", "releaseManifest")
    source_repository = _required_string(release_manifest, "sourceRepository", "releaseManifest")
    source_commit = _required_sha(release_manifest, "sourceCommit", "releaseManifest", COMMIT_PATTERN)
    manifest_relative = _required_string(release_manifest, "path", "releaseManifest")
    manifest_sha = _required_sha(release_manifest, "sha256", "releaseManifest")
    manifest_status = _required_string(release_manifest, "status", "releaseManifest")
    evidence_eligible = release_manifest.get("releaseEvidenceEligible")
    if not isinstance(evidence_eligible, bool):
        raise LockError("releaseManifest.releaseEvidenceEligible must be boolean")
    if manifest_status == "bound":
        if authority_contract != "chummer.release-authority-snapshot/v2" or not evidence_eligible:
            raise LockError("a bound release manifest must use authority snapshot v2 and be release-evidence eligible")
    elif manifest_status == "unbound_review_placeholder":
        if authority_contract != "chummer6.public-release-truth/unbound-review-placeholder/v1" or evidence_eligible:
            raise LockError("an unbound review placeholder must remain ineligible for release evidence")
    else:
        raise LockError("releaseManifest.status must be bound or unbound_review_placeholder")
    if source_repository != "ArchonMegalon/Chummer6":
        raise LockError("the checked release-manifest projection must be owned by ArchonMegalon/Chummer6")
    manifest_path = _resolve_repo_file(repo_root, manifest_relative, "releaseManifest.path")
    if _sha256(manifest_path) != manifest_sha:
        raise LockError("releaseManifest.sha256 does not match the checked file")
    if _git_blob_sha256(repo_root, source_commit, manifest_relative) != manifest_sha:
        raise LockError("releaseManifest sourceCommit/path provenance does not match its SHA256")
    try:
        manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"), object_pairs_hook=_strict_object)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise LockError(f"release manifest is invalid JSON: {exc}") from exc
    if manifest_status == "unbound_review_placeholder":
        if not isinstance(manifest_payload, dict) or manifest_payload.get("authority_binding_status") != "unbound_review_placeholder":
            raise LockError("unbound release manifest does not carry the required review-placeholder posture")
        if manifest_payload.get("release_decision_status") != "review_required":
            raise LockError("unbound release manifest must remain review_required")

    build_script = payload.get("buildScript")
    if not isinstance(build_script, dict):
        raise LockError("buildScript must be an object")
    _exact_keys(build_script, {"path", "sha256"}, "buildScript")
    script_relative = _required_string(build_script, "path", "buildScript")
    script_sha = _required_sha(build_script, "sha256", "buildScript")
    script_path = _resolve_repo_file(repo_root, script_relative, "buildScript.path")
    if _sha256(script_path) != script_sha:
        raise LockError("buildScript.sha256 does not match the checked script")

    return payload


def _git_output(directory: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-c", "gc.auto=0", "-c", "maintenance.auto=0", "-C", str(directory), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        raise LockError(f"git {' '.join(args)} failed for {directory}: {completed.stdout.strip()}")
    return completed.stdout.strip()


def verify_checkouts(payload: dict[str, Any], base: Path, locked: bool) -> None:
    for repository in payload["repositories"]:
        directory = base / repository["directory"]
        if not directory.is_dir():
            raise LockError(f"missing checked-out repository: {directory}")
        actual_commit = _git_output(directory, "rev-parse", "HEAD")
        if locked and actual_commit != repository["commit"]:
            raise LockError(
                f"{repository['name']} checkout drift: expected {repository['commit']}, got {actual_commit}"
            )
        expected_sdk = repository["globalJsonSdkVersion"]
        global_json = directory / "global.json"
        if expected_sdk is None:
            if locked and global_json.exists():
                raise LockError(f"{repository['name']} unexpectedly gained global.json at the pinned commit")
            continue
        if not global_json.is_file():
            raise LockError(f"{repository['name']} is missing its pinned global.json")
        try:
            actual_sdk = json.loads(global_json.read_text(encoding="utf-8"))["sdk"]["version"]
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise LockError(f"{repository['name']} global.json is invalid: {exc}") from exc
        if locked and actual_sdk != expected_sdk:
            raise LockError(f"{repository['name']} SDK declaration drift: expected {expected_sdk}, got {actual_sdk}")


def write_nuget_config(
    payload: dict[str, Any], repo_root: Path, rid: str, packages_root: Path, output: Path
) -> None:
    if rid not in SUPPORTED_RIDS:
        raise LockError(f"unsupported NuGet runtime identifier: {rid}")
    packages = _locked_packages(payload, repo_root, rid)
    if not packages_root.is_absolute():
        raise LockError("NuGet global packages root must be absolute")
    if packages_root.exists() and packages_root.is_symlink():
        raise LockError("NuGet global packages root must not be a symlink")
    if output.exists():
        raise LockError(f"refusing to replace an existing NuGet config: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.parent.is_symlink():
        raise LockError("NuGet config parent must not be a symlink")

    service_index = payload["nuget"]["serviceIndexes"][0]
    package_ids = sorted({package["id"] for package in packages.values()}, key=str.casefold)
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        "<configuration>",
        "  <config>",
        f'    <add key="globalPackagesFolder" value="{html.escape(str(packages_root), quote=True)}" />',
        "  </config>",
        "  <packageSources>",
        "    <clear />",
        (
            f'    <add key="{html.escape(service_index["key"], quote=True)}" '
            f'value="{html.escape(service_index["url"], quote=True)}" protocolVersion="3" />'
        ),
        "  </packageSources>",
        "  <disabledPackageSources>",
        "    <clear />",
        "  </disabledPackageSources>",
        "  <packageSourceMapping>",
        "    <clear />",
        f'    <packageSource key="{html.escape(service_index["key"], quote=True)}">',
    ]
    for package_id in package_ids:
        lines.append(f'      <package pattern="{html.escape(package_id, quote=True)}" />')
    lines.extend(["    </packageSource>", "  </packageSourceMapping>", "</configuration>"])
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify_nuget_cache(payload: dict[str, Any], repo_root: Path, rid: str, packages_root: Path) -> None:
    if rid not in SUPPORTED_RIDS:
        raise LockError(f"unsupported NuGet runtime identifier: {rid}")
    if not packages_root.is_dir() or packages_root.is_symlink():
        raise LockError(f"NuGet global packages root is missing or unsafe: {packages_root}")
    for walk_root, directory_names, file_names in os.walk(packages_root, followlinks=False):
        root_path = Path(walk_root)
        for name in [*directory_names, *file_names]:
            if (root_path / name).is_symlink():
                raise LockError(f"NuGet cache contains a symlink: {root_path / name}")

    expected = _locked_packages(payload, repo_root, rid)
    expected_by_id: dict[str, dict[str, dict[str, str]]] = {}
    for (package_id, version), package in expected.items():
        expected_by_id.setdefault(package_id, {})[version] = package

    actual_id_entries = list(packages_root.iterdir())
    if any(not entry.is_dir() for entry in actual_id_entries):
        raise LockError("NuGet cache root contains a non-package entry")
    actual_ids = {entry.name for entry in actual_id_entries}
    if actual_ids != set(expected_by_id):
        raise LockError(
            f"NuGet cache package set drift; missing={sorted(set(expected_by_id) - actual_ids)}, "
            f"extra={sorted(actual_ids - set(expected_by_id))}"
        )

    approved_source = payload["nuget"]["serviceIndexes"][0]["url"]
    for package_id, versions in expected_by_id.items():
        id_root = packages_root / package_id
        actual_version_entries = list(id_root.iterdir())
        if any(not entry.is_dir() for entry in actual_version_entries):
            raise LockError(f"NuGet cache package directory contains a non-version entry: {id_root}")
        actual_versions = {entry.name for entry in actual_version_entries}
        if actual_versions != set(versions):
            raise LockError(
                f"NuGet cache version drift for {package_id}; "
                f"missing={sorted(set(versions) - actual_versions)}, extra={sorted(actual_versions - set(versions))}"
            )
        for version, package in versions.items():
            package_root = id_root / version
            metadata_path = package_root / ".nupkg.metadata"
            metadata = _load_json(metadata_path, f"NuGet cache metadata for {package_id}/{version}")
            _exact_keys(metadata, {"version", "contentHash", "source"}, f"NuGet cache metadata for {package_id}/{version}")
            if metadata.get("version") != 2:
                raise LockError(f"NuGet cache metadata version drift for {package_id}/{version}")
            if metadata.get("contentHash") != package["contentHash"]:
                raise LockError(f"NuGet cache contentHash drift for {package_id}/{version}")
            if metadata.get("source") != approved_source:
                raise LockError(f"NuGet cache source drift for {package_id}/{version}")

            archive = package_root / f"{package_id}.{version}.nupkg"
            sidecar = package_root / f"{package_id}.{version}.nupkg.sha512"
            if not archive.is_file() or archive.is_symlink() or not sidecar.is_file() or sidecar.is_symlink():
                raise LockError(f"NuGet cache archive or SHA512 sidecar is missing for {package_id}/{version}")
            try:
                recorded_archive_sha = sidecar.read_text(encoding="ascii").strip()
            except (OSError, UnicodeDecodeError) as exc:
                raise LockError(f"cannot read NuGet archive SHA512 for {package_id}/{version}: {exc}") from exc
            _canonical_sha512(recorded_archive_sha, f"NuGet cache archive SHA512 for {package_id}/{version}")
            actual_archive_sha = _archive_sha512(archive)
            if recorded_archive_sha != actual_archive_sha:
                raise LockError(f"NuGet cache archive SHA512 drift for {package_id}/{version}")
            if "archiveSha512" in package and actual_archive_sha != package["archiveSha512"]:
                raise LockError(f"NuGet implicit runtime archive drift for {package_id}/{version}")

    print(f"NuGet cache verified: {len(expected)} exact packages for {rid}")


def emit_tsv(payload: dict[str, Any], lock_path: Path) -> None:
    print(f"LOCK_SHA256\t{_sha256(lock_path)}")
    print(f"SDK_VERSION\t{payload['dotnet']['sdkVersion']}")
    print(f"DOTNET_INSTALL_URL\t{payload['dotnet']['installScript']['url']}")
    print(f"DOTNET_INSTALL_SHA256\t{payload['dotnet']['installScript']['sha256']}")
    manifest = payload["releaseManifest"]
    print(f"RELEASE_MANIFEST_SHA256\t{manifest['sha256']}")
    print(f"RELEASE_MANIFEST_STATUS\t{manifest['status']}")
    print(f"RELEASE_EVIDENCE_ELIGIBLE\t{str(manifest['releaseEvidenceEligible']).lower()}")
    for repository in payload["repositories"]:
        print(
            "REPOSITORY\t"
            f"{repository['directory']}\t{repository['name']}\t{repository['commit']}"
        )
    for service_index in payload["nuget"]["serviceIndexes"]:
        print(
            "NUGET_SERVICE_INDEX\t"
            f"{service_index['key']}\t{service_index['url']}\t{service_index['sha256']}"
        )
    for package_lock in payload["nuget"]["packageLocks"]:
        print(
            "NUGET_PACKAGE_LOCK\t"
            f"{package_lock['runtimeIdentifier']}\t{package_lock['path']}\t{package_lock['sha256']}"
        )


def verify_file(path: Path, expected_sha256: str, label: str) -> None:
    if not SHA256_PATTERN.fullmatch(expected_sha256):
        raise LockError(f"{label} expected SHA256 is not canonical")
    if not path.is_file():
        raise LockError(f"{label} download is missing: {path}")
    actual = _sha256(path)
    if actual != expected_sha256:
        raise LockError(f"{label} SHA256 mismatch: expected {expected_sha256}, got {actual}")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    subparsers = root.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("--lock", type=Path, required=True)
    inspect_parser.add_argument("--repo-root", type=Path, required=True)

    checkouts_parser = subparsers.add_parser("verify-checkouts")
    checkouts_parser.add_argument("--lock", type=Path, required=True)
    checkouts_parser.add_argument("--repo-root", type=Path, required=True)
    checkouts_parser.add_argument("--base", type=Path, required=True)
    checkouts_parser.add_argument("--moving", action="store_true")

    file_parser = subparsers.add_parser("verify-file")
    file_parser.add_argument("--path", type=Path, required=True)
    file_parser.add_argument("--sha256", required=True)
    file_parser.add_argument("--label", default="download")

    config_parser = subparsers.add_parser("write-nuget-config")
    config_parser.add_argument("--lock", type=Path, required=True)
    config_parser.add_argument("--repo-root", type=Path, required=True)
    config_parser.add_argument("--rid", required=True)
    config_parser.add_argument("--packages-root", type=Path, required=True)
    config_parser.add_argument("--output", type=Path, required=True)

    cache_parser = subparsers.add_parser("verify-nuget-cache")
    cache_parser.add_argument("--lock", type=Path, required=True)
    cache_parser.add_argument("--repo-root", type=Path, required=True)
    cache_parser.add_argument("--rid", required=True)
    cache_parser.add_argument("--packages-root", type=Path, required=True)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "verify-file":
            verify_file(args.path, args.sha256, args.label)
            return 0
        payload = validate_lock(args.lock.resolve(), args.repo_root.resolve())
        if args.command == "inspect":
            emit_tsv(payload, args.lock.resolve())
        elif args.command == "verify-checkouts":
            verify_checkouts(payload, args.base.resolve(), locked=not args.moving)
        elif args.command == "write-nuget-config":
            write_nuget_config(payload, args.repo_root.resolve(), args.rid, args.packages_root, args.output)
        elif args.command == "verify-nuget-cache":
            verify_nuget_cache(payload, args.repo_root.resolve(), args.rid, args.packages_root)
        else:
            raise LockError(f"unsupported command: {args.command}")
    except (LockError, OSError) as exc:
        print(f"source lock validation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
