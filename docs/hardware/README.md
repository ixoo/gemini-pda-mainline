# Hardware knowledge base

This directory is the canonical record of durable Gemini PDA hardware facts. It
expands the concise [hardware support matrix](../HARDWARE_SUPPORT.md) without
conflating component identity with Linux runtime support.

Detailed investigations, candidate chronology, scripts, raw samples, and
negative branches belong in the [experiment index](../../experiments/README.md).
A hardware document should summarize only the current conclusion and link to
the experiments that support or challenge it.

## Inventory

| Document | Scope |
| --- | --- |
| [Gemian hardware baseline](gemini-gemian-baseline.md) | Sanitized read-only observations from the working vendor kernel on the named unit. |
| [Gemini audio input/output](gemini-audio.md) | AFE/codec topology, speaker/earpiece/headphone outputs, microphone inputs, headset jack, amplifier and mainline gaps. |
| [MT6351 ACCDET](mt6351-accdet.md) | Headset-jack register contract, MICBIAS1, button AUXADC channel, and the plan for classification and buttons. |
| [MT6797 CPU clusters](mt6797-cpu-clusters.md) | Ten-core identity, three-cluster topology, firmware/vendor ownership, per-cluster clocks, rails, OPP selection, hotplug, and mainline gaps. |
| [MT6797 SPM sleep](mt6797-spm-sleep.md) | Secure-firmware suspend path, A53 retention, SPM program format and loading, deep idle/SODI/suspend entry conditions, PMIC sleep tables. |
| [DA921x, I2C6, and Cortex-A72](da921x-i2c6-a72.md) | Current regulator/transport/CPU boundary, evidence limits, and safety invariants. |
| [MT6797 live resource map](mt6797-live-resource-map.md) | Register, IRQ, clock, rail, storage, display, GPU, connectivity, and USB resources mapped to Linux boundaries. |
| [MT6797 and Gemini interrupts](mt6797-interrupts.md) | GICv3, EINT, SPI/PPI/SGI map, dispatch paths, handler behavior, and live-evidence limits. |
| [Mali-T880 GPU](mali-t880.md) | GPU identity, MFG power/clock/rail map, RT5735, OPP/DVFS, firmware/userspace boundary, and Panfrost configuration recipe. |
| [MT6797 video codec](mt6797-video-codec.md) | VDEC, VENC and MJC registers, interrupts, domains, clocks, larbs, vendor userspace control model, and the mainline gap. |
| [MT6797 thermal observation](mt6797-thermal-observation.md) | Aggregate temperature semantics, shared bank ownership, precision and freshness limits. |
| [MT6797 thermal management](mt6797-thermal-management.md) | Sensor banks, efuse/LK calibration handoff, conversion formulas, trips, cooling policy, and firmware ownership. |
| [MT6351 PMIC auxiliary ADC](mt6351-pmic-adc.md) | Register window, channel scaling, consumers, modem share ring, and upstream coverage. |
| [MT6797 integrated Wi-Fi](mt6797-wifi.md) | Platform ancestry, selected gen3 AHB transport, firmware structure and shared connectivity ownership. |
| [MT6797 Wi-Fi firmware contract](mt6797-wifi-firmware-contract.md) | The behaviour the mainline driver relies on from the host-loaded Wi-Fi image. |
| [MT6797 Bluetooth and Bluetooth audio](mt6797-bluetooth.md) | CONSYS WMT function 0, STP task-0 HCI, both userspace stacks, and the CVSD-over-SRAM voice path. |
| [MT6797 connectivity coexistence](mt6797-connectivity-coexistence.md) | How Wi-Fi, Bluetooth and LTE share the 2.4 GHz medium and the CONSYS subsystem. |
| [Gemini GNSS and navigation](gemini-gnss.md) | CONSYS/BORA receiver ownership, the STP task-2 GFNS protocol, NMEA delivery, and the daemon, SUPL, EPO, FLP and sensor-fusion layers. |
| [Gemini FM receiver](gemini-fm.md) | MT6631 FM over CONSYS STP task 1: packets, registers, power-up and power-down, tune and search, CONSYS I2S audio into the AFE, firmware files and the V4L2 mapping. |
| [GNSS kernel driver specification](gemini-gnss-driver.md) | The `libmnl` protocol mapped to a `drivers/gnss` client, the start/stop state machine, the `MNL.bin` firmware boundary, and the host path that replaces it on this device. |
| [Gemini keyboard](keyboard.md) | AW9523 matrix wiring, physical keymap, and kernel/userspace mapping boundary. |
| [Gemini charging](gemini-charging.md) | Switch charger, boot-chain policy, charge state machine, thermal current gates, and safety limits. |
| [Gemini USB-C ports](usb-c.md) | Both connectors: controllers, PHYs, FUSB301 Type-C logic, VBUS sources, charging, HDMI, and upstream coverage. |
| [Gemini fuel gauge](gemini-fuel-gauge.md) | FGADC counter, SOC/OCV/Qmax/aging model, calibration paths, and persistence. |
| [Gemini I2C1 sensors](gemini-sensors.md) | IMU and light/proximity on mainline, the mount matrix, interrupt ownership, and which candidate addresses answer. |
| [Gemini touchscreen](touchscreen.md) | Controller wiring, vendor TPD/NT36xxx stack, firmware contract, and the project's separate mainline driver. |
| [Gemini camera path](gemini-camera.md) | SP5509 sensor, rails/pins/MCLK, GPL kernel and proprietary HAL split, SENINF/CSI-2 receiver contract, capture path, and mainline mapping. |
| [AW9120 indicator LEDs](aw9120-led.md) | 20-channel LED controller wiring, register/SRAM protocol, Gemian daemon usage, and the mainline module. |
| [Vendor kernel ABI](vendor-kernel-abi.md) | Private interfaces used by the working stack and their standard Linux replacements. |
| [Vendor userspace](vendor-userspace.md) | Android HALs, services, libraries, compatibility bridges, and migration implications. |
| [Firmware boundary](firmware.md) | Installed firmware evidence, licensing/redistribution limits, and protected exclusions. |
| [Retained LK bootloader](lk.md) | Slot selection by key, boot modes, eMMC write protection per mode, boot image limits, DT handoff, verification and fastboot. |
| [Boot graphics](boot-graphics.md) | Retained LK logo-container format, complete slot geometry, Gemian Yamui splash, and modification safety boundary. |
| [Display and panel path](display-panel.md) | Panel/DSI contract, MMSYS/DDP route, fbdev and vendor HWC userspace path, backlight, and the GPU's renderer-only relationship to the panel. |
| [Partition backup boundary](partition-backup.md) | Safe private capture policy, checksums, naming, permissions, and non-public raw state. |

