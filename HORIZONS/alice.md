# ALICE

![ALICE banner](../assets/horizons/alice.png "the simulation is here to hurt your feelings before reality does.")

**Stress-test the build before the run does.**

_Status: Horizon only - future idea, not active build work._

_Image idea: a smug runner strapped into a simulation bench while warning lights flash and the diagnostic screen prepares to ruin their self-esteem._

## What problem does this solve?

Most tables only discover weak builds after they explode in public. ALICE is the idea of giving players and GMs a deterministic crash bench: seeded scenarios, reproducible pressure, and visible proof of where the build folds.

## A real table scene

> The player is bragging. The sim bench is about to take that personally.
>
> A player starts bragging before session, which is how the lab knows it has work to do.
> **Player:** "My infiltrator is unstoppable."
> **GM:** "Last run you got flash-banged by a rent-a-cop and cried."
> **Player:** "That was tactical sorrow."
> **Chummer6:** "Ran 500 seeded breach sims. In 71 percent of them, you fold the moment the hallway goes loud."
> **Player:** "Rude."
> **Chummer6:** "Suggested fixes: stop treating Body as decorative."

## Meanwhile, Chummer is doing this

- replaying a seeded scenario with the same inputs
- holding the runtime stack constant between runs
- tracing the collapse point instead of just reporting failure
- showing which rule path, modifier, or choice killed the build

## Why that would be great

Players could find weak assumptions before session night, and GMs could test scenarios without pretending vibes are coverage.

## Why it is still a Horizon

This only works if deterministic engine truth, scenario harnesses, and receipt quality are already clean. A sim lab built on fuzzy behavior would just produce expensive nonsense.

## What would need to exist first

- deterministic engine truth
- scenario harnesses with reproducible seeds
- explain receipts
- stable runtime stack fingerprints

## Pitch your own future

If your table pain is not "we only discover bad builds in public," go back to the [Horizons index](README.md) and drag a different problem into the light.
---

_Last synced: 2026-03-13_  
_Derived from: chummer6-design horizon guidance, current public shape_  
_Canonical source: chummer6-design_
