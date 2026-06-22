from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "build-chummer6-linux.sh"
DOC = REPO_ROOT / "SOURCE_BUILD_LINUX.md"
DOWNLOAD = REPO_ROOT / "DOWNLOAD.md"


class LinuxSourceBuildScriptTests(unittest.TestCase):
    def run_script(self, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        return subprocess.run(
            ["bash", str(SCRIPT), *args],
            cwd=REPO_ROOT,
            env=merged_env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=60,
            check=False,
        )

    def test_script_has_valid_bash_syntax(self) -> None:
        completed = subprocess.run(
            ["bash", "-n", str(SCRIPT)],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout)

    def test_help_documents_non_destructive_audit_mode(self) -> None:
        completed = self.run_script("--help")
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("--audit-only", completed.stdout)
        self.assertIn("--skip-system-deps", completed.stdout)
        self.assertIn("CHUMMER_BUILD_BASE", completed.stdout)

    def test_audit_only_runs_without_network_or_package_install(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            completed = self.run_script(
                "--audit-only",
                "--base",
                temp_dir,
                env={"CHUMMER_MIN_FREE_GIB": "0"},
            )
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("Audit complete", completed.stdout)
        self.assertIn("Detected package manager", completed.stdout)
        self.assertNotIn("Cloning or updating", completed.stdout)
        self.assertNotIn("Installing the repository-pinned .NET SDK", completed.stdout)

    def test_invalid_disk_threshold_fails_before_work(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            completed = self.run_script(
                "--audit-only",
                "--base",
                temp_dir,
                env={"CHUMMER_MIN_FREE_GIB": "not-a-number"},
            )
        self.assertNotEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("CHUMMER_MIN_FREE_GIB must be a whole number", completed.stdout)

    def test_too_little_space_fails_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            completed = self.run_script(
                "--audit-only",
                "--base",
                temp_dir,
                env={"CHUMMER_MIN_FREE_GIB": "999999999"},
            )
        self.assertNotEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("At least 999999999 GiB free is required", completed.stdout)

    def test_public_docs_link_to_source_build_path_without_replacing_downloads(self) -> None:
        script_text = SCRIPT.read_text(encoding="utf-8")
        doc_text = DOC.read_text(encoding="utf-8")
        download_text = DOWNLOAD.read_text(encoding="utf-8")

        self.assertIn("Build from source on Linux", doc_text)
        self.assertIn("Most users should use the installers", doc_text)
        self.assertIn("--audit-only", doc_text)
        self.assertIn("--skip-system-deps", doc_text)
        self.assertIn("Advanced users can also [build the Linux desktop client from source](SOURCE_BUILD_LINUX.md).", download_text)
        self.assertIn("https://github.com/$GITHUB_ORG/$repository_name.git", script_text)
        self.assertIn("DOTNET_CLI_TELEMETRY_OPTOUT=1", script_text)
        self.assertIn("AVALONIA_TELEMETRY_OPTOUT=1", script_text)
        self.assertIn("ChummerUseLocalCompatibilityTree=true", script_text)


if __name__ == "__main__":
    unittest.main()
