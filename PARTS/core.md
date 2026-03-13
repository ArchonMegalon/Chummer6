# Core

![Core banner](../assets/parts/core.png "Wide cinematic cyberpunk concept art for the Chummer6 core part page. A street sam and GM lean over a scarred prep table in a neon-safehouse, one tense combat call under review on a rugged terminal while layered logic trails and provenance markers float as subtle AR artifacts; the mood is focused, technical, and controlled rather than flashy. One clear focal subject: a runner team at a live table. Set the scene in a rainy neon street front. Show this happening: framing the next move before the chrome starts smoking. Make the core visual metaphor immediately legible: scene-aware cyberpunk guide art. Use a group_table composition. Palette: cyan-magenta neon. Mood: dangerous, curious, and slightly amused. Humor note: dry roast energy without clown mode. Concrete visible props: wet chrome, holographic receipts, rain haze. Useful diegetic overlays in-scene: diegetic HUD traces, receipt markers, signal arcs. Reader-facing motifs to weave in visually: battered terminal glow, receipt-like evidence slips, stacked logic layers, subtle era and scripting markers, runner prep table clutter. Overlay ideas to imply, not print literally: Rules receipt, Deterministic path, Lua rule hook, SR4+ era support. Include one small diegetic Chummer troll motif as a pin, placed as a small in-world detail inside the safe crop. Detail: a small recurring Chummer troll motif in the classic horned squat stance. Keep it secondary but clearly visible on a README banner. Do not center it, do not crop it out, and do not turn it into the main subject. Make it feel like a lived-in Shadowrun street, lab, archive, forge, or table scene, not a product poster. Avoid generic skylines, abstract icon soup, flat infographics, or brochure-cover posing. Do not print text, prompts, OODA labels, metadata, or resolution callouts on the image. No readable titles, no watermark, no giant centered logos, 16:9. Debug hover: if the math looks cursed, this is where the curse gets cross-examined.")

**The deterministic rules engine.**

Core is where Shadowrun math stops bluffing. It takes the same inputs, runs the same logic, and is supposed to give you a ruling you can actually trust.

## You touch this when...

...the table asks, "why is my dice pool 11?" and somebody wants proof instead of volume.

Use case: the samurai thinks recoil got ignored, the mage thinks sustaining got applied twice, and you need the layer that can show base value, modifiers, scripted hooks, and final result in order.

## Why it matters

When the math is opaque, trust dies fast. Core is the part that turns rules debate into something inspectable instead of theatrical.

## What it owns

- engine runtime and reducer truth
- explain receipts and deterministic evaluation
- engine-facing shared interfaces

## What it does not own

- the hosted service layer
- the at-the-table shell
- render-only media work

## What is happening now

Current focus is sharp and boring in the best way: keep engine behavior deterministic, keep receipts readable, and keep Lua plus era-specific edge cases grounded in code instead of vibes.

## Go deeper

- [Program map](README.md)
- [Current phase](../NOW/current-phase.md)
- [Where to go deeper](../WHERE_TO_GO_DEEPER.md)
---

_Last synced: 2026-03-13_  
_Derived from: chummer6-design ownership map, current public shape, owning repo READMEs_  
_Canonical source: chummer6-design_
