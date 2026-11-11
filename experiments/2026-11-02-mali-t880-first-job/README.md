# Experiment: first Mali-T880 job on the station

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-02-mali-t880-first-job` |
| Status | `completed`: shaders, DVFS to 520 MHz and idle power-off work from modules, by default; the governor caps one step at a false temperature, not shown under real heat |
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

### Run 3, fresh boot `336cfaa9`, `panfrost.ko` `89a6ba8a`: `gpu-test.sh probe`, then `gpu-test.sh job`, 26 MHz

Image and DTB as before, commit `bd3aebd1` for the module, battery 90% and not charging.

- Probe, first load of the boot: exit 0. `control=on`, `runtime_status=active`,
  `runtime_suspended_time=0` at every read; `PWR_STATUS` `0x2B003F5E` at every read while
  loaded, so all six MFG domains stayed on. Log: `runtime PM usage count 1 at the end of probe`.
- Jobs, second load: `job 0: ok in 1247 us`, `job 99: ok in 754 us`, both exception status `0x1`,
  `passed 100 of 100 jobs`. Each job zeroed a word seeded with a non-zero value, and the tool
  fails at the first that does not; it prints the status of the first and last only.
- SoC 32.3 to 32.9 C across the run. Usage count 2 on this load.
- After unload: MFG domains off, LDO enable off, protection bits 21/23 set in `PROTECTEN` and
  `STA1`, `mfg_sel` gated, rail off. No module left. Tainted 0, and no fault, Oops, warning or
  scheduler timeout from the GPU in the log.

### Run 4, same boot: `gpu-test.sh job 1`, about 364 MHz

Owner-approved, same modules and image, battery 91% and not charging, one run, exit 0.

- Log: `GPU clock 364000000 Hz`, `VGPU on at 1000000 uV`. `CLK_CFG_1` read `0x02010100`: on, parent
  `syspll_d3`. MFGPLL stayed off.
- Identity as before. `job 0: ok in 333 us`, `job 99: ok in 131 us`, both status `0x1`,
  `passed 100 of 100 jobs`. SoC 31.9 to 32.6 C.
- After unload: domains and LDO enable off, tainted 0, no GPU fault in the log. `CLK_CFG_1` read
  `0x82010100`: gated, parent left on `syspll_d3`. That is expected: the module does not restore
  the mux, and sets it on every load.

### Run 5, boot `9d0a3335`: first shaders, through Mesa

Image from `f297381e`, `Image.gz` `3bf81854`, package `be518bd1`, with the GPU modules byte-identical
to run 3 (no GPU change, only other sessions' patches). Tool from `fbe7061d`: [`gpu-gles.c`](gpu-gles.c)
and [`build-mesa.sh`](build-mesa.sh), Mesa 24.3.4, bundle `SHA256SUMS` `34254eee`, loaded through its
own loader from `/run`. Battery 91% and not charging. One run at each clock, exit 0 both.

| | 26 MHz | about 364 MHz |
| --- | --- | --- |
| Renderer | `Mali-T880 (Panfrost)`, `OpenGL ES 3.1 Mesa 24.3.4` | same |
| Frames | 20 of 20 correct | 20 of 20 correct |
| Frame 0 | 21448 us | 5921 us |
| Frame 19 | 4229 us | 1357 us |
| SoC | 31.5 to 31.7 C | 31.5 to 31.7 C |

Each frame clears a 64x64 image, draws one triangle and reads it back. The tool fails unless the
middle holds this frame's red value, from a uniform, and the corner still holds the clear. Domains on
while loaded, off after, LDO enable off, tainted 0, no GPU fault, reset or timeout in the log.

### Runs 6 and 7, same boot: sustained shader load, about 364 MHz

Limits: from the vendor's adaptive cooler in
[MT6797 thermal management](../../docs/hardware/mt6797-thermal-management.md), stop at SoC 75 C (its
target Tj) and refuse to start at 55 C (its exit). Battery stops at 46 C (where the vendor cuts charging).
Stopping at them is our inference, since there is no cooling device; the vendor keeps running and cuts a
power budget. The owner asked for these limits. Battery 91% and not charging; on USB power (inference).

| | Run 6 | Run 7 |
| --- | --- | --- |
| Load | a triangle over 1/8 of 512x512, 16-step loop | every pixel of 512x512, 32-step loop |
| Duration | 60 s | 60 s |
| Frames | 33543, 559/s | 5950, 99/s |
| Pixel, all frames equal | 128,139,0 | 128,66,0 |
| SoC peak, start | about 35 C, 32.9 C | 35.6 C, 33.3 C |
| Battery voltage | flat | 4.25 V down to 4.21 V under load |

No GPU fault in either. Run 7 used `unstable_ioctls=1`, so `tainted=64` on that boot, for the counter window:

- Over 5.003742 s, block 0 word 6 (read as GPU active) was `0x606e7019`, 323 M/s. Blocks 3 to 6 word 4
  ran 310 M/s each, within 0.05% of each other.
- So **all four cores work and share the load evenly**, and the clock is at least 323 MHz. 3.26 M
  cycles per 10.08 ms frame fits 364 MHz at 89% busy, with the read-back between frames (inference: the
  counter names and the busy fraction are not independently confirmed).
- The 139 pixel of run 6 does not match a CPU evaluation (232), so that loop ran on the GPU, with its
  own `sin`.

A 2.3 C rise fits the 0.53 W the vendor's coefficient gives at this point (1461 uW/MHz/V2, a calculation). Run 10
settles the sensor side.

### Run 8, same boot: 442.5 MHz, first use of the MFGPLL

`0483`, one run, 60 s, exit 0, no fault. 442499878 Hz in the log, `CLK_CFG_1` bits 25:24 = 1, `MFGPLL_CON1`
`0x821104EC`. GPU active 394 M/s, cores 377 M/s each, 7228 frames, a ratio of 1.215 to run 7 against
1.216 for the clocks. Same pixel, 128,66,0. SoC 32.9 to 36.5 C, a rise of 3.6 C against 2.3 C at 364 MHz. That
is weak evidence, from one comparison, that the sensor sees GPU load.

`MFGPLL_CON0` stayed `0x101` after unload. The counts read `prepare=1 enable=0` on `mfg_sel`, `mfgpll_ck`
and `mfgpll` with no GPU module loaded, so `mtk_pll_unprepare` never ran. From the source, the holder is
`of_syscon_register`: it attaches the first clock of a `syscon` node to its regmap, and
`regmap_mmio_attach_clk` prepares it for good. The `scpsys` node is a `syscon` whose first clock is
`CLK_TOP_MUX_MFG`, a leftover from the legacy driver. So `mfg_sel` is prepared from boot, which also explains
why the first load dropped the loader's running PLL. That regmap also enables the mux around each SPM access
(from the source; not observed). `0484` parks the mux at unload. Removing the leftover clock is an
image change, batched below.

### Run 9, same boot: 520 MHz, the vendor's pre-EEM point

`0484`, one run, 60 s, exit 0, no fault. 520000000 Hz in the log, 8226 frames, same pixel. GPU active 453.5 M/s,
87% of the clock, cores 433 M/s each. Frame gain 1.138 against 1.175 for the clocks, so something outside the
GPU clock now takes a larger share (read-back or memory, inference). SoC 33.0 to 37.3 C, a rise of 4.3 C,
against 3.6 and 2.3 C at the lower clocks. Battery 25.9 C at most, 4.231 V.

After unload, `MFGPLL_CON0` `0x0`, `CLK_CFG_1` `0x80010100`, `mfgpll` prepare 0, `mfg_sel` prepare 1: `0484` works.
The log's usage count grew one per load, 6 here, from the leak in `panfrost_remove`, which `0485` fixes.

The run stop moves to 58 C from here, the first CPU cooling trip in the policy recovered from Gemian's files.
The source's 75 C target is real, but that policy starts cooling far earlier and there is no cooler here.

### Run 10, boot `145d8512`: the new image, package `6fe0e33d` (`0483`-`0489`)

Boot normal: Wi-Fi associated, tainted 0, no GPU module, MFG off. Battery 91% and not charging. The loader left
the MFGPLL running at 500.5 MHz with `mfg_sel` prepared, as run 8's reading predicted.

**Idle power-off**, first load of the boot, about 364 MHz, 200 frames with 100 ms gaps: exit 0, 200 of 200 correct,
usage count 0 at the end of probe. `runtime_suspended_time` rose 8107 ms during the frames. `PWR_STATUS` read MFG off
when idle and on after a frame, and the first load stopped the loader's PLL. With the 50 ms autosuspend in a 100 ms
gap, a suspend lasts at most about 50 ms, so that time took at least 162 power cycles, likely about 200 (arithmetic;
cycles were not counted). VGPU and the LDOs stayed on throughout, by design.

**Per-bank**, second load, 520 MHz, 60 s: 8328 frames, exit 0, no fault, usage count 1, so the leak is fixed.

| Bank | Start C | After 5 s | End of load | 1 s after unload |
| --- | --- | --- | --- | --- |
| 0 | 31.3 | 33.1 | 35.1 | 34.9 |
| **1** | **30.2** | **35.4** | **37.7** | **34.2** |
| 2 | 32.9 | 33.8 | 36.2 | 35.7 |
| 3 | 32.9 | 34.1 | 36.2 | 35.6 |
| 4 | 32.9 | 33.9 | 36.2 | 35.4 |
| 5 | 32.6 | 34.1 | 36.5 | 35.3 |

Bank 1 starts coolest, rises 5.2 C in 5 s against 1 to 2 C elsewhere, peaks highest and falls 3.5 C within a
second of unload. That **answers the sensor question**: bank 1 is the bank nearest the GPU, and `soc-thermal`'s
maximum follows it, so the 58 C stop does see the GPU. That bank 1's sensor is named `MCU4` is the vendor's source,
not a measurement. The other banks warm too, from shared heating or the small CPU load.

DVFS, the fourth step, has not run. It waits for the owner, since it is the first run below 1.0 V.

### Run 11, same boot: DVFS, `DVFS=1 ./gpu-test.sh load`

Owner-approved, one run. 8277 frames in 60 s, within 0.6% of fixed 520 MHz, same pixel, no fault, SoC peak 38.0 C.
`trans_stat`: four transitions, 442.5 to 238, 238 to 520, 520 to 442.5, 442.5 to 238. Time in state: 520 MHz 59956 ms,
238 MHz about 2.4 s, 442.5 MHz about 120 ms, 365 MHz none. The rail read 850000 uV at 238 MHz while idle.

So rate and voltage changes work on a running GPU, including the parked PLL divider changes. **The points below 520 MHz
are not validated under load**: no shader work ran below 1.0 V for any length of time this run can show.

### Run 12, same boot: first pinned load, refused

`panfrost` refused before any power step: `VGPU at 850000 uV`. Run 11's unload left the rail at the lowest point, and the
DVFS path checked for its start voltage without setting it. No shader work ran. `0490` raises the rail before enabling.

### Run 13, same boot: each OPP under load, then idle power-off with DVFS

With `0490`, one run each, no fault, same pixel, 128,66,0, at every point. The rail reads come from the script's state lines, not
continuously.

| Pinned | Rail | Frames in 30 s | Slowest | SoC at end |
| --- | --- | --- | --- | --- |
| 442.5 MHz | 937500 uV | 3608 | 13 ms | 35.3 C |
| 365 MHz | 912500 uV | 2988 | 15 ms | 34.7 C |
| 238 MHz | 850000 uV | 2056 | 18 ms | 33.5 C |

Idle power-off with DVFS, 300 light frames with 100 ms gaps: 300 of 300 correct. Those frames kept devfreq at 238 MHz, so no rate
change happened around a power cycle.

**Limits.** One chip, one run each, 30 s, cool and near room temperature. These are table values with no EEM, and vendor EEM
exists because margins vary with temperature and unit, so the hot end is not covered.


### Run 14, same boot: idle power-off with DVFS, bursts and gaps

`BURST=30 GAP_MS=200`, 60 s, exit 0, same pixel, no fault, suspended time rising. But only 5 transitions: 38 s at 520 MHz and under
a second in the others. A suspended GPU stops devfreq's monitor, and with a 50 ms autosuspend against 50 ms polling it almost never
samples an idle GPU, so gaps alone cannot lower the rate. So rate changes around power cycles remain untested. The next pattern
adds frames that keep the GPU awake but barely busy.

### Run 15, same boot: idle power-off, DVFS, bursts and light frames

`BURST=30 GAP_MS=200 LIGHT=30`, 60 s. 85 transitions across all four OPPs. Frames right, exit 0, but **one job timed out and then
faulted**, about 3.7 s in, on the fragment slot, with the same job chain address on both lines, then recovered, with no further fault in the
remaining 57 s:

    gpu sched timeout, js=0, config=0x3b00, status=0x8, head=0xa10a480, tail=0xa10a480
    js fault, js=0, status=INSTR_INVALID_ENC, head=0xa10a480, tail=0xa10a480

An invalid instruction read could be margin around a rate or rail change, or software: state lost across a power cycle, cache or TLB
handling, or the new light frames. This run is the first with resume and many rate changes together, and the first with light frames. So
**idle power-off with DVFS is not admitted**. The tool's exit code and pixel check could not see this, so `gpu-test.sh` now fails on any GPU
fault since the run began. Earlier runs were each searched for these by hand, and clean.

### Run 16, same boot: the three causes separated

Same pattern, 120 s each, gated on faults and logging each rate change.

| Run | Domains cycle | Rates move | Up steps | Faults |
| --- | --- | --- | --- | --- |
| A, fixed 520 MHz | yes | no | none | 0 |
| B | no | yes | 71 | 1 |
| C | yes | yes | 142 | 3 |

All four faults came after a 238 to 520 MHz step: three job timeouts 506 to 522 ms later, the job timeout, and one
`INSTR_OPERAND_FAULT` 219 us later. So 4 of 213 up steps, and power cycling and light frames are not needed. That was the only up step in
these runs, so the other up steps are not excluded.

The vendor waits the slew time plus 350 us after each GPU voltage rise (`mt_gpufreq_volt_switch`). We waited about 37 us, from the
ramp delay in our DT. `0492` adds the 350 us. This fits the evidence, the largest voltage rise failing rarely, but it is a hypothesis until a
clean run says so: at about 1.9% per step, 300 clean steps would be chance only about 0.3% of the time.

### Run 17, same boot: the settle hypothesis rejected

With `0492`, the same pattern for 300 s: 3 faults in 177 up steps, 1.7% against 1.9%, all after a 238 to 520 MHz step: 7 of 7 now, with varying
codes (`INSTR_INVALID_ENC`, `INSTR_OPERAND_FAULT`, `INSTR_INVALID_PC`), which suggests a shader core reading garbage (inference). So **settling time is
not the main cause**. The regulator core runs the wait on every selector change; nothing in the log confirms it on the device. `0492` matches the vendor and
stays. A rail droop is not excluded: the rail has only been read as a register.

That step is the only up step ever taken, and the only one with the GPU busy by construction, so those two cannot yet be told apart. Down
steps have never faulted, but run at low use. The vendor commits rates from a GED timer, and no drain was found at that level; not every caller was traced.

### Run 18, same boot: rate steps under full load

60 s each with the rate moved every 100 ms between two OPPs, at steady full load. About 291 steps each way per run.

| Pair | Post-dividers | VCO jump | Job timeouts |
| --- | --- | --- | --- |
| 238 and 520 MHz | 8 and 2 | 864 MHz | 6 |
| 442.5 and 520 MHz | 4 and 2 | 730 MHz | 3 |
| 238 and 365 MHz | 8 and 4 | 444 MHz | 4 |
| 365 and 442.5 MHz | both 4 | 310 MHz | **0** |

Dividers and VCO from the driver's arithmetic and the registers read at 238, 442.5 and 520 MHz, not 365. Three runs lose jobs and the one with no divider change does not.
Rail steps do not sort them, and all four park the mux, so neither the rail nor the park alone is the cause. Timing the 500 ms job
timeout back, B's and D's faults land on a down step, so it is not up steps either (inference, softer in A). The likely mechanism is a relock across a
divider taking longer than the 20 us before the mux returns, though that is unmeasured, and the vendor has the same 20 us. Its table may simply cross a divider less.
`0493` drains the GPU before a rate change, which covers any such mechanism, from the module.

### Run 19, same boot: the drain

`0493`, about 70 s at the same pairs, then the realistic pattern for 300 s. Pixel the same throughout, tainted 0.

| Pair | Steps each way | Faults, was | Slowest frame, was |
| --- | --- | --- | --- |
| 238 and 520 MHz | 336 | 0, 6 | 19 ms, 554 ms |
| 442.5 and 520 MHz | 334 | 0, 3 | 14 ms, 602 ms |
| 238 and 365 MHz | 325 | 0, 4 | 19 ms, 598 ms |
| 365 and 442.5 MHz, control | 324 | 0, 0 | 14 ms, 18 ms |

No change was skipped, and frame rates did not fall. Realistic pattern with idle power-off: 177 up steps, 0 faults, where the same count gave 3. `MFGPLL_CON1`
read `0x820E09D8` at 365 MHz, so that pair does share a divider. At about 1% per step, three clean pairs of 300 would be chance about 0.01% of the time.

**What this does not show.** That the relock is the mechanism: it is still unmeasured, and the drain removes the symptom. A crossing with no job may still disturb a job that starts next, though nothing here
shows it. These jobs are short, so a job over 200 ms, which skips the change, has not been tried, and sustained long jobs could hold the rate where it is. One chip, about 35 C, so the hot end,
where the missing EEM matters most, is not covered.

### Run 20, same boot: the new defaults

`0494`, DVFS and idle power-off on by default. 60 s of full load: 8176 frames, same pixel, 0 faults, `control=auto`. 20 small frames then idle: all
correct, suspended with MFG off a second later. No GPU fault, tainted 0.

The write of the top state to the cooling device did pull the rate to 238 MHz, but it came back 93 ms later, and the state read 0 by the next check. The
cause is probably the thermal core rewriting the state from a zone below its trip (inference). So **the cap at 58 C is not shown**: the device can lower the rate once,
and nothing shows it holds, or that the real trip applies it. This run peaked at 37.5 C.

### Run 21, same boot: the cooling cap through thermal emulation

Owner-approved, as it masks `soc-thermal`'s 95 and 110 C trips for up to 20 s; the 117 C hardware reset and the battery zone do not read that value. With a load at 520 MHz, `emul_temp` read a false 60 C from 20 to 40 s:
`cur_state` went to 1 and the rate to 442.5 MHz, and both held for the whole window, then returned. Frames per 5 s went from about 670 to 587 and back to 672, in proportion to the clock. No fault, no true bank near 58 C, zone reading true afterward.

So **the governor caps one step and holds, at a constant false temperature**. A constant value has no rising trend, which fits `step_wise` raising the state only once (inference). This does not show a cap to the lowest OPP, or any cap under real heat, or that one step would stop real heating. Real load has not got past about 38 C.

### Run 22, boot `505d2716`: first load of a boot with the defaults, with the display bound

Image `677021f2`, package `967983c2`, the native display driver holding `drm`, which differs from the runs above (`d1ad67a4`). `panfrost.ko` is byte-identical to run 21's, `d5a92ac7`.
`./gpu-test.sh load`, one run, exit 0: `0x880`, four cores, DRM minor 1, 8310 frames, slowest 26 ms, same pixel 128,66,0, 0 GPU faults.
The device suspended at once on load (`runtime_suspended_time` 53 ms, `PWR_STATUS` MFG off), ran 59976 ms at 520 MHz, then idled off. After unload, MFG off, LDO enable off, protection set, `mfg_sel` gated, `MFGPLL_CON0` `0x0`. Tainted 0. The display's modules stayed, and
sampled display registers were unchanged. The owner's view of the panel is the display session's to record.

### Run 23, boot `a22a4ca8`: the new image, then a 10-minute soak

Image `02e045fa`, package `8f569751` from `c546644d`, with the native display bound. `panfrost.ko` the same bytes as before; `drm_shmem_helper` rebuilt (`9687ea4f`). Unattended.

The first load, 60 s on defaults, was clean: `0x880`, 8101 frames, 0 faults, MFG off after. The 10-minute load on defaults, at 520 MHz for 599996 ms: 82297 frames, slowest 19 ms, the same pixel throughout, 0 faults, tainted 0.

| Minute | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Bank 1, C | 27.7 | 34.7 | 35.6 | 36.2 | 36.5 | 36.5 | 37.0 | 36.8 | 37.2 | 37.4 | 36.5 |
| SoC, C | 30.9 | 34.7 | 35.4 | 36.1 | 36.3 | 36.7 | 37.0 | 36.8 | 37.2 | 37.4 | 37.5 |

Bank 1 led the others throughout. About 6.6 C over 10 minutes, still rising about 0.2 C a minute at the end, so not a hard plateau, but far from the 58 C trip. Battery 25.2 to 25.6 C. On a desk at room temperature, on USB power: one condition, which a pocket or a warm room would change.

## Analysis

The hypothesis held at 26 MHz: modules alone bring up the GPU with the vendor's power order, it
identifies as `0x880` with four shader cores, and it completes bounded jobs through its own MMU
and job interrupt, across repeated load and unload on one boot, at both clocks tested.

Run 3's first-load count of 1 is the forbid's own reference. The old hold would have had the same
count, so what suspended the device in run 2 is still not explained. `pm_runtime_forbid()` stopped
it in the one fresh-boot case tested. Upstream's remove leaks one reference on each unload, which
is why the count climbs; it is harmless here.

The Zero job uses no shader core; run 5 does, since the compiled vertex and fragment shaders carry the
uniform to the pixels the tool checks. A correct image at both clocks shows Mesa's compiler, the tiler,
fragment jobs and shader execution on this GPU. It cannot say how many of the four cores did the work.
Run 23's 10 minutes at 520 MHz reached 37.5 C, so this point stays far below the trip on a desk, by measurement. Before that, the temperature range said nothing about real load: the runs before run 6, and runs 6 and 7 only reach about 0.5 W by calculation.  Job times fell from 754 us to 131 us at the higher clock, which points
the same way as the registers but does not measure the clock. The rail is a register value and the clock is a mux register plus the
framework's rate. Neither was measured. Runtime-suspended domain cycling stays forbidden, so no
idle power saving exists: while loaded, the rail and the domains stay on.

## Conclusion

`confirmed` for the named unit, on the image with `Image.gz` `bef4c6d4` and these modules at `56cd6c6e`, at up to 38 C:

- The T880 probes, identifies as `0x880` with four cores, and runs Mesa 24.3.4 shaders with a correct image on all four cores under 60 s of full load.
- Each OPP from 238 to 520 MHz holds under pinned load, and changes between them run with no fault, on a drained GPU.
- Its domains power off when idle and return correctly.
- `soc-thermal` sees it through bank 1, and its governor caps the GPU one step at a false 60 C.

**Not shown:** a cooling cap beyond one step or under real heat; real-size rendering or a real application; the display path; any clock above 520 MHz; a measured rail or clock; the hot end, where the missing EEM matters
most; jobs over 200 ms, which skip a rate change; VGPU and the LDOs off at idle, which stay on. Nothing loads these modules at boot.

## Follow-up

1. A cap under real heat, which needs a load that reaches the trip.
2. VGPU and the LDOs off at idle, then `domain-supply` on MFG_ASYNC, the upstream shape, once the regulator can be built in.
3. The `scpsys` clock: it holds `mfg_sel` prepared from boot, and it is also what stops the loader's running PLL on first load, so removing it needs its own way to stop that PLL.
4. Whether a relock across a post-divider really needs more than 20 us, which would let the drain go. Built-in code, so an image.
5. Clocks above 520 MHz need rail voltages above 1.0 V, a separate decision.
6. Showing GPU output on screen, which belongs with the display work.
7. Before upstream: `0493` takes `rate_lock` in `run_job`, while the rate change under that lock can allocate in the regulator and I2C paths. That breaks the fence-signalling rule against waiting on reclaim, a deadlock in principle under memory pressure, from review, not observed. `run_job` already calls `pm_runtime_get_sync`, which has the same issue. Fixing it needs a test, so it did not go in overnight.
8. Under a real desktop, wlroots with qutebrowser on Arch, importing a dma-buf as a Panfrost handle hit `WARN_ON(bo->base.madv != PANFROST_MADV_WILLNEED)` in
   `panfrost_gem_open` twice, untainted, rendering fine (station-work-91). The buffer resolved to a Panfrost object its owner had marked purgeable. The madvise ioctl
   does not refuse that for a shared object, and its own comment expects userspace not to. This is upstream code that the MT6797 patches do not touch. The risk, from
   the source and not seen: under memory pressure the shrinker could purge pages another process is using. Userspace was Mesa 26.2.6, Qt WebEngine 6.11.3 and qutebrowser 3.7.0. A check under memory pressure has not been run.
9. On the same card desktop (boot `2d9dc5ae`, Umbriel with effects), three job timeouts in 2 s, each `status=0x8` (still active), two on `js=0` fragment jobs and one with config
   `0x3301`. The desktop recovered. This is not the import warning above. It is the same signature as the post-divider faults before `0493`, but rate logging was off, so it cannot be placed
   against a rate change. The other candidates are a job truly longer than the 500 ms timeout at a low rate, or a userspace or GPU fault. `0668` lets
   `mt6797_log_rates` be switched on through sysfs, without unloading the driver the compositor holds. The display's `swiotlb buffer is full` lines nearby
   are the display's own DMA mapping, and nothing ties them to the GPU.
   At 460 s of uptime that boot had 44 rate changes, most of them crossing a post-divider (14 from 238 to 520 MHz alone), with DVFS and idle-off on and logging off. The
   driver had the drain, so either a change slips past it, or the timeouts have another cause. Rate logging on the next occurrence decides it.
   Again on boot `58bcf387` (kernel from `47b11c27`, with `0493` and `0668`): 4 timeouts in about 7 minutes, against 108 rate changes, 37 of them 238 to 520 MHz. The GPU's
   power-allocator cooling sat at 0 of 3, so `0687` is not the cause. A job starting just after a divider change, while the PLL may still be settling, is not covered by
   the drain (inference). But in run 19 many jobs started within milliseconds of a change, with no fault, so the log is still needed.
   About a minute after two of those timeouts, a video showed part of a desktop panel holding fragments of another window's text on alternate frames, with the
   next frame clean. A buffer left half-written by a killed job, and then kept by a client that redraws only damaged regions, would show on one of its two buffers only,
   until it is redrawn whole (inference). Whether this needs a preceding timeout, and whether a fresh surface clears it, is not yet known.
   With the rate log on, the same boot caught two more. The rate fell to 238 MHz at 884.44 s, an idle drop. The governor then asked four times to go back to 520 MHz, and
   each was skipped by the drain as not idle. The jobs timed out at 885.25 and 885.83 s, well away from any rate change. So no change slipped past the drain. A job long at
   238 MHz blocks the very raise that would shorten it, and passes the 500 ms timeout. The drain turns a slow job into a timeout. In this pattern it is the
   cause, not the cure (inference from one capture).

   The way out without the drain is to never cross a post-divider. The vendor's own split (type 12, cid 2 to 4) uses post-divider 4 for 250 to 900 MHz, and 8 only below that.
   Mainline picks 2 at 520 MHz, because the MFGPLL's minimum VCO defaults to 1000 MHz. With a 1400 MHz minimum, 365, 442.5 and 520 MHz all use 4. Dropping 238 MHz, which idle
   power-off makes worth little, then leaves no crossing at all. A floor of 365 MHz through devfreq's `min_freq` tests the first half on the running boot.
   `0690` gives the MFGPLL the vendor's divider table (4 from 250 to 900 MHz, 8 below). `0691` drops 238 MHz and raises the rail floor to 0.9125 V. `0692` drains only for a change that crosses
   a divider, which the table no longer has. Compile-checked only; it needs a boot.
