#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKET_PATH = REPO_ROOT / "CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json"
README_PATH = REPO_ROOT / "README.md"
STATUS_PATH = REPO_ROOT / "STATUS.md"
DOWNLOAD_PATH = REPO_ROOT / "DOWNLOAD.md"
MIGRATION_PATH = REPO_ROOT / "FROM_CHUMMER5A_TO_CHUMMER6.md"


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _require_contains(name: str, haystack: str, needle: str) -> None:
    if needle and needle not in haystack:
        raise ValueError(f"{name} is missing required release-truth line: {needle!r}")


def main() -> int:
    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
    readme = _load_text(README_PATH)
    status = _load_text(STATUS_PATH)
    download = _load_text(DOWNLOAD_PATH)
    migration = _load_text(MIGRATION_PATH)

    _require_contains("README.md", readme, str(packet.get("shelf_truth_line") or ""))
    _require_contains("README.md", readme, str(packet.get("proof_scope_line") or ""))
    if "clear public proof" not in readme:
        raise ValueError("README.md lost the public-proof boundary rewrite")

    _require_contains("STATUS.md", status, str(packet.get("shelf_truth_line") or ""))
    release_status = str(packet.get("release_status") or "").strip()
    if release_status:
        _require_contains("STATUS.md", status, f"- Release status: {release_status}.")

    if "Proof scope:" not in download or "blanket flagship" not in download:
        raise ValueError("DOWNLOAD.md lost the proof-scope boundary")
    if "chummer.run" not in download:
        raise ValueError("DOWNLOAD.md lost the chummer.run download authority")
    _require_contains("DOWNLOAD.md", download, str(packet.get("shelf_truth_line") or ""))

    visible_platforms = list(packet.get("available_platforms") or packet.get("desktop_platforms_visible") or [])
    missing_platforms = list(packet.get("missing_platforms") or [])

    if visible_platforms:
        if len(visible_platforms) == 1:
            try_line = f"- Today you can try preview builds on {visible_platforms[0]}."
        elif len(visible_platforms) == 2:
            try_line = f"- Today you can try preview builds on {visible_platforms[0]} and {visible_platforms[1]}."
        else:
            try_line = f"- Today you can try preview builds on {', '.join(visible_platforms[:-1])}, and {visible_platforms[-1]}."
        _require_contains("FROM_CHUMMER5A_TO_CHUMMER6.md", migration, try_line)

    if missing_platforms:
        if len(missing_platforms) == 1:
            wait_line = f"- If you rely on {missing_platforms[0]} as your main platform, wait before switching full time."
            warning_line = f"- Current warning: There is still no public {missing_platforms[0]} installer."
        elif len(missing_platforms) == 2:
            wait_line = f"- If you rely on {missing_platforms[0]} and {missing_platforms[1]} as your main platform, wait before switching full time."
            warning_line = f"- Current warning: Public installers are still missing for {missing_platforms[0]} and {missing_platforms[1]}."
        else:
            wait_line = (
                f"- If you rely on {', '.join(missing_platforms[:-1])}, and {missing_platforms[-1]} as your main platform, "
                "wait before switching full time."
            )
            warning_line = (
                f"- Current warning: Public installers are still missing for {', '.join(missing_platforms[:-1])}, "
                f"and {missing_platforms[-1]}."
            )
        _require_contains("FROM_CHUMMER5A_TO_CHUMMER6.md", migration, wait_line)
        _require_contains("DOWNLOAD.md", download, warning_line)

    if missing_platforms:
        missing_line = f"Still missing from the public download page: {', '.join(missing_platforms[:-1]) + (' and ' if len(missing_platforms) > 1 else '') + missing_platforms[-1]}."
        if len(missing_platforms) == 2:
            missing_line = f"Still missing from the public download page: {missing_platforms[0]} and {missing_platforms[1]}."
        elif len(missing_platforms) > 2:
            missing_line = (
                f"Still missing from the public download page: {', '.join(missing_platforms[:-1])}, and {missing_platforms[-1]}."
            )
        _require_contains("README.md", readme, missing_line)
        _require_contains("STATUS.md", status, missing_line)

    print("chummer6_docs_release_truth:ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
