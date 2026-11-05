# Gemini PDA Mainline

Upstream-first Linux enablement for the Planet Computers Gemini PDA.

> [!CAUTION]
> **v1 ships as it is, and you use it entirely at your own risk.** It can corrupt your data,
> cost you your recovery path or damage your device. It has had limited testing, on one unit.
> There is no warranty ([MIT licence](LICENSE)) and no promise of support.

> [!WARNING]
> This is an early hardware-enablement project, not a custom ROM or a
> daily-driver image. An incorrect image, partition write, clock, regulator, or
> memory-map change can corrupt data or damage hardware. Preserve a known-good
> recovery path, back up device-specific data, and never experiment on the
> preloader, NVRAM, or partition table.

## Mission

Make the Gemini PDA a first-class mainline Linux device: bootable with an
ordinary upstream-derived arm64 kernel, described by upstream Device Tree,
usable through standard Linux subsystems, and maintainable without a permanent
vendor-kernel fork.

The intended end state is distribution-owned kernel updates, not a
repository-owned ROM:

```text
MediaTek BootROM
  -> retained low-level firmware while bring-up is in progress
  -> maintained bootloader or chainloader
  -> standard Linux Image + upstream DTB + initramfs
  -> ordinary distribution userspace
```

## Current status

The named Gemini runs a Linux 7.1.3 development station from RAM, through the
retained LK and non-primary `boot2`, with the owner holding the side key to select
it. Everything below is one unit on a local patch series. Nothing has been submitted
upstream, it isn't a daily driver, and a build isn't support.

- **In use on the station:** the console on the native display at a measured 54 Hz,
  the keyboard, the lid, USB SSH, eight A53 CPUs, restart, writes to `boot2` from the
  running system with full readback, speakers and headphones at 48 kHz, and Wi-Fi as
  WPA2-PSK on the owner's network.
- **Protection in the kernel:** a charge guard, which stops at capacity 80 %, 50 °C
  and 0 °C, and thermal trips. None of the trips has fired, the guard has been shown
  by moved limits and emulation rather than a real charge or a real hot or cold
  battery, and charging isn't limited while powered off.
- **Modules loaded by hand, mostly on one boot:** the touchscreen, the Mali-T880
  through Panfrost, Bluetooth A2DP, the IMU and light and proximity sensors, the front
  camera through a test tool with its DMA bypassing the M4U, the AW9120 indicator
  LEDs, and the two A72 CPUs on an opt-in profile.
- **Partly there:** GNSS tracks two live satellites from a userspace host, with no
  position on mainline yet.
- **Not started or not shown:** suspend, cpuidle and cpufreq, which decide battery
  life and heat; microSD; USB host; the modem.

**[v1](docs/RELEASE_READINESS.md) is all of the above, with that limited testing,** still without
cpufreq or power governors. People can start experimenting with it, at their own risk. The public
image now carries all of it, with most parts loaded by hand; that build booted once, and every
group but the radios [loaded](experiments/2026-10-30-mainline-dev-station/README.md#v1-candidate-boot-2026-11-05) with taint 0. There's no first-install tool, as the [testing guide](docs/TESTING_GUIDE.md) says.

The [hardware support matrix](docs/HARDWARE_SUPPORT.md) owns current capability
claims and their limits. Exact candidates and negative results live in
[experiments](experiments/README.md), and the [roadmap](docs/ROADMAP.md) owns the
current work order.

## What this repository is

This repository is the coordination and reproducibility layer for:

- hardware archaeology backed by evidence;
- a safe, repeatable mainline boot loop;
- temporary, reviewable patches against a pinned upstream kernel;
- named experiment profiles, test logs, and hardware-support tracking;
- upstream submission state across Linux, Device Tree bindings, bootloaders,
  and userspace.

It intentionally does not vendor a Linux source tree or act as a long-lived
kernel fork. Generic support belongs in the relevant upstream subsystem;
Gemini-specific description belongs in an upstream board Device Tree.

## Project principles

1. **Upstream first.** Every local patch needs a plausible upstream home and a
   deletion condition.
2. **Evidence before implementation.** Record the exact variant, source,
   method, uncertainty, and contradiction before promoting a hardware claim.
3. **Safe iteration.** Keep recovery independent, target only explicitly
   authorized non-primary partitions, and reject ambiguous device writes.
4. **Reproducibility.** Pin the upstream source, patch selection,
   configuration, toolchain, packaging inputs, and artifact checksums.
5. **Standard interfaces.** Prefer Linux subsystem contracts over
   device-specific userspace ABIs.
6. **Experiments stay experiments.** Detailed candidate chronology, raw
   observations, and rejected branches belong under `experiments/`; durable
   docs contain only current conclusions and links to their evidence.

## Start here

| Goal | Document |
| --- | --- |
| Understand risk and device-write rules | [Safety policy](docs/SAFETY.md) |
| See the current work order | [Roadmap](docs/ROADMAP.md) |
| Check present subsystem support | [Hardware support matrix](docs/HARDWARE_SUPPORT.md) |
| See what v1 is and leaves out | [Release readiness](docs/RELEASE_READINESS.md) and [testing guide](docs/TESTING_GUIDE.md) |
| Understand ownership and patch layering | [Architecture](docs/ARCHITECTURE.md) |
| Reproduce a kernel build | [Kernel workflow](docs/KERNEL_WORKFLOW.md) |
| Inspect durable hardware facts | [Hardware knowledge base](docs/hardware/README.md) |
| Inspect experiment history and evidence | [Experiment index](experiments/README.md) |
| Contribute a change | [Contributing guide](CONTRIBUTING.md) |

## Repository layout

```text
configs/       reusable and named-experiment kernel configuration fragments
docs/          architecture, safety, workflow, support, and hardware facts
experiments/   one directory per investigation, including scripts and results
kernel/        pinned upstream manifest
patches/       ordered reviewable patch series
scripts/       safe build, validation, backup, and device helpers
```

Generated kernel sources, build trees, device captures, credentials, and raw
partition images are local artifacts and must not be committed.

## Related work

- [bsg100/gemini-linux](https://github.com/bsg100/gemini-linux) provides active
  Gemini/MT6797 research and hardware-tested reference points.
- [Jasu/gemini-pda-buildroot](https://github.com/Jasu/gemini-pda-buildroot)
  provides historical early-mainline and BusyBox bring-up evidence.

These projects are evidence and collaboration inputs. Reuse still requires
protocol, licensing, and current-upstream review.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md), [docs/SAFETY.md](docs/SAFETY.md), and
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) before changing code or touching
hardware.

## License

Documentation and repository tooling are licensed under the terms in
[LICENSE](LICENSE). Imported or referenced patches retain their own authorship
and licensing metadata.
