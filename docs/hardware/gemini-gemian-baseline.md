# Gemini PDA Gemian hardware baseline

This document records the software-visible hardware of one Gemini PDA running
Gemian. It is a starting point for a mainline device tree, not proof that any
component works on the repository's current upstream kernel.

## Provenance and scope

| Field | Value |
| --- | --- |
| Observation date | 2026-07-11 baseline; read-only reruns 2026-07-13 and 2026-07-14 |
| Device access | Owner-authorized read-only SSH collection on a private LAN |
| OS | Debian GNU/Linux 9 (stretch), Gemian userspace |
| Kernel | `3.18.41+`, build `#7 SMP PREEMPT Fri Mar 29 10:39:03 GMT 2019` |
| Architecture | AArch64 |
| Device-tree model | `MT6797X` |
| Root compatible | `mediatek,MT6797` |
| Device variant | Installed Android image identifies `Gemini 4G`; physical SKU not independently established |
| Collector | [`collect.sh`](../../experiments/2026-07-11-gemian-hardware-inventory/scripts/collect.sh) |
| Experiment record | [2026-07-11 Gemian hardware inventory](../../experiments/2026-07-11-gemian-hardware-inventory/README.md); [2026-07-13 live inventory rerun](../../experiments/2026-07-11-gemian-hardware-inventory/results/live-inventory-rerun-20260713.txt); [2026-07-14 live runtime snapshot](../../experiments/2026-07-14-first-boot-probe-audit/results/live-runtime-snapshot-20260714.txt); [2026-07-14 corrected vendor runtime capture](../../experiments/2026-07-13-mainline-handoff-closure/results/vendor-baseline-runtime-20260714.txt); [battery-recovery runtime capture](../../experiments/2026-07-13-mainline-handoff-closure/results/vendor-baseline-battery-recovery-20260714.txt); [vendor-to-mainline gap audit](../../experiments/2026-07-14-live-vendor-mainline-gap-audit/README.md); [2026-07-14 live-kernel ownership audit](../../experiments/2026-07-14-live-kernel-ownership-audit/README.md); [boot contract recovery](../../experiments/2026-07-12-boot-contract-recovery/README.md) |

The implementation-facing register, IRQ, clock, storage, M4U, display, GPU,
and USB details are maintained in the
[MT6797 live resource map](mt6797-live-resource-map.md).

The collector removed unique identifiers and did not read eMMC CID, filesystem
UUIDs, MAC addresses, IMEI/MEID values, calibration data, firmware, partitions,
or user files. Although passwordless sudo was expected, `sudo -n` required a
password on this installation. The owner later supplied the password for a
transient interactive session, allowing read-only collection of `/proc/iomem`.
The vendor kernel does not provide a regulator summary file, but its regulator
class is readable. No credential was stored and no remote state was changed.

The 2026-07-14 kernel refresh confirms that this vendor image is effectively
monolithic for active drivers: `CONFIG_MODULES` is unset and `/proc/modules` is
absent, while the selected vendor paths are built into the image. This matters
for the replacement boundary: a Linux 7.1.3 module file is not equivalent to a
vendor-owned runtime path until a rootfs loads it and a device probes. The
symbol/config comparison and exact private-capture hashes are recorded in the
[current 72-patch live-kernel ownership audit](../../experiments/2026-07-14-live-kernel-ownership-audit/results/live-kernel-ownership-current-72-package-20260714.txt);
the [historical package result](../../experiments/2026-07-14-live-kernel-ownership-audit/results/live-kernel-ownership-20260714.txt)
is retained for provenance.
The owner-authorized post-reboot baseline is summarized in
[`vendor-baseline-postreboot-20260714.txt`](../../experiments/2026-07-13-mainline-handoff-closure/results/vendor-baseline-postreboot-20260714.txt);
its private raw capture remains mode 0600 and Git-ignored.
A later battery-recovery snapshot preserved the same vendor kernel, storage,
reservation, and ownership facts but observed 0–2 rather than 0–1 CPUs online;
possible/present stayed 0–9. Treat this as time-dependent hotplug/policy state
until a controlled mainline boot explains it. See
[`vendor-baseline-battery-recovery-20260714.txt`](../../experiments/2026-07-13-mainline-handoff-closure/results/vendor-baseline-battery-recovery-20260714.txt).

Confidence in this document has a deliberately narrow meaning:

- `observed`: directly exposed by the running kernel, sysfs, or procfs;
- `described`: a name or topology present in the vendor device tree/config, but
  not an independent physical part identification;
- `inferred`: multiple observations point to a conclusion, but alternatives
  remain.

## Platform and CPU

