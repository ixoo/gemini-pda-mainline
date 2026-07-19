# Pinned stable-kernel patch workflow

This repository stores an ordered patch series and the inputs needed to apply it
to a verified stable Linux release. It does not store a Linux source tree or
build outputs.

## One-command build

From macOS:

```sh
./scripts/dev-vm build-kernel
```

That command performs the complete workflow inside the ARM64 development VM:

1. reads `kernel/manifest.json`;
2. downloads the pinned kernel.org tarball into the guest cache;
3. verifies its SHA-256 before extraction;
4. creates a managed source tree on the guest ext4 filesystem;
5. applies every patch named in `patches/series`, in order;
6. starts from arm64 `defconfig` and merges the project fragments;
7. builds `Image`, the LK-compatible gzip-compressed `Image.gz`, and all arm64
   DTBs out-of-tree;
8. packages both kernel forms, the MediaTek DTBs, configuration, provenance,
   and checksums under `~/artifacts/gemini-pda/`.

The download, source, build, and artifact locations never live in the macOS
checkout. Print their exact guest paths with:

```sh
./scripts/dev-vm kernel paths
```

## Patch series

Create logical commits in a disposable development clone, then export them with
`git format-patch`. Store the resulting files below a directory named for the
baseline and list them in application order:

```text
patches/
  series
  v7.1.3/
    0001-arm64-dts-mediatek-add-gemini-pda.patch
    0002-clk-mediatek-add-required-clock.patch
```

`patches/series` would contain:

```text
v7.1.3/0001-arm64-dts-mediatek-add-gemini-pda.patch
v7.1.3/0002-clk-mediatek-add-required-clock.patch
```

Blank lines and lines beginning with `#` are ignored. Missing files, unsafe
paths, whitespace in paths, checksum failures, and patches that do not apply
cleanly stop the build before compilation.

When the series changes, the next preparation replaces only the generated,
versioned source tree. Do not make unique edits in that managed tree; author
changes in a separate Git clone and export them back into this repository.

## Kernel configuration

The manifest names an upstream base configuration and an ordered list of config
profiles. The default `full` profile uses `configs/gemini.fragment`; add a
symbol there with the patch that requires it. The separate `handoff` profile
uses `configs/gemini-handoff.fragment` and is intentionally built-in-only and
probe-minimal for the first LK-to-Linux execution test. The `usbdiag` profile
applies `configs/gemini-usbdiag.fragment` after that baseline and adds the
gadget-only MTU3/T-PHY and IPv4 path without enabling storage, host-mode USB,
Type-C policy, or unrelated network devices. The diagnostic-only
`usbdiag-clkignore` profile then applies
`configs/gemini-clk-ignore-unused.fragment`; its sole request appends
`clk_ignore_unused` to the forced kernel `CONFIG_CMDLINE`. This broad profile is
not a normal boot configuration. Separately, the
`observability-fbcon-rotation` profile retains the exact observability inputs
and changes exactly two resolved
configuration lines: it enables `CONFIG_FRAMEBUFFER_CONSOLE_ROTATION=y` and
appends only `fbcon=rotate:3` to forced `CONFIG_CMDLINE`. It intentionally does
not change the font or add display, input, storage, or networking policy. Kernel
`merge_config.sh` reports redundant or overridden values, and `olddefconfig`
resolves new dependencies. The repository validator checks the final requested
value for each symbol, so a later profile fragment may intentionally override
an earlier profile baseline without hiding an unresolved Kconfig change.

The Gemini fragment also disables EFI, ACPI, virtualization/Xen, SCSI, and ATA
for this DT-only Android/LK handoff. Those host-oriented stacks are not part of
the device boot contract and keeping them out of the built-in image leaves room
under the MT6797 LK platform's fixed 50 MiB decompression buffer. This is a
Gemini packaging constraint, not an upstream arm64 default.

## Individual stages

