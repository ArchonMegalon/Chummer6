# Mobile

![Mobile banner](../assets/parts/mobile.png "the session shell for when your table refuses to stay in one physical century.")<br>_[the session shell for when your table refuses to stay in one physical century.](../assets/parts/mobile.png)_

**The part you feel at the table.**

Mobile is the play-shell that lives on your glass when the lead starts flying. It’s a local-first PWA designed to survive the deepest basement Wi-Fi dead zones, bundling the deterministic Lua engine directly onto your device for zero-latency math and tactical HUDs that actually follow the books.

## You touch this when...

Web-devs love their 'always-online' clouds until the packets start dropping mid-combat. If your character sheet turns into a 404 the moment you step into a Faraday cage or a shitty game store basement, it’s not a tool—it’s a liability. We’re cutting the umbilical cord so your dice receipts and SR4 modifiers stay as rugged as your street-doc's cyber-repair kit.

## What it owns

- player and GM play shell
- local-first session state
- runtime stack consumption
- sync-friendly play flows

## What it does not own

- builder/workbench UX
- provider secrets
- copied shared interfaces

## What is happening now

We’re currently hardening the offline queueing and runtime cache. It’s less about pretty pixels right now and more about ensuring your event logs and session state don't desync when the Matrix goes dark. We're building the foundation for a play-shell that handles the math provenance so you can focus on the run.

## Go deeper

- [Program map](README.md)
- [Current phase](../NOW/current-phase.md)
- [Where to go deeper](../WHERE_TO_GO_DEEPER.md)
---

_Last synced: 2026-03-13_<br>
_Derived from: chummer6-design ownership map, current public shape, owning repo READMEs_<br>
_Canonical source: chummer6-design_
