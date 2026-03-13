# Media Factory

![Media Factory banner](../assets/parts/media-factory.png "Wide cinematic cyberpunk concept art for the Chummer6 media-factory part page. A scarred media technician in a neon workshop monitors a physical queue wall of render job cards; duplicate cards are merged into one lane, failed cards cycle through a glowing recovery loop, completed assets are clipped with secure token tags, and a paper-like receipt trail snakes across the desk beside a tactical city map and coffee gone cold. One clear focal subject: a cyberpunk protagonist. Set the scene in a cyberpunk workshop with exposed internals. Show this happening: framing the next move before the chrome starts smoking. Make the core visual metaphor immediately legible: scene-aware cyberpunk guide art. Use a single_protagonist composition. Palette: cyan-magenta neon. Mood: dangerous, curious, and slightly amused. Humor note: dry roast energy without clown mode. Concrete visible props: wet chrome, holographic receipts, rain haze. Useful diegetic overlays in-scene: diegetic HUD traces, receipt markers, signal arcs. Reader-facing motifs to weave in visually: queue lanes with card flow, merged duplicate stamps, retry loop sparks settling into green, asset chain-of-custody slips, tool-worn prep table. Overlay ideas to imply, not print literally: Asset receipt, Dedupe hit, Retry recovered, Signed link issued. Include one small diegetic Chummer troll motif as a pin, placed as a small in-world detail inside the safe crop. Detail: a small recurring Chummer troll motif in the classic horned squat stance. Keep it secondary but clearly visible on a README banner. Do not center it, do not crop it out, and do not turn it into the main subject. Make it feel like a lived-in Shadowrun street, lab, archive, forge, or table scene, not a product poster. Avoid generic skylines, abstract icon soup, flat infographics, or brochure-cover posing. Do not print text, prompts, OODA labels, metadata, or resolution callouts on the image. No readable titles, no watermark, no giant centered logos, 16:9. Debug hover: the render pipeline, where aesthetics meet logistics and both get audited.")

**Render jobs in, assets out, receipts intact.**

Media Factory is the render-only lane: job queues in, previews out, links signed, and every generated asset leaves a trail behind it.

## You touch this when...

...a screen or workflow needs generated visual output and you do not want that concern leaking all over rules logic or session flow.

Use case: a render job needs to produce an asset preview or export artifact without dragging the rest of the stack into storage and retry chaos.

## Why it matters

If asset generation is sloppy, every other seam pays for it. Media Factory exists to keep render complexity contained and inspectable.

## What it owns

- render queues
- signed URLs and storage adapters
- dedupe, retry, and asset lifecycle receipts

## What it does not own

- lore generation
- session relay
- provider routing and rules math

## What is happening now

This is still deliberate scaffold work. The goal is a narrow, boringly reliable boundary before anyone gets cute with visuals.

## Go deeper

- [Program map](README.md)
- [Current phase](../NOW/current-phase.md)
- [Where to go deeper](../WHERE_TO_GO_DEEPER.md)
---

_Last synced: 2026-03-13_  
_Derived from: chummer6-design ownership map, current public shape, owning repo READMEs_  
_Canonical source: chummer6-design_
