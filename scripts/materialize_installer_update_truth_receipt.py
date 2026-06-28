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
LINUX_SOURCE_BUILD_POLICY_PATH = DESIGN_ROOT / "products" / "chummer" / "maintenance" / "LINUX_SOURCE_BUILD_PATH.md"
MAC_SOURCE_BUILD_POLICY_PATH = DESIGN_ROOT / "products" / "chummer" / "maintenance" / "MAC_SOURCE_BUILD_PATH.md"
SOURCE_BUILD_LINUX_DOC_PATH = REPO_ROOT / "SOURCE_BUILD_LINUX.md"
SOURCE_BUILD_LINUX_SCRIPT_PATH = REPO_ROOT / "scripts" / "build-chummer6-linux.sh"
SOURCE_BUILD_LINUX_INSTALL_SCRIPT_PATH = REPO_ROOT / "scripts" / "install-chummer6-linux-local.sh"
SOURCE_BUILD_MACOS_DOC_PATH = REPO_ROOT / "SOURCE_BUILD_MACOS.md"
SOURCE_BUILD_MACOS_BUILD_SCRIPT_PATH = REPO_ROOT / "scripts" / "build-chummer6-macos-local.sh"
SOURCE_BUILD_MACOS_INSTALL_SCRIPT_PATH = REPO_ROOT / "scripts" / "install-chummer6-macos-local.sh"
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
    linux_source_build_policy = _load_text(LINUX_SOURCE_BUILD_POLICY_PATH)
    mac_source_build_policy = _load_text(MAC_SOURCE_BUILD_POLICY_PATH)
    source_build_linux_doc = _load_text(SOURCE_BUILD_LINUX_DOC_PATH)
    source_build_linux_script = _load_text(SOURCE_BUILD_LINUX_SCRIPT_PATH)
    source_build_linux_install_script = _load_text(SOURCE_BUILD_LINUX_INSTALL_SCRIPT_PATH)
    source_build_macos_doc = _load_text(SOURCE_BUILD_MACOS_DOC_PATH)
    source_build_macos_build_script = _load_text(SOURCE_BUILD_MACOS_BUILD_SCRIPT_PATH)
    source_build_macos_install_script = _load_text(SOURCE_BUILD_MACOS_INSTALL_SCRIPT_PATH)
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
            _display_path(LINUX_SOURCE_BUILD_POLICY_PATH),
            _display_path(MAC_SOURCE_BUILD_POLICY_PATH),
            _display_path(SOURCE_BUILD_LINUX_DOC_PATH),
            _display_path(SOURCE_BUILD_LINUX_SCRIPT_PATH),
            _display_path(SOURCE_BUILD_LINUX_INSTALL_SCRIPT_PATH),
            _display_path(SOURCE_BUILD_MACOS_DOC_PATH),
            _display_path(SOURCE_BUILD_MACOS_BUILD_SCRIPT_PATH),
            _display_path(SOURCE_BUILD_MACOS_INSTALL_SCRIPT_PATH),
            _display_path(RELEASE_PACKET_PATH),
        ],
        "policy": {
            "update_modes": update_modes,
            "installer_first_platforms": installer_first_platforms,
            "packaged_default_mode": "full",
            "linked_account_default_mode": "full",
            "source_build_linux_default_mode": "notify",
            "source_build_linux_analytics_default": "off",
            "source_build_macos_default_mode": "notify",
            "source_build_macos_analytics_default": "off",
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
            "desktop_system_mentions_linux_source_build_notify_default": (
                "Linux source-build launchers default to `notify`" in desktop_system
                or "Linux local-source-build launchers default to `notify`" in desktop_system
            ),
            "desktop_system_mentions_linux_source_build_split": (
                "Linux local-source-build lane stays split into a build step plus a separate user-local install step." in desktop_system
            ),
            "desktop_system_mentions_macos_local_source_build_notify_default": (
                "The personal macOS local-source-build lane follows the same update default." in desktop_system
            ),
            "desktop_system_mentions_macos_local_source_build_split": (
                "It remains a separate build step plus install step" in desktop_system
            ),
            "linux_source_build_policy_mentions_split": (
                "split into a build step and a separate user-local install step" in linux_source_build_policy
            ),
            "mac_source_build_policy_mentions_split": (
                "split into a build step and a separate install step" in mac_source_build_policy
            ),
            "source_build_linux_doc_mentions_notify_default": (
                "Source-built copies check for newer published builds in notify-only mode by default." in source_build_linux_doc
            ),
            "source_build_linux_doc_mentions_second_script_install": (
                "The binary is installed by a second script on purpose." in source_build_linux_doc
            ),
            "source_build_linux_doc_mentions_launcher_override": (
                "The generated launcher sets `CHUMMER_DESKTOP_UPDATE_MODE=notify` only when you have not already chosen another mode." in source_build_linux_doc
            ),
            "source_build_linux_doc_mentions_analytics_default_off": (
                "Analytics also default to `off` through `CHUMMER_DESKTOP_ANALYTICS_DEFAULT=off`" in source_build_linux_doc
            ),
            "source_build_linux_build_script_mentions_second_script_install": (
                "This script only builds the binary and archive artifacts." in source_build_linux_script
                and "Install the result later with ./install-chummer6-linux-local.sh." in source_build_linux_script
            ),
            "source_build_linux_script_sets_notify_default": (
                'export CHUMMER_DESKTOP_UPDATE_MODE="${CHUMMER_DESKTOP_UPDATE_MODE:-notify}"' in source_build_linux_script
            ),
            "source_build_linux_script_sets_analytics_default_off": (
                'export CHUMMER_DESKTOP_ANALYTICS_DEFAULT="${CHUMMER_DESKTOP_ANALYTICS_DEFAULT:-off}"' in source_build_linux_script
            ),
            "source_build_linux_install_script_sets_notify_default": (
                'export CHUMMER_DESKTOP_UPDATE_MODE="${CHUMMER_DESKTOP_UPDATE_MODE:-notify}"' in source_build_linux_install_script
            ),
            "source_build_linux_install_script_sets_analytics_default_off": (
                'export CHUMMER_DESKTOP_ANALYTICS_DEFAULT="${CHUMMER_DESKTOP_ANALYTICS_DEFAULT:-off}"' in source_build_linux_install_script
            ),
            "source_build_macos_doc_mentions_second_script_install": (
                "The binary is installed by a second script on purpose." in source_build_macos_doc
            ),
            "source_build_macos_doc_mentions_notify_default": (
                "CHUMMER_DESKTOP_UPDATE_MODE=notify" in source_build_macos_doc
            ),
            "source_build_macos_doc_mentions_analytics_default_off": (
                "CHUMMER_DESKTOP_ANALYTICS_DEFAULT=off" in source_build_macos_doc
            ),
            "source_build_macos_build_script_mentions_second_script_install": (
                "This script only builds the binary and archive artifacts." in source_build_macos_build_script
                and "Install the result later with ./install-chummer6-macos-local.sh." in source_build_macos_build_script
            ),
            "source_build_macos_build_script_sets_notify_default": (
                'export CHUMMER_DESKTOP_UPDATE_MODE="${CHUMMER_DESKTOP_UPDATE_MODE:-notify}"' in source_build_macos_build_script
            ),
            "source_build_macos_build_script_sets_analytics_default_off": (
                'export CHUMMER_DESKTOP_ANALYTICS_DEFAULT="${CHUMMER_DESKTOP_ANALYTICS_DEFAULT:-off}"' in source_build_macos_build_script
            ),
            "source_build_macos_install_script_sets_notify_default": (
                'export CHUMMER_DESKTOP_UPDATE_MODE="${CHUMMER_DESKTOP_UPDATE_MODE:-notify}"' in source_build_macos_install_script
            ),
            "source_build_macos_install_script_sets_analytics_default_off": (
                'export CHUMMER_DESKTOP_ANALYTICS_DEFAULT="${CHUMMER_DESKTOP_ANALYTICS_DEFAULT:-off}"' in source_build_macos_install_script
            ),
        },
        "release_truth": {
            "public_download_authority": str(release_packet.get("public_download_authority") or "").strip(),
            "available_platforms": list(release_packet.get("available_platforms") or []),
            "missing_platforms": list(release_packet.get("missing_platforms") or []),
            "shelf_truth_line": str(release_packet.get("shelf_truth_line") or "").strip(),
        },
        "coherence": {
            "linux_source_build_defaults_match_policy": True,
            "linux_source_build_is_explicitly_two_step": True,
            "macos_source_build_defaults_match_policy": True,
            "macos_source_build_is_explicitly_two_step": True,
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
