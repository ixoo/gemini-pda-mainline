# Hardware support matrix

This matrix separates what runs on real hardware from what exists upstream. A compile-only result is not runtime support, and a local hardware result is not upstream support.

## State definitions

Runtime state:

| State | Meaning |
| --- | --- |
| `unknown` | No reproducible current-mainline result recorded |
| `enumerates` | Driver probes or device is visible, but function is not established |
| `partial` | Some intended behavior works with documented gaps |
| `working` | Acceptance test passes on named hardware and kernel revision |
| `stable` | Released upstream code passes a documented regression protocol |
| `regressed` | A previously passing protocol now fails |
| `not-applicable` | Hardware is absent on this variant |

Upstream state:

| State | Meaning |
| --- | --- |
| `missing` | Required support is not known upstream |
| `local` | A temporary local change exists |
| `RFC` | A public request-for-comments series exists |
| `submitted` | Patch series is under formal upstream review |
| `accepted` | Maintainer tree contains the change |
| `released` | A tagged upstream kernel contains the change |

Firmware boundary:

| State | Meaning |
| --- | --- |
| `none` | No separately loaded firmware known |
| `required-free` | Redistributable firmware required |
| `required-nonfree` | Device firmware is required but not freely redistributable |
| `unknown` | Boundary or license is not established |

## Initial matrix

All runtime states below are intentionally conservative. Historical results are listed as evidence to reproduce, not promoted to `working`.

