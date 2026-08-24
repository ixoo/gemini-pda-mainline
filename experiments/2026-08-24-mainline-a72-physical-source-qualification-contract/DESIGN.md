# A72 staged physical-source qualification design

## Phase A: read-only DA921x snapshot separation

The first source slice is hardware-free. Its generated kernel delta may edit
only the DA921x provider implementation and private contract header, its
Kconfig/test wiring, and focused in-memory tests. Normal repository experiment
files, profile configuration, manifest selection, and Buildbox tooling remain
subject to the repository workflow.

It must make the following fixed machinery available whenever
`ARM64_MT6797_A72_PROVIDER_OWNER` is selected, independently of
`REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION`:

- the five-register order `0x56`, `0x51`, `0x5e`, `0xd9`, `0xda`;
- a read-only two-message raw transfer helper;
- a provider endpoint containing adapter, address, read transport, and mutex;
- two complete immediate samples under endpoint and root-adapter locks with
  adapter retries temporarily zero;
- exact equality of both five-byte samples;
- one complete `mt6797_a72_provider_snapshot`; and
- `.snapshot = da9213_provider_snapshot` in the registered provider ops.

The real endpoint uses only `__i2c_transfer`; it must not expose a delay or
write callback. Positive acquire/release code and writer helpers remain under
their existing positive Kconfig guard. With that guard off, acquire and
release retain their current `-EOPNOTSUPP` responses before any I2C operation.

Every snapshot error leaves the public output all-zero. Registration remains
device-managed through `devm_add_action_or_reset()`, and unregister clears the
exact provider pair before endpoint storage is released.

### Phase-A proof

Focused in-memory tests must cover:

1. two exact matching five-register samples accepted;
2. every negative and short transfer at all ten read ordinals;
3. every second-sample byte mismatch returning `-EAGAIN`;
4. output all-zero on every failure;
5. one endpoint mutex and one root-adapter lock across both samples;
6. retries changed to zero and restored on every exit;
7. missing, duplicate, and exact unregister registry behavior;
8. acquire/release still returning `-EOPNOTSUPP` with zero transfers;
9. positive-provider config off, writer-transaction-window config off, and no
   Buck-B writer symbol in the linked image; and
10. no direct-source registration, A34, P30, provider action, CPU operation,
    MMIO, SMC, physical I2C, DT enablement, or device access.

Generate logical core and test patches only on Buildbox from a clean pushed
commit. After canonical admission, build one isolated no-modules profile on
Buildbox. The phase is compile/KUnit evidence only and cannot create a boot
candidate.

## Phase B: staged candidate-only physical observer

Phase B remains design-only until Phase A passes. It adds a new default-off
diagnostic mode and a candidate-only DT, not a production publisher.

### Device lifetime

The observer probe resolves phandles for the platform-state, clock, and
BigiDVFS devices. It must obtain and retain a reference to each bound device
before registering the direct-source callback. The DA921x source remains
owned by the separate provider registry.

After one public direct snapshot returns, the observer unregisters the exact
direct callback/context, then releases the three device references in reverse
order. Every deferral or error before registration releases all acquired
references. The direct registry mutex remains held through the callback, so
unregister cannot race the snapshot.

### Exact lock and reader order

```text
cpu_hotplug_lock (read)
  -> a72_transition_lock
    -> direct-source registry mutex
      -> platform-state source mutex; release
      -> provider registry -> endpoint -> root-adapter; release
      -> clock operation -> handoff/clock/IRQ/semaphore; release
      -> retained record 1: before-bigidvfs
      -> BigiDVFS operation mutex, exactly one two-sample call; release
      -> retained record 2: after-bigidvfs
    -> final pristine-owner recheck
```

The callback clears its destination first. It sets source ABI and `valid=1`
only after record 2 and every component result succeeds. The outer compositor
then publishes the complete direct-state result only after its final owner
check. Any error leaves both callback and public destinations all-zero.

### Retained attribution

The future implementation owns a new token `GPSQ-20260824-A` and only slots 1
and 2 in the existing ramoops reservation:

- slot 1: `checkpoint=before-bigidvfs`;
- slot 2: `checkpoint=after-bigidvfs`.

Both commits use the already qualified payload, start, size, signature-last,
barrier, full-readback, no-overwrite, no-clear, and no-retry protocol. The
guarded installer must require both headers exact-empty before a write. The
runtime may make at most two short retained-RAM writes and exactly one
BigiDVFS backend call, which contains eight read-only SMC invocations as two
complete four-word samples.

### Runtime oracle

A live success must contain exactly one complete record for:

- direct ABI 2 target identity, topology, and pristine owner;
- DA921x ABI 1 and all five raw bytes;
- every platform-state field and `valid=1`;
- protected-clock ABI 2, generation 1, and all 18 raw words;
- BigiDVFS ABI 1, generation 1, and all four raw words;
- one source registration, one callback, one unregister;
- one clock call, one BigiDVFS call, zero compositor retry;
- no provider acquire/release, register-data write, A34 evaluation, P30
  claim, publisher call, owner mutation, CPU request, or block mount; and
- CPU0--7, CPU8/9 offline, I2C6/DA921x, keyboard, USB, console, and native
  recovery serviceability.

Changed-ID Gemian recovery must independently classify the two exact retained
records and verify inactive `boot2` still matches the installed candidate.
The candidate is rejected on any missing, duplicate, malformed, or
contradictory evidence.

### Why the clock call is not an unchanged repetition

The prior qualified clock call ran from a clock-only observer. Phase B asks a
different question: can the same transport complete after platform and
DA921x capture while the CPU-hotplug and A72 transition owners remain held,
and immediately before the first BigiDVFS sample in one all-or-zero direct
record? The one clock call is necessary input to that combined record and adds
an independent owner/ordering observation. A second Phase-B attempt is not
allowed unless new evidence changes the hypothesis.

## Explicit exclusions

Neither phase may add a replay producer, production publisher caller, A34
vector change, lifecycle publication, diagnostic-blocker clear, P30 claim,
provider acquire/release, Buck-B write, CPU-veto change, CPU_ON, CPU_OFF, or
CPU8/CPU9 request. Phase A additionally forbids a build candidate, device
access, DT enablement, and every physical hardware operation.
