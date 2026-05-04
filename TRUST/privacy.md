# What Chummer stores, and what it does not

This is the simple privacy picture right now: what your account stores, what stays out, and how support and linked installs work.

## Your account keeps sign-in, preferences, and support together

Your Chummer account keeps your basic profile, linked sign-in methods, device access, support cases, and preview preferences together so you do not have to rebuild that history by hand.

## The download file is the same for everyone

When Chummer publishes a download, everyone gets the same file. Chummer does not build a private installer just for your account. If linked handoff is available, the account-aware piece is the short-lived handoff code that reconnects a local copy back to your account.

## Temporary sign-in tokens and raw secrets stay out of your account record

Short-lived third-party tokens stay on the machine or service using them. Your account keeps consent, support, and access records, not raw secret keys.

## Recognition should not force publicity

Participation and recognition remain optional layers. Private product use, private support, and a quiet account setup remain valid even while community pages exist.

## What is collected and how to stop it

Chummer keeps hosted Tier-2 telemetry opt-out by default for normal releases. You can disable hosted telemetry on first run and later in settings. Support and crash uploads remain explicit opt-in workflows.

- What we collect is bounded to install-level health and usability fields, not private campaign names or raw runner sheets.
- Opting out stops hosted telemetry emission while local install and support history remain on-device.
- Critical support workflows and explicit crash diagnostics stay explicit opt-in.
