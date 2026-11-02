# Mali-T880 GPU on MT6797

Scope: the Gemini's Mali-T88x MP4 GPU, the MT6797 MFG power/clock/rail
resources, vendor GPU DVFS and firmware/userspace boundaries, and the exact
mainline Panfrost configuration needed to bring it up safely.

| Field | Value |
| --- | --- |
| Device | Named Gemini PDA development unit (MT6797X) |
| Last verified | 2026-11-02 (first job on the station) |
| GPU identity | Mali-T88x MP4 r1p0, product `0x0880`, four cores |
| Mainline model | Panfrost `GPU_MODEL(t880, 0x880)` |
| Vendor source | Gemian `8cfe6596` / `59e00a91` lineage |
| Exact vendor DTB | `9e26929563f7682d1f7545d6007f0092c7e085a4edbd6e7be0ac8eaa5159b2f9` |
| Active vmlinux | `cc66df06194d3315335462760962165e1dcb2e50221574aeb45a0805bb17a162` |
| Current status | Sustained shader load to 520 MHz at 1.0 V and idle power-off, from modules on the station; DVFS not yet run; see the first job |

The detailed vendor-side evidence is in the
[GPU RE record](../../experiments/2026-10-04-gemini-gpu-re/README.md) and the
[GPU/Panfrost recovery record](../../experiments/2026-07-12-mt6797-gpu-panfrost-recovery/README.md).
This document keeps the durable configuration facts and the proposed bring-up
recipe. The [November 1 review](../../experiments/2026-11-01-mali-t880-research-review/README.md)
corrects the clock, voltage and sequencing claims below. The existing profile
and composed DTB remain offline preparation; they are not ready for a GPU boot.

The station runs `mtk-pm-domains`, not legacy SCPSYS, so sections 5, 6.2 and 6.4
describe a path it does not use. [The first job](../../experiments/2026-11-02-mali-t880-first-job/README.md)
has the design for the station and a live baseline that differs from the LK state
recorded here: on that boot the LDOs were at reset and MFG_ASYNC was off. It also read
the RT5735 at 975000 uV and disabled before any load, on bus `1-001c` on that image, and
explains the 156 MHz report: `mfg_52m_sel` on `univpll2_d8` is 156 MHz in the clock framework,
despite its name.

## 1. Identity and mainline coverage

| Fact | Confidence | Evidence |
| --- | --- | --- |
| GPU is Mali-T88x MP4 r1p0, product `0x0880`, four shader cores | `observed` | Vendor runtime identity, [recovery summary](../../experiments/2026-07-12-mt6797-gpu-panfrost-recovery/results/runtime-summary.txt) |
| Vendor DT uses legacy `arm,malit860`/`arm,mali-t86x`/`arm,malit8xx`/`arm,mali-midgard` | `observed` | Vendor `mt6797.dtsi` |
| Panfrost 7.1.3 includes `t880`/`0x880` and the T76x/T8xx quirks | `confirmed` | `panfrost_gpu.c` model table |
| The upstream Midgard binding does not accept MT6797 | `confirmed` | `arm,mali-midgard.yaml` compatible list |
| Panfrost T880 needs no loadable GPU firmware | `confirmed` | Midgard model; no vendor GPU firmware file; see section 7 |

