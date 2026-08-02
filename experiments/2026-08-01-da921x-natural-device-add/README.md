# DA921x natural I2C device-add path

| Field | Value |
| --- | --- |
| ID | `2026-08-01-da921x-natural-device-add` |
| Status | `deployed and powered off; selected boot2 runtime pending` |
| Subsystem | I2C, driver core, OF, kobject uevent, netlink |
| Device variant | Named Gemini PDA development unit |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 3 transport boundary |

## Question or hypothesis

Can the exact OF-created legacy DA921x client complete its boot-time
`device_register()`/`device_add()` path while its natural add event traverses
the ordinary `kobject_uevent_env()` namespace and network-broadcast call site,
returns zero, and preserves the zero-hardware and serviceability baseline?

Stage 25 proved the same exact event through that call site and public return
as a post-serviceability replay with one listener. This experiment changes one
boundary: the observed event is the original add event emitted inside the
client's natural device-registration path. Because this happens before
userspace can bind a group-1 listener, the already-proven boot topology must
contain one socket, zero listeners, zero skb allocations, and zero broadcasts.

## Decision

- One exact device-register entry and return, one uevent call-site entry and
  return, one public return, one namespace check, one untagged route, zero
  tagged routes, and return zero throughout advances to stage 26.
- The ordinary broadcast path must independently observe one socket, zero
  listeners, zero allocations, and zero broadcasts; the exact unbound OF
  client must remain present after `device_register()` returns.
- CPU0-7, console, keyboard, USB, native reboot, I2C5/AP-DMA, DVFSP handoff,
  and all zero-I2C/oracle counters must remain unchanged.
- Success closes the real-compatible event/serviceability regression and
  permits a separately built identification-only driver-bind experiment. It
  does not prove driver bind, regulator-provider behavior, a register write,
  or A72 power.
- Any missing or repeated boundary, nonzero return, allocation or broadcast,
  client bind, hardware activity, or baseline regression rejects the result.

## Safety and negative space

Patch `0147` adds read-only counters and one exact observation arm immediately
before the existing `device_register()` call. It has no sysfs trigger, replay,
client lifecycle operation, driver, provider, I2C transfer, register access,
printk, usermode helper, device-storage path, or CPU8/9 request. The matching
driver remains module-only and absent from the initramfs, and both A72 CPUs
remain disabled.

Build only with `./scripts/build-kernel --backend buildbox` from an exact clean
pushed commit. Do not run a native VM kernel build without an explicit owner
request. The experiment-only patch has no DCO sign-off and is not
submission-ready.

## Evidence plan

The runtime checker is read-only. It must require the exact kernel release,
stage 26, exact natural-device-add counters, the unbound `1-0068` OF client,
CPU0-7 online with CPU8-9 offline, zero I2C/oracle activity, and the complete
serviceability baseline. A fresh second read-only snapshot must confirm the
same persistent state. Visual white/grey-screen or reboot behavior alone is
inconclusive.

## Input validation

The 136-patch canonical series accepts patch `0147` after the runtime-proven
Stage 25 source. All 53 manifest profiles satisfy the canonical-subsequence
invariant and all eight focused invariant mutations are rejected. The isolated
fragment selects the natural-device-add gate and release suffix exactly.
Strict Checkpatch reports zero warnings and zero checks; its only error is the
intentionally absent experiment-only DCO sign-off. The read-only runtime
checker passes Bash syntax and managed-VM ShellCheck. No native VM kernel build
was run. Exact identities are in `results/input-validation.txt`.

## Offline validation

Buildbox compiled the exact clean pushed commit `a8a6efa` and the fetched
package revalidated with the intended 136-patch series and isolated profile.
The matching driver remains module-only and absent from the initramfs,
userspace uevent helpers remain disabled, and A72 power remains disabled. Two
independent Linux candidate assemblies were byte-identical. The retained
candidate passed its checksum manifest and all 32 LK container gates; it
carries the unchanged module-free initramfs and the exact previously validated
real-compatible Gemini DT. The runtime collector is read-only and writes only
its temporary checker below initramfs `/run`. Exact identities are in
`results/offline-validation.txt`.

## Deployment

The guarded installer ran from known-good Gemian, resolved logical `boot2`
from the live GPT, proved that it was neither the active root nor mounted,
matched the exact Stage 25 predecessor, and passed the stable-power gates. It
wrote the padded Stage 26 image, synchronized and flushed it, matched the
device-side checksum, and passed an independent full-partition readback. No
fresh backup was created; the project-wide backup is the recovery source. The
temporary readback was removed and the device shut down cleanly after verified
success. Exact sanitized evidence is in `results/deployment.txt`.
