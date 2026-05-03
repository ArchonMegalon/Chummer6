# ALICE

Builders can branch the same runner into temporary build ghosts, compare grounded tradeoffs, and commit only the variant they trust.

![ALICE horizon art](../assets/horizons/alice.png)

## Why this matters

We only discover weak builds after they explode in public.

Picture the scene: A player compares two temporary ghosts of the same runner, sees the tradeoffs, the math, and the likely trouble spots, then applies only the reviewed variant.


## Current stage

- Today: Future concept.
- Next: Research and prototypes.

**ALICE is Chummer’s build-simulation and what-if horizon: the future where players can compare builds, catch trouble, test upgrade paths, and understand tradeoffs before the table discovers the mistake under pressure.**

Its first real product-shaped move should be:

> **BUILD GHOST**
>
> Branch this runner, try the change, inspect the delta, and only commit if you trust the result.

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

## Build Ghost operating rule

Build Ghosts are temporary derived work copies, not new canonical runners.

That means:

- the source runner stays untouched while you explore variants
- Ghost A and Ghost B can diverge from the same snapshot
- legality, nuyen, and role-fit checks come from Chummer-owned engine truth
- assistant language may explain a computed delta, but it does not replace the math
- the canonical runner only changes through an explicit `Apply Ghost` action
- every apply or discard path should leave a receipt and an undo anchor

Facepop is out of scope here.
It belongs to public concierge and testimonial capture, not runtime build simulation.

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
- Spawn Build Ghost
- Compare team role fit
- Fix budget issue
- Keep my chaos

That is ALICE.

## What it should include

### Build comparison

Compare:

- current build vs snapshot
- variant A vs variant B
- live runner vs Ghost A vs Ghost B
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

The first ALICE slice should be:

**Build Ghost compare bench**

It should let a user:

1. spawn Ghost A and Ghost B from the current runner snapshot
2. change selected build inputs inside each ghost without touching the source runner
3. compare legality, nuyen posture, role fit, and weak-link callouts
4. inspect receipts and grounded deltas before committing anything
5. discard one ghost or apply one reviewed ghost delta
6. keep an undo anchor back to the source snapshot

The first good UI posture is a three-column compare surface:

- source runner
- Ghost A
- Ghost B

The action rail should stay blunt:

- `Discard Ghost`
- `Apply Ghost`
- `Show math`
- `Show receipts`
- `Compare against campaign`

Success looks like:

> A player understands why one legal build is worse for their intended run before the session starts.

## The vision

Chummer should not only answer:

> “Is this legal?”

It should also answer:

> “Will this actually work for what I am trying to do?”

**ALICE is where Chummer becomes a build mentor with receipts.**