```sh
./scripts/dev-vm kernel status
./scripts/dev-vm kernel check-latest
./scripts/dev-vm kernel prepare
./scripts/dev-vm kernel configure
./scripts/dev-vm kernel build
```

The manifest remains pinned until reviewed and changed in Git. `check-latest`
only compares it to kernel.org; it never changes build inputs automatically.
Select a non-default profile with `KERNEL_PROFILE=NAME`, or use the dedicated
handoff and USB-diagnostic build shortcuts:

```sh
./scripts/dev-vm build-handoff-kernel
./scripts/dev-vm build-usbdiag-kernel
```

Set `BUILD_MODULES=1` inside a guest shell when modules are needed. The
resulting package contains them below `modules/lib/modules/<release>/` and
records `modules_built=true` in `provenance/build.json`. Linux 7.1.3
builds `Image.gz` as an explicit arm64 boot target; no `CONFIG_KERNEL_GZIP`
symbol is required. The package retains the uncompressed arm64 `Image` for
inspection and generic loaders, plus `Image.gz` for the retained Planet LK
handoff. The Android 8 LK source selects
its 64-bit path from `bootopt`, scans the compressed kernel payload for an
appended DTB, and calls its gzip decompressor before entering the kernel; a raw
`Image` is therefore not a valid Gemini LK kernel payload.

Validate the newest package after a build (or pass an explicit guest artifact
directory):

```sh
./scripts/dev-vm validate-kernel
```

The validator checks the complete `SHA256SUMS` manifest, required
`Image`/`Image.gz`/DTB and provenance files, and the recorded source, patchset,
and configuration hashes.
It is an integrity check only; it does not imply that the kernel boots or that
any peripheral driver works on a device.

For the retained Planet LK handoff, build the non-flashing Android v0 candidate
only through the VM wrapper documented in [DEV_VM.md](DEV_VM.md):
`experiments/2026-07-16-lk-handoff-alignment/scripts/build-lk-handoff-candidate.sh`.
It requires an explicit package from the current `handoff` profile, creates a
byte-reproducible storage-inert initramfs, serializes mandatory-LK and optional
simplefb variants, and records parser and input-hash evidence. The wrapper does
not select a partition or write hardware; a successful parse is not a runtime
boot result.

Build the USB diagnostic Android v0 image only with
`experiments/2026-07-16-usb-gadget-diagnostic/scripts/build-usb-diagnostic-candidate.sh`.
It requires an explicit package from the current `usbdiag` profile and an
explicit new output directory. The wrapper rejects storage, host/dual-role USB,
Type-C, and unrelated probe families; applies only the validated USB status
overlay after the mandatory LK overlay; embeds a deterministic static-BusyBox
initramfs; and checks the exact LK/arm64 container contract. It has no device
or flashing interface. Enumeration, ping, and the TCP marker remain three
distinct hardware gates and must not be inferred from a successful build.

The visible handoff diagnostics are packaging-only derivatives of that exact
package. Candidate E is produced by
`experiments/2026-07-16-screen-marker-diagnostic/scripts/build-screen-marker-candidate.sh`.
Candidate F must be produced by
`experiments/2026-07-16-screen-clock-retention-diagnostic/scripts/build-clock-retention-candidate.sh`;
it reconstructs and hash-pins exact Candidate E, reuses its Image and initramfs
byte-for-byte, derives the infra-clock phandle from the pinned DTB, and permits
only one added simplefb `CLK_INFRA_DISP_PWM` reference. Build it twice into new
directories and require complete directory equality before exporting one. Both
wrappers remain non-flashing; the separate standing `boot2` synchronization
policy in `AGENTS.md` applies only after their manifests and experiment gates
pass.

