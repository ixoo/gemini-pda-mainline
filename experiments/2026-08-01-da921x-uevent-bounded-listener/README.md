# DA921x bounded uevent listener

| Field | Value |
| --- | --- |
| ID | `2026-08-01-da921x-uevent-bounded-listener` |
| Status | `input validated; awaiting Buildbox` |
| Subsystem | I2C, OF, kobject uevent, netlink |
| Device variant | Named Gemini PDA development unit |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 3 transport boundary |

## Question or hypothesis

Can one independently observable userspace group-1 listener be added to the
runtime-proven stage-20 topology, while the exact target event is revalidated,
serialized, and consumed before multicast, without changing the zero-hardware
or serviceability baseline?

The stage-20 predecessor observed one uevent socket, no listener, no skb
allocation, and no broadcast. This candidate retains the exact target kobject
after that result and exposes a one-shot, exact-token trigger. A purpose-built
static helper binds one listener before issuing the trigger. Stage 21 requires
the same one-socket topology, exactly one listener, and no broadcast. The
helper additionally requires a bounded 1.5-second receive timeout with no
event receipt.

## Decision

- Exact stage 21, `attempts=1`, `baseline_sockets=1`, `sockets=1`,
  `listeners=1`, `broadcasts=0`, and a bounded no-receipt result pass this
  discriminator. The next experiment may separately test one multicast.
- Stage 20 after the trigger proves that the replay did not finish the new
  path and rejects the candidate.
- Any other socket or listener count, any broadcast, any event receipt, a
  second trigger, or any changed event or hardware baseline fails closed.
- A visual white/grey-screen and reboot cycle without exact identity, stage,
  or attributable reset evidence is inconclusive.

## Safety and build policy

The retained target can be triggered exactly once and only from stage 20. The
replayed event traverses the normal socket list but is consumed before
`netlink_broadcast()`. The listener helper never prints an event payload. The
matching DA921x driver remains module-only and absent from the initramfs; the
real client remains unbound. The patch adds no driver, provider, I2C transfer,
register access, printk, device-storage path, or multicast delivery.

Build only through `./scripts/build-kernel --backend buildbox` from an exact
clean pushed commit. Do not run a native VM kernel build unless the owner
explicitly requests one. The experiment patch uses the actual author identity,
carries no synthetic sign-off, and is not submission-ready.

## Associated code

- `listener/bounded-listener.c` is the small static ARM64 listener and trigger
  verifier. It requires root only to write the experiment-only sysfs trigger.
- `scripts/build-listener.sh` verifies the pinned source identity, enforces a
  private managed output path, and builds with the VM cross compiler.
- The listener binary is a private, ignored runtime artifact and is not
  committed. Its reproducible identity is recorded in
  `results/input-validation.txt`.

## Input validation

All 131 patches apply to the pinned Linux 7.1.3 source. The named profile
resolves the complete stage-20 predecessor plus only the bounded-listener gate
and release `7.1.3-gemini-da921x-boundlis`. All 48 manifest profiles pass the
canonical-order invariant and all eight focused invariant mutations are
rejected.

Strict checkpatch has zero warnings and checks; its sole error is the
intentionally absent experiment-only DCO. The helper passes `bash -n`,
ShellCheck, and `-Wall -Wextra -Werror`. Two static ARM64 builds were
byte-identical. Host and VM free-space checks passed with 91 GiB and 83 GiB
available. Exact identities are in `results/input-validation.txt`. No native
VM kernel build or device access was used for this experiment validation.

## Frozen pre-build hypothesis

Buildbox must compile the exact clean pushed commit and produce the named
release with every predecessor gate and the new bounded-listener gate built
in. Offline assembly must pass the existing checksum, provenance, LK-container,
and configuration checks. No package or candidate may be selected by timestamp.

The complete input-to-action map is frozen in
`results/pre-build-hypothesis.txt`. Runtime and deployment plans will be frozen
against the exact validated package and container identities before any device
write or selected boot.

## Observations

Input validation only. No compile claim, hardware-support claim, device write,
or runtime claim has been made yet.

## Follow-up

Commit and push the clean source, build it on Buildbox, fetch only the validated
package, assemble twice, and compare the results. If all offline gates pass,
deploy only to live-GPT-resolved inactive `boot2` under the standing guarded
workflow, verify the full-partition readback, shut the device down, and run the
frozen stage-21 listener check on the first selected boot.
