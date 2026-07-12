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

The private, Git-ignored payload is exposed read-only at
`~/reverse-engineering/gemini-vendor`. Analysis notes and generated databases
should go in a separate guest-owned directory such as
`~/reverse-engineering/work/`; tools cannot modify the source extraction.

Provisioned tools include:

- Ghidra 12.1.2 headless, pinned by the official release SHA-256 with native
  Linux ARM64 components built during provisioning, running on OpenJDK 21;
- Radare2, GDB multiarch, AArch64/ARM32 binutils, elfutils, Capstone, checksec,
  patchelf, pax-utils, strace, and ltrace;
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

## Build the patched stable kernel

The repository is already wired into the guest's native source, build, and
artifact directories. Run the complete verified pipeline from macOS:

```sh
./scripts/dev-vm build-kernel
```

See the [pinned stable-kernel patch workflow](KERNEL_WORKFLOW.md) for the
manifest, patch-series, configuration, provenance, and artifact contracts.

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