Synchronization does not select `boot2` for the next reboot. Static analysis
of the exact captured LK maps its observed `boot2` and `boot3` partition
lookups to hardware-key tests (codes `0x11` and `0x08`) and found no direct
software reboot destination for either partition in the audited paths. The
live Gemian inventory likewise found no exposed matching boot-target control
and no enabled kexec path. Until a separately
designed, recoverable, one-shot bootloader selector exists, the owner must use
the silver button for each `boot2` test. Do not substitute kexec: it would also
bypass LK's required DT, memory, and reserved-memory fixups. See the
[exact-LK selection audit](../experiments/2026-07-12-boot-contract-recovery/results/lk-boot2-software-selection-audit-20260718.txt).

Candidate G must be produced by
`experiments/2026-07-16-fbcon-text-diagnostic/scripts/build-fbcon-text-candidate.sh`.
It reconstructs and hash-pins exact Candidate F, requires an identical
`Image.gz` plus DTB kernel segment, and changes only the initramfs: tracked
`/init` bytes replace the raw marker path while `screen-marker.raw`, `bin/dd`
and `bin/wc` are removed. Its validator rejects framebuffer-device, storage,
raw-memory and reset access. Build it twice into new directories, require
complete byte equality and export one exact directory. Candidate G deliberately
does not rotate fbcon because the exact tested kernel compiles rotation out;
its attended boot reproduced sideways output for 1–2 seconds before the screen
and apparent backlight went black.

Candidate H must be produced by
`experiments/2026-07-16-simplefb-mm-root-retention/scripts/build-mm-root-candidate.sh`.
It reconstructs and hash-pins exact Candidate G, keeps `Image.gz` and initramfs
byte-for-byte, resolves both providers from the pinned DTB, and permits only
`CLK_TOP_MUX_MM` to be appended to the existing simplefb clocks property. Build
it twice into new directories, require complete directory equality, and export
one exact directory. In Candidate H's attended series, two attempts visibly
progressed farther and the owner approximately recognized its initramfs-only
marker before the screen and backlight went off; later attempts did not
reproduce the progress. This strongly attributes those attempts to external
`/init`, but does not establish stable display retention.

Candidate I must be produced by
`experiments/2026-07-16-fbcon-refresh-timing-diagnostic/scripts/build-fbcon-refresh-candidate.sh`.
It reconstructs and hash-pins exact Candidate H, keeps `Image.gz` and its
appended DTB kernel segment byte-for-byte, and preserves the exact initramfs
archive tree except for tracked `/init`. That init emits one tty0 line per
second through `T+60`, then enters a silent static hold. Its validator permits
only the ramdisk-derived Android-v0 fields to change. Build it twice into new
directories, require complete directory equality, and export one exact
directory. The validated image is synchronized and fully read back from
logical `boot2`. The reported intended selection went directly to black and
showed no Candidate I marker, counter, or other console text. Because the exact
attempt count, backlight, final state, and recovery action were not recorded,
selection and `/init` execution remain unconfirmed and the active-refresh
versus static-hold hypothesis remains untested. Rotation requires a separate
configuration-only candidate after display retention is stable.

Candidate J must be built from the `usbdiag-clkignore` package with
`experiments/2026-07-17-clk-ignore-unused-diagnostic/scripts/build-clk-ignore-unused-candidate.sh`.
Pass the exact usbdiag baseline package and the new package explicitly. The
builder reconstructs exact Candidate I and requires byte-identical I DTB and
initramfs inputs plus an unchanged Android header command line; only the newly
compiled kernel payload and its payload-derived header fields may change. Do
not append the option only to the Android header: Candidate I has
`CONFIG_CMDLINE_FORCE=y`, so Linux replaces loader-provided bootargs and that
header-only delta is a runtime no-op. The validator explicitly rejects the
discarded no-op artifact.

