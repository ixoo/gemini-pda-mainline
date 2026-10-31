# MT6797 thermal management and calibration

Scope: the named MT6797X Gemini PDA and the vendor Android/3.18 stack it
shipped with. This document records how temperature is measured, calibrated,
converted and acted on, and which firmware owns each step. It is a static
source, firmware and document study. It does not claim mainline thermal
protection, throttling, cooling or suspend support; runtime status stays in the
[hardware support matrix](../HARDWARE_SUPPORT.md), and the evidence chronology
is in the [thermal management experiment](../../experiments/2026-10-31-mt6797-thermal-management/README.md).

Confidence terms follow the [hardware knowledge base](README.md) convention.

## 1. Sensing topology

The thermal controller is a 4 KiB block at `0x1100b000`, IRQ `GIC_SPI 78`,
clock `INFRA_THERM`, and shares its register window with the EEM/PTP block
(`PTPCORESEL`/`EEMCORESEL` at offset `0x400`). It reads four on-die diode
sensors (`TS_MCU1..4`) plus the ABB sensor through AUXADC channel 11, using
bank selection rather than simultaneous conversion.

| Bank | Role stated by the vendor source | Sensor(s) |
| --- | --- | --- |
| 0 | BIG (Cortex-A72) | `MCU1` |
| 1 | GPU | `MCU4` |
| 2 | SOC | `MCU2`, `MCU3` (maximum is reported) |
| 3 | CPU-L | `MCU2` |
| 4 | CPU-LL | `MCU2` |
| 5 | MCUCCI | `MCU2` |

Vendor source: `drivers/misc/mediatek/thermal/mt6797/src/mtk_tc.c`
(`planet-community/android_kernel_planetcom_mt6797` commit `8cfe6596`) lines
70-102, 600-640, 1084-1122. Sampling is 2-of-4 hardware filtering
(`TEMPMSRCTL0 = 0x492`), about 18 ms sensor interval, with a different interval
for bank 0.

Freshness: the driver reads `TEMPMSR0..3 & 0xfff` with no status bit. Its
only validity mechanism is a first-valid gate. `tscpu_thermal_fast_init`
seeds every bank with the sentinel `0xDA1` (`THERMAL_INIT_VALUE`,
`tscpu_settings.h:106`; `mtk_tc.c:990-1080`), and `check_all_temp_valid`
treats temperatures as valid once no reading still equals it
(`mtk_ts_cpu.c:2170-2184`). This proves one conversion per sensor since
setup, and is the same read-before-arm order the 117 °C trip needs. It gives
no per-read age. The mainline variant has no such gate yet.

The public MT6797 documents do **not** enumerate these sensors. The functional
specification says only that "several embedded temperature sensors" feed the
thermal controller (FS v1.0 p.188) and marks AUXADC channels 10 and 11
"Internal use" (p.115-116). The register tables contain no thermal-controller
chapter; only its clock gate (`0x10001080` bit 10), software reset
(`0x10001120` bit 0) and TOPRGU request bits are documented. The bank/sensor
map above is therefore vendor-source evidence, not datasheet evidence.

## 2. Calibration: efuse → LK → `atag,devinfo` → driver

The driver does not read the efuse controller. It calls
`get_devinfo_with_index()` on a RAM array populated from the flat device tree
property `/chosen/atag,devinfo` (`devinfo/v1/devinfo.c:275-295`), which LK
writes as 100 words read from the efuse data registers
(`lk/platform/mt6797/atags.c:196-206`, LK commit `f4988d74`). The three words
used by the thermal driver are indices 31, 32 and 33, corresponding to the
efuse registers `0x10206180`, `0x10206184` and `0x10206188`
(`tscpu_settings.h:122-124`).

