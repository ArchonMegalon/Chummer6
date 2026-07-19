from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LOCK = REPO_ROOT / "RELEASE.lock.json"
VERIFIER = REPO_ROOT / "scripts" / "verify_linux_source_lock.py"


class CheckedLinuxSourceLockTests(unittest.TestCase):
    def inspect(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "python3",
                str(VERIFIER),
                "inspect",
                "--lock",
                str(LOCK),
                "--repo-root",
                str(REPO_ROOT),
            ],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
            check=False,
        )

    def test_checked_lock_closes_the_exact_review_only_v2_graph(self) -> None:
        completed = self.inspect()
        self.assertEqual(0, completed.returncode, completed.stdout)
        self.assertIn("SDK_VERSION\t10.0.103", completed.stdout)
        self.assertIn("RELEASE_EVIDENCE_ELIGIBLE\tfalse", completed.stdout)
        self.assertEqual(5, completed.stdout.count("REPOSITORY\t"))
        self.assertEqual(2, completed.stdout.count("NUGET_PACKAGE_PLANE\t"))
        self.assertEqual(6, completed.stdout.count("NUGET_PROJECT_LOCK\t"))

    def test_hub_and_ui_authorities_are_exact_not_mutable_refs(self) -> None:
        payload = json.loads(LOCK.read_text(encoding="utf-8"))
        repositories = {row["directory"]: row for row in payload["repositories"]}
        self.assertEqual(
            "35aa5a828f076d7c7c4a57dbab17d8715f9c3b68",
            repositories["chummer.run-services"]["commit"],
        )
        self.assertEqual(
            "73dbef29bef4b5c9ae7a081361a4e317a3489229",
            repositories["chummer6-ui"]["commit"],
        )
        for row in repositories.values():
            self.assertRegex(row["commit"], r"^[0-9a-f]{40}$")
            self.assertNotIn(row["commit"], {"main", "master", "HEAD"})

    def test_lock_never_promotes_the_unbound_release_packet(self) -> None:
        payload = json.loads(LOCK.read_text(encoding="utf-8"))
        self.assertEqual("review_required", payload["releaseStatus"])
        self.assertIs(payload["releaseEvidenceEligible"], False)
        self.assertEqual(
            "unbound_review_placeholder", payload["releaseManifest"]["status"]
        )
        self.assertIs(payload["releaseManifest"]["releaseEvidenceEligible"], False)

    def test_source_lock_verifier_is_an_exact_checked_build_authority(self) -> None:
        payload = json.loads(LOCK.read_text(encoding="utf-8"))
        descriptor = payload["sourceLockVerifier"]
        self.assertEqual(
            {"path", "sha256"},
            set(descriptor),
        )
        self.assertEqual(
            "scripts/verify_linux_source_lock.py",
            descriptor["path"],
        )
        actual = hashlib.sha256((REPO_ROOT / descriptor["path"]).read_bytes()).hexdigest()
        self.assertEqual(actual, descriptor["sha256"])


if __name__ == "__main__":
    unittest.main()
