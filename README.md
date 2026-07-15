# Gemini PDA Mainline

Upstream-first Linux enablement for the Planet Computers Gemini PDA.

> [!WARNING]
> This is an early hardware-enablement project, not a custom ROM or a daily-driver image. An incorrect image, partition write, clock, regulator, or memory-map change can corrupt data or damage hardware. Preserve a known-good recovery path, back up device-specific data, and never experiment on the preloader, NVRAM, or partition table.

## Mission

Make the Gemini PDA a first-class mainline Linux device: bootable with an ordinary upstream-derived arm64 kernel, described by upstream Device Tree, usable with standard Linux subsystems, and maintainable without a permanent vendor-kernel fork.

The desired end state is distribution-owned kernel updates, not a repository-owned ROM:

```text
MediaTek BootROM
  -> retained low-level firmware while bring-up is in progress
  -> maintained bootloader or chainloader
  -> standard Linux Image + upstream DTB + initramfs
  -> Debian, Alpine, postmarketOS, or another ordinary distribution
```

## What this repository is

This repository is the coordination and reproducibility layer for:

- hardware archaeology backed by evidence;
- a safe, repeatable mainline boot loop;
- temporary, reviewable patch series on current upstream Linux;
- test logs and hardware-support tracking;
- upstream submission state across Linux, Device Tree bindings, bootloaders, and userspace;
- cross-project coordination.

It is intentionally **not** a long-lived Linux source fork. Generic support belongs in the relevant upstream subsystem; Gemini-specific description belongs in an upstream board Device Tree.

## Current status

The project is at **M0: safe reproducible lab**.

