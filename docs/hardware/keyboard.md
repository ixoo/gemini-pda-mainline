# Gemini PDA keyboard

This document records the durable keyboard hardware and software boundary for
the named Gemini PDA development unit. Candidate construction, artifact
identity, installation records, failed branches, and raw captures remain in
the linked experiments.

## Current hardware boundary

| Area | Current fact | Evidence boundary |
| --- | --- | --- |
| Controller | AW9523 at I2C5 address `0x5b`; the working mainline path binds `aw9523-pinctrl`, then `matrix-keypad`, and exposes a matrix-owned input event device | Observed on the named unit; the vendor device tree and source agree |
| I2C transport | MT6797 uses the `mt8173_compat` controller data for the AW9523 one-byte register write plus one-byte read | The direct match cleared the earlier combined-read timeout and produced working input. This does not constitute a physical bus-waveform measurement |
| Reset | GPIO58 is the expander shutdown/reset signal | The upstream driver's active-high logical contract is intentional: its logical low-to-high sequence produces the required physical low pulse and high release |
| Interrupt | GPIO87 maps to EINT10 | Observed in the vendor topology and active vendor interrupt state. The accepted mainline path uses polling, so parent-IRQ delivery remains untested |
| Matrix | AW9523 port 0 provides eight rows; port 1 bits 0–6 provide seven columns | Source-derived 8×7 wiring; complete electrical contact coverage remains unverified |
| Polarity | The selected column is driven low, inactive columns high, and a low row is pressed | Source-derived. The generic matrix consumer therefore needs `gpio-activelow` and `drive-inactive-cols` |
| Keycodes | The active vendor binary contains 52 assigned positions and four `KEY_UNKNOWN` positions in the 56-position matrix | The four unproven positions remain omitted as `KEY_RESERVED` in the reusable Linux map until a physical trace identifies them |
| Accepted runtime | H, E, L, P, Enter, A, and S press/release events have been retained across bounded runs; the owner separately reported working physical typing and the current VT map | This is partial legend coverage, not a complete keyboard certification |

The complete sanitized coordinate table is
[`keyboard-keymap.txt`](../../experiments/2026-07-12-input-backlight-recovery/results/keyboard-keymap.txt).
The current reusable map has 52 matching `MATRIX_KEY()` entries and omits four
unassigned positions. An omitted Linux matrix slot remains zero-initialized as
`KEY_RESERVED`, suppressing its `EV_KEY` event while still permitting a scanner
to expose the coordinate as `MSC_SCAN`. An explicit `KEY_UNKNOWN` would instead
advertise and emit keycode 240. Omission is therefore a conservative policy,
not evidence that those contacts are electrically absent.

### Physical Fn-key discrepancy

The retained source checkout labels physical matrix position
`(row=4,col=3)` as `KEY_FN`, but the exact active vendor boot binary compiles
that position as `KEY_LEFTMETA`. Its live capability bitmap also advertises
`KEY_LEFTMETA` and `KEY_UNKNOWN`, not `KEY_FN`. The source and running binary
are different snapshots; the active binary is authoritative for the captured
unit.

The installed XKB symbols independently treat `<LWIN>`/`KEY_LEFTMETA` as the
Gemini function-layer modifier. No retained evdev trace isolates a physical Fn
press by itself, so the electrical contact-to-keycode conclusion is based on
the exact active binary plus the userspace layout rather than a dedicated
single-key runtime capture.

## Current VT console map

The accepted console policy keeps the AW9523 kernel keycode map unchanged and
loads a deterministic eight-table VT map in Unicode mode. A live
`KDGKBENT` query verified all declared entries, the untouched upper table
halves, and the absence of undeclared tables before the interactive prompt was
accepted.

The durable policy is:

- physical keycode 125 (`KEY_LEFTMETA`) acts as VT `K_ALTGR`, providing the Fn
  layer;
