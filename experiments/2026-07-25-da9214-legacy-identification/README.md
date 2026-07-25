# Candidate AS: identify the legacy DA9214

Candidate AS is the next hardware candidate after Candidate AR. It keeps the
AR console, keyboard, USB gadget, manual reboot, SMP-8, and DVFSP/I2C6
ownership boundary. It adds only the legacy DA9214 identification path and
the exact electrical description needed to exercise it.

## Evidence and hypothesis

The live Gemini repeatedly returned 0xd9 from legacy interface register 0x105,
0xd0 from interface2 register 0x106, and 0xc0 from CONFIG_E register 0x147
through the Gemian legacy PAGE_CON page-2 protocol. The normal DA9211-family
application-ID read at 0x201 returned 0x0 and is not a usable identity test on
this board.

The hypothesis is that a page-2 probe which requires the exact three-value
signature will bind the real two-output legacy DA9214. The legacy selector
protocol necessarily writes only the documented PAGE_CON selector at the
primary 0x68 address with PAGE_REVERT set; it must not write voltage, enable,
disable, or configuration registers. The probe remains behind AR's already
validated DVFSP handoff and AP_DMA preservation boundary.

## Unique changes

- 0096 adds a board-specific legacy DA9214 protocol path with a page-2
  identification regmap and two-regulator contract.
- 0104 requires the exact repeated 0xd9/0xd0/0xc0 signature.
- 0105 restores I2C6's 3.4 MHz push-pull electrical properties and adds the
  two DA9214 outputs, with no A72 consumer, supply, boot-on, voltage request,
  or enable GPIO.
- 0106 corrects the page-2 transport to the Gemian primary-address PAGE_CON
  sequence after the first AS boot rejected the adjacent-address assumption.

The access-controller dependency remains mandatory; this candidate does not
change the proven DVFSP cleanup policy.

## Decision gate

The boot is successful only if the known-good console, keyboard, USB shell, and
eight CPUs remain available; DVFSP late validation passes; cleanup reports
shared-ap-dma=preserved, samples=32, and dma_unchanged=32; and I2C6 reaches
handoff=ready with the address 0x68 client bound. The regulator driver must log
the exact repeated signature, register exactly two outputs, and perform no
voltage, enable, disable, or configuration writes. The documented PAGE_CON
selector writes are allowed only to select page 2 with PAGE_REVERT and must be
followed by a verified page-0 state. A fault, reset, watchdog reboot, unstable
page state, signature mismatch, or unexpected I2C6 ownership result is a stop
condition.

Candidate AS booted successfully and preserved the console/USB/eight-CPU and
DVFSP/AP_DMA contracts, but failed closed before identity reads:
'da9211 1-0068: error -ENXIO: failed to repeat legacy page-state read'.
The primary 0x68 client existed, while no DA9214 driver or regulator bound.
The exact evidence is in
'results/runtime-candidate-as-attempt-1-20260725.txt'. This identifies the
transport bug; the next candidate applies the Gemian PAGE_CON selector
sequence and is not a repeat of the AS image.

## Reproducibility

- Profile:
  observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-observer-initcall-blacklist-dvfsp-handoff-owner-i2c6-consumer-ap-dma-preserve-da9214-legacy-readonly
- Series: patches/series-dvfsp-handoff-owner-i2c6-consumer-ap-dma-preserve-da9214-legacy-readonly
- Builder: scripts/build-candidate-as.sh
- DT validator: scripts/validate-dtb-delta-as.py
- Package/boot validators: scripts/validate-package-as.py and
  scripts/validate-boot-as.py
- Installer deriver: scripts/derive-installer.py

The builder reuses the exact Candidate AO DT/initramfs/keymap/console/USB
baseline and performs no device access. Artifact hashes remain TO_PIN_* until
two independent package/container assemblies agree. The eventual installer
will accept only gemini@192.168.1.50, require the exact current Candidate AR
padded boot2 checksum
89a77153f57b6a3061a3e46cbda2e0b79a806464044d48713ddcfcb624526b0a, perform one
bounded full-partition write with full readback verification, and never reboot
or change slot selection.

The USB banner may continue to identify the inherited initramfs baseline; the
DA9214 probe and handoff markers are the attributable Candidate AS evidence.