| Fact | Confidence | Evidence |
| --- | --- | --- |
| MediaTek MT6797/Helio X20-family platform | `observed` | Root compatible `mediatek,MT6797`; vendor kernel config `CONFIG_MTK_PLATFORM="mt6797"` |
| 8 Cortex-A53 plus 2 Cortex-A72 CPUs described | `observed` | Ten CPU DT nodes: eight ARM part `0xd03`, two part `0xd08` |
| The online CPU mask is time-dependent; the latest corrected 2026-07-14 capture reported `0-2` while possible/present remained `0-9` (the prior post-reboot read reported `0-1`; an earlier read reported `0-1,4`) | `observed` | `/sys/devices/system/cpu/{online,possible,present}` in the private vendor baseline |
| Boot command line constrained the system to five CPUs | `observed` | Sanitized boot arguments contained `maxcpus=5` |
| Online cores used the vendor `mt-cpufreq` driver | `observed` | CPU0 cpufreq sysfs |
| CPU0 range was 221 MHz to 1.547 GHz | `observed` | `cpuinfo_min_freq=221000`, `cpuinfo_max_freq=1547000` kHz |
| GICv3 and ARMv8 architectural timer | `observed` | DT compatible nodes and live interrupts |
| PSCI 0.2 firmware interface | `observed` | DT PSCI node |
| PSCI transport and function IDs | `observed` | 2026-07-13 read-only DT capture: `method=smc`, `0x84000001`–`0x84000004` for suspend/off/on/affinity |
| Architectural counter and clockevent | `observed` | 2026-07-13 capture: `arch_sys_counter`, `arch_sys_timer`, `arm,armv8-timer`, four GIC PPIs, 13 MHz frequency |
| Approximately 3.68 GiB usable RAM | `observed` | `MemTotal: 3860680 kB` |

The CPU observation does not establish why only a subset of cores were online. The boot
limit, thermal/hotplug policy, and vendor power-management behavior are all
possible contributors and need a controlled experiment. The newer bounded
capture also found a downstream reporting contradiction: its global online mask
and `/proc/cpuinfo` briefly disagreed with per-CPU flags and `/proc/stat`, while
separate reads returned `0-1` and the latest battery-recovery snapshot returned
`0-2`. Treat the online count as time-dependent until a mainline boot verifies
it. See the [CPU/PSCI/timer recovery experiment](../../experiments/2026-07-13-cpu-psci-timer-recovery/README.md).

The independent bsg100 Linux 6.6 boot record adds a runtime warning: standard
PSCI brought up CPU1 through CPU7, while CPU8 (the first Cortex-A72) blocked in
`CPU_ON`; a diagnostic `maxcpus=8` boot reached all A53 cores. The current 7.1.3
board does not copy that workaround and keeps all ten generic CPU nodes, so the
first mainline boot must identify the boundary rather than assuming either
full SMP or an A53-only policy. See the [normalized cross-check](../../experiments/2026-07-13-cpu-psci-timer-recovery/results/bsg100-cpu-psci-crosscheck-20260714.txt).

## Boot handoff and storage boundary

The retained Planet LK hands Linux an Android-format boot image. The running
`boot`, `boot2`, and `boot3` partitions were byte-identical in the private
provenance check. The image uses a 2048-byte page, loads the kernel at
`0x40080000`, loads the initramfs at `0x45000000`, and carries a 130,745-byte
DTB appended inside the kernel payload. LK supplies a chosen command line with
`root=/dev/ram`, `maxcpus=5`, the `ttyMT0` console, Android boot-state fields,
and ramdump reservations; unique serial values are redacted. The chosen DT
places the initramfs at `0x45000000`–`0x4560f6bd`. The retained LK source
shows that this command line is constructed late: its non-FPGA default is
`ttyMT3`, the preloader's `log_enable`/`log_port` selects a `ttyMT0`–`ttyMT3`
variant, and LK overwrites `/chosen/bootargs` after appending the boot-image
header command line. The live `ttyMT0` observation is therefore a runtime
handoff result, not a DTB `stdout-path` guarantee. See the [LK console mutation
audit](../../experiments/2026-07-13-uart-console-recovery/results/lk-console-mutation-current-77-20260714.txt).

The installed Gemian root filesystem is `/dev/mmcblk0p29`. The installed
`gemian-modular-kernel` `linux-boot.img` is not byte-identical to the active
boot image, so it is not valid evidence for the running kernel. See the
[sanitized boot-image summary](../../experiments/2026-07-12-boot-contract-recovery/results/boot-image-summary.txt)
and [live handoff summary](../../experiments/2026-07-12-boot-contract-recovery/results/runtime-summary.txt).
The retained Planet Android 8 LK source audit adds an important constraint:
`bootopt=64...` selects the 64-bit branch, which gunzips the kernel and scans
for an appended DTB; the Android header `dt_size` field is not used by that
branch. The MT6797 platform build sets a 50 MiB decompression buffer. The
current raw `Image` therefore had to be replaced by `Image.gz` and reduced from
52,570,624 to 48,547,848 decompressed bytes before it could be packaged for
this loader. The [LK source/package audit](../../experiments/2026-07-12-boot-contract-recovery/results/lk-boot-contract-audit-20260713.txt)
records the exact source, hashes, and a private parse-complete candidate;
acceptance and runtime boot remain untested.

