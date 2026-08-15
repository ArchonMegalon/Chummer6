from __future__ import annotations

import importlib.util
import tempfile
import unittest
import urllib.error
from unittest import mock
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "verify_public_guide_links.py"
SPEC = importlib.util.spec_from_file_location("verify_public_guide_links", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"Unable to load module from {MODULE_PATH}")
link_verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(link_verifier)


class Response:
    def __init__(self, status: int) -> None:
        self.status = status

    def __enter__(self) -> "Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class VerifyPublicGuideLinksTests(unittest.TestCase):
    def test_http_check_retries_transient_5xx(self) -> None:
        url = "https://chummer.run/participate"
        responses: list[object] = [
            urllib.error.HTTPError(url, 502, "Bad Gateway", hdrs=None, fp=None),
            Response(200),
        ]

        def fake_urlopen(_request: object, timeout: int) -> object:
            self.assertEqual(1, timeout)
            next_response = responses.pop(0)
            if isinstance(next_response, Exception):
                raise next_response
            return next_response

        with mock.patch.object(link_verifier.urllib.request, "urlopen", side_effect=fake_urlopen), mock.patch.object(link_verifier.time, "sleep"):
            self.assertIsNone(link_verifier._check_http(url, timeout=1))

        self.assertEqual([], responses)

    def test_http_check_does_not_retry_permanent_4xx(self) -> None:
        url = "https://chummer.run/missing"
        error = urllib.error.HTTPError(url, 404, "Not Found", hdrs=None, fp=None)

        with mock.patch.object(link_verifier.urllib.request, "urlopen", side_effect=error) as urlopen, mock.patch.object(link_verifier.time, "sleep") as sleep:
            self.assertEqual("http status 404", link_verifier._check_http(url, timeout=1))

        self.assertEqual(1, urlopen.call_count)
        sleep.assert_not_called()

    def test_review_route_requires_and_accepts_http_409(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "DOWNLOAD.md").write_text(
                "- Review route (currently withheld): [Inspect route](https://chummer.run/downloads/install/windows-installer)\n",
                encoding="utf-8",
            )
            error = urllib.error.HTTPError(
                "https://chummer.run/downloads/install/windows-installer",
                409,
                "Conflict",
                hdrs=None,
                fp=None,
            )

            with mock.patch.object(
                link_verifier.urllib.request,
                "urlopen",
                side_effect=error,
            ):
                failures = link_verifier.verify(
                    root,
                    "https://chummer.run",
                    check_http=True,
                    timeout=1,
                    expect_review_withheld=True,
                )

        self.assertEqual([], failures)

    def test_review_route_rejects_an_unexpectedly_open_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "DOWNLOAD.md").write_text(
                "- Review route (currently withheld): [Inspect route](https://chummer.run/downloads/install/windows-installer)\n",
                encoding="utf-8",
            )

            with mock.patch.object(
                link_verifier.urllib.request,
                "urlopen",
                return_value=Response(200),
            ):
                failures = link_verifier.verify(
                    root,
                    "https://chummer.run",
                    check_http=True,
                    timeout=1,
                    expect_review_withheld=True,
                )

        self.assertEqual(1, len(failures))
        self.assertIn("review-withheld route must return http status 409", failures[0])

    def test_http_409_remains_a_failure_outside_review_route_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "README.md").write_text(
                "[Download](https://chummer.run/downloads/install/windows-installer)\n",
                encoding="utf-8",
            )
            error = urllib.error.HTTPError(
                "https://chummer.run/downloads/install/windows-installer",
                409,
                "Conflict",
                hdrs=None,
                fp=None,
            )

            with mock.patch.object(
                link_verifier.urllib.request,
                "urlopen",
                side_effect=error,
            ):
                failures = link_verifier.verify(
                    root,
                    "https://chummer.run",
                    check_http=True,
                    timeout=1,
                )

        self.assertEqual(1, len(failures))
        self.assertIn("http status 409", failures[0])

    def test_missing_local_target_is_reported_relative_to_checked_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "public-guide"
            root.mkdir()
            markdown = root / "README.md"
            markdown.write_text("[Missing](SOURCE_BUILD_LINUX.md)\n", encoding="utf-8")

            failures = link_verifier.verify(root, "https://chummer.run", check_http=False, timeout=1)

        self.assertEqual(
            ["README.md:1: missing local target: SOURCE_BUILD_LINUX.md: SOURCE_BUILD_LINUX.md"],
            failures,
        )

    def test_source_owned_doc_can_resolve_links_against_chummer6_source_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_root = Path(tmpdir)
            public_root = temp_root / "public-guide"
            source_root = temp_root / "Chummer6"
            public_root.mkdir()
            (source_root / "scripts").mkdir(parents=True)
            markdown = public_root / "SOURCE_BUILD_MACOS.md"
            markdown.write_text("[Build](scripts/build-chummer6-macos-local.sh)\n", encoding="utf-8")
            (source_root / "SOURCE_BUILD_MACOS.md").write_text(markdown.read_text(encoding="utf-8"), encoding="utf-8")
            (source_root / "scripts" / "build-chummer6-macos-local.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")

            failures = link_verifier.verify(
                public_root,
                "https://chummer.run",
                check_http=False,
                timeout=1,
                source_root=source_root,
            )

        self.assertEqual([], failures)


if __name__ == "__main__":
    unittest.main()
