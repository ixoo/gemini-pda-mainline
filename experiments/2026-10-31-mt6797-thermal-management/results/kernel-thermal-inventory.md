# Vendor Android 3.18 thermal stack inventory — Gemini PDA (aeon6797_6m_n / MT6797X)

Scope: static reading of the MediaTek vendor kernel tree

- Tree: vendor kernel checkout at commit `8cfe6596a503612e3332d9c26e292a19525a7f07`
  (`planet-community/android_kernel_planetcom_mt6797`, branch master)
- Project config used as the reference: `arch/arm64/configs/aeon6797_6m_n_defconfig`
  (also `_debug`, `_halium`, `_hybris` — all four set `CONFIG_THERMAL=y`,
  `CONFIG_MTK_THERMAL_PA_VIA_ATCMD=y`, `CONFIG_MTK_COMBO_WIFI=y`;
  e.g. `arch/arm64/configs/aeon6797_6m_n_defconfig:188,251,391`)

All paths below are relative to the tree root. Every claim is tagged with `path:line`.

Legend used throughout:

- **PRESENT** = code exists in this tree.
- **BUILT** = compiled for MTK_PLATFORM=mt6797 with the reference defconfig.
- **LIVE** = actually registered/programmed at boot in this configuration.
- **DEAD** = compiled (or not) but never effective for this project.

---

## 0. Executive summary

| Item | Finding |
|---|---|
| Thermal controller | `mediatek,mt6797-therm_ctrl` at `0x1100B000` (4 KiB), IRQ `GIC_SPI 78`, clock `INFRA_THERM` ("therm-main") — `arch/arm64/boot/dts/mt6797.dtsi:2495-2501` |
| Sensor banks | 6 banks / 5 diode sensors (MCU1..MCU4, ABB); A72 "BIG" = bank0/MCU1, GPU = bank1/MCU4 |
| Calibration source | devinfo words 31/32/33, which on this platform come from the **LK/preloader `atag,devinfo` blob**, not from a kernel efuse read (`drivers/misc/mediatek/devinfo/v1/devinfo.c:275-340`) |
| HW protection trip | programmed to **117 °C** into `TEMPPROTTC` + `TEMPMONINT[31]` (SPM state2) with RGU "thermal direct reset" armed (`mtk_tc.c:1207-1259`) |
| SW polling | `mtktscpu` zone polls every **40 ms**, 20 ms above 60 °C, 160 ms below 20 °C |
| Active thermal zones at boot | mtktscpu, mtktsbattery, mtktsAP (board NTC), mtktsbtsmdpa, mtktspmic, mtktspa, mtktsdram, mtktsimgsensor, tsda9214, mtktswmt |
| Effective cooling | CPU power budget (ATM + DTM) → `mt_ppm_cpu_thermal_protect()` → PPM v1 → `mt_cpufreq`; GPU power budget → `mt_gpufreq_thermal_protect()`; plus 117 °C reset cooler |
| PPM | **ppm_v1** for MT6797 (`drivers/misc/mediatek/base/power/Makefile:17`); ppm_v2 is MT6757 only (`:18`) |
| DVFSP / HW-GOV | compiled **out**: `CONFIG_HYBRID_CPU_DVFS` is not set in any aeon defconfig |
| PTP/EEM | `mt_eem.c` (no `mt_ptp.c` exists); thermal slope/intercept (`ts_MTS`/`ts_BTS`) is programmed into `EEM_TSCALCS` per bank and drives per-cluster voltage |

---

## 1. Thermal controller driver: `drivers/misc/mediatek/thermal/mt6797/`

Files: `src/mtk_tc.c` (1428 lines), `src/mtk_pmic_efuse.c` (183), `inc/tscpu_settings.h` (656),
`inc/tspmic_settings.h` (47), `inc/tzcpu_initcfg.h` (51), `inc/clatm_initcfg.h` (62),
`inc/mt_ts_setting.h` (25), `inc/mt_cooler_setting.h` (32), `inc/tmp_*.h`.

Build: `src/Makefile:20-21` → `mtk_tc.o`, `mtk_pmic_efuse.o`, gated on `CONFIG_THERMAL` (y).
`drivers/misc/mediatek/thermal/Makefile:38-46` builds `common/` and `$(MTK_PLATFORM)/` (= mt6797) for this platform.

### 1.1 Device-tree binding, addresses, IRQ, clock

- Compatible string: `"mediatek,mt6797-therm_ctrl"` — `mtk_tc.c:105-108`, looked up in
  `get_io_reg_base()` at `mtk_tc.c:1336`.
- Base: `thermal_base = of_iomap(node, 0)` (`mtk_tc.c:1340`); physical base and size are parsed
  from `reg` into `thermal_phy_base` (`mtk_tc.c:1352`).
  DT value: `<0x1100b000 0x1000>` (`arch/arm64/boot/dts/mt6797.dtsi:2497`).
- IRQ: `irq_of_parse_and_map(node, 0)` (`mtk_tc.c:1345`); DT says `GIC_SPI 78, LEVEL_LOW`
  (`mt6797.dtsi:2498`); installed as `IRQF_TRIGGER_LOW` in probe (`mtk_ts_cpu.c:2583-2586`).
- Clock: `devm_clk_get(&dev->dev, "therm-main")` (`mtk_ts_cpu.c:2557`), enabled via
  `clk_prepare_enable(therm_main)` (`mtk_tc.c:233`), disabled at `mtk_tc.c:252`.
  DT: `clocks = <&infrasys INFRA_THERM>; clock-names = "therm-main";` (`mt6797.dtsi:2499-2500`).
- Auxiliary mappings used by the driver (`mtk_tc.c:1355-1382`):
  | Node compatible | Use | DT |
  |---|---|---|
  | `mediatek,mt6797-auxadc` | `auxadc_ts_base` (`AUXADC_BASE_2`), ADC data/valid registers | `0x11001000` (`mt6797.dtsi:2363-2364`) |
  | `mediatek,INFRACFG_AO` | `infracfg_ao_base` (thermal SW reset) | see §1.1.1 |
  | `mediatek,APMIXED` | `apmixed_base` (`TS_CON0/1` = sensor mux select) | see §1.1.1 |
  | `mediatek,mt6797-infrasys` | AHB clock monitor, only if `THERMAL_GET_AHB_BUS_CLOCK` (0) | not used |

#### 1.1.1 DT-compatible discrepancy (important, verify on device)

The driver looks up **`"mediatek,INFRACFG_AO"`** and **`"mediatek,APMIXED"`** in upper case
(`mtk_tc.c:1365`, `mtk_tc.c:1374`) and `BUG_ON(node == 0)` immediately after each lookup
(`mtk_tc.c:1366`, `mtk_tc.c:1375`). The DTS in this tree has lower-case compatibles:
`"mediatek,infracfg_ao"` (`mt6797.dtsi:810`) and `"mediatek,apmixed"` (`mt6797.dtsi:955`).
`grep -rn 'mediatek,APMIXED\|mediatek,INFRACFG_AO' arch/` returns **nothing**.

Consequence: with *this* DTS the platform probe would BUG() after `get_io_reg_base()` succeeded for
therm/auxadc. Since the shipped device obviously booted, the runtime DTB used by the product must
differ from this tree (inference), or the thermal driver was never probed on the shipped build
(inference). **This must be checked against the real device DTB before relying on any of the
register programming described below.** It is also the single most important practical warning for
a mainline port: do not copy these compat strings blindly.

`get_io_reg_base()` returns 1 on success and 0 on IRQ failure; probe returns early on 0
(`mtk_tc.c:1347-1350`, `mtk_ts_cpu.c:2553-2554`).

### 1.2 Register map (thermal controller, offsets from `thermal_base`)

Defined in `tscpu_settings.h:532-602` (bank/shared block) and `:605-608` (PTP/SPM spares):

| Offset | Name | Purpose |
|---|---|---|
| 0x000 | `TEMPMONCTL0` | enable sensing points (`0x0F` = 4 points, `mtk_tc.c:1043`) |
| 0x004/0x008 | `TEMPMONCTL1`/`TEMPMONCTL2` | counting unit / sensing interval |
| 0x00C / 0x010 | `TEMPMONINT` / `TEMPMONINTSTS` | interrupt enable / status |
| 0x030 / 0x034 | `TEMPOFFSETH` / `TEMPOFFSETL` | OTP high/low offset thresholds |
| 0x038 | `TEMPMSRCTL0` | HW sample filtering (`0x492` = 2-of-4) |
| 0x040 / 0x044 | `TEMPAHBPOLL` / `TEMPAHBTO` | AHB poll period / timeout |
| 0x048-0x050, 0x0B4 | `TEMPADCPNP0..3` | PNP sensor index per measurement slot |
| 0x054-0x08C | `TEMPADCMUX`, `TEMPADCEN`, `TEMPADC*ADDR`, `TEMPRDCTRL`, `TEMPADCVALID*` | auxadc bridging |
| 0x090-0x098, 0x0B8 | `TEMPMSR0..3` | 12-bit raw measurement results |
| 0x0A0-0x0A8, 0x0BC | `TEMPIMMD0..3` | immediate-mode results |
| 0x0C0-0x0CC | `TEMPPROTCTL`, `TEMPPROTTA/B/C` | HW protection control + thresholds |
| 0x400 | `PTPCORESEL` | **bank select**, shared with EEM `EEMCORESEL` |
| 0x404-0x41C | `THERMINTST`, `PTPODINTST`, `THSTAGE0/1/2ST`, `THAHBST0/1` | PTP/thermal state status |
| 0x420-0x42C | `PTPSPARE0..3` | shared scratch with EEM (`EEMSPARE0..3`) |
| 0x430 | `THSLPEVEB` | slope Vbe register |

