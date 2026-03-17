# Evidence Room

![Evidence Room banner](../assets/horizons/evidence-room.png "proof, provenance, and one coffee cup that has seen too much.")<br>_[proof, provenance, and one coffee cup that has seen too much.](../assets/horizons/evidence-room.png)_

**The math doesn't lie, but it usually mumbles. Time to make it talk.**

_Status: Horizon only — future idea, not active build work._

## What problem does this solve?

Most character managers are black boxes that spit out a '7' and expect you to trust the ghost in the machine. When your GM demands to know why your street sam has a +4 to Agility while hip-deep in a toxic sewer, answering 'because the app says so' is a one-way ticket to a forced reroll. Debugging your own stats shouldn't require a degree in data archaeology or a deep dive into raw Lua logs that look like a decker's fever dream after a bad BTL hit.

## A real table scene

GM: 'Hold up. Why is your recoil compensation at 11? You're firing a hold-out pistol.'
Player: 'I... uh... the sheet says 11. It's probably right?'
GM: 'The sheet is hallucinating. Open the Evidence Room and find the receipt.'
Player: 'Scanning... okay, here it is. It's pulling a "Custom Grip" bonus from that Ares Alpha you threw in the trash three sessions ago.'
GM: 'The one at the bottom of the Redmond Barrens? Nice try. Delete it.'
Player: 'Done. Math receipt updated. Recoil is back to 2. My bad.'

<p align="center"><img src="../assets/horizons/details/evidence-room-scene.png" alt="Evidence Room dialogue scene still" width="420"></p>


## Meanwhile, Chummer is doing this

- Hardening the core engine's ability to tag every modifier with a provenance receipt.
- Refining local-first storage so your forensic data doesn't vanish during a grid crash.
- Training the Lua scripting engine to write logs that humans can actually read without a translator.

## Why that would be great

The Evidence Room is your forensic toolkit for character integrity. It transforms debug archaeology into a grounded dossier, serving up 'Math Receipts' for every sub-processor, stim-patch, and obscure modifier in your kit. You get absolute confidence in your numbers because you can see exactly where they came from and who approved them. It’s the clinical, cynical truth behind every stat, delivered in a high-contrast HUD that doesn't care about your 'vibe-based' math.

## Why it is still a Horizon

This is a data-haven currently under decryption. While the core engine is already whispering these receipts in the background, we're waiting to move the forensic lab into the active build until the mobile HUD can handle the data density without melting your commlink. We’re prioritizing a stable SR4 core over a pretty archive room for now.

## What would need to exist first

- evidence receipts
- source classification
- approvals
- preview and apply separation

## Pitch your own future

Got a cleaner way to visualize the forensic trail of a glitching combat roll? Toss your ideas into the long-range plan on the issue tracker.
---

<sub>Updated: 2026-03-13</sub>
