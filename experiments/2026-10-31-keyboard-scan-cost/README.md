# Experiment: keyboard driver gaps, scan cost and ghosting

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-31-keyboard-scan-cost` |
| Status | `running`: station 13b capture `a930528e…` showed two keys in one row cancel (`drive-inactive-cols`); fix 0374 built, not yet booted. The earlier ghost-filter confirmation is withdrawn |
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
3. (Added after the station 13b capture.) With 0374, two keys in one matrix
   row are both reported, for example Left Shift+Z and Ctrl+Alt.

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
| **Same-row keys** (found on the device, not in the research) | Vendor scan drives inactive columns high | `drive-inactive-cols` (from 0076) drives every unscanned column high | **Observed** on station 13b: Left Shift+Z lost both keys; Ctrl+Alt the same. **Fixed by 0374**, not yet booted |
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

The Buildbox build with 0374, from commit `3aeb8d9b`, also passed. It applied
848 patches and the package passed validation:

| Field | Value |
| --- | --- |
| Package | `linux-7.1.3-gemini-a1c5a72405a6caf2249d40408e6b254cb4be5e099e623978057492d819633f65` |
| `patchset_sha256` | `aaaa46a03c239f544e4b80aa98546e7035ecd3b1dbc1ab27db6e736418cfc38c` |
| `config_sha256` | `d3077e5390307842b1dec29f9ca64cab8bd2b069d0f0ec2433cd36ddb29f8924` |
| `image_gzip_sha256` | `3af32c3ce0011332cce286a056e97afacb45e2c38ff3610b74e2ad51a6375418` |

Not done for either package: fetching it, assembling a boot2 image and the
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

**Typing checks on the same boot.** The owner typed while the device
session dumped `/dev/input/event1`. It read the device with
`od -An -v -tx1 -w24` and decoded `struct input_event` on the host. The
busybox `hexdump` format in this record's message captured nothing. `od`
block-buffers, so the tail of a capture is lost when the reader is killed.
Results are given as keycode (`MSC_SCAN`):

| Step | Result |
| --- | --- |
| B5, typing | Seven letters each reported once. Key 36 (J) was held from 283.98 to 287.58 s with steady autorepeat. Shift+Fn+1 reported 125 (35), 42 (30) and 2 (0). The console text was not compared |
| B6a, Ctrl+Left Shift+N | 29 (38) and 42 (30) held, and Shift repeated and was pressed again afterwards. Neither `KEY_N` nor scan 34 (M) was reported. **Reinterpreted below:** Shift and N share row 3 |
| B6b, Ctrl+Alt+7 | **Not exercised.** The first attempt pressed 7 alone, then Alt. In the second, 7 went down at 574.96 s after Ctrl had been released, and the rest of the capture was lost to buffering |
| B6c, Ctrl+Right Shift+V | 29 (38) and 54 (43) held, and 47 (28, V) was reported |
| B7, unconnected | Scans seen: 0, 6, 8, 14, 16, 17, 19, 22, 28, 30, 33, 35, 38, 43, 56. None in 59–62 |

All observed scan codes match the map: (row << 3) + column. Step 1 (the
baseline) did not run. No station 12 interrupt count exists, so the scan cost
has no measured "before".

**Ctrl+Alt+7 and same-row keys, station 13b.** Afterwards the owner reported
that Ctrl+Alt+7 printed "7" on the console. Station 13b, boot
`a930528e-cf16-4afd-915e-792018a67e02`, carries the same keyboard patches.
With the device free, `/dev/input/event1` was captured read-only through
`dd bs=24`, which writes every event as it arrives, while the owner typed.
The decoded capture is in
[`results/same-row-capture-a930528e.txt`](results/same-row-capture-a930528e.txt).

| Sequence typed | Events reported |
| --- | --- |
| Hold Ctrl, hold Alt, hold 7, release Ctrl, then 7 and Alt | Ctrl down at 294.63 s and **up at 295.09 s while still held**, as Alt went down. 7 down at 295.73 s with no modifier. Alt down at 297.75 s, once Ctrl was released |
| Ctrl+Alt+7, other orders | 7 alone. Ctrl alone. Alt and 7 in the same scan. Ctrl and Alt were never reported held together |
| Hold Left Shift, tap Z | Shift down at 545.13 s, **up at 545.75 s** as Z went down, down again at 546.11 s. Z was never reported |
| Hold Right Shift, tap Z | Right Shift, then Z down and up, then Right Shift up |
| Hold Left Shift, tap Q | Shift, then Q down and up, then Shift up |

In the Linux VT map, keycode 8 gives "7" plain, `^_` with Ctrl, ESC 7 with Alt
and nothing with Ctrl+Alt. The default kernel tables are kept for those
states. A complete Ctrl+Alt+7 therefore prints nothing, filter or not. The
"7" on the console was the bare 7 in the first row.

## Analysis

The 876 interrupts a second are consistent with the code-derived 21
transfers per scan, at one I2C5 interrupt per transfer:

- Polling re-arms `poll-interval` after each scan ends, so the scan period
  is the scan time plus 20–24 ms. At the default `HZ=250`, 20 ms is
  5 jiffies, rounded up to the next tick.
- 876 / 21 gives about 41.7 scans a second, or a period of about 24 ms.
  That fits a scan of a few milliseconds plus the re-arm delay.

This is consistency, not proof for the scan cost. One interrupt per transfer is assumed, not
measured, and nothing else on I2C5 was ruled out. Without a measured
baseline, the size of the reduction from the old code (84 transfers per
scan, about 2400 a second at a longer period) remains an inference. It has
no measurement on this unit.

**Same-row cancellation.** Every lost key pairs with another pressed key in
the same matrix row and a different column: Ctrl (4,6) with Alt (4,1), and
Left Shift (3,6) with Z (3,0). Pairs in different rows work, such as Right
Shift (5,3)+Z and Left Shift+Q (1,5). Ctrl+Alt alone is no ghost-filter
rectangle, so the filter cannot explain it.

The likely mechanism is inferred, not measured. `drive-inactive-cols` drives
every unscanned column high while the scanned column is low. Two pressed
keys in one row then join a low column to a high one through the row. The
row settles between the two levels and reads high, as released, whichever of
the two columns is scanned. The fault is in the board description from
patch 0076. It predates 0362–0366, which do not change the column levels
during a scan.

**The B6a ghost conclusion is withdrawn.** Left Shift and N also share
row 3, and B6a showed Shift dropping and returning, so the missing N fits
the same cancellation. Driven-high columns also block the path that would
make a phantom: the fourth corner is reached through a column that is
driven high. On station 13 the ghost filter therefore probably never
triggered. Whether the matrix ghosts is open again. The vendor comment
still says it does.

**Fix, 0374.** Drop `drive-inactive-cols`, so the scan turns inactive
columns into inputs. A pressed key then only connects its row to the one
driven column, and two keys in one row read correctly. Real ghosting becomes
possible, which is the case 0364–0366 filter. The cost is two more AW9523
writes per column (direction changes), about 35 transfers per scan instead
of 21.

## Conclusion

- **Same-row fault: confirmed** on the named unit, station 13b boot
  `a930528e…`. With `drive-inactive-cols`, Left Shift+Z and Ctrl+Alt lose
  both keys. 0374 is the candidate fix, built but not yet booted.
- **Hypothesis 2: inconclusive (corrected).** It was first recorded as
  confirmed from B6a. Same-row cancellation explains the missing N, so the
  filter was never shown to act. 0364–0366 stay, because they are needed once
  0374 makes ghosting possible.
- **Hypothesis 1: inconclusive.** The candidate binds, polls without read
  errors and types normally, with autorepeat. Its I2C5 rate of about 876
  interrupts a second fits 21 transfers per scan. There is no measured
  baseline, so the reduction itself is inferred. 0362 and 0363 stay, because
  no regression was seen.
- No unconnected position reported a scan.

## Follow-up

- **0374 test (predeclared).** Boot a station kernel with 0374 and capture
  `/dev/input/event1` with `dd bs=24`.
  - Left Shift+Z and Ctrl+Alt+7: expect both modifiers and Z or 7 reported.
    Ctrl+Alt+7 then prints nothing, because its VT entry is empty.
  - Ctrl+Left Shift+N: expect N and M both absent (the filter drops the
    rectangle). If M is reported, the filter has failed. If N is reported
    with no M, the matrix does not ghost.
  - Typing, autorepeat and Fn+B/N as before. I2C5 rate: expect about 35/21
    of the current rate, at a slightly longer period.
  - If typing regresses, return to station 13b.

- If a measured scan-cost reduction is ever needed, boot a station kernel
  without 0362–0363 and repeat step A3.
- Event dumps on the station need an unbuffered reader. Plain `od` loses the
  tail of a killed capture.
