#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKET_PATH = REPO_ROOT / ".guide-internal" / "receipts" / "CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json"
README_PATH = REPO_ROOT / "README.md"
STATUS_PATH = REPO_ROOT / "STATUS.md"
DOWNLOAD_PATH = REPO_ROOT / "DOWNLOAD.md"
MIGRATION_PATH = REPO_ROOT / "FROM_CHUMMER5A_TO_CHUMMER6.md"


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _require_contains(name: str, haystack: str, needle: str) -> None:
    if needle and needle not in haystack:
        raise ValueError(f"{name} is missing required release-status line: {needle!r}")


def main() -> int:
    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
    readme = _load_text(README_PATH)
    status = _load_text(STATUS_PATH)
    download = _load_text(DOWNLOAD_PATH)
    migration = _load_text(MIGRATION_PATH)

    _require_contains("README.md", readme, str(packet.get("shelf_truth_line") or ""))
    _require_contains("README.md", readme, str(packet.get("short_release_summary") or ""))
    _require_contains("README.md", readme, str(packet.get("desktop_pick_line") or ""))
    if "honest pitch" not in readme or "Start here if you just want the answer" not in readme:
        raise ValueError("README.md lost the human first-answer framing")

    linux_source_build_gate = packet.get("linux_source_build_gate")
    if not isinstance(linux_source_build_gate, dict):
        raise ValueError("release truth packet is missing linux_source_build_gate")
    if str(linux_source_build_gate.get("status") or "").strip() != "passed":
        raise ValueError("linux_source_build_gate did not pass")
    if str(linux_source_build_gate.get("docker_image") or "").strip() != "debian:bookworm-slim":
        raise ValueError("linux_source_build_gate lost the expected docker image")
    if not str(linux_source_build_gate.get("rid") or "").strip().startswith("linux-"):
        raise ValueError("linux_source_build_gate lost the linux RID")
    for field_name in ("archive_sha256", "executable_sha256"):
        field_value = str(linux_source_build_gate.get(field_name) or "").strip()
        if len(field_value) != 64:
            raise ValueError(f"linux_source_build_gate has an invalid {field_name}")

    macos_source_build_contract = packet.get("macos_source_build_contract")
    if not isinstance(macos_source_build_contract, dict):
        raise ValueError("release truth packet is missing macos_source_build_contract")
    if str(macos_source_build_contract.get("status") or "").strip() != "passed":
        raise ValueError("macos_source_build_contract did not pass")
    if str(macos_source_build_contract.get("scope") or "").strip() != "script_contract_only":
        raise ValueError("macos_source_build_contract lost the bounded script-only scope")
    if str(macos_source_build_contract.get("runtime_coverage") or "").strip() != "not_run_on_non_macos_host":
        raise ValueError("macos_source_build_contract lost the bounded runtime coverage")
    if macos_source_build_contract.get("real_macos_runtime_proof_required") is not True:
        raise ValueError("macos_source_build_contract must still require real mac runtime proof")
    for field_name in (
        "maintenance_policy_marks_real_build_as_macos_only",
        "maintenance_policy_requires_two_step_install",
        "doc_marks_second_script_install",
    ):
        if macos_source_build_contract.get(field_name) is not True:
            raise ValueError(f"macos_source_build_contract lost required flag: {field_name}")

    _require_contains("STATUS.md", status, str(packet.get("shelf_truth_line") or ""))
    release_status = str(packet.get("release_status") or "").strip()
    published_line = str(packet.get("published_line") or "").strip()
    if published_line:
        _require_contains("STATUS.md", status, published_line)
    if release_status:
        _require_contains("STATUS.md", status, f"- Release status: {release_status}.")
    missing_installer_lane_line = str(packet.get("missing_installer_lane_line") or "").strip()
    architecture_scope_line = str(packet.get("architecture_scope_line") or "").strip()
    missing_platforms = list(packet.get("missing_platforms") or [])
    if missing_platforms and missing_installer_lane_line:
        _require_contains("STATUS.md", status, missing_installer_lane_line)
    if architecture_scope_line:
        _require_contains("STATUS.md", status, architecture_scope_line)

    if "Proof scope:" in download or "Claim boundary:" in download or "blanket flagship" in download:
        raise ValueError("DOWNLOAD.md reintroduced proof-scope copy")
    if "Windows and Linux downloads start on `chummer.run`." not in download:
        raise ValueError("DOWNLOAD.md lost the human download opening")
    if "chummer.run" not in download:
        raise ValueError("DOWNLOAD.md lost the chummer.run download authority")
    _require_contains("DOWNLOAD.md", download, str(packet.get("shelf_truth_line") or ""))
    _require_contains("DOWNLOAD.md", download, str(packet.get("release_verification_summary") or ""))
    _require_contains("DOWNLOAD.md", download, str(packet.get("known_issue_summary") or ""))
    for stale_phrase in (
        "Release status is missing or stale",
        "gold-ready",
        "some release notes are still catching up",
        "portable package",
        "portable builds",
        "Character math is already solid",
    ):
        combined = "\n".join([status, download, readme, migration])
        if stale_phrase.lower() in combined.lower():
            raise ValueError(f"public docs contain stale release wording: {stale_phrase}")

    visible_platforms = list(packet.get("available_platforms") or packet.get("desktop_platforms_visible") or [])

    if visible_platforms:
        if len(visible_platforms) == 1:
            try_line = f"Today you can try the current builds on {visible_platforms[0]}."
        elif len(visible_platforms) == 2:
            try_line = f"Today you can try the current builds on {visible_platforms[0]} and {visible_platforms[1]}."
        else:
            try_line = f"Today you can try the current builds on {', '.join(visible_platforms[:-1])}, and {visible_platforms[-1]}."
        _require_contains("FROM_CHUMMER5A_TO_CHUMMER6.md", migration, try_line)

    if missing_platforms:
        if len(missing_platforms) == 1:
            wait_line = f"If you rely on {missing_platforms[0]} as your main platform, wait before switching full time."
            warning_line = (
                f"{missing_platforms[0]} does not have a normal installer yet."
            )
        elif len(missing_platforms) == 2:
            wait_line = f"If you rely on {missing_platforms[0]} and {missing_platforms[1]} as your main platform, wait before switching full time."
            warning_line = f"{missing_platforms[0]} and {missing_platforms[1]} do not have normal installers yet."
        else:
            wait_line = (
                f"If you rely on {', '.join(missing_platforms[:-1])}, and {missing_platforms[-1]} as your main platform, "
                "wait before switching full time."
            )
            warning_line = (
                f"{', '.join(missing_platforms[:-1])}, and {missing_platforms[-1]} do not have normal installers yet."
            )
        _require_contains("FROM_CHUMMER5A_TO_CHUMMER6.md", migration, wait_line)
        _require_contains("STATUS.md", status, warning_line)

    print("chummer6_docs_release_truth:ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
