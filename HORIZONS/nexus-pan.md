# NEXUS-PAN

![NEXUS-PAN banner](../assets/horizons/nexus-pan.png "Wi-Fi died; the table did not. That is the fantasy.")<br>_[Wi-Fi died; the table did not. That is the fantasy.](../assets/horizons/nexus-pan.png)_

**A live synced table instead of lonely files.**

_Status: Horizon only — future idea, not active build work._

## What problem does this solve?

Sessions want shared authority, resilient sync, and live state that survives dodgy networks and chaotic tables.

## A real table scene

Rain hits the windows, one phone just rejoined, and nobody wants a sync argument.

> **GM**<br>
> "Rain comes down hard. Visibility drops. Security just woke up."

> **Decker**<br>
> "My phone died. I missed the last two actions. It chose performance art."

> **Street Sam**<br>
> "I already burned one Edge and took 3 stun, right?"

> **Mage**<br>
> "And I am still sustaining that spell. Probably."

> **Chummer6**<br>
> "Decker device rejoined. Replayed 6 missed events. Current initiative: 11. Rain penalty applied."

> **GM**<br>
> "Good. Nobody do forensic accounting. Keep going."

<p align="center"><img src="../assets/horizons/details/nexus-pan-scene.png" alt="NEXUS-PAN dialogue scene still" width="420"></p>


## Meanwhile, Chummer is doing this

- keeping session state as one shared event stream
- recording who changed what and when
- replaying missed turns onto the rejoined device
- showing the same initiative, resources, and effects to everyone

## Why that would be great

Less desync, fewer trust fights, faster recovery from bad signal, and more time actually playing the scene instead of rebuilding it from memory.

## Why it is still a Horizon

The play-split's event-log and sync foundations are still being hardened to ensure zero-latency truth before we add the chrome.

## What would need to exist first

- session authority profile
- append-only session events
- local-first sync and replay
- clean play API seams

## Pitch your own future

If your table pain is different, head back to the [Horizons index](README.md) and pitch a better future mess.
---

_Last synced: 2026-03-13_<br>
_Derived from: chummer6-design horizon guidance, current public shape_<br>
_Canonical source: chummer6-design_
