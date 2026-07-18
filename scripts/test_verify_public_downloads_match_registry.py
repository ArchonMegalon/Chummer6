#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_PATH = Path(__file__).resolve().parent / "verify_public_downloads_match_registry.py"
SPEC = importlib.util.spec_from_file_location("verify_public_downloads_match_registry_module", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class VerifyPublicDownloadsMatchRegistryTests(unittest.TestCase):
    def _write_fixture(self, root: Path) -> Path:
        registry_root = root.parent / "chummer-hub-registry" / ".codex-studio" / "published"
        registry_root.mkdir(parents=True, exist_ok=True)
        registry_path = registry_root / "RELEASE_CHANNEL.generated.json"
        registry_path.write_text(
            json.dumps(
                {
                    "status": "published",
                    "channelId": "public_stable",
                    "channel": "public_stable",
                    "rolloutState": "public_stable",
                    "supportabilityState": "gold_supported",
                    "version": "run-20260704-170602",
                    "releaseVersion": "run-20260704-170602",
                    "publishedAt": "2026-07-04T17:48:20Z",
                    "artifacts": [
                        {
                            "artifactId": "avalonia-linux-x64-installer",
                            "platform": "linux",
                            "rid": "linux-x64",
                            "arch": "x64",
                            "kind": "installer",
                            "fileName": "chummer-avalonia-linux-x64-installer.deb",
                            "downloadUrl": "https://chummer.run/downloads/files/chummer-avalonia-linux-x64-installer.deb",
                            "sha256": "5c8518f0f7f24b3f7101ff6fcea0fe33f012b4dfb03704f5bdf0067571f2d70b",
                            "sizeBytes": 37024862,
                            "platformLabel": "Avalonia Desktop Linux X64 Installer",
                            "compatibilityState": "compatible",
                            "installAccessClass": "account_recommended",
                        },
                        {
                            "artifactId": "avalonia-win-x64-installer",
                            "platform": "windows",
                            "rid": "win-x64",
                            "arch": "x64",
                            "kind": "installer",
                            "fileName": "chummer-avalonia-win-x64-installer.exe",
                            "downloadUrl": "https://chummer.run/downloads/files/chummer-avalonia-win-x64-installer.exe",
                            "sha256": "80655fd79a096cd7714910d7b38f7741eea01f82ada96dc6a2a097951997d91a",
                            "sizeBytes": 2734106,
                            "platformLabel": "Avalonia Desktop Windows X64 Installer",
                            "compatibilityState": "compatible",
                            "installAccessClass": "open_public",
                        },
                    ],
                    "desktopTupleCoverage": {
                        "requiredDesktopPlatforms": ["linux", "windows"],
                        "requiredDesktopHeads": ["avalonia"],
                        "promotedInstallerTuples": [
                            {
                                "artifactId": "avalonia-linux-x64-installer",
                                "platform": "linux",
                                "rid": "linux-x64",
                                "arch": "x64",
                            },
                            {
                                "artifactId": "avalonia-win-x64-installer",
                                "platform": "windows",
                                "rid": "win-x64",
                                "arch": "x64",
                            },
                        ],
                        "missingRequiredPlatforms": [],
                        "missingRequiredHeads": [],
                        "missingRequiredPlatformHeadPairs": [],
                        "missingRequiredPlatformHeadRidTuples": [],
                        "externalProofRequests": [],
                        "complete": True
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        packet = {
            "authority": MODULE.resolve_release_authority(registry_path).authority,
            "generated_from": MODULE.CANONICAL_RELEASE_CHANNEL_SOURCE,
            "available_platforms": ["Windows", "Linux"],
            "required_platforms": ["Windows", "Linux"],
            "missing_platforms": [],
            "shelf_truth_line": "Windows and Linux downloads are posted.",
            "architecture_scope_line": "Desktop downloads are available for Linux x64 and Windows x64 only. No public download is posted for Linux ARM64, Windows ARM64, and macOS yet.",
            "missing_installer_lane_line": "Normal installers are available on the desktop platforms that are currently offered.",
        }
        receipts_root = root / ".guide-internal" / "receipts"
        receipts_root.mkdir(parents=True, exist_ok=True)
        (receipts_root / "CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json").write_text(
            json.dumps(packet, indent=2) + "\n",
            encoding="utf-8",
        )

        (root / "DOWNLOAD.md").write_text(
            "\n".join(
                [
                    "# Download",
                    "",
                    "## Current public download",
                    "",
                    "- Windows and Linux downloads are posted.",
                    "",
                    "## Current build matrix",
                    "",
                    "### Windows",
                    "",
                    "- Avalonia Desktop Windows X64 Installer.",
                    "- Download: [Open download](https://chummer.run/downloads/files/chummer-avalonia-win-x64-installer.exe)",
                    "- File: `chummer-avalonia-win-x64-installer.exe`",
                    "- Size: 2.6 MiB (2734106 bytes)",
                    "- Access: Public download.",
                    "",
                    "### Linux",
                    "",
                    "- Avalonia Desktop Linux X64 Installer.",
                    "- Download: [Open download](https://chummer.run/downloads/files/chummer-avalonia-linux-x64-installer.deb)",
                    "- File: `chummer-avalonia-linux-x64-installer.deb`",
                    "- Size: 35.3 MiB (37024862 bytes)",
                    "- Access: Public download.",
                    "",
                    "### macOS",
                    "",
                    "- There is no public macOS download today.",
                    "",
                    "## SHA256",
                    "",
                    "- Avalonia Desktop Linux X64 Installer: `5c8518f0f7f24b3f7101ff6fcea0fe33f012b4dfb03704f5bdf0067571f2d70b`",
                    "- Avalonia Desktop Windows X64 Installer: `80655fd79a096cd7714910d7b38f7741eea01f82ada96dc6a2a097951997d91a`",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (root / "STATUS.md").write_text(
            "\n".join(
                [
                    "# Status",
                    "",
                    "- Windows and Linux downloads are posted.",
                    "- Desktop downloads are available for Linux x64 and Windows x64 only. No public download is posted for Linux ARM64, Windows ARM64, and macOS yet.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return registry_path

    def test_main_accepts_registry_aligned_docs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "Chummer6"
            root.mkdir(parents=True, exist_ok=True)
            registry_path = self._write_fixture(root)

            original_root = MODULE.REPO_ROOT
            original_download = MODULE.DOWNLOAD_PATH
            original_status = MODULE.STATUS_PATH
            original_packet = MODULE.PACKET_PATH
            try:
                MODULE.REPO_ROOT = root
                MODULE.DOWNLOAD_PATH = root / "DOWNLOAD.md"
                MODULE.STATUS_PATH = root / "STATUS.md"
                MODULE.PACKET_PATH = root / ".guide-internal" / "receipts" / "CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json"
                with mock.patch.dict(os.environ, {MODULE.REGISTRY_ENV: str(registry_path)}, clear=False):
                    self.assertEqual(MODULE.main([]), 0)
            finally:
                MODULE.REPO_ROOT = original_root
                MODULE.DOWNLOAD_PATH = original_download
                MODULE.STATUS_PATH = original_status
                MODULE.PACKET_PATH = original_packet

    def test_main_fails_when_download_sha_drifts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "Chummer6"
            root.mkdir(parents=True, exist_ok=True)
            registry_path = self._write_fixture(root)
            download_path = root / "DOWNLOAD.md"
            download_path.write_text(
                download_path.read_text(encoding="utf-8").replace(
                    "5c8518f0f7f24b3f7101ff6fcea0fe33f012b4dfb03704f5bdf0067571f2d70b",
                    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                ),
                encoding="utf-8",
            )

            original_root = MODULE.REPO_ROOT
            original_download = MODULE.DOWNLOAD_PATH
            original_status = MODULE.STATUS_PATH
            original_packet = MODULE.PACKET_PATH
            try:
                MODULE.REPO_ROOT = root
                MODULE.DOWNLOAD_PATH = root / "DOWNLOAD.md"
                MODULE.STATUS_PATH = root / "STATUS.md"
                MODULE.PACKET_PATH = root / ".guide-internal" / "receipts" / "CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json"
                with mock.patch.dict(os.environ, {MODULE.REGISTRY_ENV: str(registry_path)}, clear=False):
                    with self.assertRaises(ValueError):
                        MODULE.main([])
            finally:
                MODULE.REPO_ROOT = original_root
                MODULE.DOWNLOAD_PATH = original_download
                MODULE.STATUS_PATH = original_status
                MODULE.PACKET_PATH = original_packet

    def test_main_accepts_account_installers_and_public_archive_fallbacks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "Chummer6"
            root.mkdir(parents=True, exist_ok=True)
            registry_path = self._write_fixture(root)
            release = json.loads(registry_path.read_text(encoding="utf-8"))
            release["artifacts"] = [
                {
                    "artifactId": "avalonia-osx-arm64-installer",
                    "platform": "macos",
                    "rid": "osx-arm64",
                    "arch": "arm64",
                    "kind": "installer",
                    "fileName": "chummer-avalonia-osx-arm64-installer.dmg",
                    "downloadUrl": "/downloads/files/chummer-avalonia-osx-arm64-installer.dmg",
                    "sha256": "a" * 64,
                    "sizeBytes": 101,
                    "platformLabel": "Avalonia Desktop macOS ARM64 Installer",
                    "compatibilityState": "compatible",
                    "installAccessClass": "account_required",
                },
                {
                    "artifactId": "avalonia-osx-arm64-archive",
                    "platform": "macos",
                    "rid": "osx-arm64",
                    "arch": "arm64",
                    "kind": "archive",
                    "fileName": "chummer-avalonia-osx-arm64.tar.gz",
                    "downloadUrl": "/downloads/files/chummer-avalonia-osx-arm64.tar.gz",
                    "sha256": "b" * 64,
                    "sizeBytes": 202,
                    "platformLabel": "Avalonia Desktop macOS ARM64",
                    "compatibilityState": "compatible",
                    "installAccessClass": "open_public",
                },
            ]
            release["desktopTupleCoverage"] = {
                "requiredDesktopPlatforms": ["macos"],
                "requiredDesktopHeads": ["avalonia"],
                "promotedInstallerTuples": [
                    {
                        "artifactId": "avalonia-osx-arm64-installer",
                        "platform": "macos",
                        "rid": "osx-arm64",
                        "arch": "arm64",
                    }
                ],
                "missingRequiredPlatforms": [],
                "missingRequiredHeads": [],
                "missingRequiredPlatformHeadPairs": [],
                "missingRequiredPlatformHeadRidTuples": [],
                "externalProofRequests": [],
                "complete": True,
            }
            registry_path.write_text(json.dumps(release, indent=2) + "\n", encoding="utf-8")

            packet_path = root / ".guide-internal" / "receipts" / "CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json"
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            packet.update(
                {
                    "authority": MODULE.resolve_release_authority(registry_path).authority,
                    "available_platforms": ["macOS"],
                    "required_platforms": ["macOS"],
                    "missing_platforms": [],
                    "shelf_truth_line": "macOS downloads are posted.",
                    "architecture_scope_line": "Desktop downloads are available for macOS ARM64 only. No public download is posted for Linux x64, Windows x64, Linux ARM64, and Windows ARM64 yet.",
                    "missing_installer_lane_line": "Normal installers are available on the desktop platforms that are currently offered.",
                }
            )
            packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
            (root / "DOWNLOAD.md").write_text(
                """# Download

## Current public download

- macOS downloads are posted.

## Current build matrix

### Windows

- There is no public Windows download today.

### Linux

- There is no public Linux download today.

### macOS

- Avalonia Desktop macOS ARM64 Installer.
- Download: [Open download](/downloads/files/chummer-avalonia-osx-arm64-installer.dmg)
- File: `chummer-avalonia-osx-arm64-installer.dmg`
- Size: 101 bytes
- Access: Sign-in required.
- Avalonia Desktop macOS ARM64 archive package.
- status: Fallback or recovery package, not an equal flagship default.
- Download: [Open download](/downloads/files/chummer-avalonia-osx-arm64.tar.gz)
- File: `chummer-avalonia-osx-arm64.tar.gz`
- Size: 202 bytes
- Access: Public download.

## SHA256

- Avalonia Desktop macOS ARM64 Installer: `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`
- Avalonia Desktop macOS ARM64: `bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb`
""",
                encoding="utf-8",
            )
            (root / "STATUS.md").write_text(
                """# Status

- macOS downloads are posted.
- Desktop downloads are available for macOS ARM64 only. No public download is posted for Linux x64, Windows x64, Linux ARM64, and Windows ARM64 yet.
""",
                encoding="utf-8",
            )

            original_root = MODULE.REPO_ROOT
            original_download = MODULE.DOWNLOAD_PATH
            original_status = MODULE.STATUS_PATH
            original_packet = MODULE.PACKET_PATH
            try:
                MODULE.REPO_ROOT = root
                MODULE.DOWNLOAD_PATH = root / "DOWNLOAD.md"
                MODULE.STATUS_PATH = root / "STATUS.md"
                MODULE.PACKET_PATH = packet_path
                with mock.patch.dict(os.environ, {MODULE.REGISTRY_ENV: str(registry_path)}, clear=False):
                    self.assertEqual(MODULE.main([]), 0)
            finally:
                MODULE.REPO_ROOT = original_root
                MODULE.DOWNLOAD_PATH = original_download
                MODULE.STATUS_PATH = original_status
                MODULE.PACKET_PATH = original_packet

    def test_registry_resolution_never_uses_mutable_sibling_fallback(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(FileNotFoundError, "explicit authority manifest"):
                MODULE._resolve_registry_manifest()

    def test_release_mode_requires_explicit_immutable_authority_flags(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            MODULE.main(["--release"])
        self.assertEqual(raised.exception.code, 2)

    def test_main_rejects_packet_manifest_digest_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "Chummer6"
            root.mkdir(parents=True, exist_ok=True)
            registry_path = self._write_fixture(root)
            packet_path = root / ".guide-internal" / "receipts" / "CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json"
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            packet["authority"]["manifestSha256"] = "0" * 64
            packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")

            original_root = MODULE.REPO_ROOT
            original_download = MODULE.DOWNLOAD_PATH
            original_status = MODULE.STATUS_PATH
            original_packet = MODULE.PACKET_PATH
            try:
                MODULE.REPO_ROOT = root
                MODULE.DOWNLOAD_PATH = root / "DOWNLOAD.md"
                MODULE.STATUS_PATH = root / "STATUS.md"
                MODULE.PACKET_PATH = packet_path
                with mock.patch.dict(os.environ, {MODULE.REGISTRY_ENV: str(registry_path)}, clear=False):
                    with self.assertRaisesRegex(ValueError, "authority.manifestSha256"):
                        MODULE.main([])
            finally:
                MODULE.REPO_ROOT = original_root
                MODULE.DOWNLOAD_PATH = original_download
                MODULE.STATUS_PATH = original_status
                MODULE.PACKET_PATH = original_packet


if __name__ == "__main__":
    unittest.main()
