# Experiment: AW9523 interrupt mode for the keyboard (EINT10)

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-31-keyboard-eint10` |
| Status | `running`: station 15 failed B3 (EINT10 never fired); diagnosed as the EINT pad mode; fix 0377–0378 built, not yet booted |
| Subsystem | input: `gpio-matrix-keypad` row interrupts through `pinctrl-aw9523` and MT6797 EINT10 |
| Device variant | named Gemini PDA (MT6797X), boot2 station |
| Date(s) | 2026-10-31 |
| Investigator(s) | project custodian |
| Tracking issue | none |

## Question or hypothesis

The owner asked whether the keyboard driver could use interrupts instead of
polling. The station polls the matrix every 20 ms, about 35 I2C transfers per
scan. Station 14 measured 1428 I2C5 interrupts a second at idle
([scan-cost record](../2026-10-31-keyboard-scan-cost/README.md)).

The vendor kernel uses the AW9523 INT output, GPIO87 as EINT10, level low
([keyboard research](../../docs/hardware/keyboard.md#interrupt-chain)). It has
never run on mainline. Candidate Q in
[2026-07-18](../2026-07-18-keyboard-shell-diagnostic/README.md) described it,
lost the console before any keyboard gate, and polling replaced it. No
real-pad EINT has yet fired on mainline MT6797. The lid's EINT5 (dual edge)
never did, while the PMIC's virtual EINT176 works
([C1 analysis](../2026-10-04-gemini-c1-preparation/README.md#eint5-after-c1-4-offline)).

**Hypotheses.**
1. Restoring the INT description lets `pinctrl-aw9523` request EINT10 without
   a storm. Every pin interrupt stays masked while the matrix polls, so
   EINT10 stays at zero.
2. In row interrupt mode, EINT10 fires on key changes and stays quiet at
   idle. The keyboard then types as in polling mode, with I2C5 near zero at
   idle.

Level-low EINT10 also tests a real-pad EINT without EINT5's dual-edge
emulation. A negative result narrows that problem too.

## Design

- **[0375](../../patches/proposals/0375-Input-matrix_keypad-add-an-experiment-only-scan-mode.patch)**
  (experiment only) adds a writable `matrix_keypad.poll_override`, read at
  probe: 0 keeps the DT's 20 ms polling, below 0 forces row interrupts.
  Unbinding and binding `keyboard-matrix` switches modes on one boot. A
  failed interrupt mode therefore returns to polling over SSH, with no
  reboot and no boot2 change.
- **[0376](../../patches/proposals/0376-arm64-dts-mediatek-gemini-station-describe-the-keybo.patch)**
  restores the AW9523 `interrupt-parent`, `interrupts = <10 IRQ_TYPE_LEVEL_LOW>`,
  `interrupt-controller` and `#interrupt-cells` on the station only. The
  Wi-Fi service board still deletes them.
- **Modules.** The owner prefers modules so iterations avoid reboots. The
  keyboard is the console, so `matrix_keypad` and `pinctrl-aw9523` stay built
  in, because a failed module load at boot would take the console. The
  runtime override gives the same no-reboot iteration for the scan mode.
- **What can fail at boot.** If `pinctrl-aw9523` cannot request EINT10, its
  probe fails and the keyboard is absent. Polling would not save it. SSH
  stays. That is the main risk this candidate adds over station 14.

## Build

The Buildbox modules build from commit `712b5d97` passed. It applied 850
patches and the package passed validation:

| Field | Value |
| --- | --- |
| Job | `712b5d97de31fb76d5b3671039edf0b1d2d54aa9-mt6797-a53-station-m1` |
| Package | `linux-7.1.3-gemini-6d6a06d938c159e44f6fa3f73ef4f0364120872ff1ab3dfa2923bf485a463da4` |
| `patchset_sha256` | `ec5825ac4eb958e24c4dbcefb6593bde3ffae202c723fe3b4764504e5fe2f668` |
| `config_sha256` | `d3077e5390307842b1dec29f9ca64cab8bd2b069d0f0ec2433cd36ddb29f8924` (same as station 14) |
| `image_gzip_sha256` | `827cfb41431e880fb8f73dad8cb2af7128eb19eb32494f84ebfaaa50cc6c3c0b` |

