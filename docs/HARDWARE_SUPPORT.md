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

USB diagnostic history: patches 0077–0078 add an opt-in
forced B-device session property and disabled Gemini MTU3 peripheral wiring.
The separate [USB gadget diagnostic](../experiments/2026-07-16-usb-gadget-diagnostic/README.md)
enables only that peripheral test path in its candidate overlay. The exact
image was synchronized, fully read back, and tested from `boot2`; the device
remained dark and steady while two bounded host checks found no USB child. This
is a failed enumeration test, not proof that Linux did not execute. Later
retained exact Candidate M and N console-ramoops records independently prove
that the 11290000 T-PHY and 11271000 MTU3 probes returned zero, the forced
B-device session ran, built-in `g_ether` reported ready, and MTU3 logged its high-speed
gadget pull-up action. Candidate AC later established the direct no-bridge
development path through exact USB identity, selected configuration, fixed-MAC
host interface, carrier, static-address ping, TCP marker, and bounded shell.
Exact AH attempt 2 independently retained the same USB service under the
AF-kernel/AD-board split. This still does not establish an electrical D+
waveform, physical-port mapping, host mode, VBUS, Type-C policy, role switching,
or charging. See the
[sanitized retained-pstore result](../experiments/2026-07-16-usb-gadget-diagnostic/results/retained-pstore-mtu3-gadget-evidence-20260718.txt),
[Candidate AC experiment](../experiments/2026-07-21-usb-gadget-ethernet/README.md),
and [AH attempt-2 result](../experiments/2026-07-22-ad-contract-af-kernel-split/results/runtime-candidate-ah-attempt-2-20260722.txt).

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
[Candidate Q](../experiments/2026-07-18-keyboard-shell-diagnostic/README.md)
was subsequently built, installed to logical `boot2`, and fully read back, but
its intended selection did not provide a working text console and left no
pstore evidence. No marker, AW9523/input evidence, or shell was observed; the
failing layer remains unknown. Static review found that Q supplied raw parent
interrupt line 87 although GPIO87 maps to EINT10, but that defect is not proven
to explain the runtime boundary. Do not repeat unchanged Q. Candidate U was the
intended P-based upstream-AW9523 polling follow-up with a shell independent of
event capture. U was independently built twice with matching validated outputs
and installed to live-resolved logical `boot2` with a matching full-partition
readback. Its first intended selection produced a black screen and dark console
with no marker or automatic reboot. A later changed Gemian boot ID and empty
authenticated pstore do not establish kernel, `/init`, console, AW9523,
keyboard, or shell entry. Do not repeat unchanged U. See its [build reproduction](../experiments/2026-07-19-keyboard-polling-diagnostic/results/final-build-reproduction-20260719.txt),
[write/readback](../experiments/2026-07-19-keyboard-polling-diagnostic/results/boot2-write-candidate-u-20260719.txt),
and [runtime result](../experiments/2026-07-19-keyboard-polling-diagnostic/results/runtime-candidate-u-attempt-1-20260719.txt).
Post-run audit found that U's final DTB came from the kernel package rather than
exact P and omitted P's loader-framebuffer, no-IRQ watchdog, and other
LK-aligned fixups. This explains why U did not carry P's configured console
path, but does not prove U entered Linux or establish the black-screen cause.

[Candidate V](../experiments/2026-07-19-keyboard-watchdog-diagnostic/README.md)
is the installed successor, not a reinterpretation of U. It restores exact P's
hardware-passed final DTB and no-IRQ watchdog/ramoops foundation, applies only
the audited keyboard polling transform, and hard-pins the corrected polling
implementation. Two fresh kernel builds and two V assemblies reproduced; the
package, focused schemas, component validators, and all 24 negative mutation
cases passed. Its raw 6,864,896-byte image is SHA-256
`9ef0ee8dc1eb49752f9cf8f60b247b9b85e4fd2a9f090473f1d91848114087b0`.
The padded `boot2` target, remote checksum, and full local readback match
SHA-256
`57d362a86fae38c0ec2cec909ef6ae8d8ad124b87abb2ee58d179184c1f19168`;
the guarded installation did not reboot the unit. The owner later selected V
from `boot2`, saw a visible console, and observed an automatic return. Exact
retained markers establish kernel/initramfs entry, local-shell's pre-exec
`tty1_shell=ready` recorder, the `mtk-wdt` association/open/one-ping contract,
and waits through 30 seconds. Gemian reported `boot_reason=4`,
`androidboot.bootreason=wdt_by_pass_pwk`, and `powerup_reason=reboot`. This adds
one attributable no-IRQ watchdog-recovery and loader-simplefb/fbcon result.

It adds no keyboard or usable-shell result. AW9523 probe on adapter 0 at
address `0x5b` repeatedly failed `-110`/`ETIMEDOUT`, including its reset retry;
AW9523 and the matrix stayed unbound and no event node appeared. The keyboard
attempt stops before polling/input at the controller-to-AW9523 provider
boundary. Exact working-3.18 disassembly and latest-bsg100 hardware evidence
select the missing direct MT6797 controller match and WRRD/aux-length contract
as the next hypothesis while AW9523 reset/cache and matrix polling stay fixed.
`tty1_shell=ready` precedes the shell `exec` and proves neither
`ash`, prompt visibility, nor interactivity. Marker fanout can bury tty1, and
the V keymap lacks slash/minus keys needed to type `/bin/v-pass`. Do not repeat
unchanged V. Preserve
the exact [build reproduction](../experiments/2026-07-19-keyboard-watchdog-diagnostic/results/final-build-reproduction-20260719.txt),
[guarded write/readback](../experiments/2026-07-19-keyboard-watchdog-diagnostic/results/boot2-write-candidate-v-20260719.txt),
[runtime evidence](../experiments/2026-07-19-keyboard-watchdog-diagnostic/results/runtime-candidate-v-attempt-1-20260719.txt),
and [working 3.18 controller audit](../experiments/2026-07-19-keyboard-watchdog-diagnostic/results/working-3.18-aw9523-i2c-binary-audit-20260719.txt).

