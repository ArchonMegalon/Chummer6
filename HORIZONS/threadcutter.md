# THREADCUTTER

![THREADCUTTER banner](../assets/horizons/threadcutter.png "because every clever overlay eventually meets another clever overlay in a dark alley.")<br>_[because every clever overlay eventually meets another clever overlay in a dark alley.](../assets/horizons/threadcutter.png)_

**Snip the digital overlaps before your character sheet becomes a glitchy abstract masterpiece.**

_Status: Horizon only — future idea, not active build work._

## What problem does this solve?

Devs love to believe their Lua script is a delicate snowflake, ignoring the fact that you’re probably stacking it with twelve other scripts in a blizzard of bad dependencies. Most code is written as if it's the only thing running, hardcoding overrides that turn other mods into digital static. When two of these 'chosen one' scripts meet in a dark alley, your character sheet doesn't just break—it flatlines. Without a forensic tool to spot the turf war, your runner is just digital scrap waiting for a reboot.

## A real table scene

GM: "Roll Initiative. Why are you staring at your commlink like it's a live grenade?"
Player: "The sheet says I have 40 Initiative dice. I think my mods are... cooperating too much."
GM: "Did you install that 'Ultra-Reflexes' script on top of the 'Wired Reflexes' fix?"
Player: "Maybe? It's all just red text now."
GM: "Congrats, your nervous system is a feedback loop. Roll to not explode."
Player: "Hold on, Threadcutter just found the collision in the Lua stack. Snipping the extra threads."
GM: "Fix it fast, or the street doc is getting a new organ donor."

<p align="center"><img src="../assets/horizons/details/threadcutter-scene.png" alt="THREADCUTTER dialogue scene still" width="420"></p>


## Meanwhile, Chummer is doing this

- Scripters are pushing the boundaries of what the Lua engine can rewrite without a total crash.
- The long-range plan is stabilizing how multi-era rulepacks can talk to each other.
- Math receipts are being polished to show you exactly which mod is responsible for your current stats.

## Why that would be great

Threadcutter is the ultimate runtime auditor for your character’s soul. It treats your rule stack like a piece of high-end cyberware, identifying the exact point where two mods are fighting over the same data-port. Instead of a cryptic error message, you get a surgical view of the conflict and the tools to snip the problem before it flatlines your session. It turns 'the app crashed' into 'here is the exact script that tried to steal your Agility stats.'

## Why it is still a Horizon

This isn't in the active build pile yet because untangling three-way script collisions is like trying to defuse a bomb with a pair of chopsticks while a troll is punching you. It's a horizon goal—a piece of future-tech we're decrypting to ensure that when you finally get your hands on a fully moddable engine, you don't spend more time debugging your stats than you do dodging bullets. We're waiting for the core engine to be bulletproof before we start letting mods take potshots at it.

## What would need to exist first

- conflict reports
- migration previews
- apply and rollback receipts

## Pitch your own future

Got a sharper way to handle a digital knife-fight between mods? Drop your logic in the issue tracker.
---

<sub>Updated: 2026-03-13</sub>
