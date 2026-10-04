# Experiment: Gemini GPU (Mali-T880 / MT6797 MFG) reverse engineering

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-04-gemini-gpu-re` |
| Status | `completed` (offline source review; no build, boot or device access) |
| Subsystem | MT6797 MFG power domains and bus protection, MFGPLL and MFG clocks, GPU SRAM LDO, RT5735 VGPU rail, vendor GPU DVFS/EEM, Panfrost integration |
| Device variant | Project Gemini (Gemian `3.18.41+`, MT6797X, Mali-T88x MP4 r1p0, product `0x0880`) |
| Date(s) | 2026-10-04 |
| Investigator(s) | Claude (owner-requested investigation) |
| Tracking issue | Not yet assigned |

## Question

What does the stock Gemian kernel actually do to power, clock, supply and
scale the Mali GPU, and what does that imply for the disabled Panfrost
integration already carried in this repository (patches 0047–0051 and
0058–0059)? The roadmap's
[GPU step](../../docs/ROADMAP.md#after-wi-fi-remaining-driver-gaps) lists the
MFG power domains, the RT5735 VGPU regulator and safe OPPs as prerequisites.
This record answers, from the pinned public vendor source and the pinned Linux
7.1.3 tree, which vendor steps the local patches already reproduce, which ones
they omit, and which values are safe starting points. It follows the format of
the [charging record](../2026-10-04-gemini-charging-re/README.md): verified
facts first, each cited, then ranked hypotheses with a device test. It changes
no patch, profile, candidate or device state.

Earlier records own the live observations this builds on: the
[GPU/Panfrost recovery record](../2026-07-12-mt6797-gpu-panfrost-recovery/README.md)
(runtime GPU identity, live DVFS table, vendor ELF analysis), the
[RT5735 VGPU recovery record](../2026-07-12-rt5735-vgpu-recovery/README.md)
(register contract, live DT) and the
[clock/power/reset recovery record](../2026-07-12-mt6797-clock-power-reset-recovery/README.md)
(SPM register map, live clock summary). Native display and PMIC basics are
investigated in their own 2026-10-04 threads and are only referenced here.

## Inputs

Every vendor citation below is a public GPL file at Gemian commit
`8cfe6596a503612e3332d9c26e292a19525a7f07`, the same commit the charging record
used. Every mainline citation is Linux `7.1.3` as pinned in
`kernel/manifest.json`. Exact paths, sizes and SHA-256 values are in
[`source-inputs.json`](source-inputs.json). The vendor `mt_gpufreq.c` and the
r12p1 `mtk_config_platform.c` hashes are byte-identical to those recorded by the
2026-07-13 [vendor ELF analysis](../2026-07-12-mt6797-gpu-panfrost-recovery/results/mali-vendor-analysis.txt),
so the two records describe the same files. No vendor source, firmware or
private capture is copied into this repository; register offsets, bit positions
and configuration values are cited as facts.

Two caveats apply throughout. First, as in the charging record, the public
board DTS does not necessarily match the live Gemian DTB: the live `vgpu_buck@60`
candidate reported by the 2026-07-12 inventory does not exist in the public
`mt6797.dtsi` or `aeon6797_6m_n.dts` at this commit, so live-DTB values win
where they differ. Second, the Mesa Panfrost documentation could not be fetched
from this session (the session's network policy denies `docs.mesa3d.org`), so
userspace support for T880 is recalled, not re-verified, and is marked as such.

## Part 1: verified facts

### GPU identity, vendor driver configuration and Panfrost model coverage

- **F1. The vendor GPU node and driver build.** `mali@13040000` carries the
  legacy compatibles `arm,malit860`, `arm,mali-t86x`, `arm,malit8xx`,
  `arm,mali-midgard`, a `0x4000` window, three level-low SPIs 264/263/262 named
  `JOB`/`MMU`/`GPU`, `clock-frequency = <700000000>` and thirteen clock handles
  (`MFG_BG3D`, `INFRA_MFG_VCG`, the six SCPSYS MFG handles, `TOP_MUX_MFG_52M`,
  `TOP_UNIVPLL2_D8`, `INFRA_DVFS_SPM1`, `INFRA_I2C_GPUPM`, `INFRA_AP_DMA`); it has
  no supply, reset, OPP or IOMMU property
  ([`mt6797.dtsi` lines 3049–3083](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L3049-L3083)).
  The defconfig selects `CONFIG_MTK_GPU_SUPPORT=y`, `CONFIG_MTK_GPU_VERSION="mali
  midgard r12p1"` and `CONFIG_MTK_GPU_COMMON_DVFS_SUPPORT=y`
  ([`aeon6797_6m_n_defconfig` lines 195–197](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/configs/aeon6797_6m_n_defconfig#L195-L197)).
  In the r12p1 MT6797 platform `Kbuild`, `MTK_GPU_APM`, `MTK_GPU_DPM` and
  `MTK_GPU_OCP` are commented out and `MTK_GPU_SPM` depends on
  `CONFIG_MTK_GPU_SPM_DVFS_SUPPORT`, which the defconfig does not set
  ([`Kbuild` lines 6–9](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/gpu/gpu_mali/mali_midgard/mali-r12p1/drivers/gpu/arm/midgard/platform/mt6797/Kbuild#L6-L9)).
  Consequence: the active vendor path is the plain one, in which the Kbase
  platform callbacks sequence power and the separate `mt_gpufreq` driver owns
  frequency and voltage; every `#ifdef MTK_GPU_SPM`/`APM`/`OCP` block in the
  platform source is dead on this image. The runtime identity (`Mali-T88x MP4
  r1p0`, product `0x0880`, four cores) is unchanged from the
  [GPU recovery record](../2026-07-12-mt6797-gpu-panfrost-recovery/results/runtime-summary.txt).
- **F2. Panfrost 7.1.3 covers the core model; the binding does not yet name
  MT6797.** `GPU_MODEL(t880, 0x880)` is in the model table, and the T86x/T88x
  specific quirks are `SC_LS_ALLOW_ATTR_TYPES` and, for revision ≥ `0x2000`
  only, the job-throttle limit
  ([`panfrost_gpu.c` lines 134, 158–160, 220](https://github.com/gregkh/linux/blob/v7.1.3/drivers/gpu/drm/panfrost/panfrost_gpu.c#L134)).
  The binding accepts `arm,mali-t880` only behind `samsung,exynos8890-mali`,
  one or two clocks named `core`/`bus`, one `mali-supply`, one `power-domains`
  entry, one or two `resets` and an OPP table
  ([`arm,mali-midgard.yaml` lines 55–58, 67–78, 83–90](https://github.com/gregkh/linux/blob/v7.1.3/Documentation/devicetree/bindings/gpu/arm,mali-midgard.yaml#L55-L90)).
  Local [patch 0058](../../patches/v7.1.3/0058-drm-panfrost-add-MT6797-platform-data.patch)
  adds `mediatek,mt6797-mali` with four named domains and relaxes
  `power-domains` to five. Mesa's Panfrost driver supports Midgard T760 and
  newer, which includes T860/T880, with OpenGL ES 3.1 (recalled, not
  re-verified in this session; see Inputs).

### MFG power domains and bus protection

- **F3. The active vendor MTCMOS driver is `clk-mt6797-pg.c`; the legacy
  `mt_spm_mtcmos.c` is dead code.** The base power `Makefile` has
  `mt_spm_mtcmos.o` commented out
  ([line 42](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/base/power/mt6797/Makefile#L42)),
  and that legacy file's `spm_mtcmos_ctrl_mfg()` uses the MT8173-era
  `SPM_MFG_PWR_CON 0x214` with status bit 4
  ([`mt_spm_mtcmos.c` lines 1117, 1560–1625](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/base/power/mt6797/mt_spm_mtcmos.c#L1560-L1625)),
  which does not match MT6797 and must not be used as evidence. The CCF
  power-gate driver defines `MFG_ASYNC_PWR_CON 0x334`, `MFG_PWR_CON 0x338`,
  `MFG_SRAM_CON 0x33c`, `MFG_CORE0..3_PWR_CON 0x340–0x34c`, status bits
  13/12/11/10/9/8, MFG SRAM power-down bits 1:0 with ack bits 17:16, and core
  SRAM power-down bit 8 (in each core's own `PWR_CON`) with ack bits 20–23 in
  `MFG_SRAM_CON`
  ([`clk-mt6797-pg.c` lines 139–145, 206–211, 231–240](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/clk/mediatek/clk-mt6797-pg.c#L139-L145);
  routines at [lines 933–1013](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/clk/mediatek/clk-mt6797-pg.c#L933-L1013)
  for core3, [1258–1342](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/clk/mediatek/clk-mt6797-pg.c#L1258-L1342)
  for MFG and [1344–1405](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/clk/mediatek/clk-mt6797-pg.c#L1344-L1405)
  for MFG_ASYNC). Local
  [patch 0047](../../patches/v7.1.3/0047-pmdomain-mediatek-add-MT6797-MFG-domains.patch)
  encodes exactly these offsets, masks and the async → mfg → core0..3
  hierarchy.
- **F4. Register write order differs slightly from generic mainline SCPSYS, and
  the vendor itself uses both orders.** Vendor power-off of a core domain writes
  `SRAM_PDN=1`, waits for the ack, then `PWR_CLK_DIS=1`, `PWR_ISO=1`,
  `PWR_RST_B=0`, `PWR_ON=0`, `PWR_ON_2ND=0`; power-off of MFG writes `SRAM_PDN`,
  then `PWR_ISO=1`, `PWR_CLK_DIS=1`, `PWR_RST_B=0`, `PWR_ON=0`, `PWR_ON_2ND=0`
  (`clk-mt6797-pg.c` lines 944–960 and 1268–1285). Power-on is identical in all
  vendor routines and in mainline: `PWR_ON`, `PWR_ON_2ND`, wait for both status
  registers, `PWR_CLK_DIS=0`, `PWR_ISO=0`, `PWR_RST_B=1`, `SRAM_PDN=0`, wait for
  the ack. Mainline `scpsys_power_off()` orders `ISO=1`, `RST_B=0`,
  `CLK_DIS=1`, `ON=0`, `ON_2ND=0`
  ([`mtk-scpsys.c` lines 311–357, 361–400](https://github.com/gregkh/linux/blob/v7.1.3/drivers/pmdomain/mediatek/mtk-scpsys.c#L311-L400)),
  i.e. the MFG order. Inference, not fact: because the vendor applies the
  mainline order to MFG and the other order to the cores, the difference is
  unlikely to matter; it is recorded so a future hang is not misattributed.
- **F5. MFG bus protection is performed by the vendor Mali platform driver,
  not by the MTCMOS driver, and the local patches omit it.** In the power-gate
  driver the MFG protect/unprotect code is commented out
  ([`clk-mt6797-pg.c` lines 453–456](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/clk/mediatek/clk-mt6797-pg.c#L453-L456)).
  The Kbase platform code instead defines `MFG_PROT_MASK = BIT(21) | BIT(23)`
  and calls `spm_topaxi_protect()`, which sets or clears those bits in
  `INFRA_TOPAXI_PROTECTEN` (`0x10001220`) and polls `INFRA_TOPAXI_PROTECTSTA1`
  (`0x10001228`): protection is asserted once at platform init, asserted before
  every power-off, and released 100 µs after the last MFG clock enable on
  every power-on
  ([`mtk_config_platform.c` lines 42, 301–302, 389, 727](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/gpu/gpu_mali/mali_midgard/mali-r12p1/drivers/gpu/arm/midgard/platform/mt6797/mtk_config_platform.c#L281-L302);
  [`clk-mt6797-pg.c` lines 169–171, 400–440](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/clk/mediatek/clk-mt6797-pg.c#L400-L440)).
  Mainline SCPSYS implements the same mechanism through `bus_prot_mask` and
  `mtk_infracfg_set_bus_protection()` on the same offsets
  ([`infracfg.h` lines 442–443](https://github.com/gregkh/linux/blob/v7.1.3/include/linux/soc/mediatek/infracfg.h#L442-L443),
  [`mtk-scpsys.c` lines 279–300](https://github.com/gregkh/linux/blob/v7.1.3/drivers/pmdomain/mediatek/mtk-scpsys.c#L279-L300)),
  and the MT8173 data names bit 21 `MFG_M0` and bit 23 `MFG_SNOOP_OUT` on its
  MFG domain ([`infracfg.h` lines 407–416](https://github.com/gregkh/linux/blob/v7.1.3/include/linux/soc/mediatek/infracfg.h#L407-L416)).
  Patch 0047 sets no `bus_prot_mask` on any MT6797 MFG domain. This corrects the
  earlier records' reading that "no bus-protect bit is inferred": the MTCMOS
  driver does not execute it, but the GPU driver does.
- **F6. The 52 MHz pre-clock is reproduced; its parent and the `INFRA_MFG_VCG`
  gate are not.** Every MFG power gate names `mfg_52m_sel` as its `pre_clk`,
  prepared before and released after each switch
  ([`clk-mt6797-pg.c` lines 2417–2440, 2530–2535](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/clk/mediatek/clk-mt6797-pg.c#L2530-L2535));
  local [patch 0050](../../patches/v7.1.3/0050-pmdomain-mediatek-use-MT6797-MFG-52MHz-preclock.patch)
  does the same through `CLK_MFG_52M`. In addition the Mali platform init
  re-parents `mfg_52m_sel` to `univpll2_d8` (`mtk_config_platform.c` lines
  661–662, 714–716), and every power-on enables `infra_mfg_vcg` ("mfg52m-vcg",
  infracfg gate bit 14 fed by `mfg_52m_sel`) first and disables it last
  (lines 288, 401; [`clk-mt6797.c` line 535](https://github.com/gregkh/linux/blob/v7.1.3/drivers/clk/mediatek/clk-mt6797.c#L535)).
  Mainline `mfg_52m_sel` (CLK_CFG `0x104` bits 2:1) has parents `clk26m`,
  `univpll2_d8`, `univpll2_d4`, `univpll2_d4`
  ([lines 305–310, 378–379](https://github.com/gregkh/linux/blob/v7.1.3/drivers/clk/mediatek/clk-mt6797.c#L305-L310));
  the local DT assigns no parent and the Panfrost node has no `bus` clock. The
  2026-07-12 live clock summary reported `mfg_52m_sel`/`infra_mfg_vcg` at
  156 MHz, which is `univpll2_d4` (1248 MHz / 2 / 4), not the 78 MHz
  `univpll2_d8` the source selects; the discrepancy is unexplained (H5).
- **F7. The vendor programs GPU SRAM LDO controls in INFRACFG_AO that mainline
  never touches.** `mt_gpufreq_ext_ic_init()` maps `GPU_LDO_BASE 0x10001000`
  and writes `0xfc0 = 0x0f0f0f0f`, `0xfc4 = 0x0f0f0f0f`, `0xfbc = 0xff`
  ([`mt_gpufreq.c` lines 211, 2712–2725](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/base/power/mt6797/mt_gpufreq.c#L2712-L2725));
  the Mali platform init writes `0xfd8 = 0x88888888`, `0xfe4 = 0x8` (vendor
  comment "RG_GPULDO_RSV_H_0-8 = 0x8"), `0xfc0 = 0xfc4 = 0x0f0f0f0f`,
  `0xfc8 = 0x0f`
  ([`mtk_config_platform.c` lines 707–712](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/gpu/gpu_mali/mali_midgard/mali-r12p1/drivers/gpu/arm/midgard/platform/mt6797/mtk_config_platform.c#L707-L712));
  and every GPU power-on writes `0xfbc = 0x1ff` before enabling VGPU while
  every power-off writes `0xfbc = 0` after disabling it (lines 285, 404). The
  vendor's debug dump labels the `0x10001fc0` window "LDO" (lines 148–175).
  Mainline 7.1.3 has no consumer of these registers; `infracfg` is a plain
  syscon in the MT6797 DTS.
- **F8. The vendor writes four G3D-config registers at power-on and polls an
  idle flag at power-off.** Power-on sets `0x13000000 + 0x1c |= async_value`,
  where `async_value` is `0xa` if the DVFS table's top frequency is ≥ 780 MHz
  and `0x5` otherwise, then writes `0xffffffff` to `0x3e0`, `0x3e4`, `0x3e8`,
  `0x3ec`, `0x3f0` ("enable PMU")
  ([`mtk_config_platform.c` lines 313–320, 684](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/gpu/gpu_mali/mali_midgard/mali-r12p1/drivers/gpu/arm/midgard/platform/mt6797/mtk_config_platform.c#L313-L320)).
  Power-off writes `MFG_DEBUG_SEL (0x180) = 3` and waits up to 100 000 µs for
  `MFG_DEBUG_A (0x184)` bit 2 (idle) before touching clocks
  (lines 358–366; [`mtk_kbase_spm.h` lines 71–73](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/gpu/gpu_mali/mali_midgard/mali-r12p1/drivers/gpu/arm/midgard/platform/mt6797/mtk_kbase_spm.h#L71-L73)).
  The `MFG_BG3D` gate at set/clear/status `0x4`/`0x8`/`0x0` is unchanged from the
  clock/power record and is what local
  [patch 0048](../../patches/v7.1.3/0048-clk-mediatek-add-MT6797-MFGSYS.patch) exposes.
  Mainline Panfrost writes none of the `0x13000000` block.
- **F9. The only reset the vendor applies in the normal path is a one-shot
  TOPRGU `MFG_RST` pulse at platform init.** `toprgu_mfg_reset()` sets and,
  1 µs later, clears `MTK_WDT_SWSYS_RST_MFG_RST = 0x0004` through
  `mtk_wdt_swsysret_config()` and is called once from `mtk_platform_init()`,
  after the LDO and mux writes and before bus protection is asserted
  ([`mtk_config_platform.c` lines 271–278, 724–727](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/gpu/gpu_mali/mali_midgard/mali-r12p1/drivers/gpu/arm/midgard/platform/mt6797/mtk_config_platform.c#L271-L278)).
  The `0x0c` G3D-config reset write (`3` then `0`) exists only under
  `MTK_MT6797_DEBUG` and has no caller in the normal path (lines 243–248).
  Mainline `mtk_wdt` registers a TOPRGU reset controller only for compatibles
  with match data; `mediatek,mt6589-wdt`, the fallback the MT6797 DTS uses, has
  none, so no reset provider exists for the MFG line
  ([`mtk_wdt.c` lines 452–456, 495–502](https://github.com/gregkh/linux/blob/v7.1.3/drivers/watchdog/mtk_wdt.c#L452-L456)).
  Panfrost takes an optional reset array and asserts/deasserts it at
  runtime-PM transitions only with the `GPU_PM_RT` feature
  ([`panfrost_device.c` lines 22–36, 418–473](https://github.com/gregkh/linux/blob/v7.1.3/drivers/gpu/drm/panfrost/panfrost_device.c#L418-L473)).

### MFGPLL, the MFG mux and frequency changes

- **F10. The vendor DVFS driver programs MFGPLL directly, parking the MFG mux on
  26 MHz when the post-divider changes.** `mt_gpufreq_dds_calc()` computes
  `dds = ((kHz/100 × postdiv × 2) × 16384 / 26 + 5) / 10` for `postdiv` ∈
  {1, 2, 4} and writes `0x80000000 | (postdiv_code << 24) | dds` to
  `MFGPLL_CON1`, with `postdiv_code` 1/2/3 for ÷2/÷4/÷8; if the post-divider
  field (bits 26:24) changes, `mfg_sel` is first switched to `clk_sub_parent`
  (`clk26m`), the PLL is written, 20 µs elapse, and the mux returns to
  `clk_main_parent` (`mfgpll_ck`)
  ([`mt_gpufreq.c` lines 1489–1543](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/base/power/mt6797/mt_gpufreq.c#L1489-L1543);
  [`mt_gpufreq.h` lines 20–24](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/base/power/mt6797/mt_gpufreq.h#L20-L24);
  `gpufreq` DT node with `clk_mux = TOP_MUX_MFG`, `clk_main_parent =
  TOP_MFGPLL_CK`, `clk_sub_parent = clk26m` at
  [`mt6797.dtsi` lines 3968–3978](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L3968-L3978)).
  The post-divider scheme depends on the efuse speed bounding (`cid`, F18):
  `cid 0` always ÷2; `cid 1` ÷2 at ≥ 500 MHz, ÷4 at ≥ 250 MHz, ÷8 at ≥ 125 MHz;
  `cid 2–4` ÷4 at ≥ 250 MHz, ÷8 below (lines 1546–1570). The current frequency
  is read back from `MFGPLL_CON1` (lines 1680–1698). Mainline describes
  `mfgpll` as a standard MediaTek PLL at `0x240` with PCW at `0x244` bits 20:0
  (21 bits) and the post-divider at `0x244` bit 24
  ([`clk-mt6797.c` lines 631–632](https://github.com/gregkh/linux/blob/v7.1.3/drivers/clk/mediatek/clk-mt6797.c#L631-L632)),
  the same fields the vendor writes, so CCF `clk_set_rate()` on `mfgpll` can
  reproduce the programming; the generic PLL driver does not park the consumer
  mux.
- **F11. The mainline MFG clock tree cannot propagate a rate request yet.**
  `mfg_sel` (CLK_CFG `0x50` bits 25:24, gate bit 31) has parents `clk26m`,
  `mfgpll_ck`, `syspll_d3`, `univpll_d3` and no `CLK_SET_RATE_PARENT`
  ([`clk-mt6797.c` lines 143–148, 336](https://github.com/gregkh/linux/blob/v7.1.3/drivers/clk/mediatek/clk-mt6797.c#L336)),
  and the local `mfg_bg3d` gate is a plain `GATE_MTK` on `mfg_sel`
  (patch 0048). Panfrost's devfreq calls `dev_pm_opp_set_rate()` on its single
  `core` clock ([`panfrost_devfreq.c` lines 35–43](https://github.com/gregkh/linux/blob/v7.1.3/drivers/gpu/drm/panfrost/panfrost_devfreq.c#L35-L43)),
  so with the pinned flags an OPP table with more than the boot frequency
  cannot be applied; a single fixed operating point that equals the rate the
  tree already runs at is the only form that works unchanged.
- **F12. Vendor ordering of a frequency/voltage change.** Going up, voltage is
  raised first and the clock switched second; going down, the clock is switched
  first ([`mt_gpufreq.c` lines 1853–1872](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/base/power/mt6797/mt_gpufreq.c#L1853-L1872)).
  After a voltage increase the driver waits `ΔmV × 10 / slew_rate + 1` µs plus
  a fixed 350 µs, with the slew rate read from the RT5735 (lines 952–998,
  1670–1675); after a VGPU enable it waits 350 µs (`EXTIC_VOLT_ON_OFF_DELAY_US`,
  lines 226, 1071). The mainline OPP core applies the same voltage-then-clock
  ordering (standard OPP behaviour, not re-cited here); the RT5735 waits are
  the regulator driver's responsibility (F15, H8).

### VGPU rail: RT5735 on I2C7

- **F13. Node, bus and board data.** The RT5735 node is in the SoC-level
  `mt6797.dtsi`, not the board file: `i2c7@11010000` (clocks `INFRA_I2C_GPUPM`,
  `INFRA_AP_DMA`, property `mediatek,gpupm_used`) contains `rt5735@1c` with
  compatible `rt,rt5735-regulator`, `rt,dvs_up = <0x6>`, `rt,dvs_down = <0x1>`,
  `rt,ioc = <0x1>`, `rt,tpwth = <0x2>` and `rt,rearm`
  ([`mt6797.dtsi` lines 2549–2573](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L2549-L2573));
  `aeon6797_6m_n.dts` adds nothing for I2C7, the RT5735 or a `vgpu_buck`. The
  PMIC's `buck_vgpu` is described `regulator-always-on`, `regulator-boot-on`,
  0.6–1.39375 V (lines 429–436) but is not the GPU supply: `mt_gpufreq.c`
  selects `VGPU_SET_BY_EXTIC`
  ([line 111](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/base/power/mt6797/mt_gpufreq.c#L111)).
  Mainline `mt6797.dtsi` has `i2c7@11010000` on the same clocks, disabled
  ([lines 362–375](https://github.com/gregkh/linux/blob/v7.1.3/arch/arm64/boot/dts/mediatek/mt6797.dtsi#L362-L375));
  local [patch 0051](../../patches/v7.1.3/0051-regulator-add-Richtek-RT5735-VSEL0-support.patch)
  adds a disabled `regulator@1c`.
- **F14. Register map and vendor initial configuration.** From
  [`rt5735.h` lines 7–45](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/power/mt6797/rt5735.h#L7-L45):
  `PID 0x03` (value `0x10`), `RID 0x04`, `FID 0x05`, `VID 0x06`,
  `PROGVSEL1 0x10`, `PROGVSEL0 0x11` (bit 7 enable, bits 6:0 code,
  600 mV + 6.25 mV × code, 0.6–1.39375 V; `rt5735.c` lines 250–278),
  `PGOOD 0x12` (bit 4 active discharge, bit 1 PGDVS, bit 0 PGDCDC),
  `TIME 0x13` (bits 4:2 DVS-up slew), `COMMAND 0x14` (bit 7 VSEL0 forced PWM,
  bit 6 VSEL1 forced PWM, bit 5 DVS mode), `LIMCONF 0x16` (bits 7:6 IOC,
  bits 5:4 TPWTH, bits 2:1 DVS-down slew, bit 0 REARM). Slew decoding: DVS-up
  code 0 → 64, 1 → 16, 2/6 → 32, 3/7 → 8, 4/5 → 4 mV/µs; DVS-down code
  0 → 32, 1 → 4, 2 → 8, 3 → 16 mV/µs (lines 355–405). At probe the vendor
  writes `PGOOD = 0x00`, `TIME = 0x19`, `COMMAND = 0x01`, `LIMCONF = 0x63`
  (defaults at lines 46–51 merged with the DT values; `rt5735_chip_init`,
  lines 749–757), i.e. DVS-up 32 mV/µs, DVS-down 4 mV/µs, IOC 1, TPWTH 2,
  REARM on, discharge off. Then `mt_gpufreq_ext_ic_init()` sets VSEL0 to
  1.000 V, enables it and programs DVS-up 32 mV/µs again
  ([`mt_gpufreq.c` lines 2726–2729](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/base/power/mt6797/mt_gpufreq.c#L2726-L2729)).
  Patch 0051's driver agrees on PID, VSEL0, the enable bit, the step and the
  discharge bit; it declares no `enable_time`, no `ramp_delay` and writes no
  protection registers.
- **F15. VGPU is switched off whenever the vendor GPU is powered down.**
  `mt_gpufreq_voltage_enable_set()` sets or clears `PROGVSEL0` bit 7, waits
  350 µs, reads it back and calls `BUG()` if the readback disagrees
  ([`mt_gpufreq.c` lines 1013–1146](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/base/power/mt6797/mt_gpufreq.c#L1013-L1146));
  the Mali power-on callback calls it with 1 as its second step and the
  power-off callback with 0 as its second-to-last step (F21). This is why the
  2026-07-12 capture saw "voltage control disabled, voltage 0" with the GPU
  idle: `_mt_gpufreq_get_cur_volt()` returns 0 when the VSEL0 enable bit is
  clear (lines 1700–1728). Mainline Panfrost's `default_data` keeps
  `mali-supply` enabled from probe onward (enabled either by
  `panfrost_regulator_init()` or by the OPP core) and only the MT8183-style
  `GPU_PM_VREG_OFF` feature turns it off, during system suspend
  ([`panfrost_device.c` lines 87–118, 242–247](https://github.com/gregkh/linux/blob/v7.1.3/drivers/gpu/drm/panfrost/panfrost_device.c#L87-L118);
  [`panfrost_drv.c` lines 1073–1116](https://github.com/gregkh/linux/blob/v7.1.3/drivers/gpu/drm/panfrost/panfrost_drv.c#L1073-L1116)).
- **F16. The vendor probe carries two hazards mainline must not inherit.**
  Before the first I2C transfer the probe bit-bangs nine SCL pulses on the I2C7
  pins (vendor GPIO 153/154) to recover a stuck SDA
  ([`rt5735.c` lines 762–796, 815](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/power/mt6797/rt5735.c#L762-L830));
  if the product-ID read then still fails it calls `battery_disable_batfet()`
  (line 827), the BQ25896 `BATFET_DIS` write the charging record's F14
  describes, which disconnects the battery. A product-ID mismatch returns
  `-ENODEV` (line 828). A shutdown-time bit-bang also exists (lines 459–580).
  Patch 0051 does none of this, which is the correct boundary.
- **F17. EEM encodes RT5735 voltages as 600 mV + 6.25 mV steps, and the live
  table is consistent with that.** `mt_eem.c` defines
  `GPU_PMIC_BASE_RT5735 = 60000`, `GPU_PMIC_STEP_RT5735 = 625` and separate
  16-entry RT5735 code tables per speed bin
  ([lines 581–597, 1156–1157](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/base/power/mt6797/mt_eem.c#L1155-L1160)),
  while the GPU detector entry still points at the FAN53555 constants
  `GPU_PMIC_BASE 60300`/`STEP 1282` (lines 1898–1899); `mt_gpufreq_update_volt()`
  decodes the codes it receives with the RT5735 formula when that part is
  present (`mt_gpufreq.c` lines 846–872, 1232–1263). The seven live table
  voltages from the 2026-07-12 capture (1.1125, 1.06875, 1.0125, 0.975,
  0.93125, 0.90625, 0.84375 V) are all `600 mV + 6.25 mV × n` with `n` = 82,
  75, 66, 60, 53, 49, 39, so the running binary applies the RT5735 encoding at
  least in the final decode.

### Vendor DVFS table, efuse selection and EEM

- **F18. The live table type 12 is the "plus" table, selected by efuse
  function code 4.** `mt_gpufreq_get_dvfs_table_type()` reads `func_code_1 =
  devinfo[22] & 0xf` and `ptp_version = (devinfo[61] >> 4) & 0xf`; type 12 is
  chosen when `func_code_1 == 4`
  ([`mt_gpufreq.c` lines 582–620](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/base/power/mt6797/mt_gpufreq.c#L582-L620)),
  and type 12 maps to `mt_gpufreq_opp_plus_tbl_e1_1` (lines 2901–2903):
  900 MHz / 1.1545 V, 780 / 1.1032, 610 / 1.0134, 520 / 0.975, 442.5 / 0.9365,
  365 / 0.9108, 238 / 0.8467 (lines 135–182, 317–325). The frequencies match
  the live table exactly; the live voltages are lower because EEM has
  recalibrated them (F17, F19). A second efuse field, `gpu_speed_bounding =
  (devinfo[8] >> 8) & 0xf`, sets `cid` (0 free-run, 1 800M, 2 700M, 3 600M,
  4 and 12–15 500M) and with it the PLL post-divider scheme (F10)
  (lines 621–651); its live value is unknown. `devinfo[]` is the array the
  loader passes in the flattened DT `/chosen` property `atag,devinfo`, exposed
  through the `/dev/devmap` ioctl `READ_DEV_DATA`
  ([`devinfo.c` lines 72–97, 196–200, 261, 283–295](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/devinfo/v1/devinfo.c#L283-L295));
  words 12 onward include the HRID, so the raw array is device-identifying.
- **F19. EEM (PTPOD) owns the GPU voltage table, and the vendor runs a fixed
  point until it is ready.** The GPU detector has features `INIT01 | INIT02 |
  MON`, `max_freq 850 MHz`, `VBOOT 1.0006 V`, limits `VMAX 1.15 V` /
  `VMIN 0.80 V`, `DVTFIXED 0x5`, `VCO 0x10`
  ([`mt_eem.c` lines 1888–1899, 1166–1167, 1178, 1187](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/base/power/mt6797/mt_eem.c#L1888-L1899)),
  reads its calibration from `devinfo[50–53, 56–61, 65, 66]` (lines
  4881–4892) and pushes eight codes through `set_volt_gpu()` →
  `mt_gpufreq_update_volt()` (lines 2809–2830). The `eem_fsm@1100b000` node
  (SPI 129) consumes `MFG_BG3D`, `SCP_SYS_MFG` and `INFRA_THERM`
  ([`mt6797.dtsi` lines 2503–2509](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/arch/arm64/boot/dts/mt6797.dtsi#L2503-L2509)),
  so EEM powers the MFG domain itself during calibration. Until EEM reports
  ready, `mt_gpufreq_disable_by_ptpod()` holds the first table entry whose
  default voltage is ≤ `GPU_DVFS_PTPOD_DISABLE_VOLT = 1.0006 V` and runs it at
  1.0006 V (`mt_gpufreq.c` lines 182, 1168–1199); for the type-12 table that
  entry is **520 MHz**, so every stock boot runs the GPU at 520 MHz / 1.0006 V
  before calibration. The Kbase early init defers until EEM and the external
  buck are both ready (`mtk_config_platform.c` lines 474–494). Mainline has no
  MT6797 SVS/EEM driver; Panfrost reads an optional nvmem cell `speed-bin`
  into `opp-supported-hw`
  ([`panfrost_devfreq.c` lines 95–117](https://github.com/gregkh/linux/blob/v7.1.3/drivers/gpu/drm/panfrost/panfrost_devfreq.c#L95-L117)),
  and the mainline `mt6797.dtsi` has no efuse node.
- **F20. Vendor power model and limiters.** The dynamic power reference is
  1169 mW at 800 MHz and 1.0 V with a constant 71 mW leakage term
  ([`mt_gpufreq.c` lines 759–786](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/base/power/mt6797/mt_gpufreq.c#L759-L786)),
  which in the binding's `dynamic-power-coefficient` unit (µW/MHz/V²,
  [`arm,mali-midgard.yaml` lines 90–102](https://github.com/gregkh/linux/blob/v7.1.3/Documentation/devicetree/bindings/gpu/arm,mali-midgard.yaml#L90-L102))
  is 1169000 / 800 ≈ **1461**. Thermal, PBM and low-battery limiters cap the
  OPP index (`mt_gpufreq_thermal_protect` line 2388,
  `mt_gpufreq_set_power_limit_by_pbm` line 2462, low-battery callbacks lines
  2252–2380); the low-battery limit is 442.5 MHz (lines 2130–2140).

### The complete vendor GPU power sequence versus Panfrost

- **F21. Vendor power-on and power-off, in order.** Power-on
  ([`mtk_config_platform.c` lines 281–348](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/gpu/gpu_mali/mali_midgard/mali-r12p1/drivers/gpu/arm/midgard/platform/mt6797/mtk_config_platform.c#L281-L348)):
  `0x10001fbc = 0x1ff` → VGPU enable (+350 µs) → `infra_mfg_vcg` →
  MTCMOS `mfg_async` → `mfg` → `mfg_core0..3` (each with the 52 MHz pre-clock)
  → `mfg_bg3d` → 100 µs → release bus protection bits 21|23 → `0x1c` timing →
  PMU enables. Power-off (lines 350–405): poll MFG idle → assert bus protection
  → `mfg_bg3d` off → cores → `mfg` → `mfg_async` → `infra_mfg_vcg` off → VGPU
  disable → `0x10001fbc = 0`. One-time init (lines 623–731): map five
  compatibles, get clocks, set voltage bounds 1150/850 mV and the frequency
  bounds from the DVFS table, LDO writes (F7), `mfg_52m_sel` → `univpll2_d8`,
  TOPRGU MFG reset (F9), assert bus protection. Mainline Panfrost with the
  local patches: `panfrost_device_init()` attaches the four named domains with
  `DL_FLAG_PM_RUNTIME | DL_FLAG_RPM_ACTIVE` device links (so genpd powers
  `mfg_async` → `mfg` → cores, with the SRAM and pre-clock handling of patches
  0047/0050), optionally deasserts resets, enables `core` and optional `bus`
  clocks, sets up devfreq/OPP or enables `mali-supply`, then resets the GPU
  ([`panfrost_device.c` lines 143–257](https://github.com/gregkh/linux/blob/v7.1.3/drivers/gpu/drm/panfrost/panfrost_device.c#L143-L257));
  runtime PM autosuspends after 50 ms
  ([`panfrost_drv.c` lines 991–995](https://github.com/gregkh/linux/blob/v7.1.3/drivers/gpu/drm/panfrost/panfrost_drv.c#L991-L995)),
  which powers the domains down through the links but, without `GPU_PM_RT`,
  leaves the clocks enabled and, in every configuration, leaves VGPU on. The
  mainline sequence therefore lacks, relative to the vendor: the LDO reserve
  writes (F7), the bus-protection handshake (F5), the `infra_mfg_vcg` gate and
  mux parent (F6), the G3D-config timing/PMU writes (F8), the TOPRGU reset
  (F9) and the VGPU off-at-idle behaviour (F15).

### This repository

- **F22. Current state of the local integration.** Patches 0047–0050 provide the
  six-domain SCPSYS hierarchy with separate SRAM offsets and the 52 MHz
  pre-clock, a `mediatek,mt6797-mfgsys` gate provider and a disabled
  `syscon@13000000`; patch 0051 the disabled RT5735 provider; patches 0058–0059
  the `mediatek,mt6797-mali` platform data and a disabled `gpu@13040000` with
  `clocks = <&mfgsys CLK_MFG_BG3D>` (`core`), the four core domains and
  `mali-supply = <&rt5735_vgpu>`, no OPP table, no reset, no `bus` clock
  ([patch 0059](../../patches/v7.1.3/0059-arm64-dts-mediatek-add-disabled-MT6797-Panfrost-node.patch)).
  `configs/gemini.fragment` enables `COMMON_CLK_MT6797_MFGSYS` and
  `REGULATOR_RT5735` (lines 20, 52) but contains no `CONFIG_DRM`,
  `CONFIG_DRM_PANFROST` or `CONFIG_PM_DEVFREQ`, and the handoff fragment
  states `# CONFIG_DRM is not set` (`configs/gemini-handoff.fragment` line 181),
  so the current `full` profile does not build Panfrost; the 2026-07-14
  package audit that found `panfrost.ko` refers to an earlier package. Base
  mainline 7.1.3 has only `mfg_async` for MT6797 with `CLK_MFG` as its clock
  ([`mtk-scpsys.c` lines 797–803](https://github.com/gregkh/linux/blob/v7.1.3/drivers/pmdomain/mediatek/mtk-scpsys.c#L797-L803))
  and no MT6797 entry in the newer `mtk-pm-domains` driver
  ([`mtk-pm-domains.c` lines 1164–1169](https://github.com/gregkh/linux/blob/v7.1.3/drivers/pmdomain/mediatek/mtk-pm-domains.c#L1164-L1169)).

## Part 2: hypotheses, ranked by value per device minute

Each hypothesis states what would confirm or refute it and the cheapest test.
"Offline" means a patch, compile, DT-check or binding-check in the normal build
flow; "Gemian read" means one bounded, read-only inspection of the running
stock kernel over the known-good LAN SSH path under the existing standing
authorization; "mainline boot" means a new reviewed experiment with its own
candidate, hypothesis, decision branches and stop conditions, and for the GPU
specifically with a serial console or pstore path so an MFG bus hang is
attributable. None is admitted by this record.

1. **H1. The MFG domain needs `bus_prot_mask = BIT(21) | BIT(23)` in patch
   0047, and without it the first MFG access after a power cycle can hang the
   AXI fabric (F5).** The vendor asserts these INFRA_TOPAXI bits around every
   power transition and MT8173 mainline puts the equivalent bits on its MFG
   domain. Test: offline, add the mask to `MT6797_POWER_DOMAIN_MFG` (mainline
   handles it after SRAM power-up on the way on and before SRAM power-down on
   the way off, matching the vendor order); then, in the H3 boot, read
   `0x10001228` bits 21/23 with the GPU runtime-suspended (expect set) and
   active (expect clear). Confidence: high that it is harmless, medium that it
   is required for stability.
2. **H2. The GPU SRAM LDO controls at `0x10001fbc–0x10001fe4` must hold the
   vendor values before the MFG and core SRAMs power up, and the retained
   loader does not set them (F7).** If true, mainline needs a small
   infracfg-syscon write before the MFG domain powers on (the reserve
   register `0xfbc` is toggled per power cycle by the vendor; `0xfc0`,
   `0xfc4`, `0xfc8`, `0xfd8`, `0xfe4` are set once). Test, in order: (a) Gemian
   read of those six words while the stock GPU is idle (expect `0xfbc = 0`,
   `0xfc0 = 0xfc4 = 0x0f0f0f0f`, `0xfc8 = 0x0f`, `0xfd8 = 0x88888888`,
   `0xfe4 = 0x8`) and, if the owner is willing, once more during a short GPU
   load (expect `0xfbc = 0x1ff`); (b) in the H3 boot, read the same words
   before Panfrost probes. If (b) shows them at reset values, the SRAM
   power-down ack poll in `scpsys_sram_enable()` is the expected failure mode
   (timeout, `-ETIMEDOUT` in `scpsys_power_on`). Confidence: medium that they
   are required; high that the two reads decide it.
3. **H3. A first mainline GPU boot can use a single fixed operating point of
   520 MHz at 1.000 V, the point the stock kernel itself runs on every boot
   before calibration (F19), with the clock tree left at the rate CCF reports
   and VGPU enabled by Panfrost's regulator init (F15), no OPP table and no
   devfreq.** Prerequisites: H1 applied, H2 answered, `CONFIG_DRM`,
   `CONFIG_DRM_PANFROST` and the GPU, `mfgsys`, `i2c7` and `regulator@1c`
   nodes enabled in a named profile (not `gemini.fragment`), the RT5735 node
   given `regulator-min/max-microvolt = <1000000>` so the regulator core
   cannot be asked for anything else. Test: read `clk_summary` for `mfgpll`,
   `mfg_sel`, `mfg_bg3d` before the probe (the 2026-07-12 live summary showed
   `mfgpll` at 500.5 MHz under Gemian, but the loader's value under mainline is
   unknown); if the rate is above 520 MHz, add `assigned-clock-rates` for
   `mfgpll` (≤ 520 MHz) or park `mfg_sel` on `syspll_d3`/`univpll_d3` first.
   Then confirm the Panfrost probe line reports `mali-t880` with product
   `0x880`, no MMU or GPU fault, `/dev/dri/renderD*` present, and that runtime
   suspend/resume (idle for 50 ms, then `cat` a sysfs attribute that resumes
   the device) cycles the four domains without an SCPSYS timeout. A render-only
   GLES test waits for a userspace image and for native display; probe plus
   power cycling is the decision-changing measurement. Stop conditions: any
   SCPSYS ack timeout, any `INFRA_TOPAXI` poll timeout, loss of console.
   Confidence: medium.
4. **H4. The TOPRGU `MFG_RST` line (SWSYSRST bit 2) should be exposed as a
   mainline reset and listed in the GPU node, and the vendor's one-shot pulse
   is what leaves the GPU in a known state after the loader (F9).** Test:
   offline, add an MT6797 entry to `mtk_wdt` with `toprgu_sw_rst_num` and give
   the GPU `resets = <&watchdog 2>`; Panfrost deasserts it at init. On device,
   compare the H3 probe with and without the property only if the first probe
   reports a GPU fault or a hung soft-reset (`panfrost_gpu_soft_reset`
   timeout). Confidence: medium that it matters; the loader's Mali state is
   unknown.
5. **H5. The `mfg_52m_sel` parent and the `infra_mfg_vcg` gate matter for the
   MFG SRAM/async handshake, and the live 156 MHz reading means the parent is
   `univpll2_d4`, not the `univpll2_d8` the source sets (F6).** Test: Gemian
   read of CLK_CFG `0x10000104` bits 2:1 and `/sys/kernel/debug/clk/mfg_52m_sel`
   under the stock kernel settles the parent; offline, add
   `assigned-clocks`/`assigned-clock-parents` for `mfg_52m_sel` to the observed
   parent and give the Panfrost node `clocks = <&mfgsys CLK_MFG_BG3D>,
   <&infrasys CLK_INFRA_MFG_VCG>` with `clock-names = "core", "bus"`, which
   Panfrost already supports. Confidence: high that the parent read resolves
   the discrepancy, medium that the gate is required.
6. **H6. Dynamic GPU DVFS needs clock-tree flags, not new drivers: give
   `mfg_sel` `CLK_SET_RATE_PARENT` (and the `mfg_bg3d` gate the same) so
   `dev_pm_opp_set_rate()` reaches `mfgpll`, then use the type-12 static table
   below 780 MHz with its *uncalibrated* voltages as the first OPP table (F10,
   F11, F18).** The uncalibrated voltages are 25–45 mV above the EEM-adjusted
   live values, i.e. conservative; `VMAX 1.15 V` bounds them. The open risk is
   the post-divider transition without the vendor's 26 MHz parking; the mainline
   PLL driver changes PCW and post-divider in place. Test: offline first; on
   device only after H3 passes, with `devfreq` governor `userspace`, stepping
   one OPP at a time and reading `clk_summary` and the RT5735 VSEL0 code after
   each step. Confidence: medium.
7. **H7. The device's efuse speed bin and function code can be read from the
   loader-provided `atag,devinfo` array and decide the OPP table and post-divider
   scheme (F18, F19).** Test: Gemian read of
   `/proc/device-tree/chosen/atag,devinfo` (or the `/dev/devmap` ioctl),
   extracting only words 8 (bits 11:8), 22 (bits 3:0) and 61 (bits 7:4) plus
   the EEM words 50–53, 56–61, 65, 66 for a private archive. Expected:
   word 22 bits 3:0 = 4 (type 12). Publish only the decoded `cid`/type; the
   array contains the HRID. This also tells whether a mainline
   `opp-supported-hw` nvmem path is worth building. Confidence: high. The same
   read should include the live `i2c@11010000` children to settle the
   `vgpu_buck@60` provenance question from the Inputs section.
8. **H8. The local RT5735 driver needs `enable_time = 350 µs` and a
   `ramp_delay` derived from the TIME/LIMCONF slew fields so the regulator
   core waits as the vendor does (F12, F14); it should keep ignoring the
   protection registers.** With no `ramp_delay` the OPP core returns from a
   voltage increase immediately, which only matters once H6 changes voltages;
   `enable_time` matters for H3 because Panfrost resets the GPU right after
   enabling the supply. Test: offline (regulator core prints the computed
   delays with `regulator.debug`); on device, part of H6. Confidence: high for
   the values (they are the vendor's own), low for whether the omission causes
   a visible failure.
9. **H9. Thermal protection for the GPU can reuse the vendor power model
   (`dynamic-power-coefficient = <1461>`, F20) through Panfrost's
   `#cooling-cells` once an MT6797 thermal zone exists; until then the fixed
   520 MHz point (below the vendor's own 442.5 MHz low-battery cap only in
   voltage, not frequency) is the only protection and GPU load tests must stay
   short.** No GPU-specific test; depends on the thermal step in the roadmap.
10. **H10. Keeping VGPU on across runtime suspend (mainline default) costs idle
    power that the vendor avoids by cycling the rail (F15); an MT6797
    `pm_features` choice may be needed later.** Test: much later, battery
    current with the GPU idle under mainline versus Gemian; no action now.
11. **H11. (Negative, no test.)** The legacy `mt_spm_mtcmos.c` MFG routine and
    the `0x0c` G3D-config "reset" are not part of the running vendor sequence
    (F3, F9) and should not be ported or cited as requirements.

## Consequences for the roadmap (no changes applied here)

- The roadmap's GPU step lists MFG power domains, the RT5735 rail and safe
  OPPs. The domains and the rail are already described (F22); the missing
  pieces are smaller and specific: the bus-protection mask (H1), the INFRACFG
  GPU-LDO words (H2), the `mfg_52m` parent and `INFRA_MFG_VCG` gate (H5), an
  optional TOPRGU reset (H4), and regulator timing (H8). Two Gemian reads
  (H2a, H5, H7) and a sequence of offline patch edits precede the first
  mainline GPU boot (H3).
- The safe first operating point is the vendor's own pre-calibration point,
  520 MHz at 1.000 V (F19), not the 700 MHz DT label and not the 900 MHz top
  of the live table. Dynamic DVFS is a clock-flag and OPP-table change (H6),
  not a new frequency driver.
- The GPU does not depend on the PMIC step: its supply is the external RT5735
  and its domains are SPM registers. It does depend on the display step for
  any visible result and on the thermal step for sustained load (H9).
- Nothing here authorizes enabling the GPU node, changing the RT5735 output,
  or writing INFRACFG, SPM or TOPRGU registers on the device. The first GPU
  boot is a new reviewed experiment.

## Validation

Documentation-only change: `./scripts/check-repository` and link checks apply;
no kernel build, DT check or device action was performed. Line numbers were
taken from the exact fetched files recorded in `source-inputs.json`.
