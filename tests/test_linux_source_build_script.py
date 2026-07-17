from __future__ import annotations

import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "build-chummer6-linux.sh"
INSTALL_SCRIPT = REPO_ROOT / "scripts" / "install-chummer6-linux-local.sh"
AUDIT_SCRIPT = REPO_ROOT / "scripts" / "check-host-chummer6-linux.sh"
PREREQ_SCRIPT = REPO_ROOT / "scripts" / "list-chummer6-linux-prereqs.sh"
DOCKER_GATE_SCRIPT = REPO_ROOT / "scripts" / "verify_linux_source_build_docker_gate.sh"
DOC = REPO_ROOT / "SOURCE_BUILD_LINUX.md"
DOWNLOAD = REPO_ROOT / "DOWNLOAD.md"
BUILD_SCRIPT_TIMEOUT_SECONDS = 180


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
            timeout=BUILD_SCRIPT_TIMEOUT_SECONDS,
            check=False,
        )

    def test_script_has_valid_bash_syntax(self) -> None:
        for path in (SCRIPT, INSTALL_SCRIPT, AUDIT_SCRIPT, PREREQ_SCRIPT, DOCKER_GATE_SCRIPT):
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

    def test_repo_sync_disables_git_auto_maintenance(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('git -c gc.auto=0 -c maintenance.auto=0 "$@"', script)
        self.assertIn('git_automation clone --depth 1 --filter=blob:none --branch "$GIT_REF" "$expected_url" "$target"', script)
        self.assertIn('git_automation -C "$target" fetch --depth 1 origin "$GIT_REF"', script)

    def test_host_audit_wrapper_runs_the_non_destructive_audit_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            completed = subprocess.run(
                ["bash", str(AUDIT_SCRIPT), "--base", temp_dir],
                cwd=REPO_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=60,
                check=False,
            )
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("Checking build script syntax...", completed.stdout)
        self.assertIn("Running host audit...", completed.stdout)
        self.assertIn("Audit complete", completed.stdout)

    def test_prerequisite_script_prints_package_guidance(self) -> None:
        completed = subprocess.run(
            ["bash", str(PREREQ_SCRIPT), "--manager", "apt"],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("Package manager: apt", completed.stdout)
        self.assertIn("Base tools:", completed.stdout)
        self.assertIn("Runtime and desktop libraries:", completed.stdout)
        self.assertIn("apt-get install git git-lfs curl", completed.stdout)

    def test_docker_gate_help_describes_the_fresh_container_lane(self) -> None:
        completed = subprocess.run(
            ["bash", str(DOCKER_GATE_SCRIPT), "--help"],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("fresh slim Docker container", completed.stdout)
        self.assertIn("debian:bookworm-slim", completed.stdout)
        self.assertIn("CHUMMER_KEEP_DOCKER_GATE_WORKDIR", completed.stdout)
        self.assertIn("CHUMMER_LINUX_SOURCE_BUILD_GATE_MIN_FREE_GIB", completed.stdout)

    def test_help_documents_non_destructive_audit_mode(self) -> None:
        completed = self.run_script("--help")
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("--audit-only", completed.stdout)
        self.assertIn("--skip-system-deps", completed.stdout)
        self.assertIn("CHUMMER_BUILD_BASE", completed.stdout)
        self.assertIn("no longer changes behavior", completed.stdout)
        self.assertIn("never installs", completed.stdout)
        self.assertIn("./install-chummer6-linux-local.sh", completed.stdout)

    def test_help_runs_when_home_is_unset(self) -> None:
        env = os.environ.copy()
        env.pop("HOME", None)
        completed = subprocess.run(
            ["bash", str(SCRIPT), "--help"],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("--audit-only", completed.stdout)

    def test_install_script_help_describes_user_local_install(self) -> None:
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
        self.assertIn("already built local Chummer6 Linux binary", completed.stdout)
        self.assertIn("$HOME/.local/opt/chummer6-source-build", completed.stdout)
        self.assertIn("$HOME/.local/bin/chummer6-source-build", completed.stdout)
        self.assertIn("--artifact PATH", completed.stdout)
        self.assertIn("--archive PATH", completed.stdout)

    def test_install_script_can_stage_a_user_local_install_from_artifact_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact = root / "artifact"
            destination = root / "install"
            command_link = root / "bin" / "chummer6-source-build"
            artifact.mkdir(parents=True)
            (artifact / "Chummer.Avalonia").write_text(
                "#!/usr/bin/env bash\nset -euo pipefail\nprintf 'fake avalonia %s %s\\n' \"$0\" \"${1:-}\"\n",
                encoding="utf-8",
            )
            (artifact / "BUILD-MANIFEST.txt").write_text("fake manifest\n", encoding="utf-8")
            (artifact / "run-chummer6.sh").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            (artifact / "Chummer.Avalonia").chmod(0o755)
            (artifact / "run-chummer6.sh").chmod(0o755)

            completed = subprocess.run(
                [
                    "bash",
                    str(INSTALL_SCRIPT),
                    "--artifact",
                    str(artifact),
                    "--destination",
                    str(destination),
                    "--command-link",
                    str(command_link),
                    "--force",
                ],
                cwd=REPO_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=30,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout)
            self.assertIn("Installed local source build:", completed.stdout)
            self.assertTrue((destination / "app" / "Chummer.Avalonia").exists())
            self.assertTrue((destination / "run-chummer6.sh").exists())
            self.assertTrue(command_link.exists())
            self.assertTrue(command_link.is_symlink())
            launcher_text = (destination / "run-chummer6.sh").read_text(encoding="utf-8")
            self.assertIn('while [[ -L "$SOURCE" ]]', launcher_text)
            self.assertIn('CHUMMER_DESKTOP_UPDATE_MODE="${CHUMMER_DESKTOP_UPDATE_MODE:-notify}"', launcher_text)
            self.assertIn('CHUMMER_DESKTOP_ANALYTICS_DEFAULT="${CHUMMER_DESKTOP_ANALYTICS_DEFAULT:-off}"', launcher_text)
            launched = subprocess.run(
                [str(command_link), "--startup-smoke"],
                cwd=REPO_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=30,
                check=False,
            )
            self.assertEqual(launched.returncode, 0, launched.stdout)
            self.assertIn("fake avalonia", launched.stdout)
            self.assertIn(str(destination / "app" / "Chummer.Avalonia"), launched.stdout)
            self.assertIn("--startup-smoke", launched.stdout)

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
        self.assertIn("build-chummer6-linux.sh --base", doc_text)
        self.assertIn("install-chummer6-linux-local.sh", doc_text)
        self.assertIn("--skip-system-deps", doc_text)
        self.assertIn("verify_linux_source_build_docker_gate.sh", doc_text)
        self.assertIn("debian:bookworm-slim", doc_text)
        self.assertIn("does not ask for `sudo`", doc_text)
        self.assertIn("does not install system packages either way", doc_text)
        self.assertIn("The build step never installs the user-local copy for you.", doc_text)
        self.assertIn("The binary is installed by a second script on purpose.", doc_text)
        self.assertIn("$HOME/.local/opt/chummer6-source-build", doc_text)
        self.assertIn("$HOME/.local/bin/chummer6-source-build", doc_text)
        self.assertIn("CHUMMER_DESKTOP_UPDATE_MODE=notify", doc_text)
        self.assertIn("The updater supports three modes:", doc_text)
        self.assertIn("`full` for automatic download and replacement", doc_text)
        self.assertIn("`notify` for update notices without automatic replacement", doc_text)
        self.assertIn("`off` to skip startup update checks", doc_text)
        self.assertIn("For extra-paranoid builds, you can also run the checked-in Docker verification script", doc_text)
        self.assertNotIn(".guide-internal/receipts/LINUX_SOURCE_BUILD_DOCKER_GATE.generated.json", doc_text)
        self.assertIn("a `.sha256` file", doc_text)
        self.assertNotIn("asks before installing Linux prerequisites", doc_text)
        self.assertIn("Advanced users can also [build the Linux desktop client from source](SOURCE_BUILD_LINUX.md).", download_text)
        self.assertIn("REPO_BASE_URL=\"${CHUMMER_REPO_BASE_URL:-https://github.com/$GITHUB_ORG}\"", script_text)
        self.assertIn("expected_url=\"$REPO_BASE_URL/$repository_name.git\"", script_text)
        self.assertIn("DOTNET_CLI_TELEMETRY_OPTOUT=1", script_text)
        self.assertIn("AVALONIA_TELEMETRY_OPTOUT=1", script_text)
        self.assertIn('CHUMMER_DESKTOP_UPDATE_MODE="${CHUMMER_DESKTOP_UPDATE_MODE:-notify}"', script_text)
        self.assertIn("This script only builds the binary and archive artifacts.", script_text)
        self.assertIn("./install-chummer6-linux-local.sh", script_text)
        self.assertIn("CHUMMER_KEEP_BUILD_TEMP", script_text)
        self.assertIn("cleanup_build_temp || true", script_text)
        self.assertIn("ChummerUseLocalCompatibilityTree=true", script_text)
        self.assertIn("CHUMMER_REPO_BASE_URL", script_text)
        self.assertIn("Missing required build tools:", script_text)
        self.assertIn("missing the ICU runtime needed by dotnet", script_text)
        docker_gate_text = DOCKER_GATE_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("debian:bookworm-slim", docker_gate_text)
        self.assertIn("bash scripts/check-host-chummer6-linux.sh --base /work/base", docker_gate_text)
        self.assertIn("bash scripts/build-chummer6-linux.sh --base /work/base", docker_gate_text)
        self.assertIn("CHUMMER_KEEP_DOCKER_GATE_WORKDIR", docker_gate_text)
        self.assertIn("CHUMMER_LINUX_SOURCE_BUILD_GATE_MIN_FREE_GIB", docker_gate_text)
        self.assertIn("CHUMMER_LINUX_SOURCE_BUILD_GATE_RECEIPT_PATH", docker_gate_text)
        self.assertIn('CHUMMER_MIN_FREE_GIB=${CHUMMER_LINUX_SOURCE_BUILD_GATE_MIN_FREE_GIB:-0}', docker_gate_text)
        self.assertIn("--startup-smoke", docker_gate_text)
        self.assertIn("CHUMMER_DESKTOP_STARTUP_SMOKE_RECEIPT", docker_gate_text)
        self.assertIn("CHUMMER_DESKTOP_STARTUP_SMOKE_FAILURE_PACKET", docker_gate_text)
        self.assertIn("fresh_container_gate", docker_gate_text)
        self.assertIn("--desktop-update-launch-installer", docker_gate_text)
        self.assertIn("updater-special-mode-", docker_gate_text)
        self.assertIn("updater-special-mode-success-", docker_gate_text)
        self.assertIn("installer_launch_failed", docker_gate_text)
        self.assertIn('cat > "$FAKE_BIN_ROOT/dpkg"', docker_gate_text)
        self.assertIn("dpkgInvoked", docker_gate_text)
        self.assertIn("stageDeleted", docker_gate_text)
        self.assertIn("docker_args=(", docker_gate_text)
        self.assertIn('docker "${docker_args[@]}"', docker_gate_text)
        self.assertIn('docker run --rm -v "$HOST_WORK_ROOT:/cleanup" "$IMAGE"', docker_gate_text)
        self.assertIn('if [[ "$CHUMMER_REPO_BASE_URL" == file://* ]]; then', docker_gate_text)
        self.assertIn('docker_args+=(-v "$repo_base_path:/mirror:ro")', docker_gate_text)
        self.assertIn('docker_args+=(-e "CHUMMER_GATE_LOCAL_REPO_MIRROR=1")', docker_gate_text)
        self.assertIn('repo_base_url_for_container="file:///mirror"', docker_gate_text)
        self.assertIn('if [[ "${CHUMMER_GATE_LOCAL_REPO_MIRROR:-0}" == "1" ]]; then', docker_gate_text)
        self.assertIn("git config --global --add safe.directory '*'", docker_gate_text)
        self.assertIn("write_receipt()", docker_gate_text)
        self.assertIn("LINUX_SOURCE_BUILD_DOCKER_GATE.generated.json", docker_gate_text)
        self.assertIn('"contract_name": "ea.chummer6_linux_source_build_docker_gate.v1"', docker_gate_text)
        install_text = INSTALL_SCRIPT.read_text(encoding="utf-8")
        self.assertIn('DEFAULT_DESTINATION="${CHUMMER_LINUX_INSTALL_DESTINATION:-$HOME/.local/opt/chummer6-source-build}"', install_text)
        self.assertIn('DEFAULT_COMMAND_LINK="${CHUMMER_LINUX_INSTALL_COMMAND_LINK:-$HOME/.local/bin/chummer6-source-build}"', install_text)
        self.assertIn('export CHUMMER_DESKTOP_UPDATE_MODE="${CHUMMER_DESKTOP_UPDATE_MODE:-notify}"', install_text)
        self.assertIn('export CHUMMER_DESKTOP_ANALYTICS_DEFAULT="${CHUMMER_DESKTOP_ANALYTICS_DEFAULT:-off}"', install_text)
        self.assertNotIn("sudo ", install_text)
        self.assertIn("This script never installs packages. It only prints the package names", PREREQ_SCRIPT.read_text(encoding="utf-8"))
        self.assertNotIn("run_root", script_text)
        self.assertNotIn("confirm(", script_text)
        self.assertNotIn("install_system_dependencies", script_text)
        self.assertNotIn("sudo apt-get install", script_text)
        self.assertNotIn("sudo dnf install", script_text)
        self.assertNotIn("sudo pacman -S", script_text)
        self.assertNotIn("sudo zypper install", script_text)
        self.assertIn("The binary and its native library links are verified.", doc_text)
        self.assertIn("A real desktop session is still needed for a final launch check.", doc_text)
        self.assertIn("ICU runtime libraries", doc_text)

    def test_full_build_fails_cleanly_when_required_tools_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            completed = self.run_script(
                "--base",
                temp_dir,
                env={
                    "CHUMMER_MIN_FREE_GIB": "0",
                    "PATH": "/bin",
                },
            )

        self.assertNotEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("Missing required build tools:", completed.stdout)
        self.assertTrue(
            any(hint in completed.stdout for hint in ("apt-get install", "dnf install", "pacman -S", "zypper install", "Install the missing tools with your package manager")),
            completed.stdout,
        )

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
            self.assertIn("Executable SHA256:", completed.stdout)
            self.assertIn("Archive SHA256:", completed.stdout)
            self.assertIn("All required owner projects are present.", completed.stdout)
            self.assertIn("source-build", completed.stdout)
            self.assertTrue((base / "artifacts" / "chummer6-linux-x64" / "Chummer.Avalonia").exists())
            launcher = base / "artifacts" / "chummer6-linux-x64" / "run-chummer6.sh"
            self.assertTrue(launcher.exists())
            self.assertIn('while [[ -L "$SOURCE" ]]', launcher.read_text(encoding="utf-8"))
            self.assertIn('CHUMMER_DESKTOP_UPDATE_MODE="${CHUMMER_DESKTOP_UPDATE_MODE:-notify}"', launcher.read_text(encoding="utf-8"))
            manifest = (base / "artifacts" / "chummer6-linux-x64" / "BUILD-MANIFEST.txt").read_text(encoding="utf-8")
            self.assertIn("chummer6-ui", manifest)
            self.assertIn("Executable SHA256:", manifest)
            archives = list((base / "artifacts").glob("chummer6-linux-x64-*.tar.gz"))
            self.assertEqual(1, len(archives), completed.stdout)
            self.assertFalse((base / ".tmp").exists())
            self.assertFalse((base / ".tools" / "dotnet-install.sh").exists())
            self.assertFalse((base / "chummer-core-engine" / ".tmp").exists())

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
    def _write_fake_dotnet(base: Path, sdk_version: str = "10.0.103") -> None:
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
                [
                    "git",
                    "-c",
                    "gc.auto=0",
                    "-c",
                    "maintenance.auto=0",
                    "clone",
                    "--bare",
                    str(source),
                    str(remotes / f"{repository_name}.git"),
                ],
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
            ["git", "-c", "gc.auto=0", "-c", "maintenance.auto=0", *args],
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
                    repo_root="${PWD%/chummer6-ui}"
                    mkdir -p "$repo_root/chummer-core-engine/.tmp/ai/local-nuget"
                    printf 'local package' > "$repo_root/chummer-core-engine/.tmp/ai/local-nuget/Chummer.Engine.Contracts.0.0.0-local.nupkg"
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
