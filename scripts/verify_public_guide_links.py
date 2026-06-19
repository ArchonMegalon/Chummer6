#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import string
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PUBLIC_ORIGIN = "https://chummer.run"

LINK_RE = re.compile(
    r"!?\[[^\]]+\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)"
    r"|<((?:https?://|mailto:)[^>]+)>"
    r"|(https?://[^\s)>,]+)"
)


def _iter_markdown_files(root: Path) -> list[Path]:
    ignored = {".git", ".pytest_cache", ".guide-internal"}
    return [
        path
        for path in sorted(root.rglob("*.md"))
        if not any(part in ignored for part in path.relative_to(root).parts)
    ]


def _clean_target(target: str) -> str:
    return target.strip().rstrip("`.,;:")


def _slugify_heading(heading: str) -> str:
    heading = heading.strip().lower()
    heading = "".join(ch for ch in heading if ch not in string.punctuation.replace("-", ""))
    heading = re.sub(r"\s+", "-", heading)
    heading = re.sub(r"-+", "-", heading).strip("-")
    return heading


def _anchors_for(markdown_path: Path) -> set[str]:
    anchors: set[str] = set()
    for line in markdown_path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if not match:
            continue
        anchors.add(_slugify_heading(match.group(2)))
    return anchors


def _split_target(target: str) -> tuple[str, str]:
    path, sep, fragment = target.partition("#")
    return path, fragment if sep else ""


def _check_http(url: str, timeout: int) -> str | None:
    request = urllib.request.Request(url, method="GET", headers={"User-Agent": "chummer6-public-guide-link-check/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            if 200 <= status < 400:
                return None
            return f"http status {status}"
    except urllib.error.HTTPError as exc:
        if 200 <= exc.code < 400:
            return None
        return f"http status {exc.code}"
    except Exception as exc:  # pragma: no cover - exercised in CI by real network failures.
        return f"{exc.__class__.__name__}: {exc}"


def _check_local_link(root: Path, source: Path, target: str) -> str | None:
    path_part, raw_fragment = _split_target(target)
    fragment = urllib.parse.unquote(raw_fragment)
    if not path_part:
        destination = source
    else:
        destination = (source.parent / urllib.parse.unquote(path_part)).resolve()
    try:
        destination.relative_to(root)
    except ValueError:
        return "local link escapes public guide root"
    if not destination.exists():
        return f"missing local target: {destination.relative_to(ROOT)}"
    if fragment and destination.suffix.lower() == ".md":
        anchors = _anchors_for(destination)
        if fragment.lower() not in anchors:
            return f"missing anchor #{fragment} in {destination.relative_to(ROOT)}"
    return None


def verify(root: Path, public_origin: str, check_http: bool, timeout: int) -> list[str]:
    failures: list[str] = []
    for markdown_path in _iter_markdown_files(root):
        text = markdown_path.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), 1):
            for match in LINK_RE.finditer(line):
                target = _clean_target(next(group for group in match.groups() if group))
                if not target:
                    continue
                if target.startswith("mailto:"):
                    if "@" not in target:
                        failures.append(f"{markdown_path.relative_to(root)}:{line_number}: invalid mailto link: {target}")
                    continue
                if target.startswith(("http://", "https://")):
                    if check_http:
                        failure = _check_http(target, timeout)
                        if failure:
                            failures.append(f"{markdown_path.relative_to(root)}:{line_number}: {failure}: {target}")
                    continue
                if target.startswith("/"):
                    if check_http:
                        url = public_origin.rstrip("/") + target
                        failure = _check_http(url, timeout)
                        if failure:
                            failures.append(f"{markdown_path.relative_to(root)}:{line_number}: {failure}: {target}")
                    continue
                failure = _check_local_link(root, markdown_path, target)
                if failure:
                    failures.append(f"{markdown_path.relative_to(root)}:{line_number}: {failure}: {target}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate public-guide Markdown links.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--public-origin", default=DEFAULT_PUBLIC_ORIGIN)
    parser.add_argument("--skip-http", action="store_true", help="Only validate local files and anchors.")
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args()

    failures = verify(args.root.resolve(), args.public_origin, not args.skip_http, args.timeout)
    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1
    print("public_guide_links:ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
