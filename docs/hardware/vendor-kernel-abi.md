# Vendor kernel ABI and Linux 7.1.3 gaps

This document turns the working Gemian/Android binary stack into requirements
for upstream-oriented Gemini support. The goal is not to reproduce MediaTek's
private userspace ABI. The goal is to identify the hardware functions and
replace each boundary with standard Linux subsystems.

## Evidence and confidence

Evidence comes from the 2026-07-11 physical-device inventory, extracted system
firmware and userspace, static ELF analysis, Gemini-specific LXC/udev rules, and
the pinned Linux 7.1.3 source tree. See the
[ABI experiment](../../experiments/2026-07-11-vendor-kernel-abi/README.md).
The sanitized inventory-to-mainline mapping is in the
[ABI design record](../../experiments/2026-07-11-vendor-kernel-abi/results/vendor-abi-mainline-design.md),
and can be regenerated with the experiment's
[gap analyzer](../../experiments/2026-07-11-vendor-kernel-abi/scripts/analyze-mainline-abi.sh).
The dated [coverage](../../experiments/2026-07-14-upstream-mt6797-coverage-audit/README.md),
[configuration](../../experiments/2026-07-12-kernel-config-gap-audit/README.md),
and [ownership](../../experiments/2026-07-14-live-kernel-ownership-audit/README.md)
audits remain evidence inputs, not current package authority.
The corrected 2026-07-14 vendor runtime capture is compared with the static
mainline handoff in the [live vendor-to-mainline gap audit](../../experiments/2026-07-14-live-vendor-mainline-gap-audit/README.md);
its result is a comparison aid, not a mainline boot claim.
The MT6797 I2C controller reuse decision is recorded in the [focused I2C
audit](../../experiments/2026-07-14-upstream-mt6797-coverage-audit/results/i2c-mt6797-controller-reuse-20260714.txt):
the historical and current controller paths both use the `mt6577` register and
quirk profile, while the current ten-node Gemini DTS supplies the required
`mt6797-i2c` plus `mt6577-i2c` fallback and optional arbitration clocks.

I2C6 has an additional ownership and transfer-format ABI. Live Gemian marks it
`appm_used`; exact binary analysis identifies `SEMA_I2C_DRV` as a DVFSP
pause-source protocol rather than a hardware semaphore. Normal DVFSP holds a
persistent I2C_APPM clock reference, each I2C6 transaction adds a temporary
reference, and enabled A72 iDVFS can add another. Vendor stop is reversible
through retained restart paths. ATF remains a keyed CSPM and secure-semaphore
writer, and an SCP-local alias has not been excluded, so Linux must not assume
global ownership. The local handoff implementation can preserve I2C5's shared
AP-DMA baseline while leaving childless I2C6 serviceable.

The proven I2C6 data path is deliberately narrow: the native packed/FIFO path
completes the exact one-byte-pointer plus one-byte-read shape. Direct reads
at `0x68` and `0x69` establish a stable legacy
DA9213/DA9214/DA9215-compatible board tuple on the named unit, not a unique
silicon identity. Arbitrary messages, register-data writes, error recovery,
resume, regulator-provider behavior, and A72 power remain unproved. The
upstream DA9211/A-family probe is not a match for this legacy protocol; use a
dedicated legacy-family driver/binding or a genuinely separated variant with
zero probe-time writes and fail-closed fixed reads. The complete current
boundary is in the [DA921x/I2C6/A72 contract](da921x-i2c6-a72.md), while the
authoritative sequence is in the [roadmap](../ROADMAP.md). Detailed evidence
remains in
the [DVFSP/I2C6 arbitration recovery](../../experiments/2026-07-24-mt6797-dvfsp-i2c6-arbitration/README.md)
and the [exact board-contract runtime result](../../experiments/2026-07-28-da9214-gauss/results/runtime-candidate-gauss-attempt-1-20260728.txt).

Interface names embedded in a binary prove that the code was built with that
path, not that the path was exercised in the captured boot. An interface is
called `live-correlated` only when the earlier physical inventory also observed
the related device or driver.

## Existing Linux 7.1.3 foundation

The upstream `mt6797.dtsi` provides:

- ten CPU nodes (eight Cortex-A53 and two Cortex-A72), PSCI, timer, and GICv3;
- the 26 MHz oscillator, top clock generator, infrastructure clocks, and
  application PLL block;
- MT6797 pinctrl/GPIO and initial UART/I2C pin groups;
- SCPSYS power domains and watchdog;
- system interrupt routing;
- four UARTs and all ten I2C controllers, disabled for board selection;
- clock/syscon nodes for MMSYS, IMGSYS, VDECSYS, and VENCSYS.

Linux 7.1.3 also contains MT6797 clock drivers, pinctrl, legacy SCPSYS data,
PMIC-wrapper support, an MT6351 codec, MT6797 AFE/DAI and MT6351 machine driver,
and generic drivers that may cover some observed peripherals.

