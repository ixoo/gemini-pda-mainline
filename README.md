# Gemini PDA Mainline

Upstream-first Linux enablement for the Planet Computers Gemini PDA.

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

The named Gemini boots local Linux 7.1.3 integration candidates through the
retained LK and non-primary `boot2`. Console, built-in keyboard, USB gadget
administration, native restart, eight A53 CPUs and bounded eMMC development
access have attributable results.

Isolated candidates also demonstrate both A72 CPUs, standard 4+4+2 topology,
bounded cross-CPU RAM checks and repeated CPU9 down/restore. Frequency and
read-only thermal observation have runtime evidence. Cross-boot thermal
repeatability, thermal protection, general power management and default-profile
A72 support remain open. A successful experiment is not released upstream
support.

The [hardware support matrix](docs/HARDWARE_SUPPORT.md) owns current capability
claims. Exact candidates, admission decisions and negative results live in
[experiments](experiments/README.md). The [roadmap](docs/ROADMAP.md) owns the
current work order and parallel delivery plan; the
[workstream registry](project/workstreams.json) records responsibility and scope.

The project now separates safe development-system integration, A72/power
research and upstream preparation. Independent display, connectivity and
peripheral research does not wait for complete A72 suspend support. All device
experiments share one explicit admission queue and preserve recovery.

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
| See the current critical path | [Roadmap](docs/ROADMAP.md) |
| Check present subsystem support | [Hardware support matrix](docs/HARDWARE_SUPPORT.md) |
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
