# UI

![UI banner](../assets/parts/ui.png "where you lovingly inspect every choice before the run and then blame the dice anyway.")<br>_[where you lovingly inspect every choice before the run and then blame the dice anyway.](../assets/parts/ui.png)_

**The workbench and big-screen UX.**

The UI is the heavy-duty workbench for when you’re done squinting at a commlink and ready to do some actual engineering. This is high-density chrome for the big screen—inspectors, builders, and deep-view dossiers for runners who treat their gear like a religion and their stats like a blueprint.

## You touch this when...

Because guessing is for people who don't mind their cyber-arm glitching in a firefight. This part of the kit provides the math receipts that show the work. It makes the system inspectable instead of mystical, allowing you to audit every modifier and rule until you’re certain your build is street-legal—or at least street-lethal.

## What it owns

- workbench/browser/desktop UX
- builders, inspectors, and compare flows
- explain and audit-facing UX on the workbench side
- moderation and admin surfaces that stay outside the live play shell
- desktop packaging, installer delivery, and workbench-side release polish

## What it does not own

- the dedicated play/mobile shell
- offline session-ledger authority
- engine/runtime mechanics truth
- hosted orchestration or provider-secret ownership
- source-copied shared UI primitives that belong in `Chummer.Ui.Kit

## What is happening now

The current objective is a heavy purge of the 'it worked on my machine' philosophy. We're deleting the hosted-service clutter and half-baked features to focus on a hardened prep surface. If a component doesn't help you build a better runner, it’s being tossed out of the airlock. We’re sharpening the inspectors so the UI feels like a precision tool instead of a dev’s junk drawer.

## Go deeper

- [Program map](README.md)
- [Current phase](../NOW/current-phase.md)
- [Where to go deeper](../WHERE_TO_GO_DEEPER.md)
---

<sub>Updated: 2026-03-13</sub>
