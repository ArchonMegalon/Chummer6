#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RECEIPT_PATH = REPO_ROOT / ".guide-internal" / "receipts" / "DESKTOP_UPDATE_RUNTIME.generated.json"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> int:
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    _require(receipt.get("contract_name") == "ea.chummer6_desktop_update_runtime.v1", "unexpected contract_name")
    _require(receipt.get("status") == "passed", "desktop_update_runtime receipt is not passed")
    generated_at = str(receipt.get("generated_at_utc") or "").strip()
    _require(bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", generated_at)), "generated_at_utc must be ISO UTC")

    tested_repo_name = str(receipt.get("tested_repo_name") or "").strip()
    _require(tested_repo_name in {"chummer-presentation", "chummer6-ui"}, "tested_repo_name must be a known desktop repo")

    generated_from = receipt.get("generated_from")
    _require(isinstance(generated_from, list) and len(generated_from) == 2, "generated_from must list the updater test project and runtime test file")

    prebuild_commands = receipt.get("prebuild_commands")
    _require(isinstance(prebuild_commands, list), "prebuild_commands must be recorded")
    for prebuild_command in prebuild_commands:
        _require(isinstance(prebuild_command, dict), "prebuild command entries must be objects")
        _require(prebuild_command.get("exit_code") == 0, "prebuild commands must succeed")
        prebuild_command_line = prebuild_command.get("command")
        _require(isinstance(prebuild_command_line, list) and len(prebuild_command_line) >= 5, "prebuild command must be recorded")
        _require(prebuild_command_line[0] == "bash", "prebuild command must run through bash")
        _require("with-package-plane.sh" in prebuild_command_line[1], "prebuild command must use with-package-plane.sh")
        _require(prebuild_command_line[2] == "build", "prebuild command must build a compatibility project")

    command = receipt.get("command")
    _require(isinstance(command, list) and len(command) >= 8, "command must be recorded")
    _require(command[0] == "dotnet" and command[1] == "test", "command must run dotnet test")
    _require("--project" in command, "command must specify the test project")
    _require(
        "-p:RunDesktopUpdateRuntimeTestsOnly=true" in command,
        "command must run the isolated desktop update runtime test lane",
    )
    _require("--filter" in command, "command must include a test filter")
    _require("FullyQualifiedName~DesktopUpdateRuntimeTests" in command, "command must target DesktopUpdateRuntimeTests")

    timeout_seconds = receipt.get("timeout_seconds")
    _require(isinstance(timeout_seconds, int) and timeout_seconds >= 60, "timeout_seconds must be a sane integer timeout")
    _require(receipt.get("timed_out") is False, "desktop update runtime test must not time out")
    _require(receipt.get("run_desktop_update_tests_only") is True, "run_desktop_update_tests_only must be true")
    _require(str(receipt.get("filter") or "").strip() == "FullyQualifiedName~DesktopUpdateRuntimeTests", "filter mismatch")

    result = receipt.get("result")
    _require(isinstance(result, dict), "result block missing")
    _require(result.get("timed_out") is False, "desktop update runtime result must not be timed out")
    _require(result.get("exit_code") == 0, "desktop update runtime test exit_code must be zero")
    _require(result.get("mentions_passed_banner") is True, "desktop update runtime test must emit a Passed banner")
    _require(result.get("mentions_desktop_update_runtime_tests") is True, "desktop update runtime test must mention DesktopUpdateRuntimeTests")
    _require(result.get("mentions_total") is True, "desktop update runtime test must report total counts")
    summary_lines = result.get("summary_lines")
    _require(isinstance(summary_lines, list) and len(summary_lines) > 0, "summary_lines must capture the dotnet test summary")

    print("desktop_update_runtime_receipt:ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
