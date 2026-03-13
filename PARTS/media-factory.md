# Media Factory

![Media Factory banner](../assets/parts/media-factory.png "render jobs belong here, not taped to whatever repo the dev had open at 2 a.m.")<br>_[render jobs belong here, not taped to whatever repo the dev had open at 2 a.m.](../assets/parts/media-factory.png)_

**Render-only asset lifecycle.**

Media Factory is the air-gapped industrial forge where render jobs and signed URLs live. It handles the heavy lifting of asset lifecycles so the core rules engine doesn't choke on your high-res street sam portraits.

## You touch this when...

Because dragging storage adapters and retry logic into the character sheet's math is a great way to make the grid crash when you're just trying to look at a gun. We keep the provider soup out of the simulation.

## What it owns

- render queues
- signed URLs and storage adapters
- dedupe/retry and asset lifecycle receipts

## What it does not own

- lore generation
- session relay
- provider routing and rules math

## What is happening now

We're keeping it in a sterile scaffold for now. Narrow and boring is the goal until the asset handshakes stop feeling like a glitchy deck and start feeling like a professional data-pipe.

## Go deeper

- [Program map](README.md)
- [Current phase](../NOW/current-phase.md)
- [Where to go deeper](../WHERE_TO_GO_DEEPER.md)
---

_Last synced: 2026-03-13_<br>
_Derived from: chummer6-design ownership map, current public shape, owning repo READMEs_<br>
_Canonical source: chummer6-design_
