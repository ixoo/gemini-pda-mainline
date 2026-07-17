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
The current working series extends through patch 0078. Patches 0072–0076 add
disabled SPI and input candidates; the latest validated package for that
boundary is `linux-7.1.3-gemini-6116c9e7da3f` with patchset SHA-256
`6116c9e7da3fc2f56612029236a3bcd370c61f91b3c0951dd4e2c1915537f55e`.
Patches 0077–0078 add an opt-in T-PHY B-device-session capability and disabled
Gemini MTU3 peripheral wiring for the separate USB diagnostic. The exact USB
image was tested from non-primary `boot2` and did not enumerate. A follow-up
that retained its kernel and DTB while changing only initramfs `/init` reached
a delayed off-like state after an owner-estimated 5–10 seconds instead of
remaining dark and steady. This is strong indirect evidence for external
`/init` execution, but it is not a stopwatch measurement, repeat, or surviving
log and does not establish that the USB driver probed or works. A subsequent
screen-marker candidate retains the same `Image.gz`, adds only a validated
simplefb description, and performs one bounded framebuffer fill. It was
written, flushed, fully read back from `boot2`, and attempted once; the display
was black and showed none of the expected bands. This fails the positive test
but does not distinguish kernel entry, simplefb, the write, or LK scanout
retention. Candidate F keeps that exact Image and initramfs while adding only a
path-resolved `CLK_INFRA_DISP_PWM` simplefb reference. Its first attended boot
showed sideways console text for about one second before black. This is the
first positive visual Linux 7.1.3 signal and strongly supports simplefb/fbcon
output, although the unread text does not independently prove `/init`.
Candidate G keeps F's exact kernel segment and DTB, removes all raw framebuffer
access through an initramfs-only delta, and holds a distinctive tty0 banner.
Its two builds are byte-identical and its logical-`boot2` write has a matching
full readback. Its attended boot reproduced sideways scrolling for 1–2 seconds
before black with the backlight apparently off. Candidate H preserves G's exact
kernel and initramfs and appends only `CLK_TOP_MUX_MM` to the simplefb clocks
property. In one attended series, two attempts visibly progressed farther and
the owner approximately recognized H's initramfs-only marker before the screen
and backlight went off; later attempts did not reproduce the visible progress.
This strongly attributes those visible attempts to external `/init`, but does
not establish repeatability or stable display retention. Candidate I preserves
H's exact kernel and DTB and exact initramfs tree except `/init`, then emits one
tty0 line per second through `T+60` before a silent static hold. It was built,
exported, synchronized, and fully read back from logical `boot2`, but the
reported intended selection went directly to black with no I marker, counter,
or other text. Its selection, `/init`, active-refresh interval, and static hold
are therefore unestablished; the timing hypothesis remains untested.