That PMIC statement has an important boundary: the wrapper driver recognizes
both `mediatek,mt6797-pwrap` and an `mediatek,mt6351` child and supplies the
regmap used by the audio codec, but unpatched Linux 7.1.3 has no MT6351
regulator, RTC, power-key, charger, IRQ-domain, or general MFD child support.
The PMIC is now directly confirmed as MT6351 E2. The local series supplies the
otherwise-absent parent EINT, mandatory infracfg reset provider, pwrap SoC
node, four-bank IRQ domain, MFD cells, and enough regulator data for the
VEMC/VIO18 rails used by the partial eMMC path. General regulator coverage,
RTC, power-key, charger, and power-off behavior remain incomplete.
See the [MT6351 recovery experiment](../../experiments/2026-07-11-mt6351-pmic-recovery/README.md).
The corrected live binding capture adds a probe-model distinction: the vendor
`1000d000.pwrap` platform device is unbound, while standalone `mt-pmic` and
`mt-rtc` devices are bound and all regulator class devices link to `mt-pmic`.
This does not contradict the confirmed MT6351 identity; it shows that the
vendor stack reaches the PMIC through a private/global wrapper path rather than
the upstream parent-PWRAP/child-MT6351 topology. Treat the topology as an
implementation boundary to validate, not as a reason to discard the reusable
PWRAP protocol or to claim a failed PMIC.
The exact current board DT makes this PMIC path a prerequisite for eMMC:
MSDC0 consumes MT6351 VEMC/VIO18, while PWRAP and the MFD IRQ setup perform
write-capable probe work. The [first-boot probe dependency audit](../../experiments/2026-07-14-first-boot-probe-audit/README.md)
records the dated source anchors and package provenance. Power sequencing
cannot be treated as a DT-only task.

The unpatched upstream MT6797 SoC DTS has no nodes for MSDC/eMMC, USB/PHY,
IOMMU/M4U, GPU, display components, DSI, AFE, thermal sensors, CPU
OPPs/cpufreq, RTC, or connectivity. Local patches now cover selected eMMC and
peripheral-only USB foundations, but the remaining functions still require
SoC-level descriptions and likely driver fixes; a board DTS alone is
insufficient.

## Kernel-facing ABI map

