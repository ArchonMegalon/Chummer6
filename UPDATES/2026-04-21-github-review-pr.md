# GitHub Codex Review

PR: local://guide

Findings:
- [high] manifest.generated.json [review] review-no-committed-delta
`git diff --stat main...HEAD` is empty, so the branch under review contains no committed change relative to `main`.; `git status --short` shows only a local modification to `manifest.generated.json` (` M manifest.generated.json`), which is not part of the branch delta being reviewed.
Expected fix: Commit the intended manifest change into the branch (or otherwise include the fix in the `main...HEAD` diff), then re-run review.
