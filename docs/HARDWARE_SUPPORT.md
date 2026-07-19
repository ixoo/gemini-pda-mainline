# Hardware support matrix

This matrix separates what runs on real hardware from what exists upstream. A compile-only result is not runtime support, and a local hardware result is not upstream support.

Detailed component facts and provenance belong in the
[hardware knowledge base](hardware/README.md). Reproducible investigations and
their associated code belong in [`experiments/`](../experiments/README.md).
The [Gemian hardware baseline](hardware/gemini-gemian-baseline.md) records
vendor-kernel component and wiring evidence without promoting it to current
mainline runtime support.

Current handoff note (2026-07-16): the focused package
`linux-7.1.3-gemini-handoff-6116c9e7-f43cb03c` supplied the first corrected
test artifact. It uses one CPU, an external Android-v0 ramdisk containing a
storage-inert static
BusyBox initramfs, exact little-endian/4 KiB/relocatable ARM64 flags,
`kernel_addr=0x40200000`, and packaging-only LK DT compatibility overlays. The
strict Android-v0/LK parser and full package
checksums pass, and two independent candidate builds are byte-identical. The
display candidate SHA-256 is
`37e9be6a597dbcb690d5a57fb5d88ba038529b07cbe1b449456855e60e1fa82a`;
the mandatory-only candidate is
`e314c1b2eaba065289d416ad5c507d9d7a44b97d70c8647f7fd55c797d4451e5`.
The display candidate was selected from `boot2` with the silver button for one
controlled attempt. The owner observed a dark screen, no serial output, no
initramfs marker or interaction, and no boot loop. That last observation is a
useful difference from earlier looping attempts, but it cannot distinguish a
running kernel from a silent early hang or panic; Linux runtime remains
`unknown`.
See the [LK handoff alignment experiment](../experiments/2026-07-16-lk-handoff-alignment/README.md).

Current USB diagnostic note (2026-07-16): patches 0077–0078 add an opt-in
forced B-device session property and disabled Gemini MTU3 peripheral wiring.
The separate [USB gadget diagnostic](../experiments/2026-07-16-usb-gadget-diagnostic/README.md)
enables only that peripheral test path in its candidate overlay. The exact
image was synchronized, fully read back, and tested from `boot2`; the device
remained dark and steady while two bounded host checks found no USB child. This
is a failed enumeration test, not proof that Linux did not execute. Later
retained exact Candidate M and N console-ramoops records independently prove
that the 11290000 T-PHY and 11271000 MTU3 probes returned zero, the forced
B-device session ran, built-in `g_ether` reported ready, and MTU3 logged its high-speed
gadget pull-up action. That promotes only the low-level gadget registration
path; it is not an electrical D+ measurement. No host enumeration, selected
configuration, network interface, carrier, IP traffic,
or remote shell has been observed. See the
[sanitized retained-pstore result](../experiments/2026-07-16-usb-gadget-diagnostic/results/retained-pstore-mtu3-gadget-evidence-20260718.txt).

A [timed-reboot follow-up](../experiments/2026-07-16-timed-reboot-diagnostic/README.md)
retains that exact kernel and DTB and changes only external initramfs `/init`.
Its first boot began dark with the backlight on, later entered an off-like state
with the backlight off, and did not restart automatically. Manual power-key
start was required. The one-file delta makes `/init`, timer, and restart-path
execution strong but indirect evidence, not confirmation: the owner later
estimated 5–10 seconds from backlight-on to backlight-off, compatible with the
10-second timer, but no stopwatch measurement, repeat, or candidate log
survived. Gemian sets TOPRGU mode bit 4 to bypass the power key
for normal reboot; mainline preserves its inherited value. PSCI off/key-gating,
a successful TOPRGU reset waiting for the key, and a quiesced failed reset
remain unresolved. The following Gemian boot reported `power_key` and no
watchdog, exception, or battery-removal flag, which is compatible with a
key-gated reset. No support-matrix state is
promoted by this result, and it establishes neither USB host mode, VBUS,
Type-C policy, nor charging behavior.

A [deterministic screen-marker follow-up](../experiments/2026-07-16-screen-marker-diagnostic/README.md)
now reconstructs exact candidate D, retains its byte-identical `Image.gz`, adds
only the allowlisted LK simple-framebuffer node, and replaces the reset timer
with one fail-closed `0x8f7000`-byte `/dev/fb0` fill. Two independent builds
are byte-identical and exported with complete checksums. The candidate was
written, flushed, and fully read back from non-primary `boot2`. Its first
owner-run boot remained black and showed none of the expected bands. The
positive marker test therefore failed, but no runtime state is promoted:
kernel entry, simplefb binding, the framebuffer write, and retained LK scanout
remain indistinguishable because the node names no display clocks and Linux
may disable unclaimed loader clocks before userspace.

A focused audit of bsg100 commit `035d4b0` supplies a concrete next
discriminator: its hardware history observed unused-clock cleanup gating
`CLK_INFRA_DISP_PWM` and `pwm_sel`, which extinguished the LK-retained
backlight. Candidate F now keeps Candidate E's exact Image, initramfs and marker
while adding only a path-resolved simplefb
`clocks = <&infrasys CLK_INFRA_DISP_PWM>;` reference. Its two builds are
byte-identical and its synchronized `boot2` write has a matching full readback.
On the first attended boot, sideways console text moved across the display for
about one second before black. This is the first positive visual Linux 7.1.3
handoff signal and strongly supports kernel entry plus simplefb/fbcon output;
the unread text does not independently prove `/init`. Candidate G retains F's
exact kernel and DTB, removes all raw framebuffer access through an
initramfs-only delta, and reproduced sideways scrolling for 1–2 seconds before
black with the backlight apparently off. Because G never accesses `/dev/fb0`,
this rejects Candidate F's raw overwrite as the cause; the unread output still
does not attribute execution to `/init`. Candidate H preserves Candidate G's
exact kernel and initramfs and appends only `CLK_TOP_MUX_MM` to simplefb's
existing `CLK_INFRA_DISP_PWM` clock list. In one owner-attended series, two
attempts visibly progressed farther and the owner approximately recognized H's
initramfs-only marker; the backlight stayed on while text was visible and went
off at the black transition. Later attempts did not reproduce the visible
progress. This strongly attributes those visible attempts to external `/init`,
but does not establish stable retention. Candidate I keeps H's exact
kernel/DTB and exact initramfs tree except `/init`, which emits one tty0 line
per second through `T+60` before a silent static hold. It is built reproducibly,
exported, synchronized and fully read back from `boot2`; the reported intended
selection went directly to black with no I marker, counter, or other text.
Because attempts, backlight, final state, and recovery were not recorded,
selection and `/init` remain unconfirmed and the timing hypothesis is untested.

Candidate J rebuilds that kernel to append `clk_ignore_unused` to forced
`CONFIG_CMDLINE`, retaining exact I's DTB, initramfs, and Android header command
line. A header-only draft was rejected as a no-op under
`CONFIG_CMDLINE_FORCE=y`. Its raw SHA-256 is
`6d5bad08c2f93eba7fbd66ea5c54de2437f81e44832426a97d4d65d550c659f4`;
an isolated clean rebuild reproduced the config, kernel payload, `System.map`,
all 119 DTBs, and boot image byte-for-byte. It was synchronized to logical
`boot2`; that full 16 MiB target and local readback matched SHA-256
`465e4c747138e12191d38fd6b4cde68cd0b9a19f918030dea05c9b8dbdd4d3fc`.
No reboot was part of the write. On the first later owner-attended intended
`boot2` selection, the last visible suffix before the screen became black was
reported as `4/60`. Only the tracked shared I/J `/init` emits that counter, so the
verified write/readback and intended selection strongly support kernel entry,
visible fbcon/tty0 output, and `/init` reaching tick 04 in this attempt. The full
line and marker were not exactly transcribed. A later two-bullet report is
provisionally interpreted as two additional intended J/`boot2` selections
because its outcomes are mutually exclusive, with owner confirmation pending.
One reached "iteration 4" before black, compatible with and corroborating tick
04 without an exact marker transcription. One went directly black with no
console and cannot establish selected slot, kernel entry, or `/init`.
Provisionally, two of three intended selections had tick-04-compatible visible
output and one of three was no-console and unattributable. Stable visibility,
causality, and any clock identity remain unestablished. The control does not
enable already-off clocks, prevent explicit disables, or retain regulators or
power domains. That exact J kernel compiles fbcon rotation out; later isolated
Candidate P established readable normal-landscape loader fbcon in one run.
None of this is native display support or proof that every
scanout clock is known. See the
[first runtime](../experiments/2026-07-17-clk-ignore-unused-diagnostic/results/runtime-candidate-j-attempt-1-20260717.txt)
and [repeat](../experiments/2026-07-17-clk-ignore-unused-diagnostic/results/runtime-candidate-j-repeat-report-20260717.txt)
records. Further J repetition is stopped; no matched-I rollback is authorized
by the standing `boot2` opt-in. Candidate K was a reproducible exact-J
initramfs-only derivative and its write/readback remains historical evidence,
but a strategy review cancelled it without a runtime selection: it has no
kernel, DT, or configuration delta and would not change the next action.
[Candidate L](../experiments/2026-07-17-uart-pstore-observability/README.md)
was the reproduced-and-written observability gate that added UART0
GPIO97/98 pinmux, an exact mainline-console/active-Gemian primary
`console-ramoops` alignment, and MT6797 watchdog auto-restart plus IRQ-dependent
dual-stage policy. A distinct fresh-source build reproduced all non-timestamp
package and candidate content, and the exact padded image was synchronized,
block-flushed, and fully read back from logical `boot2`. Mainline pmsg is not
cross-version evidence; its enlarged allocation supplies address alignment.
Attempt 1 showed LK splash then black and was unattributable. Attempt 2 showed
console output through exact suffix `remaining 5s`, unique to Candidate L's
tracked `watchdog0=waiting` initramfs loop. Kernel, loader-simplefb/fbcon,
devtmpfs, and `/init` entry are strongly supported for that attempt, while
`/dev/watchdog0` was absent at the last visible check. Connected serial was
silent. Manual recovery was required and immediate pstore was empty.

