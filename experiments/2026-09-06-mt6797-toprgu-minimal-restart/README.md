# Experiment: minimal MT6797 TOPRGU restart diagnostic

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-06-mt6797-toprgu-minimal-restart` |
| Status | Buildbox-validated package; device readiness remains false |
| Subsystem | MediaTek watchdog system restart |
| Device variant | Existing named Gemini PDA; retail subvariant unconfirmed |
| Date | 2026-09-06 |

## Question

Can the single hardware-passed MT6797 ordinary-restart result be reproduced
with the narrowest policy delta: set the existing auto-start bit only in the
software-restart path and run TOPRGU at priority 130, while leaving watchdog
start and inherited-watchdog adoption behavior unchanged?

A pass would show that priority 255 and the additional lifecycle mutations in
historical patch 0081 are unnecessary for this ordinary-restart path. A failure
would be inconclusive and would not select either removed behavior for
promotion.

The frozen scope, validation boundary and executable future one-boot decision
table are in [the work item](WORK_ITEM.md). The policy applies SoC-wide to every
MT6797 watchdog match even though any future deployment is limited to the named
Gemini; one unit cannot establish generic upstream policy. Source replay and
Buildbox compilation are complete. Checkpatch reports only the deliberately
absent synthetic-author sign-off, so upstream authorship remains gated. No boot
candidate, device selection or runtime claim exists yet; device readiness and
hardware equivalence remain pending separate gates.

## Offline candidate record

The review artifact is [`0543-watchdog-mtk-minimal-MT6797-restart.patch`](../../patches/v7.1.3/0543-watchdog-mtk-minimal-MT6797-restart.patch).
Its experiment series is [`series-mt6797-toprgu-minimal-restart`](../../patches/series-mt6797-toprgu-minimal-restart),
the profile proposal is [`proposal.json`](proposal.json), and the only new
configuration is the local-version fragment
[`gemini-mt6797-toprgu-minimal-restart.fragment`](../../configs/gemini-mt6797-toprgu-minimal-restart.fragment).

Run `PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate.py` for the static
manifest, canonical-order, patch-shape, inheritance, frozen-chain, and ten
targeted refusal-fixture checks. The result is recorded in
[`results/offline-validation-20260906.txt`](results/offline-validation-20260906.txt).
The validator intentionally checks the frozen parent patch for the retained
restart-path `WDT_MODE_AUTO_START`; it does not claim source replay, a build,
hardware support, or a boot candidate.

The prior Buildbox attempt at exact commit
`e70982c09a16a0bb8b152a0dfcada7db69d2a0bf` failed before applying 0543 because
its first hunk expected stale source context. The corrected patch was replayed
read-only against the effective single-file chain in a temporary Buildbox
directory, proving preimage `9ee35ef` and postimage `cf093ee`.

Buildbox then applied all 530 patches, compiled `mtk_wdt.o`, linked Linux, and
validated the package from exact repository commit `745ecaea21c004a377a01287bea8ac3b58c2d6e2`.
The immutable build facts are in
[`results/buildbox-745ecaea.txt`](results/buildbox-745ecaea.txt). The fetched
package inventory is `9b14f15515bb56ec19eb39611a1262edfe56d9df25d3ed69828c4318d76498ca`.
This is compile and provenance evidence only: no boot candidate has been
constructed or selected, and no device or hardware-support claim follows.
