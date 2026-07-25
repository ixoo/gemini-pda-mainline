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
5. applies every patch named by the selected profile's effective series, in
   order (`patches/series` is the canonical default);
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

The canonical `patches/series` would contain:

```text
v7.1.3/0001-arm64-dts-mediatek-add-gemini-pda.patch
v7.1.3/0002-clk-mediatek-add-required-clock.patch
```

Blank lines and lines beginning with `#` are ignored. Missing files, unsafe
paths, whitespace in paths, checksum failures, and patches that do not apply
cleanly stop the build before compilation.

`patches/series` remains the canonical superset and relative order. A named,
manifest-pinned experiment profile may select a canonical-order subsequence
with its own `patch_series` member. This isolates an already-listed change
without rewriting the global integration stack; it is not a second untracked
patch history. The effective series and every listed patch must be regular,
non-symlink files below `patches/`, with no absolute, whitespace, empty, `.` or
`..` path components. An override uses a profile-specific managed source
directory so it cannot replace the default series' prepared tree. The package
records the effective series path, content, and exact patch inventory, and the
validator recomputes the path-sensitive patchset identity.

When the series changes, the next preparation replaces only the generated,
versioned source tree. Do not make unique edits in that managed tree; author
changes in a separate Git clone and export them back into this repository.
The canonical working series contains 101 ordered entries through patch 0102,
with unsafe active-A72 draft 0093 and legacy-DA9214 draft 0096 excluded. The diagnostic
`observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-reject-gate`
profile selects an 89-entry subsequence: exact Candidate AD patches 0001–0087
followed only by corrected 0092. It deliberately omits 0088–0091 and the
unlisted, unsafe active-power draft 0093. Patch 0093 remains unselected pending
a replacement derived from a read-only Gemian state capture and the reviewed
firmware/power ownership contract.

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
not change the font or add display, input, storage, or networking policy. The
later `observability-fbcon-rotation-keyboard-wrrd` diagnostic profile retains
the Candidate V keyboard configuration and appends
`configs/gemini-keyboard-wrrd.fragment`. That fragment compiles
`CONFIG_FONT_TER16x32=y`, selects `fbcon=font:TER16x32`, and moves the fixed
virtual kernel console to tty2 so an independently respawned foreground shell
can own tty1. Its keyboard-causal change is not configuration policy: patch
0086 adds exactly one direct `mediatek,mt6797-i2c` match to existing
`mt8173_compat`. W's first runtime showed that tty2 did not isolate visible
printk from the foreground tty1 shell. The subsequent
`observability-fbcon-rotation-keyboard-wrrd-manual-reboot` profile appends
`configs/gemini-keyboard-manual-reboot.fragment` and removes only that virtual
console token, retaining the fixed serial console, rotation, `TER16x32`, and
all W keyboard policy. Two clean Candidate X builds reproduced the complete
non-timestamp package content; X later booted and worked by owner report, while
its typed generic reboot appeared to hang. Patch 0087 is the separate Candidate
AB restart experiment: it selects watchdog restart priority 255 only for
MT6797, ahead of ARM64 PSCI priority 129, and retains priority 128 for every
other supported MediaTek variant. AB's reproducible package and container keep
this resolved configuration exact. One attended run retained exact AB
attribution and the console-map gate, stayed idle for 45 seconds without an
automatic reset or countdown, and reset immediately by owner observation after
typed bare `reboot`; this is one named-unit hardware pass. The
`observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8` then applies
`configs/gemini-smp8.fragment` and changes only `maxcpus=1` to the eight
hardware-proven Cortex-A53 CPUs. Candidate AD passed that boundary with CPUs
0--7 online and CPU8/9 offline. The isolated
`observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-observer`
profile adds `configs/gemini-a72-observer.fragment`: built-in DA9214 and
read-only A72 resource observation plus `regulator_ignore_unused`. Its
CPU8/9-specific enable method rejects before PSCI `CPU_ON`; observer resource
availability is not A72 support or permission to online either CPU.

The separate
`observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-reject-gate`
profile keeps Candidate AD's exact resolved configuration and selects only the
corrected, fail-closed 0092 kernel gate after the AD prefix. CPU0–7 retain
generic PSCI; CPU8/9 advertise the custom method, which returns `-EAGAIN`
before `PSCI_CPU_ON`, reports CPU disable unavailable, and exposes no
disable/die/kill callback. `maxcpus=8` means this profile requests neither A72.
This is an isolation experiment, not A72 enablement or runtime support. Exact
Candidate AI passed its guarded install, readable-console, USB-attributed
eight-A53 runtime, native-reboot/changed-Gemian-return, and post-cycle
full-`boot2` integrity gates; CPU8/9 remained offline and unrequested.

