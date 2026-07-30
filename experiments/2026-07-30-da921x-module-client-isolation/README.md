# DA921x module-profile client-creation isolation

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-30-da921x-module-client-isolation` |
| Status | `attempt 1 serviceable; enabled client creation implicated` |
| Subsystem | regulator, I2C, arm64 Device Tree |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-07-30 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 3 serviceability regression |

## Question or hypothesis

Did attempt 1 of the post-serviceability module profile fail because the
enabled DT child was instantiated, or because changing the kernel to support
the DA921x driver as a module changed the boot boundary?

This candidate preserves the exact failed module-profile `Image.gz`, kernel
config, manual-only module initramfs, Gate 3 controller description, Android
header, and LK placement contract. Its sole semantic delta sets
`/i2c@1100e000/regulator@68/status` from `okay` to `disabled`.

## Decision

- Serviceability implicates enabled DT-client creation, independent of driver
  probe execution.
- Another pre-serviceability failure implicates the module-enabled
  kernel/configuration boundary rather than client creation.
- Either result forbids an unchanged repeat and provides no permission to load
  the module, register a provider, or request A72.

## Safety

The disabled child prevents automatic client creation. The module remains at
its manual-only initramfs path but must not be loaded during this experiment.
No I2C transfer, bind, provider, A72 request, partition read, or partition
write is part of runtime collection.

## Observations

The source-pinned builder validated the exact failed module-profile artifact,
then derived the child-disabled DT twice and assembled the Android boot
container twice. Both pairs matched. All 32 LK gates passed. The exact 16 MiB
boot2 hash is
`5b41962c02a65883a60a144ab5864a9d100d8a7800e368d1155c983136b12b37`.
See `results/offline-validation.txt`.

On returned Gemian boot ID `d59afc66-9f02-4155-a76d-2a32472822db`,
live GPT resolved boot2 as `/dev/mmcblk0p30`, separate from active root
`/dev/mmcblk0p29`. The exact failed module-profile predecessor matched and
battery state was `100|Good`. No new backup was created. The write was synced
and flushed; the on-device checksum and an independent streamed full readback
matched byte-for-byte. Temporary staging and readback files were removed, then
the device shut down cleanly. See `results/install-boot2-20260730.txt`.

## Attempt 1

The owner selected `boot2` once. The candidate USB gadget enumerated on the
host with exact MAC `42:00:15:19:84:00`; after the host address was restored
on the new interface, the direct netcat shell was serviceable.

Runtime identity was `7.1.3-gemini-da921x-mod` on boot ID
`2008b2a9-3475-4662-9afd-519e892fdc6b`. CPUs 0--7 were online, CPUs 8--9
remained offline, USB was configured/up, the keyboard and tty1 were present,
and the active console was ttyS0. The DT child was exact compatible
`dlg,da9214-legacy` with `status = "disabled"`. No `0x68` client existed.

I2C6 handoff was ready with one successful initialization and zero transfer,
DMA-start, nonzero-start, and IRQ counters. Every lifecycle-oracle counter was
zero. The module file matched its exact packaged checksum, but no DA921x
symbol, driver directory, `/sys/module` entry, or `/proc/modules` entry
existed. `/sbin/modprobe` was absent. No module load, bind, I2C trigger, or
partition access was performed. See
`results/runtime-candidate-client-disabled-attempt-1-20260730.txt`.

## Conclusion

Attempt 1 passes the serviceability gate. Because it preserves the exact
failed module-profile kernel, config, initramfs, module bytes, USB identity,
and container contract while disabling only the child, it rules out the
module-enabled kernel/configuration boundary. The prior failure is caused by
the enabled DT-client path before DA921x driver code executes.

This result does not yet distinguish generic I2C-client instantiation and
resource/dependency handling from matching the real DA921x compatible/modalias.
This exact candidate must not be repeated, and the module must not be loaded.