Note the **aliasing with the EEM/PTP block**: `arch/arm64/boot/dts/mt6797.dtsi:2503-2509` declares
`eem_fsm@1100b000` at the *same* address and size as `therm_ctrl@1100b000` (`:2495-2501`), and
`inc/mt_defptp.h:41` sets `EEM_BASEADDR` to `0x1100B000`. `PTPCORESEL` (0x400) and `EEMCORESEL`
(0x400) are literally the same register, which is why both drivers take the same lock
(`mt_ptp_lock()` / `mt_ptp_unlock()`, declared `mt_ptp.h:205-206`, used at `mtk_tc.c:721,791` and
`mt_eem.c:2170-2173`).

Bank select encoding (`tscpu_switch_bank()`, `mtk_tc.c:1084-1122`):

| Bank | `PTPCORESEL[3:0]` | Comment in source |
|---|---|---|
| 0 | 0x0 | BIG (A72) |
| 1 | 0x1 | GPU |
| 2 | 0x2 | SOC |
| 3 | 0x3 | CPU-L (source comment wrongly says "bank2", `mtk_tc.c:1102`) |
| 4 | 0x4 | CPU-LL |
| 5 | 0x5 | MCUCCI |

### 1.3 Bank → sensor map and sensor IDs

`tscpu_g_bank[]` — `mtk_tc.c:83-102` (duplicated as comments at `mtk_tc.c:70-77`, `:267-274`,
`:593-599`, `:661-667`):

| Bank | Name | Sensor(s) | `ts_number` |
|---|---|---|---|
| 0 | BIG / A72 | `MCU1` | 1 |
| 1 | GPU | `MCU4` | 1 |
| 2 | SOC | `MCU2`, `MCU3` (max of both, `mtk_tc.c:621-629`) | 2 |
| 3 | CPU-L | `MCU2` | 1 |
| 4 | CPU-LL | `MCU2` | 1 |
| 5 | MCUCCI | `MCU2` | 1 |

Sensor enum: `MCU1=0, MCU2, MCU3, MCU4, ABB, ENUM_MAX` (`tscpu_settings.h:214-221`).
Readback accessors: `get_immediate_big_wrap` (bank0/MCU1, `mtk_tc.c:601-609`),
`get_immediate_gpu_wrap` (bank1/MCU4, `:611-619`), `get_immediate_soc_wrap` (`:621-629`),
`get_immediate_cpuL_wrap` (`:631-639`), `get_immediate_cpuLL_wrap` (`:641-649`),
`get_immediate_mcucci_wrap` (`:651-659`);
`get_immediate_ts1..ts4_wrap` (`:669-710`) map to bank0/MCU1, max(bank2/MCU2, bank3/MCU2,
bank4/MCU2, bank5/MCU2), bank2/MCU3, bank1/MCU4 respectively.

Sensor *selector* values written into the analog mux (`tscpu_settings.h:154-158`):

```
TEMPADC_MCU1 = 0x00   TEMPADC_MCU2 = 0x01   TEMPADC_MCU3 = 0x02
TEMPADC_MCU4 = 0x03   TEMPADC_ABB  = 0x10
```

These are `TSCON1[5:4]` (group) | `TSCON1[2:0]` (channel) (`tscpu_settings.h:135-149`).
They are written by the controller itself: `TEMPPNPMUXADDR` is set to
`TS_CONFIGURE_P` = `TS_CON1_P` = `apmixed_phy_base + 0x604` (`mtk_tc.c:1149`, `mtk_tc.c:521`),
matching `TS_CON1_TM = APMIXED_BASE_2 + 0x604` (`tscpu_settings.h:519`).

Measurement path: the TC triggers AUXADC on **channel 11** (`TEMPADCMUX = 0x800`,
`TEMPADCEN = 0x800`, `mtk_tc.c:868-874`), samples `AUXADC_DAT11` for validity+data
(`mtk_tc.c:880-881`), and stores 12-bit results in `TEMPMSR0..3`. Raw read is
`readl(TEMPMSR0..3) & 0x0fff` (`mtk_tc.c:931`). Before first use, AUXADC ch11 is put in
non-autoset, non-immediate mode (`mtk_tc.c:1132-1135`) and re-enabled at `:1155`.

### 1.4 Calibration data: efuse/devinfo fields, defaults, validity

Decode — `tscpu_thermal_cal_prepare()`, `mtk_tc.c:407-483`; devinfo indices
`ADDRESS_INDEX_0 = 32` (`0x10206184`), `_1 = 31` (`0x10206180`), `_2 = 33` (`0x10206188`)
(`tscpu_settings.h:122-124`, `mtk_tc.c:411-413`).

| Field | Source word | Bits | Notes |
|---|---|---|---|
| `ADC_GE_T` [9:0] | idx 32 | [31:22] | ADC gain error, default 512 |
| `ADC_OE_T` [9:0] | idx 32 | [21:12] | ADC offset error, default 512 |
| `O_VTSMCU1` (9b) | idx 31 | [25:17] | default 260 |
| `O_VTSMCU2` (9b) | idx 31 | [16:8] | default 260 |
| `O_VTSMCU3` (9b) | idx 32 | [8:0] | default 260 |
| `O_VTSMCU4` (9b) | idx 33 | [31:23] | default 260 |
| `O_VTSABB` (9b) | idx 33 | [22:14] | default 260 |
| `DEGC_cali` (6b) | idx 31 | [6:1] | default 40 |
| `ADC_CALI_EN_T` (1b) | idx 31 | [0] | 0 ⇒ sample not calibrated |
| `O_SLOPE_SIGN` (1b) | idx 31 | [7] | 0 = positive slope |
| `O_SLOPE` (6b) | idx 31 | [31:26] | ignored when ID==0 |
| `ID` (1b) | idx 32 | [9] | 0 = TSMC sample ⇒ force `O_SLOPE=0` |

Citations: decode at `mtk_tc.c:423-454`; field/range documentation comment at `mtk_tc.c:360-373`
(quoted comments: `ADC_GE_T [9:0] Default:512 265 ~ 758`, `O_VTSMCU1 (9b) Default:260 -8 ~ 484`,
`DEGC_cali(6b) Default:40 1 ~ 63`); ID handling `mtk_tc.c:456-462`.

Sanitising (`eDataCorrector()`, `mtk_tc.c:374-405`) — applied only when `ADC_CALI_EN_T == 1`
(`mtk_tc.c:465-467`):

- `ADC_GE_T`, `ADC_OE_T` outside `265..758` → 512
- any `O_VTS*` outside `-8..484` → 260
- `DEGC_cali` outside `1..63` → 40
- if `ADC_CALI_EN_T == 0`: warn "This sample is not Thermal calibrated" and set
  `GE=OE=512, O_VTS*=260, DEGC=40, slope_sign=0, slope=0` (`mtk_tc.c:468-480`)

Note on ranges: the `-8` lower bound of the `O_VTS*` check is unreachable because the fields are
9-bit values stored in `__s32` (`mtk_tc.c:382-401`); effectively only the `> 484` case is caught.
O_SLOPE is 6 bits with a separate sign bit, so `1663 ± O_SLOPE*10` stays in `1603..1723`.

Precomputed terms (`tscpu_thermal_cal_prepare_2()`, `mtk_tc.c:485-518`):

```
ge   = (ADC_GE_T - 512) * 10000 / 4096          /* gain error, x10000 */
oe   =  ADC_OE_T - 512
gain = 10000 + ge
fmt_n    = O_VTS_n + 3350 - oe
x_roomt[n] = (((fmt_n * 10000) / 4096) * 10000) / gain    /* "room-temp" ADC code, x10000 */
```

`x_roomt[]` is indexed by *sensor* enum (MCU1..ABB), and `get_thermal_slope_intercept()` picks the
per-bank dominant sensor: bank0→idx0 (MCU1), bank1→idx3 (MCU4), banks 2..5→idx1 (MCU2)
(`mtk_tc.c:285-307`).

**Source of the calibration words.** `get_devinfo_with_index()` reads a RAM array populated at boot
from the flat-DT `/chosen` property **`atag,devinfo`** written by LK/preloader
(`drivers/misc/mediatek/devinfo/v1/devinfo.c:275-295`, `:72-97`; early_initcall at `:340-370`).
Linux never touches the efuse controller for these values on this platform. The `efusec@10206000`
node (`mt6797.dtsi:1939-1942`) has no `nvmem-cells`; efuse is consumed by baseband/other drivers.

