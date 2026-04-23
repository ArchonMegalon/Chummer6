# GitHub Codex Review

PR: local://guide

Findings:
- [medium] DOWNLOAD.md [contracts] public-guide-contract-source-leak
`DOWNLOAD.md:22` now says flagship wording is reserved for surfaces that satisfy `FLAGSHIP_RELEASE_ACCEPTANCE.yaml`, which exposes an internal contract artifact name in public-facing copy.; The required guide context says this repo is 'not a contract source' and lists 'contract files' as out of scope (`/docker/chummercomplete/chummer-design/products/chummer/projects/guide.md`).
Expected fix: Rewrite that claim-boundary sentence in public language without naming internal contract files or internal acceptance artifacts.
