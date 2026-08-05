# Experiment: A41 attributable per-target capability planning

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-05-a72-a41-per-target-plan` |
| Status | `completed` (offline source-contract validation only) |
| Subsystem | arm64 capability finalization and MT6797 late Cortex-A72 profile |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Date(s) | 2026-08-05 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 4, A41 |

## Question or hypothesis

Can the planner preserve independent CPU8 and CPU9 capability results, bind
each result to one exact registered logical CPU, and reject evidence declared
FIXTURE or incomplete RUNTIME before plan publication while retaining all
existing admission vetoes?

## Provenance and environment

- Linux release: 7.1.3, official archive SHA-256
  `be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc`.
- Patch 0153 source parent: commit
  `63e5d894150a5d5d1d897a639199a096815bb385`, tree
  `c3db9d87cf885b6e2313041e1e3b8b28ea8e98c1`.
- Patch 0153 source commit:
  `7fcc8ca433d2306d2e3d005289d6cf01dfbf0f4c`, tree
  `47133d89119afe60e38057c8ac39840665a1f142`, diff SHA-256
  `a4927f805364a0cace03dd1c0326c59f33479b9d47e3db2600541969e52a5d1f`.
- Format-patch:
  [0153](../../patches/v7.1.3/0153-arm64-preserve-per-target-late-CPU-capability-state.patch),
  SHA-256
  `c89fa4c00ee56fbf259f3ddbc19d7434fb08d7bac91530db5f8d5f5d54e3caa7`.
  It uses a synthetic, non-certifying experiment author, has no
  `Signed-off-by`, and is not submission-ready.
- Selected series:
  [`patches/series-a72-reject-gate-a41-per-target-plan`](../../patches/series-a72-reject-gate-a41-per-target-plan),
  95 entries, SHA-256
  `85874b97036200f24cb0f72cc4bc2592963f8aeb71fa9dfeb88d6e2c95ff19ca`.
- Ordered patchset identity:
  `e7f8a5aadc4103ae0723bdac55ec5405600cabdcca9bfd0fe50453f09e0af012`.
- Externally computed selected source-state identity:
  `78fcb018e5693cc258127ea6e2655319f55b80135c1230cb42fbf70c6d2e6deb`.
- In-source non-circular parent identity:
  `f073150a6bbfb6af1d4262f4b754534118181ee40284d60a59aa1068740d118d`.
  It identifies the exact patch-0152 selected source state, not patch 0153 or
  a running image.
- Selected profile:
  `observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-reject-gate-a41-per-target-plan`.
- Ordered configuration-input identity:
  `4dfe301404e0d972342311b51e9c9674d7ec3bc5198912fb2ec7f6167f72fb3e`.
  It is not a resolved or running `.config` identity.
- Build/compiler: not invoked; no compile claim is made.
- Boot path and target partition: none.

## Safety assessment

No kernel build, package, boot image, partition write, CPU request, firmware
call, device connection, or network operation was made. The inherited
`maxcpus=8` policy and patch-0092 `.cpu_boot = -EAGAIN` and
`.cpu_can_disable = false` vetoes remain unchanged.

The owner's contemporaneous Gemian recovery reboot is not attributed to this
source-only milestone and supplies no A72 evidence.

## Associated code

- Patch 0153 and its selected series/profile above.
- [Design](DESIGN.md).
- [Implementation markers](results/implementation.tsv).
- `scripts/validate.py` and `scripts/test_mutations.py`; both are offline and
  require no privilege.

## Procedure

1. Start from exact source commit `63e5d894…` and retain the patch-0152
   40-row expected-A72 census.
2. Add an explicit logical-CPU mapping for both target slots and validate its
   uniqueness and equality with the registered mask before classification.
3. Run every local descriptor and every match-list member independently for
   each slot, retaining two classified/present bitmap pairs.
4. Add the versioned runtime-binding schema and require complete matching
   fields declared RUNTIME before any future plan publication; do not claim
   that this milestone independently attests who supplied that declaration.
5. Require the exact per-target 34/4/30/6 partition, empty runtime evidence,
   all standing blockers, zero plan identity, and `-EAGAIN`.
6. Run patch, source, canonical-series, veto, and adversarial mutation checks.

## Observations

- Slot 0 maps uniquely to CPU8; slot 1 maps uniquely to CPU9.
- Each target independently retains 34 classified rows, of which 4 are
  PRESENT and 30 ABSENT; the same 6 dynamic rows remain UNRESOLVED.
- Aggregate classified state is the intersection of both target classifications;
  aggregate presence is their union only after complete classification.
- Runtime binding is origin NONE with zero validity and identities. Both the
  profile and architecture lifecycle keep RUNTIME_BINDING set.
- Planner failure and profile-validation failure now receive distinct
  CAP_INVENTORY and PLAN_VALIDATION blocker bits.
- The partial validator and preparation path return `-EAGAIN`;
  `local_caps_planned` and every plan-identity word remain zero.

## Analysis

The hypothesis is confirmed for the blocked representation boundary. ABI 3
could hide CPU8/CPU9 disagreement behind one aggregate callback result. ABI 4
cannot classify either slot until its logical CPU is attributable, and it
retains each result independently. Declared FIXTURE data may later exercise the
six-row evaluator but cannot satisfy the publication guard. The origin and
identities are still supplied by the profile, however, so ABI 4 does not attest
that a record labeled RUNTIME came from an independent runtime producer. That
producer and its validation remain a later gate; the current MT6797 profile
supplies only NONE and remains blocked independently.

This closes no hardware row. CPU8 and CPU9 still need observed register,
GIC/hyp, cache, firmware, resolved/running configuration, image, and command
line evidence, plus a complete typed-effect plan.

## Conclusion

Confirmed for Linux source commit `7fcc8ca4…`: the implementation state is
`PARTIAL_PER_TARGET_PLAN_BOUNDARY`. A41 is incomplete; PLAN_FROZEN, COMMITTED,
READY, build, boot candidate, device action, and hardware-support claims remain
unavailable.

## Roadmap boundary

[The roadmap](../../docs/ROADMAP.md) alone owns the ordered next action and
exit criteria.
