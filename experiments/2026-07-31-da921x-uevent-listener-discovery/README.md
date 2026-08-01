# DA921x uevent listener discovery

| Field | Value |
| --- | --- |
| ID | `2026-07-31-da921x-uevent-listener-discovery` |
| Status | `input validated; awaiting Buildbox build` |
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
