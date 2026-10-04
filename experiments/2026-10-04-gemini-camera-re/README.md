# Experiment: Gemini camera path reverse engineering

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-04-gemini-camera-re` |
| Status | `completed` (offline source review; no build, boot or device access) |
| Subsystem | Camera sensor ("SP5509"/Hi-556 register map), camera rails and pins, MCLK, SENINF/CSI-2 receiver, CAM/CAMSV/ISP, autofocus, flash, calibration EEPROM |
| Device variant | Project Gemini (Gemian `3.18.41+`, MT6797X, MT6351 E2) |
| Date(s) | 2026-10-04 |
| Investigator(s) | Claude (owner-requested investigation) |
| Tracking issue | Not yet assigned |

## Question

What does the stock Gemian kernel actually do to power, clock, identify and
stream the Gemini's camera, which parts of that path have a mainline
equivalent, what is irreducibly blocked, and what is the cheapest first
experiment? The roadmap keeps cameras as feasibility work only. This record
answers from the pinned public vendor source and the pinned Linux 7.1.3 tree,
separates verified facts from hypotheses, and ranks the hypotheses by how they
should be tested. It changes no patch, profile, candidate or device state.

The [2026-07-13 camera recovery record](../2026-07-13-camera-recovery/README.md)
owns the live observations this builds on: the runtime identity strings
(`AEON_CAMERA0=non_sensor`, `AEON_CAMERA1=sp5509mipirawsls`), the I2C wrapper
topology (`2-002d`, `3-0036`, `8-0036`, `2-0072`, `3-000c`), the vendor ELF
probe transaction (register `0x0f16`, raw ID `0x0556`, write IDs `0x40`/`0x50`)
and the [MT6797 pipeline contract](../2026-07-13-camera-recovery/results/mt6797-camera-pipeline-contract.md)
(window, IRQ, clock and larb-port inventory). This record does not repeat that
inventory; it adds what that record left open: which socket is populated, which
bus, rails, pins and MCLK the fitted module uses, what the "SP5509" is at
register level, where the receiver programming lives, and what the lens, flash
and EEPROM paths are.

## Inputs

Every vendor citation below is a public GPL file at Gemian commit
`8cfe6596a503612e3332d9c26e292a19525a7f07`, the same commit the
[charging record](../2026-10-04-gemini-charging-re/README.md) used. Every
mainline citation is Linux `7.1.3` as pinned in `kernel/manifest.json`.
libcamera citations are the `libcamera-org/libcamera` GitHub mirror of the
upstream `master` branch on 2026-10-04. Exact URLs, sizes and SHA-256 values
are in [`source-inputs.json`](source-inputs.json). Line numbers refer to those
exact revisions. No vendor source, register table, firmware or private capture
is copied into this repository; register addresses, bit positions and
configuration values are cited as facts.

Two caveats apply throughout. First, as in the charging record, the public
board files do not always describe the live Gemian image: the public
`cust_i2c.dtsi` places the camera wrappers on `i2c0` while the live wrappers
sit on `i2c2`/`i2c3` (F8), and the public defconfig's sensor list names two
source directories that the public commit does not carry (F3). Where the public
tree and the live capture disagree, the live capture wins. Second, the prior
camera record used a different vendor checkout (Planet commit `c5b0be85…`);
the camera files inspected here hash identically where both records cite them
(`kd_camera_hw.c`, `kd_sensorlist.h`, `kd_imgsensor.h`, `camera_isp.h`,
`mt6797.dtsi`, `aeon6797_6m_n.dts`), so the two records describe the same
vendor code.

## Part 1: verified facts

### Which cameras exist and which socket is populated

- **F1. The Gemini has a built-in 5 MP front camera; the rear camera is a
  5 MP optional accessory without a flash.** The
  [Wikipedia specification](https://en.wikipedia.org/wiki/Gemini_PDA) lists
  "Front camera 5 MP" and a "Rear camera 5MP" as a paid campaign extra; The
  Register's
  [2018-04-27 review of the accessory](https://www.theregister.com/2018/04/27/gemini_camera_esim_software_updates/)
  describes it as a £39 module that "is easily slotted into a port behind the
  screen" with "no flash". These are product facts, not source facts; they
  frame F2.
- **F2. The vendor proc names map to sockets, not to physical positions:
  `AEON_CAMERA0` is the MAIN socket and `AEON_CAMERA1` is the SUB socket.**
  `MAIN_CAM_PROC_NAME "AEON_CAMERA0"` / `SUB_CAM_PROC_NAME "AEON_CAMERA1"` at
  [`kd_sensorlist.c` lines 78–79](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/imgsensor/src/mt6797/kd_sensorlist.c#L78-L79);
  the strings start as `KDIMGSENSOR_NOSENSOR` (lines 86–87) and are overwritten
  with the driver name only when a sensor on that socket is found
  ([lines 2173–2175](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/imgsensor/src/mt6797/kd_sensorlist.c#L2173-L2175)).
  Combined with the live `camera0=non_sensor`, `camera1=sp5509mipirawsls`
  ([live repeat](../2026-07-13-camera-recovery/results/live-camera-repeat-20260714.txt)),
  the development unit has an SP5509-class sensor on the **SUB** socket and
  nothing found on the MAIN socket. With F1, the SUB socket is the built-in
  front camera and the MAIN socket is the empty rear-accessory port. The last
  step (SUB = front) is an inference from the product description, not from
  source.
- **F3. The public sensor list differs from the live binary, and the extra
  entries are the alternative 5 MP parts.** The defconfig selects
  `CONFIG_CUSTOM_KERNEL_IMGSENSOR="sp5506_mipi_raw sp5509_mipi_raw_sls st55a_mipi_raw sp5509_main_mipi_raw"`
  ([line 189](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/configs/aeon6797_6m_n_defconfig#L189)).
  `kd_sensorlist.h` registers `SP5506_MIPI_RAW` with the **OV5675** ID and
  init function and `ST55A_MIPI_RAW` with the **S5K5E2YA** ID and init
  function
  ([lines 168–186](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/imgsensor/src/mt6797/kd_sensorlist.h#L168-L186)),
  which is why the live `kallsyms` carried `OV5675_MIPI_RAW_SensorInit` and
  `S5K5E2YA_MIPI_RAW_SensorInit`. The `sp5506_mipi_raw/` and `st55a_mipi_raw/`
  directories are absent from this public commit (fetch returned 404), so the
  OV5675 and S5K5E2YA code the live image runs is not inspectable here. They
  are the manufacturer's second-source 5 MP options for the two sockets; no
  evidence says either is fitted.

### What the "SP5509" is at register level

- **F4. The SLS sensor identity transaction is the Hynix Hi-556's.** The
  vendor defines `SP5509_SENSOR_ID_SLS 0x556` and `SP5509_MAIN_SENSOR_ID
  0x557`
  ([`kd_imgsensor.h` lines 259–261](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/imgsensor/inc/kd_imgsensor.h#L259-L261));
  the SLS driver reads register `0x0f16`
  ([`sp5509mipiraw_Sensor.c` lines 1171–1174](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/imgsensor/src/mt6797/sp5509_mipi_raw_sls/sp5509mipiraw_Sensor.c#L1171-L1174))
  and the "main" variant returns the same register plus one
  ([`sp5509mainmipiraw_Sensor.c` lines 1167–1170](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/imgsensor/src/mt6797/sp5509_main_mipi_raw/sp5509mainmipiraw_Sensor.c#L1167-L1170)),
  so both tables match a chip that answers `0x0556`. Upstream
  `drivers/media/i2c/hi556.c` defines `HI556_REG_CHIP_ID 0x0f16` and
  `HI556_CHIP_ID 0x0556`
  ([lines 27–28](https://github.com/gregkh/linux/blob/v7.1.3/drivers/media/i2c/hi556.c#L27-L28)).
  The vendor file's stale "Hi-556" comments that the prior record dismissed
  are therefore accurate about the silicon.
- **F5. The vendor SLS register programming is the upstream Hi-556 sequence
  with one PLL difference.** Side by side (vendor `sensor_init` from
  [line 518](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/imgsensor/src/mt6797/sp5509_mipi_raw_sls/sp5509mipiraw_Sensor.c#L518);
  upstream tables from
  [line 125](https://github.com/gregkh/linux/blob/v7.1.3/drivers/media/i2c/hi556.c#L125)):

  | Register | Vendor SLS | Upstream hi556 | Meaning (per upstream names) |
  | --- | --- | --- | --- |
  | `0x0a00` | `0x0000` first (line 521) | `HI556_REG_MODE_SELECT`, standby `0x0000`, streaming `0x0100` (lines 30–32) | mode select |
  | `0x0e00`, `0x0e02`, `0x0e0c` | `0x0102`, `0x0102`, `0x0100` (522–524) | identical first three entries of `mipi_data_rate_874mbps` (126–128) | PLL/MIPI preamble |
  | `0x2000`…`0x2016` | `0x7400`, `0x001c`, `0x0242`, `0x0942`, `0x7007`, `0x0fd9`, `0x0259`, `0x7008`, `0x160e`, `0x0047`, `0x2118`, `0x0041` (525–536) | identical (129–140) | sensor microcode block |
  | `0x0008` | `0x0b00` (712) | `HI556_REG_LLP`, `.llp = 0x0b00` (41, 313, 565) | line length 2816 |
  | `0x0006` | `0x07bc` (init), `0x0814` class in modes | `HI556_REG_FLL`, `HI556_FLL_30FPS 0x0814` (35–36) | frame length |
  | `0x0a12` / `0x0a14` | `0x0a20` / `0x0798` (727–728) | identical (328–329, 375–376) | 2592 × 1944 output |
  | `0x0902` | `0x4319` (800) | identical (386) | MIPI TX operation mode |
  | `0x000e` | `0x0000`/`0x0100`/`0x0200`/`0x0300` mirror/flip (480–490) | not driven by upstream | orientation |
  | `0x0f30` / `0x0f32` | **`0x6e25`** / `0x7067` (683–684, 772–773) | **`0x5b15`** / `0x7067` (288–289, 354–355) | PLL |

  The only systematic difference is `0x0f30`, and the vendor runs the sensor
  from a **24 MHz** MCLK (`.mclk = 24`,
  [line 247](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/imgsensor/src/mt6797/sp5509_mipi_raw_sls/sp5509mipiraw_Sensor.c#L247))
  while upstream requires **19.2 MHz** (`HI556_MCLK 19200000`, line 23, enforced
  at [lines 1349–1352](https://github.com/gregkh/linux/blob/v7.1.3/drivers/media/i2c/hi556.c#L1349-L1352)).
  A 24 MHz PLL variant is therefore the one register-table change a mainline
  driver needs; the rest of the vendor tables add nothing the upstream driver
  does not already carry.
- **F6. Link and timing contract (vendor SLS `imgsensor_info`, lines 49–250):**
  two MIPI lanes, "NCSI2" PHY selection, manual settle delay, RAW Gr first
  pixel, 176 MHz pixel clock, 2592 × 1944 at line length 2816 / frame length
  2083 (30 fps class), 640 × 480 at frame length 520 (120 fps class),
  1296 × 972, I2C write IDs `0x40` then `0x50` (7-bit `0x20`/`0x28`) at
  300 kHz
  ([lines 244–250](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/imgsensor/src/mt6797/sp5509_mipi_raw_sls/sp5509mipiraw_Sensor.c#L244-L250)).
  Upstream hi556 is also 2-lane only
  ([lines 24, 1233–1234](https://github.com/gregkh/linux/blob/v7.1.3/drivers/media/i2c/hi556.c#L1233-L1234))
  with a single 437 MHz link frequency (line 22), i.e. 174.8 Mpixel/s at 10
  bits; the vendor's 176 MHz pixel clock implies about 440 MHz, consistent
  with the slightly different PLL in F5 (inference).
- **F7. Upstream `hi556` is ACPI-only in 7.1.3 and models a simpler power
  tree than the vendor table.** The driver has an ACPI id `INT3537` and no
  `of_match_table`
  ([lines 1425–1450](https://github.com/gregkh/linux/blob/v7.1.3/drivers/media/i2c/hi556.c#L1425-L1450));
  there is no `hynix,hi556` binding document in the tree (fetch 404; the
  [MAINTAINERS entry](https://github.com/gregkh/linux/blob/v7.1.3/MAINTAINERS#L11950-L11955)
  lists only the `.c`). It takes supplies `dovdd`, `avdd`, `dvdd`
  (lines 629–631), an optional `reset` GPIO (line 1338) and a clock named
  `clk` through `devm_v4l2_sensor_clk_get` (line 1344), which on a DT node
  uses `devm_clk_get_optional` and otherwise synthesises a fixed clock from a
  `clock-frequency` property
  ([`v4l2-common.c` lines 740–808](https://github.com/gregkh/linux/blob/v7.1.3/drivers/media/v4l2-core/v4l2-common.c#L740-L808)).
  Power-on enables clock, then regulators, waits 2 ms, releases reset and
  waits 5 ms ([lines 1291–1316](https://github.com/gregkh/linux/blob/v7.1.3/drivers/media/i2c/hi556.c#L1291-L1316)).
  The vendor SLS table is: MCLK on; reset low; power-down low; DOVDD 1.8 V;
  AVDD 2.8 V; DVDD 1.2 V; 10 ms steps; reset high; power-down high; AFVDD
  commented out
  ([`kd_camera_hw.c` lines 193–204](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/imgsensor/src/mt6797/camera_hw/kd_camera_hw.c#L193-L204)).
  Upstream has no power-down GPIO, so a DT description must either tie PDN
  high through pinctrl or add a small `powerdown-gpios` handling. libcamera's
  sensor property table has no `hi556` entry (it has `hi846` and `ov5675`;
  [`camera_sensor_properties.cpp`](https://github.com/libcamera-org/libcamera/blob/master/src/libcamera/sensor/camera_sensor_properties.cpp)),
  a small addition.

### Socket wiring: bus, rails, pins and MCLK

- **F8. The SUB socket is on I2C3 (`0x11014000`); the MAIN socket is on
  I2C2.** `SUPPORT_I2C_BUS_NUM1 2` / `SUPPORT_I2C_BUS_NUM2 3`
  ([`kd_sensorlist.c` lines 125–131](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/imgsensor/src/mt6797/kd_sensorlist.c#L125-L131)),
  and `DUAL_CAMERA_SUB_SENSOR` switches `gI2CBusNum` to `SUPPORT_I2C_BUS_NUM2`
  before `SensorOpen()`
  ([lines 1259–1262](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/imgsensor/src/mt6797/kd_sensorlist.c#L1259-L1262)).
  The vendor `i2c3` node is `0x11014000`
  ([`mt6797.dtsi` lines 2610–2620](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L2610-L2620)),
  matching the live `3-0036 camera_sub` wrapper. Upstream `mt6797.dtsi` has
  the same `i2c3@11014000` node, disabled, with pins `GPIO74 SCL3_0` /
  `GPIO75 SDA3_0`
  ([lines 173–177, 408–421](https://github.com/gregkh/linux/blob/v7.1.3/arch/arm64/boot/dts/mediatek/mt6797.dtsi#L408-L421)).
  The public `cust_i2c.dtsi` (`camera_main@10`, `camera_main_af@0c`,
  `camera_sub@3c` under `&i2c0`,
  [lines 11–27](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/cust_i2c.dtsi#L11-L27))
  is a stale generated file and does not describe the live wrappers. No
  Gemini DT patch in `patches/v7.1.3/` enables `i2c3` today.
- **F9. The front camera's rails are MT6351 LDOs: `vcama` 2.8 V, `vcamd`
  1.21 V, `vcamio` 1.8 V; no GPIO-controlled LDO is in its path.**
  `_hwPowerOn()` maps `AVDD`→`vcama`, `DVDD`→`vcamd`, `DOVDD`→`vcamio`,
  `AFVDD`→`vcamaf`, obtained with `regulator_get()` on the `kd_camera_hw1`
  device
  ([`kd_sensorlist.c` lines 3886–3898, 3947–3990](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/imgsensor/src/mt6797/kd_sensorlist.c#L3947-L3990)),
  whose node binds `vcama-supply` → `ldo_vcama`, `vcamd-supply` → `ldo_vcamd`,
  `vcamaf-supply` → `ldo_vldo28`, `vcamio-supply` → `ldo_vcamio`
  ([`mt6797.dtsi` lines 3868–3874](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L3868-L3874)).
  For the SUB socket (`pinSetIdx == 1`) the AVDD/DVDD/DOVDD steps take the
  regulator branch because the `CUST_SUB_*` entries of `PowerCustList` are
  `GPIO_UNSUPPORTED`
  ([`kd_camera_hw.c` lines 111–124, 528–538, 570–585](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/imgsensor/src/mt6797/camera_hw/kd_camera_hw.c#L528-L538)),
  and the 1.2 V DVDD request is rewritten to 1.21 V (lines 573–576) because
  the vendor `vcamd` range is 900000–1210000 µV
  ([`mt6797.dtsi` lines 602–606](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L602-L606)).
  The `GPIO73`/`GPIO254` `cam_ldo_vcama`/`cam_ldo_vcamd` pin states
  (board DTS [lines 1189–1215](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/aeon6797_6m_n.dts#L1189-L1215))
  are only reached through `mtkcam_gpio_set()` when a `PowerCustList` entry is
  `GPIO_SUPPORTED`, which holds only for `MAIN2_AVDD`/`MAIN2_DVDD`
  (lines 120–121, 457–497); the prior record's "rail GPIO73/GPIO254" belongs
  to a third socket this board does not populate. The local
  [MT6351 regulator patch 0015](../../patches/v7.1.3/0015-regulator-mt6351-add-regulator-driver.patch)
  already provides `VCAMA` (`0x0a12`), `VCAMD` (`0x0a40`), `VCAMIO`
  (`0x0a58`) and fixed 2.8 V `VLDO28`, so no new regulator work is needed.
- **F10. The front camera's control pins are reset `GPIO33` and power-down
  `GPIO29`; its MCLK is SENINF1's timing generator on pad `CMMCLK1`
  (`GPIO31`).** `kdCISModulePowerOn()` sets `pinSetIdx = 1` for the SUB
  socket
  ([`kd_camera_hw.c` lines 812–832](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/imgsensor/src/mt6797/camera_hw/kd_camera_hw.c#L812-L832)),
  which selects the `cam1_rst*`/`cam1_pnd*` pinctrl states (lines 243–246,
  301–324) defined on `GPIO33` and `GPIO29`
  (board DTS [lines 1133–1159](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/aeon6797_6m_n.dts#L1133-L1159));
  the MAIN socket uses `GPIO32`/`GPIO28` (lines 1105–1131). The SUB socket's
  MCLK step calls `ISP_MCLK2_EN()` (line 659), which sets bits 31 and 29 of
  `SENINF1_BASE + 0x0600`
  ([`camera_isp.c` lines 11660–11682](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/cameraisp/src/mt6797/camera_isp.c#L11660-L11682));
  the MAIN socket's `ISP_MCLK1_EN()` does the same on SENINF0. The MT6797 pin
  table has `CMMCLK0 = GPIO30`, `CMMCLK1 = GPIO31`, `CMMCLK2 = GPIO36`,
  `CMMCLK3 = GPIO35`
  ([`mt6797-pinfunc.h` lines 115, 119, 150, 159](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/include/dt-bindings/pinctrl/mt6797-pinfunc.h#L115-L119)).
  SENINF1 → `CMMCLK1` → `GPIO31` is the natural pairing but the pad mapping is
  not stated in source (inference; H2). The MCLK source clock is the
  `TOP_MUX_CAMTG` mux, parented to `UNIVPLL_D26` for the "48 MHz group" or
  `UNIVPLL2_D2` for the "52 MHz group" by `kdSetSensorMclk()`
  ([`kd_sensorlist.c` lines 3798–3812](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/imgsensor/src/mt6797/kd_sensorlist.c#L3798-L3812);
  clock handles at `mt6797.dtsi` lines 3876–3879); the division from that
  group to 24 MHz is a SENINF TG register field the kernel does not program
  (see F13). Upstream `mt6797-clk.h` has `CLK_TOP_MUX_CAMTG` (11),
  `CLK_TOP_UNIVPLL_D26` (64) and `CLK_TOP_UNIVPLL2_D2` (72).

### Receiver and ISP

- **F11. Address and interrupt inventory beyond the prior record.** The
  prior [pipeline contract](../2026-07-13-camera-recovery/results/mt6797-camera-pipeline-contract.md)
  lists IMGSYS, DIP, CAMSYS, CAMTOP, CAM A/B, CAMSV and SENINF windows. The
  same vendor `mt6797.dtsi` also gives: `smi_larb6@15001000` IRQ 245,
  `dpe@15028000` IRQ 261, `fd@1502b000` IRQ 259
  ([lines 3566–3625](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L3566-L3625)),
  `smi_larb2@1a001000` IRQ 258 (lines 3794–3797), the `camtop/cama/camb`
  `_set`/`_inner`/`_clr` aliases at `0x1a00b000`–`0x1a01d000` (lines
  3818–3861) and two MIPI RX analog windows `csi0@10217000` and
  `csi1@10218000` (lines 2195–2203). The ISP driver's mmap table confirms the
  hardware bases it hands to userspace: `CAM_A 0x1a004000`, `CAMSV_0
  0x1a050000`, `DIP_A 0x15022000`, `UNI_A 0x1a003000`, `SENINF 0x1a040000`,
  `MIPI_RX 0x10217000`, `GPIO 0x10002000`
  ([`camera_isp.h` lines 37–49](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/cameraisp/src/mt6797/inc/camera_isp.h#L37-L49)).
- **F12. Clock, power-domain and IOMMU providers: partly upstream, partly
  local, nothing camera-specific missing at provider level.** The vendor
  `imgsys_config` node consumes 14 clocks: `SCP_SYS_DIS`, `MM_SMI_COMMON`,
  `SCP_SYS_ISP`, `IMG_LARB6`, `IMG_DIP`, `IMG_DPE`, `IMG_FDVT`, `CAM_LARB2`,
  `CAM_CAMSYS`, `CAM_CAMTG`, `CAM_SENINF`, `CAM_CAMSV0/1/2`
  ([`mt6797.dtsi` lines 3531–3565](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L3531-L3565)).
  Upstream 7.1.3 provides `clk-mt6797-img.c` (`IMG_FDVT/DPE/DIP/LARB6`,
  [lines 23–26](https://github.com/gregkh/linux/blob/v7.1.3/drivers/clk/mediatek/clk-mt6797-img.c#L23-L26))
  and `MT6797_POWER_DOMAIN_ISP` (2) / `_MM` (3) in `mt6797-power.h`, but **no
  CAM clock driver** (the clk Makefile lists only `mt6797`, `-img`, `-mm`,
  `-vdec`, `-venc` at
  [lines 32–36](https://github.com/gregkh/linux/blob/v7.1.3/drivers/clk/mediatek/Makefile#L32-L36));
  the prior record's statement that 7.1.3 "contains MT6797 camera clock data"
  was measured on the patched VM tree. The local
  [patches 0021/0022](../../patches/v7.1.3/0022-clk-mediatek-add-MT6797-CAM-and-MJC-clocks.patch)
  add `mediatek,mt6797-camsys` gates `CAMSV2/1/0`, `SENINF`, `CAMTG` (parent
  `camtg_sel`), `CAMSYS`, `LARB2`, and
  [patch 0025](../../patches/v7.1.3/0025-arm64-dts-mediatek-mt6797-add-M4U-and-SMI.patch)
  adds `m4u@10205000`, `larb2@1a001000` and `larb6@15001000`, all
  `status = "disabled"`. Upstream `mtk_iommu.c`/`mtk-smi.c` have no
  `mt6797` compatible (nearest `mt6795`/`mt8167`,
  [`mtk_iommu.c` lines 1905–1907](https://github.com/gregkh/linux/blob/v7.1.3/drivers/iommu/mtk_iommu.c#L1905-L1907)),
  so the local [patch 0023](../../patches/v7.1.3/0023-dt-bindings-iommu-mediatek-add-MT6797-M4U-and-SMI.patch)
  bindings carry that. `configs/gemini.fragment` already sets
  `CONFIG_COMMON_CLK_MT6797_CAMSYS`, `CONFIG_MTK_IOMMU`, `CONFIG_MTK_SMI`
  (lines 18, 21–22).
- **F13. The SENINF/CSI-2 receiver programming lives in proprietary
  userspace, not in the GPL kernel.** `ISP_mmap()` maps the `SENINF`
  (`0x1a040000`, 16 KiB), `MIPI_RX` (`0x10217000`, 8 KiB) and `GPIO`
  (`0x10002000`) windows into the calling process
  ([`camera_isp.c` lines 9051–9105](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/cameraisp/src/mt6797/camera_isp.c#L9051-L9105)).
  The kernel itself only `of_iomap`s `seninf0`–`seninf3`
  (lines 11358–11399) to toggle the MCLK enable bits (F10) and to back up and
  restore registers across suspend (lines 9798 onward). That backup table
  addresses SENINF through `ISP_IMGSYS_BASE + 0x8000` (`SENINF_TOP_CTRL
  0x8000`, `SENINF_TOP_MUX_CTRL 0x8008`, `MIPI_RX_CON00_CSI0 0x8300`,
  `MIPI_RX_CON00_CSI1 0x8700`, lines 2098–2229), i.e. `0x15008000`, which
  is **not** the `0x1a040000` SENINF window the same driver maps; the
  struct is inherited from an earlier SoC layout and the relative offsets
  (`TOP_CTRL +0x0`, `TOP_MUX_CTRL +0x8`, CSI0 block `+0x300`, CSI1 block
  `+0x700`) are the only usable information in it. Consequence: no GPL file
  in this tree contains the CSI-2 lane, mux, data-type or timing programming
  for the Gemini's receiver. The private HAL (`camera.mt6797.so`, hashed in
  the [prior validation](../2026-07-13-camera-recovery/results/mainline-camera-source-validation.txt))
  holds it. This is the irreducible blocker for a native receiver driver;
  the CAM A/B/CAMSV interrupt and DMA handling, by contrast, is in the kernel
  and already summarised in the prior pipeline contract.
- **F14. Mainline 7.1.3 has no MediaTek camera receiver or ISP driver; an
  out-of-tree MT8365 series and libcamera support exist.**
  `drivers/media/platform/mediatek/` builds only `jpeg`, `mdp`, `vcodec`,
  `vpu`, `mdp3`
  ([Makefile](https://github.com/gregkh/linux/blob/v7.1.3/drivers/media/platform/mediatek/Makefile));
  no `isp/`, `seninf` or `camsv` directory exists (fetch 404). The
  "[PATCH v8 0/5] Add Mediatek ISP3.0" series (2025-01-22, MT8365, SENINF +
  CAMSV under `drivers/media/platform/mediatek/isp/`, CAMSV described as "a
  path to bypass the SoC ISP so that image data coming from the SENINF can go
  directly into memory";
  [cover letter](https://lkml.iu.edu/hypermail/linux/kernel/2501.2/06543.html))
  is the nearest public V4L2 implementation of the same block family, and
  libcamera's simple pipeline handler already lists `mtk-seninf` with
  `mtk-mdp` as converter
  ([`simple.cpp` lines 258–268](https://github.com/libcamera-org/libcamera/blob/master/src/libcamera/pipeline/simple/simple.cpp)).
  Whether MT6797 SENINF/CAMSV registers match MT8365's is not established
  (H4).

### Autofocus, flash and calibration EEPROM

- **F15. The only compiled lens driver is DW9714AF at 7-bit `0x0c`; the
  front module is probably fixed focus.** Defconfig: `CONFIG_MTK_LENS=y`,
  `CONFIG_MTK_LENS_DUMMYLENS_SUPPORT=y`, `CONFIG_MTK_LENS_DW9714AF_SUPPORT=y`
  ([lines 204–208](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/configs/aeon6797_6m_n_defconfig#L204-L208)).
  Both `MAINAF` and `SUBAF` character drivers list the same DW9714AF entry
  ([`main_lens.c` lines 70–81](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/lens/main/main_lens.c#L70-L81),
  [`sub_lens.c` lines 68–76](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/lens/sub/sub_lens.c#L68-L76));
  `DW9714AF.c` uses 8-bit slave `0x18` shifted to 7-bit `0x0c`
  ([lines 29, 55–57](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/lens/main/common/dw9714af/DW9714AF.c#L29)),
  which is exactly the live `3-000c SUBAF` wrapper on the front camera's bus.
  However the wrapper is a static DT client, the SLS power table never
  enables `AFVDD` (F7), and the vendor "main" table does
  ([`kd_camera_hw.c` line 216](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/imgsensor/src/mt6797/camera_hw/kd_camera_hw.c#L216)),
  so the front module is described as fixed focus and the AF rail/driver
  belong to the rear accessory socket. Upstream has `dw9714.c` and the
  `dongwoon,dw9714` binding (`vcc-supply`, optional `powerdown-gpios`;
  [binding](https://github.com/gregkh/linux/blob/v7.1.3/Documentation/devicetree/bindings/media/i2c/dongwoon,dw9714.yaml)),
  so if an actuator is ever found, no new driver is needed.
- **F16. There is no flash LED driver: the vendor builds `dummy_flashlight`.**
  `CONFIG_MTK_FLASHLIGHT=y`, `CONFIG_CUSTOM_KERNEL_FLASHLIGHT="dummy_flashlight"`
  ([defconfig lines 193–194](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/configs/aeon6797_6m_n_defconfig#L193-L194)).
  The dummy driver's open/release/ioctl return success and do nothing
  ([`dummy_flashlight.c` lines 130–160](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/flashlight/src/mt6797/dummy_flashlight/dummy_flashlight.c#L130-L160));
  `kd_flashlightlist.c` reports `FLASHLIGHT_NONE` to userspace and installs
  `strobeInit_dummy` for every socket
  ([lines 283–318, 339–344](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/flashlight/src/mt6797/kd_flashlightlist.c#L283-L318)).
  Board pin states for flash enable/torch/PWM in `aeon_gpio.dtsi` are all
  commented out
  ([lines 88–139](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/aeon_gpio.dtsi#L88-L139));
  the only concrete flash pin is a `hwen` state on `GPIO90`
  ([board DTS lines 1470–1503](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/aeon6797_6m_n.dts#L1470-L1503)),
  and the public `strobe_main@63` client on `i2c2`
  ([`cust_i2c.dtsi` lines 68–70](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/cust_i2c.dtsi#L68-L70))
  has no compiled driver (the flashlight Makefile adds only generic strobe
  objects plus the dummy directory). With F1 ("no flash"), there is nothing
  to port.
- **F17. Calibration EEPROM support is configured but its sources are not
  public.** `CONFIG_MTK_CAM_CAL=y`, `CONFIG_CUSTOM_KERNEL_CAM_CAL_DRV="BRCB032GWZ_3 GT24c32a cat24c16"`
  (defconfig lines 190–191) and a `cam_cal_drv` node with `main_bus = <2>`,
  `sub_bus = <3>`
  ([`mt6797.dtsi` lines 4266–4269](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L4266-L4269));
  the `cam_cal` source directory is absent from the public commit (404).
  Whether the front module carries an EEPROM is unknown. Mainline raw capture
  does not need it; lens shading and colour data would live in a libcamera
  tuning file.

### This repository today

- **F18. The Gemini DT enables no camera consumer and no I2C3.** The
  [Gemini board patch 0020](../../patches/v7.1.3/0020-arm64-dts-mediatek-add-Planet-Gemini-PDA.patch)
  enables `uart0` and `mmc0`; later patches enable `i2c0`, `i2c1` and `i2c6`
  for other devices, none `i2c2` or `i2c3`. `larb2`, `larb6` and `m4u` are
  disabled (F12). The support matrix row is `unknown` / `missing` /
  `required-nonfree` ([`HARDWARE_SUPPORT.md` line 80](../../docs/HARDWARE_SUPPORT.md)),
  and this record changes none of that.

## Part 2: hypotheses, ranked by value per device minute

"Gemian read" means one bounded, read-only inspection of the running stock
kernel over the known-good LAN SSH path under the existing standing
authorization; "mainline boot" means a new reviewed experiment with its own
candidate, hypothesis and stop conditions. None is admitted by this record.
The prior record's rule stands: no `i2cdetect`, no arbitrary writes, no
streaming as an identity probe.

1. **H1. The front camera is a Hynix Hi-556 (or an Hi-556 die under the
   SP5509 name) at 7-bit `0x20` on I2C3, and upstream `hi556` will identify
   it once it accepts a 24 MHz clock and a DT match (F4–F8).** Two tests, in
   order:
   (a) **Gemian read, zero new transactions:** the SLS driver prints
   `sp5509 i2c write id: 0x%x, ReadOut sensor id: 0x%x` on success
   ([lines 1210–1215](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/imgsensor/src/mt6797/sp5509_mipi_raw_sls/sp5509mipiraw_Sensor.c#L1210-L1215));
   one `dmesg`/`logcat` read after the stock camera app has been opened once
   settles the populated write ID (`0x40` → `0x20`, or `0x50` → `0x28`) and
   confirms `0x556` on this unit. This is the cheapest decision-changing
   measurement in the record.
   (b) **Mainline boot, read-only in intent:** `i2c3` enabled with the
   upstream pins, an `hi556` node at the address from (a) with
   `dovdd-supply = vcamio (1.8 V)`, `avdd-supply = vcama (2.8 V)`,
   `dvdd-supply = vcamd (1.2 V; 1.21 V if the LDO table has no 1.2 V step)`,
   `reset-gpios = GPIO33 active-low`, PDN `GPIO29` driven high by pinctrl,
   `clk` = a 24 MHz source (H2), plus a local patch adding an OF match, a
   24 MHz PLL entry (`0x0f30 = 0x6e25`) and relaxing the 19.2 MHz check. The
   probe reads `0x0f16` and stops; success is a registered `/dev/v4l-subdev`
   and no stream. Confidence: high for identity and register map (F4, F5),
   medium for the address (two candidates), medium for the PDN polarity
   (vendor table drives it high after reset, F7).
2. **H2. The 24 MHz MCLK reaches the module on `CMMCLK1`/`GPIO31` from
   SENINF1's timing generator, sourced from the `CAMTG` mux at 48 MHz
   (`UNIVPLL_D26`) divided by two (F10).** The vendor kernel sets only the
   enable bits of `SENINF1 + 0x600`; the divider field is programmed by
   userspace through the SENINF mmap (F13), so it is not recoverable from
   GPL source. Tests: (a) Gemian read of `/sys/kernel/debug/clk/clk_summary`
   (if mounted) with the camera app open, for `camtg_sel`'s parent and rate;
   (b) in the H1(b) boot, if the Hi-556 does not answer I2C without MCLK (many
   Hynix parts do not), probing with and without a programmed TG is itself the
   measurement; (c) fall-back: route `CLK_TOP_MUX_CAMTG` to `UNIVPLL_D26` and
   write a candidate divider into `SENINF1 + 0x600` from a bounded test
   driver, checking the pad with no instrument other than the sensor's
   response. Confidence: medium on the pad, low on the register field.
3. **H3. A first receiver test can use the sensor's own test pattern
   generator, needing no ISP and no DMA tuning.** Upstream hi556 exposes
   `HI556_REG_ISP 0x0a05` / `HI556_REG_TEST_PATTERN 0x0201`
   ([lines 66–68](https://github.com/gregkh/linux/blob/v7.1.3/drivers/media/i2c/hi556.c#L66-L68)).
   Once a SENINF/CAMSV path exists (H4), the first frame should be a colour
   bar from the sensor, which separates receiver faults from sensor exposure
   faults. Confidence: high that the register exists; depends on H4.
4. **H4. The MT8365 "ISP3.0" SENINF/CAMSV out-of-tree drivers are the right
   template for an MT6797 receiver and raw-to-memory path, with a different
   register map (F13, F14).** Offline test, no device: diff the MT8365
   series' SENINF register header against the vendor offsets that are
   recoverable (`TOP_CTRL +0x0`, `TOP_MUX_CTRL +0x8`, CSI0 analog block
   `+0x300`, CSI1 `+0x700`, TG at `+0x600`) and against the vendor CAMSV
   interrupt bit names in the pipeline contract; count matching fields. If
   the layouts match, the realistic mainline target is **SENINF → CAMSV →
   memory** (RAW10 frames), consumed by libcamera's simple pipeline with its
   software ISP, not the vendor's DIP/CAM A hardware ISP. Confidence: medium;
   MT6797 (2016) predates MT8365 (2019) and MediaTek renamed blocks between
   generations.
5. **H5. The lane routing and PHY timing the vendor HAL writes can be
   recovered by a bounded capture rather than by disassembly (F13).** Because
   the vendor exposes the SENINF and MIPI RX windows by mmap, a Gemian read of
   those physical ranges while the stock camera streams (a `/dev/mem`-class
   read of `0x1a040000`–`0x1a043fff` and `0x10217000`–`0x10218fff`, if the
   stock kernel permits it) yields the configured register image for the
   front camera; comparing it against the idle image gives the receiver
   programming without touching the proprietary binary. This is read-only at
   the register level but must be reviewed for side effects on
   read-sensitive registers before admission. Confidence: medium; value high
   because it is the only path to the missing sequence besides RE of the HAL.
6. **H6. The front module has no DW9714 actuator populated; the `SUBAF`
   wrapper is a static client that binds regardless (F15).** Tests: Gemian
   read of the kernel log for `SUBAF`/`DW9714AF` I2C errors during a camera
   session; or, in the H1(b) boot, a single read at `0x0c` on I2C3 (the
   DW9714 has no ID register, so only ACK/NACK is informative). Confidence:
   medium-high.
7. **H7. The MAIN socket on the development unit is empty, and the rear
   accessory, if ever attached, is one of OV5675 / S5K5E2YA / "SP5509 main"
   (F2, F3).** Test only if the owner has the accessory: a Gemian read of
   `/proc/AEON_CAMERA0` with it fitted. Upstream already has `ov5675.c`; the
   other two have no upstream driver (S5K5E2 has none in 7.1.3's
   `drivers/media/i2c/Kconfig`). Confidence: high that the socket is empty.
8. **H8. The 1.21 V DVDD the vendor applies is a vendor LDO-table artefact;
   1.2 V is the correct mainline request (F9).** No device test needed: the
   local MT6351 regulator patch's `vcamd` table decides whether 1.2 V is a
   selectable step; if not, request 1.21 V as the vendor does.
9. **H9. The front camera is on CSI1 (`0x10218000`), the MAIN socket on
   CSI0 (`0x10217000`).** Suggested by the SENINF1/MCLK2 pairing (F10) and
   the two analog windows (F11), but SENINF-to-CSI muxing is exactly the
   userspace-programmed part (F13). Resolved by H5 or H4; no separate test.

## Consequences for the roadmap (no changes applied here)

- The sensor side is feasible with small, upstreamable changes: `hi556`
  needs an OF match and binding, a 24 MHz PLL table and a power-down GPIO;
  the rails, pins and bus are now known (F8–F10) and the regulator provider
  exists locally. libcamera needs a one-entry sensor property.
- The receiver and ISP side is the irreducible blocker the roadmap row
  asked to make visible: the CSI-2/SENINF programming for this board exists
  only in the proprietary HAL (F13), mainline has no MediaTek receiver
  driver (F14), and the hardware ISP is out of scope. The realistic target
  is a raw SENINF→CAMSV capture with software ISP, after H4/H5 recover the
  register contract.
- Flash and autofocus need no work for the built-in camera (F15, F16); the
  rear accessory is absent on the development unit (F2).
- The cheapest first experiment is H1(a), a log read on Gemian, followed by
  H1(b), a mainline probe that reads one register. Neither streams.

## Validation

Documentation-only change: `./scripts/check-repository` and link checks apply;
no kernel build, DT check or device action was performed. Line numbers were
taken from the exact fetched files recorded in `source-inputs.json`.
