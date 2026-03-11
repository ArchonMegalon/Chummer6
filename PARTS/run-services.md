# Run Services

**The hosted API and orchestration layer.**

        Run Services is the hosted api and orchestration layer when the chrome is working and the excuses are not. Run Services is the network backbone: identity, relay, approvals, memory, hosted play APIs, previews, and the clever server-side machinery that should eventually feel completely unremarkable.

        ## Why you should care

        When Chummer needs to coordinate, publish, preview, or synchronize, this is where the adult supervision lives. If this part goes sideways, the whole run gets janky fast and somebody starts blaming the dev.

        ## What it owns

        - identity, relay, approvals, and memory
- hosted play APIs and orchestration
- preview/apply/rollback style server workflows

        ## What it does not own

        - engine math truth
- the long-term play shell
- render-only media execution

        ## What is happening now

        The mission is shrink-to-fit: keep the hosted boundary sharp and stop letting it impersonate every other part of the program. The short version: make it real, keep it sharp, and stop letting legacy duct tape cosplay as architecture.

        ## Go deeper

        - [Program map](README.md)
        - [Current phase](../NOW/current-phase.md)
        - [Where to go deeper](../WHERE_TO_GO_DEEPER.md)
---

_Last synced: 2026-03-11_  
_Derived from: chummer6-design ownership map, current public shape, owning repo READMEs_  
_Canonical source: chummer6-design_
