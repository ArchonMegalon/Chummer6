# Media Factory

**Render-only asset lifecycle.**

Media factory is where render jobs, previews, signed URLs, and asset lifecycle management should eventually live without dragging narrative policy, rules math, or provider sprawl in with them.

## Why it matters

It is still early. The right move is to keep it narrow and get the seam stable before trying to make it impressive.

## What it owns

- render queues
- storage adapters and signed URLs
- dedupe/retry and rendered asset lifecycle

## What it does not own

- lore retrieval
- session relay
- provider routing and rules math

## Want more?

- [Program map](README.md)
- [Current phase](../NOW/current-phase.md)
- [Where the real truth lives](../WHERE_THE_REAL_TRUTH_LIVES.md)

---

_Last synced: 2026-03-11_  
_Derived from: chummer6-design ownership matrix, owning repo README, Fleet state_  
_Canonical source: chummer6-design_