J's raw boot-image SHA-256 is
`6d5bad08c2f93eba7fbd66ea5c54de2437f81e44832426a97d4d65d550c659f4`.
The final kernel package and an isolated clean rebuild produced byte-identical
resolved config, `Image`, `Image.gz`, `System.map`, all 119 DTBs, and the same
boot image. Only the generated `build.json` timestamp and therefore its package
checksum manifest differ. J was exported and synchronized to logical `boot2`.
At `20260717T111314Z`, the live label resolved to `/dev/mmcblk0p30`, not an
assumed partition number. The exact 16 MiB target was writable, unmounted, and
had no holders; active root was `/dev/mmcblk0p29`, AC was online, and the
battery reported 100%, Full, and Good. The old exact-I partition was backed up,
the write was
synced and block-flushed, and the complete target plus local readback match SHA-256
`465e4c747138e12191d38fd6b4cde68cd0b9a19f918030dea05c9b8dbdd4d3fc`.
No reboot or shutdown was part of that operation. On the first later
owner-attended intended `boot2` selection, the last visible suffix before black
was reported as `4/60`. Since only the tracked shared I/J `/init` emits that counter,
the verified target/readback and intended selection strongly support Linux
entry, fbcon/tty0 output, and shared `/init` execution through tick 04 for this
attempt. The full line and marker were not exactly transcribed. A later
two-bullet report is provisionally interpreted as two additional intended
J/`boot2` selections because its outcomes are mutually exclusive, with owner
confirmation pending. One reached "iteration 4" before black, compatible with
and corroborating tick 04 without an exact marker transcription. One went
directly black with no console and cannot establish selected slot, kernel entry,
or `/init`. Provisionally, two of three intended selections had
tick-04-compatible visible output and one of three was no-console and
unattributable. Stable visibility and causality are not established. See the
[write/readback record](../experiments/2026-07-17-clk-ignore-unused-diagnostic/results/boot2-write-candidate-j-20260717.txt)
and the [first runtime](../experiments/2026-07-17-clk-ignore-unused-diagnostic/results/runtime-candidate-j-attempt-1-20260717.txt)
and [repeat](../experiments/2026-07-17-clk-ignore-unused-diagnostic/results/runtime-candidate-j-repeat-report-20260717.txt)
records.
At runtime, `clk_ignore_unused` only prevents the Common Clock Framework's
automatic unused-clock cleanup: it does not enable clocks that are already off,
prevent explicit driver disables, or retain regulators or power domains. Treat
J as a bounded attended discriminator, never as a default or a complete
display-power solution. Stop further J repetition. Candidate K was a
reproducible exact-J initramfs-only derivative, but the strategy review
cancelled it without a runtime selection: it has no kernel, DT, or configuration
delta and cannot supply a decision-changing observation. Its write/readback
record remains historical evidence; do not boot it.

