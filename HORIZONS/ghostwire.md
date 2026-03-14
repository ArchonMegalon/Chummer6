# GHOSTWIRE

![GHOSTWIRE banner](../assets/horizons/ghostwire.png "memory is a liar; event logs are just meaner about it.")<br>_[memory is a liar; event logs are just meaner about it.](../assets/horizons/ghostwire.png)_

**Memory is a liar. Event logs are just meaner about it.**

_Status: Horizon only — future idea, not active build work._

## What problem does this solve?

After a four-hour crawl through a Renraku black-site, every player becomes a professional liar. Was the alarm tripped by the Decker's failed exploit or the Street Sam's heavy breathing? Without a forensic record, the table descends into a rulebook-thumping contest where logic is buried under a layer of stale pizza and 'magic numbers' that were never actually rolled. If you can't replay the state changes, the GM is just a referee in a shouting match.

## A real table scene

GM: The HTR team is three floors down and they aren't coming for autographs. Decker: Impossible. I spiked the silent alarm on the way in. Sam: I saw the mag-lock cycle red when you touched the terminal. Decker: That was a visual glitch! I had four hits on the suppression. GM: Hold on. Booting GHOSTWIRE... scrubbing to the 21:04 timestamp. GM: There. You suppressed the alarm, but the host-swap triggered a secondary ping you ignored. Decker: Wait... the log shows three hits. I must have miscounted the dice. Sam: Receipts don't lie, chummer. Start running.

<p align="center"><img src="../assets/horizons/details/ghostwire-scene.png" alt="GHOSTWIRE dialogue scene still" width="420"></p>


## Meanwhile, Chummer is doing this

- Tuning the Lua engine to ensure every roll is 100% deterministic. - Finalizing the state-transition hooks in the core logic so every 'Oops' has a timestamp. - Stress-testing the mobile shell's ability to cache session echoes without melting your deck.

## Why that would be great

It’s a tactical black box for the modern runner. GHOSTWIRE takes the 'he-said, she-said' out of the equation by providing a granular, scrubbable timeline of every event, roll, and state change in the session. It turns a chaotic table argument into a forensic debrief, allowing GMs to show exactly where the plan went sideways and letting players learn from their tactical blunders instead of arguing about them. No more 'forgetting' that Wound Modifier when the heat gets high.

## Why it is still a Horizon

This is deep-sim territory. We're currently focused on making sure the rules actually work—SR4 logic, Lua portability, and offline stability come first. You can't have a forensic replay of a system that isn't fully mapped out yet. We're scrubbing the code for lazy state management and ghost-variables now so the recording is crystal clear later. We're building the engine; the flight recorder comes after we're sure the plane can fly.

## What would need to exist first

- session authority and event history
- evidence labeling
- replayable receipts
- clean sync seams

## Pitch your own future

Keep the drama in the shadows, not in the rulebook. Get ready to own the receipts.
---

_Last synced: 2026-03-13_<br>
_Derived from: chummer6-design horizon guidance, current public shape_<br>
_Canonical source: chummer6-design_