- the backslash key emits `\` and `|` in its plain and Shift states, with the
  standard Ctrl file-separator and Alt meta-backslash behavior;
- the comma and period positions provide `,`/`/` and `.`/`?`;
- Fn provides the photographed printable and navigation layer, including
  U+263A WHITE SMILING FACE, Caps Lock, Home, Page Up, Page Down, and End;
- Shift+Fn with digits 1 through 0 maps to F1 through F10; and
- Shift, Ctrl, Alt, and Fn have explicit release entries so a modifier cannot
  remain logically stuck when changing tables.

The owner reported the resulting keymap working. Retained A/S events and the
live table query establish that the map was loaded while the expected input
device was active. Physical F1–F10 and Page Up/Page Down behavior remains
unconfirmed, not failed: those presses had no visible discriminator during the
accepted session. The four vendor-unknown contacts, full modifier combinations,
rollover, ghosting, autorepeat, LEDs, and wake behavior also remain open.

Media, brightness, phone, airplane-mode, launcher, voice-assistant, and Sym
actions are userspace policy. They must not be guessed into the kernel matrix
map from printed legends.

### Console and reboot acceptance

A readable foreground shell and the larger `TER16x32` console font were part
of the successful owner-assisted keyboard acceptance. The accepted path stayed
interactive without an automatic watchdog reset, accepted a typed bare
`reboot`, and reached the kernel restart path on the named unit. This is useful
end-to-end evidence that physical input reached the VT and shell; restart
handler attribution and timing belong to the watchdog/restart experiment, not
to the keyboard hardware contract.

Kernel logs must not be directed onto the same VT used for keyboard acceptance.
A future regression result is incomplete if logging obscures the prompt or if a
timer-driven reboot prevents deliberate key testing.

## XKB and kernel boundary

The installed userspace model is `planetgemini`, layout `us`, with symbols in
`/usr/share/X11/xkb/symbols/planet_vndr/gemini`. It implements an
ISO-Level3/Mod5 function layer, media and brightness actions, navigation, and
F1–F10 symbols over ordinary Linux keycodes. It does not require a
Gemini-specific kernel keyboard driver.

The kernel should model the hardware as the upstream AW9523 GPIO/pinctrl
provider feeding `gpio-matrix-keypad`, using the active-binary-normalized 8×7
map. VT keymaps and XKB symbols are separate policy layers:

```text
AW9523 matrix coordinate
        -> Linux input keycode
        -> VT console map or XKB userspace symbols
