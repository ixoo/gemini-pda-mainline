# DA921x netlink skb serialization

| Field | Value |
| --- | --- |
| ID | `2026-07-31-da921x-netlink-skb-serialization` |
| Status | `deployed to boot2; awaiting first selected boot` |
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

## Offline result

Buildbox produced the exact clean-source package at commit `2a0a253808592acd70c323d7176beb7d2c6bf7c2`.
The Buildbox host and the managed VM independently validated its provenance,
release, configuration, architecture, patchset, and 119 DTBs. The kernel image
is `d1030e6ab652ba753ff7a0956fc822950e42c6b2eb3fc3371781831919b4f3ee`.
No native VM kernel build was run.

Two independent assemblies produced byte-identical candidate directories and
the same 32-of-32 LK validation result. The selected Android boot image is
`28dd17db57bd6362634f2ce8c22a065ca03664f4151ab092eb9e378d4e4b2269`;
the exact 16 MiB `boot2` image is
`64667964870c38dcedbcfcbb8d8f644ad21fba66bb4e712987c4e4fdd3bb32ec`.
The redundant assembly was removed after comparison. The retained candidate
was exported with every manifest checksum passing.

The bounded installer requires the currently deployed corrected-layout image
`d9370fd47dd4c4e3ae1851ffd639a9b1e623b3f36de54560935323618690def2`
as its exact predecessor. It resolves `boot2` from the live GPT, rejects an
active or mounted target, records but does not back up the predecessor, writes
only the exact padded image, requires a matching full-partition readback, and
shuts the device down after success.

## Deployment result

The exact corrected-layout runtime was identity-checked at stage 17 and made
one native, storage-free return to Gemian. Gemian returned on `3.18.41+` with
a changed boot ID. The guarded installer resolved `boot2` as
`/dev/mmcblk0p30`, distinct from root `/dev/mmcblk0p29`, and confirmed the
expected predecessor with 98% battery capacity and `Good` health.

The installer wrote only the exact padded candidate, synchronized and flushed
it, verified the live partition checksum, then streamed an independent full
partition readback and compared every byte. The temporary readback was removed;
no backup was created because the verified project-wide backup is the recovery
basis. The device then shut down cleanly and disconnected, ready for the owner
to select `boot2` once.

The source-pinned one-shot collector is ready before that boot. It accepts only
release `7.1.3-gemini-da921x-skbser`, final stage 18, the unchanged validated
nine-entry environment, the unbound real OF client, and the zero-I2C/serviceable
baseline. It writes only its temporary check below initramfs `/run`, removes it,
and performs no partition access or reboot.
