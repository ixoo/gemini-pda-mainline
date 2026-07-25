# Gemini PDA keyboard

## Current evidence

| Field | Finding | Confidence / method |
| --- | --- | --- |
| Matrix controller | AW9523 at I2C bus 5, address `0x5b` (`aw9523_key`) | Observed in a passive Gemian capture; vendor source agrees |
| Interrupt/reset | GPIO87/EINT10 interrupt; GPIO58 expander shutdown/reset | Observed in the device tree/source. W bound AW9523 once through the GPIO58 reset path; parent IRQ delivery remains untested because W deliberately polls without that consumer |
| Matrix wiring | Port 0: eight rows; port 1 bits 0–6: seven columns | Source-derived from the vendor driver; W exercised coordinates reported as H, E, L, P, and Enter, and AA r1 later retained A/S press-release events. Complete electrical wiring remains unverified |
| Scan behavior | Vendor path delays the external IRQ by 1 ms, scans after another 1 ms, then rescans at 100 Hz; a normal transition can keep IRQ masked for up to 100 cycles | Vendor timing is source-derived and not directly measured. W separately passed one 20-ms generic-polling run; that is not a measurement of the vendor IRQ timing or a direct `matrix-keypad` debounce value |
| Keymap | 8×7 = 56 positions, 52 assigned codes, four `KEY_UNKNOWN` spares in the active binary | The exact active boot ELF compiles physical `(row=4,col=3)` as `KEY_LEFTMETA`; the retained source checkout labels that position `KEY_FN`. W retained H/E/L/P/Enter and AA r1 retained A/S press-release events. The four unproven contacts remain deliberately omitted as `KEY_RESERVED` |
| Userspace layout | XKB model `planetgemini`, layout `us`, symbols `planet_vndr/gemini` | Fresh passive capture; XKB file hash is recorded in the input experiment |
| Candidate Q runtime | No working text console; no Q marker, AW9523/input observation, shell, or pstore evidence | Exact Q build/write/readback succeeded, but the one intended selection was non-diagnostic beyond the missing console; keyboard function remains unestablished |
| Candidate U runtime | Black screen and dark console; no marker, automatic reboot, or retained pstore | Exact U build/write/readback succeeded, but its one intended selection established no kernel, initramfs, AW9523, input, or shell gate |
| Candidate V runtime | Visible console and automatic watchdog return; exact V marker and `tty1_shell=ready` retained, but AW9523 probe repeatedly failed `-110`/`ETIMEDOUT` | Proves kernel/initramfs and local-shell pre-exec recorder only. AW9523 and matrix remained unbound with no input event; no usable shell or key test occurred |
| Working 3.18 controller reference | Exact active binary converts the AW9523 one-byte write plus one-byte read into MT6797 hardware WRRD and programs RX length at auxiliary offset `0x6c` | V instead falls through to `mt6577_compat`, which suppresses WRRD and lacks the auxiliary-length contract; latest bsg100 fixed the same cross-device failure with a direct MT6797-to-MT8173 controller-data match |
| Candidate W runtime | Patch 0086 adds exactly one direct `mediatek,mt6797-i2c` match to existing `mt8173_compat`; exact V's final DTB, AW9523/matrix state, no-IRQ watchdog, and ramoops remain fixed | In one exact run AW9523 and matrix bound, `/dev/input/event0` appeared, and H/E/L/P/Enter press/releases survived. The owner observed a visible shell and working keyboard and approved `TER16x32`. Kernel logs still mixed with the shell, the watchdog returned automatically, `pass` was absent, and full coverage/repeatability remain unproven |
| Candidate X runtime | Retain exact W's kernel, DTB, keyboard path, font, and ramoops; remove only the virtual-console token and userspace watchdog ownership, then add a typed manual reboot path | Owner reported X booted and worked, but typed `reboot` appeared to hang. Empty pstore leaves clean tty1, exact marker, X uptime, and individual keyboard subgates unproved |
| Candidate Y pre-boot rejection | Retain exact X kernel/DT/config; change four initramfs members for typed watchdog expiry | Exact BusyBox resolves bare `reboot` to its internal applet instead of Y's wrapper, and watchdog-open failure cannot reach the promised refusal. Y was built and fully read back but never booted; do not boot it |
| Candidate Z runtime | Retain exact Y kernel/DT/config; change four initramfs members and add read-only `reboot-dispatch.env` | In one owner-attended selection Z booted, keyboard input still worked, and the typed watchdog command returned automatically. Changed boot-ID and `wdt_by_pass_pwk` evidence corroborate the reset, but no individual key trace, exact dispatch text, or full-map test survived |
| Candidate AA r0 pre-boot rejection | Retain exact Z kernel/DT/config/matrix/recovery; add the first deterministic VT map | Historical raw image `a2ad7a4107abd99cbd349b8f2deadd0185cbdd5bb0884ecbdae8ff2a7499ed4c`, incomplete map `48f1f61a9ad8ba327a3105c0dfbbc698c1e55bb3bcca695b46887888be8ca821`, and installed/read-back padded image `157c7cd5d814d7b2704d679faacd3215c5e889642b4261441f99653957585eaa` are exact. R0 omitted Shift+Fn F1–F10 and used an invalid dump-byte oracle; it was superseded before boot and must not be selected |
| Candidate AA r1 attempt 1 pass | Retain exact Z kernel/DT/config/matrix/recovery; replace only VT-map policy and live verification | The 2,311-byte, eight-table map has SHA-256 `02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c` and 53 semantic changes. Two builds are recursively byte- and metadata-identical; canonical verifier SHA-256 is `29735d212e74d0b0040a3ead173a83223b89ce5d947b697a115707eb3d23b238`. Raw 7,378,944-byte SHA-256 is `37e82bf3be87dd9e52fb8d60597b69f92a5c0dc5aebd51d178f1e7efd33343d7`; guarded padded `boot2` readback SHA-256 is `38b49c7c19c2d97fa0c48436545219489221aa367aedf491ae6ebd4ec4856703`. Retained pstore proves loaded-now Unicode mode, all 2,048 exact entries/table invariants, normal-prompt readiness, exact AW9523/matrix/event0 identity, A/S press-release events, >123 seconds without automatic watchdog ownership, and typed recovery; the owner reported the new keymap working. F1–F10 and Page Up/Page Down remain unconfirmed, not failed |
| Candidate AB attempt 1 pass | Patch 0087 raises only MT6797 TOPRGU restart priority to 255, ahead of PSCI 129; other MediaTek variants remain 128; the exact AA r1 keyboard path and map are retained | On the current Gemini unit, the owner reported the keyboard/map working, waited at least 45 seconds without an automatic reset, and observed an immediate reset after typed bare `reboot`. Retained pstore records the request at 66.021584 seconds and the final kernel restart line at 66.049438 seconds, a 27.854 ms kernel-log interval; a changed boot ID and Gemian return close the one-run oracle. There was no userspace watchdog, countdown, or automatic-reset path. F1–F10 and Page Up/Page Down remain unconfirmed, not failed, and repeatability remains open |

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
`56baafdde43da9e3d66474f231a9bfd9d8d9fda40cd4c4af939ae1251db426cb`
in the latest authenticated read-only inspection. It maps
`<LWIN>`/`KEY_LEFTMETA` to `ISO_Level3_Shift`/Mod5, independently
corroborating AA r1's Fn-as-Level3 console policy. AA r1 mirrors only the
photographed printable/navigation symbols, smiley, and Shift+Fn F1–F10 at the
VT layer; it does not change the AW9523 kernel keycode map. Media, brightness,
phone, airplane-mode, launcher, voice-assistant, and Sym actions remain
userspace policy and must not be guessed into that hardware map from printed
legends. See the current [AA r1 layout reference](../../experiments/2026-07-20-keyboard-console-map-diagnostic/results/layout-reference-aa-r1-20260721.txt).

