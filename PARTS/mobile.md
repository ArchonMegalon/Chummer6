# Web/PWA/Play

The installable web companion and its PWA/Play delivery line.

![Web/PWA/Play guide art](../assets/parts/mobile.png)

## When you care

You use Chummer through an installable web experience or a browser-backed Play delivery path.

## Why you care

The `chummer6-mobile` lane keeps web, PWA, and Play-facing delivery together without borrowing native Android claims.

## What it looks like

- one Web/PWA/Play companion rather than a second native Android identity
- install and offline behavior that remains owned by the web delivery lane
- release evidence that is reported separately from native Android build and device evidence

## Limits today

- this is not the native Android application
- Web/PWA/Play evidence does not prove a native APK, API-level journey, or physical-device install

## Current state

The `chummer6-mobile` repository is the Web/PWA/Play delivery lane. It is separate from `chummer-android`; availability and evidence for either lane must be reported independently on the current status pages.

## Go deeper

- [What is visible today](../NOW/public-surfaces.md)
- [Where to go deeper](../WHERE_TO_GO_DEEPER.md)