Candidate L is the current observability workflow. It multiplexes three
source-backed changes with distinct intended signals into one expensive boot;
this is an observability acceptance gate, not a single-variable causal test.
UART0's board pins use GPIO97 RX and GPIO98 TX;
`ramoops@44410000` maps the Linux 7.1.3 console exactly onto the primary
`console-ramoops` zone confirmed by the pinned Gemian source and exact active
binary; MT6797 watchdog start and inherited-running paths normalize
auto-restart (bypass-power-key) mode and select dual-stage only when the
requested bark IRQ establishes a pretimeout, while the immediate
software-restart path sets
auto-restart before issuing SWRST. The
observability configuration uses a `0x20000` mainline pmsg allocation only for
address alignment to preserve that primary-console address; the pmsg frontend
is compiled out and is not a cross-version recovery channel. Its initramfs writes durable kernel-console markers, opens the watchdog, sends one
ownership-handoff ping to cancel the inherited kernel keepalive, and then holds
the fd without further pings. The subsequent known-good Gemian boot can collect
surviving pstore evidence. This must not be represented as runtime support
before the candidate is booted and its evidence recovered. Its distinct
fresh-source rebuild, exact candidate reproduction, export, and full logical
`boot2` write/readback are complete; those operations establish artifact and
partition identity only. See the
[Candidate L experiment](../experiments/2026-07-17-uart-pstore-observability/README.md),
[reproduction result](../experiments/2026-07-17-uart-pstore-observability/results/final-build-reproduction-20260717.txt),
and [write/readback result](../experiments/2026-07-17-uart-pstore-observability/results/boot2-write-candidate-l-20260717.txt).
Attempt 1 showed the LK splash and then black; manual recovery and delayed
collection found no pstore marker. Attempt 2 showed console output through the
exact suffix `remaining 5s`, unique to Candidate L's tracked
`watchdog0=waiting` loop. Combined with the verified target, this strongly
supports kernel, loader-simplefb/fbcon, devtmpfs, and `/init` entry and
establishes that `/dev/watchdog0` was absent at that check. Connected serial
was silent. The screen switched off, automatic return was not observed, manual
power recovery was required, and immediate pstore was empty. Do not rebuild or
select unchanged L. The source audit found that the falling-edge SPI is
correctly translated by the inherited MediaTek SYSIRQ hierarchy, so changing
its polarity would be an unsupported guess. Candidate M instead removes only
the optional bark IRQ from the final diagnostic DTB, keeps the exact L kernel
and config, and emits the platform/driver/class/probe state before attempting
the basic watchdog reset. Its first runtime passed: retained
`console-ramoops` proves successful no-IRQ `mtk-wdt` registration,
`/dev/watchdog0`, a 31-second timeout, one handoff ping, and progress through
30 seconds before the automatic Gemian return. Gemian's boot reason and PMIC
flags independently report a watchdog reset. Retain that basic watchdog and
pstore foundation; do not repeat unchanged M. Candidate N implements the next
gate: it retains M's exact kernel/configuration/DTB, changes only initramfs
`/init`, arms the watchdog before requesting only CPU1 online, and records the
pre/post CPU masks and PSCI lines. Two builds are byte-identical and its exact
padded image is synchronized, flushed, and fully read back from logical
`boot2`. Its one runtime cycle passed: the standard hotplug request returned,
CPU1 booted as MPIDR `0x1` / Cortex-A53, its accounting advanced, and it stayed
online through the 25-second marker before the watchdog returned the unit to
Gemian automatically. This proves only the first secondary Cortex-A53 in one
run. Close unchanged N. Candidate O then requested CPU1 through CPU7
sequentially with a durable begin/return/mask and execution checkpoint after
every request, a first-failure stop, and both Cortex-A72s left for a separate
gate. This retained the proven watchdog recovery path while making the last
checkpoint the failure boundary. See
[attempt 1](../experiments/2026-07-17-uart-pstore-observability/results/runtime-candidate-l-attempt-1-20260718.txt)
and [attempt 2](../experiments/2026-07-17-uart-pstore-observability/results/runtime-candidate-l-attempt-2-20260718.txt),
the [registration audit](../experiments/2026-07-17-uart-pstore-observability/results/watchdog-registration-audit-20260718.txt),
the [Candidate M runtime record](../experiments/2026-07-18-watchdog-registration-diagnostic/results/runtime-candidate-m-attempt-1-20260718.txt),
the [Candidate N build record](../experiments/2026-07-18-cpu1-online-diagnostic/results/final-build-reproduction-20260718.txt),
its [logical-`boot2` write/readback](../experiments/2026-07-18-cpu1-online-diagnostic/results/boot2-write-candidate-n-20260718.txt),
and its [runtime record](../experiments/2026-07-18-cpu1-online-diagnostic/results/runtime-candidate-n-attempt-1-20260718.txt).

