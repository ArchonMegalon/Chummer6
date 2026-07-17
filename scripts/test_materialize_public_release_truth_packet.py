#!/usr/bin/env python3
from __future__ import annotations

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
        "status": "published",
        "channelId": "public_stable",
        "rolloutState": "public_stable",
        "supportabilityState": "gold_supported",
        "publishedAt": "2026-07-11T16:49:15Z",
        "knownIssueSummary": "Current release checks are clear for the promoted shelf.",
        "desktopTupleCoverage": {
            "requiredDesktopPlatforms": ["linux", "windows"],
            "requiredDesktopHeads": ["avalonia"],
            "promotedInstallerTuples": [
                {
                    "head": "avalonia",
                    "platform": "linux",
                    "rid": "linux-x64",
                    "artifactId": "linux-installer",
                },
                {
                    "head": "avalonia",
                    "platform": "windows",
                    "rid": "win-x64",
                    "artifactId": "windows-installer",
                },
            ],
            "desktopRouteTruth": [
                {"head": "blazor-desktop", "routeRole": "fallback"},
            ],
            "missingRequiredPlatforms": [],
            "missingRequiredHeads": [],
            "missingRequiredPlatformHeadPairs": [],
            "missingRequiredPlatformHeadRidTuples": [],
            "externalProofRequests": [],
            "complete": True,
        },
        "artifacts": [
            {
                "artifactId": "linux-installer",
                "head": "avalonia",
                "platform": "linux",
                "rid": "linux-x64",
                "kind": "installer",
                "compatibilityState": "compatible",
                "installAccessClass": "open_public",
            },
            {
                "artifactId": "windows-installer",
                "head": "avalonia",
                "platform": "windows",
                "rid": "win-x64",
                "kind": "installer",
                "compatibilityState": "compatible",
                "installAccessClass": "open_public",
            },
        ],
    }


class PublicReleaseTruthPacketTests(unittest.TestCase):
    def test_gold_supported_posture_uses_current_required_platform_scope(self) -> None:
        packet = MODULE.build_packet(release_payload(), {}, {}, "registry.json")

        self.assertEqual(packet["release_posture"], "gold_supported")
        self.assertEqual(packet["required_platforms"], ["Windows", "Linux"])
        self.assertEqual(packet["available_platforms"], ["Windows", "Linux"])
        self.assertEqual(packet["missing_platforms"], [])
        self.assertEqual(packet["phase_label"], "Gold-supported release")
        self.assertIn("gold-supported", packet["quality_gap_line"])
        self.assertNotIn("remaining work", packet["quality_gap_line"].lower())
        self.assertNotIn("preview", packet["short_release_summary"].lower())
        self.assertEqual(packet["known_issue_summary"], "No current download blocker is listed for these installers.")
        self.assertEqual(packet["fallback_heads"], ["Chummer.Blazor.Desktop"])

    def test_gold_supported_posture_fails_closed_when_supportability_drifts(self) -> None:
        payload = release_payload()
        payload["supportabilityState"] = "review_required"

        packet = MODULE.build_packet(payload, {}, {}, "registry.json")

        self.assertEqual(packet["release_posture"], "preview_or_review_required")
        self.assertEqual(packet["phase_label"], "Current release build")
        self.assertIn("remaining work", packet["quality_gap_line"].lower())

    def test_missing_required_platform_is_not_confused_with_out_of_scope_platforms(self) -> None:
        payload = release_payload()
        coverage = payload["desktopTupleCoverage"]
        assert isinstance(coverage, dict)
        coverage["missingRequiredPlatforms"] = ["windows"]
        coverage["complete"] = False
        payload["artifacts"] = [payload["artifacts"][0]]

        packet = MODULE.build_packet(payload, {}, {}, "registry.json")

        self.assertEqual(packet["missing_platforms"], ["Windows"])
        self.assertNotIn("macOS", packet["missing_platforms"])
        self.assertEqual(packet["release_posture"], "preview_or_review_required")


if __name__ == "__main__":
    unittest.main()
