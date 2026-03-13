# Core

![Core banner](../assets/parts/core.png "if the math looks cursed, this is where the curse gets cross-examined.")

**The deterministic rules engine.**

Core is where Shadowrun math stops bluffing. It takes the same inputs, runs the same logic, and is supposed to give you a ruling you can actually trust.

## You touch this when...

...the table asks, "why is my dice pool 11?" and somebody wants proof instead of volume.

Use case: the samurai thinks recoil got ignored, the mage thinks sustaining got applied twice, and you need the layer that can show base value, modifiers, scripted hooks, and final result in order.

## Why it matters

When the math is opaque, trust dies fast. Core is the part that turns rules debate into something inspectable instead of theatrical.

## What it owns

- engine runtime and reducer truth
- explain receipts and deterministic evaluation
- engine-facing shared interfaces

## What it does not own

- the hosted service layer
- the at-the-table shell
- render-only media work

## What is happening now

Current focus is sharp and boring in the best way: keep engine behavior deterministic, keep receipts readable, and keep Lua plus era-specific edge cases grounded in code instead of vibes.

## Go deeper

- [Program map](README.md)
- [Current phase](../NOW/current-phase.md)
- [Where to go deeper](../WHERE_TO_GO_DEEPER.md)
---

_Last synced: 2026-03-13_  
_Derived from: chummer6-design ownership map, current public shape, owning repo READMEs_  
_Canonical source: chummer6-design_
