#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).with_name("materialize_public_release_truth_packet.py")
SPEC = importlib.util.spec_from_file_location("materialize_public_release_truth_packet", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def release_payload() -> dict[str, object]:
    return {
        "releaseStatus": "published",
        "channel": "public_stable",
        "rolloutState": "public_stable",
        "supportabilityState": "gold_supported",
        "publishedAt": "2026-07-11T16:49:15Z",
        "knownIssueSummary": "Current release checks are clear for the promoted shelf.",
        "desktopTupleCoverage": {
            "requiredDesktopPlatforms": ["linux", "windows"],
            "requiredDesktopHeads": ["avalonia"],
            "promotedInstallerTuples": [],
            "missingRequiredPlatforms": [],
            "missingRequiredHeads": [],
            "missingRequiredPlatformHeadPairs": [],
            "missingRequiredPlatformHeadRidTuples": [],
            "externalProofRequests": [],
            "complete": True,
        },
    }


def authority() -> dict[str, object]:
    return {
        "artifactCount": 2,
        "artifacts": [
            {
                "arch": "x64",
                "artifactId": "linux-installer",
                "compatibilityState": "compatible",
                "downloadUrl": "https://chummer.run/downloads/g/generation-1/files/linux.deb",
                "head": "avalonia",
                "installAccessClass": "open_public",
                "kind": "installer",
                "platform": "linux",
                "promotionState": "promoted",
                "publicationScope": "signed-in-and-public",
                "publicInstallRoute": "/downloads/files/linux.deb",
                "revokeState": "not_revoked",
                "rid": "linux-x64",
                "sha256": "a" * 64,
                "sizeBytes": 100,
            },
            {
                "arch": "x64",
                "artifactId": "windows-installer",
                "compatibilityState": "compatible",
                "downloadUrl": "https://chummer.run/downloads/g/generation-1/files/windows.exe",
                "head": "avalonia",
                "installAccessClass": "open_public",
                "kind": "installer",
                "platform": "windows",
                "promotionState": "promoted",
                "publicationScope": "signed-in-and-public",
                "publicInstallRoute": "/downloads/files/windows.exe",
                "revokeState": "not_revoked",
                "rid": "win-x64",
                "sha256": "b" * 64,
                "sizeBytes": 200,
            },
        ],
        "authorityContract": "chummer.release-authority-snapshot/v2",
        "availablePlatforms": ["linux", "windows"],
        "channel": "public_stable",
        "downloadAccessPosture": "open_public",
        "knownIssueSummary": "No current blocker.",
        "manifestPath": "RELEASE_CHANNEL.json",
        "manifestSha256": "c" * 64,
        "nextActions": [],
        "primaryHeadByPlatform": {"linux": "avalonia", "windows": "avalonia"},
        "registryCommit": "d" * 40,
        "registryRepository": "ArchonMegalon/chummer6-hub-registry",
        "releaseDecisionPath": "RELEASE_DECISION.json",
        "releaseDecisionSha256": "e" * 64,
        "releaseDecisionStatus": "stable_ready",
        "releaseVersion": "run-20260711-164915",
        "rolloutState": "public_stable",
        "status": "published",
        "supportOwner": "Chummer release engineering",
        "supportabilityState": "gold_supported",
    }


class PublicReleaseTruthPacketTests(unittest.TestCase):
    def build(self, payload: dict[str, object], snapshot: dict[str, object]) -> dict[str, object]:
        return MODULE.build_packet(
            payload,
            {},
            {},
            snapshot,
            {"snapshotSha256": "f" * 64},
            MODULE.CANONICAL_RELEASE_CHANNEL_SOURCE,
        )

    def test_gold_supported_posture_uses_snapshot_platform_scope(self) -> None:
        packet = self.build(release_payload(), authority())

        self.assertEqual(packet["release_posture"], "stable_ready")
        self.assertEqual(packet["required_platforms"], ["Linux", "Windows"])
        self.assertEqual(packet["available_platforms"], ["Linux", "Windows"])
        self.assertEqual(packet["missing_platforms"], ["macOS"])
        self.assertEqual(packet["phase_label"], "Gold-supported release")
        self.assertEqual(packet["primary_head"], "Chummer.Avalonia")

    def test_gold_supported_posture_fails_closed_without_stable_decision(self) -> None:
        snapshot = copy.deepcopy(authority())
        snapshot["releaseDecisionStatus"] = "preview_ready"

        packet = self.build(release_payload(), snapshot)

        self.assertEqual(packet["release_posture"], "preview_ready")
        self.assertEqual(packet["phase_label"], "Preview-ready release")
        self.assertIn("remaining work", packet["quality_gap_line"].lower())

    def test_manifest_missing_platform_flags_cannot_override_snapshot_scope(self) -> None:
        payload = release_payload()
        coverage = payload["desktopTupleCoverage"]
        assert isinstance(coverage, dict)
        coverage["missingRequiredPlatforms"] = ["windows"]
        coverage["complete"] = False

        packet = self.build(payload, authority())

        self.assertEqual(packet["missing_platforms"], ["macOS"])
        self.assertNotIn("Windows", packet["missing_platforms"])
        self.assertEqual(packet["release_posture"], "stable_ready")


if __name__ == "__main__":
    unittest.main()
