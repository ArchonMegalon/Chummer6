from __future__ import annotations

import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "regenerate_public_guide_from_design.sh"


class RegeneratePublicGuideWrapperTests(unittest.TestCase):
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

    def test_help_documents_single_command_workflow(self) -> None:
        completed = self.run_script("--help")
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("Regenerate the Chummer6 public guide from the design repo", completed.stdout)
        self.assertIn("--check", completed.stdout)
        self.assertIn("--skip-http", completed.stdout)
        self.assertIn("CHUMMER_DESIGN_REPO_ROOT", completed.stdout)

    def test_verify_script_chain_mentions_linux_surface_guard(self) -> None:
        verify_script = (REPO_ROOT / "scripts" / "verify_public_guide.sh").read_text(encoding="utf-8")
        self.assertIn("test_verify_linux_source_build_surface.py", verify_script)

    def test_verify_script_supports_skip_http_mode(self) -> None:
        verify_script = (REPO_ROOT / "scripts" / "verify_public_guide.sh").read_text(encoding="utf-8")
        self.assertIn("--skip-http)", verify_script)
        self.assertIn('link_args+=(--skip-http)', verify_script)

    def test_wrapper_runs_generator_sync_and_verify_in_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chummer6_root = root / "chummer6"
            design_root = root / "chummer-design"
            out_dir = design_root / "products" / "chummer" / "public-guide"
            log_path = root / "calls.log"

            self._write_fake_scripts(chummer6_root, design_root)

            completed = self.run_script(
                env={
                    "CHUMMER6_REPO_ROOT": str(chummer6_root),
                    "CHUMMER_DESIGN_REPO_ROOT": str(design_root),
                    "CHUMMER_PUBLIC_GUIDE_OUT": str(out_dir),
                    "CALL_LOG": str(log_path),
                }
            )

            self.assertEqual(completed.returncode, 0, completed.stdout)
            calls = log_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(
                [
                    f"generator env:CHUMMER6_PUBLIC_GUIDE_SOURCE_ROOT={chummer6_root}",
                    f"generator --repo-root {design_root} --out {out_dir}",
                    f"sync --source {out_dir}",
                    f"verify --source {out_dir}",
                ],
                calls,
            )

    def test_check_mode_forwards_check_to_generator_and_sync(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chummer6_root = root / "chummer6"
            design_root = root / "chummer-design"
            out_dir = design_root / "products" / "chummer" / "public-guide"
            log_path = root / "calls.log"

            self._write_fake_scripts(chummer6_root, design_root)

            completed = self.run_script(
                "--check",
                env={
                    "CHUMMER6_REPO_ROOT": str(chummer6_root),
                    "CHUMMER_DESIGN_REPO_ROOT": str(design_root),
                    "CHUMMER_PUBLIC_GUIDE_OUT": str(out_dir),
                    "CALL_LOG": str(log_path),
                },
            )

            self.assertEqual(completed.returncode, 0, completed.stdout)
            calls = log_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(
                [
                    f"generator env:CHUMMER6_PUBLIC_GUIDE_SOURCE_ROOT={chummer6_root}",
                    f"generator --repo-root {design_root} --out {out_dir} --check",
                    f"sync --source {out_dir} --check",
                    f"verify --source {out_dir}",
                ],
                calls,
            )

    def test_skip_http_mode_is_forwarded_only_to_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chummer6_root = root / "chummer6"
            design_root = root / "chummer-design"
            out_dir = design_root / "products" / "chummer" / "public-guide"
            log_path = root / "calls.log"

            self._write_fake_scripts(chummer6_root, design_root)

            completed = self.run_script(
                "--skip-http",
                env={
                    "CHUMMER6_REPO_ROOT": str(chummer6_root),
                    "CHUMMER_DESIGN_REPO_ROOT": str(design_root),
                    "CHUMMER_PUBLIC_GUIDE_OUT": str(out_dir),
                    "CALL_LOG": str(log_path),
                },
            )

            self.assertEqual(completed.returncode, 0, completed.stdout)
            calls = log_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(f"verify --source {out_dir} --skip-http", calls[-1])
            self.assertNotIn("--skip-http", calls[-2])

    def test_canonical_regeneration_clears_portal_release_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chummer6_root = root / "chummer6"
            design_root = root / "chummer-design"
            out_dir = design_root / "products" / "chummer" / "public-guide"
            log_path = root / "calls.log"
            env_log_path = root / "environment.log"
            registry_root = root / "canonical-registry"

            self._write_fake_scripts(chummer6_root, design_root)

            completed = self.run_script(
                env={
                    "CHUMMER6_REPO_ROOT": str(chummer6_root),
                    "CHUMMER_DESIGN_REPO_ROOT": str(design_root),
                    "CHUMMER_PUBLIC_GUIDE_OUT": str(out_dir),
                    "CHUMMER_PORTAL_RELEASE_CHANNEL_PATHS": str(root / "stale-workspace-release.json"),
                    "CHUMMER_HUB_REGISTRY_ROOT": str(registry_root),
                    "CALL_LOG": str(log_path),
                    "ENV_LOG": str(env_log_path),
                },
            )

            self.assertEqual(completed.returncode, 0, completed.stdout)
            self.assertEqual(
                [
                    f"release-truth portal= hub={registry_root}",
                    f"generator portal= hub={registry_root}",
                ],
                env_log_path.read_text(encoding="utf-8").splitlines(),
            )

    @staticmethod
    def _write_fake_scripts(chummer6_root: Path, design_root: Path) -> None:
        (chummer6_root / "scripts").mkdir(parents=True)
        (design_root / "scripts" / "ai").mkdir(parents=True)
        (design_root / "products" / "chummer" / "public-guide").mkdir(parents=True)

        (design_root / "scripts" / "ai" / "materialize_public_guide_bundle.py").write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import os
                import sys
                env_log = os.environ.get("ENV_LOG")
                if env_log:
                    with open(env_log, "a", encoding="utf-8") as handle:
                        handle.write("generator portal=" + os.environ.get("CHUMMER_PORTAL_RELEASE_CHANNEL_PATHS", "") + " hub=" + os.environ.get("CHUMMER_HUB_REGISTRY_ROOT", "") + "\\n")
                with open(os.environ["CALL_LOG"], "a", encoding="utf-8") as handle:
                    handle.write("generator env:CHUMMER6_PUBLIC_GUIDE_SOURCE_ROOT=" + os.environ.get("CHUMMER6_PUBLIC_GUIDE_SOURCE_ROOT", "") + "\\n")
                    handle.write("generator " + " ".join(sys.argv[1:]) + "\\n")
                """
            ),
            encoding="utf-8",
        )
        (chummer6_root / "scripts" / "sync_public_guide_from_design.py").write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import os
                import sys
                with open(os.environ["CALL_LOG"], "a", encoding="utf-8") as handle:
                    handle.write("sync " + " ".join(sys.argv[1:]) + "\\n")
                """
            ),
            encoding="utf-8",
        )
        (chummer6_root / "scripts" / "materialize_public_release_truth_packet.py").write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import os
                env_log = os.environ.get("ENV_LOG")
                if env_log:
                    with open(env_log, "a", encoding="utf-8") as handle:
                        handle.write("release-truth portal=" + os.environ.get("CHUMMER_PORTAL_RELEASE_CHANNEL_PATHS", "") + " hub=" + os.environ.get("CHUMMER_HUB_REGISTRY_ROOT", "") + "\\n")
                raise SystemExit(0)
                """
            ),
            encoding="utf-8",
        )
        verify_script = chummer6_root / "scripts" / "verify_public_guide.sh"
        verify_script.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -euo pipefail
                printf 'verify %s\n' "$*" >> "$CALL_LOG"
                """
            ),
            encoding="utf-8",
        )
        verify_script.chmod(0o755)


if __name__ == "__main__":
    unittest.main()
