# Experiment: CPU8/CPU9 parallel disjoint load

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-03-a72-cpu9-parallel-disjoint-load` |
| Status | `compile-review-pass; container-pending` |
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
- Buildbox reconstructed the exact pair-v5 parent, applied the deterministic
  child transformation, and produced one source patch changing only
  `arch/arm64/kernel/psci.c`.
- Source-review repository commit:
  `b980bb9a3fef35f32be717757ec4216061d5c8ca`.
- Exact generated parent commit:
  `f465d671ed82fd2a461c7a6b0f567452e70400d8`.
- Generated child commit:
  `0bbc78db4` (Buildbox detached source-review commit).
- Generated patch SHA-256:
  `17d222165657e6679df3b7be6e1c712a15ec979012755cdbc95ae087eeed48f4`.
- Pair-v5 validation: four pattern vectors and 16 negative mutations passed.
- Pair-v6 validation: four pattern vectors and 19 negative mutations passed.
- No container, deployment, device action, or runtime claim exists yet.
- Final Buildbox compile-review commit:
  `ad7807ccc50bebd0aaeafcbe4dadb4c11c44b850`.
- Child `Image.gz-dtb` SHA-256:
  `8bbbc62e997c7140f2648d5da2d825622ef19cb0eba94684218ab4d049a96e0a`.
- Exact pair-v5 parent `Image.gz-dtb` SHA-256:
  `c8dec67729bfceaaf1005e656e51e10950b787f07256f1daad1ce0cb64519814`.
- Child and parent configs are byte-identical; extracted diagnostics are
  byte-identical.
- Measured static stack: parallel callback 48 bytes, coherency worker 112
  bytes, complete terminal worker 784 bytes; the working set is not on stack.
- This is still compile-review evidence, not a boot candidate or runtime claim.

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
- [`scripts/source_edits.py`](scripts/source_edits.py): exact-parent source
  transformation.
- [`scripts/test_static.py`](scripts/test_static.py): positive source contract,
  independent payload vectors, safety inventory, and negative mutations.
- [`scripts/generate-on-buildbox`](scripts/generate-on-buildbox): clean-pushed-
  commit Buildbox patch generation with exact parent provenance.
- [`scripts/build-on-buildbox`](scripts/build-on-buildbox): pair-v6 versus exact
  pair-v5 comparative compile entry point.
- [`patches/series`](patches/series): exact generated source-review patch order.
- [`results/compile-review-20260803.txt`](results/compile-review-20260803.txt):
  exact hashes, linked binary boundaries, stack measurements, and tooling
  chronology for the final comparative Buildbox pass.

## Conclusion

`compile-review-pass; container-pending`: the exact pair-v6 source and negative
mutations pass, both pair-v6 and exact pair-v5 compile under identical pinned
inputs, and the binary/configuration/diagnostic/stack gates pass. The child is
not deployable until two independent Android-v0 container constructions agree
byte-for-byte and an offline candidate validator binds every identity.

## Follow-up

Construct the pair-v6 Android-v0 container twice from the final validated
`Image.gz-dtb` and the pinned active pair-v5 ramdisk/header contract. Require
byte-identical raw and padded outputs plus an independent offline validator
before any `boot2` write.
