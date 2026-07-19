#!/usr/bin/env python3
"""Compose one exact UI package feed and two RID-specific restore feeds."""

from __future__ import annotations

import argparse
import base64
import binascii
import dataclasses
import hashlib
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unicodedata
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path, PurePosixPath
from types import ModuleType
from typing import Any


CONTRACT = "chummer6.linux-package-plane-materialization/v1"
FEED_CONTRACT = "chummer6.normalized-same-run-feed/v1"
RID_FEED_CONTRACT = "chummer6.rid-restore-feed/v1"
NORMALIZATION_CONTRACT = "chummer6.deterministic-nupkg/v1"
NORMALIZATION_PROOF_CONTRACT = "chummer6.package-normalization-proof/v1"
CANONICAL_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
CANONICAL_EXTERNAL_ATTR = 0o100644 << 16
SUPPORTED_RIDS = ("linux-x64", "linux-arm64")
EXPECTED_SDK_ARCHIVES = {
    rid: {
        "fileName": f"dotnet-sdk-10.0.103-{rid}.tar.gz",
        "source": (
            "https://builds.dotnet.microsoft.com/dotnet/Sdk/10.0.103/"
            f"dotnet-sdk-10.0.103-{rid}.tar.gz"
        ),
    }
    for rid in SUPPORTED_RIDS
}
EXPECTED_TOOLCHAIN_PATHS = {
    "dotnet_host": "dotnet",
    "csc": "sdk/10.0.103/Roslyn/bincore/csc.dll",
    "msbuild": "sdk/10.0.103/Microsoft.Build.dll",
    "nuget_packaging": "sdk/10.0.103/NuGet.Packaging.dll",
}
EXPECTED_RUNTIME_PACKAGES = {
    (rid, package_id): {
        "fileName": f"{package_id.lower()}.10.0.3.nupkg",
        "source": (
            "https://api.nuget.org/v3-flatcontainer/"
            f"{package_id.lower()}/10.0.3/{package_id.lower()}.10.0.3.nupkg"
        ),
    }
    for rid in SUPPORTED_RIDS
    for package_id in (
        f"Microsoft.AspNetCore.App.Runtime.{rid}",
        f"Microsoft.NETCore.App.Host.{rid}",
        f"Microsoft.NETCore.App.Runtime.{rid}",
    )
}
SHA256_RE = __import__("re").compile(r"^[0-9a-f]{64}$")
SHA512_RE = __import__("re").compile(r"^[0-9a-f]{128}$")
COMMIT_RE = __import__("re").compile(r"^[0-9a-f]{40}$")