| Field | Word | Bits | Default | Accepted range |
| --- | --- | --- | --- | --- |
| `ADC_GE_T` | 32 | 31:22 | 512 | 265-758 |
| `ADC_OE_T` | 32 | 21:12 | 512 | 265-758 |
| `O_VTSMCU1` | 31 | 25:17 | 260 | ≤484 |
| `O_VTSMCU2` | 31 | 16:8 | 260 | ≤484 |
| `O_VTSMCU3` | 32 | 8:0 | 260 | ≤484 |
| `O_VTSMCU4` | 33 | 31:23 | 260 | ≤484 |
| `O_VTSABB` | 33 | 22:14 | 260 | ≤484 |
| `DEGC_cali` | 31 | 6:1 | 40 | 1-63 |
| `ADC_CALI_EN_T` | 31 | 0 | — | 1 = calibrated |
| `O_SLOPE_SIGN` | 31 | 7 | 0 | — |
| `O_SLOPE` | 31 | 31:26 | 0 | forced 0 when `ID=0` |
| `ID` | 32 | 9 | 0 | 0 = TSMC sample |

When `ADC_CALI_EN_T` is 0 the driver warns "not Thermal calibrated" and uses the
defaults (`mtk_tc.c:465-480`). The same words feed EEM voltage calibration
(devinfo 50-66); an all-zero devinfo disables EEM entirely
(`base/power/mt6797/mt_eem.c:4964-4972`). Mainline exposes only the ordered
12-byte thermal cell (`0057a-nvmem-mediatek-add-MT6797-LK-calibration-provider.patch`)
and requires it to be valid before conversion (`0512-thermal-mediatek-require-valid-MT6797-calibration.patch`).

## 3. Temperature conversion

### 3.1 SoC diodes (authoritative formula)

The vendor formula (`raw_to_temperature_roomt()`, `mtk_tc.c:553-590`) and its
mainline port (`raw_to_mcelsius_v4()` in
`0057-thermal-mediatek-add-MT6797-AUXADC-support.patch`) are:

```
gain    = 10000 + (ADC_GE_T - 512) * 10000 / 4096
oe      = ADC_OE_T - 512
x_roomt = (((O_VTS + 3350 - oe) * 10000 / 4096) * 10000) / gain
u       = ((raw - oe) * 10000 >> 12) * 10000 / gain - x_roomt
u       = u * 15 / 18
delta   = u * 1000 / (1663 + O_SLOPE * 10)      /* sign 0 */
delta   = u * 1000 / (1663 - O_SLOPE * 10)      /* sign 1 */
T_0.1C  = (DEGC_cali * 10 / 2) - delta
```

`raw` is `TEMPMSR0..3 & 0xfff`; `x_roomt` uses the bank's dominant sensor
(bank 0 → `MCU1`, bank 1 → `MCU4`, banks 2-5 → `MCU2`). All arithmetic is
signed integer with truncation at each step, so repeatability is exact but the
result is not a floating-point conversion. `raw == 0` returns 0 °C.

The same calibration produces the slope/intercept pair `ts_MTS`/`ts_BTS` that
is programmed into EEM (`mtk_tc.c:258-338`, `mt_eem.c:2259-2261`) and into the
SPM suspend VCORE protection (`spm_v2/mt_spm.c:1924-1981`), so the thermal
calibration also defines the voltage controller's temperature scale.

### 3.2 PMIC die temperature (MT6351)

A separate Vbe-based conversion uses PMIC OTP/efuse words 0 and 1
(`thermal/mt6797/src/mtk_pmic_efuse.c:62-183`); the channel and register
interface of the PMIC ADC itself are documented in
[MT6351 PMIC auxiliary ADC](mt6351-pmic-adc.md):

```
O_VTS       = (word1[3:0] << 9) | (word0[15:7])
DEGC_cali   = word0[6:1]
O_SLOPE     = word1[10:5]      (sign in word1[4])
vbe_t       = -((O_VTS * 1800) / 4096) * 1000
intercept   = (vbe_t * 1000) / -(1598 ± O_SLOPE * 10) + DEGC_cali * 500
T           = intercept + (1000000 * raw) / -(1598 ± O_SLOPE)
```

