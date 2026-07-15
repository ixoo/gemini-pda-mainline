# Experiments and reverse engineering

This directory contains reproducible investigations of the Gemini PDA and its
software-visible hardware. The write-up, probe code, and sanitized evidence for
an investigation stay together so another contributor can repeat or challenge
the result.

## Index

- [2026-07-11 Gemian hardware inventory](2026-07-11-gemian-hardware-inventory/README.md)
  — read-only whole-device discovery baseline and reusable collector.
- [2026-07-11 Gemian firmware inventory](2026-07-11-gemian-firmware-inventory/README.md)
  — private vendor-firmware capture, sanitized hashes, and load evidence.
- [2026-07-11 Gemian hardware-userspace inventory](2026-07-11-gemian-hardware-userspace-inventory/README.md)
  — Android HAL, vendor library/daemon, and native compatibility-boundary map.
- [2026-07-11 MT6797 device-tree recovery](2026-07-11-mt6797-device-tree-recovery/README.md)
  — decoded live resources for mainline DTS and driver data.
- [2026-07-11 vendor userspace to kernel ABI](2026-07-11-vendor-kernel-abi/README.md)
  — static interface extraction and Linux 7.1.3 replacement-gap analysis.
- [2026-07-11 Gemini panel recovery](2026-07-11-gemini-panel-recovery/README.md)
  — runtime panel selection, DSI mode, command, bias, reset, false-DT-lead,
    and the descriptor-based mainline NT36672E framework recovery.
- [2026-07-11 MT6351 PMIC recovery](2026-07-11-mt6351-pmic-recovery/README.md)
  — direct PMIC identity, pwrap/reset clocks, regulators, RTC, power keys, and
  the missing MT6797 EINT prerequisite.
- [2026-07-12 MT6797 MSDC recovery](2026-07-12-mt6797-msdc-recovery/README.md)
  — storage-controller register contract, live eMMC/card-slot state, and a
  conservative Linux 7.1 bring-up plan.
- [2026-07-12 MT6797 M4U and SMI recovery](2026-07-12-mt6797-m4u-smi-recovery/README.md)
  — multimedia IOMMU topology, SMI larbs, fault IDs, ports, clocks, and
  power-domain recovery for Linux 7.1.
- [2026-07-12 MT6797 CMDQ/GCE recovery](2026-07-12-mt6797-cmdq-gce-recovery/README.md)
  — live mailbox execution, thread/address format, subsystem selectors,
  hardware events, clock gating, and normal/secure IRQ separation.
- [2026-07-12 MT6797 display-mutex recovery](2026-07-12-mt6797-display-mutex-recovery/README.md)
  — module bits, SOF/EOF encoding, register layout, live IRQ/clock evidence,
  DEVAPC boundary, MM power domain, and GCE client contract.
- [2026-07-12 MT6797 MMSYS routing recovery](2026-07-12-mt6797-mmsys-routing-recovery/README.md)
  — complete mux graph, active OVL/RDMA/UFOE/DSI route, reset banks, and GCE
  client contract.
- [2026-07-12 MT6797 DRM component recovery](2026-07-12-mt6797-drm-component-recovery/README.md)
  — OVL, fixed-function PQ, RDMA, UFOE, DSI, and MIPI-PHY register-generation,
  clock, interrupt, and safe first-light contract recovery.
- [2026-07-12 input and backlight recovery](2026-07-12-input-backlight-recovery/README.md)
  — live Novatek touchscreen/EINT, AW9523 keyboard matrix, and MT6797 display
  PWM contracts compared with Linux 7.1.3 reuse boundaries, plus a disabled
  standard AW9523 matrix-keypad candidate and vendor-ELF/source parity for the
  eleven-entry NT36xxx trim table.
- [2026-07-12 sensor and IIO recovery](2026-07-12-sensor-iio-recovery/README.md)
  — live I2C1 sensor bindings, vendor virtual-sensor boundary, and Linux 7.1.3
  reuse versus new-driver decisions.
