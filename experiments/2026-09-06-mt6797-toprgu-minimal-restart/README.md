# Experiment: minimal MT6797 TOPRGU restart diagnostic

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-06-mt6797-toprgu-minimal-restart` |
| Status | complete offline; accepted after repair 2 at 2026-09-06T08:53:09Z |
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
Gemini; one unit cannot establish generic upstream policy. No candidate, build,
device selection or runtime claim exists yet. Source replay, Checkpatch,
Buildbox compilation, device readiness and hardware equivalence remain pending
separate gates.

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
