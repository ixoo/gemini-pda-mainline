# DA921x post-serviceability name-only client

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-30-da921x-name-only-client` |
| Status | `attempt 1 safely inconclusive; sysfs was read-only` |
| Subsystem | regulator, I2C, arm64 Device Tree, driver core |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-07-30 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 3 serviceability regression |

## Question or hypothesis

Is the compatible-derived I2C client name/modalias sufficient to reproduce the
pre-serviceability failure without an OF node?

The boot candidate preserves the exact module-profile kernel and exact
module-free initramfs, but disables the real-compatible DT child to regain
serviceability. After all serviceability, driver-absence, and zero-transfer
gates pass, the runtime helper creates exactly one unbound name-only
`da9214-legacy` client at `0x68` through the controller’s sysfs `new_device`
interface.

## Decision

- Surviving name-only creation with zero I2C activity implicates the OF
  node/modalias path rather than the derived I2C name/modalias.
- A reset caused by name-only creation makes that derived client identity
  sufficient.
- Any resident matching driver, nonzero counter, ambiguous adapter, or
  pre-existing `0x68` client aborts before the write.

## Safety

The initramfs contains no DA921x module or loader. The runtime helper proves
that no matching driver is resident before creating the client. No driver may
bind, and every I2C transfer, DMA-start, nonzero-start, IRQ, and lifecycle
oracle counter must remain zero. No device partition is accessed.

## Observations

The source-pinned assembly produced raw candidate
`e8d2999159754e9548f45e93340511861814988a842314cf21dcb2a74a4e8890`
and exact 16 MiB boot2 image
`fc17b54c7b107f92297fd6715c0c2ec3b322ae79ef322b00ae8cacb332735d5e`.
All 32 LK/container gates passed. Direct DT validation confirmed exact
compatible `dlg,da9214-legacy`, unchanged `0x68,0x69`, and `status =
"disabled"`. The exact module-free initramfs is preserved.

The corrected runtime helper is
`9b633372e224b3a551a5ca571346d7d9c2f6c5433a18e7fbac471c23813dd6de`.
Static validation found exactly one sysfs control write and no module load,
driver bind, I2C utility, partition, reboot, or poweroff operation.

See [offline validation](results/offline-validation.txt) and the
[pre-boot hypothesis](results/pre-boot-hypothesis.txt).

The guarded installer resolved logical `boot2` as `/dev/mmcblk0p30` from the
live GPT while Gemian boot ID
`b04cd6b0-f10f-4ff2-9cdd-c1d2b66ffc63` was active. The exact failed no-module
predecessor checksum matched. It wrote the padded candidate, synchronized and
flushed it, then required both a matching on-device full-partition checksum
and an independent 16 MiB byte comparison. Both matched
`fc17b54c7b107f92297fd6715c0c2ec3b322ae79ef322b00ae8cacb332735d5e`.
No new backup was created under the project’s standing backup policy. The
temporary readback was removed and device shutdown was confirmed. See
[installation result](results/install-boot2-20260730-2034.txt).

## Attempt 1

The owner selected `boot2` once and reported a good boot. Runtime identity was
`7.1.3-gemini-da921x-mod` on boot ID
`611b1935-4414-435b-a2b8-77365f3ea474`. Console, USB/netcat, CPUs 0--7,
keyboard, tty1, I2C6 handoff, and the zero-transfer/oracle baseline were
serviceable. The child was disabled, no `0x68` client existed, and no DA921x
module, symbol, or driver was present.

Three helper revisions failed closed before the control write while correcting
DT string normalization, first-line counter tokenization, and the observed
adapter symlink topology. Read-only snapshots after each abort confirmed no
client and all counters zero.

The final helper
`9b633372e224b3a551a5ca571346d7d9c2f6c5433a18e7fbac471c23813dd6de`
passed every pre-creation gate and issued the single permitted
`new_device` write. The kernel rejected it because the exact initramfs mounts
sysfs read-only. No client was created, no driver bound, and all I2C/oracle
counters remained zero. The procedure did not remount sysfs because that was
outside the predeclared attempt. Native reboot returned Gemian `3.18.41+` on
new boot ID `48f75b8b-b3e9-47cc-a378-bdd7a91bd3c0`.

See [runtime result](results/runtime-name-only-attempt-1-20260730.txt).

## Conclusion

Attempt 1 is safely inconclusive about name-only client creation: the sysfs
mount policy rejected the write before the kernel’s `new_device` parser could
instantiate a client. It adds durable evidence that the serviceable disabled
child and exact no-module kernel retain a zero-activity baseline.

A second selected boot of the same artifact is permitted only for a new,
decision-changing observation path: an exact helper must validate the
read-only baseline, create a cleanup trap, briefly remount sysfs read-write,
issue one `new_device` write, immediately restore sysfs read-only, and then
verify the client and zero counters. It is not a repeatability test.

The attempt 2 hypothesis is recorded in
[pre-run RW-window hypothesis](results/pre-run-rw-window-attempt-2.txt).
The exact cleanup-trapped helper is
`62f266f005062c6e70239e4ff5ade97721a7b19ff6ae290f75103e8bc4cd332d`;
static validation found one `new_device` write, two bounded sysfs remount
operations, and no module load, driver bind, I2C utility, partition, reboot,
or poweroff operation.
