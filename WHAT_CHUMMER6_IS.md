# What Chummer6 Is

![What Chummer6 is banner](assets/pages/what-chummer6-is.png "product story first, architecture sermon later, assuming the dev can resist lecturing for five minutes.")

Chummer6 is becoming a clearer, more trustworthy, more table-friendly Shadowrun toolkit.

It is trying to make rules calls fast, explainable, and recoverable. That means deterministic outcomes, readable receipts, local-first session behavior, multi-era support, and scripted rule hooks for the weird cases that usually turn into forum trench warfare.

## What it is trying to become

Chummer6 is not just trying to be a character manager with nicer chrome. It is trying to become a toolkit that helps players and GMs:

- get a ruling quickly
- see why that ruling happened
- keep playing when the network misbehaves
- carry different rules eras without pretending they are identical
- handle odd table logic in code instead of folklore

## A real table moment

**GM:** "You are wounded, sustaining, and standing in bad weather. Roll it."
**Player:** "Why is my pool lower than I expected?"
**Chummer6:** "Base 11. Wounds -1. Sustaining -1. Weather -1. Final 8."
**GM:** "Good. We move."

That is the product story in miniature. Not "trust me, bro." Not "dig through source." Just a fast answer with enough proof to keep the table moving.

## What feels different from old Chummer habits

The project is leaning harder into explicit trust:

- same inputs should produce the same result
- the result should come with a readable receipt
- the session should survive local/offline reality
- the active rules and config stack should be visible
- the ugly edge cases should have a real extension lane

If older Chummer habits taught you to expect one giant opaque box, this is trying to be the opposite: sharper seams, clearer proof, and less mystery math.

## The kinds of trust it wants to earn

- **Math trust:** the number should be reproducible.
- **Receipt trust:** the path to the number should be visible.
- **Session trust:** your table should not collapse because Wi-Fi had a mood.
- **Change trust:** custom rules, era differences, and future expansions should be legible instead of spooky.

## Why there are multiple parts

The codebase is split because the product is getting bigger and more specialized. A rules engine, a prep workbench, a table-facing shell, hosted coordination, shared chrome, artifact handling, render jobs, and a blueprint repo all have different jobs. Keeping those seams honest is how the project avoids one giant haunted monolith.

If you want that map, go to [PARTS/README.md](PARTS/README.md).

## What this repo is

This repo is the friendly public guide to that wider program. It is here to explain the product in plain language, show what is real now versus future-looking, and help humans get oriented before they go hunting through deeper repos.
---

_Last synced: 2026-03-13_  
_Derived from: chummer6-design, current public shape_  
_Canonical source: chummer6-design_