Candidate O uses a narrower deterministic path than a full kernel rebuild. Its
builder accepts only the pinned Candidate N artifact, extracts and revalidates
the exact N `Image.gz`, embedded configuration, and DTB CPU/PSCI/watchdog
contract, replaces only initramfs `/init`, and reconstructs the Android-v0
image with the unchanged LK addresses, name, and command line. Its two clean
builds were recursively byte-identical. Its one retained runtime cycle passed:
all live logical CPU1–9 mappings matched their expected DT nodes, each standard
CPU1–7 hotplug request returned success, every target emitted a boot line and
advancing accounting checkpoint, and the final online mask was `0-7` while the
Cortex-A72 CPU8/9 pair remained offline and untouched. The final success marker
and 5- and 10-second wait markers survived the automatic watchdog recovery.
This is one hotplug run only; it does not establish repeatability, boot-time
SMP, stress, coherency, DVFS, idle states, thermal behavior, or either
Cortex-A72 online path. Close unchanged O. The reproducible build remains:

```sh
DEV_VM_NAME=gemini-pda-build-recovery-20260717 ./scripts/dev-vm run \
  /mnt/gemini-pda-mainline/experiments/2026-07-18-cortex-a53-sweep-diagnostic/scripts/build-cortex-a53-sweep-candidate.sh \
  --baseline /home/julien.guest/artifacts/boot-candidates/candidate-N-cpu1-online-7cdb4b99
```

See the
[Candidate O runtime result](../experiments/2026-07-18-cortex-a53-sweep-diagnostic/results/runtime-candidate-o-attempt-1-20260718.txt).

Candidate P is the closed rotation gate over exact hardware-tested O. Its
resolved configuration differs by exactly two lines:
`# CONFIG_FRAMEBUFFER_CONSOLE_ROTATION is not set` becomes
`CONFIG_FRAMEBUFFER_CONSOLE_ROTATION=y`, and the forced `CONFIG_CMDLINE` gains
only the final token `fbcon=rotate:3`. The current 8×16 font and every other
resolved configuration, source, patch, DTB, initramfs, LK-container, and
watchdog-policy input remain exact. Its reproducible build command is:

```sh
KERNEL_PROFILE=observability-fbcon-rotation ./scripts/dev-vm build-kernel
```

The normal package validators, P-specific package/Android-v0 delta validators,
negative mutation suite, and two independent VM builds pass. The exported
artifact is
`artifacts/vm-export/boot-candidates/candidate-P-fbcon-rotation-170a640`;
its raw boot-image SHA-256 is
`d192dac9e4516eac9319da2a885abaf3203da6c357c574e7f1f6deef2208d341`.
It was written to live-resolved logical `boot2`, synchronized, block-flushed,
and fully read back. The exact padded target and full readback SHA-256 is
`cea00d591e74a29d74200f4d292a92aaca2f890bd965af37a7673ab906f4afbc`.
The one attributable runtime selection passed. The owner observed readable
console text in normal-landscape orientation, the complete inherited O sweep,
and an unassisted return to Gemian. The post-return `console-ramoops` retains
the exact `GEMINI_A53_SWEEP_20260718_O` marker, every CPU1–7 checkpoint, final
`online=0-7` success with CPU8/9 offline, and both watchdog waits. Because the
collector started after return, it did not span the tested boot-ID transition
or independently capture the reset reason. Close unchanged P: this is one
loader-retained simplefb/fbcon rotation result, not repeatability or native
DRM/panel/backlight support. See the
[Candidate P experiment](../experiments/2026-07-18-fbcon-rotation-diagnostic/README.md),
[runtime result](../experiments/2026-07-18-fbcon-rotation-diagnostic/results/runtime-candidate-p-attempt-1-20260718.txt),
[build reproduction](../experiments/2026-07-18-fbcon-rotation-diagnostic/results/final-build-reproduction-20260718.txt),
and [write/readback](../experiments/2026-07-18-fbcon-rotation-diagnostic/results/boot2-write-candidate-p-20260718.txt).

