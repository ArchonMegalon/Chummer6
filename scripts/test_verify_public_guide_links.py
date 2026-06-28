from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "verify_public_guide_links.py"
SPEC = importlib.util.spec_from_file_location("verify_public_guide_links", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"Unable to load module from {MODULE_PATH}")
link_verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(link_verifier)


class VerifyPublicGuideLinksTests(unittest.TestCase):
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
