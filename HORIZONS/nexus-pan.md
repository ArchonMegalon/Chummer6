# NEXUS-PAN

Shared state survives device churn without the table losing trust.

![NEXUS-PAN horizon art](../assets/horizons/nexus-pan.png)

## Why this matters

My devices drift and the table loses confidence.

Picture the scene: A player reconnects in the middle of a session and gets back in step without the GM rebuilding everything by memory.


## Current stage

- Today: shipped mvp.
- Next: Expand bounded coaching and fallout follow-through.

## The problem

When phones, tablets, or laptops drift apart during play, the whole table stops trusting what is on screen.

## What has to be true first

* durable session state
* reliable sync bundles
* visible reconnect explanations
* in-session reliability
* offline-capable local state
* explicit stale, pending, and conflicted state
