# Gemini PDA keyboard

## Current evidence

| Field | Finding | Confidence / method |
| --- | --- | --- |
| Matrix controller | AW9523 at I2C bus 5, address `0x5b` (`aw9523_key`) | Observed in a passive Gemian capture; vendor source agrees |
| Interrupt/reset | GPIO87/EINT10 interrupt; GPIO58 expander shutdown/reset | Observed in the device tree/source; polarity and timing still need hardware validation |
| Matrix wiring | Port 0: eight rows; port 1 bits 0–6: seven columns | Source-derived from the vendor driver; not electrically stimulated |
| Scan behavior | Vendor path delays the external IRQ by 1 ms, scans after another 1 ms, then rescans at 100 Hz; a normal transition can keep IRQ masked for up to 100 cycles | Source-derived; runtime input transition not performed. This is not a direct `matrix-keypad` debounce value |
| Keymap | 8×7 = 56 positions, 52 assigned codes, four intentional `KEY_UNKNOWN` spares | The exact active boot ELF compiles physical `(row=4,col=3)` as `KEY_LEFTMETA`; the retained source checkout labels that position `KEY_FN`, so the source/build discrepancy is documented rather than silently copied |
| Userspace layout | XKB model `planetgemini`, layout `us`, symbols `planet_vndr/gemini` | Fresh passive capture; XKB file hash is recorded in the input experiment |

The complete sanitized matrix table is in
[`keyboard-keymap.txt`](../../experiments/2026-07-12-input-backlight-recovery/results/keyboard-keymap.txt).
The validator reports 52 matching `MATRIX_KEY()` entries and four unassigned
positions in the current patch 0054; see the [active-boot map consistency
result](../../experiments/2026-07-12-input-backlight-recovery/results/keymap-consistency-active-boot-20260714.txt).
A source audit confirms what “unassigned” means in Linux 7.1.3: an omitted
matrix slot remains zero-initialized as `KEY_RESERVED`, so its `EV_KEY` event
is suppressed, while the scanner may still expose the physical coordinate as
`MSC_SCAN`.  An explicit `KEY_UNKNOWN` entry would instead advertise and emit
keycode 240.  The four vendor `KEY_UNKNOWN` positions are therefore omitted
intentionally until an owner-assisted evdev trace proves that any of them is a
real contact; this is not evidence that the contacts are electrically absent.
See the reproducible [keycode-semantics audit](../../experiments/2026-07-12-input-backlight-recovery/results/keyboard-keycode-semantics-20260714.txt)
and [audit script](../../experiments/2026-07-12-input-backlight-recovery/scripts/audit-keyboard-keycode-semantics.sh).
A fresh capture confirms the separate `Integrated keyboard` input device,
AW9523 binding, and active EINT10; it does not prove every physical legend,
modifier, rollover, LED, or wake behavior. Its capability bitmap advertises
`KEY_LEFTMETA` and `KEY_UNKNOWN`, but not `KEY_FN`. The exact active boot ELF
now independently confirms those disputed capability bits and maps the
physical `(row=4,col=3)` record to `KEY_LEFTMETA`; the retained source checkout
is a later, different source/build snapshot. See the normalized [capability
comparison](../../experiments/2026-07-12-input-backlight-recovery/results/live-keyboard-capability-compare-20260714.txt)
and [active ELF map result](../../experiments/2026-07-12-input-backlight-recovery/results/active-aw9523-elf-keymap-20260714.txt).

## XKB and kernel boundary

The installed XKB symbols implement userspace policy over ordinary Linux
keycodes: an ISO-Level3/Mod5 function layer, media/brightness/navigation
levels, and F1–F10 symbols. They do not require a Gemini-specific kernel
keyboard driver. The installed file is
`/usr/share/X11/xkb/symbols/planet_vndr/gemini`, layout `us`; its SHA-256 is
recorded in the input experiment's sanitized live result.

