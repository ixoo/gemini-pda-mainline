# Firmware-owner lease design

## Boundary

The existing Linux lease in patch `0174` serializes the handoff object and
holds its generation/cookie across one MT65xx I2C6 transfer. It does not prove
the vendor firmware pause source. Patch `0175` therefore adds a second,
private lease whose only authority is a registered external owner.

The current mainline handoff is not that owner: it maps only CSPM, validates a
stopped receiver, and has no CSRAM mapping, PCM image residency, firmware
request, or reset/IM/PCM kick sequence. A future owner must first establish
those start/resource facts, or explicitly identify a trusted firmware service
that has already started and owns the PCM. A direct `SW_PAUSE`/`FW_DONE`
implementation without that prerequisite is rejected.

## Startup-state adapter seam

The PCM owner has two distinct authorities: the image/receiver owner and the
Linux startup-state owner. The latter cannot be inferred from the firmware
lease token. The public start path needs a coherent snapshot of the current
cluster and rail state before it writes CSRAM records or requests PCM run.

The reviewed adapter seam is conceptual, not yet a kernel API:

1. `snapshot`: under the CPU/rail transition lock, return the current cluster
   membership, `is_on` state, OPP identity, frequency, voltage, VSRAM,
   ceiling/floor, clock state, rail state, and a monotonically identified state
   generation.
2. `validate`: immediately before image start and again immediately before
   `PCM_KICK`, prove that the snapshot generation and all state fields still
   match the live owners. A mismatch aborts the start and invalidates the
   pending image generation.
3. `publish`: copy only the validated snapshot into the initial CSRAM/control
   records, with the image and state generations bound together. No guessed
   OPP or voltage may be substituted for a missing field.
4. `invalidate`: on a regulator/clock transition, suspend/resume, PCM fault,
   or owner removal, revoke the bound generation and prevent a stale callback
   from reaching the firmware lease.

The intended lifecycle is `UNAVAILABLE -> SNAPSHOTTED -> RESOURCES_HELD ->
IMAGE_READY -> RUNNING`, with every failure or asynchronous transition entering
`INVALIDATED`/`FAULTED`. The current tree has no provider that can implement
`snapshot`; the existing handoff remains a stopped-state observer. This seam
must be satisfied before adding a loader, mapping CSRAM, or registering the
callback in patch `0175`.

## State-owner selection

The existing MT6797 A72 observer is not a state owner: it only reads the
external Vproc snapshot and deliberately denies `CPU_ON`. The reusable clock
backend research identifies the actual missing owner pieces as an MT6797
CPU-PLL/mux/divider provider, the MCUMIXED/DVFSP semaphore boundary, and a
separate secure BigiDVFS backend for the A72 cluster. Generic MediaTek CCF
math and the generic OPP framework are reusable components, not ownership of
those protected transitions. Direct CPU-PLL MMIO is unsafe, and the vendor
EEM/PTP path makes a static downstream OPP table non-authoritative.

The next implementation seam is consequently a disabled, read-only MT6797
clock/state contract that proves the cross-owner read path. Patch `0192`
defines that dormant boundary as a private state-owner registry: `snapshot`
must return every requested cluster's flags, OPP, frequency, voltage, VSRAM,
ceiling, floor, clock state, rail state, and nonzero generation; `validate`
must re-check that generation under the owner's transition lock; and
`invalidate` covers owner removal, clock/rail transitions, suspend/resume, and
PCM faults. The registry holds its lock across callbacks, rejects incomplete
snapshots, and returns `-EOPNOTSUPP` while no owner is registered. It performs
no MMIO or transition itself. Only after a real clock/rail owner is registered
and independently reviewed can it become the live state owner used by the PCM
adapter; no voltage or frequency transition is implied by this design.

```text
Linux transfer lease {generation,cookie}
        |
        +-- firmware acquire request (SEMA_I2C_DRV contract)
        |      pause source 0x2; SW_PAUSE bit 13; FW_DONE bit 15; 2 ms bound
        |
        +-- physical I2C6 transaction (future caller; not added here)
        |
        +-- firmware release request with the same owner handle
```

The callback registry is empty by default. Both operations are mandatory,
registration is single-owner, and unregister returns `-EBUSY` while a firmware
lease is held. The registry mutex stays held while the callback runs so its
context cannot disappear; a callback must not recursively register or
unregister itself.

## Acquire response

The owner must return:

- ABI and user identity unchanged;
- `status == 0`, `returned == 1`, and the exact Linux generation/cookie;
- a nonzero opaque `owner_handle`;
- pause-source map `0x2`;
- all three `SW_PAUSE` words asserted; and
- all three `FW_DONE` words asserted.

Only this response creates the stored firmware lease. A missing owner or a
fully structured refusal returns `-EOPNOTSUPP` before any lease is held.

## Release response

Release carries the exact Linux token and stored owner handle. A successful
response must echo the identity and handle, report `status == 0`, clear the
pause-source map, and clear all three `SW_PAUSE` words. The `FW_DONE` words are
an acquire acknowledgement and are not used as a post-release ownership claim.

Any release refusal, callback error, stale handle, malformed response, or
state/token change faults the handoff and retains the firmware lease. No
automatic inverse or retry is allowed.

## Review boundary

This contract names the vendor protocol but does not prove that the current
one-way receiver implements it. A future callback owner must identify its
firmware domain, prove callback lifetime and concurrent writers, and provide
independent evidence for the three pause/acknowledgement words. Until that
proof exists, the provider cannot perform page selection or register-data
writes.