[Candidate M](../experiments/2026-07-18-watchdog-registration-diagnostic/README.md)
then retained L's exact kernel, removed only the optional bark IRQ as its
hardware hypothesis, and passed its first runtime decision oracle. Its exact
marker survived into Gemian's `console-ramoops`: the no-IRQ `mtk-wdt` probe
succeeded, `/dev/watchdog0` was armed at a 31-second timeout, and progress
reached 30 seconds before the owner-observed automatic return. Gemian's
watchdog boot reason and PMIC flags independently confirm the reset. This
promotes only the basic single-stage watchdog and cross-version pstore path;
UART, bark/pretimeout, SMP, storage, USB, and native display remain unproven.

[Candidate N](../experiments/2026-07-18-cpu1-online-diagnostic/README.md)
then retained M's exact kernel, configuration, no-IRQ DTB, watchdog, and pstore
contract while changing only external `/init` to request CPU1 online. Its
surviving exact-marker record proves logical CPU1 mapped to DT `cpu@1`, the
standard hotplug request returned, GICv3 redistributor initialization ran, and
MPIDR `0x1` booted as a Cortex-A53. The online mask changed from `0` to `0-1`,
CPU1 accounting advanced, and it stayed online through the 25-second marker
before the watchdog returned the device to Gemian without owner help. This is
partial runtime support for the first secondary Cortex-A53 only, from one run.

[Candidate O](../experiments/2026-07-18-cortex-a53-sweep-diagnostic/README.md)
then retained N's exact kernel, configuration, DTB, and recovery contract while
changing only external `/init`. Its surviving exact-marker record proves the
standard hotplug requests for CPU1–7 all returned: every target booted with
Cortex-A53 MIDR `0x410fd034`, initialized its GICv3 redistributor, advanced
per-CPU accounting, and reached its cumulative pass checkpoint. The final
online mask was `0-7`; CPU8/9 mapped to the two Cortex-A72 nodes but remained
offline and were not written. The collector observed a changed-cycle return to
Gemian, which reported a watchdog-class boot reason. This establishes all
eight Cortex-A53 cores concurrently online by hotplug in one run, not
repeatability, boot-time SMP, stress/coherency, DVFS, idle, thermal behavior,
or either Cortex-A72 `CPU_ON` path.

[Candidate P](../experiments/2026-07-18-fbcon-rotation-diagnostic/README.md)
then changed only the framebuffer-console rotation configuration on exact O
and passed its first attributable run. The owner observed readable text in the
Gemini's normal-landscape orientation, the complete inherited O sweep, and an
unassisted return to Gemian. Post-return `console-ramoops` retains every O CPU
checkpoint, final `online=0-7` success, and both watchdog waits. Collection
began after the return, so it did not span the tested boot-ID transition or
independently capture a reset reason. This establishes one loader-retained
simplefb/fbcon rotation result, not repeatability or native display ownership.
The next gate is the planned, exact-P-based
[Candidate Q keyboard and supervised-shell experiment](../experiments/2026-07-18-keyboard-shell-diagnostic/README.md).

