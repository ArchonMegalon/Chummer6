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
- native group invites and Chronicle Studio approval steps alongside local dice, condition, notes, files, print, and share

## Limits today

- the signed Android preview is not Play-installable until Google accepts the pending upload-key reset and an internal-test install is proven
- the reusable coordinator leaves room for iPhone and tablet-specific shells, but those platform heads are not shipped yet

## Current state

The dedicated Android preview is now a native MAUI Shell rather than a Blazor or WebView wrapper. Its current signed API 36 candidate and native phone/tablet captures pass local release gates; Play upload and tester installation remain pending behind the submitted upload-key reset.

## Go deeper

- [What is visible today](../NOW/public-surfaces.md)
- [Where to go deeper](../WHERE_TO_GO_DEEPER.md)
