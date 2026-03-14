# Tactical Pulse

![Tactical Pulse banner](../assets/horizons/tactical-pulse.png "shared situational awareness for the exact moment everyone swears they were paying attention.")<br>_[shared situational awareness for the exact moment everyone swears they were paying attention.](../assets/horizons/tactical-pulse.png)_

**Sync your team's sensors before the noise hits the fan.**

_Status: Horizon only — future idea, not active build work._

## What problem does this solve?

Modern combat is a data-firehose that usually ends with the Samurai shooting a dead guard while the Mage is busy recalculating a visibility penalty. Most 'tactical' tools are just static lists that fail the moment the first grenade goes off, leaving the GM to repeat the same three threat locations every single initiative pass.

## A real table scene

GM: 'The HTR squad is stacking up on the loading dock.' Street Sam: 'Wait, are they behind the crates or the van?' Mage: 'I already pinged the van on the AR layer, look at your HUD.' Decker: 'The Pulse has them at 10 meters and closing. I'm slaving the door lock now.' Street Sam: 'Copy that. Pulse shows a clear line of fire. Fragging 'em.' GM: 'Nice. Everyone's initiative just synced. Let’s dance.'

<p align="center"><img src="../assets/horizons/details/tactical-pulse-scene.png" alt="Tactical Pulse dialogue scene still" width="420"></p>


## Meanwhile, Chummer is doing this

- Hardening the event-driven state sync to ensure 'Local-First' doesn't mean 'Local-Only.' - Architecting session authority envelopes so your decker can't 'accidentally' edit the Boss's HP. - Scraping the barnacles off the engine to make room for high-contrast tactical vectors.

## Why that would be great

It turns the table from a group of people staring at separate papers into a coordinated strike team. Imagine a shared situational awareness where the GM's 'theater of the mind' is backed by hard, synced data—no more arguing about who saw what or where the grenade actually landed when the lights went out.

## Why it is still a Horizon

Real-time sync is a meat-grinder for code stability, and we refuse to ship a 'Pulse' that skips beats or desyncs your team into different dimensions. We are currently perfecting the deterministic Lua engine to ensure the math stays rock-solid before we try to broadcast it across the grid.

## What would need to exist first

- session authority
- event envelopes
- local-first sync
- evidence-grounded summaries

## Pitch your own future

Think you can optimize the tactical data-flow better than a bunch of burned-out code-monkeys? Drop a ping in the issue tracker and show us the ghost in your machine.
---

_Last synced: 2026-03-13_<br>
_Derived from: chummer6-design horizon guidance, current public shape_<br>
_Canonical source: chummer6-design_
