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

## Storage use

Keep the VM ready for development, but do not use it as a historical archive.
The normal steady state is the provisioned toolchain, verified download cache,
one prepared copy of each kernel source state still in use, active
out-of-tree builds, and the exact artifacts required by open experiments.

Before a large extraction, clean build, or reproducibility run, inspect the
guest filesystem and the three workspace roots:

```sh
./scripts/dev-vm run bash -lc \
  'df -h "$HOME"; du -x -h -d 1 "$HOME/src" "$HOME/build" "$HOME/artifacts"'
```

The managed kernel workflow reuses a prepared tree when its source-state marker
matches. Do not select a new `GEMINI_SOURCE_ROOT` simply to make a clean build.
Use a separate `GEMINI_BUILD_ROOT` when independent build output is required,
then remove that directory once its checksums and comparison result have been
recorded. A separate source root is justified only when extraction or source
preparation is itself under test, and it is temporary.

Review `~/artifacts` at the end of an experiment. Keep the selected validated
package or candidate and unique decision-relevant evidence; remove failed
staging directories, superseded packages, and redundant exports after their
provenance and result are recorded. Use `export-artifact` for the exact item
needed on the host instead of copying all guest artifacts.

Do not treat private host artifacts as ordinary build cache. Device-partition
backups and unique captures may be large but irreplaceable; review their
retention and independent backup status before deleting them. Reclaim
regenerable guest source/build data and redundant exports first.

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

The default `full` profile is the hardware-development build. For a first LK
handoff test, build the separate built-in-only profile instead:

```sh
KERNEL_JOBS=8 ./scripts/dev-vm build-handoff-kernel
```

That profile keeps only the early console, framebuffer console, architectural
boot foundation, MT6797 clocks/pinctrl/timers, and watchdog. It deliberately
omits storage, PMIC/regulator, DMA/IOMMU, SCP, USB, network, and other
peripheral probes. `KERNEL_PROFILE`, `BUILD_MODULES`, and `KERNEL_JOBS` are
also forwarded by the lower-level `./scripts/dev-vm kernel COMMAND` form;
generated source, build, and module files remain guest-owned.

For a reusable minimal USB-gadget handoff build, use the separate `usbdiag`
profile:

```sh
KERNEL_JOBS=8 ./scripts/dev-vm build-usbdiag-kernel
```

It applies after the handoff fragment and adds only IPv4, gadget-only MTU3,
the MT6797 USB2 T-PHY, regulator core, and built-in `g_ether`. Storage, USB
host/dual-role mode, xHCI, Type-C policy, mass-storage gadgets, and unrelated
network-device families remain disabled. This is still a build result, not a
USB runtime claim.

See the [pinned stable-kernel patch workflow](KERNEL_WORKFLOW.md) for the
manifest, patch-series, configuration, provenance, and artifact contracts.

Validate the explicitly selected guest-owned package, including every file in
its checksum manifest and the required provenance fields:

```sh
./scripts/dev-vm validate-kernel
```

This is still a compile-and-package check, not evidence that the image boots or
that a driver works on hardware. Built-in symbols are the only drivers
available before a root filesystem can load modules; when `BUILD_MODULES=1` is
used, optional modules are exported under the package's `modules/` tree for
later rootfs integration. Dated package records remain with their experiments
and are not current authority. Select the exact package named by the active
experiment as described in [the kernel workflow](KERNEL_WORKFLOW.md); never
infer “latest” from a timestamp or directory order.

## Build a non-flashing LK candidate

The retained Planet LK path needs an Android-v0
gzip-plus-appended-DTB container, not the raw `Image`. Candidate construction
is experiment-specific: use only the builder and validator named by the active
experiment, pass its exact validated package, and choose a new explicit output
directory.

A candidate builder must remain non-flashing, reject implicit “newest”
selection and output overwrite, record its complete inputs, and validate the
LK placement, appended DTB, initramfs, configuration, provenance, and
checksums required by that experiment. Exact commands, deltas, identities, and
runtime classifiers belong in the experiment record rather than this VM
guide. See the [kernel workflow](KERNEL_WORKFLOW.md#building-an-lk-boot-candidate)
and [experiment index](../experiments/README.md).

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
machine. Prefer the bounded form when only one reviewed candidate is needed:

```sh
./scripts/dev-vm export-artifact boot-candidates/EXACT-DIRECTORY
```

It copies only that path below guest `~/artifacts` to host
`artifacts/vm-export/`, rejects traversal and absolute paths, and refuses to
overwrite an existing host target. Never include the preloader, NVRAM, a
partition table, or a whole-device image in the normal workflow.

## Deleting the VM

Deletion removes the guest filesystem, including `~/src`, `~/build`, and
`~/artifacts`. It requires an explicit destructive flag:

```sh
./scripts/dev-vm remove --force
```

Export anything that must be retained before deleting the instance.
