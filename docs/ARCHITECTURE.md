# Architecture and ownership

## Target architecture

The project aims to move the maintainable boundary as far down the boot stack as practical without making risky boot-firmware replacement a prerequisite for useful Linux support.

```text
Phase 1: safe enablement

MediaTek BootROM                 immutable silicon
  -> retained preloader / ATF    DRAM, secure-world, early platform init
  -> retained Planet LK          development shim and recovery choices
  -> upstream-derived Linux      generic MT6797 support + Gemini board DT
  -> standard initramfs/rootfs   distribution-neutral userspace

Phase 2: boot ownership

MediaTek BootROM
  -> retained or replaceable early firmware, evaluated separately
  -> maintained U-Boot/open LK chainloader
  -> standard Image/DTB/initramfs selection
  -> owner-controlled verification and recovery keys
```

Replacing the preloader or secure firmware is a separate stretch project. Linux hardware enablement must not depend on it.

## Ownership boundaries

| Layer | Desired owner | Project rule |
| --- | --- | --- |
| Linux generic drivers | Upstream subsystem | Extend generic drivers; no Gemini-only copies |
| MT6797 SoC description/support | Upstream Linux/DT maintainers | Keep reusable SoC work separate from board data |
| Gemini board Device Tree | Upstream Linux | Declarative board description with reviewed bindings |
| Temporary integration series | This repository | Pinned, reviewable, disposable after upstream merge |
| Initramfs/build tooling | This repository or distribution | Reproducible and non-destructive by default |
| Root filesystem | Distribution | No project-specific userspace requirement |
| Boot selection/recovery | Device owner | Preserve known-good path and owner-controlled artifacts |
| Modem/Wi-Fi firmware | Device firmware boundary | Retain only where unavoidable; expose standard kernel/userspace interfaces |

## Non-negotiable principles

### Upstream is the product

Every local kernel change needs:

- an upstream destination;
- a responsible issue;
- test evidence;
- a stated dependency chain;
- a deletion condition.

Branches may be rebased. GitHub issues and public mailing-list archives are the durable project record.

### No vendor-code laundering

Vendor source is evidence, not automatically acceptable implementation. Facts may be re-expressed; copied code must have clear provenance, compatible licensing, and a reason it cannot be replaced with an existing upstream abstraction.

### Generic before board-specific

Changes should layer cleanly:

```text
binding -> generic driver capability -> MT6797 SoC node -> Gemini board node
```

A Gemini quirk in a generic driver must be narrowly justified. Board policy does not belong in a reusable SoC driver.

### Chip identity before driver reuse

Driver reuse is a protocol decision, not a naming decision. For each vendor
component, compare the observed chip-ID/register map, bus transaction model,
power/reset/IRQ contract, and firmware ownership with the Linux 7.1.x driver
and binding:

| Evidence | Mainline action |
| --- | --- |
| Same silicon protocol and standard resources | Reuse the existing driver; add only SoC/board data, a binding extension, or a mount/power description. |
| Same family but an unrepresented register revision or board state machine | Extend the generic driver with narrowly scoped data and a reviewable compatibility record. |
| Different chip ID, register map, transport, or firmware ownership | Select an existing family driver or write a new chip/transport driver. Do not make the closest generic driver emulate the vendor ABI. |
| Identity or resources remain indirect | Keep the node disabled and record the discriminating probe; do not promote a compatible string to hardware support. |

The legacy Gemini sensor stack illustrates the rule: `bmi160_acc` and
`bmi160_gyro` are strong software-path evidence, but the vendor probes rewrite
both logical clients to `0x69` and the electrical ID was not directly captured.
The current record therefore favors one standard BMI160 IIO instance while
leaving LSM6DS3 or a genuinely different part free to select its own upstream
or new driver. See the [sensor/IIO recovery experiment](../experiments/2026-07-12-sensor-iio-recovery/README.md)
and [vendor IMU probe record](../experiments/2026-07-12-sensor-iio-recovery/results/vendor-imu-probe.txt).

### Standard subsystem contracts

Userspace should see ordinary Linux interfaces. Examples include DRM/KMS, evdev, power_supply, hwmon/thermal, MMC, USB role switch, ALSA ASoC, rfkill, and a documented modem transport usable by ModemManager or oFono.

### Firmware is isolated

Some embedded firmware will likely remain opaque. Acceptable firmware:

- runs on an isolated device or coprocessor;
- is loaded through a standard kernel mechanism where possible;
- does not require an out-of-tree proprietary kernel module;
- has documented version, source, checksum, and redistribution status outside Git when redistribution is not allowed.

### Reproducibility and evidence

Every boot artifact must be traceable to source revisions, configuration, toolchain, and packaging inputs. Hardware claims progress through the support-matrix states; compilation alone never means `working`.

### Safety is architectural

- Development targets a non-primary boot slot.
- Recovery remains independently bootable.
- Scripts reject ambiguous block-device and partition targets.
- NVRAM, GPT, preloader, and secure firmware are outside ordinary workflows.
- Logs are redacted before publication.

## Patch lifecycle

Temporary patches live under a directory named for their upstream base only when active work needs them. Each series should contain:

```text
patches/<upstream-base>/<topic>/
  README.md       purpose, dependencies, owner, upstream target, status
  series          ordered patch list
  0001-*.patch
```

Once merged upstream, remove the patches and replace them with the first containing release/commit in the issue and support matrix.

## Baseline and current implementation map

