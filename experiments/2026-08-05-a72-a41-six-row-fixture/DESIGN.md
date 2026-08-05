# A41 ABI-5 six-row fixture-evaluator design

## Boundary

Patch 0154 advances the blocked ABI-4 representation to an ABI-5 pure
classifier and typed-effect evaluator for one exact source fixture:

```text
exact FIXTURE evidence for CPU8 and CPU9
        |
        v
40 source-owned descriptors evaluated per target
        |
        +-- target0: 40 classified / 8 present / 32 absent
        +-- target1: 40 classified / 8 present / 32 absent
        |
        v
6 required rows + exact per-target and aggregate typed effects
        |
        v
profile validator returns -EAGAIN; plan identity remains zero
        |
        v
runtime-binding + commit-path blockers
        |
        v
no PLAN_FROZEN / COMMITTED / READY / CPU_ON
```

The output exists only in the architecture-owned scratch plan. No evaluator
field authorizes a live capability, alternative, vector, HWCAP, or firmware
mutation.

## Exact fixture input

The fixture evidence identity is
`c41b8b84d68f9c0f05a9a047d319de9cfe8d41e8b792cb509ffa4be08341e887`.
Its binding origin is FIXTURE, with binding validity zero and all resolved,
running, image, and command-line identity words zero.

Both targets have the same policy and register contract except for logical CPU
and MPIDR:

| Field | Target 0 | Target 1 |
| --- | --- | --- |
| Logical CPU | 8 | 9 |
| MPIDR | `0x200` | `0x201` |
| MIDR | `0x410fd080` (Cortex-A72) | `0x410fd080` (Cortex-A72) |
| REVIDR | `0` | `0` |
| Raw CTR | `0x83338003` | `0x83338003` |
| CLIDR | `0` | `0` |
| Effective CTR | `0x93338003` | `0x93338003` |
| PFR0/PFR1/PFR2, ISAR2, MMFR1 | all zero | all zero |
| ICC SRE/IDR0 and ICH VTR/status | all zero | all zero |
| Hypervisor state | available, kernel not in hyp mode | available, kernel not in hyp mode |
| ICH VTR source | `ARM64_LATE_CPU_ICH_VTR_NONE` | `ARM64_LATE_CPU_ICH_VTR_NONE` |
| SMCCC WA1 / WA2 | `SMCCC_RET_SUCCESS` / `SMCCC_RET_SUCCESS` | `SMCCC_RET_SUCCESS` / `SMCCC_RET_SUCCESS` |
| SMCCC WA3 | not valid; zero | not valid; zero |
| Policy | SMC, mitigations on, `nospectre_v2=0`, V4 dynamic | identical |

The target capability-valid mask contains MIDR, ID registers, CTR, GIC, hyp,
WA1, and WA2. It deliberately excludes WA3, ASID, granule, and VA evidence.
The system evidence is exact: CTR `0xb4448004`, strict mask
`0xffffffffffff3fff`, SSBS zero, and UNAFFECTED early Spectre-v2, Spectre-v4,
and BHB state with zero BHB matcher count and method bits.

The ordered configuration-input identity is
`8ab011246184c5fff4885bdc38fef09d24cc31960235fb7640ea081505949815`.
It identifies profile inputs, not a resolved or running configuration.

## Six evidence-dependent rows

| Slot | Capability | Exact result | Decision input |
| --- | --- | --- | --- |
| 33 | `ARM64_HAS_GICV5_LEGACY` | ABSENT | GCIE and legacy fields are zero; SRE cross-check is consistent. |
| 36 | `ARM64_HAS_ICH_HCR_EL2_TDIR` | ABSENT | GIC is unusable and ICH source is NONE with zero value/status. |
| 69 | `ARM64_MISMATCHED_CACHE_TYPE` | PRESENT | Both masked raw and recomputed effective CTR differ from system CTR. |
| 79 | `ARM64_SPECTRE_V2` | PRESENT | CSV2 is zero and the exact WA1 status is SUCCESS. |
| 81 | `ARM64_SPECTRE_V4` | PRESENT | SSBS is zero and the exact WA2 status is SUCCESS. |
| 82 | `ARM64_SPECTRE_BHB` | PRESENT | CSV2 is not 3; ClearBHB and ECBHB fields are zero. |

