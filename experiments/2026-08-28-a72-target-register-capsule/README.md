# Experiment: CPU8/CPU9 target-register capsule

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-28-a72-target-register-capsule` |
| Status | `validated-definition` |
| Subsystem | MT6797 retained Cortex-A72 pair and arm64 ID-register evidence |
| Device variant | Gemini PDA x27, named project device |
| Date(s) | 2026-08-28 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | Roadmap Gate 7 READY runtime-evidence closure |

## Question or hypothesis

After the exact repeatable scheduler-context parent passes every existing
startup, coherency, workload, placement, completion, and cleanup predicate, can
one bounded task on CPU8 and one on CPU9 each publish a complete immutable
architectural-register capsule that agrees with the target's existing
per-CPU `cpu_data` record?

## Provenance and environment

- Exact parent experiment:
  [`2026-08-03-a72-scheduler-context`](../2026-08-03-a72-scheduler-context/README.md).
- Exact parent Gemian source commit:
  `59e00a9144d782e148332009a835b99c43382467`.
- Exact parent scheduler patchset SHA-256:
  `bd5799cecd14aa34a87562b09507a6d9f18f11cd138420bcba629f12793e7bfe`.
- Exact reconstructed parent `arch/arm64/kernel/psci.c` SHA-256:
  `a09af27d80e502a7c62e365f271ed74f6f09212935882e242d4d0f432ec29f34`.
- Parent runtime: two attributable cycles with adjacent exact pair-v6/pair-v7
  PASS terminals, bounded scheduler-context work on CPU8 and CPU9, clean task
  retirement, watchdog recovery, and unchanged boot2.
- Build backend: Buildbox only. No native VM kernel build is permitted.

## Safety assessment

The child changes only the two already-bound scheduler tasks after the complete
pair-v6 parent gate. Each task disables preemption briefly, reads a fixed list
of read-only architectural identification/cache/timer registers, compares the
overlapping values with its already-populated `cpu_data`, publishes one static
capsule, and resumes the unchanged parent rendezvous and workload.

It adds no CPU_ON, CPU_OFF, PSCI, SMC/HVC, MMIO, regulator, clock, reset,
watchdog, affinity, scheduling-policy, retry, storage, or reboot action. It
does not read arbitrary newer system-register encodings. The fixed list is the
register inventory already read by the exact 3.18 `cpuinfo_store_cpu()` path,
plus MPIDR, REVIDR, CLIDR, and ID_AA64DFR0; the latter DFR0 access is already
used by the same kernel's debug/perf paths. Existing watchdog recovery and the
CPU_OFF prohibition remain byte-identical.

No candidate may be built until deterministic transformation, exact-parent
reversal, field serialization, output schema, forbidden-action inventory, and
negative mutations pass. A future physical boot must use one new candidate and
one fixed decision map; the proven parent must not be rerun unchanged.

## Associated code

- [`DESIGN.md`](DESIGN.md): exact capture, publication, result, and decision
  contract.
- [`scripts/capsule_edits.py`](scripts/capsule_edits.py): deterministic
  one-file transformation of the exact scheduler parent.
- [`scripts/test_capsule_child.py`](scripts/test_capsule_child.py): exact-parent
  reversal, semantic inventory, output-schema, and negative-mutation tests.
- [`scripts/generate-on-buildbox`](scripts/generate-on-buildbox): reconstructs
  the exact parent from public Git inputs and emits only the child patch.
- [`results/definition-validation-20260828.txt`](results/definition-validation-20260828.txt):
  local syntax, ShellCheck, serialization, exact-reversal, and mutation result.

## Procedure

1. Freeze the exact parent source, patchset, `psci.c`, and runtime evidence.
2. Validate the deterministic editor and negative mutations locally.
3. Commit and push the clean definition, then generate the one-file child patch
   from that exact commit on Buildbox.
4. Fetch, review, admit, and pin the generated patch and patchset identities.
5. Extend the existing Buildbox compile review so the exact unpark parent is
   the binary comparison and capture symbols/reads/output/stack are inspected.
6. Define deterministic container, guarded boot2 deployment, and one-attempt
   runtime classification before any device write.

## Observations

- The exact 3.18 `cpuinfo_store_cpu()` path already runs on every secondary and
  stores CNTFRQ, CTR, DCZID, MIDR, six AArch64 ID registers, and twelve
  AArch32 ID registers in per-CPU `cpu_data`.
- The same source already reads ID_AA64DFR0 in debug, hardware-breakpoint,
  perf, and KVM code. MPIDR, REVIDR, and CLIDR are architected read-only
  identity/cache registers on the target architecture.
- The accepted scheduler child runs one normal-priority bound task on each A72
  only after the complete pair-v6 parent predicate. Its result storage is
  static and zeroed before the one run.
- Ordinary Gemian's passive hotplug state does not naturally retain CPU8/CPU9;
  the already-proven experiment-only parent is the available bounded execution
  source. A same-day 12-second passive sample therefore supplied no substitute
  target evidence.

The deterministic editor and validator now pass Python syntax, one positive
definition case, exact field inventories, and twelve unsafe mutations. Both
shell files pass `bash -n` and ShellCheck, and the Buildbox command is exposed
by the local help path. No source generation, build, candidate, deployment, or
new runtime result has occurred yet. See
[`results/definition-validation-20260828.txt`](results/definition-validation-20260828.txt).

## Analysis

Copying `cpu_data` alone would rely on source attribution for target locality.
Reading the same safe inventory from within each bound task and comparing it
field-by-field with that CPU's prior record provides two independent paths:
the current task placement oracle and the secondary-startup record. The capsule
hash serializes named fields rather than structure bytes, so padding and host
layout cannot affect its identity.

This capsule is target evidence, not a mainline policy decision. It deliberately
does not claim system capability state, GIC/hyp usability, SMCCC mitigation
policy, ASID/page/VA configuration, capability commitment, READY, production
scheduling, CPU_OFF, or sustained load. Those fields must be derived and
validated by the mainline architecture owner after the raw target record is
captured.

## Conclusion

`validated-definition`: the smallest target-local capture child and its
deterministic Buildbox generator are frozen. Local validation preserves the
repeatable parent's power and recovery behavior and admits only the bounded
read-only register capsule. No compile or hardware claim exists yet.

## Follow-up

Continue only through the ordered action in
[`docs/ROADMAP.md`](../../docs/ROADMAP.md): generate and validate the exact child
patch on Buildbox, then perform the Buildbox-only binary review before defining
a physical candidate.