The subsystem audit baseline is Linux 7.1.3 with 72 non-comment entries and
patchset SHA-256
`c2d9eea95daa25dd8faddef4f9822e663db67d5d0946f06f0251cc52c92cf08c`.
The current working series adds patches 0072–0073 for MT6797 SPI reuse and
disabled SoC nodes, producing package `linux-7.1.3-gemini-c2feb465d6c6` with
patchset SHA-256
`c2feb465d6c6debf6f333516ce360cf8a1259da5dde631e828e7efac92ed33ae`; see the
[SPI patch validation](../experiments/2026-07-14-upstream-mt6797-coverage-audit/results/spi-mainline-patch-validation-c2feb-20260714.txt).
The following map is the implementation boundary for the baseline candidate; it is
deliberately grouped by dependency rather than treating every patch as a new
driver.

| Series range | Area | Reuse decision | Current runtime boundary | Next evidence gate |
| --- | --- | --- | --- | --- |
| 0001–0006 | Infracfg reset, MT6797 pinctrl, EINT | Extend generic reset/pinctrl/EINT data; no vendor ABI copied | Pinctrl is built in; UART0 depends on its pin state; extra EINT consumers remain disabled | Verify GPIO polarity, IRQ routing, debounce, and wake on hardware |
| 0007–0015 | PWRAP, MT6351 MFD/regulator/RTC | Reuse upstream MTK PWRAP/MT6397 framework code; the MT6351 MFD/regulator/RTC implementation is a local 7.1.3 addition with MT6797 pwrap and rail data | Built-in and implicitly enabled; probe writes pwrap/IRQ state and can affect PMIC ownership | Capture before/after pwrap, PMIC interrupt masks, IDs, and rail selectors during recovery-backed boot |
| 0016–0020 | MSDC/eMMC and Gemini board description | Reuse `mtk-sd` with MT6797 tuning data and conservative board DT | MSDC0 is built in and enabled at 25 MHz legacy timing; microSD stays disabled | Read-only eMMC probe/I/O, then controlled timing escalation |
| 0021–0025 | CAM/MJC clocks, M4U/SMI | Reuse generic CCF/IOMMU/SMI with new MT6797 data; add only missing providers | Providers are built in or available, but multimedia DMA consumers remain disabled | Enable one verified DMA consumer after clock, larb, port, reset, and fault contracts are captured |
| 0026–0044 | GCE, mutex, MMSYS, DRM, DSI, PHY, panel, display PWM | Reuse generic multimedia cores with MT6797 platform data and a board panel descriptor | Display objects are module-only or disabled; panel graph and power sequence are not runtime-proven | First-light test only after exact panel bias/reset/backlight/graph evidence |
| 0045–0046 | AFE resources and thermal/DVFSP resources | Board DT description only; no consumer is enabled | AFE, thermal, and AUXADC nodes remain disabled | Resolve machine-card/calibration contracts and preserve fail-closed thermal behavior |
| 0047–0051 | MFG power domains/clocks, 52 MHz preclock, RT5735 VGPU | Reuse SCPSYS/CCF/regulator abstractions with MT6797 SRAM and ownership data | GPU/MFG/RT5735 consumers remain disabled; CPU clock ownership is separately secure/semaphore-mediated | Prove power/reset/OPP/rail ownership before Panfrost or DVFS |
| 0052–0057a | BMI160, watchdog, AW9523, FAN49101, FUSB301, thermal, LK calibration | Reuse standard BMI160/watchdog/AW9523 foundations; new chip driver/data only where register contract differs; NVMEM provider is a narrow LK ABI adapter | Watchdog is implicitly enabled; other candidates are disabled or module-only; calibration provider is read-only/root-only | Hardware ID/readback with explicit recovery; never promote a compatible string from indirect evidence |
| 0058–0065 | Panfrost, DPI, PMIC parent fix, SCPSYS/AFE bindings, DVFSP deferral | Reuse Panfrost/DRM/PMIC/SCPSYS/ASoC frameworks; keep undocumented DVFSP out | Panfrost/DPI/AFE consumers remain disabled or module-only | Validate each consumer’s clocks, resets, IOMMU, supplies, and firmware boundary independently |
| 0066–0071 | USB T-PHY/MTU3/xHCI/MUSB and MSDC pinmux policy | Reuse generic USB cores with MT6797 glue and source-derived split windows; use pinmux-only MSDC state | USB nodes remain disabled; built-in code is package capability, not probe evidence | Gadget-only console first, then role/VBUS and PHY tests with external recovery |

The [current driver-coverage audit](../experiments/2026-07-13-driver-coverage-audit/results/driver-coverage-current-77-package-20260714.txt), [first-boot dependency audit](../experiments/2026-07-14-first-boot-probe-audit/results/first-boot-probe-audit-current-77-package-20260714.txt), [module-closure audit](../experiments/2026-07-14-mainline-module-closure-audit/results/module-closure-current-72-20260714.txt), and [current 74-patch package validation](../experiments/2026-07-13-kernel-integration/results/mainline-74-patch-current-20260714.txt) provide the corresponding hashes and linked-in/module-only evidence. The 72-patch subsystem records remain valid content audits because patches 0072–0073 only add disabled SPI support. This table is a design map, not a claim that any disabled or module-only path works on hardware.

## Decision records

Material decisions belong in issues labeled `type: decision`. A decision must state context, options considered, safety impact, upstream impact, and reversal conditions. This prevents repository-local convention from silently becoming a new downstream ABI.
