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
        self.assertIn("--authority-current", completed.stdout)
        self.assertIn("CHUMMER6_GUIDE_ASSET_SOURCE", completed.stdout)
        self.assertIn("CHUMMER_DESIGN_REPO_ROOT", completed.stdout)
        self.assertIn("CHUMMER_RELEASE_AUTHORITY_CURRENT", completed.stdout)

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
            authority_env = self._authority_env(root)

            completed = self.run_script(
                env={
                    "CHUMMER6_REPO_ROOT": str(chummer6_root),
                    "CHUMMER_DESIGN_REPO_ROOT": str(design_root),
                    "CHUMMER_PUBLIC_GUIDE_OUT": str(out_dir),
                    "CALL_LOG": str(log_path),
                    **authority_env,
                }
            )

            self.assertEqual(completed.returncode, 0, completed.stdout)
            calls = log_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(
                [
                    f"materialize --authority-current {authority_env['CHUMMER_RELEASE_AUTHORITY_CURRENT']} --registry-commit {'a' * 40} --expected-release-decision-status preview_ready --served-mirror https://chummer.run/downloads/RELEASE_CHANNEL.generated.json",
                    f"generator env:CHUMMER6_PUBLIC_GUIDE_SOURCE_ROOT={chummer6_root} CHUMMER6_GUIDE_ASSET_SOURCE={chummer6_root / 'assets'}",
                    f"generator --repo-root {design_root} --out {out_dir}",
                    f"sync --source {out_dir}",
                    f"verify env:CHUMMER_DESIGN_REPO_ROOT={design_root} --source {out_dir} --authority-current {authority_env['CHUMMER_RELEASE_AUTHORITY_CURRENT']} --registry-commit {'a' * 40} --expected-release-decision-status preview_ready --served-mirror https://chummer.run/downloads/RELEASE_CHANNEL.generated.json",
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
            authority_env = self._authority_env(root)

            completed = self.run_script(
                "--check",
                env={
                    "CHUMMER6_REPO_ROOT": str(chummer6_root),
                    "CHUMMER_DESIGN_REPO_ROOT": str(design_root),
                    "CHUMMER_PUBLIC_GUIDE_OUT": str(out_dir),
                    "CALL_LOG": str(log_path),
                    **authority_env,
                },
            )

            self.assertEqual(completed.returncode, 0, completed.stdout)
            calls = log_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(
                [
                    f"materialize --authority-current {authority_env['CHUMMER_RELEASE_AUTHORITY_CURRENT']} --registry-commit {'a' * 40} --expected-release-decision-status preview_ready --served-mirror https://chummer.run/downloads/RELEASE_CHANNEL.generated.json --check",
                    f"generator env:CHUMMER6_PUBLIC_GUIDE_SOURCE_ROOT={chummer6_root} CHUMMER6_GUIDE_ASSET_SOURCE={chummer6_root / 'assets'}",
                    f"generator --repo-root {design_root} --out {out_dir} --check",
                    f"sync --source {out_dir} --check",
                    f"verify env:CHUMMER_DESIGN_REPO_ROOT={design_root} --source {out_dir} --authority-current {authority_env['CHUMMER_RELEASE_AUTHORITY_CURRENT']} --registry-commit {'a' * 40} --expected-release-decision-status preview_ready --served-mirror https://chummer.run/downloads/RELEASE_CHANNEL.generated.json",
                ],
                calls,
            )

    def test_design_repo_option_recomputes_default_generator_and_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chummer6_root = root / "chummer6"
            design_root = root / "selected-design"
            out_dir = design_root / "products" / "chummer" / "public-guide"
            log_path = root / "calls.log"
            self._write_fake_scripts(chummer6_root, design_root)
            authority_env = self._authority_env(root)

            completed = self.run_script(
                "--design-repo",
                str(design_root),
                env={
                    "CHUMMER6_REPO_ROOT": str(chummer6_root),
                    "CHUMMER_DESIGN_REPO_ROOT": "",
                    "CHUMMER_PUBLIC_GUIDE_OUT": "",
                    "CHUMMER_PUBLIC_GUIDE_GENERATOR": "",
                    "CALL_LOG": str(log_path),
                    **authority_env,
                },
            )

            self.assertEqual(completed.returncode, 0, completed.stdout)
            calls = log_path.read_text(encoding="utf-8").splitlines()
            self.assertIn(f"generator --repo-root {design_root} --out {out_dir}", calls)
            self.assertIn(f"sync --source {out_dir}", calls)

    def test_missing_authority_fails_before_any_materialization_or_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chummer6_root = root / "chummer6"
            design_root = root / "chummer-design"
            log_path = root / "calls.log"
            self._write_fake_scripts(chummer6_root, design_root)

            completed = self.run_script(
                env={
                    "CHUMMER6_REPO_ROOT": str(chummer6_root),
                    "CHUMMER_DESIGN_REPO_ROOT": str(design_root),
                    "CALL_LOG": str(log_path),
                    "CHUMMER_RELEASE_AUTHORITY_CURRENT": "",
                    "CHUMMER_REGISTRY_COMMIT": "",
                    "CHUMMER_EXPECTED_RELEASE_DECISION_STATUS": "",
                }
            )

            self.assertEqual(completed.returncode, 2, completed.stdout)
            self.assertIn("Immutable release authority is mandatory", completed.stdout)
            self.assertFalse(log_path.exists())

    @staticmethod
    def _authority_env(root: Path) -> dict[str, str]:
        current = root / "CURRENT.json"
        current.write_text("{}\n", encoding="utf-8")
        return {
            "CHUMMER_RELEASE_AUTHORITY_CURRENT": str(current),
            "CHUMMER_REGISTRY_COMMIT": "a" * 40,
            "CHUMMER_EXPECTED_RELEASE_DECISION_STATUS": "preview_ready",
        }

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
                with open(os.environ["CALL_LOG"], "a", encoding="utf-8") as handle:
                    handle.write(
                        "generator env:CHUMMER6_PUBLIC_GUIDE_SOURCE_ROOT="
                        + os.environ.get("CHUMMER6_PUBLIC_GUIDE_SOURCE_ROOT", "")
                        + " CHUMMER6_GUIDE_ASSET_SOURCE="
                        + os.environ.get("CHUMMER6_GUIDE_ASSET_SOURCE", "")
                        + "\\n"
                    )
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
                import sys
                with open(os.environ["CALL_LOG"], "a", encoding="utf-8") as handle:
                    handle.write("materialize " + " ".join(sys.argv[1:]) + "\\n")
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
                printf 'verify env:CHUMMER_DESIGN_REPO_ROOT=%s %s\n' "${CHUMMER_DESIGN_REPO_ROOT:-}" "$*" >> "$CALL_LOG"
                """
            ),
            encoding="utf-8",
        )
        verify_script.chmod(0o755)


if __name__ == "__main__":
    unittest.main()
