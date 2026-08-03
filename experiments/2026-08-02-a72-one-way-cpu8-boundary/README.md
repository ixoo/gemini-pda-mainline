# Experiment: A72 one-way CPU8 startup boundary

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-02-a72-one-way-cpu8-boundary` |
| Status | `cpu8-online-once-post-success-hps-down-crash` |
| Subsystem | MT6797 CPU8 external rail, isolation, SRAM-LDO, PSCI, and DCM |
| Device variant | Gemini PDA x27, named project device |
| Date(s) | 2026-08-02 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | Roadmap Gate 4 into Gate 7 |

## Question or hypothesis

Can one natural CPU8 request run the already-proven pre-isolation sequence,
cross the one-way external-isolation boundary, complete the retained-firmware
SRAM-LDO and PSCI path, and publish CPU8 online without ever guessing a Linux
inverse after isolation?

The design, deterministic source-generation, Buildbox compile/binary review,
container, deployment, and retained-runtime gates passed. CPU8 reached the
exact online checkpoint once. About 1.17 seconds later, an HPS CPU-down attempt
faulted in a pre-platform hotplug notifier and caused the observed restart.

## Provenance and environment

- Pinned public Gemian source: `59e00a9144d782e148332009a835b99c43382467`.
- Accepted predecessor: the exact 2026-08-02 pre-isolation rollback runtime.
- Working-path comparator: the immutable first natural Gemian CPU8 up/down
  capture from 2026-08-02.
- Build backend for any future implementation: Buildbox only.
- Future boot path: validated Android-v0 image on live-GPT-resolved `boot2`.

## Safety assessment

The owner audit rejects an isolation-clear-then-set experiment. The public
Linux path clears `CPU_EXT_BUCK_ISO[1:0]` but contains no inverse writer. The
natural down capture ends with the B isolation bit restored, but that write is
outside the instrumented Linux path and cannot be attributed to a Linux owner.

The only admissible design therefore has two failure domains:

- before isolation clear, unwind only the exact state owned by this attempt;
- at or after isolation clear, retain external power, never guess isolation or
  SRAM restoration, reject retry, preserve a durable terminal marker, and use
  the independently armed reset/recovery path.

CPU9, CPU disable, iDVFS, cpufreq/OPP changes, DCM before secondary completion,
and any user-triggered register interface are forbidden. The independent
recovery-only runtime has now passed, authorizing source generation and offline
review. It does not authorize deployment before those gates pass.

## Associated code

- [`DESIGN.md`](DESIGN.md): exact state machine and runtime evidence contract.
- [`scripts/one_way_model.py`](scripts/one_way_model.py): executable abstract
  state model; it performs no I/O or hardware action.
- [`scripts/test_one_way_model.py`](scripts/test_one_way_model.py): positive,
  rollback, fault-retain, CPU9, and mutation-boundary tests.
- [`results/isolation-owner-audit-20260802.txt`](results/isolation-owner-audit-20260802.txt):
  pinned source/runtime reconciliation and rejected inverse branch.
- [`results/design-validation-20260802.txt`](results/design-validation-20260802.txt):
  model identity, test result, and implementation decision.
- [`results/source-recovery-readiness-review-20260802.txt`](results/source-recovery-readiness-review-20260802.txt):
  exact insertion points, secondary-completion ownership, watchdog-kicker
  conflict, pstore boundary, and recovery-only prerequisite.
- [`results/post-recovery-source-generation-plan-20260802.txt`](results/post-recovery-source-generation-plan-20260802.txt):
  closes that prerequisite and fixes the exact five-patch source-generation,
  watchdog, SRAM-readback, secondary-completion, and forbidden-path plan.
- [`results/patch-generation-review-20260802.txt`](results/patch-generation-review-20260802.txt):
  records the rejected drafts, accepted three-patch identities, 19 mutation
  rejections, and manual source-control-flow review.
- [`patches/`](patches/): exact Buildbox-generated experiment-only source
  patches in deterministic order; their exact compiled candidate produced the
  runtime result below but remains unsuitable for unchanged repetition.
- [`results/buildbox-compile-binary-review-20260802.txt`](results/buildbox-compile-binary-review-20260802.txt):
  records changed-versus-parent compilation, exact configuration, machine-code
  ordering, symbol separation, diagnostics, and stack-usage review.
- [`scripts/build-candidate.sh`](scripts/build-candidate.sh): checksum-pinned,
  offline-only, twice-reproduced Android-v0 candidate construction.
- [`scripts/test_candidate.py`](scripts/test_candidate.py): static identity,
  provenance, reconstruction, padding, manifest, and offline-only gates.
- [`results/offline-container-review-20260802.txt`](results/offline-container-review-20260802.txt):
  exact raw/full-partition identities and independent structure review.
- [`results/runtime-decision-map-20260802.txt`](results/runtime-decision-map-20260802.txt):
  exact pre-boot hypothesis, attributable success/failure classes, recovery
  evidence, and guarded deployment boundary.
- [`scripts/install-boot2.sh`](scripts/install-boot2.sh): source-pinned guarded
  installer for only the exact candidate over the exact rollback predecessor.
- [`scripts/capture-live-outcome.sh`](scripts/capture-live-outcome.sh): optional
  read-only direct USB/netcat capture of an exact terminal marker before reset.
- [`results/owner-write-override-20260802.txt`](results/owner-write-override-20260802.txt):
  one-use owner approval for the exact live recovery predecessor and 65%
  battery floor while retaining every other deployment gate.
- [`results/deployment-20260802.txt`](results/deployment-20260802.txt): exact
  live-GPT write, two full readbacks, shutdown, changed-boot recovery, and
  unchanged-candidate evidence.
- [`results/runtime-attempt-1-cpu8-online-20260802.txt`](results/runtime-attempt-1-cpu8-online-20260802.txt):
  exact nine-stage startup, unique CPU8-online marker, and post-success HPS
  CPU-down notifier fault classification.

## Procedure

1. Pin and hash the public Linux forward/off paths and exact register names.
2. Reconcile every public Linux `0x10006290` writer with the owner-observer
   records and accepted runtime captures.
3. Reject any inverse without an observed owner and matching serialization.
4. Model the pre-isolation rollback and post-isolation fault-retain domains.
5. Require exact PSCI/affinity/secondary reconciliation before DCM or online.
6. Run the model tests locally. Do not build a kernel or access the device.

## Observations

The public Linux source has one A72 isolation write: it clears both external
buck-isolation bits during `cpu_power_on_buck()`. Its `cpu_power_off_buck()`
disables BUCKB and calls an ineffective SRAM disable wrapper; it never writes
the isolation register. The natural down capture later observes the offline
value restored, without an instrumented Linux mutation record for that write.

The first two generated drafts were rejected during review. The accepted third
generation separates a forward failure from a rollback failure, verifies the
watchdog's automatic-reset mode, rejects secure-read error sentinels, and pins
all configuration dependencies plus the CL2 source guard. Its static validator
passed 19 deliberate mutations.

The changed and exact parent kernels then compiled on Buildbox with identical
inherited diagnostics. Machine-code review confirmed CPU9 rejection, watchdog
takeover before the one-way path, isolation before SRAM verification, PSCI
after SRAM verification, and DCM only after generic secondary completion. Two
raw Android-v0 assemblies and two full-partition constructions were
byte-identical. The exact reviewed kernel is the sole payload change; all boot
fields and the known-good Gemian ramdisk are preserved.

The guarded deployment then passed from the exact recovery-only predecessor at
an owner-approved 67% battery state, including two matching full-partition
readbacks, cleanup, and shutdown. On the selected boot, retained ramoops
recorded all nine intended checkpoints and exactly one `cpu8-online-held`
terminal marker after secondary completion and DCM. The vendor logs immediately
reported cluster 2 on at 845 MHz. A later HPS CPU-down attempt faulted in
`cpuhvfs_notify_cluster_off` before the platform reject callback and caused the
automatic return to Gemian.

## Analysis

A reversible isolation-only candidate would invent a Linux-owned inverse and
would not match the successful owner sequence. A candidate that clears
isolation and waits for userspace would instead hold an intermediate state far
longer than the observed 240 microseconds. Both branches are rejected.

The smallest decision-changing implementation is one atomic, one-shot CPU8
startup transaction. It must proceed immediately from isolation clear through
the SRAM request and standard PSCI call, or enter terminal fault-retain and
reset recovery. This crosses more than one register boundary, but every stage
has an independent typed observation and a distinct terminal classification.

## Conclusion

`cpu8-online-checkpoint-confirmed`: the exact one-way implementation crossed
the reviewed boundary and published CPU8 online once without CPU9 or CPU_OFF.
This closes startup feasibility, not stable CPU8 support. The later failure is
now localized to HPS entering generic CPU-down notification before the
platform CPU-disable rejection can run.

## Follow-up

Pin the exact HPS/generic-hotplug call ordering and design the smallest early
CPU8-down veto that runs before notifier dispatch. Keep CPU8 online, retain
CPU9 and CPU_OFF rejection plus watchdog recovery, add a bounded
accounting/coherency observation window, and use Buildbox only. Do not repeat
the current candidate unchanged.
