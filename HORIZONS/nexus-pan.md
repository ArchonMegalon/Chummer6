# NEXUS-PAN

Shared state survives device churn without the table losing trust.

![NEXUS-PAN horizon art](../assets/horizons/nexus-pan.png)

## Why this matters

My devices drift and the table loses confidence.

Picture the scene: A player reconnects in the middle of a session and gets back in step without the GM rebuilding everything by memory.


## Current stage

- Today: Future concept.
- Next: Research and prototypes.

## The problem

When phones, tablets, or laptops drift apart during play, the whole table stops trusting what is on screen.

## What it would do

Chummer would keep reconnects and shared session state steady enough that players can jump back in without the GM rebuilding context by hand.
It would build on the existing session record instead of creating a separate version of events.
It would also handle bad signals and device handoffs honestly: clear offline status, safe local continuity, and visible conflict recovery when reconnecting goes wrong.

## What has to be true first

* durable session state
* reliable sync bundles
* visible reconnect explanations
* in-session reliability
* offline-capable local state
* explicit stale, pending, and conflicted state

## Why it is not ready yet

The live release still needs boringly reliable session continuity.
Until reconnects and shared-state handoffs stay solid under stress, a richer PAN layer would add confusion instead of removing it.
