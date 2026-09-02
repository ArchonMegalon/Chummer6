# Native Android

A native Android phone app with a wizard-led SR5 creation and Career preview.

![Native Android guide art](../assets/parts/mobile.png)

## When you care

You want to create or resume an SR5 runner on your phone and try the currently proven Career actions through Google Play Internal testing.

## Why you care

The `chummer-android` app turns character creation and Career changes into guided, rule-bound choices instead of presenting a universal property editor.

## What it looks like

- an SR5 Priority creation wizard with resumable prerequisites and typed Attributes, Skills, Qualities, Magic or Resonance, Resources, Gear, and Lifestyle choices
- SR5 Before Run, Playtime, and the currently exposed core Career phone workflows
- local save, reopen, and process-restart behavior exercised by the exact API 36 wizard evidence
- Play Store updates remain owned by Google Play rather than an in-app desktop updater

## Limits today

- preview.10 is available only through Google Play Internal testing; Production and a public store release remain inactive
- this is a limited SR5 phone-wizard beta, not Full Editing, Chummer5 parity, tablet support, SR4 or SR6 completion, or a Rook/live-avatar release
- the exact API 36 evidence covers three wizard journeys; it does not prove every declared wizard family or every Chummer5-editable value
- no physical-phone record for installing this exact bundle from Google Play has been recorded yet

## Current state

The `chummer-android` app is a native MAUI Shell, not a Blazor or WebView wrapper. Google Play made preview.10, version code 10, available to the two approved internal testers on September 3, 2026. The published AAB SHA-256 is 964d81b5d4463e0bd1c6de8172a7a12655e982897202b0151dccc69a566aaae1 and its sealed source-graph SHA-256 is 257ce53d912aea02416a64288029a589324e037464f76883d925b678b7364a24. Android main merge 1ce1ba8e2ebe289604b0392383bbe2d942726245 preserves the exact tested head f276d4af2d936760f6d21871f281b1f7dd50e261. Hosted API 36 run 33689337831 passed the SR5 Priority prerequisite, Career active-skill advance, Career weapon-fire, and exact three-journey aggregate gates; Full Editing was absent. This proves the limited wizard beta only. It does not prove a physical Play-managed install, all phone wizards, tablet support, exhaustive edit parity, or public/Production availability.

## Go deeper

- [What is visible today](../NOW/public-surfaces.md)
- [Where to go deeper](../WHERE_TO_GO_DEEPER.md)
