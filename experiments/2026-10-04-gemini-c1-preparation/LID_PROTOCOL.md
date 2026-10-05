# C1 lid test protocol (C1-3)

Status: draft for coordinator review, 2026-10-06. Package pending; no
candidate composed and no device action taken under this protocol.

## Hypothesis and unique observation

Two boots gave no lid interrupt; see the
[lid diagnosis](README.md#lid-diagnosis-offline). Either hardware debounce on
a dual-edge EINT5 suppresses the interrupt, or the GPIO66 level never changes.
The unique observation is GPIO66's level with the lid open and closed, which
neither earlier boot could read.

## Artifact changes from the C1 follow-up

- Patch c1/0010 sets the lid's `debounce-interval` to 0, so no debounce of any
  kind is requested on EINT5.
- The C1 fragment enables `CONFIG_DEBUG_FS`, so `/sys/kernel/debug/gpio` shows
  GPIO66's level.

Nothing else changes: same PMIC observer, key child, pull-up, input enable,
RTC and PSCI power-off. Compose like the C1 follow-up, with the fixed
`rtc-alarm.sh`.

## Sequence

1. Confirm boot identity, release and USB SSH. Mount debugfs read-only if it
   is not mounted.
2. Start one background `busybox timeout 60 busybox cat` of the lid event node
   into a file.
3. Read the GPIO66 line from `/sys/kernel/debug/gpio` and the Hall line from
   `/proc/interrupts` with the lid open.
4. The owner closes the lid and keeps it closed. Read both again.
5. The owner opens the lid. Read both again.
6. Save `dmesg`, seal the log and return through the reviewed path. The power
   key and RTC alarm need not be repeated.

Budgets: one close/open cycle, read-only debugfs reads, no register writes, no
retry.

## Decision branches

- **Level changes and the Hall interrupt count rises.** Debounce was the cause.
  Keep debounce off or use software debounce; propose an `mtk-eint` fix that
  refuses hardware debounce on dual-edge lines.
- **Level changes but no interrupt.** EINT5 routing or dual-edge handling is
  wrong; diagnose `mtk-eint` and patch 0005's mapping offline.
- **Level does not change.** The pin, pull or sensor is the problem: check the
  sensor supply and the magnet position offline, and compare with a Gemian
  read of GPIO66 during a lid cycle.
- **Events appear but inverted.** Flip the GPIO polarity.