The live `0x0880` ID is the authority, not the vendor's `arm,malit860`
compatible. Panfrost uses the GPU ID and model table, so the core register
model is supported. The missing work is MT6797 platform integration, not a new
GPU silicon driver. [Mesa's Panfrost support table](https://docs.mesa3d.org/drivers/panfrost.html)
(checked 2026-11-01) lists T880 with OpenGL ES 3.1 and OpenGL 3.1, with no
Midgard Vulkan support. This is driver model coverage, not Gemini runtime evidence.

## 2. Register, interrupt, clock and power map

| Resource | Value | Notes |
| --- | --- | --- |
| GPU register window | `0x13040000` + `0x4000` | Vendor and mainline node |
| Vendor `clock-frequency` | 700 MHz | Descriptive label, not an OPP contract |
| Job interrupt | GIC SPI 264, level-low | `interrupt-names = "job"` |
| MMU interrupt | GIC SPI 263, level-low | `interrupt-names = "mmu"` |
| GPU interrupt | GIC SPI 262, level-low | `interrupt-names = "gpu"` |
| MFG clock gate | `mfgsys` `CLK_MFG_BG3D` | Gate/status at `0x4`/`0x8`/`0x0` |
| Bus/VCG gate | `infrasys` `CLK_INFRA_MFG_VCG` | Infracfg gate bit 14 |
| MFG PLL | `apmixedsys` `CLK_APMIXED_MFGPLL`, `0x240`/`0x244` | PCW/post-divider |
| MFG mux | `topckgen` `CLK_TOP_MUX_MFG` | Parent `CLK_TOP_MFGPLL_CK` |
| 52 MHz pre-clock | `topckgen` `CLK_TOP_MUX_MFG_52M` | Vendor parent `univpll2_d8`; live value suggests `univpll2_d4` |
| Power domains | `MFG_ASYNC` (5) -> `MFG` (6) -> `CORE0..3` (7-10) | SPM offsets `0x334`, `0x338`, `0x340`-`0x34c` |
| SRAM power | `MFG_SRAM_CON` `0x33c` | MFG bits 1:0/17:16; core bits 8/20-23 |
| MFG bus protection | `INFRA_TOPAXI_PROTECTEN` bits 21 and 23 | Vendor Kbase and `gpu/0001` patch |
| GPU SRAM LDO | `0x10001fbc`-`0x10001fe4` | Vendor writes; LK pre-sets a modem-boot subset |
| TOPRGU MFG reset | `SWSYSRST` bit 2 | Composition references the local provider; no vendor-equivalent init pulse |
| GPU MMU | Panfrost's own MMU | No `iommus`; MT6797 M4U has no GPU port |

The GPU has no standard M4U `iommus` property. The vendor Mali block exposes
its own MMU interrupt, and the M4U port table contains no GPU client. Do not
add an IOMMU phandle by analogy with other MediaTek GPUs.

The loader also touches MFGPLL: LK's `mt_pll_turn_off()` disables it in the
battery/charging path before `md1_power_down()`. Mainline must not assume the
MFGPLL is running or at a particular rate when Panfrost probes; it should set
the PLL/mux explicitly for the fixed point.

The vendor Kbase driver defaults `system_coherency` to `COHERENCY_NONE`, and
the exact DT has no `system-coherency` override. Do not add `dma-coherent` by
analogy; Panfrost should run with its normal cache-maintenance path.

## 3. VGPU rail: RT5735 on I2C7

The GPU supply is the external Richtek RT5735 on I2C7 at address `0x1c`, not
the MT6351 PMIC `buck_vgpu`.

| Field | Value |
| --- | --- |
| Bus/address | `i2c7@11010000`, `regulator@1c` |
| Compatible | `richtek,rt5735` |
| Output | VSEL0 register `0x11`, enable bit 7, code bits 6:0 |
| Voltage | 600 mV + 6.25 mV x code, 0.6-1.39375 V |
| Product ID | register `0x03` = `0x10` |
| Vendor enable wait | 350 us |
| Vendor up-slew | 32 mV/us by default; down-slew 4 mV/us |

The exact Gemian DTB also contains an `i2c7` child `vgpu_buck@60` with
compatible `mediatek,vgpu_buck`, status `okay`; the vendor source matches that
compatible to the FAN53555 driver at I2C7 address `0x60`. The 2026-07-12
inventory found it unbound, and the hardware is an RT5735 at `0x1c`. It is an
alternate board descriptor, not the active GPU supply. RT5735 is the bound
regulator and the one the vendor `mt_gpufreq` path drives.

The vendor powers the rail off when the GPU is idle and on during a GPU power
cycle. Mainline Panfrost enables `mali-supply` at probe and leaves it on unless
an MTK-specific runtime-PM feature is added. A first bring-up should therefore
use a fixed 1.0 V rail and accept the idle cost.

## 4. Operating points and DVFS

The live table is type 12, selected by efuse function code 4. These are the
public source table's voltage requests and corresponding truncated RT5735
selectors, before per-unit EEM adjustment:

| Frequency | Vendor voltage request | RT5735 code |
| --- | --- | --- |
| 900 MHz | 1.1545 V | 88 |
| 780 MHz | 1.1032 V | 80 |
| 610 MHz | 1.0134 V | 66 |
| 520 MHz | 0.9750 V | 60 |
| 442.5 MHz | 0.9365 V | 53 |
| 365 MHz | 0.9108 V | 49 |
| 238 MHz | 0.8467 V | 39 |

EEM recalibrates these values; the live sample had lower voltages
(1.1125/1.06875/1.0125/0.975/0.93125/0.90625/0.84375 V). Before EEM is ready,
the vendor requests **520 MHz at 1.0006 V**. Its RT5735 conversion truncates
that request to selector 64, **1.0000 V nominal**. This supports investigating
520 MHz / 1.0 V as a first fixed point, but does not establish safe mainline
sequencing or physical voltage. It is above the 442.5 MHz low-battery cap.

The vendor also uses:

- `dynamic-power-coefficient` equivalent `1461` uW/MHz/V^2;
- thermal, PBM and low-battery OPP limiting;
- MFGPLL post-divider parking when the divider changes;
- `Vsram`/`VGPU` sequencing with voltage-first up and clock-first down.

Mainline does not have the MT6797 EEM/SVS driver. The proposed first probe
targets a fixed 520 MHz / 1.0 V point without an OPP table or devfreq policy. For dynamic DVFS later, review
representable voltages and ceilings rather than copying vendor requests into
scalar OPP entries. Rate propagation through `mfg_sel`/`mfg_bg3d` already exists;
PLL parking, actual parent selection and rate verification remain necessary.

The thermal policy is not a kernel unknown. The stock Android `.tp` files
contain the complete zone/trip/cooler tables, and the `clctm` cooler record
carries CPU/GPU frequency-voltage pairs. The decoded policy and the exact GPU
power-budget path are recorded in
[MT6797 thermal management](mt6797-thermal-management.md) and
[stock thermal policy](../../experiments/2026-10-31-mt6797-thermal-management/results/userspace-policy.md).
For the GPU this means:

- the GPU has no separate thermal zone in the shipped policy, but bank 1 tracks GPU load on this unit, warming first
  and most ([first job](../../experiments/2026-11-02-mali-t880-first-job/README.md));
- cooling reaches it as a **power budget** through
  `mt_gpufreq_thermal_protect()`, arbitrated with PBM and low-battery limits;
- mainline needs a devfreq cooling device, not a new GPU temperature sensor.

What userspace cannot supply is the per-unit calibration: the NTC tables and
pull-up/supply parameters are in `.tp`, but the actual efuse/devinfo words are
programmed per device. LK reads them at boot and appends them to
`/chosen/atag,devinfo`; the kernel never reads the efuse controller. The
current mainline NVMEM provider (`0057a`) exposes only the three thermal words
(31-33). GPU EEM uses words 22 and 50-66, so a GPU DVFS profile needs an
additional read-only NVMEM cell for those words, or a direct efuse provider.

## 5. Vendor power sequence and mainline gaps

Vendor power-on:

```text
GPU LDO reserve (0x10001fbc = 0x1ff)
 -> VGPU enable (+350 us)
 -> infra_mfg_vcg
 -> mfg_async -> mfg -> mfg_core0..3
 -> mfg_bg3d
 -> 100 us
 -> release bus protection bits 21|23
 -> G3D timing/PMU writes
```

Vendor power-off polls MFG idle, asserts bus protection, disables BG3D, then
cores, MFG, ASYNC and VCG, and finally disables VGPU and the LDO enables.

The vendor platform init programs the full GPU SRAM LDO set once, before any
GPU power sequence. The MT6797 register table names these as `GPULDO_CTRL_0..10`
in INFRACFG AO and confirms the field layout:

| Register | Field | Reset | Vendor | LK |
| --- | --- | --- | --- | --- |
| `0x10001fbc` | `RG_GPULDO_EN_0..8` | `0x000` | `0x1ff` on, `0x0` off | `0xff` |
| `0x10001fc0` | `VOSEL/LP` for LDO 0-3 | `0x09090909` | `0x0f0f0f0f` | `0x0d0d0d0d` |
| `0x10001fc4` | `VOSEL/LP` for LDO 4-7 | `0x09090909` | `0x0f0f0f0f` | `0x0d0d0d0d` |
| `0x10001fc8` | `VOSEL/LP` for LDO 8 | `0x00000009` | `0x0000000f` | untouched |
| `0x10001fd8` | `RSV_H_0..7` | `0xffffffff` | `0x88888888` | untouched |
| `0x10001fe4` | `RSV_H_8` (3:0) | `0x0` | `0x00000008` | untouched |

`VOSEL` and `LP` are separate fields; the repeated `0x0f` programming
does not enable the `LP` bit. LDO 8 lives in
`GPULDO_CTRL_3` and its high trim in `GPULDO_CTRL_10`. `GPULDO_CTRL_4`
(`CAL_0..7`), `CTRL_5` (`NDIS/STB/BYPASS`), `CTRL_8` (`RSV_M`) and `CTRL_9`
(`RSV_L`) are left at reset by the vendor; mainline should not invent values
for them.

The vendor sequence is therefore:

```text
probe:  fd8=0x88888888, fe4=0x8, fc0/fc4=0x0f0f0f0f, fc8=0x0f
power-on:  fbc=0x1ff
power-off: fbc=0x0
```

The MT6797 SCPSYS driver has the INFRACFG regmap, but placing the writes
in its MFG callback is only a proposal. The vendor enables LDOs before VGPU
and MFG_ASYNC; MFG callbacks run after ASYNC and do not coordinate Panfrost
supply enable. Legacy SCPSYS also powers every domain at provider probe,
independently of GPU-node status. The owner and rollback sequence must be
designed before implementing these writes.

LK only pre-sets `fc0/fc4=0x0d0d0d0d` and `fbc=0xff`, so LDO 8 and all high
trims are missing before a mainline probe. This is a concrete, source-backed
implementation gap, not an unknown.

The same vendor probe also selects `univpll2_d8` for `mfg_52m_sel`, pulses the
TOPRGU MFG reset and asserts the bus protection mask. The offline composition
now covers the mux parent and reset reference; the LDO writes still need a
driver home. The reset is `TOPRGUWDT_SWSYSRST` (`0x10007018`) bit 2
`mfg_grst_b` (“write 1 to reset MFG”), matching `MT6797_TOPRGU_MFG_SW_RST`.

`MFG_ASYNC_CON` at `0x1300001c` is the other concrete write. Its `MEM_MST_SEL`
and `MEM_SLV_SEL` fields select the async-FIFO delay (`1T` reset, `2T` = 1,
`3T` = 2). The vendor chooses `0xa` when the **table maximum** is at
least 780 MHz, otherwise `0x5`, and ORs it into this register at power-on.
Type 12 therefore selects `0xa` even at 520 MHz. Panfrost does not write it;
the inherited value is unverified, not necessarily the reset value.

The 52 MHz preclock is likewise explicit in the register table:
`CLK_MISC_CFG_0` (`0x10000104`) bits `[2:1]` select `00=26M`, `01=52M`,
`10/11=104M`, and the reset value is `00`. Bit 0 (`pdn_mfg_52m_ck`) resets to
0 (clock enabled). The vendor selects `univpll2_d8`; its clock name is not a
measurement of frequency. The earlier live 156 MHz report remains unexplained, so both the
selected parent and actual rate need verification after assignment.

The GPU core mux is `CLK_CFG_1` (`0x10000050`): bits `[25:24]` select
`0=clk26m`, `1=mfgpll_ck`, `2=syspll_d3`, `3=univpll_d3`, and bit 31
`pdn_mfg` resets to 0 (clock enabled). The reset value selects **26 MHz**,
but the loader can change it. Neither the reset value nor a requested `assigned-clock-rates = <520000000>` proves
the actual parent/rate at probe.

The loader is not neutral here. Planet LK's `md1_boot()` / `md1_pmic_setting()`
writes a modem-boot subset before Linux:

```text
0x10001fc0 = 0x0d0d0d0d
0x10001fc4 = 0x0d0d0d0d
0x10001fbc = 0xff
0x10006334 = 0x1e -> 0xe -> 0xc -> 0xd   // MFG_ASYNC_PWR_CON
```

That leaves the GPU SRAM LDO at a non-reset value and `mfg_async` powered
before the mainline GPU probe. It is not the vendor GPU driver's final
`0x0f0f0f0f`/`0x1ff` state, so the first mainline boot must not assume either
reset defaults or full vendor LDO programming.

The live Gemian boot log adds two useful values: the GPU starts at
520 MHz / 975 mV (`g_cur_gpu_freq = 520000`, `g_cur_gpu_volt = 97500`) and
iDVFS reports `SRAM LDO setting = 110000 (x100mv)`, i.e. 1.1 V. The vendor
`mali` driver in that boot says "Continuing without Mali regulator control"
and "without Mali clock control"; `mt_gpufreq`, not Kbase, owns VGPU and the
GPU clock there. Mainline Panfrost must do both itself.

Mainline Panfrost with the local patches:

```text
attach core0..3 genpd links -> parent MFG/MFG_ASYNC power
 -> optional reset
 -> enable core/bus clocks
 -> enable mali-supply
 -> GPU soft reset
```

The composition helper requests a core rate of 520 MHz and the SCPSYS
`mfg_52m_sel` parent `univpll2_d8`; Panfrost does not set a rate without an
OPP table. Panfrost requests the domains first,
then deasserts reset, enables clocks and enables VGPU; the vendor enables VGPU,
the 52 MHz VCG clock, the domains, and only then `mfg_bg3d`.

The MT6797 platform data keeps `pm_features = 0`. Consequently clocks and
VGPU remain enabled across runtime suspend, and TOPRGU is not toggled by
runtime PM. Initial reset handling deasserts the line; teardown asserts it.
This does not reproduce the vendor init pulse. Any change to `GPU_PM_RT`,
`GPU_PM_CLK_DIS` or `GPU_PM_VREG_OFF` needs a separate ordering review.

Missing or unvalidated relative to the vendor:

| Item | State | Consequence |
| --- | --- | --- |
| Bus protection bits 21/23 | `gpu/0001` prepared on MFG | Correct mask, but releases before cores/BG3D and protects after child shutdown; vendor ordering not reproduced |
| GPU SRAM LDO reserve writes | Exact values known, not implemented | Possible SCPSYS/SRAM power-up failure |
| Fixed 520 MHz core rate | Requested by composition helper | Verify actual parent/rate and safe PLL transition; assignment is not runtime evidence |
| `mfg_52m_sel` parent | Set by composition helper | Vendor explicitly selects `univpll2_d8` |
| G3D timing/PMU writes | Not implemented | Vendor ORs `0xa` for the type-12 table, independent of current frequency, and enables PMU counters; runtime necessity unverified |
| TOPRGU MFG reset | Composition adds `resets`; initial probe deasserts only | No vendor-equivalent init pulse or runtime-PM reset with current platform data |
| VGPU/domain/clock order | Panfrost order differs | First-boot risk if a gate needs VGPU or a domain |
| VGPU off at idle | Not implemented | Idle power cost; rail/domain combination has not been validated |

The first GPU boot must not assume all of these are harmless. The bus
protection mask is the highest-value prerequisite; the SRAM LDO words and the
power sequence are the highest-risk unknowns.

## 6. Mainline configuration recipe

### 6.1 Kconfig

A GPU profile must start from a runtime profile that does not carry the
handoff `# CONFIG_DRM is not set`, then add:

```text
CONFIG_DRM=y
CONFIG_DRM_PANFROST=m
CONFIG_PM_DEVFREQ=y
CONFIG_PM_OPP=y
CONFIG_DEVFREQ_THERMAL=y
CONFIG_ENERGY_MODEL=y
CONFIG_MTK_SCPSYS=y
CONFIG_COMMON_CLK_MT6797_MFGSYS=y
CONFIG_REGULATOR_RT5735=y
CONFIG_I2C_MT65XX=y
```

`CONFIG_DRM_PANFROST` selects `DRM_SCHED`, `DRM_GEM_SHMEM_HELPER`,
`IOMMU_SUPPORT`, `IOMMU_IO_PGTABLE_LPAE` and `PM_DEVFREQ`. It does not select
`CONFIG_DEVFREQ_THERMAL`; enable that explicitly if a GPU cooling device is
wanted. Do not enable `CONFIG_MTK_SCPSYS_PM_DOMAINS` instead of
`CONFIG_MTK_SCPSYS`: the newer `mtk-pm-domains` driver has no MT6797 GPU
entries, while the legacy `mtk-scpsys` driver has the MFG hierarchy added by
patch 0047.

The current `gemini.fragment` already enables `COMMON_CLK_MT6797_MFGSYS` and
`REGULATOR_RT5735`, but it does not enable DRM/Panfrost, and every A53 runtime
profile includes `gemini-handoff.fragment`, which disables DRM. A GPU bring-up
therefore needs a named GPU profile, not the A53 baseline.

The offline profile `mt6797-a53-gpu-bringup` now exists:

- `configs/gemini-a53-gpu-bringup.fragment`
- `patches/series-a53-gpu-bringup` (A53 foundation plus `gpu/0001`)
- `kernel/manifest.json` profile `mt6797-a53-gpu-bringup`

It selects the GPU platform providers but has not been built in its experiment
record. The GPU node stays disabled, but SCPSYS can still power the MFG domains
at provider probe. Do not boot this profile as an inert GPU-disabled baseline.
The enabled DTB is produced separately by
[`compose-gpu-dtb.py`](../../experiments/2026-10-31-mali-t880-offline-bringup/scripts/compose-gpu-dtb.py)
after a reviewed build.

### 6.2 Device tree: first fixed point

The existing offline composition enables `mfgsys`, `i2c7`, RT5735 and GPU,
requests 520 MHz / 1.0 V, omits the OPP table and `iommus`, and references
TOPRGU MFG reset. The fragment below describes that proposal, not a
runtime-ready recipe; the sequencing and validator blockers in the
[review](../../experiments/2026-11-01-mali-t880-research-review/README.md) must be resolved first.

```dts
&mfgsys {
	status = "okay";
};

&i2c7 {
	status = "okay";
	pinctrl-names = "default";
	pinctrl-0 = <&i2c7_pins_a>;

	rt5735_vgpu: regulator@1c {
		compatible = "richtek,rt5735";
		reg = <0x1c>;
		regulator-name = "vgpu";
		regulator-min-microvolt = <1000000>;
		regulator-max-microvolt = <1000000>;
		regulator-enable-ramp-delay = <350>;
		regulator-settling-time-up-us = <350>;
		regulator-ramp-delay = <4000>;
		status = "okay";
	};
};

&gpu {
	status = "okay";
	mali-supply = <&rt5735_vgpu>;
	clocks = <&mfgsys CLK_MFG_BG3D>,
		 <&infrasys CLK_INFRA_MFG_VCG>;
	clock-names = "core", "bus";
	assigned-clocks = <&mfgsys CLK_MFG_BG3D>;
	assigned-clock-rates = <520000000>;
	resets = <&watchdog MT6797_TOPRGU_MFG_SW_RST>;
};

&scpsys {
	assigned-clocks = <&topckgen CLK_TOP_MUX_MFG_52M>;
	assigned-clock-parents = <&topckgen CLK_TOP_UNIVPLL2_D8>;
};
```

`CLK_MFG_BG3D` is a gate with `CLK_SET_RATE_PARENT`, so the rate request
can propagate through `mfg_sel`; `MUX_GATE` already supplies the same flag.
This does not guarantee the selected parent is `mfgpll` or the rate is exactly
520 MHz. The parent choice, PLL transition and measured rate require validation.

The base GPU node from patch 0059 supplies the register, interrupts and
`core0..3` domains:

```dts
gpu: gpu@13040000 {
	compatible = "mediatek,mt6797-mali", "arm,mali-t880";
	reg = <0 0x13040000 0 0x4000>;
	interrupts = <GIC_SPI 264 IRQ_TYPE_LEVEL_LOW>,
		     <GIC_SPI 263 IRQ_TYPE_LEVEL_LOW>,
		     <GIC_SPI 262 IRQ_TYPE_LEVEL_LOW>;
	interrupt-names = "job", "mmu", "gpu";
	clocks = <&mfgsys CLK_MFG_BG3D>;
	clock-names = "core";
	power-domains = <&scpsys MT6797_POWER_DOMAIN_MFG_CORE0>,
			 <&scpsys MT6797_POWER_DOMAIN_MFG_CORE1>,
			 <&scpsys MT6797_POWER_DOMAIN_MFG_CORE2>,
			 <&scpsys MT6797_POWER_DOMAIN_MFG_CORE3>;
	power-domain-names = "core0", "core1", "core2", "core3";
	status = "disabled";
};
```

The parent `MFG`/`MFG_ASYNC` domains are powered through the SCPSYS subdomain
hierarchy; the GPU lists only the four leaf cores because Panfrost attaches
those as device links.

### 6.3 Later OPP table

After fixed-point sequencing and runtime have been established, derive a standard
OPP table with reviewed voltage ceilings and RT5735-representable outputs.
The vendor request table in section 4 is evidence, not ready-to-use DTS.

A scalar `opp-microvolt` sets target, minimum and maximum equal. For example,
`<846700>` cannot round to 850000 µV because that exceeds its maximum. Six of
the seven earlier example scalar values were unrepresentable; that example is
withdrawn. Explicit supported selectors or reviewed target/min/max triplets
are required. The 900 MHz vendor request also exceeds the cited 1.15 V
software ceiling, so it must not be admitted merely because it is in the table.
See the [voltage review](../../experiments/2026-11-01-mali-t880-research-review/README.md#4-voltage-requests-and-representable-outputs-differ).

No rate-propagation flag change is needed. Divider-change parking, regulator
settling and thermal cooling remain separate requirements before dynamic DVFS.

### 6.4 Required profile/series

The local patches are:

| Patch | Role |
| --- | --- |
| `0047` | MT6797 MFG `mfgsys`/`mfg`/`core0..3` SCPSYS domains |
| `0048` | MT6797 `mfgsys` clock provider (`CLK_MFG_BG3D`) |
| `0049` | disabled `mfgsys` node |
| `0050` | 52 MHz MFG pre-clock handling |
| `0051` | RT5735 VSEL0 regulator |
| `0058` | Panfrost `mediatek,mt6797-mali` platform data |
| `0059` | disabled GPU node |
| `gpu/0001` | MFG bus protection bits 21/23 |

A GPU profile must include these in canonical order and must not be mixed with
the A53 handoff profile's final `CONFIG_DRM=n`. The offline
`mt6797-a53-gpu-bringup` profile selects `gpu/0001`; it has no GPU runtime validation and the base GPU node remains disabled.

## 7. Firmware and userspace boundary

- **No GPU firmware blob is required.** The installed vendor firmware set
  contains no Mali/MFG/GPU image. Midgard T880 is driven by the kernel; Panfrost
  needs no firmware.
- `mtk_kbase_spm_fw.c` contains `dvfs_gpu_binary[]`, a 1992-word
  `SPM_PCMASM_JADE_20150421` PCM image. Active vmlinux contains the
  `dvfs_gpu_binary` and `mtk_kbase_spm_*` symbols, but the vendor Kbuild only
  defines `MTK_GPU_SPM` when `CONFIG_MTK_GPU_SPM_DVFS_SUPPORT` is set, which
  the active configuration does not. The SPM kick path is therefore compiled
  out. The image is GPU SPM/DVFS microcode, not Mali shader or job firmware.
- The vendor userspace is `libGLES_mali.so` r12p1-01alp0, API
  `r12p0-04rel0`, supporting GLES 3.2/OpenCL 1.2/Vulkan and T880. It is a
  proprietary userspace driver, not a kernel firmware dependency, and is not
  compatible with Panfrost. Use Mesa Panfrost for mainline.
- The 25 MiB `libGLES_mali.so` contains the LLVM-based shader compiler and
  command-stream runtime (18.8 MiB `.text`), not an embedded GPU firmware
  image. It opens `/dev/mali`, `/dev/urandom`, `/proc/gpufreq/*` and
  `/proc/self/*`; it has no firmware path, `request_firmware` call, or
  firmware-like section. `libged.so`, `ged_srv` and `libgpu_aux.so` likewise
  contain policy/framebuffer helpers, not firmware.
- The vendor kernel GPU driver has no `request_firmware`/microcode load path.
  The only "GPU firmware" is the optional SPM PCM array described above.
- Vendor `kbase`/GED/SPM-DVFS policy is not part of Panfrost. Do not port it.

## 8. Bring-up order and validation

1. Offline: resolve provider-probe effects and rail/LDO/domain/clock/protection
   ordering, and repair the validator's provider/reference checks. The existing
   profile and `gpu/0001` do not yet establish a safe power sequence.
2. First boot: enable `mfgsys`, `i2c7`, RT5735 and GPU at fixed 520 MHz /
   1.0 V. Confirm:
   - `panfrost 13040000.gpu: Mali-T880` (or `mali-t880` model);
   - no MMU/GPU fault or SCPSYS timeout;
   - `/dev/dri/renderD128` exists;
   - runtime suspend/resume cycles the four core domains;
   - no `INFRA_TOPAXI` protect timeout.
3. Only after that, add the OPP table and devfreq with a userspace governor,
   one step at a time.
4. Add thermal cooling and a longer load only after the thermal provider and
   calibrated trips exist.

Stop on any SCPSYS/SRAM ack timeout, bus-protect timeout, GPU fault, or loss of
console. The first GPU boot is a reviewed experiment, not a default profile.

## 9. Implementation readiness

Enough is known to describe a proposed **fixed-point** DT/profile, but the
current composition is not ready for a first probe:

- Panfrost T880 model, GPU ID, register window and three interrupt lines
- MFG `mfg_bg3d`/`infra_mfg_vcg` clocks and MFG PLL/mux
- MFG_ASYNC -> MFG -> CORE0..3 power hierarchy
- RT5735 VSEL0 contract and fixed 1.0 V operating point
- No GPU firmware and no `iommus` property
- Required Kconfig and the offline GPU profile

Still needed before a safe first probe:

| Missing information | Why it matters | How to obtain |
| --- | --- | --- |
| MFG SRAM LDO and supply ordering | Exact writes known, owner and rollback unresolved | Design across SCPSYS probe and Panfrost runtime PM; inherited values alone do not prove ordering |
| Bus-protection enforcement/order | Mask placement differs from vendor sequence | Resolve release/assert position and bound any later readback protocol |
| `mfg_52m_sel` parent and VCG gate | Composition sets `univpll2_d8`; verify runtime | `clk_summary` and CLK_CFG `0x10000104[2:1]` |
| RT5735 actual voltage/current/timing | Live Gemian shows 975 mV at 520 MHz; mainline targets 1.0 V | Regulator summary or reviewed read-only I2C/register read |
| Exact efuse speed bin/function code | OPP selection and PLL post-divider | Read `atag,devinfo` words 8/22/61 (publish decoded fields only) |
| GPU clock rate inherited at boot | Composition requests 520 MHz; verify actual rate | `clk_summary` / Panfrost `clock rate` log |
| TOPRGU MFG reset necessity | A reference alone does not pulse it | Review initial pulse and provider before comparing attributable probes |

Still needed before dynamic DVFS/thermal:

- per-unit EEM/devinfo calibration values (tables, NTC parameters and trips are
  already known from source and the `.tp` policy);
- a mainline devfreq cooling device and trip binding (the vendor path is a
  power-budget call, not a GPU thermal zone);
- verified `opp-supported-hw`/`cid` mapping;
- runtime-PM policy for VGPU idle-off.

Still needed before upstream:

- a non-vendor-specific MT6797 Panfrost compatible/platform-data strategy;
- reset provider and bus-protect ownership;
- thermal/OPP bindings and documentation.

Not required:

- a GPU firmware blob;
- an `iommus` property;
- vendor Kbase/GED/SPM-DVFS policy.

## 10. Gaps

| Gap | Impact |
| --- | --- |
| GPU SRAM LDO init not implemented | Vendor programs `fd8/fe4/fc0/fc4/fc8`; LK only pre-sets a subset |
| MFG bus-protect mask prepared but not runtime-verified | Potential AXI hang on power cycle |
| `mfg_52m_sel` parent set by composition, `infra_mfg_vcg` gate unverified | Possible async/SRAM handshake issue |
| TOPRGU MFG reset exposed in composition, no one-shot pulse | Initial Panfrost probe deasserts; current runtime PM does not toggle it |
| Fixed 520 MHz rate requested by composition, not yet proven | Actual parent/rate and PLL transition still need verification |
| Panfrost clock/regulator/domain order differs from vendor | First-boot risk if a gate needs VGPU or a domain |
| G3D timing/PMU writes absent | Vendor ORs `0xa` for type 12 regardless of current frequency, and enables PMU counters |
| RT5735 DVS slew/LIMCONF init absent | Validate enable/settling timing and inherited protection state before probe or DVFS |
| EEM NVMEM cell and EEM driver absent | Calibrated dynamic OPPs unavailable; even static OPPs require voltage/ceiling review |
| EEM/thermal calibration absent | Dynamic table not admitted; trips/NTC policy are known from `.tp` |
| Exact GPU speed bin/efuse words not captured | `cid`/post-divider and `opp-supported-hw` cannot be finalized |
| No GPU runtime result | Panfrost support is still unproven on this unit |

## 11. Evidence index

- [November 1 research review](../../experiments/2026-11-01-mali-t880-research-review/README.md)
- [GPU offline bring-up preparation](../../experiments/2026-10-31-mali-t880-offline-bringup/README.md)
- [GPU RE record](../../experiments/2026-10-04-gemini-gpu-re/README.md)
- [GPU/Panfrost recovery](../../experiments/2026-07-12-mt6797-gpu-panfrost-recovery/README.md)
- [RT5735 recovery](../../experiments/2026-07-12-rt5735-vgpu-recovery/README.md)
- [Clock/power/reset recovery](../../experiments/2026-07-12-mt6797-clock-power-reset-recovery/README.md)
- [Live resource map](mt6797-live-resource-map.md)
- [Interrupt map](mt6797-interrupts.md)
- [MT6797 Functional Specification V1.0](https://www.96boards.org/documentation/consumer/mediatekx20/additional-docs/docs/MT6797_Functional_Specification_V1_0.pdf)
- [MT6797 Register Table Part I](https://www.96boards.org/documentation/consumer/mediatekx20/additional-docs/docs/MT6797_Register_Table_Part_1.pdf) — `GPULDO_CTRL_0..10`, `CLK_MISC_CFG_0`, `CLK_CFG_1`, `TOPRGUWDT_SWSYSRST`
- [MT6797 Register Table Part II](https://www.96boards.org/documentation/consumer/mediatekx20/additional-docs/docs/MT6797_Register_Table_Part_2.pdf) — `MFG_TOP`, `MFG_ASYNC_CON`, `MFG_PERF_EN`
- Vendor `mtk_config_platform.c`, `mt_gpufreq.c`, `power/mt6797/rt5735.c`
- LK `atags.c`, `mt_boot.c`
- Patches `0047`-`0051`, `0058`-`0059`, `0090`, `gpu/0001`
- Panfrost `panfrost_gpu.c`, `panfrost_drv.c`, `arm,mali-midgard.yaml`
