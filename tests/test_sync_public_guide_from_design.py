from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LINUX_SOURCE_BUILD_POLICY = (
    REPO_ROOT.parent
    / "chummer-design"
    / "products"
    / "chummer"
    / "maintenance"
    / "LINUX_SOURCE_BUILD_PATH.md"
)
MODULE_PATH = REPO_ROOT / "scripts" / "sync_public_guide_from_design.py"
SPEC = importlib.util.spec_from_file_location("sync_public_guide_from_design", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"Unable to load module from {MODULE_PATH}")
guide_sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guide_sync)

_render_manifest = guide_sync._render_manifest
_sync_removable_file = guide_sync._sync_removable_file


class RenderWithStartHereTests(unittest.TestCase):
    def test_sync_files_include_black_ledger_newsroom_page(self) -> None:
        self.assertIn("BLACK_LEDGER_NEWSROOM.md", guide_sync.SYNC_FILES)

    def test_black_ledger_stays_out_of_primary_public_navigation(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        horizons = (REPO_ROOT / "HORIZONS" / "README.md").read_text(encoding="utf-8")
        newsroom = (REPO_ROOT / "BLACK_LEDGER_NEWSROOM.md").read_text(encoding="utf-8")

        self.assertNotIn("Open the Black Ledger command map", readme)
        self.assertNotIn("[Black Ledger Newsroom](BLACK_LEDGER_NEWSROOM.md)", readme)
        self.assertNotIn("[BLACK LEDGER](black-ledger.md)", horizons)
        self.assertNotIn("[Black Ledger](HORIZONS/black-ledger.md)", newsroom)
        self.assertFalse((REPO_ROOT / "HORIZONS" / "black-ledger.md").exists())

    def test_signal_deck_is_removable_when_design_omits_it(self) -> None:
        self.assertIn("SIGNAL_DECK.md", guide_sync.REMOVABLE_SYNC_FILES)
        self.assertNotIn("SIGNAL_DECK.md", guide_sync.SYNC_FILES)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            missing_source = tmp_path / "source" / "SIGNAL_DECK.md"
            destination = tmp_path / "dest" / "SIGNAL_DECK.md"
            destination.parent.mkdir(parents=True)
            destination.write_text("# Signal Deck\n", encoding="utf-8")
            failures: list[str] = []

            _sync_removable_file(missing_source, destination, False, failures)

            self.assertEqual([], failures)
            self.assertFalse(destination.exists())

    def test_sync_uses_generated_public_copy_without_legacy_rewrite_tables(self) -> None:
        self.assertFalse(hasattr(guide_sync, "TEXT_REWRITES"))
        self.assertFalse(hasattr(guide_sync, "START_HERE_TRANSFORMS"))
        self.assertFalse(hasattr(guide_sync, "_render_with_start_here"))


class RenderManifestTests(unittest.TestCase):
    def test_assets_from_source_manifest_are_preserved(self) -> None:
        source = """{
  "generated_by": "materialize_public_guide_bundle.py",
  "generated_from": "products/chummer/PUBLIC_GUIDE_EXPORT_MANIFEST.yaml",
  "assets": [
    "assets/hero/chummer6-hero.png"
  ],
  "status": "ok"
}
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            source_path = tmp_path / "manifest.generated.json"
            source_path.write_text(source, encoding="utf-8")
            for relative_path in (
                "assets/hero/chummer6-hero.avif",
                "assets/hero/chummer6-hero.webp",
                "assets/pages/horizons-index.avif",
            ):
                asset_path = tmp_path / relative_path
                asset_path.parent.mkdir(parents=True, exist_ok=True)
                asset_path.write_text("stub", encoding="utf-8")

            rendered = _render_manifest(source_path)

        self.assertIn('"assets/hero/chummer6-hero.png"', rendered)
        self.assertNotIn('"assets/hero/chummer6-hero.avif"', rendered)
        self.assertNotIn('"assets/hero/chummer6-hero.webp"', rendered)
        self.assertNotIn('"assets/pages/horizons-index.avif"', rendered)

    def test_generated_from_is_normalized_to_repo_relative_path(self) -> None:
        source = """{
  "generated_by": "materialize_public_guide_bundle.py",
  "generated_from": "/docker/chummercomplete/chummer-design/products/chummer/PUBLIC_GUIDE_EXPORT_MANIFEST.yaml",
  "status": "ok"
}
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "manifest.generated.json"
            source_path.write_text(source, encoding="utf-8")

            rendered = _render_manifest(source_path)

        self.assertIn('"generated_from": "products/chummer/PUBLIC_GUIDE_EXPORT_MANIFEST.yaml"', rendered)
        self.assertNotIn("/docker/chummercomplete/chummer-design/", rendered)

    def test_generated_from_windows_path_is_normalized_to_repo_relative_path(self) -> None:
        source = """{
  "generated_by": "materialize_public_guide_bundle.py",
  "generated_from": "C:\\\\work\\\\chummer-design\\\\products\\\\chummer\\\\PUBLIC_GUIDE_EXPORT_MANIFEST.yaml",
  "status": "ok"
}
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "manifest.generated.json"
            source_path.write_text(source, encoding="utf-8")

            rendered = _render_manifest(source_path)

        self.assertIn('"generated_from": "products/chummer/PUBLIC_GUIDE_EXPORT_MANIFEST.yaml"', rendered)
        self.assertNotIn("C:\\\\work\\\\chummer-design\\\\", rendered)

    def test_generated_from_repo_relative_path_without_leading_separator_is_preserved(self) -> None:
        source = """{
  "generated_by": "materialize_public_guide_bundle.py",
  "generated_from": "products/chummer/PUBLIC_GUIDE_EXPORT_MANIFEST.yaml",
  "status": "ok"
}
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "manifest.generated.json"
            source_path.write_text(source, encoding="utf-8")

            rendered = _render_manifest(source_path)

        self.assertIn('"generated_from": "products/chummer/PUBLIC_GUIDE_EXPORT_MANIFEST.yaml"', rendered)

    def test_generated_from_dot_prefixed_repo_relative_path_is_normalized(self) -> None:
        source = """{
  "generated_by": "materialize_public_guide_bundle.py",
  "generated_from": "./products/chummer/PUBLIC_GUIDE_EXPORT_MANIFEST.yaml",
  "status": "ok"
}
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "manifest.generated.json"
            source_path.write_text(source, encoding="utf-8")

            rendered = _render_manifest(source_path)

        self.assertIn('"generated_from": "products/chummer/PUBLIC_GUIDE_EXPORT_MANIFEST.yaml"', rendered)
        self.assertNotIn('"generated_from": "./products/chummer/', rendered)

    def test_generated_from_windows_dot_prefixed_repo_relative_path_is_normalized(self) -> None:
        source = """{
  "generated_by": "materialize_public_guide_bundle.py",
  "generated_from": ".\\\\products\\\\chummer\\\\PUBLIC_GUIDE_EXPORT_MANIFEST.yaml",
  "status": "ok"
}
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "manifest.generated.json"
            source_path.write_text(source, encoding="utf-8")

            rendered = _render_manifest(source_path)

        self.assertIn('"generated_from": "products/chummer/PUBLIC_GUIDE_EXPORT_MANIFEST.yaml"', rendered)
        self.assertNotIn('"generated_from": ".\\\\products\\\\chummer\\\\', rendered)

    def test_sync_files_keep_public_root_human_facing(self) -> None:
        self.assertIn("START_HERE.md", guide_sync.SYNC_FILES)
        self.assertIn("ONRAMP.md", guide_sync.SYNC_FILES)
        self.assertIn("SOURCE_BUILD_LINUX.md", guide_sync.SYNC_FILES)
        self.assertIn("SOURCE_BUILD_LINUX.md", guide_sync.SOURCE_OWNED_SYNC_FILES)
        self.assertIn(
            "RUNNER_PASSPORT.md",
            guide_sync.SYNC_FILES,
        )
        for internal_name in (
            "manifest.generated.json",
            "CHUMMER6_PUBLIC_RELEASE_TRUTH_PACKET.generated.json",
            "CHUMMER6_PUBLIC_GUIDE_TRUTH_AUDIT.generated.json",
            "CHUMMER6_PUBLIC_GUIDE_NEW_SECTIONS.generated.json",
            "CHUMMER6_GUIDE_GENERATOR_REGISTRY_ALIGNMENT.generated.json",
            "FINAL_CHUMMER6_DOCS_GENERATION_VERDICT.md",
        ):
            self.assertNotIn(internal_name, guide_sync.SYNC_FILES)
            self.assertIn(internal_name, guide_sync.INTERNAL_SYNC_FILES)
            self.assertIn(internal_name, guide_sync.STALE_ROOT_FILES)

    def test_onramp_horizon_page_is_removed_from_public_horizons(self) -> None:
        self.assertIn("HORIZONS/onramp.md", guide_sync.REMOVABLE_SYNC_FILES)

    def test_only_linux_source_build_page_is_source_owned_today(self) -> None:
        self.assertEqual({"SOURCE_BUILD_LINUX.md"}, guide_sync.SOURCE_OWNED_SYNC_FILES)
        self.assertNotIn("DOWNLOAD.md", guide_sync.SOURCE_OWNED_SYNC_FILES)
        self.assertNotIn("HELP.md", guide_sync.SOURCE_OWNED_SYNC_FILES)
        self.assertNotIn("README.md", guide_sync.SOURCE_OWNED_SYNC_FILES)
        self.assertEqual(
            {
                "SOURCE_BUILD_LINUX.md": {
                    "policy": "products/chummer/maintenance/LINUX_SOURCE_BUILD_PATH.md",
                    "reason": "Linux source-build behavior and user-facing instructions are owned in Chummer6.",
                }
            },
            guide_sync.SOURCE_OWNED_SYNC_METADATA,
        )

    def test_source_owned_linux_page_is_backed_by_design_maintenance_policy(self) -> None:
        policy_text = LINUX_SOURCE_BUILD_POLICY.read_text(encoding="utf-8")
        self.assertIn("Chummer6/SOURCE_BUILD_LINUX.md", policy_text)
        self.assertIn("This path has one executable implementation and one user-facing explanation.", policy_text)
        self.assertIn("Do not mirror the shell script into `chummer-design`.", policy_text)
        metadata = guide_sync.SOURCE_OWNED_SYNC_METADATA["SOURCE_BUILD_LINUX.md"]
        self.assertEqual("products/chummer/maintenance/LINUX_SOURCE_BUILD_PATH.md", metadata["policy"])
        self.assertIn("owned in Chummer6", metadata["reason"])

    def test_source_owned_linux_page_fails_closed_when_generated_copy_drifts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            source = tmp_path / "source" / "SOURCE_BUILD_LINUX.md"
            destination = tmp_path / "dest" / "SOURCE_BUILD_LINUX.md"
            source.parent.mkdir(parents=True, exist_ok=True)
            destination.parent.mkdir(parents=True, exist_ok=True)
            source.write_text("generated\n", encoding="utf-8")
            destination.write_text("canonical\n", encoding="utf-8")
            failures: list[str] = []

            guide_sync._sync_source_owned_file(source, destination, False, failures)

            self.assertEqual(
                [f"source-owned file drift: {destination} != {source}"],
                failures,
            )
            self.assertEqual("canonical\n", destination.read_text(encoding="utf-8"))

    def test_base_client_features_sync_outside_horizons(self) -> None:
        self.assertIn("FEATURES", guide_sync.SYNC_DIRS)
        for relative_path in (
            "community-hub.md",
            "edition-studio.md",
            "ghostwire.md",
            "local-co-processor.md",
            "nexus-pan.md",
            "quicksilver.md",
            "run-control.md",
        ):
            self.assertTrue((REPO_ROOT / "FEATURES" / relative_path).exists())
            self.assertFalse((REPO_ROOT / "HORIZONS" / relative_path).exists())


if __name__ == "__main__":
    unittest.main()
