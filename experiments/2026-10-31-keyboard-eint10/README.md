# Experiment: AW9523 interrupt mode for the keyboard (EINT10)

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-31-keyboard-eint10` |
| Status | `planned`: patches 0375–0376 built for the station; not yet booted |
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

None yet.

## Conclusion

Not run.
