# NEXUS-PAN

![NEXUS-PAN banner](../assets/horizons/nexus-pan.png "Wide cinematic cyberpunk concept art for the Chummer6 nexus-pan horizon page. Rain-soaked cyberpunk backroom table, decker-GM at center over a tactical holo-map; one player phone shifts from ghosted offline avatar to solid rejoined state as event stamps cascade and reconcile initiative/resources; visible sync threads between devices, high-contrast neon realism, specific and dangerous atmosphere. One clear focal subject: a runner team at a live table. Set the scene in a dangerous but inviting cyberpunk scene. Show this happening: framing the next move before the chrome starts smoking. Make the core visual metaphor immediately legible: forensic replay echoes. Use a group_table composition. Palette: cyan-magenta neon. Mood: dangerous, curious, and slightly amused. Humor note: dry roast energy without clown mode. Concrete visible props: wet chrome, holographic receipts, rain haze. Useful diegetic overlays in-scene: diegetic HUD traces, receipt markers, signal arcs. Reader-facing motifs to weave in visually: threadlike sync links, append-only event stamps, ghost-to-solid avatar transition, mirrored tactical state panes. Overlay ideas to imply, not print literally: Session authority, Append-only events, Offline replay, State restored. Include one small diegetic Chummer troll motif as a pin, placed as a small in-world detail inside the safe crop. Detail: a small recurring Chummer troll motif in the classic horned squat stance. Keep it secondary but clearly visible on a README banner. Do not center it, do not crop it out, and do not turn it into the main subject. Make it feel like a lived-in Shadowrun street, lab, archive, forge, or table scene, not a product poster. Avoid generic skylines, abstract icon soup, flat infographics, or brochure-cover posing. Do not print text, prompts, OODA labels, metadata, or resolution callouts on the image. No readable titles, no watermark, no giant centered logos, 16:9. Debug hover: Wi-Fi died; the table did not. That is the fantasy.")

**One living table state, even when the signal gets cute.**

_Status: Horizon only - future idea, not active build work._

_Image idea: a rain-soaked table, one phone reconnecting, AR initiative markers hovering over coffee cups, and one player looking personally betrayed by Wi-Fi._

## What problem does this solve?

A real Shadowrun table is messy: one player is on a phone, one is on a tablet, the GM has too many tabs open, somebody's Wi-Fi dies, and suddenly half the table is arguing over whether the samurai already spent Edge. NEXUS-PAN is the idea of making the table state the truth instead of treating every device like a lonely little island.

## A real table scene

The cafe Wi-Fi dies at the exact moment the firefight becomes interesting.

**GM:** "Rain comes down hard. Visibility drops. Security just woke up."
**Decker:** "My phone died. I missed the last two actions. It chose performance art."
**Street Sam:** "I already burned one Edge and took 3 stun, right?"
**Mage:** "And I am still sustaining that spell. Probably."
**Chummer6:** "Decker device rejoined. Replayed 6 missed events. Current initiative: 11. Rain penalty applied."
**GM:** "Good. Nobody do forensic accounting. Keep going."

## Meanwhile, Chummer is doing this

- keeping session state as one shared event stream
- recording who changed what and when
- replaying missed turns onto the rejoined device
- showing the same initiative, resources, and effects to everyone

## Why that would be great

Less desync, fewer trust fights, faster recovery from bad signal, and more time actually playing the scene instead of rebuilding it from memory.

## Why it is still a Horizon

This only works if session authority, event semantics, replay behavior, and offline recovery are solid enough to deserve trust. That foundation is still the prerequisite work.

## What would need to exist first

- session authority profile
- append-only session events
- local-first sync and replay
- clean play API seams

## Pitch your own future

If your table pain is different, head back to the [Horizons index](README.md) and pitch a better future mess.
---

_Last synced: 2026-03-13_  
_Derived from: chummer6-design horizon guidance, current public shape_  
_Canonical source: chummer6-design_
