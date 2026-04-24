# GitHub Codex Review

PR: local://guide

Findings:
- [medium] scripts/sync_public_guide_from_design.py [tests] missing-readme-sanitization-regression-test
`scripts/sync_public_guide_from_design.py` now rewrites the README sentence `Preview proof, fallback routes, artifact explainers, and packet-detail artifacts can show real progress, but flagship wording is reserved for surfaces that independently clear the flagship acceptance bar.` into public-safe wording.; The source bundle currently contains that internal-style sentence in `/docker/chummercomplete/chummer-design/products/chummer/public-guide/README.md`, so the rewrite is active on the main public page path today.; `tests/test_sync_public_guide_from_design.py` adds coverage for the DOWNLOAD sanitization and manifest preservation, but it has no assertion that README sanitization happens or that the internal acceptance-bar phrasing is absent from rendered README output.
Expected fix: Add a regression test that feeds the current README source phrase through `_render_with_start_here(..., "README.md", ...)` and asserts the public-safe replacement is present while the acceptance-bar wording is removed.
