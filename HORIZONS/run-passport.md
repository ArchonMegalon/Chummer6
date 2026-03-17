# RUN PASSPORT

![RUN PASSPORT banner](../assets/horizons/run-passport.png "crossing rule borders without smuggling cursed assumptions in your coat.")<br>_[crossing rule borders without smuggling cursed assumptions in your coat.](../assets/horizons/run-passport.png)_

**Your runner's DNA doesn't change, but the local physics might. Carry a passport that actually speaks the language of the sprawl you're entering.**

_Status: Horizon only — future idea, not active build work._

## What problem does this solve?

Portability is the cheap high-ball promise made by devs who haven't seen a real table explode. Most 'export' features are just glorified text dumps that die the moment a GM introduces a house rule or a different era's gear. You end up with 'data rot'—stats that don't add up, modifiers with no parents, and a character sheet that is more 'trust me, bro' than actual math.

## A real table scene

GM: "Nice street sam. Where’d you pull the math for that Wired Reflexes stack?"
Player: "Seattle '07 legacy pack. Why?"
GM: "We're running Neo-Tokyo '12 rules here. Your initiative pass logic is practically contraband."
Player: "Hold on—flashing the Passport. Check the compatibility projection."
GM: [Scans holographic HUD] "Alright, looks like the engine auto-shunted the lag. You’re legal, but your dodge pool is taking a 2-point hit for local gravity. Deal?"
Player: "Better than a character rebuild. Let's roll."

<p align="center"><img src="../assets/horizons/details/run-passport-scene.png" alt="RUN PASSPORT dialogue scene still" width="420"></p>


## Meanwhile, Chummer is doing this

- Hardening the SR4 core engine to ensure the 'DNA' of a character is immutable regardless of the UI.
- Mapping the lineage of modifiers so the engine knows exactly which Lua script 'blessed' your Strength stat.
- Stress-testing the runtime stack to see how many conflicting house rules it takes to make the math cry.

## Why that would be great

This isn't just a file move; it is a digital dossier that carries its own rule-DNA. Run Passport gives you a verifiable lineage for every stat, gear piece, and karma point. When you walk into a new table, the engine runs a compatibility scan against the host's ruleset, highlighting exactly where your specialized cyberware might glitch or where your math might be considered 'smuggled contraband.' It is the difference between a character sheet and a character that actually belongs.

## Why it is still a Horizon

Because making math deterministic across five different rule eras and a dozen different house-rule 'interpretations' is the kind of task that turns dev brains into scorched silicon. We are still polishing the core engine's ability to 'show its work' without it looking like a 400-page tax audit. We would rather wait and give you a rock-solid identity than ship a 'portable' file that corrupts the moment it sees a different flavor of Lua script.

## What would need to exist first

- runtime stack profile
- fingerprint and lineage
- compatibility projections

## Pitch your own future

Got a house rule so weird it would break a passport officer's heart? Pitch us your most edge-case portability nightmares at the tracker.
---

<sub>Updated: 2026-03-13</sub>
