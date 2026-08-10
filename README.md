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

The named development unit boots a local Linux 7.1.3 integration candidate from
the non-primary `boot2` path. The current serviceability foundation includes:

- loader-retained framebuffer console with a readable font, although console
  appearance can be delayed and native DRM/panel ownership is not implemented;
- the built-in keyboard through AW9523 and generic matrix polling;
- USB gadget Ethernet and a development shell;
- native MT6797 TOPRGU kernel restart;
- all eight Cortex-A53 CPUs, logical CPU0–7, online together;
- separately validated development access to the eMMC block layer.

The latest decisive evidence is logged in the
[DA921x board-contract experiment](experiments/2026-07-28-da9214-gauss/README.md).
It completed a serviceability-gated, read-only
DA9213/DA9214/DA9215-compatible tuple over the now-working native I2C6
packed/FIFO `1+1` path.

That result closes the narrow read-only board-contract gate. It does **not**
identify one unique DA921x model, prove a register-data write, register a
regulator provider, establish rail ownership, or enable either Cortex-A72.
Logical CPUs 8 and 9 remain offline by design.

The latest source-only Buildbox gate adds a read-only 19-word LK PTP/EEM
calibration handoff to the dormant state-source seam. It applies and links the
full 201-entry kernel series, but does not read device calibration at runtime,
register an owner/provider, write hardware, boot a device, or open CPU8/CPU9;
see the [PTP handoff Buildbox result](experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/state-source-ptp-handoff-buildbox-20260809.txt).

The next source-only seam decodes the public MT6797 `M_HW_RES1/7/9` detector
fields for BIG/L/2L/CCI and requires all four INIT/MON states plus a nonzero
efuse-variant provenance identity before calibration can proceed. It remains
pure, default-off, and unregistered. Revision `e335ba8` applies all 202
canonical entries on Buildbox, produces 119 DTBs, passes package checksums,
and fetches only the validated package; see the [PTP state decoder Buildbox
result](experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/state-source-ptp-decode-buildbox-20260809.txt).
No runtime calibration was read and no device or CPU8/CPU9 action is implied.

Patch `0214` now makes the decoded PTP state a required input to the dormant
calibration builder. The builder validates the BIG/L/2L/CCI bank identity,
INIT/MON enablement, DVFS level, and bin range before accepting calibration
state. Revision `be44cbc` applies all 203 canonical entries on Buildbox,
produces 119 DTBs, passes package checksums, and fetches only the validated
package; see the [PTP calibration-binding Buildbox result](experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/state-source-ptp-calibration-buildbox-20260809.txt).
This remains compile-only: no provider registration, runtime calibration read,
hardware or firmware operation, device boot, or CPU8/CPU9 admission occurred.

Patch `0215` binds the PTP-derived silicon identity, calibration rows, live
state, full provenance, and owner/transition handles under one transition
mutex. Revision `180d5d7` applies 204 canonical series entries on Buildbox,
produces 119 DTBs, passes package checksums, and fetches only the validated
package; see the [calibrated state-owner source Buildbox result](experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/state-owner-source-buildbox-20260809.txt).
The seam is still default-off and unregistered: actual efuse/EEM/PMIC/clock
source callbacks and protected owner registration remain open, with no
hardware, firmware, device, or CPU8/CPU9 action.

Patch `0216` binds that source to an external clock/rail transition lock and
monotonic generation callback. It rejects a generation change during a full
readback/conversion snapshot and rejects generation rollback, while exposing
only dormant owner callbacks. Revision `0808526` applies 205 canonical series
entries on Buildbox, produces 119 DTBs, passes package checksums, and fetches
only the validated package; see the [transition-generation arbitration
Buildbox result](experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/state-owner-arbitration-buildbox-20260809.txt).
This is still compile-only and unregistered: the real efuse/EEM/PMIC/clock
provider and protected owner registration remain open.

The latest source-only gate adds hardware-free KUnit tests for the DVFSP
resource-owner lifecycle and arbitration boundary. Revision `7bffe69` applies
all 233 canonical patches on Buildbox, links the `dvfsp-owner-kunit` profile,
validates 119 DTBs and package checksums, and fetches only the validated
package; see the [KUnit Buildbox receipt](experiments/2026-08-06-mt6797-dvfsp-firmware-lease/results/owner-kunit-buildbox-20260810.txt).
The tests use fake devices only. No provider is registered, no hardware or
firmware operation occurs, and CPU8/CPU9 remain offline. The next source step
is a reviewed owner/provider bridge for real identity, PPM/CCI, live rail/clock,
and generation callbacks; runtime registration and device boot remain closed.

The profile-series invariant is repaired. The immediate task is the zero-write
legacy-family driver and binding contract, not another ad hoc A72 boot. The
exact sequence and exit criteria through isolated probe/bind/unbind and
provider safety are maintained in the [roadmap](docs/ROADMAP.md#ordered-gates).

See:

- [current roadmap](docs/ROADMAP.md);
- [concise hardware support matrix](docs/HARDWARE_SUPPORT.md);
- [DA921x, I2C6, and Cortex-A72 boundary](docs/hardware/da921x-i2c6-a72.md);
- [experiment index](experiments/README.md).

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
