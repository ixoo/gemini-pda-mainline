# DA921x single uevent multicast

| Field | Value |
| --- | --- |
| ID | `2026-08-01-da921x-uevent-single-multicast` |
| Status | `deployed to boot2; awaiting selected-boot runtime` |
| Subsystem | I2C, OF, kobject uevent, netlink |
| Device variant | Named Gemini PDA development unit |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 3 transport boundary |

## Question or hypothesis

Can the exact runtime-proven stage-21 event be multicast once to the single
independently bound group-1 listener, with matching kernel-side topology and
broadcast counters plus one exact userspace receipt and no duplicate, while
preserving the unbound-client, zero-I2C, and serviceability baseline?

Stage 21 proved one uevent socket, exactly one group-1 listener, zero
broadcasts, and bounded no-receipt while the target skb was consumed before
multicast. This candidate retains that exact target and exposes a separate
one-shot trigger. It revalidates the topology under the socket-list mutex,
allocates one skb, calls group-1 multicast exactly once, and records stage 22
only after the bounded kernel-side result passes.

The static listener independently requires one exact 293-byte datagram: the
known header, all eight fixed entries in order, one final decimal `SEQNUM`,
kernel group-1 source, root credentials, and no second receipt during a bounded
wait. It reports only validation metadata and never prints the event payload.

## Decision

- Stage 22 with one baseline socket, one socket, one listener, one allocation,
  one broadcast call, normalized return zero, one exact userspace receipt, and
  no duplicate passes this transport discriminator.
- A topology mismatch must stop before allocation or multicast.
- Missing, malformed, truncated, non-kernel, non-root, or duplicate receipt;
  any counter mismatch; a second trigger; or a changed event or hardware
  baseline fails closed.
- A visual white/grey-screen and reboot cycle without exact identity, stage,
  or attributable reset evidence is inconclusive.

## Safety and build policy

The experiment performs one intentional multicast only after exact kernel,
stage, topology, helper, and sysfs-state gates. The initramfs has no udev and
the runtime helper must be the only group-1 listener. The matching DA921x
driver remains module-only and absent from the initramfs; the real client
remains unbound. The event path adds no driver, provider, I2C transfer,
register access, printk, or device-storage path.

The runtime check may temporarily remount only the virtual sysfs writable for
the exact trigger and must restore it read-only before result evaluation and
from an exit trap on every failure. Helpers exist only in initramfs `/run` and
are removed after execution. No partition read, device-storage write, or
reboot belongs to the runtime check.

Build only through `./scripts/build-kernel --backend buildbox` from an exact
clean pushed commit. Do not run a native VM kernel build unless the owner
explicitly requests one. The experiment patch uses the actual author identity,
carries no synthetic sign-off, and is not submission-ready.

## Associated code

- `listener/single-multicast-listener.c` binds the one group-1 listener,
  triggers the exact replay, and validates the bounded receipt without printing
  its payload.
- `scripts/build-listener.sh` pins the listener source and builds one static
  ARM64 helper in the managed VM.
- Patch `0143` implements the one-shot kernel-side stage-22 discriminator.

## Input validation

All 132 patches apply to the pinned Linux 7.1.3 source. The named profile
resolves the complete stage-21 predecessor plus only the single-multicast gate
and release `7.1.3-gemini-da921x-mcast1`. All 49 manifest profiles pass the
canonical-order invariant and all eight focused invariant mutations are
rejected.

Strict checkpatch has zero warnings and checks; its sole error is the
intentionally absent experiment-only DCO. The helper passes `-Wall -Wextra
-Werror`; two static ARM64 builds were byte-identical. Host and VM free-space
checks passed with 91 GiB and 83 GiB available. Exact identities are in
`results/input-validation.txt`. No native VM kernel build or device access was
used.

## Frozen pre-build hypothesis

Buildbox must compile the exact clean pushed commit and produce the named
release with every predecessor gate and the new single-multicast gate built in.
Offline assembly must pass the existing checksum, provenance, LK-container,
and configuration checks. No package or candidate may be selected by timestamp.

The complete input-to-action map is frozen in
`results/pre-build-hypothesis.txt`. Runtime and deployment plans will be frozen
against the exact validated package, container, and helper identities before
any device write or selected boot.

## Observations

The first buildbox job compiled and validated the expected release, but its
package provenance exposed that the frozen pre-build patchset identity had been
captured before a later metadata-only correction to patch `0143`'s email
diffstat. No source hunk or configuration changed. The package's exact patchset
therefore differed from the frozen value and was rejected before fetch,
candidate assembly, or device access. The correction and both identities are
recorded in `results/pre-build-identity-correction.txt`.

The replacement buildbox job compiled and validated exact clean commit
`bd4602cdcab7794972b503fcbdf3857cec703cfb`. Two independent managed-Linux
assemblies were byte-identical. The retained 6,864,896-byte container passed
all 32 LK analyzer gates and was padded to the exact 16,777,216-byte `boot2`
size. The duplicate assembly and helper were removed after comparison. No
native VM kernel build or device access was used.

Because each selected boot starts at stage 20, the frozen runtime checker first
re-establishes the proven stage-21 predecessor with the checksum-pinned bounded
listener, then invokes the separate checksum-pinned single-multicast helper.
Both triggers occur during one temporary writable sysfs interval; the exit trap
restores sysfs read-only on success and every failure. Exact identities and the
result-to-action map are in `results/offline-validation.txt` and
`results/runtime-plan.txt`.

The guarded installer identified known-good Gemian, resolved live GPT label
`boot2` to inactive `/dev/mmcblk0p30`, and matched the exact stage-21
predecessor checksum. External power was present at 100% with good battery
health. No new backup was created. The exact padded candidate was written,
synced, flushed, and verified by a matching independent full-partition
readback; its temporary copy was removed and clean shutdown was confirmed.
Sanitized evidence is in `results/deployment.txt`.

## Follow-up

The owner physically selects `boot2`. Once the USB/netcat console is available,
run the checksum-pinned one-shot runtime collector and preserve its exact
stage-22 result before choosing the next Gate 3 boundary.
