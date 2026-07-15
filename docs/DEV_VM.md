# ARM64 development VM

The supported development environment is an ARM64 Ubuntu 24.04 LTS virtual
machine on Apple Silicon. It is intended for Linux, Device Tree, initramfs,
boot-artifact, and static-analysis work. Firmware flashing remains outside this
VM and should be performed from the separate x86_64 Windows recovery machine.

## Design

- Lima manages the VM declaratively.
- Apple's Virtualization Framework (`vz`) runs an ARM64 guest without CPU
  emulation.
- The Ubuntu cloud image is selected by a dated URL and verified by SHA-256.
- Kernel trees and build outputs live on the guest's ext4 filesystem.
- The host repository is mounted read-only at `/mnt/gemini-pda-mainline`.
- No USB passthrough or flashing software is configured.
- Guest package inventories are recorded under `~/.config/gemini-pda/`.

The read-only repository mount lets host-side editors and Codex update project
scripts and patches without allowing a guest process to alter the checkout.
Large source trees and build outputs stay out of the macOS filesystem.

## Create the VM

On an Apple Silicon Mac with Homebrew installed:

```sh
./scripts/dev-vm setup
```

The command installs Lima if necessary, creates the VM, provisions development
tools, and runs a health check. Defaults are 8 CPUs, 8 GiB RAM, and a 100 GiB
expandable disk. Override them only before the first creation:

```sh
DEV_VM_CPUS=10 \
DEV_VM_MEMORY_GIB=12 \
DEV_VM_DISK_GIB=150 \
./scripts/dev-vm setup
```

Lima stores the VM disk outside this Git repository. Changing these environment
variables later does not resize an existing instance.

## Daily use

```sh
# Enter an interactive Linux shell.
./scripts/dev-vm shell

# Enter directly in the private vendor-binary extraction.
./scripts/dev-vm re-shell

# Run one Linux command from macOS.
./scripts/dev-vm run uname -a

# Stop and restart the VM.
./scripts/dev-vm stop
./scripts/dev-vm start

# Verify architecture, mounts, and development tools.
./scripts/dev-vm doctor
```

The guest creates these directories:

```text
~/src/         Linux, Buildroot, U-Boot, and other source trees
~/build/       Out-of-tree build directories
~/artifacts/   Images, DTBs, checksums, manifests, and export candidates
```

The project checkout is available as both `/mnt/gemini-pda-mainline` and the
`~/gemini-pda-mainline-host` symlink. It is intentionally not writable.

## Reverse engineering

Run the host-side extraction first, then reprovision the VM:

```sh
./scripts/extract-device-userspace --target gemini@DEVICE
./scripts/dev-vm provision
./scripts/dev-vm re-shell
```

If `artifacts/credentials/gemini_ed25519` exists, the extractor automatically
uses that Git-ignored key with `IdentitiesOnly=yes` and `IdentityAgent=none`.

The private, Git-ignored payload is exposed read-only at
`~/reverse-engineering/gemini-vendor`. Analysis notes and generated databases
should go in a separate guest-owned directory such as
`~/reverse-engineering/work/`; tools cannot modify the source extraction.

Provisioned tools include:

- Ghidra 12.1.2 headless, pinned by the official release SHA-256 with native
  Linux ARM64 components built during provisioning, running on OpenJDK 21;
- Radare2, GDB multiarch, AArch64/ARM32 binutils, elfutils, Capstone, checksec,
  patchelf, pax-utils, strace, and ltrace;
- `vmlinux-to-elf` 1.3.6 in the pinned Python environment for reconstructing
  symbol-bearing ELFs from raw or compressed vendor kernel images;
- QEMU AArch64/ARM user-mode emulation and an ARMHF cross libc;
- APKTool, AAPT, Android build tools, and ADB for Android formats;
- Binwalk, YARA, ssdeep/hashdeep, Sleuth Kit, Foremost, archive/compression
  tools, SQLite, and fast text/hex inspection utilities;
- Python bindings for ELF parsing, Capstone disassembly, and Unicorn emulation.

