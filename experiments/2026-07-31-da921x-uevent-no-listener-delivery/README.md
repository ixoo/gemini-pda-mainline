# DA921x uevent no-listener delivery

| Field | Value |
| --- | --- |
| ID | `2026-07-31-da921x-uevent-no-listener-delivery` |
| Status | `first selected boot passed stage 20` |
| Subsystem | I2C, OF, kobject uevent, netlink |
| Device variant | Named Gemini PDA development unit |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 3 transport boundary |

## Question or hypothesis

Can the runtime-proven zero-listener event exercise the normal untagged uevent
delivery loop and return zero with no skb allocation or broadcast, while
preserving the exact stage-19 serviceability and zero-hardware baseline?

The predecessor observed one socket and zero group-1 listeners. This candidate
reuses the normal untagged loop with bounded observation enabled. It fails
closed before allocation or `netlink_broadcast()` if any listener appears and
advances to stage 20 only after the loop returns zero with the same socket
count, zero listeners, zero allocations, and zero broadcasts.

## Decision

- Exact stage 20, `sockets=1`, `listeners=0`, `allocations=0`,
  `broadcasts=0`, `retval=0`, and the unchanged baseline prove the controlled
  no-listener result serviceable. The next split may add a deliberately bounded
  listener before testing multicast delivery.
- A changed listener count fails closed before allocation or broadcast and
  rejects this candidate as a no-listener measurement.
- A serviceable stage-19 result rejects execution of the new result path.
- A visual/reboot cycle without exact candidate identity or attributable crash
  evidence is inconclusive under the owner's retrospective evidence caution.
- Any changed event, client, CPU, handoff, or I2C baseline rejects attribution.

## Safety and build policy

The experiment never permits `netlink_broadcast()` when a listener exists.
With the runtime-proven zero-listener topology, it enters the normal loop,
skips the sole socket, consumes no new skb, and returns zero. The matching
DA921x driver remains module-only and absent from the initramfs; the real client
remains unbound. The patch adds no driver, provider, I2C transfer, register
access, printk, device-storage path, listener, or event delivery.

Build only through `./scripts/build-kernel --backend buildbox` from an exact
clean pushed commit. Do not run a native VM kernel build unless the owner
explicitly requests one. The experiment patch uses the actual author identity,
carries no synthetic sign-off, and is not submission-ready.

## Input validation

All 130 patches apply to the pinned Linux 7.1.3 source. The named profile
resolves the complete stage-19 predecessor plus only the new no-listener gate
and release `7.1.3-gemini-da921x-nodeliv`. All 47 manifest profiles pass the
canonical-order invariant and all eight focused invariant mutations are
rejected.

The merged configuration retains both listener discovery and no-listener
delivery gates. Strict checkpatch has no warnings or checks after excluding the
intentionally absent experiment-only DCO. Host and VM free-space checks passed
with 93 GiB and 83 GiB available. Exact identities are recorded in
`results/input-validation.txt`. No native VM kernel build was run and the
device was not accessed for this experiment.

## Offline candidate validation

Buildbox produced the exact clean `arm64` package from repository commit
`42875efb2dc1cd21f2304834f5d989771ce68197`. Independent managed-VM
validation passed its complete checksum and provenance bundle, including all
119 DTBs. The selected package has release
`7.1.3-gemini-da921x-nodeliv`; both transport observation gates are built in,
the matching driver remains module-only, and the retained lifecycle initramfs
contains neither modules nor `modprobe`.

Two independent managed-VM assemblies were byte-identical. The retained
6,862,848-byte LK container passed all 32 analyzer gates and was padded to the
exact 16,777,216-byte boot2 size. Only the selected candidate was exported;
the duplicate assembly was removed after comparison. Exact package, container,
manifest, assembler, and guarded-installer identities are recorded in
`results/offline-validation.txt`. No native VM kernel build or device access
was used for this validation.

## Deployment

The proven stage-19 runtime was identity-gated by release and boot ID over its
USB netcat console, then requested its native reboot without storage access.
Known-good Gemian returned as `3.18.41+` with changed boot ID
`16145818-6558-416e-b783-f261bc7faabb`.

The guarded installer resolved live GPT label `boot2` to `/dev/mmcblk0p30`
while root was `/dev/mmcblk0p29`. External power was present, capacity was
100%, health was Good, and the full predecessor checksum matched the proven
stage-19 candidate. No new backup was created. The exact padded no-listener
candidate was written, synced, flushed, and verified by matching full-partition
readback; the temporary readback was removed and clean shutdown was confirmed.
Sanitized deployment evidence is recorded in `results/deployment.txt`.

## Frozen runtime plan

The first selected boot must identify release
`7.1.3-gemini-da921x-nodeliv`, validation state `validated`, and stage 20.
The read-only verifier requires the predecessor listener observation and new
delivery observation both to report exactly one socket and zero listeners. The
new path must additionally report zero allocations, zero broadcasts, and
return value zero. The established event envelope, classification, real
unbound OF client, CPU set, ready I2C6 handoff, zero I2C/oracle activity, and
USB/netcat serviceability must remain unchanged.

A pass proves the normal no-listener loop returned without allocating or
broadcasting. A changed listener topology rejects the measurement because the
candidate must fail closed before those operations. Stage 19 rejects execution
of the new result path. A visual/reboot cycle without exact identity, stage, or
attributable reset evidence is inconclusive. Exact identities and the complete
result-to-action map are frozen in `results/runtime-plan.txt` before the boot.

## Runtime result

The first selected boot matched release `7.1.3-gemini-da921x-nodeliv`, full
installed boot2 checksum
`bf4b379696cf2a93806d969ffaa90d8652ab092f8643e0539d694ca7971f77e0`,
USB identity and route, and boot ID
`148bcdb3-325e-489f-85cd-939d955b0218`. The BusyBox-compatible checker
reported state `validated` and final stage 20.

Both observations reported one socket and zero group-1 listeners. The new
delivery observation additionally reported zero skb allocations, zero
broadcasts, and return value zero. This proves the exact event exercised the
normal no-listener loop and returned successfully without allocation or
multicast delivery on this initramfs boot.

The nine-entry envelope and classification were unchanged. The real `1-0068`
OF client remained unbound; CPUs 0--7, USB/netcat, and I2C6 handoff
serviceability passed while every I2C and lifecycle oracle remained zero. The
collector removed its temporary `/run` verifier and performed no partition
read, storage write, or reboot. The initial host-side attempt ended before a
device connection because macOS had not yet restored the USB address; it
contains no runtime evidence and does not affect this connected pass.

This closes the zero-listener delivery result. A later multicast test must
first add an independently observable, deliberately bounded listener so event
receipt can be attributed without relying on screen or reboot behavior.