### 1.5 Raw → temperature conversion (authoritative formula)

`raw_to_temperature_roomt()` — `mtk_tc.c:553-590`; call site `read_tc_raw_and_temp()`
`mtk_tc.c:926-938`; result multiplied by 100 at `mtk_tc.c:937`.

Input: `raw = readl(TEMPMSR0..3) & 0x0FFF` (12-bit). Output: millidegrees Celsius
(0.001 °C), computed at 0.1 °C resolution then scaled.

```
t0 = (DEGC_cali * 10) >> 1                      /* = 5 * DEGC_cali, units 0.1 °C */
d  = raw - oe
u  = ((( (d * 10000) >> 12) * 10000) / gain) - x_roomt[sensor]
u  = u * 15 / 18
q  = (u * 1000) / (1663 + O_SLOPE * 10)         /* O_SLOPE_SIGN == 0 */
q  = (u * 1000) / (1663 - O_SLOPE * 10)         /* O_SLOPE_SIGN == 1 */
q  = -q                                         /* code: q = q - (q << 1) */
T_01C = t0 + q                                  /* 0.1 °C */
T_mC  = T_01C * 100
```

Source lines: `t0` at `:571`; `d` at `:572`; `u` at `:574-575`; slope branch at `:578-581`;
negation `:583`; sum `:586`; scale `:937`.

Arithmetic notes (important for reimplementation/units):

- `>> 12` is a divide-by-4096 before the `* 10000 / gain` normalisation — this is the same
  `x10000`-scaled domain as `x_roomt`, hence the subtraction at `:574`.
- All divisions are C integer divisions on `__s32`: **truncation toward zero at every step**
  (`:574`, `:575`, `:579`, `:581`). Worst-case error is roughly ±1 LSB of 0.1 °C plus the
  `*15/18` and `/1000` truncations; the driver advertises no accuracy figure anywhere.
- The formula is reported in-source as DE-confirmed but *unverified by this review*:
  "The equations in this function are confirmed by Thermal DE Alfred Tsai"
  (`mtk_tc.c:309-312`). Treat the closed form as vendor-supplied, not derived.
- `raw == 0` short-circuits to 0 °C (`mtk_tc.c:568-569`) — so a dead ADC channel reads 0, not -40.

`temperature_to_raw_room()` is the inverse, used only to program hardware thresholds
(`mtk_tc.c:521-550`, guarded by `THERMAL_CONTROLLER_HW_TP`):

```
a = T_mC - (DEGC_cali * 1000 / 2)
b = a * (1663 ± O_SLOPE*10) / 10 * 18 / 15 ; b = -b
c = b / 1000 + x_roomt[sensor] * 10
raw = (c * 4096 / 10000 * gain) / 100000 + oe
```

Because of the same truncations the round trip is not exact (a few LSB of 12-bit code).

### 1.6 `ts_MTS` / `ts_BTS` (the values handed to EEM and SPM)

`get_thermal_slope_intercept()` — `mtk_tc.c:258-338`, `EXPORT_SYMBOL` at `:338`, prototype in
`drivers/misc/mediatek/include/mt-plat/mt6797/include/mach/mt_thermal.h:57-66`
(`struct TS_PTPOD { unsigned int ts_MTS; unsigned int ts_BTS; }`).

```
temp0 = (10000 * 100000 / gain) * 15 / 18
temp1 = (temp0 * 10) / (1663 ± O_SLOPE * 10)          -> ts_MTS
temp0 = DEGC_cali * 10 / 2
temp1 = ((10000 * 100000 / 4096 / gain) * oe + x_roomt * 10) * 15 / 18
temp2 = temp1 * 100 / (1663 ± O_SLOPE * 10)
ts_BTS = (temp0 + temp2 - 250) * 4 / 10
```

(`mtk_tc.c:314-331`.) Consumers: EEM (`mt_eem.c:2140-2142`), SPM suspend VCORE protection
(`mt_spm.c:1941-1943`), OTP (`mt_otp.c:852-854`).

### 1.7 Hardware thermal protection (trip0 → SPM state2 / reset)

`set_tc_trigger_hw_protect(temperature, temperature2, bank)` — `mtk_tc.c:899-923`:

1. `raw_high = temperature_to_raw_room(temperature, dominant_sensor_of_bank)` (`:911`)
2. `TEMPMONINT = 0` (disable IRQ sources) (`:914`)
3. `TEMPPROTCTL = 0x20000` — "set hot to wakeup event control" (`:917`)
4. `TEMPPROTTC = raw_high` — "set hot to HOT wakeup event" (`:919`)
5. `TEMPMONINT |= 0x80000000` — "enable trigger Hot SPM interrupt" (`:922`)

`0x80000000` is `THERMAL_tri_SPM_State2` (`tscpu_settings.h:649`); the ISR's handling of that bit
only prints "Thermal state2 to trigger SPM state2" (`mtk_tc.c:788-789`), i.e. the action is pure
hardware. `THERMAL_tri_SPM_State0/State1` are `0x20000000`/`0x40000000` (`:647-648`).

**`temperature2` (the "middle threshold", `tc_mid_trip`) is not programmed** — it is only logged
(`mtk_tc.c:906`) and documented as `-275000` to disable (`:896-898`). So in this revision the
"mid trip" plumbing in `mtk_ts_cpu.c` (`tc_mid_trip`, set to `trip_temp[1]` on cooler bind at
`mtk_ts_cpu.c:493`) has **no effect on hardware**.

Callers of `tscpu_config_all_tc_hw_protect()`: probe (`mtk_ts_cpu.c:2595`), cooler bind/unbind
(`mtk_ts_cpu.c:488,494`), resume (`mtk_ts_cpu.c:1639`), proc write (`mtk_ts_cpu.c:999`).

Reset arming — `tscpu_config_all_tc_hw_protect()` (`mtk_tc.c:1207-1259`):

- `wd_api->wd_thermal_direct_mode_config(WD_REQ_DIS, WD_REQ_RST_MODE)` **before** programming
  (`:1229`; `BUG()` if the WD API is unavailable, `:1232`)
- per-bank `tscpu_switch_bank(i)` + `set_tc_trigger_hw_protect()` under `mt_ptp_lock` (`:1243-1251`)
- `wd_api->wd_thermal_direct_mode_config(WD_REQ_EN, WD_REQ_RST_MODE)` **after** (`:1255`)

So the RGU "thermal direct reset" mode is only armed once thresholds are valid. Probe comment:
"default is dual mode (irq/reset), if not to config this and hot happen, system will reset after
30 secs" (`mtk_ts_cpu.c:2546-2552`) — the 30 s figure is a vendor comment, not verified here.

A **second, software** reset path exists: the `mtktscpu-sysrst` cooling device writes to address 0
to force a data abort (`common/coolers/mtk_cooler_sysrst.c:58-76`, specifically `:71`), driven by
`mtktscpu` trip 0 = 117 °C (§2.1).

Interrupt handler (`tscpu_thermal_all_bank_interrupt_handler`, `mtk_tc.c:795-812`) reads
`THERMINTST[7:0]` and calls `thermal_interrupt_handler(i)` for each bank bit that reads **0**
(note the inverted test, `:807-808`). The per-bank handler (`:712-793`) only decodes and logs
cold/hot/LO/HO/state0/1/2 status; `THERMAL_INFORM_OTP` (0, `tscpu_settings.h:111`) would have
enabled the OTP offset-window logic at `:728-761` and `:1167-1205`, so that whole block is **DEAD**.

### 1.8 Sampling configuration and polling intervals

Hardware sampling (`thermal_reset_and_initial()`, `mtk_tc.c:814-892`), non-bank0 path
(`:841-847`):

- `TEMPMONCTL1 = 0x0C` → 12 × (1/78 MHz) × 256 ≈ 39.384 µs counting unit
- `TEMPMONCTL2 = 0x101AD` → filter interval 1 unit, sensor interval 429 units ≈ 18.1 ms
- `TEMPAHBPOLL = 0x30D` → AHB poll ≈ 10 µs
- `TEMPAHBTO = 0xFFFFFFFF` (`:861`)
- filter: `TEMPMSRCTL0 = 0x492` = "2 out of 4 samples" because `THERMAL_CONTROLLER_HW_FILTER == 2`
  (`tscpu_settings.h:75`, `mtk_tc.c:849-850`). Other filter constants present at `:831-838`.
- bank0 uses `g_bigCTS = {0xC, 0x0001002E, 0x30D, 1}` (`mtk_tc.c:179`, applied `:824-827`) —
  i.e. BIG bank is sampled with a different interval (`0x0001002E`) than the other banks.
- `TEMPMONIDET0/1 = 0` → interrupt on first occurrence (`:863-864`).
- `TEMPADCVALIDMASK = 0x2C`, `TEMPRDCTRL = 0`, `TEMPADCVOLTAGESHIFT = 0` (`:886-889`).