| Domain | Vendor interfaces observed in binaries/config | Live correlation | Mainline replacement |
| --- | --- | --- | --- |
| Display | `/dev/graphics/fb*`, `/dev/mtk_disp_mgr`, `/dev/ion`, `/dev/swsync`, M4U, `/proc/ged`, GED debugfs, `DISP_IOCTL_*` | `mtkfb`, DISPSYS, DSI and framebuffer active | DRM/KMS components, dma-buf heaps, dma-fence/sync_file, MediaTek IOMMU, Panfrost. Linux 7.1.3 contains reusable DRM/DSI/PHY and display-PWM pieces, but the Gemini panel graph and native display consumers remain absent or disabled. Loader-retained fbcon is not native display support; see the [support matrix](../HARDWARE_SUPPORT.md). |
| CPU/PSCI/timer | Vendor CPU hotplug/cpuidle policy, PSCI SMC calls, ARM timer PPIs, and MT6797 CPU GPT | Ten DT CPUs, PSCI 0.2 `smc`, standard `0x84000001`–`0x84000004` IDs, `arch_sys_counter`/`arch_sys_timer` active | The local Linux 7.1.3 path uses generic ARM64 topology, PSCI, GIC, and `arm_arch_timer`; CPU0–7 are serviceable together, while CPU8–9 remain disconnected by design pending the external-rail and complete A72 power-sequence gates. Keep vendor SPM/PCM idle and HMP/HPS/PPM policy out of the mainline contract. See the [DA921x/I2C6/A72 boundary](da921x-i2c6-a72.md). |
| UART/console | Vendor `ttyMT0`–`ttyMT3`, downstream console token, VFIFO/AP-DMA channels and pinctrl console states | Four live `mtk-uart` ports; `ttyMT0` is the active console; retained LK source rewrites its default `ttyMT3` token from preloader `log_enable`/`log_port` and overwrites final `/chosen/bootargs` | Linux 7.1.3 `8250_mtk` with the MT6797 compatible is the reuse path for one-window PIO and early console; its baud-clock lifetime already uses `devm_clk_get_enabled()`, so the bsg100 `clk_ignore_unused` workaround is not needed. Keep vendor VFIFO/AP-DMA out until channels are mapped. Mainline boot evidence now captures the effective command line and provides a loader-retained fbcon, but physical UART output remains unproved; see the [UART/console experiment](../../experiments/2026-07-13-uart-console-recovery/README.md). |
| I2C controllers | Vendor `mt-i2c` adapters 0–9 and board clients on chargers, sensors, cameras, touch, keyboard, USB-C, and regulators | A bounded live capture reports all ten adapters and the expected client placement. On the named unit, the local ownership path leaves childless I2C6 serviceable without taking I2C5's shared AP-DMA clock, and the native packed/FIFO path completes the exact one-byte-pointer plus one-byte-read shape. One gated run completed 14/14 fixed direct reads at `0x68` and `0x69` while CPU0–7, the CPU8/9-offline state, DVFSP handoff, and USB remained stable. | Reuse Linux 7.1.3 `i2c-mt65xx` with `mediatek,mt6797-i2c` plus `mediatek,mt6577-i2c` fallback for general controllers, and the dedicated `mediatek,mt6797-idvfs-i2c` data for I2C6. Preserve the reversible DVFSP pause protocol and shared AP-DMA baseline; do not copy the vendor fatal retry policy. The current result covers only the exact packed/FIFO 1+1 read. General transfers, writes, recovery, resume, provider behavior, and A72 power are separate gates. See the [DA921x/I2C6/A72 contract](da921x-i2c6-a72.md). |
| SPI controllers | Vendor `mt6797-spi` masters 0–5; test children on every bus and an unbound `fpc1020` candidate at SPI1 CS0 | Six live masters and five `test_spi`-style children are present; `spi1.0` is unbound and no transfer was issued | Patches 0072–0073 now reuse `spi-mt65xx` with its existing `mt6765_compat` (pad selection, enhanced 16-bit timing, mandatory TX, extended DMA) and add six disabled SoC nodes with standard parent/selector/gate clocks and `mediatek,pad-select`. The captured SPI1 wiring is GPIO234–237 (`SPI1_*_B`); vendor pinctrl has an empty default plus explicit GPIO-function/SPI-function switching states, so a static mainline pin group remains an evidence gate. Do not port vendor `mt_chip_conf`, test ABI, or fingerprint policy. See the [SPI controller reuse audit](../../experiments/2026-07-14-upstream-mt6797-coverage-audit/results/spi-mt6797-controller-reuse-20260714.txt), [SPI1 pinctrl contract](../../experiments/2026-07-14-upstream-mt6797-coverage-audit/results/spi1-pinctrl-contract-20260714.txt), and [patch validation](../../experiments/2026-07-14-upstream-mt6797-coverage-audit/results/spi-mainline-patch-validation-c2feb-20260714.txt) |
| Camera | `/dev/camera-isp`, `/dev/camera-fdvt`, `/dev/camera-dpe`, `/dev/kd_camera_hw*`, `/dev/MAINAF`, `/dev/SUBAF`, Android camera HAL and `libcameracustom.so` | `sp5509mipirawsls` selected by the live vendor image; pinned Planet sources contain separate SP5509 main/SLS implementations with 16-bit I2C, mode tables, and SLS power data, plus a 12-node CAM/SENINF/CAMSV/ISP implementation exposed through private `camera-isp` ioctl/mmap; immutable vendor ELF probes `0x0f16` for raw ID `0x0556` with candidate write IDs `0x40`/`0x50`; wrapper buses are `i2c2/3/8` at `0x11013000`/`0x11014000`/`0x11009000`, but no static `0x20`/`0x28` client objects exist; SENINF and camera hardware wrappers bound | New SP5509 V4L2 sensor sub-device plus a separately recovered MT6797 SENINF/CSI/CAM/CAMSV/ISP media-controller and verified M4U capture path; source/ELF facts are design inputs, not physical address or endpoint proof. See the [SP5509 source contract](../../experiments/2026-07-13-camera-recovery/results/sp5509-source-contract.md) and [MT6797 pipeline contract](../../experiments/2026-07-13-camera-recovery/results/mt6797-camera-pipeline-contract.md); do not reproduce vendor ioctls |
| GPU | `/dev/mali0`, Mali GLES/Vulkan, GED frequency/utilization controls | Legacy DT labels the node T860, but the bound vendor ELF/runtime identifies Mali-T88x MP4 / product `0x0880`; the pinned tree contains generic Kbase r12p0 plus configured r12p1 MT6797 platform/SPM source. The optional SPM/DVFS feature is not enabled in the captured autoconf/ELF path | Panfrost T880 core model plus a standard MT6797 platform backend for clocks, regulator readiness, power domains, reset, and fixed OPPs; do not port GED/Kbase userspace or SPM firmware ABI |
| Sensors | `/dev/hwmsensor`, `/dev/m_batch_misc`, `/dev/input/event*`, `/sys/class/misc/m_*` controls | BMI160 and STK3X1X paths observed | IIO/input drivers per physical sensor; userspace fusion for virtual sensors |
| Thermal | `/proc/mtktz/mtktscpu`, `mtktsbattery`, `mtktsAP`, `tzcpu_read_temperature`, CPU online sysfs | 13 vendor zones enumerate but are disabled; live calibration and complete source recover six banks, five sensor inputs, channel 11, and three efuse words | Patch 0057 extends the existing MediaTek AUXADC thermal driver with an MT6797-specific data/variant path for register timing, valid mask, buffer/IRQ protection, and ADC-OE conversion; reuse DT thermal, IIO, and standard cooling APIs, but do not reuse another SoC's calibration data. Nodes remain disabled pending runtime proof. See the [thermal recovery experiment](../../experiments/2026-07-13-mt6797-thermal-recovery/README.md) |
| LEDs | standard red/green LED sysfs plus `/proc/aw9120_reg` | AW9120 and LED class active | LED class/multicolor driver; debug registers only through debugfs if justified |
| Keyboard | integrated input device; `planetgemini` XKB model; AW9523 vendor node | AW9523 at I2C5 `0x5b`, EINT 10; source-derived 8×7 map with 52 assigned codes and four `KEY_UNKNOWN` positions; vendor scan drives the selected column low, inactive columns high, and treats a low row bit as pressed | The local AW9523 plus generic matrix-polling path now produces retained press/release events and owner-accepted typing with the physical map. Function keys, Page Up/Page Down, modifiers, rollover, wake, and complete event coverage remain explicit acceptance gates. The XKB function layer is userspace policy; see the [keyboard boundary](keyboard.md). |
| Touch | input event plus vendor NVT firmware path | NVT at I2C4 `0x62`, EINT 8; fresh filtered probe log returns `00 00 03 72 66 03`, matching masked trim-table entry 8 / NT36772 event map `0x11e00`, with PID `0x0101` and firmware `0x05`/bar `0xFA` | `novatek-nvt-ts` does not cover the verified alternate-address/xdata contract. Patch 0075 provides a disabled-by-default NT36772 boundary and passes object/module plus binding checks; validate logical-address `0x01`, rails/reset, and runtime before enabling it, with firmware update excluded. See the [live trim identity](../../experiments/2026-07-12-input-backlight-recovery/results/nvt-live-trim-identity-20260714.txt), [protocol record](../../experiments/2026-07-12-input-backlight-recovery/results/nt36xxx-protocol.txt), and [boundary checks](../../experiments/2026-07-12-input-backlight-recovery/results/nt36772-mainline-boundary-20260714.txt) |
| Storage | `mtk-msdc.0/11230000.msdc0`, GPT by-name links | eMMC on MSDC0; MSDC1/card detect described. The local Linux 7.1.3 profile binds PWRAP/MT6351 VEMC/VIO18 and enumerates the DF4064 user area, boot areas, and GPT partitions. | Reuse `mtk-sd` with the local MT6797 record and conservative Gemini nodes. Guarded reads and writes to an explicitly resolved inactive `boot2` work; primary `boot` protection, microSD, reliability, and suspend remain separate gates. See the [eMMC experiment](../../experiments/2026-07-25-emmc-development/README.md). |
| Audio | ALSA PCM plus `/dev/accdet`, `/dev/fm`, `/dev/hdmitx`, `/dev/vow`, ANC/offload and CCCI speech nodes | MTK sound card and PCM endpoints active | Existing MT6797 ASoC/MT6351 base, standard jack, speaker amp, DAPM routes; modem voice separate |
| USB-C | role-switch policy and FUSB301 vendor paths | two FUSB301 I2C devices; MUSB/MTU3 paths | The local MTU3/USB2 PHY peripheral-only path supports gadget Ethernet and the development shell. Generic FUSB301 support is prepared separately; host/xHCI, role switching, VBUS and rail ownership, Type-C policy, redriver glue, both physical ports, and hotplug remain open. |
| Wi-Fi/BT/FM | `/dev/stpwmt`, `wmtdetect`, `wmtWifi`, `/dev/fm`, WMT launcher/firmware (`stpbt` is a source/userspace name, not a captured device node) | MT6797 CONSYS/WMT bound; Wi-Fi `mt-wifi` and BTIF TX/RX DMA active; MT6631 FM configured | Mainline needs a consys firmware/power/SDIO boundary, standard cfg80211/Bluetooth/FM interfaces, and no permanent vendor character ABI |
| GNSS | `stpgps`, `gps`, GPS HAL, MNL/AGPS sockets | vendor `gps`/`gps_emi` bound; ROMv3 patch includes GNSS/geofence strings; GPIO69 is the board GPS-LNA control | Establish combo-firmware ownership and message routing before adapting the serial GNSS core |
| Modem | CCCI, EEMCS, EMD, `ttyC`, 18 MD1 `ccmni` ports, 8 MD3/C2K `cc3mni` ports, and shared audio channels | MD1 and MD3 CCCI nodes, AP/MD CLDMA/CCIF devices, and active CLDMA/CCIF IRQs are live; source recovers the 16-byte wire header, 8+8 queue families, packed 36-bit descriptors, CCIF flow-control SRAM, and staged EMI-MPU/remap ownership | MT6797 requires a new APB CLDMA/CCIF/shared-memory transport with firmware handshake, reset, and EMI MPU ownership; Linux 7.1.3 `t7xx` is PCIe/DPMAIF-specific. Reuse standard WWAN/TTY/netdev layers only above that transport; keep the vendor character ABI private. See the [modem/CCCI recovery](../../experiments/2026-07-13-modem-ccci-recovery/README.md) and [MT6797 CCCI contract](../../experiments/2026-07-13-modem-ccci-recovery/results/mt6797-ccci-mainline-contract.md) |
| Secure services | Trusty/MobiCore device rules | not independently correlated | Preserve firmware boundary; exclude from initial mainline board support |

