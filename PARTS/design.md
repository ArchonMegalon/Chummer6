# Design

![Design banner](../assets/parts/design.png "the long-range planning room, still dangerously attractive to people who enjoy scope diagrams.")<br>_[the long-range planning room, still dangerously attractive to people who enjoy scope diagrams.](../assets/parts/design.png)_

**The long-range plan and ownership map.**

Think of this as the master tactical map for the entire sprawl. Design is where we draw the ownership lines between every bit and byte, ensuring the math stays deterministic even when your deck is redlining. It’s the source of truth that keeps the engine from free-styling your character's stats into a glitchy mess.

## You touch this when...

Because 'trust me' is a great way to end up in a body bag. We ditched the fragile spreadsheets for a Lua-scripted engine that treats rules like law. This tactical long-range plan ensures that when we add SR4 support or a new era's chrome, the whole system doesn't turn into a pile of spaghetti code that even a Tier-1 decker couldn't untangle. We’re building for the long haul, not just patching leaks with digital duct tape.

## What it owns

- cross-repo architecture and ownership
- milestone framing and split order
- review guidance and mirror rules

## What it does not own

- implementation
- dispatchable coding work
- human-only storytelling

## What is happening now

The current focus is locking down the multi-era logic and making sure the local-first engine works as flawlessly offline as a hardwired datajack. We're keeping the tactical map updated so the code monkeys stop improvising and start sticking to the script. If you find a rule that doesn't add up, hit the Issue Tracker and let us know where the signal is dropping.

## Go deeper

- [Program map](README.md)
- [Current phase](../NOW/current-phase.md)
- [Where to go deeper](../WHERE_TO_GO_DEEPER.md)
---

<sub>Updated: 2026-03-13</sub>