The retained LK source also changes how the board DT must be modeled. With
early-DTB loading and `MBLOCK_LIB_SUPPORT=2`, LK rewrites `/memory`, `/chosen`,
model/CPU metadata, and Android firmware properties, then appends runtime
`mblock-*` reservations after checking existing `/reserved-memory` `reg`
entries for overlap. The current mainline DT therefore preserves the shipping
pre-LK dynamic CCCI/CONSYS/SCP-share/SPM reservations but does not duplicate
post-LK addresses observed in one live handoff. See the [LK FDT fixup
audit](../../experiments/2026-07-13-lk-fdt-fixup-recovery/README.md).

The live UART console is downstream-specific: `/proc/consoles` names
`ttyMT0` (major 204, minor 209), while `ttyMT1`–`ttyMT3` are auxiliary ports.
The pinned mainline board description deliberately uses the standard
`serial0:921600n8` stdout path and Linux's 8250 MediaTek driver, which normally
creates a `ttyS*` device rather than `ttyMT0`. Because LK rewrites the final
`bootargs` and appends the boot-image command line after its downstream token
mutation, the combined command line and actual console must be checked during
the first reversible mainline boot; a downstream `console=ttyMT0` argument
cannot be assumed to select the mainline console.
See the [UART/console recovery experiment](../../experiments/2026-07-13-uart-console-recovery/README.md).

## SoC resources and buses

| Resource | Observed detail |
| --- | --- |
| Pin controller | MT6797 pinctrl at `0x10005000`; 262 GPIO pins described |
| I2C | Ten controllers, exposed as I2C buses 0 through 9 |
| UART | Four `mtk-uart` devices at `0x11002000` through `0x11005000` |
| Console | Boot arguments named `ttyMT0` at 921600 baud and `tty0` |
| eMMC controller | MSDC0 at `0x11230000`, vendor driver `mtk-msdc` |
| Removable-card controller | MSDC1 at `0x11240000`; card-detect GPIO/EINT 67 described |
| USB 2 host path | Controller at `0x11200000`, vendor MUSB host driver |
| USB 3 device path | Controller at `0x11270000`, vendor MTU3 device driver |
| GPU | Mali node at `0x13040000`, compatible strings include `arm,malit860` and `arm,mali-t86x` |
| Display subsystem | MT6797 display block at `0x14000000` with active vendor display interrupts |
| Interrupt controller | GICv3 at `0x19000000` |

Addresses are observations from this vendor boot contract. They should be
checked against upstream `mt6797.dtsi` before being copied into board code.

The elevated `/proc/iomem` snapshot reported these System RAM extents:

```text
0x40000000-0x445fffff
0x44670000-0x7dfaffff
0x7ff80000-0x87ffffff
0x88600000-0x8effffff
0x90000000-0xbf9fffff
0xbfc00000-0xbfdcffff
0xbfde6000-0xbfdeffff
0xbfff0000-0x13fffffff
```

The gaps correlate with firmware and device reservations. `/proc/iomem` also
confirmed the ten I2C controller windows, SPI controller windows, USB3 regions
at `0x11270000`, `0x11280000`, and `0x11290000`, and the Mali window at
`0x13040000-0x13043fff`.

## Live I2C inventory

The sensor-specific capture and source comparison are recorded in the
[sensor/IIO recovery experiment](../../experiments/2026-07-12-sensor-iio-recovery/README.md).
The live driver names below are vendor 3.18 drivers; they are not Linux 7.1.3
IIO bindings.

The table distinguishes a bound vendor driver from an unbound DT label. A bound
driver is evidence of the software path in this kernel, not always proof of the
exact chip revision.

