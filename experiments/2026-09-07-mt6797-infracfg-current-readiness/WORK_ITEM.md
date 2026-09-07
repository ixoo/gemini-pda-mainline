# Work item: refresh MT6797 infracfg upstream readiness

- **Status:** accepted ordering stop at `2026-09-07T18:52:09Z` after
  independent integration review.

- **Outcome:** re-evaluate the accepted six-patch MT6797 infracfg reset topic
  against current official trees and public overlap, then select the exact
  current rebase/adaptation contract or return a source-pinned stop. Do not
  submit a historical series merely because it compiled on its old base.
- **Parent:** repository commit
  `22d46e7c6681ab6850f7f026d3fa87b624b59aaa` on `origin/main`.
- **Owner and reviewer:** Astra Medium owns the hard-uncertainty current-tree
  and overlap audit; Sol Medium reviews any proposed cross-file integration
  contract. `/root` integrates records and owns shared manifest/series changes.
- **Model route:** `gemini_specialist`, `gpt-6-astra`, medium. No implementation
  route is selected by this item.
- **Frozen local inputs:**
  `patches/series-mt6797-infracfg-revised-kunit`, its six named patches below
  `patches/upstream-4d7d9486/`, the `mt6797-infracfg-revised-kunit` manifest
  profile, the accepted revised-topic integration record, submission-readiness
  packet, current ordering refresh and separate common-helper cleanup proposal.
  Pin their exact hashes in the result receipt.
- **Current inputs:** query current official mainline, `clk-next`, MediaTek
  `for-next` and an appropriate current integration tree. Pin refs and the exact
  source bytes for every path touched by the six-patch series, the MT6797
  common-probe conversion footprint and common clock reset-registration error
  unwind. Inspect primary public thread/patch records for the 32-patch
  conversion and any successors; distinguish posting from acceptance.
- **Owned scope:** read-only source, series and overlap assessment. `/root` may
  create only this experiment's contract, source receipt and verdict record.
  Kernel patches, proposals, configs, manifest, canonical/named series,
  roadmap, registries, device queue and private evidence are frozen until an
  independently reviewed next contract admits a change.
- **Questions:** determine whether the common-probe conversion or equivalent
  reset support landed; whether generic bank-bounds protection is still needed;
  whether optional `#reset-cells` compatibility remains the correct binding
  policy; whether provider registration belongs in the private MT6797 probe or
  a common descriptor hook; whether the separate common-helper cleanup remains
  necessary; and whether the SoC DTS declaration can remain independently
  routed. Compare exact context and behavior, not filenames alone.
- **Acceptance:** source-pinned footprint and overlap receipt; exact disposition
  of each of the six local patches plus the cleanup proposal; one coherent
  current-base dependency/order decision; maintainers/tree route; existing
  evidence that can and cannot transfer; and either a smallest frozen Luna High
  rebase contract with checks or an exact stop and one next discriminator.
- **Mandatory exclusions:** no synthetic certification, DCO claim, upstream
  contact, blind import of the 32-patch conversion, historical fix-on-fix
  replay, private/vendor source, consumer wiring, TOPRGU, PMIC/thermal policy,
  device node beyond the existing `#reset-cells` declaration, or new hardware
  claim. Do not edit the six patches in this audit.
- **Stop conditions:** stop if current ownership overlaps unresolved public
  work, source identity is insufficient to select an adaptation, the binding
  would break existing DT compatibility, provider failure cleanup is unsafe,
  or a coherent slice lacks a current caller/test story. Name the missing fact.
- **Validation:** exact ref/hash/link checks, local series order and focused
  patch-context assessment. Do not rebuild unchanged historical inputs. A new
  Buildbox build is mandatory only after a later accepted implementation
  changes exact kernel inputs and is committed, pushed and clean.
- **Hardware and private analysis:** none. No VM, device, firmware, capture,
  boot candidate or deployment.
- **Upstream:** no contact or submission. Actual authorship, truthful DCO and
  coding-assistance disclosure remain independent later gates.
- **Handoff:** concise current-readiness verdict, per-patch disposition,
  current-source receipt, overlap/order decision, precise next contract or
  stop, limitations and review-ready UTC. Preserve concurrent user changes.
