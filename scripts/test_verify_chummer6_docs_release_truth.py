#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
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
            "authority": {"releaseDecisionStatus": "preview_ready"},
            "release_decision_status": "preview_ready",
            "release_posture": "preview_ready",
            "shelf_truth_line": shelf_truth_line,
            "short_release_summary": "Use the files linked on [Download](DOWNLOAD.md). If your platform is not listed there yet, wait before switching full time.",
            "desktop_pick_line": "If you see both desktop apps, start with Avalonia.",
            "published_line": "Published: June 21, 2026 at 5:53 UTC.",
            "release_status": "Published",
            "release_verification_summary": "This release covers installs and recovery.",
            "known_issue_summary": "No current download blocker is listed for these installers.",
            "linux_source_build_gate": {
                "status": "passed",
                "generated_at_utc": "20260622T201728Z",
                "docker_image": "debian:bookworm-slim",
                "rid": "linux-x64",
                "archive_sha256": "c045d341fd0a64b862e1546db188c5fd4ebb728fac0521133908e7724ecf44d7",
                "executable_sha256": "0744cbfbaac51ceeed13aaa376224000a50f984cf52cb7ee036d1670e343f786",
            },
            "macos_source_build_contract": {
                "status": "passed",
                "generated_at_utc": "2026-06-27T20:59:24Z",
                "scope": "script_contract_only",
                "runtime_coverage": "not_run_on_non_macos_host",
                "real_macos_runtime_proof_required": True,
                "maintenance_policy_marks_real_build_as_macos_only": True,
                "maintenance_policy_requires_two_step_install": True,
                "doc_marks_second_script_install": True,
            },
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
                    "If you are here to decide whether this is worth your time, the honest pitch is simple.",
                    "## Start here if you just want the answer",
                    packet["shelf_truth_line"],
                    packet["short_release_summary"],
                    packet["desktop_pick_line"],
                ]
            ),
            encoding="utf-8",
        )
        (root / "STATUS.md").write_text(
            "\n".join(
                [
                    "# Status",
                    packet["published_line"],
                    f"- Release status: {packet['release_status']}.",
                    packet["shelf_truth_line"],
                    packet["architecture_scope_line"],
                    packet["missing_installer_lane_line"],
                ]
            ),
            encoding="utf-8",
        )
        (root / "DOWNLOAD.md").write_text(
            "\n".join(
                [
                    "# Download",
                    MODULE._download_opening(available_platforms),
                    packet["published_line"],
                    f"- Release status: {packet['release_status']}.",
                    packet["shelf_truth_line"],
                    "Downloads are served from chummer.run.",
                    packet["release_verification_summary"],
                    packet["known_issue_summary"],
                    download_warning_line,
                ]
            ),
            encoding="utf-8",
        )
        now_dir = root / "NOW"
        now_dir.mkdir(parents=True, exist_ok=True)
        (now_dir / "current-status.md").write_text(
            "\n".join(
                [
                    "# Current status",
                    packet["published_line"],
                    f"- Release status: {packet['release_status']}.",
                    packet["shelf_truth_line"],
                    packet["architecture_scope_line"],
                    packet["release_verification_summary"],
                    packet["known_issue_summary"],
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
                shelf_truth_line="Windows and Linux downloads are posted.",
                available_platforms=["Windows", "Linux"],
                missing_platforms=["macOS"],
                missing_installer_lane_line="macOS does not have a normal installer yet.",
                architecture_scope_line="Desktop downloads are available for Windows x64 and Linux x64 only.",
                download_warning_line="macOS currently has archive previews only.",
                migration_preview_line="Today you can try the current builds on Windows and Linux.",
                migration_wait_line="If you rely on macOS as your main platform, wait before switching full time.",
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
                MODULE._verify_document_content()
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
                shelf_truth_line="Windows and Linux downloads are posted.",
                available_platforms=["Windows", "Linux"],
                missing_platforms=["macOS"],
                missing_installer_lane_line="macOS does not have a normal installer yet.",
                architecture_scope_line="Desktop downloads are available for Windows x64 and Linux x64 only.",
                download_warning_line="macOS currently has archive previews only.",
                migration_preview_line="Today you can try preview builds on Windows and Linux.",
                migration_wait_line="If you rely on macOS as your main platform, wait before switching full time.",
            )
            (root / "FROM_CHUMMER5A_TO_CHUMMER6.md").write_text(
                "# From Chummer5a to Chummer6\nToday you can try the current builds on Windows.\nIf you rely on macOS as your main platform, wait before switching full time.\n",
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
                    MODULE._verify_document_content()
            finally:
                MODULE.REPO_ROOT = original_root
                MODULE.PACKET_PATH = original_packet
                MODULE.README_PATH = original_readme
                MODULE.STATUS_PATH = original_status
                MODULE.DOWNLOAD_PATH = original_download
                MODULE.MIGRATION_PATH = original_migration

    def test_main_fails_when_public_docs_keep_stale_release_noise(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_fixture(
                root,
                shelf_truth_line="Windows and Linux downloads are posted.",
                available_platforms=["Windows", "Linux"],
                missing_platforms=["macOS"],
                missing_installer_lane_line="macOS does not have a normal installer yet.",
                architecture_scope_line="Desktop downloads are available for Windows x64 and Linux x64 only.",
                download_warning_line="No current download blocker is listed for these installers.",
                migration_preview_line="Today you can try the current builds on Windows and Linux.",
                migration_wait_line="If you rely on macOS as your main platform, wait before switching full time.",
            )
            (root / "DOWNLOAD.md").write_text(
                (root / "DOWNLOAD.md").read_text(encoding="utf-8")
                + "\nRelease status is missing or stale on this shelf, so preview publication is visible but not yet gold-ready.\n"
                + "Use a portable package only for recovery.\n",
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
                    MODULE._verify_document_content()
            finally:
                MODULE.REPO_ROOT = original_root
                MODULE.PACKET_PATH = original_packet
                MODULE.README_PATH = original_readme
                MODULE.STATUS_PATH = original_status
                MODULE.DOWNLOAD_PATH = original_download
                MODULE.MIGRATION_PATH = original_migration

    def test_main_accepts_macos_only_release_packet(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_fixture(
                root,
                shelf_truth_line="macOS downloads are posted.",
                available_platforms=["macOS"],
                missing_platforms=[],
                missing_installer_lane_line="Normal installers are available on every promised desktop platform.",
                architecture_scope_line="Desktop downloads are available for macOS ARM64 only.",
                download_warning_line="This release is still changing.",
                migration_preview_line="Today you can try the current builds on macOS.",
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
                MODULE._verify_document_content()
            finally:
                MODULE.REPO_ROOT = original_root
                MODULE.PACKET_PATH = original_packet
                MODULE.README_PATH = original_readme
                MODULE.STATUS_PATH = original_status
                MODULE.DOWNLOAD_PATH = original_download
                MODULE.MIGRATION_PATH = original_migration

    def test_main_fails_when_linux_source_build_gate_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_fixture(
                root,
                shelf_truth_line="Windows and Linux downloads are posted.",
                available_platforms=["Windows", "Linux"],
                missing_platforms=[],
                missing_installer_lane_line="Normal installers are available on every promised desktop platform.",
                architecture_scope_line="Desktop downloads are available for Linux x64 and Windows x64 only.",
                download_warning_line="No current download blocker is listed for these installers.",
                migration_preview_line="Today you can try the current builds on Windows and Linux.",
            )
            packet_path = root / "CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json"
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            packet.pop("linux_source_build_gate", None)
            packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
            original_root = MODULE.REPO_ROOT
            original_packet = MODULE.PACKET_PATH
            original_readme = MODULE.README_PATH
            original_status = MODULE.STATUS_PATH
            original_download = MODULE.DOWNLOAD_PATH
            original_migration = MODULE.MIGRATION_PATH
            try:
                MODULE.REPO_ROOT = root
                MODULE.PACKET_PATH = packet_path
                MODULE.README_PATH = root / "README.md"
                MODULE.STATUS_PATH = root / "STATUS.md"
                MODULE.DOWNLOAD_PATH = root / "DOWNLOAD.md"
                MODULE.MIGRATION_PATH = root / "FROM_CHUMMER5A_TO_CHUMMER6.md"
                with self.assertRaises(ValueError):
                    MODULE._verify_document_content()
            finally:
                MODULE.REPO_ROOT = original_root
                MODULE.PACKET_PATH = original_packet
                MODULE.README_PATH = original_readme
                MODULE.STATUS_PATH = original_status
                MODULE.DOWNLOAD_PATH = original_download
                MODULE.MIGRATION_PATH = original_migration

    def test_main_fails_when_macos_source_build_contract_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_fixture(
                root,
                shelf_truth_line="Windows and Linux downloads are posted.",
                available_platforms=["Windows", "Linux"],
                missing_platforms=[],
                missing_installer_lane_line="Normal installers are available on every promised desktop platform.",
                architecture_scope_line="Desktop downloads are available for Linux x64 and Windows x64 only.",
                download_warning_line="No current download blocker is listed for these installers.",
                migration_preview_line="Today you can try the current builds on Windows and Linux.",
            )
            packet_path = root / "CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json"
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            packet.pop("macos_source_build_contract", None)
            packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
            original_root = MODULE.REPO_ROOT
            original_packet = MODULE.PACKET_PATH
            original_readme = MODULE.README_PATH
            original_status = MODULE.STATUS_PATH
            original_download = MODULE.DOWNLOAD_PATH
            original_migration = MODULE.MIGRATION_PATH
            try:
                MODULE.REPO_ROOT = root
                MODULE.PACKET_PATH = packet_path
                MODULE.README_PATH = root / "README.md"
                MODULE.STATUS_PATH = root / "STATUS.md"
                MODULE.DOWNLOAD_PATH = root / "DOWNLOAD.md"
                MODULE.MIGRATION_PATH = root / "FROM_CHUMMER5A_TO_CHUMMER6.md"
                with self.assertRaises(ValueError):
                    MODULE._verify_document_content()
            finally:
                MODULE.REPO_ROOT = original_root
                MODULE.PACKET_PATH = original_packet
                MODULE.README_PATH = original_readme
                MODULE.STATUS_PATH = original_status
                MODULE.DOWNLOAD_PATH = original_download
                MODULE.MIGRATION_PATH = original_migration

    def test_main_fails_when_download_reintroduces_github_release_link(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_fixture(
                root,
                shelf_truth_line="Windows and Linux downloads are posted.",
                available_platforms=["Windows", "Linux"],
                missing_platforms=[],
                missing_installer_lane_line="Normal installers are available on every promised desktop platform.",
                architecture_scope_line="Desktop downloads are available for Linux x64 and Windows x64 only.",
                download_warning_line="Preview caveats still apply.",
                migration_preview_line="Today you can try the current builds on Windows and Linux.",
            )
            (root / "DOWNLOAD.md").write_text(
                (root / "DOWNLOAD.md").read_text(encoding="utf-8")
                + "\n- [Raw GitHub releases](https://github.com/ArchonMegalon/Chummer6/releases)\n",
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
                    MODULE._verify_document_content()
            finally:
                MODULE.REPO_ROOT = original_root
                MODULE.PACKET_PATH = original_packet
                MODULE.README_PATH = original_readme
                MODULE.STATUS_PATH = original_status
                MODULE.DOWNLOAD_PATH = original_download
                MODULE.MIGRATION_PATH = original_migration

    def test_main_fails_when_download_published_line_drifts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_fixture(
                root,
                shelf_truth_line="Windows and Linux downloads are posted.",
                available_platforms=["Windows", "Linux"],
                missing_platforms=[],
                missing_installer_lane_line="Normal installers are available on every promised desktop platform.",
                architecture_scope_line="Desktop downloads are available for Linux x64 and Windows x64 only.",
                download_warning_line="Preview caveats still apply.",
                migration_preview_line="Today you can try the current builds on Windows and Linux.",
            )
            download_path = root / "DOWNLOAD.md"
            download_path.write_text(
                download_path.read_text(encoding="utf-8").replace(
                    "Published: June 21, 2026 at 5:53 UTC.",
                    "Published: June 20, 2026 at 9:00 UTC.",
                ),
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
                    MODULE._verify_document_content()
            finally:
                MODULE.REPO_ROOT = original_root
                MODULE.PACKET_PATH = original_packet
                MODULE.README_PATH = original_readme
                MODULE.STATUS_PATH = original_status
                MODULE.DOWNLOAD_PATH = original_download
                MODULE.MIGRATION_PATH = original_migration

    def test_download_opening_is_derived_from_available_platforms(self) -> None:
        self.assertEqual(MODULE._download_opening(["macOS"]), "macOS downloads start on `chummer.run`.")
        self.assertEqual(
            MODULE._download_opening(["Linux", "Windows", "macOS"]),
            "Linux, Windows, and macOS downloads start on `chummer.run`.",
        )
        self.assertEqual(
            MODULE._download_opening([]),
            "Public downloads start on `chummer.run` when a release is posted.",
        )

    def test_registry_alignment_has_no_production_bypass_keyword(self) -> None:
        with self.assertRaises(TypeError):
            MODULE.main([], verify_registry_alignment=False)

    def test_every_invocation_requires_explicit_authority_flags(self) -> None:
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            MODULE.main([])
        self.assertEqual(raised.exception.code, 2)

    def test_gold_copy_requires_stable_ready_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            packet_path = Path(temp_dir) / "packet.json"
            packet_path.write_text(
                json.dumps(
                    {
                        "authority": {"releaseDecisionStatus": "preview_ready"},
                        "phase_label": "Gold-supported release",
                        "release_decision_status": "preview_ready",
                        "release_posture": "preview_ready",
                    }
                ),
                encoding="utf-8",
            )
            original_packet = MODULE.PACKET_PATH
            try:
                MODULE.PACKET_PATH = packet_path
                with self.assertRaisesRegex(ValueError, "stable_ready"):
                    MODULE._verify_document_content()
            finally:
                MODULE.PACKET_PATH = original_packet


if __name__ == "__main__":
    unittest.main()