## Fresh post-reboot transport evidence

After a battery-depletion reboot, bounded read-only collectors again observed
the vendor `mtk_wmt`/`mt-wifi`/`mtk_btif`/GPS owners, an operational `wlan0`,
the same WMT/ROMv3 firmware hashes, and the same MD1/MD3 CCCI/CLDMA/CCIF
topology. The connectivity log additionally confirms that Android `ueventd`
fulfills initial kernel firmware requests after direct lookup returns `-ENOENT`;
this is a vendor bootloader/userspace boundary, not a mainline firmware-loader
contract. The sanitized records are the [post-reboot connectivity result](../../experiments/2026-07-12-connectivity-wmt-recovery/results/live-connectivity-postreboot-20260714.txt)
and [post-reboot CCCI result](../../experiments/2026-07-13-modem-ccci-recovery/results/live-ccci-postreboot-20260714.txt).
No CCCI node, shared-memory region, radio interface, or firmware ioctl was
opened or modified by the collectors.

The same post-reboot read-only pass also rechecked the six vendor SPI masters:
their windows, IRQs, pad macros, and `test_spi`/unbound-`fpc1020` child topology
match the earlier capture byte-for-byte. The [sanitized SPI result](../../experiments/2026-07-14-upstream-mt6797-coverage-audit/results/spi-live-postreboot-20260714.txt)
supports resource-map stability only; it does not justify enabling a mainline
SPI child or issuing a transfer.

## Display and memory-management detail

The hardware composer retains readable C++ symbols and error strings. Its
`DispDevice`, `OverlayEngine`, `HWCDispatcher`, and `SyncControl` layers open a
`/dev/graphics/fb%d` descriptor and issue session operations named:

- create/destroy session;
- query display capabilities and session information;
- prepare input, output, and present fences;
- configure a frame and validate layer placement;
- set session mode and power mode;
- wait for VSync and completion.

