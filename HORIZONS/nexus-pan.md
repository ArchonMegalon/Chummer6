# NEXUS-PAN

![NEXUS-PAN banner](../assets/horizons/nexus-pan.png "Wi-Fi died; the table did not. That is the fantasy.")<br>_[Wi-Fi died; the table did not. That is the fantasy.](../assets/horizons/nexus-pan.png)_

**Your table is a mesh, not a graveyard for static PDFs.**

_Status: Horizon only — future idea, not active build work._

## What problem does this solve?

A folder full of character files isn't a live table; it's a graveyard of stale data and 'Final_V4' naming conventions. Most tools today are fragile web-apps that hallucinate math the moment the GM’s basement Wi-Fi chokes on a soy-caf spill. We’ve been conditioned to accept 'lonely files' as a feature, but when the Street Sam’s deck de-syncs from the GM’s tracker, the run grinds to a halt for a manual math audit. You shouldn't need a PhD in version control just to track a Physical damage box.

## A real table scene

GM: "The Renraku Red Samurai drops a flash-pak. Everyone, Initiative." STREET SAM: "I’m at zero bars in this basement. Did my Wired Reflexes kick in?" DECKER: "Relax, omae. I’m seeing your sync-pulse on my screen." GM: "I just slid the tokens. Check your displays." STREET SAM: "Wait, my commlink just re-linked. The initiative pass is already there." ADEPT: "And I just spent the Edge. It’s live on the GM’s tracker." GM: "No lag, no 'did you save?'. We’re hot."

<p align="center"><img src="../assets/horizons/details/nexus-pan-scene.png" alt="NEXUS-PAN dialogue scene still" width="420"></p>


## Meanwhile, Chummer is doing this

- Hardening the Lua engine to ensure every 'sync' event produces the exact same math on every device. - Mapping out the 'Append-Only' event log so your character's history is a verifiable black box. - Designing the 'Ghost-Mode' buffer so you can keep playing offline and merge back into the timeline later.

## Why that would be great

NEXUS-PAN turns your gaming group into a resilient local mesh. It treats every roll and Nuyen spent as a ledger entry that replicates across the table in real-time. When the signal drops, the local-first architecture keeps the dice rolling; when you’re back on the grid, the state re-syncs seamlessly. It’s the 'World State' for your specific run, ensuring the GM and players are always looking at the same digital truth, even if your commlink is held together with duct tape.

## Why it is still a Horizon

Building a sync engine that doesn't hallucinate math or corrupt state is a massive architectural lift. We’re currently focused on making the Lua Core engine bulletproof and the SR4 ruleset deterministic. Once the brain is stable, we can build the nervous system that lets devices talk to each other without a central server breathing down their necks. We aren't interested in shipping a 'maybe it works' cloud solution—we’re building a table-ready mesh that actually survives a subway tunnel.

## What would need to exist first

- session authority profile
- append-only session events
- local-first sync and replay
- clean play API seams

## Pitch your own future

Got a better blueprint for a zero-trust table mesh? Drop your decker logic in the issue tracker.
---

_Last synced: 2026-03-13_<br>
_Derived from: chummer6-design horizon guidance, current public shape_<br>
_Canonical source: chummer6-design_
