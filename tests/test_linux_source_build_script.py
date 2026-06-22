from __future__ import annotations

import os
import subprocess
import tempfile
import textwrap
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
        self.assertIn("REPO_BASE_URL=\"${CHUMMER_REPO_BASE_URL:-https://github.com/$GITHUB_ORG}\"", script_text)
        self.assertIn("expected_url=\"$REPO_BASE_URL/$repository_name.git\"", script_text)
        self.assertIn("DOTNET_CLI_TELEMETRY_OPTOUT=1", script_text)
        self.assertIn("AVALONIA_TELEMETRY_OPTOUT=1", script_text)
        self.assertIn('CHUMMER_DESKTOP_UPDATE_MODE="${CHUMMER_DESKTOP_UPDATE_MODE:-notify}"', script_text)
        self.assertIn("CHUMMER_KEEP_BUILD_TEMP", script_text)
        self.assertIn("cleanup_build_temp || true", script_text)
        self.assertIn("ChummerUseLocalCompatibilityTree=true", script_text)
        self.assertIn("CHUMMER_REPO_BASE_URL", script_text)
        self.assertIn("The script verifies the published binary and its native library links.", doc_text)
        self.assertIn("real Linux desktop session with X11 or Wayland", doc_text)

    def test_full_flow_can_build_from_local_git_mirror_with_fake_projects(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            remotes = root / "remotes"
            work = root / "work"
            base = root / "build"
            fake_bin = root / "bin"
            remotes.mkdir()
            fake_bin.mkdir()

            self._write_fake_git_lfs(fake_bin)
            self._write_fake_dotnet(base)
            self._create_fake_remote_repositories(work, remotes)

            completed = self.run_script(
                "--base",
                str(base),
                "--skip-system-deps",
                env={
                    "CHUMMER_MIN_FREE_GIB": "0",
                    "CHUMMER_REPO_BASE_URL": remotes.as_uri(),
                    "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
                },
            )

            self.assertEqual(completed.returncode, 0, completed.stdout)
            self.assertIn("Build complete.", completed.stdout)
            self.assertIn("All required owner projects are present.", completed.stdout)
            self.assertIn("source-build", completed.stdout)
            self.assertTrue((base / "artifacts" / "chummer6-linux-x64" / "Chummer.Avalonia").exists())
            launcher = base / "artifacts" / "chummer6-linux-x64" / "run-chummer6.sh"
            self.assertTrue(launcher.exists())
            self.assertIn('CHUMMER_DESKTOP_UPDATE_MODE="${CHUMMER_DESKTOP_UPDATE_MODE:-notify}"', launcher.read_text(encoding="utf-8"))
            manifest = (base / "artifacts" / "chummer6-linux-x64" / "BUILD-MANIFEST.txt").read_text(encoding="utf-8")
            self.assertIn("chummer6-ui", manifest)
            self.assertIn("Executable SHA256:", manifest)
            archives = list((base / "artifacts").glob("chummer6-linux-x64-*.tar.gz"))
            self.assertEqual(1, len(archives), completed.stdout)
            self.assertFalse((base / ".tmp").exists())
            self.assertFalse((base / ".tools" / "dotnet-install.sh").exists())

    def test_full_flow_uses_highest_sdk_version_across_cloned_repositories(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            remotes = root / "remotes"
            work = root / "work"
            base = root / "build"
            fake_bin = root / "bin"
            remotes.mkdir()
            fake_bin.mkdir()

            self._write_fake_git_lfs(fake_bin)
            self._write_fake_dotnet(base, sdk_version="10.0.103")
            self._create_fake_remote_repositories(work, remotes)

            completed = self.run_script(
                "--base",
                str(base),
                "--skip-system-deps",
                env={
                    "CHUMMER_MIN_FREE_GIB": "0",
                    "CHUMMER_REPO_BASE_URL": remotes.as_uri(),
                    "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
                },
            )

            self.assertEqual(completed.returncode, 0, completed.stdout)
            self.assertIn(".NET SDK: 10.0.103", completed.stdout)
            manifest = (base / "artifacts" / "chummer6-linux-x64" / "BUILD-MANIFEST.txt").read_text(encoding="utf-8")
            self.assertIn(".NET SDK: 10.0.103", manifest)

    @staticmethod
    def _write_fake_git_lfs(fake_bin: Path) -> None:
        git_lfs = fake_bin / "git-lfs"
        git_lfs.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        git_lfs.chmod(0o755)

    @staticmethod
    def _write_fake_dotnet(base: Path, sdk_version: str = "10.0.100") -> None:
        dotnet_dir = base / ".tools" / "dotnet"
        dotnet_dir.mkdir(parents=True)
        dotnet = dotnet_dir / "dotnet"
        dotnet.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                case "${1:-}" in
                  --list-sdks)
                    echo "__SDK_VERSION__ [/fake/sdk]"
                    ;;
                  --info)
                    echo ".NET SDK: __SDK_VERSION__"
                    ;;
                  *)
                    echo "fake dotnet $*"
                    ;;
                esac
                """
            ).replace("__SDK_VERSION__", sdk_version),
            encoding="utf-8",
        )
        dotnet.chmod(0o755)

    def _create_fake_remote_repositories(self, work: Path, remotes: Path) -> None:
        for repository_name, files in self._fake_repository_files().items():
            source = work / repository_name
            source.mkdir(parents=True)
            for relative_path, content in files.items():
                path = source / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                if relative_path.endswith(".sh"):
                    path.chmod(0o755)
            self._run_git(source, "init", "--initial-branch=main")
            self._run_git(source, "add", ".")
            self._run_git(
                source,
                "-c",
                "user.name=Chummer Test",
                "-c",
                "user.email=chummer-test@example.invalid",
                "commit",
                "-m",
                "seed",
            )
            completed = subprocess.run(
                ["git", "clone", "--bare", str(source), str(remotes / f"{repository_name}.git")],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=30,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout)

    @staticmethod
    def _run_git(cwd: Path, *args: str) -> None:
        completed = subprocess.run(
            ["git", *args],
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError(completed.stdout)

    @staticmethod
    def _fake_repository_files() -> dict[str, dict[str, str]]:
        project = "<Project Sdk=\"Microsoft.NET.Sdk\"></Project>\n"
        return {
            "chummer6-core": {
                "global.json": '{ "sdk": { "version": "10.0.103" } }\n',
                "Chummer.Contracts/Chummer.Contracts.csproj": project,
                "Chummer.Application/Chummer.Application.csproj": project,
                "Chummer.Infrastructure/Chummer.Infrastructure.csproj": project,
                "Chummer.Rulesets.Hosting/Chummer.Rulesets.Hosting.csproj": project,
                "Chummer.Rulesets.Sr4/Chummer.Rulesets.Sr4.csproj": project,
                "Chummer.Rulesets.Sr5/Chummer.Rulesets.Sr5.csproj": project,
                "Chummer.Rulesets.Sr6/Chummer.Rulesets.Sr6.csproj": project,
            },
            "chummer6-hub": {
                "global.json": '{ "sdk": { "version": "10.0.103" } }\n',
                "Chummer.Campaign.Contracts/Chummer.Campaign.Contracts.csproj": project,
                "Chummer.Play.Contracts/Chummer.Play.Contracts.csproj": project,
                "Chummer.Run.Contracts/Chummer.Run.Contracts.csproj": project,
            },
            "chummer6-hub-registry": {
                "global.json": '{ "sdk": { "version": "10.0.103" } }\n',
                "Chummer.Hub.Registry.Contracts/Chummer.Hub.Registry.Contracts.csproj": project,
            },
            "chummer6-ui-kit": {
                "global.json": '{ "sdk": { "version": "10.0.103" } }\n',
                "src/Chummer.Ui.Kit/Chummer.Ui.Kit.csproj": project,
            },
            "chummer6-ui": {
                "global.json": '{ "sdk": { "version": "10.0.100" } }\n',
                "Chummer.Avalonia/Chummer.Avalonia.csproj": project,
                "scripts/ai/restore.sh": "#!/usr/bin/env bash\nset -euo pipefail\necho restore \"$@\"\n",
                "scripts/ai/with-package-plane.sh": textwrap.dedent(
                    """\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    out=""
                    previous=""
                    for arg in "$@"; do
                      if [[ "$previous" == "-o" ]]; then
                        out="$arg"
                        break
                      fi
                      previous="$arg"
                    done
                    [[ -n "$out" ]] || { echo "missing -o" >&2; exit 2; }
                    mkdir -p "$out"
                    cat > "$out/Chummer.Avalonia" <<'APP'
                    #!/usr/bin/env bash
                    echo "fake Chummer.Avalonia"
                    APP
                    chmod +x "$out/Chummer.Avalonia"
                    """
                ),
            },
        }


if __name__ == "__main__":
    unittest.main()