The same code allocates ION buffers, imports/shares handles, configures M4U
ports, maps MediaTek virtual addresses, and communicates frequency/VSync hints
through GED. Gralloc uses framebuffer pan/variable-screen ioctls and a private
`FBIOGET_DMABUF` operation.

Disassembly confirms twelve vendor framebuffer requests with encoded payloads
from 4 to 88 bytes, plus standard `FBIOBLANK`. The full numeric table and
method-level call graph are preserved in the linked experiment. Picture-quality
and adaptive-backlight code separately use `/dev/mtk_disp_mgr`; this should not
be conflated with HWC's framebuffer session ABI.

Mainline must not expose these private ioctls. Required enablement layers are:

1. MT6797 IOMMU/M4U data and stream IDs for display and multimedia clients.
2. MMSYS routing and component clocks/resets/power domains.
3. OVL/RDMA/WDMA/COLOR/DSI components wired into MediaTek DRM.
4. The exact DSI panel, supplies, reset GPIO, timings, orientation, and
   backlight.
5. Standard dma-buf and fence synchronization.
6. Panfrost as a separate consumer of GPU clocks, SCPSYS domains, reset,
   regulator, and OPP data.

The MT6797 M4U port table contains display, MDP, video, camera, and MJC clients
but no GPU client. The legacy Mali-T860-labelled node (runtime product
`0x0880`, T880-family) has its own MMU interrupt. Do not add an `iommus`
relationship between Mali and the MediaTek M4U without contrary hardware
evidence.

The vendor framebuffer reports 1080x2160 at 32 bpp with physical rotation 90.
Runtime debugfs selects `aeon_nt36672_fhd_dsi_vdo_x600_xinli`, a four-lane,
single-DSI burst-video LCM. The root DT's
`r63419_wqhd_truly_phantom_2k_cmd_ok` dual-DSI description is inactive because
this build has `DISP_OPT_USE_DEVICE_TREE=0`. Linux 7.1.3 contains NT36672A and
NT36672E panel drivers, but neither existing panel variant matches the Gemini
mode, command table, supplies, or power sequence. See the
[panel-recovery experiment](../../experiments/2026-07-11-gemini-panel-recovery/README.md).

Panel identity remains a deliberate gate: the named-device capture only proves
the selected vendor driver, while the independent bsg100 hardware capture reads
SEEPROM words identifying an AUO/Solomon SSD2092 and direct DSI status values.
The shared 1080x2160 video geometry is useful for host planning, but the
NT36672 and SSD2092 command/power contracts must not be merged without a direct
readback on the named device. The [bsg100 cross-check](../../experiments/2026-07-13-bsg100-gemini-linux-comparison/results/bsg100-panel-crosscheck-20260714.txt)
records hashes and the contradiction. The named device's separate
`solomon_touch@0x53` node is unbound while NVT `cap_touch@0x62` is active, and a
filtered suspend capture contains both panel-name strings; neither observation
is a silicon identity read.

## Sensor model

The HAL exposes far more logical sensors than physical parts: acceleration,
gyro, magnetic field, light, proximity, pressure, humidity, step, pickup,
tilt, shake, glance, face-down, rotation vectors, gravity, and other fused
events. Most are controlled through one misc-class directory per logical
sensor, with `active` and `devnum` files, plus a batch misc device.

The live vendor kernel binds BMI160-named accelerometer/gyroscope clients at
I2C1 addresses `0x68`/`0x69` and an STK3X1X-named light/proximity child at `0x48`,
but it exposes no IIO devices (`CONFIG_IIO` is unset). Static disassembly
shows both vendor probes overwrite `i2c_client.addr` with `0x69`; the logical
address pair therefore does not establish two physical chips. Linux 7.1.3 has a
generic BMI160 IIO driver, plus generic BMP280 and HTS221 drivers for the
vendor's unbound `0x77` and `0x5f` candidates. The upstream STK3310-family
driver is a likely reuse candidate for STK3X1X: the vendor header/disassembly
and Linux 7.1.3 share the state/control, threshold, flag, data, and product-ID
(`0x3e`) register model. However, the vendor accepts broader product-ID
high-nibble families (`0x10`, `0x20`, and `0x30`) than the explicit upstream ID
table, and the live product/revision has not been read safely. Do not add a
generic compatible or claim runtime support until that identity and the
VDD/VIO plus GPIO88/EINT11 contract are captured; use a chip-specific driver if
the actual protocol differs. The complete audit is in
[stk3310-reuse-audit.txt](../../experiments/2026-07-12-sensor-iio-recovery/results/stk3310-reuse-audit.txt).
Linux has no direct MMC3530 match. Its closest MEMSIC magnetometer
implementation is MMC35240, but the Gemini has no bound MMC3530 symbols or
magnetic input stream in the capture.
The captured `sensors.mt6797.so` maps the physical vendor paths through
`m_*_misc` device-number attributes and `/dev/input/eventN`, not I2C from
userspace. Static disassembly shows its accelerometer and gyroscope HAL
decoders divide ABS values by per-device `mdiv` values read from the vendor
`*active` attributes, but do not apply axis permutation or sign changes. The
legacy direction-7 transform therefore belongs to the vendor kernel sensor
path. The recovered vendor kernel table resolves direction 7 to
`sign={-1,-1,-1}`, `map={1,0,2}` (`out=(-raw_y,-raw_x,-raw_z)`), equivalent to
the IIO property `mount-matrix = "0", "-1", "0", "-1", "0", "0", "0", "0", "-1"`.
The recovered BMI160 data paths apply the sign/map before emitting their
legacy input-event triplets. The vendor's virtual
step/fusion/gesture classes remain userspace policy. See the [sensor/IIO recovery experiment](../../experiments/2026-07-12-sensor-iio-recovery/README.md)
and its [binary ABI record](../../experiments/2026-07-12-sensor-iio-recovery/results/hal-binary-contract.txt)
and [axis contract](../../experiments/2026-07-12-sensor-iio-recovery/results/hal-axis-contract.txt)
for the exact live and source evidence.

