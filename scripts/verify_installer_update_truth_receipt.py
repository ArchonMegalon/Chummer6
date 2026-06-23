#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RECEIPT_PATH = REPO_ROOT / ".guide-internal" / "receipts" / "INSTALLER_UPDATE_TRUTH.generated.json"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> int:
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    _require(receipt.get("contract_name") == "ea.chummer6_installer_update_truth.v1", "unexpected contract_name")
    _require(receipt.get("status") == "passed", "installer/update truth receipt is not passed")
    generated_at = str(receipt.get("generated_at_utc") or "").strip()
    _require(bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", generated_at)), "generated_at_utc must be ISO UTC")

    generated_from = receipt.get("generated_from")
    _require(isinstance(generated_from, list) and len(generated_from) == 5, "generated_from must list the source files")

    policy = receipt.get("policy")
    _require(isinstance(policy, dict), "policy block missing")
    _require(policy.get("update_modes") == ["full", "notify", "off"], "update_modes must be full/notify/off")
    _require(policy.get("installer_first_platforms") == ["Windows", "Linux"], "installer_first_platforms must be Windows/Linux")
    _require(str(policy.get("packaged_default_mode") or "").strip() == "full", "packaged_default_mode must be full")
    _require(str(policy.get("linked_account_default_mode") or "").strip() == "full", "linked_account_default_mode must be full")
    _require(str(policy.get("source_build_default_mode") or "").strip() == "notify", "source_build_default_mode must be notify")
    for key in (
        "public_policy_mentions_modes",
        "desktop_system_mentions_exact_modes",
        "desktop_system_mentions_packaged_full_default",
        "desktop_system_mentions_linked_account_full_default",
        "desktop_system_mentions_source_build_notify_default",
        "source_build_doc_mentions_notify_default",
        "source_build_doc_mentions_launcher_override",
        "source_build_script_sets_notify_default",
    ):
        _require(policy.get(key) is True, f"{key} must be true")

    release_truth = receipt.get("release_truth")
    _require(isinstance(release_truth, dict), "release_truth block missing")
    _require(str(release_truth.get("public_download_authority") or "").strip() == "https://chummer.run/downloads", "public download authority mismatch")
    _require(isinstance(release_truth.get("available_platforms"), list), "available_platforms missing")

    coherence = receipt.get("coherence")
    _require(isinstance(coherence, dict), "coherence block missing")
    for key in (
        "source_build_default_matches_policy",
        "release_packet_matches_installer_first_platforms",
        "public_download_authority_is_chummer_run",
    ):
        _require(coherence.get(key) is True, f"{key} must be true")

    print("installer_update_truth_receipt:ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
