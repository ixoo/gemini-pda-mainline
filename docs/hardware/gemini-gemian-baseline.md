# Gemini PDA Gemian hardware baseline

This document records the software-visible hardware of one Gemini PDA running
Gemian. It is a starting point for a mainline device tree, not proof that any
component works on the repository's current upstream kernel.

## Provenance and scope

| Field | Value |
| --- | --- |
| Observation date | 2026-07-11 |
| Device access | Owner-authorized read-only SSH collection on a private LAN |
| OS | Debian GNU/Linux 9 (stretch), Gemian userspace |
| Kernel | `3.18.41+`, build `#7 SMP PREEMPT Fri Mar 29 10:39:03 GMT 2019` |
| Architecture | AArch64 |
| Device-tree model | `MT6797X` |
| Root compatible | `mediatek,MT6797` |
| Device variant | Installed Android image identifies `Gemini 4G`; physical SKU not independently established |
| Collector | [`collect.sh`](../../experiments/2026-07-11-gemian-hardware-inventory/scripts/collect.sh) |
| Experiment record | [2026-07-11 Gemian hardware inventory](../../experiments/2026-07-11-gemian-hardware-inventory/README.md) |

The collector removed unique identifiers and did not read eMMC CID, filesystem
UUIDs, MAC addresses, IMEI/MEID values, calibration data, firmware, partitions,
or user files. Although passwordless sudo was expected, `sudo -n` required a
password on this installation. The owner later supplied the password for a
transient interactive session, allowing read-only collection of `/proc/iomem`.
The vendor kernel does not provide a regulator summary file, but its regulator
class is readable. No credential was stored and no remote state was changed.

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
| Only CPU0 and CPU1 were online during capture | `observed` | `/sys/devices/system/cpu/{online,offline}` and `lscpu`; CPUs 2-9 offline |
| Boot command line constrained the system to five CPUs | `observed` | Sanitized boot arguments contained `maxcpus=5` |
| Online cores used the vendor `mt-cpufreq` driver | `observed` | CPU0 cpufreq sysfs |
| CPU0 range was 221 MHz to 1.547 GHz | `observed` | `cpuinfo_min_freq=221000`, `cpuinfo_max_freq=1547000` kHz |
| GICv3 and ARMv8 architectural timer | `observed` | DT compatible nodes and live interrupts |
| PSCI 0.2 firmware interface | `observed` | DT PSCI node |
| Approximately 3.68 GiB usable RAM | `observed` | `MemTotal: 3860680 kB` |

The CPU observation does not establish why only two cores were online. The boot
limit, thermal/hotplug policy, and vendor power-management behavior are all
possible contributors and need a controlled experiment.

## SoC resources and buses

| Resource | Observed detail |
| --- | --- |
| Pin controller | MT6797 pinctrl at `0x10005000`; 262 GPIO pins described |
| I2C | Ten controllers, exposed as I2C buses 0 through 9 |
| UART | Four `mtk-uart` devices at `0x11002000` through `0x11005000` |
| Console | Boot arguments named `ttyMT0` at 921600 baud and `tty0` |
| eMMC controller | MSDC0 at `0x11230000`, vendor driver `mtk-msdc` |
| Removable-card controller | MSDC1 at `0x11240000`; card-detect EINT 6 described |
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
| 1/`0x3e` | `LP3101` | `LP3101` | LCD bias | `observed` |
| 1/`0x48` | `STK3X1X` | `STK3X1X` | Ambient-light/proximity sensor | `observed` |
| 1/`0x5f` | `humidity` | unbound | Humidity-sensor candidate | `described` |
| 1/`0x68` | `BMI160` | BMI160 accelerometer driver | Accelerometer | `observed` |
| 1/`0x69` | `BMI160` | BMI160 gyroscope driver | Gyroscope | `observed` |
| 1/`0x6a` | `gsensor` | unbound | Alternate accelerometer node | `described` |
| 1/`0x6b` | `gyro` | unbound | Alternate gyroscope node | `described` |
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

SPI1 chip select 0 has an unbound `fpc1020` fingerprint candidate. Because the
kernel configuration did not enable that driver and no live device bound, this
does not establish that a fingerprint sensor is fitted. Other `test_spi` nodes
appear to be vendor test scaffolding.

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
broken.

## Human interface, display, and audio