| Bus/address | DT or modalias name | Live driver | Likely role | Confidence |
| --- | --- | --- | --- | --- |
| 0/`0x25` | `FUSB301_1` | `FUSB301_1` | USB-C switch/role controller 1 | `observed` |
| 0/`0x31` | `speaker_amp` | unbound | Speaker amplifier | `described` |
| 0/`0x53` | `rt9466` | unbound | Alternate charger path | `described` |
| 0/`0x63` | `strobe_main` | unbound | Camera flash | `described` |
| 0/`0x6b` | `sw_charger` | `bq25890` | Charger | `observed` |
| 0/`0x70` | `buck_boost` | `fan49101` | Buck/boost regulator | `observed` |
| 1/`0x25` | `FUSB301_0` | `FUSB301_0` | USB-C switch/role controller 0 | `observed` |
| 1/`0x30` | `mmc3530` | unbound | Magnetometer candidate | `described` |
| 1/`0x3e` | `LP3101` | `LP3101` | LCD bias; vendor name conflicts with LowPowerSemi's non-I2C part, while the register protocol matches TPS65132 | `observed` |
| 1/`0x48` | `alsps` | vendor `stk3x1x` | Ambient-light/proximity sensor | `observed` |
| 1/`0x5f` | `humidity` | unbound | Humidity-sensor candidate | `described` |
| 1/`0x68` | `gsensor_bmi160` | vendor `bmi160_acc` | BMI160-compatible accelerometer path; vendor probe rewrites `i2c_client.addr` to `0x69`; physical part not electrically probed | `observed` |
| 1/`0x69` | `gyro_bmi160` | vendor `bmi160_gyro` | BMI160-compatible gyroscope path; vendor probe also forces `0x69`, so the second legacy client does not prove a second chip | `observed` |
| 1/`0x6a` | `gsensor` | unbound | Alternate LSM6DS3-family accelerometer candidate | `described` |
| 1/`0x6b` | `gyro` | unbound | Alternate LSM6DS3-family gyroscope candidate | `described` |
| 1/`0x77` | `barometer` | unbound | Barometer candidate | `described` |
| 2/`0x2d` | `camera_main` | generic vendor camera binding | Main-camera path | `described` |
| 2/`0x72` | `MAINAF` | `MAINAF` | Main-camera autofocus | `observed` |
| 3/`0x0c` | `SUBAF` | `SUBAF` | Secondary-camera autofocus | `observed` |
| 3/`0x2c` | `AW9120` | `AW9120` | LED controller | `observed` |
| 3/`0x36` | `camera_sub` | generic vendor camera binding | Secondary-camera path | `described` |
| 3/`0x39` | `sii9022` | unbound | HDMI/MHL bridge candidate | `described` |
| 3/`0x50` | `EDID` | unbound | Bridge EDID path | `described` |
| 4/`0x53` | `solomon` | unbound | Alternate touchscreen node | `described` |
| 4/`0x62` | `NVT-ts` | `NVT-ts` | Capacitive touchscreen | `observed` |
| 5/`0x28` | `NFC` | unbound | NFC candidate | `described` |
| 5/`0x5b` | `AW9523` | `AW9523` | Integrated keyboard GPIO/matrix controller | `observed` |
| 6/`0x68` | `DA9214` | `DA9214` | CPU buck regulator | `observed` |
| 7/`0x1c` | `RT5735` | `RT5735` | Regulator | `observed` |
| 7/`0x60` | `VGPU_BUCK` | unbound | GPU buck candidate | `described` |
| 8/`0x36` | `camera_main_hw` | generic vendor camera binding | Main-camera hardware path | `described` |

The generic camera wrapper labels above are not sensor identities. A read-only
runtime capture reports `/proc/AEON_CAMERA0=non_sensor` and
`/proc/AEON_CAMERA1=sp5509mipirawsls`; the corresponding vendor symbols include
`sp5509_MAIN_MIPI_RAW_SensorInit` and `sp5509_MIPI_RAW_SensorInit_sls`.
The camera wrapper buses map to I2C controller windows `i2c2=0x11013000`,
`i2c3=0x11014000`, and `i2c8=0x11009000`; no static sysfs client exists at
candidate `0x20`/`0x28` on those buses. The collector did not probe the bus, so
the exact physical I2C address, register ID, lane/mode timing, orientation, and
autofocus actuator still need a discriminating, non-streaming recovery. See the
[camera recovery experiment](../../experiments/2026-07-13-camera-recovery/README.md).

The external-display candidates are still unverified at runtime: I2C3 `0x39`
(`sii9022_hdmi`) and `0x50` (`siiedid`) are both unbound in the live capture.
The vendor DTS includes an SII9024A-named wiring file with GPIO57 reset, GPIO62
HPD/EINT, GPIO247 1.2 V enable, and DPI GPIO39–54. The immutable vendor
source/ELF checks indexed family ID `0x9022` and TPI byte `0xb0` at register
`0x1b`, so Linux 7.1.3's generic `sii902x` protocol is a reuse candidate; the
reset/rails, 16-bit graph, HPD, and EDID mux still need board evidence. See the
[external-display recovery experiment](../../experiments/2026-07-13-external-display-recovery/README.md);
the private `/dev/hdmitx` node is not mainline evidence.

SPI1 chip select 0 has an unbound `fpc1020` fingerprint candidate. Because the
kernel configuration did not enable that driver and no live device bound, this
does not establish that a fingerprint sensor is fitted. Other `test_spi` nodes
appear to be vendor test scaffolding.
The source-level controller comparison is recorded in the [MT6797 SPI reuse
audit](../../experiments/2026-07-14-upstream-mt6797-coverage-audit/results/spi-mt6797-controller-reuse-20260714.txt):
the vendor register layout matches Linux `spi-mt65xx`'s existing
`mt6765_compat` profile. Patches 0072–0073 now add the MT6797 alias and six
disabled controller nodes with standard clock triplets; mainline pinctrl
groups and runtime transfers remain to be validated. See the [patch
validation](../../experiments/2026-07-14-upstream-mt6797-coverage-audit/results/spi-mainline-patch-validation-c2feb-20260714.txt).
The same capture shows SPI1 GPIO234–237 using an empty default pinctrl state
plus explicit GPIO-function/SPI-function switching states; this is documented
in the [SPI1 pinctrl contract](../../experiments/2026-07-14-upstream-mt6797-coverage-audit/results/spi1-pinctrl-contract-20260714.txt)
and remains open for mainline static-pinctrl validation.

## Storage