Note the asymmetry in the vendor code: the slope term is multiplied by 10 in
the intercept but not in the per-count denominator.

`raw` is PMIC AUXADC channel 4. Uncalibrated parts fall back to
`O_VTS=1600`, `DEGC_cali=50`, slope 0; `DEGC_cali` outside 38-60 is clamped to
53 by an MT6755 workaround. The source comments mix 0.1 °C and 0.001 °C
scaling, so the unit of the returned value is treated as 0.001 °C only because
the zone wrapper expects millidegrees; the arithmetic itself is unverified.

### 3.3 Other temperature sources

| Source | Method | Evidence |
| --- | --- | --- |
| Board NTC (`mtktsAP`, `mtktsbtsmdpa`) | AUXADC NTC channel, 390 kΩ pull-up, `mV = raw*1500/4096`, `R = 390000*mV/(1800-mV)`, interpolated over a −40…125 °C table | `common/thermal_zones/mtk_ts_bts.c:123-130, 472-577` |
| Battery pack | battery NTC read on PMIC ADC channel 3 (`BATON`), converted with the board NTC table | [PMIC ADC](mt6351-pmic-adc.md); `power/mt6797/battery_meter_hal.c:1140-1180` |
| Modem RF/PA | modem-reported `RFTEMP_*` attributes; −127 °C when unavailable | `common/thermal_zones/mtk_ts_pa.c:170-218` |
| Modem ADC | baseband NVRAM table (`l1cal_temperatureADC_T`), exposed over the PMIC-wrapper modem ADC path | retained modem image strings; register table part 1 p.608, 662 (`MD_ADC_STA0[31:16]`) |
| Wi-Fi/BT combo | WMT command (`WMT_THERM_READ_CMD`) returning a raw value; observed live as `[Thermal] current_temp = 0x12/0x15` | vendor `mtk_ts_wmt.c`; retained Gemian log |
| DDR | JEDEC derating index 0-7, not a temperature | `mtk_ts_dram.c:71-92` |
| Camera | values pushed by the camera stack, invalid sentinel −275000 | `mtk_ts_imgsensor.c:62-79` |

The datasheets contain **no** conversion equation, reference temperature or
calibration procedure for the on-die sensors, and the register tables contain
no access to `0x10206180`/`84`/`88`. The formulas above are recovered from the
vendor driver, not from the documents.

## 4. Protection thresholds and actions

| Domain | Threshold | Action | Evidence |
| --- | --- | --- | --- |
| CPU hotspot | 117 °C | Hardware: `TEMPPROTTC` + `TEMPMONINT[31]` (SPM state2), TOPRGU "thermal direct reset" armed | `mtk_tc.c:899-923, 1207-1259` |
| CPU hotspot | 117 °C | Software: `mtktscpu-sysrst` writes to address 0 (data abort/reset) | `mtk_cooler_sysrst.c:71` |
| CPU hotspot | 120 °C | Thermal-zone critical trip | `tscpu_settings.h:179` |
| CPU | 95 °C / 85 °C | Static CPU power clamp (`cpu00` / `cpu03`) | `tzcpu_initcfg.h:24-28` |
| CPU | 65 °C | Adaptive power-budget loop starts (target Tj 75 °C, exit 55 °C) | `tzcpu_initcfg.h:30-31`, `clatm_initcfg.h:19-28` |
| CPU (EEM) | ≤33 °C | +62.5 mV voltage bump | `mt_eem.c:3519-3523` |
| Battery / board NTC | 60 °C | Zone critical, no bound cooler in kernel | `mtk_ts_battery.c:83`, `mtk_ts_bts.c:87` |
| Modem/PA | 85 °C | Zone critical and software reset | `mtk_ts_pa.c:49,59,80` |
| PMIC (MT6351) | 150 °C | Zone critical and software reset; hardware shutdown 150 °C, release 110 °C | `mtk_ts_pmic.c:421`, PMIC datasheet p.18 |
| PMIC regulation | ≈125 °C / 110 °C | `THR_H`/`THR_L` interrupt pair (adjustable, 50 ms debounce) | PMIC datasheet p.59-60 |
| DDR | 125 °C / 110 °C | Reset / `cpu01` clamp | `mtk_ts_dram.c:52-53` |
| Camera | 125 °C | `cpu03` clamp | `mtk_ts_imgsensor.c:46` |

