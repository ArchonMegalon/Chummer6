# Core

**The deterministic rules engine.**

        Core is where the numbers stop bluffing. It owns the engine behavior, the reducer logic, and the boringly reliable parts that let the rest of Chummer stop arguing about what a rule actually means.

        ## Why you should care

        When a dice pool feels wrong or a result needs explaining, this is the part that should be able to say exactly why.

        ## What it owns

        - engine runtime and reducer truth
- explain receipts and deterministic evaluation
- engine-facing shared interfaces

        ## What it does not own

        - the hosted service layer
- the at-the-table shell
- render-only media work

        ## What is happening now

        The current mission is purification: keep the engine mean, lean, and predictable until it obviously means engine truth and not a junk drawer.

        ## Go deeper

        - [Program map](README.md)
        - [Current phase](../NOW/current-phase.md)
        - [Where to go deeper](../WHERE_TO_GO_DEEPER.md)
---

_Last synced: 2026-03-11_  
_Derived from: chummer6-design ownership map, current public shape, owning repo READMEs_  
_Canonical source: chummer6-design_
