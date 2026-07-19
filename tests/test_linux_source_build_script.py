from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "build-chummer6-linux.sh"


class LinuxSourceBuildScriptTests(unittest.TestCase):
    def run_script(
        self, *arguments: str, env: dict[str, str] | None = None, timeout: int = 30
    ) -> subprocess.CompletedProcess[str]:
        command_env = os.environ.copy()
        command_env.update({"CHUMMER_MIN_FREE_GIB": "0"})
        if env:
            command_env.update(env)
        return subprocess.run(
            ["bash", str(SCRIPT), *arguments],
            cwd=REPO_ROOT,
            env=command_env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )

    def test_help_describes_the_immutable_no_siblings_flow(self) -> None:
        completed = self.run_script("--help")
        self.assertEqual(0, completed.returncode, completed.stdout)
        for phrase in (
            "exact 40-character commit",
            "without executing dotnet-install.sh",
            "no network package sources or siblings",
            "releaseEvidenceEligible=false",
            "Python >=3.11",
        ):
            self.assertIn(phrase, completed.stdout)

    def test_audit_emits_one_well_formed_completion_line(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            completed = self.run_script("--audit-only", "--base", temp_dir)
        self.assertEqual(0, completed.returncode, completed.stdout)
        lines = [
            line for line in completed.stdout.splitlines() if line.startswith("Audit complete:")
        ]
        self.assertEqual(1, len(lines), completed.stdout)
        self.assertRegex(
            lines[0],
            r"^Audit complete: immutable source lock, Python 3\.\d+\.\d+, "
            r"linux-x64 -> linux-x64, five exact commits\.$",
        )

    def test_unsuitable_python3_then_suitable_python311_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            old = fake_bin / "unsuitable-python3"
            good = fake_bin / "suitable-python3.11"
            old.write_text(
                "#!/usr/bin/env bash\n"
                "if [[ ${1:-} == -c ]]; then echo 3.10.14; exit 0; fi\n"
                "exit 91\n",
                encoding="utf-8",
            )
            good.write_text(
                f"#!/usr/bin/env bash\nexec {sys.executable!s} \"$@\"\n",
                encoding="utf-8",
            )
            old.chmod(0o755)
            good.chmod(0o755)
            completed = self.run_script(
                "--audit-only",
                "--base",
                str(root / "build"),
                env={
                    "PATH": f"{fake_bin}:{os.environ['PATH']}",
                    "CHUMMER_PYTHON_CANDIDATES": f"{old.name} {good.name}",
                },
            )
        self.assertEqual(0, completed.returncode, completed.stdout)
        self.assertIn("Selected Python", completed.stdout)
        self.assertIn(str(good), completed.stdout)
        self.assertIn("Audit complete", completed.stdout)

    def test_no_suitable_python_fails_before_authority_or_clone_work(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fake = root / "python-too-old"
            fake.write_text(
                "#!/usr/bin/env bash\n"
                "if [[ ${1:-} == -c ]]; then echo 3.10.14; exit 0; fi\n"
                "exit 91\n",
                encoding="utf-8",
            )
            fake.chmod(0o755)
            completed = self.run_script(
                "--audit-only",
                "--base",
                str(root / "never-created"),
                env={"CHUMMER_PYTHON_CANDIDATES": str(fake)},
            )
            self.assertFalse((root / "never-created").exists())
        self.assertNotEqual(0, completed.returncode, completed.stdout)
        self.assertIn("Python >=3.11 is required", completed.stdout)
        self.assertNotIn("Cloning five exact", completed.stdout)

    def test_moving_ref_requires_acknowledgement_and_remains_review_only(self) -> None:
        rejected = self.run_script("--audit-only", "--ref", "main")
        self.assertEqual(2, rejected.returncode, rejected.stdout)
        self.assertIn("requires --allow-moving-ref", rejected.stdout)
        with tempfile.TemporaryDirectory() as temp_dir:
            allowed = self.run_script(
                "--audit-only",
                "--allow-moving-ref",
                "--ref",
                "main",
                "--base",
                temp_dir,
            )
        self.assertEqual(0, allowed.returncode, allowed.stdout)
        self.assertIn("NON-REPRODUCIBLE REQUEST", allowed.stdout)
        self.assertIn("NOT RELEASE EVIDENCE", allowed.stdout)

    def test_ephemeral_nuget_config_is_removed_on_normal_and_error_exit(self) -> None:
        for action, expected in (("normal", 0), ("error", 1)):
            with self.subTest(action=action), tempfile.TemporaryDirectory() as temp_dir:
                completed = self.run_script(
                    "--base",
                    temp_dir,
                    env={
                        "CHUMMER_SOURCE_BUILD_TEST_MODE": "1",
                        "CHUMMER_SOURCE_BUILD_CLEANUP_TEST_ACTION": action,
                    },
                )
                self.assertEqual(expected, completed.returncode, completed.stdout)
                self.assertEqual([], list(Path(temp_dir).glob(".source-run.*")))
                self.assertEqual([], list(Path(temp_dir).glob("**/NuGet.Config")))

    def test_ephemeral_nuget_config_is_removed_on_int_and_term(self) -> None:
        for sent_signal, expected in (
            (signal.SIGHUP, 129),
            (signal.SIGINT, 130),
            (signal.SIGTERM, 143),
        ):
            with self.subTest(sent_signal=sent_signal), tempfile.TemporaryDirectory() as temp_dir:
                env = os.environ.copy()
                env.update(
                    {
                        "CHUMMER_MIN_FREE_GIB": "0",
                        "CHUMMER_SOURCE_BUILD_TEST_MODE": "1",
                        "CHUMMER_SOURCE_BUILD_CLEANUP_TEST_ACTION": "wait",
                    }
                )
                process = subprocess.Popen(
                    ["bash", str(SCRIPT), "--base", temp_dir],
                    cwd=REPO_ROOT,
                    env=env,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                )
                self.assertIsNotNone(process.stdout)
                output = ""
                deadline = time.monotonic() + 20
                while "CLEANUP_TEST_READY" not in output and time.monotonic() < deadline:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                    output += line
                self.assertIn("CLEANUP_TEST_READY", output)
                process.send_signal(sent_signal)
                remainder, _ = process.communicate(timeout=10)
                output += remainder
                self.assertEqual(expected, process.returncode, output)
                self.assertEqual([], list(Path(temp_dir).glob(".source-run.*")))
                self.assertEqual([], list(Path(temp_dir).glob("**/NuGet.Config")))

    def test_prelock_inspection_file_is_removed_when_interrupted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env = os.environ.copy()
            env.update(
                {
                    "CHUMMER_MIN_FREE_GIB": "0",
                    "CHUMMER_SOURCE_BUILD_TEST_MODE": "1",
                    "CHUMMER_SOURCE_BUILD_CLEANUP_TEST_ACTION": "prelock-wait",
                }
            )
            process = subprocess.Popen(
                ["bash", str(SCRIPT), "--base", temp_dir],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            self.assertIsNotNone(process.stdout)
            output = ""
            deadline = time.monotonic() + 20
            while "PRELOCK_CLEANUP_TEST_READY" not in output and time.monotonic() < deadline:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                output += line
            self.assertIn("PRELOCK_CLEANUP_TEST_READY", output)
            process.send_signal(signal.SIGHUP)
            remainder, _ = process.communicate(timeout=10)
            output += remainder
            self.assertEqual(129, process.returncode, output)
            self.assertEqual([], list(Path(temp_dir).glob(".source-lock-inspect.*")))

    def test_locked_clone_ignores_an_advanced_fake_hub_main(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            remotes = root / "remotes"
            work = root / "hub-work"
            remote = remotes / "chummer6-hub.git"
            remotes.mkdir()
            subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
            subprocess.run(["git", "init", str(work)], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(work), "config", "user.email", "test@example.invalid"], check=True)
            subprocess.run(["git", "-C", str(work), "config", "user.name", "Source Lock Test"], check=True)
            (work / "authority.txt").write_text("locked\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(work), "add", "authority.txt"], check=True)
            subprocess.run(["git", "-C", str(work), "commit", "-m", "locked authority"], check=True, capture_output=True)
            locked = subprocess.check_output(
                ["git", "-C", str(work), "rev-parse", "HEAD"], text=True
            ).strip()
            (work / "authority.txt").write_text("advanced main\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(work), "commit", "-am", "advance main"], check=True, capture_output=True)
            advanced = subprocess.check_output(
                ["git", "-C", str(work), "rev-parse", "HEAD"], text=True
            ).strip()
            self.assertNotEqual(locked, advanced)
            subprocess.run(["git", "-C", str(work), "branch", "-M", "main"], check=True)
            subprocess.run(["git", "-C", str(work), "remote", "add", "origin", str(remote)], check=True)
            subprocess.run(["git", "-C", str(work), "push", "-u", "origin", "main"], check=True, capture_output=True)

            completed = self.run_script(
                "--base",
                str(root / "build"),
                env={
                    "CHUMMER_REPO_BASE_URL": f"file://{remotes}",
                    "CHUMMER_SOURCE_BUILD_TEST_MODE": "1",
                    "CHUMMER_SOURCE_BUILD_CLEANUP_TEST_ACTION": "clone-exact",
                    "CHUMMER_SOURCE_BUILD_TEST_REPOSITORY": "chummer6-hub",
                    "CHUMMER_SOURCE_BUILD_TEST_COMMIT": locked,
                },
            )
        self.assertEqual(0, completed.returncode, completed.stdout)
        self.assertIn(f"CLONE_EXACT_HEAD {locked}", completed.stdout)
        self.assertNotIn(f"CLONE_EXACT_HEAD {advanced}", completed.stdout)

    def test_script_has_no_installer_execution_or_curl_credential_config(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("bash \"$DOTNET_INSTALL", text)
        self.assertNotIn("dotnet-install.sh --", text)
        self.assertNotIn("curl --config", text)
        self.assertNotIn("Authorization: Bearer", text)
        self.assertIn("curl --disable --fail --location", text)
        self.assertIn("install-sdk", text)
        self.assertIn("sanitize-diagnostics", text)
        self.assertIn("clone_exact", text)
        self.assertIn("ChummerUseLocalCompatibilityTree=false", text)

    def test_restore_installs_project_local_locks_without_a_global_lock_path(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('NUGET_CONFIG="$UI_ROOT/NuGet.Config"', text)
        self.assertIn('cd "$UI_ROOT"', text)
        self.assertIn('"$DOTNET" restore "$PROJECT_RELATIVE"', text)
        self.assertIn('--configfile NuGet.Config', text)
        self.assertIn('--locked-mode', text)
        self.assertIn('project_directory="$UI_ROOT/${project%/*}"', text)
        self.assertIn('package_lock="$project_directory/packages.lock.json"', text)
        self.assertIn('PROJECT_LOCK_COUNT" -eq 3', text)
        self.assertNotIn('--lock-file-path', text)
        self.assertNotIn('NuGetLockFilePath', text)
        self.assertNotIn('export RestoreConfigFile=', text)

    def test_malicious_curlrc_cannot_inject_auth_or_verbose_diagnostics(self) -> None:
        sentinel = "ambient-curl-bearer-sentinel-73f9"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            args_file = root / "curl.args"
            fake_curl = fake_bin / "curl"
            fake_curl.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "printf '%s\\n' \"$@\" > \"$CHUMMER_CURL_ARGS_FILE\"\n"
                "if [[ ${1:-} != --disable ]]; then cat \"$HOME/.curlrc\"; fi\n"
                "output=''\n"
                "while (($#)); do\n"
                "  if [[ $1 == --output ]]; then output=$2; shift 2; else shift; fi\n"
                "done\n"
                "[[ -n $output ]] && : > \"$output\"\n",
                encoding="utf-8",
            )
            fake_curl.chmod(0o755)
            (root / ".curlrc").write_text(
                f'verbose\nheader = "Authorization: Bearer {sentinel}"\n',
                encoding="utf-8",
            )
            completed = self.run_script(
                "--base",
                str(root / "build"),
                env={
                    "HOME": str(root),
                    "PATH": f"{fake_bin}:{os.environ['PATH']}",
                    "CHUMMER_CURL_ARGS_FILE": str(args_file),
                    "CHUMMER_SOURCE_BUILD_TEST_MODE": "1",
                    "CHUMMER_SOURCE_BUILD_CLEANUP_TEST_ACTION": "curl-config",
                },
            )
            arguments = args_file.read_text(encoding="utf-8").splitlines()
        self.assertEqual(0, completed.returncode, completed.stdout)
        self.assertEqual("--disable", arguments[0])
        self.assertNotIn(sentinel, completed.stdout)
        self.assertNotIn("Authorization: Bearer", completed.stdout)


if __name__ == "__main__":
    unittest.main()
