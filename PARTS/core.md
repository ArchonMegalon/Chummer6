# Core

![Core banner](../assets/parts/core.png "if the math looks cursed, this is where the curse gets cross-examined.")<br>_[if the math looks cursed, this is where the curse gets cross-examined.](../assets/parts/core.png)_

**The deterministic rules engine.**

Core is where the numbers stop bluffing. It is the deterministic heart of the machine, owning the engine runtime and reducer logic so the rest of your deck can stop arguing about what a rule actually means.

## You touch this when...

Because your GM's homebrew Excel macros are a nightmare of hidden math-sins. You need explainable receipts for every dice pool modifier, backed by raw Lua scripts that don't lie when the noise hits.

## What it owns

- engine runtime and reducer truth
- explain receipts and deterministic evaluation
- engine-facing shared interfaces

## What it does not own

- the hosted service layer
- the at-the-table shell
- render-only media work

## What is happening now

We are purifying the runtime. The current mission is to keep the engine mean, lean, and predictable—hardening the SR4 plugin and stripping away the legacy junk drawer until all that's left is engine truth.

## Go deeper

- [Program map](README.md)
- [Current phase](../NOW/current-phase.md)
- [Where to go deeper](../WHERE_TO_GO_DEEPER.md)
---

_Last synced: 2026-03-13_<br>
_Derived from: chummer6-design ownership map, current public shape, owning repo READMEs_<br>
_Canonical source: chummer6-design_
