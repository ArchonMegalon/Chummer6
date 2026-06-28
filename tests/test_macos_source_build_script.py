from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "build-chummer6-macos-local.sh"
AUDIT_SCRIPT = REPO_ROOT / "scripts" / "check-host-chummer6-macos-local.sh"
INSTALL_SCRIPT = REPO_ROOT / "scripts" / "install-chummer6-macos-local.sh"
DOC = REPO_ROOT / "SOURCE_BUILD_MACOS.md"
DOWNLOAD = REPO_ROOT / "DOWNLOAD.md"


class MacOsSourceBuildScriptTests(unittest.TestCase):
    def test_scripts_have_valid_bash_syntax(self) -> None:
        for path in (SCRIPT, AUDIT_SCRIPT, INSTALL_SCRIPT):
            completed = subprocess.run(
                ["bash", "-n", str(path)],
                cwd=REPO_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=30,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout)

    def test_build_script_help_stays_local_only(self) -> None:
        completed = subprocess.run(
            ["bash", str(SCRIPT), "--help"],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("--audit-only", completed.stdout)
        self.assertIn("never installs macOS packages", completed.stdout)
        self.assertIn("local source-build helper for personal macOS binaries", completed.stdout)
        self.assertIn("does not sign or notarize anything", completed.stdout)
        self.assertIn("only builds the binary and archive artifacts", completed.stdout)
        self.assertIn("never installs", completed.stdout)
        self.assertIn("Install the result", completed.stdout)
        self.assertIn("./install-chummer6-macos-local.sh", completed.stdout)

    def test_host_audit_wrapper_help_is_clear(self) -> None:
        completed = subprocess.run(
            ["bash", str(AUDIT_SCRIPT), "--help"],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("ready for a local Chummer6 source build", completed.stdout)
        self.assertIn("never builds Chummer", completed.stdout)

    def test_install_script_help_describes_local_app_bundle_install(self) -> None:
        completed = subprocess.run(
            ["bash", str(INSTALL_SCRIPT), "--help"],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("already built local Chummer6 macOS binary", completed.stdout)
        self.assertIn("personal .app bundle", completed.stdout)
        self.assertIn("$HOME/Applications/Chummer6 Source Build.app", completed.stdout)
        self.assertIn("--artifact PATH", completed.stdout)
        self.assertIn("--archive PATH", completed.stdout)

    def test_non_macos_host_fails_cleanly_before_build_work(self) -> None:
        completed = subprocess.run(
            ["bash", str(SCRIPT), "--audit-only", "--base", str(REPO_ROOT / ".tmp" / "mac-audit-test")],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
            check=False,
        )
        self.assertNotEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("This script builds only on macOS.", completed.stdout)

    def test_script_contains_expected_local_build_defaults(self) -> None:
        script_text = SCRIPT.read_text(encoding="utf-8")
        wrapper_text = AUDIT_SCRIPT.read_text(encoding="utf-8")
        install_text = INSTALL_SCRIPT.read_text(encoding="utf-8")

        self.assertIn('CHUMMER_DESKTOP_UPDATE_MODE="${CHUMMER_DESKTOP_UPDATE_MODE:-notify}"', script_text)
        self.assertIn('CHUMMER_DESKTOP_ANALYTICS_DEFAULT="${CHUMMER_DESKTOP_ANALYTICS_DEFAULT:-off}"', script_text)
        self.assertIn('REPO_BASE_URL="${CHUMMER_REPO_BASE_URL:-https://github.com/$GITHUB_ORG}"', script_text)
        self.assertIn('RID="osx-arm64"', script_text)
        self.assertIn('RID="osx-x64"', script_text)
        self.assertIn('shasum -a 256 "$1" | awk', script_text)
        self.assertIn("git lfs install --skip-repo", script_text)
        self.assertIn('while [[ -L "$SOURCE" ]]', script_text)
        self.assertIn('exec "$HERE/Chummer.Avalonia" "$@"', script_text)
        self.assertNotIn("sudo ", script_text)
        self.assertNotIn("install_system_dependencies", script_text)
        self.assertIn('CHUMMER_MIN_FREE_GIB="${CHUMMER_MIN_FREE_GIB:-0}"', wrapper_text)
        self.assertIn('DEFAULT_DESTINATION="${CHUMMER_MAC_INSTALL_DESTINATION:-$HOME/Applications/Chummer6 Source Build.app}"', install_text)
        self.assertIn('while [[ -L "$SOURCE" ]]', install_text)
        self.assertIn('CFBundleExecutable</key>', install_text)
        self.assertIn('exec "$PAYLOAD_DIR/Chummer.Avalonia" "$@"', install_text)
        self.assertIn('xattr -dr com.apple.quarantine "$DESTINATION_PATH"', install_text)
        self.assertNotIn("codesign", install_text)

    def test_public_docs_make_the_two_script_flow_explicit(self) -> None:
        doc_text = DOC.read_text(encoding="utf-8")
        download_text = DOWNLOAD.read_text(encoding="utf-8")

        self.assertIn("Build from source on macOS", doc_text)
        self.assertIn("Most users should use the installers on [Download](DOWNLOAD.md).", doc_text)
        self.assertIn("macOS is not on the public installer shelf today", doc_text)
        self.assertIn("build-chummer6-macos-local.sh", doc_text)
        self.assertIn("install-chummer6-macos-local.sh", doc_text)
        self.assertIn("The binary is installed by a second script on purpose.", doc_text)
        self.assertIn("The build step never installs it for you.", doc_text)
        self.assertIn("does not install packages, it does not ask for `sudo`, and it never installs the `.app` bundle", doc_text)
        self.assertIn("CHUMMER_DESKTOP_UPDATE_MODE=notify", doc_text)
        self.assertIn("CHUMMER_DESKTOP_ANALYTICS_DEFAULT=off", doc_text)
        self.assertIn("unsigned `.app` bundle", doc_text)
        self.assertIn("not an official macOS release", doc_text)
        self.assertIn("For a personal local Mac build, use [SOURCE_BUILD_MACOS.md](SOURCE_BUILD_MACOS.md).", download_text)


if __name__ == "__main__":
    unittest.main()
