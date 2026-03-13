# What Chummer6 Is

![What Chummer6 is banner](assets/pages/what-chummer6-is.png "Wide cinematic cyberpunk concept art for the Chummer6 what-is banner. Cyberpunk safehouse table, runner and GM in-frame, glowing character dossier projected from commlink, printed-style rules receipt with modifier trail, subtle HUD tags for Offline-ready and Lua hook, gritty neon documentary look, no corporate dashboard aesthetic. One clear focal subject: A street samurai and GM reviewing a generated rules receipt beside a loaded character dossier.. Set the scene in Action resolves, receipt appears, table verifies, play continues without debate spiral.. Show this happening: Chummer6 exists to keep crunchy Shadowrun decisions honest in real sessions: deterministic outcomes, human-readable receipts, and tools that keep working when your connection doesn’t. It helps players, GMs, and tinkerers who want fewer forum-lawyering stalemates and more playable clarity. It also says the quiet part out loud: multi-era support is real, and Lua-scripted rules handle the weird edge cases instead of pretending they don’t exist. What it is not: a cloud lock-in service, a hand-wavy rules vibe machine, or an org chart disguised as a guide.. Make the core visual metaphor immediately legible: what chummer6 is. Use a single_protagonist composition. Palette: ['dossier board', 'receipt slip with traced modifiers', 'neon tactical map glow', 'blackbox opened to show internals']. Mood: Feel like this is a reliable fixer: crunchy, transparent, and not cloud-hostage.. Humor note: Direct, streetwise, mildly witty; roast mystery math, not users.. Useful diegetic overlays in-scene: deterministic rules engine, explain/provenance receipts, Lua-scripted rules support, multi-era rulesets including SR4 plugin signal. Overlay ideas to imply, not print literally: deterministic rules engine, explain/provenance receipts, Lua-scripted rules support, multi-era rulesets including SR4 plugin signal, local-first and offline/installable play surfaces. Include one small diegetic Chummer troll motif as a pin, placed as a small in-world detail inside the safe crop. Detail: a small recurring Chummer troll motif in the classic horned squat stance. Keep it secondary but clearly visible on a README banner. Do not center it, do not crop it out, and do not turn it into the main subject. Make it feel like a lived-in Shadowrun street, lab, archive, forge, or table scene, not a product poster. Avoid generic skylines, abstract icon soup, flat infographics, or brochure-cover posing. Do not print text, prompts, OODA labels, metadata, or resolution callouts on the image. No readable titles, no watermark, no giant centered logos, 16:9. Debug hover: product story first, architecture sermon later, assuming the dev can resist lecturing for five minutes.")

Chummer6 is becoming a clearer, more trustworthy, more table-friendly Shadowrun toolkit.

It is trying to make rules calls fast, explainable, and recoverable. That means deterministic outcomes, readable receipts, local-first session behavior, multi-era support, and scripted rule hooks for the weird cases that usually turn into forum trench warfare.

## What it is trying to become

Chummer6 is not just trying to be a character manager with nicer chrome. It is trying to become a toolkit that helps players and GMs:

- get a ruling quickly
- see why that ruling happened
- keep playing when the network misbehaves
- carry different rules eras without pretending they are identical
- handle odd table logic in code instead of folklore

## A real table moment

**GM:** "You are wounded, sustaining, and standing in bad weather. Roll it."
**Player:** "Why is my pool lower than I expected?"
**Chummer6:** "Base 11. Wounds -1. Sustaining -1. Weather -1. Final 8."
**GM:** "Good. We move."

That is the product story in miniature. Not "trust me, bro." Not "dig through source." Just a fast answer with enough proof to keep the table moving.

## What feels different from old Chummer habits

The project is leaning harder into explicit trust:

- same inputs should produce the same result
- the result should come with a readable receipt
- the session should survive local/offline reality
- the active rules and config stack should be visible
- the ugly edge cases should have a real extension lane

If older Chummer habits taught you to expect one giant opaque box, this is trying to be the opposite: sharper seams, clearer proof, and less mystery math.

## The kinds of trust it wants to earn

- **Math trust:** the number should be reproducible.
- **Receipt trust:** the path to the number should be visible.
- **Session trust:** your table should not collapse because Wi-Fi had a mood.
- **Change trust:** custom rules, era differences, and future expansions should be legible instead of spooky.

## Why there are multiple parts

The codebase is split because the product is getting bigger and more specialized. A rules engine, a prep workbench, a table-facing shell, hosted coordination, shared chrome, artifact handling, render jobs, and a blueprint repo all have different jobs. Keeping those seams honest is how the project avoids one giant haunted monolith.

If you want that map, go to [PARTS/README.md](PARTS/README.md).

## What this repo is

This repo is the friendly public guide to that wider program. It is here to explain the product in plain language, show what is real now versus future-looking, and help humans get oriented before they go hunting through deeper repos.
---

_Last synced: 2026-03-13_  
_Derived from: chummer6-design, current public shape_  
_Canonical source: chummer6-design_