Candidate J is the next broad early-handoff control. It rebuilds the kernel to
append `clk_ignore_unused` to the forced `CONFIG_CMDLINE`, while keeping exact
I's DTB, initramfs, and Android header command line. A header-only draft was
rejected because `CONFIG_CMDLINE_FORCE=y` makes that loader-provided addition a
runtime no-op. An isolated clean rebuild reproduced the resolved config,
kernel payload, `System.map`, all 119 DTBs, and raw boot image byte-for-byte;
only timestamp-bearing build provenance and its checksum manifest differ. The
raw J image SHA-256 is
`6d5bad08c2f93eba7fbd66ea5c54de2437f81e44832426a97d4d65d550c659f4`;
it is synchronized to logical `boot2`, and the full 16 MiB target/readback
matches SHA-256
`465e4c747138e12191d38fd6b4cde68cd0b9a19f918030dea05c9b8dbdd4d3fc`.
The write did not reboot the device and runtime remains pending. This
deliberately broad diagnostic does not enable clocks that are already off,
prevent explicit clock disables, or retain regulators or power domains, and it
is not a normal boot policy. The exact kernel compiles fbcon rotation out, so
rotation remains a separate later configuration test.
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
| 0072–0076 | SPI aliases/nodes, hall input, NT36772 boundary, keyboard polarity | Reuse generic SPI and input frameworks where the captured protocol matches; keep every new board consumer disabled | The 77-patch package validates, but these additions have no current-mainline runtime result | Test one bounded consumer at a time with exact identity and recovery evidence |
| 0077–0078 | MTU3 peripheral diagnostic | Extend the existing MediaTek T-PHY with an opt-in forced B-device session and describe Gemini peripheral wiring while leaving base nodes disabled | The exact USB image was fully read back and runtime-tested from `boot2`; two bounded host checks found no USB child. A ramdisk-only timed-reboot follow-up produced strong indirect `/init` evidence but no automatic restart, which does not promote USB support. Candidate E's marker remained black. Candidate F's sole simplefb clock-reference delta then produced about one second of visible sideways fbcon text before black, strongly supporting kernel/simplefb/fbcon execution. Candidate G removed only the raw framebuffer overwrite and reproduced sideways scrolling for 1–2 seconds before black with the backlight apparently off. Candidate H appended only the MM-root clock reference; two attempts visibly progressed farther and approximately exposed its initramfs marker before the screen and backlight went off, while later attempts did not reproduce the progress. Candidate I is an exact-H initramfs-only timing derivative, fully read back from `boot2`; the reported intended selection was directly black with no I marker or counter, so its timing hypothesis remains untested. Candidate J rebuilds I's kernel with `clk_ignore_unused` in forced `CONFIG_CMDLINE`, keeps exact I's DTB/initramfs/header cmdline, and is reproducibly built, synchronized, flushed, and fully read back from logical `boot2`; runtime is pending | Run J's bounded attended no-marker/marker procedure. Treat it only as a broad clock-cleanup discriminator: it neither enables already-off clocks nor covers explicit disables, regulators, or power domains. Rotate only after retention is stable. Resolve PSCI versus TOPRGU independently; prove USB host enumeration before ping and the TCP marker shell. Infer nothing about host mode, VBUS, Type-C policy, or charging |

The [current driver-coverage audit](../experiments/2026-07-13-driver-coverage-audit/results/driver-coverage-current-77-package-20260714.txt), [first-boot dependency audit](../experiments/2026-07-14-first-boot-probe-audit/results/first-boot-probe-audit-current-77-package-20260714.txt), [module-closure audit](../experiments/2026-07-14-mainline-module-closure-audit/results/module-closure-current-72-20260714.txt), [77-patch package validation](../experiments/2026-07-12-input-backlight-recovery/results/mainline-display-input-current-77-package-20260714.txt), [USB diagnostic experiment](../experiments/2026-07-16-usb-gadget-diagnostic/README.md), [timed-reboot follow-up](../experiments/2026-07-16-timed-reboot-diagnostic/README.md), [screen-marker follow-up](../experiments/2026-07-16-screen-marker-diagnostic/README.md), [clock-retention result](../experiments/2026-07-16-screen-clock-retention-diagnostic/README.md), [fbcon-text follow-up](../experiments/2026-07-16-fbcon-text-diagnostic/README.md), [MM-root-retention follow-up](../experiments/2026-07-16-simplefb-mm-root-retention/README.md), [fbcon refresh-timing follow-up](../experiments/2026-07-16-fbcon-refresh-timing-diagnostic/README.md), and [broad unused-clock diagnostic](../experiments/2026-07-17-clk-ignore-unused-diagnostic/README.md) provide the corresponding evidence boundaries. The older subsystem records remain content audits where later patches do not touch their inputs. This table is a design map, not a claim that any disabled, module-only, or diagnostic path works on hardware.
Candidate J's partition operation is separately recorded in its
[full write/readback result](../experiments/2026-07-17-clk-ignore-unused-diagnostic/results/boot2-write-candidate-j-20260717.txt).

## Decision records

Material decisions belong in issues labeled `type: decision`. A decision must state context, options considered, safety impact, upstream impact, and reversal conditions. This prevents repository-local convention from silently becoming a new downstream ABI.
