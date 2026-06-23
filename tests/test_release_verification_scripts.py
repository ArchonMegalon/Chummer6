from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RELEASE_VERIFY_SCRIPT = REPO_ROOT / "scripts" / "release" / "verify_guide_convergence.sh"


class ReleaseVerificationScriptTests(unittest.TestCase):
    def test_release_wrapper_has_valid_bash_syntax(self) -> None:
        completed = subprocess.run(
            ["bash", "-n", str(RELEASE_VERIFY_SCRIPT)],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout)

    def test_release_wrapper_runs_docker_gate_before_public_guide_verification(self) -> None:
        script_text = RELEASE_VERIFY_SCRIPT.read_text(encoding="utf-8")
        docker_line = 'bash "$repo_root/scripts/verify_linux_source_build_docker_gate.sh"'
        receipt_test_line = 'python3 "$repo_root/scripts/test_verify_linux_source_build_docker_gate_receipt.py" >/dev/null'
        receipt_verify_line = 'python3 "$repo_root/scripts/verify_linux_source_build_docker_gate_receipt.py" >/dev/null'
        guide_line = 'bash "$repo_root/scripts/verify_public_guide.sh"'
        installer_update_test_line = 'python3 "$repo_root/scripts/test_installer_update_truth_receipt.py" >/dev/null'
        installer_update_materialize_line = 'python3 "$repo_root/scripts/materialize_installer_update_truth_receipt.py" >/dev/null'
        installer_update_verify_line = 'python3 "$repo_root/scripts/verify_installer_update_truth_receipt.py" >/dev/null'
        convergence_test_line = 'python3 "$repo_root/scripts/test_release_verification_receipt.py" >/dev/null'
        convergence_materialize_line = 'python3 "$repo_root/scripts/materialize_release_verification_receipt.py" >/dev/null'
        convergence_verify_line = 'python3 "$repo_root/scripts/verify_release_verification_receipt.py" >/dev/null'

        self.assertIn('repo_root="${CHUMMER6_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"', script_text)
        self.assertIn(docker_line, script_text)
        self.assertIn(receipt_test_line, script_text)
        self.assertIn(receipt_verify_line, script_text)
        self.assertIn(guide_line, script_text)
        self.assertIn(installer_update_test_line, script_text)
        self.assertIn(installer_update_materialize_line, script_text)
        self.assertIn(installer_update_verify_line, script_text)
        self.assertIn(convergence_test_line, script_text)
        self.assertIn(convergence_materialize_line, script_text)
        self.assertIn(convergence_verify_line, script_text)
        self.assertLess(script_text.index(docker_line), script_text.index(guide_line))
        self.assertLess(script_text.index(docker_line), script_text.index(receipt_test_line))
        self.assertLess(script_text.index(receipt_test_line), script_text.index(receipt_verify_line))
        self.assertLess(script_text.index(receipt_verify_line), script_text.index(guide_line))
        self.assertLess(script_text.index(guide_line), script_text.index(installer_update_test_line))
        self.assertLess(script_text.index(installer_update_test_line), script_text.index(installer_update_materialize_line))
        self.assertLess(script_text.index(installer_update_materialize_line), script_text.index(installer_update_verify_line))
        self.assertLess(script_text.index(installer_update_verify_line), script_text.index(convergence_test_line))
        self.assertLess(script_text.index(convergence_test_line), script_text.index(convergence_materialize_line))
        self.assertLess(script_text.index(convergence_materialize_line), script_text.index(convergence_verify_line))
        self.assertIn("LINUX_SOURCE_BUILD_DOCKER_GATE.generated.json", (REPO_ROOT / "scripts" / "verify_linux_source_build_docker_gate.sh").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
