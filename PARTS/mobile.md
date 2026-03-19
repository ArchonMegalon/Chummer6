# Mobile

![Mobile banner](../assets/parts/mobile.png "the session shell for when your table refuses to stay in one physical century.")<br>_[the session shell for when your table refuses to stay in one physical century.](../assets/parts/mobile.png)_

**The part you feel at the table.**

This is your tactical HUD, the piece of gear that stays in your hand when the lead starts flying. It’s a local-first session shell that lives on your hardware, ensuring your dossier stays live even when the grid is ghosting you in the Barrens.

## You touch this when...

A character builder is for the safehouse; a mobile shell is for survival. It handles the heavy lifting of rule-checking and modifier stacks, providing 'Math Receipts' so you don't have to pause the action to prove your dice pool is legal.

## What it owns

- player shell and GM shell for live play
- local-first session ledger handling on the client side
- reconnect, replay, resume, and observer continuity on the play shell side
- offline/media caching for play use
- dedicated `/api/play/*` route consumption and play-shell integration
- installable PWA hardening for mobile/tablet play

## What it does not own

- workbench/browser/desktop builder UX
- engine/rules evaluation truth
- registry or publication moderation UX
- hosted orchestration ownership
- copied shared contracts or copied shared UI primitives

## What is happening now

We're hardening the event logs and offline queues because 'always-on' is a corpo lie. For the devs who think 'deterministic' is a personality trait, we’re making sure the engine runs exactly the same way every time, even if your battery is screaming for mercy.

## Go deeper

- [Program map](README.md)
- [Current phase](../NOW/current-phase.md)
- [Where to go deeper](../WHERE_TO_GO_DEEPER.md)
---

<sub>Updated: 2026-03-13</sub>
