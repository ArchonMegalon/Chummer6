#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PUBLIC_ORIGIN = "https://chummer.run"
MEDIA_URL_RE = re.compile(r"https://chummer\.run/media/[^\s)\"']+?\.mp4", re.IGNORECASE)
IGNORED_DIRS = {".git", ".pytest_cache", ".guide-internal"}
DEFAULT_MEDIA_ROOTS = (
    Path("/docker/chummercomplete/chummer.run-services/Chummer.Run.Api/wwwroot"),
    Path("/app/wwwroot"),
)


def _iter_markdown_files(root: Path) -> list[Path]:
    return [
        path
        for path in sorted(root.rglob("*.md"))
        if not any(part in IGNORED_DIRS for part in path.relative_to(root).parts)
    ]


def _clean_url(value: str) -> str:
    return value.strip().rstrip(".,;:")


def _video_links(root: Path) -> dict[str, list[str]]:
    links: dict[str, list[str]] = {}
    for markdown_path in _iter_markdown_files(root):
        for line_number, line in enumerate(markdown_path.read_text(encoding="utf-8").splitlines(), 1):
            for match in MEDIA_URL_RE.finditer(line):
                url = _clean_url(match.group(0))
                links.setdefault(url, []).append(f"{markdown_path.relative_to(root)}:{line_number}")
    return links


def _candidate_media_roots(configured: list[Path]) -> list[Path]:
    roots: list[Path] = []
    env_value = os.environ.get("CHUMMER6_PUBLIC_MEDIA_ROOT", "").strip()
    if env_value:
        roots.append(Path(env_value))
    roots.extend(configured)
    roots.extend(DEFAULT_MEDIA_ROOTS)

    resolved: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if not str(root).strip():
            continue
        candidate = root.expanduser()
        try:
            key = candidate.resolve()
        except OSError:
            key = candidate
        if key in seen:
            continue
        seen.add(key)
        resolved.append(candidate)
    return resolved


def _local_media_path(url: str, media_roots: list[Path]) -> Path | None:
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc != "chummer.run" or not parsed.path.startswith("/media/"):
        return None
    relative = Path(urllib.parse.unquote(parsed.path.lstrip("/")))
    for root in media_roots:
        candidate = root / relative
        if candidate.is_file():
            return candidate
    return None


def _ffprobe_audio(target: str, timeout: int) -> tuple[bool, str]:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a",
        "-show_entries",
        "stream=index,codec_name,codec_type",
        "-of",
        "json",
        target,
    ]
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return False, "ffprobe is not installed"
    except subprocess.TimeoutExpired:
        return False, f"ffprobe timed out after {timeout}s"

    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        return False, detail[-1] if detail else f"ffprobe exited {result.returncode}"

    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        return False, f"ffprobe returned invalid JSON: {exc}"

    streams = payload.get("streams") or []
    if not isinstance(streams, list) or not streams:
        return False, "no audio stream found"
    codecs = [
        str(stream.get("codec_name") or "unknown")
        for stream in streams
        if isinstance(stream, dict) and str(stream.get("codec_type") or "") == "audio"
    ]
    if not codecs:
        return False, "no audio stream found"
    return True, ",".join(codecs)


def verify(root: Path, media_roots: list[Path], *, local_only: bool, timeout: int) -> list[str]:
    failures: list[str] = []
    links = _video_links(root)
    if not links:
        return ["no public guide MP4 links found"]

    for url, references in sorted(links.items()):
        local_path = _local_media_path(url, media_roots)
        target = str(local_path) if local_path is not None else url
        if local_path is None and local_only:
            roots = ", ".join(str(root) for root in media_roots)
            failures.append(f"{url}: no local media file found under {roots}; referenced by {', '.join(references)}")
            continue
        ok, detail = _ffprobe_audio(target, timeout)
        if not ok:
            source = str(local_path) if local_path is not None else "public URL"
            failures.append(f"{url}: {detail} via {source}; referenced by {', '.join(references)}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate that public-guide MP4 links have audio streams.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--media-root", type=Path, action="append", default=[])
    parser.add_argument("--local-only", action="store_true", help="Fail instead of probing the public URL when local media is missing.")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    root = args.root.resolve()
    media_roots = _candidate_media_roots(args.media_root)
    failures = verify(root, media_roots, local_only=args.local_only, timeout=args.timeout)
    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1
    print("public_guide_video_audio:ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