The recovered vendor gyro initializer reads register `0x00` and accepts IDs
`0xd0` through `0xd3`; the accelerometer initializer reads the same register
but does not visibly reject an unexpected value in the recovered path. The
standard Linux 7.1.3 BMI160 core recognizes `0xd1` and `0xd3`, but currently
continues after an unknown-ID warning. A mainline Gemini probe must record the
actual ID and register behavior before claiming BMI160 support; a different
chipset is a reason to select an existing family driver or add a new driver,
not to bend BMI160 around the legacy ABI. See the [vendor IMU probe record](../../experiments/2026-07-12-sensor-iio-recovery/results/vendor-imu-probe.txt).

The vendor's `bmi160_bmi_value` diagnostic is not an identity field: its
handler reads a 12-byte raw data block beginning at register `0x0c`. Neighboring
register-selection attributes can issue arbitrary reads and writes, so they are
not part of the safe inventory contract.

Do not create kernel drivers for vendor virtual-sensor classes. Enable physical
IIO/input devices with timestamps and interrupts, then implement fusion and
gesture policy in userspace unless a standard kernel interface requires more.

## Input and keyboard

Gemian labels the device `Integrated keyboard` and selects XKB model
`planetgemini`. A fresh passive capture again ties it to AW9523 on I2C5
address `0x5b`, with EINT 10. The installed `planet_vndr/gemini` symbols add
an ISO-Level3/Mod5 function layer and media/brightness/navigation levels over
ordinary Linux keycodes. Linux 7.1.3 includes an AW9523 GPIO/pinctrl driver,
but the working local path uses AW9523 GPIO plus generic 8×7 matrix polling,
with a 20 ms interval and 2 µs column-settle delay. It produces retained
press/release events and owner-accepted typing with the current physical map.
The installed XKB file remains userspace metadata, not a kernel ABI.

The vendor timing policy is not a direct Linux DT timing contract: its AW9523
path delays external IRQ work by 1 ms, scans after another 1 ms, then rescans
at 100 Hz for up to 100 cycles after a transition. The retained AW9523 EINT
pseudo-node has no `debounce` tuple even though the source requests one and
ignores the property-read error. The local polling policy is therefore an
independently accepted mainline behavior, not a claim that the vendor timing
was reproduced. Function keys, Page Up/Page Down, modifiers, rollover, wake,
and complete event coverage remain open. See the canonical
[keyboard boundary](keyboard.md); detailed traces stay with its linked
experiments.

The separate hall/toggle inputs are not part of the AW9523 matrix. The live
device exposes GPIO66/EINT5 as a vendor `hall` switch and an `EV_SW` capability
on the `ACCDET` input device; GPIO93/EINT16 is exposed as `switch`, while the
vendor driver generates `KEY_F9`/`KEY_F10` pulses. Linux 7.1.3's `gpio-keys`
can represent the hall path as `SW_LID` once polarity, debounce units, and
wake policy are verified. The toggle's physical function is unresolved, so no
Android switch-class compatibility layer or key mapping should be committed
yet. See the [hall/lid/switch recovery experiment](../../experiments/2026-07-12-hall-lid-switch-recovery/README.md).

## Audio boundary

Unlike display, the vendor audio HAL is already centered on ALSA. Its readable
class names show separate providers/handlers for normal capture/playback,
Bluetooth SCO/CVSD, FM, modem DAI, voice uplink/downlink, VOW, ANC, HDMI, and
external speaker paths. It also loads calibration through audio/NVRAM helper
libraries.

Linux 7.1.3's MT6797 AFE and MT6351 codec/machine code is therefore a strong
starting point. Its binding already fixes the AFE register window at
`0x11220000`, interrupt SPI 151, the audio SCPSYS domain, and eight named
infrastructure/top clocks. The MT6351 codec must be a child of the PMIC wrapper
and obtains its regmap from that parent. Gemini work still needs those SoC/PMIC
nodes, machine routing, jack/accdet, speaker amplifier identity, and safe
gain/supply sequencing. Cellular speech channels must remain a separate later
transport. The local configuration now prepares the three standard driver
paths as modules and their objects compile; this is a build-only capability,
not an enabled card. The dated object validation remains in the
[audio recovery experiment](../../experiments/2026-07-12-audio-afe-recovery/README.md);
it is not current package authority. The modem-audio boundary and calibration
data must remain private.

## Power, PMIC, and suspend

