# What Chummer6 Is

![What Chummer6 is banner](assets/pages/what-chummer6-is.png "product story first, architecture sermon later, assuming the dev can resist lecturing for five minutes.")<br>_[product story first, architecture sermon later, assuming the dev can resist lecturing for five minutes.](assets/pages/what-chummer6-is.png)_

Your chrome shouldn't come with a 'trust me' from your GM.

Chummer6 is a deterministic engine that treats your character sheet like a live, audited dossier. Built on a local-first architecture with scripted Lua logic, it provides explainable receipts for every single modifier on your screen. It functions as an installable web app (PWA) that stays on your device, ensuring you never lose access to your stats even when you're running silent in a matrix dead zone.

## What it is trying to become

Chummer6 is not just trying to be a character manager with nicer chrome. It is trying to become a toolkit that helps players and GMs:

- get a ruling quickly
- see why that ruling happened
- keep playing when the network misbehaves
- carry different rules eras without pretending they are identical
- handle odd table logic in code instead of folklore

## A real table moment

> **GM**<br>
> "You are wounded, sustaining, and standing in bad weather. Roll it."

> **Player**<br>
> "Why is my pool lower than I expected?"

> **Chummer6**<br>
> "Base 11. Wounds -1. Sustaining -1. Weather -1. Final 8."

> **GM**<br>
> "Good. We move."

That is the product story in miniature. Not "trust me, bro." Not "dig through source." Just a fast answer with enough proof to keep the table moving.

## What feels different from old Chummer habits

The project is leaning harder into explicit trust:

- same inputs should produce the same result
- the result should come with a readable receipt
- the session should survive local or offline reality
- the active rules and config stack should be visible
- the ugly edge cases should have a real extension lane

## The kinds of trust it wants to earn

- **Math trust:** the number should be reproducible.
- **Receipt trust:** the path to the number should be visible.
- **Session trust:** your table should not collapse because Wi-Fi had a mood.
- **Change trust:** custom rules, era differences, and future expansions should be legible instead of spooky.

## What you would actually notice on game night

- fewer "wait, why did that number move?" pauses
- fewer arguments that depend on memory or volume
- faster recovery when one device falls out of the session
- clearer separation between verified facts, inferred summaries, and made-up nonsense
- more honest labels about what is real now versus still moving

## Why there are multiple parts

The codebase is split because the product is getting bigger and more specialized. A rules engine, a prep workbench, a table-facing shell, hosted coordination, shared chrome, artifact handling, render jobs, and a blueprint repo all have different jobs. Keeping those seams honest is how the project avoids one giant haunted monolith.

If you want that map, go to [PARTS/README.md](PARTS/README.md).

Need the deeper split or implementation trail after the product story? Start with [PARTS/README.md](PARTS/README.md) or [WHERE_TO_GO_DEEPER.md](WHERE_TO_GO_DEEPER.md).
---

_Last synced: 2026-03-13_<br>
_Derived from: chummer6-design, current public shape_<br>
_Canonical source: chummer6-design_
