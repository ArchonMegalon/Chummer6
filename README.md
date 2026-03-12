# Chummer6

![Chummer6 hero banner](assets/hero/chummer6-hero.png)

> **Shadowrun rules truth, with receipts.**
>
> Chummer6 exists for one reason: Shadowrun math should be clear, not mystical. When a rules call gets spicy, you can open a receipt that shows how the result was built.

Why this matters at a real table: arguments end faster, trust goes up, and the game keeps moving. It runs local-first, so it still works when your Wi-Fi eats itself, and it supports multiple eras of play, including SR4 plugin paths plus Lua rule hooks for weird edge cases. If you only click one thing next, take the guided intro, then check a real receipt trail so you can see the proof flow yourself.

No, this is not the code repo.  
No, you do not need a flowchart and three espressos to understand the program.  
That is the whole reason this repo exists.

## Pick your path

- **I’m new here:** [Start Here](START_HERE.md)
- **Give me the two-minute version:** [What Chummer6 is](WHAT_CHUMMER6_IS.md)
- **What is happening right now?** [Current status](NOW/current-status.md)
- **How do the parts fit together?** [Program map](PARTS/README.md)
- **What are the future rabbit holes?** [Horizons](HORIZONS/README.md)
- **Where should I go deeper?** [Where to go deeper](WHERE_TO_GO_DEEPER.md)

## What Chummer6 is

This repo is the human guide layer for the Chummer ecosystem: it explains what the core engine guarantees, how UI/mobile fronts fit, and how to use features that matter at the table without making you read source first.

Think of it like this:

- `chummer6-design` is the blueprint room
- the code repos are the workshops
- **Chummer6 is the map on the wall**

## Why this is worth watching

Chummer6 gives you deterministic rules truth with human-readable receipts, plus local-first play across app surfaces.

Follow this project if you care about dangerous-simulation energy with fewer black boxes: rules decisions you can audit, offline play you can trust, and a stack that keeps getting sharper for real sessions.

- Your rules calls are auditable, not hand-wavy
- Works offline; your table is not hostage to Wi-Fi
- Multi-era rulesets (including SR4 plugin support) are explicitly in play
- Lua/scripted rules let edge cases live in code, not forum arguments

## What’s happening now

![Current status banner](assets/pages/current-status.png)

Right now the crew is doing foundation work, not bolting neon spoilers onto half-built engines.
People want crunchy simulation depth, but not mystery math or SaaS lock-in.

Current focus:
- Show value before repo topology
- Lead with receipts + local-first + multi-era
- Keep tone sharp, helpful, slightly streetwise
- keep public previews honestly labeled until they become the real thing

Read more: [Current phase](NOW/current-phase.md)

## Meet the parts

![Parts overview](assets/pages/parts-index.png)

<table>
  <tr>
    <td align="center"><a href="PARTS/core.md"><img src="assets/parts/core.png" alt="Core" width="300"><br><strong>Core</strong><br><em>The deterministic rules engine</em></a></td>
    <td align="center"><a href="PARTS/presentation.md"><img src="assets/parts/presentation.png" alt="Presentation" width="300"><br><strong>Presentation</strong><br><em>The workbench and big-screen UX</em></a></td>
    <td align="center"><a href="PARTS/play.md"><img src="assets/parts/play.png" alt="Play" width="300"><br><strong>Play</strong><br><em>The player and GM shell</em></a></td>
    <td align="center"><a href="PARTS/run-services.md"><img src="assets/parts/run-services.png" alt="Run services" width="300"><br><strong>Run services</strong><br><em>The hosted API and orchestration layer</em></a></td>
  </tr>
  <tr>
    <td align="center"><a href="PARTS/ui-kit.md"><img src="assets/parts/ui-kit.png" alt="UI kit" width="300"><br><strong>UI kit</strong><br><em>Shared chrome and visual primitives</em></a></td>
    <td align="center"><a href="PARTS/hub-registry.md"><img src="assets/parts/hub-registry.png" alt="Hub registry" width="300"><br><strong>Hub registry</strong><br><em>Artifacts, installs, and compatibility</em></a></td>
    <td align="center"><a href="PARTS/media-factory.md"><img src="assets/parts/media-factory.png" alt="Media factory" width="300"><br><strong>Media factory</strong><br><em>Render-only asset lifecycle</em></a></td>
    <td align="center"><a href="PARTS/design.md"><img src="assets/parts/design.png" alt="Design" width="300"><br><strong>Design</strong><br><em>The long-range blueprint room</em></a></td>
  </tr>
