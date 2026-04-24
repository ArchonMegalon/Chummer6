# GitHub Codex Review

PR: local://guide

Findings:
- [medium] tests/test_sync_public_guide_from_design.py [tests] tests-direct-exec-import-regression
The only local change replaces the repo-relative `importlib.util.spec_from_file_location(...)` loader with `from scripts import sync_public_guide_from_design as guide_sync`.; `python -m unittest tests.test_sync_public_guide_from_design -v` passes from the repo root, but `python tests/test_sync_public_guide_from_design.py` now fails with `ModuleNotFoundError: No module named 'scripts'` because direct execution sets `sys.path[0]` to `tests/`, not the repo root.; This is a regression from the previous repo-relative loader approach, which did not depend on the caller already having the repo root on `sys.path`.
Expected fix: Restore a repo-relative module load that works when the test file is executed directly, or otherwise add the repo root to `sys.path` before importing `scripts.sync_public_guide_from_design`.
