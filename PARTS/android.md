# Native Android

A native Android app for building runners, playing at the table, and managing a campaign.

![Native Android guide art](../assets/parts/mobile.png)

## When you care

You want to open a runner, roll at the table, run a group, or review a campaign book in the native Android app.

## Why you care

The `chummer-android` app keeps the important Chummer work in familiar phone navigation, while local runner tools remain useful offline.

## What it looks like

- five clear destinations for Home, Build, Play, Campaign, and More
- linked online runners and groups open in native screens instead of the web app
- a GM can create or edit a group, copy or share an invite, and see the roster from the Campaign tab
- an invited player can sign in, choose or create a runner, and join with a runner ticket tied to that group
- Play Store updates stay inside the app; sideloaded builds explain the Play-owned update path without opening another app
- local dice, condition, notes, files, print, share, and Chronicle review remain available without turning the phone app into a web wrapper
- account deletion stays native and clears the device link only after all first-party erasure records are complete

## Limits today

- preview.7 is available only through Google Play Internal testing; the public store listing is not live
- Google Play still shows the temporary unreviewed package name; the saved listing and app-content changes were last recorded in review, and current console status still needs re-confirmation
- current source includes a distinct tablet composition, but it is not part of the released Play artifact; an iPhone version is not shipped
- the local phone and tablet journeys are representative rather than exhaustive, so they do not close the 1,775-row Chummer5 edit-parity inventory

## Current state

The `chummer-android` app is a native MAUI Shell, not a Blazor or WebView wrapper. Google Play accepted the exact-hash-approved preview.7 bundle and made version code 7 available to the two approved internal testers on August 14, 2026. A real-device Play install has not yet been recorded. Separately from that released bundle, current merged source produces one locally verified API 36 APK whose phone and distinct tablet profiles each pass 19 of 19 edit, navigation, save, reload, and process-restart checks against the same APK SHA-256 (935f8354c8ce4ea3e32bd1c5ff2efe8f1efffbb70bb612292080a555fe2a7b94); the repository Python suite passes 90 of 90 checks and the native build reports zero warnings and errors. This is local representative evidence, not evidence that the candidate was installed from Play or that every Chummer5-editable value is complete. Account linking fails closed when a grant or approval expires, invite links must match the expected secure Chummer route exactly, and local credentials clear only after the server record covers all five first-party erasure components.

## Go deeper

- [What is visible today](../NOW/public-surfaces.md)
- [Where to go deeper](../WHERE_TO_GO_DEEPER.md)
