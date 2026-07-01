from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RELEASE_VERIFY_SCRIPT = REPO_ROOT / "scripts" / "release" / "verify_guide_convergence.sh"


def _write_shell_stub(
    path: Path,
    *,
    step_name: str,
    creates_receipt: str | None = None,
    requires_receipts: list[str] | None = None,
    exit_code: int = 0,
) -> None:
    requires_receipts = requires_receipts or []
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        'root="${CHUMMER_TEST_RELEASE_WRAPPER_ROOT:?}"',
        'log_path="${CHUMMER_TEST_RELEASE_WRAPPER_LOG:?}"',
        f"printf '%s\\n' '{step_name}' >> \"$log_path\"",
    ]
    lines.extend(
        f'test -f "$root/.guide-internal/receipts/{receipt_name}"'
        for receipt_name in requires_receipts
    )
    if creates_receipt is not None:
        lines.extend(
            [
                'mkdir -p "$root/.guide-internal/receipts"',
                f'cat <<\'JSON\' > "$root/.guide-internal/receipts/{creates_receipt}"',
                '{"status":"passed"}',
                "JSON",
            ]
        )
    lines.append(f"exit {exit_code}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    path.chmod(0o755)


def _write_python_stub(
    path: Path,
    *,
    step_name: str,
    creates_receipt: str | None = None,
    requires_receipts: list[str] | None = None,
    exit_code: int = 0,
) -> None:
    requires_receipts = requires_receipts or []
    lines = [
        "#!/usr/bin/env python3",
        "from __future__ import annotations",
        "",
        "import os",
        "from pathlib import Path",
        "",
        'root = Path(os.environ["CHUMMER_TEST_RELEASE_WRAPPER_ROOT"])',
        'log_path = Path(os.environ["CHUMMER_TEST_RELEASE_WRAPPER_LOG"])',
        'receipts_root = root / ".guide-internal" / "receipts"',
        'with log_path.open("a", encoding="utf-8") as handle:',
        f'    handle.write("{step_name}\\n")',
    ]
    lines.extend(
        f'assert (receipts_root / "{receipt_name}").is_file(), "{receipt_name} missing"'
        for receipt_name in requires_receipts
    )
    if creates_receipt is not None:
        lines.extend(
            [
                "receipts_root.mkdir(parents=True, exist_ok=True)",
                f'(receipts_root / "{creates_receipt}").write_text(\'{{"status":"passed"}}\\\\n\', encoding="utf-8")',
            ]
        )
    lines.append(f"raise SystemExit({exit_code})")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    path.chmod(0o755)


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
        macos_contract_test_line = 'python3 "$repo_root/scripts/test_macos_source_build_contract_receipt.py" >/dev/null'
        macos_contract_materialize_line = 'python3 "$repo_root/scripts/materialize_macos_source_build_contract_receipt.py" >/dev/null'
        macos_contract_verify_line = 'python3 "$repo_root/scripts/verify_macos_source_build_contract_receipt.py" >/dev/null'
        release_truth_materialize_line = 'python3 "$repo_root/scripts/materialize_public_release_truth_packet.py" >/dev/null'
        installer_update_test_line = 'python3 "$repo_root/scripts/test_installer_update_truth_receipt.py" >/dev/null'
        installer_update_materialize_line = 'python3 "$repo_root/scripts/materialize_installer_update_truth_receipt.py" >/dev/null'
        installer_update_verify_line = 'python3 "$repo_root/scripts/verify_installer_update_truth_receipt.py" >/dev/null'
        desktop_update_test_line = 'python3 "$repo_root/scripts/test_desktop_update_runtime_receipt.py" >/dev/null'
        desktop_update_materialize_line = 'python3 "$repo_root/scripts/materialize_desktop_update_runtime_receipt.py" >/dev/null'
        desktop_update_verify_line = 'python3 "$repo_root/scripts/verify_desktop_update_runtime_receipt.py" >/dev/null'
        convergence_test_line = 'python3 "$repo_root/scripts/test_release_verification_receipt.py" >/dev/null'
        convergence_materialize_line = 'python3 "$repo_root/scripts/materialize_release_verification_receipt.py" >/dev/null'
        convergence_verify_line = 'python3 "$repo_root/scripts/verify_release_verification_receipt.py" >/dev/null'

        self.assertIn('repo_root="${CHUMMER6_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"', script_text)
        self.assertIn(docker_line, script_text)
        self.assertIn(receipt_test_line, script_text)
        self.assertIn(receipt_verify_line, script_text)
        self.assertIn(guide_line, script_text)
        self.assertIn(macos_contract_test_line, script_text)
        self.assertIn(macos_contract_materialize_line, script_text)
        self.assertIn(macos_contract_verify_line, script_text)
        self.assertIn(release_truth_materialize_line, script_text)
        self.assertIn(installer_update_test_line, script_text)
        self.assertIn(installer_update_materialize_line, script_text)
        self.assertIn(installer_update_verify_line, script_text)
        self.assertIn(desktop_update_test_line, script_text)
        self.assertIn(desktop_update_materialize_line, script_text)
        self.assertIn(desktop_update_verify_line, script_text)
        self.assertIn(convergence_test_line, script_text)
        self.assertIn(convergence_materialize_line, script_text)
        self.assertIn(convergence_verify_line, script_text)
        self.assertLess(script_text.index(docker_line), script_text.index(guide_line))
        self.assertLess(script_text.index(docker_line), script_text.index(receipt_test_line))
        self.assertLess(script_text.index(receipt_test_line), script_text.index(receipt_verify_line))
        self.assertLess(script_text.index(receipt_verify_line), script_text.index(macos_contract_test_line))
        self.assertLess(script_text.index(macos_contract_test_line), script_text.index(macos_contract_materialize_line))
        self.assertLess(script_text.index(macos_contract_materialize_line), script_text.index(macos_contract_verify_line))
        self.assertLess(script_text.index(macos_contract_verify_line), script_text.index(release_truth_materialize_line))
        self.assertLess(script_text.index(release_truth_materialize_line), script_text.index(guide_line))
        self.assertLess(script_text.index(guide_line), script_text.index(installer_update_test_line))
        self.assertLess(script_text.index(installer_update_test_line), script_text.index(installer_update_materialize_line))
        self.assertLess(script_text.index(installer_update_materialize_line), script_text.index(installer_update_verify_line))
        self.assertLess(script_text.index(installer_update_verify_line), script_text.index(desktop_update_test_line))
        self.assertLess(script_text.index(desktop_update_test_line), script_text.index(desktop_update_materialize_line))
        self.assertLess(script_text.index(desktop_update_materialize_line), script_text.index(desktop_update_verify_line))
        self.assertLess(script_text.index(desktop_update_verify_line), script_text.index(convergence_test_line))
        self.assertLess(script_text.index(convergence_test_line), script_text.index(convergence_materialize_line))
        self.assertLess(script_text.index(convergence_materialize_line), script_text.index(convergence_verify_line))
        self.assertIn("LINUX_SOURCE_BUILD_DOCKER_GATE.generated.json", (REPO_ROOT / "scripts" / "verify_linux_source_build_docker_gate.sh").read_text(encoding="utf-8"))

    def test_release_wrapper_executes_gate_steps_in_contract_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_root = Path(temp_dir)
            log_path = fake_root / "release-wrapper.log"
            receipts_root = fake_root / ".guide-internal" / "receipts"
            receipts_root.mkdir(parents=True, exist_ok=True)

            _write_shell_stub(
                fake_root / "scripts" / "verify_linux_source_build_docker_gate.sh",
                step_name="docker_gate",
                creates_receipt="LINUX_SOURCE_BUILD_DOCKER_GATE.generated.json",
            )
            _write_python_stub(
                fake_root / "scripts" / "test_verify_linux_source_build_docker_gate_receipt.py",
                step_name="test_linux_gate_receipt",
                requires_receipts=["LINUX_SOURCE_BUILD_DOCKER_GATE.generated.json"],
            )
            _write_python_stub(
                fake_root / "scripts" / "verify_linux_source_build_docker_gate_receipt.py",
                step_name="verify_linux_gate_receipt",
                requires_receipts=["LINUX_SOURCE_BUILD_DOCKER_GATE.generated.json"],
            )
            _write_shell_stub(
                fake_root / "scripts" / "verify_public_guide.sh",
                step_name="verify_public_guide",
                requires_receipts=[
                    "LINUX_SOURCE_BUILD_DOCKER_GATE.generated.json",
                    "MACOS_SOURCE_BUILD_CONTRACT.generated.json",
                    "CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json",
                ],
            )
            _write_python_stub(
                fake_root / "scripts" / "test_macos_source_build_contract_receipt.py",
                step_name="test_macos_source_build_contract",
                requires_receipts=["LINUX_SOURCE_BUILD_DOCKER_GATE.generated.json"],
            )
            _write_python_stub(
                fake_root / "scripts" / "materialize_macos_source_build_contract_receipt.py",
                step_name="materialize_macos_source_build_contract",
                creates_receipt="MACOS_SOURCE_BUILD_CONTRACT.generated.json",
                requires_receipts=["LINUX_SOURCE_BUILD_DOCKER_GATE.generated.json"],
            )
            _write_python_stub(
                fake_root / "scripts" / "verify_macos_source_build_contract_receipt.py",
                step_name="verify_macos_source_build_contract",
                requires_receipts=["MACOS_SOURCE_BUILD_CONTRACT.generated.json"],
            )
            _write_python_stub(
                fake_root / "scripts" / "materialize_public_release_truth_packet.py",
                step_name="materialize_public_release_truth_packet",
                creates_receipt="CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json",
                requires_receipts=[
                    "LINUX_SOURCE_BUILD_DOCKER_GATE.generated.json",
                    "MACOS_SOURCE_BUILD_CONTRACT.generated.json",
                ],
            )
            _write_python_stub(
                fake_root / "scripts" / "test_installer_update_truth_receipt.py",
                step_name="test_installer_update_truth",
                requires_receipts=["CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json", "MACOS_SOURCE_BUILD_CONTRACT.generated.json"],
            )
            _write_python_stub(
                fake_root / "scripts" / "materialize_installer_update_truth_receipt.py",
                step_name="materialize_installer_update_truth",
                creates_receipt="INSTALLER_UPDATE_TRUTH.generated.json",
                requires_receipts=["CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json"],
            )
            _write_python_stub(
                fake_root / "scripts" / "verify_installer_update_truth_receipt.py",
                step_name="verify_installer_update_truth",
                requires_receipts=["INSTALLER_UPDATE_TRUTH.generated.json"],
            )
            _write_python_stub(
                fake_root / "scripts" / "test_desktop_update_runtime_receipt.py",
                step_name="test_desktop_update_runtime",
                requires_receipts=["INSTALLER_UPDATE_TRUTH.generated.json"],
            )
            _write_python_stub(
                fake_root / "scripts" / "materialize_desktop_update_runtime_receipt.py",
                step_name="materialize_desktop_update_runtime",
                creates_receipt="DESKTOP_UPDATE_RUNTIME.generated.json",
                requires_receipts=["INSTALLER_UPDATE_TRUTH.generated.json"],
            )
            _write_python_stub(
                fake_root / "scripts" / "verify_desktop_update_runtime_receipt.py",
                step_name="verify_desktop_update_runtime",
                requires_receipts=["DESKTOP_UPDATE_RUNTIME.generated.json"],
            )
            _write_python_stub(
                fake_root / "scripts" / "test_release_verification_receipt.py",
                step_name="test_release_verification_convergence",
                requires_receipts=[
                    "MACOS_SOURCE_BUILD_CONTRACT.generated.json",
                    "LINUX_SOURCE_BUILD_DOCKER_GATE.generated.json",
                    "CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json",
                    "INSTALLER_UPDATE_TRUTH.generated.json",
                    "DESKTOP_UPDATE_RUNTIME.generated.json",
                ],
            )
            _write_python_stub(
                fake_root / "scripts" / "materialize_release_verification_receipt.py",
                step_name="materialize_release_verification_convergence",
                creates_receipt="RELEASE_VERIFICATION_CONVERGENCE.generated.json",
                requires_receipts=[
                    "MACOS_SOURCE_BUILD_CONTRACT.generated.json",
                    "LINUX_SOURCE_BUILD_DOCKER_GATE.generated.json",
                    "CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json",
                    "INSTALLER_UPDATE_TRUTH.generated.json",
                    "DESKTOP_UPDATE_RUNTIME.generated.json",
                ],
            )
            _write_python_stub(
                fake_root / "scripts" / "verify_release_verification_receipt.py",
                step_name="verify_release_verification_convergence",
                requires_receipts=["RELEASE_VERIFICATION_CONVERGENCE.generated.json"],
            )

            completed = subprocess.run(
                ["bash", str(RELEASE_VERIFY_SCRIPT)],
                cwd=REPO_ROOT,
                env={
                    **os.environ,
                    "CHUMMER6_REPO_ROOT": str(fake_root),
                    "CHUMMER_TEST_RELEASE_WRAPPER_ROOT": str(fake_root),
                    "CHUMMER_TEST_RELEASE_WRAPPER_LOG": str(log_path),
                },
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=30,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stdout)
            self.assertTrue((receipts_root / "RELEASE_VERIFICATION_CONVERGENCE.generated.json").is_file())
            self.assertEqual(
                log_path.read_text(encoding="utf-8").splitlines(),
                [
                    "docker_gate",
                    "test_linux_gate_receipt",
                    "verify_linux_gate_receipt",
                    "test_macos_source_build_contract",
                    "materialize_macos_source_build_contract",
                    "verify_macos_source_build_contract",
                    "materialize_public_release_truth_packet",
                    "verify_public_guide",
                    "test_installer_update_truth",
                    "materialize_installer_update_truth",
                    "verify_installer_update_truth",
                    "test_desktop_update_runtime",
                    "materialize_desktop_update_runtime",
                    "verify_desktop_update_runtime",
                    "test_release_verification_convergence",
                    "materialize_release_verification_convergence",
                    "verify_release_verification_convergence",
                ],
            )

    def test_release_wrapper_stops_on_failed_step(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_root = Path(temp_dir)
            log_path = fake_root / "release-wrapper.log"

            _write_shell_stub(
                fake_root / "scripts" / "verify_linux_source_build_docker_gate.sh",
                step_name="docker_gate",
                creates_receipt="LINUX_SOURCE_BUILD_DOCKER_GATE.generated.json",
            )
            _write_python_stub(
                fake_root / "scripts" / "test_verify_linux_source_build_docker_gate_receipt.py",
                step_name="test_linux_gate_receipt",
                requires_receipts=["LINUX_SOURCE_BUILD_DOCKER_GATE.generated.json"],
            )
            _write_python_stub(
                fake_root / "scripts" / "verify_linux_source_build_docker_gate_receipt.py",
                step_name="verify_linux_gate_receipt",
                exit_code=23,
                requires_receipts=["LINUX_SOURCE_BUILD_DOCKER_GATE.generated.json"],
            )
            _write_shell_stub(
                fake_root / "scripts" / "verify_public_guide.sh",
                step_name="verify_public_guide",
            )

            completed = subprocess.run(
                ["bash", str(RELEASE_VERIFY_SCRIPT)],
                cwd=REPO_ROOT,
                env={
                    **os.environ,
                    "CHUMMER6_REPO_ROOT": str(fake_root),
                    "CHUMMER_TEST_RELEASE_WRAPPER_ROOT": str(fake_root),
                    "CHUMMER_TEST_RELEASE_WRAPPER_LOG": str(log_path),
                },
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=30,
                check=False,
            )

            self.assertEqual(completed.returncode, 23, completed.stdout)
            self.assertEqual(
                log_path.read_text(encoding="utf-8").splitlines(),
                [
                    "docker_gate",
                    "test_linux_gate_receipt",
                    "verify_linux_gate_receipt",
                ],
            )


if __name__ == "__main__":
    unittest.main()