The VM compile test was clean: `W=1` on `matrix_keypad.o`, checkpatch on
both patches, and `CHECK_DTBS` on the station DTB with no AW9523 finding.
The DTB has `interrupts = <10 8>` on `gpio-expander@5b`.

## Safety assessment

All state changes are a boot2 flash under the standing rules and two sysfs
writes on the running station. There are no register writes outside the
drivers, and no radio or calibration actions. A storm on EINT10 would keep the
AW9523 interrupt thread reading I2C5. That costs CPU and bus time, not
hardware. Return to station 14 if the console or SSH degrades. The owner
types; boot2 selection stays physical.

## Procedure (predeclared)

Use the station 14 capture method: `dd if=/dev/input/event1 bs=24` over SSH.
Find the event node again after each rebind. The EINT10 line in
`/proc/interrupts` is named `5-005b`, the AW9523 I2C device. The row lines
are named `matrix-keypad`.

**A. Boot, polling (default).**
1. Verify the boot identity. `dmesg`: AW9523 bound, `polling mode, interval
   20 ms`, no IRQ request error. `/proc/device-tree/i2c@1101c000/gpio-expander@5b/interrupts`
   is present.
2. Read the `5-005b` and `1101c000.i2c` counts, wait 10 s idle, then read
   them again. Do this 3 times.
   - Expect `5-005b` +0 and I2C5 about 1430 a second, as on station 14.
   - **Stop** if `5-005b` rises more than 100 a second: the line is stuck
     asserted. Return to station 14.
3. The owner types a short line. The console works and `5-005b` does not
   change.

**B. Row interrupt mode.**
1. Switch modes:
   ```sh
   echo -1 > /sys/module/matrix_keypad/parameters/poll_override
   echo keyboard-matrix > /sys/bus/platform/drivers/matrix-keypad/unbind
   echo keyboard-matrix > /sys/bus/platform/drivers/matrix-keypad/bind
   killall lid-guard
   ```
   `lid-guard` still holds the removed device; init respawns it on the new
   one. Expect `dmesg` to say `row interrupt mode` and `/proc/interrupts` to
   list 8 `matrix-keypad` lines.
2. Idle 10 s, 3 times. Expect `5-005b` +0 and I2C5 under 10 a second.
3. The owner presses and releases one key (A) 5 times, slowly. Expect
   `5-005b` and at least one `matrix-keypad` row count to rise with each
   change, and 5 A press/release pairs in the capture.
4. Then the station 14 checks:
   - a typed sentence and a 2 s held key (autorepeat);
   - Left Shift+Z and Ctrl+Alt held together;
   - Fn+B/Fn+N;
   - a lid close and open: `lid-guard` inhibit stops the keypad, and reopening
     restores it.
   Then repeat B2.

**Decisions.**
- A fails to bind or loses the console: EINT10's description breaks probe.
  Return to station 14. The next step is a probe that cannot fail the
  provider, not a retry.
- A2 storm: the INT line is low at idle (pull or mux). Return to station 14.
- B3, no `5-005b` change and no key events: EINT10 does not deliver. That is
  the same class as EINT5. Switch back with `poll_override=0`, unbind, bind
  and `killall lid-guard`, and keep polling. Record it against the EINT5
  register-snapshot plan.
- B3 shows `5-005b` changes but no `matrix-keypad` rows: delivery works and
  the nested dispatch fails. Switch back and keep polling.
- B passes: interrupt mode is viable. A later candidate drops
  `poll-interval` from the station DT, and 0375 goes.

## Observations

**Station 15, boot `64f8483d-8bee-4383-9f7b-cfe3d6fb2d2f`.** Built at
`712b5d97`: Image.gz `827cfb41…`, DTB `591aca1b…`, boot2 `9bdf9e98…`, and the
same RAM root as station 14. The device session ran the procedure with the
owner. Raw files are retained privately with its station 15 evidence. The
EINT10 line is named `1-005b`, because the AW9523 is on Linux I2C bus 1, not
`5-005b` as this record predicted.

