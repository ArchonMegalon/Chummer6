# TABLE PULSE

GMs get opt-in post-session coaching about table dynamics without turning Chummer into surveillance.

![TABLE PULSE horizon art](../assets/horizons/table-pulse.png)

## Why this matters

I know the table drifted, but I cannot say where the energy, pacing, or spotlight balance broke.

Picture the scene: After an online session, the GM opens a coaching packet and sees spotlight balance, pacing heat zones, disengagement markers, and one or two concrete suggestions for the next run.


## Current stage

- Today: Future concept.
- Next: Research and prototypes.

## The problem

The GM knows something went off after a session, but cannot clearly reconstruct where pacing dragged, who lost the room, or which scene actually landed.

## What it would do

TABLE PULSE turns live-session pressure into bounded follow-up packets and post-session coaching.

It starts with:

* heat domains and threshold events
* recipient decision packets
* GM pulse policy
* player-safe delivery and mute controls
* optional narrated summaries

It then widens into:

* between-session rumor, order, and Passport hooks
* remote reaction mini-games for outside players or role-holders
* public-safe BLACK LEDGER aftermath projection

It is for reflection, pressure handling, and bounded follow-up after play. It is not live
surveillance, player scoring, or moderation truth.

## What players and remote users would actually see

The first public-safe version is not a giant dashboard. It is a handful of sharp bounded moments:

* a packet that says a scene generated heat
* a reason why this player or faction contact received the packet
* one or two choices that can move pressure, rumor, or favor
* a receipt that shows whether the GM still must approve fallout

Remote users would only see packets they are explicitly allowed to see under campaign policy,
quiet hours, and recipient rules.

## Heat and reaction model

TABLE PULSE treats heat as a governed pressure signal, not generic drama text.

Examples:

* pacing heat
* spotlight imbalance
* interruption or confusion spikes
* faction or public pressure after a noisy result
* consequence pressure that can spill into BLACK LEDGER

Heat does not mutate table truth by itself. It creates a bounded packet that a GM can inspect,
route, suppress, or turn into a follow-up action.

## Remote reaction mini-games

The most exciting outside-the-session lane is the remote reaction mini-game family.

Core examples:

* **Intercept** - catch, forward, or suppress a courier or intel lane
* **Cover Story** - shape the cleanup narrative after a messy outcome
* **Scramble** - spend time, favor, or logistics to preserve an asset
* **Temptation** - accept a risky offer that increases pressure for a later edge
* **Shadow Reply** - send back a coded answer that changes rumor, order, or Passport flavor

These are:

* opt-in or policy-allowed
* receipt-backed
* bounded in consequence
* safe to adjudicate outside the main session

They are not:

* direct mutation of live table canon
* autonomous side campaigns
* public scoreboards
* a replacement for the GM

## Likely owners

* `chummer6-hub`
* `chummer6-media-factory`

## Key tool posture

* `Nonverbia` - primary coaching and social-dynamics analysis lane
* `hedy.ai` - bounded transcript structure, highlight digest, and GM debrief prompt lane
* `vidBoard` - later bounded player-safe recap and GM-private debrief video lane
* `Soundmadeseen` - optional narrated coaching summary
* `Unmixr AI` - bounded candidate voice lane until proven
* `MarkupGo` - coaching packet render support
* `PeekShot` - preview/share-safe summary card support

See also: `HEDY_AI_TABLE_PULSE_DESIGN.md`

## What has to be true first

* explicit consent and upload policy
* post-session-only analysis and packet rules
* privacy and retention rules for coaching media
* share-safe coaching summaries
* replay and receipt references where available
* mute, suppression, and quiet-hours proof
* GM adjudication for outside reactions

## Hard boundary

* not live surveillance
* not player scoring
* not moderation truth
* not discipline automation
* not durable session truth

## Why it is not ready yet

This only works if it stays consensual, private, and clearly separate from moderation or rules truth.
Until Chummer can prove those guardrails end to end, TABLE PULSE remains a future-facing horizon
page rather than a claim that the full heat, remote-user, and mini-game stack is already shipped.
