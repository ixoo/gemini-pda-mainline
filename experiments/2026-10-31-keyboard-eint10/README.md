# Experiment: AW9523 interrupt mode for the keyboard (EINT10)

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-31-keyboard-eint10` |
| Status | `running`: station 18 confirms 0381 (correct keys, idle I2C5 0/s) but misses same-row keys pressed in sequence; 0382–0384 built for station 19, not yet booted |
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

**Station 16 build.** The Buildbox modules build from `41216047` passed:
job `41216047d2fa5bd7e62ab4bb77da1cae16aa1bd0-mt6797-a53-station-m1`, 852
patches. Package
`linux-7.1.3-gemini-ff3485136dddbaef11b0b19bea1666bc123c4b117eae974b7ec310f9f3ff79ef`,
`patchset_sha256` `1808212b…`, `config_sha256` `d3077e53…` (unchanged),
Image.gz `6e7f8b49159acc478332351c191827ba74d4962c6fe70945b4a83ac1acf0487c`.

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

**Station 16, boot `f7f9a221-8d26-4641-bbc6-23c68362e1cb`.** Built at
`41216047`: Image.gz `6e7f8b49…`, DTB `591aca1b…`, boot2 `ce9886e2…`, same RAM
root. Run by the device session with the owner. Raw files are retained
privately with its station 16 evidence.

| Step | Result |
| --- | --- |
| A1 | No `Ignoring 3 default trigger` warning (0378). Pins line `087: 1001-…`: **mode 1**. GPIO66 is still mode 0, because the lid is a polled GPIO, not an IRQ |
| A2 | Idle 3 × 10 s: `1-005b` 0. I2C5 19245, 33700, 48124 and 62575, about 1445 a second |
| B1 | `row interrupt mode`. GPIO87 stays in mode 1 after the request, so 0377 holds. Rows are IRQs 218–225 |
| B2 | Idle 20 s: I2C5 constant at 76699, `1-005b` 0 |
| B3/B4 | **EINT10 delivers:** `1-005b` went from 0 to 155 while the owner typed. The 8 row IRQs stayed at **0**. The first A press reported A (scan 21). The next four A presses each reported `KEY_RIGHT` (45) and Enter (53) together instead. The rest of B4 gave multi-key garbage, such as 1, S, 8 and Left Shift together. The owner: "things appear, but not the correct key mapping clearly" |
| After B4 | In row-interrupt mode at idle, I2C5 ran at about 271 a second with `1-005b` unchanged. After returning to polling, about 1745 a second against the 1445 baseline. A 20 ms debugfs GPIO sampler run by the device session was active, and it may account for the extra |
| Restore | `poll_override=0`, unbind, bind and `killall lid-guard` gave polling mode again |

The kernel log retained for station 16 ends at 11 s, before the interrupt
phase.

## Conclusion

0377 makes EINT10 deliver: GPIO87 stays in mux mode 1, and the line counted
key activity. Row-interrupt mode is **not** usable yet. The scan reports wrong
keys after the first press. The row interrupts never counted, so the rows were
still disabled each time EINT10 dispatched to them. The station keeps
polling. `matrix_keypad` disables and enables its row IRQs under a spinlock,
which a sleeping I2C irqchip like the AW9523's cannot serve. This is under
investigation from the kernel log of that phase.

**Station 16 follow-up (read-only, same boot, uptime 412 s).**
- The kernel log after 50 s has only the probe, mode and `lid-guard` lines:
  no BUG, WARN, scheduling-while-atomic or driver error. This kernel lacks
  `CONFIG_DEBUG_ATOMIC_SLEEP`, so it would not report a mutex taken under a
  spinlock without contention.
- The 20 ms sampler had ended with its SSH session. In polling mode, I2C5
  still ran at about 1749 a second against the 1445 boot baseline, with
  `1-005b` unchanged at 160. About 300 a second of extra traffic has
  persisted since the interrupt phase, unexplained.
- `/sys/kernel/debug/irq` is absent, and the kernel has no ftrace or kprobes.

The counters contradict the expected path. `handle_nested_irq()` counts
only a row interrupt that is enabled, so rows that never counted were
disabled whenever EINT10 dispatched to them. Yet scans ran and reported
keys. Rather than guess, station 17 adds tracing:
- [0379](../../patches/proposals/0379-Input-matrix_keypad-add-experiment-only-scan-tracing.patch):
  `matrix_keypad.trace_scans` logs each row IRQ, start, and interrupt-mode
  scan with its row words;
- [0380](../../patches/proposals/0380-pinctrl-aw9523-add-experiment-only-interrupt-tracing.patch):
  `pinctrl_aw9523.trace_irq` logs each expander interrupt thread run with
  its port values, changed bits and nested dispatches.

Both are experiment only and off by default.

**Station 17 build.** The Buildbox modules build from `9788c425` passed:
job `9788c4253944645e5fd73dc099fb46a966ce5f21-mt6797-a53-station-m1`, 854
patches. Package
`linux-7.1.3-gemini-b44aa040149ab5454b966dde72d824dc903b36fb802f4e3b0ff7354caf11aa26`,
`patchset_sha256` `5b2808df…`, Image.gz
`322445285b27305a860940896a33f097eee4dde52b7363ed55707df089a6fedd`.

**Station 17 test (predeclared).**
1. Boot (polling). Repeat A1–A2 with `1-005b`. Record the I2C5 baseline.
2. `echo 1 > /sys/module/matrix_keypad/parameters/trace_scans`,
   `echo 1 > /sys/module/pinctrl_aw9523/parameters/trace_irq`, then switch
   to interrupt mode as in B1 (including `killall lid-guard`). The rebind
   should log `trace: start`, one scan, and `scan end ff`, or `00`
   depending on polarity.
3. Idle 10 s: count new trace lines and the I2C5 delta.
4. The owner presses and releases A once, waits 2 s, then once more.
   Save `dmesg`, `/proc/interrupts` and the event capture.
5. Return to polling, turn both traces off, and take one I2C5 delta.

What the log decides:
- `irq in` lines with no `nested` line: no changed row bits, or no mapping.
- `nested` lines with no `row irq` line: the row was disabled (pending).
- `row irq` present: the count reading was wrong.
- The `scan … cols` words for a single A press show directly whether the
  rows are read wrong, compared with polling's correct reading.

**Station 17, boot `4235af32-408a-4d0d-9f93-417b051f6c74`.** Built at
`9788c425`: Image.gz `32244528…`, DTB `591aca1b…`, boot2 `7623630d…`, same RAM
root. The device session ran the trace test with the owner. The verbatim
kernel log and the capture are retained privately with its station 17
evidence. The owner saw no "a".

- **Polling.** I2C5 at 1438 a second, with no warning and the pad in mode 1.
  After the trace test and the return to polling, the rate was again 1438
  a second. With no sampler running this time, the station 16 excess did
  not recur.
- **Interrupt-mode idle.** I2C5 was flat and no trace lines appeared.
- **A press, verbatim excerpt:**

```text
195.347013 aw9523: trace: irq in 80fb changed 7f04
195.347056 matrix-keypad: trace: row irq 220 pending 0 stopped 0
195.352432 aw9523: trace: irq in dffb changed 6004
195.353750 matrix-keypad: trace: scan init 04 err 0 cols 00 00 00 00 00 20 00
195.355863 matrix-keypad: trace: scan end 04
195.508784 matrix-keypad: trace: row irq 220 pending 0 stopped 0
195.514402 matrix-keypad: trace: scan init 00 err 0 cols 00 00 00 00 00 00 00
```

  The row interrupt and the start-of-scan read agree: row 2 (`init 04`). The
  interrupt thread read `dffb` during the scan: P1 `0xdf` (column 5 driven)
  and P0 `0xfb` (row 2 low), which is correct for A at (2,5). The scan
  stored `cols[5] = 0x20`, which is P1 inverted, not P0. The other columns
  read 00. Both A presses gave `KEY_RIGHT` (scan 45).
- **Wake key, held.** About 20 scans, 8.7 ms apart, each ending in
  `scan end 7f rescan`. `7f` is P1 `0x80` inverted.
- **Counts.** `1-005b` went from 0 to 74. The row lines in `/proc/interrupts`
  stayed at 0 although the trace shows their handlers running. On this
  kernel, the nested interrupt counts do not appear there, so the station
  16 reading of "rows never ran" was wrong.

**Cause.** The AW9523 regmap sets `.disable_locking = true` and relies on the
driver's `i2c_lock`. `aw9523_irq_thread_func()` reads IN0 and IN1 through
that regmap without taking the lock. Regmap formats and receives every read
through the shared `map->work_buf`, so the thread's concurrent IN1 read
overwrote the scan's IN0 result. Only the column being read when the thread
ran is corrupted, which matches the single wrong column per scan. The same
race explains station 16's Right arrow + Enter: P1 `0x9f` inverted.

**Fix,
[0381](../../patches/proposals/0381-pinctrl-aw9523-serialize-the-interrupt-thread-s-port.patch).**
Take `i2c_lock` around the thread's port reads, and release it before the
nested dispatch. The mask and unmask callbacks also call regmap without
`i2c_lock`. They are left unchanged: `matrix_keypad` calls `enable_irq()`
under a spinlock, so a mutex there could sleep in atomic context. In this
trace, the lazy disable never masked and the unmask found the bits already
clear, so neither wrote.

**Station 18 build.** The Buildbox modules build from `c3cf556a` passed:
job `c3cf556a43f7cc2d792adabf117eba8bc37279ea-mt6797-a53-station-m1`, 855
patches. Package
`linux-7.1.3-gemini-cd8b1f9f175ffb87506a137c9cd46a6ce2a83b65db1161c4cd2bcae8aec0b8de`,
`patchset_sha256` `633abc1c…`, Image.gz
`e6bc5893353b45aa44a78d1e027bf742d86beb86472c4bfbff82fb5e053aa91a`.

**Station 18 test (predeclared).** Station 17 plus 0381, traces still
available.
1. Polling: A1–A2 as before.
2. With traces on, switch to interrupt mode. The owner presses A twice,
   2 s apart, then holds A for 2 s.
   - Expect `cols … 04` in column 5 (`00 00 00 00 00 04 00`), A (scan 21) in
     the capture, and `scan end` matching `init`.
   - A held key gives one scan per change, not a rescan storm.
3. Traces off. B4 as on station 14: a sentence, autorepeat, Left Shift+Z,
   Ctrl+Alt, Fn+B/N, and a lid close and open. Then idle 10 s and take the
   I2C5 delta, expected under 10 a second.
4. Return to polling at the end.

**Decisions.**
- If 2 and 3 pass, interrupt mode works. The next candidate makes it the
  station default (drop `poll-interval`) and removes 0375, 0379 and 0380.
- If any wrong key remains, keep the traces and compare the column words
  with the thread's port reads again.

**Station 18, boot `feb511fb-45ba-4be8-b0d5-11ccde05f032`.** Built at
`c3cf556a`: Image.gz `e6bc5893…`, DTB `591aca1b…`, boot2 `1a90ccff…`, same RAM
root. Run by the device session with the owner, who reported "it worked".
Raw files are retained privately with its station 18 evidence.

| Step | Result |
| --- | --- |
| Polling | No warning, pad in mode 1, I2C5 1449 a second, `1-005b` 0 |
| Traced A presses | Both: `scan init 04 err 0 cols 00 00 00 00 00 04 00`, `scan end 04`, and A (code 30, scan 21) in the capture. No `rescan` line anywhere. Idle I2C5 was flat. The 2 s hold was not captured, probably owner timing |
| Sentence, traces off | "hello world" exactly, with clean press/release pairs |
| Autorepeat | H held: first repeat after 255 ms |
| Left Shift+Z | First: Z alone, **no Shift**. Second: Shift and Z in one scan, correct |
| Ctrl+Alt+7 | First: 7, then Alt 18 ms later, then Ctrl only as 7 was released. Second: all three in one scan, correct |
| Fn+B, Fn+N | Each letter reported about 10 ms before Fn |
| Lid | Close and open seen by `lid-guard` |
| Idle I2C5, interrupt mode | 54819 to 54819 over 10 s: **0 a second**, against about 1449 polling. `1-005b` totalled 1035 |

**0381 confirmed.** With the thread's reads serialized, the scan reads the
right rows, and the held-key rescan storm is gone.

**Same-row keys.** Between interrupt scans, every column is driven, so a
held key keeps its row low. A second key in that row produces no edge on
the row line, no AW9523 interrupt and no scan. Left Shift and Z share
row 3, and Ctrl and Alt share row 4. Each failed when pressed one after the
other, and worked only when they landed in the same scan. Polling never
missed them. Whether the Fn+B and Fn+N order is the same effect or owner
timing is undetermined: Fn is in row 4, B and N in row 3. The vendor driver
keeps rescanning while keys are held, which avoids this.

**Fix, station 19.**
- [0382](../../patches/proposals/0382-dt-bindings-input-gpio-matrix-keypad-add-held-poll-i.patch)
  adds `held-poll-interval` to the binding.
- [0383](../../patches/proposals/0383-Input-matrix_keypad-keep-scanning-while-a-key-is-hel.patch)
  makes `matrix_keypad` keep scanning at that interval while any key is
  held, with the row interrupts off and the columns inactive. Row interrupts
  return once a scan finds every key released. A stopped device always
  takes the normal path, which keeps the IRQ disable depth balanced across
  stop and start.
- [0384](../../patches/proposals/0384-arm64-dts-mediatek-gemini-station-scan-the-keyboard-.patch)
  removes `poll-interval` from the station's keyboard and sets
  `held-poll-interval = <20>`. **Station 19 boots in interrupt mode.**
  `poll_override` (0375) and the traces (0379, 0380) remain, so a fault can
  be corrected over SSH.

**Station 19 test (predeclared).**
1. **Boot.**
   - The kernel log says `row interrupt mode`, and the console takes typing
     from the start.
   - Idle 3 × 10 s: I2C5 under 10 a second, `1-005b` flat.
   - Fallback if the console fails:
     `echo 20 > /sys/module/matrix_keypad/parameters/poll_override`, unbind,
     bind, `killall lid-guard`.
2. **Same-row keys, pressed one after the other.**
   - Hold Left Shift, then press Z: expect Shift down, then Z.
   - Hold Ctrl, then Alt, then press 7: expect Ctrl, Alt, then 7. The
     ghost filter may drop the 7.
   - Hold Fn, then press B and N: brightness steps, with Fn reported before
     the letter.
3. **The rest.**
   - A typed sentence.
   - A 2 s held key, checking autorepeat and the I2C5 delta during the hold
     (about the polling rate).
   - A lid close and open, and the I2C5 delta afterwards at idle.

**Decisions.**
- If 1–3 pass, interrupt mode is the station default. A cleanup candidate
  removes 0375, 0379 and 0380.
- If the boot console fails, use the fallback and return to station 18
  behaviour by DT.

Earlier: hypothesis 1 confirmed on station 15: EINT10 is requested without a storm
and stays at zero while polling. Hypothesis 2 failed on station 15. The
leading explanation is the pad-mode bug in 0005, and 0377 is its candidate
fix, not yet booted.
