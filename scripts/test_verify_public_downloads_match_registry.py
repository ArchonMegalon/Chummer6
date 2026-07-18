#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import contextmanager, redirect_stderr
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "tests"))
from release_authority_fixture import write_authority_fixture


SCRIPT_PATH = Path(__file__).resolve().parent / "verify_public_downloads_match_registry.py"
SPEC = importlib.util.spec_from_file_location("verify_public_downloads_match_registry_module", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class VerifyPublicDownloadsMatchRegistryTests(unittest.TestCase):
    def _write_fixture(self, root: Path):
        authority = write_authority_fixture(root / "authority")
        resolved = MODULE.resolve_release_authority(
            authority.current_path,
            registry_commit=authority.registry_commit,
            expected_release_decision_status="preview_ready",
        )
        docs_root = root / "Chummer6"
        receipts_root = docs_root / ".guide-internal" / "receipts"
        receipts_root.mkdir(parents=True)
        artifacts = MODULE.authority_artifacts(resolved.authority)
        available = ["Linux", "Windows"]
        missing = ["macOS"]
        packet = {
            "architecture_scope_line": MODULE._architecture_scope_line(artifacts),
            "authority": resolved.authority,
            "authority_source": resolved.authority_source,
            "available_platforms": available,
            "generated_from": resolved.served_mirror,
            "missing_installer_lane_line": MODULE._missing_installer_lane_line(missing),
            "missing_platforms": missing,
            "required_platforms": available,
            "served_mirror": resolved.served_mirror,
            "shelf_truth_line": "Linux and Windows downloads are posted.",
        }
        (receipts_root / "CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json").write_text(
            json.dumps(packet, indent=2) + "\n",
            encoding="utf-8",
        )
        (docs_root / "DOWNLOAD.md").write_text(
            """# Download

## Current public download

- Linux and Windows downloads are posted.

## Current build matrix

### Windows

- Avalonia Desktop Windows X64 Installer.
- Download: [Open download](https://chummer.run/downloads/install/avalonia-win-x64-installer)
- File: `chummer-avalonia-win-x64-installer.exe`
- Size: 2.6 MiB (2734106 bytes)
- Access: Public download.

### Linux

- Avalonia Desktop Linux X64 Installer.
- Download: [Open download](https://chummer.run/downloads/install/avalonia-linux-x64-installer)
- File: `chummer-avalonia-linux-x64-installer.deb`
- Size: 35.3 MiB (37024862 bytes)
- Access: Public download.

### macOS

- There is no public macOS download today.

## SHA256

- Avalonia Desktop Linux X64 Installer: `5c8518f0f7f24b3f7101ff6fcea0fe33f012b4dfb03704f5bdf0067571f2d70b`
- Avalonia Desktop Windows X64 Installer: `80655fd79a096cd7714910d7b38f7741eea01f82ada96dc6a2a097951997d91a`
""",
            encoding="utf-8",
        )
        (docs_root / "STATUS.md").write_text(
            "\n".join(
                [
                    "# Status",
                    packet["shelf_truth_line"],
                    packet["architecture_scope_line"],
                    packet["missing_installer_lane_line"],
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return docs_root, authority

    @contextmanager
    def _module_paths(self, docs_root: Path):
        originals = (MODULE.REPO_ROOT, MODULE.DOWNLOAD_PATH, MODULE.STATUS_PATH, MODULE.PACKET_PATH)
        MODULE.REPO_ROOT = docs_root
        MODULE.DOWNLOAD_PATH = docs_root / "DOWNLOAD.md"
        MODULE.STATUS_PATH = docs_root / "STATUS.md"
        MODULE.PACKET_PATH = (
            docs_root / ".guide-internal" / "receipts" / "CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json"
        )
        try:
            yield
        finally:
            MODULE.REPO_ROOT, MODULE.DOWNLOAD_PATH, MODULE.STATUS_PATH, MODULE.PACKET_PATH = originals

    @staticmethod
    def _args(authority) -> list[str]:
        return [
            "--authority-current",
            str(authority.current_path),
            "--registry-commit",
            authority.registry_commit,
            "--expected-release-decision-status",
            "preview_ready",
        ]

    def test_main_accepts_exact_snapshot_aligned_docs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            docs_root, authority = self._write_fixture(Path(temp_dir))
            with self._module_paths(docs_root):
                self.assertEqual(MODULE.main(self._args(authority)), 0)

    def test_main_fails_when_download_sha_drifts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            docs_root, authority = self._write_fixture(Path(temp_dir))
            download = docs_root / "DOWNLOAD.md"
            download.write_text(
                download.read_text(encoding="utf-8").replace(
                    "5c8518f0f7f24b3f7101ff6fcea0fe33f012b4dfb03704f5bdf0067571f2d70b",
                    "a" * 64,
                ),
                encoding="utf-8",
            )
            with self._module_paths(docs_root), self.assertRaisesRegex(ValueError, "SHA256"):
                MODULE.main(self._args(authority))

    def test_main_rejects_generation_download_url_in_public_docs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            docs_root, authority = self._write_fixture(Path(temp_dir))
            download = docs_root / "DOWNLOAD.md"
            download.write_text(
                download.read_text(encoding="utf-8").replace(
                    "https://chummer.run/downloads/install/avalonia-linux-x64-installer",
                    "https://chummer.run/downloads/g/generation-1/files/chummer-avalonia-linux-x64-installer.deb",
                ),
                encoding="utf-8",
            )
            with self._module_paths(docs_root), self.assertRaisesRegex(ValueError, "publicInstallRoute"):
                MODULE.main(self._args(authority))

    def test_main_rejects_extra_documented_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            docs_root, authority = self._write_fixture(Path(temp_dir))
            download = docs_root / "DOWNLOAD.md"
            download.write_text(
                download.read_text(encoding="utf-8").replace(
                    "### macOS",
                    "- Unapproved Recovery Archive.\n"
                    "- Download: [Open download](https://chummer.run/downloads/install/recovery)\n"
                    "- File: `recovery.zip`\n"
                    "- Size: 10 bytes\n"
                    "- Access: Public download.\n\n"
                    "### macOS",
                ),
                encoding="utf-8",
            )
            with self._module_paths(docs_root), self.assertRaisesRegex(ValueError, "row count"):
                MODULE.main(self._args(authority))

    def test_main_rejects_packet_authority_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            docs_root, authority = self._write_fixture(Path(temp_dir))
            packet_path = (
                docs_root / ".guide-internal" / "receipts" / "CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json"
            )
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            packet["authority"]["artifactCount"] = 0
            packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
            with self._module_paths(docs_root), self.assertRaisesRegex(ValueError, "authority drifted"):
                MODULE.main(self._args(authority))

    def test_main_requires_strict_authority_without_release_marker(self) -> None:
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            MODULE.main([])
        self.assertEqual(raised.exception.code, 2)

    def test_legacy_manifest_flag_cannot_bypass_snapshot_authority(self) -> None:
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            MODULE.main(["--authority-manifest", "/tmp/manifest.json"])
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