```

Do not put XKB media policy into the hardware map, and do not copy the vendor
input ABI or an older custom AW9523 platform-data driver. The reusable board
description should preserve:

- I2C5 pinctrl and the working MT6797 controller-data match;
- `gpio-ranges = <&aw9523 0 0 16>`;
- GPIO58 with the upstream driver's active-high logical reset contract;
- GPIO87/EINT10 for a later IRQ-specific experiment;
- `gpio-activelow` and `drive-inactive-cols`; and
- the normalized 52-entry matrix map with the four unknown positions omitted.

## Timing, IRQ, and polling boundary

The retained vendor source uses this policy:

1. the external IRQ queues work after 1 ms;
2. work starts the first scan after another 1 ms;
3. subsequent scans run every 10 ms; and
4. a transition can retain 100 rescans, while the ghost-suppression branch can
   skip 50 cycles.

The vendor device tree requests a debounce tuple, but the retained MT6797
pseudo-node supplies no value and the driver passes its initialized zero tuple
after ignoring the property-read error. These are source facts, not a measured
bounce interval or a Linux DT timing contract.

Linux 7.1.3 `gpio-matrix-keypad` normally uses row interrupts followed by a
full scan after optional debounce and column-settling delays. The local generic
polling extension instead skips row-IRQ and wake setup, schedules scans through
managed delayed work, and serializes suspend/resume with input open/close. Its
non-polling behavior is unchanged.

The accepted named-unit path used:

- a 20 ms polling interval;
- a 2 us column scan delay;
- no claimed polling debounce; and
- the upstream AW9523 reset implementation.

That configuration produced working input once and has remained the
serviceability baseline. It does not measure event latency, contact bounce, or
the upstream reset waveform. It also does not validate EINT10 delivery,
interrupt masking, wake, or equivalence to the vendor 100 Hz post-transition
rescan policy.

Independent bsg100 hardware results corroborate physical typing through an
AW9523 polling path and keyboard/USB-gadget pinctrl coexistence on another
Gemini unit. They support the architecture and integration direction, but do
not prove this unit's exact electrical behavior or justify importing the
custom driver, platform-data API, or reset polarity.

## Observation and inference limits

Directly observed on the named unit:

- AW9523, the matrix consumer, and the matrix-owned input device bound;
- bounded H/E/L/P/Enter and A/S press/release events;
- a live exact VT-map query passed while the expected input device was active;
- the owner reported working physical typing and the current map; and
- a typed command reached the shell and kernel restart path.

High-confidence implementation inference:

- the direct MT6797 controller-data match fixed the AW9523 combined-read
  failure, because that was the keyboard-causal kernel change and the provider
  subsequently bound. No physical I2C waveform was captured.

Source- or binary-derived rather than electrically measured:

- the complete 8×7 coordinate assignment and scan polarity;
- the GPIO58 reset waveform and vendor timing policy;
- EINT10 routing for the future interrupt path; and
- the active-binary resolution of the Fn position as `KEY_LEFTMETA`.

Not established:

- complete physical legend coverage or the function of the four unknown
  contacts;
- physical F1–F10 and Page Up/Page Down results;
- IRQ-driven scanning, debounce, latency, rollover, ghosting, autorepeat,
  keyboard LEDs, wake, suspend/resume, or long-duration repeatability; and
- equivalence across all Gemini hardware revisions.

The [roadmap](../ROADMAP.md#parallel-work-that-does-not-block-the-a72-sequence)
owns scheduling for the remaining acceptance work. Map coverage, multi-key
behavior, interrupt-versus-polling behavior, wake/suspend, LEDs, and
console/USB coexistence require separate attributable experiments; this
hardware document does not prescribe their order or candidate construction.

## Evidence index

- [Input and keyboard recovery](../../experiments/2026-07-12-input-backlight-recovery/README.md),
  including the [sanitized matrix](../../experiments/2026-07-12-input-backlight-recovery/results/keyboard-keymap.txt),
  [map consistency result](../../experiments/2026-07-12-input-backlight-recovery/results/keymap-consistency-active-boot-20260714.txt),
  [active-binary map](../../experiments/2026-07-12-input-backlight-recovery/results/active-aw9523-elf-keymap-20260714.txt),
  and [capability comparison](../../experiments/2026-07-12-input-backlight-recovery/results/live-keyboard-capability-compare-20260714.txt)
- [Keycode semantics](../../experiments/2026-07-12-input-backlight-recovery/results/keyboard-keycode-semantics-20260714.txt),
  [matrix polarity](../../experiments/2026-07-12-input-backlight-recovery/results/keyboard-polarity-contract-20260714.txt),
  and [timing contract](../../experiments/2026-07-12-input-backlight-recovery/results/keyboard-timing-contract-20260714.txt)
- [Working MT6797 controller comparison](../../experiments/2026-07-19-keyboard-watchdog-diagnostic/results/working-3.18-aw9523-i2c-binary-audit-20260719.txt)
  and [first retained working-input result](../../experiments/2026-07-19-keyboard-wrrd-diagnostic/results/runtime-candidate-w-attempt-1-20260719.txt)
- [Current VT layout reference](../../experiments/2026-07-20-keyboard-console-map-diagnostic/results/layout-reference-aa-r1-20260721.txt)
  and [hardware acceptance result](../../experiments/2026-07-20-keyboard-console-map-diagnostic/results/runtime-candidate-aa-r1-attempt-1-20260721.txt)
- [Typed kernel-restart acceptance](../../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/runtime-candidate-ab-attempt-1-20260721.txt)
- [Independent bsg100 comparison](../../experiments/2026-07-13-bsg100-gemini-linux-comparison/results/audit-current-20260714.txt)
- [Vendor-kernel input boundary](vendor-kernel-abi.md#input-and-keyboard)
  and [Gemian hardware baseline](gemini-gemian-baseline.md)
