# Hardware knowledge base

This directory is the canonical record of Gemini PDA hardware facts. It expands
the concise [hardware support matrix](../HARDWARE_SUPPORT.md) without conflating
component identity with runtime support.

## Inventory

- [Gemini PDA Gemian hardware baseline](gemini-gemian-baseline.md) — sanitized,
  read-only observations from the 2019 vendor kernel on one physical device.
- [Firmware boundary](firmware.md) — installed vendor blobs, observed load
  evidence, private-artifact policy, and protected exclusions.
- [Private MMC partition captures](partition-backup.md) — read-only,
  checksummed partition backup tooling and the handling boundary for raw device
  state.
- [MMC partition backup experiment](../../experiments/2026-07-14-mmc-partition-backup/README.md)
  — inventory and provenance for the private all-partition capture.
- [Gemian hardware-specific userspace](vendor-userspace.md) — Android HALs,
  MediaTek services/libraries, native compatibility bridges, and mainline
  migration implications.
- [Gemini PDA keyboard](keyboard.md) — AW9523 matrix wiring, the source-derived
  8×7 keymap, and the userspace XKB/kernel boundary.
- [Vendor kernel ABI and Linux 7.1.3 gaps](vendor-kernel-abi.md) — private
  kernel interfaces consumed by the working stack, upstream coverage, and the
  ordered replacement plan.
- [MT6797 live resource map](mt6797-live-resource-map.md) — register, IRQ,
  clock, rail, M4U-port, display-chain, storage, GPU, connectivity, and USB evidence mapped to
  concrete Linux 7.1.x patch boundaries.
- [Gemini panel recovery experiment](../../experiments/2026-07-11-gemini-panel-recovery/README.md)
  — compiled-in selected NT36672-family panel, DSI timing, bias/reset sequencing,
  and the inactive R63419 device-tree alternative.
- [Camera recovery experiment](../../experiments/2026-07-13-camera-recovery/README.md)
  — runtime SP5509 identity, vendor camera-resource boundary, and the missing
  Linux 7.1.3 sensor/pipeline contracts.
- [External-display recovery experiment](../../experiments/2026-07-13-external-display-recovery/README.md)
  — unbound SII9022/EDID candidates, SII9024A-named vendor wiring, and the
  standard Linux `sii902x` bridge boundary.
- [Memory carve-out recovery experiment](../../experiments/2026-07-13-memory-carveout-recovery/README.md)
  — discontiguous DRAM, fixed firmware reservations, dynamic CONSYS/SCP-share/
  SPM ownership, and the Linux 7.1.3 DT boundary.
- [Modem/CCCI recovery experiment](../../experiments/2026-07-13-modem-ccci-recovery/README.md)
  — live MD1 and MD3/C2K CCCI/CLDMA topology, vendor shared-memory/EMI
  ownership, and the new MT6797 transport boundary.
- [Transport and firmware boundary audit](../../experiments/2026-07-14-transport-firmware-boundary-audit/README.md)
  — current package, DT reservations, proprietary firmware ownership, and
  reusable framework versus new-backend decisions.
- [UART/console recovery experiment](../../experiments/2026-07-13-uart-console-recovery/README.md)
  — live four-port UART topology, vendor AP-DMA versus PIO console behavior,
  and the Linux 7.1.3 8250/bootloader naming boundary.
- [CPU/PSCI/timer recovery experiment](../../experiments/2026-07-13-cpu-psci-timer-recovery/README.md)
  — live CPU DT topology, PSCI 0.2 SMC contract, architectural timer PPIs,
  clocksource/clockevents, and the generic ARM64 reuse boundary.
- [MT6797 thermal recovery experiment](../../experiments/2026-07-13-mt6797-thermal-recovery/README.md)
  — live disabled thermal zones, thermal/AUXADC resources, sensor-bank
  mapping, efuse calibration, and the new-driver boundary.
- [MT6351 PMIC recovery experiment](../../experiments/2026-07-11-mt6351-pmic-recovery/README.md)
  — confirmed PMIC revision, wrapper/reset/EINT dependencies, regulator
  selectors, RTC, power-key path, and mainline patch boundaries.
- [Input and backlight recovery experiment](../../experiments/2026-07-12-input-backlight-recovery/README.md)
  — Novatek touchscreen/EINT, AW9523 keyboard matrix, and MT6797 display-PWM
  contracts compared with Linux 7.1.3, including the vendor-ELF/source parity
  check for the eleven-entry NT36xxx trim table.
