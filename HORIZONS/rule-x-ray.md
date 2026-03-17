# RULE X-RAY

![RULE X-RAY banner](../assets/horizons/rule-x-ray.png "every modifier gets dragged into the light like it owes the table money.")<br>_[every modifier gets dragged into the light like it owes the table money.](../assets/horizons/rule-x-ray.png)_

**Stop guessing why your dice pool just cratered. Drag every modifier into the light like it owes the table money.**

_Status: Horizon only — future idea, not active build work._

## What problem does this solve?

Shadowrun math is a jagged stack of bad life choices, chrome-plated buffs, and 'GM says so' penalties. Most tools just spit out a final number and expect you to trust the machine. When the math feels like voodoo, the game grinds to a halt while three people flip through PDFs to find out if a specific wound penalty stacks with a background count. Opaque math is the fastest way to kill the tension of a run.

## A real table scene

GM: "That's a -7 penalty on the hack, Neon. The noise in this sprawl is brutal."
Neon: "Minus seven? I'm literally sitting on a satellite uplink and running a signal filter."
GM: "The noise, the grid-spam, and your biofeedback wounds... it adds up, omae."
Neon: [Taps the glowing red dice pool total on his deck's HUD]
Neon: "Rule X-Ray's showing the receipts. The uplink is nullifying the spam entirely."
GM: "Wait, let me see that... Huh. The Lua trace says the uplink rule takes precedence over local noise."
Neon: "Exactly. I'm only at a -3. Now watch me melt this host."

<p align="center"><img src="../assets/horizons/details/rule-x-ray-scene.png" alt="RULE X-RAY dialogue scene still" width="420"></p>


## Meanwhile, Chummer is doing this

['- Hardening the Lua rules engine to ensure every modifier has a deterministic, traceable paper trail.', '- Polishing the mobile HUD to handle deep-nested math stacks without looking like a 20th-century tax form.', "- Refactoring legacy rule logic into clean, auditable packs that can't hide behind 'magic' constants."]

## Why that would be great

Rule X-Ray turns your character sheet from a static spreadsheet into a living, auditable dossier. Every number becomes a clickable provenance receipt, showing you exactly which Lua script, gear piece, or status effect is touching your dice pool. It’s the end of 'voodoo math'—if a modifier is there, the machine can prove why, giving GMs and players a single source of truth that doesn't require a degree in arcane accounting or a three-hour dive into the rulebooks.

## Why it is still a Horizon

This isn't a weekend UI patch for devs who think 'deterministic' is just a fancy word for 'it worked on my machine.' It requires a ground-up engine where every rule is a first-class citizen with a traceable ID. We're currently refactoring the core rulesets into clean Lua packs so that when you click a '4', the engine doesn't just say 'because,' it points to the exact line of code and the specific piece of gear that put it there. We're building the foundation of trust before we turn on the lights.

## What would need to exist first

- explain canon
- provenance receipts
- deterministic engine evaluation

## Pitch your own future

If you've ever lost a firefight to a math error, tell us how you'd want to see the receipts—the long-range plan is always looking for a sharper lens.
---

<sub>Updated: 2026-03-13</sub>
