# Experiment: P24 closed generic admission-hook model

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-05-a72-p24-closed-hooks` |
| Status | `Buildbox-validated` (after proof-storage compile correction; no hardware action) |
| Subsystem | Generic CPU-up and arm64 MT6797 admission boundaries |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Date(s) | 2026-08-05 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 4, P24 admission hooks |
| Claim | `PARTIAL_P24_CLOSED_ADMISSION_HOOKS` |

## Question or hypothesis

Can two generic CPU-up admission hooks preserve default behavior everywhere
except the selected MT6797 A72 targets, while proving those targets stop before
generic work and every owner or hardware effect?

The modeled public hook precedes `cpu_possible`, node-online work, and CPU-map
locking. The modeled internal hook precedes per-CPU state lookup,
`cpus_write_lock`, CPUHP state mutation, callbacks, and the architecture boot
method. Direct thaw and SMT callers both reach the internal hook.

## Provenance and environment

- Model inputs: the frozen contract in [DESIGN.md](DESIGN.md).
- Kernel patch: `0160`, SHA-256
  `5fd606b8eb6554d7e9bcdc7a62548091f4e86476593b6999204f719013b8b287`,
  stable patch-id `4e9efdbc51626664a77d08ce402101c4080e4cee`, prepared commit
  `7fb9cec977e636c7df35b26588b493c05a1f102f`.
- Selected source-state SHA-256:
  `afa58437e1c1dc851ec131f56e297a2db9ade31ec510aad8160708c0a8f0e9bd`;
  configuration-input SHA-256:
  `6eca02a9f2831249d9353b2822cd0c3661f20bc540f13e460c5d5cee57bf396d`.
- Runtime: Python 3 standard library only for the independent oracle and
  exact validator.
- The oracle imports no kernel module and reads no Linux source, patch,
  generated constant, configuration, build product, package metadata, result
  transcript, or device state. The validator separately pins the patch,
  profile, source-order tokens, safety backstops, and these experiment files.
- No kernel configuration was resolved and no compiler, build backend,
  package, boot image, target partition, network, or device was used.

## Safety assessment

The oracle and mutation runner construct frozen Python values and enumerate a
bounded input matrix. The validator reads only repository-local source and
metadata; none of these scripts can call CPU hotplug, firmware, CPU_ON, the
owner transaction entry, or a device, and none writes hardware or artifacts.

## Associated code

- [Hook contract](DESIGN.md)
- [Independent oracle](scripts/oracle.py)
- [Unsafe mutation runner](scripts/test_mutations.py)
- [Exact milestone validator](scripts/validate.py)
- [Oracle transcript](results/source-oracle-validation-20260805.txt)
- [Mutation transcript](results/mutation-validation-20260805.txt)
- [Kernel static review](results/kernel-static-review-20260805.txt)
- [Offline integration validation](results/offline-validation-20260805.txt)
- [`0160` closed-hook patch](../../patches/v7.1.3/0160-cpu-add-closed-arm64-CPU-up-admission-hooks.patch)

No privileges or external dependencies are required. The validator invokes
only repository-local scripts and the standard Git patch-id and manifest
checks.

## Procedure

Run from this experiment directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/oracle.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test_mutations.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate.py
```

The oracle must preserve generic handling for the weak default, an arm64
method without callbacks, out-of-range inputs, and every MT6797 CPU0 through
CPU7 case. It must reject CPU8/CPU9 with the exact public, internal, frozen,
and intermediate-target errors, retain both existing safety backstops, and
leave the complete modeled state unchanged. The mutation runner must detect
every unsafe rule by its intended invariant. The exact validator binds those
observations to the immutable 0160 patch and the named 65-profile manifest
selection.

## Observations

- The oracle evaluated 32 admission probes across other architectures, arm64
  methods without callbacks, out-of-range dispatch, every MT6797 CPU0 through
  CPU7, and both MT6797 A72 CPUs.
