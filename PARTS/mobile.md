# Mobile

![Mobile banner](../assets/parts/mobile.png "Wide cinematic cyberpunk concept art for the Chummer6 mobile part page. A gritty cyberpunk basement session in progress, one focused GM with a battered handheld device managing initiative and queued actions, tactical map spread across a cluttered table, signal indicator shifting from no-service to synced state, faint replay trail ghosting over recent moves, printed evidence-slip style rules receipt clipped beside dice and notes, practical neon and tungsten lighting, intimate documentary framing, high credibility, no sterile dashboard vibe. One clear focal subject: a runner team at a live table. Set the scene in a dangerous but inviting cyberpunk scene. Show this happening: sorting a hot dossier and live evidence threads. Make the core visual metaphor immediately legible: forensic replay echoes. Use a group_table composition. Palette: cyan-magenta neon. Mood: dangerous, curious, and slightly amused. Humor note: dry roast energy without clown mode. Concrete visible props: wet chrome, holographic receipts, rain haze. Useful diegetic overlays in-scene: diegetic HUD traces, receipt markers, signal arcs. Reader-facing motifs to weave in visually: scarred handheld glass, dossier event strip, sync pulse returning, receipt slip with stamped confirmation, ghosted path of replayed actions. Overlay ideas to imply, not print literally: Offline-ready, Replay log, Rules receipt, SR4+ era support, Lua rule hook. Include one small diegetic Chummer troll motif as a pin, placed as a small in-world detail inside the safe crop. Detail: a small recurring Chummer troll motif in the classic horned squat stance. Keep it secondary but clearly visible on a README banner. Do not center it, do not crop it out, and do not turn it into the main subject. Make it feel like a lived-in Shadowrun street, lab, archive, forge, or table scene, not a product poster. Avoid generic skylines, abstract icon soup, flat infographics, or brochure-cover posing. Do not print text, prompts, OODA labels, metadata, or resolution callouts on the image. No readable titles, no watermark, no giant centered logos, 16:9. Debug hover: the table-facing shell, where signal loss stops being a personality test.")

**Table play that still respects reality.**

Mobile is the player and GM shell: the part you feel when the session is actually happening and nobody wants to do state tracking by hand.

## You touch this when...

...the run starts, somebody loses signal, and the table needs the software to keep up without becoming the problem.

Use case: a player reconnects mid-scene, the GM still needs the current initiative and effects to be right, and everyone would like to avoid forensic spreadsheet time.

## Why it matters

Table trust lives here. Actions need to queue locally, sync cleanly, and recover without turning every hiccup into a blame meeting.

## What it owns

- player and GM play shell
- local-first session state
- runtime stack consumption
- sync-friendly play flows

## What it does not own

- builder and workbench UX
- provider secrets
- copied shared interfaces

## What is happening now

Current focus is resilience over glitter: event logs, runtime cache, offline queueing, sync recovery, and a table-facing flow that keeps moving when network conditions act like a hostile NPC.

## Go deeper

- [Program map](README.md)
- [Current phase](../NOW/current-phase.md)
- [Where to go deeper](../WHERE_TO_GO_DEEPER.md)
---

_Last synced: 2026-03-13_  
_Derived from: chummer6-design ownership map, current public shape, owning repo READMEs_  
_Canonical source: chummer6-design_
