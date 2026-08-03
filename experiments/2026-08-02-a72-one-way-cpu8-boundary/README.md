# Experiment: A72 one-way CPU8 startup boundary

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-02-a72-one-way-cpu8-boundary` |
| Status | `implementation-unblocked` |
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

This is a design question only. No kernel was built and no device action ran.

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

`confirmed-design-boundary-implementation-unblocked`: there is no
evidence-backed Linux inverse for external isolation. The next safe
implementation may attempt CPU8 once only
with pre-isolation rollback and post-isolation fault-retain; it must not add an
isolation-only rollback or a CPU8 off path. Source review additionally proves
that the normal watchdog kicker defeats an assumed independent timeout and
that generic SMP owns secondary completion. The no-A72 recovery-only
discriminator has now proved watchdog ownership, durable ramoops attribution,
reset, and known-good recovery on hardware.

## Follow-up

Generate the one-way CPU8 source patches, validate them against the model and
mutation boundaries, and compile changed-versus-unpatched kernels on Buildbox.
Do not deploy until the exact binary ordering, stack, container, and guarded
runtime decision-map reviews pass.
