# Core

![Core banner](../assets/parts/core.png "if the math looks cursed, this is where the curse gets cross-examined.")<br>_[if the math looks cursed, this is where the curse gets cross-examined.](../assets/parts/core.png)_

**The deterministic rules engine.**

The Core is the high-bandwidth logic unit where the numbers stop bluffing. It’s the deterministic engine that handles the heavy lifting—modifiers, dice pools, and rule-checks—so you can focus on the run instead of arguing over page 142 of a damp rulebook. It’s local-first and offline-ready, meaning your dossier stays on your deck, not in some corporate cloud that’ll crash the moment the jammer kicks in.

## You touch this when...

Because when your Street Sam is staring down a Red Samurai and needs to know exactly why their initiative just spiked, 'trust me' doesn't cut it. We’ve moved the logic to a scriptable Lua engine that provides math receipts for every calculation. If a dice pool looks weird, you can audit the logic yourself. It’s about transparency and total era support—starting with a hardened SR4 core that actually respects the math.

## What it owns

- rules math
- runtime fingerprints
- runtime bundles
- deterministic reducers
- explain provenance
- engine contract canon
- ruleset/plugin/script ABI

## What it does not own

- UI rendering or shell chrome
- hosted-service workflows
- relay or campaign orchestration
- media rendering
- registry persistence
- provider routing
- play/mobile client implementation

## What is happening now

Right now, we’re in a purification phase. Our code-monkeys are stripping out their favorite junk-drawer habits and hardening the SR4 logic to ensure every modifier is deterministic and explainable. We're refining the mobile prep surface to make sure it doesn't feel like a lazy port of a desktop spreadsheet. The goal is a lean, mean engine that treats your character like a dossier, not a data-entry error.

## Go deeper

- [Program map](README.md)
- [Current phase](../NOW/current-phase.md)
- [Where to go deeper](../WHERE_TO_GO_DEEPER.md)
---

<sub>Updated: 2026-03-13</sub>
