# Core

![Core banner](../assets/parts/core.png)

        **The deterministic rules engine.**

        Core is where Shadowrun math stops being a bar fight. Same inputs, same outcome, every time, with reducer logic that does not blink when the table gets loud. This is the rules engine truth layer, not a junk drawer for everything else.

        ## Why you should care

        When a roll looks cursed, Core can show the receipts step by step so players and GMs can see exactly how the result happened. That means fewer vibe-based rulings, faster disputes, and more trust that the crunch is doing what it says on the tin.

        ## What it owns

        - engine runtime and reducer truth
- explain receipts and deterministic evaluation
- engine-facing shared interfaces

        ## What it does not own

        - the hosted service layer
- the at-the-table shell
- render-only media work

        ## What is happening now

        Right now the mission is purification: keep Core lean, deterministic, and brutally clear about ownership. It owns runtime truth, reducer truth, and engine-facing shared interfaces, while hosted services, table-shell UX, and render-only media stay outside the blast radius.

        ## Go deeper

        - [Program map](README.md)
        - [Current phase](../NOW/current-phase.md)
        - [Where to go deeper](../WHERE_TO_GO_DEEPER.md)
---

_Last synced: 2026-03-11_  
_Derived from: chummer6-design ownership map, current public shape, owning repo READMEs_  
_Canonical source: chummer6-design_