The vendor system loads nine SPM microprograms and exposes `/dev/spm`; its
thermal HAL reads vendor procfs and CPU hotplug state. These are tightly coupled
to MediaTek 3.18 power policy. Linux 7.1.3 has SCPSYS coverage but no Gemini CPU
OPPs, cpufreq, an MT6797 thermal compatible, PMIC/regulator graph, or SPM firmware
contract in the MT6797 DTS. The complete Planet CPU-DVFS source recovers three
cluster PLL paths plus CCI, function/date-efuse-selected tables, DA9214/SRAM
tracking, an active EEM/PTP calibration state machine, and an optional private
PCM controller. Mainline's OPP/regulator and clock-reparenting helpers are
reusable, and its newer MediaTek SVS driver demonstrates NVMEM-backed phase
handling plus runtime OPP voltage adjustment. However, the MT6797 EEM window
is shared with the thermal controller and has a different register, efuse,
clock/power, and DA9214 contract. The existing MT6797 CCF provider also lacks
the vendor ARMPLL/CPU-mux/CCI clock definitions required by `clk_set_rate()`;
an MT6797 clock extension plus cpufreq variant, or a new provider/driver, is
appropriate once those boundaries are proven. The vendor CPU PLL window is
also protected by a DVFSP/CSPM hardware semaphore shared by the kernel, SPM,
and ATF, while B-cluster PLL/SRAM operations use secure BigiDVFS SMCCC calls;
direct writable CCF MMIO is therefore not a safe default. The staged ownership
and provider boundary are recorded in the [MT6797 CPU clock backend result](../../experiments/2026-07-12-mt6797-clock-power-reset-recovery/results/mt6797-cpu-clock-backend.md).
The external DA921x provider and both Cortex-A72 CPUs remain unavailable:
the fixed read-only board contract is established, but register writes, rail
ownership, constraints, rollback, resume, and the complete Linux/firmware
power sequence are not. Follow the ordered
[roadmap gates](../ROADMAP.md#ordered-gates), constrained by the
[DA921x/I2C6/A72 safety boundary](da921x-i2c6-a72.md), before requesting CPU8
or CPU9.

The thermal experiment recovered the complete six-bank, five-sensor,
channel-11, efuse-calibrated hardware boundary. The generic AUXADC-thermal bank
and calibration architecture are reusable, but the MT6797-specific valid mask,
sampling filter, APMIXED buffer, IRQ/protection, and ADC-OE conversion need an
explicit variant; a wholly separate driver is acceptable if the variant cannot
be represented cleanly in the generic driver. The generic
PSCI/architectural-timer boundary is separately
captured in the [CPU/PSCI/timer recovery](../../experiments/2026-07-13-cpu-psci-timer-recovery/README.md);
it is safe to reuse the standard transport without assuming the vendor deep-idle
parameters.

Initial mainline bring-up should use conservative fixed clocks, only verified
regulators, and no attempt to reuse vendor SPM programs. Add suspend only after
boot, storage, serial console, interrupt, PMIC, and power-domain behavior is
repeatable. The firmware-reserved regions in the baseline remain mandatory
until ownership is understood.

## Peripheral driver coverage in Linux 7.1.3

| Observed candidate | Linux 7.1.3 status | Required work |
| --- | --- | --- |
| AW9523 | Generic GPIO/pinctrl driver and binding present | The local generic matrix-polling path provides accepted partial keyboard input. Function keys, navigation keys, modifiers, rollover, wake, complete event coverage, IRQ mode, and backlight remain separate gates; see the [keyboard boundary](keyboard.md). |
| BMI160 | I2C/SPI IIO driver present | Patch 52 supplies a disabled `bosch,bmi160` candidate and config; direct ID, rails, IRQ/polling, and runtime validation remain |
| BMP280 | I2C/SPI IIO driver present | Confirm the unbound `0x77` candidate, standard compatible, supplies, and any IRQ |
| HTS221 | I2C/SPI IIO driver present | Confirm the unbound `0x5f` candidate, standard compatible, supply, and any IRQ |
| MMC3530 | No matching driver found | Identify the `0x30` part and add a new IIO driver/binding if confirmed |
| MMC35240 | I2C IIO driver present | Use only as a register-model hypothesis for the unbound MMC3530 candidate |
| Novatek touch | Linux driver supports NT11205 and NT36672A; vendor source/ELF accepts eleven masked NT36xxx signatures with distinct logical-addressed transfers | Live filtered probe now records trim `00 00 03 72 66 03`, matching NT36772 trim-table entry 8 / event map `0x11e00`; validate the alternate `0x01` target, rails/reset, and event path before adding a separate backend. See the [live identity record](../../experiments/2026-07-12-input-backlight-recovery/results/nvt-live-trim-identity-20260714.txt) |
| BQ25890 | Charger driver/binding present | Confirm exact silicon and safe board limits; describe supplies/USB role |
| DA9214-named external buck | Linux 7.1.3's DA9211/A-family probe is not a match for the observed legacy protocol. The named unit exposes a fixed DA9213/DA9214/DA9215-compatible read-only tuple, but no suitable provider is active and the tuple is not a unique silicon ID. | Required boundaries are a dedicated legacy-family driver/binding or genuinely separated variant, zero probe-time writes, fail-closed fixed reads, and independent validation of BUCK mapping, ownership, voltage/current tables, enable and IRQ semantics, constraints, rollback, resume, and consumers. See the [DA921x/I2C6/A72 contract](da921x-i2c6-a72.md), [ordered roadmap](../ROADMAP.md#ordered-gates), and [exact board-contract experiment](../../experiments/2026-07-28-da9214-gauss/README.md). |
| SII9022/Sil9024A candidate | I2C3 `0x39`/EDID `0x50` clients unbound; vendor source/ELF checks indexed ID `0x9022` plus TPI ID `0xb0` at register `0x1b`, then uses private `/dev/hdmitx`, `mediatek,sii9022_hdmi`, and a separate EDID client (the `siiSegEDID` segment pointer is declared but not assigned in the pinned source). Vendor DPI0 is `0x1401e000`/SPI231 with MM/interface gates and TVDPLL D2/D4/D8/D16 sources | Linux 7.1.3 `sii902x`/DRM bridge and generic `mtk_dpi` are the reuse candidates; patches 60/61 add only MT6797 DPI platform data and a disabled unconnected node. Adapt the verified 20/50/20 ms reset, GPIO247 1.2 V enable, I/O rail, 16-bit DPI graph, HPD, EDID mux, and PLL factor table only after physical identity/resources are proven; do not port the vendor HDMI ioctl ABI |
| Mali T860 | Panfrost family support present | MT6797 GPU node/compatible, power domains, clocks, reset, regulator, OPPs and runtime tests |
| MT6351/MT6797 audio | Codec, AFE and machine drivers present | Add SoC/board DT nodes and validate routing |
| STK3X1X | Existing `stk3310` IIO driver has a matching register model, but no generic `stk3x1x` compatible | Capture product/revision at `0x3e`; reuse the upstream STK3310-family binding when the explicit ID and VDD/VIO/GPIO contract match, otherwise add a chip-specific driver |
| FUSB301 | Patch 0056 adds a generic `onsemi,fusb301`/`onsemi,fusb301a` Type-C controller and binding; validates Device ID `0x12`, documented mode/current/interrupt registers, attach/partner/BC/orientation status, and standard Type-C reporting. Vendor probe logs now return `0x12` on both populated I2C clients; only FUSB301A's GPIO64/EINT path obtains a valid IRQ | Mainline IRQ/connector mapping, VBUS switch/current control, SuperSpeed redriver, and USB role integration remain unverified; Gemini board nodes stay absent. See the [FUSB301 validation](../../experiments/2026-07-12-usb-typec-recovery/results/fusb301-mainline-validation.txt), [fresh USB/Type-C capture](../../experiments/2026-07-12-usb-typec-recovery/results/runtime-usb-typec-battery-recovery-20260714.txt), and [design record](../../experiments/2026-07-12-usb-typec-recovery/results/fusb301-mainline-design.md) |
| AW9120 | No matching driver exists. Live I2C3 `0x2c` returns ID `0xb223`; GPIO245 is active-high PDN/reset, and public retained source plus the installed Gemian daemon map the five RGB blocks to outputs 1–15. I2C3 GPIO74/75 and the 8-bit-register/big-endian-16-bit protocol are known; current code 1 is the documented 3.5 mA minimum | Add a new generic regmap LED-class/multicolor driver and binding with `enable-gpios`; first validate block-1 green/output 2 at 3.5 mA and capped PWM. Enable only I2C3/`0x2c`, never scan shared `0x39`/`0x50`, and do not reproduce the vendor `/proc` ABI. See the [Gemian baseline](gemini-gemian-baseline.md#aw9120-indicator-leds) and [screen/LED selection record](../../experiments/2026-07-16-screen-marker-diagnostic/results/display-path-selection-20260716.txt) |
| RT5735 | Local patch 51 adds a standard VSEL0 provider; vendor source checks product ID `0x10`, uses VSEL registers `0x10`/`0x11`, and enables via bit 7 | Runtime identity/readback and external VGPU wiring remain unverified; do not assume FAN53555 compatibility |
| FAN49101 | Populated buck/boost at I2C0 `0x70`; vendor registers `0x00` reset, `0x01` VOUT, `0x02` control, `0x40` manufacturer ID, `0x41` die ID; source accepts manufacturer `0x83` and uses 603 mV + 12.826 mV steps with VOUT bit 7 enable; a post-recovery vendor probe logged manufacturer `0x83`, die `0x06` | Patch 0055 adds a dedicated `onsemi,fan49101` regulator driver/binding and disabled Gemini node; object, binding, and focused DTB schema validation pass. Mainline readback, control/reset, rail ownership, ramp, and rollback evidence are still required. See the [FAN49101 register contract](../../experiments/2026-07-12-charger-power-recovery/results/fan49101-register-contract.txt), [fresh charger capture](../../experiments/2026-07-12-charger-power-recovery/results/live-charger-battery-recovery-20260714.txt), and [validation result](../../experiments/2026-07-12-charger-power-recovery/results/fan49101-mainline-validation.txt) |
| LP3101-named LCD bias | TPS65132 protocol matches address, VPOS/VNEG selectors, `0x0f` = 5.5 V, and per-output enables; downstream `lp3101.c` only writes registers and has no readback or ID check | Reuse the TPS65132 driver only after physical or electrical identity/compatibility proof; the LowPowerSemi LP3101 documentation conflicts with the live I2C interface |
| Gemini NT36672-family panel | Related NT36672A/E DRM panel drivers exist, but no matching module data | Add a specific compatible and recovered mode/command/power data; verify ID on hardware |
| R63419 root-DT panel | No matching panel driver; proven inactive on this runtime | Retain only as a possible board-family/variant lead |

`No matching driver found` means a targeted name/compatible search in the
pinned tree found none; it does not prove that a compatible generic driver is
impossible.

## Planning authority

The current implementation sequence and milestone exits live only in the
[roadmap](../ROADMAP.md). This ABI map supplies constraints to that plan:

- replace vendor character interfaces with standard Linux subsystems;
- preserve firmware, modem, calibration, and secure-world boundaries;
- enable one resource owner or consumer at a time with a reversible,
  attributable experiment; and
- require a named kernel, DT, config, boot path, bounded protocol, and
  sanitized evidence before changing the support matrix.
