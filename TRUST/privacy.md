---
title: "What Chummer stores, and what it does not"
source: "products/chummer/PUBLIC_TRUST_CONTENT.yaml"
generated_by: "materialize_public_guide_bundle.py"
---

# What Chummer stores, and what it does not

This is the practical hosted-product posture right now: what the account keeps, what stays out of Hub, and how install linking and support stay bounded.

## Hub keeps the account, preferences, and access state together

The hosted account keeps your basic profile, linked sign-in methods, devices and access state, support cases, and preview preferences so the public and signed-in surfaces stay coherent.

## The installer stays canonical; the account handoff is the variable part

Chummer does not personalize the installer binary. The account-aware part is the signed-in receipt and short-lived claim code that can bind the local copy back to your account on first launch.

## Temporary provider auth material and raw secrets do not belong in Hub

Temporary third-party auth material stays on the execution host. Hub keeps consent, support, and receipt state; it does not become a bucket for raw provider secrets.

## Recognition should not force publicity

Participation and recognition remain optional layers. Private product use, private support, and a quiet account posture remain valid even while community surfaces exist.