- [2026-07-12 USB and Type-C recovery](2026-07-12-usb-typec-recovery/README.md)
  — live USB1/USB3 windows, MT6797 PHY clocks and tuning boundary, and the
  generic FUSB301 controller candidate plus the unresolved board/role contract.
- [2026-07-12 connectivity/WMT recovery](2026-07-12-connectivity-wmt-recovery/README.md)
  — MT6797 CONSYS/WMT identity, Wi-Fi/BTIF/GNSS/FM resources, firmware hashes,
  and the standard Linux 7.1 reuse boundary.
- [2026-07-12 audio AFE recovery](2026-07-12-audio-afe-recovery/README.md)
  — live ASoC endpoints, MT6797 AFE/MT6351 codec graph, and the existing
  Linux 7.1.3 reuse boundary.
- [2026-07-12 CPU DVFS, thermal, and suspend recovery](2026-07-12-cpufreq-thermal-suspend-recovery/README.md)
  — live cpufreq policies, vendor OPP diagnostics, thermal-zone sentinels,
  cpuidle/PSCI state evidence, and the missing MT6797 mainline contracts.
- [2026-07-13 CPU/PSCI/timer recovery](2026-07-13-cpu-psci-timer-recovery/README.md)
  — live ten-CPU DT topology, PSCI 0.2 SMC IDs, architectural timer PPIs,
  clocksource/clockevent selection, and the generic Linux reuse boundary.
- [2026-07-13 MT6797 thermal recovery](2026-07-13-mt6797-thermal-recovery/README.md)
  — live disabled thermal zones, six-bank/five-sensor mapping, efuse
  calibration contract, and the new MT6797 thermal-driver boundary.
- [2026-07-12 MT6797 GPU/Panfrost recovery](2026-07-12-mt6797-gpu-panfrost-recovery/README.md)
  — live Mali-T88x identity, vendor GPU DVFS/clock contracts, and the
  Panfrost-versus-platform integration boundary.
- [2026-07-12 RT5735 VGPU recovery](2026-07-12-rt5735-vgpu-recovery/README.md)
  — external GPU-buck identity, register/voltage contract, and the dedicated
  regulator-driver boundary.
- [2026-07-12 boot contract recovery](2026-07-12-boot-contract-recovery/README.md)
  — Android boot-image layout, retained LK chosen properties, root partition,
  and the reversible mainline boot-artifact boundary.
- [2026-07-12 charger and fuel-gauge recovery](2026-07-12-charger-power-recovery/README.md)
  — live BQ25890/FAN49101 ownership, the inactive RT9466 alternative, and the
  standard power-supply versus new-driver boundary, including the bounded
  FAN49101 register contract and disabled-only mainline driver candidate.
- [2026-07-12 MT6797 watchdog recovery](2026-07-12-mt6797-watchdog-recovery/README.md)
  — TOPRGU register/protocol reuse, the Gemini bark IRQ, and the vendor WDK
  side-channel boundary.
- [2026-07-12 MT6797 clock/power/reset recovery](2026-07-12-mt6797-clock-power-reset-recovery/README.md)
  — live clock summary, SCPSYS resource ordering, MFG/core SRAM handshake,
  and the generic-provider extension boundary.
- [2026-07-12 MT6797 EINT and pinctrl recovery](2026-07-12-mt6797-eint-recovery/README.md)
  — vendor-versus-live EINT contract, recovered GPIO map, virtual PMIC input,
  and the generic Linux reuse/new-data boundary.
- [2026-07-12 hall/lid/switch recovery](2026-07-12-hall-lid-switch-recovery/README.md)
  — GPIO66/EINT5 hall input, GPIO93/EINT16 toggle input, vendor polarity and
  debounce behavior, and the standard `gpio-keys` replacement boundary.
- [2026-07-12 kernel configuration gap audit](2026-07-12-kernel-config-gap-audit/README.md)
  — vendor 3.18 versus prepared Linux 7.1.3 options, modern symbol mappings,
  and the distinction between missing drivers and private policy switches.
- [2026-07-13 driver coverage audit](2026-07-13-driver-coverage-audit/README.md)
  — linked-in/module-only driver ownership and live vendor-driver comparison
  for the packaged Linux 7.1.3 candidate.