- [Sensor and IIO recovery experiment](../../experiments/2026-07-12-sensor-iio-recovery/README.md)
  — live I2C1 sensor bindings, vendor virtual-sensor boundary, and Linux 7.1.3
  reuse versus new-driver decisions.
- [Connectivity/WMT recovery experiment](../../experiments/2026-07-12-connectivity-wmt-recovery/README.md)
  — MT6797 CONSYS/WMT identity, Wi-Fi/BTIF/GNSS/FM resources, firmware
  boundary, and Linux 7.1.3 reuse candidates.
- [Charger and fuel-gauge recovery experiment](../../experiments/2026-07-12-charger-power-recovery/README.md)
  — live BQ25890/FAN49101 ownership, the inactive RT9466 alternative, and
  standard power-supply versus new-driver boundaries.
- [MT6797 watchdog recovery experiment](../../experiments/2026-07-12-mt6797-watchdog-recovery/README.md)
  — TOPRGU register/protocol reuse, the Gemini bark IRQ, and the vendor WDK
  side-channel boundary.
- [Hall/lid/switch recovery experiment](../../experiments/2026-07-12-hall-lid-switch-recovery/README.md)
  — GPIO66/EINT5 hall input, GPIO93/EINT16 toggle input, and the standard
  Linux input replacement boundary.
- [Kernel configuration gap audit](../../experiments/2026-07-12-kernel-config-gap-audit/README.md)
  — vendor-enabled options compared with the prepared Linux 7.1.3 config,
  including modern symbol replacements and private-policy exclusions.
- [Driver coverage audit](../../experiments/2026-07-13-driver-coverage-audit/README.md)
  — exact linked-in/module-only ownership in the current package compared with
  live vendor drivers.
- [First-boot probe audit](../../experiments/2026-07-14-first-boot-probe-audit/README.md)
  — PWRAP/MT6351/regulator/MSDC ordering and stateful probe side effects.
- [Live vendor-to-mainline gap audit](../../experiments/2026-07-14-live-vendor-mainline-gap-audit/README.md)
  — corrected read-only runtime capture compared with the current Linux 7.1.3
  handoff and first-boot boundaries.
- [Upstream MT6797 coverage audit](../../experiments/2026-07-14-upstream-mt6797-coverage-audit/README.md)
  — family-driver reuse decisions for the MT6797 I2C and SPI controller blocks,
  backed by historical source and live bus topology; the SPI alias and
  disabled-node package passed build and binding validation.

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
- confirmed facts, each tied to a source or experiment;
- inferred or disputed claims, clearly labeled;
- register, bus, address, IRQ, GPIO, clock, regulator, memory-map, or protocol
  details when independently established;
- firmware and calibration boundaries;
- safety constraints and known destructive operations;
- open questions and the next discriminating experiment;
- links to associated experiment code, kernel patches, issues, and upstream
  discussions.

Use a compact fact table where it helps:

| Claim | Variant | Confidence | Evidence | Last verified |
| --- | --- | --- | --- | --- |
| Example claim | Wi-Fi + LTE | inferred | `experiments/...` | YYYY-MM-DD |

Confidence should be one of:

| Level | Meaning |
| --- | --- |
| `reported` | A secondary source states it; not independently checked |
| `inferred` | Evidence suggests it, but alternatives remain |
| `observed` | Directly measured or read from named hardware |
| `confirmed` | Reproduced with an explicit method and consistent evidence |

## Provenance rules

For every nontrivial claim, record enough information to locate and reassess
the evidence:

- exact device variant, with personal identifiers removed;
- evidence type and acquisition method;
- source URL, public document revision, kernel/vendor-tree path and commit, or
  experiment identifier;
- date observed and author/reporter;
- known uncertainty, conflicting evidence, and assumptions.

Vendor trees and proprietary documents may be cited as research inputs when
lawful, but do not copy their code or contents into this repository. Record
independently established facts and an appropriate source reference.

## Relationship to support status

Knowing that a component exists does not mean Linux supports it. Runtime and
upstream states remain in `docs/HARDWARE_SUPPORT.md`. A matrix state changes only
when a linked experiment or test report identifies the device, kernel revision,
patch-series revision, configuration, procedure, repetitions, and redacted
evidence.
