# RULE X-RAY

![RULE X-RAY banner](../assets/horizons/rule-x-ray.png "every modifier gets dragged into the light like it owes the table money.")<br>_[every modifier gets dragged into the light like it owes the table money.](../assets/horizons/rule-x-ray.png)_

**Every digit gets a birth certificate. Drag your modifiers into the light like they owe the table money.**

_Status: Horizon only — future idea, not active build work._

## What problem does this solve?

Black-box math is the fastest way to kill a session. When the 'Magic Number' on your screen doesn't match the 'Book Number' in your head, trust evaporates. Most tools hide their logic-sins behind layers of UI-fluff, leaving GMs to guess which hardcoded hack or nested if-statement is eating the street samurai's dice pool.

## A real table scene

GM: "Roll Agility + Firearms. Threshold 3." SAMURAI: "My deck says I'm rolling 8. I should have 12." GM: "Did you count the wound penalties?" SAMURAI: "Yeah. And the smartlink. And the custom grip." GM: "Maybe it's the background count?" SAMURAI: "The app just says '8'. I guess I'll just die then."

<p align="center"><img src="../assets/horizons/details/rule-x-ray-scene.png" alt="RULE X-RAY dialogue scene still" width="420"></p>


## Meanwhile, Chummer is doing this

- Hardening the deterministic Lua engine for multi-era SR4 compatibility. - Mapping the 'Provenance Chain' to track every modifier from source to sheet. - Scrubbing hardcoded 'magic numbers' from the core logic prototype.

## Why that would be great

Rule X-Ray turns your character sheet into a tactical HUD with receipts. Click any number—from your recoil compensation to your lifestyle cost—and see the exact Lua script responsible for the result. It’s deterministic truth: no hallucinations, no 'because I said so' logic, just a clear chain of evidence for every buff, wound, and bad life choice in the stack.

## Why it is still a Horizon

The math has to be perfect before we bother making it pretty. We are currently prioritizing engine-level stability and local-first PWA architecture over the visual x-ray layer. We're busy cleaning up the technical debt of 'magic numbers' in the core engine to ensure that when you finally do click that 8, the receipt it hands you is actually worth the data it's printed on.

## What would need to exist first

- explain canon
- provenance receipts
- deterministic engine evaluation

## Pitch your own future

Stop guessing why your dice pool is shrinking and join the effort to give every rule a paper trail.
---

_Last synced: 2026-03-13_<br>
_Derived from: chummer6-design horizon guidance, current public shape_<br>
_Canonical source: chummer6-design_
