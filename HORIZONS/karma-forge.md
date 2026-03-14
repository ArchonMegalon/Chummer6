# Karma Forge

![Karma Forge banner](../assets/horizons/karma-forge.png "house rules with receipts, not forked-code folklore and a group chat apology.")<br>_[house rules with receipts, not forked-code folklore and a group chat apology.](../assets/horizons/karma-forge.png)_

**House rules with receipts, not forked-code folklore and a group chat apology.**

_Status: Horizon only — future idea, not active build work._

## What problem does this solve?

Most house rules are 'trust me bro' math or private forks that rot the moment the main repo updates. You change one line of damage logic in a local file, and suddenly your street sam is rolling 40 dice because of a leaked variable. Nobody—including you—can find the bug without a debugger and a prayer, turning your game night into an impromptu QA session for your own spaghetti code.

## A real table scene

GM: 'Wait, why is your recoil compensation higher than the gun’s barrel length?' Player: 'Oh, I patched the core logic to use my house-rule strength-to-recoil ratio.' GM: 'Show me the math. Right now.' Player: 'Uh... it’s in a private branch on my deck. Somewhere in the CharacterModel logic?' GM: 'Great. We’re pausing the run while you play detective in your own mess.' Table: (Collective sigh of digital exhaustion) Player: 'Found it! I think I forgot to carry the one in the Lua bridge.'

<p align="center"><img src="../assets/horizons/details/karma-forge-scene.png" alt="Karma Forge dialogue scene still" width="420"></p>


## Meanwhile, Chummer is doing this

["- Architecting a runtime stack that respects rule priority instead of just 'last write wins.'", '- Perfecting overlay fingerprinting so you know exactly which logic-chip broke the math.', "- Designing 'Explain-Receipt' UI so every +1 modifier has a searchable birth certificate."]

## Why that would be great

It turns house rules from a coding nightmare into a tactical slotting system. You don't fork the engine; you slot a Lua-etched logic module into the stack. If the math smells wrong, you pull the receipt, check the conflict report, and toggle the overlay without ever touching the core source. It’s the difference between performing open-heart surgery on the app and simply swapping a cyberdeck module mid-run.

## Why it is still a Horizon

Building a rules engine that allows arbitrary logic injection without turning into a security sinkhole or a performance black hole takes surgical precision. We are mapping the Math-Provenance pathways to ensure that when a rule changes, every downstream calculation knows why and where it came from. It is high-stakes logic-smithing, and we aren't firing up the forge until the logic-crystals stop cracking under the pressure of edge-case math.

## What would need to exist first

- runtime stack and fingerprint DTOs
- overlay receipts and conflict reports
- explain/provenance receipts
- clean shared interfaces

## Pitch your own future

Ready to rebuild the physics of the Sixth World? The forge is heating up.
---

_Last synced: 2026-03-13_<br>
_Derived from: chummer6-design horizon guidance, current public shape_<br>
_Canonical source: chummer6-design_
