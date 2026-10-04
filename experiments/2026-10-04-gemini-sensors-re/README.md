# Experiment: Gemini sensor path reverse engineering

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-04-gemini-sensors-re` |
| Status | `completed` (offline source review; no build, boot or device access) |
| Subsystem | I2C1 sensors: BMI160 IMU, STK3X1X light/proximity, MMC3530 magnetometer candidate, BMP280/HTS221 candidates, vendor sensor framework |
| Device variant | Project Gemini (Gemian `3.18.41+`, MT6797X) |
| Date(s) | 2026-10-04 |
| Investigator(s) | Claude (owner-requested investigation) |
| Tracking issue | Not yet assigned |

## Question

What does the stock Gemian kernel actually do to power, identify, configure
and read each sensor, which of the eight I2C1 client addresses have a driver
behind them at all, and what does that imply for a mainline IIO description?
The roadmap's [sensors step](../../docs/ROADMAP.md#after-wi-fi-remaining-driver-gaps)
listed rails, interrupts and mount orientation as unknowns. This record
answers what the pinned public vendor source can answer, separates verified
facts from hypotheses, and ranks the hypotheses by how they should be tested.
It changes no patch, profile, candidate or device state.

Earlier records own the live observations and the upstream-architecture
decision this builds on: the
[sensor/IIO recovery](../2026-07-12-sensor-iio-recovery/README.md) (live I2C1
topology, vendor HAL/axis contracts, patch 0052), the
[current-upstream architecture review](../2026-09-07-gemini-sensors-upstream-architecture/README.md)
with its [BMI identity](../2026-09-07-gemini-sensors-upstream-architecture/BMI_IDENTITY.md)
(`0xd1`), [STK identity](../2026-09-07-gemini-sensors-upstream-architecture/STK_IDENTITY.md)
(`0x11`/`0xc2`) and [BMI resources](../2026-09-07-gemini-sensors-upstream-architecture/BMI_RESOURCES.md)
observations, and the [live resource map](../../docs/hardware/mt6797-live-resource-map.md#sensors-and-iio-boundary).
Nothing in those records is repeated as a new finding here; this record adds
the vendor driver behaviour behind them.

## Inputs

Every vendor citation below is a public GPL file at Gemian commit
`8cfe6596a503612e3332d9c26e292a19525a7f07`, the same commit the
[charging record](../2026-10-04-gemini-charging-re/README.md) used. Every
mainline citation is Linux `7.1.3` as pinned in `kernel/manifest.json`. Exact
URLs, sizes and SHA-256 values are in [`source-inputs.json`](source-inputs.json).
Line numbers refer to those exact revisions. No vendor source, firmware or
private capture is copied into this repository; register addresses, bit
values and configuration constants are cited as facts.

The charging record's caveat applies here too, and more strongly: the public
board DTS does not describe the live sensor nodes (F1). Where the public tree
and a live capture disagree, the live capture wins.

## Part 1: verified facts

### What the public tree does and does not describe

- **F1. The public board DTS carries sensor *configuration* nodes but no I2C1
  sensor *clients*, and the public tree cannot build its own DTB.**
  `aeon6797_6m_n.dts` has `cust_accel@0/1`, `cust_alsps@0`, `cust_mag@0`,
  `cust_gyro@0/1`, `cust_baro@0` and `cust_hmdy@0`
  ([lines 203–297](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/aeon6797_6m_n.dts#L203-L297)),
  while the only `&i2c1` children in the tree are an MT6735 code-generator
  template with `cap_touch@5d` and `i2c_lcd_bias@3e`, and its sensors sit on
  `&i2c2` at other addresses
  ([`cust_i2c.dtsi` lines 1–4, 29–66](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/cust_i2c.dtsi#L29-L66)).
  `mt6797.dtsi` line 4286 includes `cust.dtsi`, which is absent from the
  public `arch/arm64/boot/dts/` directory, and the DTS `Makefile` lists no
  MediaTek target. The live DTB's eight I2C1 children (`0x30`, `0x48`, `0x5f`,
  `0x68`, `0x69`, `0x6a`, `0x6b`, `0x77`; [live resource map](../../docs/hardware/mt6797-live-resource-map.md#sensors-and-iio-boundary))
  therefore come from a board file this public commit does not carry, exactly
  as the charging record found for the charger node.
- **F2. The sensor EINT pseudo-nodes differ between the public tree and the
  live DTB.** `cust_eint.dtsi` declares `ALS@65`, `GSE_1@66` and `GYRO@67`
  with `interrupts = <N 8>` and zero debounce
  ([lines 50–69](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/cust_eint.dtsi#L50-L69)),
  but no file includes it. `mt6797.dtsi` instead defines `als: als`
  (`"mediatek, als-eint"`, **disabled**, no `interrupts`) and `gse_1`
  (`"mediatek, gse_1-eint"`) with no interrupt at all
  ([lines 4137–4147](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L4137-L4147)).
  The STK driver fails its probe when that node has no mappable interrupt
  (F11), yet the live kernel binds it and the live EINT table shows ALS on
  line 11 ([recovery record](../2026-07-12-sensor-iio-recovery/README.md#observations)).
  So the live DTB carries an `als-eint` node with `interrupts` the public tree
  lacks; the public `<65 8>` tuple is a template value, not Gemini wiring.
- **F3. Board pin configuration for the two sensor interrupt lines (public DTS).**
  `alsps_intpin_cfg` selects `PINMUX_GPIO88__FUNC_EINT11` with
  `bias-pull-up`; `gyro_intpin_cfg` selects `PINMUX_GPIO65__FUNC_GPIO65` (GPIO
  function, **not** its `EINT4` alternate) with `bias-pull-down`; both
  `pin_default` states are empty
  ([`aeon6797_6m_n.dts` lines 299–341](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/aeon6797_6m_n.dts#L299-L341)).
  The `&gyro` consumer is the vendor `gyroscope@0` platform node
  (`mt6797.dtsi` line 4165). In the pinned mainline pin table GPIO65's
  function 1 is `EINT4` and GPIO88's is `EINT11`
  ([`mt6797-pinfunc.h` lines 372–373](https://github.com/gregkh/linux/blob/v7.1.3/include/dt-bindings/pinctrl/mt6797-pinfunc.h#L372-L373)).
  Neither the BMI160 gyro driver nor the shared `gyroscope.c` framework
  references pinctrl or requests an interrupt (bounded grep), so the stock
  kernel configures GPIO65 as a pulled-down input and then never reads it.
- **F4. No sensor has a controlled supply in the vendor model.** Every
  `cust_*` node sets `power_id = <0xffff>` and `power_vol = <0>` (F1 lines);
  `sensor_dts.c` maps `0xffff` to `hw->power_id = -1`
  ([lines 61–66](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/hwmon/sensor_dts/sensor_dts.c#L61-L66)
  and the ALS/mag equivalents at lines 123–128, 211–216), and none of the
  bound drivers (`bmi160_acc.c`, `bmi160_gyro.c`, `stk3x1x.c`) contains a
  regulator or `hwPowerOn` call (bounded grep). The sensor rails are therefore
  always-on from the kernel's point of view; which MT6351 LDO (or fixed rail)
  feeds them is not recorded anywhere in the vendor software path. This
  confirms the [resource follow-up](../2026-09-07-gemini-sensors-upstream-architecture/BMI_RESOURCES.md)
  from source rather than from a live cached value.
- **F5. Which vendor sensor drivers are compiled.** The defconfig enables
  `CONFIG_MTK_BMI160_ACC`, `CONFIG_MTK_BMI160_GYRO`, `CONFIG_MTK_LSM6DS3A_NEW`,
  `CONFIG_MTK_LSM6DS3G_NEW`, `CONFIG_MTK_STK3X1X_NEW`, `CONFIG_MTK_BMI160_STC`,
  `CONFIG_CUSTOM_KERNEL_STEP_COUNTER` and
  `CONFIG_CUSTOM_KERNEL_SIGNIFICANT_MOTION_SENSOR`; it leaves
  `CONFIG_CUSTOM_KERNEL_MAGNETOMETER`, `CONFIG_MTK_MMC3524XD`,
  `CONFIG_CUSTOM_KERNEL_BAROMETER`, `CONFIG_MTK_BMP280`,
  `CONFIG_CUSTOM_KERNEL_HUMIDITY` and `CONFIG_MTK_HTS221` unset
  ([`aeon6797_6m_n_defconfig` lines 219–240](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/configs/aeon6797_6m_n_defconfig#L219-L240)).
  `CONFIG_MTK_TINYSYS_SCP_SUPPORT=y` (line 282) but `CONFIG_MTK_SCP_SENSORHUB_V1`
  is not set, so every per-sensor Makefile takes its non-hub branch
  ([`accelerometer/Makefile`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/accelerometer/Makefile),
  [`magnetometer/Makefile`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/magnetometer/Makefile)).
  Consequence: **the Gemini has no sensor hub path; all sensors are AP-side
  I2C1 clients**, and the stock kernel has **no magnetometer, barometer or
  humidity driver at all**. The `0x30`, `0x77` and `0x5f` clients were never
  touched by the vendor kernel.

### BMI160 accelerometer and gyroscope (vendor behaviour)

- **F6. Both vendor IMU drivers force their client to `0x69` and accept chip
  IDs `0xd0`–`0xd3`; only the gyro rejects a mismatch.**
  `bmi160_acc_i2c_probe` sets `client->addr = 0x69`
  ([`bmi160_acc.c` line 3539](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/accelerometer/bmi160_acc/bmi160_acc.c#L3539));
  `bmi160_acc_check_chip_id` reads register `0x00` twice and logs success for
  `SENSOR_CHIP_ID_BMI` (`0xD0`), `_C2` (`0xD1`), `_C3` (`0xD3`) but returns
  the read status either way
  ([lines 551–572](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/accelerometer/bmi160_acc/bmi160_acc.c#L551-L572),
  [header lines 143–145](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/accelerometer/bmi160_acc/bmi160_acc.h#L143-L145)).
  `bmi160_gyro_i2c_probe` also sets `client->addr = 0x69` (line 1509) and
  `bmg_get_chip_type` fails with `INVALID_TYPE` outside the same three IDs
  ([`bmi160_gyro.c` lines 619–645](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/gyroscope/bmi160_gyro/bmi160_gyro.c#L619-L645)).
  The header's nominal `BMI160_I2C_ADDR` is `0x68` (header line 103), which
  explains the live `0x68` client name; the transfer address is `0x69`. This
  is the source form of the disassembly finding in the recovery record.
- **F7. Vendor IMU initialisation sequence.** Accelerometer
  `bmi160_acc_init_client`: chip-ID read, soft reset (`CMD 0x7E = 0xB6`),
  5 ms, ODR 200 Hz, OSR4 averaging, range ±4 g, interrupt-enable registers
  `0x50`–`0x52` cleared, then accelerometer suspend
  ([lines 1691–1725](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/accelerometer/bmi160_acc/bmi160_acc.c#L1691-L1725)).
  Gyroscope `bmg_init_client`: chip ID, ODR 100 Hz, range ±2000 °/s,
  gyro suspend
  ([lines 794–808](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/gyroscope/bmi160_gyro/bmi160_gyro.c#L794-L808)).
  Power on writes `CMD_PMU_ACC_NORMAL` / `CMD_PMU_GYRO_NORMAL` on demand
  (acc lines 636–672). Two Linux clients therefore drive one chip's `CMD`
  register with no shared lock other than the I2C core; the accelerometer's
  soft reset also resets the gyro configuration. Mainline's single IIO
  device per chip is the correct model, and these values (200 Hz/±4 g,
  100 Hz/±2000 °/s) are the vendor's operating point.
- **F8. The vendor accelerometer requests an interrupt it can never
  receive.** `bmi160_request_irq` looks up `"mediatek, ALS-eint"`, maps its
  interrupt and requests it as `bmi160_accint` with `IRQF_TRIGGER_RISING`
  ([lines 3494–3513](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/accelerometer/bmi160_acc/bmi160_acc.c#L3494-L3513));
  the work handler reads `INT_STATUS[0..3]` (`0x1C`–`0x1F`) and dispatches
  step-detector and significant-motion events (lines 3468–3485). But the
  driver never writes `INT_OUT_CTRL` (`0x53`), `INT_LATCH` (`0x54`) or
  `INT_MAP_0..2` (`0x55`–`0x57`): the header defines them (header lines
  179, 259–262) and `bmi160_acc.c` contains no reference to any of them
  (bounded grep). With the pin output disabled, the BMI160 drives neither
  INT1 nor INT2, so the request is inert; the live ALS EINT counter at zero
  is consistent with this. This is the source basis for the
  [resource follow-up](../2026-09-07-gemini-sensors-upstream-architecture/BMI_RESOURCES.md)'s
  "do not copy the ALS IRQ into the IMU description".
- **F9. Step counter and significant motion are in-chip BMI160 features
  driven by a third vendor module through the same client.** `bmi160_stc.c`
  reuses `bmi160_acc_i2c_client` (lines 1231–1243), enables the chip's step
  counter and reads `STEP_CNT` `0x78`/`0x79`
  ([lines 134, 307–321](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/step_counter/bmi160_stc/bmi160_stc.c#L307-L321));
  it is selected by `CONFIG_MTK_BMI160_STC`
  ([`step_counter/Makefile` line 18](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/step_counter/Makefile#L18)).
  The pinned mainline BMI160 driver exposes no step counter; this is a
  feature gap, not a hardware-support gap, and belongs to userspace or a
  later upstream extension.
- **F10. The LSM6DS3 alternates are compiled, probe at `0x6b`, and fail on
  the WHO_AM_I check; this is why the live `0x6a`/`0x6b` clients are
  unbound.** The LSM6DS3 accelerometer driver matches the generic
  `"mediatek,gsensor"` node, forces `client->addr = 0x6B` and requires
  `WHO_AM_I` (`0x0F`) `== 0x69`
  ([`lsm6ds3-int.c` lines 626–637, 4715, 5133–5134](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/accelerometer/lsm6ds3-new/lsm6ds3-int.c#L4715),
  [header line 67](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/accelerometer/lsm6ds3-new/lsm6ds3-int.h#L67));
  the gyro half does the same on `"mediatek,gyro"`
  ([`lsm6ds3_gy.c` lines 183, 436–440, 2254](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/gyroscope/lsm6ds3-new/lsm6ds3_gy.c#L2254)).
  Both the BMI160 and LSM6DS3 drivers are built in (F5) and the live capture
  binds only the BMI160 pair, so on this unit nothing at `0x6b` answered
  `0x69` to register `0x0f`. Inference: no LSM6DS3 is populated; the
  `0x6a`/`0x6b` DT children are the board template's alternates. Public
  Gemian notes about LSM6DS3 units describe a different board population.
- **F11. Direction table.** `hwmsen_helper.c`'s `map[]` gives direction 7 as
  `sign={-1,-1,-1}, map={1,0,2}` and direction 6 (the LSM6DS3 alternate) as
  `sign={1,-1,-1}, map={0,1,2}`
  ([lines 570–581](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/hwmon/hwmsen/hwmsen_helper.c#L570-L581)).
  This confirms the recovery record's direction-7 matrix from source. The
  `cust_mag@0` node also uses direction 7 (F1), so a populated magnetometer
  would share the IMU's package orientation in the vendor model.

### STK3X1X light/proximity sensor (vendor behaviour)

- **F12. Probe, address and interrupt plumbing.** `stk3x1x_i2c_probe` sets
  `client->addr = hw->i2c_addr[0]` from the `cust_alsps@0` array
  (`<0x48 0 0 0>`), looks up `"mediatek, als-eint"` (lower case; the
  accelerometer uses upper case, F8), and configures PS interrupt mode 1 with
  ALS in polling mode (`polling_mode_ps = 0`, `polling_mode_als = 1`)
  ([`stk3x1x.c` lines 5029, 5076–5090](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/alsps/stk3x1x-new/stk3x1x.c#L5029)).
  `stk3x1x_setup_eint` reads the node's `debounce`, selects the `pin_cfg`
  pinctrl state (GPIO88/EINT11 pull-up, F3), maps the interrupt and requests
  it with `IRQF_TRIGGER_NONE` (trigger type from the DT tuple), returning
  `-EINVAL` when the node has no mappable interrupt
  ([lines 2491–2548](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/alsps/stk3x1x-new/stk3x1x.c#L2491-L2548));
  `stk3x1x_init_client` calls it on first boot and fails the probe on error
  (lines 2551–2575). The handler does `disable_irq_nosync` and schedules
  work (lines 2481–2489). The pull-up plus proximity-interrupt mode implies
  an active-low, open-drain-style INT; the exact live trigger tuple is in the
  private capture, not here.
- **F13. Register programme at init.** After `SW_RESET` (`0x80`) the driver
  writes `STATE` from its cached value, `PSCTRL = 0x31` (persistence 4,
  gain 64×, IT 0.391 ms; bits 7:6 cleared in PS polling mode), `ALSCTRL =
  0x39` (persistence 1, gain 64×, IT 50 ms), `LEDCTRL = 0xFF` (100 mA IRDR,
  64/64 duty), `WAIT = 0x07` (50 ms), then thresholds
  ([defines lines 80–83](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/alsps/stk3x1x-new/stk3x1x.c#L80-L83),
  [init lines 2551–2625](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/alsps/stk3x1x-new/stk3x1x.c#L2551-L2625)).
  `STK_TUNE0` is defined (line 69), so proximity thresholds are auto-tuned
  around a measured crosstalk (`MAX_MIN_DIFF 140`, `LT_N_CT 70`, `HT_N_CT 100`,
  lines 100–102) rather than taken from the DT `ps_threshold_high/low =
  50/40` (F1). `STK_ALS_FIR` is also defined (line 71). The register map
  (`STATE 0x00` … `THD 0x06–0x0D`, `FLAG 0x10`, `DATA 0x11–0x14`,
  `PDT_ID 0x3E`, `RSRVD 0x3F`; [header lines 57–82](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/alsps/stk3x1x-new/stk3x1x.h#L57-L82))
  is the one the earlier reuse audit matched to upstream.
- **F14. Vendor identity handling, and what the observed `0x11`/`0xc2` means
  in it.** `stk3x1x_read_id` reads two bytes at `0x3E`, names only
  `STK3310SA 0x17`, `STK3311SA 0x1E` and `STK3311WV 0x1D` for special
  handling, treats VID `0xC3` as a board flag, calls `stk3x1x_read_otp25`
  (which **writes** `STATE`, `0x90` and `0x92` before reading `0x91`; lines
  793–840), and accepts any PID whose high nibble is `0x1`, `0x2` or `0x3`
  ([lines 116–118, 847–903](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/alsps/stk3x1x-new/stk3x1x.c#L847-L903)).
  The observed `0x11` therefore takes the generic `0x1x` path with the
  default LED/ratio settings; the vendor has no variant-specific behaviour
  for it and gives VID `0xc2` no meaning. The vendor's own init is not
  write-free (OTP access), so it is not a model for a read-only identity
  check; the earlier bounded observation stays the only safe one.

### Magnetometer, barometer, humidity candidates

- **F15. The vendor "MMC3530" driver is a MEMSIC MMC3524x driver, it is not
  compiled, and its register map equals the mainline `mmc35240` driver's.**
  `mmc3524xd.c` matches `"mediatek,msensor_mmc3530"` and reads
  `"mediatek,mmc3530"` configuration (lines 181–182, 2933–2939); its probe
  first issues a `TM` (take measurement) command and then requires product
  ID register `0x20` to read `0x08` or `0x09`
  ([lines 2695–2756](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/magnetometer/mmc3524xd/mmc3524xd.c#L2740-L2756)).
  Its header has `DATA 0x00`, `DS 0x06`, `CTRL 0x07` (TM/CM/SET/RESET/REFILL
  bits), `BITS 0x08`, `PRODUCTID_1 0x20`, 7-bit address `0x30`
  ([`mmc3524xd.h` lines 15–38](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/magnetometer/mmc3524xd/mmc3524xd.h#L15-L38)).
  The pinned upstream `mmc35240.c` uses `XOUT_L 0x00`…`ZOUT_H 0x05`,
  `STATUS 0x06`, `CTRL0 0x07` (same TM/CMM/SET/RESET/REFILL bit positions),
  `CTRL1 0x08`, `ID 0x20`
  ([lines 25–52](https://github.com/gregkh/linux/blob/v7.1.3/drivers/iio/magnetometer/mmc35240.c#L25-L52)).
  This corrects the resource map's "Linux 7.1.3 has no matching driver":
  the vendor's own driver family is the MMC35240 register model. Because
  `CONFIG_MTK_MMC3524XD` is unset (F5), **the stock kernel never addressed
  `0x30`**, so population is unknown in both directions.
- **F16. BMP280 and HTS221 are DT template candidates with no vendor driver
  built (F5).** Upstream has `bosch,bmp280` (`ID 0xD0 == 0x58`;
  [`bmp280.h` lines 326–332](https://github.com/gregkh/linux/blob/v7.1.3/drivers/iio/pressure/bmp280.h#L326-L332))
  and `st,hts221` (`WHO_AM_I 0x0F == 0xBC`;
  [`hts221_core.c` lines 22–23](https://github.com/gregkh/linux/blob/v7.1.3/drivers/iio/humidity/hts221_core.c#L22-L23)).
  Nothing in the vendor path, live capture or public notes shows either part
  populated; the `0x77` and `0x5f` DT children are the same template
  inheritance as the LSM6DS3 alternates (F10).

### Mainline 7.1.3 and this repository

- **F17. Upstream `bmi160` matches the observed silicon and tolerates the
  vendor's omissions.** `bmi_chip_ids` = `0xD3` (BMI120), `0xD1` (BMI160);
  an unknown ID only warns (`"Chip id not found"`) and probe continues
  ([`bmi160_core.c` lines 29–30, 116–118, 740–744](https://github.com/gregkh/linux/blob/v7.1.3/drivers/iio/imu/bmi160/bmi160_core.c#L740-L744));
  `vdd`/`vddio` are acquired with `devm_regulator_bulk_get` (lines 840–842),
  so a node without supplies gets dummy regulators; the interrupt is
  optional and selected by name `INT1`/`INT2` with the trigger type taken from
  the DT tuple and written to `INT_OUT_CTRL`/`INT_LATCH`/`INT_MAP`
  (lines 559–620, 638–651, 655–695); probe soft-resets and leaves both
  accel and gyro in normal mode (lines 720–750). Compatibles are
  `bosch,bmi120` and `bosch,bmi160`
  ([`bmi160_i2c.c` lines 24–26](https://github.com/gregkh/linux/blob/v7.1.3/drivers/iio/imu/bmi160/bmi160_i2c.c#L24-L26));
  the binding allows `interrupts`, `interrupt-names`, `drive-open-drain`,
  `vdd-supply`, `vddio-supply`, `mount-matrix`
  ([`bosch,bmi160.yaml`](https://github.com/gregkh/linux/blob/v7.1.3/Documentation/devicetree/bindings/iio/imu/bosch,bmi160.yaml)).
- **F18. Upstream `stk3310` accepts the register model, logs `0x11` as
  unknown and continues.** `stk3310_chip_ids` = `0x31`, `0x13`, `0x15`,
  `0x1E`, `0x12`, `0x1D`, `0x51`; `stk3310_init` reads `0x3E`, prints
  `"new unknown chip id"` on a miss, enables ALS+PS and PS interrupts
  ([`stk3310.c` lines 38–44, 85–92, 482–507](https://github.com/gregkh/linux/blob/v7.1.3/drivers/iio/light/stk3310.c#L482-L507));
  the IRQ is optional and requested `IRQF_TRIGGER_FALLING | IRQF_ONESHOT`
  (lines 636–641); OF compatibles are `sensortek,stk3013/3310/3311/3335`
  (lines 716–719) and the binding adds `proximity-near-level`
  ([`stk33xx.yaml`](https://github.com/gregkh/linux/blob/v7.1.3/Documentation/devicetree/bindings/iio/light/stk33xx.yaml)).
  The 2024 upstream series that relaxed the ID check and added `0x15`/`0x1E`
  ([patch 1/3](https://lkml.iu.edu/hypermail/linux/kernel/2405.2/04552.html),
  [patch 3/3](https://lkml.iu.edu/hypermail/linux/kernel/2405.2/04554.html))
  does not mention `0x11`; no public source found names the `0x11` variant.
- **F19. Upstream `mmc35240` validates nothing at probe and performs
  SET/RESET.** `mmc35240_init` reads `ID 0x20` only for a debug print, then
  runs the SET/RESET coil sequence and reads OTP
  ([lines 179–230](https://github.com/gregkh/linux/blob/v7.1.3/drivers/iio/magnetometer/mmc35240.c#L203-L230));
  compatible `memsic,mmc35240` lives in `trivial-devices.yaml` (line 250);
  `CONFIG_MMC35240` is in `drivers/iio/magnetometer/Kconfig` (lines 131–136).
- **F20. Upstream `mt6797.dtsi` has `i2c1` disabled and the SoC offers three
  I2C1 pin pairs.** `i2c1: i2c@11008000` carries `status = "disabled"` and
  the `mt6797-i2c`/`mt6577-i2c` compatibles
  ([lines 300–313](https://github.com/gregkh/linux/blob/v7.1.3/arch/arm64/boot/dts/mediatek/mt6797.dtsi#L300-L313));
  `SCL1_0/SDA1_0` are GPIO55/56, `SCL1_1/SDA1_1` GPIO53/54, `SCL1_2/SDA1_2`
  GPIO60/58
  ([`mt6797-pinfunc.h` lines 292–336](https://github.com/gregkh/linux/blob/v7.1.3/include/dt-bindings/pinctrl/mt6797-pinfunc.h#L292-L336)).
  Neither the public vendor DTS nor any repository record names which pair
  the Gemini uses; the vendor controller driver takes the pins from a
  non-public board file.
- **F21. Repository state.** Patch 0052 adds one disabled `bosch,bmi160`
  child at `0x69` with the direction-7 matrix under the still-disabled
  `&i2c1`, with no pinctrl, supplies or interrupt
  ([patch 0052](../../patches/v7.1.3/0052-arm64-dts-mediatek-add-disabled-Gemini-BMI160-candidate.patch));
  `configs/gemini.fragment` sets `CONFIG_IIO=y`, `CONFIG_BMI160_I2C=m`,
  `CONFIG_STK3310=m` (lines 32–45) and nothing for MMC35240, BMP280 or
  HTS221; no patch configures I2C1 pins. Lid/hall switch on GPIO66/EINT5 is a
  `gpio-keys` matter already in the
  [live resource map](../../docs/hardware/mt6797-live-resource-map.md), not a
  sensor chip, and is out of scope here.

## Part 2: hypotheses, ranked by value per device minute

"Gemian read" means one bounded, read-only inspection of the running stock
kernel over the known-good LAN SSH path under the standing authorization;
"mainline boot" means a new reviewed experiment with its own candidate,
hypothesis and stop conditions. The I2C1 enablement that every mainline test
below needs is shared with the display bias chip
([roadmap step 7](../../docs/ROADMAP.md#after-wi-fi-remaining-driver-gaps)).
None of these is admitted by this record.

1. **H1. One BMI160 is populated with SDO high, answering only at `0x69`; a
   mainline `bosch,bmi160` node at `0x69` with no supplies and no interrupt
   enumerates one IIO device with sane static gravity after the direction-7
   matrix (F6, F7, F11, F17).** Test: the first I2C1 mainline boot enables
   patch 0052's node as is (the upstream probe's soft reset is the same
   command the vendor issues at every init, F7), then reads
   `in_accel_*_raw`, `in_anglvel_*_raw` and `in_accel_mount_matrix` with the
   device flat and on each edge. A second probe at `0x68` is not needed:
   the vendor never used it and a `-ENXIO`/no-ACK there would only confirm
   F6. Confidence: high. This is the cheapest decision-changing sensor test
   and it also validates I2C1 for the display bias chip.
2. **H2. GPIO65 is the BMI160 INT1 wire (EINT4 alternate), unused by the
   stock kernel (F3, F8).** The board dedicates a pulled-down pin to the
   `gyro` node and the IMU drives no interrupt output, so nothing else
   explains the pin's name. Test, after H1: add
   `interrupts = <65 IRQ_TYPE_EDGE_RISING>` (EINT4), `interrupt-names =
   "INT1"` and count `/proc/interrupts` with the data-ready trigger enabled
   at 100 Hz; a static count means INT2 or no wire, so retry with `"INT2"`
   once. A Gemian read cannot settle this because the vendor never enables
   the output. Confidence: medium on the pin, low on INT1 vs INT2.
3. **H3. The IMU and ALS rails are always-on fixed or default-on PMIC rails,
   so mainline nodes may omit `vdd-supply`/`vddio-supply` at first without
   changing device state (F4, F17).** Test: H1 succeeding is the test; if the
   probe fails with no ACK, the next step is a Gemian read of the MT6351 LDO
   enable bits in the private register dump rather than guessing a supply.
   Record the rail owner before any suspend/resume test. Confidence: high.
4. **H4. The STK `0x11` part is a register-compatible STK3311-family device
   and the upstream `stk3310` driver works through the
   `sensortek,stk3311` compatible, with the unknown-ID message as the only
   difference (F13, F14, F18).** The vendor uses identical register
   semantics for `0x11` and for its named variants, with no `0x11`-specific
   branch. Test, in the H1 boot or the next: a node at `0x48` with
   `compatible = "sensortek,stk3311"`, no interrupt, read
   `in_illuminance_raw` in the dark and under a lamp and `in_proximity_raw`
   with and without a hand over the sensor; compare ALS gain/IT behaviour with
   F13. Do not add `0x11` to the upstream ID table or a new compatible until
   the marketed part name is known; a vendor datasheet or Planet BOM note is
   the discriminator, and Julien's reference documents may hold it.
   Confidence: high for protocol, unresolved for the name.
5. **H5. The proximity interrupt is GPIO88/EINT11, active low, usable with
   `IRQ_TYPE_LEVEL_LOW` or falling edge (F3, F12, F18).** Test, after H4:
   add `interrupts = <88 IRQ_TYPE_LEVEL_LOW>` (EINT11), set
   `events/in_proximity_thresh_rising_value` above the idle reading and
   confirm one event per hand pass. Confidence: high for the pin, medium for
   the type (the live tuple in the private capture settles it first).
6. **H6. Something answers at I2C1 `0x30` and it is MEMSIC MMC3524x/35240
   class (register `0x20` reads `0x08` or `0x09`), so mainline
   `memsic,mmc35240` is the driver (F15, F19).** Test: one read of register
   `0x20` at `0x30`, with no `TM`, `SET` or `RESET`, from a mainline boot
   (`i2cget`-class read on the enabled bus) or, if admitted, a Gemian read
   through a bounded tool, since the stock kernel has no client bound there.
   No ACK means unpopulated and closes the magnetometer question; `0x08`/
   `0x09` admits an `mmc35240` node (whose probe then performs SET/RESET,
   harmless for a magnetometer). Confidence: medium that a part is present
   (the board template and the direction-7 `cust_mag` suggest a design slot,
   but the vendor shipped no driver), high on the driver if it is.
7. **H7. `0x77` (BMP280) and `0x5f` (HTS221) are unpopulated (F16).** Test:
   in the same session as H6, read `0xD0` at `0x77` and `0x0F` at `0x5f`;
   expected no ACK. `0x58`/`0xBC` would admit the existing upstream drivers
   with no further RE. Confidence: high that they are absent; cost is two
   reads.
8. **H8. The Gemini uses the `SCL1_0/SDA1_0` pair (GPIO55/56) for I2C1
   (F20).** This is the first (function 1) muxing and the one the SoC
   documentation treats as default; the alternates are function 3/4 on pins
   the public board DTS assigns to other roles. Test: a Gemian read of the
   live pinmux state for GPIO53–60 in the existing private GPIO dump (the
   [live resource map](../../docs/hardware/mt6797-live-resource-map.md)
   capture family) before the first mainline I2C1 boot; a wrong pair costs a
   full boot with a dead bus. Confidence: medium.
9. **H9. Step counting, significant motion, and every vendor virtual sensor
   stay out of the kernel (F9).** The chip features exist, but upstream
   `bmi160` has no interface for them and the project's userspace-fusion rule
   stands. No device test; revisit only if a userspace consumer asks for the
   hardware step counter.
10. **H10. The LSM6DS3 alternates need no mainline consideration (F10).**
    No test; the vendor's own ID check already failed on this unit. If a
    future unit binds `lsm6ds3` in Gemian, the upstream `st,lsm6ds3`
    (`st_lsm6dsx`) driver is the counterpart, with direction 6 as the matrix
    source.

## Consequences for the roadmap (no changes applied here)

- The roadmap's sensor unknowns resolve as: rails are always-on and unnamed
  in the vendor path (F4, H3); the vendor uses **no** IMU interrupt and GPIO65
  is the only candidate wire (F3, F8, H2); the ALS/PS interrupt is GPIO88/
  EINT11 pulled up (F3, F12, H5); mount orientation is confirmed from the
  vendor table (F11) and still needs the one physical-frame check in H1.
- The STK `0x11` question is a naming problem, not a protocol problem (F14,
  F18, H4): upstream will drive it today under `sensortek,stk3311` with a
  log line. An upstream ID-table addition needs the marketed part name.
- The magnetometer is reopened: the vendor's own driver is the MMC35240
  register family and mainline has that driver (F15, F19); a single
  register read (H6) decides whether a compass exists on this unit.
- Two addresses (`0x77`, `0x5f`) can be closed with two reads (H7); two more
  (`0x6a`, `0x6b`) are closed by source (F10).
- Before the first I2C1 boot, settle the pin pair (H8); it is the only
  sensor-related item a Gemian read answers more cheaply than a boot.

## Validation

Documentation-only change: `./scripts/check-repository` and link checks apply;
no kernel build, DT check or device action was performed. Line numbers were
taken from the exact fetched files recorded in `source-inputs.json`. The two
LKML citations in F18 were read for their chip-ID lists only.
