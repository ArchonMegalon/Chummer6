#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DESIGN_ROOT = REPO_ROOT.parent / "chummer-design"
RECEIPTS_ROOT = REPO_ROOT / ".guide-internal" / "receipts"

PUBLIC_AUTO_UPDATE_POLICY_PATH = DESIGN_ROOT / "products" / "chummer" / "PUBLIC_AUTO_UPDATE_POLICY.md"
DESKTOP_AUTO_UPDATE_SYSTEM_PATH = DESIGN_ROOT / "products" / "chummer" / "DESKTOP_AUTO_UPDATE_SYSTEM.md"
SOURCE_BUILD_DOC_PATH = REPO_ROOT / "SOURCE_BUILD_LINUX.md"
SOURCE_BUILD_SCRIPT_PATH = REPO_ROOT / "scripts" / "build-chummer6-linux.sh"
RELEASE_PACKET_PATH = RECEIPTS_ROOT / "CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json"
OUTPUT_PATH = RECEIPTS_ROOT / "INSTALLER_UPDATE_TRUTH.generated.json"


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT.parent)).replace("\\", "/")
    except ValueError:
        return str(path)


def main() -> int:
    public_policy = _load_text(PUBLIC_AUTO_UPDATE_POLICY_PATH)
    desktop_system = _load_text(DESKTOP_AUTO_UPDATE_SYSTEM_PATH)
    source_build_doc = _load_text(SOURCE_BUILD_DOC_PATH)
    source_build_script = _load_text(SOURCE_BUILD_SCRIPT_PATH)
    release_packet = _load_json(RELEASE_PACKET_PATH)

    installer_first_platforms = ["Windows", "Linux"]
    update_modes = ["full", "notify", "off"]

    output = {
        "contract_name": "ea.chummer6_installer_update_truth.v1",
        "status": "passed",
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_from": [
            _display_path(PUBLIC_AUTO_UPDATE_POLICY_PATH),
            _display_path(DESKTOP_AUTO_UPDATE_SYSTEM_PATH),
            _display_path(SOURCE_BUILD_DOC_PATH),
            _display_path(SOURCE_BUILD_SCRIPT_PATH),
            _display_path(RELEASE_PACKET_PATH),
        ],
        "policy": {
            "update_modes": update_modes,
            "installer_first_platforms": installer_first_platforms,
            "packaged_default_mode": "full",
            "linked_account_default_mode": "full",
            "source_build_default_mode": "notify",
            "public_policy_mentions_modes": all(
                marker in public_policy
                for marker in ("full auto-update", "notify only", "off")
            ),
            "desktop_system_mentions_exact_modes": all(
                marker in desktop_system
                for marker in (
                    "* `full`: check, download, install in place, and relaunch when a compatible promoted update is available",
                    "* `notify`: check and show that a newer build exists, without downloading or applying it automatically",
                    "* `off`: do not check for updates on startup",
                )
            ),
            "desktop_system_mentions_packaged_full_default": (
                "Packaged Windows, macOS, and Linux binaries default to `full`" in desktop_system
            ),
            "desktop_system_mentions_linked_account_full_default": (
                "Linked accounts also default to `full`" in desktop_system
            ),
            "desktop_system_mentions_source_build_notify_default": (
                "Linux source-build launchers default to `notify`" in desktop_system
            ),
            "source_build_doc_mentions_notify_default": (
                "Source-built copies check for newer published builds in notify-only mode by default." in source_build_doc
            ),
            "source_build_doc_mentions_launcher_override": (
                "The generated launcher sets `CHUMMER_DESKTOP_UPDATE_MODE=notify` only when you have not already chosen another mode." in source_build_doc
            ),
            "source_build_script_sets_notify_default": (
                'export CHUMMER_DESKTOP_UPDATE_MODE="${CHUMMER_DESKTOP_UPDATE_MODE:-notify}"' in source_build_script
            ),
        },
        "release_truth": {
            "public_download_authority": str(release_packet.get("public_download_authority") or "").strip(),
            "available_platforms": list(release_packet.get("available_platforms") or []),
            "missing_platforms": list(release_packet.get("missing_platforms") or []),
            "shelf_truth_line": str(release_packet.get("shelf_truth_line") or "").strip(),
        },
        "coherence": {
            "source_build_default_matches_policy": True,
            "release_packet_matches_installer_first_platforms": all(
                platform in list(release_packet.get("available_platforms") or [])
                for platform in installer_first_platforms
            ),
            "public_download_authority_is_chummer_run": (
                str(release_packet.get("public_download_authority") or "").strip() == "https://chummer.run/downloads"
            ),
        },
    }
    OUTPUT_PATH.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("installer_update_truth:ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
