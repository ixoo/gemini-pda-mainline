# DA921x uevent no-listener delivery

| Field | Value |
| --- | --- |
| ID | `2026-07-31-da921x-uevent-no-listener-delivery` |
| Status | `input validated; awaiting Buildbox build` |
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