## Documentation assessments

These source reviews preserve documentary contradictions and interpretation
limits. Their reconciliation notes link newer work; current support and
priorities remain in the support matrix and roadmap.

| Assessment | Remaining reference value |
| --- | --- |
| [MT6797 functional specification](../../experiments/2026-09-28-mt6797-functional-spec-review/README.md) | HIF example errors, global DMA visibility and thermal acquisition limits; subsequent HIF review is linked. |
| [MT6351 datasheet](../../experiments/2026-09-28-mt6351-datasheet-review/README.md) | Unresolved VS1/VS2/VPA conversion conflict, incomplete VCN fields and storage trim evidence. |
| [17-source collection](../../experiments/2026-09-29-documentation-collection-review/README.md) | Read side effects, power-control limits, SSD2092 classification and source defects; [source inventory](../../experiments/2026-09-29-documentation-collection-review/sources.json). |

## What belongs here

Create one focused Markdown document per stable subject, such as a device
variant, boot-chain boundary, SoC block, board bus, connector, power rail, or
peripheral. Prefer durable subject names:

```text
docs/hardware/
  variants.md
  boot-chain.md
  mt6797-clocks.md
  keyboard.md
  usb-c.md
```

A hardware document should contain:

- scope and affected Gemini variants;
- confirmed facts tied to a source or experiment;
- inference and disputed claims labeled explicitly;
- independently established register, bus, address, IRQ, GPIO, clock,
  regulator, memory-map, or protocol details;
- firmware and calibration boundaries;
- safety constraints and known destructive operations;
- unresolved questions and discriminating observations;
- a concise evidence index.

Use a compact fact table when it helps:

| Claim | Variant | Confidence | Evidence | Last verified |
| --- | --- | --- | --- | --- |
| Example claim | Wi-Fi + LTE | `inferred` | `experiments/...` | YYYY-MM-DD |

Confidence terms:

| Level | Meaning |
| --- | --- |
| `reported` | A secondary source states it; it has not been independently checked. |
| `inferred` | Evidence favors it, but plausible alternatives remain. |
| `observed` | It was directly measured or read on named hardware. |
| `confirmed` | An explicit method reproduced consistent evidence within its stated scope. |

Confidence always applies to the exact scope stated. Repetition inside one
invocation is not cross-boot repeatability; one named unit is not every
hardware variant.

## What does not belong here

Keep these in the associated `experiments/<date>-<name>/` directory:

- candidate-by-candidate narratives;
- build, package, and partition hashes;
- complete register dumps or sample streams;
- mutation-test output and validator transcripts;
- temporary scripts and one-shot interfaces;
- abandoned hypotheses and superseded result branches.

The durable hardware document should retain the conclusion, the uncertainty,
the unresolved discriminators, and links sufficient to find those records.

## Provenance rules

For each nontrivial claim, record enough information to reassess it:

- exact device variant, with personal identifiers removed;
- evidence type and acquisition method;
- public source revision, kernel/vendor-tree path and commit, or experiment ID;
- observation date and investigator;
- uncertainty, assumptions, and contradictory evidence.

Vendor trees, binaries, and proprietary documents may be lawful research
inputs, but do not copy unlicensed code or documents into this repository.
Record independently established facts and cite the source boundary.

Do not link public documentation to private raw captures, credentials,
absolute local paths, serials, IMEI values, keys, calibration data, or
unreviewed proprietary artifacts.

## Relationship to support status

Knowing that a component exists does not mean Linux supports it. Runtime and
upstream states remain in [the support matrix](../HARDWARE_SUPPORT.md). A
support state changes only when a linked experiment identifies the hardware,
kernel and profile, procedure, repetition count, sanitized evidence, and known
negative space.
