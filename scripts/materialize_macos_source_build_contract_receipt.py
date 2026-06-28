#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DESIGN_ROOT = REPO_ROOT.parent / "chummer-design"
RECEIPTS_ROOT = REPO_ROOT / ".guide-internal" / "receipts"
OUTPUT_PATH = RECEIPTS_ROOT / "MACOS_SOURCE_BUILD_CONTRACT.generated.json"
DEFAULT_TIMEOUT_SECONDS = 120

BUILD_SCRIPT_PATH = REPO_ROOT / "scripts" / "build-chummer6-macos-local.sh"
AUDIT_SCRIPT_PATH = REPO_ROOT / "scripts" / "check-host-chummer6-macos-local.sh"
INSTALL_SCRIPT_PATH = REPO_ROOT / "scripts" / "install-chummer6-macos-local.sh"
DOC_PATH = REPO_ROOT / "SOURCE_BUILD_MACOS.md"
DOWNLOAD_PATH = REPO_ROOT / "DOWNLOAD.md"
TEST_PATH = REPO_ROOT / "tests" / "test_macos_source_build_script.py"
MAINTENANCE_POLICY_PATH = DESIGN_ROOT / "products" / "chummer" / "maintenance" / "MAC_SOURCE_BUILD_PATH.md"


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT.parent)).replace("\\", "/")
    except ValueError:
        return str(path)


def _run_command(command: list[str], timeout_seconds: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout_seconds,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )


def _summary_lines(output: str) -> list[str]:
    lines: list[str] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if (
            "Ran " in line
            or line == "OK"
            or "FAILED" in line
            or "Traceback" in line
            or "AssertionError" in line
            or "This script builds only on macOS." in line
        ):
            lines.append(line)
    return lines[-12:]


def main() -> int:
    timeout_seconds = int(os.environ.get("CHUMMER_MACOS_SOURCE_BUILD_CONTRACT_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)).strip())
    maintenance_policy = MAINTENANCE_POLICY_PATH.read_text(encoding="utf-8")
    doc_text = DOC_PATH.read_text(encoding="utf-8")
    build_script_text = BUILD_SCRIPT_PATH.read_text(encoding="utf-8")
    install_script_text = INSTALL_SCRIPT_PATH.read_text(encoding="utf-8")

    syntax_results: list[dict[str, object]] = []
    for path in (BUILD_SCRIPT_PATH, AUDIT_SCRIPT_PATH, INSTALL_SCRIPT_PATH):
        command = ["bash", "-n", str(path)]
        completed = _run_command(command, timeout_seconds)
        syntax_results.append(
            {
                "path": _display_path(path),
                "command": command,
                "exit_code": completed.returncode,
                "summary_lines": _summary_lines(completed.stdout or ""),
            }
        )
        if completed.returncode != 0:
            output = {
                "contract_name": "ea.chummer6_macos_source_build_contract.v1",
                "status": "failed",
                "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "scope": "script_contract_only",
                "runtime_coverage": "not_run_on_non_macos_host",
                "real_macos_runtime_proof_required": True,
                "generated_from": [
                    _display_path(BUILD_SCRIPT_PATH),
                    _display_path(AUDIT_SCRIPT_PATH),
                    _display_path(INSTALL_SCRIPT_PATH),
                    _display_path(DOC_PATH),
                    _display_path(DOWNLOAD_PATH),
                    _display_path(TEST_PATH),
                    _display_path(MAINTENANCE_POLICY_PATH),
                ],
                "syntax_checks": syntax_results,
                "unit_test": {
                    "command": [],
                    "exit_code": None,
                    "summary_lines": [],
                },
                "policy": {
                    "maintenance_policy_marks_real_build_as_macos_only": "A real binary build still has to happen on a Mac host." in maintenance_policy,
                    "maintenance_policy_requires_two_step_install": "split into a build step and a separate install step" in maintenance_policy,
                    "build_launcher_resolves_symlinks": 'while [[ -L "$SOURCE" ]]' in build_script_text,
                    "install_launcher_resolves_symlinks": 'while [[ -L "$SOURCE" ]]' in install_script_text,
                    "doc_marks_local_personal_build": "This is a local personal source build" in doc_text,
                },
            }
            OUTPUT_PATH.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print("macos_source_build_contract:failed")
            return 1

    test_command = ["python3", "-m", "unittest", "tests/test_macos_source_build_script.py", "-q"]
    test_completed = _run_command(test_command, timeout_seconds)
    passed = test_completed.returncode == 0

    output = {
        "contract_name": "ea.chummer6_macos_source_build_contract.v1",
        "status": "passed" if passed else "failed",
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scope": "script_contract_only",
        "runtime_coverage": "not_run_on_non_macos_host",
        "real_macos_runtime_proof_required": True,
        "generated_from": [
            _display_path(BUILD_SCRIPT_PATH),
            _display_path(AUDIT_SCRIPT_PATH),
            _display_path(INSTALL_SCRIPT_PATH),
            _display_path(DOC_PATH),
            _display_path(DOWNLOAD_PATH),
            _display_path(TEST_PATH),
            _display_path(MAINTENANCE_POLICY_PATH),
        ],
        "syntax_checks": syntax_results,
        "unit_test": {
            "command": test_command,
            "exit_code": test_completed.returncode,
            "summary_lines": _summary_lines(test_completed.stdout or ""),
        },
        "policy": {
            "maintenance_policy_marks_real_build_as_macos_only": "A real binary build still has to happen on a Mac host." in maintenance_policy,
            "maintenance_policy_requires_two_step_install": "split into a build step and a separate install step" in maintenance_policy,
            "maintenance_policy_requires_notify_default": "notify-only for auto-update by default" in maintenance_policy,
            "maintenance_policy_requires_analytics_off_default": "analytics-off by default" in maintenance_policy,
            "build_launcher_resolves_symlinks": 'while [[ -L "$SOURCE" ]]' in build_script_text,
            "install_launcher_resolves_symlinks": 'while [[ -L "$SOURCE" ]]' in install_script_text,
            "doc_marks_local_personal_build": "This is a local personal source build" in doc_text,
            "doc_marks_not_public_release": "not an official macOS release" in doc_text,
            "doc_marks_second_script_install": "The binary is installed by a second script on purpose." in doc_text,
        },
    }
    OUTPUT_PATH.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("macos_source_build_contract:ok" if passed else "macos_source_build_contract:failed")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
