# Experiment: CPU8/CPU9 parallel disjoint load

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-03-a72-cpu9-parallel-disjoint-load` |
| Status | `design-review-pending` |
| Subsystem | MT6797 retained Cortex-A72 pair and cache coherency |
| Device variant | Gemini PDA x27, named project device |
| Date(s) | 2026-08-03 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | Roadmap Gate 8 CPU9 coherency/load |

## Question or hypothesis

After reproducing the exact pair-v5 scalar and alternating multi-cacheline
gates, can retained CPUs 8 and 9 concurrently write disjoint halves of a 64 KiB
shared working set, rendezvous through finite barriers, and verify every word
written by the peer for 128 rounds without mismatch, callback error, lost
watchdog recovery, or changed power boundary?

## Provenance and environment

- Exact parent experiment:
  `2026-08-03-a72-cpu9-multiline-integrity`.
- Exact parent repository compile commit:
  `fb647817cd573e3dd8719821da8742bc5433979b`.
- Exact parent multiline patchset SHA-256:
  `c7a9b020563c4abb74059bbf72705839c528a81d577c7031ddfb36de647fd896`.
- Exact parent full boot2 SHA-256:
  `5227729e34ca42cf606f43008ec753fce15147693ce7a670818db58c5903fa48`.
- Parent runtime: two exact pair-v5 passes with identical deterministic hashes,
  64/64 rounds, 262,144 exact cross-CPU word checks per cycle, zero errors or
  mismatches, complete HPS/scalar attribution, watchdog-class recovery, offline
  recovery CPUs 8/9, and unchanged boot2.
- Build backend: Buildbox only; no native VM kernel build.
- No source patch, compile, container, deployment, or runtime claim exists at
  this design stage.

## Safety assessment

The child may add only one finite CPU0-owned observation phase after the exact
pair-v5 parent phases pass. It must not alter CPU startup, inherited scalar or
alternating callbacks, HPS veto/timing, CPU_OFF prohibition, regulator/clock/
reset/MMIO state, watchdog timing, pair sampling, userspace control, or recovery.
Every rendezvous and data loop has a compile-time bound; the working set is
static BSS and no payload is placed on the callback stack.

## Associated code

- [`DESIGN.md`](DESIGN.md): exact working set, concurrency oracle, barriers,
  bounds, terminal, result classes, and safety boundary.

## Conclusion

`design-review-pending`: pair-v5 proves repeatable alternating data integrity,
but not concurrent writers. This child isolates parallel disjoint ownership as
the next decision-changing observation. It must pass source generation,
mutation, Buildbox compile/binary/stack, container, deployment, and runtime-map
gates before device access.

## Follow-up

Review the design against the exact pair-v5 source, then implement a
deterministic exact-parent transformer and mutation harness. Only a clean,
pushed source review may be submitted to Buildbox.