class MaterializationError(RuntimeError):
    pass


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise MaterializationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8-sig"), object_pairs_hook=strict_object
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MaterializationError(f"could not read {label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise MaterializationError(f"{label} must be a JSON object")
    return payload


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha512_file(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def canonical_base64_sha512(value: Any) -> bool:
    if not isinstance(value, str) or value != value.strip():
        return False
    try:
        decoded = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error):
        return False
    return len(decoded) == 64 and base64.b64encode(decoded).decode("ascii") == value


def exact_write_json(path: Path, payload: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise MaterializationError(f"refusing to replace generated authority: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())


def load_module(path: Path, name: str) -> ModuleType:
    if path.is_symlink() or not path.is_file():
        raise MaterializationError(f"authority module is missing or unsafe: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise MaterializationError(f"could not load authority module: {path}")
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
    if completed.returncode != 0:
        raise MaterializationError(
            f"git {' '.join(arguments)} failed for {root}: {completed.stdout.strip()}"
        )
    return completed.stdout.strip()


def verify_checkout(root: Path, repository: str, commit: str, label: str) -> None:
    if not root.is_dir() or root.is_symlink():
        raise MaterializationError(f"{label} checkout is missing or unsafe")
    if not COMMIT_RE.fullmatch(commit) or git_output(root, "rev-parse", "HEAD") != commit:
        raise MaterializationError(f"{label} checkout does not match its exact commit")
    origin = git_output(root, "remote", "get-url", "origin")
    if origin.removesuffix(".git").rstrip("/") != repository.removesuffix(".git").rstrip("/"):
        raise MaterializationError(f"{label} checkout origin differs from authority")
    if git_output(root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise MaterializationError(f"{label} checkout must start clean")


def source_file(root: Path, relative: str, label: str) -> Path:
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise MaterializationError(f"{label} path is not portable")
    if root.is_symlink() or not root.is_dir():
        raise MaterializationError(f"{label} checkout is missing or unsafe")
    resolved_root = root.resolve()
    unresolved = resolved_root
    for index, part in enumerate(pure.parts):
        unresolved = unresolved / part
        try:
            metadata = unresolved.lstat()
        except OSError as exc:
            raise MaterializationError(f"{label} is missing: {relative}") from exc
        if unresolved.is_symlink():
            raise MaterializationError(f"{label} contains a symlinked path component")
        if index < len(pure.parts) - 1 and not stat.S_ISDIR(metadata.st_mode):
            raise MaterializationError(f"{label} parent component is not a directory")
    path = unresolved.resolve()
    try:
        path.relative_to(resolved_root)
    except ValueError as exc:
        raise MaterializationError(f"{label} path escapes its checkout") from exc
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode):
        raise MaterializationError(f"{label} is not a regular file")
    return path


def validate_sdk(
    sdk_root: Path, sdk_authority: dict[str, Any], host_rid: str
) -> dict[str, Any]:
    rows = sdk_authority.get("archives")
    if (
        set(sdk_authority) != {
            "archives",
            "contract",
            "legacyInstallerReference",
            "sdkVersion",
        }
        or
        sdk_authority.get("contract") != "chummer6.dotnet-sdk-archive-authority/v1"
        or sdk_authority.get("sdkVersion") != "10.0.103"
        or not isinstance(rows, list)
        or len(rows) != len(SUPPORTED_RIDS)
    ):
        raise MaterializationError("SDK authority contract is invalid")
    if sdk_authority.get("legacyInstallerReference") != {
        "executionAllowed": False,
        "sha256": "082f7685e156738a1b2e2ed8381a621870d4ce8e8c59278034556f05c186eb2e",
        "url": "https://dot.net/v1/dotnet-install.sh",
    }:
        raise MaterializationError("legacy dotnet installer reference is not exact")
    observed_rids: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != {
            "fileName",
            "rid",
            "sha256",
            "sha512",
            "sizeBytes",
            "source",
            "toolchainFiles",
            "version",
        }:
            raise MaterializationError(f"SDK archive authority row {index} is invalid")
        rid = row["rid"]
        expected = EXPECTED_SDK_ARCHIVES.get(rid)
        if (
            expected is None
            or rid in observed_rids
            or row["fileName"] != expected["fileName"]
            or row["source"] != expected["source"]
            or row["version"] != sdk_authority["sdkVersion"]
            or not SHA256_RE.fullmatch(str(row["sha256"]))
            or not SHA512_RE.fullmatch(str(row["sha512"]))
            or not isinstance(row["sizeBytes"], int)
            or isinstance(row["sizeBytes"], bool)
            or row["sizeBytes"] <= 0
        ):
            raise MaterializationError(f"SDK archive authority row {index} is not exact")
        toolchain = row["toolchainFiles"]
        if not isinstance(toolchain, list) or len(toolchain) != len(EXPECTED_TOOLCHAIN_PATHS):
            raise MaterializationError(f"SDK toolchain inventory is incomplete for {rid}")
        observed_tools: set[str] = set()
        for tool_index, tool in enumerate(toolchain):
            if not isinstance(tool, dict) or set(tool) != {
                "name",
                "path",
                "sha256",
                "sizeBytes",
            }:
                raise MaterializationError(
                    f"SDK toolchain row {rid}/{tool_index} is invalid"
                )
            name = tool["name"]
            if (
                name in observed_tools
                or EXPECTED_TOOLCHAIN_PATHS.get(name) != tool["path"]
                or not SHA256_RE.fullmatch(str(tool["sha256"]))
                or not isinstance(tool["sizeBytes"], int)
                or isinstance(tool["sizeBytes"], bool)
                or tool["sizeBytes"] <= 0
            ):
                raise MaterializationError(
                    f"SDK toolchain row {rid}/{tool_index} is not exact"
                )
            observed_tools.add(name)
        if observed_tools != set(EXPECTED_TOOLCHAIN_PATHS):
            raise MaterializationError(f"SDK toolchain identities are incomplete for {rid}")
        observed_rids.add(rid)
    if observed_rids != set(SUPPORTED_RIDS):
        raise MaterializationError("SDK authority does not cover both Linux RIDs")
    selected = next((row for row in rows if row.get("rid") == host_rid), None)
    if not isinstance(selected, dict):
        raise MaterializationError(f"SDK authority does not contain {host_rid}")
    dotnet = source_file(sdk_root, "dotnet", "dotnet host")
    if not os.access(dotnet, os.X_OK):
        raise MaterializationError("dotnet host is not executable")
    toolchain = selected.get("toolchainFiles")
    if not isinstance(toolchain, list) or len(toolchain) != 4:
        raise MaterializationError("SDK toolchain inventory is incomplete")
    observed: list[dict[str, Any]] = []
    for index, row in enumerate(toolchain):
        if not isinstance(row, dict) or set(row) != {"name", "path", "sha256", "sizeBytes"}:
            raise MaterializationError(f"SDK toolchain row {index} is invalid")
        path = source_file(sdk_root, str(row["path"]), f"SDK toolchain {row['name']}")
        actual = {
            "name": row["name"],
            "path": row["path"],
            "sha256": sha256_file(path),
            "sizeBytes": path.stat().st_size,
        }
        if actual != row:
            raise MaterializationError(f"SDK toolchain bytes differ: {row['name']}")
        observed.append(actual)
    completed = subprocess.run(
        [str(dotnet), "--version"],
        cwd=sdk_root,
        env={
            "DOTNET_ROOT": str(sdk_root),
            "DOTNET_MULTILEVEL_LOOKUP": "0",
            "DOTNET_NOLOGO": "1",
            "DOTNET_SKIP_FIRST_TIME_EXPERIENCE": "1",
            "PATH": f"{sdk_root}{os.pathsep}{os.defpath}",
        },
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0 or completed.stdout.strip() != sdk_authority["sdkVersion"]:
        raise MaterializationError("authenticated SDK did not report its exact version")
    return {"rid": host_rid, "sdkVersion": completed.stdout.strip(), "toolchainFiles": observed}


RELATIONSHIPS_NAMESPACE = (
    "http://schemas.openxmlformats.org/package/2006/relationships"
)
MANIFEST_RELATIONSHIP = "http://schemas.microsoft.com/packaging/2010/07/manifest"
CORE_PROPERTIES_RELATIONSHIP = (
    "http://schemas.openxmlformats.org/package/2006/relationships/metadata/"
    "core-properties"
)


def relationship_rows(data: bytes, nuspec_name: str, core_path: str) -> None:
    upper = data.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper or b"<!--" in data:
        raise MaterializationError("package relationships contain active/ambiguous XML")
    stripped = data.strip()
    if stripped.count(b"<?") > 1 or (b"<?" in stripped and not stripped.startswith(b"<?xml")):
        raise MaterializationError("package relationships contain an unexpected processing instruction")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise MaterializationError("package relationships XML is invalid") from exc
    if (
        root.tag != f"{{{RELATIONSHIPS_NAMESPACE}}}Relationships"
        or root.attrib
        or (root.text or "").strip()
        or (root.tail or "").strip()
    ):
        raise MaterializationError("package relationships root is not exact")
    expected = {
        (MANIFEST_RELATIONSHIP, f"/{nuspec_name}"),
        (CORE_PROPERTIES_RELATIONSHIP, f"/{core_path}"),
    }
    observed: set[tuple[str, str]] = set()
    identifiers: set[str] = set()
    children = list(root)
    if len(children) != len(expected):
        raise MaterializationError("package relationships contain missing or extra rows")
    for child in children:
        if (
            child.tag != f"{{{RELATIONSHIPS_NAMESPACE}}}Relationship"
            or set(child.attrib) != {"Id", "Target", "Type"}
            or list(child)
            or (child.text or "").strip()
            or (child.tail or "").strip()
        ):
            raise MaterializationError("package relationship row is not exact")
        identifier = child.attrib["Id"]
        row = (child.attrib["Type"], child.attrib["Target"])
        if not identifier or identifier in identifiers or row in observed or row not in expected:
            raise MaterializationError("package relationship row is duplicated or unexpected")
        identifiers.add(identifier)
        observed.add(row)
    if observed != expected:
        raise MaterializationError("package relationships do not bind exact metadata parts")


def canonical_relationships(nuspec_name: str, core_path: str) -> bytes:
    namespace = RELATIONSHIPS_NAMESPACE
    ET.register_namespace("", namespace)
    root = ET.Element(f"{{{namespace}}}Relationships")
    rows = (
        (MANIFEST_RELATIONSHIP, f"/{nuspec_name}"),
        (CORE_PROPERTIES_RELATIONSHIP, f"/{core_path}"),
    )
    for relationship_type, target in sorted(rows):
        identifier = "R" + hashlib.sha256(
            f"{relationship_type}\n{target}".encode("utf-8")
        ).hexdigest()[:16].upper()
        ET.SubElement(
            root,
            f"{{{namespace}}}Relationship",
            {"Type": relationship_type, "Target": target, "Id": identifier},
        )
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def normalize_package(
    path: Path, package_id: str, version: str, *, verify_idempotence: bool = True
) -> dict[str, Any]:
    try:
        path_metadata = path.lstat()
    except OSError as exc:
        raise MaterializationError(f"package input is missing: {path}") from exc
    if path.is_symlink() or not stat.S_ISREG(path_metadata.st_mode):
        raise MaterializationError(f"package input is not a regular file: {path}")
    original_sha256 = sha256_file(path)
    original_size = path.stat().st_size
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if not names or len(names) != len(set(names)):
                raise MaterializationError(f"package ZIP paths are invalid: {path.name}")
            normalized_names: set[str] = set()
            payloads: dict[str, bytes] = {}
            for info in archive.infolist():
                name = info.filename
                pure = PurePosixPath(name)
                normalized_name = unicodedata.normalize("NFC", name).casefold()
                unix_mode = stat.S_IFMT(info.external_attr >> 16)
                if (
                    pure.is_absolute()
                    or not pure.parts
                    or any(part in {"", ".", ".."} for part in pure.parts)
                    or ".." in pure.parts
                    or pure.as_posix() != name
                    or "\\" in name
                    or any(ord(character) < 32 for character in name)
                    or name.endswith("/")
                    or normalized_name in normalized_names
                    or (
                        info.create_system == 3
                        and unix_mode not in {0, stat.S_IFREG}
                    )
                    or info.flag_bits & 0x1
                ):
                    raise MaterializationError(f"unsafe package ZIP path: {name}")
                if pure.name.casefold() == ".signature.p7s":
                    raise MaterializationError(
                        f"signed package cannot be normalized safely: {path.name}"
                    )
                normalized_names.add(normalized_name)
                payloads[name] = archive.read(name)
    except (OSError, zipfile.BadZipFile) as exc:
        raise MaterializationError(f"invalid package ZIP {path.name}: {exc}") from exc
    nuspec_names = [name for name in payloads if name.lower().endswith(".nuspec")]
    if len(nuspec_names) != 1:
        raise MaterializationError(f"package has no exact nuspec: {path.name}")
    try:
        nuspec = ET.fromstring(payloads[nuspec_names[0]])
    except ET.ParseError as exc:
        raise MaterializationError(f"package nuspec is invalid: {path.name}") from exc
    element_values = {
        element.tag.rsplit("}", 1)[-1]: (element.text or "").strip()
        for element in nuspec.iter()
    }
    if element_values.get("id") != package_id or element_values.get("version") != version:
        raise MaterializationError(f"package identity differs: {path.name}")
    core_names = [
        name
        for name in payloads
        if name.startswith("package/services/metadata/core-properties/")
        and name.endswith(".psmdcp")
    ]
    if len(core_names) != 1 or "_rels/.rels" not in payloads:
        raise MaterializationError(f"package metadata parts are incomplete: {path.name}")
    old_core_path = core_names[0]
    original_relationships = payloads["_rels/.rels"]
    relationship_rows(original_relationships, nuspec_names[0], old_core_path)
    core_bytes = payloads.pop(old_core_path)
    core_path = (
        "package/services/metadata/core-properties/"
        f"{hashlib.sha256(core_bytes).hexdigest()[:32]}.psmdcp"
    )
    payloads[core_path] = core_bytes
    normalized_relationships = canonical_relationships(nuspec_names[0], core_path)
    payloads["_rels/.rels"] = normalized_relationships
    expected_assembly = f"lib/net10.0/{package_id}.dll"
    if expected_assembly not in payloads:
        raise MaterializationError(
            f"package expected assembly is absent: {path.name}/{expected_assembly}"
        )
    preserved_entries = [
        {
            "path": name,
            "sha256": hashlib.sha256(data).hexdigest(),
            "sizeBytes": len(data),
        }
        for name, data in sorted(payloads.items())
        if name not in {"_rels/.rels", core_path}
    ]
    assembly_sha256 = hashlib.sha256(payloads[expected_assembly]).hexdigest()
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    os.close(descriptor)
    temporary_path = Path(temporary)
    try:
        with zipfile.ZipFile(temporary_path, "w", compression=zipfile.ZIP_STORED) as output:
            output.comment = b""
            for name in sorted(payloads):
                info = zipfile.ZipInfo(name, date_time=CANONICAL_TIMESTAMP)
                info.compress_type = zipfile.ZIP_STORED
                info.create_system = 3
                info.external_attr = CANONICAL_EXTERNAL_ATTR
                info.extra = b""
                info.comment = b""
                output.writestr(info, payloads[name])
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)
    try:
        with zipfile.ZipFile(path) as canonical:
            canonical_names = canonical.namelist()
            if canonical_names != sorted(payloads) or canonical.comment:
                raise MaterializationError("normalized package ZIP order/comment differs")
            for info in canonical.infolist():
                if (
                    info.date_time != CANONICAL_TIMESTAMP
                    or info.compress_type != zipfile.ZIP_STORED
                    or info.create_system != 3
                    or info.external_attr != CANONICAL_EXTERNAL_ATTR
                    or info.extra
                    or info.comment
                ):
                    raise MaterializationError("normalized package ZIP metadata differs")
            for name, expected_bytes in payloads.items():
                if canonical.read(name) != expected_bytes:
                    raise MaterializationError(
                        f"normalized package changed entry bytes: {path.name}/{name}"
                    )
    except (OSError, zipfile.BadZipFile) as exc:
        raise MaterializationError(f"normalized package is invalid: {path.name}") from exc
    normalized_sha256 = sha256_file(path)
    normalized_size = path.stat().st_size
    if verify_idempotence:
        descriptor, temporary = tempfile.mkstemp(
            prefix=f".{path.name}.idempotence.", dir=path.parent
        )
        os.close(descriptor)
        idempotent_path = Path(temporary)
        try:
            shutil.copyfile(path, idempotent_path)
            normalize_package(
                idempotent_path,
                package_id,
                version,
                verify_idempotence=False,
            )
            if (
                idempotent_path.stat().st_size != normalized_size
                or sha256_file(idempotent_path) != normalized_sha256
            ):
                raise MaterializationError(
                    f"package normalization is not idempotent: {path.name}"
                )
        finally:
            idempotent_path.unlink(missing_ok=True)
    return {
        "assemblyPath": expected_assembly,
        "assemblySha256": assembly_sha256,
        "changedMetadata": {
            "coreProperties": {
                "canonicalPath": core_path,
                "originalPath": old_core_path,
                "preserved": True,
                "sha256": hashlib.sha256(core_bytes).hexdigest(),
                "sizeBytes": len(core_bytes),
            },
            "relationships": {
                "normalizedSha256": hashlib.sha256(
                    normalized_relationships
                ).hexdigest(),
                "normalizedSizeBytes": len(normalized_relationships),
                "originalSha256": hashlib.sha256(original_relationships).hexdigest(),
                "originalSizeBytes": len(original_relationships),
                "path": "_rels/.rels",
            },
        },
        "normalizedSha256": normalized_sha256,
        "normalizedSizeBytes": normalized_size,
        "originalSha256": original_sha256,
        "originalSizeBytes": original_size,
        "packageId": package_id,
        "preservedEntries": preserved_entries,
        "signatureStatus": "absent",
        "version": version,
    }


def pack_owner_package(
    ui_module: ModuleType,
    package: dict[str, Any],
    owner: dict[str, Any],
    owner_root: Path,
    owners_root: Path,
    feed: Path,
    config: Path,
    environment: dict[str, str],
) -> dict[str, Any]:
    project = source_file(owner_root, package["project"], f"{package['packageId']} project")
    command = [
        "dotnet",
        "pack",
        str(project),
        "-c",
        "Release",
        "-o",
        str(feed),
        f"-p:PackageVersion={package['version']}",
        f"-p:Version={package['version']}",
        f"-p:RepositoryCommit={owner['commit']}",
        f"-p:SourceRevisionId={owner['commit']}",
        f"-p:RepositoryUrl={owner['repository']}",
        "-p:RepositoryBranch=",
        "-p:PublishRepositoryUrl=true",
        "-p:ContinuousIntegrationBuild=true",
        "-p:Deterministic=true",
        "-p:DeterministicSourcePaths=true",
        "-p:EmbedUntrackedSources=false",
        f"-p:PathMap={owner_root.resolve()}=/_/src/{owner['directory']}",
        "-p:UseSharedCompilation=false",
        *(
            ["-p:PackageLicenseExpression=GPL-3.0-only"]
            if owner["repository"]
            == "https://github.com/ArchonMegalon/chummer6-core.git"
            else []
        ),
        f"-p:ChummerWorkspaceRoot={owners_root}",
        "-p:ChummerUseLocalCompatibilityTree=false",
        "-p:ChummerLocalContractsProject=",
        "-p:ChummerContractsPackageVersion=5.225.0",
        "-p:ChummerEngineContractsPackageVersion=5.225.0",
        "-p:ChummerCampaignContractsPackageVersion=0.1.0-preview",
        "-p:ChummerHubRegistryContractsPackageVersion=0.1.0-preview",
        "-p:ChummerRunContractsPackageVersion=0.1.0-preview",
        "-p:ChummerRunRegistryPackageVersion=0.1.0-preview",
        "-p:ChummerDesktopRuntimeIdentifiers=",
        "-p:RuntimeIdentifiers=",
        f"-p:RestoreSources={feed}",
        "-p:RestoreAdditionalProjectSources=",
        f"-p:RestoreConfigFile={config}",
        "-p:RestoreFallbackFolders=",
        "-p:RestoreIgnoreFailedSources=false",
        "-warnaserror:NU1603,NU1608",
        "--configfile",
        str(config),
        "--disable-build-servers",
        "--nologo",
        "-v",
        "minimal",
    ]
    ui_module.run(command, cwd=owner_root, environment=environment)
    output = feed / package["fileName"]
    if output.is_symlink() or not output.is_file():
        raise MaterializationError(f"pack did not emit {package['fileName']}")
    return normalize_package(output, package["packageId"], package["version"])


def compose_hub_packages(
    ui_module: ModuleType,
    lock: dict[str, Any],
    owners: dict[str, Path],
    sdk_root: Path,
    hub_staging: Path,
    feed: Path,
    environment: dict[str, str],
    host_rid: str,
) -> dict[str, Any]:
    authority = lock["canonicalOwnerFeed"]
    hub_root = owners[authority["ownerDirectory"]]
    if host_rid == "linux-x64":
        receipt = ui_module.import_hub_canonical_feed(
            lock, hub_root, sdk_root, hub_staging, feed, environment
        )
        return {
            **receipt,
            "hubV3NativeProducerExecuted": True,
            "producerMode": "hub-v3-pinned-x64-toolchain",
        }

    producer_path = source_file(
        hub_root, authority["producerPath"], "Hub canonical feed producer"
    )
    lock_path = source_file(hub_root, authority["lockPath"], "Hub package-plane lock")
    if sha256_file(producer_path) != authority["producerSha256"]:
        raise MaterializationError("Hub producer differs from UI authority")
    if sha256_file(lock_path) != authority["lockSha256"]:
        raise MaterializationError("Hub package-plane lock differs from UI authority")
    hub_module = load_module(producer_path, "chummer_hub_package_plane_authority")
    hub_lock = hub_module.load_lock(lock_path)
    observed_toolchain = {
        "dotnet_host": sha256_file(sdk_root / "dotnet"),
        "csc": sha256_file(sdk_root / "sdk/10.0.103/Roslyn/bincore/csc.dll"),
        "msbuild": sha256_file(sdk_root / "sdk/10.0.103/Microsoft.Build.dll"),
        "nuget_packaging": sha256_file(sdk_root / "sdk/10.0.103/NuGet.Packaging.dll"),
    }
    cross_arch_lock = dataclasses.replace(
        hub_lock, toolchain_sha256=observed_toolchain
    )
    cross_arch_marker = hashlib.sha256(
        (authority["lockSha256"] + "\nlinux-arm64-byte-reproduction\n").encode("ascii")
    ).hexdigest()
    hub_module.build_feed(
        cross_arch_lock,
        lock_sha256=cross_arch_marker,
        feed=hub_staging,
        dotnet=str(sdk_root / "dotnet"),
    )
    for package in authority["packages"]:
        source = hub_staging / package["fileName"]
        if (
            not source.is_file()
            or source.is_symlink()
            or source.stat().st_size != package["sizeBytes"]
            or sha256_file(source) != package["sha256"]
        ):
            raise MaterializationError(
                f"arm64 reproduction differs from canonical bytes: {package['fileName']}"
            )
        shutil.copyfile(source, feed / package["fileName"])
    return {
        "hubV3NativeProducerExecuted": False,
        "inventoryContract": authority["inventoryContract"],
        "inventorySha256": authority["inventorySha256"],
        "lockContract": authority["lockContract"],
        "lockSha256": authority["lockSha256"],
        "ownerCommit": next(
            row["commit"]
            for row in lock["owners"]
            if row["directory"] == authority["ownerDirectory"]
        ),
        "packageCount": len(authority["packages"]),
        "packages": authority["packages"],
        "producerMode": (
            "arm64-sdk-canonical-byte-reproduction-"
            "hub-v3-native-x64-producer-not-executed"
        ),
        "producerPath": authority["producerPath"],
        "producerSha256": authority["producerSha256"],
        "projectLockFilesEnforced": True,
        "status": "passed",
    }


def package_identity_rows(lock: dict[str, Any]) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for package in [*lock["externalPackages"], *lock["packages"]]:
        rows[package["fileName"]] = {
            "packageId": package["packageId"],
            "version": package["version"],
        }
    owners = {row["directory"]: row for row in lock["owners"]}
    for package in lock["packages"]:
        owner = owners[package["ownerDirectory"]]
        rows[package["fileName"]].update(
            {
                "commit": owner["commit"],
                "project": package["project"],
                "repository": owner["repository"],
            }
        )
    return rows


def owner_package_metadata(
    path: Path,
    identity: dict[str, str],
    owner_versions: dict[str, str],
) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(path) as archive:
            nuspec_names = [
                name for name in archive.namelist() if name.lower().endswith(".nuspec")
            ]
            if len(nuspec_names) != 1:
                raise MaterializationError(f"owner package has no exact nuspec: {path.name}")
            root = ET.fromstring(archive.read(nuspec_names[0]))
            repository_nodes = [
                node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "repository"
            ]
            license_nodes = [
                node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "license"
            ]
            if len(repository_nodes) != 1 or len(license_nodes) != 1:
                raise MaterializationError(
                    f"owner package provenance/license metadata is incomplete: {path.name}"
                )
            repository = repository_nodes[0]
            observed_repository = (repository.attrib.get("url") or "").strip()
            observed_commit = (repository.attrib.get("commit") or "").strip()
            if (
                observed_repository != identity["repository"]
                or observed_commit != identity["commit"]
            ):
                raise MaterializationError(
                    f"owner package source provenance differs: {path.name}"
                )
            license_node = license_nodes[0]
            license_type = (license_node.attrib.get("type") or "").strip()
            license_value = (license_node.text or "").strip()
            if license_type not in {"expression", "file"} or not license_value:
                raise MaterializationError(f"owner package license differs: {path.name}")
            if license_type == "file" and license_value not in archive.namelist():
                raise MaterializationError(
                    f"owner package license file is absent: {path.name}"
                )
            dependencies: list[dict[str, str]] = []
            for node in root.iter():
                if node.tag.rsplit("}", 1)[-1] != "dependency":
                    continue
                package_id = (node.attrib.get("id") or "").strip()
                if not package_id.startswith("Chummer."):
                    continue
                version = (node.attrib.get("version") or "").strip()
                expected = owner_versions.get(package_id)
                if expected is None or version not in {
                    expected,
                    f"[{expected}]",
                    f"[{expected}, )",
                }:
                    raise MaterializationError(
                        f"owner package internal dependency differs: {path.name}/{package_id}"
                    )
                dependencies.append({"packageId": package_id, "version": version})
    except (OSError, zipfile.BadZipFile, ET.ParseError) as exc:
        raise MaterializationError(f"could not validate owner package {path.name}: {exc}") from exc
    return {
        "internalDependencies": sorted(
            dependencies, key=lambda row: (row["packageId"], row["version"])
        ),
        "license": {"type": license_type, "value": license_value},
    }


def detailed_inventory(
    ui_module: ModuleType,
    feed: Path,
    identities: dict[str, dict[str, str]],
    owner_versions: dict[str, str],
    locked_sha256: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    basic = ui_module.package_inventory(feed, set(identities), locked_sha256)
    rows: list[dict[str, Any]] = []
    for row in basic:
        identity = identities[row["fileName"]]
        detailed = {
            **identity,
            **row,
            "archiveSha512": base64.b64encode(
                bytes.fromhex(sha512_file(feed / row["fileName"]))
            ).decode("ascii"),
        }
        if "repository" in identity:
            detailed.update(
                owner_package_metadata(feed / row["fileName"], identity, owner_versions)
            )
        rows.append(detailed)
    return rows


def validate_runtime_authority(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("packages")
    if (
        payload.get("contract") != "chummer6.linux-runtime-package-authority/v1"
        or not isinstance(rows, list)
        or len(rows) != 6
    ):
        raise MaterializationError("runtime package authority is invalid")
    observed: set[tuple[str, str]] = set()
    for index, row in enumerate(rows):
        required = {
            "contentHash",
            "fileName",
            "packageId",
            "rid",
            "sha256",
            "sha512",
            "sizeBytes",
            "source",
            "version",
        }
        if not isinstance(row, dict) or set(row) != required:
            raise MaterializationError(f"runtime package row {index} is invalid")
        identity = (row["rid"], row["packageId"])
        expected = EXPECTED_RUNTIME_PACKAGES.get(identity)
        if (
            expected is None
            or identity in observed
            or row["fileName"] != expected["fileName"]
            or row["source"] != expected["source"]
            or row["version"] != "10.0.3"
            or not canonical_base64_sha512(row["contentHash"])
            or not SHA256_RE.fullmatch(str(row["sha256"]))
            or not SHA512_RE.fullmatch(str(row["sha512"]))
            or not isinstance(row["sizeBytes"], int)
            or isinstance(row["sizeBytes"], bool)
            or row["sizeBytes"] <= 0
        ):
            raise MaterializationError(f"runtime package row {index} is not canonical")
        observed.add(identity)
    if observed != set(EXPECTED_RUNTIME_PACKAGES):
        raise MaterializationError("runtime package authority is incomplete")
    return rows


def fetch_runtime_package(row: dict[str, Any], destination: Path) -> None:
    target = destination / row["fileName"]
    if target.exists() or target.is_symlink():
        raise MaterializationError(f"runtime package target already exists: {target}")
    request = urllib.request.Request(
        row["source"], headers={"User-Agent": "chummer6-linux-source-lock/2"}
    )
    sha256 = hashlib.sha256()
    sha512 = hashlib.sha512()
    size = 0
    try:
        with urllib.request.urlopen(request, timeout=60) as source, target.open("xb") as output:
            while chunk := source.read(1024 * 1024):
                size += len(chunk)
                if size > 96 * 1024 * 1024:
                    raise MaterializationError("runtime package exceeds 96 MiB")
                sha256.update(chunk)
                sha512.update(chunk)
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    if (
        size != row["sizeBytes"]
        or sha256.hexdigest() != row["sha256"]
        or sha512.hexdigest() != row["sha512"]
    ):
        target.unlink(missing_ok=True)
        raise MaterializationError(f"runtime package bytes differ: {row['fileName']}")


def compare_or_write(
    generated: dict[str, Any], expected: Path | None, output: Path | None, label: str
) -> None:
    if (expected is None) == (output is None):
        raise MaterializationError(
            f"choose exactly one expected or generated {label} inventory path"
        )
    if expected is not None:
        if load_json(expected, f"expected {label} inventory") != generated:
            raise MaterializationError(f"{label} inventory differs from checked authority")
    else:
        assert output is not None
        exact_write_json(output, generated)


def normalization_output_projection(payload: dict[str, Any]) -> dict[str, Any]:
    packages = payload.get("packages")
    if not isinstance(packages, list):
        raise MaterializationError("normalization proof packages are invalid")
    projected: list[dict[str, Any]] = []
    for row in packages:
        if not isinstance(row, dict):
            raise MaterializationError("normalization proof package row is invalid")
        changed = row.get("changedMetadata")
        if not isinstance(changed, dict):
            raise MaterializationError("normalization proof metadata mapping is invalid")
        core = changed.get("coreProperties")
        relationships = changed.get("relationships")
        if not isinstance(core, dict) or not isinstance(relationships, dict):
            raise MaterializationError("normalization proof metadata rows are invalid")
        projected.append(
            {
                "assemblyPath": row.get("assemblyPath"),
                "assemblySha256": row.get("assemblySha256"),
                "changedMetadata": {
                    "coreProperties": {
                        "canonicalPath": core.get("canonicalPath"),
                        "preserved": core.get("preserved"),
                        "sha256": core.get("sha256"),
                        "sizeBytes": core.get("sizeBytes"),
                    },
                    "relationships": {
                        "normalizedSha256": relationships.get("normalizedSha256"),
                        "normalizedSizeBytes": relationships.get(
                            "normalizedSizeBytes"
                        ),
                        "path": relationships.get("path"),
                    },
                },
                "commit": row.get("commit"),
                "fileName": row.get("fileName"),
                "normalizedSha256": row.get("normalizedSha256"),
                "normalizedSizeBytes": row.get("normalizedSizeBytes"),
                "packageId": row.get("packageId"),
                "preservedEntries": row.get("preservedEntries"),
                "project": row.get("project"),
                "repository": row.get("repository"),
                "signatureStatus": row.get("signatureStatus"),
                "version": row.get("version"),
            }
        )
    return {
        "canonicalFeedInventorySha256": payload.get(
            "canonicalFeedInventorySha256"
        ),
        "contract": payload.get("contract"),
        "normalizationContract": payload.get("normalizationContract"),
        "packageCount": payload.get("packageCount"),
        "packages": projected,
    }


def validate_normalization_proof(
    payload: dict[str, Any], canonical_rows: list[dict[str, Any]]
) -> None:
    if set(payload) != {
        "canonicalFeedInventorySha256",
        "contract",
        "normalizationContract",
        "packageCount",
        "packages",
    }:
        raise MaterializationError("normalization proof root schema is invalid")
    packages = payload.get("packages")
    if (
        payload.get("contract") != NORMALIZATION_PROOF_CONTRACT
        or payload.get("normalizationContract") != NORMALIZATION_CONTRACT
        or not SHA256_RE.fullmatch(
            str(payload.get("canonicalFeedInventorySha256"))
        )
        or payload.get("canonicalFeedInventorySha256")
        != canonical_json_sha256(canonical_rows)
        or not isinstance(payload.get("packageCount"), int)
        or isinstance(payload.get("packageCount"), bool)
        or not isinstance(packages, list)
        or payload["packageCount"] != len(packages)
        or not packages
    ):
        raise MaterializationError("normalization proof contract is invalid")
    canonical_by_file = {row["fileName"]: row for row in canonical_rows}
    observed: set[str] = set()
    for index, row in enumerate(packages):
        label = f"normalization proof package {index}"
        if not isinstance(row, dict) or set(row) != {
            "assemblyPath",
            "assemblySha256",
            "changedMetadata",
            "commit",
            "fileName",
            "normalizedSha256",
            "normalizedSizeBytes",
            "originalSha256",
            "originalSizeBytes",
            "packageId",
            "preservedEntries",
            "project",
            "repository",
            "signatureStatus",
            "version",
        }:
            raise MaterializationError(f"{label} schema is invalid")
        file_name = row["fileName"]
        canonical = canonical_by_file.get(file_name)
        if (
            not isinstance(file_name, str)
            or file_name in observed
            or canonical is None
            or row["normalizedSha256"] != canonical["sha256"]
            or row["normalizedSizeBytes"] != canonical["sizeBytes"]
            or canonical.get("packageId") != row["packageId"]
            or canonical.get("version") != row["version"]
            or canonical.get("commit") != row["commit"]
            or canonical.get("project") != row["project"]
            or canonical.get("repository") != row["repository"]
            or row["signatureStatus"] != "absent"
            or not SHA256_RE.fullmatch(str(row["originalSha256"]))
            or not SHA256_RE.fullmatch(str(row["normalizedSha256"]))
            or not SHA256_RE.fullmatch(str(row["assemblySha256"]))
            or not isinstance(row["originalSizeBytes"], int)
            or isinstance(row["originalSizeBytes"], bool)
            or row["originalSizeBytes"] <= 0
            or not isinstance(row["normalizedSizeBytes"], int)
            or isinstance(row["normalizedSizeBytes"], bool)
            or row["normalizedSizeBytes"] <= 0
            or row["assemblyPath"] != f"lib/net10.0/{row['packageId']}.dll"
        ):
            raise MaterializationError(f"{label} identity or digest differs")
        changed = row["changedMetadata"]
        if not isinstance(changed, dict) or set(changed) != {
            "coreProperties",
            "relationships",
        }:
            raise MaterializationError(f"{label} metadata mapping is invalid")
        core = changed["coreProperties"]
        relationships = changed["relationships"]
        if (
            not isinstance(core, dict)
            or set(core)
            != {
                "canonicalPath",
                "originalPath",
                "preserved",
                "sha256",
                "sizeBytes",
            }
            or core.get("preserved") is not True
            or not SHA256_RE.fullmatch(str(core.get("sha256")))
            or not isinstance(core.get("sizeBytes"), int)
            or isinstance(core.get("sizeBytes"), bool)
            or core["sizeBytes"] <= 0
            or core.get("canonicalPath")
            != (
                "package/services/metadata/core-properties/"
                f"{core['sha256'][:32]}.psmdcp"
            )
            or not isinstance(core.get("originalPath"), str)
            or not core["originalPath"].startswith(
                "package/services/metadata/core-properties/"
            )
            or not core["originalPath"].endswith(".psmdcp")
        ):
            raise MaterializationError(f"{label} core-properties mapping is invalid")
        if (
            not isinstance(relationships, dict)
            or set(relationships)
            != {
                "normalizedSha256",
                "normalizedSizeBytes",
                "originalSha256",
                "originalSizeBytes",
                "path",
            }
            or relationships.get("path") != "_rels/.rels"
            or not SHA256_RE.fullmatch(str(relationships.get("originalSha256")))
            or not SHA256_RE.fullmatch(str(relationships.get("normalizedSha256")))
            or not isinstance(relationships.get("originalSizeBytes"), int)
            or isinstance(relationships.get("originalSizeBytes"), bool)
            or relationships["originalSizeBytes"] <= 0
            or not isinstance(relationships.get("normalizedSizeBytes"), int)
            or isinstance(relationships.get("normalizedSizeBytes"), bool)
            or relationships["normalizedSizeBytes"] <= 0
        ):
            raise MaterializationError(f"{label} relationships mapping is invalid")
        preserved = row["preservedEntries"]
        if not isinstance(preserved, list) or not preserved:
            raise MaterializationError(f"{label} preserved entries are invalid")
        preserved_paths: set[str] = set()
        for entry_index, entry in enumerate(preserved):
            if (
                not isinstance(entry, dict)
                or set(entry) != {"path", "sha256", "sizeBytes"}
                or not isinstance(entry.get("path"), str)
                or not entry["path"]
                or entry["path"] in preserved_paths
                or not SHA256_RE.fullmatch(str(entry.get("sha256")))
                or not isinstance(entry.get("sizeBytes"), int)
                or isinstance(entry.get("sizeBytes"), bool)
                or entry["sizeBytes"] < 0
            ):
                raise MaterializationError(
                    f"{label} preserved entry {entry_index} is invalid"
                )
            preserved_paths.add(entry["path"])
        if (
            "_rels/.rels" in preserved_paths
            or core["canonicalPath"] in preserved_paths
        ):
            raise MaterializationError(
                f"{label} changed metadata was mislabeled as preserved"
            )
        assembly = next(
            (entry for entry in preserved if entry["path"] == row["assemblyPath"]),
            None,
        )
        if assembly is None or assembly["sha256"] != row["assemblySha256"]:
            raise MaterializationError(f"{label} assembly preservation is not proven")
        nuspec_paths = [
            entry["path"]
            for entry in preserved
            if entry["path"].casefold().endswith(".nuspec")
        ]
        if len(nuspec_paths) != 1:
            raise MaterializationError(f"{label} does not preserve one exact nuspec")
        expected_relationships = canonical_relationships(
            nuspec_paths[0], core["canonicalPath"]
        )
        if (
            relationships["normalizedSha256"]
            != hashlib.sha256(expected_relationships).hexdigest()
            or relationships["normalizedSizeBytes"]
            != len(expected_relationships)
        ):
            raise MaterializationError(
                f"{label} normalized relationships are not derivable"
            )
        observed.add(file_name)
    if observed and [row["fileName"] for row in packages] != sorted(observed):
        raise MaterializationError("normalization proof package order is not canonical")


def compare_or_write_normalization_proof(
    generated: dict[str, Any],
    expected: Path | None,
    output: Path | None,
    canonical_rows: list[dict[str, Any]],
) -> Path:
    if (expected is None) == (output is None):
        raise MaterializationError(
            "choose exactly one expected or generated normalization proof path"
        )
    validate_normalization_proof(generated, canonical_rows)
    if expected is not None:
        checked = load_json(expected, "checked normalization proof")
        validate_normalization_proof(checked, canonical_rows)
        if normalization_output_projection(checked) != normalization_output_projection(
            generated
        ):
            raise MaterializationError(
                "independent package normalization differs from checked proof"
            )
        return expected
    assert output is not None
    exact_write_json(output, generated)
    return output


def compose(args: argparse.Namespace) -> dict[str, Any]:
    for path, label in (
        (args.ui_root, "UI checkout"),
        (args.owners_root, "owner root"),
        (args.sdk_root, "SDK root"),
    ):
        if not path.is_dir() or path.is_symlink():
            raise MaterializationError(f"{label} is missing or unsafe")
    if args.output_root.exists() or args.output_root.is_symlink():
        raise MaterializationError("materialization output must start absent")
    args.output_root.mkdir(mode=0o700, parents=True)

    sdk_authority = load_json(args.sdk_authority, "SDK authority")
    sdk_receipt = validate_sdk(args.sdk_root, sdk_authority, args.host_rid)
    ui_lock_path = source_file(args.ui_root, args.ui_lock_path, "UI package-plane lock")
    ui_verifier_path = source_file(
        args.ui_root, args.ui_verifier_path, "UI package-plane verifier"
    )
    if sha256_file(ui_lock_path) != args.ui_lock_sha256:
        raise MaterializationError("UI package-plane lock differs from authority")
    if sha256_file(ui_verifier_path) != args.ui_verifier_sha256:
        raise MaterializationError("UI package-plane verifier differs from authority")
    ui_module = load_module(ui_verifier_path, "chummer6_ui_package_plane_authority")
    ui_lock = ui_module.load_json(ui_lock_path)
    ui_module.validate_lock(ui_lock)
    ui_commit = git_output(args.ui_root, "rev-parse", "HEAD")
    if ui_commit != args.ui_commit:
        raise MaterializationError("UI checkout differs from exact consumer authority")
    if git_output(args.ui_root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise MaterializationError("UI checkout must start clean")

    upstream_receipt = load_json(
        args.upstream_verification_receipt, "final UI package-plane receipt"
    )
    upstream_packages = upstream_receipt.get("packageInventory")
    upstream_owner_sources = upstream_receipt.get("ownerSources")
    if (
        upstream_receipt.get("contractName")
        != "chummer6-ui.fresh-package-plane-verification"
        or upstream_receipt.get("contractVersion") != 5
        or upstream_receipt.get("status") != "passed"
        or upstream_receipt.get("mode") != "integration"
        or upstream_receipt.get("consumerCommit") != ui_commit
        or upstream_receipt.get("stubPackagesAllowed") is not False
        or upstream_receipt.get("localCompatibilityTree") is not False
        or upstream_receipt.get("packageCacheWasFresh") is not True
        or not isinstance(upstream_packages, list)
        or len(upstream_packages) != 96
        or not SHA256_RE.fullmatch(
            str(upstream_receipt.get("packageFeedInventorySha256"))
        )
        or canonical_json_sha256(upstream_packages)
        != upstream_receipt.get("packageFeedInventorySha256")
        or not isinstance(upstream_owner_sources, list)
    ):
        raise MaterializationError("final UI package-plane receipt is not exact")
    expected_upstream_owners = [
        {
            "commit": row["commit"],
            "directory": row["directory"],
            "repository": row["repository"],
            "sdkVersion": ui_lock["sdkVersion"],
        }
        for row in ui_lock["owners"]
    ]
    if upstream_owner_sources != expected_upstream_owners:
        raise MaterializationError("final UI receipt owner authorities differ")
    upstream_receipt_sha256 = sha256_file(args.upstream_verification_receipt)

    owner_roots: dict[str, Path] = {}
    for owner in ui_lock["owners"]:
        root = args.owners_root / owner["directory"]
        verify_checkout(root, owner["repository"], owner["commit"], owner["directory"])
        owner_roots[owner["directory"]] = root

    canonical_feed = args.output_root / "canonical-feed"
    canonical_feed.mkdir(mode=0o700)
    hub_staging = args.output_root / "hub-canonical-staging"
    caches = args.output_root / "composition-caches"
    sdk_parent = os.environ.copy()
    sdk_parent["PATH"] = f"{args.sdk_root}{os.pathsep}{sdk_parent.get('PATH') or os.defpath}"
    sdk_parent["DOTNET_ROOT"] = str(args.sdk_root)
    environment = ui_module.isolated_child_environment(caches, sdk_parent)
    environment.update(
        {
            "CI": "true",
            "DOTNET_ROOT": str(args.sdk_root),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "SOURCE_DATE_EPOCH": "0",
            "TZ": "UTC",
        }
    )
    ui_module.require_exact_sdk(
        args.output_root, environment, ui_lock["sdkVersion"], "package composition"
    )
    for package in ui_lock["externalPackages"]:
        ui_module.acquire_external_package(package, canonical_feed)
    pack_config = args.output_root / "pack.NuGet.Config"
    ui_module.write_nuget_config(pack_config, canonical_feed)
    hub_receipt = compose_hub_packages(
        ui_module,
        ui_lock,
        owner_roots,
        args.sdk_root,
        hub_staging,
        canonical_feed,
        environment,
        args.host_rid,
    )
    canonical_ids = {
        row["packageId"] for row in ui_lock["canonicalOwnerFeed"]["packages"]
    }
    owner_by_directory = {row["directory"]: row for row in ui_lock["owners"]}
    normalization_rows: list[dict[str, Any]] = []
    for package in ui_lock["packages"]:
        if package["packageId"] in canonical_ids:
            continue
        owner = owner_by_directory[package["ownerDirectory"]]
        normalization_rows.append(
            {
                **pack_owner_package(
                ui_module,
                package,
                owner,
                owner_roots[owner["directory"]],
                args.owners_root,
                canonical_feed,
                pack_config,
                environment,
                ),
                "commit": owner["commit"],
                "fileName": package["fileName"],
                "project": package["project"],
                "repository": owner["repository"],
            }
        )

    identities = package_identity_rows(ui_lock)
    owner_versions = {
        row["packageId"]: row["version"] for row in ui_lock["packages"]
    }
    locked_sha256 = {
        row["fileName"]: row["sha256"] for row in ui_lock["externalPackages"]
    }
    locked_sha256.update(
        {
            row["fileName"]: row["sha256"]
            for row in ui_lock["canonicalOwnerFeed"]["packages"]
        }
    )
    canonical_rows = detailed_inventory(
        ui_module, canonical_feed, identities, owner_versions, locked_sha256
    )
    canonical_inventory = {
        "contract": FEED_CONTRACT,
        "hubCanonicalFeed": {
            "inventorySha256": ui_lock["canonicalOwnerFeed"]["inventorySha256"],
            "lockSha256": ui_lock["canonicalOwnerFeed"]["lockSha256"],
            "producerSha256": ui_lock["canonicalOwnerFeed"]["producerSha256"],
        },
        "normalizationContract": NORMALIZATION_CONTRACT,
        "packageCount": len(canonical_rows),
        "packageInventorySha256": canonical_json_sha256(canonical_rows),
        "packages": canonical_rows,
        "upstreamVerification": {
            "consumerCommit": upstream_receipt["consumerCommit"],
            "contractName": upstream_receipt["contractName"],
            "contractVersion": upstream_receipt["contractVersion"],
            "packageCount": len(upstream_packages),
            "packageFeedInventorySha256": upstream_receipt[
                "packageFeedInventorySha256"
            ],
            "receiptSha256": upstream_receipt_sha256,
            "status": upstream_receipt["status"],
        },
        "uiCommit": ui_commit,
        "uiLockSha256": args.ui_lock_sha256,
        "uiVerifierSha256": args.ui_verifier_sha256,
    }
    compare_or_write(
        canonical_inventory,
        args.expected_feed_inventory,
        args.write_feed_inventory,
        "canonical feed",
    )
    canonical_inventory_file = args.expected_feed_inventory or args.write_feed_inventory
    assert canonical_inventory_file is not None
    canonical_inventory_file_sha256 = sha256_file(canonical_inventory_file)
    normalization_proof = {
        "canonicalFeedInventorySha256": canonical_inventory[
            "packageInventorySha256"
        ],
        "contract": NORMALIZATION_PROOF_CONTRACT,
        "normalizationContract": NORMALIZATION_CONTRACT,
        "packageCount": len(normalization_rows),
        "packages": sorted(normalization_rows, key=lambda row: row["fileName"]),
    }
    normalization_proof_file = compare_or_write_normalization_proof(
        normalization_proof,
        args.expected_normalization_proof,
        args.write_normalization_proof,
        canonical_rows,
    )
    normalization_proof_file_sha256 = sha256_file(normalization_proof_file)

    runtime_rows = validate_runtime_authority(
        load_json(args.runtime_authority, "runtime package authority")
    )
    rid_receipts: list[dict[str, Any]] = []
    for rid in SUPPORTED_RIDS:
        restore_feed = args.output_root / "rid-feeds" / rid
        restore_feed.mkdir(mode=0o700, parents=True)
        for row in canonical_rows:
            source = canonical_feed / row["fileName"]
            target = restore_feed / row["fileName"]
            shutil.copyfile(source, target)
            if sha256_file(target) != row["sha256"]:
                raise MaterializationError(f"RID feed copy drift: {rid}/{target.name}")
        rid_runtime = [row for row in runtime_rows if row["rid"] == rid]
        rid_identities = dict(identities)
        for row in rid_runtime:
            fetch_runtime_package(row, restore_feed)
            rid_identities[row["fileName"]] = {
                "packageId": row["packageId"],
                "version": row["version"],
            }
        rid_locked = {row["fileName"]: row["sha256"] for row in canonical_rows}
        rid_locked.update({row["fileName"]: row["sha256"] for row in rid_runtime})
        rid_rows = detailed_inventory(
            ui_module, restore_feed, rid_identities, owner_versions, rid_locked
        )
        rid_inventory = {
            "baseFeedFileSha256": canonical_inventory_file_sha256,
            "baseFeedInventorySha256": canonical_inventory["packageInventorySha256"],
            "contract": RID_FEED_CONTRACT,
            "packageCount": len(rid_rows),
            "packages": rid_rows,
            "restoreFeedInventorySha256": canonical_json_sha256(rid_rows),
            "runtimeIdentifier": rid,
            "runtimePackageAuthoritySha256": sha256_file(args.runtime_authority),
        }
        expected = (
            args.expected_x64_inventory
            if rid == "linux-x64"
            else args.expected_arm64_inventory
        )
        output = (
            args.write_x64_inventory
            if rid == "linux-x64"
            else args.write_arm64_inventory
        )
        compare_or_write(rid_inventory, expected, output, rid)
        inventory_file = expected or output
        assert inventory_file is not None
        config = args.output_root / f"NuGet.{rid}.Config"
        ui_module.write_nuget_config(config, restore_feed)
        rid_receipts.append(
            {
                "feed": str(restore_feed),
                "inventoryFileSha256": sha256_file(inventory_file),
                "inventorySha256": rid_inventory["restoreFeedInventorySha256"],
                "nugetConfig": str(config),
                "nugetConfigSha256": sha256_file(config),
                "runtimeIdentifier": rid,
            }
        )

    if len({row["inventorySha256"] for row in rid_receipts}) != 2:
        raise MaterializationError("RID restore feeds were accidentally relabeled as identical")
    if any(
        load_json(
            args.expected_x64_inventory
            if row["runtimeIdentifier"] == "linux-x64"
            else args.expected_arm64_inventory,
            f"{row['runtimeIdentifier']} checked inventory",
        )["baseFeedInventorySha256"]
        != canonical_inventory["packageInventorySha256"]
        for row in rid_receipts
        if args.expected_x64_inventory is not None
        and args.expected_arm64_inventory is not None
    ):
        raise MaterializationError("RID feeds do not bind one byte-identical canonical feed")

    receipt = {
        "canonicalFeed": str(canonical_feed),
        "canonicalFeedFileSha256": canonical_inventory_file_sha256,
        "canonicalFeedInventorySha256": canonical_inventory[
            "packageInventorySha256"
        ],
        "contract": CONTRACT,
        "hostRid": args.host_rid,
        "hubCanonicalFeed": hub_receipt,
        "normalization": {
            "contract": NORMALIZATION_CONTRACT,
            "inputInventorySha256": canonical_json_sha256(
                [
                    {
                        "fileName": next(
                            package["fileName"]
                            for package in ui_lock["packages"]
                            if package["packageId"] == row["packageId"]
                            and package["version"] == row["version"]
                        ),
                        "originalSha256": row["originalSha256"],
                        "originalSizeBytes": row["originalSizeBytes"],
                    }
                    for row in normalization_rows
                ]
            ),
            "packages": normalization_rows,
            "proofFileSha256": normalization_proof_file_sha256,
        },
        "ownerSources": ui_lock["owners"],
        "releaseEvidenceEligible": False,
        "releaseStatus": "review_required",
        "ridFeeds": rid_receipts,
        "sdk": sdk_receipt,
        "uiCommit": ui_commit,
        "uiLockSha256": args.ui_lock_sha256,
        "upstreamVerificationReceiptSha256": upstream_receipt_sha256,
    }
    receipt_path = args.output_root / "materialization-receipt.json"
    exact_write_json(receipt_path, receipt)
    return {**receipt, "receiptPath": str(receipt_path), "receiptSha256": sha256_file(receipt_path)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ui-root", type=Path, required=True)
    parser.add_argument("--owners-root", type=Path, required=True)
    parser.add_argument("--sdk-root", type=Path, required=True)
    parser.add_argument("--sdk-authority", type=Path, required=True)
    parser.add_argument("--runtime-authority", type=Path, required=True)
    parser.add_argument(
        "--upstream-verification-receipt", type=Path, required=True
    )
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--host-rid", choices=SUPPORTED_RIDS, required=True)
    parser.add_argument("--ui-commit", required=True)
    parser.add_argument("--ui-lock-path", default="config/package-plane.lock.json")
    parser.add_argument("--ui-lock-sha256", required=True)
    parser.add_argument(
        "--ui-verifier-path", default="scripts/ai/verify_fresh_checkout_package_plane.py"
    )
    parser.add_argument("--ui-verifier-sha256", required=True)
    parser.add_argument("--expected-feed-inventory", type=Path)
    parser.add_argument("--expected-normalization-proof", type=Path)
    parser.add_argument("--expected-x64-inventory", type=Path)
    parser.add_argument("--expected-arm64-inventory", type=Path)
    parser.add_argument("--write-feed-inventory", type=Path)
    parser.add_argument("--write-normalization-proof", type=Path)
    parser.add_argument("--write-x64-inventory", type=Path)
    parser.add_argument("--write-arm64-inventory", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        receipt = compose(args)
    except (
        MaterializationError,
        OSError,
        subprocess.SubprocessError,
        urllib.error.URLError,
        zipfile.BadZipFile,
    ) as exc:
        print(f"linux-package-plane:error: {exc}", file=sys.stderr)
        return 2
    print(f"PACKAGE_PLANE_RECEIPT\t{receipt['receiptPath']}\t{receipt['receiptSha256']}")
    print(
        "CANONICAL_FEED\t"
        f"{receipt['canonicalFeed']}\t{receipt['canonicalFeedInventorySha256']}"
    )
    for row in receipt["ridFeeds"]:
        print(
            "RID_FEED\t"
            f"{row['runtimeIdentifier']}\t{row['feed']}\t{row['inventorySha256']}"
        )
        print(
            "RID_NUGET_CONFIG\t"
            f"{row['runtimeIdentifier']}\t{row['nugetConfig']}\t{row['nugetConfigSha256']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