The follow-up
`observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-reject-gate-cpu8-request`
profile appends only `configs/gemini-a72-reject-cpu8-request.fragment` and
changes the resolved command line from `maxcpus=8` to `maxcpus=9`. With the
serialized hotplug path, Candidate AJ therefore requests logical CPU8 once;
corrected patch 0092 must return `-EAGAIN` before `PSCI_CPU_ON`, while CPU9 is
not requested and CPUs 0--7 remain online. Two independent packages and two
independent Android-v0 assemblies reproduce. The exact raw image SHA-256 is
`a3c649b5ca7a9ac07e290ca9a8838f0a3be33ab9e39554c4bafe50c98d18e2a8`,
and two independent 16 MiB zero-padding constructions agree on SHA-256
`8e322ed2a8fc82a4746ec118c2b0adad6003d03f0670284b9ab281c92120b257`.
Guarded installation and matching full readback passed. Attempt 1 was rejected
as a target-identity mismatch. Attempt 2's exact USB/runtime oracle passed with
advancing CPU0–7, exactly one CPU8 pre-PSCI gate rejection, exactly one
`CPU8: failed to boot: -11`, and no CPU9 attempt. Native reboot returned to
changed-boot-ID Gemian, and one full read-only post-return `boot2` hash still
matched AJ. The retained pstore is deliberately an unpaired post-return
snapshot, not paired-cycle evidence. AJ remains `PARTIAL` only because explicit
confirmation of a readable local console during attempt 2 is pending. AJ is a
rejection-path negative control, not Cortex-A72 support. A separate
safety-predecessor audit does not upgrade that console result or call the
snapshot paired, but accepts the exact runtime/native-reboot/changed-return/
full-readback chain as sufficient to build and guardedly install the one-token,
fail-closed CPU9 control over exact AJ.

The isolated
`observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-`
`a72-observer-initcall-blacklist-dvfsp-handoff-owner` profile selects the
Candidate AO handoff owner through patches 0094, 0095, 0097, and 0098 while
excluding active-A72 draft 0093 and legacy-DA9214 draft 0096. Its final DT
keeps I2C6 disabled/childless and omits DA9214 and A72-power consumers. Two
clean packages and two complete Android-v0 artifacts reproduced; the exact
full-readback-verified `boot2` image passed one named-unit runtime. One balanced
CCF reference preserved the stopped PCM signature, closed I2C_APPM after
release, and remained closed at 45 seconds with zero faults. This profile is a
validated one-way clock-accounting boundary only. It does not authorize I2C6,
DA9214, A72, or suspend/resume; add those as separately reviewed profiles and
experiments.

The
`observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-`
`a72-observer-initcall-blacklist-dvfsp-handoff-owner-i2c6-consumer`
profile selects exact AO plus patches 0099–0102. Candidate AP built twice,
reproduced two complete containers, and was fully read back from logical
`boot2` as exact padded SHA-256
`602f06be094c6091ceff9b501bf5328bc2f79d26be5c26f98479905aa3caa5f9`;
its separate PM-audit profile compiled and linked but was never
assembled, installed, or booted. AP's exact live FDT passed, yet its one
hardware run returned structured `FAIL`: the guarded clock hold regated
I2C_APPM but AP_DMA stayed ungated through all 32 cleanup samples. The provider
faulted closed and I2C6 returned `-EIO` before binding an adapter or issuing a
transfer. Native reboot returned to changed-ID Gemian and the full read-only
post-return `boot2` hash remained exact. Do not repeat the same artifact. A
future profile must first add a decision-changing observation of AP_DMA's
existing owner and a baseline-preserving cleanup oracle; suspend/resume,
DA9214, and A72 remain out of scope.

Any future active A72 profile must replace, not select or edit in place, draft
patch 0093. The reviewed contract assigns DA9214/PWRAP/external-isolation
preparation to Linux and initial B PLL, MP2/core MTCMOS/reset, internal bus
protection, and CCI admission to secure firmware. Require independent SRAM-LDO
readback, because the captured firmware service's zero return is not completion
evidence. There is no proven inverse/off path: after external isolation is
cleared, retain power on failure, fault without retry, and expose no hotplug-off
callback. The prerequisite non-mutating Gemian observer is still being
developed; no synchronized live register-state capture has been obtained. See
the [A72 firmware/power contract](../experiments/2026-07-22-a72-firmware-power-contract/README.md).

