from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "sync_public_guide_from_design.py"
SPEC = importlib.util.spec_from_file_location("sync_public_guide_from_design", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"Unable to load module from {MODULE_PATH}")
guide_sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guide_sync)

_render_manifest = guide_sync._render_manifest
_render_with_start_here = guide_sync._render_with_start_here
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

    def test_readme_start_here_links_are_unique(self) -> None:
        source = """# Chummer6

## Start here

- [Download](DOWNLOAD.md)
- [Status](STATUS.md)
- [What Chummer6 Is](WHAT_CHUMMER6_IS.md)
- [From Chummer5a to Chummer6](FROM_CHUMMER5A_TO_CHUMMER6.md)
- [From Chummer5a to Chummer6](FROM_CHUMMER5A_TO_CHUMMER6.md)
- [Help](HELP.md)
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "README.md"
            source_path.write_text(source, encoding="utf-8")

            rendered = _render_with_start_here(source_path, "README.md", "")

        self.assertEqual(
            rendered.count("[From Chummer5a to Chummer6](FROM_CHUMMER5A_TO_CHUMMER6.md)"),
            1,
        )

    def test_readme_rewrites_noisy_first_contact_labels(self) -> None:
        source = """# Chummer6

Use this guide to answer the practical questions first: what Chummer6 is, what is real today, what to download, and where to get help.

When you are ready for more, use: [How can I help](HOW_CAN_I_HELP.md), [Help](HELP.md), [Worlds and future work](HORIZONS/README.md).

## Product parts

Use [Worlds and future work](HORIZONS/README.md) for longer-running campaign lanes.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "README.md"
            source_path.write_text(source, encoding="utf-8")

            rendered = _render_with_start_here(source_path, "README.md", "")

        self.assertIn("[Campaign tools](HORIZONS/README.md)", rendered)
        self.assertIn("[Contact](CONTACT.md)", rendered)
        self.assertIn("## Campaign tools", rendered)
        self.assertNotIn("Worlds and future work", rendered)
        self.assertNotIn("How can I help", rendered)

    def test_readme_rewrites_internal_acceptance_bar_phrase(self) -> None:
        sources = (
            """# Chummer6

Preview proof, fallback routes, artifact explainers, and packet-detail artifacts can show real progress, but flagship wording is reserved for surfaces that independently clear the flagship acceptance bar.
""",
            """# Chummer6

Preview evidence and fallback routes can show real progress, but flagship wording is reserved for surfaces that independently clear the flagship acceptance bar.
""",
        )

        for source in sources:
            with tempfile.TemporaryDirectory() as tmpdir:
                source_path = Path(tmpdir) / "README.md"
                source_path.write_text(source, encoding="utf-8")

                rendered = _render_with_start_here(source_path, "README.md", "")

        self.assertIn("visitor can actually inspect and use", rendered)
        self.assertNotIn("flagship acceptance bar", rendered)
        self.assertNotIn("Preview evidence", rendered)

    def test_faq_rewrites_heading_and_body(self) -> None:
        source = """# FAQ

## If you want the behind-the-scenes details

### Where does the deeper plan live?

In the planning notes that shape the roadmap and the public guide.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "FAQ.md"
            source_path.write_text(source, encoding="utf-8")

            rendered = _render_with_start_here(source_path, "FAQ.md", "")

        self.assertIn("## If you want more detail", rendered)
        self.assertNotIn("## If you want the behind-the-scenes details", rendered)
        self.assertIn(
            "Start with [Where To Go Deeper](WHERE_TO_GO_DEEPER.md). It points to the optional deeper guide pages without sending most readers through internal planning material first.",
            rendered,
        )
        self.assertNotIn(
            "In the planning notes that shape the roadmap and the public guide.",
            rendered,
        )

    def test_download_rewrites_internal_acceptance_reference(self) -> None:
        source = """# Download

## What should I download first?

- Start with the installer for your platform.

## Current public download

- Claim boundary: Flagship wording is reserved for surfaces that currently satisfy FLAGSHIP_RELEASE_ACCEPTANCE.yaml; preview artifacts, proof cards, captions, packet siblings, artifact-factory explainers, and fallback routes do not earn that claim by proximity.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "DOWNLOAD.md"
            source_path.write_text(source, encoding="utf-8")

            rendered = _render_with_start_here(
                source_path,
                "DOWNLOAD.md",
                "## Current public download\n",
            )

        self.assertIn(
            "Claim boundary: That stronger wording only belongs on the main release surfaces after they are ready for visitors; preview artifacts, captions, packet siblings, artifact-factory explainers, and fallback routes do not inherit it just by sitting nearby.",
            rendered,
        )
        self.assertNotIn("FLAGSHIP_RELEASE_ACCEPTANCE.yaml", rendered)
        self.assertNotIn("proof cards", rendered)
        self.assertNotIn("public proof", rendered)


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
