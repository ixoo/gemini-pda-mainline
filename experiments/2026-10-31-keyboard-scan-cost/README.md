# Experiment: keyboard driver gaps, scan cost and ghosting

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-31-keyboard-scan-cost` |
| Status | `running`: station 13 boot `66b68797…` passed steps A1–A4; the typing steps have not run |
| Subsystem | input: `gpio-matrix-keypad` over the AW9523 expander on I2C5 |
| Device variant | named Gemini PDA (MT6797X), boot2 station |
| Date(s) | 2026-10-31 |
| Investigator(s) | project custodian |
| Tracking issue | none |

## Question or hypothesis

This record compares the [keyboard research](../../docs/hardware/keyboard.md),
including the [2026-10-31 vendor input research](../2026-10-31-gemini-keyboard-input/README.md),
with what the station kernel's keyboard driver does. Three gaps can be fixed
in the generic driver without new hardware evidence.

**Hypotheses.**
1. Patches 0362 and 0363 cut the I2C transfers in each 20 ms scan from about
   84 to 21, with no change to the reported keys.
2. With patches 0364–0366, Ctrl+Left Shift+N, Z, X, C and V report no phantom
   key. Combinations that do not ghost are unchanged.

## Gap list

The research and the code were compared on 2026-10-31. The station applies
`patches/series-a53-station` through proposal 0361, and its `station-dt.sh`
overlay leaves the keyboard nodes alone.

| Area | Research | Station kernel before this record | Gap and basis |
| --- | --- | --- | --- |
| Matrix and map | 8×7, 52 keys; the 4 unknown positions are P0_7 × P1_3–P1_6 and are unconnected | Same map; (7,3)–(7,6) omitted, so they emit only `MSC_SCAN` 59–62 | None |
| Meta/Fn | `KEY_LEFTMETA` at (4,3) on Gemini | Same. The VT map and `lid-guard` treat it as Fn | None |
| **Ghosting** | The vendor driver blocks ghosted positions. Its comment says Ctrl+Left Shift+N also shows M, and it has a z/x/c/v exception for Ctrl+Shift | No ghost filter. In the Linux map, LeftCtrl (4,6), LeftShift (3,6) and N (3,2) put the phantom at (4,2) = M, matching the vendor comment | **Source-documented and consistent with the map.** Phantom Fn, Alt, Space or comma on Ctrl+Shift+X/C/V/Z, and `2` on Ctrl+Alt+7 ([model](results/ghost-model.txt)). **Fixed by 0364–0366** |
| **Scan bus cost** | Not measured | Every scan reads each of 8 rows on its own (56 reads). It also turns all 7 columns off before the scan and on after it (14 writes), besides the 14 per-column writes | **Code-derived.** About 84 transfers per scan, about 4200 a second, polled continuously while the lid is open. **Fixed by 0362 and 0363** |
| **Read error** | — | A failed row read counts as a pressed row, so an I2C error types several phantom keys | **Code-derived**, never observed. **Fixed by 0362**: an incomplete scan is dropped and the last state is kept |
| Scan mode | Vendor: EINT10, then 1 ms fast and 10 ms slow rescans | 20 ms polling; parent IRQ removed in `wifi-service` | EINT10 is untested, and the hall EINT5 never fired on mainline. That is a separate IRQ-versus-polling experiment. Not changed here |
| Event order | Vendor reports presses before releases within a scan | One `input_sync` frame per scan, in column order | Not changed. The frame is atomic for evdev, but the order within it differs from the vendor's. No failure observed |
| Debounce | Vendor tuple is zero | Polling ignores `debounce-delay-ms`; the 20 ms sample spacing is the only filter | Not observed to fail. No change |
| Lid | Vendor ignores scans and releases all keys while the lid is closed | `lid-guard` inhibits the input device. The input core releases held keys and the driver stops polling | Equivalent in userspace. No change |
| Wake | The matrix is not a wake source; the PMIC power key is | Polling registers no wake | None |
| Backlight | None on Gemini | None | None |

## Changes

- [`0362`](../../patches/proposals/0362-Input-matrix_keypad-read-each-column-s-rows-with-one.patch)
  reads a column's rows with one `gpiod_get_array_value_cansleep()` call. The
  AW9523 rows share port 0, so `get_multiple()` reads them in one transfer
  (the direction register is cached). On a read error, the scan reports
  nothing and keeps the last key state.
- [`0363`](../../patches/proposals/0363-Input-matrix_keypad-leave-columns-inactive-between-p.patch)
  stops polling mode from driving every column active after each scan. Only
  row interrupts need that state. The cached AW9523 output register then turns
  the next scan's deactivation into no writes. Upstream, this belongs in 0084.
- [`0364`](../../patches/proposals/0364-dt-bindings-input-gpio-matrix-keypad-add-needs-ghost.patch)
  adds a boolean `needs-ghost-filter` to the binding. It follows
  `google,needs-ghost-filter`.
- [`0365`](../../patches/proposals/0365-Input-matrix_keypad-add-an-optional-ghost-filter.patch)
  drops a scan in which two columns share more than one pressed row, the
  policy of `cros_ec_keyb` and `tegra-kbc`. Positions without a key do not
  count, so Ctrl+Alt+K, whose phantom is the unconnected (7,6), still works.
- [`0366`](../../patches/proposals/0366-arm64-dts-mediatek-gemini-enable-the-keyboard-ghost-.patch)
  sets the property on the Gemini `keyboard-matrix` node.

Per-scan transfers, counted from the code:

| | Row reads | Column writes | Total |
| --- | --- | --- | --- |
| Before | 56 | 7 off + 14 per column + 7 on | 84 |
| 0362 | 7 | 28 | 35 |
| 0362 + 0363 | 7 | 14 | 21 |

Interrupt mode keeps its old column handling. Only 0362's array read and its
error path, and the opt-in ghost filter, apply there.

**Ghost-filter trade-off.** A dropped scan means the ambiguous key is lost,
not mistyped. Ctrl+Left Shift+Z/X/C/V/N therefore produce nothing until the
user releases a key. The vendor masks the phantoms for z/x/c/v instead. That
guesses which key is real, so it is left out of the generic driver. Ctrl+Right
Shift with the same letters does not ghost, because Right Shift is at (5,3).

## Provenance and environment

- Base: `v7.1.3` plus `patches/series-a53-station` through proposal 0361.
- Compile test: the native arm64 VM, in a separate worktree of the dev tree,
  with the station configuration (`CONFIG_KEYBOARD_MATRIX=y`,
  `CONFIG_PINCTRL_AW9523=y`).
  - `make W=1 drivers/input/keyboard/matrix_keypad.o` is clean after each
    driver patch.
  - `checkpatch.pl --no-signoff` passes all five patches.
  - `dt_binding_check` for `gpio-matrix-keypad.yaml` passes.
  - `CHECK_DTBS=y` for `mt6797-gemini-pda-station.dtb` reports no keyboard
    finding. Only the existing `usb@11271000` `ranges_format` warnings remain.
  - The built DTB carries `needs-ghost-filter` on `/keyboard-matrix`.
- [`ghost-model.py`](ghost-model.py) closes the pressed set over shared rows
  and columns, then applies the same column-pair test as 0365. Its
  [result](results/ghost-model.txt) is a model of the map, not a hardware
  observation.
- Buildbox: see [Build](#build).
- The patches carry no `Signed-off-by`. The owner must add a truthful one
  before any upstream submission.

## Build

The Buildbox build from commit `d71114b0` passed. It applied all 840
`series-a53-station` patches, including 0362–0366, and the package passed
validation:

| Field | Value |
| --- | --- |
| Profile | `mt6797-a53-station`, release `7.1.3-gemini-a53-station` |
| Package | `linux-7.1.3-gemini-3880bdeabaf9b4688e7e513e93a762bedfa0607126985d1790ef3f90e6ca31c8` |
| `patchset_sha256` | `8247cd8a89caf74dcbb0967ce459b7b4fc8dd0a6092a80bc5b2f76eca2ea8824` |
| `config_sha256` | `d9fcfee20d204c4d50291e55a0b75fdfb0da3b0f78d7f500a9a8c4b65a64b3e7` |
| `image_gzip_sha256` | `1c312e7c4c80a512c816924303702bf13850d7023f6683dca23cebe16b6eecc8` |

Not done: fetching the package, assembling a boot2 image and the
`station-dt.sh` DTB, flashing and booting. Each needs the device custodian,
and boot2 selection needs the owner.

## Safety assessment

The kernel change only affects how the matrix GPIOs are read and driven, and
which scans are reported. The pin configuration, map and polarity are
unchanged. A failure loses keyboard input. Key-only USB SSH and the boot2
recovery path stay available. The test is read-only apart from normal typing:
it reads `/proc/interrupts`, the kernel log and event dumps of the
`keyboard-matrix` device, and it needs the owner to type. Flashing boot2 and
the physical boot2 selection need the owner's approval, under the standing
boot2 installation rules in `AGENTS.md`.

## Procedure (predeclared)

1. **Baseline, current station kernel.** With the lid open and no key held,
   read the I2C5 (`1101c000.i2c`) count in `/proc/interrupts` twice, 10 s
   apart, three times. Record the rate.
2. **Candidate.** Install the package built from this record's commit on
   boot2, boot it and verify the boot identity. Confirm that `matrix-keypad`
   logs `polling mode, interval 20 ms` and that no `failed to read rows` lines
   appear. Repeat step 1.
3. **Typing.** The owner types a known line on the console, holds a letter
   for 2 s (autorepeat), then uses Shift+Fn+1 (F1), Ctrl+A, Alt+A and
   Fn+B/Fn+N (brightness). Expect the same results as the current station.
4. **Ghosting.** Run an event dump on the `keyboard-matrix` device over SSH.
   The owner holds LeftCtrl and LeftShift, then presses N. Repeat with Ctrl+Alt
   and 7, and with Ctrl+RightShift and V.
   - Before (current station): expect `MSC_SCAN` 34 (`KEY_M`) with N, and scan
     1 (`KEY_2`) with 7.
   - Candidate: expect neither key in the first two cases, and V reported in
     the third.
5. **Unconnected positions.** With the same dump, record any `MSC_SCAN` 59–62
   during the whole session. None are expected.

**Decisions.**
- Hypothesis 1 holds if the I2C5 interrupt rate drops by at least half and
  typing matches. 0362 and 0363 then stay in the station.
- Hypothesis 2 holds if step 4 shows the phantom before and none after, with
  the Right Shift case reported. If the current station shows no phantom, the
  unit has diodes or other isolation, and 0366 is dropped.
- If typing regresses, revert to the current station kernel. Bisect by
  dropping 0366, then 0363, before changing anything else.

## Observations

**Station 13, boot `66b68797-9d46-4f09-bd83-2e4a0aac9813`.** Built at
`dad24105` (846 patches, with 0362–0366 and the fuel-gauge proposals
0367–0372), on boot2 `61b1218e…`. The device session ran these read-only
checks and reported them to this record. The raw output is retained
privately with that session's station 13 evidence.

| Step | Result |
| --- | --- |
| A1, driver | The first probe deferred (`-517`) at 0.830 s. At 1.017 s, `keyboard-matrix` registered as `input1` and logged `polling mode, interval 20 ms`. There was no `failed to read rows` line, and `aw9523_driver_init` returned 0 |
| A2, DT | `/proc/device-tree/keyboard-matrix/needs-ghost-filter` is present |
| A3, I2C5 rate | `1101c000.i2c` (IRQ 216) read 30787, 39544, 48301 and 57058 at uptimes 36, 46, 56 and 66 s. That is +8757 per 10 s each time, about 876 interrupts a second, with the lid open and no key held |
| A4, node | `keyboard-matrix` is `/dev/input/event1`. `evtest` is absent and `hexdump` is present |

Steps 1 and 3–5 of the original procedure (the baseline, typing, ghosting
and unconnected positions) have not run. No station 12 interrupt count
exists, so step 1 has no measured "before".

## Analysis

The 876 interrupts a second are consistent with the code-derived 21
transfers per scan, at one I2C5 interrupt per transfer:

- Polling re-arms `poll-interval` after each scan ends, so the scan period
  is the scan time plus 20–24 ms. At the default `HZ=250`, 20 ms is
  5 jiffies, rounded up to the next tick.
- 876 / 21 gives about 41.7 scans a second, or a period of about 24 ms.
  That fits a scan of a few milliseconds plus the re-arm delay.

This is consistency, not proof. One interrupt per transfer is assumed, not
measured, and nothing else on I2C5 was ruled out. Without a measured
baseline, the size of the reduction from the old code (84 transfers per
scan, about 2400 a second at a longer period) remains an inference. It has
no measurement on this unit.

## Conclusion

Inconclusive. The candidate binds, polls at 20 ms, carries the ghost
filter and reports no read errors, at about 876 I2C5 interrupts a second.
Typing and the ghost-filter behaviour are still untested.
