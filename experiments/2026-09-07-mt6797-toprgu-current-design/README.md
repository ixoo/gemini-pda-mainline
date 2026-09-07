# Experiment: MT6797 TOPRGU current policy design

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-07-mt6797-toprgu-current-design` |
| Status | completed hard-risk review; implementation refused |
| Subsystem | MediaTek watchdog system restart |
| Device variant | Existing named Gemini PDA; no device access |
| Date | 2026-09-07 |
| Investigator | Astra Medium specialist; accepted after Sol Medium integration review |

## Question

Does current primary-source and project evidence justify turning the historical
Gemini restart changes into an MT6797-wide upstream policy for TOPRGU mode bit 4
and restart priority?

**No.** The available evidence supports a downstream firmware convention and
one successful historical Gemini candidate. It does not establish a universal
MT6797 firmware contract or locate the earlier failed restart inside PSCI. No
implementation interface is admitted from this review.

The exact work boundary is in [the contract](WORK_ITEM.md), and current source,
archive and retained-project identities are in
[the receipt](results/source-review.json). This review refines the
[2026-09-05 readiness assessment](../2026-09-05-mt6797-toprgu-upstream-preparation/README.md)
without rewriting its chronology.

## Current source and overlap

Mainline `c297ed90fbba72d32b7759aae362b36d15b2db1f` retains the source bytes
reviewed on 2026-09-05 for the relevant watchdog, PSCI, binding and MT6797 DTS
files. It has no explicit MT6797 watchdog match, preserves mode bit 4 in the
restart path, gives the MediaTek watchdog priority 128 and gives PSCI priority
129. MediaTek `for-next` at `f5be25e697e0362103625b1b197af126ae4ba5f7`
differs in the watchdog file for optional-IRQ handling, not for this policy.
The inspected `linux-staging` `watchdog-next` snapshot at
`b85ed7f7259b49077955e835ecc32b32b75053e8` also contains no MT6797 match or
restart-policy change. This snapshot is overlap evidence, not a selected
submission base.

Two distinct public topics touch the required match-data area:

- Akari Tsuyukusa's [July explicit-compatible patch](https://lists.openwall.net/linux-kernel/2026/07/16/1686)
  proposes an MT6797 match while changing fallback policy.
- Luca Scorcia's [August v4 reset series](https://lists.openwall.net/linux-kernel/2026/08/19/855)
  changes MT6589/MT8167 reset support and the match-data structure. Akari's
  [review reply](https://lists.openwall.net/linux-kernel/2026/08/19/1675)
  calls out fallback-layout hazards including MT6797.

These are separate series. Their presence does not establish acceptance, but it
does make private match-data plumbing an upstream coordination point. Resolve
both against the authenticated final watchdog submission base before drafting.

## Policy verdict

### Mode bit 4

The retained public MT6797 downstream driver describes bit 4 as a firmware
power-key-bypass convention. Its reset routine sets or clears the bit according
to a caller argument and also performs other mode, secure-call and PMIC actions.
That proves neither that bit 4 alone is sufficient nor that every MT6797 boot
firmware requires Linux to force it.

A future proposal may consider a restart-only bit policy, structurally leaving
watchdog start, adoption, resume and pretimeout behavior unchanged. This review
does not establish the MT6797-wide safety of that change and therefore does not
authorize an implementation. Do not import the broader downstream reset
sequence or historical patch 0081's watchdog-runtime normalization.

### Restart priority

Keep upstream priority 128 in any new local design until ownership is proven.
Priority 130 is the smallest value above current PSCI priority 129, but it still
selects TOPRGU before firmware for every matching MT6797 system. Priority 255
also outranks every handler in the intervening range and is broader still. The
historical failed restart did not retain a PSCI-handler entry, while Candidate
AB's [single attended result](../2026-07-20-mt6797-kernel-restart-diagnostic/results/runtime-candidate-ab-attempt-1-20260721.txt)
did not isolate priority from its complete candidate.
Neither value is justified as SoC-wide policy.

### Match data and reset registration

Current probe code registers a reset controller whenever match data exists;
reset core does not reject a zero reset count. If policy-only match data is ever
admitted, a nonzero-count guard must keep zero-count policy data from publishing
an empty reset controller, preserve null-data behavior and retain existing
positive-count providers. Match data must also be available before watchdog
restart publication. Pending compatible/reset work owns part of this structure.

## Conditional smallest split

Only if later evidence admits the policies, keep two independent behavior
changes:

1. restart-only bit-4 selection with the minimum match-data plumbing and
   zero-count reset separation;
2. a separately justified restart-ordering change.

Exclude TOPRGU reset IDs and `#reset-cells`, fallback cleanup, watchdog
start/adoption/pretimeout changes, A72 work and all observers. This is a scope
boundary for future review, not approval to generate either patch.

## Evidence limit and next check

Candidate AB's [experiment record](../2026-07-20-mt6797-kernel-restart-diagnostic/README.md)
and exact attended result prove one restart for its historical artifact on the
named Gemini. They do not prove a current minimal derivative, priority-130
equivalence, bit-4 necessity or behavior on other MT6797 firmware.

The historical implementation inputs remain immutable evidence:
[0081 mode policy](../../patches/v7.1.3/0081-watchdog-mtk-set-MT6797-auto-restart-mode.patch),
[0087 restart priority](../../patches/v7.1.3/0087-watchdog-mtk-prioritize-MT6797-TOPRGU-restart.patch)
and [0090 reset export](../../patches/v7.1.3/0090-watchdog-mtk-expose-MT6797-TOPRGU-resets.patch).
None is selected as a modern outgoing patch by this review.

The next discriminating evidence is a primary firmware contract showing bit-4
semantics across supported MT6797 boot firmware, plus an attributable trace that
locates the failed restart stage and establishes whether firmware bypass is a
SoC requirement or a narrower platform limitation. If only Gemini evidence can
be obtained, return to upstream owners with that narrower design question; do
not encode it silently as generic MT6797 match data.

## Safety and validation

This was read-only source and archive review. Exact ref queries, file hashes and
the existing runtime record were checked. No patch, manifest, series, profile,
kernel source, build, VM, private capture, device state or upstream mailbox was
changed. No modern `Tested-by`, author identity, DCO sign-off or maintainer
agreement follows.

The first integration review accepted the technical verdict and requested
direct identities for retained project evidence. One documentation-only repair
added the links and hashes now present in the contract, this record and the
receipt. The second review verified all seven retained links and hashes and
accepted the packet. No technical claim or stop decision changed.