| Step | Result |
| --- | --- |
| A1 | The DT node carries the interrupt properties. AW9523 bound, `polling mode, interval 20 ms`, with no IRQ request error. `/proc/interrupts`: `25: mt-eint 10 Level 1-005b`. gpiolib warned once: `/i2c@1101c000/gpio-expander@5b: Ignoring 3 default trigger` (`gpiolib.c:2217`), from `aw9523_probe` |
| A2 | Idle: `1-005b` +0. I2C5 16710, 31130, 45480 and 59993 at 10 s steps, about 1440 a second |
| A3 | The owner typed a line and the console worked. `1-005b` stayed 0 |
| B1 | `row interrupt mode`, as `input2` on `event1`. 8 lines `aw9523 0..7 Edge matrix-keypad` (IRQs 218–225). `lid-guard` restarted |
| B2 | Idle 30 s: I2C5 constant at 2520349, `1-005b` and the row IRQs 0 |
| B3/B4 | **Fail.** The owner typed the full list and nothing appeared. `1-005b` and all 8 row IRQs stayed 0. I2C5 +65 in total. The `dd` capture was empty. The lid close and open were seen by `lid-guard` |
| Chip state (after typing, `i2cget -f`) | IN0 `0xff`, IN1 `0x80`, OUT1 `0x80` (columns 0–6 driven low), CFG0 `0xff` (rows input), CFG1 `0x80`, INT0 `0x00` (row interrupts enabled), INT1 `0xff`, GCR `0x00`. Reading IN0 clears any pending latch, so a latch could not be seen |
| GPIO87 (debugfs) | `pin 87 (GPIO87): 1-005b (GPIO UNCLAIMED) function func1 group GPIO87`. Pins line `087: 0001-524-524-52400`: **mode 0**, input, data in 1. gpiolib: `gpio-87 (|interrupt) in hi IRQ` |
| Restore | `poll_override=0`, unbind, bind and `killall lid-guard` gave `polling mode, interval 20 ms` and about 1445 I2C5 interrupts a second |

## Analysis

The expander was armed: row interrupts were enabled and the columns driven
low, so a key press pulls a row low and should latch INT. EINT10 never
counted. The debugfs mode explains it. The pinctrl state selected func1
(EINT10, mux mode 1), but the pad read back in **mode 0** (GPIO).

Patch 0005 gives every EINT-capable MT6797 pin `MTK_EINT_FUNCTION(0, n)`.
When an EINT is requested, `mtk_xt_set_gpio_as_eint()` writes that `eint_m`
into the pad mode. That replaces the DT's EINT10 function with GPIO, so the
pad no longer reaches the EINT block. 17 pads, GPIO61–68 and GPIO85–93,
list a dedicated `EINT0`–`EINT16` function at mode 1. The lid's GPIO66 (EINT5)
is one of them, which explains why its level followed the lid as a GPIO but
EINT5 never fired. The PMIC's EINT176 is virtual, so the pad write is skipped,
which is why it works.

This is inferred from the table, the readback and the two failures. Whether
the INT pin went low during a press was not sampled.

**Fix candidate.**
- [0377](../../patches/proposals/0377-pinctrl-mediatek-mt6797-use-the-EINT-mux-mode-on-ded.patch)
  sets `eint_m = 1` for those 17 pads. The other 155 lines keep mode 0
  until their routing is known.
- [0378](../../patches/proposals/0378-pinctrl-aw9523-do-not-set-a-default-IRQ-trigger.patch)
  removes the gpiolib warning by leaving the AW9523 default trigger as
  `IRQ_TYPE_NONE`.

**Station 16 test (predeclared).** Run steps A and B again, with `1-005b` as
the EINT10 line, plus:
- **A1:** the debugfs pins line for 087 starts with mode **1**, and no
  `Ignoring 3 default trigger` warning appears.
- **B3:** `1-005b` and row IRQs count on each press and release, and 5 A
  pairs appear in the capture.
- **Discriminator if B3 still fails:** with the keyboard in interrupt mode,
  the owner holds one key. Read `gpio-87` in debugfs before any AW9523
  register read: the latch is not cleared until IN0 is read.
  - `lo` means INT reaches the pad and the EINT block does not see it.
  - `hi` means the expander does not assert INT, or INT is wired elsewhere.

## Conclusion

Hypothesis 1 confirmed on station 15: EINT10 is requested without a storm
and stays at zero while polling. Hypothesis 2 failed on station 15. The
leading explanation is the pad-mode bug in 0005, and 0377 is its candidate
fix, not yet booted.