TOPRGU carries the reset request: `0x1000700c` bit 18 reports an asserted
thermal reset, `0x10007030` bit 18 enables it, and `0x10007034` bit 18 converts
it to an IRQ instead of a reset (register table part 1 p.593-604). The vendor
driver arms that route only after programming the thresholds.

Only `mtktscpu` is kernel-polled (40 ms; 20 ms above 60 °C; 160 ms below
20 °C). Every other zone registers with `interval = 0` and therefore only
reads on demand; their trip points do not fire on their own unless userspace or
another kernel path polls them.

Those are the kernel's built-in defaults. On the stock Android boot the
userspace policy writer replaces them through the driver's procfs nodes with
different values, including a 110 °C CPU reset, 58/57 °C adaptive-cooler
entries and battery charge throttling from 46 °C (§7). Which set is active
therefore depends on whether `thermal_manager` ran; the kernel defaults are the
fallback, not the shipped policy. The retained Gemian build runs no Android
thermal manager, so its effective protection is the kernel default set: the
117 °C hardware reset, the 95/85 °C clamps and the device-tree 50/47 °C charge
window.

## 5. Policy chain

The cooling stack produces **milliwatt power budgets**, not frequencies:

```
thermal zone → cooler (ATM/DTM) → ap_thermal_limit MIN arbitration
             → mt_ppm_cpu_thermal_protect(budget)
             → PPM v1 budget→OPP search → mt_cpufreq limit
```

- `cpu00`-`cpu33` are static budget steps; `cpu_adaptive_0..2` run the
  adaptive power-budget loop (PHPB variant; Tj 75 °C, 300-3960 mW CPU,
  800-2000 mW GPU, 2/8 °C gain terms) (`mtk_cooler_dtm.c`, `mtk_cooler_atm.c`,
  `clatm_initcfg.h`).
- GPU budgets go to `mt_gpufreq_thermal_protect()`; no DDR frequency cooler
  exists.
- PPM v1 is AP-side and table-driven; in this tree it runs inline in the
  caller's context (the PPM kthread is compiled out), so a thermal transition
  executes on the polling path (`ppm_v1/src/mt_ppm_main.c:516-532`).
- Further coolers exist but are unbound by default: charging current
  (`bcct`), frame rate (`fps`), modem TX/UL (`mutt`/`amutt`, requires
  `CONFIG_MTK_THERMAL_PA_VIA_ATCMD`), backlight, camera flag, shutdown,
  kernel power-off.
- The hybrid CPU DVFSP integration (`CONFIG_MTK_HYBRID_CPU_DVFS`) is **not**
  enabled in the Android defconfigs or in the retained Gemian configuration,
  so the AP performs CPU DVFS in software. The CSPM DVFSP firmware still exists
  as a hardware resource and is the subject of the project's I2C6/DA921x
  handoff work; how its autonomous state relates to a non-hybrid AP DVFS build
  is unresolved.

## 6. Firmware roles