Init sequence: `tscpu_thermal_initial_all_bank()` (`mtk_tc.c:1124-1165`) — for each bank: switch
bank, reset+configure TC, program PNP slots with the bank's sensor selectors, point
`TEMPPNPMUXADDR` at `TS_CON1`, then enable periodic sensing points per bank.

Fast-init variant `tscpu_thermal_fast_init()` (`mtk_tc.c:990-1082`) polls `TEMPMSR0..3` up to 20
times for the sentinel `THERMAL_INIT_VALUE = 0xDA1` (`tscpu_settings.h:106`,
`mtk_tc.c:1047-1076`). In this build it is **DEAD**: no caller in the mt6797 path
(`init_thermal()` in `mtk_ts_cpu.c` does not call it).

Software polling (`mtktscpu` zone):

- `interval = TZCPU_INITCFG_INTERVAL = 40` ms (`tzcpu_initcfg.h:18`, `mtk_ts_cpu.c:104`), passed as
  `polling_delay` to the zone (`mtk_ts_cpu.c:1388-1389`).
- Fast polling: if `T >= fast_polling_trip_temp (60000)` → `polling_delay = interval/2 = 20 ms`
  (`mtk_tc.c:156-158`, `mtk_ts_cpu.c:663-670`). `fast_polling_trip_temp_high` is marked deprecated
  (`mtk_tc.c:157`).
- Low-power overrides applied afterwards (`mtk_ts_cpu.c:673-679`, factors `mtk_tc.c:147-150`):
  `T >= 40000` → keep current delay; `20000 <= T < 40000` → `40 * factor1 (1) = 40 ms`;
  `T < 20000` → `40 * factor2 (4) = 160 ms`.
- Each poll re-reads **all** banks: `tscpu_update_tempinfo()` → `read_all_bank_temperature()`
  (`mtk_ts_cpu.c:2201-2218`), i.e. 6 bank switches + 7 sensor reads + 2 calibrations per cycle.
- Every acceptable temp is also pushed to MET (`THERMAL_DRV_UPDATE_TEMP_DIRECT_TO_MET = 1`,
  `tscpu_settings.h:100`, `mtk_ts_cpu.c:2241-2255`).

Other zones default to `interval = 0` (= no kernel polling), see §2.

### 1.9 Default trips, bound coolers, project overrides

`tzcpu_initcfg.h` (project-specific, `TZCPU_SET_INIT_CFG = 1` at `:16`):

| Trip | Temp | Bound cooler string | Line |
|---|---|---|---|
| 0 | 117000 (117 °C) | `mtktscpu-sysrst` | `:21-22` |
| 1 | 95000 | `cpu00` | `:24-25` |
| 2 | 85000 | `cpu03` | `:27-28` |
| 3 | 65000 | `cpu_adaptive_0` | `:30-31` |
| 4..9 | 63000/60000/55000/50000/45000/40000 | `""` (unbound) | `:33-49` |

`TZCPU_INITCFG_NUM_TRIPS = 4` (`:19`) — so only trips 0..3 exist for this project; trips 4..9 are
dead initialisers. Bound as `g_bind0..3` (`mtk_ts_cpu.c:164-173`); the non-initcfg defaults
(`:175-184`, e.g. `cpu02/cpu15/cpu22/cpu28`) are **not** used for mt6797.

Practical reading of these bindings (inference from the binding semantics in
`mtk_ts_cpu.c:482-531` and the MTK wrapper): `cpu00`/`cpu03` are **static** DTM steps, so at 95 °C
the CPU is clamped to the DTM step-0 power and at 85 °C to step-3 (see §2.5), while
`cpu_adaptive_0` starts the ATM loop at 65 °C with target Tj 75 °C (§3).

Zone ops: `thermal_zone_device_ops` for the CPU zone at `mtk_ts_cpu.c:722-731`;
critical temperature `MTKTSCPU_TEMP_CRIT = 120000` (`tscpu_settings.h:179`,
`mtk_ts_cpu.c:607-611`).

### 1.10 PMIC thermal efuse (`src/mtk_pmic_efuse.c`)

Separate, unrelated to the CPU diode calibration. Reads MT6351 efuse via
`pmic_Read_Efuse_HPOffset(0..1)` (`:68-69`), decodes:

| Field | Bits | Line |
|---|---|---|
| `ADC_CALI_EN` | efuse[0][0] | `:74` |
| `DEGC_cali` | efuse[0][6:1] | `:75` |
| `O_VTS` (13b) | efuse[1][3:0]<<9 \| efuse[0][15:7] | `:76` |
| `O_SLOPE_SIGN` | efuse[1][4] | `:77` |
| `O_SLOPE` | efuse[1][10:5] | `:78` |
| `ID` | efuse[1][11] | `:79` |

