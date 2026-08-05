# Experiment: P30 generation protocol source oracle

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-05-a72-p30-generation-protocol` |
| Status | `completed` (reviewed dormant C model plus independent source oracle) |
| Subsystem | arm64 late Cortex-A72 admission protocol |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Date(s) | 2026-08-05 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 4, P30 |
| Claim | `PARTIAL_P30_PROTOCOL_MODEL` |

## Question or hypothesis

Can an independent finite-state model express the corrected P30 generation
contract and reject bounded mutations of its safety and progress rules?

The modeled contract uses opaque, one-shot generations scoped to each
operation. Its decisive success trace retires CPU8 generation 42 and then
accepts and retires CPU9 generation 7; no global generation ordering is
permitted.

## Provenance and environment

- Model inputs: the frozen corrected P30 contract summarized in
  [DESIGN.md](DESIGN.md).
- Kernel patch: `0158`, SHA-256
  `7055f48c5257689b19e9ab32c71075d23ea041eb735a66b59482f0c1a7d9957c`,
  prepared commit `1402ad95c4db48dd38140c62aea6bf916853f414`.
- Selected source-state SHA-256:
  `dab76fafaf0c21695cfb242329c442ceb137e835f7ca143272b07ef8e7be47fb`;
  configuration-input SHA-256:
  `699f14786e1d64eb3811f0b6c481c31d9e0e77fc96b64eb4d12ebbbfde3b23b0`.
- Runtime: Python 3 standard library only.
- Kernel source, generated constants, build products, package metadata, and
  device state are not read by the oracle.
- No kernel configuration was resolved and no compiler, build backend,
  package, boot image, target partition, network, or device was used.

## Safety assessment

This experiment is read-only with respect to kernel trees and hardware. It
constructs immutable Python values and performs a bounded breadth-first search.
It does not call firmware, issue CPU_ON, write a partition, reboot, or shut
down a device.

## Associated code

- [Protocol design](DESIGN.md)
- [Independent BFS oracle](scripts/oracle.py)
- [Mutation runner](scripts/test_mutations.py)
- [Exact milestone validator](scripts/validate.py)
- [Validation transcript](results/source-oracle-validation-20260805.txt)
- [Offline integration validation](results/offline-validation-20260805.txt)
- [Kernel static review](results/kernel-static-review-20260805.txt)
- [`0158` dormant model patch](../../patches/v7.1.3/0158-arm64-add-dormant-late-CPU-startup-arbitration.patch)

No privileges or external dependencies are required.

## Procedure

1. Run `PYTHONDONTWRITEBYTECODE=1 python3 scripts/oracle.py` from this
   experiment directory.
2. Require a complete BFS with zero contract violations and the explicit
   CPU8/gen42 then CPU9/gen7 retirement witness.
3. Run
   `PYTHONDONTWRITEBYTECODE=1 python3 scripts/test_mutations.py`.
4. Require every bounded unsafe mutant to be detected by its intended check.
5. Run `PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate.py` and require the
   exact patch, reviewed source hashes, profile, canonical series, source and
   configuration identities, oracle, documentation, and all 63 manifest
   profiles to pass.

## Observations

- The corrected model explored 144 reachable states and 240 accepted
  transitions with zero violations.
- The exact success witness retired CPU8 generation 42 before CPU9 generation
  7 and rejected replay of both retired tokens.
- All 17 bounded unsafe mutants were detected by their intended checks.
- Two independent source reviews returned GO on header SHA-256 `8e601ae0…`,
  model SHA-256 `240a7fc6…`, and KUnit SHA-256 `8d33a563…`. File-mode
  Checkpatch reported zero errors and zero warnings for those three files; 17
  default-off KUnit cases are registered. Patch mode separately reports the
  deliberately absent synthetic-author sign-off and submission-readiness
  warnings, consistent with this experiment-only archive.
- The patch has zero production callers. The selected MT6797 CPU boot method
  still returns `-EAGAIN`, CPU disable still returns false, and no
  disable/die/kill operation or membership/P14/P15 hook was added.
- While this source-only work was in progress, the owner reported a boot2
  start followed by a Gemian reboot. This is recovery chronology only: this
  milestone created no build, package, candidate, write, or boot, so the
  report neither validates nor rejects it.
- The exact offline integration validator passed patch, source/configuration
  identity, documentation, oracle, and all 63 manifest-profile series checks.
- No kernel build, KUnit execution, runtime test, network access, or device
  action was performed.

## Analysis

The finite search establishes internal consistency for the modeled state
machine. In particular, it distinguishes per-operation opacity from a global
generation floor, makes `PUBLISHING` an indivisible winner state, and prevents
quarantine from either disappearing or bypassing P14/P15 retirement. It also
shows that a quarantined publisher can still complete publication and drain
the internally sampled online result.

The reviewed kernel change implements the same dormant C transition model and
has no production caller. The independent oracle does not inspect that source;
the exact patch hash and two static reviews bind the comparison. Its fixed
two-token universe and bounded actions are deliberate: they make every
reachable state enumerable, but they are not a proof over arbitrary kernel
concurrency, weak-memory executions, or production integration.

## Conclusion

Confirmed for the exact reviewed dormant C model and the independent Python
specification oracle: `PARTIAL_P30_PROTOCOL_MODEL`. The corrected bounded
contract is internally consistent and distinguishes all 17 modeled unsafe
mutations.

This result makes **no claim** that a P24 production owner exists, that kernel
hooks implement the model, that a kernel builds or runs, or that P30E has an
MMU-off proof. It does not authorize a package, boot candidate, deployment,
CPU_ON request, or device action.

## Follow-up

[The roadmap](../../docs/ROADMAP.md) alone owns ordered next steps. Production
code must be reviewed independently against this oracle before any build or
runtime claim can be made.
