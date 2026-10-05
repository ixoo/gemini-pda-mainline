# Experiment: Gemini PMIC basics reverse engineering

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-04-gemini-pmic-basics-re` |
| Status | `completed` (offline source review; no build, boot or device access) |
| Subsystem | MT6797 PMIC wrapper, MT6351 initialisation, regulators, interrupts, power/home keys, RTC, restart and power-off |
| Device variant | Project Gemini (Gemian `3.18.41+`, MT6797X, MT6351 E2) |
| Date(s) | 2026-10-04 |
| Investigator(s) | Claude (owner-requested investigation) |
| Tracking issue | Not yet assigned |

## Question

What does the stock Gemian kernel actually do with the MT6351 PMIC beyond
charging: how it brings the wrapper up, what it writes into the PMIC at boot,
which interrupts it uses, how the power key, RTC, restart and power-off work,
and what that implies for the mainline description. The roadmap's
[PMIC foundation step](../../docs/ROADMAP.md#ordered-gaps) left three items
open: the RTC BBPU reload question, the power-key long-press reset policy and
a reviewed power-off path. This record answers them from the pinned public
vendor source and the pinned Linux 7.1.3 tree, separates verified facts from
hypotheses, and ranks the hypotheses by how they should be tested. It changes
no patch, profile, candidate or device state.

Charging, BC1.1 and the fuel gauge are owned by the
[charging record](../2026-10-04-gemini-charging-re/README.md) and are only
referenced here. Earlier records own the live observations this builds on: the
[PMIC recovery](../2026-07-11-mt6351-pmic-recovery/README.md) (MT6351 E2
identity, EINT176, vendor interrupt banks), the
[PWRAP reset serviceability result](../2026-09-04-mt6797-pwrap-reset-serviceability/README.md)
(mainline wrapper, MFD and regulator bound on the device), the
[MFD upstream preparation](../2026-09-08-mt6351-mfd-upstream-preparation/README.md),
the [keys preparation](../2026-09-08-mt6351-keys-preparation/README.md) with its
[reset policy](../2026-09-08-mt6351-keys-preparation/RESET_POLICY.md), the
[RTC source audit](../2026-07-11-mt6351-pmic-recovery/results/rtc-source-audit-20260908.md)
and the [kernel restart diagnostic](../2026-07-20-mt6797-kernel-restart-diagnostic/README.md).

## Inputs

Every vendor citation below is a public GPL file at Gemian commit
`8cfe6596a503612e3332d9c26e292a19525a7f07`, the same commit the charging
record used. Every mainline citation is Linux `7.1.3` as pinned in
`kernel/manifest.json`. Exact URLs, sizes and SHA-256 values are in
[`source-inputs.json`](source-inputs.json). Line numbers refer to those exact
revisions. No vendor source, firmware or private capture is copied into this
repository; register addresses, bit positions and configuration values are
cited as facts. The one derived artifact,
[`results/pmic-init-setting-decoded.tsv`](results/pmic-init-setting-decoded.tsv),
lists the vendor's boot-time PMIC writes by register and field name so that
H8 can be tested without re-reading the source.

Two caveats apply throughout. First, the public source is not proven to be
the running binary (the charging record's F2 showed the live DTB differs from
the public board DTS). Second, the public `aeon6797_6m_n_defconfig` differs
from the retained active Gemian configuration in at least one PMIC-relevant
option (F12), so where the two disagree the retained configuration is the
better witness for the running kernel.

## Part 1: verified facts

### PMIC wrapper

- **F1. Both kernels skip wrapper initialisation when the loader already did
  it.** The vendor driver tests `PMIC_WRAP_INIT_DONE2` and only calls
  `pwrap_init()` when it reads zero
  ([`pwrap_hal.c` lines 1374–1384 and 1428](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/pmic_wrap/mt6797/pwrap_hal.c#L1374-L1384)).
  Mainline `pwrap_probe()` has the same gate with the comment "The PMIC could
  already be initialized by the bootloader"
  ([`mtk-pmic-wrap.c` lines 2532–2542](https://github.com/gregkh/linux/blob/v7.1.3/drivers/soc/mediatek/mtk-pmic-wrap.c#L2532-L2542)),
  and its `pwrap_init()` is the only place the `pwrap` reset line is pulsed
  (lines 2054–2061). The 2026-09-04 serviceability boot bound `mt-pmic-pwrap`,
  the MT6351 core and the regulator driver with zero wrapper errors
  ([runtime result](../2026-09-04-mt6797-pwrap-reset-serviceability/results/runtime-attempt-1-pwrap-serviceable-20260904.txt)
  lines 27–41). Inference, not yet shown by a log: on an ordinary LK boot the
  mainline wrapper inherits the loader's initialised state and never exercises
  the infracfg reset, so the reset repair matters only for the cold-init path.
- **F2. The vendor's own cold-init sequence is the reference if that path is
  ever needed.** `pwrap_init()` pulses `INFRA_GLOBALCON_RST0/RST1` bit 0,
  selects the 26 MHz SPI clock, resets the SPI slave, tunes `SI` strobe,
  programs the register clock and dual-IO, initialises the cipher, runs a
  write test against `DEW_WRITE_TEST` (`0xa55a`), sets arbiter priorities
  `0x6543C210`/`0xFEDBA987` and output selects `0x87654210`/`0xFED3CBA9`,
  enables starvation control, writes `INIT_DONE0`–`INIT_DONE3` and finally
  enables the P2P channel
  ([`pwrap_hal.c` lines 1076–1189](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/pmic_wrap/mt6797/pwrap_hal.c#L1076-L1189)).
  Mainline's MT6797 master data uses `PWRAP_CAP_RESET | PWRAP_CAP_DCM` and the
  MT6351 slave entry has `caps = 0`, i.e. no SPI-slave reset and no dual-IO
  step (lines 2207–2210, 2318–2326). The two sequences are therefore not
  identical; which one the preloader runs is unknown.
- **F3. The PMIC interrupt reaches the AP only through EINT176.** The vendor
  requests `pmic-eint` with `IRQF_TRIGGER_NONE` on the DT line
  (`interrupts = <262 4>`, `debounce = <262 1000>`,
  [`mt6797.dtsi` lines 965–977](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L965-L977)),
  disables the line in the hard handler, wakes a `SCHED_FIFO` priority-98
  thread, and that thread reads the four `INT_STATUS` banks, runs one callback
  per set bit, writes the bit back (W1C), clears the wrapper's EINT latch and
  re-enables the line
  ([`pmic_irq.c` lines 518–524 and 648–730](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/power/mt6797/pmic_irq.c#L648-L730)).
  The local MFD patch's 64-entry enumeration matches the vendor table bit for
  bit, including the unused slots 8, 38, 39 and 53–63
  ([patch 0010](../../patches/v7.1.3/0010-mfd-mt6397-add-MT6351-core-and-interrupt-support.patch),
  [`pmic_irq.c` lines 124–198](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/power/mt6797/pmic_irq.c#L124-L198)).

### MT6351 identity and boot-time initialisation

- **F4. The vendor keys silicon-specific writes on `HWCID`, and the live part
  takes the `0x5140` branch.** `PMIC_INIT_SETTING_V1()` compares `HWCID`
  (`0x0200`) against `0x5120` and `0x5140`
  ([`pmic_initial_setting.c` lines 157–457](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/power/mt6797/pmic_initial_setting.c#L157-L457));
  the live reads were `HWCID 0x5140`, `SWCID 0x5120`
  ([PMIC recovery](../2026-07-11-mt6351-pmic-recovery/README.md#physical-pmic-identity)).
  The `0x5140` branch adds six writes: `RG_SRCVOLTEN_MODE` and `RG_VOWEN_MODE`
  to 1 (`TOP_CKSEL_CON2`), `VSRAM_PROC` `VOSEL_CTRL = 1`, `VOSEL_SLEEP = 0x10`
  and `VSLEEP_EN = 1`, and `RG_VSRAM_PROC_MODE_CTRL = 1`. The local MFD core
  identifies the chip through `SWCID` high byte `0x51`
  (patch 0010, `cid_addr = MT6351_SWCID`), consistent with how mainline
  identifies MT6357/MT6358 (`mt6397-core.c` lines 283–330).
- **F5. The vendor kernel re-applies a 245-field PMIC configuration at
  `fs_initcall` time; mainline applies none of it.** `pmic_mt_probe()` prints
  the CID and status registers, then runs `PMIC_INIT_SETTING_V1()`, the
  AUXADC init, the interrupt setup, the regulator registration and the
  low-battery protection
  ([`pmic.c` lines 4668–4750, 5098](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/power/mt6797/pmic.c#L4668-L4750)).
  The decoded table groups as follows (register family, writes):

  | Family | Writes | What the writes do |
  | --- | ---: | --- |
  | `STRUP_CON*` / `STRUP_ANA` | 25 | Power-good high-to-low shutdown enables for 13 rails, over-current enables for VCORE/VMODEM/VMD1/VSRAM_MD, UVLO debounce, `STRUP_PWROFF_SEQ_EN` and `PREOFF_EN` = 1, `RG_STRUP_THR_CLR`/`PG_STATUS_CLR`/`CLR_JUST_RST` pulses |
  | `TOP_RST_*` | 4 | `TOP_RST_STATUS_CLR = 0xFFFF`, `WDTRSTB_STATUS` read then cleared, **`RG_WDTRSTB_EN = 1`** (F18) |
  | `TOP_CON`, `SMT_CON*` | 7 | `SRCLKEN_IN0/IN1` and `OSC_SEL` hardware mode, Schmitt triggers on the SPI pads and `WDTRSTB_IN` |
  | `TOP_CKPDN*`, `TOP_CKSEL*`, `TOP_CKHWEN*` | 22 | AUXADC clocks on, `RTC_75K`, `RTCDET`, `RTC_EOSC32` and `TRIM_75K` clocks gated, `RG_75K_32K_SEL = 1`, audio 18 MHz gated |
  | `BUCK_*` (9 bucks) | 68 | Slew rates `0x11`/`0x4`, `VSLEEP_EN = 1` on all nine bucks, `VOSEL_CTRL = 1` on VCORE and VSRAM_PROC (hardware voltage selection), OC shutdown select, analog loop constants, `BUCK_OC_CON0/3/4 = 0xFFFF` |
  | `LDO_*` and `*_ANA_CON` | 60 | `OCFB_EN = 1` on 30 LDOs, mode/`SRCLK` selectors, `RG_VA10_VOSEL = 2`, **`RG_VDRAM_EN = 0`** and `RG_VBIF28_ON_CTRL = 0` (F10) |
  | `FGADC_CON*` | 7 | Sleep-mode coulomb counting thresholds (charging record F15) |
  | `AUXADC_*` | 21 | Averaging, per-channel trim selects, `MDBG`/`MDRT` periodic detection |
  | `CHR_CON*` | 8 | `VCDT_HV_VTH = 0xB`, `VBAT_OV_VTH = 0x4`, `CHRWDT_TD = 0x3`, `BC11_RST = 1`, `HWCV_EN`/`ULC_DET_EN` = 1 (charging record F6/F9) |

  Because the preloader and LK have already run their own PMIC
  initialisation, these writes are the kernel's refresh of settings the
  loader may already hold; the public source does not show which values
  differ from the loader state at kernel entry (H8).
- **F6. Before a software reset the vendor forces four bucks to a safe sleep
  configuration.** `pmic_pre_wdt_reset()` sets `VSLEEP_SEL = 0` and
  `VOSEL_SLEEP = 0x10` for VCORE, VSRAM_MD, VMODEM and VMD1 with interrupts
  disabled, then dumps all registers
  ([`pmic.c` lines 203–227](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/power/mt6797/pmic.c#L203-L227)).
  It is called from the TOPRGU reset path (F19). Mainline's restart does not
  touch the PMIC.
- **F7. Low-battery and over-current protection are software features of the
  vendor PMIC driver.** Thresholds are `3400`, `3250` and `3100` mV scaled by
  `4096/5400` into `AUXADC_LBAT_VOLT_MAX/MIN`, with the `BAT_L` interrupt
  (index 7) enabled on demand, and battery over-current at `5950`/`7000` mA
  ([`mt_pmic.h` lines 36–42](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/include/mt-plat/mt6797/include/mach/mt_pmic.h#L36-L42),
  [`pmic.c` lines 2336–2338, 2405–2427](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/power/mt6797/pmic.c#L2405-L2427)).
  The default interrupt set the vendor enables unconditionally is keys 0–3
  and `CHRDET` 46, with the RTC driver adding 9
  ([`pmic_irq.c` lines 570–646](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/power/mt6797/pmic_irq.c#L570-L646),
  [`mtk_rtc_common.c` lines 735–742](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/rtc/mtk_rtc_common.c#L735-L742)).
  Mainline has none of the protection logic; the roadmap's battery step
  inherits that gap.

### Regulators

- **F8. Vendor rail set and board constraints.** Nine bucks (VCORE, VGPU,
  VMODEM, VMD1, VSRAM_MD, VS1, VS2, VPA, VSRAM_PROC; 600–1393.75 mV in
  6.25 mV steps) and 33 LDO entries including the split `vcn33_bt`/`vcn33_wifi`
  pair sharing one `VOSEL`
  ([`pmic.c` lines 1584–1663](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/power/mt6797/pmic.c#L1584-L1663)).
  The public DT marks every buck except VCORE `regulator-always-on` and
  `regulator-boot-on`, and marks these LDOs `boot-on`: `va18`, `vtcxo24`,
  `vusb33`, `vemc_3v3`, `vio28`, `vio18`, `vsram_proc`, `vxo22`, `va10`,
  `vdram` ([`mt6797.dtsi` lines 417–774](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L417-L774)).
  The local [regulator driver](../../patches/v7.1.3/0015-regulator-mt6351-add-regulator-driver.patch)
  describes the same nine bucks and a single `VCN33`; the live mainline boot
  registered 40 regulators and consumed only VEMC and VIO18 (F1 result,
  lines 31–33). The Gemini board DT carries only the parent fix
  ([patch 0062](../../patches/v7.1.3/0062-arm64-dts-mediatek-gemini-fix-MT6351-regulator-parent.patch))
  and no rail constraints, so today every unused rail is protected only by the
  profiles' `regulator_ignore_unused` flag
  ([roadmap shared dependencies table](../../docs/ROADMAP.md#shared-dependencies)).
- **F9. VCORE and VSRAM_PROC are under hardware voltage control in the vendor
  configuration.** `BUCK_VCORE_VOSEL_CTRL = 1` and (E2 branch)
  `BUCK_VSRAM_PROC_VOSEL_CTRL = 1` select the hardware `VOSEL` path used by the
  SPM/DVFS engines (F5 table; the vendor DT leaves `vcore` without
  `always-on` for the same reason). A software write to `VCORE_VOSEL` from a
  mainline regulator consumer therefore may not take effect, or may fight
  the firmware, until that bit is understood (H7).
- **F10. The vendor clears the software enable of VDRAM at init
  (`RG_VDRAM_EN = 0`) while DRAM obviously stays powered.** The same table
  writes `RG_VBIF28_ON_CTRL = 0`. So for at least VDRAM the software enable
  bit is not the rail's sole control, and a mainline regulator description
  must not let the regulator core "disable" VDRAM as unused (H7).

### Power and home keys

- **F11. Key events travel PMIC interrupt → vendor thread → keypad driver,
  and the public Gemian source reports the power key as `KEY_ESC`.** IRQs 0/2
  (`pwrkey`, `pwrkey_r`) and 1/3 (`homekey`, `homekey_r`) call
  `kpd_pwrkey_pmic_handler()`/`kpd_pmic_rstkey_handler()`
  ([`pmic_irq.c` lines 216–275](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/power/mt6797/pmic_irq.c#L216-L275)),
  which under `CONFIG_KPD_PWRKEY_USE_PMIC=y` report `KEY_ESC` for the power key
  and the DT `kpd-sw-rstkey` code for the home key
  ([`hal_kpd.c` lines 356–382](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/input/keyboard/mediatek/mt6797/hal_kpd.c#L356-L382),
  [`kpd.c` lines 356–370](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/input/keyboard/mediatek/kpd.c#L356-L370),
  [defconfig line 371](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/configs/aeon6797_6m_n_defconfig#L371)).
  The DT value `kpd-sw-pwrkey = <116>` (`KEY_POWER`,
  [`cust_kpd.dtsi` lines 11–30](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/cust_kpd.dtsi#L11-L30))
  is not used on this path. The earlier PMIC record's "reported as Linux key
  code 116" was read from the live DT, not from an event capture; the public
  source says the Gemini's On/Esc button is delivered as Escape under Gemian.
  Which code a mainline `mediatek,pmic-keys` node should use is a board
  decision (H1).
- **F12. The long-press reset policy differs between the public defconfig and
  the retained running configuration.** `long_press_reboot_function_setting()`
  writes `RG_PWRKEY_RST_EN`, `RG_HOMEKEY_RST_EN` and `RG_PWRKEY_RST_TD` only
  when `CONFIG_KPD_PMIC_LPRST_TD` is defined, and otherwise clears both
  enables
  ([`hal_kpd.c` lines 240–290](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/input/keyboard/mediatek/mt6797/hal_kpd.c#L240-L290)).
  The public defconfig at this commit sets `CONFIG_ONEKEY_REBOOT_NORMAL_MODE`
  and `_OTHER_MODE` (lines 369–370) but **not** `CONFIG_KPD_PMIC_LPRST_TD`, so
  the public build disables hardware long-press reset; the retained active
  Gemian configuration has `CONFIG_KPD_PMIC_LPRST_TD=1`, giving one-key reset
  with selector 1 (11 s) as the [reset policy record](../2026-09-08-mt6351-keys-preparation/RESET_POLICY.md)
  established. The running kernel's register state is still unobserved (H3).
  Field positions are confirmed in the header: `TOP_RST_MISC` (`0x02b6`) bits
  9/8 enables, bits 13:12 selector
  ([`upmu_hw.h` lines 2811–2844](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/include/mt-plat/mt6797/include/mach/upmu_hw.h#L2811-L2844)).
- **F13. Mainline `mtk-pmic-keys` has no MT6351 data and always writes the
  reset register.** The driver covers MT6397/6323/6331/6357/6358/6359
  (`mtk-pmic-keys.c` lines 61–135, 302–318) and programs `pmic_rst_reg` from
  `power-off-time-sec`/`mediatek,long-press-mode` on every probe, so an
  absent property disables both hardware reset enables. MT6351 support exists
  locally in [patch 0011](../../patches/v7.1.3/0011-Input-mtk-pmic-keys-add-MT6351-support.patch)
  and the [keys topic](../2026-09-08-mt6351-keys-preparation/README.md); the
  MFD cell needs a matching enabled `keys` child to bind, and no Gemini key
  node exists yet.

### RTC

- **F14. Register layout: base `0x4000`, write trigger at `+0x3c`, key
  `0x43 << 8`, PMIC interrupt 9.** Vendor:
  [`mtk_rtc_hal.h` lines 26 and 36](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/include/mt-plat/mt6797/include/mach/mtk_rtc_hal.h#L26-L36),
  [`mt_rtc_hw.h` lines 19–26, 265](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/include/mt-plat/mt6797/include/mach/mt_rtc_hw.h#L19-L26).
  `BBPU` bits: `PWREN` 0 ("BBPU = 1 when alarm occurs"), `BBPU` 2 ("1: power
  on, 0: power down"), `AUTO` 3 ("BBPU = 0 when xreset_rstb goes low"),
  `CLRPKY` 4, `RELOAD` 5, `CBUSY` 6. Mainline `rtc-mt6397` uses the same
  `BBPU`, `CBUSY`, key and `WRTGR_MT6397 = 0x3c`
  ([`rtc.h` lines 17–23](https://github.com/gregkh/linux/blob/v7.1.3/include/linux/mfd/mt6397/rtc.h#L17-L23)),
  which is what the local [RTC patch 0012](../../patches/v7.1.3/0012-rtc-mt6397-add-MT6351-support.patch)
  maps MT6351 onto.
- **F15. The vendor `RELOAD` sequence is shared with chips that mainline
  already serves without it.** `hal_rtc_get_tick_time()` sets `KEY | RELOAD`,
  triggers, then reads the counters and re-reads seconds for rollover
  ([`mtk_rtc_hal_common.c` lines 201–218](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/rtc/mtk_rtc_hal_common.c#L201-L218)).
  That file is built for every vendor PMIC family, MT6323 and MT6391 included
  ([`rtc/Makefile`](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/rtc/Makefile)),
  while mainline `__mtk_rtc_read_time()` reads the counters directly and
  checks seconds rollover with no `RELOAD`
  ([`rtc-mt6397.c` lines 62–86](https://github.com/gregkh/linux/blob/v7.1.3/drivers/rtc/rtc-mt6397.c#L62-L86))
  and ships for `mediatek,mt6323-rtc` (line 334). So the reload is a vendor
  convention, not a per-chip requirement that mainline has had to honour for
  MT6323; the inference that MT6351 behaves the same is H5.
- **F16. Alarm and interrupt handling match in shape.** Vendor sets the alarm
  with `RTC_AL_MASK_DOW`, `IRQ_EN |= ONESHOT | AL`, reads `IRQ_STA` (read-
  clear) and treats `IRQ_STA_LP` as a low-power exception
  ([`mtk_rtc_hal.c` (mt6351) lines 229–300](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/rtc/mt6351/mtk_rtc_hal.c#L229-L300));
  mainline does the same at `rtc-mt6397.c` lines 40–58 and 178–235, with the
  local [IRQ_EN masking fix](../2026-09-08-mt6397-rtc-irq-fix/README.md) and
  [wake error fix](../2026-09-12-mt6397-rtc-wake-errors/README.md) pending.
- **F17. The RTC spare registers are the loader's boot-mode mailbox.**
  `RTC_PDN1` (`0x402c`) carries `FAC_RESET` bit 4, `BYPASS_PWR` 6,
  `PWRON_TIME` 7, `GPIO_*` users 8–12, `FAST_BOOT` 13, `KPOC` 14, `DEBUG` 15;
  `RTC_PDN2` carries `PWRON_ALARM` 4, UART bits 5–6, autoboot 7, `LOGO` 15;
  `RTC_SPAR0` bit 6 is `32K_LESS` and bit 7 `LP_DET`
  ([`mt_rtc_hw.h` lines 195–245](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/include/mt-plat/mt6797/include/mach/mt_rtc_hw.h#L195-L245)).
  `arch_reset("recovery"|"bootloader"|"kpoc")` sets `FAC_RESET`, `FAST_BOOT`
  or `KPOC` through `rtc_mark_*()` before the TOPRGU reset
  ([`wd_api.c` lines 583–613](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/watchdog/mediatek/wdk/wd_api.c#L583-L613),
  [`mtk_rtc_common.c` lines 346–374](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/rtc/mtk_rtc_common.c#L346-L374)).
  Mainline `rtc-mt6397` reads only `PDN2_PWRON_ALARM` and never writes `PDN1`
  or `SPAR0`, so a mainline reboot cannot request recovery or fastboot and,
  conversely, cannot corrupt the loader's flags (H9). The vendor init also
  gates the `RTC_75K`, `RTCDET` and `EOSC32` clocks and selects `75K_32K_SEL`
  (F5), and `hal_rtc_bbpu_pwdn()` reads `32K_LESS` to decide the power-down
  sequence (F21).

### Restart and power-off

- **F18. The vendor enables the PMIC's watchdog-reset input at every boot.**
  `PMIC_INIT_SETTING_V1()` reads `WDTRSTB_STATUS` (bit 2 of `TOP_RST_MISC`,
  "did the PMIC reset because of WDTRSTB"), pulses `WDTRSTB_STATUS_CLR` and sets
  `RG_WDTRSTB_EN` (bit 0) to 1 (decoded table rows 1–3). With that bit set,
  the TOPRGU's external reset output (`WDT_MODE_EXTEN`, F19) resets the PMIC
  as well, which is what makes a vendor reboot a cold PMIC reset. Mainline
  never touches `TOP_RST_MISC` bit 0 and inherits whatever the loader left
  there (H4).
- **F19. The vendor explicitly bypasses PSCI for both restart and power-off
  on MT6797.** Its `psci.c` wraps `arm_pm_restart = psci_sys_reset` and
  `pm_power_off = psci_sys_poweroff` in `#ifndef CONFIG_ARCH_MT6797`
  ([`psci.c` lines 410–414](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/kernel/psci.c#L410-L414)),
  the DT advertises `arm,psci-0.2` with only suspend/off/on/affinity function
  IDs ([`mt6797.dtsi` lines 59–66](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L59-L66)),
  and `machine_restart()` falls through to the restart-notifier chain
  ([`process.c` lines 160–170](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/kernel/process.c#L160-L170)).
  There a priority-128 notifier calls `arch_reset()` → `wd_api->wd_sw_reset()`
  → `wdt_arch_reset()`: an SMC `MTK_SIP_KERNEL_DISABLE_DFD`, `WDT_RESTART`
  with its key, `WDT_MODE = KEY | EXTEN` plus `AUTO_RESTART` for an ordinary
  reboot, `pmic_pre_wdt_reset()` (F6), a 100 µs delay and `WDT_SWRST` with key
  `0x1209`
  ([`wd_api.c` lines 583–650](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/watchdog/mediatek/wdk/wd_api.c#L583-L650),
  [`mtk_wdt.c` lines 321–366](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/watchdog/mediatek/wdt/mt6797/mtk_wdt.c#L321-L366)).
  Mainline registers the PSCI restart notifier at priority 129 and
  `mtk_wdt` at 128 ([`psci.c` lines 309–330, 682](https://github.com/gregkh/linux/blob/v7.1.3/drivers/firmware/psci/psci.c#L309-L330),
  [`mtk_wdt.c` lines 228–245, 439](https://github.com/gregkh/linux/blob/v7.1.3/drivers/watchdog/mtk_wdt.c#L228-L245));
  the local watchdog patches
  [0081](../../patches/v7.1.3/0081-watchdog-mtk-set-MT6797-auto-restart-mode.patch),
  [0087](../../patches/v7.1.3/0087-watchdog-mtk-prioritize-MT6797-TOPRGU-restart.patch)
  and [0543](../../patches/v7.1.3/0543-watchdog-mtk-minimal-MT6797-restart.patch)
  reproduce the vendor ordering and `AUTO_RESTART` contract, and the TOPRGU
  restart has completed an ordinary reboot on the device
  ([restart record](../2026-07-20-mt6797-kernel-restart-diagnostic/README.md)).
  What mainline still lacks from the vendor path is the `DISABLE_DFD` SMC and
  the pre-reset buck writes (F6); neither has been shown necessary.
- **F20. Vendor power-off is an RTC `BBPU` write, installed over PSCI at
  late init.** `mt_power_management_init()` sets `pm_power_off = mt_power_off`
  ([`mt_pm_init.c` line 620](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/base/power/mt6797/mt_pm_init.c#L620)).
  `mt_power_off()` → `hal_rtc_bbpu_pwdn()`: clear the 2-second reboot bits in
  `RTC_AL_SEC` (`2SEC_EN` bit 8, `AUTO_PDN_SEL` bit 6), set `RTC_CON_F32KOB`
  when no `RTC_GPIO` user holds the 32 kHz export, and, when `32K_LESS` is
  clear and no charger is detected, drive the `SRCLKEN` pin low as a GPIO
  before writing `BBPU = KEY | AUTO | PWREN` (`0x4309`, `BBPU` bit 2 cleared)
  and triggering
  ([`mtk_rtc_hal.c` (mt6351) lines 176–213](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/rtc/mt6351/mtk_rtc_hal.c#L176-L213),
  [`mtk_rtc_hal_common.c` lines 138–154](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/rtc/mtk_rtc_hal_common.c#L138-L154),
  [`mtk_rtc_common.c` lines 388–410](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/rtc/mtk_rtc_common.c#L388-L410)).
  `PWREN` stays set so an RTC alarm can power the device back on, and with a
  charger attached the PMIC's `CHRDET` re-powers into LK's kernel power-off
  charging mode (`CONFIG_MTK_KERNEL_POWER_OFF_CHARGING=y`, defconfig line 387;
  `chrdet_int_handler()` powers off again on unplug in that mode,
  `pmic_irq.c` lines 285–308).
- **F21. Mainline has a reusable PMIC power-off driver, but not for MT6351,
  and its write differs.** `mt6323-poweroff` registers a `SYS_OFF_MODE_POWER_OFF`
  handler that writes `RTC_BBPU = RTC_BBPU_KEY` (clearing `PWREN`, `BBPU` and
  `AUTO`), triggers `WRTGR` at `+0x3c` and polls `CBUSY`
  ([`mt6323-poweroff.c` lines 17–40, 60–75](https://github.com/gregkh/linux/blob/v7.1.3/drivers/power/reset/mt6323-poweroff.c#L17-L40));
  it binds only to the `mediatek,mt6323-pwrc` cell whose resource is the
  MT6323 RTC base `0x8000`
  ([`mt6397-core.c` lines 45–46, 122–150](https://github.com/gregkh/linux/blob/v7.1.3/drivers/mfd/mt6397-core.c#L122-L150),
  [binding lines 199–216](https://github.com/gregkh/linux/blob/v7.1.3/Documentation/devicetree/bindings/mfd/mediatek,mt6397.yaml#L199-L216)).
  On MT6351 the same registers sit at `0x4000` (F14). Without such a cell,
  mainline's `pm_power_off` is `psci_sys_poweroff` (PSCI `SYSTEM_OFF` into the
  retained ATF, `psci.c` lines 332–334, 684), a path the vendor kernel never
  exercises (F19), so its behaviour on this device is unknown (H2). The
  [timed reboot diagnostic](../2026-07-16-timed-reboot-diagnostic/README.md)
  already noted that the candidate "has no poweroff node or enabled PMIC
  poweroff driver".
- **F22. Live mainline evidence to date.** Wrapper, MT6351 core and regulator
  driver bound with 40 regulators and VEMC/VIO18 consumers (F1); TOPRGU
  restart completed an ordinary reboot (F19); no mainline boot has yet bound
  the RTC or key cells, delivered a PMIC interrupt to a consumer, read the RTC
  or attempted power-off ([support matrix](../../docs/HARDWARE_SUPPORT.md)
  row "RTC, power keys, and power-off": `unknown`).

## Part 2: hypotheses, ranked by value per device minute

Each hypothesis states what would confirm or refute it and the cheapest
test. "Gemian read" means one bounded, read-only inspection of the running
stock kernel over the known-good LAN SSH path under the existing standing
authorization, remembering the
[`pmic_access` caching limit](../2026-09-08-mt6351-keys-preparation/RESET_BINARY.md#why-the-existing-debug-read-is-insufficient);
"mainline boot" means a new reviewed experiment with its own candidate,
hypothesis and stop conditions. None is admitted by this record.

1. **H1. With a `keys` child (`mediatek,mt6351-keys`, power key only), the
   MFD interrupt domain delivers press and release events on EINT176 under
   mainline with no further PMIC configuration (F3, F11, F13).** This is the
   cheapest decision-changing PMIC test: it validates the whole EINT → MFD
   → child IRQ path that the RTC alarm (H6) and `CHRDET` (charging record H2)
   also need. Test: mainline boot with the key node, `power-off-time-sec`
   absent for now (H3 decides), count `powerkey`/`powerkey_r` in
   `/proc/interrupts` and read events with `evtest` across one attended
   press. Default picked for the keycode: `KEY_POWER` (116), because that is
   what systemd-logind and the live Gemian DT expect, with a note that the
   public Gemian source delivers `KEY_ESC` (F11); switching later is a one-line
   DT change. Confidence: high; the vendor enables these lines with nothing
   but the mask bits.
2. **H2. PSCI `SYSTEM_OFF` through the retained ATF does not power the
   Gemini down, and the correct mainline power-off is an MT6351 variant of
   `mt6323-poweroff` at RTC base `0x4000` (F19–F21).** The vendor's explicit
   `#ifndef CONFIG_ARCH_MT6797` and its RTC-based override are strong
   circumstantial evidence; the ATF binary itself was not inspected. Two
   sub-questions: whether `KEY`-only (mainline MT6323 semantics) or
   `KEY | AUTO | PWREN` (vendor) is right for this board, and whether the
   `SRCLKEN`-low step matters. Test, in order: (a) a mainline boot that issues
   `poweroff` with the charger **detached** (otherwise `CHRDET` re-powers into
   LK charging mode, F20) and a UART/USB log, classifying the outcome as
   powered down, reset or hang, with the usual stop condition and recovery;
   (b) if (a) hangs or resets, a candidate adding an `mt6351-pwrc` cell and a
   small compatible extension of `mt6323-poweroff` using the vendor's
   `0x4309` value, since the vendor sequence is the only one proven on this
   board. Confidence: medium-high that (a) fails, high that (b) works.
3. **H3. The running Gemian holds `TOP_RST_MISC` bits 9=1, 8=0, 13:12=01
   (one-key, 11 s), matching the retained configuration rather than the
   public defconfig (F12).** This decides the `power-off-time-sec` /
   `mediatek,long-press-mode` values for the key node and whether mainline's
   unconditional reset-register write (F13) would silently remove the user's
   hardware escape hatch. Test: a Gemian read of register `0x2b6` through the
   existing bounded `pmic_access` path, repeated once with a different
   register in between to defeat the cached-value limit. Confidence: medium.
4. **H4. The loader leaves `RG_WDTRSTB_EN` (`TOP_RST_MISC` bit 0) set, so a
   mainline TOPRGU restart with `EXTEN` already resets the PMIC exactly as the
   vendor reboot does (F18, F19).** If instead the bit is clear, a mainline
   reboot is a warm AP-only reset and PMIC state (regulator votes, interrupt
   masks, RTC spare bits) survives across reboots, which would change how
   much F5 state mainline can trust at boot. Test: the same `0x2b6` Gemian
   read as H3 covers bit 0 (the vendor kernel has set it by then, so the
   loader-only value needs a mainline boot that reads `TOP_RST_MISC` through
   the MFD regmap before anything writes it). Confidence: medium.
5. **H5. Mainline `rtc-mt6397` reads a correct, fresh time from MT6351
   without the vendor `RELOAD` write (F14–F16).** The sibling-chip evidence is
   the argument; the residual risk is a stale shadow register. Test: mainline
   boot with the existing RTC node, compare three `hwclock -r` readings ten
   seconds apart against the monotonic clock, and compare the first against
   the Gemian time recorded before the boot. A frozen or jumping value
   refutes; agreement within a second confirms and closes the roadmap's
   reload item. Confidence: high.
6. **H6. The RTC alarm fires through MFD interrupt 9 and reaches the RTC
   class device.** Test: in the H5 boot, `rtcwake -m on -s 10` with no system
   suspend and check `/proc/interrupts` and `/sys/class/rtc/rtc0/since_epoch`;
   this exercises `IRQ_EN_ONESHOT_AL` and the `IRQ_STA` read-clear that the
   local IRQ_EN fix touches. Confidence: high once H1 passes.
7. **H7. The Gemini board DT needs explicit rail constraints before
   `regulator_ignore_unused` can be dropped: VCORE and VSRAM_PROC (hardware
   `VOSEL_CTRL`), VDRAM (software enable not authoritative), VS1/VS2 and the
   modem bucks must be `always-on`, and no consumer may change VCORE voltage
   (F8–F10).** Test: offline, write the constraint set from the vendor DT's
   `boot-on`/`always-on` list and the F9/F10 exceptions, then a mainline boot
   that keeps `regulator_ignore_unused` but logs `regulator_summary`; only a
   later reviewed boot removes the flag. Confidence: high for the list,
   medium on whether any further rail (e.g. `vxo22`, `vtcxo24` feeding the
   26 MHz source) is critical.
8. **H8. At kernel entry the loader-left PMIC state already equals most of
   the vendor's 245-field refresh, so mainline needs no init table (F5).**
   The decision-changing subset is small: `TOP_RST_MISC`, `STRUP_CON15`
   (`PWROFF_SEQ_EN`), `TOP_CKPDN_CON0–2`, `BUCK_VCORE_CON0`, `LDO_VDRAM_CON0`,
   `CHR_CON1/6/13`. Test: a mainline boot reading those ten registers through
   the MFD regmap at probe time and diffing against the decoded table; any
   difference becomes a single reviewed write, not a port of the table.
   Confidence: medium.
9. **H9. Mainline `reboot recovery` and `reboot bootloader` have no effect
   on LK's boot-mode selection because nothing writes `RTC_PDN1` (F17).** Not
   a safety problem (the flags are also never corrupted) but a usability
   gap once mainline is the daily system; a later small `reboot-mode`
   style driver could set `FAC_RESET`/`FAST_BOOT`. Test: none now; confirm
   as a side observation of the first mainline `reboot recovery` attempt.
10. **H10. Without the vendor low-battery protection (F7) a mainline session
    on battery relies on the PMIC's hardware UVLO alone.** Keep sessions on
    external power or above the vendor's 3.4 V first threshold until the
    battery step provides a gauge; the charging record's H5 driver is the
    natural home for an `LBAT` threshold. No test now.
11. **H11. A mainline power-off with the cable attached will appear as a
    reboot into LK's charging screen (F20).** Expectation-setting for H2 and
    for anyone judging a power-off result by the display alone; test is part
    of H2(a).

## Consequences for the roadmap (no changes applied here)

- The roadmap's three PMIC-foundation items resolve as: the RTC reload
  question is answered from sibling-chip evidence pending one cheap read test
  (H5); the long-press policy is one register read away (H3) and must be set
  explicitly in the key node because mainline otherwise disables it (F13);
  the reviewed power-off path should be an MT6351 `pwrc` cell reusing
  `mt6323-poweroff`, not PSCI (H2).
- One combined runtime packet can test H1, H5, H6 and H2(a) in a single
  attended mainline boot; H3/H4 need one bounded Gemian read first.
- Regulator constraints (H7) are a prerequisite for ever removing
  `regulator_ignore_unused`, and VCORE must stay off-limits to consumers.
- Nothing here authorises a key-node install, a power-off attempt or any
  PMIC write; those remain reviewed experiments with their own candidates.

## Validation

Documentation-only change: `./scripts/check-repository` and link checks
apply; no kernel build, DT check or device action was performed. Line
numbers were taken from the exact fetched files recorded in
`source-inputs.json`; the decoded init table was produced by a throwaway
script over those files and is not itself a tool of this repository.

## H7 ordering refinement (2026-10-05)

Writing the constraint set before any observation is not write-free. In pinned
Linux 7.1.3, `set_machine_constraints()` calls `_regulator_do_enable()` for
every rail marked `regulator-always-on` or `regulator-boot-on`. The MT6351
regmap update writes only when the enable bit differs, so a rail the loader
left on sees no write, but a rail it left off is switched on. That would turn
on modem bucks with no modem running, and for VDRAM it would set the software
enable that the vendor init clears (F10). `regulator_ignore_unused` would not
prevent these enables.

The order therefore changes. The C1 boot records each regulator's sysfs
`state` with no constraint nodes added. That shows each rail's inherited
enable state without any new PMIC write; the C1 kernel has no debugfs for
`regulator_summary`. Its baseline observer already captures `LDO_VDRAM_CON0` and
`BUCK_VCORE_CON0` before the regulator child probes. The constraint set is then
written so that `always-on` and `boot-on` mark only rails observed on, plus
any rail with a reviewed reason to switch on. VCORE and VSRAM_PROC get no
voltage range, so no consumer can change them.

Correction to F8 and H7: the A53 profiles do not pass `regulator_ignore_unused`;
their forced command line carries only `clk_ignore_unused`. Unused rails are
protected instead because late cleanup ignores rails without a DT node, which
get no status-change permission. Every new rail node that is not
`regulator-always-on` therefore becomes eligible for switch-off at late init
unless a consumer enables it. Add nodes only with that in mind.