| Fact | Confidence | Evidence |
| --- | --- | --- |
| Internal eMMC reports name `DF4064`, manufacturer ID `0x45` | `observed` | Sanitized MMC sysfs fields |
| eMMC manufacturing date reports October 2017 | `observed` | MMC `date` field |
| User capacity is 62,537,072,640 bytes (~58.2 GiB) | `observed` | Block-device size |
| Boot0, boot1, and RPMB areas are each 4 MiB | `observed` | Block-device inventory |
| Root filesystem is ext4 on partition 29 | `observed` | Mount and block inventory |
| No removable MMC device was present | `observed` | Only `mmc0:0001` enumerated during capture |

No reads were made from block-device contents. The absence of a second MMC
device only describes this capture; it is not evidence that the microSD path is
broken. The independent bsg100 Linux 6.6 record provides a useful hardware
cross-check: after correcting MSDC0 to level-low SPI79, adding explicit VEMC /
VIO18 supplies, using the MT2701-generation register profile, and removing
unsupported pinconf, the same DF4064 enumerated with partitions p1–p33. The
current Linux 7.1.3 design preserves those boundaries through a dedicated
MT6797 compatibility record and a 25 MHz first-boot cap; its runtime remains
unverified. See the [MSDC cross-check](../../experiments/2026-07-12-mt6797-msdc-recovery/results/bsg100-msdc-crosscheck-20260714.txt).

## Human interface, display, and audio

| Subsystem | Observation | Confidence |
| --- | --- | --- |
| Keyboard | Separate `Integrated keyboard` input device bound through AW9523 at I2C5 `0x5b`; EINT 10 active. The retained vendor source describes an 8-row × 7-column matrix with a 56-position keymap, including `KEY_UNKNOWN` spare positions and page keys emitted as `KEY_DOWN`/`KEY_UP`; the exact active boot ELF independently compiles the physical Fn position as `KEY_LEFTMETA` and retains the four `KEY_UNKNOWN` entries, resolving the source/build discrepancy for the candidate map. Physical press/release and wake behavior remain untested | `observed` |
| SoC keypad | Separate `mtk-kpd` input device present | `observed` |
| Touchscreen | `mtk-tpd` input device backed by NVT at I2C4 `0x62`; EINT 8 active; live trim bytes `00 00 03 72 66 03` select NT36772 entry 8 / event map `0x11e00`; a separate vendor `solomon_touch@0x53` node is present but unbound | `observed` |
| Hall/lid path | Vendor hall and switch drivers bound; live DT maps GPIO66/EINT5 and GPIO93/EINT16 | `observed` |
| Display | `mtkfb` framebuffer, 1080x2160, 32 bpp; virtual size 1088x4320 | `observed` |
| Display rotation | Vendor config sets physical rotation to 90 degrees | `described` |
| Active panel driver | Debugfs selects `aeon_nt36672_fhd_dsi_vdo_x600_xinli`; 1080x2160, DSI video mode | `observed software selection` |
| Panel controller/module | Vendor driver describes NT36672 ID `0x8070`, four-lane RGB888 burst video; kernel ID callback does not read it; bsg100 hardware logs independently read an AUO/Solomon SSD2092 identity | `identity unresolved` |
| Alternate root-DT panel | `r63419_wqhd_truly_phantom_2k_cmd_ok`, 1440x2560 dual-DSI command mode; observed inactive because `DISP_OPT_USE_DEVICE_TREE=0` | `observed` |
| Audio | One `mt-snd-card` with 31 vendor PCM endpoints | `observed` |
| LEDs | `red`, `green`, and `lcd-backlight` class devices | `observed` |

The post-battery-recovery passive capture keeps both Android switch-class
states at `0`; hall EINT5 has activity while toggle EINT16 is idle. No physical
transition was performed, so the hall polarity and toggle user meaning remain
unverified. See the [sanitized hall/lid recovery result](../../experiments/2026-07-12-hall-lid-switch-recovery/results/live-hall-lid-recovery-20260714.txt).

The live `NVT-ts` probe completed successfully at I2C4 `0x62`, and a fresh
filtered log records trim bytes `00 00 03 72 66 03`, PID `0x0101`, firmware
`0x05`/bar `0xFA`, and IRQ 392. The bytes match masked source/ELF trim-table
entry 8, identifying the live controller family as NT36772 with event map
`0x11e00`; this does not identify it as Linux's NT36672A protocol. See the
[live trim identity](../../experiments/2026-07-12-input-backlight-recovery/results/nvt-live-trim-identity-20260714.txt)
and [NVT ELF validation](../../experiments/2026-07-12-input-backlight-recovery/results/linux-nvt-elf-validation.txt)
for source/binary parity and the remaining transport/runtime gates.
The earlier post-battery-recovery passive capture still shows `cap_touch`
bound to `NVT-ts`, with no `/dev/i2c-4` and no filtered dmesg identity line;
the later focused capture closes that logging gap (see the linked live trim
identity result above).

