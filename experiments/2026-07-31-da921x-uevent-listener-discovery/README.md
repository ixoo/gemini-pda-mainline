# DA921x uevent listener discovery

| Field | Value |
| --- | --- |
| ID | `2026-07-31-da921x-uevent-listener-discovery` |
| Status | `deployed to boot2; awaiting first selected boot` |
| Subsystem | I2C, OF, kobject uevent, netlink |
| Device variant | Named Gemini PDA development unit |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 3 transport boundary |

## Question or hypothesis

Can the exact runtime-validated DA921x event traverse the normal uevent socket
list and inspect group-1 listener state, then return with the skb still consumed
before multicast, without losing the established serviceability and
zero-hardware baseline?

The predecessor proved exact 293-byte skb allocation and serialization,
metadata initialization, consumption, return, and cleanup serviceable. This
candidate changes only the next transport boundary: under the normal socket-list
mutex it counts at most 1024 socket entries and their group-1 listener state,
exposes the two bounded integers read-only, records stage 19, and never calls
`netlink_broadcast()`.

## Decision

- Exact stage 19 plus bounded counts and the unchanged baseline proves socket
  list traversal and listener discovery safe; the next split is a controlled
  no-listener delivery result versus multicast to a listener.
- A reset stops transport work and implicates list traversal or listener
  inspection.
- A serviceable stage 18 result rejects traversal success and localizes the
  failure without authorizing a looser expectation.
- Any changed event, client, CPU, handoff, or I2C baseline rejects attribution.

## Safety and build policy

The predecessor skb remains consumed before this discriminator. The matching
DA921x driver remains module-only and absent from the initramfs; the real client
remains unbound. The patch adds no driver, provider, I2C transfer, register
access, printk, device-storage path, reboot, skb delivery, or multicast.

Build the kernel only through `./scripts/build-kernel --backend buildbox` from
an exact clean pushed commit. Do not run a native VM kernel build unless the
owner explicitly requests one. The experiment patch uses the actual author
identity, carries no synthetic sign-off, and is not submission-ready.

## Input validation

All 129 patches apply to the pinned Linux 7.1.3 source. The named profile
resolves the complete stage-18 predecessor plus only the new listener-discovery
gate and release `7.1.3-gemini-da921x-listen`; the predecessor profile resolves
the new gate off. All 46 manifest profiles pass the canonical-order invariant
and all eight focused invariant mutations are rejected.

Focused strict checkpatch reports zero warnings and checks when the
intentionally absent experiment-only DCO is excluded. Host and VM free-space
checks passed with 92 GiB and 83 GiB available. The exact patchset and
configuration identities are recorded in `results/input-validation.txt`.
No native VM kernel build was run and the device was not accessed for this
experiment.

## Offline candidate validation

Buildbox produced the exact clean `arm64` package from repository commit
`ea93d5e1555692296f88dd90478fc7c34213b507`. Independent managed-VM
validation passed its complete checksum and provenance bundle, including all
119 DTBs. The selected package has release
`7.1.3-gemini-da921x-listen`; the matching driver remains module-only, while
the retained lifecycle initramfs contains neither modules nor `modprobe`.

Two independent managed-VM assemblies were byte-identical. The retained
6,862,848-byte LK container passed all 32 analyzer gates and was padded to the
exact 16,777,216-byte boot2 size. Only the selected candidate was exported;
the duplicate assembly was removed after comparison. Exact package, container,
manifest, assembler, and guarded-installer identities are recorded in
`results/offline-validation.txt`. No native VM kernel build or device access
was used for this validation.

## Deployment

The proven stage-18 runtime was identity-gated by release and boot ID over its
USB netcat console, then requested its native reboot without storage access.
Known-good Gemian returned as `3.18.41+` with changed boot ID
`688dcb74-51c4-4dbc-82e8-890d95b770cb`.

The guarded installer resolved live GPT label `boot2` to `/dev/mmcblk0p30`
while root was `/dev/mmcblk0p29`. External power was present, capacity was
100%, health was Good, and the full predecessor checksum matched the proven
stage-18 candidate. No new backup was created. The exact padded listener
candidate was written, synced, flushed, and verified by matching full-partition
readback; the temporary readback was removed and clean shutdown was confirmed.
Sanitized deployment evidence is recorded in `results/deployment.txt`.
