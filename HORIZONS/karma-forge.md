# Karma Forge

![Karma Forge banner](../assets/horizons/karma-forge.svg)

**Personalized rules without forked-code chaos.**

_Status: Horizon only — future idea, not active build work._

## The brutal truth

People love customizing the rules right up until those rules stop agreeing with each other and nobody can explain the damage calculation.

## The use case

You want a custom rules layer for your table. Instead of forking the app and praying, you slot in a controlled overlay stack that can be inspected, explained, previewed, and rolled back.

## What is the idea?

Karma Forge is a future rabbit hole worth documenting because it solves a real problem in a way that could make Chummer feel sharper, weirder, and more alive.

## What problem does it solve?

Players want house rules, variants, and personalized rule stacks without turning every table into a private fork nobody else can inspect.

## Foundations first

- runtime stack and fingerprint DTOs
- overlay receipts and conflict reports
- explain/provenance receipts
- clean shared interfaces

## Which parts would it touch later?

- `core`
- `play`
- `run-services`
- `hub-registry`
- `design`

## Why it waits

Because the split still needs its contract reset and seam cleanup. Fancy overlay power on top of fuzzy foundations is how you summon haunted software.
---

_Last synced: 2026-03-11_  
_Derived from: chummer6-design horizon guidance, current public shape_  
_Canonical source: chummer6-design_
