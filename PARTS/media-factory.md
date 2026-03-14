# Media Factory

![Media Factory banner](../assets/parts/media-factory.png "render jobs belong here, not taped to whatever repo the dev had open at 2 a.m.")<br>_[render jobs belong here, not taped to whatever repo the dev had open at 2 a.m.](../assets/parts/media-factory.png)_

**Render-only asset lifecycle.**

Media Factory is the grimy industrial basement where we cage the render jobs and storage adapters so your rules math doesn't get contaminated by unoptimized assets or provider soup.

## You touch this when...

Because your deck shouldn't brick just because you wanted a high-res gear preview. By decoupling the asset lifecycle from the core logic, we ensure the engine stays fast and local-first, even when the UI gets heavy. It’s the difference between a smooth tactical overlay and a crash-test simulation because a dev forgot how to compress a texture.

## What it owns

- render queues
- signed URLs and storage adapters
- dedupe/retry and asset lifecycle receipts

## What it does not own

- lore generation
- session relay
- provider routing and rules math

## What is happening now

Currently at the scaffold-stage, which is dev-speak for 'we're keeping the pipes tight until they stop leaking.' We’re focusing on a narrow, stable seam for render queues and lifecycle receipts before we let the feature-creep sprawl into the rest of the architecture.

## Go deeper

- [Program map](README.md)
- [Current phase](../NOW/current-phase.md)
- [Where to go deeper](../WHERE_TO_GO_DEEPER.md)
---

_Last synced: 2026-03-13_<br>
_Derived from: chummer6-design ownership map, current public shape, owning repo READMEs_<br>
_Canonical source: chummer6-design_
