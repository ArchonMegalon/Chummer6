from __future__ import annotations

import argparse
import base64
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock, patch


REPO_ROOT = Path(__file__).resolve().parents[1]
VERIFIER_PATH = REPO_ROOT / "scripts" / "verify_linux_source_lock.py"

SPEC = importlib.util.spec_from_file_location("verify_linux_source_lock_v2_tested", VERIFIER_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - import machinery guard
    raise RuntimeError(f"cannot load verifier: {VERIFIER_PATH}")
VERIFIER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VERIFIER
SPEC.loader.exec_module(VERIFIER)


def checked_json(relative: str) -> dict:
    return json.loads((REPO_ROOT / relative).read_text(encoding="utf-8"))


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def digest64(seed: bytes) -> str:
    return base64.b64encode(hashlib.sha512(seed).digest()).decode("ascii")


class StrictJsonAndPortabilityTests(unittest.TestCase):
    def test_load_json_accepts_a_canonical_object(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "authority.json"
            path.write_text('{"contract":"example/v1","rows":[]}\n', encoding="utf-8")
            self.assertEqual(
                {"contract": "example/v1", "rows": []}, VERIFIER.load_json(path)
            )

    def test_load_json_rejects_duplicate_keys_at_every_depth(self) -> None:
        cases = {
            "top-level": '{"contract":"a","contract":"b"}\n',
            "nested": '{"outer":{"digest":"a","digest":"b"}}\n',
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for name, text in cases.items():
                with self.subTest(name=name):
                    path = root / f"{name}.json"
                    path.write_text(text, encoding="utf-8")
                    with self.assertRaisesRegex(VERIFIER.LockError, "duplicate JSON key"):
                        VERIFIER.load_json(path)

    def test_load_json_rejects_non_object_and_malformed_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for name, text in (("array", "[]\n"), ("malformed", '{"a":]\n')):
                with self.subTest(name=name):
                    path = root / f"{name}.json"
                    path.write_text(text, encoding="utf-8")
                    with self.assertRaises(VERIFIER.LockError):
                        VERIFIER.load_json(path)

    def test_portable_json_allows_https_authorities(self) -> None:
        payload = {
            "authority": "https://api.nuget.org/v3-flatcontainer/package/1.0/package.nupkg",
            "mirror": "https://builds.dotnet.microsoft.com/dotnet/Sdk/10.0.103/file.tar.gz",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "portable.json"
            write_json(path, payload)
            VERIFIER.portable_json(path, "portable authority")

    def test_portable_json_rejects_posix_machine_local_paths(self) -> None:
        cases = (
            "/tmp/chummer/receipt.json",
            "/var/tmp/chummer/receipt.json",
            "/docker/chummercomplete/receipt.json",
            "/workspace/release/receipt.json",
            "/home/alice/receipt.json",
            "/Users/alice/receipt.json",
            "file:///srv/private/receipt.json",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "receipt.json"
            for value in cases:
                with self.subTest(value=value):
                    write_json(path, {"path": value})
                    with self.assertRaisesRegex(VERIFIER.LockError, "non-portable"):
                        VERIFIER.portable_json(path, "receipt")

    def test_portable_json_rejects_windows_drive_and_unc_paths(self) -> None:
        cases = (
            r"C:\build\chummer\receipt.json",
            "C:/build/chummer/receipt.json",
            r"\\release-server\evidence\receipt.json",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "receipt.json"
            for value in cases:
                with self.subTest(value=value):
                    write_json(path, {"path": value})
                    with self.assertRaisesRegex(VERIFIER.LockError, "non-portable"):
                        VERIFIER.portable_json(path, "receipt")

    def test_generator_diagnostics_preserve_error_but_remove_paths_and_secrets(self) -> None:
        sentinel = "sentinel-bearer-value-92f0"
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "generator.log"
            path.write_text(
                "package generator failed while normalizing owner feed\n"
                "source=/docker/private/owner/project.csproj\n"
                "windows=C:\\private\\owner\\project.csproj\n"
                "unc=\\\\build-server\\private-share\\project.csproj\n"
                f"Authorization: Bearer {sentinel}\n"
                f"api_key={sentinel}\n"
                f"password={sentinel}\n"
                f"client_secret={sentinel}\n"
                f"access-token={sentinel}\n",
                encoding="utf-8",
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                VERIFIER.sanitize_diagnostics(path, [temp_dir])
            sanitized = output.getvalue()
        self.assertIn("package generator failed while normalizing owner feed", sanitized)
        self.assertIn("[redacted-secret]", sanitized)
        self.assertNotIn(sentinel, sanitized)
        self.assertNotIn("/docker/private", sanitized)
        self.assertNotIn("C:\\private", sanitized)
        self.assertNotIn("\\\\build-server", sanitized)


class UnsymlinkedCliPathTests(unittest.TestCase):
    def test_regular_file_and_directory_are_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = root / "authority.json"
            path.write_text("{}\n", encoding="utf-8")
            self.assertEqual(root, VERIFIER.unsymlinked_cli_path(root, "root", kind="directory"))
            self.assertEqual(
                path, VERIFIER.unsymlinked_cli_path(path, "authority", kind="file")
            )

    def test_direct_file_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "target.json"
            target.write_text("{}\n", encoding="utf-8")
            link = root / "authority.json"
            link.symlink_to(target)
            with self.assertRaisesRegex(VERIFIER.LockError, "symlink"):
                VERIFIER.unsymlinked_cli_path(link, "authority", kind="file")

    def test_parent_directory_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            real = root / "real"
            real.mkdir()
            (real / "authority.json").write_text("{}\n", encoding="utf-8")
            alias = root / "alias"
            alias.symlink_to(real, target_is_directory=True)
            with self.assertRaisesRegex(VERIFIER.LockError, "symlink"):
                VERIFIER.unsymlinked_cli_path(
                    alias / "authority.json", "authority", kind="file"
                )

    def test_missing_output_below_symlinked_parent_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            real = root / "real"
            real.mkdir()
            alias = root / "alias"
            alias.symlink_to(real, target_is_directory=True)
            with self.assertRaisesRegex(VERIFIER.LockError, "symlink"):
                VERIFIER.unsymlinked_cli_path(
                    alias / "new.json",
                    "output",
                    kind="path",
                    allow_missing=True,
                )


class ProjectLockClosureTests(unittest.TestCase):
    @staticmethod
    def _descriptor(rid: str) -> dict:
        lock = checked_json("RELEASE.lock.json")
        return next(
            row for row in lock["nuget"]["packageLocks"]
            if row["runtimeIdentifier"] == rid
        )

    @staticmethod
    def _validated_rows(rid: str) -> dict:
        descriptor = ProjectLockClosureTests._descriptor(rid)
        return {
            row["project"]: VERIFIER.validate_package_lock(
                REPO_ROOT / row["path"], rid, row["project"]
            )
            for row in descriptor["projectLocks"]
        }

    def test_checked_authority_binds_exactly_three_project_locks_per_rid(self) -> None:
        for rid in VERIFIER.SUPPORTED_RIDS:
            with self.subTest(rid=rid):
                descriptor = self._descriptor(rid)
                projects = [row["project"] for row in descriptor["projectLocks"]]
                self.assertEqual(list(VERIFIER.PROJECT_LOCK_ORDER), projects)
                for row in descriptor["projectLocks"]:
                    path = REPO_ROOT / row["path"]
                    self.assertEqual(row["sha256"], VERIFIER.sha256_file(path))
                rows = self._validated_rows(rid)
                root = VERIFIER.validate_project_lock_closure(rows, rid)
                self.assertEqual(39, len(root))
                self.assertLessEqual(
                    set(rows[VERIFIER.DESKTOP_RUNTIME_PROJECT]), set(root)
                )
                self.assertLessEqual(
                    set(rows[VERIFIER.PRESENTATION_PROJECT]), set(root)
                )

    def test_project_lock_descriptor_mutations_fail_closed(self) -> None:
        original = checked_json("RELEASE.lock.json")

        def missing(payload: dict) -> None:
            payload["nuget"]["packageLocks"][0]["projectLocks"].pop()

        def reordered(payload: dict) -> None:
            payload["nuget"]["packageLocks"][0]["projectLocks"].reverse()

        def relabeled(payload: dict) -> None:
            payload["nuget"]["packageLocks"][0]["projectLocks"][1]["project"] = (
                VERIFIER.PRESENTATION_PROJECT
            )

        def wrong_sha(payload: dict) -> None:
            payload["nuget"]["packageLocks"][0]["projectLocks"][1]["sha256"] = (
                "0" * 64
            )

        def wrong_path(payload: dict) -> None:
            payload["nuget"]["packageLocks"][0]["projectLocks"][1]["path"] = (
                "release-locks/avalonia-linux-x64.packages.lock.json"
            )

        mutations = {
            "missing": (missing, "exactly three"),
            "reordered": (reordered, "project order differs"),
            "relabeled": (relabeled, "project order differs"),
            "wrong SHA": (wrong_sha, "SHA256 differs"),
            "wrong path": (wrong_path, "authority path differs"),
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for name, (mutate, expected) in mutations.items():
                with self.subTest(name=name):
                    payload = deepcopy(original)
                    mutate(payload)
                    path = root / f"{name.replace(' ', '-')}.lock.json"
                    write_json(path, payload)
                    with self.assertRaisesRegex(VERIFIER.LockError, expected):
                        VERIFIER.validate_lock(path, REPO_ROOT)

    def test_project_specific_direct_and_project_graph_mutations_fail(self) -> None:
        rid = "linux-x64"
        source = checked_json(
            "release-locks/desktop-runtime-linux-x64.packages.lock.json"
        )
        mutations = {
            "direct graph": lambda payload: payload["dependencies"]["net10.0"][
                "System.Security.Cryptography.ProtectedData"
            ].__setitem__("resolved", "10.0.1"),
            "project graph": lambda payload: payload["dependencies"]["net10.0"].pop(
                "chummer.presentation"
            ),
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for name, mutate in mutations.items():
                with self.subTest(name=name):
                    payload = deepcopy(source)
                    mutate(payload)
                    path = root / f"{name.replace(' ', '-')}.packages.lock.json"
                    write_json(path, payload)
                    with self.assertRaisesRegex(VERIFIER.LockError, "graph differs"):
                        VERIFIER.validate_package_lock(
                            path, rid, VERIFIER.DESKTOP_RUNTIME_PROJECT
                        )

    def test_auxiliary_content_hash_must_match_the_root_closure(self) -> None:
        rid = "linux-x64"
        payload = checked_json(
            "release-locks/presentation-linux-x64.packages.lock.json"
        )
        payload["dependencies"]["net10.0"]["Chummer.Ui.Kit"]["contentHash"] = (
            digest64(b"substituted presentation package content")
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "presentation.packages.lock.json"
            write_json(path, payload)
            rows = self._validated_rows(rid)
            rows[VERIFIER.PRESENTATION_PROJECT] = VERIFIER.validate_package_lock(
                path, rid, VERIFIER.PRESENTATION_PROJECT
            )
            with self.assertRaisesRegex(VERIFIER.LockError, "content hash differs"):
                VERIFIER.validate_project_lock_closure(rows, rid)


class RuntimeAndRidFeedAuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runtime_path = REPO_ROOT / "release-locks/linux-runtime-packages.authority.json"
        cls.base_path = REPO_ROOT / "release-locks/linux-package-feed.inventory.json"
        cls.runtime_payload = checked_json(
            "release-locks/linux-runtime-packages.authority.json"
        )
        cls.base_payload = checked_json("release-locks/linux-package-feed.inventory.json")

    def test_checked_runtime_authority_is_exactly_six_rows(self) -> None:
        observed = VERIFIER.validate_runtime_authority(deepcopy(self.runtime_payload))
        self.assertEqual(6, len(observed))
        self.assertEqual(VERIFIER.expected_runtime_identities(), set(observed))

    def test_runtime_authority_rejects_deleted_extra_duplicate_and_substituted_rows(self) -> None:
        def delete_row(payload: dict) -> None:
            payload["packages"].pop()

        def add_row(payload: dict) -> None:
            payload["packages"].append(deepcopy(payload["packages"][0]))

        def duplicate_with_six_rows(payload: dict) -> None:
            payload["packages"][-1] = deepcopy(payload["packages"][0])

        def substitute_identity(payload: dict) -> None:
            row = payload["packages"][0]
            row["packageId"] = "Example.Runtime.linux-x64"
            row["fileName"] = "example.runtime.linux-x64.10.0.3.nupkg"
            row["source"] = (
                "https://api.nuget.org/v3-flatcontainer/example.runtime.linux-x64/"
                "10.0.3/example.runtime.linux-x64.10.0.3.nupkg"
            )

        def relabel_rid(payload: dict) -> None:
            payload["packages"][0]["rid"] = "linux-arm64"

        def boolean_size(payload: dict) -> None:
            payload["packages"][0]["sizeBytes"] = True

        mutations = {
            "deleted": delete_row,
            "extra": add_row,
            "duplicate": duplicate_with_six_rows,
            "substituted": substitute_identity,
            "rid relabel": relabel_rid,
            "boolean size": boolean_size,
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                payload = deepcopy(self.runtime_payload)
                mutate(payload)
                with self.assertRaises(VERIFIER.LockError):
                    VERIFIER.validate_runtime_authority(payload)

    def _validate_rid_payload(self, payload: dict, rid: str) -> dict:
        runtime_rows = VERIFIER.validate_runtime_authority(
            deepcopy(self.runtime_payload)
        )
        return VERIFIER.validate_rid_feed_inventory(
            payload,
            rid,
            deepcopy(self.base_payload),
            VERIFIER.sha256_file(self.base_path),
            runtime_rows,
            VERIFIER.sha256_file(self.runtime_path),
        )

    @staticmethod
    def _reseal_rid_payload(payload: dict) -> None:
        payload["restoreFeedInventorySha256"] = VERIFIER.canonical_json_sha256(
            payload["packages"]
        )

    def test_checked_rid_feed_inventories_validate_with_exact_99_row_projection(self) -> None:
        for rid in VERIFIER.SUPPORTED_RIDS:
            with self.subTest(rid=rid):
                payload = checked_json(f"release-locks/{rid}-restore-feed.inventory.json")
                observed = self._validate_rid_payload(payload, rid)
                self.assertEqual(99, len(observed))

    def test_rid_feed_rejects_canonical_base_reordering_even_when_resealed(self) -> None:
        rid = "linux-x64"
        payload = checked_json(f"release-locks/{rid}-restore-feed.inventory.json")
        runtime_ids = {
            identity
            for identity in VERIFIER.expected_runtime_identities()
            if identity[0].endswith(rid)
        }
        base_indices = [
            index
            for index, row in enumerate(payload["packages"])
            if (row["packageId"].casefold(), row["version"].casefold())
            not in runtime_ids
        ]
        first, second = base_indices[:2]
        payload["packages"][first], payload["packages"][second] = (
            payload["packages"][second],
            payload["packages"][first],
        )
        self._reseal_rid_payload(payload)
        with self.assertRaisesRegex(VERIFIER.LockError, "order|projection"):
            self._validate_rid_payload(payload, rid)

    def test_rid_feed_rejects_runtime_substitution_even_when_resealed(self) -> None:
        rid = "linux-x64"
        payload = checked_json(f"release-locks/{rid}-restore-feed.inventory.json")
        index = next(
            index
            for index, row in enumerate(payload["packages"])
            if row["packageId"].casefold().startswith("microsoft.netcore.app.host")
        )
        row = payload["packages"][index]
        row["packageId"] = "Example.Runtime.linux-x64"
        row["fileName"] = "example.runtime.linux-x64.10.0.3.nupkg"
        self._reseal_rid_payload(payload)
        with self.assertRaises(VERIFIER.LockError):
            self._validate_rid_payload(payload, rid)

    def test_rid_feed_rejects_extra_row_and_rid_relabel(self) -> None:
        rid = "linux-x64"
        original = checked_json(f"release-locks/{rid}-restore-feed.inventory.json")

        extra = deepcopy(original)
        row = deepcopy(extra["packages"][-1])
        row["packageId"] = "Example.Extra"
        row["version"] = "1.0.0"
        row["fileName"] = "example.extra.1.0.0.nupkg"
        extra["packages"].append(row)
        extra["packageCount"] = 100
        self._reseal_rid_payload(extra)
        with self.assertRaises(VERIFIER.LockError):
            self._validate_rid_payload(extra, rid)

        relabeled = deepcopy(original)
        relabeled["runtimeIdentifier"] = "linux-arm64"
        with self.assertRaises(VERIFIER.LockError):
            self._validate_rid_payload(relabeled, rid)

    def test_rid_feed_rejects_runtime_byte_substitution_even_when_resealed(self) -> None:
        rid = "linux-arm64"
        payload = checked_json(f"release-locks/{rid}-restore-feed.inventory.json")
        row = next(
            item
            for item in payload["packages"]
            if item["packageId"].casefold().startswith("microsoft.netcore.app.runtime")
        )
        row["sha256"] = "0" * 64 if row["sha256"] != "0" * 64 else "1" * 64
        self._reseal_rid_payload(payload)
        with self.assertRaisesRegex(VERIFIER.LockError, "runtime bytes"):
            self._validate_rid_payload(payload, rid)


class SdkAuthorityAndExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sdk_payload = checked_json(
            "release-locks/dotnet-sdk-10.0.103.authority.json"
        )

    def test_checked_sdk_authority_covers_both_exact_linux_rids(self) -> None:
        observed = VERIFIER.validate_sdk_authority(deepcopy(self.sdk_payload))
        self.assertEqual(set(VERIFIER.SUPPORTED_RIDS), set(observed))

    def test_sdk_authority_rejects_structural_and_identity_mutations(self) -> None:
        def delete_archive(payload: dict) -> None:
            payload["archives"].pop()

        def add_archive(payload: dict) -> None:
            payload["archives"].append(deepcopy(payload["archives"][0]))

        def duplicate_rid(payload: dict) -> None:
            payload["archives"][1] = deepcopy(payload["archives"][0])

        def wrong_source(payload: dict) -> None:
            payload["archives"][0]["source"] = "https://attacker.invalid/sdk.tar.gz"

        def boolean_size(payload: dict) -> None:
            payload["archives"][0]["sizeBytes"] = True

        def missing_tool(payload: dict) -> None:
            payload["archives"][0]["toolchainFiles"].pop()

        def wrong_tool_path(payload: dict) -> None:
            payload["archives"][0]["toolchainFiles"][0]["path"] = "other/dotnet"

        def legacy_execution(payload: dict) -> None:
            payload["legacyInstallerReference"]["executionAllowed"] = True

        mutations = {
            "deleted archive": delete_archive,
            "extra archive": add_archive,
            "duplicate RID": duplicate_rid,
            "source substitution": wrong_source,
            "boolean size": boolean_size,
            "missing tool": missing_tool,
            "tool path substitution": wrong_tool_path,
            "legacy installer execution": legacy_execution,
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                payload = deepcopy(self.sdk_payload)
                mutate(payload)
                with self.assertRaises(VERIFIER.LockError):
                    VERIFIER.validate_sdk_authority(payload)

    def _sdk_tree(self, root: Path, *, version_output: str = "10.0.103") -> dict:
        tool_rows = []
        for name, relative in VERIFIER.SDK_TOOL_PATHS.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if name == "dotnet_host":
                content = f"#!/bin/sh\nprintf '%s\\n' '{version_output}'\n".encode()
            else:
                content = f"authenticated:{name}".encode()
            path.write_bytes(content)
            if name == "dotnet_host":
                path.chmod(0o755)
            tool_rows.append(
                {
                    "name": name,
                    "path": relative,
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "sizeBytes": len(content),
                }
            )
        return {"toolchainFiles": tool_rows}

    def test_sdk_directory_requires_exact_bytes_and_executable_dotnet(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            row = self._sdk_tree(root)
            VERIFIER.validate_sdk_directory(root, row, execute=True)

            csc = root / VERIFIER.SDK_TOOL_PATHS["csc"]
            csc.write_bytes(csc.read_bytes() + b"tampered")
            with self.assertRaisesRegex(VERIFIER.LockError, "toolchain bytes"):
                VERIFIER.validate_sdk_directory(root, row, execute=False)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            row = self._sdk_tree(root)
            (root / "dotnet").chmod(0o644)
            with self.assertRaisesRegex(VERIFIER.LockError, "not executable"):
                VERIFIER.validate_sdk_directory(root, row, execute=False)

    def test_sdk_directory_rejects_authenticated_bytes_that_report_wrong_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            row = self._sdk_tree(root, version_output="10.0.999-attacker")
            with self.assertRaisesRegex(VERIFIER.LockError, "exact version"):
                VERIFIER.validate_sdk_directory(root, row, execute=True)

    def test_install_sdk_rejects_archive_byte_substitution_before_extraction(self) -> None:
        expected = b"expected authenticated SDK archive"
        substituted = b"x" * len(expected)
        self.assertEqual(len(expected), len(substituted))
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive = root / "sdk.tar.gz"
            archive.write_bytes(substituted)
            context = {
                "sdkRows": {
                    "linux-x64": {
                        "sizeBytes": len(expected),
                        "sha256": hashlib.sha256(expected).hexdigest(),
                        "sha512": hashlib.sha512(expected).hexdigest(),
                    }
                }
            }
            with self.assertRaisesRegex(VERIFIER.LockError, "archive differs"):
                VERIFIER.install_sdk(context, "linux-x64", archive, root / "sdk")

    def test_official_tar_root_spellings_are_safe_noop_members(self) -> None:
        self.assertIsNone(VERIFIER.normalized_tar_name("."))
        self.assertIsNone(VERIFIER.normalized_tar_name("./"))
        self.assertEqual("sdk/10.0.103/file", VERIFIER.normalized_tar_name("./sdk/10.0.103/file"))
        for unsafe in ("sdk/file", "../sdk/file", "./../sdk/file"):
            with self.subTest(unsafe=unsafe), self.assertRaises(VERIFIER.LockError):
                VERIFIER.normalized_tar_name(unsafe)


class DirectSyntheticCacheTests(unittest.TestCase):
    def test_real_cache_metadata_archive_and_source_substitutions_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            feed = root / "feed"
            cache = root / "cache"
            package_root = cache / "example.package" / "1.0.0"
            feed.mkdir()
            package_root.mkdir(parents=True)
            archive_bytes = b"synthetic exact package bytes"
            file_name = "example.package.1.0.0.nupkg"
            feed_archive = feed / file_name
            feed_archive.write_bytes(archive_bytes)
            archive_sha512 = base64.b64encode(
                hashlib.sha512(archive_bytes).digest()
            ).decode("ascii")
            content_hash = digest64(b"synthetic NuGet content hash")
            source_sha256 = hashlib.sha256(archive_bytes).hexdigest()
            cache_archive = package_root / file_name
            cache_archive.write_bytes(archive_bytes)
            (package_root / f"{file_name}.sha512").write_text(
                archive_sha512, encoding="ascii"
            )
            metadata = {
                "version": 2,
                "contentHash": content_hash,
                "source": str(feed.resolve()),
            }
            write_json(package_root / ".nupkg.metadata", metadata)
            expected_rows = [
                {
                    "archiveSha512": archive_sha512,
                    "contentHash": content_hash,
                    "packageId": "Example.Package",
                    "sourceSha256": source_sha256,
                    "version": "1.0.0",
                }
            ]
            restore_rows = {
                ("example.package", "1.0.0"): {
                    "archiveSha512": archive_sha512,
                    "fileName": file_name,
                    "packageId": "Example.Package",
                    "sha256": source_sha256,
                    "sizeBytes": len(archive_bytes),
                    "version": "1.0.0",
                }
            }
            VERIFIER.verify_cache_directory(
                expected_rows, restore_rows, feed, cache, "linux-x64", "restore"
            )

            cache_archive.write_bytes(archive_bytes + b" substituted")
            with self.assertRaisesRegex(VERIFIER.LockError, "archive differs"):
                VERIFIER.verify_cache_directory(
                    expected_rows,
                    restore_rows,
                    feed,
                    cache,
                    "linux-x64",
                    "post_publish",
                )

            cache_archive.write_bytes(archive_bytes)
            metadata["source"] = "https://attacker.invalid/v3/index.json"
            write_json(package_root / ".nupkg.metadata", metadata)
            with self.assertRaisesRegex(VERIFIER.LockError, "metadata differs"):
                VERIFIER.verify_cache_directory(
                    expected_rows,
                    restore_rows,
                    feed,
                    cache,
                    "linux-x64",
                    "post_publish",
                )


class CacheInventoryContractTests(unittest.TestCase):
    @staticmethod
    def _row() -> dict[str, str]:
        return {
            "archiveSha512": digest64(b"archive"),
            "contentHash": digest64(b"content"),
            "packageId": "Example.Package",
            "sourceSha256": hashlib.sha256(b"archive").hexdigest(),
            "version": "1.2.3",
        }

    @staticmethod
    def _model(rid: str) -> dict[str, str]:
        if rid == "linux-x64":
            return {
                "executionModel": "native",
                "hostRid": "linux-x64",
                "sdkRid": "linux-x64",
                "targetRid": "linux-x64",
            }
        return {
            "executionModel": "cross_target",
            "hostRid": "linux-x64",
            "sdkRid": "linux-x64",
            "targetRid": "linux-arm64",
        }

    def _payload(self, rid: str, rows: list[dict[str, str]]) -> dict:
        model = self._model(rid)
        inventory_digest = VERIFIER.canonical_json_sha256(rows)
        return {
            "baseFeedInventorySha256": "b" * 64,
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
            "packageLockSha256": "a" * 64,
            "packages": rows,
            "restoreFeedInventorySha256": "c" * 64,
            "runtimeIdentifier": rid,
            "runtimePackageAuthoritySha256": "d" * 64,
            "sdkExecuted": True,
            "sdkRid": model["sdkRid"],
            "targetRid": model["targetRid"],
        }

    def _validate(self, payload: dict, rid: str, rows: list[dict[str, str]]) -> None:
        VERIFIER.validate_cache_inventory(
            payload,
            rid,
            "a" * 64,
            "b" * 64,
            "c" * 64,
            "d" * 64,
            rows,
            self._model(rid),
        )

    def test_native_and_cross_target_cache_models_are_explicit(self) -> None:
        for rid in VERIFIER.SUPPORTED_RIDS:
            with self.subTest(rid=rid):
                rows = [self._row()]
                self._validate(self._payload(rid, rows), rid, rows)

    def test_checked_package_planes_derive_41_native_and_42_cross_target_rows(self) -> None:
        base_path = REPO_ROOT / "release-locks/linux-package-feed.inventory.json"
        runtime_path = (
            REPO_ROOT / "release-locks/linux-runtime-packages.authority.json"
        )
        base = checked_json("release-locks/linux-package-feed.inventory.json")
        runtime = VERIFIER.validate_runtime_authority(
            checked_json("release-locks/linux-runtime-packages.authority.json")
        )
        expected_counts = {"linux-x64": 41, "linux-arm64": 42}
        for rid, expected_count in expected_counts.items():
            with self.subTest(rid=rid):
                package_rows = VERIFIER.validate_package_lock(
                    REPO_ROOT
                    / f"release-locks/avalonia-{rid}.packages.lock.json",
                    rid,
                )
                rid_payload = checked_json(
                    f"release-locks/{rid}-restore-feed.inventory.json"
                )
                rid_rows = VERIFIER.validate_rid_feed_inventory(
                    rid_payload,
                    rid,
                    base,
                    VERIFIER.sha256_file(base_path),
                    runtime,
                    VERIFIER.sha256_file(runtime_path),
                )
                rows = VERIFIER.cache_expected_rows(
                    package_rows,
                    rid_rows,
                    runtime,
                    rid,
                    include_app_host=rid == "linux-arm64",
                )
                self.assertEqual(expected_count, len(rows))
                host_rows = [
                    row
                    for row in rows
                    if row["packageId"].casefold().startswith(
                        "microsoft.netcore.app.host"
                    )
                ]
                self.assertEqual(1 if rid == "linux-arm64" else 0, len(host_rows))

    def test_cache_inventory_rejects_model_and_execution_claim_mutations(self) -> None:
        rid = "linux-arm64"
        rows = [self._row()]
        mutations = {
            "host RID": ("hostRid", "linux-arm64"),
            "SDK RID": ("sdkRid", "linux-arm64"),
            "target RID": ("targetRid", "linux-x64"),
            "execution model": ("executionModel", "native"),
            "SDK not executed": ("sdkExecuted", False),
            "native target claimed": ("nativeTargetExecuted", True),
        }
        for name, (key, value) in mutations.items():
            with self.subTest(name=name):
                payload = self._payload(rid, rows)
                payload[key] = value
                with self.assertRaises(VERIFIER.LockError):
                    self._validate(payload, rid, rows)

    def test_cache_inventory_rejects_phase_reorder_omission_and_digest_drift(self) -> None:
        rid = "linux-x64"
        rows = [self._row()]
        mutations = {
            "reordered": lambda value: value.reverse(),
            "missing": lambda value: value.pop(),
            "wrong phase": lambda value: value[1].__setitem__("phase", "publish"),
            "wrong digest": lambda value: value[1].__setitem__(
                "packageInventorySha256", "0" * 64
            ),
            "wrong count": lambda value: value[0].__setitem__("packageCount", 2),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                payload = self._payload(rid, rows)
                mutate(payload["observations"])
                with self.assertRaisesRegex(VERIFIER.LockError, "phase observations"):
                    self._validate(payload, rid, rows)

    def test_cache_inventory_rejects_count_and_source_digest_tampering(self) -> None:
        rid = "linux-x64"
        rows = [self._row()]

        wrong_count = self._payload(rid, rows)
        wrong_count["packageCount"] = 2
        with self.assertRaises(VERIFIER.LockError):
            self._validate(wrong_count, rid, rows)

        wrong_source = self._payload(rid, deepcopy(rows))
        wrong_source["packages"][0]["sourceSha256"] = "0" * 64
        with self.assertRaises(VERIFIER.LockError):
            self._validate(wrong_source, rid, rows)


class CacheMaterializerObservationTests(unittest.TestCase):
    def _args(
        self,
        root: Path,
        *,
        rid: str = "linux-x64",
        execution_model: str = "native",
        same_cache: bool = False,
    ) -> argparse.Namespace:
        paths = {}
        for name in (
            "package_lock",
            "base_feed_inventory",
            "rid_feed_inventory",
            "runtime_authority",
            "sdk_authority",
        ):
            paths[name] = root / f"{name}.json"
            write_json(paths[name], {})
        write_json(
            paths["base_feed_inventory"], {"packageInventorySha256": "b" * 64}
        )
        sdk_root = root / "sdk"
        feed = root / "feed"
        restore = root / "restore-cache"
        post_publish = restore if same_cache else root / "post-publish-cache"
        for directory in {sdk_root, feed, restore, post_publish}:
            directory.mkdir()
        return argparse.Namespace(
            rid=rid,
            execution_model=execution_model,
            sdk_root=sdk_root,
            feed=feed,
            restore_cache_root=restore,
            post_publish_cache_root=post_publish,
            output=root / "cache.inventory.json",
            **paths,
        )

    @staticmethod
    def _expected_row() -> dict[str, str]:
        return {
            "archiveSha512": digest64(b"archive"),
            "contentHash": digest64(b"content"),
            "packageId": "Example.Package",
            "sourceSha256": hashlib.sha256(b"archive").hexdigest(),
            "version": "1.0.0",
        }

    def _patch_materializer(self, expected_rows: list[dict[str, str]], verify: Mock):
        rid_payload = {"restoreFeedInventorySha256": "c" * 64}
        return (
            patch.object(VERIFIER, "validate_package_lock", return_value={}),
            patch.object(
                VERIFIER,
                "direct_feed_authorities",
                return_value=(rid_payload, {}, {}),
            ),
            patch.object(VERIFIER, "validate_feed_directory"),
            patch.object(VERIFIER.platform, "machine", return_value="x86_64"),
            patch.object(
                VERIFIER,
                "validate_sdk_authority",
                return_value={"linux-x64": {"toolchainFiles": []}},
            ),
            patch.object(VERIFIER, "validate_sdk_directory"),
            patch.object(VERIFIER, "cache_expected_rows", return_value=expected_rows),
            patch.object(VERIFIER, "verify_cache_directory", new=verify),
        )

    def _run_patched(self, args: argparse.Namespace, verify: Mock) -> None:
        rows = [self._expected_row()]
        patches = self._patch_materializer(rows, verify)
        entered = []
        try:
            for context in patches:
                entered.append(context)
                context.start()
            VERIFIER.materialize_cache_inventory(args)
        finally:
            for context in reversed(entered):
                context.stop()

    def test_materializer_authenticates_distinct_restore_and_post_publish_caches(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            args = self._args(Path(temp_dir))
            verify = Mock()
            self._run_patched(args, verify)
            payload = json.loads(args.output.read_text(encoding="utf-8"))

        self.assertEqual(2, verify.call_count)
        self.assertEqual(args.restore_cache_root, verify.call_args_list[0].args[3])
        self.assertEqual("restore", verify.call_args_list[0].args[5])
        self.assertEqual(args.post_publish_cache_root, verify.call_args_list[1].args[3])
        self.assertEqual("post_publish", verify.call_args_list[1].args[5])
        self.assertEqual(["restore", "post_publish"], [row["phase"] for row in payload["observations"]])
        self.assertTrue(payload["sdkExecuted"])
        self.assertFalse(payload["nativeTargetExecuted"])

    def test_materializer_rejects_same_cache_for_both_phase_observations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            args = self._args(Path(temp_dir), same_cache=True)
            verify = Mock()
            with self.assertRaisesRegex(VERIFIER.LockError, "must be distinct"):
                self._run_patched(args, verify)
            self.assertFalse(args.output.exists())
            verify.assert_not_called()

    def test_materializer_fails_if_post_publish_cache_substitution_is_observed(self) -> None:
        def verify_phase(*arguments):
            if arguments[5] == "post_publish":
                raise VERIFIER.LockError("post-publish cache substitution")

        with tempfile.TemporaryDirectory() as temp_dir:
            args = self._args(Path(temp_dir))
            verify = Mock(side_effect=verify_phase)
            with self.assertRaisesRegex(VERIFIER.LockError, "substitution"):
                self._run_patched(args, verify)
            self.assertEqual(2, verify.call_count)
            self.assertFalse(args.output.exists())

    def test_materializer_rejects_wrong_host_and_model_rid_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cases = (
                ("linux-arm64", "native"),
                ("linux-x64", "cross_target"),
            )
            for rid, model in cases:
                with self.subTest(rid=rid, model=model):
                    case_root = root / f"{rid}-{model}"
                    case_root.mkdir()
                    args = self._args(case_root, rid=rid, execution_model=model)
                    with self.assertRaises(VERIFIER.LockError):
                        self._run_patched(args, Mock())

        with tempfile.TemporaryDirectory() as temp_dir:
            args = self._args(Path(temp_dir))
            rows = [self._expected_row()]
            verify = Mock()
            patches = list(self._patch_materializer(rows, verify))
            patches[3] = patch.object(VERIFIER.platform, "machine", return_value="aarch64")
            entered = []
            try:
                for context in patches:
                    entered.append(context)
                    context.start()
                with self.assertRaisesRegex(VERIFIER.LockError, "linux-x64 host"):
                    VERIFIER.materialize_cache_inventory(args)
            finally:
                for context in reversed(entered):
                    context.stop()


class ReleasePostureAndConfigTests(unittest.TestCase):
    @staticmethod
    def _lock_shell() -> dict:
        return {
            "contract": VERIFIER.CONTRACT,
            "schemaVersion": VERIFIER.SCHEMA_VERSION,
            "releaseStatus": "review_required",
            "releaseEvidenceEligible": False,
            "repositories": [],
            "dotnet": {},
            "packagePlane": {},
            "nuget": {},
            "releaseManifest": {},
            "buildScript": {},
        }

    def test_release_posture_cannot_be_promoted_or_made_evidence_eligible(self) -> None:
        mutations = {
            "stable claim": ("releaseStatus", "stable_ready"),
            "preview claim": ("releaseStatus", "preview_ready"),
            "eligible": ("releaseEvidenceEligible", True),
            "integer lookalike": ("releaseEvidenceEligible", 0),
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for name, (key, value) in mutations.items():
                with self.subTest(name=name):
                    payload = self._lock_shell()
                    payload[key] = value
                    path = root / f"{name}.json"
                    write_json(path, payload)
                    with self.assertRaisesRegex(
                        VERIFIER.LockError, "review-required/ineligible"
                    ):
                        VERIFIER.validate_lock(path, root)

    def test_review_required_false_posture_passes_the_posture_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = root / "lock.json"
            write_json(path, self._lock_shell())
            with self.assertRaisesRegex(VERIFIER.LockError, "exactly five repositories"):
                VERIFIER.validate_lock(path, root)

    def test_generated_nuget_config_has_only_the_absolute_local_feed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            feed = root / "feed"
            feed.mkdir()
            packages = root / "packages"
            output = root / "NuGet.Config"
            VERIFIER.write_nuget_config(feed, packages, output)
            text = output.read_text(encoding="utf-8")
        self.assertIn("<clear />", text)
        self.assertIn("same-run-local-feed", text)
        self.assertIn(str(feed), text)
        self.assertNotIn("https://", text)
        self.assertNotIn("nuget.org", text.lower())


class CliSymlinkBoundaryTests(unittest.TestCase):
    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VERIFIER_PATH), *arguments],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
            check=False,
        )

    def test_inspect_rejects_symlinked_lock_and_repository_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            lock_link = root / "lock.json"
            lock_link.symlink_to(REPO_ROOT / "RELEASE.lock.json")
            result = self.run_cli(
                "inspect", "--lock", str(lock_link), "--repo-root", str(REPO_ROOT)
            )
            self.assertNotEqual(0, result.returncode, result.stdout)
            self.assertIn("symlinked path component", result.stdout)

            repo_link = root / "repo"
            repo_link.symlink_to(REPO_ROOT, target_is_directory=True)
            result = self.run_cli(
                "inspect",
                "--lock",
                str(REPO_ROOT / "RELEASE.lock.json"),
                "--repo-root",
                str(repo_link),
            )
            self.assertNotEqual(0, result.returncode, result.stdout)
            self.assertIn("symlinked path component", result.stdout)

    def test_install_and_verify_sdk_reject_symlink_candidates_before_use(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive = root / "archive.tar.gz"
            archive.write_bytes(b"not-an-sdk")
            archive_link = root / "archive-link.tar.gz"
            archive_link.symlink_to(archive)
            result = self.run_cli(
                "install-sdk",
                "--lock",
                str(REPO_ROOT / "RELEASE.lock.json"),
                "--repo-root",
                str(REPO_ROOT),
                "--rid",
                "linux-x64",
                "--archive",
                str(archive_link),
                "--output",
                str(root / "sdk-output"),
            )
            self.assertNotEqual(0, result.returncode, result.stdout)
            self.assertIn("symlinked path component", result.stdout)

            sdk = root / "sdk"
            sdk.mkdir()
            sdk_link = root / "sdk-link"
            sdk_link.symlink_to(sdk, target_is_directory=True)
            result = self.run_cli(
                "verify-sdk",
                "--lock",
                str(REPO_ROOT / "RELEASE.lock.json"),
                "--repo-root",
                str(REPO_ROOT),
                "--rid",
                "linux-x64",
                "--sdk-root",
                str(sdk_link),
            )
            self.assertNotEqual(0, result.returncode, result.stdout)
            self.assertIn("symlinked path component", result.stdout)

    def test_feed_cache_and_output_parent_symlinks_fail_at_cli_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            feed = root / "feed"
            feed.mkdir()
            feed_link = root / "feed-link"
            feed_link.symlink_to(feed, target_is_directory=True)
            cache = root / "cache"
            cache.mkdir()
            result = self.run_cli(
                "verify-nuget-cache",
                "--lock",
                str(REPO_ROOT / "RELEASE.lock.json"),
                "--repo-root",
                str(REPO_ROOT),
                "--rid",
                "linux-x64",
                "--feed",
                str(feed_link),
                "--packages-root",
                str(cache),
            )
            self.assertNotEqual(0, result.returncode, result.stdout)
            self.assertIn("symlinked path component", result.stdout)

            output_parent = root / "real-output"
            output_parent.mkdir()
            output_link = root / "output-link"
            output_link.symlink_to(output_parent, target_is_directory=True)
            result = self.run_cli(
                "write-nuget-config",
                "--feed",
                str(feed),
                "--packages-root",
                str(cache),
                "--output",
                str(output_link / "NuGet.Config"),
            )
            self.assertNotEqual(0, result.returncode, result.stdout)
            self.assertIn("symlinked path component", result.stdout)

    def test_cache_materializer_rejects_symlinked_authority_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            lock_link = root / "packages.lock.json"
            lock_link.symlink_to(
                REPO_ROOT / "release-locks/avalonia-linux-x64.packages.lock.json"
            )
            result = self.run_cli(
                "materialize-cache-inventory",
                "--rid",
                "linux-x64",
                "--package-lock",
                str(lock_link),
                "--base-feed-inventory",
                str(REPO_ROOT / "release-locks/linux-package-feed.inventory.json"),
                "--rid-feed-inventory",
                str(REPO_ROOT / "release-locks/linux-x64-restore-feed.inventory.json"),
                "--runtime-authority",
                str(REPO_ROOT / "release-locks/linux-runtime-packages.authority.json"),
                "--sdk-authority",
                str(REPO_ROOT / "release-locks/dotnet-sdk-10.0.103.authority.json"),
                "--sdk-root",
                str(root),
                "--feed",
                str(root),
                "--restore-cache-root",
                str(root),
                "--post-publish-cache-root",
                str(root),
                "--execution-model",
                "native",
                "--output",
                str(root / "out.json"),
            )
            self.assertNotEqual(0, result.returncode, result.stdout)
            self.assertIn("symlinked path component", result.stdout)


if __name__ == "__main__":
    unittest.main()