Kernel
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

Build the gate-only isolation profile explicitly:

```sh
KERNEL_PROFILE=observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-reject-gate \
  ./scripts/dev-vm build-kernel
```

Build the separate CPU8 rejection-request profile explicitly:

```sh
KERNEL_PROFILE=observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-reject-gate-cpu8-request \
  ./scripts/dev-vm build-kernel
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
`Image`/`Image.gz`/DTB and provenance files, the manifest-selected effective
series and exact patch inventory, and the recorded source, patchset, profile,
configuration-input, and resolved-configuration identities.
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

Candidate L was a historical observability workflow. It multiplexed three
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

Candidate Q completed its reproducible build, validation, export, and matching
full logical-`boot2` readback. Its later intended selection did not provide a
working text console. No exact Q marker, AW9523 binding line, input device,
event, shell prompt, or retained pstore record was observed; kernel entry,
`/init`, keyboard, and shell behavior therefore remain unestablished. Static
review found a concrete DT error: Q supplied `<87 IRQ_TYPE_LEVEL_LOW>` to the
MT6797 parent interrupt domain even though GPIO87's recovered mapping is
EINT10. That error is not runtime proof of the failure's cause. Do not repeat
unchanged Q. Preserve its build and write records as historical artifact
identity evidence and its separate runtime record as the narrower hardware
result. See the
[Candidate Q experiment](../experiments/2026-07-18-keyboard-shell-diagnostic/README.md)
plus its [build reproduction](../experiments/2026-07-18-keyboard-shell-diagnostic/results/final-build-reproduction-20260719.txt),
[write/readback](../experiments/2026-07-18-keyboard-shell-diagnostic/results/boot2-write-candidate-q-20260719.txt),
and [runtime result](../experiments/2026-07-18-keyboard-shell-diagnostic/results/runtime-candidate-q-attempt-1-20260719.txt).

Candidate U used the next available identifier because the never-built R is
retired and S/T remain reserved for eMMC and USB networking. U was independently
built twice with matching validated outputs, then installed to live-resolved
logical `boot2` with a matching full-partition readback. Its first intended
selection produced a black screen and dark console with no visible marker or
automatic reboot. The device later returned to Gemian with a changed boot ID,
but authenticated post-return pstore was empty. Kernel, `/init`, console,
AW9523, keyboard, and shell entry remain unestablished. Post-run artifact audit
found that U's final DTB was built from the corrected kernel package DTB rather
than exact Candidate P's final DTB. It therefore omitted P's
`/chosen/framebuffer@7dfb0000`, framebuffer clocks, no-IRQ watchdog state, and
other LK-aligned fixups. This explains why U did not carry P's configured
loader-console path, but does not prove U entered Linux or that the omission
caused the black screen. Keep Linux 7.1.3's upstream
`pinctrl-aw9523` implementation and its `GPIO_ACTIVE_HIGH` reset description:
with that driver's logical reset sequence, it produces the required physical
low pulse and high release. Do not copy bsg100's separate AW9523B driver or its
driver-specific reset polarity.

Series patches 0083 and 0084 supply the decision-changing U delta: a generic,
schema-described binding and polling mode for Linux 7.1.3
`gpio-matrix-keypad`, informed by
bsg100's hardware-tested
[physical-typing commit](https://github.com/bsg100/gemini-linux/commit/6bd4d572670698f80ca08ad083657621b62cc8f3)
and [keyboard/USB coexistence commit](https://github.com/bsg100/gemini-linux/commit/aff681d3c727137c4016376e12055d380867f5c3).
Patch 0085 separately corrects the reusable disabled board description from
raw EINT87 to EINT10 without enabling it. U's validated candidate-only active
DTB omits the AW9523 parent interrupt and all nested interrupt-controller
properties; it retains the GPIO87/EINT10 input pinmux with no active consumer.
The upstream AW9523 driver explicitly supports operation without a parent IRQ.
The polling capability must be a reviewable generic driver plus binding change
adapted to the current 7.1.3
descriptor-based implementation, not a verbatim copy of the reference's older
6.6 platform-data patch. U's validated DT policy pins I2C5 at 400 kHz,
`poll-interval = <20>` and `col-scan-delay-us = <2>` without the reference
DT's runtime-inert debounce property, and retains `drive-inactive-cols`. Build
validation is complete, but the non-diagnostic first boot supplied no
polling-path evidence.

U's validated initramfs construction reverses Q's serviceability dependency: it
starts and supervises the local shell independently of the bounded no-grab event
capture, so a present but nonfunctional keyboard cannot delay shell creation
for the entire capture window. It emits to the requested tty sinks and retains
`consoleblank=0`, CPU0-only and storage/network-inert policy, kernel watchdog
keepalive, `panic=0`, and no deliberate normal-path reset; the installed DTB
nevertheless lacked P's simplefb node. The successful build and schema checks
do not prove that U boots or that the keyboard works. Pin
every selected profile in
`kernel/manifest.json`, keep U's oracle and builder beside its experiment, and
do not promote keyboard data to the reusable board defaults before named-device
events and typed shell input are observed.

See the [Candidate U build, install, and failed runtime handoff](../experiments/2026-07-19-keyboard-polling-diagnostic/README.md),
[build reproduction](../experiments/2026-07-19-keyboard-polling-diagnostic/results/final-build-reproduction-20260719.txt),
and [write/readback](../experiments/2026-07-19-keyboard-polling-diagnostic/results/boot2-write-candidate-u-20260719.txt),
plus its [runtime result](../experiments/2026-07-19-keyboard-polling-diagnostic/results/runtime-candidate-u-attempt-1-20260719.txt).
Do not repeat unchanged U; a later device boot needs a durable independent
observation path.

Candidate V is that distinct successor. Build it only with
`experiments/2026-07-19-keyboard-watchdog-diagnostic/scripts/build-keyboard-watchdog-candidate.sh`.
The builder pins the corrected 86-patch polling-profile package and exact
Candidate P artifact, uses P's final DTB as the immutable base, treats the
package DTB only as a keyboard-resource oracle, and permits no caller-supplied
hash overrides. Its parsed whole-FDT validator allows only the documented
I2C5/AW9523/matrix polling transform and requires P's simplefb, no-IRQ
watchdog, ramoops, CPU, ATF, SCP, and USB fixups to remain exact. V's initramfs
starts the shell, event probe, and exact-device watchdog owner independently;
the expected no-IRQ timeout supplies bounded recovery and `/dev/kmsg` markers
feed P's durable `console-ramoops` zone.

Two fresh kernel builds reproduced the selected non-timestamp package content
and two complete V builds were recursively identical. The package validator,
focused schemas, candidate validators, and all 24 negative mutation cases
passed. Strict Checkpatch was clean for patches 0083--0085; patch 0082 has one
commit-message long-line warning only. The raw 6,864,896-byte candidate is
SHA-256
`9ef0ee8dc1eb49752f9cf8f60b247b9b85e4fd2a9f090473f1d91848114087b0`.

On 2026-07-19 the live GPT resolved logical `boot2` as `/dev/mmcblk0p30` while
root remained separate. The complete pre-write U backup matched SHA-256
`7c57176f3fb5e8e7c9619f038cf09517ca85ee0323ff48ff8c382b60b2794c6e`.
After guarded synchronization, flush, and full readback, the exact padded
target, remote checksum, and local readback matched SHA-256
`57d362a86fae38c0ec2cec909ef6ae8d8ad124b87abb2ee58d179184c1f19168`.
Root identity, boot ID, and power state were unchanged; no reboot or shutdown
was part of the operation. The owner later selected V from `boot2`; the console
was visible and the device returned automatically. Retained
`console-ramoops` proves the exact V marker, kernel/initramfs entry,
`tty1_shell=ready`, exact `mtk-wdt` association, open and one handoff ping with
timeout 31, and waits through 30 seconds. No 35-second or expiry-failure marker
survived. Gemian reported `boot_reason=4`,
`androidboot.bootreason=wdt_by_pass_pwk`, and `powerup_reason=reboot`, making
this an attributable watchdog recovery.

Interpret `tty1_shell=ready` narrowly: local-shell emitted it before its shell
`exec`, so it proves neither `ash` execution nor a visible, interactive prompt.
The owner had no usable shell or keyboard-test opportunity. All probe/watchdog
markers also write tty1 and can bury the prompt, while V's matrix keymap lacks
`KEY_SLASH` and `KEY_MINUS`, making `/bin/v-pass` normally untypeable from V's
own keyboard. AW9523 probe at I2C adapter 0 address `0x5b` repeatedly failed
`-110`/`ETIMEDOUT`, including the reset retry; AW9523 and the matrix remained
unbound and no event node appeared. Stop unchanged V at this provider boundary
before matrix polling/input. The exact working 3.18 binary uses unconditional
WRRD plus auxiliary RX-length offset `0x6c`, whereas V falls through to
`mt6577_compat` and suppresses WRRD. Latest bsg100 fixed the same combined-read
failure in hardware with a direct `mediatek,mt6797-i2c` match using
`mt8173_compat`. Retain V's AW9523 reset/cache/matrix state and use that direct
controller-data match as the next single causal change; tty1 and `TER16x32`
edits remain observation-path changes. See the
[Candidate V experiment](../experiments/2026-07-19-keyboard-watchdog-diagnostic/README.md),
[build reproduction](../experiments/2026-07-19-keyboard-watchdog-diagnostic/results/final-build-reproduction-20260719.txt),
[guarded write/readback](../experiments/2026-07-19-keyboard-watchdog-diagnostic/results/boot2-write-candidate-v-20260719.txt),
[runtime evidence](../experiments/2026-07-19-keyboard-watchdog-diagnostic/results/runtime-candidate-v-attempt-1-20260719.txt),
and [working 3.18 binary/controller audit](../experiments/2026-07-19-keyboard-watchdog-diagnostic/results/working-3.18-aw9523-i2c-binary-audit-20260719.txt).

Candidate W is the validated, installed successor to V. Build its package with the
`observability-fbcon-rotation-keyboard-wrrd` profile and assemble it only with
`experiments/2026-07-19-keyboard-wrrd-diagnostic/scripts/build-keyboard-wrrd-candidate.sh`.
The builder requires the exact V artifact and copies V's final DTB byte for
byte, retaining its loader simplefb, AW9523/reset/cache/matrix description,
no-IRQ watchdog, and ramoops. Its deterministic initramfs requests kernel output
on tty2, respawns the local shell on foreground tty1 without background marker
fanout, and uses a letters-only `pass` token. The larger built-in
`TER16x32` font is an observation delta, not part of the I2C hypothesis.

The causal patch is the one-line direct match
`{ .compatible = "mediatek,mt6797-i2c", .data = &mt8173_compat },`. This
matches the exact working 3.18 WRRD plus auxiliary receive-length contract and
the latest checked bsg100 `main` revision
[`60f5f4ac777a0aeccc89b5d3a4f8cd1f1ebe57b3`](https://github.com/bsg100/gemini-linux/commit/60f5f4ac777a0aeccc89b5d3a4f8cd1f1ebe57b3).
Two clean kernel packages match after excluding only `SHA256SUMS` and
`provenance/build.json`'s `generated_utc`; the normalized build-JSON SHA-256 is
`d2e4c1367d8394340efa4d1f67c2404c13c1f323b9490dacc59dd3be2512847a`.
Two final W assemblies match recursively, their complete `SHA256SUMS` manifest
is SHA-256
`257b17585c171e29ae3510fdab7602aa59e4da570aa906abb8b9e5b7e8da5851`,
and the mutation suite passes 24/24. The W initramfs SHA-256 is
`3793bec7a63074b237d041bcd42e6edfccc80f0a3d7b19869abf99ee7874dac6`;
the raw 6,866,944-byte image SHA-256 is
`34c41fad1e86de05b6a1f64f7e5d9229bd26ea88d982b0a57f2b9573aeb782d4`.
The exported `rebuild4` artifact was then installed by the separate guarded
helper only to live-resolved logical `boot2`; the operation did not reboot or
select the device. Its padded image, remote post-flush checksum, and full local
readback match SHA-256
`0ff3220096aa53f792116b3899e356bc2516816c9c330309c3d81e9fe1446608`.
W attempt 1 then passed the provider and bounded-input gates once. Retained
`console-ramoops` proves that `0-005b` probed successfully and bound
`aw9523-pinctrl`; `keyboard-matrix` then bound `matrix-keypad`, registered exact
`/dev/input/event0`, and emitted press/release records for H, E, L, P, and
Enter. The owner observed the shell and working keyboard and approved the
larger font. The same run failed serviceability: kernel logs remained visibly
mixed with tty1, and the deliberate watchdog open/one-ping path returned the
unit automatically before useful interactive work. Gemian reported
`wdt_by_pass_pwk`. No `pass` marker or durable command-execution result exists,
and all-key coverage and repeatability remain untested. See the
[Candidate W experiment](../experiments/2026-07-19-keyboard-wrrd-diagnostic/README.md),
[build reproduction](../experiments/2026-07-19-keyboard-wrrd-diagnostic/results/final-build-reproduction-20260719.txt),
[mutation result](../experiments/2026-07-19-keyboard-wrrd-diagnostic/results/validator-mutations-20260719.txt),
[guarded write/readback](../experiments/2026-07-19-keyboard-wrrd-diagnostic/results/boot2-write-candidate-w-20260719.txt),
and [runtime result](../experiments/2026-07-19-keyboard-wrrd-diagnostic/results/runtime-candidate-w-attempt-1-20260719.txt).

Candidate X was the validated and installed serviceability artifact. Its exact
hypothesis retains W's keyboard kernel and byte-exact final DTB,
deletes only `console=tty2` from forced `CONFIG_CMDLINE`, keeps serial and
ramoops logging, and removes every initramfs watchdog open/ping path. A
respawned tty1 shell exposes a typeable `reboot` wrapper whose durable request
marker precedes one forced restart request.

Build reproduction is complete: two clean packages contain 220 identical
non-timestamp files, two final assemblies match recursively, all 32 LK gates
pass, and the mutation suite rejects 47/47 cases. The selected package is
`linux-7.1.3-gemini-observability-fbcon-rotation-keyboard-wrrd-manual-reboot-4cd417ad-c811a159`.
The deterministic initramfs SHA-256 is
`b54ce3cd75e7947ed867165e31abbf6ee6cbac7d41d171435f99bba7825bc769`;
the 6,864,896-byte raw image SHA-256 is
`bf4003871daaba1faa293f2b128021d3a67d41ebf3ddff1c42463409803b9296`.
The guarded helper backed up exact W, live-resolved `boot2` as
`/dev/mmcblk0p30` with active root `/dev/mmcblk0p29`, wrote and flushed X, and
verified a complete 16 MiB readback with SHA-256
`e89d71f15465b544db163b5f0b90b456e913c38ba4d2ed49aa7bde345148c855`.
It did not reboot; the device remained in its known-good OS with an unchanged
boot ID.

The owner later reported that X booted and worked, but typed `reboot` appeared
to hang. No automatic return was observed; power-key recovery reached Gemian
and pstore was empty. Do not claim clean tty1, exact X entry, X uptime, or
individual keyboard subgates. See the
[Candidate X experiment](../experiments/2026-07-19-keyboard-manual-reboot-diagnostic/README.md),
[build reproduction](../experiments/2026-07-19-keyboard-manual-reboot-diagnostic/results/final-build-reproduction-20260719.txt),
[mutation result](../experiments/2026-07-19-keyboard-manual-reboot-diagnostic/results/validator-mutations-20260719.txt),
[guarded write/readback](../experiments/2026-07-19-keyboard-manual-reboot-diagnostic/results/boot2-write-candidate-x-20260719.txt),
and [runtime result](../experiments/2026-07-19-keyboard-manual-reboot-diagnostic/results/runtime-candidate-x-attempt-1-20260719.txt).

Candidate Y was reproducibly built and fully read back, but an exact BusyBox
audit rejected it before boot. Bare `reboot` resolves to BusyBox's internal
applet instead of Y's external wrapper, and a failed special-builtin watchdog
redirection exits before its promised refusal. Y was never selected and must
not be booted.

Candidate Z is the hardware-tested keyboard/recovery artifact inherited by AA r1. It reuses Y's exact kernel, DTB, and
configuration, changes `init`, `bin/local-shell`, `bin/reboot`, and
`bin/x-record`, and adds read-only `bin/reboot-dispatch.env`. The final
interactive shell inherits an alias to absolute `/bin/reboot`; a runtime oracle
withholds the shell unless exact BusyBox reports
`reboot is an alias for /bin/reboot`. The wrapper performs exact
`mtk-wdt`/ramoops preflight before a catchable function-call open, sends one
ping, holds fd 3, and visibly waits for the 31-second hardware expiry with no
sync or fallback. Two complete builds match recursively; the Linux-arm64
dispatch gate, all 32 LK gates, and 75/75 mutations pass. Raw SHA-256 is
`985a6472b7fdbfd4c58da4773a8c2cae1e3aa40ea90240eb2b309390ed7674b9`;
the installation-time full `boot2` readback is
`ba21e6424f94c82f14fd51b5681eea68d6cf09e9177e4f9ca2061c9f129abb40`.
The owner later selected Z once, reported a successful boot with the keyboard
still working, typed its watchdog reboot, and observed an automatic return to
Gemian. A changed boot ID and `androidboot.bootreason=wdt_by_pass_pwk`
corroborate a watchdog-class reset. No exact marker, live dispatch/preflight
text, countdown timing, clean-console result, or individual-key trace survived;
do not infer those subgates or repeatability. Close unchanged Z. See the [Y rejection](../experiments/2026-07-19-keyboard-typed-watchdog-reboot-diagnostic/results/preboot-command-dispatch-audit-20260720.txt),
[Z experiment](../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/README.md),
[build validation](../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/results/build-validation-20260720.txt),
[dispatch validation](../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/results/ash-dispatch-validation-20260720.txt),
[mutation result](../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/results/validator-mutations-20260720.txt),
[write/readback](../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/results/boot2-write-candidate-z-20260720.txt),
and [runtime result](../experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/results/runtime-candidate-z-attempt-1-20260720.txt).

Candidate AA now has explicit r0 and r1 boundaries. Historical AA r0 was built,
validated, installed, and fully read back, but it was superseded before boot:
its map omitted Shift+Fn F1–F10 and its `dumpkmap` byte comparison was not a
valid live-map oracle. Do not boot it. Its immutable raw image SHA-256 remains
`a2ad7a4107abd99cbd349b8f2deadd0185cbdd5bb0884ecbdae8ff2a7499ed4c`,
its historical keymap SHA-256 remains
`48f1f61a9ad8ba327a3105c0dfbbc698c1e55bb3bcca695b46887888be8ca821`,
and its exact 16 MiB padded logical-`boot2` image and full readback remain
`157c7cd5d814d7b2704d679faacd3215c5e889642b4261441f99653957585eaa`.
Those identities are storage/build evidence only.

AA r1 has now been canonically built twice, validated, installed, and passed
its first attended runtime test. Rebuild it only on Linux AArch64 with
`experiments/2026-07-20-keyboard-console-map-diagnostic/scripts/build-keyboard-console-map-candidate.sh`,
passing the exact Candidate Z artifact, the checksum-pinned Linux v7.1
`drivers/tty/vt/defkeymap.c_shipped`, and a new output parent outside the
repository. The builder retains Z's kernel field, final DTB, configuration,
matrix path, font, dispatch, and typed-watchdog recovery. It changes only
`init`, `bin/local-shell`, and `bin/x-record`, then adds static
`bin/console-unicode-mode`, static `bin/console-keymap-verify`, and read-only
`etc/gemini-us.bkeymap`.

The recovery-VM canonical static AArch64 verifier is SHA-256
`29735d212e74d0b0040a3ead173a83223b89ce5d947b697a115707eb3d23b238`.
Two clean AA r1 constructions are recursively byte- and metadata-identical.
They retain exact Z's kernel field, final DTB, and resolved configuration; the
7,378,944-byte raw boot artifact is SHA-256
`37e82bf3be87dd9e52fb8d60597b69f92a5c0dc5aebd51d178f1e7efd33343d7`.

The r1 map is 2,311 bytes, declares eight tables, has SHA-256
`02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c`,
and makes exactly 53 audited semantic changes. It covers the photographed
printable and navigation layer, Fn+period U+263A, Shift+Fn digits as F1–F10,
the physical backslash key's Ctrl/Alt semantics, and safe modifier
press/release entries. Media, brightness, phone, airplane, launcher, and voice
actions remain userspace policy rather than VT keysyms.

The normal `GEMINI-AA-R1#` prompt is unavailable until tty1 `K_UNICODE` mode is
set and read back. A first shell entry requires exact pre-load table state
before `loadkmap`; a respawn safely accepts only the already loaded exact map.
The static verifier reads all 2,048 entries in the eight planned tables through
`KDGKBENT`, requires every untouched upper-half entry to be `K_HOLE`, accounts
for table 3's valid payload-entry-0 `K_HOLE` becoming kernel `K_ALLOCATED`, and
requires every undeclared table to remain absent. Failure exposes only
`GEMINI-AA-R1-KEYMAP-FAIL#` with Z's typed recovery path. The calibrated
guarded installer required exact r0 padded predecessor
`157c7cd5d814d7b2704d679faacd3215c5e889642b4261441f99653957585eaa`,
resolved live-GPT logical `boot2` as `/dev/mmcblk0p30` with active root on
`/dev/mmcblk0p29`, preserved a private full backup, and wrote, flushed, and
fully read back padded r1 as SHA-256
`38b49c7c19c2d97fa0c48436545219489221aa367aedf491ae6ebd4ec4856703`.
The operation did not reboot or select a slot. See the [AA r0/r1
experiment](../experiments/2026-07-20-keyboard-console-map-diagnostic/README.md),
r1 [build validation](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/build-validation-aa-r1-20260721.txt),
[installer validation](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/installer-validation-aa-r1-20260721.txt),
[guarded write/readback](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/boot2-write-candidate-aa-r1-20260721.txt),
[layout reference](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/layout-reference-aa-r1-20260721.txt),
and [runtime result](../experiments/2026-07-20-keyboard-console-map-diagnostic/results/runtime-candidate-aa-r1-attempt-1-20260721.txt).

