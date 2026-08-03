# Experiment: CPU8/CPU9 multi-cacheline integrity

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-03-a72-cpu9-multiline-integrity` |
| Status | `design-review-pending` |
| Subsystem | MT6797 retained Cortex-A72 pair and cache coherency |
| Device variant | Gemini PDA x27, named project device |
| Date(s) | 2026-08-03 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | Roadmap Gate 8 CPU9 coherency/load |

## Question or hypothesis

After reproducing the exact 1,024-round scalar pair-v4 oracle, can retained
CPUs 8 and 9 alternately publish and verify deterministic payloads across a
16 KiB, 256-cacheline shared working set for 64 bounded rounds without a data
mismatch, callback error, lost watchdog recovery, or changed power boundary?

## Provenance and environment

- Exact parent experiment:
  `2026-08-03-a72-cpu9-bounded-coherency`.
- Exact parent repository compile commit:
  `938cdefde98522a2cd3504605aee04e4c83d5671`.
- Exact parent coherence patchset SHA-256:
  `d4c40577b9e91fedfde048b29cb203311de264c526c71e3abd907fc6fafcf67f`.
- Exact parent full boot2 SHA-256:
  `eda1d5bb312aa937e41499ea8fd13a5f8ae95865399605fe7cf93ee61daaa23d`.
- Parent runtime: two exact pair-v4 passes with 1,024/1,024 final sequences,
  zero coherence errors, complete HPS CPU9 `-EPERM` attribution, watchdog-class
  recovery, offline recovery CPUs 8/9, and unchanged boot2.
- Build backend: Buildbox only; no native VM kernel build.
- No source patch, compile, container, deployment, or runtime claim exists at
  this design stage.

## Safety assessment

The child may add only a second, finite CPU0-owned observation phase after the
unchanged scalar phase passes. It must not alter CPU startup, the scalar
callback, HPS veto or timing, CPU_OFF prohibition, regulator/clock/reset/MMIO
state, watchdog timing, pair sampling, userspace control, or recovery. Every
wait and data loop has a compile-time bound; the worker publishes a complete
terminal snapshot before the inherited watchdog restart.

## Associated code

- [`DESIGN.md`](DESIGN.md): exact working set, data oracle, synchronization,
  bounds, terminal, result classes, source invariants, and safety boundary.

## Conclusion

`design-review-pending`: the exact parent already proves repeatable scalar
shared-memory visibility. This child is intended to test a larger deterministic
working set without changing any power boundary. It is not yet implemented and
must pass source generation, mutation, Buildbox compile/binary/stack, container,
deployment, and runtime-map gates before device access.

## Follow-up

Review the design against the exact pair-v4 source. Then implement a
deterministic exact-parent transformer and mutation harness. Only a clean,
pushed source review may be submitted to Buildbox.
