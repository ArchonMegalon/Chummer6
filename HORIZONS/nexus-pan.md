---
title: "Horizon: NEXUS-PAN"
source: "products/chummer/HORIZON_REGISTRY.yaml"
generated_by: "materialize_public_guide_bundle.py"
---

# NEXUS-PAN

- id: nexus-pan
- pain_label: My devices drift and the table loses confidence.
- wow_promise: Shared state survives device churn without the table losing trust.
- table_scene: A player reconnects mid-session and catches up without the GM reconstructing state by memory.

![NEXUS-PAN horizon art](../assets/horizons/nexus-pan.png)


## Build path

- intent: eventual_product_lane
- current_state: horizon
- next_state: bounded_research

## Registry posture

- owning_repo: chummer6-core
- owning_repo: chummer6-mobile
- owning_repo: chummer6-hub
- promoted_tools: none
- bounded_tools: none

## Canon source

`products/chummer/horizons/nexus-pan.md`

## Table pain

Tables lose confidence when devices, PAN state, and cross-actor continuity drift during live play.

## Bounded product move

Chummer would expose grounded device and shared-state continuity support without inventing new rules truth outside the engine and play contracts.

## Likely owners

* `chummer6-core`
* `chummer6-mobile`
* `chummer6-hub`

## Tool posture

No external tool is required for the canonical core of this horizon.
If projections or operator aids appear later, they remain downstream helpers only.

## Foundations

* session semantic canon
* runtime bundle canon
* explain provenance
* play-shell reliability

## Why still a horizon

The active release path is still finishing canonical session and runtime seams.
Until those seams are fully trustworthy, a richer PAN layer would widen unstable boundaries.
