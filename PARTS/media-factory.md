# Media Factory

![Media Factory banner](../assets/parts/media-factory.png "the render pipeline, where aesthetics meet logistics and both get audited.")

**Render jobs in, assets out, receipts intact.**

Media Factory is the render-only lane: job queues in, previews out, links signed, and every generated asset leaves a trail behind it.

## You touch this when...

...a screen or workflow needs generated visual output and you do not want that concern leaking all over rules logic or session flow.

Use case: a render job needs to produce an asset preview or export artifact without dragging the rest of the stack into storage and retry chaos.

## Why it matters

If asset generation is sloppy, every other seam pays for it. Media Factory exists to keep render complexity contained and inspectable.

## What it owns

- render queues
- signed URLs and storage adapters
- dedupe, retry, and asset lifecycle receipts

## What it does not own

- lore generation
- session relay
- provider routing and rules math

## What is happening now

This is still deliberate scaffold work. The goal is a narrow, boringly reliable boundary before anyone gets cute with visuals.

## Go deeper

- [Program map](README.md)
- [Current phase](../NOW/current-phase.md)
- [Where to go deeper](../WHERE_TO_GO_DEEPER.md)
---

_Last synced: 2026-03-13_  
_Derived from: chummer6-design ownership map, current public shape, owning repo READMEs_  
_Canonical source: chummer6-design_
