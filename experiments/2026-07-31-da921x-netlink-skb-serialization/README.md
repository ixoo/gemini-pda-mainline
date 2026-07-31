# DA921x netlink skb serialization

| Field | Value |
| --- | --- |
| ID | `2026-07-31-da921x-netlink-skb-serialization` |
| Status | `offline validated; awaiting Buildbox build` |
| Subsystem | I2C, OF, kobject uevent, netlink |
| Device variant | Named Gemini PDA development unit |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 3 transport boundary |

## Question or hypothesis

Can the exact runtime-validated DA921x add event be allocated and serialized
into its normal netlink skb, then consumed before socket traversal or multicast,
without losing the established serviceability and zero-hardware baseline?

The predecessor proved the corrected eight fixed entries plus final `SEQNUM`,
successful suppression, return, and cleanup serviceable. This candidate changes
only the next transport boundary: it uses the normal skb allocator, validates
the exact header, environment copy, 293-byte total length, root credentials,
destination group, and port ID, records stage 18, and consumes the skb.

## Decision

- Exact stage 18 plus the unchanged baseline proves allocation, serialization,
  metadata initialization, and skb cleanup safe; the next split is socket-list
  traversal/listener discovery versus multicast delivery.
- A reset stops transport work and implicates serialization or skb cleanup.
- A serviceable stage 17 result identifies allocation or validation failure and
  does not authorize loosening an expectation.
- Any changed event, client, CPU, handoff, or I2C baseline rejects attribution.

## Safety and build policy

The skb is consumed before the uevent socket list is traversed and before any
netlink multicast. The matching DA921x driver remains module-only and absent
from the initramfs; the real client remains unbound. The patch adds no driver,
provider, I2C transfer, register access, printk, device-storage path, or reboot.

Build the kernel only through `./scripts/build-kernel --backend buildbox` from
an exact clean pushed commit. Do not run a native VM kernel build unless the
owner explicitly requests one. The experiment patch uses the actual author
identity, carries no synthetic sign-off, and is not submission-ready.

## Input validation

All 128 patches apply to the pinned Linux 7.1.3 source. The named profile
resolves the complete predecessor state plus only the new serialization gate
and release `7.1.3-gemini-da921x-skbser`; the predecessor profile resolves the
new gate off. All 45 manifest profiles pass the canonical-order invariant and
all eight focused invariant mutations are rejected.

Focused strict checkpatch reports zero errors, warnings, and checks when the
intentionally absent experiment-only DCO is excluded. Host and VM free-space
checks passed with 93 GiB and 83 GiB available. The exact patchset and
configuration identities are recorded in `results/input-validation.txt`.
No native VM kernel build was run and the device was not accessed for this
experiment.
