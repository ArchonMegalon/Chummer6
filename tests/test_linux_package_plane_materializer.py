from __future__ import annotations

import hashlib
import importlib.util
import stat
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