In attended attempt 1, retained pstore records `origin=loaded-now` at 2.407618
seconds, successful tty1 `K_UNICODE` readback, all 2,048 planned-table entries
exact, all high halves holes, all undeclared tables absent, table 3 allocated,
`GEMINI-AA-R1#`, and validated reboot dispatch. The owner reported that the
new keymap worked, and retained A/S press-release events corroborate the input
path. Bare `reboot` was requested at 126.258967 seconds, proving an interval
longer than 123 seconds without automatic watchdog ownership; the inherited wrapper then
opened and pinged the 31-second watchdog once, retained fd 3, and recorded
5/10/15/20/25/30-second countdown checkpoints. A changed boot ID plus Gemian
`boot_reason=4`, `androidboot.bootreason=wdt_by_pass_pwk`, and
`powerup_reason=reboot` corroborate the return. F1–F10 and Page Up/Page Down
remain unconfirmed, not failed, because the console supplied no visible
discriminator.

Candidate AB is the separate kernel-native reboot experiment. Patch 0087 gives
only MT6797 TOPRGU restart priority 255 so it runs before ARM64 PSCI priority
129; every other supported MediaTek watchdog variant remains at 128. After
`KBUILD_BUILD_VERSION=1` was pinned, managed clean builds 3 and 4 reproduced
all 221 non-dynamic package files and modes. Their raw `build.json` differs
only in `generated_utc`, and their normalized provenance is exact. The common
`Image.gz` SHA-256 is
`37ba538e76e329f3e57cfa78b481151e2d1e5eabcc321a29c7b54d476b6ec26f`.