| Firmware | Thermal role | Evidence |
| --- | --- | --- |
| Preloader | Contains an efuse data-register table including `0x10206180/84/88`, selects CPU DVFS tables (`MT_CPU_DVFS_B/L/LL`) and sets VCORE/VSRAM from EEM calibration; no temperature polling found | retained preloader strings and efuse-register table |
| LK | Reads 100 efuse words and passes `/chosen/atag,devinfo`; `atag,ptp` voltage tagging is disabled for MT6797 | LK source `atags.c:196-206`; retained LK strings |
| ATF/TEE | AArch64 secure firmware with an ARMPLL/POSDIV "iDVFS" path; no thermal thresholds | retained TEE strings; no thermal symbols |
| SCP (TinySys CM4) | FreeRTOS with only DMA, DVFS, IPI and SPM modules; PWRAP access and IPI OPP limits for its own clock domain; no thermal sensor or trip code found | retained SCP image strings and module list |
| DVFSP / CSPM | PCM firmware in the SoC CSPM microcontroller; owns CPU DVFS/I2C6 on the vendor stack when active; not part of the SCP image | vendor `mt_cpufreq_hybrid.c`; project I2C6 handoff evidence |
| SPM PCM (`pcm_*.bin`) | Sleep/deep-idle and VCORE-DVFS instruction images; no readable policy | retained vendor firmware set |
| Modem | Own temperature-ADC calibration from NVRAM, throttling levels, `+ETHERMAL`/`+EADC` commands, and a CCCI sysmsg callback the AP can use to request modem thermal mitigation | retained modem image strings |
| Wi-Fi | Autonomous `THERM_THERMCR0` thermal loop with lower/upper bounds and overheat handling for RF calibration; AP queries it through WMT | retained Wi-Fi image strings; live `WMT_THERM_READ_CMD` log |

No firmware blob was found to implement the SoC thermal *policy*; the
temperature decisions are AP-kernel and userspace work, with firmware acting as
calibration and actuation.

## 7. Userspace policy (Android)

The stock Android device tree ships `configs/.tp/thermal.conf`,
`.thermal_policy_00..03`, `thermal.off.conf` and `.ht120.mtc`, plus the vendor
daemons `thermal`, `thermal_manager`, `thermald`, `thermalloadalgod`,
`thermalindicator`, `thermal.mt6797.so` and libraries `libmtcloader.so` and
`libthermalalgo.so`.

The `.tp` files are not cryptographically protected: `libmtcloader.so` applies a
per-line Caesar rotation over the 91 printable ASCII characters, with a
period-10 key indexed by the column position, and passes line breaks through.
The decrypted format is a flat list of two-line records — a `/proc` path
followed by the value written verbatim into it — terminated by `EOF`. No
temperature constant is compiled into any thermal daemon or HAL; the shipped
trip points come from that data. The codec is reproduced in the
[experiment script](../../experiments/2026-10-31-mt6797-thermal-management/scripts/mtk-tp-policy.py).

`thermal_manager` runs as root at boot, loads `thermal.conf`, and writes the
records into `/proc/driver/thermal/tz*` (zone trips and cooler bindings) and
`/proc/mtkcooler/*` (cooler parameters). Zone-to-cooler mapping is therefore
data-driven, not compiled in. `libthermalalgo.so` computes a target junction
temperature from PCB temperature over a netlink socket for the adaptive CPU
coolers; `thermald` and `thermalindicator` only report.

Recovered boot-default policy (`thermal.conf`), selected entries:

| Zone | Trips (temperature / cooler) |
| --- | --- |
| CPU | 110 °C `mtktscpu-sysrst`, 58 °C `cpu_adaptive_0`, 57 °C `cpu_adaptive_1` |
| PMIC | 145 °C `mtktspmic-sysrst` |
| Battery | 60 °C `mtktsbattery-sysrst`, 48/47/46 °C `mtk-cl-bcct02/01/00` |
| Board + modem PA | 100 °C `mtktspa-sysrst`, 57 °C camera, 56 °C LCD-off charge limit, 50 °C frame-rate cap, 47 °C adaptive charge current |
| Modem/PA | 120 °C `mtk-cl-shutdown02`, 110 °C `mtk-cl-mdoff`, 100 °C `mtk-cl-noIMS`, 57 °C adaptive modem throttling |
| WMT / PA / DRAM / DA9214 | 120 °C / 120 °C / 200 °C / 200 °C reset coolers |
| Auxiliary sensors 1/2/4 | 150 °C staged power-off |

