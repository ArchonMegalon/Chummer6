# GitHub Codex Review

PR: local://guide

Findings:
- [high] scripts/sync_public_guide_from_design.py [correctness] faq-heading-rewrite-noop
`TEXT_REWRITES["FAQ.md"]` at `scripts/sync_public_guide_from_design.py:199-203` replaces `"## If you want more detail"` with the exact same string, so it is a no-op.; The canonical source bundle still contains the old heading `## If you want the behind-the-scenes details` in `/docker/chummercomplete/chummer-design/products/chummer/public-guide/FAQ.md`, so the sync script will not apply the intended wording change on regeneration.; Current repo diff against `main` shows only the FAQ body text changed, not the heading, which is consistent with the rewrite table not matching the source heading.
Expected fix: Update the FAQ heading rewrite to match the actual upstream source text and regenerate/verify the synced FAQ output.
- [medium] scripts/sync_public_guide_from_design.py [tests] faq-rewrite-missing-regression-coverage
The repository has no automated coverage for this script change: `rg --files | rg 'test|tests|sync_public_guide_from_design'` returned only `scripts/sync_public_guide_from_design.py` and its `__pycache__` entry.; The heading rewrite bug above is exactly the kind of source-string mismatch a small regression test or equivalent automated check on rendered FAQ output should catch.
Expected fix: Add automated regression coverage for the FAQ transform path, including both the heading and body rewrites from the design bundle source.
