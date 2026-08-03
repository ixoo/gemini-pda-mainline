# Experiment: CPU9 cluster-reuse startup

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-03-a72-cpu9-cluster-reuse` |
| Status | `runtime-rejected-positive-cpu9-execution-evidence` |
| Subsystem | MT6797 CPU9 PSCI per-core startup with CPU8 retained |
| Device variant | Gemini PDA x27, named project device |
| Date(s) | 2026-08-03 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | Roadmap Gate 8 CPU9-specific entry |

## Question or hypothesis

After the exact repeatable CPU8 child has completed cluster-singleton
preparation, can the first natural HPS CPU9 request use only standard PSCI
`CPU_ON` for MPIDR `0x201`, complete generic secondary startup, and execute
three bounded synchronous callbacks on both CPU8 and CPU9 without replaying
the external rail, isolation, SRAM-LDO, DCM, or other cluster preparation?

## Provenance and environment

- Exact source: `59e00a9144d782e148332009a835b99c43382467`.
- Exact parent: the runtime-repeatable late CPU8 hold patch chain.
- Build backend: Buildbox only; no native VM kernel build.
- CPU9 stays disabled until source generation, mutation/static validation,
  exact-parent compilation, binary/stack review, container, deployment, and
  runtime-map gates independently pass.

## Safety assessment

The design preserves the fixed watchdog deadline, CPU8 one-way startup,
pre-isolation rollback, post-isolation retention, HPS/public CPU-down vetoes,
and CPU_OFF prohibition. CPU9 may be attempted once only after the CPU8
completion state proves CPU8 online, CPU9 offline, PSCI acceptance, verified
DCM enable, and cluster-online publication. CPU9 uses no Linux-side power or
clock write: secure firmware owns its per-core PSCI sequence.

Any CPU9 PSCI or completion failure retains CPU8 and cluster power, emits one
terminal, rejects retry, and waits for the already-owned watchdog. No inverse,
CPU_OFF, watchdog refresh, voltage/frequency change, synthetic load, or
userspace control is introduced.

## Associated code

- [`DESIGN.md`](DESIGN.md): exact entry, forward, failure, evidence, and result
  contracts.
- [`scripts/source_edits.py`](scripts/source_edits.py): deterministic
  late-parent transformation.
- [`scripts/validate_patch.py`](scripts/validate_patch.py): source ordering,
  inventory, and forbidden-action checks.
- [`scripts/test_static.py`](scripts/test_static.py): rejection mutations for
  CPU identity, parent state, PSCI-only ordering, pair sampling, and recovery.
- [`scripts/build-on-buildbox`](scripts/build-on-buildbox): exact late-parent
  versus CPU9-child compile, diagnostics, binary, disassembly, and stack gate.
- [`scripts/build-candidate.sh`](scripts/build-candidate.sh),
  [`scripts/assemble.py`](scripts/assemble.py), and
  [`scripts/test_candidate.py`](scripts/test_candidate.py): pinned offline
  Android-v0 construction and independent validation.
- [`scripts/install-boot2.sh`](scripts/install-boot2.sh),
  [`scripts/capture-live-outcome.sh`](scripts/capture-live-outcome.sh), and
  [`scripts/test_runtime_tools.py`](scripts/test_runtime_tools.py): guarded
  boot2 deployment, read-only netcat observation, and offline contract tests.
- [`patches/`](patches/): one Buildbox-generated logical CPU9 child patch.
- [`results/patch-generation-review-20260803.txt`](results/patch-generation-review-20260803.txt):
  exact identities, rejected validator revisions, and accepted source review.
- [`results/compile-review-20260803.txt`](results/compile-review-20260803.txt):
  exact child/parent compile, gate corrections, binary, and stack decision.
- [`results/offline-container-review-20260803.txt`](results/offline-container-review-20260803.txt):
  three-build reproduction, Android-v0 parse, padding, and candidate decision.
- [`results/runtime-decision-map-20260803.txt`](results/runtime-decision-map-20260803.txt):
  pre-boot hypothesis, exact success/failure classes, and deployment boundary.
- [`results/deployment-20260803.txt`](results/deployment-20260803.txt): exact
  predecessor, live target, full write/readback, cleanup, and shutdown result.
- [`results/runtime-attempt-1-rejected-20260803.txt`](results/runtime-attempt-1-rejected-20260803.txt):
  changed-cycle pair sample, HPS down pressure, recovery, and next boundary.

## Procedure

1. Apply the complete exact runtime-repeatable CPU8 parent patch chain.
2. Add a child-only Kconfig gate that leaves the parent unchanged when off.
3. Permit exactly one natural CPU9 request only after CPU8's verified cluster
   completion; call standard PSCI directly without cluster preparation.
4. Reconcile CPU9 generic secondary completion and then schedule bounded pair
   samples at about +1, +6, and +10 seconds.
5. Reject CPU9 retry, CPU8/9 down, CPU_OFF, cluster preparation replay, load,
   DVFS, thermal, suspend, and guessed inverse actions.
6. Generate one reviewable patch and compare a full child build with the exact
   late-CPU8 parent on Buildbox before any container or device action.

## Observations

The repeatable parent produced exact late CPU8 terminals at 12.415481 and
12.265514 seconds. Its retained windows also recorded 16 CPU9 requests per run
rejected before A72 action, providing a natural deterministic CPU9 trigger.
Offline ownership evidence assigns cluster-singleton preparation to the CPU8
transition and CPU9 per-core MTCMOS/reset/CCI work to secure PSCI firmware.

The first compile-gate run built both the CPU9 child and exact late-CPU8 parent,
then rejected publication because GCC inlined the private CPU9 boot helper and
the gate incorrectly required that helper as a standalone disassembly symbol.
No bundle was accepted. The corrected gate compares the durable HPS caller and
secondary-completion disassemblies. Review of that first accepted compile
bundle then tightened the durable anchors further to `cpu_psci_cpu_boot` and
`__cpu_up`, the exact compiled callers containing the two child changes.

## Analysis

CPU9 must not replay CPU8's DA921x, SPM isolation/reset, PWRAP, SRAM-LDO, or DCM
sequence. The smallest decision-changing child replaces the CPU9 rejection
with a one-shot, exact-prestate standard PSCI call and makes the retained late
terminal substantive by synchronously executing on both A72 CPUs.

## Conclusion

`runtime-rejected-positive-cpu9-execution-evidence`: the exact late parent, one logical child,
PSCI-only CPU9 path, pair sampler, forbidden actions, ordering, all 16
mutations, two full builds, identical diagnostics, durable-caller disassembly,
bounded stack review, and three independent exact Android-v0 constructions
pass. Runtime then proved CPU8 and CPU9 simultaneously online and executing two
synchronous pair rounds, but 83 HPS CPU9-down requests triggered the inherited
veto and the third sample lay beyond the fixed watchdog window. The declared
pass predicate therefore failed and this exact artifact must not be repeated.

## Follow-up

Design a child that preserves PSCI-only cluster reuse and CPU_OFF prohibition,
moves all three pair samples inside the fixed watchdog window, and reports the
repeated HPS CPU9-down pressure once without weakening the veto.
