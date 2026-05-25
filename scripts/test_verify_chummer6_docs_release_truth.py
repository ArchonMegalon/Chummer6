#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parent / "verify_chummer6_docs_release_truth.py"
SPEC = importlib.util.spec_from_file_location("verify_chummer6_docs_release_truth_module", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DocsReleaseTruthVerifierTests(unittest.TestCase):
    def _write_fixture(
        self,
        root: Path,
        *,
        shelf_truth_line: str,
        available_platforms: list[str],
        missing_platforms: list[str],
        missing_installer_lane_line: str,
        architecture_scope_line: str,
        download_warning_line: str,
        migration_preview_line: str,
        migration_wait_line: str | None = None,
    ) -> None:
        packet = {
            "shelf_truth_line": shelf_truth_line,
            "proof_scope_line": "Proof on the public shelf is scoped to the posted files and flows you can inspect today; it is not a blanket flagship-complete claim.",
            "release_status": "Published",
            "available_platforms": available_platforms,
            "missing_platforms": missing_platforms,
            "missing_installer_lane_line": missing_installer_lane_line,
            "architecture_scope_line": architecture_scope_line,
        }
        (root / "CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json").write_text(
            json.dumps(packet, indent=2) + "\n",
            encoding="utf-8",
        )
        (root / "README.md").write_text(
            "\n".join(
                [
                    "# Readme",
                    packet["shelf_truth_line"],
                    packet["proof_scope_line"],
                    "This page keeps the clear public proof boundary intact.",
                    packet["missing_installer_lane_line"],
                    packet["architecture_scope_line"],
                ]
            ),
            encoding="utf-8",
        )
        (root / "STATUS.md").write_text(
            "\n".join(
                [
                    "# Status",
                    f"- Release status: {packet['release_status']}.",
                    packet["shelf_truth_line"],
                    packet["missing_installer_lane_line"],
                    packet["architecture_scope_line"],
                ]
            ),
            encoding="utf-8",
        )
        (root / "DOWNLOAD.md").write_text(
            "\n".join(
                [
                    "# Download",
                    packet["shelf_truth_line"],
                    "Proof scope: this is not a blanket flagship promise.",
                    "Downloads are served from chummer.run.",
                    download_warning_line,
                ]
            ),
            encoding="utf-8",
        )
        migration_rows = [
            "# From Chummer5a to Chummer6",
            migration_preview_line,
        ]
        if migration_wait_line:
            migration_rows.append(migration_wait_line)
        (root / "FROM_CHUMMER5A_TO_CHUMMER6.md").write_text("\n".join(migration_rows), encoding="utf-8")

    def test_main_accepts_available_platforms_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_fixture(
                root,
                shelf_truth_line="Downloads are currently live for Windows and Linux, but macOS still lacks the promoted desktop installer proof this release says they need.",
                available_platforms=["Windows", "Linux"],
                missing_platforms=["macOS"],
                missing_installer_lane_line="Still missing from the promoted installer lane: macOS.",
                architecture_scope_line="Current public desktop scope covers Windows x64, Linux x64, and macOS ARM64 only. No public route is posted for Windows ARM64, Linux ARM64, or macOS x64 on the current shelf.",
                download_warning_line="- Current warning: There is still no public macOS installer.",
                migration_preview_line="- Today you can try preview builds on Windows and Linux.",
                migration_wait_line="- If you rely on macOS as your main platform, wait before switching full time.",
            )
            original_root = MODULE.REPO_ROOT
            original_packet = MODULE.PACKET_PATH
            original_readme = MODULE.README_PATH
            original_status = MODULE.STATUS_PATH
            original_download = MODULE.DOWNLOAD_PATH
            original_migration = MODULE.MIGRATION_PATH
            try:
                MODULE.REPO_ROOT = root
                MODULE.PACKET_PATH = root / "CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json"
                MODULE.README_PATH = root / "README.md"
                MODULE.STATUS_PATH = root / "STATUS.md"
                MODULE.DOWNLOAD_PATH = root / "DOWNLOAD.md"
                MODULE.MIGRATION_PATH = root / "FROM_CHUMMER5A_TO_CHUMMER6.md"
                self.assertEqual(MODULE.main(), 0)
            finally:
                MODULE.REPO_ROOT = original_root
                MODULE.PACKET_PATH = original_packet
                MODULE.README_PATH = original_readme
                MODULE.STATUS_PATH = original_status
                MODULE.DOWNLOAD_PATH = original_download
                MODULE.MIGRATION_PATH = original_migration

    def test_main_fails_when_migration_preview_line_drifts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_fixture(
                root,
                shelf_truth_line="Downloads are currently live for Windows and Linux, but macOS still lacks the promoted desktop installer proof this release says they need.",
                available_platforms=["Windows", "Linux"],
                missing_platforms=["macOS"],
                missing_installer_lane_line="Still missing from the promoted installer lane: macOS.",
                architecture_scope_line="Current public desktop scope covers Windows x64, Linux x64, and macOS ARM64 only. No public route is posted for Windows ARM64, Linux ARM64, or macOS x64 on the current shelf.",
                download_warning_line="- Current warning: There is still no public macOS installer.",
                migration_preview_line="- Today you can try preview builds on Windows and Linux.",
                migration_wait_line="- If you rely on macOS as your main platform, wait before switching full time.",
            )
            (root / "FROM_CHUMMER5A_TO_CHUMMER6.md").write_text(
                "# From Chummer5a to Chummer6\n- Today you can try preview builds on Windows.\n- If you rely on macOS as your main platform, wait before switching full time.\n",
                encoding="utf-8",
            )
            original_root = MODULE.REPO_ROOT
            original_packet = MODULE.PACKET_PATH
            original_readme = MODULE.README_PATH
            original_status = MODULE.STATUS_PATH
            original_download = MODULE.DOWNLOAD_PATH
            original_migration = MODULE.MIGRATION_PATH
            try:
                MODULE.REPO_ROOT = root
                MODULE.PACKET_PATH = root / "CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json"
                MODULE.README_PATH = root / "README.md"
                MODULE.STATUS_PATH = root / "STATUS.md"
                MODULE.DOWNLOAD_PATH = root / "DOWNLOAD.md"
                MODULE.MIGRATION_PATH = root / "FROM_CHUMMER5A_TO_CHUMMER6.md"
                with self.assertRaises(ValueError):
                    MODULE.main()
            finally:
                MODULE.REPO_ROOT = original_root
                MODULE.PACKET_PATH = original_packet
                MODULE.README_PATH = original_readme
                MODULE.STATUS_PATH = original_status
                MODULE.DOWNLOAD_PATH = original_download
                MODULE.MIGRATION_PATH = original_migration

    def test_main_accepts_macos_only_preview_packet(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_fixture(
                root,
                shelf_truth_line="Downloads are currently live for macOS.",
                available_platforms=["macOS"],
                missing_platforms=[],
                missing_installer_lane_line="Promoted installer coverage is visible on every promised desktop platform.",
                architecture_scope_line="Current public desktop scope covers macOS ARM64 only. No public route is posted for Windows ARM64, Linux ARM64, and macOS x64 on the current shelf.",
                download_warning_line="- Current warning: Preview caveats still apply, but the current public downloads have recent proof for setup, recovery, offline-ready behavior, release follow-up, and support.",
                migration_preview_line="- Today you can try preview builds on macOS.",
            )
            original_root = MODULE.REPO_ROOT
            original_packet = MODULE.PACKET_PATH
            original_readme = MODULE.README_PATH
            original_status = MODULE.STATUS_PATH
            original_download = MODULE.DOWNLOAD_PATH
            original_migration = MODULE.MIGRATION_PATH
            try:
                MODULE.REPO_ROOT = root
                MODULE.PACKET_PATH = root / "CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json"
                MODULE.README_PATH = root / "README.md"
                MODULE.STATUS_PATH = root / "STATUS.md"
                MODULE.DOWNLOAD_PATH = root / "DOWNLOAD.md"
                MODULE.MIGRATION_PATH = root / "FROM_CHUMMER5A_TO_CHUMMER6.md"
                self.assertEqual(MODULE.main(), 0)
            finally:
                MODULE.REPO_ROOT = original_root
                MODULE.PACKET_PATH = original_packet
                MODULE.README_PATH = original_readme
                MODULE.STATUS_PATH = original_status
                MODULE.DOWNLOAD_PATH = original_download
                MODULE.MIGRATION_PATH = original_migration


if __name__ == "__main__":
    unittest.main()
