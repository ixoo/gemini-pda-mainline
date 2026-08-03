# Experiment: CPU8/CPU9 parallel disjoint load

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-03-a72-cpu9-parallel-disjoint-load` |
| Status | `deployed-and-shutdown; first-runtime-pending` |
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
- No deployment, device action, or runtime claim exists yet.
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
- The compile bundle alone was not a boot candidate; the independently
  reproduced padded container below is the accepted exact candidate for
  guarded deployment. It has not yet produced runtime evidence.
- Two independent offline container roots produced byte-identical Android-v0
  images and exact 16 MiB padded images.
- Raw Android-v0 SHA-256:
  `6673d9ff6b9ff0a2bb4cf7a89815d73022208975dca713176c71a3b0865c7c51`.
- Full padded boot2 SHA-256:
  `0beead0b00485ad18333aca4d688fcd549c813113b7ec0554a6761c7147b17fb`.
- Independent validation pins all tool, parent, compile, kernel, ramdisk,
  header, layout, raw, padded, manifest, and offline-only identities.
- Before pair-v6 deployment, the owner selected the still-installed pair-v5
  boot2 and observed its automatic restart into Gemian. Live boot2 remained
  exact pair-v5 (`5227729e...`), so this cycle is excluded from pair-v6 runtime
  evidence. The unchanged recovery boot ID prevents treating the retained
  pair-v5 pstore terminal as a newly attributable repeat.
- Deployment tooling commit:
  `59e8d7bbc6effae49248554df6bfe23ea6cc1d81`.
- The guarded installer resolved live-GPT `boot2` as `/dev/mmcblk0p30`, proved
  it inactive and unmounted, and confirmed 100% battery with good health.
- Full predecessor SHA-256 matched exact pair-v5:
  `5227729e34ca42cf606f43008ec753fce15147693ce7a670818db58c5903fa48`.
- The write was synced and flushed; both target-side and independent streamed
  full-partition readbacks matched exact pair-v6:
  `0beead0b00485ad18333aca4d688fcd549c813113b7ec0554a6761c7147b17fb`.
- No fresh partition backup was made, temporary readback data was removed, and
  clean shutdown was confirmed by loss of reachability. There was no reboot.

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
- [`scripts/assemble.py`](scripts/assemble.py): source-pinned pair-v5 Android-v0
  contract with only the final pair-v6 kernel field substituted.
- [`scripts/build-candidate.sh`](scripts/build-candidate.sh): deterministic
  double assembly and independent 16 MiB padding constructor.
- [`scripts/test_candidate.py`](scripts/test_candidate.py): independent pinned
  offline candidate validator.
- [`results/offline-container-review-20260803.txt`](results/offline-container-review-20260803.txt):
  exact container identities, validation scope, and acceptance boundary.
- [`scripts/install-boot2.sh`](scripts/install-boot2.sh): source-pinned guarded
  installer for exact pair-v5 predecessor to pair-v6 candidate, full readback,
  and mandatory clean shutdown.
- [`scripts/capture-live-outcome.sh`](scripts/capture-live-outcome.sh): optional
  read-only USB/netcat complete pair-v6 terminal collector.
- [`scripts/test_runtime_tools.py`](scripts/test_runtime_tools.py): installer,
  collector, identity-mutation, and decision-map contract validator.
- [`results/runtime-decision-map-20260803.txt`](results/runtime-decision-map-20260803.txt):
  fixed pair-v6 deployment, recovery, pass, and reject branches.
- [`results/deployment-20260803.txt`](results/deployment-20260803.txt): exact
  live-GPT write, full-readback, no-backup, and shutdown evidence.

## Conclusion

`deployed-and-shutdown; first-runtime-pending`: source, mutation,
comparative compile, binary, configuration, diagnostics, stack, two-root
container reproducibility, and independent Android-v0 validation gates pass.
The pair-v6 installer and read-only collector are source-pinned to accepted
pair-v5 tools, the exact predecessor/candidate identities are mutation-tested,
and the runtime decision map is fixed. The exact pair-v6 candidate is installed
with full readback verification and the device is off. No pair-v6 runtime claim
exists yet.

## Follow-up

Arm changed-cycle pstore collection and physically select boot2 once under the
fixed decision map. Classify only a complete attributable pair-v6 terminal and
recovery cycle; screen color and restart alone are not evidence.
