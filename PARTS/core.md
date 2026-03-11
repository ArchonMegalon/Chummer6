# Core

**The deterministic rules engine.**

If Chummer is going to stay trustworthy, this is where that trust starts. Core owns the engine truth, the reducer logic, and the contract line that everything else should eventually consume instead of copying.

## Why you should care

Core is where the numbers have to stay honest. If this layer drifts, every shiny higher layer becomes harder to trust.

## What it owns

- engine runtime and reducer truth
- explain canon and deterministic behavior
- engine-facing contracts

## What it does not own

- hosted orchestration
- play shell ownership
- render execution

## What is happening now

Core is still carrying some transitional weight. The job now is purification: shrink it until it unmistakably means engine truth and little else.

## Go deeper

- [Program map](README.md)
- [Current phase](../NOW/current-phase.md)
- [Where the real truth lives](../WHERE_THE_REAL_TRUTH_LIVES.md)

---

_Last synced: 2026-03-11_  
_Derived from: chummer6-design ownership matrix, owning repo README, Fleet state_  
_Canonical source: chummer6-design_
