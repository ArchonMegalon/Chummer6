# NEXUS-PAN

![NEXUS-PAN banner](../assets/horizons/nexus-pan.png "Wi-Fi died; the table did not. That is the fantasy.")<br>_[Wi-Fi died; the table did not. That is the fantasy.](../assets/horizons/nexus-pan.png)_

**Stop treating your tactical data like a digital graveyard and start running a live mesh.**

_Status: Horizon only — future idea, not active build work._

## What problem does this solve?

A folder full of character files isn't a table; it's a quiet argument waiting to happen. The moment the GM asks 'who has the link?' and three people start scrolling through email attachments, the run is dead. We’re still treating character data like it is 2011, praying the 'Final_V2' PDF is actually the one with the spent Edge, while the basement Wi-Fi laughs at our tactical ambitions.

## A real table scene

GM: 'Host is going turtle. Everyone, slave your devices to the mesh, now.'
Street Sam: 'My commlink’s red-lining. Signal’s dropping.'
Decker: 'Relax. I’ve got the local sync pulsed. We’re a mesh now.'
GM: 'I’m seeing your physical tracks update on my HUD in real-time. Nice.'
Mage: 'Wait, I just took 3 boxes of stun. Did that hit everyone’s display?'
Street Sam: 'Got it. I’m already slinging the patch-kit stats.'
Decker: 'Wi-Fi's officially flatlined. Doesn't matter. The NEXUS is holding.'

<p align="center"><img src="../assets/horizons/details/nexus-pan-scene.png" alt="NEXUS-PAN dialogue scene still" width="420"></p>


## Meanwhile, Chummer is doing this

- Hardening the core engine to handle append-only event streams without melting your CPU.
- Refining the local-first sync logic so your phone doesn't throw a tantrum when it loses a single bar.
- Stress-testing the play API seams to ensure the GM’s 'god-view' stays authoritative but fair.

## Why that would be great

It turns your table into a live tactical environment. Instead of lonely islands of data, every device becomes a node in a resilient, shared reality. If the Rigger’s tablet dies, the data is already echoed across the mesh. It’s about local-first authority—meaning the math happens on your hardware, not in some laggy cloud, ensuring the dice results and state changes are deterministic, transparent, and immediate.

## Why it is still a Horizon

Syncing state across a chaotic table without a central server is a nightmare that usually leads to ghost data and corrupted saves. The devs are currently busy making sure the basic character math doesn't hallucinate before they try to make five different devices agree on who took the last bullet. We’re building the foundations of a long-range plan for session events that can survive a matrix crash—or just a really bad router.

## What would need to exist first

- session semantic canon
- runtime bundle canon
- explain provenance
- play-shell reliability

## Pitch your own future

If you’ve got a better way to wire a squad together without the lag, drop a line at the repository.
---

<sub>Updated: 2026-03-13</sub>
