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
- 0107 removes the unsupported post-access PAGE_CON reads and uses the
  write-only selector bytes (`0x80`, then `0x02`) before each page-2 identity
  read. Attempt 4 preserved the complete baseline but returned zero for every
  identity register; its evidence is in
  `results/runtime-candidate-as-attempt-4-20260726.txt`.
- 0108 restores the read-modify-write transactions used by the exact Gemian
  implementation for both PAGE_CON selector calls. The interposed PAGE_CON
  reads are part of the page-revert protocol; this patch still omits any
  separate page-state assertion and keeps the operational regmap untouched.

The access-controller dependency remains mandatory; this candidate does not
change the proven DVFSP cleanup policy.

## Decision gate

The boot is successful only if the known-good console, keyboard, USB shell, and
eight CPUs remain available; DVFSP late validation passes; cleanup reports
shared-ap-dma=preserved, samples=32, and dma_unchanged=32; and I2C6 reaches
handoff=ready with the address 0x68 client bound. The regulator driver must log
the exact repeated signature, register exactly two outputs, and perform no
voltage, enable, disable, or configuration writes. The documented PAGE_CON
selector writes are allowed only to select page 2 with PAGE_REVERT. The
source-equivalent candidate uses PAGE_CON reads only as the read-modify-write
inputs required by the legacy selector transaction; it does not assert a
separate post-access page state or expose PAGE_CON through the operational
regmap. A fault, reset, watchdog reboot, unstable page state, signature
mismatch, or unexpected I2C6 ownership result is a stop condition.

Candidate AS booted successfully and preserved the console/USB/eight-CPU and
DVFSP/AP_DMA contracts, but failed closed before identity reads:
'da9211 1-0068: error -ENXIO: failed to repeat legacy page-state read'.
The primary 0x68 client existed, while no DA9214 driver or regulator bound.
The exact evidence is in
'results/runtime-candidate-as-attempt-1-20260725.txt'. Candidate AS attempt 2
used the primary-address selector path but failed at the same unsupported
PAGE_CON read; its evidence is in
'results/runtime-candidate-as-attempt-2-20260725.txt'. Candidate AS attempt 3
removed the PAGE_CON read entirely but used `0x82` for the second selector
write; all three identity reads consequently returned zero. Attempt 4 used the
corrected raw selector bytes, rebuilt and installed it to boot2 after a full
guarded readback, then booted successfully but still returned zero for the
identity registers. Its build, install, and runtime records are in
'results/build-candidate-as-attempt-4-20260726.txt',
'results/install-candidate-as-attempt-4-boot2-20260726.txt', and
'results/runtime-candidate-as-attempt-4-20260726.txt'. The next build/boot
tests only the source-equivalent selector transaction; it is not an A72
power-on candidate and must not change the CPU policy. Attempt 5 passed all
offline validators and is installed on boot2 with a full readback; its records
are in 'results/build-candidate-as-attempt-5-20260726.txt' and
'results/install-candidate-as-attempt-5-boot2-20260726.txt'. Runtime validation
is pending the owner-attended boot from boot2.

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
baseline and performs no device access. The corrected package and its
independent DT/container derivations passed the offline validators; the pinned
artifact and installer identities are recorded in
'results/build-candidate-as-20260725.txt'. The installer accepts only
gemini@192.168.1.50, requires the exact currently installed Candidate AS
padded boot2 predecessor checksum
1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513, perform one
bounded full-partition write with full readback verification, and never reboot
or change slot selection.

The USB banner may continue to identify the inherited initramfs baseline; the
DA9214 probe and handoff markers are the attributable Candidate AS evidence.
