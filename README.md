# Chummer6

![Chummer6 hero banner](assets/hero/chummer6-hero.png "table truth, wet sleeves, and one troll charm the dev better not lose again.")<br>_[table truth, wet sleeves, and one troll charm the dev better not lose again.](assets/hero/chummer6-hero.png)_

> **Chummer6: The Engine of the Street.**
>
> Ditch the glitchy spreadsheets. Chummer6 is the high-fidelity engine your character deserves, built with deterministic logic that doesn't break when the noise hits.

If you only need the one-sentence pitch, it is this: Chummer6 is trying to help players and GMs answer "what just happened?" fast enough that the run keeps moving.

## Pick your path

- **I am new here:** [Start Here](START_HERE.md)
- **Give me the product story:** [What Chummer6 is](WHAT_CHUMMER6_IS.md)
- **Tell me what is real today:** [Current status](NOW/current-status.md)
- **Show me the parts when I actually care:** [Program map](PARTS/README.md)
- **Show me the future rabbit holes:** [Horizons](HORIZONS/README.md)
- **Point me at the deeper source material:** [Where to go deeper](WHERE_TO_GO_DEEPER.md)

## What this means at a real table

> **GM**<br>
> "Rain, noise, and recoil all apply here."

> **Player**<br>
> "Then why did my pool drop to 9?"

> **Chummer6**<br>
> "Base 11. Rain -1. Wounds -1. Recoil -1. Final 9."

We're overhauling how runners manage their lives. Instead of hardcoded math-sins, we use scripted Lua rulepacks that explain their work. Every modifier on your sheet comes with a 'receipt'—a traceable line of logic showing exactly why your dice pool is what it is. We're currently focused on hardening the SR4 ruleset and ensuring the whole system works offline, so your data stays on your deck where it belongs.

## Why this is worth watching

The grid is live. We're currently jacking in SR4 support and refining the local-first play experience.

- It supports multi-era rulesets plainly
- Every modifier is a traceable receipt
- Offline-first PWA logic
- No hardcoded math-sins

If that sounds like your kind of software, the next stop is [What Chummer6 is](WHAT_CHUMMER6_IS.md).

## What is happening right now

Right now the crew is doing trust work, not bolting neon spoilers onto half-built engines.
Legacy math-clutter vs. clean, scripted deterministic certainty.

Current focus:
- Hardening the SR4 ruleset plugin
- Optimizing Lua rule-pack delivery
- Polishing the mobile workbench UX
- keep public previews honestly labeled until they become the real thing

- [Current phase](NOW/current-phase.md)
- [Current status](NOW/current-status.md)
- [Public surfaces](NOW/public-surfaces.md)

## When you want the map

You do not need the seam map first, but it is here when you need it:

- **Rules truth** lives in [Core](PARTS/core.md)
- **Prep and inspect** lives in [UI](PARTS/ui.md)
- **Table play** lives in [Mobile](PARTS/mobile.md)
- **Online coordination** lives in [Hub](PARTS/hub.md)
- **Shared chrome** lives in [UI Kit](PARTS/ui-kit.md)
- **Artifacts and compatibility** live in [Hub Registry](PARTS/hub-registry.md)
- **Render jobs** live in [Media Factory](PARTS/media-factory.md)
- **Blueprint truth** lives in [Design](PARTS/design.md)

If you want the full guided version, read the [Program map](PARTS/README.md).

## Future rabbit holes

Beyond the current grid, we're tracking intel on deeper simulation energy—think fully scripted gear-logic and dossiers that feel as heavy as a briefcase full of nuyen.

- [Horizons index](HORIZONS/README.md)

## POC shelf

![POC warning banner](assets/hero/poc-warning.png "the build may survive your evening. Your patience is less certain.")<br>_[the build may survive your evening. Your patience is less certain.](assets/hero/poc-warning.png)_

Want to know whether all this talk cashes out into real software? This is the shelf where you stop reading and start risking your evening.

- [Chummer6 Releases](https://github.com/ArchonMegalon/Chummer6/releases)

> **Street warning:** POC builds are for curious chummers, not cautious wageslaves.<br>
> They may be unstable, unfinished, weird, or one bad click away from getting your deck **marked, hacked, or bricked**.<br>
> Install at your own risk.

The binaries come from the active Chummer6 codebase, not from this guide repo.

Need the blueprint or implementation trail after that? [Where to go deeper](WHERE_TO_GO_DEEPER.md).
---

_Last synced: 2026-03-13_<br>
_Derived from: chummer6-design, public repo READMEs, current public shape_<br>
_Canonical source: chummer6-design_
