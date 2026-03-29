---
title: "Download"
source: "chummer-hub-registry/.codex-studio/published/RELEASE_CHANNEL.generated.json"
generated_by: "materialize_public_guide_bundle.py"
---

# Download

This page is generated from the registry-owned public release-channel projection plus the canonical downloads and auto-update policy.

## Current build matrix

- phase_label: Public-fit polish
- Preview channel: docker
- version: smoke-2026.03.24-linux-x64
- published_at: 2026-03-24T19:03:57Z
- status: published
- source: `chummer-hub-registry/.codex-studio/published/RELEASE_CHANNEL.generated.json`
- rollout_state: local_docker_preview
- supportability_state: local_docker_proven

Local release proof passed for: install_claim_restore_continue, build_explain_publish, campaign_session_recover_recap, report_cluster_release_notify. Claimed-device restore and bounded offline prefetch stayed grounded on the current shelf.

- known_issues: Preview caveats still apply, but the current shelf has recent install, claimed-device recovery, bounded offline prefetch, and support proof instead of only manifest presence.
- fix_availability: Only send fixed notices after the affected install can receive the published channel artifact now on the shelf.

### Windows

- No current published Windows artifact appears in the registry projection.

### Linux

- Avalonia Desktop Linux X64: archive
- download: /downloads/files/chummer-avalonia-linux-x64.tar.gz
- file_name: chummer-avalonia-linux-x64.tar.gz
- size: 40.0 MiB (41940379 bytes)
- access: open_public

### macOS

- macOS is not on the public shelf until a signed and notarized `.dmg` is promoted.

## Honest artifact format

- No installer artifact is published in the current registry projection, so the current shelf should describe the published archive/portable formats plainly instead of implying an installer exists.
- avalonia-linux-x64-archive: archive via /downloads/files/chummer-avalonia-linux-x64.tar.gz

## SHA256

- avalonia-linux-x64-archive: `196d25f2372b01b03f5082377e0895183803d8c2aade043f34c995e2931f31ff`

## Raw release fallback

- The registry-owned compatibility export `releases.json` remains the raw fallback for legacy/manual consumers.
- Public guide copy should still lead with the current promoted shelf instead of treating the raw manifest as the front door.
- Installer-first language and trust promises come from `PUBLIC_DOWNLOADS_POLICY.md`.
- Update behavior and rollback language come from `PUBLIC_AUTO_UPDATE_POLICY.md`.
- The public release shelf posture comes from `PUBLIC_RELEASE_EXPERIENCE.yaml`.

## Release proof

- status: passed
- generated_at: 2026-03-28T21:20:34Z
- base_url: https://chummer.run

### Journeys passed

- install_claim_restore_continue
- build_explain_publish
- campaign_session_recover_recap
- report_cluster_release_notify

### Proof routes

- /downloads/install/avalonia-linux-x64-installer
- /home/access
- /home/work
- /account/work
- /account/support
- /contact