- Current upstream Linux contains a skeletal MT6797 SoC description, but no upstream Gemini PDA board Device Tree.
- Historical work in [`Jasu/gemini-pda-buildroot`](https://github.com/Jasu/gemini-pda-buildroot) reached BusyBox over UART. That result is valuable prior art, but must be reproduced against a current upstream kernel.
- [`bsg100/gemini-linux`](https://github.com/bsg100/gemini-linux) is an active modern bring-up effort with substantial hardware research. Coordination and reuse-by-reference come before parallel driver work.
- The current Linux 7.1.3 77-patch package and private LK-compatible gzip/appended-DTB candidate validate in the ARM64 VM; neither has been transferred, flashed, or booted.
- No subsystem is marked working here until a reproducible log from real Gemini hardware supports the claim.

See the [hardware support matrix](docs/HARDWARE_SUPPORT.md) for the evidence model and current inventory.

## Project principles

1. **Upstream is the product.** Local patches are a staging area with an owner, upstream destination, and deletion condition.
2. **No permanent kernel fork.** Rebase temporary series onto current upstream; do not accumulate a private platform tree.
3. **Use standard subsystem interfaces.** Prefer DRM/KMS, input, power-supply, regulator, MMC, USB, ALSA, rfkill, and ModemManager-compatible interfaces.
4. **Separate SoC and board work.** Reusable MT6797 support must not be hidden in Gemini-only code.
5. **Keep blobs behind kernel interfaces.** Opaque modem, Wi-Fi, or microcontroller firmware may remain where unavoidable; proprietary kernel modules are not an acceptable end state.
6. **Make experiments reversible.** Keep a known-good boot mode and recovery image; never make preloader or NVRAM changes part of the normal workflow.
7. **Publish evidence, not folklore.** Record source, device variant, kernel commit, configuration, test method, and logs.
8. **Stay distribution-neutral.** A successful port boots standard userspace rather than requiring a project-specific root filesystem.

The full rationale and ownership boundaries are in [Architecture and ownership](docs/ARCHITECTURE.md).

## Roadmap

| Milestone | Outcome |
| --- | --- |
| M0 — Safe reproducible lab | Recovery, provenance, variant inventory, reproducible builds, and non-destructive CI |
| M1 — Current-mainline UART boot | Current upstream kernel reaches initramfs over UART repeatedly with core SoC behavior validated |
| M2 — Persistent headless system | PMIC basics, eMMC root, USB networking/serial, SSH, and safe battery telemetry |
| M3 — Keyboard and USB serviceability | Built-in keyboard, microSD, both USB-C paths, role switching, and hotplug |
| M4 — Native display and touch | DRM/KMS scanout, panel/backlight, and touchscreen input |
| M5 — Mobile-grade power | Thermal protection, DVFS, runtime PM, suspend, reliable wake, and measured power use |
| M6 — Daily-driver peripherals | ALSA audio, Panfrost acceleration, Wi-Fi, Bluetooth, GNSS, and sensors |
| M7 — Standard boot and distro integration | Standard boot artifacts and a released-kernel, distribution-owned update path |
| Stretch — Cellular and optional hardware | Cellular transport, cameras, external display, and deeper early-firmware ownership |

Detailed exit criteria and sequencing are in the [roadmap](docs/ROADMAP.md).

Live planning is tracked in the pinned [project plan](https://github.com/ixoo/gemini-pda-mainline/issues/1), the [milestones](https://github.com/ixoo/gemini-pda-mainline/milestones), and the [open issue backlog](https://github.com/ixoo/gemini-pda-mainline/issues).

## Start here

If you own hardware:

1. Read [Safety and recovery](docs/SAFETY.md) before connecting flashing tools.
2. Identify the exact device variant and record non-sensitive evidence.
3. Record durable facts in the [hardware knowledge base](docs/hardware/README.md)
   and reproducible investigations with their code under
   [`experiments/`](experiments/README.md).
4. Choose an issue with `status: ready` and `hardware: required`, or add research to an existing issue.
5. Never publish NVRAM dumps, IMEI values, serial numbers, keys, or calibration blobs.

If you work on kernels:

1. Read [Architecture and ownership](docs/ARCHITECTURE.md) and [Contributing](CONTRIBUTING.md).
2. Set up the supported [ARM64 development VM](docs/DEV_VM.md).
3. Use the [pinned stable-kernel patch workflow](docs/KERNEL_WORKFLOW.md).
4. Start from a pinned upstream release and preserve the complete build configuration.
5. Keep one logical change per patch and identify its upstream subsystem and maintainers.
6. Attach boot logs and test conditions; compile success alone is not hardware support.

## Repository layout

```text
configs/              Gemini kernel configuration fragments
docs/                 Architecture, roadmap, safety, references, and support matrix
experiments/           Reproducible investigations, associated code, and sanitized evidence
kernel/               Pinned stable-kernel source and configuration manifest
patches/              Temporary patch series grouped by upstream base (added when needed)
scripts/              Reproducible build, packaging, and test helpers (added when verified)
vm/                   ARM64 development VM definition and provisioning inputs
project/              Declarative labels, milestones, and initial backlog
.github/              Contribution, issue, and pull-request workflows
```

Large vendor trees, firmware images, partition dumps, root filesystems, and build outputs do not belong in Git.

## Related work

This project begins by mapping and coordinating existing work rather than claiming a green-field port. See [References and prior art](docs/REFERENCES.md), especially:

- [`bsg100/gemini-linux`](https://github.com/bsg100/gemini-linux) — active modern bring-up and hardware notes;
- [`Jasu/gemini-pda-buildroot`](https://github.com/Jasu/gemini-pda-buildroot) — historical mainline UART boot;
- [`gemian/gemini-linux-kernel-3.18`](https://github.com/gemian/gemini-linux-kernel-3.18) — downstream 3.18 source;
- [`planet-community/android_kernel_planetcom_mt6797`](https://github.com/planet-community/android_kernel_planetcom_mt6797) — vendor-kernel mirror;
- [`ixoo/gemini-flash-vagrant`](https://github.com/ixoo/gemini-flash-vagrant) — account-owned historical flashing helper.

References are not endorsements of flashing instructions or licensing. Verify every artifact before use.

## Contributing

Contributions are welcome across kernel development, hardware research, documentation, test automation, and careful on-device validation. Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Kernel-bound work must follow the target upstream project's licensing, sign-off, and submission rules.

## License

Repository-authored documentation and tooling are available under the [MIT License](LICENSE) unless a file states otherwise. Imported or upstream-bound kernel material must preserve and follow its own license and SPDX identifiers.

Gemini PDA and Planet Computers are names associated with their respective owners. This independent community project is not affiliated with or endorsed by Planet Computers.