Ghidra is wired as `ghidra-analyze` for headless projects and `ghidra` for the
GUI launcher. The VM does not configure a graphical display by default, so
headless analysis is the reproducible path. Ghidra's local project databases
must be created under the guest filesystem, not the read-only payload mount.
The version and digest come from the
[official Ghidra 12.1.2 release](https://github.com/NationalSecurityAgency/ghidra/releases/tag/Ghidra_12.1.2_build),
and provisioning follows the project's
[Linux ARM64 native-build guidance](https://github.com/NationalSecurityAgency/ghidra/blob/master/GhidraDocs/GettingStarted.md).

Validation snapshot (2026-07-13): `./scripts/dev-vm doctor` passed on the
ARM64 Ubuntu 24.04 guest with Ghidra 12.1.2, Radare2 5.5.0, GDB 15.1,
`vmlinux-to-elf`, DTC, dtschema, and the cross-analysis utilities available.
From the payload root, `sha256sum -c FILES.sha256` passed for all 696 extracted
files with zero failures. The guest-visible payload is a read-only mount, so
its mode-0777 mount presentation cannot be tightened from inside the VM; the
host target remains mode 0700 and its manifest remains mode 0600. Keep analysis
databases and temporary decompilation output in guest-owned
`~/reverse-engineering/work/`, never beside the evidence payload.

## Build the patched stable kernel

The repository is already wired into the guest's native source, build, and
artifact directories. Run the complete verified pipeline from macOS:

```sh
./scripts/dev-vm build-kernel
```

To package the optional `CONFIG_*=m` outputs as well, use the same wrapper
with the documented build override:

```sh
BUILD_MODULES=1 KERNEL_JOBS=8 ./scripts/dev-vm build-kernel
```

The wrapper forwards only `BUILD_MODULES` and `KERNEL_JOBS`; generated source,
build, and module files remain guest-owned.

See the [pinned stable-kernel patch workflow](KERNEL_WORKFLOW.md) for the
manifest, patch-series, configuration, provenance, and artifact contracts.

Validate the newest guest-owned package, including every file in its checksum
manifest and the required provenance fields:

```sh
./scripts/dev-vm validate-kernel
```

This is still a compile-and-package check, not evidence that the image boots or
that a driver works on hardware. Built-in symbols are the only drivers
available to the current first-boot Image; when `BUILD_MODULES=1` is used,
optional modules are exported under the package's `modules/` tree for a later
rootfs integration. The latest authoritative package record is
[the 2026-07-14 77-patch package result](../experiments/2026-07-12-input-backlight-recovery/results/mainline-display-input-current-77-package-20260714.txt);
the current Image/DTB package intentionally has no module tree. A separate
74-patch module-bearing package remains available for later rootfs integration
and is not the first boot candidate.

## Build a non-flashing LK candidate

The retained Planet LK path needs an Android v0 gzip+appended-DTB container,
not the raw `Image`. Build one from a validated guest package with the
read-only wrapper:

```sh
./scripts/dev-vm run bash -lc \
  'experiments/2026-07-12-boot-contract-recovery/scripts/build-current-lk-candidate.sh \
     --package "$HOME/artifacts/gemini-pda/linux-7.1.3-gemini-6116c9e7da3f" \
     --output "$HOME/artifacts/boot-candidates/<new-directory>"'
```

The wrapper builds a deterministic minimal ARM64 UART initramfs, validates the
package, serializes the candidate, and records parser evidence and SHA-256
values. It refuses an existing output directory and exposes no device,
partition, fastboot, or flashing operation. Its output is guest-owned and
Git-ignored; transfer to the separate Windows flashing machine remains a
separate, explicitly reviewed step. Regenerate the candidate after changes to
`experiments/2026-07-12-boot-contract-recovery/initramfs/init`; the initramfs
is part of the candidate hash and provenance.

## Updating provisioning

After changing `vm/apt-packages.txt`, `vm/python-requirements.txt`, or
`vm/provision.sh`, apply the new provisioning to the existing VM:

```sh
./scripts/dev-vm provision
./scripts/dev-vm doctor
```

Provisioning is idempotent. It does not run a distribution upgrade or fetch a
Linux source tree. Kernel source revisions, configurations, and patch stacks
belong to the separate reproducible-build workflow.

## Exporting artifacts

Export candidates are copied to a new ignored directory on the host:

```sh
./scripts/dev-vm export-artifacts
```

An explicit destination can be supplied as the only argument. Create and check
SHA-256 manifests before transferring artifacts to the Windows flashing
machine. Never include the preloader, NVRAM, a partition table, or a whole-device
image in the normal workflow.

## Deleting the VM

Deletion removes the guest filesystem, including `~/src`, `~/build`, and
`~/artifacts`. It requires an explicit destructive flag:

```sh
./scripts/dev-vm remove --force
```

Export anything that must be retained before deleting the instance.
