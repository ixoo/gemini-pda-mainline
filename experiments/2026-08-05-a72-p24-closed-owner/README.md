# Experiment: P24 lifecycle-closed owner oracle

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-05-a72-p24-closed-owner` |
| Status | `completed` (reviewed dormant C model plus independent source oracle) |
| Subsystem | arm64 late Cortex-A72 membership admission |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Date(s) | 2026-08-05 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 4, P24 |
| Claim | `PARTIAL_P24_CLOSED_OWNER_MODEL` |

## Question or hypothesis

Can an independent finite model prove the narrow initial-owner claim: while
the future P24 owner is lifecycle `CLOSED` and membership is
`UNINITIALIZED`, exact CPU8/gen42 and CPU9/gen7 requests are denied without
changing any owner or downstream state?

The answer is bounded deliberately. The oracle exhausts every subset of the
13 named diagnostic prerequisites, both caller-readiness values, and both
exact request identities. A complete diagnostic list and a ready caller are
still not authority. The separate all-applicable-review, A26-veto-lifted, and
implementation-enabled sentinels remain false, and no `AUTHORIZED` outcome is
reachable.

## Provenance and environment

- Model inputs: the frozen contract in [DESIGN.md](DESIGN.md).
- Kernel patch: `0159`, SHA-256
  `39cd3a9e158f2d7ed3e95856002f450709f5886f11e66c9920bb62952394e515`,
  prepared commit `f1cd16bf7bdd62d86cfb6a9f1553ada3f231d39c`.
- Selected source-state SHA-256:
  `035390e2350cfff576de28083db6904fbdddcc061c4231683942aa13b5c19452`;
  configuration-input SHA-256:
  `0fe5961a34c6f2ae14b12d36a30f9f9d7a852f6d628f9344f51297942de0cb58`.
- Runtime: Python 3 standard library only.
- The oracle imports no kernel module and reads no Linux source, patch,
  generated constant, configuration, build product, package metadata, result
  transcript, or device state.
- No kernel configuration was resolved and no compiler, build backend,
  package, boot image, target partition, network, or device was used.

## Safety assessment

This experiment is read-only with respect to kernel trees and hardware. It
constructs frozen Python values and enumerates a bounded input matrix. It does
not call firmware, issue CPU_ON, write a partition, reboot, or shut down a
device.

## Associated code

- [Closed-owner design](DESIGN.md)
- [Independent oracle](scripts/oracle.py)
- [Unsafe mutation runner](scripts/test_mutations.py)
- [Exact milestone validator](scripts/validate.py)
- [Oracle transcript](results/source-oracle-validation-20260805.txt)
- [Mutation transcript](results/mutation-validation-20260805.txt)
- [Kernel static review](results/kernel-static-review-20260805.txt)
- [Offline integration validation](results/offline-validation-20260805.txt)
- [Validator refresh](results/validator-refresh-20260806.txt)
- [`0159` closed-owner patch](../../patches/v7.1.3/0159-arm64-add-closed-A72-transaction-owner-model.patch)

No privileges or external dependencies are required.

## Procedure

Run from this experiment directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/oracle.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test_mutations.py
```

The first command must enumerate all 8,192 named-prerequisite subsets for
both caller-readiness values and both exact requests. Every exact probe must
return `DENIED_CLOSED`, every malformed fixture must return
`INVALID_IDENTITY`, the reachable correct owner-state count must remain one,
and the authorized count must remain zero. The second command must reject
every unsafe mutation by its intended invariant.

