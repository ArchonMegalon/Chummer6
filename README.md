# Chummer6

![Chummer6 hero banner](assets/hero/chummer6-hero.png)

> **Shadowrun crunch, street-fast and explainable.**
>
> Chummer6 exists for one simple reason: Shadowrun is fun when the heat is high, not when everyone is arguing over mystery math. This page is your quick map to what this is, why you can trust it, and where to click first.

Think of this readme as your street-level briefing. Chummer6 gives you fast character and session flow, but every result can show its work with clear receipts (a step-by-step trail of how the rules got that answer). It is local-first, which means your game keeps moving even when the signal dies, and you can install it like an app for easier table use. Start in the workbench for prep, jump to the session shell for live play, and use the role paths to pick your next click: player, GM, or tinkerer.

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

A human-facing guide to the Chummer ecosystem: deterministic rules core, prep/workbench UX, live play session shell, and optional hosted coordination when your crew needs it.

Think of it like this:

- `chummer6-design` is the blueprint room
- the code repos are the workshops
- **Chummer6 is the map on the wall**

## Why this is worth watching

Fast character and session workflows backed by deterministic, explainable rules.

Follow this project if you want deep build/play tooling that shows its math, survives bad Wi-Fi, and keeps getting sharper across desktop, browser, and mobile.

- Trust every calc
- Play even when signal dies
- Move between devices cleanly
- Inspect the receipts when something looks cursed

## What’s happening now

![Current status banner](assets/pages/current-status.png)

Right now the crew is doing foundation work, not bolting neon spoilers onto half-built engines.
Deep crunchy simulation vs actually getting to the table tonight.

Current focus:
- Reliable rules truth
- Human-first UX across workbench/play/mobile
- Local-first play with installable web app paths
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

On the horizon: wilder runner workflows, cleaner cross-surface handoffs, and more 'show me the receipts' magic, all clearly labeled before it goes live.

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
