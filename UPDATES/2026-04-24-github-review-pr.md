# GitHub Codex Review

PR: local://guide

Findings:
- [high] scripts/sync_public_guide_from_design.py [contracts] manifest-assets-contract-drift
`_render_manifest()` now overwrites `manifest["assets"]` from `src.parent / "assets"` instead of preserving the source manifest payload.; The upstream source bundle at `/docker/chummercomplete/chummer-design/products/chummer/public-guide/manifest.generated.json` lists only PNG asset paths, but the synced repo manifest now advertises additional `.avif` and `.webp` files not present in the source manifest.; That means `--check` no longer validates repo manifest content against the source manifest contract; it validates against a locally recomputed file list instead. The new test `test_assets_are_derived_from_bundle_contents` locks in that drift.
Expected fix: Keep `manifest.generated.json` authoritative from the source bundle and only normalize `generated_from`; remove the filesystem-derived `assets` rewrite and replace the test with one that preserves the source manifest asset list.
