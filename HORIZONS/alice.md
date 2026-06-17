# ALICE

Builders get grounded what-if checks instead of vague AI advice.

![ALICE horizon art](../assets/horizons/alice.png)

## Why this matters

We only discover weak builds after they explode in public.

Picture the scene: A player compares two builds and sees the tradeoffs, the math, and the likely trouble spots before the session starts.


## Current stage

- Today: shipped native desktop workbench.
- Next: deeper continuity, richer comparison cards, and bounded origin-to-build translation.

**ALICE is Chummer’s build-simulation and what-if workbench: the desktop lane where players compare builds, catch trouble, test upgrade paths, ask rules questions, and understand tradeoffs before the table discovers the mistake under pressure.**

Many weak builds are not obvious at creation time.

A player thinks they built a decker.
The table discovers they cannot afford the gear that makes the role work.
A face has social dice but no survival path.
A combat build hits hard once and then collapses.
A table discovers their favorite option is now campaign-illegal.

ALICE exists so Chummer can say:

> “This is legal, but it may not do what you think.”

## The promise

**Grounded build advice without invented mechanics.**

ALICE should compare, simulate, and explain using Chummer-owned engine truth.

The current shipped slice already includes:

- native desktop build-help turns
- native desktop rules-coach turns
- persistent conversation history in the workbench
- bounded starter prompts
- first-party handoff into account ALICE routes

It can help answer:

- Which build is stronger for this role?
- Which option gives the better tradeoff?
- What breaks if I switch campaigns?
- Which upgrade path makes sense?
- What is a role trap?
- What does campaign change?
- What is legal but fragile?
- What can I fix quickly?

But ALICE must never invent rules.

Every claim needs a receipt.

## What it feels like

A player compares two builds:

```text
Variant A: decker/infiltrator
Variant B: pure decker
```

ALICE says:

```text
Variant B is stronger for Matrix-first runs.
Variant A is safer for mixed social infiltration.

Tradeoffs:
- Variant B improves core Matrix capability.
- Variant A survives better outside the host.
- Variant B exceeds your campaign’s starting gear budget unless the GM approves a black-channel exception.
- Variant A leaves you weaker against heavy IC.

Recommended next question:
Are you joining a Matrix-heavy campaign or a mixed-op open run?
```

Buttons:

- Show math
- Show receipts
- Compare team role fit
- Fix budget issue
- Keep my chaos

That is ALICE.

## What it should include

### Build comparison

Compare:

- current build vs snapshot
- variant A vs variant B
- runner vs campaign rule environment
- runner vs team needs
- current build vs upgrade goal
- quickstart vs custom build

### Tradeoff briefs

Not just “better/worse.”

Show:

- what improves
- what worsens
- what becomes illegal
- what becomes expensive
- what becomes fragile
- what depends on campaign context
- what role the build actually fits

### Trap detection

Detect:

- archetype drift
- underfunded role
- missing required gear
- weak survivability
- illegal package conflict
- bad upgrade path
- duplicate team role
- campaign mismatch
- hidden dependency

### Upgrade path planning

Help users ask:

- what should I buy next?
- what is the cheapest meaningful upgrade?
- what becomes available after this run?
- what should I not buy yet?
- what does this faction/world offer unlock?

### Team analysis

For campaigns and open runs:

- role coverage
- unresolved role
- missing Matrix/magic/social/combat coverage
- build conflicts
- quickstart recommendations

## What users want to know

### Is ALICE AI?

It may use assistant phrasing or drafting support, but mechanics come from Chummer-owned engine truth.

### Will ALICE tell me the “best” build?

It should explain tradeoffs, not erase player taste.

### Can it work with house rules?

Yes. It must understand the active rule environment and show what changed.

### Can it help with open runs?

Yes. It can show whether a runner fits a GM’s open-run joining policy.

### Can it be funny?

Yes. The companion can comment. The receipts still do the serious work.

## What it is not

ALICE is not:

- a hidden optimizer
- a build police bot
- an AI rules engine
- a powergaming-only tool
- legality by vibes
- advice without receipts

It should help users think, not replace them.

## The first slice

The first shipped ALICE slice is:

**Native build-help and rules-coach workbench**

It lets a user:

1. ask grounded build questions
2. ask grounded rules questions
3. stay inside the native desktop workbench
4. inspect evidence and suggested next actions
5. keep per-mode conversation continuity
6. hand off into account ALICE when deeper follow-through is needed

Success looks like:

> A player stays inside the desktop, asks what to add next or what rule they are missing, and gets a bounded answer without being dumped into a vague public chat lane.

## The vision

Chummer should not only answer:

> “Is this legal?”

It should also answer:

> “Will this actually work for what I am trying to do?”

**ALICE is where Chummer becomes a build mentor with receipts.**