Patch 0075 records a disabled-by-default NT36772 backend boundary with the
standard regulator/reset/IRQ model and per-message logical-address handling;
its focused object/module and binding checks pass, but no touchscreen DT node,
complete image package, or hardware runtime claim is made. See the
[boundary check](../../experiments/2026-07-12-input-backlight-recovery/results/nt36772-mainline-boundary-20260714.txt)
and [vendor/source protocol comparison](../../experiments/2026-07-12-input-backlight-recovery/results/nt36772-protocol-compare-20260714.txt).

The running LCM name proves software selection, not the precise panel module or
controller suffix. A discriminating physical ID read is still required. The
independent bsg100 direct-probe result names SSD2092, while this named-device
capture selects an NT36672-named LCM. The named device also retains an unbound
`solomon_touch@0x53` candidate and an active NVT touch device at `0x62`, so the
mixed `SSD2092` label in filtered suspend messages cannot be promoted to a panel
identity. These may be panel variants or legacy display/touch labels; the
current evidence cannot decide. See the [normalized bsg100 panel cross-check](../../experiments/2026-07-13-bsg100-gemini-linux-comparison/results/bsg100-panel-crosscheck-20260714.txt).
The R63419 string is an inactive vendor-tree alternative and must not be used
for the initial Gemini display implementation. Audio enumeration does not
establish working speakers, microphones, headset detection, or routing.

## Connectivity and external interfaces

| Subsystem | Observation | Confidence |
| --- | --- | --- |
| Wi-Fi | `wlan0` bound to vendor `mt-wifi`; `consys@18070000` bound to `mtk_wmt`; Android properties select `CONSYS_MT6797`/`0x6797` | `observed` |
| Combo subsystem | WMT status reports internal `MT279`, ROM E1, branch W1715MP, patch 20180307; kernel config selects `CONSYS_6797` and `MT6631_FM` | `observed` |
| Bluetooth | Vendor BTIF driver bound; active TX/RX DMA interrupts and BTIF wake line | `observed` |
| GNSS | Vendor `gps` and `gps_emi` platform drivers bound; `mtk_agpsd` and `/dev/stpgps` present | `observed` |
| Cellular | Separate MD1 CCCI and MD3/C2K CCCI domains are present: 18 `ccmni` and 8 `cc3mni` interfaces, vendor CCCI character nodes, and active CLDMA/CCIF interrupt lines | `observed` |
| USB-C | Two FUSB301 controllers bound on separate I2C buses; both vendor probe logs returned Device ID `0x12`; only the I2C0/GPIO64 path obtained a valid interrupt while I2C1 reported IRQ 0 and `-EINVAL` | `observed` |
| HDMI/MHL | SII9022/EDID DT nodes and a vendor bridge platform driver exist | `described` |

These are enumeration observations, not radio transmission, GNSS-fix,
cellular-call, USB role-swap, or external-display functional tests. Active cellular software makes
an LTE-capable configuration plausible. The later
[vendor-userspace inventory](vendor-userspace.md) found that Android
`build.prop` explicitly targets `Gemini 4G`, although the physical SKU was not
independently inspected.

The CCCI capture confirms that the modem is not a generic PCIe WWAN device. Its
MT6797 APB CLDMA/CCIF windows, vendor clocks, shared-memory layout, and EMI MPU
ownership are separate from Linux 7.1.3's PCIe/DPMAIF `t7xx` transport. Standard
WWAN/TTY/netdev interfaces remain useful above a new MT6797 transport, but the
vendor CCCI character ABI must not be carried into mainline. See the
[modem/CCCI recovery experiment](../../experiments/2026-07-13-modem-ccci-recovery/README.md).

## Power, PMIC, and thermal data

The vendor DT contains an `mt6351` child beneath the PMIC wrapper, and live
drivers include `mt-pmic` and `mt-rtc`. A later bounded wrapper read confirmed
HWCID `0x5140` and SWCID `0x5120`, which the exact vendor source identifies as
MT6351 E2. The method and safe implementation boundaries are recorded in the
[MT6351 PMIC recovery experiment](../../experiments/2026-07-11-mt6351-pmic-recovery/README.md).
The corrected runtime binding capture shows `1000d000.pwrap` unbound while
standalone `mt-pmic` and `mt-rtc` platform devices are bound; all regulator
class devices point at `mt-pmic`. This is a vendor probe-topology difference,
not evidence against the MT6351 identity or against reusing the upstream PWRAP
protocol. The [vendor-to-mainline gap audit](../../experiments/2026-07-14-live-vendor-mainline-gap-audit/README.md)
records the distinction and keeps mainline PWRAP/MT6351 probing as an explicit
first-boot gate.
The current first-boot DT/probe audit shows that the conservative UART+eMMC
path is not PMIC-independent: MSDC0 consumes MT6351 VEMC/VIO18, and PWRAP/MFD
probe writes state even when LK has already initialized the wrapper. See the
[first-boot probe dependency audit](../../experiments/2026-07-14-first-boot-probe-audit/README.md).

