# Media Factory

![Media Factory banner](../assets/parts/media-factory.png)

        **Render-only asset lifecycle.**

        Media Factory is the render pit: queues, previews, signed links, dedupe, retries, and asset receipts, all in one lane. It handles the media hustle so story logic and rules math don’t get dragged into pipeline drama.

        ## Why you should care

        As Chummer gets more visual, this layer keeps run night from face-planting when assets spike or glitch. You get clean handoffs, auditable receipts, and fewer "who broke what" debugging séances.

        ## What it owns

        - render queues
- signed URLs and storage adapters
- dedupe/retry and asset lifecycle receipts

        ## What it does not own

        - lore generation
- session relay
- provider routing and rules math

        ## What is happening now

        Right now it’s scaffold-stage on purpose. Keep the scope tight, make the seam boringly reliable, then expand once the flow survives real-world chaos.

        ## Go deeper

        - [Program map](README.md)
        - [Current phase](../NOW/current-phase.md)
        - [Where to go deeper](../WHERE_TO_GO_DEEPER.md)
---

_Last synced: 2026-03-11_  
_Derived from: chummer6-design ownership map, current public shape, owning repo READMEs_  
_Canonical source: chummer6-design_