The other 34 rows retain their source-static results. Therefore every target
and the aggregate classify all 40 rows: 8 PRESENT and 32 ABSENT. The four new
PRESENT rows plus static slots 94 and 121 make the exact required set
`{69,79,81,82,94,121}`.

## Typed effect derivation

V2 and V4 are evaluated first for each target. The aggregate system V2 state is
then folded before evaluating BHB, because BHB method validity depends on V2
not being vulnerable. Shared aggregate fields are emitted only after the two
target effects compare equal.

The exact aggregate is:

- CTR: required for target mask `0x3`; trap CTR_EL0 and install the alternative.
- Spectre-v2: MITIGATED through SMC, SMC callback, Spectre-direct hyp vector,
  and alternative.
- Spectre-v4: MITIGATED through firmware/SMC under DYNAMIC policy, callback
  mask `0x3`, and firmware alternative.
- Spectre-BHB: MITIGATED through the Cortex-A72 loop method, loop count and
  matcher count 8, loop vector template, Spectre-direct hyp vector, no firmware
  conduit, system method `0x1`, alternative, and V2-non-vulnerable flag.
- Static effects: compat AES clearing and speculative-AT finalization.

[The typed-effects table](results/typed-effects.tsv) records all 33 aggregate
fields and all 18 fields for each target, including enum choices and exact
masks.

## Validation and reachability

The fixture profile validator requires all of the following at once:

- ABI 5, exact target mapping, exact evidence/config/source identities, and
  FIXTURE origin;
- exact 40-row per-target and aggregate classification with the six-row
  required set and no conflicts;
- exact target policy, named firmware statuses, system baseline, and every
  typed effect field;
- `local_caps_planned=1` and `effects_planned=1` in scratch state;
- zero plan identity and no HWCAP draft; and
- the standing MT6797 blocker set, including RUNTIME_BINDING and COMMIT_PATH.

After all conditions pass, `validate_plan` deliberately returns `-EAGAIN`.
The profile `prepare` callback also returns `-EAGAIN`, and the architecture
core independently adds COMMIT_PATH. Consequently the lifecycle can publish
only BLOCKED. The unavailable commit function still panics if invoked out of
order, while patch 0092 continues to reject `.cpu_boot` with `-EAGAIN` and
`.cpu_can_disable` remains false.

## Failure semantics

| Mutation or unsupported case | Result |
| --- | --- |
| Unknown or reserved SMCCC status | row/effect remains unresolved; plan fails closed |
| Reserved ID-register value or inconsistent validity | row/effect remains unresolved or invalid |
| CPU8/CPU9 policy or typed-effect disagreement | aggregate evaluator rejects with `-EOPNOTSUPP` |
| Early Spectre-v2/v4/BHB state not UNAFFECTED | effect evaluator rejects with `-EOPNOTSUPP` |
| Fixture identity, target identity, evidence, or exact output drift | profile validator returns `-EINVAL` |
| Runtime binding remains FIXTURE/incomplete | RUNTIME_BINDING remains set |
| Any blocker remains | no PLAN_FROZEN, commit, verification, or READY state |

## Claim limit

The implementation state is exactly
`PARTIAL_SIX_ROW_FIXTURE_EVALUATOR`. Its accepted positive domain is the exact
named-status fixture, identical target policy, and unaffected early baseline.
It does not model arbitrary firmware behavior and does not attest a runtime
evidence producer. No build, device, network, boot, CPU admission, or hardware
support is claimed.

The latest user chronology—boot2 start followed by a Gemian reboot—is
inconclusive and unattributed to this source-only work.
