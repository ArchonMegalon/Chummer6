# NEXUS-PAN

![NEXUS-PAN banner](../assets/horizons/nexus-pan.png)

**On deck: one canon run board for the whole crew, not six conflicting saves and a prayer to the Matrix.**

_Status: Horizon only — future idea, not active build work._

## Why this would be wiz

On deck: one canon run board for the whole crew, not six conflicting saves and a prayer to the Matrix.

## The brutal truth

If your session state lives in scattered files, your table is one bad reconnect away from a rules-lawyer firefight. That is not cyberpunk; that is version-control cosplay.

## The use case

NEXUS-PAN is aimed at shared authority and local-first resilience: actions land as append-only events, offline players keep moving, and reconnecting devices replay back into the same canon state with receipts the GM can audit.

## What is the idea?

On deck: one canon run board for the whole crew, not six conflicting saves and a prayer to the Matrix.

## What problem does it solve?

Sessions want shared authority, resilient sync, and live state that survives dodgy networks and chaotic tables.

## Foundations first

- session authority profile
- append-only session events
- local-first sync and replay
- clean play API seams

## Which parts would it touch later?

- `play`
- `run-services`
- `core`
- `design`

## Why it waits

Because the play split still needs its event-log, cache, and sync foundations to become real before the dream gets chrome.
---

_Last synced: 2026-03-11_  
_Derived from: chummer6-design horizon guidance, current public shape_  
_Canonical source: chummer6-design_
