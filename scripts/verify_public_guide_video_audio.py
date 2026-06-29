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
MEDIA_URL_RE = re.compile(r"https://chummer\.run/media/[^\s)\"']+?\.(?:mp4|webm)(?:\?[^\s)\"']+)?", re.IGNORECASE)
IGNORED_DIRS = {".git", ".pytest_cache", ".guide-internal"}
DEFAULT_MEDIA_ROOTS = (
    Path("/docker/chummercomplete/chummer.run-services/Chummer.Run.Api/wwwroot"),
    Path("/app/wwwroot"),
)
VOLUME_RE = re.compile(r"(?P<kind>mean|max)_volume:\s*(?P<value>-?inf|-?\d+(?:\.\d+)?)\s*dB")
MIN_AUDIO_COVERAGE_RATIO = 0.98
MAX_UNCOVERED_TAIL_SECONDS = 0.75
MIN_MAX_VOLUME_DB = -50.0
MIN_MEAN_VOLUME_DB = -80.0
MIN_AAC_BITRATE = 16000
VOLUME_SAMPLE_SECONDS = 12.0
VOLUME_SAMPLE_POINTS = (0.0, 0.5, 0.85)


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


def _float_value(raw_value: object) -> float:
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return 0.0
    return value if value > 0 else 0.0


def _stream_duration(stream: dict[str, object]) -> float:
    return _float_value(stream.get("duration"))


def _bit_rate(stream: dict[str, object]) -> int:
    try:
        return int(stream.get("bit_rate") or 0)
    except (TypeError, ValueError):
        return 0


def _volume_sample_offsets(duration: float, sample_seconds: float) -> list[float]:
    if duration <= 0 or duration <= sample_seconds * 1.5:
        return [0.0]

    offsets: list[float] = []
    latest_start = max(0.0, duration - sample_seconds)
    for point in VOLUME_SAMPLE_POINTS:
        offset = min(latest_start, max(0.0, duration * point - sample_seconds / 2))
        if not offsets or abs(offset - offsets[-1]) >= 1.0:
            offsets.append(offset)
    return offsets


def _run_ffmpeg_volume_sample(target: str, timeout: int, offset: float, sample_seconds: float) -> tuple[bool, str, dict[str, float]]:
    command = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-ss",
        f"{offset:.3f}",
        "-t",
        f"{sample_seconds:.3f}",
        "-i",
        target,
        "-map",
        "0:a:0",
        "-vn",
        "-af",
        "volumedetect",
        "-f",
        "null",
        "-",
    ]
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return False, "ffmpeg is not installed", {}
    except subprocess.TimeoutExpired:
        return False, f"ffmpeg volumedetect timed out after {timeout}s at offset {offset:.1f}s", {}
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        return False, detail[-1] if detail else f"ffmpeg exited {result.returncode}", {}

    stats: dict[str, float] = {}
    for match in VOLUME_RE.finditer(result.stderr):
        raw_value = match.group("value")
        stats[f"{match.group('kind')}_volume_db"] = float("-inf") if raw_value == "-inf" else float(raw_value)
    if "mean_volume_db" not in stats or "max_volume_db" not in stats:
        return False, "ffmpeg volumedetect did not report mean/max volume", {}
    return True, "ok", stats


def _ffmpeg_volume(target: str, timeout: int, duration: float) -> tuple[bool, str]:
    sample_seconds = min(VOLUME_SAMPLE_SECONDS, duration) if duration > 0 else VOLUME_SAMPLE_SECONDS
    sample_seconds = max(1.0, sample_seconds)
    offsets = _volume_sample_offsets(duration, sample_seconds)

    observed: list[dict[str, float]] = []
    for offset in offsets:
        ok, detail, stats = _run_ffmpeg_volume_sample(target, timeout, offset, sample_seconds)
        if not ok:
            return False, detail
        observed.append(stats)

    if not observed:
        return False, "ffmpeg volumedetect did not sample audio"

    best = max(observed, key=lambda item: item["max_volume_db"])
    mean_volume = best["mean_volume_db"]
    max_volume = best["max_volume_db"]
    if max_volume <= MIN_MAX_VOLUME_DB or mean_volume <= MIN_MEAN_VOLUME_DB:
        return False, (
            "silent_or_placeholder_audio "
            f"samples={len(observed)} mean={mean_volume:.1f}dB max={max_volume:.1f}dB"
        )
    return True, f"samples={len(observed)} mean={mean_volume:.1f}dB max={max_volume:.1f}dB"


def _ffprobe_audio(target: str, timeout: int) -> tuple[bool, str]:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "stream=index,codec_name,codec_type,duration,bit_rate:format=duration",
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
        return False, "no media streams found"
    video_streams = [
        stream
        for stream in streams
        if isinstance(stream, dict) and str(stream.get("codec_type") or "") == "video"
    ]
    audio_streams = [
        stream
        for stream in streams
        if isinstance(stream, dict) and str(stream.get("codec_type") or "") == "audio"
    ]
    if not video_streams:
        return False, "no video stream found"
    if not audio_streams:
        return False, "no audio stream found"

    format_duration = _float_value((payload.get("format") or {}).get("duration")) if isinstance(payload.get("format"), dict) else 0.0
    video_duration = max([_stream_duration(stream) for stream in video_streams] + [format_duration])
    audio_duration = max([_stream_duration(stream) for stream in audio_streams] + [0.0])
    if video_duration > 1.0 and audio_duration > 0:
        uncovered_tail = video_duration - audio_duration
        coverage_ratio = audio_duration / video_duration if video_duration else 0.0
        if uncovered_tail > MAX_UNCOVERED_TAIL_SECONDS and coverage_ratio < MIN_AUDIO_COVERAGE_RATIO:
            return (
                False,
                "audio_undercovered "
                f"video={video_duration:.3f}s audio={audio_duration:.3f}s coverage={coverage_ratio:.3f}",
            )

    audio_stream = audio_streams[0]
    audio_codec = str(audio_stream.get("codec_name") or "unknown").strip().lower()
    bit_rate = _bit_rate(audio_stream)
    if audio_codec == "aac" and 0 < bit_rate < MIN_AAC_BITRATE:
        return False, f"placeholder_aac_bitrate bit_rate={bit_rate}"

    volume_ok, volume_detail = _ffmpeg_volume(target, timeout, video_duration)
    if not volume_ok:
        return False, volume_detail
    codecs = ",".join(str(stream.get("codec_name") or "unknown") for stream in audio_streams)
    return True, f"{codecs}; {volume_detail}"


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
    parser = argparse.ArgumentParser(description="Validate that public-guide video links have complete, non-silent audio.")
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