Two complete AB constructions, one from each package, retain the exact
hardware-passed AA r1 final DTB and console keymap and are recursively byte-
and mode-identical. The raw 7,378,944-byte image SHA-256 is
`61c74592267466735164c19f8b831ea18db2892de95e32109f2aacd7ec5c5446`.
Both constructions passed all 32 LK gates, deterministic boot-v0 and initramfs
reconstruction, and final validation; all 25 focused mutations were rejected.
The exact four-file initramfs delta has no userspace watchdog, countdown,
fallback, storage action, or automatic reboot. Its `/bin/reboot` records AB
attribution and invokes forced no-sync BusyBox reboot once.

The calibrated installer required exact padded AA r1 SHA-256
`38b49c7c19c2d97fa0c48436545219489221aa367aedf491ae6ebd4ec4856703`,
resolved live-GPT logical `boot2` as inactive `/dev/mmcblk0p30` while root was
`/dev/mmcblk0p29`, preserved a full private backup, performed one bounded
16 MiB write, synchronized and flushed it, then required matching remote and
local full readbacks at SHA-256
`b58c0347d34a3fd9031c74cb03447dd7a6fc630d5b8ea2b7eabc36827e754350`.
The installer did not reboot or select a slot, and the boot ID remained
`0f8def4f-3f94-4c57-a34c-2bb37315b19f`. In attended attempt 1 the exact AB
marker, console-map gate, and `GEMINI-AB#` prompt were retained, and the owner
confirmed that the keyboard worked. The owner waited 45 seconds without an
automatic reset or countdown, typed bare `reboot`, and observed the reset
immediately. Pstore records the manual request at 66.021584 seconds and the
final kernel `reboot: Restarting system` line at 66.049438 seconds, a 27.854 ms
request-to-final-log interval rather than an instrumented Enter-to-LK timing.
Gemian returned under boot ID `e33a0d8e-0354-4c8c-95b3-07c6970152ec`, changed
from the pre-test ID. Its `boot_reason=4`,
`androidboot.bootreason=wdt_by_pass_pwk`, and `powerup_reason=reboot` fields are
a nondiscriminating watchdog-class reason; command timing and the audited
absence of userspace watchdog ownership support prompt kernel TOPRGU SWRST.
This is one local hardware pass on the named unit, not repeatability or a
universal reliability claim. F1–F10 and Page Up/Page Down remain unconfirmed,
not failed. See the [AB
experiment](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/README.md),
[kernel reproducibility](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/kernel-reproducibility-ab-20260721.txt),
[container validation](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/container-validation-ab-20260721.txt),
[installer validation](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/installer-validation-ab-20260721.txt),
[guarded write/readback](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/boot2-write-candidate-ab-20260721.txt),
and [runtime result](../experiments/2026-07-20-mt6797-kernel-restart-diagnostic/results/runtime-candidate-ab-attempt-1-20260721.txt).

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