Candidate Q is the exact next implementation and runtime gate. By owner
decision it combines keyboard input and a supervised local shell, but keeps
their implementation and evidence layers separable: a bounded raw-event probe
must report before PID 1 exposes the shell. Starting only from exact P, create
a dedicated profile that adds `consoleblank=0` and the built-in I2C5/AW9523,
input/evdev, and matrix-keypad dependency closure. Add one reviewable DT patch
that corrects the disabled AW9523 candidate's combined-controller
`gpio-ranges` form, then enable only I2C5, its AW9523 child, and the matrix
keyboard in Q's final package. Preserve the source-backed GPIO58 reset,
GPIO87/EINT10 interrupt, active-high reset semantics required by the upstream
driver, low-level IRQ, scan polarity, and active-ELF keymap. Do not guess
debounce, scan timing, wake, or unsupported MT6797 pin-bias properties.

Q's external initramfs carries `GEMINI_KEYBOARD_SHELL_20260718_Q`, performs a
no-grab dynamic input-event probe, then supervises a BusyBox shell on
`/dev/tty1` with `TERM=linux`, sane tty state, and respawn. Use the standard
kernel console keymap; Gemian XKB symbols are userspace evidence, not part of
this candidate. Q must not open or ping `/dev/watchdog*` and has no deliberate
normal-path automatic reboot. Preserve and re-audit the pinned kernel's
`WATCHDOG_HANDLE_BOOT_ENABLED=y` keepalive behavior so an inherited active
hardware timer does not expire merely because userspace abstains. Keep
`panic=0`; a catastrophic kernel stall may still trigger hardware recovery.
Q runs only CPU0, performs no CPU-online writes, and excludes eMMC/MMC, storage
mounts, raw memory/I2C access, network configuration, and native display work.
Success requires a visible raw-event result, typed shell input/output, shell
respawn, and 15 minutes of idle console stability. Recovery afterward is
owner-selected and non-gating; an optional typed `reboot -f` may leave this
unit key-gated and requiring a power press. The exact file plan, validators,
mutation tests, runtime procedure, decision table, and baseline hashes are
recorded in the
[Candidate Q handoff](../experiments/2026-07-18-keyboard-shell-diagnostic/README.md).

Do not turn this quality-of-life sequence into one permanent catch-all kernel
profile. Q deliberately combines a hardware input gate and an initramfs shell
for one device cycle, but their changes and observations remain independently
reviewable. Candidate S is still the separate real PWRAP/MT6351/MMC profile;
Candidate T USB networking remains a separate initramfs/serviceability gate.
Pin every selected profile in `kernel/manifest.json`, validate its resolved
config, and keep its experiment oracle and artifact builder beside the
write-up. Do not promote a layer to the reusable board fragment until its
named hardware gate passes.

Before treating the series as submission-ready, run the pinned tree's review
checker over every patch:

```sh
./scripts/dev-vm run experiments/2026-07-14-patch-quality-audit/scripts/audit-checkpatch.sh
```

This is a review gate, not a build gate. The current 77-patch audit found
ten missing sign-offs, 64 warnings, and 18 check-only diagnostics, including
new binding/driver review items in patch 0075; see the [recorded result](../experiments/2026-07-14-patch-quality-audit/results/checkpatch-current-77-20260714.txt).
The [review action plan](../experiments/2026-07-14-patch-quality-audit/results/review-action-plan-current-74-20260714.md)
separates provenance blockers from cleanup work. Do not fabricate sign-offs:
the actual contributor must provide them before submission. The companion
[provenance audit](../experiments/2026-07-14-patch-quality-audit/results/patch-provenance-current-77-20260714.txt)
also rejects placeholder authors and synthetic all-zero patch object IDs.

## Moving artifacts to the flashing machine

After reviewing the guest artifacts:

```sh
./scripts/dev-vm export-artifacts
./scripts/dev-vm export-artifact boot-candidates/EXACT-DIRECTORY
```

The first command creates a timestamped, Git-ignored copy of every guest
artifact. The second copies only one exact path to host
`artifacts/vm-export/` and refuses to overwrite it. Verify `SHA256SUMS` and the
provenance metadata before transferring selected files to the separate Windows
flashing machine. The normal workflow must never package or write the
preloader, NVRAM, GPT, or a whole-device image.
