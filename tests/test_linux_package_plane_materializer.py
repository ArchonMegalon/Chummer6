from __future__ import annotations

import hashlib
import importlib.util
import stat
import sys
import tempfile
import unittest
import zipfile
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "materialize_linux_package_plane.py"
SPEC = importlib.util.spec_from_file_location("linux_package_plane", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


PACKAGE_ID = "Test.Package"
VERSION = "1.2.3"
NUSPEC = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd">
  <metadata><id>{PACKAGE_ID}</id><version>{VERSION}</version></metadata>
</package>
""".encode()
CORE_BYTES = b"<core-properties>preserve-these-exact-bytes</core-properties>"
ASSEMBLY_BYTES = b"exact-assembly-bytes"


def relationships(core_path: str, *, extra: str = "") -> bytes:
    return f"""<?xml version="1.0" encoding="utf-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Type="http://schemas.microsoft.com/packaging/2010/07/manifest" Target="/{PACKAGE_ID}.nuspec" Id="manifest-random" />
  <Relationship Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="/{core_path}" Id="core-random" {extra}/>
</Relationships>
""".encode()


def write_package(
    path: Path,
    *,
    core_name: str = "random.psmdcp",
    relationship_bytes: bytes | None = None,
    additional: list[tuple[zipfile.ZipInfo | str, bytes]] | None = None,
    timestamp: tuple[int, int, int, int, int, int] = (2026, 7, 19, 1, 2, 4),
) -> None:
    core_path = f"package/services/metadata/core-properties/{core_name}"
    entries: list[tuple[zipfile.ZipInfo | str, bytes]] = [
        (f"{PACKAGE_ID}.nuspec", NUSPEC),
        ("_rels/.rels", relationship_bytes or relationships(core_path)),
        (core_path, CORE_BYTES),
        (f"lib/net10.0/{PACKAGE_ID}.dll", ASSEMBLY_BYTES),
        ("[Content_Types].xml", b"content-types-preserved"),
    ]
    entries.extend(additional or [])
    with zipfile.ZipFile(path, "w") as archive:
        for name_or_info, payload in entries:
            if isinstance(name_or_info, zipfile.ZipInfo):
                info = name_or_info
            else:
                info = zipfile.ZipInfo(name_or_info, timestamp)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 0
            archive.writestr(info, payload)


class DeterministicPackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_independent_packs_normalize_to_identical_bytes(self) -> None:
        first = self.root / "first.nupkg"
        second = self.root / "second.nupkg"
        write_package(first, core_name="random-a.psmdcp")
        write_package(
            second,
            core_name="random-b.psmdcp",
            timestamp=(2025, 1, 2, 3, 4, 6),
        )

        first_receipt = MODULE.normalize_package(first, PACKAGE_ID, VERSION)
        second_receipt = MODULE.normalize_package(second, PACKAGE_ID, VERSION)

        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertEqual(
            first_receipt["normalizedSha256"], second_receipt["normalizedSha256"]
        )
        self.assertEqual(first_receipt["signatureStatus"], "absent")
        self.assertNotEqual(first_receipt["originalSha256"], second_receipt["originalSha256"])
        canonical_core = (
            "package/services/metadata/core-properties/"
            f"{hashlib.sha256(CORE_BYTES).hexdigest()[:32]}.psmdcp"
        )
        with zipfile.ZipFile(first) as archive:
            self.assertEqual(archive.read(canonical_core), CORE_BYTES)
            self.assertEqual(
                archive.read(f"lib/net10.0/{PACKAGE_ID}.dll"), ASSEMBLY_BYTES
            )
            self.assertEqual(
                archive.read("[Content_Types].xml"), b"content-types-preserved"
            )
        self.assertEqual(
            first_receipt["changedMetadata"]["coreProperties"],
            {
                "canonicalPath": canonical_core,
                "originalPath": (
                    "package/services/metadata/core-properties/random-a.psmdcp"
                ),
                "preserved": True,
                "sha256": hashlib.sha256(CORE_BYTES).hexdigest(),
                "sizeBytes": len(CORE_BYTES),
            },
        )
        self.assertNotEqual(
            first_receipt["changedMetadata"]["relationships"]["originalSha256"],
            first_receipt["changedMetadata"]["relationships"]["normalizedSha256"],
        )

    def test_normalization_is_idempotent(self) -> None:
        package = self.root / "package.nupkg"
        write_package(package)
        first = MODULE.normalize_package(package, PACKAGE_ID, VERSION)
        first_bytes = package.read_bytes()
        second = MODULE.normalize_package(package, PACKAGE_ID, VERSION)
        self.assertEqual(package.read_bytes(), first_bytes)
        self.assertEqual(first["normalizedSha256"], second["normalizedSha256"])

    def assert_rejected(
        self,
        *,
        additional: list[tuple[zipfile.ZipInfo | str, bytes]] | None = None,
        relationship_bytes: bytes | None = None,
    ) -> None:
        package = self.root / "rejected.nupkg"
        write_package(
            package,
            additional=additional,
            relationship_bytes=relationship_bytes,
        )
        with self.assertRaises(MODULE.MaterializationError):
            MODULE.normalize_package(package, PACKAGE_ID, VERSION)

    def test_rejects_signature(self) -> None:
        self.assert_rejected(additional=[("package/.SIGNATURE.P7S", b"signed")])

    def test_rejects_traversal(self) -> None:
        self.assert_rejected(additional=[("../escape", b"unsafe")])

    def test_rejects_casefold_duplicate(self) -> None:
        self.assert_rejected(additional=[("[content_types].XML", b"duplicate")])

    def test_rejects_unicode_normalized_duplicate(self) -> None:
        self.assert_rejected(
            additional=[("café.txt", b"one"), ("café.txt", b"two")]
        )

    def test_rejects_symlink(self) -> None:
        symlink = zipfile.ZipInfo("unsafe-link")
        symlink.create_system = 3
        symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
        self.assert_rejected(additional=[(symlink, b"target")])

    def test_rejects_unix_special_file(self) -> None:
        fifo = zipfile.ZipInfo("unsafe-fifo")
        fifo.create_system = 3
        fifo.external_attr = (stat.S_IFIFO | 0o600) << 16
        self.assert_rejected(additional=[(fifo, b"")])

    def test_rejects_symlinked_package_input(self) -> None:
        package = self.root / "package.nupkg"
        write_package(package)
        link = self.root / "linked.nupkg"
        link.symlink_to(package)
        with self.assertRaises(MODULE.MaterializationError):
            MODULE.normalize_package(link, PACKAGE_ID, VERSION)

    def test_source_authority_rejects_direct_and_parent_symlinks(self) -> None:
        authority = self.root / "authority.json"
        authority.write_text("{}\n", encoding="utf-8")
        direct = self.root / "direct.json"
        direct.symlink_to(authority)
        with self.assertRaisesRegex(MODULE.MaterializationError, "symlinked"):
            MODULE.source_file(self.root, "direct.json", "authority")

        real = self.root / "real"
        real.mkdir()
        (real / "nested.json").write_text("{}\n", encoding="utf-8")
        alias = self.root / "alias"
        alias.symlink_to(real, target_is_directory=True)
        with self.assertRaisesRegex(MODULE.MaterializationError, "symlinked"):
            MODULE.source_file(self.root, "alias/nested.json", "authority")

    def test_rejects_extra_relationship(self) -> None:
        core_path = "package/services/metadata/core-properties/random.psmdcp"
        rows = relationships(core_path).replace(
            b"</Relationships>",
            b'<Relationship Type="unexpected" Target="/x" Id="extra" /></Relationships>',
        )
        self.assert_rejected(relationship_bytes=rows)

    def test_rejects_external_relationship(self) -> None:
        core_path = "package/services/metadata/core-properties/random.psmdcp"
        self.assert_rejected(
            relationship_bytes=relationships(core_path, extra='TargetMode="External"')
        )

    def test_rejects_ambiguous_relationship_xml(self) -> None:
        core_path = "package/services/metadata/core-properties/random.psmdcp"
        rows = relationships(core_path).replace(
            b"<Relationships", b"<!-- hidden -->\n<Relationships"
        )
        self.assert_rejected(relationship_bytes=rows)

    def test_hub_producer_restore_is_sealed_to_one_local_authenticated_feed(self) -> None:
        local_feed = self.root / "canonical-feed"
        local_feed.mkdir()
        dotnet = self.root / "sdk" / "dotnet"
        observed_commands: list[tuple[str, ...]] = []

        def original_properties(*_args: object, **_kwargs: object) -> tuple[str, ...]:
            return ("-p:RepositoryUrl=https://github.com/ArchonMegalon/source.git",)

        def original_run(
            command: object, *, cwd: Path | None = None, env: object = None
        ) -> str:
            del cwd, env
            observed_commands.append(tuple(str(value) for value in command))
            return "ok"

        producer = SimpleNamespace(
            _run=original_run,
            package_build_properties=original_properties,
        )
        local_source = MODULE.configure_hub_producer_for_local_restore(
            producer,
            dotnet=dotnet,
            local_feed=local_feed,
        )
        properties = producer.package_build_properties()
        expected_properties = {
            f"-p:RestoreSources={local_feed.resolve()}",
            "-p:RestoreAdditionalProjectSources=",
            "-p:RestoreFallbackFolders=",
            "-p:RestoreIgnoreFailedSources=false",
            "-p:RestoreNoCache=true",
            "-p:NuGetAudit=false",
            "-p:ChummerDesktopRuntimeIdentifiers=",
            "-p:RuntimeIdentifiers=",
            "-p:RuntimeIdentifier=",
        }
        self.assertEqual(str(local_feed.resolve()), local_source)
        self.assertTrue(expected_properties.issubset(properties))

        config = self.root / "NuGet.Config"
        config.write_text(
            "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n"
            "<configuration><packageSources><clear />"
            f"<add key=\"nuget.org\" value=\"{local_source}\" protocolVersion=\"3\" />"
            "</packageSources></configuration>\n",
            encoding="utf-8",
        )
        restore = (
            str(dotnet),
            "restore",
            "owner.csproj",
            "--configfile",
            str(config),
            *properties,
        )
        self.assertEqual("ok", producer._run(restore))
        config_text = config.read_text(encoding="utf-8")
        self.assertIn('key="authenticated-local-feed"', config_text)
        self.assertIn(f'value="{local_source}"', config_text)
        self.assertNotIn("http://", config_text.lower())
        self.assertNotIn("https://", config_text.lower())
        self.assertNotIn("nuget.org", config_text.lower())
        self.assertEqual(restore, observed_commands[-1])
        self.assertEqual("ok", producer._run(restore))
        self.assertEqual(config_text, config.read_text(encoding="utf-8"))

        remote = self.root / "Remote.NuGet.Config"
        remote.write_text(
            "<configuration><packageSources><clear />"
            "<add key=\"remote\" value=\"https://api.nuget.org/v3/index.json\" "
            "protocolVersion=\"3\" /></packageSources></configuration>\n",
            encoding="utf-8",
        )
        rejected = tuple(
            str(remote) if value == str(config) else value for value in restore
        )
        with self.assertRaisesRegex(
            MODULE.MaterializationError,
            "one cleared local package source",
        ):
            producer._run(rejected)

        namespaced = self.root / "Namespaced.NuGet.Config"
        namespaced.write_text(
            "<configuration xmlns=\"urn:unexpected\"><packageSources><clear />"
            f"<add key=\"local\" value=\"{local_source}\" protocolVersion=\"3\" />"
            "</packageSources></configuration>\n",
            encoding="utf-8",
        )
        rejected_namespace = tuple(
            str(namespaced) if value == str(config) else value for value in restore
        )
        with self.assertRaisesRegex(
            MODULE.MaterializationError,
            "configuration is ambiguous",
        ):
            producer._run(rejected_namespace)

        remote_property = tuple(
            "-p:RestoreSources=https://api.nuget.org/v3/index.json"
            if value == f"-p:RestoreSources={local_source}"
            else value
            for value in restore
        )
        with self.assertRaisesRegex(
            MODULE.MaterializationError,
            "exact local restore boundary",
        ):
            producer._run(remote_property)
        for alternate in (
            ("--source", "https://api.nuget.org/v3/index.json"),
            ("-s", "https://api.nuget.org/v3/index.json"),
            ("-p:RestoreConfigFile=/tmp/remote.config",),
            ("-p:RuntimeIdentifiers=linux-x64",),
            ("-p:runtimeidentifier=linux-x64",),
            ("--runtime", "linux-x64"),
            ("-r", "linux-x64"),
        ):
            with self.subTest(alternate=alternate), self.assertRaisesRegex(
                MODULE.MaterializationError,
                "alternate|exact local restore boundary",
            ):
                producer._run((*restore, *alternate))

        for conflicting_property in (
            "-p:RestoreSources=https://api.nuget.org/v3/index.json",
            "-p:ChummerDesktopRuntimeIdentifiers=linux-x64;win-x64",
            "/p:RuntimeIdentifiers=linux-x64",
            "--property:runtimeidentifier=linux-x64",
        ):
            with self.subTest(conflicting_property=conflicting_property):
                conflicting = SimpleNamespace(
                    _run=original_run,
                    package_build_properties=(
                        lambda *_args, _value=conflicting_property, **_kwargs: (_value,)
                    ),
                )
                MODULE.configure_hub_producer_for_local_restore(
                    conflicting,
                    dotnet=dotnet,
                    local_feed=local_feed,
                )
                with self.assertRaisesRegex(
                    MODULE.MaterializationError,
                    "controlled restore property",
                ):
                    conflicting.package_build_properties()

        with self.assertRaisesRegex(MODULE.MaterializationError, "unexpectedly permits restore"):
            producer._run((str(dotnet), "pack", "owner.csproj", *properties))
        self.assertEqual(
            "ok",
            producer._run(
                (str(dotnet), "pack", "owner.csproj", "--no-restore", *properties)
            ),
        )

    def test_x64_hub_producer_requires_exact_pinned_inventory(self) -> None:
        hub_root = self.root / "hub"
        producer_path = hub_root / "scripts" / "producer.py"
        lock_path = hub_root / "eng" / "lock.json"
        producer_path.parent.mkdir(parents=True)
        lock_path.parent.mkdir(parents=True)
        producer_path.write_text("# exact pinned producer\n", encoding="utf-8")
        lock_path.write_text("{}\n", encoding="utf-8")

        sdk_root = self.root / "sdk"
        tool_paths = {
            "dotnet_host": sdk_root / "dotnet",
            "csc": sdk_root / "sdk/10.0.103/Roslyn/bincore/csc.dll",
            "msbuild": sdk_root / "sdk/10.0.103/Microsoft.Build.dll",
            "nuget_packaging": sdk_root / "sdk/10.0.103/NuGet.Packaging.dll",
        }
        for name, path in tool_paths.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"exact-{name}".encode())
        toolchain = {
            name: hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in tool_paths.items()
        }

        @dataclass(frozen=True)
        class FakeLock:
            approved_remote_source: str
            toolchain_sha256: dict[str, str]

        effective: dict[str, object] = {}

        def build_feed(
            lock: FakeLock, *, lock_sha256: str, feed: Path, dotnet: str
        ) -> str:
            effective.update(
                {
                    "lock": lock,
                    "lock_sha256": lock_sha256,
                    "dotnet": dotnet,
                }
            )
            feed.mkdir()
            return "b" * 64

        producer = SimpleNamespace(
            _run=lambda command, *, cwd=None, env=None: "",
            build_feed=build_feed,
            load_lock=lambda _path: FakeLock(
                approved_remote_source="https://api.nuget.org/v3/index.json",
                toolchain_sha256=toolchain,
            ),
            package_build_properties=lambda *_args, **_kwargs: (),
            validate_build_recipe=lambda _root, _lock: None,
        )
        authority = {
            "inventoryContract": "inventory/v1",
            "inventorySha256": "a" * 64,
            "lockContract": "lock/v1",
            "lockPath": "eng/lock.json",
            "lockSha256": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
            "ownerDirectory": "hub-owner",
            "packages": [],
            "producerPath": "scripts/producer.py",
            "producerSha256": hashlib.sha256(producer_path.read_bytes()).hexdigest(),
        }
        lock = {
            "canonicalOwnerFeed": authority,
            "owners": [{"commit": "1" * 40, "directory": "hub-owner"}],
        }
        canonical_feed = self.root / "canonical-feed"
        canonical_feed.mkdir()
        with mock.patch.object(MODULE, "load_module", return_value=producer):
            with self.assertRaisesRegex(
                MODULE.MaterializationError,
                "inventory differs from authority",
            ):
                MODULE.compose_hub_packages(
                    SimpleNamespace(),
                    lock,
                    {"hub-owner": hub_root},
                    sdk_root,
                    self.root / "hub-staging",
                    canonical_feed,
                    {},
                    "linux-x64",
                )
        effective_lock = effective["lock"]
        self.assertEqual(str(canonical_feed.resolve()), effective_lock.approved_remote_source)
        self.assertEqual(authority["lockSha256"], effective["lock_sha256"])
        self.assertEqual(str(sdk_root / "dotnet"), effective["dotnet"])


if __name__ == "__main__":
    unittest.main()
