# BLACKBOX LOADOUT

![BLACKBOX LOADOUT banner](../assets/horizons/blackbox-loadout.png "the software notices you forgot ammo before the NPCs do.")<br>_[the software notices you forgot ammo before the NPCs do.](../assets/horizons/blackbox-loadout.png)_

**The software notices you forgot ammo before the NPCs do.**

_Status: Horizon only — future idea, not active build work._

## What problem does this solve?

People rarely die in the sprawl because they lacked courage. They die because they forgot rope, spare clips, and basic self-respect. Most tools treat inventory like a static shopping list, leaving the 'idiot-check' to a distracted GM or a runner who hasn't slept in thirty-six hours.

## A real table scene

GM: "The HTR rotor-wash is rattling the skylight. You've got ten seconds to egress." Samurai: "Right. I grab the rappelling gear and hook into the anchor—" AR-HUD: *[Harmonic Red Pulse: MANIFEST ERROR]* Samurai: "Wait. Why is my internal display screaming at me?" Rigger: "Probably because you left the spool in the van, genius." Samurai: "I definitely bought it during the gear-up phase!" GM: "Buying it isn't carrying it. Hope you've got good health insurance for the forty-story drop."

<p align="center"><img src="../assets/horizons/details/blackbox-loadout-scene.png" alt="BLACKBOX LOADOUT dialogue scene still" width="420"></p>


## Meanwhile, Chummer is doing this

- Hardening the Lua core to ensure gear weights and bulk actually impact the manifest. - Mapping dependency trees so tactical mods require the right rails and power cells. - Refining the deterministic math receipts for offline-first session shells.

## Why that would be great

It moves the 'Oops' moment from the middle of a firefight to the safety of the hideout. Instead of arguing with the GM about what's physically in your pockets, the system runs a cold, cynical audit of your loadout against mission profiles. It transforms your character sheet from a ledger of junk into a verified mission manifest that keeps you breathing.

## Why it is still a Horizon

The logic engine needs to be smarter than a simple spreadsheet before it can reliably judge your life choices. We are building the deterministic foundations first—ensuring every stimpatch and sensor array has a verifiable receipt in the code. A 'Blackbox' that hallucinates your gear is just another way to get geeked, and we don't ship bugs that kill runners.

## What would need to exist first

- runtime stack manifests
- compatibility checks
- preview receipts

## Pitch your own future

Found a gear-sync edge case that usually gets you killed? Log it on the issue tracker and help us build a better safety net.
---

_Last synced: 2026-03-13_<br>
_Derived from: chummer6-design horizon guidance, current public shape_<br>
_Canonical source: chummer6-design_
