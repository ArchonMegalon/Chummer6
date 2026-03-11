# Nexus Pan

**A live synced table instead of isolated character files.**

_Status: Horizon only — future idea, not active build work._

## What is the idea?
A live synced table instead of isolated character files.

## What problem does it solve?
Sessions want shared state, recoverable authority, and clean handoff between host, players, and devices.

## Why would that be exciting?
Because it would make Chummer feel more connected, more inspectable, and more alive without giving up deterministic runtime truth.

## What foundations does it need first?
- session authority profile
- append-only session events
- local-first sync
- play API canon

## Which repos would be touched later?
- `mobile`
- `hub`
- `core`
- `design`

## Why is this not for right now?
The program still needs the real play split and session event canon before this becomes more than a good idea.

---

_Last synced: 2026-03-11_  
_Derived from: chummer6-design horizon guidance, Fleet live status_  
_Canonical source: chummer6-design_
