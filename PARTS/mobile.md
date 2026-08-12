# Mobile and Android

Native build, play, and campaign work without wrapping the website.

![Mobile and Android guide art](../assets/parts/mobile.png)

## When you care

You want to build or open a runner, roll at the table, manage a group, or review a campaign book from a phone.

## Why you care

The dedicated Android client keeps the full Chummer workflow available in platform-native navigation while local runner work remains useful offline.

## What it looks like

- five short native destinations for Home, Build, Play, Campaign, and More
- account-linked online runners and groups open inside the app instead of handing off to the PWA
- native group invites and Chronicle Studio approvals plus a digest-bound operator handoff alongside local dice, condition, notes, files, print, and share

## Limits today

- preview.5 source is newer than the sealed preview.4 bundle; Google enforces a post-reset upload cooldown until 14 August 2026 at 03:29:49 UTC, and preview.1 remains on the tester track until a new exact bundle is signed, uploaded, and installed
- the reusable coordinator leaves room for iPhone and tablet-specific shells, but those platform heads are not shipped yet

## Current state

The dedicated Android preview is a native MAUI Shell rather than a Blazor or WebView wrapper. Preview.5 source passes 31 contracts, its native compile gate, and an x64 MAUI build; it adds native privacy guidance and a kept in Chummer Chronicle operator handoff. Preview.4 is retained as signed historical evidence, not the next upload. Google blocks the replacement certificate until 14 August 2026 at 03:29:49 UTC, preview.1 remains active, the selected internal list contains two tester entries, and no preview.5 installation is claimed.

## Go deeper

- [What is visible today](../NOW/public-surfaces.md)
- [Where to go deeper](../WHERE_TO_GO_DEEPER.md)
