# C1 attended boot protocol

Status: draft for the first C1 boot, 2026-10-05. No candidate is validated
and no device action has been taken under this protocol.

## Hypothesis and unique observation

The C1 kernel binds the MT6351 key child, the RTC and the hall gpio-keys
node on the A53 development system. The PMIC interrupt path delivers one
short power-key press and one RTC alarm, and GPIO66 reports one lid
close/open. PSCI power-off with the charger detached turns the device off.
The unique observation is the ten-word loader-inherited PMIC baseline plus
those four events, which no earlier boot measured.

## Candidate

Build `mt6797-a53-c1-compile` from a clean pushed commit on Buildbox, fetch
the validated package, and compose the candidate from the last booted A53
service candidate. Change only the kernel image, the board DTB and the
RAM-root release gate, and add [rtc-alarm.sh](rtc-alarm.sh) to the RAM root.
Keep the PSCI power-off path and the forced command line's `clk_ignore_unused`.
The command line has no `regulator_ignore_unused`, as in every earlier A53
boot; see the [correction](README.md#regulator-flag-correction-2026-10-05).
The RAM root and parent candidate are private and live outside Buildbox.
Install through the guarded boot2 path in AGENTS.md; the owner selects
boot2 physically.

## Sequence

All steps run over the authenticated USB SSH session.

1. Confirm the exact kernel release, changed boot identity and console.
2. Save `dmesg`. Accept the baseline only if it shows indexes 0 to 9 with
   `ret=0` and `c1-baseline complete 10`. A failed read ends with `stop`;
   record it and continue without retry.
3. Record bindings for the keys, RTC and gpio-keys devices, the input
   devices, and `/proc/interrupts`. Save `name` and `state` for every
   `/sys/class/regulator/regulator.*`; this shows which MT6351 rails the
   loader left on and feeds the regulator constraint set. The C1 kernel has
   no debugfs, so the regulator summary file is not available. See the
   [H7 ordering refinement](../2026-10-04-gemini-pmic-basics-re/README.md#h7-ordering-refinement-2026-10-05).
4. For the key and the lid input devices, start one background
   `busybox timeout 60 busybox cat /dev/input/eventN > FILE` each. Resolve N
   from `/proc/bus/input/devices` by device name. Decode the raw events
   afterwards; `hexdump` buffered its output and lost it when the first boot's
   timeout killed it.
5. The owner presses the power key once, briefly. Then the owner closes and
   opens the lid once.
6. Run `rtc-alarm.sh` once. Exit 0 means fired and cancelled. Exit 10 to 13
   is a refusal before arming; record it and skip the alarm. Exit 20, 30 or
   40 is a set failure, timeout or cleanup failure; record it, no retry.
7. Save `dmesg`, `/proc/interrupts` and `/proc/driver/rtc` again.
8. Seal the session evidence. The owner detaches the charger. Run
   `poweroff -f`. The owner records whether the device turned off, or
   restarted, within 30 seconds.
9. Return to Gemian through the reviewed recovery path and confirm a
   changed-boot Gemian.

Budgets: one short key press, one lid cycle, one ten-second alarm with at
most twenty seconds of waiting, one power-off. No long press, suspend,
charger I2C access, RTC time write or PMIC write beyond driver probe.

## Decision branches

- **All four events and a complete baseline.** C1 passes. Record the PMIC
  IRQ path as working, RTC alarm delivery as observed, lid polarity as
  measured, and PSCI power-off as the power-off baseline. Continue with C3.
- **Key or alarm missing, IRQ count unchanged.** The PMIC interrupt route to
  GIC is the suspect. Diagnose offline before another boot.
- **Lid events inverted or absent.** Correct polarity or GPIO offline; the
  other C1 results stand.
- **Power-off restarts or hangs.** Keep PSCI as unproven and review the
  MT6351 power-off sequence offline; no PMIC power-off driver is added blind.
- **Baseline read failure.** Keep the observed prefix and the failing
  address; review the wrapper transport before reusing the observer.
- Unexpected heat, charging or recovery behaviour: follow the stop rules in
  [SAFETY.md](../../docs/SAFETY.md).

## Not included

C2a, the read-only charger register dump, needs its own I2C transport review
and is not part of this boot. The roadmap's C2a ride-along waits for that
review.
