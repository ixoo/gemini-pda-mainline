# DA921x post-serviceability name-only client

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-30-da921x-name-only-client` |
| Status | `installed and powered off; first boot pending` |
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

The runtime helper is
`31a44e9fd1f58ecb760aca0353c489060450a98770e598b79a4f6e49e73026ea`.
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
