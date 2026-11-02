# Experiment: first Mali-T880 job on the station

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-02-mali-t880-first-job` |
| Status | `running`: run 2 powered the GPU and identified it at 26 MHz; no job yet, domains cycle against the design |
| Subsystem | MT6797 MFG, Mali-T880, Panfrost, RT5735 |
| Device variant | named Gemini PDA (MT6797X), boot2 station |
| Date(s) | 2026-11-02 |
| Investigator(s) | GPU session; device runs by the project custodian |
| Tracking issue | none |

## Question or hypothesis

With the vendor's power order rebuilt around upstream Panfrost, at a fixed 1.0 V
and a fixed low clock, does the GPU probe, report product `0x0880` with four
shader cores, and complete a bounded job through its own MMU, from modules?

It is falsified if a domain or bus protection step times out, the identity is
wrong, or the jobs do not complete. A pass shows the job manager, MMU and job
interrupt work. It does not show shader execution, rendering, a clock above the
one tested, or any thermal behaviour under load.

## No new GPU driver

Panfrost's model table has `t880`/`0x880` and the rest of its contract matches:
one register window, three interrupts, its own MMU and no firmware. What it
lacks is the MT6797 power order, which is a small platform file in the same
module. The [October and November records](../2026-11-01-mali-t880-research-review/README.md)
already reached this.

## What the research assumed that the station does not

| Assumption | Station | Consequence |
| --- | --- | --- |
| Legacy `mtk-scpsys` with MFG entries (`0047`, `gpu/0001`) | Runs `mtk-pm-domains`, with `MTK_SCPSYS` off | `0476` adds the domains to the modern driver. `gpu/0001` and the [offline composition and validator](../2026-10-31-mali-t880-offline-bringup/README.md) do not apply |
| A domain provider powers everything at probe | `KEEP_DEFAULT_OFF` leaves them alone | Review finding 5 does not apply: loading no GPU driver powers no MFG domain |
| LK leaves the LDOs at `0xff`/`0x0d` and MFG_ASYNC on | Baseline below: LDOs at reset, MFG_ASYNC off | The module cannot rely on any inherited LDO state |
| `CONFIG_DRM=y` | `=m`, so the DRM core is a module too | Fewer boot-time changes |

## Why this needs one boot image

Almost everything is a module. Three things cannot be:

1. **`alloc_io_pgtable_ops`.** Panfrost needs `IOMMU_IO_PGTABLE_LPAE`, a bool, and
   the current image's `System.map` does not have it. No module can provide it.
2. **The domain table.** The MFG domains are entries in the built-in
   `mtk-pm-domains`, the same provider that serves AUDIO and CONN, so it cannot
   be swapped by a module while those are in use.
3. **The device tree.** The GPU node, MFGSYS, I2C7 and the RT5735 are disabled in
   the running DTB. An overlay could enable them, but the first two points need
   the image anyway.

The new image changes no behaviour until the modules load, apart from the I2C7
controller binding. The built-in additions are `IOMMU_SUPPORT` and the LPAE table
code, with no IOMMU driver, plus small `DRM_BRIDGE`, `DRM_PANEL`, `DEV_COREDUMP`
and `KCMP` code. The SMMU drivers, `MTK_IOMMU` and the other 50 display and GPU
drivers that `DRM` exposes are off, listed in
[the fragment](../../configs/gemini-a53-station-gpu.fragment). The fragment is in
the `mt6797-a53-station-a72` profile only. Later iteration on the sequence itself
needs no boot, because all of it is in `panfrost.ko`.

## Design

| Step | Owner | Vendor order |
| --- | --- | --- |
| Find regulator, clocks, regmaps, reset; defer if any is missing, before any effect | `panfrost.ko` | n/a |
| Refuse if SoC is at or above 55 C or VGPU is not 1.0 V | `panfrost.ko` | n/a |
| `mfg_52m_sel` to `univpll2_d8`, `mfg_sel` to the fixed parent, refuse above 365 MHz | `panfrost.ko` | at init |
| LDO trims, with readback | `panfrost.ko` | at init |
| One TOPRGU MFG pulse | `panfrost.ko` | at init |
| Assert protection bits 21/23 | `panfrost.ko` | at init |
| LDO enable `0x1ff`, then VGPU on | `panfrost.ko` | 1, 2 |
| VCG, MFG_ASYNC, MFG, cores | `mtk-pm-domains`, by Panfrost's device links | 3-5 |
| BG3D | Panfrost, `clk-mt6797-mfg.ko` | 6 |
| 100 us, release protection, `MFG_ASYNC_CON` bits `0xa` | `panfrost.ko` | 7-9 |
| Soft reset and identify | Panfrost | after |

Power-off runs the reverse: GPU off, idle poll, assert protection, BG3D, cores, MFG,
MFG_ASYNC, VCG, VGPU, LDO enable off.

Runtime suspend is held off, so the domains cycle only at module unload. Panfrost's
own assert of the reset at teardown is skipped on MT6797, because it would happen
with the domains still on, which the vendor never does.

### Where this differs from the vendor

- **The core domain writes.** The vendor's cores clear reset, isolation, then clock
  disable. `mtk-pm-domains` clears clock disable, isolation, then reset, the order
  the vendor uses for MFG and MFG_ASYNC. Power-off differs the same way.
- **`0x10001fe4` bit 15.** The baseline read it set; the register table documents a
  reset of 0 and only bits 3:0 as `RSV_H_8`. The vendor's write of `0x8` would clear
  it. The module changes only bits 3:0.
- **PMU enable writes.** `0x3e0`-`0x3f0` are left alone. Counters are not needed here.
- **Voltage.** 1.0 V is the vendor's request before EEM runs. Every vendor voltage at
  or under 520 MHz is lower, so the two clocks allowed here have margin.

### The clock

The first run uses `clk26m`. The MFGPLL runs at about 500 MHz from the baseline, but
changing it needs the vendor's post-divider parking, which is unreviewed, and the mux
alone can avoid it. `mt6797_parent=1` selects `syspll_d3` (about 364 MHz, the vendor's
365 MHz point), so a second clock needs no boot. 26 MHz is below the vendor's table
(its lowest is 238 MHz), so it could fail for reasons a table clock would not, and
that is in the decision table. Nothing here can reach 520 MHz.

## Baseline

Read-only `devmem` on boot `92cd3b53`, image `b8b9256b`, after GNSS and Wi-Fi ran:

| Register | Value | Reading |
| --- | --- | --- |
| `PWR_STATUS` / `2ND` | `0x2B00005E` / `0x2B00004E` | bits 8-13 clear: every MFG domain off, including MFG_ASYNC |
| `MFG_ASYNC_PWR_CON`, `MFG_PWR_CON` | `0x12` | isolated, clock disabled |
| `MFG_CORE0..3_PWR_CON` | `0x112` | also SRAM down |
| `MFG_SRAM_CON` | `0x00F300FF` | SRAM down, acknowledged for MFG and all four cores |
| `INFRA_TOPAXI_PROTECTEN` / `STA1` | `0x000104B8` / `0xE0415CB8` | bits 21 and 23 clear in both |
| `GPULDO_EN` | `0x0` | off |
| `GPULDO` `fc0`/`fc4`/`fc8` | `0x09090909`/`0x09090909`/`0x9` | reset values |
| `GPULDO` `fd8`/`fe4` | `0xFFFFFFFF`/`0x00008000` | reset, except the undocumented bit 15 |
| `CLK_CFG_1` | `0x81010100` | `mfg_sel` gated, parent MFGPLL |
| `CLK_MISC_CFG_0` | `0xFFFF0000` | `mfg_52m_sel` on `clk26m`, not the vendor's parent |
| `MFGPLL_CON0`/`CON1` | `0x101`/`0x02134000` | running; PCW and post-divider give about 500 MHz (inference) |
| `SWSYSRST` | `0x00010000` | MFG bit 2 clear |

These contradict the recorded LK modem-boot subset for this boot, and are one read
of one boot. The RT5735 could not be read: I2C7 is disabled in that DTB.

## Build

| Item | Value |
| --- | --- |
| Input commit | `08b51fc31b46455c35e39b57ed4c075daa01b2c2` |
| Profile | `mt6797-a53-station-a72`, modules built, Buildbox-2, job `...-m1` |
| Package | `linux-7.1.3-gemini-9e652c87367e5dc190b99e428f5094ff9835d993d6a19c3757bc3239a7168beb` |
| `Image.gz` | `2af362e95393c01a10e0ccbdf6ed54c2657d2ea06428334e76ccc5ffa2868796` |
| Station-a72 DTB | `6dae14d6996b79b691fb025656df9e0b7d4f91d77559d2a7c905a92dd000a552` |
| `panfrost.ko` | `e27897dd9d74b045d09c91e64db1d59c122bdf37daf96dfcaa7740d9a63a5e72` |
| `gpu-job` | `dc80f5a05218885672151ecfdde278872e065117a0b689885439b6a338c51bed`, built on Buildbox-2 from `b84a1f6a`; source unchanged since |

The package's series also holds `0474`-`0475`, so this image includes the touchscreen
changes. The DTB reads GPU, I2C7, RT5735 and MFGSYS `okay`, the rail 1.0 V, eight domain
nodes in total. `System.map` now has `alloc_io_pgtable_ops`.

## Safety assessment

This changes a rail, clocks and power domains. It writes no partition except the
guarded boot2 install.

**Limits.** VGPU fixed at 1.0 V by a min = max constraint and checked by the driver;
no OPP table, devfreq or governor can change it. Clock 26 MHz, then at most 364 MHz by
explicit parameter, refused above 365 MHz. Start refused at 55 C on `soc-thermal`.
Jobs stop at 65 C. At most 100 jobs in the first run, 1000 in the tool, 1 s wait each,
60 s limit on the tool. Then everything unloads.

**Protection that stays armed.** The 95 C hot trip, 110 C critical trip, 117 C hardware
reset and 60 C battery trip remain built in. The `soc-thermal` zone reads the maximum of
its banks, including bank 1, which the vendor assigns to the GPU sensor `MCU4`.

**Not available.** There is no cooling device, so nothing throttles the GPU; the limit
is the finite run. Rail voltage is the regulator's register, not a measurement. The GPU
clock is the mux register and the clock framework's rate, not a measurement.

**Risks and recovery.** A rail on before an unready sequence could stress the block; the
sequence is ordered and bounded to prevent that. A bus access to an unprotected or
unpowered block can hang the SoC with no log. The recovery is the watchdog or the
reviewed path. Any heat, charging anomaly or unexplained reset stops testing, per
[SAFETY](../../docs/SAFETY.md).

**Never read `clk_summary` with `clk-mt6797-mfg` loaded and the GPU off.** It reads the
gate register in an unpowered block. The test unloads that module for this reason.

## Associated code

- [`0476`](../../patches/proposals/0476-pmdomain-mediatek-describe-the-MT6797-MFG-domains.patch)
  MFG domains; [`0477`](../../patches/proposals/0477-drm-panfrost-add-the-MT6797-power-sequence.patch)
  Panfrost sequence; [`0478`](../../patches/proposals/0478-arm64-dts-mediatek-gemini-enable-the-Mali-T880-on-th.patch)
  device tree.
- [Fragment](../../configs/gemini-a53-station-gpu.fragment), in profile
  `mt6797-a53-station-a72`.
- [`gpu-job.c`](gpu-job.c): identity and Write Value jobs. Job layout from Mesa
  `src/panfrost/genxml/v4.xml`. Build on Buildbox with
  `aarch64-linux-gnu-gcc -O2 -static -o gpu-job gpu-job.c`.
- [`gpu-test.sh`](gpu-test.sh): load, record, run, unload.

## Procedure

Each step is a separate custodian request, with the package and hashes.

1. Boot the new image. Confirm the station is otherwise unchanged and read the same
   registers. No module loaded.
2. `gpu-test.sh probe`: load, identify, unload, 26 MHz.
3. `gpu-test.sh job`: 100 jobs, 26 MHz.
4. `gpu-test.sh job 1`: 100 jobs, about 364 MHz, only if 3 passed.

## Decision table

| Observation | Meaning | Next |
| --- | --- | --- |
| Boot 1 differs from the baseline in MFG state, or a station service regresses | The image is not inert | Stop, diagnose. No load |
| `insmod rt5735` fails on product ID or I2C | Rail or bus wrong | Stop. No GPU load |
| VGPU not 1.0 V after that module | Constraint not applied | Stop |
| Protection assert times out | Bits do not ack with MFG off | Stop, reread vendor path |
| Domain or SRAM timeout | Rail, LDO or clock missing; compare `PWR_STATUS`, `MFG_SRAM_CON` | Stop, unload, diagnose; one change at a time |
| Load hangs or resets the SoC | Bus access to an unready block | Preserve pstore, recover, no repeat until diagnosed |
| Identity is `0x880`, four cores | Probe shown | Next step |
| Identity wrong or GPU reset timeout at 26 MHz | Possibly the low clock | Try `mt6797_parent=1` once, then stop |
| Job faults or times out at 26 MHz | Log the exception, compare with `mt6797_parent=1` | One retry at that clock, then stop |
| 100 jobs pass, unload clean, domains and LDO enable read off | Done at that clock | Next step, or record |
| Unload warns or a domain stays on | Off sequence wrong | Stop, reboot before another load |
| 65 C stop | Unexpected at this load | Stop and investigate |

## Observations

### Run 1, boot `1f79ebb0`, package `9e652c87`: `gpu-test.sh probe`, 26 MHz

- Image booted, step 1 clean. Battery 91% and not charging by owner approval, SoC 32.5 C.
- The RT5735 answered with its product ID and bound. It read 975000 uV and disabled, so the
  loader leaves that set point. The module moved it to 1000000 uV with the rail still off.
  It is bus `1-001c` on this image, not `7-001c`: only the numbering differs.
- `clk-mt6797-mfg` logged `Trying to register duplicate clock ID: 1`.
- `panfrost` logged `of_clk_hw_onecell_get: invalid index 1`, and probe failed with -2.
- `rmmod clk-mt6797-mfg` oopsed in `clk_hw_unregister` at a garbage address, leaving the
  module stuck. Device alive, tainted, SoC 32 C. The others unloaded.
- After: `PWR_STATUS`, `MFG_ASYNC_PWR_CON`, LDO enable and rail read as before the run.

**Cause, from the source.** `mtk_clk_simple_probe()` allocates a table of one slot per clock,
and the binding's only MFG ID is 1. The gate register read past the table, found garbage and
refused as a duplicate, so no clock existed. Panfrost's first lookup got -EINVAL, which
`clk_get()` turns into -ENOENT through clkdev. The removal then unregistered the garbage.

**Effects.** That lookup is the first step in `power_early`, so none of the LDO, reset,
protection, rail-enable, domain or GPU register steps ran. The only rail write was the set
point. No GPU register was accessed.

`0480` gives the module a probe of its own, sized by `CLK_MFG_NR`. Binding, DTB and image are
unchanged, so the same image can run it after a reboot.

### Run 2, boot `b4bbb55e`, new `clk-mt6797-mfg`: `gpu-test.sh probe`, 26 MHz

First GPU power-on on mainline. Owner-approved, battery 90% and not charging, SoC 31.7 C at
start, peak seen 32.4 C. Exit 0, no Oops, tainted 0.

- `mali-t880 id 0x880 major 0x1 minor 0x0 status 0x8`, `shader_present=0xf`, `l2_present=0x1`,
  `tiler_present=0x1`, `as_present=0xff`, `js_present=0x7`, revision `0x1008`.
- Log: GPU clock 26000000 Hz, VGPU on at 1000000 uV, `MFG_ASYNC_CON` `0x0` to `0xa`.
- `CLK_CFG_1` read `0x00010100`: `mfg_sel` on, parent `clk26m`. `CLK_MISC_CFG_0` bits read
  `mfg_52m_sel` on `univpll2_d8`, which the clock framework reports as 156 MHz. MFGPLL went
  from running to off (`0x1000c240`), with no write of ours.
- LDO trims and enable read back as written. Bit 15 of `0x10001fe4` kept.
- After unload: MFG domains off, protection bits 21/23 set in both `PROTECTEN` and `STA1`, LDO
  enable off, rail off. Vendor order on power-off held. The trims stay; the vendor's do too.

**Not as designed.** `PWR_STATUS` read MFG off with VCG gated right after the probe, then on after
`gpu-job` with no job, though `no_runtime_suspend` should keep them on. So the domains went off
and came back with protection released and BG3D running, which the vendor never does. Nothing
faulted. No jobs run until this is explained.

### Run 2b, same boot: a second load, with runtime PM reads

Exit 0, no fault. `runtime_status=active` throughout, domains on at every read until unload,
then off. `runtime_suspended_time` stayed at 208 ms, and that attribute accrues only while
runtime PM is enabled and the device suspended, so those 208 ms belong to run 2 (inference). So
the device itself suspended on the first load, with the usage reference held, and did not on the
second. Upstream's remove also leaves one reference behind, so an unbalanced drop on each load
would look like this. What drops it was not found from the source.

`0481` uses `pm_runtime_forbid()`, which blocks suspend regardless of the count, and logs the
count at the end of probe. Only a first load on a fresh boot can check it.

## Analysis

Run 1 tested only the rail provider and the clock module. Run 2 shows the power sequence works once, from modules, and the GPU answers with the expected identity. It does not yet show a job.

## Conclusion

Not yet run: this is a build, not hardware support. Compile checks passed in the development VM on the station tree:
`Image`, modules, the station-a72 DTB with `CHECK_DTBS`, and `dt_binding_check` of the
GPU binding, which found nothing in the nodes touched here.

## Follow-up

Depends on the result. If the jobs pass: a shader job through Mesa, a voltage review,
OPP table and cooling device, and `domain-supply` on MFG_ASYNC, the upstream shape once
the regulator can be built in.
