# Mobile

![Mobile banner](../assets/parts/mobile.png "the table-facing shell, where signal loss stops being a personality test.")

**Table play that still respects reality.**

Mobile is the player and GM shell: the part you feel when the session is actually happening and nobody wants to do state tracking by hand.

## You touch this when...

...the run starts, somebody loses signal, and the table needs the software to keep up without becoming the problem.

Use case: a player reconnects mid-scene, the GM still needs the current initiative and effects to be right, and everyone would like to avoid forensic spreadsheet time.

## Why it matters

Table trust lives here. Actions need to queue locally, sync cleanly, and recover without turning every hiccup into a blame meeting.

## What it owns

- player and GM play shell
- local-first session state
- runtime stack consumption
- sync-friendly play flows

## What it does not own

- builder and workbench UX
- provider secrets
- copied shared interfaces

## What is happening now

Current focus is resilience over glitter: event logs, runtime cache, offline queueing, sync recovery, and a table-facing flow that keeps moving when network conditions act like a hostile NPC.

## Go deeper

- [Program map](README.md)
- [Current phase](../NOW/current-phase.md)
- [Where to go deeper](../WHERE_TO_GO_DEEPER.md)
---

_Last synced: 2026-03-13_  
_Derived from: chummer6-design ownership map, current public shape, owning repo READMEs_  
_Canonical source: chummer6-design_
