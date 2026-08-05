# Experiment: A41 core-owned runtime-evidence boundary

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-05-a72-a41-runtime-evidence-owner` |
| Status | `completed` (offline source-contract validation of exact patch 0155 only) |
| Subsystem | arm64 capability finalization and MT6797 late Cortex-A72 profile |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Date(s) | 2026-08-05 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 4, A41 |
| Claim | `PARTIAL_RUNTIME_EVIDENCE_OWNER_BOUNDARY` |

## Question or hypothesis

Can ABI 6 remove the profile's authority to declare runtime observations,
give the arm64 core a private evidence record with an exact seal point, and
still remain deliberately empty and blocked until independent producers
exist?

This experiment tests only that source ownership boundary. It does not
produce target-local observations, parse a boot provenance record, establish
a complete runtime binding, freeze a plan, mutate an architecture capability,
or admit CPU8 or CPU9.

## Provenance and environment

- Kernel release: Linux 7.1.3, official archive SHA-256
  `be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc`.
- Reviewed source parent: commit
  `57d36fd59821b7de2fd81c938414e7f3c5a54229`, tree
  `253625b12d09411997e1877a58ffd843f417ad7d`.
- Patch 0155 source commit:
  `bcfb60248633bec2cdb6ab70540d5807d305c4e7`, tree
  `b23bf9e6332c865ef15606a41f11e75262e06fbf`.
- [Format-patch 0155](../../patches/v7.1.3/0155-arm64-separate-late-CPU-runtime-evidence-ownership.patch),
  SHA-256
  `bc52553d645d9d33c77e6b31e630be2243b8cb3984729422fc0ef0a7d5d45928`.
  Its `From` header names exact source commit `bcfb6024…`. The patch uses the
  synthetic, non-certifying author
  `Gemini Mainline Project <noreply@invalid>`, has no `Signed-off-by`, and is
  not submission-ready.
- The exact source change touches only
  `arch/arm64/include/asm/late_cpu_profile.h`,
  `arch/arm64/kernel/late_cpu_profile.c`,
  `arch/arm64/kernel/mt6797_psci.c`, and
  `arch/arm64/kernel/smp.c`.
- Selected manifest profile:
  `observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-reject-gate-a41-runtime-evidence-owner`.
- [Selected series](../../patches/series-a72-reject-gate-a41-runtime-evidence-owner):
  97 entries, SHA-256
  `04a20ca7ac3d979c8334ab419baed203d80c2d1c183b3a00cd44eb095293455f`.
- Ordered patchset identity:
  `ff75286cf2372fac435f5e4aae284411df8b7b9db1b167258927a707da070477`.
- Externally computed selected source-state identity:
  `c22cfc0af5aa41ca03ce1e13844866d559eac09a08718191b8857e50078f9092`.
- Ordered manifest configuration-input identity:
  `7b875e34f11c7c6d007124aacc3e1e013acc41cc1628913a94cfddf0be8d7a74`.
  This is not a resolved or running `.config` identity.
- ABI-6 fixture evidence identity:
  `09c1750da0e98f35673ef55cf6389158e301a82bbd6756342fe28427cc4d6118`.
  It is a source-fixture identity and cannot establish runtime origin.
- ABI: `ARM64_LATE_CPU_PLAN_ABI=6`.
- Kernel profile identifier: `mt6797-a53-a72-a41-v6`.
- Configuration: no configuration was resolved or built during this work.
  The existing default-off fixture path remains a source fixture, not runtime
  evidence.
- Build/compiler, package, boot image, boot path, and target partition: none.
- Device and network access: none.

## Safety assessment

This work implemented and inspected the four-file source change, generated
format-patch 0155, and added offline validation and documentation. It did not
build a kernel, call firmware, request `CPU_ON`, connect to the Gemini, write
a partition, reboot, or use the network.

The inherited `maxcpus=8` policy and patch-0092
`.cpu_boot = -EAGAIN` and `.cpu_can_disable = false` vetoes remain unchanged.
The ABI-6 change adds no producer API and no path to publish runtime evidence.
It also retains the unconditional `COMMIT_PATH` blocker and unavailable
architecture mutation transaction.

The contemporaneous owner report that Gemian was rebooting was not observed
or used by this experiment. It supplies no attributable kernel, CPU8, CPU9,
or A41 evidence.

## Associated records

- [Design and future producer contracts](DESIGN.md)
- [Field ownership](results/field-ownership.tsv)
- [Implementation markers](results/implementation.tsv)
- [Independent ownership oracle](scripts/owner_oracle.py)
- [Adversarial ownership tests](scripts/test_owner_oracle.py)
- [Offline source/repository validator](scripts/validate.py)
- [Source/repository mutation suite](scripts/test_mutations.py)
- [Owner-oracle transcript](results/owner-oracle-validation-20260805.txt)
- [Offline validation transcript](results/offline-validation-20260805.txt)
- [Mutation transcript](results/mutation-validation-20260805.txt)
- [Kernel static review](results/kernel-static-review-20260805.txt)
- [Patch 0155](../../patches/v7.1.3/0155-arm64-separate-late-CPU-runtime-evidence-ownership.patch)
- [Selected series](../../patches/series-a72-reject-gate-a41-runtime-evidence-owner)
- [Default-off profile fragment](../../configs/gemini-a72-a41-runtime-evidence-owner.fragment)
- Parent fixture experiment:
  [A41 ABI-5 six-row fixture evaluator](../2026-08-05-a72-a41-six-row-fixture/README.md)

The Python oracle models ownership and negative cases independently of kernel
source. It does not model a real target provider or make runtime evidence
available. It covers the currently reachable OPEN, SEALED_EMPTY, and FAULT
states; it deliberately does not model the reserved future SEALED_RUNTIME
overlay. No generated kernel tree, package, or runtime capture is part of this
record.

## Procedure

1. Start from exact source commit `57d36fd5…`, apply patch 0155, and inspect
   the resulting four-file ABI-6 source change and exact tree.
2. Confirm that the runtime record is private arm64-core `__initdata`, begins
   in `OPEN` with ABI 6 and origin `NONE`, and has no public writer or producer
   API.
3. Confirm that `smp_cpus_done()` calls the seal immediately after
   `hyp_mode_check()` and before profile preparation and system-capability
   finalization.
4. Trace release publication by the seal and acquire consumption by profile
   preparation.
5. Exercise the source decision table by inspection: profile origin RUNTIME,
   invalid origin, NONE with observations, FIXTURE, sealed-empty core state,
   and the reserved future sealed-runtime state.
6. Confirm that the existing fixture evaluator remains source-only and that
   all plan, commit, READY, admission, and device gates remain closed.
7. Run the independent ownership oracle's adversarial tests and require every
   NONE, FIXTURE, and profile-declared RUNTIME path to remain non-production.
8. Run the pinned repository/source validator and its adversarial mutation
   suite against the exact prepared source tree.
9. Run `git diff --check`, strict checkpatch with the policy-required missing
   sign-off exclusion, and the duplicate-include check. Do not compile, build,
   package, deploy, or access the device.

## Observations

- ABI 6 introduces private `late_runtime_evidence` storage and the states
  `OPEN`, `SEALED_EMPTY`, `SEALED_RUNTIME`, and `FAULT` in arm64 core code.
- The private record is statically initialized with ABI 6. Zero initialization
  leaves origin `NONE`, validity zero, all identities and observations zero,
  and no initial blocker while the record is `OPEN`.
- `arm64_seal_late_cpu_runtime_evidence()` runs immediately after
  `hyp_mode_check()`. It rejects a repeated or late seal, an invalid ABI or
  origin, and an incomplete runtime identity binding labeled RUNTIME. It does
  not yet validate whole-record target or system evidence completeness.
- No producer exists in this milestone. The seal therefore adds
  `ARM64_LATE_CPU_BLOCK_RUNTIME_BINDING` and release-publishes exactly
  `SEALED_EMPTY`.
- Preparation acquire-loads the seal state before invoking the profile. An
  unsealed or faulted record blocks as `runtime evidence was not sealed`.
- A profile that labels its own evidence RUNTIME blocks as
  `profile declared runtime evidence`. A profile with origin NONE but a
  nonempty binding, evidence identity, observed target identity, target
  capability, target policy, or system capability blocks as
  `profile supplied runtime observations`.
- An explicit FIXTURE remains usable by the pure source evaluator. It is not
  overlaid with core runtime data and cannot satisfy the runtime-binding gate.
- `SEALED_RUNTIME` and the overlay helper describe a future consumption path,
  but are unreachable because no writer exists for the private record.
- The MT6797 profile still returns `-EAGAIN`, the canonical plan identity is
  zero, `COMMIT_PATH` remains set, and PLAN_FROZEN, COMMITTED, READY, and A72
  admission remain unreachable.
- The offline repository/source validator passed 17/17 checks, its mutation
  suite rejected 29/29 unsafe changes, and the independent ownership oracle
  passed 22/22 adversarial cases. `git diff --check`, strict checkpatch
  (0 errors, 0 warnings, 0 checks with the repository-policy sign-off
  exclusion), and duplicate-include review passed. No compile or runtime
  validation was performed.

## Analysis

The source boundary removes ABI 5's circular ownership flaw: a profile can no
longer write both expected and running fields and then make equality appear to
be runtime attestation merely by selecting origin RUNTIME. ABI 6 reserves the
running record and its origin for architecture code, seals the write window at
one ordered point, and blocks every current production path because that
record is empty.

`SEALED_EMPTY` is not weak runtime evidence. It is positive lifecycle evidence
that the core closed an empty record before planning. The runtime-binding
blocker is therefore the required result, not an implementation failure.

The boundary does not make the core record trustworthy by itself. A future
implementation still needs two independent inputs: a build-produced expected
identity record and target-local observations produced by CPU8 and CPU9 (or a
separately trusted pre-Linux attestation). Those contracts are specified in
[the design](DESIGN.md), but neither exists in ABI 6.

## Conclusion

Confirmed only for exact patch 0155 and its source-contract oracle: ABI 6
establishes `PARTIAL_RUNTIME_EVIDENCE_OWNER_BOUNDARY`. The arm64 core owns a
private record, seals it after hypervisor-mode resolution and before capability
finalization, and rejects profile-authored RUNTIME evidence. Because there is
no producer, the only current production result is sealed-empty and blocked.

`a41_complete=no`, `runtime_evidence_complete=no`,
`plan_frozen_reachable=no`, `boot_candidate=false`,
`build_authorized=no`, and `device_action_authorized=no`.

This is not a build result, runtime result, hardware-support result, or claim
that CPU8 or CPU9 can execute safely.

## Follow-up boundary

[The roadmap](../../docs/ROADMAP.md) alone owns ordered next steps. This
experiment records ownership and future interfaces; it does not authorize a
build, boot image, deployment, CPU_ON transaction, boot, or device action.