- [2026-07-14 first-boot probe audit](2026-07-14-first-boot-probe-audit/README.md)
  — static PWRAP/MT6351/regulator/MSDC probe ordering and write-side-effect
  boundary for the conservative first boot.
- [2026-07-14 mainline module closure audit](2026-07-14-mainline-module-closure-audit/README.md)
  — built-in versus optional-module availability and exact packaged dependency
  closures for the current 7.1.3 kernel artifact.
- [2026-07-14 live vendor-to-mainline gap audit](2026-07-14-live-vendor-mainline-gap-audit/README.md)
  — read-only comparison of the live Gemian vendor contracts with the current
  Linux 7.1.3 handoff and first-boot boundaries.
- [2026-07-14 upstream MT6797 coverage audit](2026-07-14-upstream-mt6797-coverage-audit/README.md)
  — source-level reuse/new-driver census, MT6797 I2C fallback validation, and
  the SPI controller boundary through the existing `mt6765_compat` profile;
  patches 0072–0073 and their validated disabled-node package are recorded in
  the SPI patch-validation result.
- [2026-07-13 camera recovery](2026-07-13-camera-recovery/README.md)
  — runtime SP5509 camera identity, bounded vendor-ELF chip-ID/I2C recovery,
  MT6797 SENINF/ISP resource boundary, and the new-sensor-driver versus
  existing-mainline-driver decision.
- [2026-07-13 external-display recovery](2026-07-13-external-display-recovery/README.md)
  — unbound SII9022/EDID candidates, SII9024A-named vendor wiring, and the
  Linux 7.1.3 `sii902x` bridge reuse boundary.
- [2026-07-13 memory carve-out recovery](2026-07-13-memory-carveout-recovery/README.md)
  — discontiguous DRAM, fixed firmware reservations, dynamic CONSYS/SCP-share/
  SPM ownership, and the Linux 7.1.3 DT boundary.
- [2026-07-13 modem/CCCI recovery](2026-07-13-modem-ccci-recovery/README.md)
  — live MD1 and MD3/C2K CCCI/CLDMA topology, shared-memory/EMI ownership,
  and the new MT6797 transport versus reusable WWAN/TTY boundary.
- [2026-07-13 UART/console recovery](2026-07-13-uart-console-recovery/README.md)
  — live `ttyMT0`–`ttyMT3`, vendor AP-DMA/console behavior, Linux 8250 reuse,
  and the LK command-line naming boundary.
- [2026-07-13 kernel integration](2026-07-13-kernel-integration/README.md)
  — reproducible Linux 7.1.3 preparation, configuration, 57-patch compilation,
  artifact packaging, and checksum/provenance verification.

## Layout

Create a directory named with the start date and a short subject:

```text
experiments/2026-07-11-uart-identification/
  README.md
  scripts/       collection, decoding, and analysis helpers
  src/           purpose-built probe or test source
  fixtures/      small redistributable inputs needed for tests
  results/       small sanitized logs, tables, or summaries
```

Copy `experiments/TEMPLATE.md` to the new directory as `README.md`. Omit unused
subdirectories. Code must state its dependencies and default to read-only or
dry-run behavior. A command that can modify hardware must require an explicit
target and opt-in flag.

## Evidence policy

- Keep raw private captures outside Git. Commit only the smallest sanitized
  evidence needed to support the result.
- Redact serial numbers, IMEI values, identifying MAC addresses, keys,
  credentials, calibration blobs, and user data.
- Do not commit firmware, partition images, NVRAM, proprietary source or
  documents, or artifacts without verified redistribution rights.
- Hash externally retained evidence when its identity matters, but do not
  publish a hash if it could identify a person or device.
- Record failures, negative results, and ambiguity. They prevent repeated unsafe
  work and are valid outcomes.

When an experiment establishes a durable fact, summarize it in
`docs/hardware/` and link back to the experiment. When it changes runtime support,
update `docs/HARDWARE_SUPPORT.md` with the exact evidence. When it produces a
kernel change, export the logical commit into `patches/` and link all three.