Live power-related bindings included BQ25890 at I2C0 `0x6b`, FAN49101 at
`0x70`, DA9214 at I2C6 `0x68`, RT5735 at I2C7 `0x1c`, and LP3101 at I2C1
`0x3e`. A read-only charger capture confirms that `sw_charger` is bound to
BQ25890, `buck_boost` is bound to FAN49101, and the RT9466 node at `0x53` is
unbound despite its `primary_charger` label. During the latest battery-recovery
snapshot, AC was online, USB and wireless charging reported offline, and the
Li-ion battery reported present/Good, Charging, at 91 percent. These are
transient telemetry values, not charger safety validation. The identity and
mainline reuse/new-driver boundary
are recorded in the [charger/fuel-gauge recovery experiment](../../experiments/2026-07-12-charger-power-recovery/README.md).

Plausible thermal readings included battery 24 C, CPU about 25.9 C, PMIC about
26.2 C, and AP 27 C. Several vendor thermal zones returned obvious sentinel or
invalid values, including negative temperatures and a DRAM value of 2; those
values are intentionally excluded from hardware conclusions. A DA9214 zone
reported 60 C, but this single software reading was not independently measured.

The focused 2026-07-13 capture found all 13 vendor thermal zones disabled and
recorded the controller resources at `0x1100b000`/SPI 78 and AUXADC at
`0x11001000`/SPI 74. Vendor procfs exposed enabled calibration fields; their
numeric values remain in the private capture and are intentionally not
reproduced here. Static source recovery maps six logical banks onto five
TS_MCU/ABB inputs and uses three efuse words with an MT6797-specific
raw-to-temperature formula. Linux 7.1.3 has no matching MT6797 thermal or
AUXADC data, so the thermal framework can be reused only above a new
chipset-specific backend. See the [MT6797 thermal recovery
experiment](../../experiments/2026-07-13-mt6797-thermal-recovery/README.md).

The regulator class exposed the following snapshot. Minimum and maximum values
are ranges advertised by the vendor driver; they are not independently verified
board-safe limits and must not be used to justify voltage changes.

| Rail | Snapshot | Advertised range | Users |
| --- | ---: | ---: | ---: |
| `va18` | enabled, 1.800 V | 1.800 V fixed | 0 |
| `vmch` | enabled, 3.000 V | 3.000-3.300 V | 2 |
| `vio28` | enabled, 2.800 V | 2.800 V fixed | 0 |
| `vibr` | disabled, 2.800 V | 1.200-3.300 V | 0 |
| `vcamd` | disabled, 1.210 V | 0.900-1.210 V | 0 |
| `vrf18` | disabled, 1.810 V | 1.000-1.810 V | 0 |
| `vio18` | enabled, 1.800 V | 1.800 V fixed | 0 |
| `vcn18` | enabled, 1.800 V | 1.800 V fixed | 1 |
| `vcamio` | disabled, 1.800 V | 1.200-1.800 V | 0 |
| `vxo22` | enabled, 2.200 V | 1.800-2.800 V | 0 |
| `vtcxo24` | enabled, 2.375 V | 1.800-2.800 V | 0 |
| `vrf12` | disabled, 1.200 V | 0.900-1.200 V | 0 |
| `va10` | disabled, 0.950 V | 0.900-1.800 V | 0 |
| `vdram` | disabled, 1.210 V | 0.900-1.210 V | 0 |
| `vmipi` | enabled, 1.800 V | 0.900-1.800 V | 0 |
| `vgp3` | disabled, 1.810 V | 1.000-1.810 V | 0 |
| `vbif28` | disabled, 2.800 V | 2.800 V fixed | 0 |
| `vefuse` | disabled, 1.800 V | 1.200-1.860 V | 0 |
| `vcn33_bt` | enabled, 3.300 V | 3.300-3.600 V | 1 |
| `vcn33_wifi` | enabled, 3.300 V | 3.300-3.600 V | 1 |
| `vldo28` | disabled, 2.800 V | 2.800 V fixed | 0 |
| `vtcxo28` | disabled, 2.800 V | 1.800-2.800 V | 0 |
| `vmc` | enabled, 3.000 V | 1.200-3.300 V | 2 |
| `vldo28_0` | disabled, 2.800 V | 2.800 V fixed | 0 |
| `vldo28_1` | disabled, 2.800 V | 2.800 V fixed | 0 |
| `vcn28` | enabled, 2.800 V | 1.800-2.800 V | 1 |
| `vcama` | disabled, 2.800 V | 1.500-2.800 V | 0 |
| `vusb33` | enabled, 3.300 V | 3.300 V fixed | 0 |
| `vsim1` | disabled, 3.000 V | 1.700-3.100 V | 0 |
| `vsim2` | disabled, 1.800 V | 1.700-3.100 V | 0 |
| `vemc_3v3` | enabled, 3.000 V | 3.000-3.300 V | 1 |

The class also contained an unused dummy regulator. The missing regulator index
18 is explained by a broken duplicate `vsram_proc` LDO descriptor; the real
VSRAM_PROC is one of nine bucks exposed only through vendor PMIC diagnostics.
Zero user counts remain vendor-kernel implementation details, not evidence that
a physical rail is absent or unused.

## Useful GPIO and interrupt correlations

These correlations come from live pinmux/interrupt debug data and are candidates
for focused experiments, not yet stable board bindings:

