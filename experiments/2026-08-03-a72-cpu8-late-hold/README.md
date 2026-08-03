# Experiment: Retain a late CPU8 execution sample

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-03-a72-cpu8-late-hold` |
| Status | `runtime-pass-repeatability-pending` |
| Subsystem | MT6797 CPU8 IPI/coherency and retained pstore evidence |
| Device variant | Gemini PDA x27, named project device |
| Date(s) | 2026-08-03 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | Roadmap Gate 7 stability follow-up |

## Question or hypothesis

Does CPU8 remain online and execute a third synchronous callback about ten
seconds after its already-proven completion, while CPU9 remains offline and the
existing fail-closed down barriers prevent the prior notifier fault?

## Provenance and environment

- Exact source: `59e00a9144d782e148332009a835b99c43382467`.
- Exact parent: the three-patch CPU8 held-online experiment.
- Build backend: Buildbox only; no native VM kernel build.
- Intended boot path: live-GPT-resolved non-primary `boot2` after all offline
  gates pass.

## Safety assessment

The child changes only the delayed sampler. It retains the exact startup path,
HPS floor, generic pre-notifier CPU8/9 down veto, CPU9 startup rejection,
CPU_OFF prohibition, fixed watchdog owner and deadline, and recovery path. The
third sample is one synchronous IPI and accounting check; it adds no load,
voltage, clock, hotplug, watchdog refresh, control interface, or CPU9 action.

The first sample remains at about +1 second, the second at about +6 seconds,
and the new terminal sample is at about +10 seconds. The parent runtime's
watchdog ended near 14 seconds after a completion near 1.932 seconds, leaving
about two seconds between the third sample and recovery.

## Associated code

- [`DESIGN.md`](DESIGN.md): timing, terminal record, and result decisions.
- [`scripts/source_edits.py`](scripts/source_edits.py): deterministic parent
  transformation.
- [`scripts/validate_patch.py`](scripts/validate_patch.py): source ordering,
  timing, inventory, and forbidden-action checks.
- [`scripts/test_static.py`](scripts/test_static.py): mutation rejection.
- [`scripts/generate-on-buildbox`](scripts/generate-on-buildbox): exact-parent
  patch generation on Buildbox.
- [`scripts/build-on-buildbox`](scripts/build-on-buildbox): exact child versus
  held-online parent compile review.
- [`patches/`](patches/): the one logical Buildbox-generated child patch.
- [`results/patch-generation-review-20260803.txt`](results/patch-generation-review-20260803.txt):
  two rejected validator revisions and the accepted source identity.
- [`results/compile-review-20260803.txt`](results/compile-review-20260803.txt):
  exact child/parent compile, diagnostics, disassembly, and stack decision.
- [`scripts/assemble.py`](scripts/assemble.py): source-pinned Android-v0
  assembler wrapper.
- [`scripts/build-candidate.sh`](scripts/build-candidate.sh): offline,
  reproducible candidate builder derived from the accepted parent.
- [`scripts/test_candidate.py`](scripts/test_candidate.py): independent header,
  manifest, ramdisk, padding, provenance, and offline-only checks.
- [`results/offline-container-review-20260803.txt`](results/offline-container-review-20260803.txt):
  exact candidate identity and independent acceptance record.
- [`scripts/install-boot2.sh`](scripts/install-boot2.sh): guarded exact-candidate
  boot2 installer with full readback and clean shutdown.
- [`scripts/capture-live-outcome.sh`](scripts/capture-live-outcome.sh): optional
  read-only direct USB/netcat terminal capture.
- [`scripts/test_runtime_tools.py`](scripts/test_runtime_tools.py): installer,
  collector, and decision-class contract checks.
- [`results/runtime-decision-map-20260803.txt`](results/runtime-decision-map-20260803.txt):
  pre-boot hypothesis, attributable evidence, and exact result actions.
- [`results/deployment-20260803.txt`](results/deployment-20260803.txt): verified
  live-GPT boot2 write, full readback, cleanup, and shutdown evidence.
- [`results/runtime-attempt-1-pass-20260803.txt`](results/runtime-attempt-1-pass-20260803.txt):
  changed-cycle late CPU8 execution/accounting pass and recovery evidence.

## Procedure

1. Apply the exact held-online parent patch series to the pinned source.
2. Generate one logical child patch that makes sample 2 nonterminal, schedules
   sample 3 four seconds later, and emits a versioned terminal only after the
   third successful synchronous CPU8 callback.
3. Reject timing, CPU identity, CPU9, hit-count, scheduling, watchdog, load,
   hotplug, and forbidden-action mutations.
4. Commit and push the clean source/tooling revision before Buildbox patch
   generation and compilation.
5. Compare the child and exact parent diagnostics, disassembly, and stack use.
6. Construct and independently validate an Android-v0 container before one
   guarded boot2 deployment and changed-cycle pstore capture.

## Observations

Buildbox applied the full exact parent and generated one 13-addition/8-removal
patch. Two earlier generation revisions stopped before publication: one had an
ambiguous mutation anchor, and the next exposed that loose token-order checks
did not reject a wrong callback CPU. The accepted validator requires the full
IPI/accounting predicate exactly once and rejects all seven unsafe mutations.

The exact clean patch commit then passed full child and held-online-parent
builds on Buildbox. Both have the same sole inherited 69-mismatch modpost
summary and 2,484 stack reports. Disassembly confirms CPU8, CPU8-online, CPU9-
offline, three-hit, and 5,000/4,000 ms branches. The workqueue frame grows from
64 to 80 bytes; the IPI callback and startup-completion frames are unchanged.
The accepted Buildbox kernel was then assembled three times in independent
ignored output roots. All candidate files were byte-identical. Independent
parsing confirmed the Android-v0 layout and addresses, complete extent,
preserved known-good ramdisk, recomputed legacy image ID, exact kernel field,
and zero-filled boot2 tail. No device action occurred during construction.

The guarded installer subsequently resolved logical boot2 as `/dev/mmcblk0p30`
while the known-good root was `/dev/mmcblk0p29`. It accepted the exact held-
online predecessor, wrote the late candidate, flushed it, matched both target
and independent full-partition readbacks, removed temporary copies, and left
the device confirmed powered off before runtime testing.

Runtime attempt 1 then returned through the fixed watchdog with a changed boot
ID. The retained console contains exactly one held-v2 terminal at 12.415481
seconds: sample 3 executed on CPU8, CPU8 was online, CPU9 was offline, and the
cumulative callback count was exactly three. No held fault, down veto,
predecessor terminal, notifier fault, panic, Internal error, or Call trace was
retained. Known-good Gemian returned, and boot2 remained exact.

## Analysis

The prior run did not retain its +1-second and +6-second measurements because
the 65,524-byte console tail began at 9.166 seconds. A new +10-second
synchronous callback is decision-changing evidence of a longer stable hold and
is expected inside that measured retention window. Reprinting an old result
without executing CPU8 again would not meet the experiment contract.

## Conclusion

`runtime-pass-repeatability-pending`: the exact parent, one logical patch,
timing, failure predicate, terminal, forbidden actions, mutations, full builds,
diagnostics, machine code, stack-use gate, exact offline container, guarded
installer, observation tools, runtime decision map, exact boot2 write/readback,
shutdown, late synchronous CPU8 execution/accounting, and watchdog recovery
pass. This is bounded experiment evidence, not default or upstream support.

## Follow-up

Perform one explicitly declared unchanged-artifact repeatability measurement
with a fresh changed-cycle capture. On a second exact pass, begin the separate
CPU9 experiment design; broader stability, CPU_OFF, load, DVFS, thermal, and
suspend gates remain closed.
