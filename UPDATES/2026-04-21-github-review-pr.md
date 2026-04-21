# GitHub Codex Review

PR: local://guide

Findings:
- [high] README.md [review] readme-start-here-duplicate-link
`git diff --stat main...HEAD` is empty, so this review target contains no committed fix for the requested feedback.; `README.md` still lists `From Chummer5a to Chummer6` twice in `## Start here` at lines 27 and 29.
Expected fix: Remove the duplicated `Start here` entry in `README.md`, include that change in the reviewed delta, and re-verify.
- [medium] tests/test_sync_public_guide_from_design.py [tests] missing-readme-start-here-duplication-test
`tests/test_sync_public_guide_from_design.py` only covers the FAQ rewrite path (lines 10-36).; There is no regression test asserting that generated or synced README navigation entries remain unique, which allowed the duplicate `From Chummer5a to Chummer6` entry to persist unnoticed.
Expected fix: Add a regression test that exercises the README render/sync path and asserts the `Start here` list does not contain duplicate links.
