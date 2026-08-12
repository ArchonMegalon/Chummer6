#!/usr/bin/env python3
"""Validate and consume the Chummer6 Linux reproducible-source lock."""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import html
import importlib.util
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from types import ModuleType
from typing import Any


CONTRACT = "chummer6.release-source-lock/v2"
SCHEMA_VERSION = 2
RELEASE_AUTHORITY_LOCK_CONTRACT = "chummer6.release-authority-lock/v1"
SDK_VERSION = "10.0.103"
SUPPORTED_RIDS = ("linux-x64", "linux-arm64")
REQUIRED_REPOSITORIES = {
    "chummer-core-engine": "chummer6-core",
    "chummer.run-services": "chummer6-hub",
    "chummer-hub-registry": "chummer6-hub-registry",
    "chummer-ui-kit": "chummer6-ui-kit",
    "chummer6-ui": "chummer6-ui",
}
EXPECTED_SDK_DECLARATIONS = {
    "chummer-core-engine": SDK_VERSION,
    "chummer.run-services": SDK_VERSION,
    "chummer-hub-registry": None,
    "chummer-ui-kit": None,
    "chummer6-ui": SDK_VERSION,
}
ROOT_PROJECT = "Chummer.Avalonia/Chummer.Avalonia.csproj"
DESKTOP_RUNTIME_PROJECT = "Chummer.Desktop.Runtime/Chummer.Desktop.Runtime.csproj"
PRESENTATION_PROJECT = "Chummer.Presentation/Chummer.Presentation.csproj"
PROJECT_LOCK_ORDER = (
    ROOT_PROJECT,
    DESKTOP_RUNTIME_PROJECT,
    PRESENTATION_PROJECT,
)
EXPECTED_DIRECT_PACKAGES = {
    "Avalonia": "11.3.7",
    "Avalonia.Desktop": "11.3.7",
    "Avalonia.Fonts.Inter": "11.3.7",
    "Avalonia.Themes.Fluent": "11.3.7",
    "Chummer.Application": "0.1.0-preview",
    "Chummer.Campaign.Contracts": "0.1.0-preview",
    "Chummer.Engine.Contracts": "5.225.0",
    "Chummer.Infrastructure": "0.1.0-preview",
    "Chummer.Rulesets.Hosting": "0.1.0-preview",
    "Chummer.Rulesets.Sr4": "0.1.0-preview",
    "Chummer.Rulesets.Sr5": "0.1.0-preview",
    "Chummer.Rulesets.Sr6": "0.1.0-preview",
    "Chummer.Run.Contracts": "0.1.0-preview",
    "Microsoft.Extensions.DependencyInjection": "10.0.0",
    "Tmds.DBus.Protocol": "0.21.3",
}
EXPECTED_PROJECTS = {"chummer.desktop.runtime", "chummer.presentation"}
EXPECTED_RID_TRANSITIVE = {
    "Avalonia.Angle.Windows.Natives",
    "Avalonia.Native",
    "HarfBuzzSharp.NativeAssets.Linux",
    "HarfBuzzSharp.NativeAssets.Win32",
    "HarfBuzzSharp.NativeAssets.macOS",
    "SkiaSharp.NativeAssets.Linux",
    "SkiaSharp.NativeAssets.Win32",
    "SkiaSharp.NativeAssets.macOS",
}
EXPECTED_DESKTOP_RUNTIME_DIRECT_PACKAGES = {
    "Chummer.Application": "0.1.0-preview",
    "Chummer.Campaign.Contracts": "0.1.0-preview",
    "Chummer.Engine.Contracts": "5.225.0",
    "Chummer.Hub.Registry.Contracts": "0.1.0-preview",
    "Chummer.Infrastructure": "0.1.0-preview",
    "Chummer.Rulesets.Hosting": "0.1.0-preview",
    "Chummer.Rulesets.Sr4": "0.1.0-preview",
    "Chummer.Rulesets.Sr5": "0.1.0-preview",
    "Chummer.Rulesets.Sr6": "0.1.0-preview",
    "Chummer.Run.Contracts": "0.1.0-preview",
    "Microsoft.Extensions.DependencyInjection": "10.0.0",
    "System.Security.Cryptography.ProtectedData": "10.0.0",
}
EXPECTED_PRESENTATION_DIRECT_PACKAGES = {
    "Chummer.Application": "0.1.0-preview",
    "Chummer.Campaign.Contracts": "0.1.0-preview",
    "Chummer.Engine.Contracts": "5.225.0",
    "Chummer.Infrastructure": "0.1.0-preview",
    "Chummer.Rulesets.Hosting": "0.1.0-preview",
    "Chummer.Rulesets.Sr4": "0.1.0-preview",
    "Chummer.Rulesets.Sr5": "0.1.0-preview",
    "Chummer.Rulesets.Sr6": "0.1.0-preview",
    "Chummer.Run.Contracts": "0.1.0-preview",
    "Chummer.Ui.Kit": "0.1.0-preview",
}


def project_dependency_ranges(packages: dict[str, str]) -> dict[str, str]:
    return {package_id: f"[{version}, )" for package_id, version in packages.items()}


