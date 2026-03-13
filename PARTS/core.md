# Core

![Core banner](../assets/parts/core.png)

        **The deterministic rules engine.**

        Core is where Shadowrun math stops bluffing. It takes your inputs, runs the same logic every time, and gives you a ruling you can actually trust.

        ## Why you should care

        When the table argues about a dice pool, Core can show the chain: what modifier applied, where it came from, and why the outcome landed there. Less forum-lawyering, more play.

        ## What it owns

        - engine runtime and reducer truth
- explain receipts and deterministic evaluation
- engine-facing shared interfaces

        ## What it does not own

        - the hosted service layer
- the at-the-table shell
- render-only media work

        ## What is happening now

        Current focus is sharp and boring in the best way: keep engine behavior deterministic, keep receipts readable, and keep Lua-era edge cases (including SR4 paths) grounded in code, not vibes.

        ## Go deeper

        - [Program map](README.md)
        - [Current phase](../NOW/current-phase.md)
        - [Where to go deeper](../WHERE_TO_GO_DEEPER.md)
---

_Last synced: 2026-03-13_  
_Derived from: chummer6-design ownership map, current public shape, owning repo READMEs_  
_Canonical source: chummer6-design_
