# Gemini PDA keyboard

## Current evidence

| Field | Finding | Confidence / method |
| --- | --- | --- |
| Matrix controller | AW9523 at I2C bus 5, address `0x5b` (`aw9523_key`) | Observed in a passive Gemian capture; vendor source agrees |
| Interrupt/reset | GPIO87/EINT10 interrupt; GPIO58 expander shutdown/reset | Observed in the device tree/source; polarity and timing still need hardware validation |
| Matrix wiring | Port 0: eight rows; port 1 bits 0–6: seven columns | Source-derived from the vendor driver; not electrically stimulated |
| Scan behavior | Vendor path delays the external IRQ by 1 ms, scans after another 1 ms, then rescans at 100 Hz; a normal transition can keep IRQ masked for up to 100 cycles | Source-derived; runtime input transition not performed. This is not a direct `matrix-keypad` debounce value |
| Keymap | 8×7 = 56 positions, 52 assigned codes, four `KEY_UNKNOWN` spares in the active binary | The exact active boot ELF compiles physical `(row=4,col=3)` as `KEY_LEFTMETA`; the retained source checkout labels that position `KEY_FN`. The disabled mainline candidate intentionally omits the four unproven contacts, yielding `KEY_RESERVED`, so both distinctions are explicit |
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
Do not enable the bus, expander, or matrix consumer outside a dedicated,
recoverable keyboard experiment.

### SoC pinctrl and USB coexistence boundary

The current disabled board candidate describes GPIO58 as `reset-gpios` and
GPIO87/EINT10 as the interrupt, but it does not yet select a default SoC
pinctrl state for those two lines on the AW9523 I2C node. This must be resolved
before enabling the node; child AW9523 pin states describe expander pins and
cannot substitute for the MT6797-side GPIO58/GPIO87 mux and bias contract.
Its current `gpio-ranges = <&pio 0 0 16>` is also not the binding-validated
combined-controller form; Candidate Q must correct it to the expected
`gpio-ranges = <&aw9523 0 0 16>` before enablement. Preserve the upstream
driver's `GPIO_ACTIVE_HIGH` reset contract: its logical 0-to-1 sequence yields
the required physical low pulse and high release, so copying a vendor
active-low label would invert the behavior.

The Q correction must assign the existing `i2c5_pins_a` state to I2C5 and add
a source-backed SoC state with GPIO58 in GPIO/output-high mode and GPIO87 in
EINT10 mode, selected by the AW9523 node. The current MT6797 pinctrl data lacks
the generic pull and input-enable register maps needed to honor
`bias-pull-up` or `input-enable` on GPIO87. Its retained electrical state is a
named runtime risk; do not mask it with unsupported properties, guessed
polling, or fabricated timing.

The independent bsg100 Linux 6.6 effort is useful cautionary cross-device
evidence. Its retained B-18 audit reports that enabling AW9523 while the defined
`aw9523b_pins` state was not referenced by the I2C node broke its previously
working USB gadget/SSH path. Adding `pinctrl-names = "default"` and the matching
`pinctrl-0` reference reportedly restored keyboard and USB gadget coexistence.
That does not prove the same causal electrical mechanism or exact pin settings
on this unit, and the audit's earlier suspects were explicitly untested. It
does establish a concrete integration hazard: the first keyboard candidate
must use a source-backed MT6797 state for both GPIO58 and GPIO87 and must retain
T-PHY/MTU3/`g_ether` registration as a negative-regression checkpoint. See the
[retained related-project audit](../../experiments/2026-07-13-bsg100-gemini-linux-comparison/results/audit-current-20260714.txt)
and this unit's [sanitized gadget evidence](../../experiments/2026-07-16-usb-gadget-diagnostic/results/retained-pstore-mtu3-gadget-evidence-20260718.txt).

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

The exact next gate is planned
[Candidate Q](../../experiments/2026-07-18-keyboard-shell-diagnostic/README.md),
based only on hardware-passed Candidate P. By owner decision Q combines the
keyboard-event gate and a supervised local `tty1` BusyBox shell in one device
cycle, but a bounded no-grab evdev probe must run and report first so keyboard
registration and raw events remain independently attributable. Q enables only
I2C5, its AW9523 child, and the matrix consumer; it retains CPU0-only execution,
performs no storage or network access, and has no deliberate normal-path
automatic reboot. The old shell-only Candidate R was never implemented and is
retired into Q.

The attended Q protocol covers one-key press/release, Shift, Enter, the
physical `(row=4,col=3)` Meta/Fn-position key, a simultaneous-key combination,
typed shell commands, shell respawn, and a 15-minute idle-console check. It
does not attempt wake, LED control, or a full physical legend map. Promote
only the raw events and shell behavior actually observed; later work may use
that evidence to design focused debounce, rollover, wake, or keymap tests. The
older bounded matrix protocol and historical non-claim remain in
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
