# NEXUS-PAN

![NEXUS-PAN banner](../assets/horizons/nexus-pan.png "Wi-Fi died; the table did not. That is the fantasy.")

**One living table state, even when the signal gets cute.**

_Status: Horizon only - future idea, not active build work._

_Image idea: a rain-soaked table, one phone reconnecting, AR initiative markers hovering over coffee cups, and one player looking personally betrayed by Wi-Fi._

## What problem does this solve?

A real Shadowrun table is messy: one player is on a phone, one is on a tablet, the GM has too many tabs open, somebody's Wi-Fi dies, and suddenly half the table is arguing over whether the samurai already spent Edge. NEXUS-PAN is the idea of making the table state the truth instead of treating every device like a lonely little island.

## A real table scene

> Rain hits the windows, one phone just rejoined, and nobody wants a sync argument.
>
> The cafe Wi-Fi dies at the exact moment the firefight becomes interesting.
> **GM:** "Rain comes down hard. Visibility drops. Security just woke up."
> **Decker:** "My phone died. I missed the last two actions. It chose performance art."
> **Street Sam:** "I already burned one Edge and took 3 stun, right?"
> **Mage:** "And I am still sustaining that spell. Probably."
> **Chummer6:** "Decker device rejoined. Replayed 6 missed events. Current initiative: 11. Rain penalty applied."
> **GM:** "Good. Nobody do forensic accounting. Keep going."

## Meanwhile, Chummer is doing this

- keeping session state as one shared event stream
- recording who changed what and when
- replaying missed turns onto the rejoined device
- showing the same initiative, resources, and effects to everyone

## Why that would be great

Less desync, fewer trust fights, faster recovery from bad signal, and more time actually playing the scene instead of rebuilding it from memory.

## Why it is still a Horizon

This only works if session authority, event semantics, replay behavior, and offline recovery are solid enough to deserve trust. That foundation is still the prerequisite work.

## What would need to exist first

- session authority profile
- append-only session events
- local-first sync and replay
- clean play API seams

## Pitch your own future

If your table pain is different, head back to the [Horizons index](README.md) and pitch a better future mess.
---

_Last synced: 2026-03-13_  
_Derived from: chummer6-design horizon guidance, current public shape_  
_Canonical source: chummer6-design_