| Subsystem | Component / candidate | Variants | Bus or SoC block | Mainline basis/dependency | Runtime | Upstream | Firmware | Evidence / next gate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Boot | Planet LK development path | all | boot chain | Android boot-image/DT contract must be characterized | `unknown` | `missing` | `required-nonfree` | Preserve recovery; compare DT and command line before/after LK |
| CPU topology | 8x Cortex-A53 + 2x Cortex-A72 | all | MT6797 | CPUs and PSCI described in `mt6797.dtsi` | `unknown` | `released` | `unknown` | Enumerate all CPUs and stress repeated boots |
| Interrupts/timers | GICv3, arch timer | all | MT6797 | Described in `mt6797.dtsi` | `unknown` | `released` | `unknown` | Capture current-mainline timer/GIC behavior |
| RAM | LPDDR and reserved regions | all | EMI / firmware carve-outs | Board memory and carve-outs required | `unknown` | `missing` | `unknown` | Derive variant map; verify under memory stress |
| Clocks/resets | MT6797 clock tree | all | topckgen/infracfg/apmixed | Partial upstream support | `unknown` | `released` | `none` | Audit critical clocks; historical work reports corruption risk |
| Power domains | MT6797 SCPSYS | all | SCPSYS | Partial upstream support | `unknown` | `released` | `none` | Validate domain map and safe sequencing |
| UART | Debug console | all | UART0 candidate | Generic MediaTek UART plus SoC nodes | `unknown` | `released` | `none` | Reproduce historical UART/BusyBox boot on current mainline |
| Watchdog | MT6797 watchdog | all | WDT | SoC node and generic driver exist | `unknown` | `released` | `none` | Validate timeout, reboot, and disable policy |
| Pinctrl/GPIO | MT6797 pin controller | all | pinctrl | SoC pinctrl support exists | `unknown` | `released` | `none` | Produce board pin inventory with provenance |
| I2C | MT6797 controllers | all | I2C0-9 | SoC nodes and generic driver exist | `unknown` | `released` | `none` | Enable only buses with verified board wiring |
| PMIC/regulators | MT6351 reported candidate | all | PMIC wrapper | Identity and upstream dependency audit required | `unknown` | `missing` | `unknown` | Confirm silicon, rails, consumers, and voltages |
| RTC | PMIC RTC candidate | all | PMIC | Depends on verified PMIC support | `unknown` | `missing` | `unknown` | Set/read/alarm/power-cycle test |
| Charger/fuel gauge | Reported charger candidates | all | I2C/PMIC | Component identity disputed/unverified | `unknown` | `missing` | `unknown` | Confirm parts and safe limits before enabling charge control |
| eMMC | Internal storage | all | MSDC | MT6797 storage nodes/support incomplete | `unknown` | `missing` | `none` | Read-only identification before bounded write tests |
| microSD | Removable storage | all | MSDC | Board wiring and controller dependency required | `unknown` | `missing` | `none` | Detect, I/O, remove/reinsert, suspend test |
| Keyboard | AW9523B reported candidate | all | I2C GPIO/pinctrl | Generic AW9523 driver exists; matrix integration required | `unknown` | `missing` | `none` | Verify address, IRQ, matrix, modifiers, LEDs, and wake |
| Lid/power keys | GPIO/PMIC candidates | all | GPIO/PMIC | Board description required | `unknown` | `missing` | `none` | Identify debounce and wake behavior |
| Display pipeline | MT6797 MMSYS/SMI/IOMMU/CMDQ/DSI | all | multimedia | Upstream has clock/syscon skeleton only | `unknown` | `missing` | `none` | Map complete KMS dependency chain |
| Panel/backlight | Component reports conflict | all | dual MIPI-DSI candidate | Verified compatible, binding, and panel driver required | `unknown` | `missing` | `unknown` | Resolve panel identity per variant before code |
| Touchscreen | Unknown | all | I2C/SPI candidate | Identity, binding, and driver required | `unknown` | `missing` | `unknown` | Record bus/address/IRQ/reset and multitouch protocol |
| USB-C ports | Device/host/role switching | all | USB/PHY/Type-C | MT6797 USB/PHY plus board wiring required | `unknown` | `missing` | `none` | Inventory each port independently; start with gadget serial |
| GPU | Mali-T880 candidate | all | MFG/IOMMU | Panfrost supports the GPU family; platform integration required | `unknown` | `missing` | `unknown` | Validate clocks, power, resets, IOMMU, and firmware needs |
| Audio | MT6351 path reported | all | ASoC/PMIC/I2S | Codec, machine driver, routing, and jack detection audit required | `unknown` | `missing` | `unknown` | Confirm components and DAPM routes |
| Wi-Fi | Unknown combo chip | all | connectivity subsystem | Component and maintainable host interface unknown | `unknown` | `missing` | `unknown` | Identify chip, bus, firmware, calibration boundary |
| Bluetooth | Unknown combo chip | all | connectivity subsystem | Component and transport unknown | `unknown` | `missing` | `unknown` | Identify UART/bus and firmware boundary |
| GNSS | Unknown | cellular variants | modem/connectivity candidate | Architecture unknown | `unknown` | `missing` | `unknown` | Determine whether GNSS is modem-owned |
| Sensors | Multiple reported candidates | varies | I2C | Validate each part/variant against generic IIO/input drivers | `unknown` | `missing` | `unknown` | Variant-aware bus scan and provenance inventory |
| Cellular modem | MediaTek baseband | LTE variants | shared memory/CCCI candidate | Mainline transport absent | `unknown` | `missing` | `required-nonfree` | Architecture research only; non-blocking stretch goal |
| Cameras | Unknown sensors | varies | camera/ISP | ISP and sensor support unestablished | `unknown` | `missing` | `unknown` | Deferred until core platform is stable |
| External display | Unknown bridge/path | varies | display/USB candidate | Architecture unverified | `unknown` | `missing` | `unknown` | Deferred; identify physical path first |
| Suspend/wake | System suspend | all | cross-subsystem | Depends on clocks, PMIC, IRQs, and wake sources | `unknown` | `missing` | `unknown` | Repeated suspend cycles with power measurements |

## Updating the matrix

Every status change must cite a tracking issue containing:

- exact device variant;
- kernel commit and patch-series revision;
- configuration and toolchain;
- test protocol and repeat count;
- redacted log or measurement;
- upstream series/commit when the upstream state changes.

Use `stable` only when the result is present in a released upstream kernel and passes the project's regression protocol.
