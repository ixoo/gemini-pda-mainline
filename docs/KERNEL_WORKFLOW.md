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
Type-C policy, or unrelated network devices. Kernel
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
logical `boot2`; runtime is the next gate. Since unused-clock cleanup is a
synchronous late initcall that completes before external `/init`, defer the
broad `clk_ignore_unused` discriminator until later evidence makes it specific.
Rotation requires a separate configuration-only candidate after display
retention is stable.

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