- Twenty-two probes preserved generic handling: two weak-default, two
  optional-arm64-callback, two bounds, and sixteen MT6797 CPU0-through-CPU7
  cases.
- CPU8 and CPU9 each returned `-EAGAIN` at public `CPUHP_ONLINE` admission and
  at non-frozen internal `CPUHP_ONLINE` admission.
- Both frozen internal probes returned `-EPERM`; all four intermediate-target
  probes returned `-EINVAL`.
- Direct thaw and SMT path classes both reached the internal hook.
- The only reachable correct hook state was the initial immutable state.
  There were zero A72 authorizations and zero invariant violations.
- All 39 targeted unsafe mutants were detected by their intended checks.
- Two independent source reviews returned GO on the exact frozen patch.
  Strict file-mode Checkpatch reported zero errors, warnings, and checks.
  Ten default-off KUnit cases are registered but were not built or run.
- The patch adds no production caller, owner opener, transaction begin,
  P30 mutator, CPU_ON call, provider/member/hardware effect, or positive A72
  path. The existing MT6797 boot and disable vetoes remain unchanged.
- The exact offline validator passed the patch identity, source-order and
  dispatch checks, profile/configuration binding, documentation, oracle,
  mutation suite, and all 65 manifest-profile series checks.
- The first Buildbox attempt for the exact P24 profile exposed a source compile
  defect in the preceding R03/P29 ledger: its transaction referenced durable
  `provider_rejection` and `p29_rollback` records that were not stored. Patch
  0171 adds those two records; the corrected profile is validated separately
  in [Buildbox validation](results/buildbox-validation-20260806.txt). No KUnit
  execution, runtime test, network access, or device action was performed.
  Any Gemian reboot reports during this source-only work remain recovery
  chronology, not evidence for this claim.

## Analysis

The finite model separates three layers that must not be conflated. Generic
weak hooks preserve existing handling. Arm64 dispatch preserves it when a CPU
method has no callback or the CPU is outside the dispatch bound. The selected
MT6797 method preserves it for CPU0 through CPU7, but routes CPU8 and CPU9 to
an output-free, always-negative CLOSED-owner validation.

The negative result is decision-changing even when the eventual errno remains
`-EAGAIN`: public requests stop before generic topology and map work, while
direct thaw and SMT requests stop before internal CPUHP state and callbacks.
The existing CPU-boot and CPU-disable vetoes remain independent backstops.

The exact C mapping implements the same boundary: weak generic hooks preserve
default behavior; arm64 dispatch invokes optional callbacks without changing
out-of-range or missing-callback behavior; and the MT6797 adapter sends only
CPU8/CPU9 to a read-only CLOSED-owner check. The internal check performs only
bounded reads under its local raw spinlock and has no transition-mutex or
transaction entry. The source review and validator establish this mapping for
the frozen patch; they do not establish kernel concurrency, a build, or
hardware behavior.

The oracle proves only its bounded Python state machine and call-order model.
The separately reviewed C mapping and exact validator bind the same negative
contract to patch 0160, but neither extends the finite proof to kernel
concurrency or turns the dormant owner into production authority.

## Conclusion

Confirmed for the exact reviewed source model and independent bounded model:
`PARTIAL_P24_CLOSED_ADMISSION_HOOKS`. Default and unrelated paths preserve
generic handling; MT6797 CPU8/CPU9 are denied at both required entry points
before downstream work; and the complete owner/effect state remains
immutable.

This result makes **no claim** of a kernel build, KUnit execution, runtime
result, or device result. It supplies no owner opener, transaction begin,
P31/A38 attempt, token, P17/P18 publication, production P24 transaction, P30
integration, provider/member/hardware effect, CPU_ON call, or CPU boot. It
does not establish P30E, generic positive admission, a package, a boot
candidate, deployment, or hardware support.

## Follow-up

[The roadmap](../../docs/ROADMAP.md) alone owns ordered next steps. This exact
source-only mapping remains a closed denial seam; transaction/lifecycle
integration and KUnit execution require separate milestones and review.
