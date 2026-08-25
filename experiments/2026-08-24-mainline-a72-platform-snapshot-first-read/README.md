# Experiment: A72 platform snapshot as the first physical read

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-24-mainline-a72-platform-snapshot-first-read` |
| Status | `planned` — source audit and generation contract defined |
| Subsystem | MT6797 A72 platform-state read-only snapshot |
| Device variant | Gemini PDA, named project device |
| Date | 2026-08-24 |
| Boot path | retained LK, owner-selected non-primary `boot2` |

## Question or hypothesis

Can the exact runtime-passed Stage-27 reader DT complete one stable A72
platform-state snapshot while preserving serviceability and keeping every
later reader, owner, and CPU action closed?

The predecessor runtime proved that the platform-state, clock, and BigiDVFS
backends all bind cumulatively without invoking a reader. The old full physical
observer is not a valid first-read discriminator: it performs platform,
DA921x-provider, and protected-clock reads before its first retained checkpoint.

## Audited read boundary

`mt6797_a72_platform_state_snapshot()` has one mutex-protected, fixed two-sample
transaction and no loop or retry. Each sample performs exactly:

- eight SPM syscon reads;
- one spinlock-protected TOPRGU PWRAP-reset status read;
- one MCUCFG MP2 DCM read; and
- CCI status, MP2 port-control, and CCI status reads.

That is 13 read-only register observations per sample and 26 total. A busy CCI
returns `-EBUSY`; movement between samples returns `-EAGAIN`; transport errors
propagate. No path writes a register or retries.

The new candidate-only observer will retain record 1 immediately before the
snapshot call, make that call exactly once, require `valid=1`, and retain
record 2 only after success. It clears the result on every error and logs one
terminal value/count receipt only after record 2. It references no DA921x
provider, clock backend, BigiDVFS backend, compositor, publisher, owner, or CPU
operation.

## Provenance

- Canonical parent: `patches/v7.1.3/0362-pstore-add-Gemini-A72-early-initcall-ledger.patch`.
- Managed source state:
  `15cb40c8149a9c02be4e2143e733ff81b06d82c3112aaa6e96255187cd3cb6d2`.
- Managed source integrity:
  `a42dfd12969eaca5e22e88580ad8be5a5cb9b69674fd41236eafe9004bed1c74`.
- Planned canonical changes:
  `0363` retained platform-snapshot ledger, `0364` one-shot observer,
  `0365` binding, and `0366` focused injected tests.
- Build backend: Buildbox only. Native VM compilation is prohibited unless
  the owner explicitly requests it.

The Buildbox generator pins the managed source markers and every edited parent
file, produces normal `git format-patch` output with a clearly synthetic,
non-certifying author and no synthetic sign-off, replays all four patches, and
runs source and strict style validation. Patch generation performs no build,
device access, retained-memory write, or hardware operation.

## Safety assessment

CPU8 and CPU9 remain closed by exact `maxcpus=8`. The observer performs only
the audited 26 reads plus at most two short retained-RAM records. It has no
storage access, register-data write, reset action, clock operation, protected
clock read, secure call, DA921x transaction, regulator action, publication,
owner mutation, CPU request, reboot, or power action.

The eventual candidate must preserve the exact passed Stage-27 DT and all three
bound backends, add only one observer node referencing the platform-state
source, reproduce byte-identically, pass LK/container mutations, and use the
guarded live-GPT `boot2` write/readback/shutdown workflow.

## Pre-boot decision map

| Unique result | Interpretation | Decision |
| --- | --- | --- |
| Exact live identity, Stage-27 serviceability, observer bound, complete value/count receipt | One stable platform snapshot completed | Qualify the values and isolate the next reader |
| Exact live identity with observer device unbound | The call returned a bounded error or the observer contract failed | Use the exact error/retained prefix; repair only that boundary |
| Changed-ID Gemian with only `before-platform` retained | Failure occurred inside the one snapshot or before its completion checkpoint | Split the fixed platform read sequence; do not retry unchanged |
| Changed-ID Gemian with both exact records | Snapshot returned and the later failure is outside the admitted read boundary | Repair only post-checkpoint serviceability/observation |
| Changed-ID Gemian with neither record | No snapshot is attributable | Add an earlier independent observer-entry boundary |
| Neither exact live mainline nor changed-ID Gemian | Observation incomplete | Diagnose transport/selection without assigning a kernel result |

Only one owner-selected attempt is allowed after every offline, Buildbox,
container, deployment, and pre-armed runtime gate passes.
