# Experiment: Gemini cellular modem reverse engineering and feasibility

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-04-gemini-cellular-re` |
| Status | `completed` (offline source review; no build, boot or device access) |
| Subsystem | MT6797 MD1 modem: power, clocks, reset, firmware handoff, CCCI/CLDMA/CCIF handshake, EMI MPU, SIM, voice audio, RF front end, userspace |
| Device variant | Project Gemini (Gemian `3.18.41+`, MT6797X, MT6351 E2, MD1 `MOLY.LR11.W1630.MD.MP.V105.8`) |
| Date(s) | 2026-10-04 |
| Investigator(s) | Claude (owner-requested investigation) |
| Tracking issue | Not yet assigned |

## Question

What does the stock Gemian kernel actually do to bring the cellular modem up,
which pieces of that are already available in Linux 7.1.3 or this repository,
what is blocked, and what is the cheapest first device experiment? The
roadmap keeps cellular at research only. Earlier records already settled the
transport architecture and the memory handoff:

- the [July CCCI/CLDMA topology record](../2026-07-13-modem-ccci-recovery/README.md)
  and its [backend contract](../2026-07-13-modem-ccci-recovery/results/mt6797-ccci-mainline-contract.md)
  (live MD1/MD3 domains, 16-byte CCCI header, 8+8 CLDMA queues, 16-byte
  descriptors, why `t7xx` does not apply);
- the [September architecture refresh](../2026-09-07-mt6797-cellular-upstream-architecture/README.md)
  with its [memory handoff](../2026-09-07-mt6797-cellular-upstream-architecture/MEMORY_HANDOFF.md),
  [Gemian handoff observation](../2026-09-07-mt6797-cellular-upstream-architecture/GEMIAN_HANDOFF.md),
  [retained firmware join](../2026-09-07-mt6797-cellular-upstream-architecture/RETAINED_FIRMWARE.md),
  [ARM7 selection](../2026-09-07-mt6797-cellular-upstream-architecture/ARM7_SELECTION.md)
  and [secure MPU](../2026-09-07-mt6797-cellular-upstream-architecture/SECURE_MPU.md)
  sub-records.

This record does not repeat those. It adds the parts a feasibility decision
still needed: the exact AP-side power/clock/reset sequence, who loads the
firmware on this device and when, the boot handshake and what gates it, the SIM,
voice-audio and RF ownership, what the vendor userspace supplies, what Linux
7.1.3 and this repository already carry, and how the only other public
MediaTek-SoC modem effort is structured. It changes no patch, profile,
candidate or device state.

## Inputs

Every vendor citation is a public GPL file at Gemian commit
`8cfe6596a503612e3332d9c26e292a19525a7f07`, the commit the charging record
used. Every mainline citation is Linux `7.1.3` as pinned in
`kernel/manifest.json`. Exact URLs, sizes and SHA-256 values are in
[`source-inputs.json`](source-inputs.json). Line numbers refer to those exact
revisions. No vendor source, firmware, NVRAM or private capture is copied into
this repository; register addresses, bit positions and message identifiers are
cited as facts.

The public board DTS caveat from the charging record applies here too: the live
Gemian DTB was built from a board file this public commit does not carry, so
board-level values in `aeon6797_6m_n.dts` are not authoritative. For the modem
this matters less, because every modem node sits in the SoC `mt6797.dtsi` and
the public board DTS adds no modem, SIM or antenna node at all (F15, F19).

## Part 1: verified facts

### Firmware: who loads it, and when

- **F1. On this device the bootloader, not the kernel, places the MD1 image in
  DRAM; the kernel only verifies that it happened.** The vendor driver's start
  routine loads firmware with `request_firmware` only when
  `modem_run_env_ready()` is false
  ([`modem_cldma.c` lines 2066–2070](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/eccci/modem_cldma.c#L2066-L2070));
  that flag is set per modem when the LK tag table reports a zero load error
  ([`ccci_util_lib_fo.c` lines 741–742 and 1090–1093](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/ccci_util/ccci_util_lib_fo.c#L741-L742)).
  The [Gemian handoff observation](../2026-09-07-mt6797-cellular-upstream-architecture/GEMIAN_HANDOFF.md)
  recorded exactly that: `ccci,modem_info_v2` in `/chosen`, loaded flags `0x5`,
  zero errors, and the saved log taking the "ready" branch that skips image
  load. The kernel-side fallback names are `modem_<postfix>.img` then
  `modem_1_<type>_n.img` over the type table
  ([`ccci_util_lib_load_img.c` lines 58–75 and 761–796](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/ccci_util/ccci_util_lib_load_img.c#L761-L796));
  `CONFIG_MTK_MD1_SUPPORT=12`
  ([defconfig line 243](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/configs/aeon6797_6m_n_defconfig#L243))
  is index 12 of that table, `ulwctg`, matching the `ulwctg` the retained
  header reports. `modem_3_3g_n.img` in the vendor firmware directory
  ([firmware inventory](../../docs/hardware/firmware.md)) is therefore the
  MD3/C2K fallback name, not the MD1 image the device runs.
- **F2. LK performs the same load before a mainline kernel.** A validated
  mainline boot on 2026-07-24 logged the LK-added reservation
  `mblock-6-ccci` at `0xb4000000`–`0xbdffffff` (160 MiB)
  ([runtime log line 328](../2026-07-24-mt6797-dvfsp-handoff-observer/results/runtime-candidate-an-attempt-1-20260724.txt)),
  and the private post-LK FDT delta validator lists `ccci,modem_info_v2`
  under `/chosen` and `mblock-5/6/7-ccci` as expected LK additions
  ([validator lines 54 and 74–76](../2026-07-24-mt6797-dvfsp-handoff-observer/scripts/validate-live-fdt-delta.py)).
  Consequence: when mainline boots through the stock LK, the authenticated
  MD1 image, DSP and ARM7 components are already in protected DRAM at the
  addresses the [handoff record](../2026-09-07-mt6797-cellular-upstream-architecture/GEMIAN_HANDOFF.md)
  observed. A mainline modem owner does not need a firmware file, a loader or
  redistribution rights to reach the first handshake; it needs to read the LK
  tags and never touch those regions. The retained-image digest and release
  authority gaps from the September record stay open; nothing here closes them.
- **F3. The second modem domain (MD3, CDMA2000) is configured and alive on the
  stock kernel but is not needed for the Gemini's markets.** `CONFIG_MTK_MD3_SUPPORT=2`,
  `CONFIG_MTK_C2K_LTE_MODE=2` (SRLTE) and `CONFIG_MTK_ECCCI_C2K=y`
  ([defconfig lines 244–245, 257](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/configs/aeon6797_6m_n_defconfig#L244-L245));
  the AP–C2K CCIF node carries its own `SCP_SYS_C2K` clock and 4 MiB shared
  memory ([`mt6797.dtsi` lines 1973–1986](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L1973-L1986)).
  The runtime data MD1 receives advertises C2K presence
  (`FEATURE_C2K_ALWAYS_ON`, [`modem_cldma.c` lines 3084–3104](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/eccci/modem_cldma.c#L3084-L3104)),
  but only on the v1 handshake; MT6797 uses v2 (F9). Whether MD1 firmware
  tolerates MD3 never starting is unknown (H6).

### Power, clocks and reset: the AP-side sequence

- **F4. Three MT6351 bucks power the modem and the AP driver switches them
  itself: `VSRAM_MD`, `VMD1`, `VMODEM`.** `md1_pmic_setting_on()` enables each
  (`VSRAM_MD_EN` `0x0654[0]`, `VMD1_EN` `0x0640[0]`, `VMODEM_EN` `0x062C[0]`),
  sets `VSLEEP_EN` for hardware sleep control, writes `VSRAM_MD` and `VMODEM`
  to 1.0 V (`VOSEL_ON` `0x50`/`0x40`), waits 300 µs and hands the three
  `VOSEL_CTRL` bits to hardware mode
  ([`cldma_platform.c` lines 555–577](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/eccci/mt6797/cldma_platform.c#L555-L577)).
  The power-off path disables them in reverse (lines 542–553). The public DT
  marks `vmodem` and `vmd1` `regulator-always-on` with a 0.6–1.39 V range
  ([`mt6797.dtsi` lines 439–456](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L439-L456)).
  The local [MT6351 regulator patch 0015](../../patches/v7.1.3/0015-regulator-mt6351-add-regulator-driver.patch)
  already models `buck-vmodem` (`CON0 0x0628`, `CON2 0x062c`), `buck-vmd1`
  (`0x063c`/`0x0640`) and `buck-vsram-md`, so the register numbers agree with
  the vendor comments; hardware-mode `VOSEL_CTRL` and `VSLEEP_EN` are not
  exposed by that driver.
- **F5. The MD1 power domain is an SPM MTCMOS the AP toggles, with bus
  protection, and it is absent from mainline's MT6797 scpsys.** The vendor
  `spm_mtcmos_ctrl_mdsys1()` sets `TOPAXI_PROT_EN` bits 24–28, powers down via
  `SPM_MD_PWR_CON` (`SPM_BASE + 0x284`: `SRAM_PDN` bit 8, `ISO`, `CLK_DIS`,
  `RST_B`, `PWR_ON`, `PWR_ON_2ND`), toggles an "LTE LS ISO" bit in
  `C2K_SPM_CTRL`, and polls `SPM_PWR_STATUS`/`_2ND` bit 0; `MD_PWRON_BY_CPU`
  is defined, so the CPU and not the SPM microcode performs the on sequence
  ([`mt_spm_mtcmos.c` lines 1121–1154 and 1636–1725](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/base/power/mt6797/mt_spm_mtcmos.c#L1636-L1725),
  [`mt_spm.h` lines 110, 127, 176–177](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/include/mt-plat/mt6797/include/mach/mt_spm.h#L110)).
  The driver reaches it as the clock `scp-sys-md1-main`
  ([`cldma_platform.c` lines 157, 804–806](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/eccci/mt6797/cldma_platform.c#L804-L806)).
  Mainline's `mtk-scpsys.c` MT6797 table has VDEC, VENC, ISP, MM, AUDIO,
  MFG_ASYNC and MJC only
  ([`mtk-scpsys.c` lines 755–813](https://github.com/gregkh/linux/blob/v7.1.3/drivers/pmdomain/mediatek/mtk-scpsys.c#L755-L813),
  [`mt6797-power.h`](https://github.com/gregkh/linux/blob/v7.1.3/include/dt-bindings/power/mt6797-power.h)),
  and it reads power status at `0x180`/`0x184` while the vendor header puts
  `SPM_PWR_STATUS` at `0x60c`/`0x610`; that offset discrepancy must be
  resolved from the live SPM before any MD1 domain is added (H2).
- **F6. The modem's 26 MHz source is gated through `INFRA_AO_MD_SRCCLKENA`
  and the PMIC RF clock buffers.** After the domain is on, the driver kicks the
  power-budget manager, writes `0x29` into the low byte of
  `INFRA_AO_MD_SRCCLKENA` (infra AO `0x1F0C`; `0x29` sets bits 0, 3 and 5,
  which the vendor comment attributes to MD1 and VRF18 control), and only then initialises the PLLs
  ([`cldma_platform.c` lines 791–853](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/eccci/mt6797/cldma_platform.c#L791-L853)).
  Before that it calls `clk_buf_set_by_flightmode(false)` (line 803), the
  PMIC DCXO clock-buffer control in
  [`mt_clkbuf_ctl.c` line 423](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/base/power/mt6797/mt_clkbuf_ctl.c#L423)
  (`FEATURE_RF_CLK_BUF`, [`ccci_config.h` line 64](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/eccci/mt6797/ccci_config.h#L64)).
  Mainline has no MT6351 clock-buffer provider; the Wi-Fi audit found the same
  gap for CONSYS, so this is a shared connectivity/modem dependency.
- **F7. `md1_pll_init()` is a fixed register script on the modem's own clock
  blocks, written from the AP.** It resets `MDPLL1_CON0` in APMIXED to
  `0x2EE8`, enables the 208 MHz MDPLL and `AP_PLL_CON0` bit 1, then on the
  MD-side `MD_CLKSW` (`0x20150000`), `MD_GLOBAL_CON_DCM` (`0x20130000`),
  `MD_PERI_MISC` (`0x20060000`), `MDL1A0` (`0x260F0000`), `MDTOP_PLLMIXED`
  (`0x20140000`) and `MDSYS_CLKCTL` (`0x20120000`) windows it sets L1
  permissions, PSMCU/L1MCU clock selects, flex clock-generator selects
  (`0x30302020`, `0x00002030`, `0x30203031`), busy-waits for `R_PLL_STS` and
  `R_FLEXCKGEN_STS0..2` ready bits, and writes a magic word to
  `MD_GLOBAL_CON_DUMMY`
  ([`cldma_platform.c` lines 588–789](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/eccci/mt6797/cldma_platform.c#L588-L789),
  window bases at [`modem_reg_base.h` lines 49–61](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/eccci/mt6797/modem_reg_base.h#L49-L61)).
  Several of the waits are unbounded `while` loops. The MD windows live in
  the `0x2xxxxxxx` modem-view aperture that the AP reaches only after the
  MTCMOS is on ("do NOT touch MD register before this",
  [`modem_cldma.c` line 2145](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/eccci/modem_cldma.c#L2145)).
  None of these registers has a mainline clock or syscon description.
- **F8. Release is one write, and the modem watchdog is disabled first.**
  `md_cd_power_on()` ends by writing the `WDT_MD_MODE` key into the MD RGU
  (`0x200f0100`) and the L1 RGU (`0x26010000`); `md_cd_let_md_go()` then
  writes `1` to `MD_BOOT_VECTOR_EN` (`0x20000024`)
  ([`cldma_platform.c` lines 843–844 and 860–870](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/eccci/mt6797/cldma_platform.c#L860-L870),
  [`modem_reg_base.h` lines 26, 44–47](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/eccci/mt6797/modem_reg_base.h#L26)).
  Boot progress is visible from the AP in `MD1_CFG_BOOT_STATS0/1`
  (`0x10201300`/`0x10201304`, `md_cd_dump_md_bootup_status`, lines 360–380),
  which is the read-only witness a first experiment should use (H1).

### Start sequence and handshake

- **F9. The complete AP start order in `md_cd_start()` is: clear shared
  memory and queues, program EMI MPU, reset the CCIF, reset CLDMA
  (`ENABLE_CLDMA_AP_SIDE`), power on (F4–F7), first-stage MPU, release (F8),
  enable the watchdog and CCIF interrupts, reset and start CLDMA, then wait
  for handshake 1.** Lines 2143–2200 of
  [`modem_cldma.c`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/eccci/modem_cldma.c#L2143-L2200);
  CLDMA block reset uses `INFRA_RST0/1_REG_AO/PD` bits (lines 69–99 of
  `cldma_platform.c`). The FSM then polls for `CCCI_EVENT_HS1` and
  `CCCI_EVENT_HS2` with a 10 s budget in 10 ms steps and resets the budget
  while a file-system request is in flight
  ([`ccci_fsm.c` lines 166–256](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/eccci/ccci_fsm.c#L166-L256),
  [`ccci_fsm.h` lines 95–96](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/eccci/ccci_fsm.h#L95-L96)).
  Handshake 1 is the modem's control message with `data[1] == 0`
  (`MD_INIT_START_BOOT`) and `reserved == 0x5555FFFF` (`MD_INIT_CHK_ID`) on
  the control channel; handshake 2 is `MD_NORMAL_BOOT` (also value 0, without
  the check id)
  ([`port_ctlmsg.c` lines 27–41](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/eccci/port_ctlmsg.c#L27-L41),
  [`ccci_core.h` lines 789–799](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/eccci/ccci_core.h#L789-L799)).
  MT6797 selects handshake version 2 (`AP_MD_HS_V2`,
  [`ccci_modem.c` line 501](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/eccci/ccci_modem.c#L501)):
  the AP's reply to HS1 is a small "feature query" structure carrying the
  runtime-data addresses inside shared memory (in modem view, AP physical
  minus the AP-to-MD offset), the MPU start and total size, and a version
  flag; the feature negotiation itself then happens through that shared
  runtime region
  ([`modem_cldma.c` lines 2898–2952](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/eccci/modem_cldma.c#L2898-L2952)).
  The v1 structure (lines 2954–3110) documents what those features are:
  platform string `MT6797E1`, boot mode, exception and shared-memory bases,
  32 kHz-less flag, random seed, SBP code, sequence-check flags, wall-clock
  time and C2K flags.
- **F10. Reaching HS2 needs a userspace file server; reaching HS1 does not.**
  The FSM keeps resetting its timeout while `fs_ongoing` is set, which the
  CCCI file-system port raises on each modem request
  ([`ccci_fsm.c` lines 232–233 and 464–467](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/eccci/ccci_fsm.c#L232-L233)).
  The stock userspace serves those requests with `ccci_fsd` and starts the
  modem with `ccci_mdinit`; the RIL stack is `mtkrild`/`gsm0710muxd` under
  Gemian's `ofono` ([vendor userspace](../../docs/hardware/vendor-userspace.md)).
  Between HS1 and HS2 the modem reads its NVRAM through that server; no NVRAM
  content is ever handled by the kernel. This fixes the first safe milestone
  for mainline: HS1 proves power, clocks, image placement, CLDMA and the
  control channel without any file, NVRAM, SIM or radio activity.
- **F11. Exception, watchdog and wake paths are separate interrupts.** The
  `mdcldma` node carries `GIC_SPI 265` (CLDMA, level high), `GIC_SPI 147`
  (AP CCIF, level low) and `GIC_SPI 266` (MD watchdog, falling edge)
  ([`mt6797.dtsi` lines 1790–1792](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L1790-L1792)).
  The CCIF ISR acknowledges `APCCIF_RCHNUM` into `APCCIF_ACK` and only
  schedules work for `D2H_EXCEPTION_INIT`, peer wake-up, sequence error and
  CCB wake-up bits ([`modem_cldma.c` lines 1916–1946](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/eccci/modem_cldma.c#L1916-L1946));
  the watchdog ISR raises an `MD_WDT` exception (lines 1742–1772). The six
  register windows and eleven clocks the node requests are in F13.

### Memory and protection

- **F12. EMI MPU programming is done by the AP from the image's own check
  header, in two stages around power-on, and is skipped when LK already did
  it.** `ccci_set_mem_access_protection()` refuses headers older than v4,
  sets `by_pass_setting` when `modem_run_env_ready()` is true, and otherwise
  programs the MD1 ROM/DSP region (id `MPU_REGION_ID_MD1_ROM`) from the
  header's region table and the shared region (`MPU_REGION_ID_MD1_SMEM`)
  ([`ccci_platform.c` lines 362–420](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/eccci/mt6797/ccci_platform.c#L362-L420));
  `SET_EMI_STEP_BY_STAGE` and `ENABLE_EMI_PROTECTION` are on
  ([`ccci_config.h` lines 70–72](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/eccci/mt6797/ccci_config.h#L70-L72)).
  The MT6797 EMI MPU has 24 region register pairs (`EMI_MPUA`…`EMI_MPUH3`)
  plus permission words
  ([`emi_mpu.h` lines 17–47](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/include/mt-plat/mt6797/include/mach/emi_mpu.h#L17-L47)).
  On this device the saved log already showed region 7 and two region-13
  requests issued on the ready path ([handoff](../2026-09-07-mt6797-cellular-upstream-architecture/GEMIAN_HANDOFF.md)),
  and the [secure MPU record](../2026-09-07-mt6797-cellular-upstream-architecture/SECURE_MPU.md)
  shows the host cannot see whether the secure side accepted them. Mainline
  has no EMI MPU driver for any MediaTek SoC.
- **F13. The resource contract of the live `mdcldma` node is fully
  describable with existing mainline providers except the MD1 domain.** Six
  windows (`0x10014000`, `0x10015000` AO; `0x10219000`, `0x1021a000` PDN;
  `0x10209000`, `0x1020a000` CCIF), three interrupts (F11), `cldma_capability
  = 6`, `md_smem_size = 0x100000`, and eleven clocks
  ([`mt6797.dtsi` lines 1782–1818](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L1782-L1818)).
  Ten of the clocks are infracfg gates that mainline's `clk-mt6797.c` already
  provides under the same names: `CLK_INFRA_CCIF_AP`, `CLK_INFRA_CCIF_MD`,
  `CLK_INFRA_AP_C2K_CCIF_0/1` and `CLK_INFRA_MD2MD_CCIF_0..5`
  ([`clk-mt6797.c` lines 471–498](https://github.com/gregkh/linux/blob/v7.1.3/drivers/clk/mediatek/clk-mt6797.c#L471-L498),
  [`mt6797-clk.h` lines 146–171](https://github.com/gregkh/linux/blob/v7.1.3/include/dt-bindings/clock/mt6797-clk.h#L146-L171)).
  The eleventh, `SCP_SYS_MD1`, is the MTCMOS of F5. The vendor driver also
  reads `mediatek,apmixed` for `MDPLL1_CON0`/`AP_PLL_CON0` (F7), which
  mainline exposes as the `apmixedsys` syscon
  ([mainline `mt6797.dtsi` lines 225–226](https://github.com/gregkh/linux/blob/v7.1.3/arch/arm64/boot/dts/mediatek/mt6797.dtsi#L225-L226)).
- **F14. The local Gemini DT keeps the two pre-LK CCCI reservations and
  nothing else.** `reserve-memory-ccci_md1` (`0xa100000`, 32 MiB aligned) and
  `reserve-memory-ccci_share` (`0x600000`, 64 MiB aligned), both `no-map`
  ([patch 0020 lines 120–133](../../patches/v7.1.3/0020-arm64-dts-mediatek-add-Planet-Gemini-PDA.patch));
  LK removes them and adds the concrete `mblock-5/6/7-ccci` nodes at
  `0x88000000` (6 MiB), `0xb4000000` (160 MiB) and `0xbe000000` (12 MiB)
  (F2, [handoff](../2026-09-07-mt6797-cellular-upstream-architecture/GEMIAN_HANDOFF.md)).
  The vendor `ccci_util_cfg` node fixes the three shared-memory sizes at
  2 MiB each with layout version 1
  ([`mt6797.dtsi` lines 4118–4123](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L4118-L4123)),
  matching the observed 2 MiB AP–MD1 region.

### SIM

- **F15. The SIM interfaces belong to the modem; the AP owns only pin
  muxing, the two SIM LDOs and an optional hot-plug EINT description.** The
  MT6797 pin table routes `MD1_SIM1_SCLK/SRST/SIO` and `MD1_SIM2_*` to GPIO
  126–128 and 155–157 (either slot on either pad group by function number)
  ([vendor `mt6797-pinfunc.h` lines 713–726, 874–887](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/include/dt-bindings/pinctrl/mt6797-pinfunc.h#L713-L726);
  the mainline copy carries the same functions,
  [`mt6797-pinfunc.h` lines 692 and 854](https://github.com/gregkh/linux/blob/v7.1.3/include/dt-bindings/pinctrl/mt6797-pinfunc.h#L692)).
  `VSIM1`/`VSIM2` are MT6351 LDOs with a 1.7–3.1 V range
  ([`mt6797.dtsi` lines 558–569](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L558-L569));
  the live Gemian baseline shows both disabled at the PMIC while the modem is
  idle ([baseline lines 613–614](../../docs/hardware/gemini-gemian-baseline.md)),
  and the local regulator patch already lists `ldo-vsim1`/`ldo-vsim2`
  ([patch 0015 lines 289–292](../../patches/v7.1.3/0015-regulator-mt6351-add-regulator-driver.patch)).
  The modem asks the AP for hot-plug EINT attributes over the RPC port
  (`IPC_RPC_GET_EINT_ATTR_OP`) by looking up DT nodes named
  `MD1_SIM1_HOT_PLUG_EINT`…`MD1_SIM4_HOT_PLUG_EINT` and reading their
  `interrupts`, `debounce`, `sockettype`, `dedicated` and `src_pin` properties
  ([`port_rpc.c` lines 164–270 and 821](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/eccci/port_rpc.c#L164-L270)).
  Neither the public SoC DTS, board DTS nor `cust_eint.dtsi` defines such a
  node, and the only SIM-related pin functions are the modem-owned
  `MD_INT0/1_C2K_UIM0/1_HOT_PLUG_IN` lines (pinfunc lines 263, 669, 673).
  Consequence: SIM detection, voltage class selection and the ISO 7816 link
  are inside the modem firmware. A mainline AP never talks to the SIM; it
  only has to leave the pins in the LK/preloader state and keep the two LDOs
  controllable by the modem path (the vendor regulator DT marks neither
  always-on, so the PMIC's hardware SIM control, not the AP, switches them).

### Voice audio

- **F16. The voice path is the AFE's `PCM2` interface to the internal modem,
  and mainline already models it.** The vendor voice PCM driver connects
  `I03/I04 → O17/O18` (ADC to modem PCM TX) and `I14 → O03/O04/O28/O29`
  (modem PCM RX to DAC and recording paths), enables the I2S ADC/DAC and then
  `SetModemPcmConfig(MODEM_1, …)`/`SetModemPcmEnable(MODEM_1, true)`
  ([`mt_soc_pcm_voice_md1.c` lines 293–315](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/sound/soc/mediatek/mt_soc_audio_6797/mt_soc_pcm_voice_md1.c#L293-L315)),
  where `MODEM_1` writes `PCM2_INTF_CON` (`0x53C`) and `MODEM_2` writes
  `PCM_INTF_CON1` (`0x530`)
  ([`mt_soc_afe_control.c` lines 2049–2074](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/sound/soc/mediatek/mt_soc_audio_6797/mt_soc_afe_control.c#L2049-L2074)).
  Mainline's MT6797 AFE has `MT6797_DAI_PCM_1`, `MT6797_DAI_PCM_2` and
  `MT6797_DAI_HOSTLESS_SPEECH`
  ([`mt6797-afe-common.h` lines 25–31](https://github.com/gregkh/linux/blob/v7.1.3/sound/soc/mediatek/mt6797/mt6797-afe-common.h#L25-L31)),
  drives the same `PCM_INTF_CON1`/`PCM2_INTF_CON` registers
  ([`mt6797-dai-pcm.c` lines 142–145, 218–230](https://github.com/gregkh/linux/blob/v7.1.3/sound/soc/mediatek/mt6797/mt6797-dai-pcm.c#L142-L145)),
  and its hostless routes wire `PCM_1/2_CAP` to `ADDA_DL` and `ADDA_UL` to
  `PCM_1/2_PB` exactly as the vendor voice path does
  ([`mt6797-dai-hostless.c` lines 19–33](https://github.com/gregkh/linux/blob/v7.1.3/sound/soc/mediatek/mt6797/mt6797-dai-hostless.c#L19-L33)).
  The local [disabled AFE node patch 0045](../../patches/v7.1.3/0045-arm64-dts-mediatek-mt6797-add-disabled-audio-afe.patch)
  is therefore the right base; voice needs no new audio driver, only the
  AFE/MT6351 codec bring-up the roadmap's audio step already owns. Which of
  PCM 1 or PCM 2 is the internal modem on this board is a register fact from
  the vendor (`PCM2`), not yet observed live.

### RF front end and antennas

- **F17. The AP has no RF, PA, antenna-tuner or band-select control; those
  are modem-firmware buses.** The pin table exposes `BPI_BUS0..` (baseband
  parallel interface, GPIO 192 onward and 212 onward), `RFIC0_BSI_CK/EN/D0-2`
  (baseband serial interface, GPIO 183–187, shared with `SPM_BSI_*`) and
  `ANT_SEL0..7` as alternate functions
  ([vendor pinfunc lines 975–1016, 1106, 240–298](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/include/dt-bindings/pinctrl/mt6797-pinfunc.h#L975-L1016)),
  the public board pinctrl selects none of them
  ([`aeon_gpio.dtsi`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/aeon_gpio.dtsi)),
  and the only AP-side RF-adjacent action in the CCCI driver is the clock
  buffer of F6 (`ccci_set_bsi_bpi_SRAM_cfg` exists behind
  `FEATURE_BSI_BPI_SRAM_CFG`, which `ccci_config.h` does not define). The
  transceiver, PA modules, switches and calibration therefore belong to the
  modem image and its NVRAM; the AP cannot help or harm them except by
  starting the modem. Regulatory consequence: once HS2 completes and the
  modem is given a SIM, radio behaviour is entirely the vendor firmware's,
  which is the same boundary the stock kernel ships with. The public board
  identity (`MT6797_S00`, `ulwctg`) does not state which RF bands this unit
  populates; that is a hardware fact outside the public source.

### Mainline 7.1.3, this repository and other MediaTek-SoC efforts

- **F18. Linux 7.1.3 has a WWAN core and exactly one MediaTek modem driver,
  `t7xx`, which depends on PCI.** `drivers/net/wwan/Kconfig` lists
  `MHI_WWAN_*`, `QCOM_BAM_DMUX`, `RPMSG_WWAN_CTRL`, `IOSM` and `MTK_T7XX`
  ("depends on PCI")
  ([Kconfig lines 109–111](https://github.com/gregkh/linux/blob/v7.1.3/drivers/net/wwan/Kconfig#L109-L111));
  the September record already established why none is a lower transport for
  APB CLDMA/CCIF. The 2026 `t9xx` series on the lists is likewise a PCIe
  driver and does not change that
  ([lore search](https://lore.kernel.org/linux-mediatek/?q=t9xx)).
  Upstream `mt6797.dtsi` has no modem, CCIF, CLDMA, MPU or clock-buffer node
  ([mainline `mt6797.dtsi`](https://github.com/gregkh/linux/blob/v7.1.3/arch/arm64/boot/dts/mediatek/mt6797.dtsi)).
- **F19. This repository's Gemini package has no modem consumer and no WWAN
  selection in its active profiles.** No patch under `patches/v7.1.3/` touches
  CCCI, CLDMA or CCIF, no config fragment selects `CONFIG_WWAN`, and the
  earlier package audits recorded the carve-out
  ([77-patch package audit](../2026-07-13-modem-ccci-recovery/results/mainline-ccci-current-77-package-20260714.txt)).
  What the repository does carry and the modem needs: MT6351 core/IRQ
  (patch 0010), MT6351 regulators including the modem bucks and SIM LDOs
  (patch 0015), the MT6797 EINT (patch 0005), the MT6797 scpsys binding
  (patch 0063) and the disabled AFE (patch 0045).
- **F20. The only public mainline effort for a MediaTek SoC-integrated modem
  is the MT6895 one, and it keeps the vendor CCCI split rather than a WWAN
  transport.** The `MT6895-Mainline` project publishes a userspace modem owner
  (`mtk-ccci-userspace`) that opens `/dev/ccci_monitor`, `/dev/ccci_fs` and
  `/dev/ccci_rpc`, starts the modem itself, serves file-system and RPC
  requests, and a ModemManager fork with an `mtk-soc` plugin that expects
  `ttyCCCI0`, `ccmni*` and a MIPC direct-IP endpoint from "a board-specific,
  already-validated kernel configuration"
  ([owner README](https://github.com/MT6895-Mainline/mtk-ccci-userspace),
  [architecture](https://github.com/MT6895-Mainline/mtk-ccci-userspace/blob/HEAD/docs/ARCHITECTURE.md),
  [deployment contract](https://github.com/MT6895-Mainline/mtk-ccci-userspace/blob/HEAD/docs/DEPLOYMENT.md),
  [ModemManager plugin notes](https://github.com/MT6895-Mainline/modemmanager-mtk-soc/blob/HEAD/docs/MTK-SOC.md)).
  Its layer diagram names the kernel side as "CCCI / CCIF / DPMAIF / ttyCCCI
  / ccmni", that is, the vendor-derived kernel driver carried out of tree on
  a newer SoC with the DPMAIF data path MT6797 lacks; its own docs describe
  it as device-specific and not hardware-validated as a boot service. It is
  evidence that the vendor FS/RPC protocol can be re-implemented in GPL
  userspace and that ModemManager can sit on top; it is not a kernel transport
  this board can reuse, and it confirms that no MediaTek SoC modem has an
  upstream kernel path today. Older notes on MT65xx and the public
  baseband reverse-engineering corpus
  ([cyrozap notes](https://github.com/cyrozap/mediatek-lte-baseband-re/blob/master/General-Notes.adoc))
  describe the same AP/BP/DSP split and firmware structure and name no
  mainline transport either.

## Part 2: hypotheses, ranked by value per device minute

"Gemian read" means one bounded read-only inspection of the running stock
kernel over the known-good LAN SSH path under the existing standing
authorization; "mainline boot" means a new reviewed experiment with its own
candidate, hypothesis and stop conditions. None is admitted by this record.
Every mainline test below must keep the LK `mblock-*-ccci` reservations
untouched (F2, F14) and must not open, map or write modem shared memory
beyond what the hypothesis names.

1. **H1. On a mainline boot through the stock LK, MD1 is powered off, the LK
   tags are present, and the boot-status registers read as "never
   released".** Confirming this costs nothing beyond a read-only patch and
   decides whether H2–H4 can proceed on the same loader. Test: a mainline boot
   that (a) prints `/chosen/ccci,modem_info_v2` length and the three
   `mblock-*-ccci` ranges, (b) reads `SPM_PWR_STATUS`/`_2ND` bit 0 at the
   vendor offsets `0x60c`/`0x610` *and* the mainline offsets `0x180`/`0x184`
   from the SPM syscon, and (c) reads `MD1_CFG_BOOT_STATS0/1` at
   `0x10201300` (F8), all once, without any write. Expected: tags present,
   bit 0 clear in exactly one offset pair (resolving the F5 discrepancy),
   boot status zero. Confidence: high for (a) (already observed on 2026-07-24,
   F2), medium for (b), medium for (c).
2. **H2. The MD1 MTCMOS can be added to mainline scpsys as a new MT6797
   domain with `SPM_MD_PWR_CON` at `0x284`, `SRAM_PDN` bit 8, status bit 0
   and TOPAXI bus-protect bits 24–28, and powering it on from the AP is
   harmless while the modem stays in reset.** F5 gives the sequence; the
   mainline driver's generic `scpsys_power_on` already does protect, power,
   isolation and SRAM steps in this shape. Risk: the "LTE LS ISO" bit in
   `C2K_SPM_CTRL` has no generic equivalent and the vendor touches it
   explicitly; omitting it may leave the MD bus isolated. Test: in the H1
   boot plus a disabled-by-default domain, enable it once from debugfs,
   re-read status bits and `MD1_CFG_BOOT_STATS0`, then power it off; a hang
   or bus error here is the stop condition. Confidence: medium.
3. **H3. With the domain on, the PLL script of F7 can be replayed from the AP
   with bounded waits, and completing it still leaves the modem halted,
   because release is the separate boot-vector write (F8).** This is the
   last step before any proprietary code runs and is still reversible by
   powering the domain off. Test: replay F7 with every `while` converted to a
   bounded poll and logged, verify `R_PLL_STS`/`R_FLEXCKGEN_STS*` bits read as
   ready, read boot status (still zero), then power off. Confidence: medium;
   the register bases are vendor constants, the modem-view aperture must be
   mapped only after H2 succeeds.
4. **H4. Releasing the boot vector after H2–H3, with the CCIF/CLDMA windows
   mapped read-only except the CCIF ACK register, produces an observable
   HS1 (`MD_INIT_START_BOOT` with check id `0x5555FFFF`) on CLDMA receive
   queue 0 within 10 s and no exception, because LK already placed and
   protected the image (F1, F2, F12) and HS1 needs no file server (F10).**
   This is the first test that executes the vendor modem image under
   mainline. Its admitted diagnostic effect is that proprietary code runs
   with DMA access to the LK-protected regions; the stop conditions are the
   watchdog interrupt, `D2H_EXCEPTION_INIT`, any EMI violation, or a 10 s
   timeout, each followed by domain power-off and a clean shutdown. Not
   answering HS1 keeps the modem in its boot wait; it cannot reach NVRAM,
   SIM or radio without HS2. Prerequisite: a minimal CLDMA receive-ring
   bring-up at the `0x10219000` PDN window, which the July contract
   describes; that is real driver work and the first place the September
   stop still bites. Confidence: medium for the handshake, low that the
   first ring implementation is right without a capture (H5).
5. **H5. A one-time Gemian capture of the CLDMA queue-0 receive descriptor
   and the first HS1 packet, taken from the already-running stock kernel
   through `/proc/ccci_dump` and the existing debug sysfs, is enough to
   validate the descriptor decoding for H4 without a new protocol document.**
   Test: Gemian read of the CCCI dump prefix already used in the handoff
   observation, extended to the queue dump `cldma_dump_register()` prints at
   boot ([`cldma_platform.c` lines 916–964](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/eccci/mt6797/cldma_platform.c#L916-L964));
   no modem node is opened. Confidence: medium; the dump is a ring snapshot,
   not a trace.
6. **H6. MD1 boots to HS2 with MD3 never started.** The runtime data v2 does
   not carry C2K flags (F9), and C2K is only useful for CDMA2000 networks.
   Test: only after H4 and only with a reviewed file server; observe whether
   HS2 arrives with the C2K CCIF clocks left off. Confidence: medium.
7. **H7. Voice audio needs no new driver: the mainline PCM 2 DAI plus the
   hostless speech link is the vendor path (F16).** Test: once the AFE and
   MT6351 codec are up for ordinary playback, enable `PCM_2_EN` with the
   modem off and confirm no AFE error; the real check waits for a call.
   Confidence: high for the register mapping, untested for the board.
8. **H8. The SIM is invisible to a correct mainline kernel (F15); the only
   AP-side SIM work is leaving GPIO 126–128 / 155–157 in their boot state and
   keeping VSIM1/VSIM2 out of the regulator core's "unused, disable" path.**
   Test: Gemian read of the live pinmux for those pins and of the two LDO
   enable bits with a SIM inserted versus removed; then, on mainline, confirm
   `regulator_init_complete` does not disable them (mark them
   `regulator-boot-on` or claim them from the future modem node).
   Confidence: high.

## Conclusion and the cheapest first experiment

What is known: the full AP-side bring-up is a short, fixed register sequence
(F4–F9) over resources that mainline already names except the MD1 power
domain, the PMIC clock buffers and the EMI MPU; LK has already loaded and
protected the firmware before our kernel runs (F1, F2); HS1 is reachable
without any file, NVRAM, SIM or radio involvement (F10); SIM and RF are
modem-internal (F15, F17); voice audio is already in mainline's AFE (F16).

What is blocked: a redistributable CLDMA/CCCI transport does not exist
anywhere upstream (F18, F20); the EMI MPU acceptance and shared-memory release
questions from September remain; everything past HS2 needs a GPL userspace
file/RPC server plus a RIL-class control stack, for which the MT6895 project is
the only public reference and it is explicitly device-specific.

The cheapest decision-changing experiment is **H1**: one read-only mainline
boot that confirms the LK tags, resolves the SPM status offset and reads the
boot-status registers. It needs a tiny observation patch, no new DT node and no
modem activity, and it tells whether H2–H4 can be attempted on this loader at
all. H2 and H3 are the next two bounded steps and stay reversible. H4 is the
first step that runs proprietary modem code and should be the first item to
receive its own reviewed experiment with explicit stop conditions.

## Validation and limits

Offline source review only. Vendor files were read from a blob-less shallow
fetch of the pinned Gemian commit; mainline files from the pinned 7.1.3 tag;
external project pages from their public repositories. All files inspected
are listed with sizes and SHA-256 values in
[`source-inputs.json`](source-inputs.json). No kernel was built, no device was
accessed, no firmware, NVRAM, modem node, shared memory or radio state was
touched, and no claim of hardware support is made. Line numbers were checked
against the fetched revisions; the external project descriptions were taken
from their README and docs files at fetch time and may change.
