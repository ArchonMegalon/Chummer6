# FAQ

## Using Chummer6

### Can I actually use this now?

Yes, with honest caveats. There are usable public surfaces and a real POC shelf, but several surfaces are still explicitly marked preview. Read that as "real but still moving," not "imaginary."

### Is it offline-safe?

That is one of the main promises. Local-first and offline-ready behavior are part of the product story, and the current public docs explicitly treat surviving bad connectivity as a real requirement.

### Why would I trust it more than old opaque tool behavior?

Because the project is pushing toward deterministic outcomes plus readable receipts and provenance. The goal is not just to hand you a number, but to show how the number happened.

### Is this replacing older Chummer habits?

It is the next Chummer-shaped toolkit, not just a fresh coat of paint on older habits. If you are coming from older Chummer use, expect familiar goals with a stronger push toward receipts, local-first session flow, and clearer seams between parts.

### Can I keep my old habits?

Some habits, yes. But the project is trying to make more of the stack explicit: what rules are active, where a modifier came from, what is preview, and which part owns which responsibility.

### If I only care about one thing, what is the one thing it does better?

Rules truth with receipts. The standout promise is that a rules call should be explainable fast enough to help the table keep moving.

### What should I show a skeptical GM or player first?

Start with [WHAT_CHUMMER6_IS.md](WHAT_CHUMMER6_IS.md) for the product pitch, then [NOW/current-status.md](NOW/current-status.md) for the honest caveats, then [PARTS/core.md](PARTS/core.md) if the argument is really about trust in the math.

## If you want the deeper sources

### Where does the deeper plan live?

In `chummer6-design`, which carries the long-range design truth.

### Where does the actual code live?

In the split implementation repos. This guide is here so you do not need to reverse-engineer the product story from ownership seams.

### Why are there so many repos?

Because the product is already split into real responsibilities: engine, prep surface, play shell, hosted coordination, shared UI, registry, media, blueprint, and guide.

### What is live right now?

The multi-repo program is live, but several public surfaces are still preview rather than the final promoted shape.

### Where do I propose design changes?

In the [Chummer6 issue tracker](https://github.com/ArchonMegalon/Chummer6/issues). That keeps public feature requests and guide feedback in the public front door instead of throwing normal users into the design repo.

### What should I include in a bug report?

The useful stuff: what you installed, what you clicked, what you expected, what actually happened, and any screenshot or log that helps track the gremlin back to its nest.

### Can I help test or suggest future features?

Yes. Use the [Chummer6 issue tracker](https://github.com/ArchonMegalon/Chummer6/issues) for public feedback, bug reports, and future-feature suggestions. If a horizon idea sounds better than what is on the page, say so.
---

_Last synced: 2026-03-13_<br>
_Derived from: chummer6-design, current public shape_<br>
_Canonical source: chummer6-design_
