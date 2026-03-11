# Media Factory

**Render-only asset lifecycle.**

        Media Factory is render-only asset lifecycle when the chrome is working and the excuses are not. Media Factory is where render jobs, previews, signed URLs, dedupe, retry, and asset lifecycle management are supposed to live without dragging story policy, rules math, or provider soup along for the ride.

        ## Why you should care

        If Chummer gets more visual and media-heavy, this is the repo that stops the rest of the architecture from melting. If this part goes sideways, the whole run gets janky fast and somebody starts blaming the dev.

        ## What it owns

        - render queues
- signed URLs and storage adapters
- dedupe/retry and asset lifecycle receipts

        ## What it does not own

        - lore generation
- session relay
- provider routing and rules math

        ## What is happening now

        It is still scaffold-stage. The correct move is to keep it narrow until the seam is boringly stable. The short version: make it real, keep it sharp, and stop letting legacy duct tape cosplay as architecture.

        ## Go deeper

        - [Program map](README.md)
        - [Current phase](../NOW/current-phase.md)
        - [Where to go deeper](../WHERE_TO_GO_DEEPER.md)
---

_Last synced: 2026-03-11_  
_Derived from: chummer6-design ownership map, current public shape, owning repo READMEs_  
_Canonical source: chummer6-design_
