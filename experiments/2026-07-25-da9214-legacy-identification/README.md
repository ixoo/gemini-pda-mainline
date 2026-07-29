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

### Secondary-address correction (2026-07-27)

Observation: Candidate AS attempt 1 completed its first uncached direct read
from 7-bit address `0x69`, wire offset `0x00` (page-2 register `0x100`,
`PAGE_CON`). Only the immediately repeated `PAGE_CON` read returned `-ENXIO`;
the probe then stopped before attempting offsets `0x05`, `0x06`, or `0x47`.
The retained
`probe_interpretation=the-adjacent-0x69-page2-assumption-is-wrong` is therefore
invalid and superseded: attempt 1 did not reject address `0x69`.

Documented protocol: Renesas, *DA9213, DA9214, and DA9215 Multi-Phase 5A/Phase
DC-DC Buck Converter*, Datasheet Revision 3.4, 10-Feb-2022, maps pages 2 and 3
to the basic 2-WIRE address plus one (`0xD2`/`0xD3` from the default
`0xD0`/`0xD1`), which translates from primary 7-bit address `0x68` to
secondary address `0x69`. Page-2 registers `0x105`, `0x106`, and `0x147`
therefore use wire offsets `0x05`, `0x06`, and `0x47`, respectively, at
`0x69`.

Test and inference: Candidate Cassini tested this documented route only after
its USB service was available, using two bounded signature passes over those
three offsets and no `PAGE_CON` access. All six transactions and IRQs
completed, but userspace reported prefilled zero bytes, so RX-buffer overwrite
was not proven. Separate retained Gemian boot logs do prove the live
`d9 d0 c0` tuple. Neutral Candidate Photon r2 must repeat the exact six
`I2C_RDWR` request/message sequences Cassini issued, complete both passes after
successful transfers, and use distinct nonzero receive prefills while
preserving objective pre/post comparisons before any transport conclusion.
Photon r0 was superseded before any boot or probe invocation; r1 reproduced
but was superseded before installation because its output labels overclaimed
causality. Neutral r2 was installed to inactive logical `boot2` with a
matching full readback, but attempt 1 failed before recoverable console/USB
service and returned automatically to Gemian. The manually invoked helper did
not run. Candidate Hubble then restored the complete exact hardware-passed
Cassini artifact as a zero-boot-delta foundation. Exact r2 ran once from
volatile `/run` after USB serviceability, without another kernel boot. All six
ioctls completed and the transfer/DMA/start/IRQ counters advanced, but every
post byte remained equal to its distinct prefill. Cassini's zeros therefore
reflected its receive initialization, not a DA9214 tuple. The mainline WRRD
receive path must be localized before returning to the provider experiment.

## Unique changes

- 0096 adds a board-specific legacy DA9214 protocol path with a page-2
  identification regmap and two-regulator contract.
- 0104 requires the exact repeated 0xd9/0xd0/0xc0 signature.
- 0105 restores I2C6's 3.4 MHz push-pull electrical properties and adds the
  two DA9214 outputs, with no A72 consumer, supply, boot-on, voltage request,
  or enable GPIO.
- 0106 switched the page-2 transport to the Gemian primary-address PAGE_CON
  sequence based on attempt 1's then-recorded adjacent-address interpretation.
  The correction above supersedes that interpretation; this patch remains
  historical experiment lineage, not evidence against `0x69`.
- 0107 removes the unsupported post-access PAGE_CON reads and uses the
  write-only selector bytes (`0x80`, then `0x02`) before each page-2 identity
  read. This literal second byte differs from the active Gemian
  read-modify-write result, which preserves bit 7 and writes `0x82`. Attempt 4
  preserved the complete baseline but reported zero for every identity
  register; its evidence is in
  `results/runtime-candidate-as-attempt-4-20260726.txt`.
- 0108 restores the read-modify-write transactions used by the exact Gemian
  implementation for both PAGE_CON selector calls. The interposed PAGE_CON
  reads are part of the page-revert protocol; this patch still omits any
  separate page-state assertion and keeps the operational regmap untouched.
