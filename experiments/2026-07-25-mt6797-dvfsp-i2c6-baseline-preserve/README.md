# Candidate AR: preserve the shared MT6797 AP_DMA owner

This experiment is the next hardware candidate after Candidate AQ. It keeps the
known-good console, keyboard, USB gadget, manual reboot, SMP-8, A72 observer,
and childless I²C6 consumer contract unchanged. The only kernel-code change is
the DVFSP consumer-cleanup oracle in patch 0103.

## Decision-changing evidence

Candidate AQ was booted on the named Gemini and inspected over the development
USB shell. The early and late clock summaries were byte-identical. The enabled
I²C5 path owned `infra_ap_dma` (refcount 2, enabled), while
`infra_i2c_appm` was disabled after handoff. Candidate AP's cleanup oracle
required both gates to close, so it correctly failed closed before I²C6 could
bind. AQ therefore established that AP_DMA is a shared gate and must not be
treated as an exclusive I²C6 resource.

## Hypothesis

The I²C6 consumer can proceed if cleanup requires the main DVFSP signature and
`infra_i2c_appm` to gate, while requiring the AP_DMA gate bit to remain valid
and unchanged from the pre-probe baseline for all 32 post-cleanup samples.
This preserves the existing I²C5 owner and adds no regulator, storage, A72,
CPU-hotplug, or reboot operation.

## Decision gate

The candidate is hardware-successful only if the device boots with the existing
console and keyboard contract, the DVFSP late handoff passes, I²C6 reaches its
ready state, `infra_i2c_appm` is gated, and all 32 AP_DMA samples are valid and
match the pre-probe gate bit. Any other result is evidence to stop and update
the ownership model; it is not a reason to relax the oracle.

The candidate must also retain the existing AP_DMA observation path. Runtime
evidence must report both the count of samples where AP_DMA happened to be
gated and the count where its gate bit was preserved unchanged.

## Reproducibility

- Kernel profile: `observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-observer-initcall-blacklist-dvfsp-handoff-owner-i2c6-consumer-ap-dma-preserve`
- Patch series: `patches/series-dvfsp-handoff-owner-i2c6-consumer-ap-dma-preserve`
- New patch: `v7.1.3/0103-soc-mediatek-preserve-shared-MT6797-AP-DMA-owner.patch`
- Builder: `scripts/build-candidate-ar.sh`
- Installer deriver: `scripts/derive-installer.py`

The builder reuses the exact Candidate AO DT/initramfs/keymap/console/USB
baseline and the existing validated package/boot validators. It performs no
device access. Artifact hashes are intentionally `TO_PIN_*` until two
independent package/container assemblies agree; only then may an installer be
derived and the standing `boot2` safety checks be applied.

The installer is pinned to the current Candidate AQ padded `boot2` checksum
(`4ad3f29c07a243108f50f3a70049336b116fed80dcb694b2d9e0f872591255c4`) and
accepts only the exact development target `gemini@192.168.1.50`. It performs
one bounded, full-partition `boot2` write, verifies a full readback, and never
reboots or changes slot selection.

## Runtime result: 2026-07-25

Candidate AR was booted from `boot2` on the named Gemini. The development USB
shell became available immediately, while the console remained quiet during the
intentional 45-second late-validation window. The kernel reported the handoff
ready at approximately 48 seconds; this is a delay, not a boot failure.

Observed over the USB shell:

- `mt6797-dvfsp-handoff`: `state=ready`, `late_validation=passed`, and
  `i2c6_policy=requires-ready`.
- Cleanup oracle: `clocks=i2c-appm shared-ap-dma=preserved validation=passed
  samples=32 dma_gated=0 dma_unchanged=32`.
- I²C6 status: `handoff=ready`, one probe attempt, one successful init, and
  both clock-domain checks passed.
- `/proc/cpuinfo` reported all 8 CPUs; the existing USB shell and keyboard
  input-capture path remained available.

The USB banner still says Candidate AC because the initramfs/USB development
baseline is intentionally byte-exact across this experiment. The kernel
handoff markers above are the attributable Candidate AR result. The decision
gate passed: preserve AP_DMA as a shared owner and allow the I²C6 consumer to
bind after the main DVFSP handoff.