Then run:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate.py
```

The exact validator must bind the frozen patch, reviewed added-file hashes,
profile, canonical series, source/configuration identities, oracle, mutation
suite, documentation, safety gates, and every manifest profile.

## Observations

- The oracle enumerated 8,192 prerequisite subsets and 32,768 exact admission
  probes. All 32,768 were denied.
- Twelve single-field malformed identities were rejected before owner
  admission.
- The only reachable correct owner state remained the original
  `CLOSED`/`UNINITIALIZED` state. There were zero authorized outcomes and zero
  invariant violations.
- The sequential CPU8/gen42 then CPU9/gen7 witness denied both requests and
  reproduced the exactly equal frozen owner value after each denial.
- All 25 bounded unsafe mutants were detected by their intended checks.
- Three independent source reviews returned GO on the exact frozen patch.
  Strict file-mode Checkpatch reported zero errors, warnings, and checks for
  all three added files. Eight default-off KUnit cases are registered but were
  not built or run.
- The patch has zero production callers and no `CLOSED -> AVAILABLE` writer.
  It adds no P30 mutator, CPU_ON call, or hotplug registration/mutation path;
  the existing MT6797 boot and disable vetoes remain unchanged.
- While this source-only work was in progress, the owner reported that Gemian
  was rebooting. This is recovery chronology only: the milestone created no
  build, package, candidate, write, or boot, so the report neither validates
  nor rejects it.
- The exact offline validator passed the patch and reviewed-source identities,
  profile/configuration binding, documentation, oracle, mutation suite, and
  the retained original 64-profile series check.
- A 2026-08-06 validator refresh now permits the intentionally shared
  closed-owner fragment in descendant profiles, verifies that each such
  profile retains the complete closed-owner series as an ordered subsequence,
  and passes the current 67-profile manifest audit. The original milestone
  transcript remains historical evidence; the refresh is recorded separately.
- No kernel build, KUnit execution, runtime test, network access, or device
  action was performed.

## Analysis

The exhaustive matrix proves a deliberately negative property of this model.
It is impossible to turn caller claims, including the complete named
diagnostic list, into admission while the independent lifecycle authority is
closed. Denial occurs before P31/A38 or any attempt, token, membership,
provider, hardware, P30, callback-completion, commit, or rollback effect. The
same frozen value before and after every probe makes denial immutable rather
than merely repeatable by convention.

The diagnostic names are non-exhaustive labels, not capabilities. In
particular, presenting `A26_VETO` or `OWNER_IMPLEMENTATION` in a claimed
prerequisite subset does not change the separate false sentinels owned by the
future implementation. This distinction prevents either a ready caller or a
bounded checklist from becoming accidental authority.

The mutation suite is evidence about this finite Python specification only.
It does not compare or inspect a C implementation. The separately reviewed C
change implements the same initial `CLOSED`/`UNINITIALIZED` no-effect boundary,
and the exact validator binds its immutable patch and added-file hashes to this
record. That comparison does not extend the finite proof to kernel concurrency
or turn the dormant owner into production authority.

## Conclusion

Confirmed for the exact reviewed dormant C model:
`PARTIAL_P24_CLOSED_OWNER_MODEL`. CPU8 and CPU9 `CPUHP_ONLINE` probes return
`-EAGAIN` from `CLOSED`/`UNINITIALIZED` before P31/A38, with complete owner and
P30 snapshots unchanged.

Confirmed independently for the bounded oracle: prospective CPU8/gen42 and
CPU9/gen7 request fixtures are denied immutably for every named-prerequisite
subset and either caller-readiness value. Those generation, MPIDR, and cookie
fields are oracle fixtures, not inputs accepted or validated by the C
`begin_up(cpu, target, ...)` API. No `AUTHORIZED` oracle state is reachable.

This result makes **no claim** of a kernel build, KUnit execution, runtime
result, or device result. It supplies no production caller, no
`CLOSED -> AVAILABLE` opener, no generic CPU-up/CPUHP hook, and no P30E
MMU-off object or proof. It does not authorize a package, boot candidate,
deployment, CPU_ON request, or device action.

## Follow-up

[The roadmap](../../docs/ROADMAP.md) alone owns ordered next steps. Production
source and generic-hook integration require separate review and evidence.