- 0109 keeps the same selector semantics but replaces regmap's transport with
  the vendor-shaped explicit `i2c_transfer` message sequence and a driver
  mutex. This isolates transaction shape/serialization without enabling A72
  or changing the operational regmap.

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
write; all three identity reads were reported as zero. Attempt 4 used literal
write-only selector bytes (`0x80`, then `0x02`), then believed to be the
corrected sequence but now known to differ from Gemian's final `0x82`
read-modify-write result. It rebuilt and installed to boot2 after a full
guarded readback, then booted successfully but still reported zero for the
identity registers. Its build, install, and runtime records are in
'results/build-candidate-as-attempt-4-20260726.txt',
'results/install-candidate-as-attempt-4-boot2-20260726.txt', and
'results/runtime-candidate-as-attempt-4-20260726.txt'. The next build/boot
tests only the source-equivalent selector transaction; it is not an A72
power-on candidate and must not change the CPU policy. Attempt 5 passed all
offline validators and is installed on boot2 with a full readback; its records
are in 'results/build-candidate-as-attempt-5-20260726.txt' and
'results/install-candidate-as-attempt-5-boot2-20260726.txt'. Runtime validation
is recorded in 'results/runtime-candidate-as-attempt-5-20260726.txt'. The owner
reported a white screen followed by an automatic return to Gemian. Read-only
recovery found Gemian's watchdog-class boot reason (`wdt_by_pass_pwk`), while
pstore and `/proc/last_kmsg` contained no candidate record. This is evidence of
a watchdog reset before the known-good console/USB observation point, not proof
that the read-modify-write transaction alone caused the reset. The unique
candidate delta is nevertheless 0108, so it is not repeated; the next test must
isolate the DA9214 transaction with a bounded, fail-closed probe before any A72
power-on work. Attempt 6 passed the offline package, DT, LK, boot, and compiled
handoff gates. It is installed on boot2 with a full readback; its records are in
'results/build-candidate-as-attempt-6-20260726.txt' and
'results/install-candidate-as-attempt-6-boot2-20260726.txt'. It keeps A72
blacklisted and changes only the explicit vendor-shaped I2C transaction layer.
The owner again observed a black screen with backlight followed by an automatic
return to Gemian; read-only recovery again reported `wdt_by_pass_pwk`, with no
pstore record and only the tiny mrdump header in `/proc/last_kmsg`. Its runtime
record is 'results/runtime-candidate-as-attempt-6-20260726.txt'. Attempts 5 and
6 therefore close the PAGE_CON read-modify-write hypothesis across both regmap
and explicit-transfer implementations. This motivated the bounded attempt-7
test below, retaining the known-good write-only selector behavior from 0107
while using explicit vendor-shaped reads only for the page-2 identity registers.

Candidate AS attempt 7 implements that test: PAGE_CON selector bytes remain
write-only, while page-2 identity registers use the explicit vendor-shaped read
transfer. Package, DT, LK-container, boot, and compiled-handoff validation all
passed. It is installed on boot2 with a full readback; records are in
'results/build-candidate-as-attempt-7-20260726.txt' and
'results/install-candidate-as-attempt-7-boot2-20260726.txt'. A72 remains
blacklisted and no CPU power-on request is present.
The owner observed that this candidate reached a delayed but functional
console, crossing the earlier pre-console watchdog boundary. Its codename is
`Kepler`; future candidates will use a single memorable space/science/cartoons
codename alongside their exact technical identity and checksums.
The development shell is the initramfs's direct USB Ethernet service at
`10.15.19.82:2323` (BusyBox `nc`, no authentication, USB-link-only), not SSH.
The first read-only shell probe reported `usb0` carrier up, UDC configured, and
CPUs `0-7` online.

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
943018afd04bda3b333e644ceb5d507f97af1386c5f023e3bcd60d0d9ffd74ce, perform one
bounded full-partition write with full readback verification, and never reboot
or change slot selection.

The USB banner may continue to identify the inherited initramfs baseline; the
DA9214 probe and handoff markers are the attributable Candidate AS evidence.