Mainline should therefore model the hardware as an upstream AW9523 GPIO
expander feeding `gpio-matrix-keypad`, with the active-boot-normalized 8×7 map,
and leave the XKB model to userspace. The reusable board default remains
disabled until GPIO range and polarity, reset sequencing, scanning,
rollover/ghosting, modifier semantics, LEDs, and wake behavior are validated on
hardware. A source-level
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

Patch 0082 corrected the reusable disabled board description before Q: it
assigned `i2c5_pins_a`, added MT6797 states for GPIO58 and GPIO87/EINT10, and
changed the combined-controller mapping to
`gpio-ranges = <&aw9523 0 0 16>`. It also preserved the upstream driver's
`GPIO_ACTIVE_HIGH` reset contract. That contract is intentional: the driver's
logical 0-to-1 sequence produces the required physical low pulse and high
release, whereas copying a vendor active-low label would invert the behavior.

Q's candidate-only DT then enabled I2C5, AW9523, and the matrix consumer, but
its parent interrupt specifier incorrectly used raw
`interrupts = <87 IRQ_TYPE_LEVEL_LOW>`—effectively EINT87—even though MT6797
GPIO87 maps to EINT10. This is a concrete static defect, not proof of the
runtime cause: Q supplied neither a working console nor pstore evidence, so it
did not establish kernel entry, AW9523 probe, or any interrupt behavior. Do not
repeat unchanged Q. Candidate U omits the GPIO87 parent-IRQ path rather
than merely renumbering it: it keeps GPIO58 and the upstream reset behavior,
removes the AW9523 interrupt-controller/parent-interrupt properties from its
diagnostic DT, and drives the matrix through explicit polling. Patch 0085 now fixes the
reusable disabled board description to raw EINT10 for any later IRQ-mode test;
this statically validated source correction is not runtime evidence. U's
candidate-only DT retains the GPIO87/EINT10 pinmux state but gives it no active
consumer.

