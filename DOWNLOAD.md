# Download

This page describes the public preview shelf and the download formats that are actually available today.

## Current public build

- Current phase: Public-fit polish.
- Preview channel: docker.
- Current version: smoke-2026.03.24-linux-x64.
- Published: 2026-03-24T19:03:57Z.
- Shelf status: published.
- Rollout posture: local docker preview.
- Support posture: local docker proven.
- Support summary: Local release proof passed for: install_claim_restore_continue, build_explain_publish, campaign_session_recover_recap, report_cluster_release_notify. Claimed-device restore and bounded offline prefetch stayed grounded on the current shelf.
- Known issues: Preview caveats still apply, but the current shelf has recent install, claimed-device recovery, bounded offline prefetch, and support proof instead of only manifest presence.
- Fix availability: Only send fixed notices after the affected install can receive the published channel artifact now on the shelf.

### Windows

- No current published Windows download is on the public shelf.

### Linux

- Avalonia Desktop Linux X64: archive.
- Download path: `/downloads/files/chummer-avalonia-linux-x64.tar.gz`
- File name: `chummer-avalonia-linux-x64.tar.gz`
- Size: 40.0 MiB (41940379 bytes)
- Access: open public

### macOS

- macOS is not on the public shelf until a signed and notarized `.dmg` is promoted.

## Honest artifact format

- The current public shelf is archive-first right now. Do not promise an installer where one is not published.
- Avalonia Desktop Linux X64: archive via /downloads/files/chummer-avalonia-linux-x64.tar.gz

## Checksums

- Avalonia Desktop Linux X64: `196d25f2372b01b03f5082377e0895183803d8c2aade043f34c995e2931f31ff`

## Recent release proof

- Status: passed.
- Checked at: 2026-03-28T21:20:34Z.

### Covered flows

- install, claim, restore, and continue
- build, explain, and publish
- campaign session recovery and recap
- report clustering and release notification