Defaults: uncalibrated → `O_VTS=1600, DEGC_cali=50, slope=0` (`:103-109`); `ID==0` → slope 0
(`:98-99`); out-of-range `DEGC_cali` outside `38..60` → 53 (`:112-113`, labelled "SW workaround
patch for mt6755 E2").

Conversion (`mtk_raw_to_temp`, `:49-56`; coefficients `mtktspmic_cali_prepare2`, `:124-146`):

```
slope1 = 100*1000*10
slope2 = -(1598 ± O_SLOPE)
Vbe    = -((O_VTS * 1800) / 4096) * 1000
intercept = (Vbe * 1000) / (-(1598 ± O_SLOPE*10)) + DEGC_cali * (1000/2)
T_mC = intercept + (slope1 * raw) / slope2
```

Raw from `PMIC_IMM_GetOneChannelValue(PMIC_AUX_CH4, 1, 2)` (`:154`). Sanity filters:
data outside `-50000..150000` dropped, and a step > 30 °C between samples dropped (`:163-171`).
Critical: `mtktspmic_TEMP_CRIT = 150000` (`tspmic_settings.h:28`).

---

## 2. Common thermal framework: `drivers/misc/mediatek/thermal/common/`

### 2.1 What is actually built and registered for MT6797

Build gating (all `CONFIG_THERMAL=y`):

- `common/Makefile:41-46` → `mtk_thermal_platform.o`, `ap_thermal_limit.o`, `thermal_zones/`, `coolers/`
- `thermal_zones/Makefile:115-139` (**mt6797 block**) builds:
  `mtk_ts_battery`, `mtk_ts_bts`, `mtk_ts_btsmdpa`, `mtk_ts_cpu`, `mtk_ts_pa`, `mtk_ts_pa_thput`,
  `mtk_ts_pmic`, `ts_da9214`, `mtk_ts_dram`, `mtk_ts_imgsensor`, `mtk_ts_wmt` (because
  `CONFIG_MTK_COMBO_WIFI=y`, `:130-132`), `mtk_ts1..4` (`:134-137`).
  Commented out for mt6797: `mtk_ts_6311buck`, `mtk_ts_abb`, `mtk_ts_buck`, `mtk_ts5`.
  Never built (other-platform blocks only): `mtk_ts_charger` (mt6757 only, `:156`),
  `mtk_ts_Abts` (mt6757, `:165`), `mtk_ts_tsx`, `mtk_ts_5`.
- `coolers/Makefile:71-87` (**mt6755/mt6797 block**) builds: `mtk_cooler_fps`, `mtk_cooler_bcct`,
  `mtk_cooler_atm`, `mtk_cooler_dtm`, `mtk_cooler_sysrst`; plus, because
  `CONFIG_MTK_THERMAL_PA_VIA_ATCMD=y`, `mtk_cooler_amutt` and `mtk_cooler_mutt` (`:72-81`).
  Completely commented out: `amddulthro`, `amdtxctrl`, `mddtxpwr`, `mddulthro`, `mdtxpwr`,
  `mdulthro`, `3Gmutt` — **DEAD for Gemini** regardless of config.
  `mtk_ta.o` always built (`:89`).
- Root `Makefile:26-36` → `mtk_thermal_monitor.o`, `mtk_cooler_shutdown.o`,
  `mtk_cooler_backlight.o` (only if `CONFIG_MTK_LEDS`), `mtk_cooler_kshutdown.o`,
  `mtk_cooler_cam.o`, `mtk_cooler_vrt.o`.
  Commented out: `mtk_cooler_spkrvol`, `mtk_cooler_dropcall`.

Wrapper layer: every zone/cooler goes through `mtk_thermal_zone_device_register_wrapper()`
(`mtk_thermal_monitor.c:2023-2135`) and `mtk_thermal_cooling_device_register_wrapper()`
(`:2479`), selected by `MTK_THERMAL_WRAPPER_BYPASS = 0` (`include/mt-plat/mtk_thermal_monitor.h:23`).
The wrapper adds: procfs hooks, `exit_threshold` hysteresis (`mtk_thermal_monitor.c:2315-2357`,
set via `mtk_thermal_cooling_device_add_exit_point()`, `:2485-2506`), conditional-cooling gate
(`MTK_THERMAL_MONITOR_CONDITIONAL_COOLING = 1`, `:59`), and last-value caching for the
`MTK_THERMAL_SENSOR_*` lookups.

Registered thermal zones at boot (initcall → `*_register_thermal()`):

| Zone type | File:line | Temp source | `interval` | Registered at |
|---|---|---|---|---|
| `mtktscpu` | `mtk_ts_cpu.c:1388` | TC banks (max of 6 banks) | **40 ms** | platform probe |
| `mtktsbattery` | `mtk_ts_battery.c:588` | `read_tbat_value()` | 0 | `module_init` (`:666`) |
| `mtktsAP` | `mtk_ts_bts.c:1132` | board NTC via AUXADC | 0 | `module_init` (`:1221`) |
| `mtktsbtsmdpa` | `mtk_ts_btsmdpa.c:1129` | board NTC + MD PA | 0 | `module_init` (`:1219`) |
| `mtktspmic` | `mtk_ts_pmic.c:431` | `mtktspmic_get_hw_temp()` | 0 | `module_init` (`:635`) |
| `mtktspa` | `mtk_ts_pa.c:615` | modem RF temp (`RFTEMP_*`) | 0 | `module_init` (`:708`) |
| `mtktsdram` | `mtk_ts_dram.c:391` | `read_dram_temperature()` | 0 | `late_initcall` (`:471`) |
| `mtktsimgsensor` | `mtk_ts_imgsensor.c:206` | values pushed by camera | 0 | `late_initcall` (`:509`) |
| `tsda9214` | `ts_da9214.c:400` | DA9214 status bits | 0 | `late_initcall` (`:486`) |
| `mtktswmt` | `mtk_ts_wmt.c:1548,1759` | combo-chip internal | own | `mtk_ts_wmt` init |

**Not registered at boot / effectively DEAD:** `mtkts1..4` — their `module_init` only creates
`/proc/driver/thermal/tzts1..4` (`mtk_ts1.c:434-451`); the zone is created inside the proc
*write* handler (`mtk_ts1.c:403-405`), so `mtkts1..4` exist only if userspace writes the file.
`mtktscharger`, `mtkts6311`, `mtktsbuck`, `mtktsAbts`, `mtktstsx`, `mtkts5` are not built.

Because all non-CPU zones register with `interval = 0` (`mtk_ts_battery.c:48`, `mtk_ts_bts.c:55`,
`mtk_ts_pmic.c:49`, `mtk_ts_dram.c:38`, `mtk_ts_pa.c:48`, `mtk_ts_imgsensor.c:34`), **the kernel
itself only polls `mtktscpu`**. The other zones read only on demand (sysfs/proc, or a caller of
`mtk_thermal_get_temp()`), and their configured trip points therefore never fire on their own
unless something else polls them.

### 2.2 `mtktscpu` (the only actively polled zone)

- `get_temp` (`mtk_ts_cpu.c:613-719`) returns `tscpu_get_curr_max_ts_temp()` because
  `FAST_RESPONSE_ATM` is set (`tscpu_settings.h:105`, `mtk_ts_cpu.c:622-626`), i.e. the cached max
  over all 6 banks refreshed by the RT/hrtimer path, not a fresh ADC read.
- Range warnings: logs when `T > trip0-15 °C`, `T < -30 °C` or `T > 85 °C` (`:629-632`).
- Also feeds `tscpu_g_prev_temp/curr_temp` for ATM (`:682-685`).
- The `CONFIG_MTK_PMIC_CHIP_MT6353` 5 A throttle block (`:704-714`) and the MT6753 5 A block
  (`:692-701`) are **DEAD** on MT6797 (MT6351, macros undefined).
- SW filter (`ENALBE_SW_FILTER`) is off (`tscpu_settings.h:58`), so the plausibility checks at
  `:634-655` are compiled out.
- Suspend/resume re-initialises all banks and re-arms HW protection (`mtk_ts_cpu.c:1600-1645`).

### 2.3 Board/NTC and supply zones (monitoring only)

- `mtktsAP` / `mtktsbtsmdpa`: AUXADC NTC. Pull-up **390 kΩ**, 1.8 V rail, NTC channel
  `AUX_IN0_NTC` (0), 100 k NTC table (`mtk_ts_bts.c:123-130`); voltage→resistance
  `R = (390000 * mV) / (1800 - mV)` (`:537`), mV = `raw * 1500 / 4096` (`:577`); then piecewise
  interpolation over `BTS_Temperature_Table` (-40..125 °C) (`:472-515`). Crit **60 °C**
  (`:87`). No cooler bound by default (`g_bind0..9` all empty, `:63-72`; the sysrst registration is
  commented out at `:1093`).
- `mtktsbattery`: `read_tbat_value()` from the charger driver (`:39`, `:149`), crit **60 °C**
  (`:83`). No bound cooler.
- `mtktspmic`: `mtktspmic_get_hw_temp()` (§1.10), crit **150 °C** (`mtk_ts_pmic.c` uses
  `mtktspmic_TEMP_CRIT` from `tspmic_settings.h:28`), self-registered `mtktspmic-sysrst` cooler
  (`mtk_ts_pmic.c:421`).
- `mtktsdram`: DDR "temperature" is the JEDEC derating **index 0..7**, not a temperature
  (`mtk_ts_dram.c:71-92`); crit 150 °C (`:63`); binds `mtktsdram-sysrst` on trip0=125 °C and
  `cpu01` on trip1=110 °C (`:52-53`).
- `mtktsimgsensor`: max of up to 4 values pushed by the camera stack, default `-275000`
  (invalid) (`mtk_ts_imgsensor.c:62-79`); crit 150 °C (`:67`); binds `cpu03` at trip0=125 °C
  (`:46`).
- `tsda9214`: reads a 2-bit status field of the external GPU buck (`ts_da9214.c:69-101`);
  thresholds 60/125/140 °C from those bits. **The aeon DTS contains no DA9214 regulator node**
  (only a pinctrl group named `da9214_gpio_default`,
  `arch/arm64/boot/dts/aeon6797_6m_n.dts:1726-1734`), and `da9214_read_interface()` is a weak
  symbol — so this zone is **DEAD/inert** for Gemini (inference).
- `mtktspa`: modem RF temperature via `mtk_mdm_monitor` attributes `RFTEMP_*`
  (`mtk_ts_pa.c:170-218`), `-127000` when not ready (`:210`); crit **85 °C** (`:80`), trip0 = 85 °C
  with self-registered `mtktspa-sysrst` (`:59`, `:605-608`) that writes to address 0
  (`:388-402`). Requires a live modem; on a Gemini without MD firmware this reads "not ready".

`mtk_ts_pa_thput.c` (`Feature_Thro_update = 1`, `mt_ts_setting.h:22`) computes MD UL throughput
statistics for the PA cooler; it does not create a zone.

### 2.4 Coolers — what each actually does

All register through the MTK wrapper; each exposes `get/set_cur_state` and is driven either by a
zone binding or by userspace.

| Cooler type(s) | File:line | Real effect |
|---|---|---|
| `cpu00` … `cpu33` (34 static steps) | `mtk_cooler_dtm.c:242,264` | Sets a **static CPU power limit** = `(step*100 + 700) mW` minus a GPU allowance, and optionally a static GPU power limit, via `ap_thermal_limit` (`:114-184`, `:97`/`:110`) |
| `cpu_adaptive_0..2` | `mtk_cooler_atm.c:2036-2043` | Starts/stops the **ATM power-budget loop**; each has its own target Tj and exit point (`:2046-2048`) |
| `mtktscpu-sysrst`, `mtktsbuck-sysrst` | `mtk_cooler_sysrst.c:129-133` | Writes `*(u32*)0 = 0xdead` ⇒ data abort ⇒ reset (`:71`, `:105`) |
| `mtk-cl-shutdown00..0N` | `mtk_cooler_shutdown.c:329-332` | Debounced userspace notification (`SHUTDOWN=1` uevent, `:291-299`) and optional signal to a target process (`:301-307`); does **not** power off itself |
| `mtk-cl-shutdown` | `mtk_cooler_kshutdown.c:99` | **`machine_power_off()`** immediately when state == 1 (`:66-70`) |
| `mtk-cl-bcct00..02` | `mtk_cooler_bcct.c:352-354` | Caps **battery charging current** (mA packed in the upper 16 bits of the state, `:117-132`), arbitrated with other charger-limit users (`:176-235`) |
| `mtk-cl-fps00..03`, `mtk-cl-adp-fps` | `mtk_cooler_fps.c:593-598` | Caps **display frame rate** via `switch_set_state()` (`:168-202`) |
| `mtk-cl-mutt00..03`, `mtk-cl-noIMS`, `mtk-cl-mdoff`, `mtk-cl-adp-mutt`, `cl-amutt-upper/lower` | `mtk_cooler_mutt.c:764-782`, `mtk_cooler_amutt.c:392-400` | **Modem** throttling (TX power / UL throughput / IMS-off / MD-off) via CCCI; adaptive variant ramps steps (`amutt` `:126-160`). Only meaningful with a live modem |
| `mtk-cl-backlight0..N` | `mtk_cooler_backlight.c:41-63` | Caps max brightness to 100/70/40/10 % via `setMaxbrightness()` |
| `mtk-cl-cam00..0N`, `mtk-cl-cam-urgent` | `mtk_cooler_cam.c:239-267` | Sets a global "camera thermal" flag consumed by the camera driver (`:122-145`) |
| `mtk-cl-vrt00..0N` | `mtk_cooler_vrt.c:102-114` | Sets a global "virtual/video" flag only |
| (sysrst from zones) | `mtk_ts_pa.c:605`, `mtk_ts_pmic.c:421`, `mtk_ts_dram.c:252`, `ts_da9214.c:261` | Per-domain reset devices, same `*(u32*)0` pattern |

No cooler in this tree touches **DDR frequency** or **CPU frequency directly**: every CPU-side
cooler produces a *power budget in mW* which is arbitrated by `ap_thermal_limit.c` and delivered
via PPM (§3). GPU budgets go to `mt_gpufreq_thermal_protect()`.

### 2.5 Power-limit arbitration: `common/ap_thermal_limit.c`

- Three slots, `AP_THERMO_LMT_MAX_USERS = 3` (`:41`); slot 0 is reserved for "general purpose"
  (`_gp`, `:58-64`), so ATM and DTM take slots 1 and 2 (`:97-117`).
- CPU: `final = MIN(users[0..2].cpu_limit)` (`:151-152`), and on change calls
  `mt_ppm_cpu_thermal_protect(final or 0)` (`:169`), timing the call and warning if it takes
  > 100 ms (`:167-174`). Unbounded is represented as `0x7FFFFFFF` (`:47`).
- GPU: same MIN arbitration, then `mt_gpufreq_thermal_protect()` (`:192-206`).
- `mt_gpufreq_thermal_protect()` converts the power limit into a frequency limit
  (`base/power/mt6797/mt_gpufreq.c:2388-2442`).

### 2.6 ATM / adaptive power budgeting (`common/coolers/mtk_cooler_atm.c`)

Configuration in effect for Gemini: `CPT_ADAPTIVE_AP_COOLER = 1` (`tscpu_settings.h:68`),
`PRECISE_HYBRID_POWER_BUDGET = 1` (`:91`), `PHPB_DEFAULT_ON` (`:93`) ⇒ `tscpu_atm = 3`
(`mtk_cooler_atm.c:143`) ⇒ `_adaptive_power_calc = _adaptive_power_ppb` (`:2031-2035`, `:1412-1416`).
`CLATM_SET_INIT_CFG = 1` (`clatm_initcfg.h:17`) selects the per-cooler table from that header, and
`CLATM_INIT_CFG_ACTIVE_ATM_COOLER = 0` (`:52`) selects index 0 at runtime (`:1069-1091`).

Effective index-0 parameters for this project (`clatm_initcfg.h:19-28`):

| Parameter | Value | Meaning |
|---|---|---|
| `TARGET_TJ` | 75000 | target junction temperature |
| `EXIT_POINT` | 10000 | hysteresis before the cooler turns off |
| `FIRST_STEP` | 3960 | initial total budget (mW) |
| `THETA_RISE` / `THETA_FALL` | 2 / 8 | °C-per-unit gain of the loop |
| `MIN_BUDGET_CHG` | 1 | minimum budget step |
| CPU power range | 300 … 3960 mW | |
| GPU power range | 800 … 2000 mW | |

(`CLATM_INIT_CFG_CATM = 0`, `:54`, so cATM/cATM+ continuous target adaptation is **off**; the
`ta` userspace helper `mtk_ta.c:213` is therefore inert. `THERMAL_HEADROOM = 0`,
`tscpu_settings.h:86`, disables the Tpcb headroom variant.)

Algorithm (`_adaptive_power_ppb`, `:762-816`):

1. Activated by the zone binding `cpu_adaptive_0` at 65 °C; `decide_ttj()`
   (`:1025-1113`) computes `TARGET_TJ = min over active coolers of TARGET_TJS[i]`,
   `TARGET_TJ_HIGH/LOW = ±1000` (`:1066-1067`), and refreshes the per-cooler power bounds.
2. Total budget (mW):
   ```
   delta = ( (TARGET_TJ - T_curr)/tt + (T_prev - T_curr)/tp ) / theta
   if delta_threshold terms are inside the ±1 °C dead-band -> delta = 0     (:660-679)
   total = clamp(prev_total + delta, MIN_TOTAL, MAX_TOTAL)                   (:728-760)
   ```
   with a doubling of the derivative term while temperature is rising (`:671-673`) and a switch to
   "current OPP power" when the budget would otherwise be unachievable (`:746-755`).
3. Split into CPU/GPU budgets (`P_adaptive`, `:514-633`): GPU gets the highest OPP whose power
   ≤ `min(total - MIN_CPU, MAX_GPU)`, scaled by GPU loading above 80 % / below 40 %
   (`GPU_L_H_TRIP = 80`, `GPU_L_L_TRIP = 40`, `:134`, `:588-596`); CPU gets the remainder
   (`:598`).
4. Outputs: `set_adaptive_cpu_power_limit()` → `apthermolmt_set_cpu_power_limit()`
   (`:319-356`); `set_adaptive_gpu_power_limit()` → `apthermolmt_set_gpu_power_limit()`
   (`:358-368`).
5. Current power input for the loop: `mt_ppm_thermal_get_cur_power()` + 1
   (`:696-726`) — i.e. PPM's power-index of the *current* OPP.

Legacy variants (ATMv1 `case 0`, FTL ATMv2 `case 1/2` at `:836-1000`) are present but unused
because `tscpu_atm == 3`.

Fast-response path: `atm_hrtimer` at **20 ms** (`:233`, `:2058-2060`) refreshes `atm_curr_maxtj`
and wakes an RT/CFS kthread that runs the same algorithm (`:1974-2017`); enabled by
`FAST_RESPONSE_ATM = 1` (`tscpu_settings.h:105`).

BCCT (`mtk_cooler_bcct.c`) is present and built, but nothing in the kernel binds it: the CPU zone
binds only sysrst/cpuXX/cpu_adaptive_0 and no other zone has a default binding. In the vendor
product it is presumably driven from userspace thermal HAL.

---

## 3. PPM and DVFSP

### 3.1 Which PPM

`drivers/misc/mediatek/base/power/Makefile`:

- `:17` `obj-$(CONFIG_ARCH_MT6797) += ppm_v1/` → **ppm_v1 is the one used for Gemini**
- `:18` `obj-$(CONFIG_ARCH_MT6757) += ppm_v2/` (Helio P20 class) — ppm_v2 is **not** built
- `:54` `obj-$(CONFIG_ARCH_MT6797) += spm_v2/`, `:63` `pbm_v1/`

(ppm_v2's `mt_ppm_policy_ptpod.c` / `mt_ppm_policy_thermal.c` exist as sources but are never
compiled here.)

### 3.2 What PPM is and where it runs

PPM ("Power Performance Manager") is an **AP-side, table-driven CPU DVFS arbiter**: it owns a
power table (`ppm_get_power_table()`) and an efficiency table, collects per-policy requests, picks
a HICA state, and computes per-cluster `{min/max cpufreq index, min/max core count}`. It is not
firmware and does not run on SCP/MCU.

- Policies: `mt_ppm_policy_thermal.c`, `_dlpt`, `_hica`, `_lcm_off`, `_perfserv`, `_ptpod`,
  `_pwr_thro`, `_sys_boost`, `_user_limit`, `_ut`, `_force_limit`
  (`drivers/misc/mediatek/base/power/ppm_v1/src/`).
- Thermal policy priority `PPM_POLICY_PRIO_POWER_BUDGET_BASE` and it is budget-based, not
  freq-based (`mt_ppm_policy_thermal.c:35-44`).
- **Execution model in this tree: synchronous.** The `ppm_main` kthread and `ppm_task_wakeup()`
  event path are both under `#if 0` (`mt_ppm_main.c:516-532`, `:1197-1237`, `:1385-1398`);
  `ppm_task_wakeup()` therefore calls `mt_ppm_main()` **inline** (`:528`). So the HICA decision and
  the final limit broadcast execute in the *caller's* context — which for a thermal transition is
  the `mtktscpu` polling work item (or the ATM hrtimer/kthread). Consequence (inference): a PPM
  recomputation is on the thermal polling latency path; `ap_thermal_limit.c:167-174` even warns if
  that exceeds 100 ms.

Thermal entry point: `mt_ppm_cpu_thermal_protect(limited_power_mW)`
(`mt_ppm_policy_thermal.c:46-73`) stores `power_budget` and `is_activated`, then wakes PPM.
Budget→OPP conversion: `ppm_main_update_req_by_pwr()`
(`mt_ppm_main.c:97-200+`) reads current frequencies, computes current power index, then walks the
power table for `delta_power = budget - curr_power`. HICA then bounds it
(`ppm_hica_set_default_limit_by_state()`, `:160`).

Outputs: `PPM_CLIENT_DVFS` and `PPM_CLIENT_HOTPLUG` callbacks
(`mt_ppm_main.c:1098-1112`). The DVFS callback is `ppm_limit_callback()`
(`base/power/mt6797/mt_cpufreq.c:4857-4900+`), registered at `:5509`; it sets
`idx_opp_ppm_limit` / `idx_opp_ppm_base` per cluster, i.e. the actual CPU frequency ceiling.

Inputs available to thermal: `mt_ppm_thermal_get_cur_power()` (current OPP power index,
`mt_ppm_policy_thermal.c:106-151`), `..._get_min_power()` (`:75-81`), `..._get_max_power()`
(`:83-104`).

### 3.3 DVFSP (cpuHVFS) relationship

- `base/power/mt6797/mt_cpufreq_hybrid.c` is compiled (`mt6797/Makefile:51`) but its whole body is
  under `#ifdef CONFIG_HYBRID_CPU_DVFS` (`mt_cpufreq.c:155-174`, `:5477-5503`).
  `CONFIG_HYBRID_CPU_DVFS` is **not set** in any `aeon6797_*` defconfig (only
  `CONFIG_MTK_GPU_COMMON_DVFS_SUPPORT=y` appears), and the Kconfig prompt is
  `config MTK_HYBRID_CPU_DVFS` (`base/power/Kconfig:27`).
- The DVFSP is a **PCM firmware running in the CPU-SPM ("CSPM") microcontroller inside the SoC**,
  not the AP and not the SCP: see `CSRAM_BASE = 0x0012a000` / 12 KiB code RAM
  (`mt_cpufreq_hybrid.c:44-45`), the `cpuhvfs_dvfsp` ops table (kick/pause/stop/set_limit,
  `:516-553`), and the semaphores `CSPM_SEMA3_M0/M1/M2 = "MCU SEMA (FH/CPU SPM/ATF)"`
  (`:291-293`). Commands are register writes into CSPM + shared CSRAM (no IPI).
- If it were enabled, `mt_cpufreq` would replace `set_cur_freq/set_cur_volt` with hybrid ops and
  PPM would delegate the actual frequency/voltage switch to the firmware (`:5484-5501`).
  As built, **the AP does all DVFS in software via PPM v1 + `mt_cpufreq`**.

So: `thermal → ap_thermal_limit → mt_ppm_cpu_thermal_protect → PPM v1 (inline) → mt_cpufreq`.
DVFSP would sit below `mt_cpufreq` but is disabled on this product.

---

## 4. PTP / EEM — how thermal calibration reaches voltage control

There is **no `mt_ptp.c`** in this tree. The PTP/EEM implementation lives in
`drivers/misc/mediatek/base/power/mt6797/mt_eem.c` (6578 lines, always built:
`mt6797/Makefile:47`), with the API in `mt_ptp.h` (222 lines) and register map in `mt_defptp.h`
(152 lines). (`mt_eem2.c` is a second-generation EEM variant, 1355 lines, **not** in the Makefile —
dead.)

### 4.1 `ts_MTS`/`ts_BTS` consumption

`base_ops_mon_mode()` — `mt_eem.c:2117-2161`:

```
ts_bank = det->ctrl_id;                       /* BIG=0, GPU=1, SOC=2, L=3, 2L=4, CCI=5 */
get_thermal_slope_intercept(&ts_info, ts_bank);
det->MTS = ts_info.ts_MTS;  det->BTS = ts_info.ts_BTS;
```

Mapping `eem_ctrl_id → thermal_bank_name` is identity (`mt_ptp.h:80-88`, `mt_eem.c:2139`).

Then `base_ops_set_phase()` programs them into hardware on MON entry
(`mt_eem.c:2259-2261`):

```
eem_write(EEM_TSCALCS, ((det->BTS << 12) & 0xfff000) | (det->MTS & 0xfff));
```

`EEM_TSCALCS = EEM_BASEADDR + 0x230` (`mt_defptp.h:110`). So the *per-bank calibrated diode
slope/intercept* is loaded into the EEM temperature-sense hardware, which is what makes the EEM's
own junction-temperature reading comparable to the thermal controller's. This is the concrete
thermal↔EEM coupling: without it, EEM's `get_temp()` would be uncalibrated.

EEM also reads temperature live: `base_ops_get_temp()` → `tscpu_get_temp_by_bank(ts_bank)`
(`mt_eem.c:2348-2377`), i.e. it borrows the thermal zone's measured value.

### 4.2 Where temperature changes voltage (not just measurement)

`eem_set_eem_volt()` — `mt_eem.c:3509-3560`:

```
cur_temp = det->ops->get_temp(det);                 /* calibrated bank temperature */
if (cur_temp <= 33000 || !tscpu_is_temp_valid())
        low_temp_offset = volt_2_pmic(6250 + pmic_base);   /* 6250 * 10 uV = 62.5 mV */
else
        low_temp_offset = 0;
volt_tbl_pmic[i] = clamp(volt_tbl[i] + volt_offset + low_temp_offset + pi_offset, VMIN, VMAX);
```

So there is an explicit **low-temperature voltage bump (+62.5 mV below 33 °C)**, plus the
process/leakage `volt_offset` and the dynamic `pi_offset`. `volt_tbl[]` itself is the DVFS table
read out of EEM registers (`EEM_VOP30/74`, `mt_eem.c:3842-3848`).

### 4.3 How EEM efuse voltage calibration relates to thermal

- EEM efuse (Mahua/PTP words) is read through the same devinfo blob:
  `get_devinfo(&eem_devinfo)` → `get_devinfo_with_index(50..66)`
  (`mt_eem.c:4870-4905`, indices 50,51,52,53,56,57,58,59,60,61,65,66).
- The bitfield layout (`struct eem_devinfo`, `mt_eem.c:1553-1643`) carries per-rail
  `*_BDES/*_MDES/*_DCMDET/*_DCBDET/*_MTDES/*_AGEDELTA` plus enable bits `*_INITEN/*_MONEN`,
  speed bin `*_BIN_SPEC`, `*_LEAKAGE`, `*_TURBO`. These describe the **designed Vbe at a
  reference temperature** ("descriptor" values) and are the coefficients the EEM detector compares
  against; the thermal slope/intercept tells the same detector how Vbe maps to °C.
- If **all** words are zero → `ctrl_EEM_Enable = 0`, `infoIdvfs = 0x55`, eem_error
  "No EEM EFUSE available, will turn off EEM !!" (`mt_eem.c:4964-4972`). So a device with an
  unprogrammed/absent devinfo blob silently disables EEM *and* loses thermal calibration.
- CPU speed-bin index used for turbo decisions comes from efuse word 22:
  `GET_BITS_VAL(3:0, get_devinfo_with_index(22))` (`mt_eem.c:2696`, `:2851`, `:3330`, `:6529`).
- `eem_efuse_calibration()` runs at init (`mt_eem.c:6505-6512`); `process_voltage_bin()` exists but
  is **commented out** at the call site (`:6520`).
- EEM and the thermal controller serialise on the same hardware: `mt_ptp_lock()` around
  `switch_bank` + register access (`mt_eem.c:2170-2173`), same lock used by `mtk_tc.c:721-791`.

### 4.4 SPM suspend VCORE over-temperature protection

`drivers/misc/mediatek/base/power/spm_v2/mt_spm.c`:

- `spm_getTHslope()` → `get_thermal_slope_intercept(&ts_info, 0)` (bank 0 = BIG) into
  `spm_mts`/`spm_bts` (`:1934-1944`).
- `spm_Temp2ADC(T)` = `((((bts<<4) - ((T-25)<<6)) & 0xFFFF) << 6) / mts` (`:1924-1932`).
- `spm_save_thermal_adc()` writes the ADC codes for `vcore_temp_lo`/`vcore_temp_hi` into SPM
  scratch so the SPM hardware can lower VCORE during suspend without the AP
  (`:1946-1960`).
- `spm_vcore_overtemp_ctrl()` drops VCORE to 0.7 V sleep voltage when the SPM thermal ADC code
  is outside the programmed window (`:1962-1981`).
- Defaults `vcore_temp_hi = 70`, `vcore_temp_lo = 0` (`:222-223`) are in °C and are **never
  overridden from DT** (no `of_property_read` for them). With `lo=0` and `hi=70` the conditions at
  `:1970-1971` (`> lo` OR `< hi`) are almost always true, so the "0.6 V" branch is effectively
  unreachable — likely unintended in this snapshot. Flagging as an observation, not a conclusion.

---

## 5. Device tree

`arch/arm64/boot/dts/aeon6797_6m_n.dts:3` includes `mt6797.dtsi`. The aeon DTS contains **no
thermal, efuse, PTP or cooling-related nodes**; `grep -n "therm\|efuse\|ptp\|nvmem\|cooling"
aeon6797_6m_n.dts` returns nothing.

Nodes inherited from `mt6797.dtsi`:

| Node | Compatible | Address / IRQs | `nvmem` cells | Status | Line |
|---|---|---|---|---|---|
| `therm_ctrl@1100b000` | `mediatek,mt6797-therm_ctrl` | `0x1100b000 +0x1000`, `GIC_SPI 78 LEVEL_LOW`, `clocks=<&infrasys INFRA_THERM>` | none | no `status` ⇒ **enabled** | `:2495-2501` |
| `eem_fsm@1100b000` | `mediatek,mt6797-eem_fsm` | same base, `GIC_SPI 129 LEVEL_LOW`, clocks `MFG_BG3D`,`SCP_SYS_MFG`,`INFRA_THERM` | none | enabled | `:2503-2509` |
| `efusec@10206000` | `mediatek,efusec` | `0x10206000 +0x1000` | **none** | enabled | `:1939-1942` |
| `ptp3_idvfs@10220000` | `mediatek,idvfs` | `0x11017000`, `0x10005000`, `0x10000000`, `0x10001000`, `0x10206000` (Big eFUSE); `GIC_SPI 331` | none | enabled | `:2281-2291` |
| `ptpotp@10222000` | `mediatek,ptpotp` | `0x10222000 +0x1000` | none | enabled | `:2293-2296` |
| `auxadc@11001000` | `mediatek,mt6797-auxadc` | `0x11001000 +0x1000`, `GIC_SPI 74` | none | enabled | `:2363-2368` |
| `apmixed@1000c000` | `mediatek,apmixed` | `0x1000c000 +0x1000` | – | enabled | `:954-958` |
| `infracfg_ao@10001000` | `mediatek,infracfg_ao` | `0x10001000 +0x1000` | – | enabled | `:809-813` |

Key points for a mainline port:

1. **No `nvmem-cells` anywhere.** Thermal calibration is not exposed by the efuse driver; it is
   injected by the bootloader via `/chosen/atag,devinfo`
   (`devinfo/v1/devinfo.c:286-295`). The `chosen` node in the aeon DTS
   (`aeon6797_6m_n.dts:25-33`) only has `bootargs` and display atags; `atag,devinfo` is added at
   runtime by LK.
2. The thermal driver *does* require the (mis-cased) `INFRACFG_AO`/`APMIXED` compatibles — see
   §1.1.1.
3. `therm_ctrl` and `eem_fsm` overlap in address space; a mainline driver must not probe both
   without sharing the `PTPCORESEL`/`EEMCORESEL` register (offset 0x400) and its lock.

---

## 6. Temperature thresholds present in code (compiled for Gemini unless noted)

| Domain | Threshold | Meaning | Citation |
|---|---|---|---|
| CPU hotspot (TC) | **117 °C** | HW protection: `TEMPPROTTC` + `TEMPMONINT[31]` (SPM state2) and RGU thermal reset | `tzcpu_initcfg.h:21`, `mtk_tc.c:919-922`, `:1207-1259` |
| CPU hotspot (SW) | 117 °C | `mtktscpu-sysrst` cooler ⇒ data abort reset | `tzcpu_initcfg.h:22`, `mtk_cooler_sysrst.c:71` |
| CPU hotspot | 120 °C | zone `crit` temperature (Linux critical trip) | `tscpu_settings.h:179`, `mtk_ts_cpu.c:607-611` |
| CPU | 95 °C | static DTM step `cpu00` (heavy CPU clamp) | `tzcpu_initcfg.h:25` |
| CPU | 85 °C | static DTM step `cpu03` | `tzcpu_initcfg.h:28` |
| CPU | 65 °C | start adaptive ATM (`cpu_adaptive_0`), target Tj 75 °C, exit 55 °C | `tzcpu_initcfg.h:31`, `clatm_initcfg.h:19-20` |
| CPU | 60 °C | fast-polling entry (40 ms → 20 ms) | `mtk_tc.c:156`, `mtk_ts_cpu.c:663` |
| CPU | 40 / 20 °C | polling factor boundaries (40 ms / 160 ms) | `mtk_tc.c:147-150`, `mtk_ts_cpu.c:673-679` |
| CPU | 80 / 85 °C | UART-limiting thresholds (feature `ENALBE_UART_LIMIT` — no code path uses them in this tree) | `tscpu_settings.h:53-55` |
| CPU (EEM) | 33 °C | below this, +62.5 mV voltage bump | `mt_eem.c:3519-3523` |
| CPU (OTP path) | 70 / 80 °C ±3 | `THERMAL_INFORM_OTP` window — **not compiled** (`THERMAL_INFORM_OTP = 0`) | `tscpu_settings.h:111-114` |
| Battery | 60 °C | `mtktsbattery` crit | `mtk_ts_battery.c:83` |
| Board NTC (`mtktsAP`) | 60 °C | crit; no cooler bound | `mtk_ts_bts.c:87` |
| Board NTC + MD PA | 60 °C | crit | `mtk_ts_btsmdpa.c:85` |
| Board NTC range | −40 … 125 °C | NTC table clamp | `mtk_ts_bts.c:481-484` |
| Modem/PA | 85 °C | `mtktspa` crit **and** trip0 → `mtktspa-sysrst` (reset) | `mtk_ts_pa.c:80`, `:49`, `:59` |
| Modem/PA (WMT) | combo-chip internal trips, 4 bindings | `mtktswmt` → pa1/pa2/pa3/sysrst | `mtk_ts_wmt.c:123-128` |
| GPU | 120 °C | no dedicated GPU zone (bank1 feeds `mtktscpu`); `mtkts4` crit 120 °C exists only if created on demand | `mtk_ts1.c:59`, `mtk_ts4.c:59` |
| DDR | 125 °C / 110 °C | `mtktsdram` trip0 → `mtktsdram-sysrst`, trip1 → `cpu01` | `mtk_ts_dram.c:39`, `:52-53` |
| DDR | 150 °C | crit | `mtk_ts_dram.c:63` |
| PMIC (MT6351) | 150 °C | crit; raw data rejected outside −50…150 °C | `tspmic_settings.h:28`, `mtk_pmic_efuse.c:163` |
| PMIC | 100 °C / −30 °C | logging-only warning band | `mtk_pmic_efuse.c:160-161` |
| PMIC domain | 150 °C | `mtktspmic` crit + `mtktspmic-sysrst` | `mtk_ts_pmic.c:421` |
| Charger | — | **not built for MT6797** (`mtk_ts_charger` is mt6757-only) | `thermal_zones/Makefile:156` |
| Camera sensor | 125 °C trip → `cpu03`; 150 °C crit | `mtktsimgsensor` | `mtk_ts_imgsensor.c:46`, `:67` |
| GPU buck (DA9214) | 60/125/140 °C | inert: no DA9214 node in the aeon DTS | `ts_da9214.c:76-88` |
| SPM suspend VCORE | 0 / 70 °C (defaults) | SPM scratch ADC window | `mt_spm.c:222-223`, `:1962-1981` |
| Any zone | −275000 | "invalid / disabled" sentinel used across the framework | `mtk_ts_cpu.c:125`, `mtk_thermal_monitor.c:2047` |

---

## 7. What this means for a mainline port (inference — flagged as such)

- Only `mtktscpu` is a real, kernel-polled zone. A mainline driver needs: one thermal zone on the
  TC, 6-bank readback, the calibration decode of §1.4 and the formula of §1.5, plus the
  `TEMPPROTTC`/`TEMPMONINT[31]` hardware trip if HW protection is wanted.
- The CPU cooling stack (ATM + DTM + PPM) is **not** a CPUfreq driver: it produces milliwatt
  budgets. A mainline replacement can map the ATM output directly to a cpufreq `max_freq` cap, but
  the mW→OPP mapping lives in PPM's power table (`mt_ppm_main.c`, `ppm_get_power_table()`), which
  would have to be reproduced or replaced.
- Calibration is **bootloader-provided** on this platform; mainline must either read the efuse
  controller directly (addresses in `tscpu_settings.h:122-124` = `0x10206180/84/88`) or accept
  uncalibrated defaults (512/512/260/260/260/260/260/40), which the driver itself treats as a
  valid fallback (`mtk_tc.c:468-480`). Absolute temperature error with defaults is unknown.
- The DTS/driver compatible mismatch (§1.1.1) means this DTS is not the one the product booted;
  verify against the device's real DTB before trusting any register offset or IRQ here.

---

## 8. Verification still needed on hardware

1. Actual DTB used by the shipped/vendor boot (to resolve §1.1.1).
2. Whether `atag,devinfo` is present in `/chosen` on a Gemini (determines whether calibration and
   EEM are live at all).
3. Whether `mtktscpu-sysrst`/`TEMPPROTTC` really resets at 117 °C on this SoC (vendor claim, not
   measured here).
4. Real `ts_MTS`/`ts_BTS` values from a device to validate the §1.5 closed form against an
   independent thermometer.
