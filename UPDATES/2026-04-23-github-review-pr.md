# GitHub Codex Review

PR: local://guide

Findings:
- [high] DOWNLOAD.md [contracts] download-contract-file-leak
`DOWNLOAD.md` now says: `Flagship wording is reserved for surfaces that currently satisfy FLAGSHIP_RELEASE_ACCEPTANCE.yaml; ...`, which exposes an internal contract file and acceptance criterion in public-facing copy.; The required repo guide says this repo is `not a contract source` and lists `contract files` as out of scope, so this wording is a direct boundary violation/regression rather than a plain copy tweak.; `scripts/sync_public_guide_from_design.py` adds a rewrite for the analogous README sentence but leaves `DOWNLOAD.md` with no sanitizing rewrite, so the sync path does not protect against this leak recurring.
Expected fix: Rewrite the `DOWNLOAD.md` sentence in plain public language with no reference to internal acceptance files or criteria, and add the corresponding sync rewrite/coverage if this wording can arrive from the design source.