</table>

## Horizon ideas

![Horizons overview](assets/pages/horizons-index.png)

On the horizon: more runner-grade dossiers, richer receipt storytelling, and nastier edge-case support for era/rules experimentation, presented as ideas to watch, not promises from a slick suit.

<table>
  <tr>
    <td align="center"><a href="HORIZONS/karma-forge.md"><img src="assets/horizons/karma-forge.png" alt="Karma Forge" width="300"><br><strong>KARMA FORGE</strong><br><em>Personalized rule stacks without fork chaos</em></a></td>
    <td align="center"><a href="HORIZONS/nexus-pan.md"><img src="assets/horizons/nexus-pan.png" alt="NEXUS-PAN" width="300"><br><strong>NEXUS-PAN</strong><br><em>A live synced table instead of lonely files</em></a></td>
    <td align="center"><a href="HORIZONS/alice.md"><img src="assets/horizons/alice.png" alt="ALICE" width="300"><br><strong>ALICE</strong><br><em>Stress-test a build before the run</em></a></td>
  </tr>
  <tr>
    <td align="center"><a href="HORIZONS/jackpoint.md"><img src="assets/horizons/jackpoint.png" alt="JACKPOINT" width="300"><br><strong>JACKPOINT</strong><br><em>Turn grounded data into dossiers and briefings</em></a></td>
    <td align="center"><a href="HORIZONS/ghostwire.md"><img src="assets/horizons/ghostwire.png" alt="GHOSTWIRE" width="300"><br><strong>GHOSTWIRE</strong><br><em>Replay a run like a forensic sim</em></a></td>
    <td align="center"><a href="HORIZONS/rule-x-ray.md"><img src="assets/horizons/rule-x-ray.png" alt="RULE X-RAY" width="300"><br><strong>RULE X-RAY</strong><br><em>Click any number and see where it came from</em></a></td>
  </tr>
</table>

See all: [Horizon index](HORIZONS/README.md)

## What you can do

If this repo helped you get your bearings, here’s how to help back:

- **Give Chummer6 a star** if this guide saved you from digging through half the Matrix just to understand what is going on.
- **Be my test dummy and install the software.**
- **Grab the latest POC build from [Releases](https://github.com/ArchonMegalon/Chummer6/releases)** when one is available.
- **Seriously: never trust software. Never trust a dev.**
- **If the build starts acting like a recruiter for chaos, close the lid and write down the steps.**
- **If the build does something cursed, tell us exactly which click woke the gremlin.**
- **If this repo is stale, confusing, or reads like corp training material, call it out.**

> **Street warning:** POC builds are for curious chummers, not cautious wageslaves.  
> They may be unstable, unfinished, weird, or one bad click away from getting your deck **marked, hacked, or bricked**.  
> Install at your own risk.

In other words: kick the tires, break the thing, and tell me where the smoke came out.

## POC shelf

![POC warning banner](assets/hero/poc-warning.png)

If there is a fresh proof-of-concept build ready for brave idiots and helpful test dummies, the shelf is here:

- [Chummer6 Releases](https://github.com/ArchonMegalon/Chummer6/releases)

The binaries themselves come from the active Chummer6 codebase, not from this guide repo.

## Where to go deeper

Chummer6 explains. It does not ship code and it does not replace the blueprint.

- The long-range plan lives in `chummer6-design`
- The software itself lives in the owning code repos
- Chummer6 is the friendly guide for humans
---

_Last synced: 2026-03-11_  
_Derived from: chummer6-design, public repo READMEs, current public shape_  
_Canonical source: chummer6-design_