EXPECTED_PROJECT_LOCKS = {
    ROOT_PROJECT: {
        "authorityStem": "avalonia",
        "direct": EXPECTED_DIRECT_PACKAGES,
        "packageCount": 39,
        "projectDependencies": {
            "chummer.desktop.runtime": {
                **project_dependency_ranges(EXPECTED_DESKTOP_RUNTIME_DIRECT_PACKAGES),
                "Chummer.Presentation": "[1.0.0, )",
            },
            "chummer.presentation": project_dependency_ranges(
                EXPECTED_PRESENTATION_DIRECT_PACKAGES
            ),
        },
        "ridTransitive": EXPECTED_RID_TRANSITIVE,
    },
    DESKTOP_RUNTIME_PROJECT: {
        "authorityStem": "desktop-runtime",
        "direct": EXPECTED_DESKTOP_RUNTIME_DIRECT_PACKAGES,
        "packageCount": 15,
        "projectDependencies": {
            "chummer.presentation": project_dependency_ranges(
                EXPECTED_PRESENTATION_DIRECT_PACKAGES
            )
        },
        "ridTransitive": set(),
    },
    PRESENTATION_PROJECT: {
        "authorityStem": "presentation",
        "direct": EXPECTED_PRESENTATION_DIRECT_PACKAGES,
        "packageCount": 14,
        "projectDependencies": {},
        "ridTransitive": set(),
    },
}
SDK_ARCHIVE_URLS = {
    rid: (
        "https://builds.dotnet.microsoft.com/dotnet/Sdk/10.0.103/"
        f"dotnet-sdk-10.0.103-{rid}.tar.gz"
    )
    for rid in SUPPORTED_RIDS
}
SDK_TOOL_PATHS = {
    "dotnet_host": "dotnet",
    "csc": "sdk/10.0.103/Roslyn/bincore/csc.dll",
    "msbuild": "sdk/10.0.103/Microsoft.Build.dll",
    "nuget_packaging": "sdk/10.0.103/NuGet.Packaging.dll",
}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SHA512_HEX_PATTERN = re.compile(r"^[0-9a-f]{128}$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SAFE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
PACKAGE_VERSION_PATTERN = re.compile(r"^[0-9A-Za-z][0-9A-Za-z.+-]*$")
PORTABILITY_MARKERS = ("/tmp/", "/var/tmp/", "/docker/", "/workspace/", "file://")


class LockError(ValueError):
    pass


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LockError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path, label: str = "JSON authority") -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8-sig"), object_pairs_hook=strict_object
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise LockError(f"cannot read {label} {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise LockError(f"{label} root must be an object")
    return value


def exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise LockError(
            f"{label} keys mismatch; missing={sorted(expected - set(value))}, "
            f"extra={sorted(set(value) - expected)}"
        )


def required_string(value: dict[str, Any], key: str, label: str) -> str:
    item = value.get(key)
    if (
        not isinstance(item, str)
        or not item
        or item != item.strip()
        or any(character in item for character in "\r\n\t\0")
    ):
        raise LockError(f"{label}.{key} must be a canonical non-empty string")
    return item


def required_sha256(value: dict[str, Any], key: str, label: str) -> str:
    item = required_string(value, key, label)
    if not SHA256_PATTERN.fullmatch(item):
        raise LockError(f"{label}.{key} is not a canonical SHA256")
    return item


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha512_file_hex(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json_exclusive(path: Path, payload: dict[str, Any], label: str) -> None:
    if path.exists() or path.is_symlink():
        raise LockError(f"refusing to replace {label}: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def archive_sha512(path: Path) -> str:
    return base64.b64encode(bytes.fromhex(sha512_file_hex(path))).decode("ascii")


def canonical_sha512(value: Any, label: str) -> str:
    if not isinstance(value, str) or value != value.strip():
        raise LockError(f"{label} must be canonical base64 SHA512")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise LockError(f"{label} is not canonical base64") from exc
    if len(decoded) != 64 or base64.b64encode(decoded).decode("ascii") != value:
        raise LockError(f"{label} is not a SHA512 digest")
    return value


def canonical_json_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def unsymlinked_cli_path(
    value: Path, label: str, *, kind: str, allow_missing: bool = False
) -> Path:
    """Return an absolute lexical path after lstat-checking every existing component."""
    if kind not in {"file", "directory", "path"}:
        raise LockError(f"internal path-kind error for {label}")
    path = value if value.is_absolute() else Path.cwd() / value
    path = Path(os.path.abspath(path))
    existing = Path(path.anchor)
    for index, part in enumerate(path.parts[1:]):
        existing = existing / part
        final = index == len(path.parts[1:]) - 1
        try:
            metadata = existing.lstat()
        except FileNotFoundError:
            if allow_missing:
                break
            raise LockError(f"{label} is missing: {path}")
        except OSError as exc:
            raise LockError(f"cannot inspect {label}: {path}") from exc
        if existing.is_symlink():
            raise LockError(f"{label} contains a symlinked path component")
        if not final and not stat.S_ISDIR(metadata.st_mode):
            raise LockError(f"{label} parent component is not a directory")
    if allow_missing and not path.exists():
        return path
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise LockError(f"cannot inspect {label}: {path}") from exc
    if path.is_symlink():
        raise LockError(f"{label} is symlinked")
    if kind == "file" and not stat.S_ISREG(metadata.st_mode):
        raise LockError(f"{label} is not a regular file")
    if kind == "directory" and not stat.S_ISDIR(metadata.st_mode):
        raise LockError(f"{label} is not a regular directory")
    return path


def resolve_repo_file(repo_root: Path, relative: str, label: str) -> Path:
    pure = PurePosixPath(relative)
    if pure.is_absolute() or not pure.parts or ".." in pure.parts or pure.as_posix() != relative:
        raise LockError(f"{label} must be a canonical repository-relative path")
    root = unsymlinked_cli_path(repo_root, "repository root", kind="directory")
    unresolved = root
    for index, part in enumerate(pure.parts):
        unresolved = unresolved / part
        try:
            metadata = unresolved.lstat()
        except OSError as exc:
            raise LockError(f"{label} is missing: {relative}") from exc
        if unresolved.is_symlink():
            raise LockError(f"{label} contains a symlinked path component")
        if index < len(pure.parts) - 1 and not stat.S_ISDIR(metadata.st_mode):
            raise LockError(f"{label} parent component is not a directory")
    resolved = unresolved.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise LockError(f"{label} escapes the repository root") from exc
    metadata = resolved.lstat()
    if not stat.S_ISREG(metadata.st_mode):
        raise LockError(f"{label} is not a regular checked file")
    return resolved


def checked_authority(
    repo_root: Path, descriptor: dict[str, Any], label: str
) -> tuple[Path, str]:
    path = resolve_repo_file(repo_root, required_string(descriptor, "path", label), label)
    expected = required_sha256(descriptor, "sha256", label)
    actual = sha256_file(path)
    if actual != expected:
        raise LockError(f"{label} SHA256 differs: expected {expected}, got {actual}")
    return path, expected


def portable_json(path: Path, label: str) -> None:
    text = path.read_text(encoding="utf-8-sig")
    lowered = text.lower()
    found = [marker for marker in PORTABILITY_MARKERS if marker in lowered]
    home = str(Path.home()).replace("\\", "/").lower().rstrip("/") + "/"
    if home != "/" and home in lowered:
        found.append("user-home")
    if re.search(r"/(?:home|users)/[^/\s\"']+/", lowered):
        found.append("generic-user-home")
    if re.search(r"(?:^|[\"'\s])[a-z]:[\\/]", lowered):
        found.append("windows-absolute")
    if re.search(r"\\\\[^\\\s]+\\[^\\\s]+", text):
        found.append("windows-unc")
    try:
        decoded = json.loads(text, object_pairs_hook=strict_object)
    except (json.JSONDecodeError, LockError) as exc:
        raise LockError(f"{label} is not strict JSON: {exc}") from exc

    def string_values(value: Any) -> list[str]:
        if isinstance(value, str):
            return [value]
        if isinstance(value, dict):
            return [item for child in value.values() for item in string_values(child)]
        if isinstance(value, list):
            return [item for child in value for item in string_values(child)]
        return []

    for value in string_values(decoded):
        normalized = value.replace("\\", "/").lower()
        if re.match(r"^[a-z]:/", normalized):
            found.append("windows-absolute")
        if value.startswith("\\\\") and len(value.split("\\")) >= 4:
            found.append("windows-unc")
        if re.search(r"/(?:home|users)/[^/\s\"']+/", normalized):
            found.append("generic-user-home")
        found.extend(marker for marker in PORTABILITY_MARKERS if marker in normalized)
    if found:
        raise LockError(f"{label} contains non-portable path markers: {sorted(set(found))}")


def sanitize_diagnostics(path: Path, redacted_paths: list[str]) -> None:
    metadata = path.lstat()
    if (
        path.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_size > 8 * 1024 * 1024
    ):
        raise LockError("generator diagnostic input is missing or unsafe")
    text = path.read_text(encoding="utf-8", errors="replace")
    for value in sorted(set(redacted_paths), key=len, reverse=True):
        if value:
            text = text.replace(value, "[redacted-path]")
            text = text.replace(value.replace("/", "\\"), "[redacted-path]")
    text = re.sub(
        r"(?i)(authorization\s*[:=]\s*)(?:bearer\s+)?[^\s\"']+",
        r"\1[redacted-secret]",
        text,
    )
    text = re.sub(
        r"(?i)(\bbearer\s+)[A-Za-z0-9._~+/=-]+",
        r"\1[redacted-secret]",
        text,
    )
    text = re.sub(
        r"(?i)(\b(?:api[_-]?key|access[_-]?token|token|password|client[_-]?secret)"
        r"\s*[:=]\s*)[^\s\"']+",
        r"\1[redacted-secret]",
        text,
    )
    text = re.sub(
        r"(?i)(https?://)[^/@\s:]+:[^/@\s]+@",
        r"\1[redacted-credentials]@",
        text,
    )
    text = re.sub(
        r"(?<![:A-Za-z0-9])/(?:[^\s\"':/]+/)+[^\s\"':]*",
        "[redacted-absolute-path]",
        text,
    )
    text = re.sub(
        r"(?i)(?<![A-Za-z0-9])[a-z]:[\\/](?:[^\s\"']+)",
        "[redacted-absolute-path]",
        text,
    )
    text = re.sub(
        r"\\\\[^\\\s\"']+\\[^\\\s\"']+(?:\\[^\\\s\"']+)*",
        "[redacted-absolute-path]",
        text,
    )
    sys.stdout.write(text)


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise LockError(f"cannot load checked module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def git_output(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        [
            "git",
            "-c",
            "gc.auto=0",
            "-c",
            "maintenance.auto=0",
            "-C",
            str(root),
            *arguments,
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=60,
        check=False,
    )
    if completed.returncode:
        raise LockError(
            f"git {' '.join(arguments)} failed for {root}: {completed.stdout.strip()}"
        )
    return completed.stdout.strip()


def git_blob_sha256(repo_root: Path, commit: str, relative: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), "show", f"{commit}:{relative}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    if completed.returncode:
        raise LockError(f"cannot read Git provenance {commit}:{relative}")
    return hashlib.sha256(completed.stdout).hexdigest()


def validate_dependency_map(value: Any, label: str) -> None:
    if not isinstance(value, dict):
        raise LockError(f"{label} must be an object")
    folded: set[str] = set()
    for package_id, version in value.items():
        if (
            not isinstance(package_id, str)
            or not SAFE_NAME_PATTERN.fullmatch(package_id)
            or package_id.casefold() in folded
            or not isinstance(version, str)
            or not version
            or version != version.strip()
        ):
            raise LockError(f"{label} contains an invalid dependency")
        folded.add(package_id.casefold())


def validate_package_lock(
    path: Path, rid: str, project: str = ROOT_PROJECT
) -> dict[tuple[str, str], dict[str, str]]:
    spec = EXPECTED_PROJECT_LOCKS.get(project)
    if spec is None:
        raise LockError(f"NuGet package lock project is not approved: {project}")
    lock_label = f"NuGet package lock for {rid}/{project}"
    payload = load_json(path, lock_label)
    exact_keys(payload, {"version", "dependencies"}, lock_label)
    if payload.get("version") != 1:
        raise LockError(f"{lock_label} must use version 1")
    dependencies = payload.get("dependencies")
    targets = {"net10.0", f"net10.0/{rid}"}
    if not isinstance(dependencies, dict) or set(dependencies) != targets:
        raise LockError(f"{lock_label} target set differs")
    packages: dict[tuple[str, str], dict[str, str]] = {}
    projects: dict[str, dict[str, str]] = {}
    direct: dict[str, str] = {}
    rid_transitive: set[str] = set()
    for target_name in sorted(targets):
        nodes = dependencies[target_name]
        if not isinstance(nodes, dict):
            raise LockError(f"NuGet package lock target {target_name} must be an object")
        seen_names: set[str] = set()
        for package_id, node in nodes.items():
            label = f"NuGet package lock {rid}/{target_name}/{package_id}"
            if (
                not isinstance(package_id, str)
                or not SAFE_NAME_PATTERN.fullmatch(package_id)
                or package_id.casefold() in seen_names
                or not isinstance(node, dict)
            ):
                raise LockError(f"{label} identity or row is invalid")
            seen_names.add(package_id.casefold())
            if not set(node).issubset(
                {"type", "requested", "resolved", "contentHash", "dependencies"}
            ):
                raise LockError(f"{label} contains unsupported fields")
            node_type = node.get("type")
            if node_type not in {"Direct", "Transitive", "Project"}:
                raise LockError(f"{label} has an unsupported type")
            if "dependencies" in node:
                validate_dependency_map(node["dependencies"], f"{label}.dependencies")
            if node_type == "Project":
                if target_name != "net10.0" or set(node) != {"type", "dependencies"}:
                    raise LockError(f"{label} project row is not canonical")
                projects[package_id] = node["dependencies"]
                continue
            required = {"type", "resolved", "contentHash"}
            if node_type == "Direct":
                required.add("requested")
            if not required.issubset(node) or (
                node_type == "Transitive" and "requested" in node
            ):
                raise LockError(f"{label} locked package fields differ")
            version = node.get("resolved")
            if not isinstance(version, str) or not PACKAGE_VERSION_PATTERN.fullmatch(version):
                raise LockError(f"{label}.resolved is invalid")
            content_hash = canonical_sha512(node.get("contentHash"), f"{label}.contentHash")
            if node_type == "Direct":
                requested = node.get("requested")
                if not isinstance(requested, str) or not requested or requested != requested.strip():
                    raise LockError(f"{label}.requested is invalid")
                direct[package_id] = version
            elif target_name == f"net10.0/{rid}":
                rid_transitive.add(package_id)
            identity = (package_id.casefold(), version.casefold())
            row = {
                "packageId": package_id,
                "version": version,
                "contentHash": content_hash,
            }
            previous = packages.get(identity)
            if previous is not None and previous != row:
                raise LockError(f"{label} disagrees across target graphs")
            packages[identity] = row
    if direct != spec["direct"]:
        raise LockError(
            f"{lock_label} direct graph differs; "
            f"expected={spec['direct']}, got={direct}"
        )
    if projects != spec["projectDependencies"]:
        raise LockError(f"{lock_label} project graph differs: {projects}")
    if rid_transitive != spec["ridTransitive"]:
        raise LockError(f"{lock_label} RID graph differs: {rid_transitive}")
    if len(packages) != spec["packageCount"]:
        raise LockError(
            f"{lock_label} must resolve exactly {spec['packageCount']} packages"
        )
    return packages


def validate_project_lock_closure(
    locks: dict[str, dict[tuple[str, str], dict[str, str]]], rid: str
) -> dict[tuple[str, str], dict[str, str]]:
    if tuple(locks) != PROJECT_LOCK_ORDER:
        raise LockError(f"NuGet package lock {rid} project closure order differs")
    root = locks[ROOT_PROJECT]
    for project, packages in locks.items():
        for identity, row in packages.items():
            root_row = root.get(identity)
            if root_row != row:
                raise LockError(
                    f"NuGet package lock {rid}/{project} package closure or "
                    f"content hash differs: {row['packageId']} {row['version']}"
                )
    return root


def validate_basic_package_row(row: Any, label: str) -> tuple[str, str]:
    if not isinstance(row, dict):
        raise LockError(f"{label} must be an object")
    owner_fields = {"commit", "internalDependencies", "license", "project", "repository"}
    basic_fields = {
        "archiveSha512",
        "fileName",
        "packageId",
        "sha256",
        "sizeBytes",
        "version",
    }
    if frozenset(row) not in {
        frozenset(basic_fields),
        frozenset(basic_fields | owner_fields),
    }:
        raise LockError(f"{label} package schema differs")
    file_name = required_string(row, "fileName", label)
    package_id = required_string(row, "packageId", label)
    version = required_string(row, "version", label)
    if (
        not SAFE_NAME_PATTERN.fullmatch(file_name)
        or not SAFE_NAME_PATTERN.fullmatch(package_id)
        or not PACKAGE_VERSION_PATTERN.fullmatch(version)
        or file_name
        not in {
            f"{package_id}.{version}.nupkg",
            f"{package_id.lower()}.{version}.nupkg",
        }
        or not SHA256_PATTERN.fullmatch(str(row.get("sha256")))
        or not isinstance(row.get("sizeBytes"), int)
        or isinstance(row.get("sizeBytes"), bool)
        or row["sizeBytes"] <= 0
    ):
        raise LockError(f"{label} package identity or bytes are invalid")
    canonical_sha512(row.get("archiveSha512"), f"{label}.archiveSha512")
    if owner_fields.issubset(row):
        if (
            not COMMIT_PATTERN.fullmatch(str(row["commit"]))
            or not isinstance(row["internalDependencies"], list)
            or not isinstance(row["license"], dict)
            or set(row["license"]) != {"type", "value"}
            or row["license"].get("type") not in {"expression", "file"}
            or not isinstance(row["license"].get("value"), str)
            or not row["license"]["value"]
            or not isinstance(row["project"], str)
            or not row["project"]
            or not isinstance(row["repository"], str)
            or not row["repository"].startswith("https://github.com/ArchonMegalon/")
            or not row["repository"].endswith(".git")
        ):
            raise LockError(f"{label} owner provenance is invalid")
        dependencies: set[tuple[str, str]] = set()
        for dep_index, dependency in enumerate(row["internalDependencies"]):
            if (
                not isinstance(dependency, dict)
                or set(dependency) != {"packageId", "version"}
                or not isinstance(dependency.get("packageId"), str)
                or not isinstance(dependency.get("version"), str)
            ):
                raise LockError(f"{label} dependency {dep_index} is invalid")
            identity = (dependency["packageId"].casefold(), dependency["version"])
            if identity in dependencies:
                raise LockError(f"{label} contains a duplicate internal dependency")
            dependencies.add(identity)
    return package_id.casefold(), version.casefold()


def validate_base_feed_inventory(
    payload: dict[str, Any], package_plane: dict[str, Any]
) -> dict[tuple[str, str], dict[str, Any]]:
    exact_keys(
        payload,
        {
            "contract",
            "hubCanonicalFeed",
            "normalizationContract",
            "packageCount",
            "packageInventorySha256",
            "packages",
            "uiCommit",
            "uiLockSha256",
            "uiVerifierSha256",
            "upstreamVerification",
        },
        "canonical feed inventory",
    )
    packages = payload.get("packages")
    if (
        payload.get("contract") != "chummer6.normalized-same-run-feed/v1"
        or payload.get("normalizationContract")
        != package_plane["composer"]["normalizationContract"]
        or payload.get("packageCount") != 96
        or not isinstance(packages, list)
        or len(packages) != 96
        or payload.get("packageInventorySha256") != canonical_json_sha256(packages)
        or payload.get("packageInventorySha256")
        != package_plane["feedInventory"]["packageInventorySha256"]
        or payload.get("uiCommit")
        != package_plane["finalUiVerificationReceipt"]["consumerCommit"]
        or payload.get("uiLockSha256") != package_plane["uiLock"]["sha256"]
        or payload.get("uiVerifierSha256") != package_plane["uiVerifier"]["sha256"]
    ):
        raise LockError("canonical feed inventory bindings differ")
    if payload.get("hubCanonicalFeed") != {
        "inventorySha256": package_plane["hubCanonicalFeed"]["inventorySha256"],
        "lockSha256": package_plane["hubCanonicalFeed"]["lockSha256"],
        "producerSha256": package_plane["hubCanonicalFeed"]["producerSha256"],
    }:
        raise LockError("canonical feed Hub authority differs")
    receipt = package_plane["finalUiVerificationReceipt"]
    if payload.get("upstreamVerification") != {
        "consumerCommit": receipt["consumerCommit"],
        "contractName": receipt["contractName"],
        "contractVersion": receipt["contractVersion"],
        "packageCount": receipt["packageCount"],
        "packageFeedInventorySha256": receipt["packageFeedInventorySha256"],
        "receiptSha256": receipt["sha256"],
        "status": receipt["status"],
    }:
        raise LockError("canonical feed upstream receipt binding differs")
    observed: dict[tuple[str, str], dict[str, Any]] = {}
    file_names: set[str] = set()
    for index, row in enumerate(packages):
        identity = validate_basic_package_row(row, f"canonical feed package {index}")
        if identity in observed or row["fileName"].casefold() in file_names:
            raise LockError("canonical feed contains a duplicate package")
        observed[identity] = row
        file_names.add(row["fileName"].casefold())
    return observed


def expected_runtime_identities() -> set[tuple[str, str]]:
    return {
        (f"microsoft.aspnetcore.app.runtime.{rid}", "10.0.3")
        for rid in SUPPORTED_RIDS
    } | {
        (f"microsoft.netcore.app.runtime.{rid}", "10.0.3")
        for rid in SUPPORTED_RIDS
    } | {
        (f"microsoft.netcore.app.host.{rid}", "10.0.3")
        for rid in SUPPORTED_RIDS
    }


def validate_runtime_authority(payload: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    exact_keys(payload, {"contract", "packages"}, "runtime package authority")
    rows = payload.get("packages")
    if (
        payload.get("contract") != "chummer6.linux-runtime-package-authority/v1"
        or not isinstance(rows, list)
        or len(rows) != 6
    ):
        raise LockError("runtime package authority must contain exactly six rows")
    observed: dict[tuple[str, str], dict[str, Any]] = {}
    for index, row in enumerate(rows):
        label = f"runtime package authority row {index}"
        if not isinstance(row, dict):
            raise LockError(f"{label} must be an object")
        exact_keys(
            row,
            {
                "contentHash",
                "fileName",
                "packageId",
                "rid",
                "sha256",
                "sha512",
                "sizeBytes",
                "source",
                "version",
            },
            label,
        )
        package_id = required_string(row, "packageId", label)
        version = required_string(row, "version", label)
        rid = required_string(row, "rid", label)
        identity = (package_id.casefold(), version.casefold())
        expected_url = (
            "https://api.nuget.org/v3-flatcontainer/"
            f"{package_id.lower()}/{version}/{package_id.lower()}.{version}.nupkg"
        )
        if (
            identity not in expected_runtime_identities()
            or identity in observed
            or rid not in SUPPORTED_RIDS
            or not package_id.casefold().endswith(rid)
            or row.get("fileName") != f"{package_id.lower()}.{version}.nupkg"
            or row.get("source") != expected_url
            or not isinstance(row.get("contentHash"), str)
            or not SHA256_PATTERN.fullmatch(str(row.get("sha256")))
            or not SHA512_HEX_PATTERN.fullmatch(str(row.get("sha512")))
            or not isinstance(row.get("sizeBytes"), int)
            or isinstance(row.get("sizeBytes"), bool)
            or row["sizeBytes"] <= 0
        ):
            raise LockError(f"{label} is not an exact approved runtime input")
        canonical_sha512(row["contentHash"], f"{label}.contentHash")
        observed[identity] = row
    if set(observed) != expected_runtime_identities():
        raise LockError("runtime package authority identity set differs")
    return observed


def validate_rid_feed_inventory(
    payload: dict[str, Any],
    rid: str,
    base_payload: dict[str, Any],
    base_file_sha256: str,
    runtime_rows: dict[tuple[str, str], dict[str, Any]],
    runtime_file_sha256: str,
) -> dict[tuple[str, str], dict[str, Any]]:
    exact_keys(
        payload,
        {
            "baseFeedFileSha256",
            "baseFeedInventorySha256",
            "contract",
            "packageCount",
            "packages",
            "restoreFeedInventorySha256",
            "runtimeIdentifier",
            "runtimePackageAuthoritySha256",
        },
        f"{rid} restore feed inventory",
    )
    packages = payload.get("packages")
    if (
        payload.get("contract") != "chummer6.rid-restore-feed/v1"
        or payload.get("runtimeIdentifier") != rid
        or payload.get("packageCount") != 99
        or not isinstance(packages, list)
        or len(packages) != 99
        or payload.get("baseFeedFileSha256") != base_file_sha256
        or payload.get("baseFeedInventorySha256")
        != base_payload["packageInventorySha256"]
        or payload.get("runtimePackageAuthoritySha256") != runtime_file_sha256
        or payload.get("restoreFeedInventorySha256") != canonical_json_sha256(packages)
    ):
        raise LockError(f"{rid} restore feed bindings differ")
    observed: dict[tuple[str, str], dict[str, Any]] = {}
    file_names: set[str] = set()
    for index, row in enumerate(packages):
        identity = validate_basic_package_row(row, f"{rid} feed package {index}")
        if identity in observed or row["fileName"].casefold() in file_names:
            raise LockError(f"{rid} restore feed contains a duplicate package")
        observed[identity] = row
        file_names.add(row["fileName"].casefold())
    base_by_identity = {
        (row["packageId"].casefold(), row["version"].casefold()): row
        for row in base_payload["packages"]
    }
    if any(observed.get(identity) != row for identity, row in base_by_identity.items()):
        raise LockError(f"{rid} restore feed does not carry the exact canonical base")
    expected_runtime = {
        identity: row
        for identity, row in runtime_rows.items()
        if row["rid"] == rid
    }
    projected_base = [
        row
        for row in packages
        if (row["packageId"].casefold(), row["version"].casefold())
        not in expected_runtime
    ]
    if projected_base != base_payload["packages"]:
        raise LockError(f"{rid} restore feed canonical order/projection differs")
    appended = observed.keys() - base_by_identity.keys()
    if appended != set(expected_runtime):
        raise LockError(f"{rid} restore feed runtime identity set differs")
    for identity, authority in expected_runtime.items():
        feed_row = observed[identity]
        if feed_row != {
            "archiveSha512": base64.b64encode(
                bytes.fromhex(authority["sha512"])
            ).decode("ascii"),
            "fileName": authority["fileName"],
            "packageId": authority["packageId"],
            "sha256": authority["sha256"],
            "sizeBytes": authority["sizeBytes"],
            "version": authority["version"],
        }:
            raise LockError(f"{rid} restore feed runtime bytes differ")
    return observed


def validate_feed_directory(
    feed: Path, rows: dict[tuple[str, str], dict[str, Any]], label: str
) -> None:
    if not feed.is_absolute() or not feed.is_dir() or feed.is_symlink():
        raise LockError(f"{label} must be an absolute regular directory")
    entries = list(feed.iterdir())
    expected_names = {row["fileName"] for row in rows.values()}
    if {entry.name for entry in entries} != expected_names:
        raise LockError(f"{label} file set differs from its inventory")
    for row in rows.values():
        path = feed / row["fileName"]
        metadata = path.lstat()
        if (
            path.is_symlink()
            or not stat.S_ISREG(metadata.st_mode)
            or metadata.st_size != row["sizeBytes"]
            or sha256_file(path) != row["sha256"]
        ):
            raise LockError(f"{label} bytes differ: {row['fileName']}")


def cache_expected_rows(
    package_rows: dict[tuple[str, str], dict[str, str]],
    rid_feed_rows: dict[tuple[str, str], dict[str, Any]],
    runtime_rows: dict[tuple[str, str], dict[str, Any]],
    rid: str,
    feed: Path | None = None,
    include_app_host: bool = False,
) -> list[dict[str, str]]:
    expected = dict(package_rows)
    runtime_ids = [
        f"Microsoft.AspNetCore.App.Runtime.{rid}",
        f"Microsoft.NETCore.App.Runtime.{rid}",
    ]
    if include_app_host:
        runtime_ids.append(f"Microsoft.NETCore.App.Host.{rid}")
    for package_id in runtime_ids:
        identity = (package_id.casefold(), "10.0.3")
        authority = runtime_rows.get(identity)
        if authority is None:
            raise LockError(f"cache expectation lacks {package_id}")
        expected[identity] = {
            "packageId": authority["packageId"],
            "version": authority["version"],
            "contentHash": authority["contentHash"],
        }
    expected_count = 42 if include_app_host else 41
    if len(expected) != expected_count:
        raise LockError(
            f"cache expectation must contain exactly {expected_count} packages"
        )
    rows: list[dict[str, str]] = []
    for identity, package in expected.items():
        feed_row = rid_feed_rows.get(identity)
        if feed_row is None:
            raise LockError(f"RID feed lacks cache package {package['packageId']}")
        archive_digest = feed_row["archiveSha512"]
        if feed is not None:
            observed_archive = archive_sha512(feed / feed_row["fileName"])
            if observed_archive != archive_digest:
                raise LockError(
                    f"NuGet archive SHA512 differs from feed bytes: {package['packageId']}"
                )
        rows.append(
            {
                "archiveSha512": archive_digest,
                "contentHash": package["contentHash"],
                "packageId": package["packageId"],
                "sourceSha256": feed_row["sha256"],
                "version": package["version"],
            }
        )
    return sorted(rows, key=lambda row: (row["packageId"].casefold(), row["version"].casefold()))


def validate_cache_inventory(
    payload: dict[str, Any],
    rid: str,
    package_lock_sha256: str,
    base_feed_digest: str,
    restore_feed_digest: str,
    runtime_authority_sha256: str,
    expected_rows: list[dict[str, str]],
    model: dict[str, Any],
) -> None:
    exact_keys(
        payload,
        {
            "contract",
            "runtimeIdentifier",
            "packageLockSha256",
            "baseFeedInventorySha256",
            "restoreFeedInventorySha256",
            "runtimePackageAuthoritySha256",
            "packageCount",
            "packages",
            "hostRid",
            "sdkRid",
            "targetRid",
            "executionModel",
            "sdkExecuted",
            "nativeTargetExecuted",
            "observations",
        },
        f"{rid} native NuGet cache inventory",
    )
    packages = payload.get("packages")
    if (
        payload.get("contract") != "chummer6.rid-nuget-cache-inventory/v1"
        or payload.get("runtimeIdentifier") != rid
        or payload.get("packageLockSha256") != package_lock_sha256
        or payload.get("baseFeedInventorySha256") != base_feed_digest
        or payload.get("restoreFeedInventorySha256") != restore_feed_digest
        or payload.get("runtimePackageAuthoritySha256")
        != runtime_authority_sha256
        or payload.get("packageCount") != len(expected_rows)
        or not isinstance(packages, list)
        or packages != expected_rows
        or payload.get("hostRid") != model["hostRid"]
        or payload.get("sdkRid") != model["sdkRid"]
        or payload.get("targetRid") != model["targetRid"]
        or payload.get("executionModel") != model["executionModel"]
        or payload.get("sdkExecuted") is not True
        or payload.get("nativeTargetExecuted") is not False
    ):
        raise LockError(f"{rid} native NuGet cache inventory differs")
    inventory_digest = canonical_json_sha256(expected_rows)
    if payload.get("observations") != [
        {
            "packageCount": len(expected_rows),
            "packageInventorySha256": inventory_digest,
            "phase": "restore",
        },
        {
            "packageCount": len(expected_rows),
            "packageInventorySha256": inventory_digest,
            "phase": "post_publish",
        },
    ]:
        raise LockError(f"{rid} cache phase observations differ")
    for index, row in enumerate(packages):
        if not isinstance(row, dict):
            raise LockError(f"{rid} cache row {index} must be an object")
        exact_keys(
            row,
            {"packageId", "version", "contentHash", "archiveSha512", "sourceSha256"},
            f"{rid} cache row {index}",
        )
        canonical_sha512(row.get("contentHash"), f"{rid} cache contentHash {index}")
        canonical_sha512(row.get("archiveSha512"), f"{rid} cache archiveSha512 {index}")
        if not SHA256_PATTERN.fullmatch(str(row.get("sourceSha256"))):
            raise LockError(f"{rid} cache row {index} digest differs")


def validate_cache_observation_proof(
    payload: dict[str, Any],
    rid: str,
    model: dict[str, str],
    cache_authority: str,
    cache_sha256: str,
    cache_inventory: dict[str, Any],
    sdk_authority_sha256: str,
) -> None:
    exact_keys(
        payload,
        {
            "cacheInventoryAuthority",
            "cacheInventorySha256",
            "contract",
            "executionModel",
            "hostRid",
            "nativeTargetExecuted",
            "observations",
            "packageCount",
            "packageInventorySha256",
            "phaseRootsDistinct",
            "releaseEvidenceEligible",
            "runtimeIdentifier",
            "sdkAuthoritySha256",
            "sdkExecuted",
            "sdkRid",
            "sdkVersion",
            "status",
            "targetRid",
        },
        f"{rid} cache observation proof",
    )
    if (
        payload.get("contract") != "chummer6.rid-cache-observation-proof/v1"
        or payload.get("status") != "passed"
        or payload.get("releaseEvidenceEligible") is not False
        or payload.get("runtimeIdentifier") != rid
        or payload.get("cacheInventoryAuthority") != cache_authority
        or payload.get("cacheInventorySha256") != cache_sha256
        or payload.get("packageCount") != cache_inventory["packageCount"]
        or payload.get("packageInventorySha256")
        != canonical_json_sha256(cache_inventory["packages"])
        or payload.get("observations") != cache_inventory["observations"]
        or payload.get("phaseRootsDistinct") is not True
        or payload.get("hostRid") != model["hostRid"]
        or payload.get("sdkRid") != model["sdkRid"]
        or payload.get("targetRid") != model["targetRid"]
        or payload.get("executionModel") != model["executionModel"]
        or payload.get("sdkVersion") != SDK_VERSION
        or payload.get("sdkAuthoritySha256") != sdk_authority_sha256
        or payload.get("sdkExecuted") is not True
        or payload.get("nativeTargetExecuted") is not False
    ):
        raise LockError(f"{rid} cache observation proof differs")


def validate_sdk_authority(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    exact_keys(
        payload,
        {"archives", "contract", "legacyInstallerReference", "sdkVersion"},
        "SDK archive authority",
    )
    archives = payload.get("archives")
    if (
        payload.get("contract") != "chummer6.dotnet-sdk-archive-authority/v1"
        or payload.get("sdkVersion") != SDK_VERSION
        or payload.get("legacyInstallerReference")
        != {
            "executionAllowed": False,
            "sha256": "082f7685e156738a1b2e2ed8381a621870d4ce8e8c59278034556f05c186eb2e",
            "url": "https://dot.net/v1/dotnet-install.sh",
        }
        or not isinstance(archives, list)
        or len(archives) != 2
    ):
        raise LockError("SDK archive authority contract differs")
    observed: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(archives):
        label = f"SDK archive row {index}"
        if not isinstance(row, dict):
            raise LockError(f"{label} must be an object")
        exact_keys(
            row,
            {
                "fileName",
                "rid",
                "sha256",
                "sha512",
                "sizeBytes",
                "source",
                "toolchainFiles",
                "version",
            },
            label,
        )
        rid = required_string(row, "rid", label)
        tools = row.get("toolchainFiles")
        if (
            rid not in SUPPORTED_RIDS
            or rid in observed
            or row.get("version") != SDK_VERSION
            or row.get("fileName") != f"dotnet-sdk-{SDK_VERSION}-{rid}.tar.gz"
            or row.get("source") != SDK_ARCHIVE_URLS[rid]
            or not SHA256_PATTERN.fullmatch(str(row.get("sha256")))
            or not SHA512_HEX_PATTERN.fullmatch(str(row.get("sha512")))
            or not isinstance(row.get("sizeBytes"), int)
            or isinstance(row.get("sizeBytes"), bool)
            or row["sizeBytes"] <= 0
            or not isinstance(tools, list)
            or len(tools) != 4
        ):
            raise LockError(f"{label} is not exact")
        tool_names: set[str] = set()
        for tool_index, tool in enumerate(tools):
            tool_label = f"{label}.toolchainFiles[{tool_index}]"
            if not isinstance(tool, dict):
                raise LockError(f"{tool_label} must be an object")
            exact_keys(tool, {"name", "path", "sha256", "sizeBytes"}, tool_label)
            name = required_string(tool, "name", tool_label)
            if (
                name in tool_names
                or SDK_TOOL_PATHS.get(name) != tool.get("path")
                or not SHA256_PATTERN.fullmatch(str(tool.get("sha256")))
                or not isinstance(tool.get("sizeBytes"), int)
                or isinstance(tool.get("sizeBytes"), bool)
                or tool["sizeBytes"] <= 0
            ):
                raise LockError(f"{tool_label} differs")
            tool_names.add(name)
        if tool_names != set(SDK_TOOL_PATHS):
            raise LockError(f"{label} toolchain set differs")
        observed[rid] = row
    if set(observed) != set(SUPPORTED_RIDS):
        raise LockError("SDK authority does not cover both Linux RIDs")
    return observed


def validate_final_ui_receipt(
    payload: dict[str, Any],
    descriptor: dict[str, Any],
    repositories: dict[str, dict[str, Any]],
    package_plane: dict[str, Any],
    sdk_rows: dict[str, dict[str, Any]],
) -> None:
    if (
        payload.get("contractName") != descriptor["contractName"]
        or payload.get("contractVersion") != descriptor["contractVersion"]
        or payload.get("consumerCommit") != descriptor["consumerCommit"]
        or payload.get("status") != descriptor["status"]
        or payload.get("packageFeedInventorySha256")
        != descriptor["packageFeedInventorySha256"]
        or payload.get("status") != "passed"
        or payload.get("mode") != "integration"
        or payload.get("stubPackagesAllowed") is not False
        or payload.get("localCompatibilityTree") is not False
        or payload.get("packageCacheWasFresh") is not True
        or payload.get("sdkVersion") != SDK_VERSION
        or payload.get("sdkArchiveSha512") != sdk_rows["linux-x64"]["sha512"]
        or payload.get("packageSources") != ["same-run-local-feed"]
        or not isinstance(payload.get("packageInventory"), list)
        or len(payload["packageInventory"]) != descriptor["packageCount"]
        or canonical_json_sha256(payload["packageInventory"])
        != payload["packageFeedInventorySha256"]
    ):
        raise LockError("final UI package-plane receipt differs")
    expected_owners = [
        {
            "commit": repositories[directory]["commit"],
            "directory": directory,
            "repository": repositories[directory]["url"],
            "sdkVersion": SDK_VERSION,
        }
        for directory in (
            "chummer-core-engine",
            "chummer.run-services",
            "chummer-hub-registry",
            "chummer-ui-kit",
        )
    ]
    if payload.get("ownerSources") != expected_owners:
        raise LockError("final UI receipt owner source authorities differ")
    hub = package_plane["hubCanonicalFeed"]
    if payload.get("canonicalOwnerFeed") != {
        "inventoryContract": hub["inventoryContract"],
        "inventorySha256": hub["inventorySha256"],
        "lockContract": hub["lockContract"],
        "lockSha256": hub["lockSha256"],
        "ownerCommit": hub["ownerCommit"],
        "packageCount": hub["packageCount"],
        "packages": hub["packages"],
        "producerPath": hub["producerPath"],
        "producerSha256": hub["producerSha256"],
        "projectLockFilesEnforced": True,
        "status": "passed",
    }:
        raise LockError("final UI receipt Hub v3 canonical authority differs")


def validate_lock(path: Path, repo_root: Path) -> dict[str, Any]:
    payload = load_json(path, "release source lock")
    exact_keys(
        payload,
        {
            "contract",
            "schemaVersion",
            "releaseStatus",
            "releaseEvidenceEligible",
            "repositories",
            "dotnet",
            "packagePlane",
            "nuget",
            "releaseManifest",
            "sourceLockVerifier",
            "buildScript",
        },
        "release source lock",
    )
    if (
        payload.get("contract") != CONTRACT
        or payload.get("schemaVersion") != SCHEMA_VERSION
        or payload.get("releaseStatus") != "review_required"
        or payload.get("releaseEvidenceEligible") is not False
    ):
        raise LockError("release source lock must remain review-required/ineligible v2")

    repository_rows = payload.get("repositories")
    if not isinstance(repository_rows, list) or len(repository_rows) != 5:
        raise LockError("source lock must carry exactly five repositories")
    repositories: dict[str, dict[str, Any]] = {}
    names: set[str] = set()
    for index, row in enumerate(repository_rows):
        label = f"repositories[{index}]"
        if not isinstance(row, dict):
            raise LockError(f"{label} must be an object")
        exact_keys(row, {"directory", "name", "url", "commit", "globalJsonSdkVersion"}, label)
        directory = required_string(row, "directory", label)
        name = required_string(row, "name", label)
        if (
            REQUIRED_REPOSITORIES.get(directory) != name
            or directory in repositories
            or name in names
            or row.get("url") != f"https://github.com/ArchonMegalon/{name}.git"
            or not COMMIT_PATTERN.fullmatch(str(row.get("commit")))
            or row.get("globalJsonSdkVersion") != EXPECTED_SDK_DECLARATIONS[directory]
        ):
            raise LockError(f"{label} repository authority differs")
        repositories[directory] = row
        names.add(name)
    if set(repositories) != set(REQUIRED_REPOSITORIES):
        raise LockError("repository owner set differs")

    source_lock_verifier = payload.get("sourceLockVerifier")
    if not isinstance(source_lock_verifier, dict):
        raise LockError("sourceLockVerifier must be an object")
    exact_keys(source_lock_verifier, {"path", "sha256"}, "sourceLockVerifier")
    if source_lock_verifier.get("path") != "scripts/verify_linux_source_lock.py":
        raise LockError("sourceLockVerifier path differs")
    checked_authority(repo_root, source_lock_verifier, "sourceLockVerifier")

    dotnet = payload.get("dotnet")
    if not isinstance(dotnet, dict):
        raise LockError("dotnet must be an object")
    exact_keys(dotnet, {"sdkVersion", "authority"}, "dotnet")
    if dotnet.get("sdkVersion") != SDK_VERSION or not isinstance(dotnet.get("authority"), dict):
        raise LockError("dotnet SDK authority differs")
    exact_keys(dotnet["authority"], {"path", "sha256"}, "dotnet.authority")
    sdk_path, sdk_authority_file_sha = checked_authority(
        repo_root, dotnet["authority"], "dotnet.authority"
    )
    portable_json(sdk_path, "SDK authority")
    sdk_rows = validate_sdk_authority(load_json(sdk_path, "SDK authority"))

    package_plane = payload.get("packagePlane")
    if not isinstance(package_plane, dict):
        raise LockError("packagePlane must be an object")
    exact_keys(
        package_plane,
        {
            "uiLock",
            "uiVerifier",
            "finalUiVerificationReceipt",
            "hubCanonicalFeed",
            "composer",
            "feedInventory",
            "normalizationProof",
            "runtimePackageAuthority",
        },
        "packagePlane",
    )
    ui_lock = package_plane.get("uiLock")
    ui_verifier = package_plane.get("uiVerifier")
    receipt_descriptor = package_plane.get("finalUiVerificationReceipt")
    hub_feed = package_plane.get("hubCanonicalFeed")
    composer_descriptor = package_plane.get("composer")
    feed_descriptor = package_plane.get("feedInventory")
    proof_descriptor = package_plane.get("normalizationProof")
    runtime_descriptor = package_plane.get("runtimePackageAuthority")
    if not all(
        isinstance(row, dict)
        for row in (
            ui_lock,
            ui_verifier,
            receipt_descriptor,
            hub_feed,
            composer_descriptor,
            feed_descriptor,
            proof_descriptor,
            runtime_descriptor,
        )
    ):
        raise LockError("packagePlane descriptors must be objects")
    exact_keys(ui_lock, {"path", "sha256", "contractName", "contractVersion"}, "packagePlane.uiLock")
    if (
        ui_lock.get("path") != "config/package-plane.lock.json"
        or ui_lock.get("contractName") != "chummer6-ui.fresh-package-plane-lock"
        or ui_lock.get("contractVersion") != 5
        or not SHA256_PATTERN.fullmatch(str(ui_lock.get("sha256")))
    ):
        raise LockError("UI v5 lock descriptor differs")
    exact_keys(ui_verifier, {"path", "sha256"}, "packagePlane.uiVerifier")
    if (
        ui_verifier.get("path")
        != "scripts/ai/verify_fresh_checkout_package_plane.py"
        or not SHA256_PATTERN.fullmatch(str(ui_verifier.get("sha256")))
    ):
        raise LockError("UI v5 verifier descriptor differs")
    exact_keys(
        receipt_descriptor,
        {
            "path",
            "sha256",
            "consumerCommit",
            "contractName",
            "contractVersion",
            "packageFeedInventorySha256",
            "packageCount",
            "status",
        },
        "packagePlane.finalUiVerificationReceipt",
    )
    receipt_path, _ = checked_authority(
        repo_root, receipt_descriptor, "packagePlane.finalUiVerificationReceipt"
    )
    portable_json(receipt_path, "final UI verification receipt")
    if (
        receipt_descriptor.get("consumerCommit")
        != repositories["chummer6-ui"]["commit"]
        or receipt_descriptor.get("contractName")
        != "chummer6-ui.fresh-package-plane-verification"
        or receipt_descriptor.get("contractVersion") != 5
        or receipt_descriptor.get("packageCount") != 96
        or receipt_descriptor.get("status") != "passed"
        or not SHA256_PATTERN.fullmatch(
            str(receipt_descriptor.get("packageFeedInventorySha256"))
        )
    ):
        raise LockError("final UI receipt descriptor differs")
    exact_keys(
        hub_feed,
        {
            "ownerDirectory",
            "ownerCommit",
            "lockPath",
            "lockSha256",
            "lockContract",
            "producerPath",
            "producerSha256",
            "inventoryContract",
            "inventorySha256",
            "packageCount",
            "packages",
        },
        "packagePlane.hubCanonicalFeed",
    )
    if (
        hub_feed.get("ownerDirectory") != "chummer.run-services"
        or hub_feed.get("ownerCommit")
        != repositories["chummer.run-services"]["commit"]
        or hub_feed.get("lockPath") != "eng/package-plane.lock.json"
        or hub_feed.get("lockContract") != "chummer-hub.package-plane-lock/v3"
        or hub_feed.get("producerPath")
        != "scripts/ai/bootstrap-hub-package-feed.py"
        or hub_feed.get("inventoryContract")
        != "chummer-hub.external-package-inventory/v2"
        or hub_feed.get("packageCount") != 3
        or not isinstance(hub_feed.get("packages"), list)
        or len(hub_feed["packages"]) != 3
        or any(
            not SHA256_PATTERN.fullmatch(str(hub_feed.get(key)))
            for key in ("lockSha256", "producerSha256", "inventorySha256")
        )
    ):
        raise LockError("Hub v3 package authority differs")
    for index, row in enumerate(hub_feed["packages"]):
        if (
            not isinstance(row, dict)
            or set(row) != {"fileName", "sha256", "sizeBytes"}
            or not SAFE_NAME_PATTERN.fullmatch(str(row.get("fileName")))
            or not SHA256_PATTERN.fullmatch(str(row.get("sha256")))
            or not isinstance(row.get("sizeBytes"), int)
            or isinstance(row.get("sizeBytes"), bool)
            or row["sizeBytes"] <= 0
        ):
            raise LockError(f"Hub canonical package row {index} differs")
    ui_receipt_payload = load_json(receipt_path, "final UI receipt")
    validate_final_ui_receipt(
        ui_receipt_payload,
        receipt_descriptor,
        repositories,
        package_plane,
        sdk_rows,
    )

    exact_keys(composer_descriptor, {"path", "sha256", "normalizationContract"}, "packagePlane.composer")
    composer_path, _ = checked_authority(repo_root, composer_descriptor, "packagePlane.composer")
    if composer_descriptor.get("normalizationContract") != "chummer6.deterministic-nupkg/v1":
        raise LockError("composer normalization contract differs")
    composer_module = load_module(composer_path, "checked_linux_package_plane_composer")

    exact_keys(feed_descriptor, {"path", "sha256", "packageInventorySha256", "packageCount"}, "packagePlane.feedInventory")
    feed_path, feed_file_sha = checked_authority(
        repo_root, feed_descriptor, "packagePlane.feedInventory"
    )
    portable_json(feed_path, "canonical feed inventory")
    if feed_descriptor.get("packageCount") != 96:
        raise LockError("canonical feed descriptor count differs")
    base_payload = load_json(feed_path, "canonical feed inventory")
    base_rows = validate_base_feed_inventory(base_payload, package_plane)

    exact_keys(proof_descriptor, {"path", "sha256", "contractName", "packageCount"}, "packagePlane.normalizationProof")
    proof_path, _ = checked_authority(
        repo_root, proof_descriptor, "packagePlane.normalizationProof"
    )
    portable_json(proof_path, "normalization proof")
    proof_payload = load_json(proof_path, "normalization proof")
    if (
        proof_descriptor.get("contractName")
        != "chummer6.package-normalization-proof/v1"
        or proof_descriptor.get("packageCount") != 10
    ):
        raise LockError("normalization proof descriptor differs")
    try:
        composer_module.validate_normalization_proof(
            proof_payload, base_payload["packages"]
        )
    except Exception as exc:
        raise LockError(f"normalization proof rows differ: {exc}") from exc
    hub_file_names = {row["fileName"] for row in hub_feed["packages"]}
    expected_normalized = {
        row["fileName"]
        for row in base_payload["packages"]
        if "repository" in row and row["fileName"] not in hub_file_names
    }
    observed_normalized = {
        row.get("fileName")
        for row in proof_payload.get("packages", [])
        if isinstance(row, dict)
    }
    if (
        proof_payload.get("packageCount") != proof_descriptor["packageCount"]
        or len(expected_normalized) != 10
        or observed_normalized != expected_normalized
    ):
        raise LockError("normalization proof owner package identity set differs")
    receipt_inventory = ui_receipt_payload["packageInventory"]
    receipt_by_file = {
        row.get("fileName"): row
        for row in receipt_inventory
        if isinstance(row, dict)
    }
    base_by_file = {row["fileName"]: row for row in base_payload["packages"]}
    proof_by_file = {row["fileName"]: row for row in proof_payload["packages"]}
    if (
        len(receipt_by_file) != 96
        or set(receipt_by_file) != set(base_by_file)
        or set(proof_by_file) != expected_normalized
    ):
        raise LockError("UI receipt/feed/normalization package filename chain differs")
    for file_name, common in base_by_file.items():
        if file_name in proof_by_file:
            proof_row = proof_by_file[file_name]
            expected_bytes = (
                proof_row["normalizedSha256"],
                proof_row["normalizedSizeBytes"],
            )
        else:
            receipt_row = receipt_by_file[file_name]
            expected_bytes = (receipt_row.get("sha256"), receipt_row.get("sizeBytes"))
        if (common["sha256"], common["sizeBytes"]) != expected_bytes:
            raise LockError(f"UI receipt normalization chain differs: {file_name}")

    exact_keys(runtime_descriptor, {"path", "sha256", "packageCount"}, "packagePlane.runtimePackageAuthority")
    runtime_path, runtime_file_sha = checked_authority(
        repo_root, runtime_descriptor, "packagePlane.runtimePackageAuthority"
    )
    portable_json(runtime_path, "runtime package authority")
    if runtime_descriptor.get("packageCount") != 6:
        raise LockError("runtime package authority descriptor count differs")
    runtime_rows = validate_runtime_authority(
        load_json(runtime_path, "runtime package authority")
    )

    nuget = payload.get("nuget")
    if not isinstance(nuget, dict):
        raise LockError("nuget must be an object")
    exact_keys(nuget, {"packageResolution", "packageLocks"}, "nuget")
    if (
        nuget.get("packageResolution")
        != "ui-v5-normalized-same-run-feed+per-project-nuget-lock-v1-content-hash"
    ):
        raise LockError("NuGet resolution contract differs")
    package_locks = nuget.get("packageLocks")
    if not isinstance(package_locks, list) or len(package_locks) != 2:
        raise LockError("NuGet package locks must cover both Linux RIDs")
    seen_rids: set[str] = set()
    for index, entry in enumerate(package_locks):
        label = f"nuget.packageLocks[{index}]"
        if not isinstance(entry, dict):
            raise LockError(f"{label} must be an object")
        exact_keys(
            entry,
            {
                "runtimeIdentifier",
                "targetFramework",
                "projectLocks",
                "cacheInventoryPath",
                "cacheInventorySha256",
                "cacheProofPath",
                "cacheProofSha256",
                "baseFeedInventorySha256",
                "restoreFeedInventorySha256",
                "restoreFeedInventoryPath",
                "restoreFeedInventoryFileSha256",
            },
            label,
        )
        rid = required_string(entry, "runtimeIdentifier", label)
        if (
            rid not in SUPPORTED_RIDS
            or rid in seen_rids
            or entry.get("targetFramework") != "net10.0"
            or entry.get("baseFeedInventorySha256")
            != base_payload["packageInventorySha256"]
        ):
            raise LockError(f"{label} identity or base binding differs")
        seen_rids.add(rid)
        project_locks = entry.get("projectLocks")
        if not isinstance(project_locks, list) or len(project_locks) != len(
            PROJECT_LOCK_ORDER
        ):
            raise LockError(f"{label} must bind exactly three project lock files")
        locked_projects: dict[
            str, dict[tuple[str, str], dict[str, str]]
        ] = {}
        root_lock_sha = ""
        for lock_index, descriptor in enumerate(project_locks):
            descriptor_label = f"{label}.projectLocks[{lock_index}]"
            if not isinstance(descriptor, dict):
                raise LockError(f"{descriptor_label} must be an object")
            exact_keys(descriptor, {"project", "path", "sha256"}, descriptor_label)
            project = required_string(descriptor, "project", descriptor_label)
            if project != PROJECT_LOCK_ORDER[lock_index]:
                raise LockError(f"{descriptor_label} project order differs")
            expected_path = (
                f"release-locks/{EXPECTED_PROJECT_LOCKS[project]['authorityStem']}-"
                f"{rid}.packages.lock.json"
            )
            if descriptor.get("path") != expected_path:
                raise LockError(f"{descriptor_label} authority path differs")
            lock_path, lock_sha = checked_authority(
                repo_root, descriptor, descriptor_label
            )
            portable_json(lock_path, descriptor_label)
            locked_projects[project] = validate_package_lock(lock_path, rid, project)
            if project == ROOT_PROJECT:
                root_lock_sha = lock_sha
        package_rows = validate_project_lock_closure(locked_projects, rid)
        if not root_lock_sha:
            raise LockError(f"{label} has no root project lock")
        restore_path = resolve_repo_file(
            repo_root,
            required_string(entry, "restoreFeedInventoryPath", label),
            f"{label}.restoreFeedInventoryPath",
        )
        if sha256_file(restore_path) != required_sha256(
            entry, "restoreFeedInventoryFileSha256", label
        ):
            raise LockError(f"{label} restore feed inventory file differs")
        portable_json(restore_path, f"{rid} restore feed inventory")
        restore_payload = load_json(restore_path, f"{rid} restore feed inventory")
        restore_rows = validate_rid_feed_inventory(
            restore_payload,
            rid,
            base_payload,
            feed_file_sha,
            runtime_rows,
            runtime_file_sha,
        )
        if entry.get("restoreFeedInventorySha256") != restore_payload[
            "restoreFeedInventorySha256"
        ]:
            raise LockError(f"{label} restore feed digest differs")
        cache_path = resolve_repo_file(
            repo_root,
            required_string(entry, "cacheInventoryPath", label),
            f"{label}.cacheInventoryPath",
        )
        if sha256_file(cache_path) != required_sha256(
            entry, "cacheInventorySha256", label
        ):
            raise LockError(f"{label} cache inventory file differs")
        portable_json(cache_path, f"{rid} cache inventory")
        is_cross_target = rid == "linux-arm64"
        expected_cache = cache_expected_rows(
            package_rows,
            restore_rows,
            runtime_rows,
            rid,
            include_app_host=is_cross_target,
        )
        cache_model = (
            {
                "executionModel": "native",
                "hostRid": "linux-x64",
                "sdkRid": "linux-x64",
                "targetRid": "linux-x64",
            }
            if not is_cross_target
            else {
                "executionModel": "cross_target",
                "hostRid": "linux-x64",
                "sdkRid": "linux-x64",
                "targetRid": "linux-arm64",
            }
        )
        cache_inventory = load_json(cache_path, f"{rid} cache inventory")
        validate_cache_inventory(
            cache_inventory,
            rid,
            root_lock_sha,
            base_payload["packageInventorySha256"],
            restore_payload["restoreFeedInventorySha256"],
            runtime_file_sha,
            expected_cache,
            cache_model,
        )
        proof_path = resolve_repo_file(
            repo_root,
            required_string(entry, "cacheProofPath", label),
            f"{label}.cacheProofPath",
        )
        proof_sha = required_sha256(entry, "cacheProofSha256", label)
        if sha256_file(proof_path) != proof_sha:
            raise LockError(f"{label} cache proof file differs")
        portable_json(proof_path, f"{rid} cache observation proof")
        validate_cache_observation_proof(
            load_json(proof_path, f"{rid} cache observation proof"),
            rid,
            cache_model,
            entry["cacheInventoryPath"],
            entry["cacheInventorySha256"],
            cache_inventory,
            sdk_authority_file_sha,
        )
    if seen_rids != set(SUPPORTED_RIDS):
        raise LockError("NuGet package lock RID set differs")

    release_manifest = payload.get("releaseManifest")
    if not isinstance(release_manifest, dict):
        raise LockError("releaseManifest must be an object")
    exact_keys(
        release_manifest,
        {
            "authorityContract",
            "sourceRepository",
            "sourceCommit",
            "path",
            "sha256",
            "status",
            "releaseEvidenceEligible",
        },
        "releaseManifest",
    )
    manifest_path, manifest_sha = checked_authority(
        repo_root, release_manifest, "releaseManifest"
    )
    source_commit = required_string(release_manifest, "sourceCommit", "releaseManifest")
    if (
        release_manifest.get("authorityContract") != RELEASE_AUTHORITY_LOCK_CONTRACT
        or release_manifest.get("sourceRepository") != "ArchonMegalon/Chummer6"
        or not COMMIT_PATTERN.fullmatch(source_commit)
        or release_manifest.get("status") != "review_required"
        or release_manifest.get("releaseEvidenceEligible") is not False
        or git_blob_sha256(repo_root, source_commit, release_manifest["path"])
        != manifest_sha
    ):
        raise LockError("release authority lock must remain exact, bound, review-required, and evidence-ineligible")
    manifest_payload = load_json(manifest_path, "release manifest")
    exact_keys(
        manifest_payload,
        {
            "authority",
            "authority_binding_status",
            "authority_source",
            "contract_name",
            "contract_version",
            "does_not_assert",
            "release_decision_status",
            "release_evidence_eligible",
            "release_posture",
        },
        "release authority lock",
    )
    if (
        manifest_payload.get("contract_name") != RELEASE_AUTHORITY_LOCK_CONTRACT
        or manifest_payload.get("contract_version") != 1
        or manifest_payload.get("authority_binding_status") != "bound"
        or manifest_payload.get("release_decision_status") != "review_required"
        or manifest_payload.get("release_posture") != "review_required"
        or manifest_payload.get("release_evidence_eligible") is not False
    ):
        raise LockError("release authority lock posture differs")
    does_not_assert = manifest_payload.get("does_not_assert")
    if does_not_assert != [
        "artifact_build_proof",
        "product_preview_readiness",
        "stable_readiness",
        "flagship_readiness",
    ]:
        raise LockError("release authority lock claim boundary differs")
    authority_source = manifest_payload.get("authority_source")
    authority = manifest_payload.get("authority")
    if not isinstance(authority_source, dict) or not isinstance(authority, dict):
        raise LockError("bound release manifest authority is missing")
    source_registry_commit = required_string(
        authority_source,
        "registryCommit",
        "release manifest authority_source",
    )
    source_manifest_version = required_string(
        authority_source,
        "manifestVersion",
        "release manifest authority_source",
    )
    for field in (
        "currentSha256",
        "snapshotSha256",
        "manifestSha256",
        "releaseDecisionSha256",
    ):
        required_sha256(authority_source, field, "release manifest authority_source")
    if (
        authority_source.get("registryRepository")
        != "ArchonMegalon/chummer6-hub-registry"
        or not COMMIT_PATTERN.fullmatch(source_registry_commit)
        or authority_source.get("currentStatus") != "review_required"
        or authority.get("authorityContract")
        != "chummer.release-authority-snapshot/v2"
        or authority.get("registryRepository")
        != authority_source.get("registryRepository")
        or authority.get("registryCommit") != source_registry_commit
        or authority.get("releaseVersion") != source_manifest_version
        or authority.get("releaseDecisionStatus") != "review_required"
        or authority.get("manifestSha256") != authority_source.get("manifestSha256")
        or authority.get("releaseDecisionSha256")
        != authority_source.get("releaseDecisionSha256")
    ):
        raise LockError("bound release manifest authority differs")

    build_script = payload.get("buildScript")
    if not isinstance(build_script, dict):
        raise LockError("buildScript must be an object")
    exact_keys(build_script, {"path", "sha256"}, "buildScript")
    checked_authority(repo_root, build_script, "buildScript")
    return {
        "payload": payload,
        "repositories": repositories,
        "sdkRows": sdk_rows,
        "baseFeed": base_payload,
        "baseFeedPath": feed_path,
        "runtimeRows": runtime_rows,
        "runtimePath": runtime_path,
    }


def package_lock_entry(payload: dict[str, Any], rid: str) -> dict[str, Any]:
    for entry in payload["nuget"]["packageLocks"]:
        if entry["runtimeIdentifier"] == rid:
            return entry
    raise LockError(f"source lock has no package plane for {rid}")


def verify_checkouts(context: dict[str, Any], base: Path, locked: bool) -> None:
    if not base.is_dir() or base.is_symlink():
        raise LockError("checkout base is missing or unsafe")
    for directory, repository in context["repositories"].items():
        root = base / directory
        if not root.is_dir() or root.is_symlink():
            raise LockError(f"checkout is missing or unsafe: {directory}")
        origin = git_output(root, "remote", "get-url", "origin")
        if origin.removesuffix(".git").rstrip("/") != repository["url"].removesuffix(
            ".git"
        ).rstrip("/"):
            raise LockError(f"checkout origin differs: {directory}")
        if locked and git_output(root, "rev-parse", "HEAD") != repository["commit"]:
            raise LockError(f"checkout commit differs: {directory}")
        if git_output(root, "status", "--porcelain=v1", "--untracked-files=all"):
            raise LockError(f"checkout is dirty: {directory}")
        expected_sdk = repository["globalJsonSdkVersion"]
        global_json = root / "global.json"
        if expected_sdk is None:
            if locked and global_json.exists():
                raise LockError(f"checkout unexpectedly contains global.json: {directory}")
        else:
            actual = load_json(global_json, f"{directory} global.json")
            if actual.get("sdk", {}).get("version") != expected_sdk:
                raise LockError(f"checkout SDK declaration differs: {directory}")


def write_nuget_config(feed: Path, packages_root: Path, output: Path) -> None:
    if not feed.is_absolute() or not feed.is_dir() or feed.is_symlink():
        raise LockError("NuGet feed must be an absolute regular directory")
    if not packages_root.is_absolute() or packages_root.is_symlink():
        raise LockError("NuGet package cache must be an absolute non-symlink path")
    if output.exists() or output.is_symlink():
        raise LockError(f"refusing to replace NuGet config: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        "<configuration>",
        "  <config>",
        (
            '    <add key="globalPackagesFolder" value="'
            f'{html.escape(str(packages_root), quote=True)}" />'
        ),
        '    <add key="signatureValidationMode" value="accept" />',
        "  </config>",
        "  <packageSources>",
        "    <clear />",
        (
            '    <add key="same-run-local-feed" value="'
            f'{html.escape(str(feed.resolve()), quote=True)}" />'
        ),
        "  </packageSources>",
        "  <disabledPackageSources>",
        "    <clear />",
        "  </disabledPackageSources>",
        "  <packageSourceMapping>",
        '    <packageSource key="same-run-local-feed">',
        '      <package pattern="*" />',
        "    </packageSource>",
        "  </packageSourceMapping>",
        "</configuration>",
    ]
    encoded = ("\n".join(lines) + "\n").encode()
    descriptor = os.open(
        output,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(encoded)


def verify_cache_directory(
    expected_rows: list[dict[str, str]],
    restore_rows: dict[tuple[str, str], dict[str, Any]],
    feed: Path,
    packages_root: Path,
    rid: str,
    phase: str,
) -> None:
    expected = {
        (row["packageId"].casefold(), row["version"].casefold()): row
        for row in expected_rows
    }
    packages_root = unsymlinked_cli_path(
        packages_root, f"{rid} {phase} NuGet cache root", kind="directory"
    )
    for walk_root, directories, files in os.walk(packages_root, followlinks=False):
        root = Path(walk_root)
        for name in [*directories, *files]:
            candidate = root / name
            metadata = candidate.lstat()
            if candidate.is_symlink() or not (
                stat.S_ISREG(metadata.st_mode) or stat.S_ISDIR(metadata.st_mode)
            ):
                raise LockError(f"NuGet cache contains an unsafe entry: {candidate}")
    id_entries = list(packages_root.iterdir())
    if any(not entry.is_dir() or entry.is_symlink() for entry in id_entries):
        raise LockError("NuGet cache root contains a non-package entry")
    expected_by_id: dict[str, dict[str, dict[str, str]]] = {}
    for (package_id, version), row in expected.items():
        expected_by_id.setdefault(package_id, {})[version] = row
    if {entry.name for entry in id_entries} != set(expected_by_id):
        raise LockError("NuGet cache package identity set differs")
    source = str(feed.resolve())
    for package_id, versions in expected_by_id.items():
        id_root = packages_root / package_id
        version_entries = list(id_root.iterdir())
        if any(not entry.is_dir() or entry.is_symlink() for entry in version_entries):
            raise LockError(f"NuGet cache version root is unsafe: {package_id}")
        if {entry.name for entry in version_entries} != set(versions):
            raise LockError(f"NuGet cache version set differs: {package_id}")
        for version, expected_row in versions.items():
            root = id_root / version
            metadata_path = root / ".nupkg.metadata"
            metadata_stat = metadata_path.lstat()
            if (
                metadata_path.is_symlink()
                or not stat.S_ISREG(metadata_stat.st_mode)
                or metadata_stat.st_nlink != 1
            ):
                raise LockError(
                    f"NuGet cache metadata is unsafe: {package_id}/{version}"
                )
            metadata = load_json(metadata_path, f"NuGet metadata {package_id}/{version}")
            exact_keys(
                metadata,
                {"version", "contentHash", "source"},
                f"NuGet metadata {package_id}/{version}",
            )
            if (
                metadata.get("version") != 2
                or metadata.get("contentHash") != expected_row["contentHash"]
                or metadata.get("source") != source
            ):
                raise LockError(f"NuGet metadata differs: {package_id}/{version}")
            archive = root / f"{package_id}.{version}.nupkg"
            sidecar = root / f"{package_id}.{version}.nupkg.sha512"
            for checked in (archive, sidecar):
                checked_metadata = checked.lstat()
                if (
                    checked.is_symlink()
                    or not stat.S_ISREG(checked_metadata.st_mode)
                    or checked_metadata.st_nlink != 1
                ):
                    raise LockError(f"NuGet cache authority file is unsafe: {checked}")
            recorded = sidecar.read_text(encoding="ascii").strip()
            canonical_sha512(recorded, f"NuGet sidecar {package_id}/{version}")
            feed_row = restore_rows[(package_id, version)]
            if (
                recorded != expected_row["archiveSha512"]
                or archive_sha512(archive) != recorded
                or sha256_file(archive) != expected_row["sourceSha256"]
                or expected_row["sourceSha256"] != feed_row["sha256"]
                or archive.read_bytes() != (feed / feed_row["fileName"]).read_bytes()
            ):
                raise LockError(f"NuGet cache archive differs: {package_id}/{version}")
    print(
        f"NuGet cache verified: {len(expected_rows)} exact packages for "
        f"{rid} ({phase})"
    )


def verify_nuget_cache(
    context: dict[str, Any], repo_root: Path, rid: str, feed: Path, packages_root: Path
) -> None:
    payload = context["payload"]
    entry = package_lock_entry(payload, rid)
    restore_path = resolve_repo_file(
        repo_root,
        entry["restoreFeedInventoryPath"],
        f"{rid} restore feed inventory",
    )
    restore_payload = load_json(restore_path, f"{rid} restore feed inventory")
    restore_rows = {
        (row["packageId"].casefold(), row["version"].casefold()): row
        for row in restore_payload["packages"]
    }
    validate_feed_directory(feed, restore_rows, f"{rid} local restore feed")
    cache_path = resolve_repo_file(
        repo_root, entry["cacheInventoryPath"], f"{rid} cache inventory"
    )
    inventory = load_json(cache_path, f"{rid} cache inventory")
    verify_cache_directory(
        inventory["packages"],
        restore_rows,
        feed,
        packages_root,
        rid,
        inventory["executionModel"],
    )


def direct_feed_authorities(
    base_path: Path, rid_path: Path, runtime_path: Path, rid: str
) -> tuple[
    dict[str, Any],
    dict[tuple[str, str], dict[str, Any]],
    dict[tuple[str, str], dict[str, Any]],
]:
    base = load_json(base_path, "canonical feed inventory")
    if (
        set(base)
        != {
            "contract",
            "hubCanonicalFeed",
            "normalizationContract",
            "packageCount",
            "packageInventorySha256",
            "packages",
            "uiCommit",
            "uiLockSha256",
            "uiVerifierSha256",
            "upstreamVerification",
        }
        or base.get("contract") != "chummer6.normalized-same-run-feed/v1"
        or base.get("packageCount") != 96
        or not isinstance(base.get("packages"), list)
        or len(base["packages"]) != 96
        or base.get("packageInventorySha256") != canonical_json_sha256(base["packages"])
    ):
        raise LockError("canonical feed inventory is invalid")
    base_rows: dict[tuple[str, str], dict[str, Any]] = {}
    for index, row in enumerate(base["packages"]):
        identity = validate_basic_package_row(row, f"canonical feed package {index}")
        if identity in base_rows:
            raise LockError("canonical feed contains duplicate identity")
        base_rows[identity] = row
    runtime = validate_runtime_authority(load_json(runtime_path, "runtime authority"))
    rid_payload = load_json(rid_path, f"{rid} feed inventory")
    rid_rows = validate_rid_feed_inventory(
        rid_payload,
        rid,
        base,
        sha256_file(base_path),
        runtime,
        sha256_file(runtime_path),
    )
    return rid_payload, rid_rows, runtime


def materialize_cache_inventory(args: argparse.Namespace) -> None:
    if args.output.exists() or args.output.is_symlink():
        raise LockError(f"refusing to replace cache inventory: {args.output}")
    package_rows = validate_package_lock(args.package_lock, args.rid)
    rid_payload, rid_rows, runtime_rows = direct_feed_authorities(
        args.base_feed_inventory,
        args.rid_feed_inventory,
        args.runtime_authority,
        args.rid,
    )
    validate_feed_directory(args.feed, rid_rows, f"{args.rid} local restore feed")
    if args.execution_model == "native" and args.rid != "linux-x64":
        raise LockError("only observed linux-x64 native cache may be materialized")
    if args.execution_model == "cross_target" and args.rid != "linux-arm64":
        raise LockError("cross-target cache authority is only linux-arm64")
    host_machine = platform.machine().lower()
    if host_machine not in {"x86_64", "amd64"}:
        raise LockError(
            "cache observations require the authenticated linux-x64 host SDK; "
            f"observed host is {platform.machine()}"
        )
    sdk_rows = validate_sdk_authority(
        load_json(args.sdk_authority, "SDK archive authority")
    )
    validate_sdk_directory(args.sdk_root, sdk_rows["linux-x64"], execute=True)
    include_app_host = args.execution_model == "cross_target"
    rows = cache_expected_rows(
        package_rows,
        rid_rows,
        runtime_rows,
        args.rid,
        args.feed,
        include_app_host=include_app_host,
    )
    model = (
        {
            "executionModel": "native",
            "hostRid": "linux-x64",
            "sdkRid": "linux-x64",
            "targetRid": "linux-x64",
        }
        if args.execution_model == "native"
        else {
            "executionModel": "cross_target",
            "hostRid": "linux-x64",
            "sdkRid": "linux-x64",
            "targetRid": "linux-arm64",
        }
    )
    inventory_digest = canonical_json_sha256(rows)
    if os.path.samefile(args.restore_cache_root, args.post_publish_cache_root):
        raise LockError("restore and post-publish cache observations must be distinct")
    verify_cache_directory(
        rows,
        rid_rows,
        args.feed,
        args.restore_cache_root,
        args.rid,
        "restore",
    )
    verify_cache_directory(
        rows,
        rid_rows,
        args.feed,
        args.post_publish_cache_root,
        args.rid,
        "post_publish",
    )
    payload = {
        "baseFeedInventorySha256": load_json(
            args.base_feed_inventory, "canonical feed inventory"
        )["packageInventorySha256"],
        "contract": "chummer6.rid-nuget-cache-inventory/v1",
        "executionModel": model["executionModel"],
        "hostRid": model["hostRid"],
        "nativeTargetExecuted": False,
        "observations": [
            {
                "packageCount": len(rows),
                "packageInventorySha256": inventory_digest,
                "phase": "restore",
            },
            {
                "packageCount": len(rows),
                "packageInventorySha256": inventory_digest,
                "phase": "post_publish",
            },
        ],
        "packageCount": len(rows),
        "packageLockSha256": sha256_file(args.package_lock),
        "packages": rows,
        "restoreFeedInventorySha256": rid_payload["restoreFeedInventorySha256"],
        "runtimeIdentifier": args.rid,
        "runtimePackageAuthoritySha256": sha256_file(args.runtime_authority),
        "sdkExecuted": True,
        "sdkRid": model["sdkRid"],
        "targetRid": model["targetRid"],
    }
    write_json_exclusive(args.output, payload, "cache inventory")
    proof_output = getattr(args, "proof_output", None)
    if proof_output is not None:
        authority = getattr(args, "cache_inventory_authority", None)
        if (
            not isinstance(authority, str)
            or PurePosixPath(authority).is_absolute()
            or ".." in PurePosixPath(authority).parts
            or PurePosixPath(authority).as_posix() != authority
        ):
            raise LockError("cache inventory proof requires a portable authority path")
        proof = {
            "cacheInventoryAuthority": authority,
            "cacheInventorySha256": sha256_file(args.output),
            "contract": "chummer6.rid-cache-observation-proof/v1",
            "executionModel": model["executionModel"],
            "hostRid": model["hostRid"],
            "nativeTargetExecuted": False,
            "observations": payload["observations"],
            "packageCount": len(rows),
            "packageInventorySha256": inventory_digest,
            "phaseRootsDistinct": True,
            "releaseEvidenceEligible": False,
            "runtimeIdentifier": args.rid,
            "sdkAuthoritySha256": sha256_file(args.sdk_authority),
            "sdkExecuted": True,
            "sdkRid": model["sdkRid"],
            "sdkVersion": SDK_VERSION,
            "status": "passed",
            "targetRid": model["targetRid"],
        }
        write_json_exclusive(proof_output, proof, "cache observation proof")
    print(f"cache inventory materialized: {args.output} ({len(rows)} packages)")


def validate_sdk_directory(root: Path, row: dict[str, Any], execute: bool) -> None:
    if not root.is_dir() or root.is_symlink():
        raise LockError("SDK directory is missing or unsafe")
    tool_rows = {tool["name"]: tool for tool in row["toolchainFiles"]}
    for name, relative in SDK_TOOL_PATHS.items():
        path = root / relative
        metadata = path.lstat()
        expected = tool_rows[name]
        if (
            path.is_symlink()
            or not stat.S_ISREG(metadata.st_mode)
            or metadata.st_size != expected["sizeBytes"]
            or sha256_file(path) != expected["sha256"]
        ):
            raise LockError(f"SDK toolchain bytes differ: {name}")
    dotnet = root / "dotnet"
    if not os.access(dotnet, os.X_OK):
        raise LockError("SDK dotnet host is not executable")
    if execute:
        completed = subprocess.run(
            [str(dotnet), "--version"],
            cwd=root,
            env={
                "DOTNET_ROOT": str(root),
                "DOTNET_MULTILEVEL_LOOKUP": "0",
                "DOTNET_NOLOGO": "1",
                "DOTNET_SKIP_FIRST_TIME_EXPERIENCE": "1",
                "PATH": f"{root}{os.pathsep}{os.defpath}",
            },
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=60,
            check=False,
        )
        if completed.returncode or completed.stdout.strip() != SDK_VERSION:
            raise LockError("authenticated SDK did not execute as its exact version")


def normalized_tar_name(name: str) -> str | None:
    if name in {".", "./"}:
        return None
    if not name.startswith("./") or name.startswith("././"):
        raise LockError(f"SDK archive path is not canonical: {name}")
    relative = name[2:]
    if relative.endswith("/"):
        relative = relative[:-1]
    pure = PurePosixPath(relative)
    if (
        not relative
        or pure.is_absolute()
        or ".." in pure.parts
        or pure.as_posix() != relative
        or "\\" in relative
        or any(ord(character) < 32 for character in relative)
    ):
        raise LockError(f"SDK archive path is unsafe: {name}")
    return relative


def install_sdk(context: dict[str, Any], rid: str, archive: Path, output: Path) -> None:
    if rid not in SUPPORTED_RIDS:
        raise LockError(f"unsupported SDK RID: {rid}")
    row = context["sdkRows"][rid]
    archive_metadata = archive.lstat()
    if (
        archive.is_symlink()
        or not stat.S_ISREG(archive_metadata.st_mode)
        or archive_metadata.st_size != row["sizeBytes"]
        or sha256_file(archive) != row["sha256"]
        or sha512_file_hex(archive) != row["sha512"]
    ):
        raise LockError(f"downloaded SDK archive differs for {rid}")
    if output.exists() or output.is_symlink():
        raise LockError(f"refusing to replace SDK output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.parent.is_symlink():
        raise LockError("SDK output parent is symlinked")
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.extract-", dir=output.parent)
    )
    seen: set[str] = set()
    folded: set[str] = set()
    total_size = 0
    member_count = 0
    try:
        with tarfile.open(archive, "r:gz") as tar:
            for member in tar:
                relative = normalized_tar_name(member.name)
                if relative is None:
                    continue
                member_count += 1
                total_size += member.size
                normalized = relative.casefold()
                if (
                    relative in seen
                    or normalized in folded
                    or member_count > 100_000
                    or total_size > 4 * 1024 * 1024 * 1024
                    or not (member.isdir() or member.isreg())
                ):
                    raise LockError(f"SDK archive member is unsafe: {member.name}")
                seen.add(relative)
                folded.add(normalized)
                target = temporary / Path(*PurePosixPath(relative).parts)
                try:
                    target.resolve().relative_to(temporary.resolve())
                except ValueError as exc:
                    raise LockError("SDK archive member escapes output") from exc
                if member.isdir():
                    target.mkdir(mode=0o755, parents=True, exist_ok=False)
                    continue
                target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
                source = tar.extractfile(member)
                if source is None:
                    raise LockError(f"SDK archive file cannot be read: {member.name}")
                descriptor = os.open(
                    target,
                    os.O_WRONLY
                    | os.O_CREAT
                    | os.O_EXCL
                    | getattr(os, "O_NOFOLLOW", 0),
                    0o755 if member.mode & 0o111 else 0o644,
                )
                with source, os.fdopen(descriptor, "wb") as destination:
                    shutil.copyfileobj(source, destination, 1024 * 1024)
        execute = (
            (rid == "linux-x64" and platform.machine().lower() in {"x86_64", "amd64"})
            or (rid == "linux-arm64" and platform.machine().lower() in {"aarch64", "arm64"})
        )
        if not execute:
            raise LockError(
                f"SDK {rid} cannot be installed as executable evidence on host {platform.machine()}"
            )
        validate_sdk_directory(temporary, row, execute=True)
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    print(f"SDK installed and authenticated: {rid} {SDK_VERSION}")


def emit_tsv(context: dict[str, Any], lock_path: Path) -> None:
    payload = context["payload"]
    package_plane = payload["packagePlane"]
    print(f"LOCK_SHA256\t{sha256_file(lock_path)}")
    print(f"SDK_VERSION\t{SDK_VERSION}")
    print(
        "SDK_AUTHORITY\t"
        f"{payload['dotnet']['authority']['path']}\t"
        f"{payload['dotnet']['authority']['sha256']}"
    )
    for rid in SUPPORTED_RIDS:
        row = context["sdkRows"][rid]
        print(
            "SDK_ARCHIVE\t"
            f"{rid}\t{row['source']}\t{row['fileName']}\t{row['sha256']}\t"
            f"{row['sha512']}\t{row['sizeBytes']}"
        )
    manifest = payload["releaseManifest"]
    print(f"RELEASE_MANIFEST_SHA256\t{manifest['sha256']}")
    print(f"RELEASE_MANIFEST_STATUS\t{manifest['status']}")
    print("RELEASE_EVIDENCE_ELIGIBLE\tfalse")
    for row in payload["repositories"]:
        print(
            "REPOSITORY\t"
            f"{row['directory']}\t{row['name']}\t{row['commit']}"
        )
    print(
        "UI_PACKAGE_PLANE\t"
        f"{package_plane['uiLock']['path']}\t{package_plane['uiLock']['sha256']}\t"
        f"{package_plane['uiVerifier']['path']}\t{package_plane['uiVerifier']['sha256']}"
    )
    print(
        "UI_CONSUMER\t"
        f"{package_plane['finalUiVerificationReceipt']['consumerCommit']}\t"
        f"{package_plane['finalUiVerificationReceipt']['path']}\t"
        f"{package_plane['finalUiVerificationReceipt']['sha256']}"
    )
    print(
        "PACKAGE_COMPOSER\t"
        f"{package_plane['composer']['path']}\t{package_plane['composer']['sha256']}\t"
        f"{package_plane['composer']['normalizationContract']}"
    )
    print(
        "PACKAGE_AUTHORITIES\t"
        f"{package_plane['feedInventory']['path']}\t"
        f"{package_plane['normalizationProof']['path']}\t"
        f"{package_plane['runtimePackageAuthority']['path']}"
    )
    print(
        "SOURCE_LOCK_VERIFIER\t"
        f"{payload['sourceLockVerifier']['path']}\t"
        f"{payload['sourceLockVerifier']['sha256']}"
    )
    for entry in payload["nuget"]["packageLocks"]:
        for descriptor in entry["projectLocks"]:
            print(
                "NUGET_PROJECT_LOCK\t"
                f"{entry['runtimeIdentifier']}\t{descriptor['project']}\t"
                f"{descriptor['path']}\t{descriptor['sha256']}"
            )
        print(
            "NUGET_PACKAGE_PLANE\t"
            f"{entry['runtimeIdentifier']}\t{entry['cacheInventoryPath']}\t"
            f"{entry['cacheInventorySha256']}\t{entry['restoreFeedInventoryPath']}\t"
            f"{entry['restoreFeedInventoryFileSha256']}"
        )


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)

    inspect = commands.add_parser("inspect")
    inspect.add_argument("--lock", type=Path, required=True)
    inspect.add_argument("--repo-root", type=Path, required=True)

    checkouts = commands.add_parser("verify-checkouts")
    checkouts.add_argument("--lock", type=Path, required=True)
    checkouts.add_argument("--repo-root", type=Path, required=True)
    checkouts.add_argument("--base", type=Path, required=True)
    checkouts.add_argument("--moving", action="store_true")

    install = commands.add_parser("install-sdk")
    install.add_argument("--lock", type=Path, required=True)
    install.add_argument("--repo-root", type=Path, required=True)
    install.add_argument("--rid", choices=SUPPORTED_RIDS, required=True)
    install.add_argument("--archive", type=Path, required=True)
    install.add_argument("--output", type=Path, required=True)

    sdk = commands.add_parser("verify-sdk")
    sdk.add_argument("--lock", type=Path, required=True)
    sdk.add_argument("--repo-root", type=Path, required=True)
    sdk.add_argument("--rid", choices=SUPPORTED_RIDS, required=True)
    sdk.add_argument("--sdk-root", type=Path, required=True)
    sdk.add_argument("--no-execute", action="store_true")

    config = commands.add_parser("write-nuget-config")
    config.add_argument("--feed", type=Path, required=True)
    config.add_argument("--packages-root", type=Path, required=True)
    config.add_argument("--output", type=Path, required=True)

    sanitize = commands.add_parser("sanitize-diagnostics")
    sanitize.add_argument("--input", type=Path, required=True)
    sanitize.add_argument("--redact-path", action="append", default=[])

    cache = commands.add_parser("verify-nuget-cache")
    cache.add_argument("--lock", type=Path, required=True)
    cache.add_argument("--repo-root", type=Path, required=True)
    cache.add_argument("--rid", choices=SUPPORTED_RIDS, required=True)
    cache.add_argument("--feed", type=Path, required=True)
    cache.add_argument("--packages-root", type=Path, required=True)

    materialize = commands.add_parser("materialize-cache-inventory")
    materialize.add_argument("--rid", choices=SUPPORTED_RIDS, required=True)
    materialize.add_argument("--package-lock", type=Path, required=True)
    materialize.add_argument("--base-feed-inventory", type=Path, required=True)
    materialize.add_argument("--rid-feed-inventory", type=Path, required=True)
    materialize.add_argument("--runtime-authority", type=Path, required=True)
    materialize.add_argument("--sdk-authority", type=Path, required=True)
    materialize.add_argument("--sdk-root", type=Path, required=True)
    materialize.add_argument("--feed", type=Path, required=True)
    materialize.add_argument("--restore-cache-root", type=Path, required=True)
    materialize.add_argument("--post-publish-cache-root", type=Path, required=True)
    materialize.add_argument("--output", type=Path, required=True)
    materialize.add_argument("--proof-output", type=Path)
    materialize.add_argument("--cache-inventory-authority")
    materialize.add_argument(
        "--execution-model", choices=("native", "cross_target"), required=True
    )
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "sanitize-diagnostics":
            diagnostic = unsymlinked_cli_path(
                args.input, "generator diagnostic", kind="file"
            )
            sanitize_diagnostics(diagnostic, args.redact_path)
            return 0
        if args.command == "write-nuget-config":
            args.feed = unsymlinked_cli_path(
                args.feed, "NuGet feed", kind="directory"
            )
            args.packages_root = unsymlinked_cli_path(
                args.packages_root,
                "NuGet package cache",
                kind="path",
                allow_missing=True,
            )
            args.output = unsymlinked_cli_path(
                args.output, "NuGet configuration output", kind="path", allow_missing=True
            )
            write_nuget_config(args.feed, args.packages_root, args.output)
            return 0
        if args.command == "materialize-cache-inventory":
            for attribute, label in (
                ("package_lock", "NuGet package lock"),
                ("base_feed_inventory", "canonical feed inventory"),
                ("rid_feed_inventory", "RID feed inventory"),
                ("runtime_authority", "runtime package authority"),
                ("sdk_authority", "SDK archive authority"),
            ):
                setattr(
                    args,
                    attribute,
                    unsymlinked_cli_path(
                        getattr(args, attribute), label, kind="file"
                    ),
                )
            for attribute, label in (
                ("sdk_root", "authenticated SDK root"),
                ("feed", "local restore feed"),
                ("restore_cache_root", "restore cache root"),
                ("post_publish_cache_root", "post-publish cache root"),
            ):
                setattr(
                    args,
                    attribute,
                    unsymlinked_cli_path(
                        getattr(args, attribute), label, kind="directory"
                    ),
                )
            args.output = unsymlinked_cli_path(
                args.output, "cache inventory output", kind="path", allow_missing=True
            )
            if args.proof_output is not None:
                args.proof_output = unsymlinked_cli_path(
                    args.proof_output,
                    "cache observation proof output",
                    kind="path",
                    allow_missing=True,
                )
            materialize_cache_inventory(args)
            return 0
        args.lock = unsymlinked_cli_path(args.lock, "source lock", kind="file")
        args.repo_root = unsymlinked_cli_path(
            args.repo_root, "repository root", kind="directory"
        )
        context = validate_lock(args.lock, args.repo_root)
        if args.command == "inspect":
            emit_tsv(context, args.lock)
        elif args.command == "verify-checkouts":
            base = unsymlinked_cli_path(
                args.base, "checkout base", kind="directory"
            )
            verify_checkouts(context, base, locked=not args.moving)
        elif args.command == "install-sdk":
            archive = unsymlinked_cli_path(
                args.archive, "SDK archive", kind="file"
            )
            output = unsymlinked_cli_path(
                args.output, "SDK output", kind="path", allow_missing=True
            )
            install_sdk(context, args.rid, archive, output)
        elif args.command == "verify-sdk":
            sdk_root = unsymlinked_cli_path(
                args.sdk_root, "SDK root", kind="directory"
            )
            validate_sdk_directory(
                sdk_root,
                context["sdkRows"][args.rid],
                execute=not args.no_execute,
            )
        elif args.command == "verify-nuget-cache":
            feed = unsymlinked_cli_path(
                args.feed, "local restore feed", kind="directory"
            )
            packages_root = unsymlinked_cli_path(
                args.packages_root, "NuGet cache root", kind="directory"
            )
            verify_nuget_cache(
                context,
                args.repo_root,
                args.rid,
                feed,
                packages_root,
            )
        else:
            raise LockError(f"unsupported command: {args.command}")
    except (
        LockError,
        OSError,
        subprocess.SubprocessError,
        tarfile.TarError,
        ValueError,
    ) as exc:
        print(f"source lock validation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
