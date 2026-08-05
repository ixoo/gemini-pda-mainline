# Experiment: A41 canonical read-only capability planner

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-05-a72-a41-canonical-planner` |
| Status | `completed` (offline source-contract validation only) |
| Subsystem | arm64 capability finalization and MT6797 late Cortex-A72 profile |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Date(s) | 2026-08-05 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 4, A41 |

## Question or hypothesis

Can the partial A41 scaffold gain a canonical, bounded, read-only arm64
capability planner which records the exact known Cortex-A72 draft and rejects
every incomplete or drifted inventory without changing live kernel state?

This experiment does not ask whether CPU8 or CPU9 can be admitted. It cannot
close A41, create a boot candidate, or establish hardware support.

## Provenance and environment

- Kernel release: Linux 7.1.3, official archive SHA-256
  `be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc`.
- Pinned source baseline: commit
  `df9447fb8be9b03a643b00111dd25f6ce62be719`, tree
  `265ffcaf56d7ec453e0dd017f19a5373a13960ba`.
- Planner format-patch:
  [0150](../../patches/v7.1.3/0150-arm64-add-read-only-late-CPU-capability-planner.patch),
  commit `4c0300398ae77c99faca19bb6333868e1f70b299`, SHA-256
  `d9244d9f3815092b492608cd7882e471bd5026dc15f5ed4afe32ad94961dd427`.
- Selected series:
  [`patches/series-a72-reject-gate-a41-planner`](../../patches/series-a72-reject-gate-a41-planner),
  SHA-256 `50025a818157b395a8ee8980c279463876b94734da8a120c695b7c6d01690e05`.
- Ordered patchset identity:
  `5ce33180a753e2c386986c200563bf46c773cb9ec171916a9121e5e2a7cfbaa5`.
- Externally computed selected source-state identity:
  `a1573b40b7b8f5a8a87f7a2b9a431090bf714ed52c79cf1e93c78d28ce633c56`.
- Non-circular in-source parent identity:
  `2ef15df475d00e5ae0f85a1f25866cd4267a407af974b5c8cf992ad2e15e0a9b`.
  It identifies the exact pre-A41 reject-gate state, not patch 0150 or a
  running image.
- Selected manifest profile:
  `observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-reject-gate-a41-planner`.
- Ordered configuration-input identity:
  `528b2bbdea4df1e872d4671e73a788d0ecf3469d1ba24d6335ed158a1b8f63cf`.
  Patch 0150 embeds this exact digest. It is not a resolved or running
  `.config` identity.
- Build/compiler: not invoked; no compile claim is made.
- Boot path and target partition: none.

## Safety assessment

The procedure was host-side and read-only with respect to the device. Patch
0150 has no commit callback and does not write `system_cpucaps`, native or
compat HWCAPs, BHB private state, vectors, alternatives, PSCI state, or CPU
hotplug state. The patch-0092 `cpu_boot=-EAGAIN` and
`cpu_can_disable=false` vetoes remain, and the profile still inherits
`maxcpus=8`.

The selected profile always returns `-EAGAIN`. Every unclassified local
capability therefore retains the core-owned capability-inventory blocker and
keeps PREPARED, READY, build authorization, and device action unreachable.

## Associated code

- [Design record](DESIGN.md)
- [Implementation markers](results/implementation.tsv)
- [Effect inventory](results/effects.tsv)
- [Blocker inventory](results/blockers.tsv)
- [Capability classes](results/capability-classes.tsv)
- [Kernel static review](results/kernel-static-review-20260805.txt)
- [Offline validator](scripts/validate.py)
- [Adversarial mutation suite](scripts/test_mutations.py)

The scripts require Python, Git, the pinned repository inputs, and an exact
prepared Git source checkout containing the pinned baseline and final planner
commit. They need no privileges, network access, device access, or generated
kernel build/output tree. Their structural Python inspection is a review and
integrity attestation for these exact scripts, not a sandbox for arbitrary
modified Python.

## Procedure

1. Verify the exact format-patch, selected series, manifest profile,
   configuration fragment, and canonical-order subsequence.
2. Apply patches 0148, 0149, and 0150 sequentially to exact pinned source
   preimages in a temporary tree.
3. Inspect the applied source and require one bounded
   `0..ARM64_NCAPS-1` traversal over canonical `cpucap_ptrs`, bounded
   match-list and MIDR-list traversal, exact descriptor/scope checks, and an
   explicit pre-system-finalization guard.
4. Require the exact target/required draft of BHB loop `k=8`, erratum
   1742098, and speculative-AT, together with every planned-only effect in
   [`results/effects.tsv`](results/effects.tsv).
5. Require all other local predicates to remain unresolved, preparation to
   return `-EAGAIN`, every non-inventory evidence blocker to remain, and the
   patch-0092 admission/removal vetoes to remain unchanged.
6. Reject mutations that skip canonical slots or match members, alter the
   exact three-cap plan or `k=8`, weaken timing/blocker/veto rules, add a
   live mutation, return success, expose READY, authorize a build, or add a
   device path.
7. Run whitespace, duplicate-include, Checkpatch, link, sensitive-data, and
   repository manifest-series checks. Freeze only sanitized transcripts.

## Observations

- The planner visits every non-null canonical capability slot and records the
  compiled local subset without invoking `matches()` on the executing A53.
- Descriptor identity, exact Linux 7.1.3 composite types, canonical local-list
  OR semantics, nested match-list traversal, and MIDR-range-list traversal are
  checked. List iterations are capped by `ARM64_NCAPS`; offline validation
  separately proves the sentinels in the exact pinned source.
- The MT6797 profile resolves only the three current source-derived A72 rows.
  All other compiled local capabilities return
  `ARM64_LATE_CPU_CAP_UNRESOLVED`.
- Exact plan validation requires all three target and required bits, no
  conflicting bit, BHB loop `k=8`, and the complete planned effect mask.
- Planning rejects any call after system capability finalization.
- No live state mutation, commit callback, CPU_ON path, build, deployment, or
  device access occurred.

Exact pass counts and tool versions are frozen in
[`results/offline-validation-20260805.txt`](results/offline-validation-20260805.txt)
and
[`results/mutation-validation-20260805.txt`](results/mutation-validation-20260805.txt).

## Analysis

The hypothesis is confirmed only for the read-only planner boundary. The
implementation now derives its draft from the surviving canonical arm64
descriptor table rather than directly setting a three-bit profile bitmap. It
makes malformed populated descriptors, changed late-CPU type rules, a changed
BHB parameter, or an unknown required effect fail closed. The runtime table
does not independently reveal a descriptor rejected or omitted while
`cpucap_ptrs` was constructed; the exact source-identity blocker and offline
source validator remain responsible for that drift.

This is useful progress but not capability closure. Spectre-v2, Spectre-v4,
cache type, target ID registers, firmware responses, ASID width, granule,
active VA mode, GIC state, strict/system/boot capabilities, and native/compat
HWCAP compatibility remain unproven. The planner intentionally reports those
gaps rather than inferring target state from an unattributed visual or reboot
outcome.

## Conclusion

Confirmed for exact patch 0150: the canonical read-only planner is bounded,
records the known three-cap A72 draft and its effects, and remains fail closed
without changing live kernel or device state.

`a41_complete=no`, `boot_candidate=false`,
`build_authorized=no`, and `device_action_authorized=no`.

## Follow-up

[The roadmap](../../docs/ROADMAP.md) remains the sole owner of ordered project
work. The unresolved proof set is recorded in
[the blocker inventory](results/blockers.tsv). This experiment does not
authorize a build, deployment, boot, CPU_ON attempt, or device action.
