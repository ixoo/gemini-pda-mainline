# Experiment: CPU8/CPU9 scheduler-context execution

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-03-a72-scheduler-context` |
| Status | `design-review` |
| Subsystem | MT6797 retained Cortex-A72 pair and scheduler |
| Device variant | Gemini PDA x27, named project device |
| Date(s) | 2026-08-03 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | Roadmap Gate 8 scheduler-context execution |

## Question or hypothesis

After reproducing the exact pair-v6 startup and coherency/load gates, can one
normal-priority kernel thread bound to CPU8 and one bound to CPU9 both be
dispatched in task context, rendezvous concurrently, finish identical bounded
integer workloads on their assigned CPUs, and exit cleanly before the retained
watchdog recovery?

## Provenance and environment

- Exact parent experiment:
  `2026-08-03-a72-cpu9-parallel-disjoint-load`.
- Exact parent repository compile commit:
  `ad7807ccc50bebd0aaeafcbe4dadb4c11c44b850`.
- Exact parent parallel patchset SHA-256:
  `94d3b07355e1ddb67f3f643165570255bb1f42131b3b67c074d270e8581989e2`.
- Exact parent full boot2 SHA-256:
  `0beead0b00485ad18333aca4d688fcd549c813113b7ec0554a6761c7147b17fb`.
- Parent runtime: two complete pair-v6 passes with identical deterministic
  hashes, 128/128 rounds per CPU, 1,048,576 exact cross-CPU checks per cycle,
  safe changed-cycle watchdog recovery, offline recovery CPUs 8/9, and
  unchanged boot2.
- Kernel thread API reference: exact upstream Linux v7.1 `kernel/kthread.c`
  and `include/linux/kthread.h`.
- Build backend: Buildbox only; no native VM kernel build.
- No source patch, compile, container, deployment, or runtime claim exists yet.

## Safety assessment

The child may add only one finite task-context phase after every pair-v6 parent
predicate passes. It must not alter CPU startup, HPS veto/timing, CPU_OFF
prohibition, watchdog, power sequencing, clocks, reset, MMIO, regulator state,
sample timing, or recovery. It creates exactly two normal-priority kernel
threads, binds them before first wake to CPUs 8 and 9, bounds all internal waits
and work, stops both before publication, and treats incomplete cleanup as a
terminal fault. The retained watchdog remains the independent recovery bound.

## Associated code

- [`DESIGN.md`](DESIGN.md): exact lifecycle, workload, task-context oracle,
  bounds, terminal, result classes, and invariants.

## Procedure

1. Freeze the design and exact parent identities.
2. Generate one deterministic exact-parent source patch on Buildbox.
3. Reject lifecycle, affinity, bound, cleanup, parent-gate, and terminal
   mutations before compilation.
4. Compile child and exact parent on Buildbox and compare configuration,
   diagnostics, binary boundaries, and stack.
5. Reproduce and independently validate an Android-v0 boot2 container.
6. Commit and push exact deployment/runtime tooling before device access.
7. Install only through the guarded live-GPT boot2 helper, verify full readback,
   and shut down.
8. Run one attributable boot under a fixed decision map; repeat only if that map
   earns a decision-changing repeat.

## Observations

None. Design review only.

## Analysis

Pair-v6 proves bounded concurrent IPI callback execution and shared-memory
integrity. It does not prove that the scheduler can dispatch and cleanly retire
ordinary tasks on both retained A72 CPUs. This child changes only that execution
context while preserving the established power and recovery boundary.

## Conclusion

`design-review`: the question and safety boundary are specified but no source,
compile, or hardware evidence exists.

## Follow-up

Continue only through the ordered Gate 8 action in
[`docs/ROADMAP.md`](../../docs/ROADMAP.md).
