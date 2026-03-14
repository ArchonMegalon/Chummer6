# ALICE

![ALICE banner](../assets/horizons/alice.png "the simulation is here to hurt your feelings before reality does.")<br>_[the simulation is here to hurt your feelings before reality does.](../assets/horizons/alice.png)_

**Your build isn't a hero until the math says so. Let Alice hurt your feelings.**

_Status: Horizon only — future idea, not active build work._

## What problem does this solve?

Most runners build for the best-case scenario—assuming the GM forgets about recoil and the dice always land on sixes. Then the first HTR team drops from a suborbital, and suddenly your 'flavor choices' look like a suicide note. You need a clinical, deterministic way to find the exact moment your soak dice fail before you burn a character sheet.

## A real table scene

GM: 'HTR drops from the skylight. Full auto, wide burst.' Player: 'I've got this. My dodge pool is legendary.' GM: 'Alice says you have a 42% chance of losing an arm in the first three seconds.' Player: 'She's just a program! I'm rolling... oh. That's a lot of ones.' GM: 'Deterministic math is a fragging reaper, omae.' Player: 'Can I burn Edge to ignore the sim results?' GM: 'Alice doesn't negotiate with your ego.'

<p align="center"><img src="../assets/horizons/details/alice-scene.png" alt="ALICE dialogue scene still" width="420"></p>


## Meanwhile, Chummer is doing this

- Scripting the core engine to handle deterministic 'what-if' branches without choking on your house rules. - Stabilizing the SR4 plugin so your legacy builds can face modern simulation heat. - Refining the math-provenance popups so you can see exactly where the railgun breached your soak.

## Why that would be great

Alice is the antidote to 'main character syndrome.' Instead of guessing if your Street Sam can survive a frag grenade, you run a thousand-iteration lab harness and get a clinical heat map of your structural failures. It’s local-first, offline-ready, and uses the exact same Lua engine that powers your session, ensuring the math is identical to what happens at the table. No black boxes, just reproducible truth and receipts for every digit of damage.

## Why it is still a Horizon

The dev team is currently neck-deep in the 'boring stuff'—ensuring the basic Lua rulesets don't hallucinate when you try to calculate a simple melee hit. A high-fidelity stress tester like Alice requires a core engine that is 100% deterministic and bug-free across all multi-era rulesets. We’re still polishing the receipt engine before we build the machine that hands them to you at high velocity.

## What would need to exist first

- deterministic engine truth
- scenario harnesses with reproducible seeds
- explain receipts
- stable runtime stack fingerprints

## Pitch your own future

Think you can build a meat-grinder better than Alice? Show us your logic on the issue tracker.
---

_Last synced: 2026-03-13_<br>
_Derived from: chummer6-design horizon guidance, current public shape_<br>
_Canonical source: chummer6-design_