[Candidate W](../experiments/2026-07-19-keyboard-wrrd-diagnostic/README.md)
is the validated and installed successor. Patch 0086 adds exactly one direct
`mediatek,mt6797-i2c` match to existing `mt8173_compat`, matching the working
3.18 WRRD plus auxiliary receive-length contract and latest checked bsg100
`main` revision
[`60f5f4ac777a0aeccc89b5d3a4f8cd1f1ebe57b3`](https://github.com/bsg100/gemini-linux/commit/60f5f4ac777a0aeccc89b5d3a4f8cd1f1ebe57b3).
It preserves V's exact final DTB, AW9523/matrix state, no-IRQ watchdog, and
ramoops. Observation-only changes put the fixed kernel console on tty2, respawn
the foreground shell on tty1 without background marker fanout, and use the
larger built-in `TER16x32` font. Two clean packages match after normalizing
only timestamp provenance, two final assemblies match recursively, and all 24
mutation cases pass. The calibrated 6,866,944-byte container's raw image
SHA-256 is
`34c41fad1e86de05b6a1f64f7e5d9229bd26ea88d982b0a57f2b9573aeb782d4`
and its initramfs SHA-256 is
`3793bec7a63074b237d041bcd42e6edfccc80f0a3d7b19869abf99ee7874dac6`.
The exact image was installed without reboot to live-resolved logical `boot2`;
its padded image, remote checksum, and full local readback match SHA-256
`0ff3220096aa53f792116b3899e356bc2516816c9c330309c3d81e9fe1446608`.
The owner selected W once. Retained exact-W evidence shows successful
`0-005b` probe and `aw9523-pinctrl` bind, the subsequent `matrix-keypad` bind,
exact `/dev/input/event0`, and press/release records for H, E, L, P, and Enter.
The owner observed a visible shell and working keyboard and approved the font.
This promotes only those controller/provider/matrix/limited-key paths to a
one-run partial result. It does not prove a physical WRRD waveform, full key
coverage, shell-command execution, or repeatability. W's tty2 request did not
isolate kernel logs from tty1, and its deliberate watchdog handoff caused the
expected automatic return before useful work.

Candidate X was the validated serviceability candidate over exact W. It removes
only the virtual-console token and userspace watchdog
ownership, retains serial plus `/dev/kmsg`/ramoops evidence, and exposes a typed
manual reboot path. Two clean builds reproduced 220 non-timestamp files, two
complete X artifacts are recursively identical, all 32 LK gates passed, and
47/47 mutations were rejected. The raw image SHA-256 is
`bf4003871daaba1faa293f2b128021d3a67d41ebf3ddff1c42463409803b9296`.
It was synchronized, flushed, and fully read back from live-resolved logical
`boot2` with padded SHA-256
`e89d71f15465b544db163b5f0b90b456e913c38ba4d2ed49aa7bde345148c855`.
The installation did not reboot and the boot ID stayed unchanged. The owner
later reported that X booted and worked before typed `reboot` appeared to hang.
Power-key recovery reached Gemian and pstore was empty. Do not claim clean tty1,
exact X entry, X uptime, or individual keyboard subgates. Preserve the [W
build reproduction](../experiments/2026-07-19-keyboard-wrrd-diagnostic/results/final-build-reproduction-20260719.txt),
[mutation result](../experiments/2026-07-19-keyboard-wrrd-diagnostic/results/validator-mutations-20260719.txt),
[write/readback](../experiments/2026-07-19-keyboard-wrrd-diagnostic/results/boot2-write-candidate-w-20260719.txt),
[W runtime](../experiments/2026-07-19-keyboard-wrrd-diagnostic/results/runtime-candidate-w-attempt-1-20260719.txt),
[X experiment](../experiments/2026-07-19-keyboard-manual-reboot-diagnostic/README.md),
[X build reproduction](../experiments/2026-07-19-keyboard-manual-reboot-diagnostic/results/final-build-reproduction-20260719.txt),
[X mutation result](../experiments/2026-07-19-keyboard-manual-reboot-diagnostic/results/validator-mutations-20260719.txt),
[X write/readback](../experiments/2026-07-19-keyboard-manual-reboot-diagnostic/results/boot2-write-candidate-x-20260719.txt),
and [X runtime](../experiments/2026-07-19-keyboard-manual-reboot-diagnostic/results/runtime-candidate-x-attempt-1-20260719.txt).

Candidate Y was reproducibly built and fully read back, but an exact BusyBox
audit rejected it before boot because bare `reboot` bypasses its external
wrapper and its watchdog-open refusal branch is unreachable. Y was never
selected and changes no runtime support state.

Candidate Z is the hardware-tested keyboard/recovery foundation inherited by AA r1. It retains exact
Y's kernel, DTB, and configuration and changes four initramfs members plus adds
read-only `bin/reboot-dispatch.env`. Two complete builds match recursively, the
exact-BusyBox dispatch gate passed on Linux arm64, 32/32 LK gates and 75/75
mutations passed, and exact Z was fully read back from logical `boot2` with
padded SHA-256
`ba21e6424f94c82f14fd51b5681eea68d6cf09e9177e4f9ca2061c9f129abb40`.
In one owner-attended selection it booted with the keyboard still working and
returned automatically after the typed watchdog command. A changed boot ID and
`androidboot.bootreason=wdt_by_pass_pwk` corroborate a watchdog-class reset,
but no individual-key or detailed dispatch/countdown evidence survived. See the [Y
rejection](../experiments/2026-07-19-keyboard-typed-watchdog-reboot-diagnostic/results/preboot-command-dispatch-audit-20260720.txt),
[Z experiment](../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/README.md),
[build validation](../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/results/build-validation-20260720.txt),
[dispatch validation](../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/results/ash-dispatch-validation-20260720.txt),
[mutation result](../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/results/validator-mutations-20260720.txt),
[write/readback](../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/results/boot2-write-candidate-z-20260720.txt),
and [runtime result](../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/results/runtime-candidate-z-attempt-1-20260720.txt).

Candidate AA r0 is historical. Its raw image, incomplete map, and installed
16 MiB `boot2` image/readback SHA-256 values are respectively
`a2ad7a4107abd99cbd349b8f2deadd0185cbdd5bb0884ecbdae8ff2a7499ed4c`,
`48f1f61a9ad8ba327a3105c0dfbbc698c1e55bb3bcca695b46887888be8ca821`,
and `157c7cd5d814d7b2704d679faacd3215c5e889642b4261441f99653957585eaa`.
It was superseded before selection because it omitted Shift+Fn F1–F10 and
used BusyBox `dumpkmap` output as an invalid byte-exact runtime oracle. Do not
boot r0; its completed [build validation](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/build-validation-20260720.txt)
and [write/readback](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/boot2-write-candidate-aa-20260720.txt)
remain r0 evidence only.

AA r1 is the built, validated, installed, and hardware-tested replacement. It
retains exact Z's kernel field, final DTB, and resolved configuration. Its
deterministic 2,311-byte, eight-table VT map has SHA-256
`02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c`
and exactly 53 semantic changes, including Unicode smiley, Shift+Fn F1–F10,
modifier-release policy, and plain/Shift/Ctrl/Alt backslash semantics. A
respawn-safe path first accepts an already loaded exact map; otherwise it
requires the seven inherited tables before loading. The normal prompt then
requires exact `KDGKBENT` results for all 2,048 entries across eight declared
kernel tables, including the table-3 keycode-0 payload `K_HOLE` to kernel
`K_ALLOCATED` normalization, upper-half `K_HOLE` entries, and absence of every
undeclared table. Media, brightness, phone, airplane-mode, launcher,
voice-assistant, and Sym remain userspace policy. The recovery-VM canonical
static AArch64 verifier is SHA-256
`29735d212e74d0b0040a3ead173a83223b89ce5d947b697a115707eb3d23b238`.
Two clean constructions are recursively byte- and metadata-identical; the raw
7,378,944-byte artifact is SHA-256
`37e82bf3be87dd9e52fb8d60597b69f92a5c0dc5aebd51d178f1e7efd33343d7`.
The guarded installer required exact r0 padded predecessor
`157c7cd5d814d7b2704d679faacd3215c5e889642b4261441f99653957585eaa`,
preserved a private full backup, resolved live-GPT `boot2` as
`/dev/mmcblk0p30`, and fully read back padded r1 as SHA-256
`38b49c7c19c2d97fa0c48436545219489221aa367aedf491ae6ebd4ec4856703`.
The installation did not reboot. Attended attempt 1 passed: retained pstore
records `origin=loaded-now` at 2.407618 seconds, tty1 `K_UNICODE`, exact
readback of all 2,048 planned-table entries, high-half holes, every undeclared
table absent, table 3 allocated, `GEMINI-AA-R1#`, and validated reboot
dispatch. The owner reported that the new keymap worked. Bare `reboot` at
126.258967 seconds proves more than 123 seconds without automatic watchdog
ownership;
the retained record also contains exact AW9523/matrix/event0 identity and A/S
press-release events. The one-open/one-ping 31-second wrapper then retained fd
3, logged all six countdown checkpoints, and returned to Gemian. A changed
boot ID plus
`boot_reason=4`, `androidboot.bootreason=wdt_by_pass_pwk`, and
`powerup_reason=reboot` corroborate the reset. F1–F10 and Page Up/Page Down
remain unconfirmed, not failed, because no visible discriminator was
available. See the [AA
experiment](../experiments/2026-07-20-keyboard-console-map-diagnostic/README.md),
r1 [build validation](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/build-validation-aa-r1-20260721.txt),
[installer validation](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/installer-validation-aa-r1-20260721.txt),
[guarded write/readback](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/boot2-write-candidate-aa-r1-20260721.txt),
[layout reference](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/layout-reference-aa-r1-20260721.txt),
and [runtime result](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/runtime-candidate-aa-r1-attempt-1-20260721.txt).

Candidate AB passed one attended local hardware test. Patch 0087 gives MT6797 TOPRGU
restart priority 255 ahead of PSCI 129 while every other supported MediaTek SoC
keeps priority 128. After `KBUILD_BUILD_VERSION=1` was pinned, builds 3 and 4
reproduced all 221 non-dynamic package files and modes. Two independent
AA-r1-derived containers are recursively byte- and mode-identical at raw image
SHA-256
`61c74592267466735164c19f8b831ea18db2892de95e32109f2aacd7ec5c5446`,
retain the exact hardware-passed DTB and keymap, pass all 32 LK gates and all 25
focused mutation rejections, and have no userspace watchdog or automatic
reboot. The guarded installer preserved exact padded AA r1, wrote only inactive
live-GPT logical `boot2`, and fully read back padded AB as SHA-256
`b58c0347d34a3fd9031c74cb03447dd7a6fc630d5b8ea2b7eabc36827e754350`
without rebooting or changing the boot ID. Attempt 1 then retained the exact AB
marker, console-map gate, and `GEMINI-AB#` prompt; the owner confirmed the
keyboard worked, waited 45 seconds without an automatic reset or countdown,
and observed an immediate reset after typed bare `reboot`. Pstore records the
manual request at 66.021584 seconds and final kernel `reboot: Restarting
system` line at 66.049438 seconds, 27.854 ms later. That retained interval is
not instrumented Enter-to-LK timing. Gemian returned under a boot ID distinct
from the pre-attempt Gemian boot ID. The resulting `boot_reason=4`,
`androidboot.bootreason=wdt_by_pass_pwk`, and `powerup_reason=reboot` remain a
nondiscriminating watchdog-class reason, while timing and the audited absence
of userspace watchdog ownership support prompt kernel TOPRGU SWRST. Restart is
observed once on the named local unit, not proven repeatable or universally
reliable.
F1–F10 and Page Up/Page Down remain unconfirmed, not failed. See the [AB
experiment](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/README.md),
[kernel reproducibility](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/kernel-reproducibility-ab-20260721.txt),
[container validation](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/container-validation-ab-20260721.txt),
[installer validation](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/installer-validation-ab-20260721.txt),
[write/readback](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/boot2-write-candidate-ab-20260721.txt),
and [runtime result](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/runtime-candidate-ab-attempt-1-20260721.txt).

Historical subsystem-audit build note (2026-07-14): the 72-patch package
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
The historical broad 77-patch Image/DTB package is
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
properties and no periodic rescan. The recorded 77-patch candidate deliberately
omitted those properties until a named-device event trace could measure bounce
and settling; see the [keyboard timing contract](../experiments/2026-07-12-input-backlight-recovery/results/keyboard-timing-contract-20260714.txt).
That disabled 77-patch keyboard candidate also lacked a selected MT6797-side default
pinctrl state for its GPIO58 reset and GPIO87/EINT10 interrupt lines. A retained
independent-project audit reports that an equivalent omission regressed its USB
gadget path and that referencing its defined AW9523 pin state restored keyboard
and USB coexistence. Treat that as cross-device integration evidence, not proof
of identical electrical causality: the first enabled candidate must use a
source-backed SoC state and retain USB gadget registration as a regression
gate. See the [keyboard hardware record](hardware/keyboard.md#soc-pinctrl-and-usb-coexistence-boundary).
Candidate U supersedes that historical source boundary with build/static, not
positive runtime, evidence: patches 0083–0085 and two independent matching builds
validate the polling binding, generic matrix driver path, reusable disabled-board
EINT correction, and candidate-only DT. That DT retains GPIO87/EINT10 pinmux
with no parent-IRQ consumer and uses a 20 ms poll plus 2 us column-scan delay.
It intentionally omits `debounce-delay-ms`, which only delays IRQ-triggered
scans and is inert on U's continuous polling path; there is no separate polling
debounce. U's matching full-partition `boot2` readback establishes installation
identity; its subsequent black-screen run and empty post-return pstore do not
establish that the polling path executed.
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

Exact Candidate AP is the latest attributable DVFSP/I2C6 ownership result: it
failed closed after one supplier grant because AP_DMA did not satisfy the
absolute-gated cleanup oracle, while I2C6 stayed unbound and issued no
transfer. Candidate AO remains the latest passing handoff-only boundary.
Candidate AK remains the latest Cortex-A72 rejection control, while Candidate
Z remains the keyboard-map recovery foundation. AK retained an
owner-attested readable console, exact candidate runtime with advancing
CPU0–7, ordered fail-closed CPU8 and CPU9 dispatches, native reboot,
changed-Gemian return, and post-return `boot2` integrity. Neither A72 came
online and the run establishes no A72 support. W's one attributable run
promotes I2C5's provider path, AW9523, matrix polling, the exact event node,
and only the observed H/E/L/P/Enter transitions to `partial`. The owner also observed a
visible shell and approved font, but kernel-log/shell isolation failed and the
deliberate watchdog expiry prevented a useful session. W has no `pass` marker,
complete keyboard test, shell-command proof, or repeatability. X's later owner
report adds only that it
booted and worked before typed reboot appeared to hang; empty pstore supplies no
individual keyboard subgate. Y was rejected before boot. Z subsequently booted
with working keyboard input by owner report and returned through its typed
watchdog path, corroborated by changed boot-ID and watchdog-reason evidence;
that report did not add individual-key coverage. Historical AA r0 was
superseded before boot, has been replaced on `boot2`, and must not be selected.
AA r1 was built twice recursively identically, installed with a matching
guarded full readback, and passed attempt 1 with exact retained map-gate
evidence, A/S press-release events, owner-confirmed new-keymap operation, >123
seconds without automatic watchdog ownership, and typed watchdog recovery.
F1–F10 and Page Up/Page Down remain unconfirmed rather than failed.
AB's build-3/build-4 packages and two final containers reproduce, and padded AB
is fully read back from inactive `boot2`. Its attended run retained exact AB
attribution and the map gate, the keyboard worked, idle remained stable for 45
seconds, and typed bare `reboot` immediately reset by owner observation. The
27.854 ms request-to-final-kernel-log interval and changed boot ID support one
local kernel-restart pass. F1–F10 and Page Up/Page Down remain unconfirmed.
AH attempt 2 later retained native-kernel shutdown and final restart lines
26.273 ms apart before Gemian returned under a changed boot ID; this is a
second candidate-level restart observation, not an instrumented command-to-LK
latency measurement or universal repeatability claim.

Keyboard provenance update (2026-07-14): the exact active boot ELF, reconstructed
from the captured active boot payload, compiles the physical `(row=4,col=3)`
record as `KEY_LEFTMETA` and retains `KEY_UNKNOWN` at `(row=7,col=3..6)`.
Patch 0054 now follows that active-boot-normalized map; the retained source
checkout's `KEY_FN` entry is preserved as a documented source/build discrepancy.
In that reusable disabled-board description the consumer remains disabled, so
that source/package baseline itself supplies no key-testing evidence. Later W
and Z results are separate enabled diagnostic evidence: W retained only the
listed H/E/L/P/Enter transitions and Z retained no individual events. Full-map,
modifier, rollover, wake, and electrical timing coverage therefore remains
open. See the
[active ELF result](../experiments/2026-07-12-input-backlight-recovery/results/active-aw9523-elf-keymap-20260714.txt)
and [current map validation](../experiments/2026-07-12-input-backlight-recovery/results/keymap-consistency-active-boot-20260714.txt).

| Subsystem | Component / candidate | Variants | Bus or SoC block | Mainline basis/dependency | Runtime | Upstream | Firmware | Evidence / next gate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DVFSP handoff / I2C6 ownership | Candidate AN observer, Candidate AO one-way owner, and Candidate AP childless consumer | named Gemini PDA unit | CSPM `0x11015000`; infracfg I2C_APPM/AP_DMA gates; I2C6 `0x1100e000` | Candidate AN first observed an exact stopped/reset-like PCM signature with I2C_APPM ungated and correctly returned `unknown`. Exact-active-binary recovery then established reversible vendor stop and a per-transaction DVFSP pause-source protocol. Candidate AO's full-readback-verified `boot2` image passed the handoff-only oracle: the exact stopped PCM signature survived one balanced CCF hold, I2C_APPM gated after release and remained gated at 45 seconds, and no I2C6/A72 operation occurred. Candidate AP added patches 0099–0102, making AO readiness a hard dependency for enabled-but-childless I2C6. Its exact 52,655-byte live FDT passed the 37-entry LK allowlist and the provider granted access once, but the runtime ended in a structured `FAIL`: I2C_APPM regated in all 32 cleanup samples while AP_DMA remained valid and ungated in all 32. The provider faulted closed, I2C6 returned `-EIO` before adapter bind, and transfer/client/regulator/DA9214/A72/suspend counters stayed zero. CPU0–7 advanced and native reboot returned to changed-ID Gemian with exact post-return `boot2` integrity. AP_DMA was already ungated in AP's initial samples; enabled UART0 and I2C5 share that gate, but the surviving owner is not attributed. AO's narrow `partial` handoff state is retained; AP does not promote I2C6 support. | `partial` | `local` | `none` | [Candidate AN experiment](../experiments/2026-07-24-mt6797-dvfsp-handoff-observer/README.md); [active arbitration recovery](../experiments/2026-07-24-mt6797-dvfsp-i2c6-arbitration/README.md); [Candidate AO experiment](../experiments/2026-07-24-mt6797-dvfsp-one-way-handoff/README.md); [Candidate AP result](../experiments/2026-07-24-mt6797-dvfsp-i2c6-consumer/results/candidate-ap-hardware-20260724.txt); do not repeat AP—identify AP_DMA ownership and define a baseline-preserving cleanup oracle before another I2C6 candidate; validate resume separately |
| Cortex-A72 external regulator prerequisite | Candidate AL resource-only attempt 1; Candidate AP ownership predecessor | named Gemini PDA unit | MT6797 I2C6 `0x1100e000`, eventual client `0x68` | Exact AL booted with the inherited eight-A53, keyboard, USB and native-reboot path. I2C6 bound to `i2c-mt65xx`; its dynamic adapter and exact DT client appeared, but the DA9211-family probe read unsupported device ID `0x0`, returned `ENODEV`, left the client unbound and registered neither BUCKA nor `vproc-big`. The official-datasheet/source cross-check explains zero: Linux assumes the A-family `0x201` identity page, while the legacy DA9214 map used by Gemini does not expose it and documents zero for nonexistent reads. Live Gemian confirms I2C6 is `appm_used` and paired with active DVFSP arbitration, which AL lacked. Candidate AP tested only the childless ownership predecessor and failed closed before adapter bind because its absolute AP_DMA-gated cleanup oracle was not met; it performed no DA9214 operation. | `partial` | `local` | `none` | [Candidate AL runtime](../experiments/2026-07-23-da9214-resource-only/results/runtime-candidate-al-attempt-1-20260723.txt); [datasheet cross-check](../experiments/2026-07-23-da9214-resource-only/results/da9214-datasheet-crosscheck-20260723.txt); [Candidate AP result](../experiments/2026-07-24-mt6797-dvfsp-i2c6-consumer/results/candidate-ap-hardware-20260724.txt); do not repeat AL/AP or request an A72—first resolve AP_DMA ownership and I2C6 cleanup, then validate resume and only afterward test the resource-only legacy identification/page-state path |
| Keyboard/watchdog diagnostic | Candidate V attempt 1 | all | I2C5 `0x5b`; TOPRGU `0x10007000`; loader simplefb | Exact P DT foundation plus upstream AW9523, generic matrix polling, no-IRQ `mtk-wdt`, and `console-ramoops`. Retained markers prove exact V kernel/initramfs entry, local-shell's pre-exec recorder, watchdog association/open/one ping, and waits through 30 seconds; the owner saw the console and the unit returned automatically with Gemian watchdog reasons. AW9523 repeatedly failed `-110`/`ETIMEDOUT`, including reset retry; AW9523/matrix stayed unbound and no event appeared. Exact working-3.18 disassembly selects hardware WRRD and auxiliary RX-length offset `0x6c`; V instead falls through to `mt6577_compat`, suppressing WRRD and omitting that auxiliary-length contract. No prompt/interactivity or key input is established. | `partial` | `local` | `none` | [Candidate V runtime](../experiments/2026-07-19-keyboard-watchdog-diagnostic/results/runtime-candidate-v-attempt-1-20260719.txt); [working 3.18 controller audit](../experiments/2026-07-19-keyboard-watchdog-diagnostic/results/working-3.18-aw9523-i2c-binary-audit-20260719.txt); preserve the proven recovery/console path, keep AW9523 reset/cache and matrix polling fixed, add the direct MT6797-to-MT8173 controller-data match, and repair marker/prompt plus font usability; do not repeat unchanged V |
| Keyboard/controller diagnostic | Candidate W attempt 1 | all | I2C5 `0x5b`; `1101c000.i2c`; TOPRGU `0x10007000`; loader simplefb | Patch 0086 adds one direct MT6797-to-`mt8173_compat` match while the final DTB remains byte-exact V, including AW9523/matrix policy, no-IRQ watchdog, and ramoops. Two clean packages and final assemblies reproduced and the exact image was fully read back from logical `boot2`. In one run, exact retained markers show successful `0-005b`/AW9523 bind, matrix bind, `/dev/input/event0`, and H/E/L/P/Enter transitions; the owner observed a visible shell and working keyboard and approved `TER16x32`. Kernel logs still mixed with tty1 and the deliberate watchdog timeout returned automatically before useful work. | `partial` | `local` | `none` | [Candidate W experiment](../experiments/2026-07-19-keyboard-wrrd-diagnostic/README.md); [runtime](../experiments/2026-07-19-keyboard-wrrd-diagnostic/results/runtime-candidate-w-attempt-1-20260719.txt); [build reproduction](../experiments/2026-07-19-keyboard-wrrd-diagnostic/results/final-build-reproduction-20260719.txt); [write/readback](../experiments/2026-07-19-keyboard-wrrd-diagnostic/results/boot2-write-candidate-w-20260719.txt); do not infer a physical bus trace, all-key coverage, command execution, or repeatability |
| Keyboard serviceability candidate | Candidate X attempt 1 | all | Exact W I2C5/keyboard/loader-simplefb DT; tty1 plus serial/ramoops | X removed only the virtual-console token and all initramfs watchdog ownership and added a typed generic reboot path. The owner reported that X booted and worked, but typed `reboot` appeared to hang. No automatic return occurred; power-key recovery reached Gemian and pstore was empty. | `unknown` | `local` | `none` | [Candidate X experiment](../experiments/2026-07-19-keyboard-manual-reboot-diagnostic/README.md); [runtime](../experiments/2026-07-19-keyboard-manual-reboot-diagnostic/results/runtime-candidate-x-attempt-1-20260719.txt); do not infer clean tty1, exact X marker, X uptime, or individual keyboard subgates |
| Rejected typed watchdog reboot candidate | Candidate Y pre-boot rejection | all | Exact X kernel/DT/config and keyboard path; four-member initramfs delta | Y's external wrapper contains the intended watchdog sequence, but exact BusyBox resolves bare `reboot` to its internal applet and bypasses that wrapper. A failed special-builtin watchdog redirection also exits before the promised refusal. Y was reproducibly built and fully read back, but never booted. | `unknown` | `local` | `none` | [Candidate Y experiment](../experiments/2026-07-19-keyboard-typed-watchdog-reboot-diagnostic/README.md); [command-dispatch rejection](../experiments/2026-07-19-keyboard-typed-watchdog-reboot-diagnostic/results/preboot-command-dispatch-audit-20260720.txt); do not boot Y |
| Dispatch-safe typed watchdog reboot candidate | Candidate Z attempt 1 | all | Exact Y kernel/DT/config and keyboard path; four changed and one added initramfs member | The inherited interactive `ENV` alias and runtime oracle make bare `reboot` resolve to absolute `/bin/reboot`; the wrapper uses catchable function redirection for watchdog open, exact preflight, one ping, held fd, visible countdown, and no generic-reboot, sync, or fallback path. Two complete builds match recursively, the Linux-arm64 dispatch gate, 32/32 LK gates, and 75/75 mutations passed, and exact Z was fully read back from logical `boot2`. The owner then reported one successful boot, working keyboard, and automatic return after the typed watchdog command; changed boot-ID and `wdt_by_pass_pwk` evidence corroborate a watchdog-class reset. | `partial` | `local` | `none` | [Candidate Z experiment](../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/README.md); [runtime](../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/results/runtime-candidate-z-attempt-1-20260720.txt); exact marker, live alias/preflight text, countdown timing, individual keys, clean tty1, and repeatability remain unproved |
| Superseded console keymap candidate | Candidate AA r0, pre-boot rejection | all | Exact Z kernel/DT/config/matrix/recovery; historical initramfs-only derivative | The raw image (`a2ad7a4107abd99cbd349b8f2deadd0185cbdd5bb0884ecbdae8ff2a7499ed4c`), incomplete map (`48f1f61a9ad8ba327a3105c0dfbbc698c1e55bb3bcca695b46887888be8ca821`), and full installed/read-back `boot2` (`157c7cd5d814d7b2704d679faacd3215c5e889642b4261441f99653957585eaa`) are exact historical identities. R0 omitted Shift+Fn F1–F10 and relied on an invalid BusyBox dump-byte oracle. It was superseded before selection. | `unknown` | `local` | `none` | [Candidate AA experiment](../experiments/2026-07-20-keyboard-console-map-diagnostic/README.md); [historical build](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/build-validation-20260720.txt); [historical write/readback](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/boot2-write-candidate-aa-20260720.txt); do not boot r0 |
| Console keymap candidate | Candidate AA r1 attempt 1 pass | all | Exact Z kernel/DT/config/matrix/recovery; initramfs-only console-map derivative | The 2,311-byte, eight-table map has SHA-256 `02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c` and 53 semantic changes covering printable/navigation symbols, U+263A, Shift+Fn F1–F10, modifier release, and plain/Shift/Ctrl/Alt backslash policy. Two builds are recursively byte- and metadata-identical; canonical verifier SHA-256 is `29735d212e74d0b0040a3ead173a83223b89ce5d947b697a115707eb3d23b238`, and raw 7,378,944-byte artifact SHA-256 is `37e82bf3be87dd9e52fb8d60597b69f92a5c0dc5aebd51d178f1e7efd33343d7`. The guarded live-GPT `boot2` installation required exact r0 predecessor `157c7cd5d814d7b2704d679faacd3215c5e889642b4261441f99653957585eaa`, preserved a full backup, and fully read back padded r1 as `38b49c7c19c2d97fa0c48436545219489221aa367aedf491ae6ebd4ec4856703` without install-time reboot. Attempt 1 retained `origin=loaded-now`, tty1 Unicode mode, exact verification of all 2,048 entries plus high-half holes/undeclared-table absence, table-3 allocation, the normal prompt marker, and validated dispatch. The owner reported the new map working. Bare reboot followed >123 seconds without automatic watchdog ownership, then the inherited one-ping countdown returned to Gemian. F1–F10 and Page Up/Page Down remain unconfirmed, not failed. Media, brightness, phone, airplane, launcher, voice, and Sym remain userspace. | `partial` | `local` | `none` | [Candidate AA experiment](../experiments/2026-07-20-keyboard-console-map-diagnostic/README.md); [r1 build validation](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/build-validation-aa-r1-20260721.txt); [installer validation](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/installer-validation-aa-r1-20260721.txt); [write/readback](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/boot2-write-candidate-aa-r1-20260721.txt); [layout reference](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/layout-reference-aa-r1-20260721.txt); [runtime](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/runtime-candidate-aa-r1-attempt-1-20260721.txt) |
| Kernel restart candidate | Candidate AB attempt 1 pass | all | Patch 0087; MT6797 TOPRGU restart notifier | MT6797 alone selects restart priority 255 ahead of PSCI 129; every other supported MediaTek variant retains 128. Builds 3 and 4 reproduce all 221 non-dynamic package files and modes. Two independent AA-r1-derived containers are recursively byte- and mode-identical, pass 32/32 LK gates and 25/25 focused mutation rejections, retain the exact AA r1 DTB/keymap, and have no userspace watchdog or automatic reboot. Exact padded AB was fully read back from inactive logical `boot2`. Attempt 1 retained exact AB attribution, the map gate, and `GEMINI-AB#`; the keyboard worked, 45 seconds idle caused no reset/countdown, and typed bare `reboot` reset immediately by owner observation. Pstore records request at 66.021584 and final kernel restart at 66.049438 seconds. Gemian returned under a changed boot ID. The 27.854 ms retained-log interval is not instrumented Enter-to-LK timing, and watchdog-class boot reasons are nondiscriminating. Timing plus absence of userspace watchdog ownership support prompt kernel TOPRGU SWRST. | `observed` | `local` | `none` | [Candidate AB experiment](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/README.md); [kernel reproducibility](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/kernel-reproducibility-ab-20260721.txt); [container validation](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/container-validation-ab-20260721.txt); [write/readback](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/boot2-write-candidate-ab-20260721.txt); [runtime](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/runtime-candidate-ab-attempt-1-20260721.txt); one named-unit pass only—repeatability and universal reliability remain open; F1–F10 and Page Up/Page Down are unconfirmed |
| Boot | Planet LK development path | all | boot chain | Retained Android 8 LK requires `bootopt=64...`, gzip plus an appended DTB, LK-compatible DT shapes, and a decompressed payload within the 50 MiB buffer. M–P established attributable Linux/initramfs handoff, watchdog recovery, A53 hotplug, and readable rotated fbcon; W–AB established keyboard, console map, and one prompt kernel-restart pass; AC added the exact USB development service. Candidate AI's guarded installation, readable console, exact USB-attributed eight-A53 runtime, native reboot, changed-Gemian return, and post-cycle full `boot2` hash all passed. Exact AJ later replaced AI with a matching 16 MiB readback. AJ attempt 1 was rejected as a target-identity mismatch. Attempt 2 passed the exact USB/CPU runtime, one native reboot, changed-Gemian return, and matching full read-only post-return `boot2` hash. Its retained pstore is deliberately a raw unpaired post-return snapshot, not a paired cycle-observer record. Exact AK attempt 1 then passed its separate exact-runtime, native-reboot, changed-Gemian-return, and post-return full-`boot2`-hash gates; the owner attested that its local console was readable. AK's evidence chain is explicitly unpaired (`paired_cycle_observer=no`). The captured LK still requires manual silver-button `boot2` selection; typed commands do not select a slot. | `observed` | `missing` | `required-nonfree` | [AB runtime](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/runtime-candidate-ab-attempt-1-20260721.txt); [Candidate AI attempt 1](../experiments/2026-07-22-a72-reject-gate-kernel-split/results/runtime-candidate-ai-attempt-1-20260722.txt); [AJ attempt 1 identity mismatch](../experiments/2026-07-22-a72-reject-cpu8-request/results/hardware-attempt-1-identity-mismatch-20260722.txt); [AJ attempt 2](../experiments/2026-07-22-a72-reject-cpu8-request/results/hardware-attempt-2-runtime-reboot-return-20260722.txt); [AK attempt 1](../experiments/2026-07-22-a72-reject-cpu9-request/results/hardware-attempt-1-20260723.txt); [LK selection audit](../experiments/2026-07-12-boot-contract-recovery/results/lk-boot2-software-selection-audit-20260718.txt) |
| Boot handoff DT fixups | Retained MT6797 LK FDT contract | all | appended DTB, `/memory`, `/chosen`, `/reserved-memory` | LK early-loads the appended DTB, rewrites model/CPU/memory/chosen/firmware metadata, and appends runtime mblock reservations after an overlap check. Candidate AN first captured the final post-LK FDT privately. Candidate AO's 52,567-byte live tree passed exactly 37 allowlisted changes. Candidate AP repeated the whole-tree gate for its materially different final DT: the 52,655-byte live tree again had 37 entries—10 added nodes, 2 removed predecessor reservation nodes, 23 added properties on existing nodes, and 2 changed properties. Header reservations and boot CPU were unchanged; AP's handoff node remained byte-exact, its `<0x3 0x36>` clock resolved uniquely to infracfg, and exact phandle `0x2c` connected enabled childless I2C6 to the access controller. Observer, DA9214, A72-power, and legacy-DVFSP nodes remained absent. ATAG command line and bootargs were bounded, printable, and byte-equal; device-specific values were validated in memory and not retained. This validates AP's exact handoff tree, not I2C6 runtime success or every future candidate. | `observed` | `local` | `required-nonfree` | [LK FDT fixup audit](../experiments/2026-07-13-lk-fdt-fixup-recovery/README.md); [Candidate AN experiment](../experiments/2026-07-24-mt6797-dvfsp-handoff-observer/README.md); [Candidate AO live-FDT result](../experiments/2026-07-24-mt6797-dvfsp-one-way-handoff/results/live-fdt-candidate-ao-validated-20260724.txt); [Candidate AP result](../experiments/2026-07-24-mt6797-dvfsp-i2c6-consumer/results/candidate-ap-hardware-20260724.txt); preserve private-value handling and rerun the whole-tree gate for each materially different final DT |
| CPU topology | 8x Cortex-A53 + 2x Cortex-A72 | all | MT6797 | The hardware topology uses MPIDs `0x000`–`0x003`, `0x100`–`0x103`, and `0x200`–`0x201`. Candidate O brought CPU1–7 online once through standard hotplug, and AD/AI later established the boot-time eight-A53 boundary with CPU0–7 advancing and CPU8/9 offline. Corrected AI keeps generic PSCI for CPU0–7 and assigns CPU8/9 a fail-closed pre-PSCI method with disable unavailable and no power-off callback. Exact AK attempt 1 reported `possible/present=0-9`, `online=0-7`, and `offline=8-9`; CPU0–7 accounting advanced through the 45-plus-5-second stability window. Exactly one CPU8 gate rejection and one CPU8 `-11` occurred, followed in order by exactly one CPU9 gate rejection and one CPU9 `-11`. No CPU8/9 secondary transition or other fault signature occurred. This passes both fail-closed dispatch controls, not an A72 bring-up: CPU8 and CPU9 remained offline, and no Cortex-A72 support claim is established. Stress/coherency, A72 power, DVFS, idle, suspend, and thermal behavior remain unproved. | `partial` | `local` | `unknown` | [Candidate O runtime](../experiments/2026-07-18-cortex-a53-sweep-diagnostic/results/runtime-candidate-o-attempt-1-20260718.txt); [Candidate AI attempt 1](../experiments/2026-07-22-a72-reject-gate-kernel-split/results/runtime-candidate-ai-attempt-1-20260722.txt); [AK attempt 1](../experiments/2026-07-22-a72-reject-cpu9-request/results/hardware-attempt-1-20260723.txt); retain generic PSCI for the proven A53 path and keep both Cortex-A72 cores deferred |
| Cortex-A72 external power contract | DA9214 BUCKB, PWRAP reset, SPM isolation, SRAM-LDO, MP2/CCI | named Gemini PDA | Linux plus retained secure firmware | Offline source/firmware analysis assigns external DA9214/PWRAP/reset-release/isolation preparation and post-success DCM to Linux, while captured secure firmware owns initial B PLL/mux/divider, MP2/core MTCMOS/reset, internal bus protection, and CCI coherency admission. Both live TEE slots match the analyzed payload. Private-binary reconciliation separates the active March 29 Gemian boot image from the different May 24 `gbp59e00a` installed package; the active exact public commit remains unresolved. A bounded load run observed CPU8 online and then offline, with CPU9 excluded, but the sequential observer missed the transaction. Candidate AL's separate regulator prerequisite failed legacy DA9214 identity. Candidate AP then tested only the preceding childless-I2C6 ownership layer and failed closed before adapter bind because AP_DMA did not satisfy its absolute-gated cleanup oracle. The first owner-local observer draft is also not boot-ready: it bypassed a vendor write guard, could continue after a missing client, put a large snapshot in the 240-us staging window, and changed read semantics. The SRAM-LDO service's zero return is not completion evidence, no safe inverse is proven, and HPS action-end local counts are not CPU completion proof. Draft patch 0093 remains unsafe and unselected. Candidate AM remains HOLD pending attributable AP_DMA ownership and baseline-preserving I2C6 cleanup, corrected regulator identity/page handling, separate resume validation, and a reworked owner-local capture. | `unknown` | `local` | `required-nonfree` | [A72 firmware/power contract](../experiments/2026-07-22-a72-firmware-power-contract/README.md); [load-assisted CPU8 observation](../experiments/2026-07-23-gemian-a72-load-assisted-observation/results/live-attempt-1-20260723.txt); [Candidate AL runtime](../experiments/2026-07-23-da9214-resource-only/results/runtime-candidate-al-attempt-1-20260723.txt); [Candidate AP result](../experiments/2026-07-24-mt6797-dvfsp-i2c6-consumer/results/candidate-ap-hardware-20260724.txt); resolve every predecessor before reviewing any Candidate AM power-on implementation |
| Vendor CPU/scheduler policy | Gemian `3.18.41+` HMP/HMP+, HPS and PPM | named Gemini PDA | Three clusters: CPUs 0–3, 4–7, and 8–9 | The live kernel boots with `maxcpus=5`, then its private HPS/PPM stack dynamically hotplugs clusters and later collapses to CPU0 at idle. Exact active-source reconciliation corrects the earlier HPS-log interpretation: action-end leading tuples are algorithm-local counts that advance without checking `cpu_up()`/`cpu_down()`, so `<4>(4)(2)` proves policy state/intent, not all-ten completion. A later bounded direct sysfs capture does prove one CPU8 online/offline cycle; CPU9 and an all-ten simultaneous mask remain unconfirmed. Scheduling is downstream HMP/HMP+ with MediaTek runqueue, PPM, private DVFS/iDVFS, EEM, and Android-era hotplug policy, not EAS. Mainline should preserve only the evidenced three-cluster topology: do not transplant HMP/HPS/PPM or copy source-derived capacities as `capacity-dmips-mhz`. Add a standard `cpu-map` only after separate mainline CPU8 and CPU9 power-on tests; defer capacity, OPP, cpufreq, energy-model, idle, and thermal policy until measured providers exist. | `observed` | `not-applicable` | `private-power-services` | [Gemian CPU/scheduler policy correction](../experiments/2026-07-21-gemian-cpu-scheduler-policy/results/hps-online-count-adjudication-20260723.txt); [direct CPU8 observation](../experiments/2026-07-23-gemian-a72-load-assisted-observation/results/live-attempt-1-20260723.txt); HPS tuple counts are not completion evidence |
| CPU frequency / DVFS | Complete vendor `mt-cpufreq`, LL/L/B clusters plus CCI and active EEM/PTP calibration | all | MT6797 ARM PLL/muxes, shared EEM/thermal window, DA9214 Vproc, SRAM tracking, optional DVFSP | Planet source recovers function/date efuse table selection, four levels plus B TT override, direct cluster PLL programming, CCI coupling, and 10--30 mV Vproc/Vsram tracking. Runtime EEM detectors actively rewrite calibrated OPP voltages. Linux 7.1.3 has no MT6797 cpufreq or SVS match; its OPP/regulator/clock-reparent and SVS phase/adjustment patterns are reusable, but the current MT6797 CCF also lacks the vendor ARMPLL/CPU-mux/CCI clock contract. The CPU PLL windows are shared with SPM/ATF through an MCUMIXED hardware semaphore, and B-cluster PLL/SRAM operations use secure BigiDVFS calls, so a dedicated MT6797 clock backend/new driver is justified once those ownership APIs are proven. The local DTS now omits the vendor per-CPU `clock-frequency` hints because Linux 7.1.3's CPU binding rejects them; they remain descriptive evidence only, and the generic cpufreq clock/regulator/OPP contract is still absent. A fresh read-only capture shows the active policy lives under private `/proc/cpufreq` rather than standard `cpufreq/policy*` sysfs, with dynamic LL/L/B/CCI transitions and only CPUs 0–1 online at capture; this is vendor-policy evidence, not a mainline support claim. The current package audit confirms generic cpufreq/SVS modules but no MT6797 consumer, OPP table, or idle-state table; the current 72-patch build remains disabled-only | `observed` | `missing` | `unknown` | [CPU/DVFS recovery](../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/README.md), [runtime CPU policy capture](../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/results/runtime-cpu-policy-20260714.txt), [current PM package validation](../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/results/mainline-pm-current-72-package-validation.txt), [EEM calibration contract](../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/results/eem-calibration-contract.md), [cpufreq/DTS gap](../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/results/mainline-cpufreq-dt-gap.md), [CPU clock backend source design](../experiments/2026-07-12-mt6797-clock-power-reset-recovery/results/mt6797-cpu-clock-backend.md), [current 72-patch CPU clock audit](../experiments/2026-07-12-mt6797-clock-power-reset-recovery/results/mt6797-cpu-clock-backend-current-72-20260714.txt), [source validation](../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/results/mainline-cpufreq-source-validation.txt), and [mainline design](../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/results/mt6797-pm-mainline-design.md); prove shared-resource ownership, calibration, rail ownership, PLL/mux sequencing, and rollback before enabling an MT6797 variant/new driver |
| Thermal sensors | Vendor `mtkts*` zones and `mt6797-therm_ctrl` | all | thermal/AUXADC at `0x1100b000`, SPI 78; AUXADC at `0x11001000` | 13 zones enumerate but all are disabled and several readings are sentinels. Live proc calibration and complete vendor source recover six logical banks, five sensor inputs, three efuse words, channel 11, and an ID-dependent raw-to-temperature formula. Linux 7.1.3 has no MT6797 match, but its generic AUXADC-thermal bank/calibration architecture is reusable; patch 0057 adds an MT6797-specific disabled-only variant for timing, valid-mask, buffer, and ADC-OE conversion, with a complete `MAX_NUM_VTS` fallback initialization. `configs/gemini.fragment` selects both generic thermal and AUXADC modules. The board DTS now wires a fixed 12-byte `calibration-data` cell to the bounded, read-only, root-only LK `/chosen/atag,devinfo` provider in patch 0057a; the provider, Gemini DTB, focused binding schema, and full guest-only package pass compile validation, while both thermal/AUXADC nodes remain disabled. Runtime enablement is still blocked until the final LK handoff is observed and invalid calibration is made explicitly fail-closed. The vendor source audit shows words 31–33 are read through the bootloader-injected `/chosen/atag,devinfo` payload; Linux's generic MMIO efuse provider has no MT6797 match, so direct `efusec` mapping is not an established substitute. Runtime IRQ/protection, idle/wakeup, and trips remain unproven. | `observed` | `missing` | `unknown` | [MT6797 thermal recovery](../experiments/2026-07-13-mt6797-thermal-recovery/README.md), [source validation](../experiments/2026-07-13-mt6797-thermal-recovery/results/mainline-thermal-source-validation.txt), [current package policy audit](../experiments/2026-07-13-mt6797-thermal-recovery/results/mainline-thermal-current-72-policy-20260714.txt), [thermal safety contract](../experiments/2026-07-13-mt6797-thermal-recovery/results/mainline-thermal-safety-contract-20260714.txt), [calibration ownership audit](../experiments/2026-07-13-mt6797-thermal-recovery/results/mainline-thermal-calibration-ownership-20260714.txt), [provider build](../experiments/2026-07-13-mt6797-thermal-recovery/results/mt6797-calibration-provider-build-20260714.txt), [variant validation](../experiments/2026-07-13-mt6797-thermal-recovery/results/mt6797-mainline-variant-validation.txt), and [CPU/DVFS recovery](../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/README.md); preserve the bootloader calibration ABI, validate final handoff/invalid-calibration behavior, then test raw samples/trips |
| Idle / DVFSP | Vendor dpidle/SODI/MCDI plus optional hybrid DVFSP | all | CSPM `0x11015000`, CSRAM `0x0012a000`, PSCI | WFI is active; deep states show zero usage and vendor logs report blocked entry; mainline has only generic PSCI; the current package audit confirms one PSCI node and ten CPUs but no idle-state table, OPPs, or DVFSP/SPM consumer; the current DTS defers the undocumented DVFSP node because Linux has no matching driver or binding | `observed` | `missing` | `unknown` | [Current PM package validation](../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/results/mainline-pm-current-72-package-20260714.txt); [PM recovery](../experiments/2026-07-12-cpufreq-thermal-suspend-recovery/README.md); preserve the register/IRQ evidence and verify firmware idle parameters before adding states |
| Interrupts/timers | GICv3, ARMv8 architectural timer | all | MT6797 | Live `arm,armv8-timer` uses PPIs 13/14/11/10 and 13 MHz; `arch_sys_counter`/`arch_sys_timer` are active downstream; the current package links generic ARM timer/PSCI/GIC support and carries the same four PPIs; Linux 7.1.3 `arm_arch_timer` and generic GIC bindings match | `observed` | `released` | `none` | [CPU/PSCI/timer recovery](../experiments/2026-07-13-cpu-psci-timer-recovery/README.md); [current-package audit](../experiments/2026-07-13-cpu-psci-timer-recovery/results/mainline-cpu-psci-timer-current-72-package-20260714.txt); verify timer interrupts and clockevents after mainline boot; vendor CPU GPT is separate |
| RAM | LPDDR and reserved regions | all | EMI / firmware carve-outs | Live Gemian exposes ~3.68 GiB as discontiguous System RAM with fixed ATF/LK/framebuffer/CCCI/SCP regions plus dynamically allocated CONSYS/SCP-share/SPM reservations; local DT preserves the fixed regions but does not yet reproduce every dynamic ownership contract | `observed` | `local` | `unknown` | [Memory carve-out recovery](../experiments/2026-07-13-memory-carveout-recovery/README.md); compare two LK boots, reject the generic contiguous EVB range, and keep firmware/DMA consumers disabled until placement is resolved |
| Clocks/resets | MT6797 clock tree and three infracfg reset banks | all | topckgen/infracfg/apmixed plus CAM/MJC and MFG | The local series adds evidenced reset offsets `0x120`/`0x124`/`0x128`, CAM/MJC gates, and disabled-only MFGSYS gate/resource patches 48–49; patch 50 wires the vendor MFG 52 MHz preclock, with no runtime clock test | `unknown` | `local` | `none` | Runtime-test clock gates and reset consumers; never pulse an unverified line |
| Power domains | MT6797 SCPSYS, including MFG and four MFG cores | all | SCPSYS/SPM `0x10006000` | Patches 47 and 50 reuse generic SCPSYS sequencing, add the live separate-`0x33c` SRAM control/ack fields, MFG hierarchy, and required 52 MHz preclock; build-only, no domain power-on test | `unknown` | `local` | `none` | [Clock/power/reset recovery](../experiments/2026-07-12-mt6797-clock-power-reset-recovery/README.md); validate domain map and safe sequencing |
| M4U/SMI fabric | One MT6797 M4U with seven larbs and 71 ports | all | M4U `0x10205000`, SMI common `0x14022000`, larbs `0x12002000`–`0x1a001000` | Linux generation-two IOMMU/SMI frameworks are reusable with dedicated MT6797 flags, `0x1554` bus routing, and MT8167-style larb MMU register `0xfc0`; all nodes remain disabled and the recovered table has no GPU port | `unknown` | `local` | `none` | [M4U/SMI recovery](../experiments/2026-07-12-mt6797-m4u-smi-recovery/README.md); attach one verified DMA consumer at a time |
| UART | MT6797 UART0 debug console; UART1–3 auxiliary ports | all | UART0–3 at `0x11002000`–`0x11005000`, GIC SPIs 91–94 | Live `ttyMT0`–`ttyMT3` bind to vendor `mtk-uart`; Linux 7.1.3 `8250_mtk` and the MT6797 compatible provide the correct 16550/PIO reuse path, and explicitly disable DMA for a console. Vendor VFIFO/AP-DMA windows remain intentionally unrepresented. Captured Gemian and independent reference DT evidence identify UART0 RX GPIO97/function 1 and TX GPIO98/function 1. Candidate L includes that correction in an independently reproduced artifact with a matching full logical-`boot2` readback. During L attempt 2 the exact initramfs suffix was visible on fbcon while a connected serial adapter received no bytes. This makes UART operationally unavailable under the tested setup, but does not distinguish a physical fault from tty registration, console naming, baud, pinmux, or electrical issues. | `unknown` | `released` | `none` | [UART/console recovery](../experiments/2026-07-13-uart-console-recovery/README.md); [Candidate L](../experiments/2026-07-17-uart-pstore-observability/README.md); do not use UART as the sole next success criterion; reconcile LK's downstream `ttyMT0` token with mainline `ttyS*` only through a separate discriminating test |
| Watchdog | MT6797 TOPRGU at `0x10007000` | all | TOPRGU / SPI137 bark IRQ | Linux 7.1.3 `mtk_wdt` covers the MT6797 register and reset-controller protocol. Candidate M proved the no-IRQ registration, 31-second timeout, one handoff ping, automatic return, watchdog boot reason, and cross-version console retention; N–P repeated that foundation. W again proved exact association and automatic watchdog return. AA r1 stayed interactive for >123 seconds without an automatic watchdog owner, then its typed userspace countdown returned through TOPRGU. AB patch 0087 raises MT6797's restart notifier above PSCI; its exact container has no userspace watchdog, countdown, fallback, or automatic reboot. In one attended AB run, 45 seconds idle caused no reset and bare `reboot` reset immediately; retained pstore places request and final restart 27.854 ms apart. Exact AH attempt 2 again had no automatic countdown or userspace-watchdog reset; one bare `reboot` request produced retained `mtk-wdt ... shutdown` and `reboot: Restarting system` lines 26.273 ms apart before Gemian returned under a changed boot ID. These retained-log intervals are not instrumented command-to-LK timing. Watchdog-class reasons do not independently distinguish reset sources, while the command path and ownership support kernel TOPRGU SWRST. | `partial` | `local` | `none` | [AA r1 runtime](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/runtime-candidate-aa-r1-attempt-1-20260721.txt); [AB runtime](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/runtime-candidate-ab-attempt-1-20260721.txt); [AH attempt 2](../experiments/2026-07-22-ad-contract-af-kernel-split/results/runtime-candidate-ah-attempt-2-20260722.txt); native kernel restart is observed across AB and AH, while bark/pretimeout and exact-candidate repeatability remain open |
| Pinctrl/GPIO/EINT | MT6797 pin and 192-line external-interrupt controllers | all | pinctrl plus EINT at `0x1000b000` | Local series adds the decoded 172-entry map, SPI170 resource, virtual GPIO262/EINT176 and built-in EINT186 without extending physical register ranges; vendor pinctrl source does not encode a reusable map | `unknown` | `local` | `none` | [EINT/pinctrl recovery](../experiments/2026-07-12-mt6797-eint-recovery/README.md); boot-test interrupt delivery, polarity, mask/ack, debounce, and wake on controlled consumers |
| I2C | MT6797 controllers | all | I2C0-9 | SoC nodes and generic driver exist; patch 0086 directly matches MT6797 to the existing `mt8173_compat` controller data; patches 0099–0102 add AP's local I2C6 ownership gate | `partial` | `released` | `none` | W's one exact run bound `1101c000.i2c`, successfully probed I2C5 client `0-005b`, and cleared V's repeated combined-read `-110`; this supports only I2C5/AW9523. AL later completed an I2C6 transaction but lacked the recovered DVFSP ownership contract. AP tested that prerequisite with no client: its provider faulted because shared AP_DMA remained ungated, so I2C6 returned `-EIO` before binding an adapter and issued no transfer. I2C6 is therefore not promoted. See [W runtime](../experiments/2026-07-19-keyboard-wrrd-diagnostic/results/runtime-candidate-w-attempt-1-20260719.txt), [AL runtime](../experiments/2026-07-23-da9214-resource-only/results/runtime-candidate-al-attempt-1-20260723.txt), and [AP result](../experiments/2026-07-24-mt6797-dvfsp-i2c6-consumer/results/candidate-ap-hardware-20260724.txt); identify AP_DMA ownership and validate a baseline-preserving cleanup contract before another I2C6 run; error recovery, suspend, stress, and other controllers remain unproved |
| Indicator LEDs | AWINIC AW9120, five RGB blocks plus auxiliary indicators | all | I2C3 `0x2c`, GPIO245 active-high PDN | Live Gemian binds chip ID `0xb223`; retained source and the installed Gemian daemon map visible RGB outputs 1–15, GPIO74/75 I2C3 pins, 5 ms PDN timing, and the 8-bit-register/big-endian-16-bit protocol. Linux 7.1.3 has no matching driver. A new generic regmap LED-class/multicolor driver and binding are justified; the vendor `/proc` ABI is not. The first one-channel test should cap current at the documented 3.5 mA minimum and enable only I2C3/`0x2c` without scanning shared HDMI/EDID addresses | `observed` | `missing` | `none` | [AW9120 hardware record](hardware/gemini-gemian-baseline.md#aw9120-indicator-leds); [screen/LED selection](../experiments/2026-07-16-screen-marker-diagnostic/results/display-path-selection-20260716.txt); validate block-1 green visibility under Gemian before adding the bounded mainline driver, independently of the now-visible simplefb/fbcon path |
| PMIC/regulators | MT6351 E2 confirmed by HWCID `0x5140`, SWCID `0x5120`; 9 bucks plus 30 unique LDO controls | all | MT6797 pwrap, PMIC EINT176 | The local series supplies pwrap, reset/EINT providers, MT6351 MFD/IRQ, a schema, and a 39-rail driver mechanically checked against raw live selectors. The current 72-patch artifact compiles the driver, passes its focused binding and direct DT-schema checks, and places eMMC consumers under the MT6351 regulator container; E3 (`0x5130`) is intentionally rejected until separately evidenced. Pwrap and MFD probe are stateful/write-capable, so mainline runtime remains gated behind external recovery and before/after register capture | `unknown` | `local` | `none` | [PMIC recovery](../experiments/2026-07-11-mt6351-pmic-recovery/README.md); [first-boot probe audit](../experiments/2026-07-14-first-boot-probe-audit/README.md); [current 72-patch validation](../experiments/2026-07-11-mt6351-pmic-recovery/results/mainline-mt6351-current-72-validation-20260714.txt); add conservative Gemini constraints/consumers; validate readback before any voltage or OPP change |
| External GPU regulator | Richtek RT5735, live vendor DT at I²C7 `0x1c`, product ID `0x10`; separate `vgpu_buck@0x60` candidate is unbound | all | MT6797 I²C7 / external VGPU buck | Patch 51 adds a standard VSEL0 regulator provider and disabled-only Gemini node; no runtime probe or voltage transition | `observed` | `local` | `none` | [RT5735 VGPU recovery](../experiments/2026-07-12-rt5735-vgpu-recovery/README.md); verify identity and rail wiring before attaching Panfrost or enabling OPPs |
| RTC | MT6351 RTC at PMIC offset `0x4000`, vendor `rtc0`/hctosys active | all | MT6351 PMIC IRQ 9 | Local MFD resource, shared-driver match, and fixed-function DT node exist; runtime behavior remains untested | `unknown` | `local` | `none` | Run bounded read/set/alarm/power-cycle tests from mainline |
| Charger/fuel gauge | BQ25890 at I2C0 `0x6b`; FAN49101 at `0x70`; RT9466 alternative at `0x53` unbound | all | I2C/PMIC | Vendor/runtime identity is recovered; the vendor BQ register map matches Linux 7.1.3, but its presence check is only a nonzero read of `0x03`. Upstream BQ25890 core is reusable after Linux part/revision ID (`0x14`), IRQ, rail, and limit validation. Patch 0055 adds a dedicated `onsemi,fan49101` regulator driver/binding and disabled-only Gemini node; the earlier 71-patch source/object and binding checks pass, while runtime identity/readback, control/reset semantics, and rail ownership remain unverified. The current package audit confirms `bq25890_charger.ko` and `fan49101.ko` are packaged, but the Gemini DTB has no enabled charger, battery, or fuel-gauge consumer. Vendor fuel-gauge HAL still needs a standard power_supply/IIO design | `observed` | `local` | `unknown` | [Charger and fuel-gauge recovery](../experiments/2026-07-12-charger-power-recovery/README.md); [current package audit](../experiments/2026-07-12-charger-power-recovery/results/mainline-charger-current-72-package-20260714.txt); [BQ25890 reuse audit](../experiments/2026-07-12-charger-power-recovery/results/bq25890-reuse-audit-20260713.txt); [FAN49101 register contract](../experiments/2026-07-12-charger-power-recovery/results/fan49101-register-contract.txt); [prior 70-patch module validation](../experiments/2026-07-12-charger-power-recovery/results/fan49101-current-70-module-validation-20260713.txt); keep duplicate `bq24261` node and RT9466 alternative disabled, then validate read-only telemetry before charge control |
| eMMC | Internal storage | all | MSDC0 `0x11230000`, SPI79 | Live DF4064 eMMC is 8-bit HS400 at 200 MHz/1.8 V; current Linux `mtk-sd` reuses the dedicated MT6797 compatibility record (`clk_div_bits=12`, PAD_TUNE0, async/data tuning, no stop-clock/enhanced-RX/64G paths). The Gemini node deliberately caps first boot at 25 MHz legacy timing, non-removable, with VEMC/VIO18 supplies and pinmux-only states. Source, DTB, package, and fresh read-only live capture are recorded; no mainline boot or MMC I/O has run | `observed` | `partial` | `build-only` | [MSDC recovery](../experiments/2026-07-12-mt6797-msdc-recovery/README.md); [first-boot probe audit](../experiments/2026-07-14-first-boot-probe-audit/README.md); [current 72-patch validation](../experiments/2026-07-12-mt6797-msdc-recovery/results/mainline-msdc-current-c2d-reconciliation-20260714.txt); boot from external recovery with a read-only rootfs before enabling HS200/HS400 |
| microSD | Removable storage | all | MSDC1 `0x11240000`, SPI80, card-detect EINT6 | Live host has no card, 0 Hz, power off, and 3.3 V reset state. MT6797 compatibility exists, but card-detect polarity/GPIO67, pin drive, VMCH/VMC ownership, UHS voltage switching, and remove/reinsert behavior remain unvalidated; node stays disabled | `described` | `partial` | `build-only` | [MSDC recovery](../experiments/2026-07-12-mt6797-msdc-recovery/README.md); [current 72-patch validation](../experiments/2026-07-12-mt6797-msdc-recovery/results/mainline-msdc-current-c2d-reconciliation-20260714.txt); validate detection, I/O, remove/reinsert, and suspend separately |
| Keyboard | AW9523B / `aw9523_key` | all | I2C5 `0x5b`, GPIO87/EINT10, shutdown GPIO58 | Linux 7.1.3 reuses upstream `pinctrl-aw9523` plus generic `gpio-matrix-keypad`. Patches 0054/0076 describe the disabled 8×7 active-low matrix; 0082 adds I2C5/GPIO58 resources while retaining the upstream active-high logical reset contract; 0083/0084 add generic 20-ms polling; 0085 corrects EINT10; and 0086 selects the evidenced MT8173-generation I2C data. In one W run the provider and matrix bound, `/dev/input/event0` appeared, H/E/L/P/Enter events survived, and the owner observed working input. X later worked by owner report; Z then booted once with the keyboard still working, but neither retained individual-key evidence. Historical AA r0 was rejected before boot and has been replaced. AA r1 keeps exact Z's hardware path and adds an eight-table VT policy. In attended attempt 1, retained pstore proves loaded-now Unicode mode plus exact `KDGKBENT` verification of all 2,048 entries/table invariants, exact AW9523/matrix/event0 identity, and A/S press-release events; the owner reported the new keymap working. F1–F10 and Page Up/Page Down remain unconfirmed rather than failed because there was no visible discriminator. | `partial` | `local` | `none` | [Keyboard record](hardware/keyboard.md); [W runtime](../experiments/2026-07-19-keyboard-wrrd-diagnostic/results/runtime-candidate-w-attempt-1-20260719.txt); [AA r1 runtime](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/runtime-candidate-aa-r1-attempt-1-20260721.txt); AA r1 adds retained A/S events to W's earlier H/E/L/P/Enter record and establishes owner-observed new-map operation once, but not complete legend coverage or repeatability |
| Lid/power keys | MT6351 power press/release IRQs observed; hall/toggle inputs remain separate | all | PMIC IDs 0/2 through EINT176; hall GPIO66/EINT5; toggle GPIO93/EINT16; `mtk-kpd` KEY_POWER 116 | Local MFD and generic keys driver support distinct MT6351 press/release IRQs; standard `gpio-keys` can model the hall `SW_LID` path, while the toggle’s F9/F10 policy is unresolved. The latest passive capture shows hall state 0 with EINT5 activity and toggle state 0 with no EINT16 activity; no transition was stimulated. Patch 0074 records a disabled-only GPIO66 active-low `SW_LID` candidate; the packaged DTB/module audit is complete, but runtime remains untested | `unknown` | `local` | `build-only` | [Hall/lid/switch recovery](../experiments/2026-07-12-hall-lid-switch-recovery/README.md); [latest passive result](../experiments/2026-07-12-hall-lid-switch-recovery/results/live-hall-lid-recovery-20260714.txt); [75-patch package audit](../experiments/2026-07-12-input-backlight-recovery/results/mainline-display-input-current-75-package-20260714.txt); add power-key-only board data with hardware long-press reset disabled, then validate input and wake separately |
| Display pipeline | MT6797 MMSYS/SMI/IOMMU/CMDQ/MM mutex/OVL/PQ/RDMA/DSI | all | multimedia | Local series adds disabled multimedia providers; native DRM/DSI/PHY remains disabled or module-only. M–P established readable loader-retained fbcon. W produced a visible shell in the correct large font but with mixed kernel logs. X and Z booted and worked by owner report, but clean tty1 was not separately transcribed or retained. AA r1 retained that loader-console basis and booted successfully. The owner observed a working console on exact AH attempt 2 and the live collector validated the chosen simplefb/LK-reservation contract. This remains loader-retained simplefb evidence, not native display ownership. | `unknown` | `local` | `build-only` | [Candidate W runtime](../experiments/2026-07-19-keyboard-wrrd-diagnostic/results/runtime-candidate-w-attempt-1-20260719.txt); [Candidate AA r1 runtime](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/runtime-candidate-aa-r1-attempt-1-20260721.txt); [AH attempt 2](../experiments/2026-07-22-ad-contract-af-kernel-split/results/runtime-candidate-ah-attempt-2-20260722.txt); do not promote native DRM, DSI, panel, backlight, or clean tty1 support |
| Panel/backlight | Compiled-in selected NT36672-family module; exact suffix unverified; bsg100 direct hardware evidence names SSD2092 on its tested unit | all | single DSI0, 4-lane RGB888 burst video; MT6797 DISP_PWM at `0x1100f000`; LP3101 bias at I2C1 `0x3e` | Patch 43 reuses the NT36672E framework with Gemini-specific mode, 165-register sequence, supply names, and delays; its packet selector preserves the vendor MT6797 rule that commands below `0xb0` use DCS packets and commands at/above `0xb0` use generic packets. Patch 44 adds a provisional one-clock MT6797 display-PWM contract and disabled resource node; bsg100's hardware-working native DTS instead uses the upstream two-clock interface with `CLK_TOP_MUX_PWM` as `main` and `CLK_INFRA_DISP_PWM` as `mm`, so patch 44 must be re-audited before enablement. The module-inclusive package carries `panel-novatek-nt36672e.ko`, `pwm-mtk-disp.ko`, and `pwm_bl.ko`, but the PWM node and panel/backlight consumer remain disabled/absent. Panel identity is unresolved: the named device has an unbound `solomon_touch@0x53` candidate and mixed vendor log labels, while bsg100 has direct SSD2092 reads | `unknown` | `local` | `build-only` | [Panel recovery](../experiments/2026-07-11-gemini-panel-recovery/README.md); [current panel validation](../experiments/2026-07-11-gemini-panel-recovery/results/mainline-panel-current-72-validation-20260714.txt); [packet-semantics audit](../experiments/2026-07-11-gemini-panel-recovery/results/nt36672-packet-semantics-20260714.txt); [bsg100 panel cross-check](../experiments/2026-07-13-bsg100-gemini-linux-comparison/results/bsg100-panel-crosscheck-20260714.txt); [bsg100 fbcon commit audit](../experiments/2026-07-13-bsg100-gemini-linux-comparison/results/fbcon-commit-035d4b0-20260716.md); [current display/input package audit](../experiments/2026-07-12-input-backlight-recovery/results/mainline-display-input-current-72-package-20260714.txt); resolve panel identity and the PWM clock contract before a controlled native panel test |
| Touchscreen | Novatek `cap_touch` / NT36772 | all | I2C4 `0x62`, GPIO85/EINT8, reset GPIO68, vendor `NVT-ts` | A fresh filtered vendor probe log records trim bytes `00 00 03 72 66 03`, matching masked source/ELF trim-table entry 8 and selecting NT36772 event map `0x11e00`; PID `0x0101`, firmware `0x05`/bar `0xFA`, and IRQ 392 are also observed. Linux 7.1.3's `novatek-nvt-ts` targets NT11205/NT36672A and does not implement this verified alternate-address/xdata contract. Patch 0075 adds a disabled-by-default NT36772 backend boundary; its object/module and binding checks pass, and the complete 76-patch Image/DTB package now validates, but the touchscreen DT node and hardware runtime remain untested | `observed` | `released` | `build-only` | [NVT source validation](../experiments/2026-07-12-input-backlight-recovery/results/nvt-source-validation-current-20260714.txt), [NVT ELF validation](../experiments/2026-07-12-input-backlight-recovery/results/nvt-elf-validation-20260714.txt), [live trim identity](../experiments/2026-07-12-input-backlight-recovery/results/nvt-live-trim-identity-20260714.txt), [NT36772 boundary checks](../experiments/2026-07-12-input-backlight-recovery/results/nt36772-mainline-boundary-20260714.txt), [76-patch Image/DTB package](../experiments/2026-07-12-input-backlight-recovery/results/mainline-display-input-current-76-package-20260714.txt), [protocol comparison](../experiments/2026-07-12-input-backlight-recovery/results/nt36772-protocol-compare-20260714.txt), [patch 0075](../patches/v7.1.3/0075-input-touchscreen-novatek-add-NT36772-backend.patch); validate logical-address `0x01` transport, rails/reset, runtime events and suspend before enabling the node; keep firmware update disabled by default |
| USB-C ports | Device/host/role switching | all | USB1 `0x11200000`, USB3 `0x11270000`/SIF windows, MT6797 PHY, two FUSB301 at I2C0/I2C1 `0x25` | Live vendor topology and clocks are captured. USB1's MAC/FIFO/DMA protocol is source-equivalent to Linux MUSB/Inventra; patches 0066–0070 add the local MT6797 T-PHY, MTU3/xHCI, and USB11 MUSB glue/topology boundaries, while patch 0056 adds the local FUSB301 driver. The broad package keeps consumers disabled. The exact diagnostic path instead enables one USB2 peripheral-only/high-speed T-PHY/MTU3 path with forced B-device session and built-in `g_ether`. M/N retained pstore proves successful T-PHY/MTU3 probe and gadget pull-up. Candidate AC then established exact USB identity, selected configuration, fixed-MAC host interface, carrier, static `10.15.19.82/24`, ping, TCP marker, and bounded unauthenticated development shell on a direct no-bridge link. Exact AH attempt 2 independently retained that service. The probe still uses dummy `vusb33`; these results do not establish an electrical D+ waveform, physical-port identity, host mode, role switching, VBUS, Type-C, charging, mass storage, or Internet bridging. | `partial` | `local` | `none` | [USB/Type-C recovery](../experiments/2026-07-12-usb-typec-recovery/README.md); [sanitized mainline gadget evidence](../experiments/2026-07-16-usb-gadget-diagnostic/results/retained-pstore-mtu3-gadget-evidence-20260718.txt); [Candidate AC experiment](../experiments/2026-07-21-usb-gadget-ethernet/README.md); [AH attempt 2](../experiments/2026-07-22-ad-contract-af-kernel-split/results/runtime-candidate-ah-attempt-2-20260722.txt); retain the isolated gadget-development path while keeping host/role/power work separate |
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
