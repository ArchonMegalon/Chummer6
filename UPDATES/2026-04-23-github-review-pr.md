# GitHub Codex Review

PR: local://guide

Findings:
- [medium] scripts/sync_public_guide_from_design.py [tests] missing-test-dot-prefixed-generated-from
`_render_manifest()` now explicitly drops `.` path segments (`part != "."`) at `scripts/sync_public_guide_from_design.py:199-203`, which is the substantive behavior change in this slice.; The added test at `tests/test_sync_public_guide_from_design.py:108-122` only covers an already-clean repo-relative path (`products/chummer/...`), not the newly handled `./products/chummer/...` or `.\\products\\chummer\\...` forms.; That leaves the exact feedback fix unguarded, so a later refactor could regress the new normalization path without any test failure.
Expected fix: Add a focused test that exercises dot-prefixed repo-relative `generated_from` values (POSIX and/or Windows form) and asserts they normalize to `products/chummer/...`.
- [low] tests/test_sync_public_guide_from_design.py [review] test-import-now-relies-on-namespace-package-resolution
The test previously loaded the target module from its exact file path; it now does `from scripts import sync_public_guide_from_design as guide_sync` at `tests/test_sync_public_guide_from_design.py:13`.; This works here because `sys.path` is adjusted, but `scripts` is not a regular package in this repo (`scripts/__init__.py` is absent), so the import now depends on namespace-package resolution for a very generic top-level name.
Expected fix: Prefer the previous file-path-based import, or make `scripts` an explicit package before relying on package import semantics in tests.
