from __future__ import annotations

import os
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "SOURCE_BUILD_LINUX.md"
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build-chummer6-linux.sh"
AUDIT_SCRIPT = REPO_ROOT / "scripts" / "check-host-chummer6-linux.sh"
PREREQ_SCRIPT = REPO_ROOT / "scripts" / "list-chummer6-linux-prereqs.sh"


class VerifyLinuxSourceBuildSurfaceTests(unittest.TestCase):
    def test_public_doc_references_checked_in_helper_scripts(self) -> None:
        doc_text = DOC.read_text(encoding="utf-8")
        self.assertIn("bash scripts/list-chummer6-linux-prereqs.sh", doc_text)
        self.assertIn("bash scripts/check-host-chummer6-linux.sh", doc_text)
        self.assertIn("bash scripts/build-chummer6-linux.sh --base", doc_text)

    def test_helper_scripts_exist_and_are_executable(self) -> None:
        for path in (BUILD_SCRIPT, AUDIT_SCRIPT, PREREQ_SCRIPT):
            self.assertTrue(path.exists(), f"Missing helper script: {path}")
            self.assertTrue(os.access(path, os.X_OK), f"Helper script is not executable: {path}")


if __name__ == "__main__":
    unittest.main()