The latest bsg100 Linux 6.6 history supplies direct cross-device evidence for
that direction. Commit
[`6bd4d572`](https://github.com/bsg100/gemini-linux/commit/6bd4d572670698f80ca08ad083657621b62cc8f3)
reports working physical typing through a polling keyboard path; commit
[`aff681d3`](https://github.com/bsg100/gemini-linux/commit/aff681d3c727137c4016376e12055d380867f5c3)
then records keyboard and USB gadget coexistence with the relevant default
pinctrl state. These commits corroborate the I2C5/AW9523/matrix architecture
and expose pinctrl coexistence as a real integration boundary. They do not
justify copying bsg100's older custom AW9523 driver, platform-data API, or reset
polarity into Linux 7.1.3. U retains upstream `pinctrl-aw9523` and expresses
polling as a generic matrix-consumer policy. See the [retained related-project
audit](../../experiments/2026-07-13-bsg100-gemini-linux-comparison/results/audit-current-20260714.txt)
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
`col-scan-delay-us`/`all-cols-on-delay-us` add settling delays. It has no
periodic polling mode today. Series patch 0083 adds the optional standard
`poll-interval` binding property, while patch 0084 implements the small generic
polling extension: skip row-IRQ setup and wake handling when the property is
present, and reschedule delayed scan work after every poll. The corrected
patch hard-pinned by Candidate V adds managed delayed-work cancellation before
input registration and serializes suspend/resume against input open/close,
restarting only when `input_device_enabled()` permits it. The non-polling path
must remain unchanged. bsg100's
hardware-tested DT uses a 20 ms poll interval, carries a 5 ms debounce
property, and uses a 2 us column scan delay. Its polling branch does not
consume `debounce_ms`, so U omits that inert property rather than presenting
it as applied debounce. These remain unconfirmed hypotheses after U's
non-diagnostic first boot, not measurements on this unit. Its working DT also omits `drive-inactive-cols`, while the retained
vendor scan evidence led this repository to add that property. U's built and
statically validated DT retains `drive-inactive-cols`, pins I2C5 at 400 kHz,
and uses a 20 ms poll plus 2 us scan delay without a separate polling debounce;
the black-screen run supplied no evidence that this path probed or scanned.

The upstream AW9523 reset path uses a 50-us hard-reset pulse and 20-us recovery
delay rather than the vendor's 5-ms-low / 5-ms-high GPIO sequence. Preserve the
upstream behavior and active-high logical contract; do not import the bsg100
custom driver's reset implementation. An attributable V run may establish only
the checkpoints observed before its bounded watchdog expiry. Event latency,
bounce, release, scan behavior, reset behavior, rollover, and longer idle
stability remain separate later measurements. See the
reproducible
[`timing contract`](../../experiments/2026-07-12-input-backlight-recovery/results/keyboard-timing-contract-20260714.txt)
and its [`audit script`](../../experiments/2026-07-12-input-backlight-recovery/scripts/audit-keyboard-timing.sh).

Candidate Q was built twice from clean VM directories, installed to
live-resolved logical `boot2`, and fully read back with a matching checksum.
Its intended selection did not provide a working text console. No Q marker,
AW9523 binding, matrix input device, raw event, interactive shell, or pstore
record was observed. The result is therefore non-diagnostic beyond the missing
console; it does not establish whether Linux, initramfs, display/VT, I2C,
AW9523, or the keyboard ran. Preserve the [build
record](../../experiments/2026-07-18-keyboard-shell-diagnostic/results/final-build-reproduction-20260719.txt),
[write/readback](../../experiments/2026-07-18-keyboard-shell-diagnostic/results/boot2-write-candidate-q-20260719.txt),
and [runtime
record](../../experiments/2026-07-18-keyboard-shell-diagnostic/results/runtime-candidate-q-attempt-1-20260719.txt),
and do not repeat unchanged Q.

Candidate U was the next runtime gate because R is retired and S/T are
reserved. It was independently built twice with matching validated outputs,
then installed to live-resolved logical `boot2` with a matching full-partition
readback. Its first intended selection produced a black screen and dark console
with no visible marker or automatic reboot. The later Gemian boot ID changed,
but authenticated post-return pstore was empty. Every keyboard, console, shell,
kernel-entry, and init-entry gate therefore remains unestablished; do not repeat
unchanged U. Preserve the [experiment
record](../../experiments/2026-07-19-keyboard-polling-diagnostic/README.md),
[build reproduction](../../experiments/2026-07-19-keyboard-polling-diagnostic/results/final-build-reproduction-20260719.txt),
and [write/readback](../../experiments/2026-07-19-keyboard-polling-diagnostic/results/boot2-write-candidate-u-20260719.txt),
plus its [runtime result](../../experiments/2026-07-19-keyboard-polling-diagnostic/results/runtime-candidate-u-attempt-1-20260719.txt).
U's artifact is CPU0-only by configuration, adds the upstream AW9523 plus
generic polling matrix path, and retains the storage/network exclusions. A
later audit found that its final DTB came from the kernel package rather than
exact P, omitting P's loader-framebuffer, no-IRQ watchdog, and other LK-aligned
fixups. Its initramfs omits
userspace-watchdog access; the
pinned Linux 7.1.3 watchdog-policy audit confirms
`WATCHDOG_HANDLE_BOOT_ENABLED` keepalive for a boot-running timer, which is
static policy evidence rather than U runtime watchdog behavior. Q's initramfs
waited for the bounded event capture—up to 60 seconds—
before starting BusyBox init, so a dead input path also withheld the shell.
U's validated initramfs creates and supervises the local shell independently of
event capture, runs the bounded no-grab probe as a separately observable task,
reports the active VT when available, and emits stage diagnostics to
`/dev/tty0`, `/dev/console`, and `/dev/ttyS0` when those sinks exist. Its
devtmpfs setup also tolerates an already-mounted instance.

Candidate V corrects U's packaging foundation and polling implementation while
preserving U as failed historical evidence. V starts from exact P's final DTB,
including the loader-retained simplefb path, no-IRQ `mtk-wdt`, and primary
`console-ramoops`, then permits only the parsed I2C5/AW9523/matrix polling
transform. Its event helper discovers only the exact matrix-owned event node,
revalidates its name with `EVIOCGNAME`, never grabs it, and uses a bounded
absolute deadline. Shell supervision, event capture, and the exact-device
watchdog owner start independently; durable markers go through `/dev/kmsg` to
P's ramoops zone.

Two fresh kernel builds and two complete V assemblies reproduced. The package,
focused schemas, component validators, and all 24 negative mutation cases
passed. V's raw 6,864,896-byte image is SHA-256
`9ef0ee8dc1eb49752f9cf8f60b247b9b85e4fd2a9f090473f1d91848114087b0`;
the installed padded `boot2` target and full readback are SHA-256
`57d362a86fae38c0ec2cec909ef6ae8d8ad124b87abb2ee58d179184c1f19168`.
The guarded write did not reboot the device. The owner later selected V from
`boot2`, saw a visible console, had no usable shell or keyboard-test
opportunity, and observed an automatic return. Retained `console-ramoops`
contains the exact V marker and `tty1_shell=ready`, proving kernel/initramfs
entry and that local-shell reached its recorder immediately before `exec`.
That marker does not prove `ash` executed or that a prompt was visible or
interactive.

AW9523 probe on I2C adapter 0 at address `0x5b` repeatedly returned
`-110`/`ETIMEDOUT`, including its reset retry. The AW9523 driver stayed unbound,
the matrix platform device stayed unbound, and no input/event node appeared.
This isolates attempt 1 before generic matrix polling or input at the
controller-to-AW9523 provider boundary; it is not a polling, keymap, or
tty-input result. Retained markers also prove exact `mtk-wdt` association, open and one
handoff ping at timeout 31, plus waits through 30 seconds before the automatic
return. Gemian reported `boot_reason=4`, `wdt_by_pass_pwk`, and
`powerup_reason=reboot`.

The diagnostic itself has two usability flaws: every probe/watchdog marker
writes tty1 and can bury the prompt, and V's matrix keymap has neither
`KEY_SLASH` nor `KEY_MINUS`, so the advertised `/bin/v-pass` command cannot
normally be typed from V's own keyboard. Do not repeat unchanged V.
See the [Candidate V experiment](../../experiments/2026-07-19-keyboard-watchdog-diagnostic/README.md),
[build reproduction](../../experiments/2026-07-19-keyboard-watchdog-diagnostic/results/final-build-reproduction-20260719.txt),
[guarded write/readback](../../experiments/2026-07-19-keyboard-watchdog-diagnostic/results/boot2-write-candidate-v-20260719.txt),
and [runtime evidence](../../experiments/2026-07-19-keyboard-watchdog-diagnostic/results/runtime-candidate-v-attempt-1-20260719.txt).

The exact active 3.18 binary now supplies the decisive controller comparison.
It resets GPIO58 low for 5 ms and high for 5 ms, then issues the same two-message
register read needed by regmap. Its MT6797 I2C master recognizes that pair as
WRRD without a compatibility gate and writes the receive length to auxiliary
offset `0x6c`. V has no direct `mediatek,mt6797-i2c` driver match and therefore
selects `mt6577_compat`, whose disabled auto-restart suppresses WRRD and whose
`aux_len_reg = 0` does not describe that working binary. Latest checked bsg100
`main`, revision
[`60f5f4ac777a0aeccc89b5d3a4f8cd1f1ebe57b3`](https://github.com/bsg100/gemini-linux/commit/60f5f4ac777a0aeccc89b5d3a4f8cd1f1ebe57b3),
retains hardware evidence that a direct MT6797-to-`mt8173_compat` match fixed
the same combined-read failure before its later working-keyboard builds. See the
[working 3.18 binary/controller audit](../../experiments/2026-07-19-keyboard-watchdog-diagnostic/results/working-3.18-aw9523-i2c-binary-audit-20260719.txt).

Candidate W tested that successor boundary. Its only keyboard-causal
source delta is
`{ .compatible = "mediatek,mt6797-i2c", .data = &mt8173_compat },`; its
Android-v0 image retains V's exact final DTB and therefore V's AW9523 reset
timing, regmap-cache policy, I2C frequency, matrix polling, no-IRQ watchdog, and
ramoops. A generic WRRD guard-only change under `mt6577_compat` remains outside
the test because it retains the wrong auxiliary-length policy. Observation-only
changes keep kernel messages on fixed tty2, respawn the foreground shell on
tty1 without background marker fanout, make the test token letters-only, and
compile and force the larger `TER16x32` font. Two clean W packages match after
normalizing only timestamp provenance, two final assemblies match recursively,
and the mutation suite passes 24/24. The W initramfs SHA-256 is
`3793bec7a63074b237d041bcd42e6edfccc80f0a3d7b19869abf99ee7874dac6`;
the raw 6,866,944-byte boot image SHA-256 is
`34c41fad1e86de05b6a1f64f7e5d9229bd26ea88d982b0a57f2b9573aeb782d4`.
The guarded helper installed that exact image without reboot to live-resolved
logical `boot2`; the padded candidate, remote post-flush checksum, and full
local readback match SHA-256
`0ff3220096aa53f792116b3899e356bc2516816c9c330309c3d81e9fe1446608`.
The owner selected exact W once. Retained `console-ramoops` proves that the
I2C controller bound, client `0-005b` probed successfully and bound
`aw9523-pinctrl`, and the initially deferred matrix subsequently bound
`matrix-keypad` and registered `/dev/input/event0`. The bounded no-grab capture
contains press/release records for H, E, L, P, and Enter; Enter appeared four
times and each letter once. The owner independently observed a visible shell
and working keyboard and reported the larger font as perfect. This strongly
supports the direct-controller-match hypothesis for one run while stopping
short of a physical WRRD waveform measurement. W's `pass` marker is absent,
so durable shell-command execution is not established, and the limited event
set proves neither full key coverage nor repeatability.

W did not pass serviceability. Kernel logs were visibly mixed with tty1 despite
the requested tty2 kernel console, and the deliberate userspace watchdog
open/one-ping contract returned the device automatically before useful work.
Exact waits through 30 seconds plus Gemian's `wdt_by_pass_pwk` reason attribute
that return. Candidate X is the observation-only successor: it retains the
exact W kernel/DT/keyboard/font foundation, removes the virtual-console token
and userspace watchdog access, preserves `/dev/kmsg`/ramoops plus serial, and
requires a typed manual-reboot marker. Two clean builds reproduced 220
non-timestamp files, two final X artifacts are recursively identical, all 32 LK
gates passed, and 47/47 mutations were rejected. The 6,864,896-byte raw image
SHA-256 is
`bf4003871daaba1faa293f2b128021d3a67d41ebf3ddff1c42463409803b9296`.
It was installed without reboot to live-resolved logical `boot2`, synchronized,
flushed, and fully read back with padded SHA-256
`e89d71f15465b544db163b5f0b90b456e913c38ba4d2ed49aa7bde345148c855`.
The owner later reported that X booted and worked before typed `reboot` appeared
to hang. Power-key recovery returned to Gemian and pstore was empty. This does
not establish clean tty1, exact X entry, X uptime, or any individual keyboard
subgate; at that stage W remained the last artifact with retained detailed key
events. AA r1 later added retained A/S press-release records. See the
[Candidate W experiment](../../experiments/2026-07-19-keyboard-wrrd-diagnostic/README.md),
[build reproduction](../../experiments/2026-07-19-keyboard-wrrd-diagnostic/results/final-build-reproduction-20260719.txt),
[mutation result](../../experiments/2026-07-19-keyboard-wrrd-diagnostic/results/validator-mutations-20260719.txt),
[write/readback](../../experiments/2026-07-19-keyboard-wrrd-diagnostic/results/boot2-write-candidate-w-20260719.txt),
[runtime result](../../experiments/2026-07-19-keyboard-wrrd-diagnostic/results/runtime-candidate-w-attempt-1-20260719.txt),
[Candidate X experiment](../../experiments/2026-07-19-keyboard-manual-reboot-diagnostic/README.md),
[X build reproduction](../../experiments/2026-07-19-keyboard-manual-reboot-diagnostic/results/final-build-reproduction-20260719.txt),
[X mutation result](../../experiments/2026-07-19-keyboard-manual-reboot-diagnostic/results/validator-mutations-20260719.txt),
[X write/readback](../../experiments/2026-07-19-keyboard-manual-reboot-diagnostic/results/boot2-write-candidate-x-20260719.txt),
and [X runtime](../../experiments/2026-07-19-keyboard-manual-reboot-diagnostic/results/runtime-candidate-x-attempt-1-20260719.txt).

Candidate Y kept the exact X keyboard stack, but the exact BusyBox audit found
that bare `reboot` bypasses its external wrapper and that watchdog-open failure
cannot reach the intended refusal. Y was never booted and adds no keyboard
runtime evidence.

Candidate Z keeps the exact Y keyboard stack and changes four initramfs members
plus adds read-only `bin/reboot-dispatch.env`. Two complete builds match
recursively, the exact-BusyBox Linux-arm64 dispatch gate, all 32 LK gates, and
75/75 mutations passed, and exact Z was fully read back from logical `boot2`.
In one owner-attended selection Z booted, the keyboard still worked, and its
typed watchdog reboot returned the device to Gemian. A changed boot ID plus
`androidboot.bootreason=wdt_by_pass_pwk` corroborate a watchdog-class reset.
No exact Z marker, live dispatch output, individual-key trace, countdown timing,
or complete map test survived, so Z added no detailed event coverage beyond W;
AA r1 later added retained A/S press-release events. Full coverage and
repeatability remain open. See the [Y rejection](../../experiments/2026-07-19-keyboard-typed-watchdog-reboot-diagnostic/results/preboot-command-dispatch-audit-20260720.txt),
[Z experiment](../../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/README.md),
[build validation](../../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/results/build-validation-20260720.txt),
[dispatch validation](../../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/results/ash-dispatch-validation-20260720.txt),
[mutation result](../../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/results/validator-mutations-20260720.txt),
[write/readback](../../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/results/boot2-write-candidate-z-20260720.txt),
and [runtime result](../../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/results/runtime-candidate-z-attempt-1-20260720.txt).

Candidate AA r0 is historical. It preserved exact Z's kernel field, final DTB,
configuration, AW9523/matrix path, font, and typed-watchdog recovery, but its
2,055-byte, seven-table map omitted the documented Shift+Fn F1–F10 layer and
its BusyBox `dumpkmap` byte comparison could not be a valid live-map oracle.
Its immutable raw-image, map, and historical 16 MiB `boot2`/readback SHA-256
values are respectively
`a2ad7a4107abd99cbd349b8f2deadd0185cbdd5bb0884ecbdae8ff2a7499ed4c`,
`48f1f61a9ad8ba327a3105c0dfbbc698c1e55bb3bcca695b46887888be8ca821`,
and `157c7cd5d814d7b2704d679faacd3215c5e889642b4261441f99653957585eaa`.
R0 was superseded before selection. Do not boot it; its completed [build
validation](../../experiments/2026-07-20-keyboard-console-map-diagnostic/results/build-validation-20260720.txt)
and [write/readback](../../experiments/2026-07-20-keyboard-console-map-diagnostic/results/boot2-write-candidate-aa-20260720.txt)
are r0 evidence only.

AA r1 is the current built, validated, installed, and hardware-tested
console-policy candidate. It retains exact Z's kernel field, final DTB, and
resolved configuration. Its deterministic 2,311-byte
BusyBox map is generated from the checksum-pinned Linux v7.1 default, contains
eight tables, changes exactly 53 semantic entries, and has SHA-256
`02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c`.
The physical Fn keycode 125 becomes VT `K_ALTGR`. Plain/Shift backslash emits
`\\|`; Ctrl produces the standard file-separator control value and Alt emits
meta-backslash, while unsupported Shift+Ctrl and Ctrl+Alt combinations remain
`K_HOLE`. The punctuation keys emit `,/` and `.?`; Fn supplies the photographed
printable/navigation layer, U+263A WHITE SMILING FACE, Caps Lock, Home, Page
Up, Page Down, and End; Shift+Fn digits 1 through 0 emit F1 through F10.
Explicit Shift, Ctrl, Alt, and Fn release semantics prevent a modifier from
sticking across the new tables.

Before exposing `GEMINI-AA-R1#`, the respawn-safe runtime sets and reads back
tty1 `K_UNICODE`. It first accepts a previously loaded exact map; otherwise it
requires exactly the seven inherited source tables before `loadkmap`. The
post-load helper uses `KDGKBENT` to verify all 2,048 entries across the eight
declared kernel tables: all 1,024 serialized payload entries must match except
the documented table-3 keycode-0 normalization from payload `K_HOLE` to kernel
`K_ALLOCATED`, every untouched upper-half entry must be `K_HOLE`, and every
undeclared table must remain absent. Failure exposes only
`GEMINI-AA-R1-KEYMAP-FAIL#` with Z recovery. Source generation and local
semantic tests pass. The recovery-VM canonical static AArch64 verifier is
SHA-256
`29735d212e74d0b0040a3ead173a83223b89ce5d947b697a115707eb3d23b238`.
Two clean constructions are recursively byte- and metadata-identical; the raw
7,378,944-byte artifact is SHA-256
`37e82bf3be87dd9e52fb8d60597b69f92a5c0dc5aebd51d178f1e7efd33343d7`.
The guarded installer required exact r0 padded predecessor
`157c7cd5d814d7b2704d679faacd3215c5e889642b4261441f99653957585eaa`,
preserved a private full backup, resolved live-GPT `boot2` as
`/dev/mmcblk0p30` with root on `/dev/mmcblk0p29`, and fully read back padded r1
as SHA-256
`38b49c7c19c2d97fa0c48436545219489221aa367aedf491ae6ebd4ec4856703`.
The installation did not reboot.

Attended attempt 1 passed. Retained pstore records the exact map gate at
2.407618 seconds with `origin=loaded-now`, tty1 `K_UNICODE`, all 2,048 kernel
entries exact, untouched upper halves as holes, all undeclared tables absent,
table 3 allocated, `GEMINI-AA-R1#`, and validated reboot dispatch. The owner
reported that the new keymap worked and that the rest of the session was fine.
The same retained record contains exact AW9523/matrix/event0 identity and A/S
press-release events.
Bare `reboot` was requested at 126.258967 seconds, proving more than 123
seconds without automatic watchdog ownership. The inherited wrapper then
opened and pinged the 31-second watchdog once, held fd 3, and logged
5/10/15/20/25/30-second countdown checkpoints. The changed post-return boot ID
and Gemian `boot_reason=4`, `androidboot.bootreason=wdt_by_pass_pwk`, and
`powerup_reason=reboot` corroborate recovery. F1–F10 and Page Up/Page Down
remain unconfirmed—not failed—because the console offered no visible
discriminator. The private capture manifest is SHA-256
`d18eff262b66af21ee5cd61b05fd2f25b8b107187564774001f09ae3d9765a6a`.
Media, brightness, phone, airplane-mode, launcher, voice-assistant, and Sym
remain userspace policy. See
the [AA experiment](../../experiments/2026-07-20-keyboard-console-map-diagnostic/README.md),
r1 [build validation](../../experiments/2026-07-20-keyboard-console-map-diagnostic/results/build-validation-aa-r1-20260721.txt),
[installer validation](../../experiments/2026-07-20-keyboard-console-map-diagnostic/results/installer-validation-aa-r1-20260721.txt),
[guarded write/readback](../../experiments/2026-07-20-keyboard-console-map-diagnostic/results/boot2-write-candidate-aa-r1-20260721.txt),
[layout reference](../../experiments/2026-07-20-keyboard-console-map-diagnostic/results/layout-reference-aa-r1-20260721.txt),
and [runtime result](../../experiments/2026-07-20-keyboard-console-map-diagnostic/results/runtime-candidate-aa-r1-attempt-1-20260721.txt).

Candidate AB passes the separate proper-restart gate once on the current
Gemini unit. Patch 0087 assigns priority 255 only to MT6797's TOPRGU restart
notifier, ahead of PSCI priority 129; every other supported MediaTek SoC
retains priority 128. Two clean post-fix kernel packages reproduced after
pinning `KBUILD_BUILD_VERSION=1`, and two complete AA-r1-derived containers
were recursively byte- and mode-identical. The container preserves AA r1's
exact DTB, AW9523/matrix path, 2,311-byte map, verifier, font, and recovery
observability while removing userspace-watchdog ownership, countdown, and
automatic-reset policy.

The exact AB marker and map gate survived in pstore. The owner reported the
keyboard/map working, waited at least 45 seconds without an automatic reset,
then typed bare `reboot` and observed the reset trigger immediately. The
retained request is timestamped 66.021584 seconds and the final kernel
`reboot: Restarting system` line 66.049438 seconds. Their 27.854 ms difference
measures request-marker to final retained kernel line, not Enter-to-LK-splash
latency. Gemian returned with a changed boot ID. No userspace watchdog open,
ping, countdown, fallback, or automatic reset exists in this candidate. The
Gemian `wdt_by_pass_pwk` reason is a nondiscriminating watchdog-block class on
this SoC, so command ownership, timing, exact artifact identity, and selected
restart-handler ordering carry the attribution.

The directly observed result is one successful ordinary restart on this named
unit. Selection of the priority-255 TOPRGU notifier over PSCI is the
high-confidence explanation supported by the exact patch and artifact, not a
separately traced notifier callback. The working 3.18 keyboard/controller path
remains prior evidence for the I2C/AW9523 contract rather than evidence for
AB's restart handler. F1–F10 and Page Up/Page Down remain unconfirmed, not
failed; restart repeatability and broad MT6797 reliability are not established.
See the [AB experiment](../../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/README.md)
and exact [attempt-1 runtime result](../../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/runtime-candidate-ab-attempt-1-20260721.txt).

AW9523, matrix bind, an exact event node, and the listed bounded key events are
now credited for one W run. AA r1 adds one owner-confirmed new-map run plus the
exact loaded-map oracle and a >123-second idle interval. Wake, LED control,
complete legend coverage, and repeatability remain later gates. The older
bounded matrix protocol
and historical non-claim remain in
[`keyboard-next-gate-20260714.txt`](../../experiments/2026-07-12-input-backlight-recovery/results/keyboard-next-gate-20260714.txt).

The bsg100 result includes successful physical typing on its Gemini unit, a
53-key base set, and an AltGr Fn layer. It corroborates the AW9523 address and
matrix architecture plus the userspace function-layer boundary, but it does
not identify this unit's live evdev Fn code or prove that its source/build and
electrical behavior match. It remains cross-device evidence, not a substitute
for a later attributable named-device test.

See the [input/backlight experiment](../../experiments/2026-07-12-input-backlight-recovery/README.md),
[vendor-kernel ABI matrix](vendor-kernel-abi.md#input-and-keyboard), and
[Gemian baseline](gemini-gemian-baseline.md).
