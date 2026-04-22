# GitHub Codex Review

PR: local://guide

Findings:
- [high] tests/test_sync_public_guide_from_design.py [tests] tests-hardcoded-checkout-path
`tests/test_sync_public_guide_from_design.py:9` sets `MODULE_PATH = Path("/docker/chummercomplete/Chummer6/scripts/sync_public_guide_from_design.py")`.; The previous test imported `scripts.sync_public_guide_from_design` normally from the repo; this change makes the suite depend on one specific filesystem location and will fail in any other checkout or CI workspace where that absolute path does not exist.
Expected fix: Load the script module via a repo-relative path or restore the normal import so the tests run from any checkout location, then keep the new manifest normalization assertions on top of that portable import path.
