#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RECEIPT_PATH = REPO_ROOT / ".guide-internal" / "receipts" / "MACOS_SOURCE_BUILD_CONTRACT.generated.json"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> int:
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    _require(receipt.get("contract_name") == "ea.chummer6_macos_source_build_contract.v1", "unexpected contract_name")
    _require(receipt.get("status") == "passed", "macos_source_build_contract receipt is not passed")
    generated_at = str(receipt.get("generated_at_utc") or "").strip()
    _require(bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", generated_at)), "generated_at_utc must be ISO UTC")
    _require(str(receipt.get("scope") or "").strip() == "script_contract_only", "scope must stay bounded to script_contract_only")
    _require(str(receipt.get("runtime_coverage") or "").strip() == "not_run_on_non_macos_host", "runtime_coverage must remain bounded")
    _require(receipt.get("real_macos_runtime_proof_required") is True, "real_macos_runtime_proof_required must stay true")

    generated_from = receipt.get("generated_from")
    _require(isinstance(generated_from, list) and len(generated_from) == 7, "generated_from must list script/doc/test sources")

    syntax_checks = receipt.get("syntax_checks")
    _require(isinstance(syntax_checks, list) and len(syntax_checks) == 3, "syntax_checks must cover build/audit/install")
    for syntax_check in syntax_checks:
        _require(isinstance(syntax_check, dict), "syntax_check entries must be objects")
        _require(syntax_check.get("exit_code") == 0, "syntax checks must pass")
        command = syntax_check.get("command")
        _require(isinstance(command, list) and command[:2] == ["bash", "-n"], "syntax checks must run bash -n")
        _require(str(syntax_check.get("path") or "").strip(), "syntax check path missing")

    unit_test = receipt.get("unit_test")
    _require(isinstance(unit_test, dict), "unit_test block missing")
    _require(unit_test.get("exit_code") == 0, "unit_test must pass")
    command = unit_test.get("command")
    _require(isinstance(command, list) and command[:3] == ["python3", "-m", "unittest"], "unit_test command must run unittest")
    _require("tests/test_macos_source_build_script.py" in command, "unit_test must target test_macos_source_build_script.py")

    policy = receipt.get("policy")
    _require(isinstance(policy, dict), "policy block missing")
    for key in (
        "maintenance_policy_marks_real_build_as_macos_only",
        "maintenance_policy_requires_two_step_install",
        "maintenance_policy_requires_notify_default",
        "maintenance_policy_requires_analytics_off_default",
        "build_launcher_resolves_symlinks",
        "install_launcher_resolves_symlinks",
        "doc_marks_local_personal_build",
        "doc_marks_not_public_release",
        "doc_marks_second_script_install",
    ):
        _require(policy.get(key) is True, f"{key} must be true")

    print("macos_source_build_contract_receipt:ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
