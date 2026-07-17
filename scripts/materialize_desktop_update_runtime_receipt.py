#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RECEIPTS_ROOT = REPO_ROOT / ".guide-internal" / "receipts"
OUTPUT_PATH = RECEIPTS_ROOT / "DESKTOP_UPDATE_RUNTIME.generated.json"
DEFAULT_FILTER = "FullyQualifiedName~DesktopUpdateRuntimeTests"
DEFAULT_TIMEOUT_SECONDS = 900
TIMEOUT_EXIT_CODE = 124


def _resolve_desktop_repo_root() -> Path:
    explicit = os.environ.get("CHUMMER_DESKTOP_REPO_ROOT", "").strip()
    if explicit:
        return Path(explicit).resolve()
    for candidate_name in ("chummer-presentation", "chummer6-ui"):
        candidate = REPO_ROOT.parent / candidate_name
        if (candidate / "Chummer.Tests" / "Chummer.Tests.csproj").is_file():
            return candidate
    raise FileNotFoundError("Could not find a desktop presentation repository with Chummer.Tests/Chummer.Tests.csproj")


def _display_path(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base)).replace("\\", "/")
    except ValueError:
        return str(path)


def _coerce_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _run_command(
    command: list[str],
    cwd: Path,
    timeout_seconds: int,
) -> tuple[subprocess.CompletedProcess[str], bool]:
    try:
        return (
            subprocess.run(
                command,
                cwd=cwd,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=timeout_seconds,
                check=False,
            ),
            False,
        )
    except subprocess.TimeoutExpired as exc:
        return (
            subprocess.CompletedProcess(
                command,
                TIMEOUT_EXIT_CODE,
                stdout=_coerce_output(exc.output),
            ),
            True,
        )


def _summarize_output(output: str) -> list[str]:
    lines: list[str] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if (
            "Passed!" in line
            or "Failed!" in line
            or "Total tests:" in line
            or "total:" in line
            or "error" in line.lower()
        ):
            lines.append(line)
    return lines[-12:]


def main() -> int:
    desktop_repo_root = _resolve_desktop_repo_root()
    test_project_path = desktop_repo_root / "Chummer.Tests" / "Chummer.Tests.csproj"
    package_plane_helper_path = desktop_repo_root / "scripts" / "ai" / "with-package-plane.sh"
    filter_value = os.environ.get("CHUMMER_DESKTOP_UPDATE_RUNTIME_FILTER", DEFAULT_FILTER).strip() or DEFAULT_FILTER
    timeout_seconds = int(os.environ.get("CHUMMER_DESKTOP_UPDATE_RUNTIME_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)).strip())
    prebuild_commands: list[dict[str, object]] = []
    prereq_projects = [
        REPO_ROOT.parent / "chummer-hub-registry" / "Chummer.Hub.Registry.Contracts" / "Chummer.Hub.Registry.Contracts.csproj",
        REPO_ROOT.parent / "chummer.run-services" / "Chummer.Run.Contracts" / "Chummer.Run.Contracts.csproj",
        REPO_ROOT.parent / "fleet" / "repos" / "chummer-media-factory" / "src" / "Chummer.Media.Contracts" / "Chummer.Media.Contracts.csproj",
    ]
    for prereq_project_path in prereq_projects:
        if not prereq_project_path.is_file():
            continue
        prereq_command = [
            "bash",
            str(package_plane_helper_path),
            "build",
            str(prereq_project_path),
            "--nologo",
            "-m:1",
        ]
        prereq_result, prereq_timed_out = _run_command(prereq_command, desktop_repo_root, timeout_seconds)
        prebuild_commands.append(
            {
                "project": str(prereq_project_path),
                "command": prereq_command,
                "exit_code": prereq_result.returncode,
                "timed_out": prereq_timed_out,
                "summary_lines": _summarize_output(prereq_result.stdout or ""),
            }
        )
        if prereq_result.returncode != 0:
            output = {
                "contract_name": "ea.chummer6_desktop_update_runtime.v1",
                "status": "failed",
                "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "desktop_repo_root": str(desktop_repo_root),
                "tested_repo_name": desktop_repo_root.name,
                "generated_from": [
                    _display_path(test_project_path, desktop_repo_root),
                    _display_path(desktop_repo_root / "Chummer.Tests" / "DesktopUpdateRuntimeTests.cs", desktop_repo_root),
                ],
                "prebuild_commands": prebuild_commands,
                "command": [],
                "timeout_seconds": timeout_seconds,
                "timed_out": prereq_timed_out,
                "run_desktop_update_tests_only": True,
                "filter": filter_value,
                "result": {
                    "exit_code": prereq_result.returncode,
                    "timed_out": prereq_timed_out,
                    "summary_lines": _summarize_output(prereq_result.stdout or ""),
                    "mentions_passed_banner": False,
                    "mentions_desktop_update_runtime_tests": False,
                    "mentions_total": False,
                    "failure_stage": "prebuild",
                },
            }
            OUTPUT_PATH.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print("desktop_update_runtime:failed")
            return 1
    command = [
        "dotnet",
        "test",
        "--project",
        str(test_project_path),
        "-p:RunDesktopUpdateRuntimeTestsOnly=true",
        "--filter",
        filter_value,
        "-v",
        "minimal",
    ]
    completed, test_timed_out = _run_command(command, desktop_repo_root, timeout_seconds)
    output_text = completed.stdout or ""
    passed = completed.returncode == 0 and not test_timed_out
    output = {
        "contract_name": "ea.chummer6_desktop_update_runtime.v1",
        "status": "passed" if passed else "failed",
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "desktop_repo_root": str(desktop_repo_root),
        "tested_repo_name": desktop_repo_root.name,
        "generated_from": [
            _display_path(test_project_path, desktop_repo_root),
            _display_path(desktop_repo_root / "Chummer.Tests" / "DesktopUpdateRuntimeTests.cs", desktop_repo_root),
        ],
        "prebuild_commands": prebuild_commands,
        "command": command,
        "timeout_seconds": timeout_seconds,
        "timed_out": test_timed_out,
        "run_desktop_update_tests_only": True,
        "filter": filter_value,
        "result": {
            "exit_code": completed.returncode,
            "timed_out": test_timed_out,
            "summary_lines": _summarize_output(output_text),
            "mentions_passed_banner": "Passed!" in output_text,
            "mentions_desktop_update_runtime_tests": "DesktopUpdateRuntimeTests" in output_text or filter_value == DEFAULT_FILTER,
            "mentions_total": bool(re.search(r"\btotal:\s*\d+", output_text, flags=re.IGNORECASE)),
        },
    }
    OUTPUT_PATH.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("desktop_update_runtime:ok" if passed else "desktop_update_runtime:failed")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
