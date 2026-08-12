# Mobile and Android

A native phone app for building runners, playing at the table, and managing a campaign.

![Mobile and Android guide art](../assets/parts/mobile.png)

## When you care

You want to open a runner, roll at the table, run a group, or review a campaign book from your phone.

## Why you care

The Android app keeps the important Chummer work in familiar phone navigation, while local runner tools remain useful offline.

## What it looks like

- five clear destinations for Home, Build, Play, Campaign, and More
- linked online runners and groups open in native screens instead of the web app
- a GM can create or edit a group, copy or share an invite, and see the roster from the Campaign tab
- an invited player can sign in, choose or create a runner, and join with a runner ticket tied to that group
- Play Store updates stay inside the app; sideloaded builds show a clear manual update path
- local dice, condition, notes, files, print, share, and Chronicle review remain available without turning the phone app into a web wrapper

## Limits today

- the exact preview.6 bundle is locally signed and tested, but Google enforces an upload-key cooldown until 14 August 2026 at 03:29:49 UTC
- the internal track keeps its earlier build until preview.6 is approved by exact hash, uploaded, processed, and installed by a tester
- the shared app structure leaves room for iPhone and tablet-specific versions, but those versions are not shipped yet

## Current state

The Android app is a native MAUI Shell, not a Blazor or WebView wrapper. The exact signed preview.6 candidate passes 31 contract tests, clean eight-repository source validation, arm64 Release inspection, and a fresh API 36 native journey through Home, New Runner, Build, Play, Campaign, and More. Account linking fails closed when a grant or approval expires, and invite links must match the expected secure Chummer route exactly. Preview.6 has not been uploaded, processed, or installed from Play; the internal tester roster contains two approved accounts.

## Go deeper

- [What is visible today](../NOW/public-surfaces.md)
- [Where to go deeper](../WHERE_TO_GO_DEEPER.md)