Current build note (2026-07-14): the 72-patch package
`linux-7.1.3-gemini-c2d9eea95daa` remains the baseline for the subsystem audits
below; older package links are historical evidence from earlier integration
states. Its provenance
records patchset SHA-256
`c2d9eea95daa25dd8faddef4f9822e663db67d5d0946f06f0251cc52c92cf08c`, config
SHA-256 `831289dd3b53c6cec09e6c614fd83d3ab5988a4c30090bf9ec172348ec9487d5`,
Image SHA-256 `3fb6ac3043dff85dc2b6e68a2bba26d36fedf748e6f7c1bf6b6630f87446be7c`,
and Gemini DTB SHA-256
`b41580263940b47226e9819c97afbdaa9a35d4c721c471d2e8a0a3d597c553c5`. The
current package uses `modules_built=true` and contains 1,570 `.ko` objects;
the module tree is for later rootfs integration and does not change the
hardware support state.
The latest 77-patch Image/DTB package is
`linux-7.1.3-gemini-6116c9e7da3f` (patchset SHA-256
`6116c9e7da3fc2f56612029236a3bcd370c61f91b3c0951dd4e2c1915537f55e`). It
contains the complete Image and DTB set, has `modules_built=false`, and
includes the disabled-only AW9523 polarity correction in patch 0076. See the
[display/input package record](../experiments/2026-07-12-input-backlight-recovery/results/mainline-display-input-current-77-package-20260714.txt).
The direct [MSDC audit](../experiments/2026-07-12-mt6797-msdc-recovery/results/mainline-msdc-current-77-package-20260714.txt)
and [PMIC audit](../experiments/2026-07-11-mt6351-pmic-recovery/results/mainline-mt6351-current-77-package-20260714.txt)
confirm the same package's conservative storage and stateful power-management
boundaries. The candidate was written to the explicitly selected non-primary
`boot3` partition (`/dev/mmcblk0p31`) and the full 16 MiB target read back with
a matching SHA-256. It was not independently boot-tested before a later image
replaced those partition bytes; this write therefore does not change the
hardware support state. See the [boot3 write record](../experiments/2026-07-15-boot3-mainline-write/README.md).
The keyboard timing comparison confirms that the vendor AW9523 path uses a
1-ms IRQ delay, a 1-ms first scan, and 10-ms/100-Hz rescans for up to 100
cycles, while Linux `gpio-matrix-keypad` has optional debounce/settling
properties and no periodic rescan. The current candidate deliberately omits
those properties until a named-device event trace measures bounce and
settling; see the [keyboard timing contract](../experiments/2026-07-12-input-backlight-recovery/results/keyboard-timing-contract-20260714.txt).
The disabled keyboard candidate also lacks a selected MT6797-side default
pinctrl state for its GPIO58 reset and GPIO87/EINT10 interrupt lines. A retained
independent-project audit reports that an equivalent omission regressed its USB
gadget path and that referencing its defined AW9523 pin state restored keyboard
and USB coexistence. Treat that as cross-device integration evidence, not proof
of identical electrical causality: the first enabled candidate must use a
source-backed SoC state and retain USB gadget registration as a regression
gate. See the [keyboard hardware record](hardware/keyboard.md#soc-pinctrl-and-usb-coexistence-boundary).
The matching 77-patch private LK-compatible gzip+appended-DTB candidate is
`guest:~/artifacts/boot-candidates/20260714-77-diagnostics4/linux-7.1.3-gemini-6116c9e7da3f.boot.img`;
its candidate SHA-256 is
`4cc0cc0df784e7ff79633884e2b093e3c2bc1d9c6f74f01af972a7034e88997c`. The
sanitized parser record is the [77-patch LK candidate diagnostics result](../experiments/2026-07-12-boot-contract-recovery/results/mainline-77-lk-candidate-diagnostics-current-20260714.txt).
The candidate is no longer VM-private: it was written to `boot3`
(`/dev/mmcblk0p31`) and read back with a matching full-partition checksum. It
was not independently boot-tested before being replaced, so this does not
change the runtime support state. See the
[boot3 write record](../experiments/2026-07-15-boot3-mainline-write/README.md).
A later framebuffer-console prototype was written and read back on `boot2` and
`boot3`. The owner attempted to boot it, but the exact selection method was not
captured and no loader, Linux, console, or initramfs marker attributable to the
prototype was observed; the later live snapshot showed the vendor 3.18 kernel.
That result is inconclusive, not a mainline boot. See the
[display-console experiment](../experiments/2026-07-15-display-console-recovery/README.md).
The prior 76-patch Image/DTB package is
`linux-7.1.3-gemini-db59a88057b4` (patchset SHA-256
`db59a88057b4c0505cf6dfd80e990f38b74eb0e2a855799d926cf1d20e681306`). It
contains the complete Image and DTB set, but `modules_built=false`; this does
not change the hardware support state. See the [package record](../experiments/2026-07-12-input-backlight-recovery/results/mainline-display-input-current-76-package-20260714.txt).
That package also has a regenerated private LK-compatible gzip+appended-DTB
candidate; the diagnostic parser result is recorded in the [76-patch LK
candidate record](../experiments/2026-07-12-boot-contract-recovery/results/mainline-76-lk-candidate-diagnostics-current-20260714.txt).
It remains untransferred, unflashed, and unbooted, so it does not change the
runtime support state.
The current 77-patch Gemini and three-board MT6797 schema/first-boot audit is
recorded in the [first-boot package result](../experiments/2026-07-14-first-boot-probe-audit/results/first-boot-probe-audit-current-77-package-20260714.txt);
it passes statically but does not claim a boot or probe.
The matching [CPU/PSCI/timer audit](../experiments/2026-07-13-cpu-psci-timer-recovery/results/mainline-cpu-psci-timer-current-76-package-20260714.txt)
preserves all ten generic CPU nodes; the vendor `maxcpus=5` and console policy
remain LK observations awaiting a mainline boot capture.
The focused keyboard/hall follow-up is package
`linux-7.1.3-gemini-a21fac4139df` (75 patches, patchset SHA-256
`a21fac4139dfff0f448d5e8a30a15530bf3c9bb8ae7d04f17355062478c857e3`). It adds
only the disabled hall `gpio-keys` candidate and `CONFIG_KEYBOARD_GPIO=m`; the
keyboard matrix remains a disabled AW9523/gpio-matrix-keypad consumer. Its
package audit is [here](../experiments/2026-07-12-input-backlight-recovery/results/mainline-display-input-current-75-package-20260714.txt).
The current SPI working series adds patches 0072–0073 and was rebuilt as
`linux-7.1.3-gemini-c2feb465d6c6` (74 patches, patchset SHA-256
`c2feb465d6c6debf6f333516ce360cf8a1259da5dde631e828e7efac92ed33ae`). Its
SPI-specific validation passed package, DTB, and focused binding checks, but all
six MT6797 SPI nodes remain disabled and no mainline runtime transfer or boot
has been tested; see the [SPI patch validation](../experiments/2026-07-14-upstream-mt6797-coverage-audit/results/spi-mainline-patch-validation-c2feb-20260714.txt).
The current 74-patch package and private LK candidate provenance are recorded
in the [integration result](../experiments/2026-07-13-kernel-integration/results/mainline-74-patch-current-20260714.txt)
and [LK candidate result](../experiments/2026-07-12-boot-contract-recovery/results/mainline-74-lk-candidate-current-20260714.txt).
The current TOPRGU watchdog boot-policy check is recorded in the [72-patch
watchdog audit](../experiments/2026-07-12-mt6797-watchdog-recovery/results/mainline-watchdog-current-72-policy-20260714.txt).
The current MT6797 thermal/AUXADC package-policy check is recorded in the
[72-patch thermal audit](../experiments/2026-07-13-mt6797-thermal-recovery/results/mainline-thermal-current-72-policy-20260714.txt);
the thermal and AUXADC consumers remain disabled.
The current connectivity package boundary is recorded in the [authoritative
package audit](../experiments/2026-07-12-connectivity-wmt-recovery/results/mainline-connectivity-current-package-20260714.txt);
the older source-transport validation below uses a superseded package and is
historical evidence.
The current PMIC/pwrap live and package recheck is recorded in the [MT6351
validation](../experiments/2026-07-11-mt6351-pmic-recovery/results/mainline-mt6351-current-77-package-20260714.txt);
older PMIC package links below are historical.
For review convenience, the authoritative current-package audit set is:
[package delta from the prior audit set](../experiments/2026-07-14-mainline-module-closure-audit/results/package-delta-a9a7-to-c2d9-20260714.txt),
[handoff](../experiments/2026-07-13-mainline-handoff-closure/results/handoff-closure-current-72-package-20260714.txt),
[ownership](../experiments/2026-07-14-live-kernel-ownership-audit/results/live-kernel-ownership-current-72-package-20260714.txt),
[display/input](../experiments/2026-07-12-input-backlight-recovery/results/mainline-display-input-current-72-package-20260714.txt),
[MSDC](../experiments/2026-07-12-mt6797-msdc-recovery/results/mainline-msdc-current-77-package-20260714.txt),
[USB](../experiments/2026-07-12-usb-typec-recovery/results/mainline-usb-current-72-package-20260714.txt),
[audio](../experiments/2026-07-12-audio-afe-recovery/results/mainline-audio-current-72-package-20260714.txt),
[charger](../experiments/2026-07-12-charger-power-recovery/results/mainline-charger-current-72-package-20260714.txt),
[PM/DVFS](../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/results/mainline-pm-current-72-package-20260714.txt),
[sensors](../experiments/2026-07-12-sensor-iio-recovery/results/mainline-sensors-current-72-package-20260714.txt),
[GPU/Panfrost](../experiments/2026-07-12-mt6797-gpu-panfrost-recovery/results/mainline-panfrost-current-72-package-20260714.txt),
[connectivity](../experiments/2026-07-12-connectivity-wmt-recovery/results/mainline-connectivity-current-77-package-20260714.txt),
[CCCI/modem](../experiments/2026-07-13-modem-ccci-recovery/results/mainline-ccci-current-77-package-20260714.txt),
[camera/media](../experiments/2026-07-13-camera-recovery/results/mainline-camera-current-77-package-20260714.txt),
[current 74-patch first-boot dependency](../experiments/2026-07-14-first-boot-probe-audit/results/first-boot-probe-audit-current-74-package-20260714.txt),
[current 74-patch MT6797 schema](../experiments/2026-07-14-first-boot-probe-audit/results/mt6797-dtb-schema-bounded-current-74-20260714.txt),
[watchdog](../experiments/2026-07-12-mt6797-watchdog-recovery/results/mainline-watchdog-current-72-policy-20260714.txt),
and [thermal/AUXADC](../experiments/2026-07-13-mt6797-thermal-recovery/results/mainline-thermal-current-72-policy-20260714.txt).
The package's built-in versus optional-module closure is recorded in the
[module-closure audit](../experiments/2026-07-14-mainline-module-closure-audit/results/module-closure-current-72-20260714.txt);
it is a rootfs/initramfs availability result, not runtime support.
The current transport/firmware reconciliation is separately recorded in the
[72-patch boundary audit](../experiments/2026-07-14-transport-firmware-boundary-audit/results/transport-firmware-boundary-current-72-20260714.txt).
Any `current-71` result names retained in the matrix are historical evidence
or source-validation records, not the authoritative package provenance.
The subsystem audit files that still name the superseded `a9a7c5002038`
package remain content evidence; the package-delta result proves that the
corrected `c2d9eea95daa` artifact leaves their unrelated module and DTB inputs
unchanged while changing only the intended NT36672E module.
The [first-boot probe dependency audit](../experiments/2026-07-14-first-boot-probe-audit/README.md)
also confirms that the conservative eMMC path consumes MT6351 supplies and
therefore remains write-capable at probe time.
The direct 76-patch MSDC audit also records the exact built-in config and
generated DTB contract: 8-bit, non-removable, 25 MHz eMMC on VEMC/VIO18 with
MSDC1 disabled and no HS200/HS400 flags. This is package evidence only; no
mainline storage probe or I/O has run on hardware.
The current UART console contract audit confirms that `serial0` and
`stdout-path` select UART0, the linked driver symbols are present, and the
mainline console should use `ttyS0`; the vendor `ttyMT0` name and AP-DMA path
remain deferred. See [the current 77-patch console result](../experiments/2026-07-13-uart-console-recovery/results/mainline-console-contract-current-77-20260714.txt).

The [kernel configuration gap audit](../experiments/2026-07-12-kernel-config-gap-audit/README.md)
compares the live vendor config with the prepared Linux 7.1.3 configuration;
vendor-only symbols are not treated as missing drivers without a matching
register, resource, and ABI contract. Its [current 72-patch report](../experiments/2026-07-12-kernel-config-gap-audit/results/current-validation.txt)
records 351 vendor-enabled options, 96 matched options, 22 built-in/module
deltas, and 233 vendor-only names after classifying the fragment's explicit
unset policy separately.

## State definitions

Runtime state:

| State | Meaning |
| --- | --- |
| `unknown` | No reproducible current-mainline result recorded |
| `enumerates` | Driver probes or device is visible, but function is not established |
| `partial` | Some intended behavior works with documented gaps |
| `working` | Acceptance test passes on named hardware and kernel revision |
| `stable` | Released upstream code passes a documented regression protocol |
| `regressed` | A previously passing protocol now fails |
| `not-applicable` | Hardware is absent on this variant |

Upstream state:

| State | Meaning |
| --- | --- |
| `missing` | Required support is not known upstream |
| `local` | A temporary local change exists |
| `RFC` | A public request-for-comments series exists |
| `submitted` | Patch series is under formal upstream review |
| `accepted` | Maintainer tree contains the change |
| `released` | A tagged upstream kernel contains the change |

Firmware boundary:

| State | Meaning |
| --- | --- |
| `none` | No separately loaded firmware known |
| `required-free` | Redistributable firmware required |
| `required-nonfree` | Device firmware is required but not freely redistributable |
| `unknown` | Boundary or license is not established |

## Initial matrix

All runtime states below are intentionally conservative. Historical results are listed as evidence to reproduce, not promoted to `working`.

Keyboard provenance update (2026-07-14): the exact active boot ELF, reconstructed
from the captured active boot payload, compiles the physical `(row=4,col=3)`
record as `KEY_LEFTMETA` and retains `KEY_UNKNOWN` at `(row=7,col=3..6)`.
Patch 0054 now follows that active-boot-normalized map; the retained source
checkout's `KEY_FN` entry is preserved as a documented source/build discrepancy.
The consumer remains disabled and the physical press/release, modifier,
rollover, wake, and electrical timing tests remain unperformed. See the
[active ELF result](../experiments/2026-07-12-input-backlight-recovery/results/active-aw9523-elf-keymap-20260714.txt)
and [current map validation](../experiments/2026-07-12-input-backlight-recovery/results/keymap-consistency-active-boot-20260714.txt).

| Subsystem | Component / candidate | Variants | Bus or SoC block | Mainline basis/dependency | Runtime | Upstream | Firmware | Evidence / next gate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Boot | Planet LK development path | all | boot chain | Retained Android 8 LK requires `bootopt=64...`, gzip plus an appended DTB, its pre-jump CPU/reserved-memory/SCP DT shapes, and a decompressed payload within the MT6797 50 MiB buffer. The stock Gemian Image uses `text_offset=0x80000` with `kernel_addr=0x40080000`; the current Image uses `text_offset=0` and the header-derived `0x40200000`, satisfying the 2 MiB arm64 placement rule. The storage-inert handoff package and diagnostic wrappers pass exact flags, DT-delta, Android-v0 layout/ID, gzip/FDT, size, checksum, and reproducibility gates. Candidate M completed the first observable recovery cycle; N brought CPU1 online; O preserved the exact foundation while bringing all seven secondary Cortex-A53s online through standard hotplug and returning through the same recovery loop; P preserved that sweep while proving readable normal-landscape fbcon in one run. In the exact captured LK, the observed `boot2` and `boot3` paths pass through hardware-key branches; the bounded audit found no exposed direct Gemian reboot destination for them. The currently supported `boot2` workflow therefore still requires the silver button. This establishes the LK/Linux/initramfs handoff, bounded recovery loop, one-run eight-A53 hotplug path, and loader-retained console rotation, not final post-LK memory mutations, boot-time SMP, storage, UART, USB networking, native display, or general userspace. | `observed` | `missing` | `required-nonfree` | [Current handoff candidate](../experiments/2026-07-16-lk-handoff-alignment/README.md); [Candidate M runtime](../experiments/2026-07-18-watchdog-registration-diagnostic/results/runtime-candidate-m-attempt-1-20260718.txt); [Candidate N runtime](../experiments/2026-07-18-cpu1-online-diagnostic/results/runtime-candidate-n-attempt-1-20260718.txt); [Candidate O runtime](../experiments/2026-07-18-cortex-a53-sweep-diagnostic/results/runtime-candidate-o-attempt-1-20260718.txt); [Candidate P runtime](../experiments/2026-07-18-fbcon-rotation-diagnostic/results/runtime-candidate-p-attempt-1-20260718.txt); [LK software-selection audit](../experiments/2026-07-12-boot-contract-recovery/results/lk-boot2-software-selection-audit-20260718.txt); implement the exact-P-based [Candidate Q keyboard/shell gate](../experiments/2026-07-18-keyboard-shell-diagnostic/README.md) next |
| Boot handoff DT fixups | Retained MT6797 LK FDT contract | all | appended DTB, `/memory`, `/chosen`, `/reserved-memory` | LK early-loads the appended DTB, rewrites model/CPU/memory/chosen/firmware metadata, and appends runtime mblock reservations after an overlap check. The current 72-patch baseline preserves pre-LK dynamic CCCI/CONSYS/SCP-share/SPM reservations and has no static post-LK mblock snapshots; the bounded Gemini-only schema validation passes. Candidate L now strongly supports LK acceptance and Linux `/init` entry with the derived DTB, but the final post-LK rewritten FDT was not captured, so its exact memory and reservation mutations remain untested. | `unknown` | `local` | `required-nonfree` | [LK FDT fixup audit](../experiments/2026-07-13-lk-fdt-fixup-recovery/README.md); [Gemini DTB schema validation](../experiments/2026-07-14-first-boot-probe-audit/results/gemini-dtb-schema-current-72-package-20260714.txt); [Candidate L attempt 2](../experiments/2026-07-17-uart-pstore-observability/results/runtime-candidate-l-attempt-2-20260718.txt); capture the final handoff FDT before enabling DMA consumers |
| CPU topology | 8x Cortex-A53 + 2x Cortex-A72 | all | MT6797 | Live DT exposes ten PSCI-enabled CPUs (MPIDs `0x000`–`0x003`, `0x100`–`0x103`, `0x200`–`0x201`); the authoritative current 72-patch package independently contains ten `enable-method = "psci"` nodes and one `arm,psci-0.2` SMC node. Candidate O retained forced `maxcpus=1`, mapped logical CPU1–7 to `cpu@1`, `cpu@2`, `cpu@3`, `cpu@100`, `cpu@101`, `cpu@102`, and `cpu@103`, and requested each online exactly once through standard hotplug. Every request returned success; the matching MPIDRs booted with Cortex-A53 MIDR `0x410fd034`, each GICv3 redistributor initialized, each target's accounting advanced, and the cumulative mask reached `0-7`. Logical CPU8/9 mapped to Cortex-A72 `cpu@200`/`cpu@201`, remained offline, and were not written. Candidate P retained the exact successful sweep in its one rotation run. This establishes all eight A53s concurrently online by hotplug in one run, but not repeatability, boot-time SMP, stress/coherency, either A72 `CPU_ON`, DVFS, idle, suspend, or thermal behavior. | `partial` | `released` | `unknown` | [CPU/PSCI/timer recovery](../experiments/2026-07-13-cpu-psci-timer-recovery/README.md); [Candidate N runtime](../experiments/2026-07-18-cpu1-online-diagnostic/results/runtime-candidate-n-attempt-1-20260718.txt); [Candidate O runtime](../experiments/2026-07-18-cortex-a53-sweep-diagnostic/results/runtime-candidate-o-attempt-1-20260718.txt); [Candidate P runtime](../experiments/2026-07-18-fbcon-rotation-diagnostic/results/runtime-candidate-p-attempt-1-20260718.txt); retain generic PSCI for the A53 path, keep both Cortex-A72 cores deferred, and keep Q CPU0-only so keyboard/shell results are not coupled to another SMP test |
| CPU frequency / DVFS | Complete vendor `mt-cpufreq`, LL/L/B clusters plus CCI and active EEM/PTP calibration | all | MT6797 ARM PLL/muxes, shared EEM/thermal window, DA9214 Vproc, SRAM tracking, optional DVFSP | Planet source recovers function/date efuse table selection, four levels plus B TT override, direct cluster PLL programming, CCI coupling, and 10--30 mV Vproc/Vsram tracking. Runtime EEM detectors actively rewrite calibrated OPP voltages. Linux 7.1.3 has no MT6797 cpufreq or SVS match; its OPP/regulator/clock-reparent and SVS phase/adjustment patterns are reusable, but the current MT6797 CCF also lacks the vendor ARMPLL/CPU-mux/CCI clock contract. The CPU PLL windows are shared with SPM/ATF through an MCUMIXED hardware semaphore, and B-cluster PLL/SRAM operations use secure BigiDVFS calls, so a dedicated MT6797 clock backend/new driver is justified once those ownership APIs are proven. The local DTS now omits the vendor per-CPU `clock-frequency` hints because Linux 7.1.3's CPU binding rejects them; they remain descriptive evidence only, and the generic cpufreq clock/regulator/OPP contract is still absent. A fresh read-only capture shows the active policy lives under private `/proc/cpufreq` rather than standard `cpufreq/policy*` sysfs, with dynamic LL/L/B/CCI transitions and only CPUs 0–1 online at capture; this is vendor-policy evidence, not a mainline support claim. The current package audit confirms generic cpufreq/SVS modules but no MT6797 consumer, OPP table, or idle-state table; the current 72-patch build remains disabled-only | `observed` | `missing` | `unknown` | [CPU/DVFS recovery](../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/README.md), [runtime CPU policy capture](../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/results/runtime-cpu-policy-20260714.txt), [current PM package validation](../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/results/mainline-pm-current-72-package-20260714.txt), [EEM calibration contract](../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/results/eem-calibration-contract.md), [cpufreq/DTS gap](../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/results/mainline-cpufreq-dt-gap.md), [CPU clock backend source design](../experiments/2026-07-12-mt6797-clock-power-reset-recovery/results/mt6797-cpu-clock-backend.md), [current 72-patch CPU clock audit](../experiments/2026-07-12-mt6797-clock-power-reset-recovery/results/mt6797-cpu-clock-backend-current-72-20260714.txt), [source validation](../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/results/mainline-cpufreq-source-validation.txt), and [mainline design](../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/results/mt6797-pm-mainline-design.md); prove shared-resource ownership, calibration, rail ownership, PLL/mux sequencing, and rollback before enabling an MT6797 variant/new driver |
| Thermal sensors | Vendor `mtkts*` zones and `mt6797-therm_ctrl` | all | thermal/AUXADC at `0x1100b000`, SPI 78; AUXADC at `0x11001000` | 13 zones enumerate but all are disabled and several readings are sentinels. Live proc calibration and complete vendor source recover six logical banks, five sensor inputs, three efuse words, channel 11, and an ID-dependent raw-to-temperature formula. Linux 7.1.3 has no MT6797 match, but its generic AUXADC-thermal bank/calibration architecture is reusable; patch 0057 adds an MT6797-specific disabled-only variant for timing, valid-mask, buffer, and ADC-OE conversion, with a complete `MAX_NUM_VTS` fallback initialization. `configs/gemini.fragment` selects both generic thermal and AUXADC modules. The board DTS now wires a fixed 12-byte `calibration-data` cell to the bounded, read-only, root-only LK `/chosen/atag,devinfo` provider in patch 0057a; the provider, Gemini DTB, focused binding schema, and full guest-only package pass compile validation, while both thermal/AUXADC nodes remain disabled. Runtime enablement is still blocked until the final LK handoff is observed and invalid calibration is made explicitly fail-closed. The vendor source audit shows words 31–33 are read through the bootloader-injected `/chosen/atag,devinfo` payload; Linux's generic MMIO efuse provider has no MT6797 match, so direct `efusec` mapping is not an established substitute. Runtime IRQ/protection, idle/wakeup, and trips remain unproven. | `observed` | `missing` | `unknown` | [MT6797 thermal recovery](../experiments/2026-07-13-mt6797-thermal-recovery/README.md), [source validation](../experiments/2026-07-13-mt6797-thermal-recovery/results/mainline-thermal-source-validation.txt), [current package policy audit](../experiments/2026-07-13-mt6797-thermal-recovery/results/mainline-thermal-current-72-policy-20260714.txt), [thermal safety contract](../experiments/2026-07-13-mt6797-thermal-recovery/results/mainline-thermal-safety-contract-20260714.txt), [calibration ownership audit](../experiments/2026-07-13-mt6797-thermal-recovery/results/mainline-thermal-calibration-ownership-20260714.txt), [provider build](../experiments/2026-07-13-mt6797-thermal-recovery/results/mt6797-calibration-provider-build-20260714.txt), [variant validation](../experiments/2026-07-13-mt6797-thermal-recovery/results/mt6797-mainline-variant-validation.txt), and [CPU/DVFS recovery](../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/README.md); preserve the bootloader calibration ABI, validate final handoff/invalid-calibration behavior, then test raw samples/trips |
| Idle / DVFSP | Vendor dpidle/SODI/MCDI plus optional hybrid DVFSP | all | CSPM `0x11015000`, CSRAM `0x0012a000`, PSCI | WFI is active; deep states show zero usage and vendor logs report blocked entry; mainline has only generic PSCI; the current package audit confirms one PSCI node and ten CPUs but no idle-state table, OPPs, or DVFSP/SPM consumer; the current DTS defers the undocumented DVFSP node because Linux has no matching driver or binding | `observed` | `missing` | `unknown` | [Current PM package validation](../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/results/mainline-pm-current-72-package-20260714.txt); [PM recovery](../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/README.md); preserve the register/IRQ evidence and verify firmware idle parameters before adding states |
| Interrupts/timers | GICv3, ARMv8 architectural timer | all | MT6797 | Live `arm,armv8-timer` uses PPIs 13/14/11/10 and 13 MHz; `arch_sys_counter`/`arch_sys_timer` are active downstream; the current package links generic ARM timer/PSCI/GIC support and carries the same four PPIs; Linux 7.1.3 `arm_arch_timer` and generic GIC bindings match | `observed` | `released` | `none` | [CPU/PSCI/timer recovery](../experiments/2026-07-13-cpu-psci-timer-recovery/README.md); [current-package audit](../experiments/2026-07-13-cpu-psci-timer-recovery/results/mainline-cpu-psci-timer-current-72-package-20260714.txt); verify timer interrupts and clockevents after mainline boot; vendor CPU GPT is separate |
| RAM | LPDDR and reserved regions | all | EMI / firmware carve-outs | Live Gemian exposes ~3.68 GiB as discontiguous System RAM with fixed ATF/LK/framebuffer/CCCI/SCP regions plus dynamically allocated CONSYS/SCP-share/SPM reservations; local DT preserves the fixed regions but does not yet reproduce every dynamic ownership contract | `observed` | `local` | `unknown` | [Memory carve-out recovery](../experiments/2026-07-13-memory-carveout-recovery/README.md); compare two LK boots, reject the generic contiguous EVB range, and keep firmware/DMA consumers disabled until placement is resolved |
| Clocks/resets | MT6797 clock tree and three infracfg reset banks | all | topckgen/infracfg/apmixed plus CAM/MJC and MFG | The local series adds evidenced reset offsets `0x120`/`0x124`/`0x128`, CAM/MJC gates, and disabled-only MFGSYS gate/resource patches 48–49; patch 50 wires the vendor MFG 52 MHz preclock, with no runtime clock test | `unknown` | `local` | `none` | Runtime-test clock gates and reset consumers; never pulse an unverified line |
| Power domains | MT6797 SCPSYS, including MFG and four MFG cores | all | SCPSYS/SPM `0x10006000` | Patches 47 and 50 reuse generic SCPSYS sequencing, add the live separate-`0x33c` SRAM control/ack fields, MFG hierarchy, and required 52 MHz preclock; build-only, no domain power-on test | `unknown` | `local` | `none` | [Clock/power/reset recovery](../experiments/2026-07-12-mt6797-clock-power-reset-recovery/README.md); validate domain map and safe sequencing |
| M4U/SMI fabric | One MT6797 M4U with seven larbs and 71 ports | all | M4U `0x10205000`, SMI common `0x14022000`, larbs `0x12002000`–`0x1a001000` | Linux generation-two IOMMU/SMI frameworks are reusable with dedicated MT6797 flags, `0x1554` bus routing, and MT8167-style larb MMU register `0xfc0`; all nodes remain disabled and the recovered table has no GPU port | `unknown` | `local` | `none` | [M4U/SMI recovery](../experiments/2026-07-12-mt6797-m4u-smi-recovery/README.md); attach one verified DMA consumer at a time |
| UART | MT6797 UART0 debug console; UART1–3 auxiliary ports | all | UART0–3 at `0x11002000`–`0x11005000`, GIC SPIs 91–94 | Live `ttyMT0`–`ttyMT3` bind to vendor `mtk-uart`; Linux 7.1.3 `8250_mtk` and the MT6797 compatible provide the correct 16550/PIO reuse path, and explicitly disable DMA for a console. Vendor VFIFO/AP-DMA windows remain intentionally unrepresented. Captured Gemian and independent reference DT evidence identify UART0 RX GPIO97/function 1 and TX GPIO98/function 1. Candidate L includes that correction in an independently reproduced artifact with a matching full logical-`boot2` readback. During L attempt 2 the exact initramfs suffix was visible on fbcon while a connected serial adapter received no bytes. This makes UART operationally unavailable under the tested setup, but does not distinguish a physical fault from tty registration, console naming, baud, pinmux, or electrical issues. | `unknown` | `released` | `none` | [UART/console recovery](../experiments/2026-07-13-uart-console-recovery/README.md); [Candidate L](../experiments/2026-07-17-uart-pstore-observability/README.md); do not use UART as the sole next success criterion; reconcile LK's downstream `ttyMT0` token with mainline `ttyS*` only through a separate discriminating test |
| Watchdog | MT6797 TOPRGU at `0x10007000` | all | TOPRGU / SPI137 bark IRQ | Linux 7.1.3 `mtk_wdt` covers the MT6797 register and reset-controller protocol. Candidate M proved the no-IRQ `mtk-wdt` registration, 31-second timeout, one handoff ping, automatic return, watchdog boot reason, and cross-version console retention. Candidate N reproduced that recovery after onlining CPU1. Candidate O again opened and pinged the same timer once, completed the CPU1–7 sweep, retained its last line about three seconds before nominal expiry, then produced a collector-confirmed disconnect/reconnect with a changed boot ID and watchdog-class Gemian reason. Candidate P preserved the exact open/ping/wait trace and returned automatically; its post-return collector recovered pstore but did not span the cycle or capture independent reset-reason fields. The basic recovery channel remains attributable; the optional IRQ request errno, SPI137 polarity/delivery, bark, pretimeout, and patch 0081's independent counterfactual effect remain unproven. | `partial` | `local` | `none` | [Watchdog recovery](../experiments/2026-07-12-mt6797-watchdog-recovery/README.md); [Candidate M runtime](../experiments/2026-07-18-watchdog-registration-diagnostic/results/runtime-candidate-m-attempt-1-20260718.txt); [Candidate N runtime](../experiments/2026-07-18-cpu1-online-diagnostic/results/runtime-candidate-n-attempt-1-20260718.txt); [Candidate O runtime](../experiments/2026-07-18-cortex-a53-sweep-diagnostic/results/runtime-candidate-o-attempt-1-20260718.txt); [Candidate P runtime](../experiments/2026-07-18-fbcon-rotation-diagnostic/results/runtime-candidate-p-attempt-1-20260718.txt); Q must not open a userspace watchdog or deliberately auto-reset, must retain and re-audit kernel boot-time keepalive, and must keep bark work separate |
| Pinctrl/GPIO/EINT | MT6797 pin and 192-line external-interrupt controllers | all | pinctrl plus EINT at `0x1000b000` | Local series adds the decoded 172-entry map, SPI170 resource, virtual GPIO262/EINT176 and built-in EINT186 without extending physical register ranges; vendor pinctrl source does not encode a reusable map | `unknown` | `local` | `none` | [EINT/pinctrl recovery](../experiments/2026-07-12-mt6797-eint-recovery/README.md); boot-test interrupt delivery, polarity, mask/ack, debounce, and wake on controlled consumers |
| I2C | MT6797 controllers | all | I2C0-9 | SoC nodes and generic driver exist | `unknown` | `released` | `none` | Enable only buses with verified board wiring |
| Indicator LEDs | AWINIC AW9120, five RGB blocks plus auxiliary indicators | all | I2C3 `0x2c`, GPIO245 active-high PDN | Live Gemian binds chip ID `0xb223`; retained source and the installed Gemian daemon map visible RGB outputs 1–15, GPIO74/75 I2C3 pins, 5 ms PDN timing, and the 8-bit-register/big-endian-16-bit protocol. Linux 7.1.3 has no matching driver. A new generic regmap LED-class/multicolor driver and binding are justified; the vendor `/proc` ABI is not. The first one-channel test should cap current at the documented 3.5 mA minimum and enable only I2C3/`0x2c` without scanning shared HDMI/EDID addresses | `observed` | `missing` | `none` | [AW9120 hardware record](hardware/gemini-gemian-baseline.md#aw9120-indicator-leds); [screen/LED selection](../experiments/2026-07-16-screen-marker-diagnostic/results/display-path-selection-20260716.txt); validate block-1 green visibility under Gemian before adding the bounded mainline driver, independently of the now-visible simplefb/fbcon path |
| PMIC/regulators | MT6351 E2 confirmed by HWCID `0x5140`, SWCID `0x5120`; 9 bucks plus 30 unique LDO controls | all | MT6797 pwrap, PMIC EINT176 | The local series supplies pwrap, reset/EINT providers, MT6351 MFD/IRQ, a schema, and a 39-rail driver mechanically checked against raw live selectors. The current 72-patch artifact compiles the driver, passes its focused binding and direct DT-schema checks, and places eMMC consumers under the MT6351 regulator container; E3 (`0x5130`) is intentionally rejected until separately evidenced. Pwrap and MFD probe are stateful/write-capable, so mainline runtime remains gated behind external recovery and before/after register capture | `unknown` | `local` | `none` | [PMIC recovery](../experiments/2026-07-11-mt6351-pmic-recovery/README.md); [first-boot probe audit](../experiments/2026-07-14-first-boot-probe-audit/README.md); [current 72-patch validation](../experiments/2026-07-11-mt6351-pmic-recovery/results/mainline-mt6351-current-72-validation-20260714.txt); add conservative Gemini constraints/consumers; validate readback before any voltage or OPP change |
| External GPU regulator | Richtek RT5735, live vendor DT at I²C7 `0x1c`, product ID `0x10`; separate `vgpu_buck@0x60` candidate is unbound | all | MT6797 I²C7 / external VGPU buck | Patch 51 adds a standard VSEL0 regulator provider and disabled-only Gemini node; no runtime probe or voltage transition | `observed` | `local` | `none` | [RT5735 VGPU recovery](../experiments/2026-07-12-rt5735-vgpu-recovery/README.md); verify identity and rail wiring before attaching Panfrost or enabling OPPs |
| RTC | MT6351 RTC at PMIC offset `0x4000`, vendor `rtc0`/hctosys active | all | MT6351 PMIC IRQ 9 | Local MFD resource, shared-driver match, and fixed-function DT node exist; runtime behavior remains untested | `unknown` | `local` | `none` | Run bounded read/set/alarm/power-cycle tests from mainline |
| Charger/fuel gauge | BQ25890 at I2C0 `0x6b`; FAN49101 at `0x70`; RT9466 alternative at `0x53` unbound | all | I2C/PMIC | Vendor/runtime identity is recovered; the vendor BQ register map matches Linux 7.1.3, but its presence check is only a nonzero read of `0x03`. Upstream BQ25890 core is reusable after Linux part/revision ID (`0x14`), IRQ, rail, and limit validation. Patch 0055 adds a dedicated `onsemi,fan49101` regulator driver/binding and disabled-only Gemini node; the earlier 71-patch source/object and binding checks pass, while runtime identity/readback, control/reset semantics, and rail ownership remain unverified. The current package audit confirms `bq25890_charger.ko` and `fan49101.ko` are packaged, but the Gemini DTB has no enabled charger, battery, or fuel-gauge consumer. Vendor fuel-gauge HAL still needs a standard power_supply/IIO design | `observed` | `local` | `unknown` | [Charger and fuel-gauge recovery](../experiments/2026-07-12-charger-power-recovery/README.md); [current package audit](../experiments/2026-07-12-charger-power-recovery/results/mainline-charger-current-72-package-20260714.txt); [BQ25890 reuse audit](../experiments/2026-07-12-charger-power-recovery/results/bq25890-reuse-audit-20260713.txt); [FAN49101 register contract](../experiments/2026-07-12-charger-power-recovery/results/fan49101-register-contract.txt); [prior 70-patch module validation](../experiments/2026-07-12-charger-power-recovery/results/fan49101-current-70-module-validation-20260713.txt); keep duplicate `bq24261` node and RT9466 alternative disabled, then validate read-only telemetry before charge control |
| eMMC | Internal storage | all | MSDC0 `0x11230000`, SPI79 | Live DF4064 eMMC is 8-bit HS400 at 200 MHz/1.8 V; current Linux `mtk-sd` reuses the dedicated MT6797 compatibility record (`clk_div_bits=12`, PAD_TUNE0, async/data tuning, no stop-clock/enhanced-RX/64G paths). The Gemini node deliberately caps first boot at 25 MHz legacy timing, non-removable, with VEMC/VIO18 supplies and pinmux-only states. Source, DTB, package, and fresh read-only live capture are recorded; no mainline boot or MMC I/O has run | `observed` | `partial` | `build-only` | [MSDC recovery](../experiments/2026-07-12-mt6797-msdc-recovery/README.md); [first-boot probe audit](../experiments/2026-07-14-first-boot-probe-audit/README.md); [current 72-patch validation](../experiments/2026-07-12-mt6797-msdc-recovery/results/mainline-msdc-current-c2d-reconciliation-20260714.txt); boot from external recovery with a read-only rootfs before enabling HS200/HS400 |
| microSD | Removable storage | all | MSDC1 `0x11240000`, SPI80, card-detect EINT6 | Live host has no card, 0 Hz, power off, and 3.3 V reset state. MT6797 compatibility exists, but card-detect polarity/GPIO67, pin drive, VMCH/VMC ownership, UHS voltage switching, and remove/reinsert behavior remain unvalidated; node stays disabled | `described` | `partial` | `build-only` | [MSDC recovery](../experiments/2026-07-12-mt6797-msdc-recovery/README.md); [current 72-patch validation](../experiments/2026-07-12-mt6797-msdc-recovery/results/mainline-msdc-current-c2d-reconciliation-20260714.txt); validate detection, I/O, remove/reinsert, and suspend separately |
| Keyboard | AW9523B / `aw9523_key` | all | I2C5 `0x5b`, GPIO87/EINT10, shutdown GPIO58 | Linux 7.1.3 already has `pinctrl-aw9523` and `gpio-matrix-keypad`; patch 0054 supplies a disabled-only Gemini node and source-derived 8×7 keymap. The vendor scan drives the selected column low, inactive columns high, and treats a low row bit as pressed; follow-up patch 0076 adds the consumer's `gpio-activelow` and `drive-inactive-cols` properties while keeping the node disabled. A passive capture reports the separate `Integrated keyboard` input device and active AW9523 interrupt. The exact active boot ELF resolves physical `(row=4,column=3)` to `KEY_LEFTMETA` and contains four `KEY_UNKNOWN` positions, while the retained source checkout labels that position `KEY_FN`; the mainline candidate intentionally omits the four unproven contacts as `KEY_RESERVED`. The disabled candidate's current `gpio-ranges` form still needs correction to the binding-validated combined-controller form before enablement, and its upstream-driver reset semantics must remain active-high. GPIO87 has a documented electrical risk because the current MT6797 pinctrl implementation lacks the generic bias/input maps; do not invent unsupported properties. I2C5 and the expander remain disabled in the packaged DTB, and runtime remains untested. The installed `planet_vndr/gemini` XKB symbols map `<LWIN>` to `ISO_Level3_Shift`, which is userspace policy over an ordinary keycode. | `unknown` | `local` | `build-only` | See the dedicated [keyboard hardware record](hardware/keyboard.md), [Candidate Q handoff](../experiments/2026-07-18-keyboard-shell-diagnostic/README.md), [active-ELF provenance](../experiments/2026-07-12-input-backlight-recovery/results/active-aw9523-elf-keymap-20260714.txt), [capability comparison](../experiments/2026-07-12-input-backlight-recovery/results/live-keyboard-capability-compare-20260714.txt), full sanitized keymap/capture [here](../experiments/2026-07-12-input-backlight-recovery/results/live-keyboard-recovery-20260714.txt), the [polarity audit](../experiments/2026-07-12-input-backlight-recovery/results/keyboard-polarity-contract-20260714.txt), and the [0076 patch audit](../experiments/2026-07-12-input-backlight-recovery/results/keyboard-polarity-mainline-patch-20260714.txt). Q is the exact next gate: correct and validate the disabled DT candidate, enable only I2C5/AW9523/matrix in its final package, then prove raw events and typed shell input without storage or network access. |
| Lid/power keys | MT6351 power press/release IRQs observed; hall/toggle inputs remain separate | all | PMIC IDs 0/2 through EINT176; hall GPIO66/EINT5; toggle GPIO93/EINT16; `mtk-kpd` KEY_POWER 116 | Local MFD and generic keys driver support distinct MT6351 press/release IRQs; standard `gpio-keys` can model the hall `SW_LID` path, while the toggle’s F9/F10 policy is unresolved. The latest passive capture shows hall state 0 with EINT5 activity and toggle state 0 with no EINT16 activity; no transition was stimulated. Patch 0074 records a disabled-only GPIO66 active-low `SW_LID` candidate; the packaged DTB/module audit is complete, but runtime remains untested | `unknown` | `local` | `build-only` | [Hall/lid/switch recovery](../experiments/2026-07-12-hall-lid-switch-recovery/README.md); [latest passive result](../experiments/2026-07-12-hall-lid-switch-recovery/results/live-hall-lid-recovery-20260714.txt); [75-patch package audit](../experiments/2026-07-12-input-backlight-recovery/results/mainline-display-input-current-75-package-20260714.txt); add power-key-only board data with hardware long-press reset disabled, then validate input and wake separately |
| Display pipeline | MT6797 MMSYS/SMI/IOMMU/CMDQ/MM mutex/OVL/PQ/RDMA/DSI | all | multimedia | Local series adds disabled SMI/IOMMU, GCE, mutex, routes/resets, and a descriptor-ready NT36672E framework; native DRM/DSI/PHY nodes remain disabled or module-only. Candidates F–L established transient loader-retained simplefb/fbcon output. Candidate M kept that console visible through watchdog progress until automatic reset, with retained pstore independently establishing execution through 30 seconds. Candidate P's exact rotation-only derivative then produced owner-readable normal-landscape console text through the complete inherited sweep before an unassisted return; its post-return pstore retains the execution checkpoints. This is one loader-retained simplefb/fbcon rotation result, not native display support or repeatability. Native DRM, DSI, panel, and backlight ownership remain unknown. | `unknown` | `local` | `build-only` | [DRM component recovery](../experiments/2026-07-12-mt6797-drm-component-recovery/README.md); [Candidate M runtime](../experiments/2026-07-18-watchdog-registration-diagnostic/results/runtime-candidate-m-attempt-1-20260718.txt); [Candidate P runtime](../experiments/2026-07-18-fbcon-rotation-diagnostic/results/runtime-candidate-p-attempt-1-20260718.txt); retain exact P's readable loader console for Q but do not promote native panel/DRM support |
| Panel/backlight | Compiled-in selected NT36672-family module; exact suffix unverified; bsg100 direct hardware evidence names SSD2092 on its tested unit | all | single DSI0, 4-lane RGB888 burst video; MT6797 DISP_PWM at `0x1100f000`; LP3101 bias at I2C1 `0x3e` | Patch 43 reuses the NT36672E framework with Gemini-specific mode, 165-register sequence, supply names, and delays; its packet selector preserves the vendor MT6797 rule that commands below `0xb0` use DCS packets and commands at/above `0xb0` use generic packets. Patch 44 adds a provisional one-clock MT6797 display-PWM contract and disabled resource node; bsg100's hardware-working native DTS instead uses the upstream two-clock interface with `CLK_TOP_MUX_PWM` as `main` and `CLK_INFRA_DISP_PWM` as `mm`, so patch 44 must be re-audited before enablement. The module-inclusive package carries `panel-novatek-nt36672e.ko`, `pwm-mtk-disp.ko`, and `pwm_bl.ko`, but the PWM node and panel/backlight consumer remain disabled/absent. Panel identity is unresolved: the named device has an unbound `solomon_touch@0x53` candidate and mixed vendor log labels, while bsg100 has direct SSD2092 reads | `unknown` | `local` | `build-only` | [Panel recovery](../experiments/2026-07-11-gemini-panel-recovery/README.md); [current panel validation](../experiments/2026-07-11-gemini-panel-recovery/results/mainline-panel-current-72-validation-20260714.txt); [packet-semantics audit](../experiments/2026-07-11-gemini-panel-recovery/results/nt36672-packet-semantics-20260714.txt); [bsg100 panel cross-check](../experiments/2026-07-13-bsg100-gemini-linux-comparison/results/bsg100-panel-crosscheck-20260714.txt); [bsg100 fbcon commit audit](../experiments/2026-07-13-bsg100-gemini-linux-comparison/results/fbcon-commit-035d4b0-20260716.md); [current display/input package audit](../experiments/2026-07-12-input-backlight-recovery/results/mainline-display-input-current-72-package-20260714.txt); resolve panel identity and the PWM clock contract before a controlled native panel test |
| Touchscreen | Novatek `cap_touch` / NT36772 | all | I2C4 `0x62`, GPIO85/EINT8, reset GPIO68, vendor `NVT-ts` | A fresh filtered vendor probe log records trim bytes `00 00 03 72 66 03`, matching masked source/ELF trim-table entry 8 and selecting NT36772 event map `0x11e00`; PID `0x0101`, firmware `0x05`/bar `0xFA`, and IRQ 392 are also observed. Linux 7.1.3's `novatek-nvt-ts` targets NT11205/NT36672A and does not implement this verified alternate-address/xdata contract. Patch 0075 adds a disabled-by-default NT36772 backend boundary; its object/module and binding checks pass, and the complete 76-patch Image/DTB package now validates, but the touchscreen DT node and hardware runtime remain untested | `observed` | `released` | `build-only` | [NVT source validation](../experiments/2026-07-12-input-backlight-recovery/results/nvt-source-validation-current-20260714.txt), [NVT ELF validation](../experiments/2026-07-12-input-backlight-recovery/results/nvt-elf-validation-20260714.txt), [live trim identity](../experiments/2026-07-12-input-backlight-recovery/results/nvt-live-trim-identity-20260714.txt), [NT36772 boundary checks](../experiments/2026-07-12-input-backlight-recovery/results/nt36772-mainline-boundary-20260714.txt), [76-patch Image/DTB package](../experiments/2026-07-12-input-backlight-recovery/results/mainline-display-input-current-76-package-20260714.txt), [protocol comparison](../experiments/2026-07-12-input-backlight-recovery/results/nt36772-protocol-compare-20260714.txt), [patch 0075](../patches/v7.1.3/0075-input-touchscreen-novatek-add-NT36772-backend.patch); validate logical-address `0x01` transport, rails/reset, runtime events and suspend before enabling the node; keep firmware update disabled by default |
| USB-C ports | Device/host/role switching | all | USB1 `0x11200000`, USB3 `0x11270000`/SIF windows, MT6797 PHY, two FUSB301 at I2C0/I2C1 `0x25` | Live vendor topology and clocks are captured. USB1's MAC/FIFO/DMA protocol is source-equivalent to Linux MUSB/Inventra; patches 0066–0070 add the local MT6797 T-PHY, MTU3/xHCI, and USB11 MUSB glue/topology boundaries, while patch 0056 adds the local FUSB301 driver. The broad package keeps consumers disabled. The exact Candidate M/N diagnostic foundation instead enables one USB2 peripheral-only/high-speed T-PHY/MTU3 path with forced B-device session and built-in `g_ether`. Retained mainline console-ramoops proves the T-PHY and MTU3 probes returned zero, MTU3 bound IRQ 208 with DMA32 and logged Tx/Rx FIFO `0x3000/8`, `g_ether` registered the pinned locally administered MAC pair, and MTU3 logged its gadget pull-up action; that is not an electrical D+ measurement. The probe used a dummy `vusb33` regulator. Host enumeration, selected USB configuration, host network interface, carrier, packets, remote shell, physical port identity, host mode, role switching, VBUS, Type-C, and charging remain unproven. | `partial` | `local` | `none` | [USB/Type-C recovery](../experiments/2026-07-12-usb-typec-recovery/README.md); [current USB package audit](../experiments/2026-07-12-usb-typec-recovery/results/mainline-usb-current-72-package-20260714.txt); [fresh vendor capture](../experiments/2026-07-12-usb-typec-recovery/results/runtime-usb-typec-20260714.txt); [MT6797 USB3 topology validation](../experiments/2026-07-12-usb-typec-recovery/results/mt6797-usb3-topology-validation-20260713.txt); [sanitized mainline gadget evidence](../experiments/2026-07-16-usb-gadget-diagnostic/results/retained-pstore-mtu3-gadget-evidence-20260718.txt); next configure `usb0` at a fixed address and prove descriptor → interface → carrier → ping → marker → bounded shell on a direct no-bridge link |
| GPU | Live DT says Mali-T860; runtime ID is Mali-T88x MP4 r1p0 / product `0x0880` | all | `0x13040000`, vendor GIC SPIs 264/263/262, MFG clocks and four MFG-core handles | Panfrost already supports the observed Midgard T880 model. The pinned vendor tree contains generic r12p0 and configured r12p1 Kbase source, including the MT6797 platform and SPM files. Source and ELF recover ten base-clock requests, external-VGPU readiness gating, and a G3D reset write; the optional SPM/DVFS feature is present in source but absent from the captured autoconf/ELF path. Patches 47–51 expose the reusable MFG clock/SCPSYS/preclock/disabled RT5735 boundary; patches 0058–0059 add explicit MT6797 Panfrost data and a disabled four-domain node. The current package audit confirms `panfrost.ko` is packaged while the GPU/MFG clock/RT5735 consumers remain disabled, with no OPP, reset, or IOMMU property. Reset, resource reduction, and OPP calibration remain unverified; recovered M4U table has no GPU client | `unknown` | `local` | `inconclusive` | [GPU/Panfrost recovery](../experiments/2026-07-12-mt6797-gpu-panfrost-recovery/README.md); [current GPU package audit](../experiments/2026-07-12-mt6797-gpu-panfrost-recovery/results/mainline-panfrost-current-72-package-20260714.txt); [vendor source/ELF analysis](../experiments/2026-07-12-mt6797-gpu-panfrost-recovery/results/mali-vendor-analysis.txt); [Panfrost source contract](../experiments/2026-07-12-mt6797-gpu-panfrost-recovery/results/mainline-panfrost-mt6797-source-validation.txt); reuse Panfrost core model, add only a standard MT6797 platform backend where resources differ, keep node disabled, and do not add GPU `iommus` or vendor OPPs without evidence |
| Audio | MT6797 AFE + MT6351 codec candidate | all | AFE `0x11220000`, SPI 151; one live `mt-snd-card` with 31 PCM endpoints | Linux 7.1.3 has matching `mt6797-afe`, `mt6351-sound`, and `mt6797-mt6351` silicon drivers; the current package selects all three as modules with `CONFIG_SND_SOC_MT6797=m`, `CONFIG_SND_SOC_MT6351=m`, and `CONFIG_SND_SOC_MT6797_MT6351=m`, and packages the matching 1,570-module tree. Source audit finds no new audio driver needed: the binding's eight clocks split into seven platform-resume clocks plus the `mtkaif_26m_clk` ADDA DAPM supply. The current package audit confirms the AFE node is disabled and no codec/machine graph, analog wiring, jack/amp supplies, or runtime test exists | `unknown` | `released` | `build-only` | [Audio AFE recovery](../experiments/2026-07-12-audio-afe-recovery/README.md); [current audio package audit](../experiments/2026-07-12-audio-afe-recovery/results/mainline-audio-current-72-package-20260714.txt); [current source validation](../experiments/2026-07-12-audio-afe-recovery/results/audio-source-validation-20260714.txt); retain disabled AFE only, preserve the clock-consumer split, resolve MFD gates, then add a board graph and test playback/capture separately |
| Wi-Fi | MT6797 CONSYS/WMT combo, vendor `mt-wifi` | all | `consys@18070000`, Wi-Fi DMA `0x180f0000` | Live `CONSYS_MT6797`/`0x6797` properties, WMT `MT279` status, `mediatek,wifi` SPI 283, and HIF-SDIO traffic are captured; source and userspace audits identify a proprietary gen2 cfg80211/MAC over AP-DMA plus factory `/dev/wmtWifi` controls, not an MT76-compatible MAC. The current package carries cfg80211/mac80211 and unrelated MT76 modules, but no MT6797 WMT/CONSYS transport and no active connectivity DT node; Linux 7.1.3 has no MT6797 WMT/SDIO Wi-Fi binding (its `btmtksdio` driver is Bluetooth-only and for different IDs) | `enumerates` | `missing` | `unknown` | [Connectivity/WMT recovery](../experiments/2026-07-12-connectivity-wmt-recovery/README.md); [current package validation](../experiments/2026-07-12-connectivity-wmt-recovery/results/mainline-connectivity-current-package-20260714.txt); [current 71-patch transport validation](../experiments/2026-07-12-connectivity-wmt-recovery/results/mainline-connectivity-current-71-validation-20260713.txt); [transport/firmware boundary audit](../experiments/2026-07-14-transport-firmware-boundary-audit/README.md); define consys firmware ownership, SDIO/HIF protocol, and a new cfg80211 driver boundary |
| Bluetooth | MT6797 CONSYS STP over vendor BTIF | all | BTIF `0x1100c000` plus TX/RX DMA windows; consys BGF wake | Vendor BTIF TX/RX DMA interrupts are active. The current package carries generic `btmtk`/HCI UART layers but selects neither `btmtkuart` nor `btmtksdio`; Linux 7.1.3 `btmtkuart` and `btmtksdio` provide reusable STP/H:4/HCI/WMT layers, but `btmtkuart` is serdev-only and `btmtksdio` is table-bound to MT7663/MT7668/MT7921/MT7902 with a five-byte/256-byte SDIO contract; Gemini's active BTIF path and old-combo SDIO IDs/header/block contract need a new transport and consys owner | `enumerates` | `missing` | `unknown` | [Connectivity/WMT recovery](../experiments/2026-07-12-connectivity-wmt-recovery/README.md); [current package validation](../experiments/2026-07-12-connectivity-wmt-recovery/results/mainline-connectivity-current-package-20260714.txt); [current 71-patch transport-boundary validation](../experiments/2026-07-12-connectivity-wmt-recovery/results/mainline-connectivity-current-71-validation-20260713.txt); [transport/firmware boundary audit](../experiments/2026-07-14-transport-firmware-boundary-audit/README.md); add an MT6797 BTIF/DMA transport behind standard HCI, after non-transmitting identity tests |
| GNSS | CONSYS/WMT firmware-owned GNSS/FLP path | cellular variants | vendor `gps`/`gps_emi`, GPIO69 GPS LNA | Vendor `mtk_agpsd`, `/dev/stpgps`, and ROMv3 patch strings show a combo-firmware path; the current package carries generic GNSS/serial/`gnss-mtk` modules but no MT6797 combo transport or active GNSS DT node; Linux 7.1.3 `gnss-mtk` is serial-only and does not match this path | `enumerates` | `missing` | `unknown` | [Connectivity/WMT recovery](../experiments/2026-07-12-connectivity-wmt-recovery/README.md); [current package validation](../experiments/2026-07-12-connectivity-wmt-recovery/results/mainline-connectivity-current-package-20260714.txt); [current 71-patch transport validation](../experiments/2026-07-12-connectivity-wmt-recovery/results/mainline-connectivity-current-71-validation-20260713.txt); [transport/firmware boundary audit](../experiments/2026-07-14-transport-firmware-boundary-audit/README.md); establish ownership/message routing before a standard GNSS interface |
| Sensors | BMI160/LSM6DS3 IMU candidates; STK3X1X at `0x48`; MMC3530, humidity, barometer candidates | Gemini variant in live capture | I2C1 `0x11008000`, controller SPI 85; ALS GPIO88/EINT11; gyro GPIO65 candidate | Live vendor drivers bind BMI160-named clients and an STK3X1X-named child but expose no IIO; both vendor IMU probes force `i2c_client.addr` to `0x69`, so the `0x68`/`0x69` pair is not two-chip evidence; the vendor HAL maps them through legacy misc/input events and only scales ABS axes; recovered direction 7 is `out=(-raw_y,-raw_x,-raw_z)`, equivalent to the documented IIO matrix `0,-1,0 / -1,0,0 / 0,0,-1`; vendor DT also carries LSM6DS3 alternatives; patch 52 provides a disabled standard BMI160 candidate and driver config, but identity/resources remain unverified. The current package audit confirms IIO plus BMI160, LSM6DSX, and STK3310 modules are packaged, while only the disabled BMI160 candidate is present and no IRQ/supply is described; Linux 7.1.3 can reuse BMI160, LSM6DSX, BMP280, HTS221, and the STK3310-family driver when exact IDs/resources match; STK3X1X register overlap is documented, but its product/revision and GPIO/rail contract remain unverified; MMC35240 remains only a hypothesis and no magnetic stream was observed | `observed` | `partial` | `build-only` | [Sensor/IIO recovery](../experiments/2026-07-12-sensor-iio-recovery/README.md); [current sensor package audit](../experiments/2026-07-12-sensor-iio-recovery/results/mainline-sensors-current-72-package-20260714.txt); enable standard drivers only after direct ID and board-resource tests, use the recovered matrix for BMI160, reuse STK3310 only after product-ID evidence, and keep MMC3530 unbound until protocol identity is proven |
| Cellular modem | MediaTek MD1 cellular modem plus MD3/C2K modem path | LTE variants | AP/MD CLDMA and CCIF at `0x10014000`/`0x10209000`–`0x1021a000`; CCCI shared memory | Live vendor CCCI exposes 18 `ccmni` MD1 interfaces, 8 `cc3mni` MD3/C2K interfaces, and active CLDMA/CCIF IRQs. Source recovers the 16-byte CCCI header, 8+8 CLDMA/CCIF queues, 16-byte 36-bit descriptors, queue/channel tables, and staged EMI-MPU/remap ownership. The current 7.1.3 package carries generic `wwan.ko`/MHI helpers but no `t7xx` or CCCI transport; its DTB retains two `no-map` CCCI reservations and zero active modem transport nodes. Linux 7.1.3 `t7xx` is PCIe/DPMAIF-specific and is not a transport match. The generic `wwan_port_ops`/`wwan_create_port`/`wwan_port_rx` and standard WWAN/TTY/netdev layers can be reused only above a new MT6797 CCCI transport; the vendor character/ioctl ABI stays private. Firmware image and dynamic shared-memory ownership remain vendor-specific | `enumerates` | `missing` | `required-nonfree` | [Modem/CCCI recovery](../experiments/2026-07-13-modem-ccci-recovery/README.md), [current package validation](../experiments/2026-07-13-modem-ccci-recovery/results/mainline-ccci-current-package-20260714.txt), [MT6797 CCCI contract](../experiments/2026-07-13-modem-ccci-recovery/results/mt6797-ccci-mainline-contract.md), [transport/firmware boundary audit](../experiments/2026-07-14-transport-firmware-boundary-audit/README.md); resolve bootloader reservations, handshake/rings, reset, and EMI MPU ownership before any mainline modem probe |
| Cameras | SP5509 (`sp5509mipirawsls`) on the active camera path; second path reports `non_sensor` | Gemini variant in live capture | MT6797 SENINF, camera hardware, ISP, I2C | Runtime proc/kallsyms, the immutable vendor ELF, and the pinned Planet source identify the SP5509 path. Source provides separate main/SLS IDs, 16-bit I2C transactions, SLS modes, a power sequence, and a monolithic CAM/SENINF/CAMSV/ISP implementation; the ELF probes register `0x0f16` for raw ID `0x0556` and candidate write IDs `0x40`/`0x50`. Populated address, physical slot, endpoint, and board sequencing remain unverified. The current 7.1.3 package selects generic media, CAMSYS clocks, IOMMU, and SMI but has no SP5509/OV5675 sensor module or Gemini capture node; its camera SMI/larb consumers remain disabled. Linux 7.1.3 has an OV5675 driver but no SP5509 driver or matching MT6797 SENINF/CAM/CAMSV/ISP V4L2 pipeline. Existing MT6797 camera clocks, SMI/IOMMU, power, and reset providers are reuse candidates only where contracts match | `observed` | `missing` | `unknown` | [Camera recovery](../experiments/2026-07-13-camera-recovery/README.md), [current package validation](../experiments/2026-07-13-camera-recovery/results/mainline-camera-current-77-package-20260714.txt), [SP5509 source contract](../experiments/2026-07-13-camera-recovery/results/sp5509-source-contract.md), [MT6797 pipeline contract](../experiments/2026-07-13-camera-recovery/results/mt6797-camera-pipeline-contract.md), [ELF validation](../experiments/2026-07-13-camera-recovery/results/sp5509-vendor-elf-validation.txt), [transport/firmware boundary audit](../experiments/2026-07-14-transport-firmware-boundary-audit/README.md); recover physical sensor address/slot, endpoint/link rate, orientation, AF, and pipeline boundary before adding a consumer |
| External display | SII9022/Sil9024A bridge candidate plus MT6797 DPI0 producer and EDID client | Gemini variant in live capture | I2C3 `0x39`/`0x50`; vendor HPD GPIO62/EINT1; DPI0 `0x1401e000`/SPI231; DPI GPIO39–54 | Live bridge and EDID clients are unbound. Vendor source/ELF checks indexed family ID `0x9022` and TPI ID byte `0xb0` at register `0x1b`, matching Linux 7.1.3 `sii902x`; vendor DPI register/clock contract matches generic `mtk_dpi` and existing MT6797 TVDPLL/MM gates. Patches 60/61 keep DPI disabled and graph ports unconnected; board reset/rails (20/50/20 ms reset, GPIO247 1.2 V), 16-bit DRM graph, HPD, EDID mux, factor table, and physical connector remain unverified. Keep the vendor compatible and `/dev/hdmitx` ABI out of mainline | `unknown` | `released` | `unknown` | [External-display recovery](../experiments/2026-07-13-external-display-recovery/README.md); [bridge ELF validation](../experiments/2026-07-13-external-display-recovery/results/sil9022-vendor-elf-validation.txt); [DPI source validation](../experiments/2026-07-13-external-display-recovery/results/mainline-mt6797-dpi-source-validation.txt); reuse `sii902x`/`mtk_dpi` only after chip ID and board contract evidence |
| Suspend/wake | System suspend | all | cross-subsystem | Live `/sys/power/state` advertises `freeze mem`, and the current package selects generic suspend/PSCI code, but the DT has no suspend/idle state table and PMIC, SPM, clocks, IRQs, and wake sources remain unproven; no suspend was attempted | `observed` | `missing` | `unknown` | [Current PM package validation](../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/results/mainline-pm-current-72-package-20260714.txt); [CPU/DVFS recovery](../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/README.md); only test after a recovery path and repeated-cycle protocol exist |

## Updating the matrix

Every status change must cite a tracking issue containing:

- exact device variant;
- kernel commit and patch-series revision;
- configuration and toolchain;
- test protocol and repeat count;
- redacted log or measurement;
- upstream series/commit when the upstream state changes.

The tracking issue should link the supporting experiment record and detailed
hardware document when either exists.

Use `stable` only when the result is present in a released upstream kernel and passes the project's regression protocol.
