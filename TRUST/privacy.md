# What Chummer stores, and what it does not

This is the practical hosted-product picture right now: what the account keeps, what stays out of Hub, and how install linking and support work today.

## Hub keeps the account, preferences, and access state together

The hosted account keeps your basic profile, linked sign-in methods, devices and access state, support cases, and preview preferences so the public and signed-in pages stay coherent.

## The published package stays the same; the account handoff is separate

The installer stays the same for everyone when one is published, and the same rule applies to the current public package. Chummer does not personalize the published package. When linked handoff is available, the account-aware part is the signed-in receipt and short-lived code that can reconnect a local copy back to your account.

## Temporary provider auth material and raw secrets do not belong in Hub

Temporary third-party auth material stays on the execution host. Hub keeps consent, support, and receipt state; it does not become a bucket for raw provider secrets.

## Recognition should not force publicity

Participation and recognition remain optional layers. Private product use, private support, and a quiet account setup remain valid even while community pages exist.
