# Experiment: Gemini native display path reverse engineering

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-04-gemini-display-re` |
| Status | `completed` (offline source review; no build, boot or device access) |
| Subsystem | Loader display handoff, panel identity and init, DSI host, MIPI-TX PHY, panel reset and bias, display PWM backlight, MM clocks and power |
| Device variant | Project Gemini (Gemian `3.18.41+`, MT6797X, retained Planet Android 8 LK) |
| Date(s) | 2026-10-04 |
| Investigator(s) | Claude (owner-requested investigation) |
| Tracking issue | Not yet assigned |

## Question

What does the stock software actually do to bring up and drive the Gemini's
internal display, from the loader through the Gemian kernel, and what does
mainline Linux 7.1.3 still lack beyond the loader-retained `simplefb` console?
The roadmap's
[native display step](../../docs/ROADMAP.md#after-wi-fi-remaining-driver-gaps)
lists four blockers: a contradictory panel identity (NT36672 versus SSD2092),
an unidentified bias chip, an unproved reset path and an unresolved display-PWM
clock contract. This record re-reads the public vendor kernel, the public
loader source and the pinned mainline tree side by side, separates verified
facts from hypotheses, and ranks the hypotheses by how they should be tested on
the device. It changes no patch, profile, candidate or device state.

Earlier records own the live observations this builds on: the
[panel recovery](../2026-07-11-gemini-panel-recovery/README.md) (live LCM
selection, bias protocol, command-table comparison), the
[input and backlight recovery](../2026-07-12-input-backlight-recovery/README.md),
the [display architecture refresh](../2026-09-07-mt6797-display-upstream-architecture/README.md)
with its [PWM oscillator follow-up](../2026-09-07-mt6797-display-upstream-architecture/PWM_OSCILLATOR.md),
the [LK framebuffer console recovery](../2026-07-15-display-console-recovery/README.md),
the [MM root clock retention test](../2026-07-16-simplefb-mm-root-retention/README.md),
the [MMSYS routing recovery](../2026-07-12-mt6797-mmsys-routing-recovery/README.md)
and the [live resource map](../../docs/hardware/mt6797-live-resource-map.md).

## Inputs

Every vendor kernel citation is a public GPL file at Gemian commit
`8cfe6596a503612e3332d9c26e292a19525a7f07`, the same commit the charging record
used. Every loader citation is the public Planet Gemini Android 8 LK at commit
`f4988d74bb70a0a15d7f362f412afba7e7fcda46`, the commit the
[boot-graphics record](../2026-08-31-boot-graphics-recovery/README.md) pinned
for the retained LK. Every mainline citation is Linux `7.1.3` as pinned in
`kernel/manifest.json`. Exact URLs, sizes and SHA-256 values are in
[`source-inputs.json`](source-inputs.json). Line numbers refer to those exact
revisions. No vendor source, firmware or private capture is copied into this
repository; register addresses, bit positions, command bytes and timing values
are cited as facts.

Two caveats apply throughout. First, the public board DTS does not match the
live Gemian DTB in at least one node (the charging record's fact F2), and the
live kernel configuration reports a different panel rotation from the public
defconfig (fact F6 below), so board-level values in the public tree are cited
with that reservation. Second, the retained LK binary on the named device has
been matched to the pinned LK source only through its logo resource order and
security policy, not byte for byte; conclusions that depend on LK behaviour
(F1 to F4) inherit that limit.

## Part 1: verified facts

### Loader handoff and panel identity

- **F1. The loader builds both panel drivers and probes them in a fixed order
  with an identity read.** `CUSTOM_LK_LCM="aeon_nt36672_fhd_dsi_vdo_x600_xinli
  aeon_ssd2092_fhd_dsi_solomon"` at
  [`k97v1_64_bsp.mk` line 16](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/project/k97v1_64_bsp.mk#L16),
  listed in that order at
  [`mt65xx_lcm_list.c` lines 1515–1521](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/dev/lcm/mt65xx_lcm_list.c#L1515-L1521).
  With more than one driver, LK's `disp_lcm_probe()` initialises the DSI path
  with each driver's parameters, calls its `init_power` and then its
  `compare_id`; the first driver returning non-zero is selected, and if none
  does, the first list entry is used
  ([`disp_lcm.c` lines 886–911](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/platform/mt6797/disp_lcm.c#L886-L911)).
- **F2. The two loader identity checks are asymmetric.** The NT36672 driver's
  `compare_id` sends a four-byte generic packet `B9 FF 83 99`, waits, reads one
  byte each from `0xDB` and `0xF4`, and returns 1 only when the pair equals
  `0x8070`
  ([`aeon_nt36672_…xinli.c` lines 847–878](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/dev/lcm/aeon_nt36672_fhd_dsi_vdo_x600_xinli/aeon_nt36672_fhd_dsi_vdo_x600_xinli.c#L847-L878)).
  The SSD2092 driver's `compare_id` powers the panel, sends sleep-out, reads
  four bytes from `0xA1`, compares with `0x01572098`, and **returns 1 on both
  branches**
  ([`aeon_ssd2092_…solomon.c` lines 669–695](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/dev/lcm/aeon_ssd2092_fhd_dsi_solomon/aeon_ssd2092_fhd_dsi_solomon.c#L669-L695)).
  Consequence: the loader can only report the NT36672 driver when the
  `0xDB`/`0xF4` read actually returned `0x80`/`0x70`; any unit on which that
  read fails is reported as SSD2092 whatever its silicon.
- **F3. The kernel takes the panel name from the loader and never
  re-identifies or re-initialises the panel.** LK sizes the `videolfb` tag with
  `strlen(mt_disp_get_lcm_id())` and stores it as `/chosen` property
  `atag,videolfb`
  ([`mt_boot.c` lines 1983–1985 and 1432–1433](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/app/mt_boot/mt_boot.c#L1983-L1985));
  the name is the selected driver's name
  ([`mt_disp_drv.c` lines 477–479](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/platform/mt6797/mt_disp_drv.c#L477-L479)).
  The kernel parses `fb_base`, `islcmfound`, `fps`, `vram` and `lcmname` from
  that tag and sets `is_lcm_inited = 1`
  ([`mtkfb.c` lines 1820–1826 and 1901–1920](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/video/common/mtkfb.c#L1901-L1920)),
  passes the name to `primary_display_init()`
  ([line 2343](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/video/common/mtkfb.c#L2343)),
  which selects the compiled-in driver by `strcmp` against the list
  ([`disp_lcm.c` lines 1025–1040](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/video/mt6797/videox/disp_lcm.c#L1025-L1040))
  and, because the loader initialised the panel, skips `init_power` and `init`
  ([`primary_display.c` lines 3311–3313](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/video/mt6797/videox/primary_display.c#L3311-L3313),
  [`disp_lcm.c` lines 1118–1137](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/video/mt6797/videox/disp_lcm.c#L1118-L1137)).
  The kernel-side `compare_id` is compiled to `return 1` outside LK
  ([`aeon_nt36672_…xinli.c` lines 876–912](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/lcm/aeon_nt36672_fhd_dsi_vdo_x600_xinli/aeon_nt36672_fhd_dsi_vdo_x600_xinli.c#L876-L912)),
  which is why the panel record could not use it as identity evidence.
- **F4. Taken together, F1 to F3 make the named device's live driver name an
  indirect identity read.** The live capture shows the kernel bound to
  `aeon_nt36672_fhd_dsi_vdo_x600_xinli`
  ([panel `runtime-summary.txt`](../2026-07-11-gemini-panel-recovery/results/runtime-summary.txt)).
  Under the pinned LK logic that name can only have come from a successful
  `0x8070` read on the named unit; had the read failed, the always-true SSD2092
  check would have selected the Solomon driver, and the kernel would report
  that name instead. The bsg100 unit, which reports SSD2092 with direct SEEPROM
  and DSI readbacks
  ([bsg100 comparison](../2026-07-13-bsg100-gemini-linux-comparison/README.md)),
  is therefore not a contradiction but the other branch of the same loader
  logic: two panel variants exist, and each unit's loader-reported name is its
  own. This resolves the roadmap's identity gate to "NT36672 family on the
  named device", with the LK-binary caveat stated under Inputs; a direct
  `0xDB`/`0xF4` read under mainline remains the confirming test (H1).
- **F5. The loader also owns the framebuffer and its geometry.** LK reserves the
  framebuffer after loading the DTB and writes `atag,videolfb-fb_base_h/l` and
  `atag,videolfb-vramSize` into `/chosen`
  ([`mt_disp_drv.c` lines 445–467](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/platform/mt6797/mt_disp_drv.c#L445-L467));
  the live Gemian values are a 1080x2160, 32 bpp, 4352-byte-stride buffer at
  `0x7dfb0000` of `0x1f90000` bytes, format labelled ARGB8888
  ([console recovery](../2026-07-15-display-console-recovery/README.md)).
  The vendor framebuffer pads width to 1088 pixels (`MTK_FB_ALIGNMENT 32`,
  [`disp_drv_platform.h` line 40](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/video/mt6797/videox/disp_drv_platform.h#L40)),
  matching the live `virtual_size=1088,4320` and stride 4352.
- **F6. Physical rotation is a build constant and the public kernel defconfig
  disagrees with the live one.** LK sets `MTK_LCM_PHYSICAL_ROTATION = 270`
  ([`k97v1_64_bsp.mk` line 15](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/project/k97v1_64_bsp.mk#L15),
  consumed by [`mt_logo.c` lines 77–82](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/platform/mt6797/mt_logo.c#L77-L82)),
  the public kernel defconfig sets `"270"` and `CUSTOM_LCM_X="176"`
  ([`aeon6797_6m_n_defconfig` lines 216–217](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/configs/aeon6797_6m_n_defconfig#L216-L217)),
  while the live kernel reports `"90"`
  ([panel `runtime-summary.txt`](../2026-07-11-gemini-panel-recovery/results/runtime-summary.txt)).
  The panel scans out portrait 1080x2160 in all cases; the rotation is applied
  by the compositor (vendor) or by `fbcon=rotate:3` (local handoff profile,
  [`gemini-fbcon-rotation.fragment`](../../configs/gemini-fbcon-rotation.fragment)).
  A mainline DRM panel should therefore declare the portrait mode and a
  `rotation` property, not a rotated mode.

### Panel electrical contract (NT36672 driver, both trees agree)

- **F7. Power-on order.** Reset low; positive bias enable (GPIO60) then negative
  bias enable (GPIO251) through the `aeon_lcd_bias_enp1`/`enn1` pinctrl states;
  20 ms; two I2C writes to the bias chip; reset high 10 ms, low 10 ms, high
  20 ms
  ([`aeon_nt36672_…xinli.c` lines 795–840](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/lcm/aeon_nt36672_fhd_dsi_vdo_x600_xinli/aeon_nt36672_fhd_dsi_vdo_x600_xinli.c#L795-L840);
  pin states at
  [`aeon_gpio.dtsi` lines 143–171](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/aeon_gpio.dtsi#L143-L171)).
  The LK copy differs only in delays: 50 ms after reset low and 20 ms between
  the two bias writes
  ([LK lines 793–845](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/dev/lcm/aeon_nt36672_fhd_dsi_vdo_x600_xinli/aeon_nt36672_fhd_dsi_vdo_x600_xinli.c#L793-L845)).
  The SSD2092 kernel driver uses the identical power-on sequence
  ([`aeon_ssd2092_…solomon.c` lines 795–810](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/lcm/aeon_ssd2092_fhd_dsi_solomon/aeon_ssd2092_fhd_dsi_solomon.c#L795-L810)),
  so the board wiring (reset, two bias enables, one I2C bias chip) is common to
  both variants.
- **F8. Power-off order.** DCS `0x28`, 50 ms, `0x10`, 120 ms, then 10 ms, then
  negative bias off followed by positive bias off; reset is left high
  ([lines 234–240 and 847–857](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/lcm/aeon_nt36672_fhd_dsi_vdo_x600_xinli/aeon_nt36672_fhd_dsi_vdo_x600_xinli.c#L847-L857)).
  Resume is `lcm_poweron()` then `lcm_init()` (lines 859–863).
- **F9. The bias chip is driven as two selector registers only.** `lp3101.c`
  matches `mediatek,I2C_LCD_BIAS` at address `0x3E`, stores the client, and
  `lp3101_poweron()` writes `0x00 = 0x0f` and `0x01 = 0x0f`
  ([`lp3101.c` lines 18–27 and 105–127](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/gpio/lp3101.c#L105-L127)).
  No register is ever read. Mainline's `tps65132-regulator` uses the same
  address-free layout, VPOS at `0x00`, VNEG at `0x01`, 4.0 V minimum in 100 mV
  steps, and one enable GPIO per output
  ([`tps65132-regulator.c` lines 29–36 and 185–186](https://github.com/gregkh/linux/blob/v7.1.3/drivers/regulator/tps65132-regulator.c#L29-L36),
  [`ti,tps65132.yaml`](https://github.com/gregkh/linux/blob/v7.1.3/Documentation/devicetree/bindings/regulator/ti,tps65132.yaml)),
  so `0x0f` decodes to ±5.5 V **if** the part is TPS65132-compatible. The
  panel record's conclusion stands: protocol match, silicon identity unproven,
  no `ti,tps65132` compatible until identified (H5).
- **F10. The panel's logic rail is not software-switched.** The driver's
  `suspend_power`/`resume_power` bodies are fully commented out
  ([lines 769–793](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/lcm/aeon_nt36672_fhd_dsi_vdo_x600_xinli/aeon_nt36672_fhd_dsi_vdo_x600_xinli.c#L769-L793)),
  no `lcm`/`lcd` regulator exists in the public SoC or board DTS, and the only
  rail named for the display block is `vmipi` for the MIPI PHY
  ([`mt6797.dtsi` lines 676–677 and 766](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L676-L677)).
  The PMIC record lists VIO18 as always-on 1.8 V
  ([PMIC recovery](../2026-07-11-mt6351-pmic-recovery/README.md)). Which rail
  feeds the panel's IOVCC is not recorded anywhere in software (H6).
- **F11. The reset is an MMSYS register bit, not a GPIO write, in both LK and
  the kernel.** `lcm_set_reset_pin()` writes `MMSYS_CONFIG_BASE + 0x150`
  ([LK `ddp_dsi.c` lines 2431–2434](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/platform/mt6797/ddp_dsi.c#L2431-L2434),
  [kernel `ddp_dsi.c` lines 2705–2716](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/video/mt6797/dispsys/ddp_dsi.c#L2705-L2716),
  `DISP_REG_CONFIG_MMSYS_LCM_RST_B` bit 0 at
  [`ddp_reg.h` lines 1485 and 1622](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/video/mt6797/dispsys/ddp_reg.h#L1485)).
  The kernel's pinctrl-state alternative is compiled out by `#if 1`. The pad is
  GPIO180 whose function 1 is `LCM_RST`
  ([mainline `mt6797-pinfunc.h` lines 940–943](https://github.com/gregkh/linux/blob/v7.1.3/include/dt-bindings/pinctrl/mt6797-pinfunc.h#L940-L943));
  the board DTS muxes it to that function in both reset states
  ([`aeon6797_6m_n.dts` lines 1070–1084](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/aeon6797_6m_n.dts#L1070-L1084)).
  Hence the register drives the pad through the `LCM_RST` alternate function;
  muxing GPIO180 as a GPIO and using `reset-gpios` is an electrical equivalent
  only if the pad is the sole path to the panel's reset pin (H4).
- **F12. DSI tearing-effect pin.** GPIO179 is muxed to `DSI_TE0` in both
  `mode_te` states
  ([`aeon6797_6m_n.dts` lines 1058–1068](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/aeon6797_6m_n.dts#L1058-L1068)).
  The selected driver runs burst video mode (F13), which does not use TE, so a
  mainline description may omit it.

### Panel timing, DSI host and MIPI-TX PHY

- **F13. The active panel parameters.** 1080x2160, `BURST_VDO_MODE`, four
  lanes, packed RGB888, `packet_size = 256`, vertical sync/back/front
  3/15/10 lines, horizontal sync/back/front 10/42/42 pixels, `ssc_disable = 1`,
  `PLL_CLOCK = 440` (423 for the unused command-mode build), low-power clock
  between lines, ESD check DCS `0x0A` expecting `0x9C`
  ([lines 656–717](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/lcm/aeon_nt36672_fhd_dsi_vdo_x600_xinli/aeon_nt36672_fhd_dsi_vdo_x600_xinli.c#L656-L717)).
  The LK copy carries the same values (LK lines 664–699). For comparison the
  SSD2092 driver uses `SYNC_PULSE_VDO_MODE`, V 1/43/76, H 4/20/26,
  `PLL_CLOCK = 502` and no ESD check
  ([`aeon_ssd2092_…solomon.c` lines 676–716](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/lcm/aeon_ssd2092_fhd_dsi_solomon/aeon_ssd2092_fhd_dsi_solomon.c#L676-L716));
  neither its timing nor its command table is interchangeable with the
  NT36672's.
- **F14. The init table.** `init_setting` (lines 243–455) selects Novatek pages
  `0xFF = 20, 24, 25, 26, 27, 20, 21, 10` with `0xFB = 01` reloads, programs
  panel registers on those pages, then on page `0x10` writes brightness
  `0x51 = 0xFF`, control `0x53 = 0x24`, `0x55 = 0x00`, address mode
  `0x36 = 0x03`, sleep-out `0x11`, 120 ms, display-on `0x29`, 10 ms. A second
  table under `#else` (lines 457–614) is not compiled. The panel record's
  mechanical comparison (165 register writes, four exact matches with the
  upstream NT36672E table) and its packet-type audit (DCS below `0xB0`, generic
  at and above) remain the authoritative transport facts.
- **F15. `PLL_CLOCK` is half the lane bit rate, and the live "435 MHz" is an
  integer readback of the requested 440.** `DSI_PHY_clk_setting()` uses
  `data_Rate = PLL_CLOCK * 2` (880 Mbit/s per lane), selects `pcw_ratio 1,
  S2Qdiv 2, posdiv 0` for rates of 500 Mbit/s and above, and programs
  `pcw = data_Rate * pcw_ratio / 13` with three fractional bytes
  ([`ddp_dsi.c` lines 1368–1375, 1462–1492 and 1510–1521](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/video/mt6797/dispsys/ddp_dsi.c#L1462-L1492)).
  The readback helper returns `26 * floor(pcw) / (prediv * posdiv * S2Qdiv)`
  ([lines 1198–1213](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/video/mt6797/dispsys/ddp_dsi.c#L1198-L1213)),
  which for 880 Mbit/s is `26 * 67 / 4 = 435`. The resource map's retained
  435 MHz and the panel record's 4.4 % discrepancy are therefore the same
  number as the driver's 440 MHz request, truncated; the real lane rate is
  880 Mbit/s. The LK PHY code is the same algorithm
  ([LK `ddp_dsi.c` lines 1150–1198](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/platform/mt6797/ddp_dsi.c#L1150-L1198)).
- **F16. The PHY power-up order.** Lane resistance-trim fields are preserved,
  then `RG_DSI_BG_CORE_EN`, 1 ms, `RG_DSI_LDOCORE_EN` and
  `RG_DSI_CKG_LDOOUT_EN`, `DA_DSI_MPPLL_SDM_PWR_ON = 1`, `SDM_ISO_EN = 0`,
  1 ms, divider and PCW writes, optional SSC (disabled by F13),
  `SDM_FRA_EN = 1`, per-lane `LDOOUT_EN`, then PLL enable
  ([`ddp_dsi.c` lines 1412–1560](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/video/mt6797/dispsys/ddp_dsi.c#L1412-L1560)).
  The local [patch 0039](../../patches/v7.1.3/0039-phy-mediatek-add-MT6797-MIPI-DSI-TX-support.patch)
  reproduces this order and the MT6797 field layout (pre-divider bits 3:2,
  post-divider 6:4, S2Q 13:12, PCW latch at `0x60`); mainline's MT8173
  operations write different divider fields
  ([`phy-mtk-mipi-dsi-mt8173.c` lines 65–70 and 126–196](https://github.com/gregkh/linux/blob/v7.1.3/drivers/phy/mediatek/phy-mtk-mipi-dsi-mt8173.c#L126-L196)),
  so a native MT6797 PHY variant is required, not a compatible alias.
- **F17. D-PHY timing is derived from the lane rate in both stacks, with
  different formulas.** The vendor computes `ui = 1000 / data_Rate + 1` ns and
  `cycle_time = 8000 / data_Rate + 1` ns and derives HS_PRPR, HS_ZERO, HS_TRAIL,
  LPX, TA_*, CLK_* from them
  ([`ddp_dsi.c` lines 1662–1775](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/video/mt6797/dispsys/ddp_dsi.c#L1662-L1775));
  mainline `mtk_dsi_phy_timconfig()` uses its own rate-based expressions
  ([`mtk_dsi.c` lines 246–266](https://github.com/gregkh/linux/blob/v7.1.3/drivers/gpu/drm/mediatek/mtk_dsi.c#L246-L266)).
  Both target the D-PHY specification; neither carries panel-specific
  overrides for this LCM (all `dsi_params->HS_*` are zero), so mainline's
  defaults are the expected starting point and the difference is a check item,
  not a known blocker.
- **F18. Video-mode porch bytes.** The vendor programs
  `HSA_WC = HSA*3 - 4`, `HBP_WC = (HBP + HSA)*3 - 10`, `HFP_WC = HFP*3 - 12`,
  each rounded up to 4, with `BLLP_WC = 0`
  ([`ddp_dsi.c` lines 962–1030](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/video/mt6797/dispsys/ddp_dsi.c#L962-L1030)),
  giving 28, 148 and 116 bytes for F13. Mainline derives equivalent word
  counts from the DRM mode and lane count
  ([`mtk_dsi.c` lines 440–560](https://github.com/gregkh/linux/blob/v7.1.3/drivers/gpu/drm/mediatek/mtk_dsi.c#L440-L560)).
  Because the vendor's frame rate is set by lane rate plus these byte counts,
  not by a pixel clock, the mode clock a mainline panel declares is a derived
  quantity (H3). The live diagnostic `lcm_fps = 5405` is consistent with
  880 Mbit/s and these porches plus packet overhead.
- **F19. The DSI host is MT8173-generation with MT6797 clocks.** The host at
  `0x1401c000` uses SPI 229 and two MMSYS gates, `MM_DSI0_MM_CLOCK` and
  `MM_DSI0_INTERFACE_CLOCK`
  ([`mt6797.dtsi` lines 3115, 3143 and 3176–3177](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L3176-L3177));
  the MIPI-TX aperture is `0x10215000`
  ([line 2185](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L2185)).
  Mainline's `clk-mt6797-mm.c` provides the first gate (`CLK_MM_DSI0_MM_CLOCK`,
  bit 0 of the second bank) but **no `DSI0_INTERFACE_CLOCK` gate**: the
  binding header reserves ID 41 for it
  ([`mt6797-clk.h` line 255](https://github.com/gregkh/linux/blob/v7.1.3/include/dt-bindings/clock/mt6797-clk.h#L255))
  while the driver's gate table has no entry
  ([`clk-mt6797-mm.c` lines 65–76](https://github.com/gregkh/linux/blob/v7.1.3/drivers/clk/mediatek/clk-mt6797-mm.c#L65-L76)).
  The local [patch 0040](../../patches/v7.1.3/0040-arm64-dts-mediatek-mt6797-add-DSI0-and-MIPI-TX.patch)
  names that ID as the DSI `digital` clock, so as written it would resolve to
  a provider ID with no clock behind it. This is a concrete mainline gap
  independent of the panel (H7).

### Display pipeline, clocks and power

- **F20. The active single-DSI path and its owners are already recorded.**
  OVL0 → OVL0-2L → OVL1-2L → COLOR0 → CCORR → AAL → GAMMA → OD → DITHER →
  RDMA0 → bypassed UFOE → DSI0, with MMSYS routing values, 64 reset lines and
  the separate `LCM_RST_B` at `0x150`
  ([live resource map](../../docs/hardware/mt6797-live-resource-map.md),
  [MMSYS routing recovery](../2026-07-12-mt6797-mmsys-routing-recovery/README.md)).
  The vendor `dispsys` node's clock list names every MM gate plus
  `INFRA_DISP_PWM`, the MM power domain as `DISP_MTCMOS_CLK`, `TOP_MUX_PWM`,
  `UNIVPLL2_D4` and the five `ULPOSC_D*` dividers
  ([`mt6797.dtsi` lines 3156–3240](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L3156-L3240)).
  The live `mm_sel` rate is 325 MHz
  ([clock capture](../2026-07-12-mt6797-clock-power-reset-recovery/results/runtime-summary.txt)).
- **F21. Mainline 7.1.3 MT6797 coverage for this pipeline.** Present: MMSYS
  clock provider and syscon (`mediatek,mt6797-mmsys`, data limited to the clock
  driver, [`mtk-mmsys.c` lines 52–55 and 463](https://github.com/gregkh/linux/blob/v7.1.3/drivers/soc/mediatek/mtk-mmsys.c#L52-L55)),
  `scpsys` with `MT6797_POWER_DOMAIN_MM`
  ([`mtk-scpsys.c` lines 755–818](https://github.com/gregkh/linux/blob/v7.1.3/drivers/pmdomain/mediatek/mtk-scpsys.c#L755-L818),
  [`mt6797-power.h` line 13](https://github.com/gregkh/linux/blob/v7.1.3/include/dt-bindings/power/mt6797-power.h#L13)),
  `pwm_sel`/`infra_disp_pwm`/ULPOSC clocks (F24). Absent: any MT6797 entry in
  the DRM driver, display mutex, DSI host, MIPI-TX PHY, display PWM, IOMMU or
  SMI drivers (zero `mt6797` matches in `mtk_drm_drv.c`, `mtk-mutex.c`,
  `mtk_dsi.c`, `phy-mtk-mipi-dsi.c`, `pwm-mtk-disp.c`, `mtk_iommu.c` and
  `mtk-smi.c`; compatible lists at
  [`mtk_drm_drv.c` lines 335–361](https://github.com/gregkh/linux/blob/v7.1.3/drivers/gpu/drm/mediatek/mtk_drm_drv.c#L335-L361),
  [`mtk_dsi.c` lines 1307–1311](https://github.com/gregkh/linux/blob/v7.1.3/drivers/gpu/drm/mediatek/mtk_dsi.c#L1307-L1311),
  [`phy-mtk-mipi-dsi.c` lines 183–185](https://github.com/gregkh/linux/blob/v7.1.3/drivers/phy/mediatek/phy-mtk-mipi-dsi.c#L183-L185),
  [`mediatek,pwm-disp.yaml` lines 18–36](https://github.com/gregkh/linux/blob/v7.1.3/Documentation/devicetree/bindings/pwm/mediatek,pwm-disp.yaml#L18-L36)).
  The local patches 0028–0044 supply this data; the
  [architecture refresh](../2026-09-07-mt6797-display-upstream-architecture/README.md)
  dispositions (retain/adapt/split/hold/superseded) are unchanged by this
  record except where F19 and F25 add new evidence.
- **F22. The mainline `simple-framebuffer` binding can hold the loader state
  that the vendor kernel holds through `mtkfb`.** The binding accepts
  `clocks`, `power-domains`, `display` and `panel` references so the console
  keeps its resources until a native driver takes over
  ([`simple-framebuffer.yaml` lines 71–127](https://github.com/gregkh/linux/blob/v7.1.3/Documentation/devicetree/bindings/display/simple-framebuffer.yaml#L71-L127);
  driver clock, regulator and genpd handling in
  [`simplefb.c` lines 79–95 and 248–290](https://github.com/gregkh/linux/blob/v7.1.3/drivers/video/fbdev/simplefb.c#L248-L290)).
  The current patch series carries **no** `simple-framebuffer` node and no
  `/chosen` framebuffer; the working loader-retained console came from
  experiment-level DTB derivatives (the removed prototype 0077 and candidates
  G/H), and the handoff profile selects `FB_SIMPLE` with `clk_ignore_unused`
  ([`gemini-handoff.fragment` lines 154–156](../../configs/gemini-handoff.fragment),
  [MM root retention](../2026-07-16-simplefb-mm-root-retention/README.md)).
  Candidate G (PWM clock only) lost the picture after one to two seconds;
  candidate H added `CLK_TOP_MUX_MM`. So the minimum retained set is the MM
  root plus the display PWM clock, and the MM power domain.

### Backlight (display PWM)

- **F23. The LCD backlight is the display PWM block in "BLS PWM" mode with
  1024 levels.** Board LED node `lcd-backlight` has `led_mode = <5>` and
  `pwm_config = <0 0 0 0 0>`
  ([`aeon6797_6m_n.dts` lines 192–196](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/aeon6797_6m_n.dts#L192-L196));
  mode 5 is `MT65XX_LED_MODE_CUST_BLS_PWM`
  ([`leds_sw.h` lines 33–38](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/leds/mt6797/leds_sw.h#L33-L38)).
  The LED class 0–255 level is mapped to `level * 1023 / 255`
  (`MT_LED_INTERNAL_LEVEL_BIT_CNT 10`, header line 52;
  [`leds.c` lines 1046–1072](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/leds/mt6797/leds.c#L1046-L1072))
  and written as the PWM high width: `CON_1[28:16] = level`, period
  `CON_1[9:0] = 1023`, clock divider `CON_0[25:16] = 0`, enable `EN[0]`
  ([`ddp_pwm.c` lines 195–241, 311–324 and 459–505](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/video/common/aal20/ddp_pwm.c#L195-L241);
  offsets `EN 0x00, COMMIT 0x08, CON_0 0x10, CON_1 0x14` at
  [`ddp_reg.h` lines 1309–1312](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/video/mt6797/dispsys/ddp_reg.h#L1309-L1312)).
  The block is at `0x1100f000`
  ([`mt6797.dtsi` line 3118](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L3118))
  and the pad is GPIO178 function `DISP_PWM`
  ([`mt6797-pinfunc.h` line 931](https://github.com/gregkh/linux/blob/v7.1.3/include/dt-bindings/pinctrl/mt6797-pinfunc.h#L931)).
  LK uses the same `disp_bls_set_backlight` hook
  ([LK `cust_leds.c` line 32](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/target/k97v1_64_bsp/cust_leds.c#L32)),
  so the loader leaves the PWM running at full width when the kernel starts.
- **F24. The register layout equals mainline's MT8173 data; the clock contract
  is a single infra gate plus the MM domain.** Mainline `mt8173_pwm_data` is
  `enable 0x0, con0 0x10, con1 0x14, has_commit, commit 0x8`
  ([`pwm-mtk-disp.c` lines 277–285](https://github.com/gregkh/linux/blob/v7.1.3/drivers/pwm/pwm-mtk-disp.c#L277-L285)),
  identical to F23's offsets. The vendor display clock manager enables exactly
  one clock for the PWM module, ID `DISP_PWM`, which the SoC DTS maps to
  `INFRA_DISP_PWM`, and selects its parent through `MUX_PWM`
  ([`ddp_clkmgr.h` lines 50–64](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/video/mt6797/dispsys/ddp_clkmgr.h#L50-L64),
  [`ddp_pwm_mux.c` lines 137–156](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/video/mt6797/dispsys/ddp_pwm_mux.c#L137-L156),
  [`PWM_OSCILLATOR.md`](../2026-09-07-mt6797-display-upstream-architecture/PWM_OSCILLATOR.md)
  for the compiled `ddp_pwm_power_on()`). Mainline models the same tree:
  `infra_disp_pwm` gated from `pwm_sel` (ICG1 bit 17), `pwm_sel` a gated mux
  at `0x50` over `clk26m`, `univpll2_d4` and the ULPOSC dividers
  ([`clk-mt6797.c` lines 117–124, 333 and 492](https://github.com/gregkh/linux/blob/v7.1.3/drivers/clk/mediatek/clk-mt6797.c#L117-L124)).
  There is no MM-side gate for the PWM on MT6797; MT8173's `mm` clock
  (`CLK_MM_DISP_PWM0MM`) has no MT6797 counterpart in either tree. The
  binding nevertheless requires `main` and `mm`
  ([`mediatek,pwm-disp.yaml` lines 48–64](https://github.com/gregkh/linux/blob/v7.1.3/Documentation/devicetree/bindings/pwm/mediatek,pwm-disp.yaml#L48-L64)).
  This is the source-level evidence the architecture refresh asked for before
  accepting [patch 0044](../../patches/v7.1.3/0044-pwm-mediatek-add-MT6797-display-PWM-support.patch)'s
  optional-`mm` change; what it does not settle is the ULPOSC lifetime (F25).
- **F25. The PWM source is the uncalibrated ULPOSC, selected and powered
  outside the clock framework.** Board selector 0 maps to `ULPOSC_D8`
  (vendor comment "29M")
  ([`ddp_pwm_mux.c` lines 56–82](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/video/mt6797/dispsys/ddp_pwm_mux.c#L56-L82)),
  and the power-on path performs direct enable/reset/gate writes at sleep
  controller offset `0x458`
  ([lines 161–300](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/video/mt6797/dispsys/ddp_pwm_mux.c#L161-L300);
  compiled-path confirmation in the PWM oscillator follow-up). The vendor's own
  divider comments (D2 117 M, D3 78 M, D4 58 M, D8 29 M, D10 23 M) imply a
  roughly 234 MHz oscillator, whereas mainline's factor table defines
  `ulposc_ck = org/3`, `d3 = ck/4`, `d4 = ck/8`, `d8 = ck/10`, `d10 = org`
  ([`clk-mt6797.c` lines 59–65](https://github.com/gregkh/linux/blob/v7.1.3/drivers/clk/mediatek/clk-mt6797.c#L59-L65)),
  which does not follow the vendor naming. A mainline `pwm-mtk-disp` instance
  would compute its divider from `clk_get_rate("main")`, so with ULPOSC
  parentage the absolute PWM frequency is unknown even though the duty ratio is
  correct. The implied vendor frequency is about 28 kHz (29 MHz / 1024).

### Mainline and this repository

- **F26. The upstream NT36672E driver is a descriptor framework with fixed
  supplies.** It requires `vddi`, `avdd`, `avee`, `reset-gpios` and a port,
  takes an optional standard `backlight`, and sequences supplies → reset
  → page-table init → exit-sleep 120 ms → display-on 100 ms
  ([`panel-novatek-nt36672e.c` lines 16–20, 360–470 and 483–560](https://github.com/gregkh/linux/blob/v7.1.3/drivers/gpu/drm/panel/panel-novatek-nt36672e.c#L360-L470),
  [`novatek,nt36672e.yaml`](https://github.com/gregkh/linux/blob/v7.1.3/Documentation/devicetree/bindings/display/panel/novatek,nt36672e.yaml)).
  The local [patch 0043](../../patches/v7.1.3/0043-drm-panel-novatek-nt36672e-add-gemini-descriptor.patch)
  adds `planet,gemini-pda-nt36672` with `outp`/`outn` supplies, the vendor
  delays (20/10/10/20 ms power and reset, 50/120 ms off, 120/10 ms on), a
  138.839 MHz 1174x2188 mode and the 165-write table. Given F15, its mode
  clock implies 833 Mbit/s per lane, 5.3 % below the vendor's 880 Mbit/s
  (H3). Its `vddi`-less supply set matches F10.
- **F27. No MT6797 or Gemini display consumer is enabled in the current
  tree.** The board DT ([patch 0020](../../patches/v7.1.3/0020-arm64-dts-mediatek-add-Planet-Gemini-PDA.patch))
  has no panel, bias, backlight or framebuffer node; I2C1 (bias chip at `0x3e`,
  [mainline `mt6797.dtsi` line 300](https://github.com/gregkh/linux/blob/v7.1.3/arch/arm64/boot/dts/mediatek/mt6797.dtsi#L300))
  is disabled; every SoC display node from patches 0030, 0040, 0042 and 0044 is
  `status = "disabled"`. The architecture refresh's statement that mainline
  display runtime is untested remains true.

## Part 2: hypotheses, ranked by value per device minute

"Gemian read" means one bounded, read-only inspection of the running stock
kernel over the known-good LAN SSH path under the existing standing
authorization; "mainline boot" means a new reviewed experiment with its own
candidate, hypothesis and stop conditions. None is admitted by this record.

1. **H1. The named device's panel answers `0xDB = 0x80`, `0xF4 = 0x70`, confirming
   the NT36672 family directly (F2, F4).** Cheapest decisive test: a Gemian
   read of the loader log for the LK line `NT36672 id = 0x80, id1=0x70` and
   `we will use lcm: aeon_nt36672…` (`/proc/last_kmsg`, `dmesg` early lines, or
   the retained `expdb`/`pstore` LK log, whichever the stock image exposes);
   this costs nothing and needs no DSI transaction. If no LK log survives, the
   confirming mainline test is one DCS read of `0xDB`/`0xF4` from the DSI host
   during the first bring-up boot, before any init table is sent. Refutation
   (`0xA1` answering `0x01572098`, or `0xDB`/`0xF4` not `0x8070`) would mean
   the retained LK differs from the pinned source. Confidence: high.
2. **H2. The loader-initialised panel can be adopted by mainline without a
   modeset: a `simple-framebuffer` node with `power-domains = MM`, `clocks =
   mm_sel, infra_disp_pwm` and a `display`/`panel` reference keeps the picture
   until DRM binds (F5, F22).** Test: a mainline boot of the current handoff
   profile with that node generated into the DTB (as candidate H did) and
   `clk_ignore_unused` removed; pass is a stable console past `/init`, fail is
   the candidate-G blackout. This is the first step that removes a global
   flag and it exercises the MM domain under `scpsys`. Confidence: medium-high
   (candidate H already covered the clocks; the power domain is the new
   variable).
3. **H3. The mainline mode clock should be chosen so the DSI host requests the
   vendor lane rate, 880 Mbit/s, i.e. `clock = 146667` kHz for the 1174x2188
   mode (57.1 Hz nominal), rather than 138.839 MHz (F13, F15, F18).** Burst
   video mode decouples lane rate from refresh; the panel was qualified with
   the vendor rate, and the PHY timing table (F17) scales with it. Test: in
   the first panel bring-up boot, read the programmed PCW back through the
   PHY provider and measure refresh from vblank timestamps; accept either rate
   that gives a stable picture, prefer the one matching 880 Mbit/s. Confidence:
   medium.
4. **H4. GPIO180 muxed as a plain GPIO and driven by `reset-gpios` is
   electrically equivalent to the MMSYS `LCM_RST_B` write (F11).** Test, in
   order: (a) Gemian read of the pinctrl debug state for pin 180 during a
   display off/on cycle (direction and output value should follow the reset
   sequence if the pad is the only path); (b) mainline boot with the panel's
   `reset-gpios = <&pio 180 GPIO_ACTIVE_LOW>`, observing whether the panel
   accepts the init table. If (b) fails while H1 passed, the fallback is a
   small MMSYS-owned reset consumer for offset `0x150` outside the two reset
   banks. Confidence: medium.
5. **H5. The bias chip is a TPS65132-compatible dual charge pump at ±5.5 V
   (F9).** Test: a Gemian read-only I2C probe of bus 1 address `0x3e` for
   registers `0x00`, `0x01`, `0x03` and `0xFF` (TPS65132 returns the selectors
   and control; the LowPowerSemi part the vendor names has no I2C at all).
   Reads of these four registers are safe on both candidate parts. If the
   readback is `0x0f`, `0x0f`, use `ti,tps65132` with `outp`/`outn` at 5.5 V
   and `enable-gpios` 60/251; otherwise identify the marking before any
   regulator node. Confidence: medium-high on protocol, low on marking.
6. **H6. The panel's IOVCC is the always-on VIO18 rail and needs no
   `vddi-supply` consumer (F10).** Test: Gemian read of the MT6351 regulator
   enable states across one display off/on cycle; VIO18 should not toggle and
   no other LDO should toggle in step with the panel. If an LDO does toggle,
   it becomes the `vddi` supply. Confidence: medium.
7. **H7. Mainline needs a `CLK_MM_DSI0_INTERFACE_CLOCK` gate added to
   `clk-mt6797-mm.c` (second bank, the bit the vendor header uses) before the
   DSI node of patch 0040 can probe (F19).** Test: offline, read the vendor
   `ddp_clkmgr.c` and the live `clk_summary` capture for the gate's bank and
   bit, then build; on device, `clk_summary` should list the gate and the DSI
   host should not defer on `digital`. Confidence: high that the gate is
   missing, medium on the exact bit until read from the vendor clock table.
8. **H8. Display PWM can be described as an MT6797 variant with a single
   `main` clock (`infra_disp_pwm`) plus `power-domains = MM`, and brightness
   will be correct in ratio even if the ULPOSC rate is wrong (F24, F25).**
   Test: a mainline boot with patch 0044's node enabled and a standard
   `pwm-backlight` with 1024 `brightness-levels`, under the simplefb console
   of H2; read `CON_0`/`CON_1` back and compare duty to the requested level,
   and measure the PWM frequency on GPIO178 if an instrument is available. If
   the screen flickers or the computed divider overflows, the ULPOSC rate in
   CCF is wrong and a fixed-rate description is needed. Confidence: medium.
9. **H9. The panel's suspend/resume contract (F8, F14) will work through the
   NT36672E framework's prepare/unprepare with the Gemini descriptor delays,
   and the ESD check (`0x0A == 0x9C`) can be a later addition.** Test: after
   first light, two consecutive DPMS off/on cycles reading `0x0A` before off
   and after on. Confidence: medium.
10. **H10. Touch and panel power are coupled on this board** (the touch
    controller resumes on the vendor LCD-on notifier,
    [input recovery](../2026-07-12-input-backlight-recovery/README.md)), so
    the touch rail is downstream of the panel power sequence. Test: part of
    H6's regulator trace. Confidence: low-medium; recorded so the panel and
    touch descriptions are planned together.

## Part 3: what mainline needs beyond the retained simplefb

In dependency order, derived from the facts above:

1. Loader adoption (H2): a `simple-framebuffer` node carrying MM domain and
   root clocks, so `clk_ignore_unused` can go.
2. Clock gap (H7): the missing `DSI0_INTERFACE_CLOCK` gate in `clk-mt6797-mm`.
3. SoC data already drafted in patches 0028–0044, rebased per the architecture
   refresh: display mutex, MMSYS routes/resets, OVL/OVL-2L/RDMA and
   fixed-function data, DSI host data, native MIPI-TX PHY (F16), display PWM
   variant (F24).
4. MT6797 IOMMU/SMI support (absent upstream, F21) or a reviewed decision to
   run the first OVL/RDMA path without IOMMU translation.
5. Board description: bias regulator (H5), panel with `planet,gemini-pda-nt36672`
   (F26) and reset (H4), `pwm-backlight` on the display PWM (H8), I2C1
   enabled, GPIO60/GPIO251/GPIO178/GPIO180 pin states, portrait mode with a
   rotation property (F6).
6. Direct identity confirmation (H1) before any init table is sent.

## Limitations

- Offline only: no register, DSI, I2C or GPIO was read on the device for this
  record; every "live" value is quoted from earlier records.
- The LK conclusions (F1–F4) assume the retained loader matches the pinned
  public source in its LCM list and probe logic. The boot-graphics record
  matched logo order and security policy, not the LCM code.
- The public board DTS and defconfig are known to differ from the live DTB and
  configuration (F6 and the charging record's F2); board values are cited with
  that reservation.
- Command tables, ULPOSC behaviour and PHY register semantics are described,
  not copied; the vendor source remains the reference for exact bytes.

## Follow-up

- Roadmap native display step: identity gate reclassified from "contradictory"
  to "NT36672 family on the named device, pending direct confirmation (H1)";
  next device order H1 (log read), H5/H6 (bias and rail reads), H2 (simplefb
  adoption), H7 (clock gate), then H3/H4 panel bring-up.
- Patch 0040 needs the F19 clock fix before any enablement; patch 0043's mode
  clock needs the H3 decision; patch 0044's contract gains the F24 evidence.