| Function | Observed line |
| --- | --- |
| Keyboard AW9523 interrupt | EINT 10 |
| Touchscreen interrupt | EINT 8 / GPIO 85 candidate |
| Ambient-light/proximity interrupt | GPIO 88 candidate |
| microSD card detect | EINT 6 / GPIO 67 candidate |
| HDMI bridge interrupt | GPIO 62 candidate |
| Connectivity GPS-LNA control | GPIO 69; Planet `consys` pinctrl states initialize low and select runtime high/low (source-audited) |
| Camera path | GPIO 33 candidate |
| Keyboard controller | GPIO 87 candidate |
| AW9120 LED path | GPIO 245 candidate |

The decoded 172-entry MT6797 map confirms GPIO67→EINT6, GPIO85→EINT8, and
GPIO88→EINT11. The PMIC uses a dedicated pseudo-GPIO262→EINT176 path; GPIO262
is not a physical member of the SoC's GPIO0–261 register range. A separate
built-in EINT186 can be selected by alternate mux modes on GPIO61, GPIO93,
GPIO107, or GPIO181; it is not part of the ordinary 172-entry mapping table.

The mapping between EINT indices, GPIO numbers, and Linux IRQs needs to be
confirmed against the MT6797 pin controller and by one controlled stimulus per
signal.

## Firmware-reserved memory observed at boot

| Region label | Base | Size |
| --- | ---: | ---: |
| ATF reserved | `0x44600000` | `0x00010000` |
| ATF ramdump | `0x44610000` | `0x00030000` |
| cache dump | `0x44640000` | `0x00030000` |
| preloader reserve | `0x44800000` | `0x00100000` |
| LK reserve | `0x46000000` | `0x00400000` |
| ram console | `0x44400000` | `0x00010000` |
| pstore | `0x44410000` | `0x000e0000` |
| framebuffer | `0x7dfb0000` | `0x01f90000` |
| SCP shared memory | `0x8f000000` | `0x01000000` |
| SCP | `0xbfdf0000` | `0x00200000` |
| connectivity subsystem | `0xbfa00000` | `0x00200000` |
| CCCI region 0 | `0x88000000` | `0x06000000` |
| CCCI region 1 | `0xb4000000` | `0x0a000000` |
| CCCI region 2 | `0xbe000000` | `0x00c00000` |
| ATF log | `0x7ff40000` | `0x00040000` |
| log-store | `0x7ff80000` | `0x00080000` |

The live FDT also contains dynamic, size/alignment-based reservations: a
2 MiB `consys-reserve-memory` block (`no-map`), a 16 MiB `scp_share` block
(`no-map`), a `0x16000`-byte SPM block (`no-map`), and two 4 KiB dummy-read
guards. Their runtime addresses are not fixed by the source DTS. The
`mblock-1-log-store` range is not marked `no-map`, but its name identifies it as
a firmware log owner; treat it as protected until that ownership is disproved.

The `0xbfa00000` connectivity-subsystem entry is the observed allocation of
the vendor `consys-reserve-memory` node (2 MiB, `no-map`, dynamically placed
within the `0x40000000`–`0xc0000000` range). It is not a license to hard-code
that address in a mainline DTS: preserve the dynamic reservation until the
boot-firmware ownership and placement contract is independently reproduced.

These carve-outs describe the 2019 vendor boot chain. They are safety-relevant:
mainline bring-up must preserve firmware-owned ranges until each ownership and
lifetime is understood. They are not a recommendation to reproduce vendor crash
dump features or fixed addresses blindly.

The complete 2026-07-13 read-only capture and source comparison are in the
[memory carve-out recovery experiment](../../experiments/2026-07-13-memory-carveout-recovery/README.md).
It confirms that the generic Linux MT6797 EVB DTS is a contiguous-memory model
and is not a safe Gemini substitute.

## Mainline implications and open questions

This inventory improves component targeting but does not change any runtime
state in the [mainline support matrix](../HARDWARE_SUPPORT.md). Priority follow-up
work is:

1. Obtain a physical/retail variant identifier without recording a unique serial.
2. Compare the live flattened DT against upstream MT6797 resources and create a
   minimal board DT containing only verified, safely sequenced hardware.
3. Verify the PMIC chip identity, regulator rails, consumers, voltage limits,
   and power-domain dependencies before enabling dependent devices.
4. Map the two physical USB-C ports to FUSB301 instances and controller/PHY
   paths using read-only role and attach tests.
5. Confirm the selected panel's NT36672 ID and module variant with a bounded
   DSI read; recover the SP5509 camera's discriminating ID/address/lane contract
   and the MT6797 SENINF/ISP pipeline rather than treating generic DT labels as
   sufficient.
6. Stimulate keyboard, touch, lid, card detect, and sensor interrupts one at a
   time to establish GPIO/EINT mappings.
7. Document firmware/calibration ownership for connectivity and modem paths;
   never commit extracted blobs or device-unique NVRAM. The initial
   [firmware boundary inventory](firmware.md) now records the installed set.
