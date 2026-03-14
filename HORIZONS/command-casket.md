# Command Casket

![Command Casket banner](../assets/horizons/command-casket.png "somebody definitely called this a tiny admin tweak right before it needed a coffin.")<br>_[somebody definitely called this a tiny admin tweak right before it needed a coffin.](../assets/horizons/command-casket.png)_

**Controlled operator actions with receipts and a burial plan for errors.**

_Status: Horizon only — future idea, not active build work._

## What problem does this solve?

The moment nobody can answer who approved a change, every serious admin action starts smelling like haunted button mashing. Important operator actions need to be explainable, reviewable, and reversible instead of dissolving into digital ghost stories or mystery-admin folklore.

## A real table scene

GM: Wait, why did the street sam just lose his cyberware bonuses mid-combat? Decker: I was just trying to fix his initiative tracker! GM: You 'fixed' it by zeroing his essence. Pop the casket. Decker: Scanning... okay, Casket ID 402-Beta. Reverting now. GM: Receipt verified. The Sam's wires hum back to life. Don't touch the kernel again. Sam: Can we maybe do this between firefights next time?

<p align="center"><img src="../assets/horizons/details/command-casket-scene.png" alt="Command Casket dialogue scene still" width="420"></p>


## Meanwhile, Chummer is doing this

- Hardening the Lua engine to ensure state-diffs actually make sense before they are committed. - Designing cryptographic seals that look like they belong on a high-security data vault, not a spreadsheet. - Mapping out multi-sig handshakes for when the GM needs to sign off on a Decker’s 'creative' house-ruling.

## Why that would be great

Command Casket turns every heavy-handed admin tweak into a surgical, auditable data capsule. No more 'oops' moments that require a full database restore. You get a requester, an approval token, and a pre-packaged rollback plan in one glowing amber container. It is the difference between guessing why the grid crashed and having a signed confession with an Undo button.

## Why it is still a Horizon

This is grid-scale architecture that needs a rock-solid foundation in the core engine. We are currently perfecting the deterministic logic and receipt-math in the primary repos before we start building the high-security vault to store them. It is a horizon goal because 'oops' should not be the final word in your campaign.

## What would need to exist first

- approval-aware workflows
- preview, apply, and rollback receipts
- auditable command capsules

## Pitch your own future

Give the grid a memory that does not hallucinate—because every ghost in the machine needs a paper trail.
---

_Last synced: 2026-03-13_<br>
_Derived from: chummer6-design horizon guidance, current public shape_<br>
_Canonical source: chummer6-design_
