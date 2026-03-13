# THREADCUTTER

![THREADCUTTER banner](../assets/horizons/threadcutter.png "because every clever overlay eventually meets another clever overlay in a dark alley.")<br>_[because every clever overlay eventually meets another clever overlay in a dark alley.](../assets/horizons/threadcutter.png)_

**Snip the conflicts before they flatline your sheet.**

_Status: Horizon only — future idea, not active build work._

## What problem does this solve?

Sooner or later, two 'clever' changes will try to claim the same attribute at the same time, leading to silent logic collisions that brick your deck mid-combat.

## A real table scene

Two clever overlays just met and both think they are the main character.

> **GM**<br>
> "Can we run both mod packs?"

> **Player**<br>
> "Probably."

> **Chummer6**<br>
> "Conflict report generated. Both overlays modify the same recoil rule. One of them also lies about load order."

> **GM**<br>
> "Excellent. The software found the duel before the table did."

## Meanwhile, Chummer is doing this

- comparing overlays before they collide at runtime
- surfacing competing claims on the same seam
- showing what breaks, what wins, and what rolls back
- making conflict analysis a tool instead of a postmortem

## Why that would be great

Customization gets safer when the fight happens in a report first instead of in front of a live session.

## Why it is still a Horizon

The runtime stack and migration receipts must exist before the Threadcutter has anything honest to inspect; we don't guess at logic errors.

## What would need to exist first

- conflict reports
- migration previews
- apply and rollback receipts

## Pitch your own future

If your table pain is not clever mods drawing knives, the [Horizons index](README.md) has other future messes to browse.
---

_Last synced: 2026-03-13_<br>
_Derived from: chummer6-design horizon guidance, current public shape_<br>
_Canonical source: chummer6-design_