| Subsystem | Observation | Confidence |
| --- | --- | --- |
| Keyboard | Input device bound through AW9523 at I2C5 `0x5b`; EINT 10 active | `observed` |
| SoC keypad | Separate `mtk-kpd` input device present | `observed` |
| Touchscreen | `mtk-tpd` input device backed by NVT at I2C4 `0x62`; EINT 8 active | `observed` |
| Hall/lid path | Vendor hall and switch drivers bound | `observed` |
| Display | `mtkfb` framebuffer, 1080x2160, 32 bpp; virtual size 1088x4320 | `observed` |
| Display rotation | Vendor config sets physical rotation to 90 degrees | `described` |
| Panel | DT compatible contains `r63419_wqhd_truly_phantom_2k_cmd_ok` | `described` |
| Audio | One `mt-snd-card` with 31 vendor PCM endpoints | `observed` |
| LEDs | `red`, `green`, and `lcd-backlight` class devices | `observed` |

The panel string is a vendor DT selection and must not be treated as a verified
panel part number until compared with a physical identifier or discriminating
probe. Audio enumeration does not establish working speakers, microphones,
headset detection, or routing.

## Connectivity and external interfaces

| Subsystem | Observation | Confidence |
| --- | --- | --- |
| Wi-Fi | `wlan0` bound to vendor `mt-wifi`; connectivity driver `mtk_wmt` | `observed` |
| Combo subsystem | Kernel config selects `CONSYS_6797` and `MT6631_FM` | `described` |
| Bluetooth | Vendor BTIF driver bound with active TX/RX interrupts | `observed` |
| GNSS | Vendor `gps` platform driver bound | `observed` |
| Cellular | CCCI/CLDMA interrupts and numerous `ccmni`/`cc3mni` interfaces present | `observed` |
| USB-C | Two FUSB301 controllers bound on separate I2C buses | `observed` |
| HDMI/MHL | SII9022/EDID DT nodes and a vendor bridge platform driver exist | `described` |

These are enumeration observations, not radio, GNSS-fix, cellular-call, USB
role-swap, or external-display functional tests. Active cellular software makes
an LTE-capable configuration plausible. The later
[vendor-userspace inventory](vendor-userspace.md) found that Android
`build.prop` explicitly targets `Gemini 4G`, although the physical SKU was not
independently inspected.

## Power, PMIC, and thermal data

The vendor DT contains an `mt6351` child beneath the PMIC wrapper, and live
drivers include `mt-pmic` and `mt-rtc`. This confirms the vendor software
description, not an independent read of the PMIC's chip ID.

Live power-related bindings included BQ25890 at I2C0 `0x6b`, FAN49101 at
`0x70`, DA9214 at I2C6 `0x68`, RT5735 at I2C7 `0x1c`, and LP3101 at I2C1
`0x3e`. During the snapshot, AC was online, USB and wireless charging reported
offline, and the Li-ion battery reported full/good at 100 percent. These are
transient telemetry values, not charger safety validation.

Plausible thermal readings included battery 24 C, CPU about 25.9 C, PMIC about
26.2 C, and AP 27 C. Several vendor thermal zones returned obvious sentinel or
invalid values, including negative temperatures and a DRAM value of 2; those
values are intentionally excluded from hardware conclusions. A DA9214 zone
reported 60 C, but this single software reading was not independently measured.

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

The class also contained an unused dummy regulator. A missing regulator index
and zero user counts are vendor-kernel implementation details, not evidence that
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
| Connectivity subsystem | GPIO 69 candidate |
| Camera path | GPIO 33 candidate |
| Keyboard controller | GPIO 87 candidate |
| AW9120 LED path | GPIO 245 candidate |

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

These carve-outs describe the 2019 vendor boot chain. They are safety-relevant:
mainline bring-up must preserve firmware-owned ranges until each ownership and
lifetime is understood. They are not a recommendation to reproduce vendor crash
dump features or fixed addresses blindly.

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
5. Identify panel and camera silicon with discriminating reads rather than DT
   labels.
6. Stimulate keyboard, touch, lid, card detect, and sensor interrupts one at a
   time to establish GPIO/EINT mappings.
7. Document firmware/calibration ownership for connectivity and modem paths;
   never commit extracted blobs or device-unique NVRAM. The initial
   [firmware boundary inventory](firmware.md) now records the installed set.