The policy revisions differ mainly in how aggressively the adaptive CPU and
charge-current coolers are parameterised; `_03` adds camera coolers at
90-100 °C, `thermal.off.conf` keeps only reset and shutdown coolers, and
`.ht120.mtc` is a minimal 117 °C profile without a battery zone. The battery,
not the SoC, is the thermally constrained subsystem: charging is reduced from
46 °C while the CPU is only reset at 110 °C.

The retained Gemian device tree independently encodes the same priority in the
battery node: a 17-entry NTC table, a charge window of 0-50 °C with 47 °C and
6 °C boundary offsets, and charge-error temperature 255 (disabled). Those values
come from the working vendor boot and match the charge-throttling temperatures
above.

This layer has no mainline equivalent and is not required for kernel support,
but any runtime thermal claim on the vendor stack must state whether these
overrides were applied.

## 8. What mainline has and lacks

| Piece | State |
| --- | --- |
| MT6797 AUXADC-thermal variant, V4 conversion, calibration decode | Implemented, off by default (`0057`, `0512`, `0517`) |
| LK `atag,devinfo` calibration provider | Implemented, read-only (`0057a`) |
| Temperature observation | Demonstrated on hardware; accuracy and cross-boot repeatability unresolved |
| Hardware trip at 117 °C (SPM state2 / TOPRGU) | Not implemented |
| Cooling devices, trips, cpufreq/OPP integration | Not implemented |
| PMIC die-temperature monitoring | No mainline driver; MT6351 is only an MFD/regulator child |
| Modem / Wi-Fi thermal interaction | Outside mainline scope; no CCCI or WMT consumer |
| Board NTC and battery temperature | No mainline mechanism yet |
| BQ25896 TS input (hardware JEITA) | TS read 49.8% of REGN in all 54 reads across four boots, charging or not (likely a fixed divider, not the NTC; inference), so the charger's own temperature cutoffs most likely never act |
| TOPRGU thermal route under mainline | Unread; one `devmem` read on the next station boot |

## 9. Open questions

1. Which DTB the shipped vendor boot used: the vendor driver looks up
   `mediatek,INFRACFG_AO`/`APMIXED` in upper case while the tree's DTS uses
   lower case, with `BUG_ON` on failure.
2. Whether `/chosen/atag,devinfo` is present on a normal Gemini boot (it
   decides whether calibration and EEM are live).
3. Whether the 117 °C hardware path really resets the SoC on this unit
   (vendor comment claims a 30 s fallback).
4. The real `ts_MTS`/`ts_BTS` values and the absolute accuracy of the converted
   temperature against an independent sensor.
5. The intended division of labour between the non-hybrid AP DVFS build and the
   CSPM DVFSP firmware.
6. Which `.tp` policy a given SKU actually selects at runtime, whether
   `.ht120.mtc` is ever loaded, and the exact meaning of the trip-tuple middle
   and trailing fields.

## Evidence index

- Vendor kernel tree `planet-community/android_kernel_planetcom_mt6797`,
  commit `8cfe6596a503612e3332d9c26e292a19525a7f07`.
- LK tree `dguidipc/gemini-lk-android8`, commit
  `f4988d74bb70a0a15d7f362f412afba7e7fcda46`.
- Retained private firmware captures and the installed Gemian vendor firmware
  set; redistribution status is recorded in the [firmware boundary](firmware.md).
- MT6797 Functional Specification v1.0, register table parts 1 and 2, MT6351
  PMIC datasheet v12, MT6631 external datasheet (vendor documents).
- Mainline patches `0046`, `0057`, `0057a`, `0203`-`0245`, `0512`,
  `0513`, `0517` in `patches/v7.1.3/`.
- [Thermal management experiment](../../experiments/2026-10-31-mt6797-thermal-management/README.md).
- Running station-protection study: [what thermal protection the station
  needs](../../experiments/2026-10-31-gemini-thermal-protection/README.md).