Mainline should therefore model the hardware as an AW9523 GPIO/IRQ expander
feeding `gpio-matrix-keypad`, with the active-boot-normalized 8×7 map, and leave
the XKB model to userspace. The candidate remains disabled until GPIO range and
polarity, reset sequencing, interrupt latching, rollover/ghosting, modifier
semantics, LEDs, and wake behavior are validated on hardware. A source-level
polarity audit found that the vendor scan drives the selected column low and
inactive columns high, and treats a low row bit as pressed; the generic Linux
consumer needs `gpio-activelow` and `drive-inactive-cols` to represent that
state machine. Follow-up patch 0076 adds both properties to the disabled
candidate; the 77-patch package now contains that correction, but the bus,
expander, and consumer remain disabled and this is still build-only evidence.
See the
[`keyboard-polarity-contract-20260714.txt`](../../experiments/2026-07-12-input-backlight-recovery/results/keyboard-polarity-contract-20260714.txt).
The patch decision and dry-run are recorded in
[`keyboard-polarity-mainline-patch-20260714.txt`](../../experiments/2026-07-12-input-backlight-recovery/results/keyboard-polarity-mainline-patch-20260714.txt).
Do not enable the bus, expander, or matrix consumer as part of a firmware or
boot experiment.

### Timing boundary

The retained vendor AW9523 source uses `HRTIMER_FRAME=100`: the external IRQ
queues work after 1 ms, that work starts the first scan after another 1 ms, and
subsequent scans run every 10 ms. A reported transition seeds 100 further
rescans (about 1 second); a ghost-suppression path can skip 50 cycles (about
500 ms). The source also requests an AW9523 EINT `debounce` tuple, but the
retained `mt6797.dtsi` pseudo-node does not provide one and the source ignores
the property-read error, passing its initialized `0,0` tuple to
`gpio_set_debounce`. These facts describe vendor policy, not a measured
electrical bounce interval.

Linux 7.1.3 `gpio-matrix-keypad` has a different contract: row IRQs schedule a
full scan after optional `debounce-delay-ms`, and optional
`col-scan-delay-us`/`all-cols-on-delay-us` add settling delays. The current
candidate omits all three properties, so the effective defaults are zero and
there is no periodic rescan. The AW9523 mainline reset path also uses a 50-us
hard-reset pulse and 20-us recovery delay rather than the vendor's 5-ms-low /
5-ms-high GPIO sequence. No property should be added merely to copy these
numbers; the owner-assisted runtime test must measure event latency, bounce,
release, and reset behavior first. See the reproducible
[`timing contract`](../../experiments/2026-07-12-input-backlight-recovery/results/keyboard-timing-contract-20260714.txt)
and its [`audit script`](../../experiments/2026-07-12-input-backlight-recovery/scripts/audit-keyboard-timing.sh).

The next highest-value evidence gate is an owner-assisted matrix runtime test:
boot a recoverable candidate with only the AW9523 and matrix consumer enabled,
then record one-key, modifier, rollover, debounce, wake, reset-polarity, and
the physical `(row=4,col=3)` `KEY_LEFTMETA` press/release. The exact bounded
protocol and current non-claim are in
[`keyboard-next-gate-20260714.txt`](../../experiments/2026-07-12-input-backlight-recovery/results/keyboard-next-gate-20260714.txt).

The independent bsg100 Linux 6.6 effort reports successful physical typing on
its Gemini unit, including a 53-key base set and an AltGr Fn layer. This
corroborates the AW9523 address/reset/matrix architecture and the userspace
function-layer boundary, but it does not identify the live evdev Fn code or
prove that its source/build matches this Gemian image. It is therefore useful
cross-device evidence, not a substitute for the named-device test.

See the [input/backlight experiment](../../experiments/2026-07-12-input-backlight-recovery/README.md),
[vendor-kernel ABI matrix](vendor-kernel-abi.md#input-and-keyboard), and
[Gemian baseline](gemini-gemian-baseline.md).
