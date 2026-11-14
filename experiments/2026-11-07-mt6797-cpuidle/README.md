# Experiment: idle states below WFI for the MT6797 clusters

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-07-mt6797-cpuidle` |
| Status | `running`: no per-core idle state exists on this firmware; hotplug on a dark screen and `mem` suspend through the vendor program (42 mA, 0678, lid close) work on D3; the 200 mA "awake regression" was the display relighting itself; `mem` suspend outside tests waits on USB, `soc-thermal` and display fixes after a resume; S2 next |
| Subsystem | cpuidle, PSCI `CPU_SUSPEND`, SPM, CPU hotplug, A53 cpufreq, A72 module |
| Device variant | Named Gemini PDA development unit, mainline station on boot2 |
| Date(s) | 2026-11-07 |
| Investigator(s) | Julien Etienne; Claude (analysis) |
| Tracking issue | none; [roadmap](../../docs/ROADMAP.md) section 2, Power |

## Question or hypothesis

Can idle CPUs in the three clusters (CPU0-3 and CPU4-7, A53; CPU8-9, A72) go
deeper than WFI on this firmware? If so, how? If not, what saves the idle
power instead, and how much is there to save?

Today the station has `# CONFIG_CPU_IDLE is not set` in
`mt6797-a53-station-a72`, and its DT has no `idle-states`. Every idle CPU runs
WFI.

## Summary

- **No PSCI state below WFI is usable on this firmware**, as the
  [power-management record](../2026-11-06-gemini-power-management/README.md#the-firmware-side)
  found. The two power-down parameters prepare the core and then wait in EL3
  for the SPM to cut power. A standby state is a plain WFI in EL3, so it saves
  nothing.
- **The vendor has no MT6797 per-core idle program to learn from.** Its MCDI
  state is off on MT6797 builds, and Gemian used only WFI. The MCDI program in
  the GPL tree does not fit the MT6797 SPM register map (inferred; see
  [Vendor evidence](#vendor-evidence)).
- **The vendor's other states are system states.** SODI, SODI3 and deep idle
  need exactly one CPU online and many clocks off. They are the SPM route
  (P4/P5) in the power-management record, not per-core cpuidle.
- **Hotplug is the power-down that works.** `CPU_OFF` really powers the core
  down: the firmware does the teardown when another CPU asks `AFFINITY_INFO`.
  R1b measured about 15 mA for CPU1-7 offline with the display blanked, at the
  boot clocks. 0645 brings the A72 cluster back after it went down.
- **So this record measures before it builds.** Stage C0 measures what is left
  to win once A53 cpufreq is at its idle points, split between the L cluster
  and the LL cores. It also shows whether a whole A53 cluster going down and
  up leaves the cpufreq clock driver's state intact, which has not been
  observed. C0 needs no new image, firmware call or register write.
- **Enabling `CONFIG_CPU_IDLE` alone gains nothing**, and a PSCI power-down
  state in the DT without the SPM side would hang every CPU at its first idle.
- **Idle A53s already retain (2026-11-08, observed in S0).** All eight A53s,
  CPU0 included, sit in hardware ("SPARK") retention when in WFI on the
  station. `tee1` turns it on for every core it powers up.
- **The vendor's way below WFI is known (2026-11-08).** One CPU (CPU0)
  online, an SPM program loaded from DRAM and kicked, then the CPU goes down
  through `CPU_SUSPEND` `0x1010000`, or stays in `wfi` at EL1 in a bring-up
  mode. Suspend needs nothing else; deep idle and SODI need many clocks gated.
  The programs can be read from the unit's `system.img` at runtime. See
  [the vendor sequence](#the-vendor-sequence-reverse-engineered-2026-11-08)
  and [MT6797 SPM sleep](../../docs/hardware/mt6797-spm-sleep.md).

## Provenance and environment

- Kernel: Linux 7.1.3, profile `mt6797-a53-station-a72`, patches through
  `0645` at `fd704dcd`.
- Upstream sources read: `drivers/cpuidle/cpuidle-psci.c`,
  `drivers/cpuidle/dt_idle_states.c`, `drivers/firmware/psci/psci.c`,
  `arch/arm64/boot/dts/mediatek/mt6797.dtsi` at
  [v7.1](https://github.com/torvalds/linux/tree/v7.1). The 7.1.3 stable tree
  does not change these paths for this purpose.
- Vendor source: Gemian Linux 3.18
  [`59e00a91`](https://github.com/gemian/gemini-linux-kernel-3.18/tree/59e00a9144d782e148332009a835b99c43382467),
  `drivers/misc/mediatek/base/power/spm_v2/` (`mt_spm_mcdi.c`,
  `mt_spm_internal.c`, `mt_idle.c`, `mt_idle_mt6797.c`),
  `drivers/misc/mediatek/base/power/include/spm_v2/mt_spm_reg_mt6797.h`,
  `drivers/misc/mediatek/base/power/cpuidle_v1/mt_cpuidle.c` and
  `drivers/clocksource/cpuxgpt_mt6797.c`. Read as evidence only; nothing is
  reused.
- Earlier records: [power management](../2026-11-06-gemini-power-management/README.md)
  (firmware disassembly, R1, R1b, P2f), [CPU clusters](../../docs/hardware/mt6797-cpu-clusters.md#53-idle-states),
  [A53 cpufreq](../2026-11-07-mt6797-a53-cpufreq/README.md),
  [all ten cores](../2026-11-01-mt6797-all-cores/README.md) (steps 1 and 2).

## What the firmware offers

From the private disassembly of `tee1` recorded in the
[power-management record](../2026-11-06-gemini-power-management/README.md#the-firmware-side):

| `CPU_SUSPEND` (`0xc4000001`) `power_state` | Firmware behaviour | Usable as an idle state? |
| --- | --- | --- |
| Type 0 (standby), any StateID | `wfi` in EL3, then return | Works, but it is WFI behind an SMC: no saving, more latency |
| `0x0010000` (power-down, core) | Clears the core's retention controls, waits unbounded for its `CPU_RET_STATUS` bit, saves the entry, flushes L1, then `dsb; wfi; b wfi` | Only with an SPM program that cuts power on WFI and restores it on an interrupt; without one the core never returns |
| `0x1010000` (power-down, cluster) | As above; the last core in a cluster also turns off the GIC CPU interface, leaves CCI and saves L2 and GIC state | As above |
| Affinity level 2 | Rejected | No system state through `CPU_SUSPEND` |

PSCI is 0.2, `PSCI_FEATURES` answers only for `SMCCC_VERSION`, and there is no
`SYSTEM_SUSPEND`. The secure firmware writes no SPM or MTCMOS control on
suspend and has no SiP call for idle or SPM.

`CPU_OFF` is different: the core enters WFI, and the firmware does the
hardware teardown when a controlling CPU calls `AFFINITY_INFO`. `CPU_ON`
powers it back up. The A72 cluster is reset and isolated again when its last
core goes down ([step 2](../2026-11-01-mt6797-all-cores/README.md#observations));
0645 redoes the board side before CPU8 comes back.

## Vendor evidence

**The vendor DT** gives every CPU two PSCI idle states:

| Vendor state | `arm,psci-suspend-param` | Entry / exit / min residency |
| --- | --- | --- |
| core power-down | `0x0010000` | 600 / 600 / 1200 us |
| cluster power-down | `0x1010000` | 800 / 1000 / 2000 us |

The vendor kernel never requests `0x0010000`. Every non-WFI vendor state is
`cpu_suspend(2)`, which is `0x1010000`, after an SPM program has been kicked
(`mt_cpuidle.c`, `mt_cpu_dormant_interruptible`).

**The vendor idle driver** (`mt_idle.c`) offers `dpidle`, `soidle3`, `soidle`,
`mcidle`, `slidle` and `rgidle` (WFI). On MT6797:

- `mt_idle_mt6797.c` sets the `mcidle` switch to 1 only with
  `CONFIG_CPU_ISOLATION`, and to 0 otherwise. Gemian's live idle statistics
  show only WFI used
  ([resource map](../../docs/hardware/mt6797-live-resource-map.md)).
- `dpidle`, `soidle3` and `soidle` require exactly one CPU online
  (`mcidle_can_enter` and the dpidle/soidle conditions) plus multimedia clocks,
  domains and PLLs off. They are system idle states built on separate SPM
  programs; their route is the power-management record's P4/P5.

**The MCDI program** in `mt_spm_mcdi.c` is a 597-word SPM PCM image named
`pcm_mcdi_ddrdfs_v6.1_20150629`, with the kernel driving it through a mailbox
at SPM `0x098`, per-core `WFI_EN` (`0x540`-`0x55c`) and `IRQ_MASK`
(`0x500`-`0x51c`) words, and per-core local-timer hand-off to the CPUXGPT
comparators. Read against the MT6797 map in the same tree
(`mt_spm_reg_mt6797.h`):

| What the program touches | What those offsets are on MT6797 |
| --- | --- |
| Pairs `0x208`/`0x248`, `0x20c`/`0x24c`, `0x210`/`0x250`, `0x214`/`0x254` | `0x208`, `0x20c`: unnamed; `0x210`, `0x214`: `MP0_CPUSYS_PWR_CON`, `MP1_CPUSYS_PWR_CON` (cluster, not core); `0x248`-`0x254`: `MP2_CPU2/3`, `MP3_CPU0/1` (cores this chip does not have) |
| Pairs `0x21c`/`0x260` to `0x228`/`0x26c` | `0x21c`: `MP3_CPUSYS_PWR_CON`; `0x220`-`0x228`: `MP0_CPU0-2_PWR_CON`; `0x260`-`0x26c`: unnamed |
| MT6797's A53 core controls `0x220`-`0x23c` | only three of eight touched, as part of other pairs |
| MP2 (A72) controls `0x218`, `0x240`, `0x244` | none |

The MP2 offsets in that header match what the project read live during the A72
work (`0x10006218`, `0x10006240`, `0x10006244`). **Inference:** the program was
written for another chip's SPM layout and is not an MT6797 MCDI program, which
fits the switch being off. It also has no A72 path. It also writes the infra
bus-protection registers `0x10001220`/`0x10001228`, which mainline SCPSYS
writes too. No MT6797 per-core SPM program exists in the evidence. A public
decoder covers only part of the PCM instruction set
([hardware page](../../docs/hardware/mt6797-spm-sleep.md#3-the-spm-program-files)),
so the project cannot write its own.

## What mainline would need, if a state ever exists

Recorded so the first real state does not rediscover them; nothing here is
proposed for a build now.

- **DT:** a node under `/cpus/idle-states` with `compatible = "arm,idle-state"`,
  `arm,psci-suspend-param`, `entry-latency-us`, `exit-latency-us`,
  `min-residency-us` and `local-timer-stop` (the per-core architected timer
  stops when the core is off), plus `cpu-idle-states` on CPU0-7 only.
- **Config:** `CONFIG_CPU_IDLE`, a governor (`teo` or `menu`) and
  `CONFIG_ARM_PSCI_CPUIDLE`, which is `bool`, so built in.
- **The A72s:** `psci_cpuidle_probe()` walks every present CPU and fails the
  whole driver with `-ENODEV` at the first CPU with no DT idle state. CPU8-9
  are present even under `maxcpus=8`. Either they get a state, or the driver
  needs a skip like 0641 did for cpufreq-dt.
- **No state before its SPM side:** a built-in PSCI driver would request the
  state at the first idle of every CPU during boot, and without the SPM
  program every CPU would stay in the EL3 loop. The state and its SPM side
  must be in the same image, or the state must come from a module that
  registers its own cpuidle driver after the SPM side is up. In 7.1,
  `psci_cpu_suspend_enter()` and arm64 `cpu_suspend()` are not exported, so
  that module needs one built-in export.
- **Broadcast timer:** `local-timer-stop` needs a broadcast clockevent. The
  upstream `mt6797.dtsi` has no GPT node. arm64 sets up the hrtimer broadcast,
  which keeps one CPU in WFI. That would do for a first test.
- **Wake:** the SPM must see an interrupt for a powered-off core. With GICv3,
  nothing on the core-level path sets the redistributor's sleep state.
  Whether the SPM's per-core interrupt lines are enough is unknown.
- **Locks:** any SPM program shares the SPM with SCPSYS (domain power, bus
  protection) and with the DVFSP semaphore owners (the cpufreq clock driver
  holds SEMA3 for MCUMIXED). One owner must serialise them.

## Interactions with the CPU drivers

**A53 cpufreq (`clk-mt6797-mcusys`).** The driver faults and refuses changes if
MCUCFG `SYNC_DCM_CONFIG` (`0x10220744`) or a PLL differs from what it left.
Idle states and hotplug do not write MCUMIXED or sync DCM from Linux. The
unknown is the firmware: it programs the B PLL in `CPU_ON` for the A72s, and
its `CPUSYS0/1` cluster-enable path for the A53s has not been audited to that
depth ([CPU clusters §5.1](../../docs/hardware/mt6797-cpu-clusters.md#51-a53-cores)).
If bringing a powered-down A53 cluster back touched ARMPLL1, the divider or
sync DCM, the driver would fault on its next change; it fails safe, but the
cluster would run at an unmeasured rate until then. So far the A53 clusters
have gone down with no record of the clock driver being bound (R1b ran
before cpufreq existed; the P2f lid test did not record it). C0 stage c3 is
the first observation with the driver bound.

**A72 module (`mt6797-a72`).** Neither the firmware nor the vendor programs
offer an A72 idle state below WFI, so CPU8-9 get none. Their idle lever is
hotplug, which works since 0645: the module redoes the board side before CPU8
returns to a down cluster, and CPU9 cannot come back first. BUCKB stays on
while the cluster is down. What the A72s cost online and idle is step 3 of
the [all-cores record](../2026-11-01-mt6797-all-cores/README.md#follow-up-full-support-before-loading-by-default);
C0 does not repeat it, and keeps the A72 module unloaded.

**`backlight-policy` (P2f).** It offlines CPU1-7 when the display goes dark
(lid closed or console blanked) and brings back the ones it took; since H1's
change it also takes CPU8-9 when they are online. C0 must hold the CPU set itself, so the
policy is stopped for the run and restarted afterwards.

## Plan

| Stage | What | Writes | Image | Status |
| --- | --- | --- | --- | --- |
| C0 | Idle current with A53 cpufreq at its idle points: all A53s online in WFI, then the L cluster down, then CPU1-7 down; SPM status reads in each state; the L clock checked after its cluster returns | None new (see below) | Running boot2 image | Attempt 1 run 2026-11-07, stopped at c3; **attempt 2 proposed** |
| C1 | Depends on C0: a cluster-first idle hotplug policy (screen on), or nothing | Hotplug only | none, userspace | Not proposed |
| H1 | The dark-screen hotplug policy takes the A72s too, when the module has them online; five blank/wake cycles | None new (see [H1](#stage-h1-the-a72s-in-the-dark-screen-policy)) | Running image; only `/bin/backlight-policy` replaced in the running initramfs | **Implemented, compile-checked, proposed** |
| C2 | Per-core power-down in idle, through an SPM program or a firmware port | New SPM or `tee1` writes | New | Owner decision; blocked on a program that does not exist in the evidence |
| S | System idle and suspend through the SPM (deep idle with only CPU0 online) | See [the SPM route](#the-spm-route-costed) | New module, then new image | Owner decision; designed as [Route A, S0-S3](#route-a-smallest-form), not implemented |

### Stage C0 proposal

**Hypothesis.** With schedutil holding CPU0-3 at 221 MHz and CPU4-7 at
325 MHz, WFI costs less than R1b's 15 mA. Most of what is left is in the L
cluster, which goes down as a whole when CPU4-7 are offline.

**Unique observation.** The first L cluster down and up with the clock driver
bound, and the first split of hotplug savings between the L cluster and the
LL cores.

**Candidate.** The image on boot2 at the time of the run (today
station-work-87, `be1dbf5a…`), with `clk-mt6797-mcusys.ko` and `cpufreq-dt.ko`
from its package, loaded by hand as in A3, governor schedutil. The A72 module
is not loaded (`online` is `0-7`). The custodian records boot ID, boot2
identity, release and module SHA-256 at the start.

**Firmware calls and writes for owner approval.** No new one. The run uses
only these, all of which have run on the station before:

1. PSCI `CPU_OFF` (`0x84000002`) on CPU1-7 and `AFFINITY_INFO` (`0xc4000004`)
   from the controlling CPU, through `echo 0 > /sys/devices/system/cpu/cpuN/online`
   (R1b, P2f).
2. PSCI `CPU_ON` (`0xc4000003`) for CPU1-7, through `echo 1 > …/online` (R1b,
   P2f).
3. The A53 cpufreq clock driver's approved list, items 1-8, as in A3
   ([writes](../2026-11-07-mt6797-a53-cpufreq/README.md#writes-for-owner-approval)).
   Schedutil takes CPU4-7 below 1092 MHz, so items 6-8 (the MAINPLL bridge)
   are used.

Everything else is a read: `/dev/mem` 32-bit reads of the SPM addresses below,
the clock driver's debugfs `registers`, sysfs, and the fuel gauge. No
regulator, PMIC, SPM, MCUCFG, A72 or new secure write.

**SPM reads** (base `0x10006000`; status and configuration words, none of them
cleared by a read):

| Offset | Name in the vendor MT6797 header | Why |
| --- | --- | --- |
| `0x018`, `0x01c`, `0x020`, `0x024`, `0x028`, `0x02c` | `PCM_CON0`, `PCM_CON1`, `PCM_IM_PTR`, `PCM_IM_LEN`, `PCM_REG_DATA_INI`, `PCM_PWR_IO_EN` | Is any SPM program loaded or running on mainline? |
| `0x17c` | `PCM_FSM_STA` | The PCM state machine |
| `0x174` | `CPU_IDLE_STA` | Per-core `STANDBYWFI` bits (vendor bits 10-17) |
| `0x180`, `0x184` | `PWR_STATUS`, `PWR_STATUS_2ND` | Domain and cluster power |
| `0x188`, `0x18c` | `CPU_PWR_STATUS`, `CPU_PWR_STATUS_2ND` | Core power; CPU8 bit 7 and CPU9 bit 6 are known, A53 bits are read from the change |
| `0x1e4` | `CPU_RET_STATUS` | The bit the firmware's power-down path waits on |
| `0x210`, `0x214` | `MP0_CPUSYS_PWR_CON`, `MP1_CPUSYS_PWR_CON` | LL and L cluster power control |
| `0x220`-`0x23c` | `MP0_CPU0-3_PWR_CON`, `MP1_CPU0-3_PWR_CON` | Core power control |
| `0x540`-`0x55c` | `MP0/MP1_CPU0-3_WFI_EN` | Expected 0 with no program |
| `0x600`, `0x608`-`0x61c` | `SPM_SW_FLAG`, `SPM_SW_RSV_0-5` | Words a loader's program would leave |

Plus MCUCFG `0x10220744` (`SYNC_DCM_CONFIG`), as in the cpufreq t0.

### Procedure

Station on battery for every window, cable out, the charger guard as in R1.
The display is blanked through `fb0/blank` as in R1, with `backlight-policy`
stopped first, so that only this procedure changes the CPU set. Wi-Fi modules
unloaded, as in R1b. A 1 Hz logger of `current_now`, `voltage_now` and the
online mask, written as in R1. Each window is 60 samples after 10 s of
settling, with `/proc/interrupts` read at its start and end.

| Stage | Action | Expected | If not |
| --- | --- | --- | --- |
| c0 | Read-only, cable in: identity, `online` `0-7`, taint, SPM and MCUCFG reads; load the clock driver and cpufreq-dt; schedutil on both policies | Driver bound, `faulted=0`, two policies; reads recorded | Stop |
| c1 | Unplug; window W1: CPU0-7 online, idle | `scaling_cur_freq` 221000 and 325000 most of the window; SPM reads at its end | Stop if the charger reads online for more than 10 samples |
| c2 | `echo 0` to CPU4-7; W2 | `online` `0-3`; `MP1_CPUSYS_PWR_CON` and the status words change for the L cluster; SPM reads | A CPU that will not go: stop |
| c3 | `echo 1` to CPU4-7; check the clock | `online` `0-7`, no `faulted`, PLL1 and divider as before c2, sync DCM unchanged; [`cpu-mhz`](../2026-11-07-mt6797-a53-cpufreq/tools/cpu-mhz.c) on CPU4 within 5 % of `scaling_cur_freq`, hash equal | Driver faulted, PLL changed, or clock off: stop, no retry, keep logs |
| c4 | `echo 0` to CPU1-7; W3 | `online` `0`; SPM reads | Stop |
| c5 | `echo 1` to CPU1-7; W4 (drift check, as W1) | `online` `0-7`, clock check as c3 on CPU4 and CPU1 | Stop |
| c6 | Replug; restart `backlight-policy` lit; unload cpufreq-dt and the clock driver, or leave them, as the custodian prefers | `online` `0-7`, no warning | Record |

One run. About 6 minutes on battery.

### Attempt 2 changes

Attempt 1 (see [Observations](#attempt-1-2026-11-07)) showed two faults in the
procedure above. Attempt 2 runs it with these changes and nothing else:

1. **Freeze `backlight-policy`, do not kill it.** Busybox init respawns it,
   and the new copy blanked the console and took CPU1-3 down. Before c1:
   console blanking off (`printf '\033[9;0]' > /dev/tty1`), then
   `kill -STOP` on every `backlight-policy` process, checked with `ps`. Blank
   only through `fb0/blank`. In c6: unblank `fb0`, then `kill -CONT`; the
   policy took no CPU, so it brings none back.
2. **Hold the clocks at the idle points.** Under schedutil, W1 sat at
   624/832 MHz for much of the window, so the windows did not measure WFI at
   the idle points. In c0, after schedutil is set, write `scaling_max_freq`
   `221000` (policy0) and `325000` (policy4); restore `897000` and `1209000`
   in c6. These are frequency requests inside the approved list (items 1-8);
   no new write. With the clocks held, the c3 check "PLL1 and divider as
   before c2" is exact again: in attempt 1 they had moved because schedutil
   kept scaling between the reads.
3. **The mask is checked per sample.** A window whose logged `online` mask
   changes at any sample stops the run, instead of only at stage boundaries.

Expected W1 then reads `scaling_cur_freq` 221000 and 325000 in every sample.

### Stop conditions

Stop at the first of these, keep `dmesg` and the logs, and do not retry:

- a CPU that does not go down or come back, or `online` not as the stage says;
- the clock driver's `registers` showing `faulted=1`, a PLL or divider not as
  before the cluster went down, or `SYNC_DCM_CONFIG` changed;
- a measured clock more than 5 % from `scaling_cur_freq`, or a wrong hash;
- an Oops, `BUG`, `WARNING`, RCU stall or `did not` line;
- the SoC above 60 °C or the battery below 30 %;
- the station unreachable over USB SSH for 60 s after the replug; the owner
  long-presses power if it is hung.

### Decision table

Let D be W1 minus W3 (CPU1-7 in WFI against off), and L be W1 minus W2 (the
L cluster in WFI against off).

| Result | Meaning | Next |
| --- | --- | --- |
| D under 5 mA | At the idle points WFI is cheap; per-core power-down would gain little | No cpuidle work; the next power levers are clocks (P3) and VCORE. Record and close C2 |
| D 5 mA or more, L at least two thirds of D | The L cluster carries the saving, and hotplug reaches it | Propose C1: keep CPU4-7 offline while the system is idle with the display on, and bring them back on load, in `backlight-policy` or a kernel policy, with its own stage |
| D 5 mA or more, spread over the cores | Per-core power-down would pay | C2 is an owner decision: an MT6797 SPM program (none in the evidence) or a secure-firmware port (power-management P5). Hotplug stays the lever until then |
| c3 or c5 stops on the clock | The firmware touches the A53 cluster clock on power-up | Any A53 cluster hotplug, P2f included, must be coordinated with the clock driver first. Read the firmware's `CPU_ON` path for `CPUSYS1` before anything else |
| An SPM program is running on mainline (`PCM_CON0` running, `PCM_FSM_STA` not idle, `WFI_EN` set) | A loader left SPM code running | Record it in the [CPU clusters](../../docs/hardware/mt6797-cpu-clusters.md) document; any SPM work must account for it |

Limits of C0: one unit, one boot, the fuel gauge's unknown averaging window,
and the logger's own load. A72 idle cost is outside it.

### Stage H1: the A72s in the dark-screen policy

**What exists.** The console-blank half of P2f is not new: `backlight-policy`
already called `cpus(closed || blanked)`, and attempt 1 of C0 observed it
take CPU1-3 down on a console blank (1043.24 s) and bring them back on the
unblank (1945.45 s). Screen blank is covered for the A53s.

**What changed.**
[`backlight-policy.c`](../2026-10-30-mainline-dev-station/backlight-policy.c)
now handles CPU1-9:

- going dark, it takes every online CPU from 1 to 9, so CPU8-9 when the
  `mt6797-a72` module has brought them up;
- going lit, it brings back only the CPUs it took, in ascending order, so
  CPU8 is first back to a down A72 cluster, as 0645 requires (CPU9 first gets
  `EBUSY`);
- at start with the screen lit (a previous copy may have died dark), it
  brings back offline A53s only. An A72 is never brought up unless this
  program took it: without the module's board sequence, `CPU_ON` for CPU8
  never returns ([step 2](../2026-11-01-mt6797-all-cores/README.md#observations)).

No new kernel code, so no patch number. Checks: built with the release
recipe's `gcc -static -O2 -Wall -Wextra -Werror` in the dev VM (aarch64, no
warning). A throwaway harness drove `cpus()` against a fake sysfs tree:
without the A72 module (CPU1-7 dark and back, CPU8-9 untouched), with the
A72s online (CPU1-9 dark and back), with CPU3 and CPU9 offlined by the owner
(both stay off), and a restart while lit with CPU5 off (CPU5 back, CPU8-9
stay off). All matched.

**Hypothesis.** On a dark screen the policy takes CPU1-9 down and brings
them back on wake, CPU8 first, through 0645's re-preparation, every cycle.

**Unique observation.** A72 cluster down and up driven by the screen state,
repeated, instead of by hand.

**Candidate.** The running boot2 image with the A72 module loaded
(`online` `0-9`) and the A53 cpufreq modules loaded, as in all-cores step 1.
The new binary is built from the commit that records this stage, copied over
`/bin/backlight-policy` in the running initramfs, and the old process killed
so init respawns the new one (`backlight-policy: start` in `dmesg`, new PID).

**Firmware calls and writes for owner approval.** No new one:

1. PSCI `CPU_OFF`, `AFFINITY_INFO` and `CPU_ON` for CPU1-9, through sysfs
   `online` (R1b, P2f, all-cores step 2).
2. The `mt6797-a72` module's re-preparation before CPU8 returns to a down
   cluster, already approved for step 2 attempt 2: SPM `0x10006218` bit 0,
   the PWRAP reset, DA9214 `0x5e` written `0x01`, SPM `0x10006290` bits 1:0
   cleared, the SRAM LDO call, then the MP2 DCM word at `0x10222274`.
3. The A53 cpufreq driver's approved list, items 1-8, as it scales.

**Procedure.** Cable in (power is not measured here). Console blank timeout
1 minute (`printf '\033[9;1]' > /dev/tty1`, then SIGUSR1 to the policy).
Five cycles: wait for the blank, read `online` (expect `0`), press a key,
read `online` within 5 s (expect `0-9`), check `dmesg` for `cluster prepared
again for CPU8` before `CPU9: Booted`, run one `cpu-mhz` hash on CPU8 and
CPU9. Then blanking off.

**Stop** at the first of: `online` not `0` dark or not `0-9` within 5 s of the
wake; a `did not go` line; `CPU8 not prepared`; a wrong hash; an Oops,
`WARNING`, RCU stall or `faulted=1`; USB SSH unreachable for 60 s (a hang in
`CPU_ON` leaves the policy's child and one CPU stuck in firmware; the owner's
force-off is the only recovery, as in step 2 attempt 1). No retry.

| Result | Next |
| --- | --- |
| Five cycles pass, and all-cores step 3 shows the A72s cost 2 mA or more online and idle | Keep CPU8-9 in the policy; the image built next carries it |
| Five cycles pass, step 3 shows under 2 mA | The saving does not pay for the `CPU_ON` hang risk: set `LAST_CPU` back to 7 |
| A cycle fails | Keep logs; `LAST_CPU` back to 7 before any image carries this; the A72 down/up path needs work first |

### Device tests, in order

1. All-cores step 3 (A72 idle cost on battery), already approved and queued;
   it gives H1 its decision.
2. C0 attempt 2 ([changes](#attempt-2-changes)), A72 module not loaded.
3. H1, A72 module loaded. It can share a boot with 2 if C0 runs first.

## The SPM route, costed

The owner asked for idle power as far as it can go. Past hotplug, the only
lever is the SPM, and only through its programs. This section is for the
owner's decision; nothing here is built.

**What it would save, and where.** Per-core idle power-down is not on offer by
either route below: no MT6797 per-core (MCDI) program exists in the evidence.
What the SPM programs do offer is system idle: deep idle (display off), SODI
and SODI3 (display on), and suspend. The vendor enters them only with exactly
one CPU online, which is the state P2f already creates whenever the screen is
dark. They drop the 26 MHz clock, put DRAM in self-refresh and lower VCORE
through the PMIC wrapper's sleep commands. So the target is the floor that
hotplug leaves: about 96 mA with the display blanked and CPU0 alone (R1b).
How much of it the SoC states remove is **not measured**: Gemian never
reached deep idle or suspend in the retained captures (power-management
record), and R3 has not run. Phones of this class typically stand by in
single-digit to low tens of mA, but that figure includes no Gemini board
loads, so the honest range is "somewhere between a few mA and most of the
96 mA". A measurement that bounds it before any build: the floor with clocks
gated (P3), since what stays on after P3 is what only the SPM can reach.

| | Route A: Linux SPM driver, vendor programs loaded at runtime | Route B: replaced secure firmware |
| --- | --- | --- |
| What it is | A `=m` module that owns the SPM: loads a vendor `pcm_*.bin` into the SPM carveout, sets power control and wake masks, programs the PMIC wrapper's sleep commands, clones edge interrupts into CIRQ, arms the APXGPT wake timer, kicks the program, then issues `CPU_SUSPEND` `0x1010000`; resume reads the wake reason and undoes it. Entered from s2idle (and later CPU0's idle) when only CPU0 is online | A TF-A port with PSCI 1.0, `SYSTEM_SUSPEND` and the SPM sequence in EL3, as upstream TF-A does for other MediaTek SoCs; Linux then uses generic `deep` and `cpuidle-psci` |
| Programs needed | `pcm_suspend.bin`, `pcm_deepidle.bin`, `pcm_sodi_ddrdfs.bin` and their `_by_mp1` variants (names from the vendor `mt_spm.c`), from the unit's own Gemian files | The same MT6797 programs, embedded in EL3; upstream TF-A has none for MT6797 |
| Rights | Proprietary MediaTek firmware with no redistribution grant: the project cannot ship them. A loader reading them from the unit is local-only. The arrays embedded in GPL vendor files (vcorefs; the non-MT6797 MCDI image) come without source, so they are not treated as redistributable either | Same problem, plus a vendor-firmware dependency compiled into the secure world |
| Also needed | Keeping the program files when Gemian is replaced (the chosen install replaces it); the station DT already reserves the SPM carveout | Rewriting every secure service the station uses today: `CPU_ON` with the B PLL, BigiDVFS calls, the secure register window, the SRAM LDO; the preloader's handoff format |
| Approval boundary | Inside the standing scheme once its write list is approved: modules, then one image | Writes `tee1`, outside every current approval, and needs a proven recovery path below the preloader before the first write |
| Cost (estimate) | The largest item in the power work, about the size of the A72 bring-up: the vendor suspend, deep idle and SODI sources (`mt_spm*.c`, `mt_sleep.c`, `mt_idle*.c`) are about 12,000 lines; a mainline module of perhaps 1000-1500 lines; many device stages, each with a hang risk recoverable only by force-off | Months, with a bricking risk to the boot chain; it still needs the programs |
| Upstreamable | No | The Linux side yes; the firmware side only with programs that can be shipped |

**Recommendation.** Route A, local-only, and only after P3 has shown what
floor the SPM would act on. Route B removes no blocker (it needs the same
programs) and adds the largest risk in the project.

**Writes route A needs** (register level, from the vendor sequence; exact
values are fixed per program at implementation, and each stage lists them
again for approval):

- SPM, base `0x10006000`, every write keyed with `0x0b16` in bits 31:16
  where the vendor does: `POWERON_CONFIG_EN` `0x000` ← `0x0b160001`;
  `PCM_CON0` `0x018` (reset, clock enable, IM kick, PCM kick); `PCM_CON1`
  `0x01c` (IM slave, event lock, timer enable); `PCM_IM_PTR` `0x020` and
  `PCM_IM_LEN` `0x024` (the program in the carveout); `PCM_REG_DATA_INI`
  `0x028`; `PCM_PWR_IO_EN` `0x02c`; `PCM_TIMER_VAL` `0x030`;
  `SPM_POWER_ON_VAL0` `0x004`; `SPM_CLK_CON` `0x00c`; `SPM_AP_STANDBY_CON`
  `0x014`; `SPM_SW_INT_CLEAR` `0x094`; `SPM_CPU_WAKEUP_EVENT` `0x0b0`;
  `SPM_IRQ_MASK` `0x0b4`; `SPM_SRC_REQ` `0x0b8`; `SPM_SRC_MASK` `0x0bc`;
  `SPM_SRC2_MASK` `0x0c0`; `SPM_WAKEUP_EVENT_MASK` `0x0c4`;
  `SPM_WAKEUP_EVENT_EXT_MASK` `0x0c8`; `SPM_IRQ_STA` `0x158` (write to
  clear); `SPM_MAS_PAUSE_MASK_B` `0x408` and `SPM_MAS_PAUSE2_MASK_B` `0x40c`;
  `WFI_EN` `0x540`-`0x56c` (MP0, MP1, MP2); `SPM_SW_FLAG` `0x600`;
  `SPM_SW_RSV_0` `0x608`.
- PMIC wrapper, base `0x1000d000`: the 16 sleep command slots,
  `DVFS_ADR0`/`DVFS_WDATA0` at `0x10c`/`0x110` through `DVFS_ADR15`/
  `DVFS_WDATA15` at `0x184`/`0x188`, loaded with the normal and sleep phases
  (VCORE sleep voltage and low-power modes; exact PMIC registers from the
  vendor `mt_spm_pmic_wrap.c` table for MT6797).
- CIRQ (clone and flush of edge interrupts) and APXGPT at `0x10008000` (wake
  timer); their exact registers come with the stage that adds them.
- A new firmware call: PSCI `CPU_SUSPEND` (`0xc4000001`) with `0x1010000`,
  never issued on mainline.
- What the program itself does (DRAM self-refresh, 26 MHz, infra, VRF18) is
  inside the vendor binary and cannot be listed by Linux; that is the core of
  the rights and review problem.

## The vendor sequence reverse-engineered (2026-11-08)

The owner asked how the vendor stack really gets below WFI, so the project
can choose a route. This pass read the unit's `tee1`, the nine SPM programs in
the unit's Gemian `system.img`, and the vendor kernel's `spm_v2` and
`cpuidle_v1` sources. Binary work ran privately in the RE VM; no device was
touched. The durable facts, with what was observed kept apart from what was
inferred, are in [MT6797 SPM sleep](../../docs/hardware/mt6797-spm-sleep.md).
This section answers the four questions and proposes Route A.

### Answers

**1. Secure firmware.** *Observed:* `CPU_SUSPEND` power-down clears the
core's `CPUECTLR` retention and its "SPARK" retention, spins until SPM
`CPU_RET_STATUS` shows the core out of retention, sets the warm-boot entry
and AArch64 reset state for cluster 0 core 0, and for a cluster request
turns off the GIC CPU interface, leaves CCI and lets cluster 0's L2 reset.
Then it waits in `wfi` for the SPM. It writes no SPM register, and there is
no SiP call for sleep. *Inferred:* no cluster-off or MCDI-like path exists
without an SPM program, and the firmware supports suspending CPU0 only. The
state Linux must leave the SPM in, per path, is in
[§4.2 of the hardware page](../../docs/hardware/mt6797-spm-sleep.md#42-what-linux-must-leave-the-spm-in).
*New:* the firmware enables A53 hardware retention on every `CPU_ON`. S0
then observed every idle A53, CPU0 included, in retention
([S0 result](#s0-result-2026-11-08)).

**2. SPM programs.** *Observed:* a 16-bit length, the PCM code, a
descriptor with sixteen event vectors, and a version string. The kernel
copies the code into the `spm-reserve-memory` carveout, points `PCM_IM_PTR`
at it, sets power control, wake masks and flags, loads the PMIC wrapper's 16
sleep commands, kicks the PCM and takes the CPU down. Each sleep program
powers exactly one core (CPU0, or CPU4 for `_by_mp1`) and its cluster, the
DRAM PHY and the CPU buck isolation. Suspend also powers infra down. All of
them gate the 26 MHz request, put DRAM in self-refresh and lower VCORE. The
register sequence, flags, masks and PMIC tables are in sections 3-7 of the
hardware page.

**3. Entry conditions.** *Observed in the vendor source:* deep idle, SODI and
SODI3 need one CPU online (CPU0 or CPU4), many infra and multimedia clocks
gated, the multimedia domains off (and the display domain off for deep
idle), and the next timer at least 2 or 5 ms away; APXGPT GPT4 carries the
tick through the sleep. Suspend checks none of these. *Assessed for
mainline:* suspend's only condition, CPU0 alone, is met by the kernel's own
`mem` path. The idle states are blocked today by the unused infra gates R2
found, by MSDCPLL (eMMC) for SODI3, and by the missing APXGPT and SYS_CIRQ
support ([§5.3](../../docs/hardware/mt6797-spm-sleep.md#53-which-conditions-a-mainline-station-can-meet)).

**4. Expected savings.** The vendor code holds no current figures. It
implies under 10 mA in suspend (its fuel gauge treats that as "suspended"),
with VCORE at 0.6-0.7 V instead of 0.9-1.0 V. Against the 96 mA left with
CPU0 alone, the SPM can only remove what is inside the SoC and its rails; how
much of the 96 mA that is stays unmeasured until S1. Per-core power-down in
idle looks worth little: idle A53s already retain (C0 attempt 2 measures the
remainder).

**Programs at runtime.** Yes. They are files in Gemian's `system.img`
(`/vendor/firmware/`, hashes on the hardware page), the same image
[`firmware-get`](../../docs/hardware/firmware.md#getting-them-from-the-owners-own-device)
already reads read-only for the Wi-Fi files. A loader needs only
`pcm_suspend.bin` for S1. Nothing needs shipping, but the chosen install
replaces Gemian, so the files must be copied off `system.img` before that,
as [`gemian-firmware`](../../docs/hardware/firmware.md#the-set-the-card-root-carries)
does for the radio files.

### Route A, smallest form

**Shape.** One `=m` module, `mt6797-spm-sleep`, that registers `mem` suspend
operations. Linux's own suspend path already offlines CPU1-9 and suspends
the devices; the module's `enter()` then runs the vendor suspend sequence on
CPU0. Nothing is built in, no DT change, no idle state. `rmmod` removes the
operations. Deep idle and SODI are not in Route A: they need the P3 clock
work, a GPT clockevent and CIRQ first.

**Which CPU path first.** S1 uses the "CPU stays powered" mode (flag bit 0):
CPU0 executes `wfi` at EL1 while the program gates the rest. That needs no
PSCI call, which matters because `cpu_suspend()` and
`psci_cpu_suspend_enter()` are not exported in 7.1 and a module cannot use
them without a built-in change. It also keeps CPU0's context, so a failed
program cannot leave a half-restored CPU. The cost: the vendor shipped the
power-down mode, and this mode is only seen in bring-up code, so whether the
programs honour it is inferred. S2, the shipped power-down mode, follows only
if S1 works and leaves enough current on CPU0's cluster to matter.

**Stages.**

| Stage | What | Writes | Image | Status |
| --- | --- | --- | --- | --- |
| S0 | Reads only: the SPM, PMIC-wrapper, MCUCFG, INFRACFG and PMIC words S1 will touch, so every read-modify-write has a known start value; `CPU_RET_STATUS` with the reader pinned to CPU0 and to CPU3; the SPARK words; the carveout's address; the `system.img` program hashes | None | Running | **Done 2026-11-08**, no stop condition ([result](#s0-result-2026-11-08)) |
| S1 | `mem` suspend on CPU0 with the suspend program, CPU stays powered, PCM-timer wake after 30 s | The list below | Running, plus the new module | **Implemented** as [0667](#s1-implementation-2026-11-08), compile-checked; write list awaits the owner |
| S2 | As S1 with CPU power-down (`CPU_SUSPEND` `0x1010000`) | S1's list with flag bit 0 clear, plus one built-in export | New image | Owner decision after S1 |
| S3 | Deep idle or SODI from CPU0's idle with the screen dark | New masks, APXGPT, CIRQ | New image | After P3 |

### S0: reads

32-bit reads on the station, cable in, no other test running:

- SPM `0x10006000`-`0x100060c8`, `0x10006100`-`0x1000617c`,
  `0x100061e4`, `0x10006290`, `0x10006320`, `0x10006328`, `0x1000632c`,
  `0x10006540`-`0x10006564`, `0x10006600`-`0x1000661c`;
  `0x100061e4` twice more under `taskset` on CPU0 and on CPU3.
- PMIC wrapper slots `0x1000d10c`-`0x1000d188`.
- MCUCFG `0x1022002c`, `0x1022022c`, `0x1022220c`, `0x10221c00`,
  `0x10221c04`, `0x10223c00`, `0x10223c04`.
- INFRACFG_AO `0x10001f00` (4 GB mode, bit 13); chip version `0x08000008`.
- MT6351 through the station's existing PMIC read path: `0x0008`, `0x000c`,
  `0x0200` (HWCID), `0x0204`, `0x044a`, `0x045c`, `0x0470`, `0x060a`,
  `0x060c`, `0x06a8`, `0x06aa`.
- The `spm-reserve-memory` base from the boot log or `/proc/iomem`.
- The SHA-256 of `/vendor/firmware/pcm_suspend.bin` inside `system.img`, read
  the way `firmware-get` reads.

**Stop and redesign if:** `PCM_FSM_STA & 0x7fffff` is not `0x48490`;
`PCM_REG1_DATA` is 1 (a resident program); the carveout is missing; the file
hash differs.

### S0 result (2026-11-08)

Run by the device custodian. Boot `50572be9-64e5-4759-aaad-a7df73eebf72`,
release `7.1.3-gemini-a53-station`, boot2 `6c0fd742…` (station-work-91). Card
root with the desktop session up, cable in, `online` `0-7`. The A72 module
and A53 cpufreq were not loaded. Wi-Fi and Bluetooth were loaded. Taint 512
came from an earlier Panfrost `WARN`, not from S0. Reads used busybox
`devmem`; the PMIC reads used the PMIC wrapper's regmap in debugfs. Every
read completed, with no fault. The raw log stays private with the
custodian.

**Stop conditions: none hit.** `PCM_FSM_STA` `0x02848490` (reset value),
`PCM_REG1_DATA` 0, carveout present, `pcm_suspend.bin` hash matches. The
other eight program hashes also match the hardware page.

| What | Read | Meaning for S1 |
| --- | --- | --- |
| Carveout | `0xbfdd0000`-`0xbfde5fff`, 88 KiB, no-map | Program at `0xbfdd0000` |
| INFRACFG_AO `0x10001f00` | `0x11403200` | 4 GB mode on (bit 13), so `PCM_IM_PTR` = `0xffdd0000` |
| Chip version `0x08000008` | `0x0000ca01` | Flag bit 18 (segment 2) set |
| MT6351 HWCID `0x0200` | `0x5140` | Slots 10 and 11 use `0x06aa` |
| `MD1_PWR_CON`, `C2K_PWR_CON`, `CONN_PWR_CON` | `0x112`, `0x012`, `0x10d` | Modem and C2K off. CONNSYS was on with Wi-Fi/BT loaded, so S1's precondition needs those modules unloaded, as written |
| `SPM_POWER_ON_VAL0`/`VAL1` | `0x00000000` / `0x00015830` | S7 copies them as read |
| `SPM_CLK_CON` `0x00c` | `0x00008000` | S1, S13, S22 change bits 4, 6, 5 |
| `SPM_AP_STANDBY_CON` `0x014` | `0x04f80000` | Bit 23 set, so S9 writes `0x04880011` |
| `PCM_CON0`/`PCM_CON1` | `0x00000004` / `0x00006c00` | As in C0; no watchdog bits to keep |
| `SPM_SRC_REQ`/`SRC_MASK`/`SRC2_MASK` | `0x40` / `0xe1fff07e` / `0x03f107df` | S10-S12 replace them; X3 restores |
| Every `WFI_EN`, `SPM_SW_FLAG`, `SPM_SW_RSV_0`-`3` | 0 | Nothing else uses them |
| `CPU_EXT_BUCK_ISO` `0x290` | `0x00000002` | The A72 cluster's isolation, A72 module not loaded |
| PMIC wrapper slots `0x1000d10c`-`0x1000d188` | all 0 | Nothing loads them on mainline; X4 restores zeros |
| MCUCFG `MP0`/`MP1_AXI_CONFIG` | `0x0b` / `0x0b` | `ACINACTM` (bit 4) clear on both, as expected with CPUs online |
| MCUCFG `MP2_AXI_CONFIG` | `0x00000000` | `ACINACTM` clear even with the A72 cluster down |
| SPARK `0x10221c00`/`04`, `0x10223c00`/`04` | `0x3f3f3f3f` / `0x0f`, `0x3f3f3f3f` / `0x0f` | All eight A53s, CPU0 included, have SPARK on |
| MT6351 `0x060a` / `0x060c` | `0x0040` / `0x0040` | VCORE 1.0 V now; sleep voltage also 1.0 V |
| MT6351 `0x044a`, `0x045c`, `0x0470` | `0xfb21`, `0x0000`, `0x0000` | `VSLEEP_SEL` is 3 now; low-IQ off |
| MT6351 `0x0008`, `0x000c`, `0x0204` | `0x0000`, `0x0000`, `0x010b` | Power-good force bits clear |
| MT6351 `0x06a8` / `0x06aa` | `0x0050` / `0x0050` | VSRAM_PROC 1.1 V |

**Retention.** With the reader pinned to CPU0, `CPU_RET_STATUS` read
`0xFE` and `CPU_IDLE_STA` `0x3F800`. Pinned to CPU3, they read `0xF6` and
`0x3DC00`. Only the reading CPU's bits were clear, so every other A53,
CPU0 included, was in WFI and in retention. That corrects this record's
2026-11-08 inference that CPU0 lacked retention. C0 attempt 1's `0xF6` read
was taken on CPU3. Durable facts are in
[MT6797 SPM sleep §2](../../docs/hardware/mt6797-spm-sleep.md#2-a53-retention-spark-is-already-on-for-every-a53).

**What S0 settles for S1.** Every data-dependent value in the S1 list is now
fixed (below). One precondition was not met in this run (CONNSYS on), as
expected, because the run kept Wi-Fi loaded. Nothing in S0 argues against
S1.

### S1: the write list, for owner approval

All on CPU0, inside `enter()`, with interrupts off and CPU1-9 already offline.
SPM base `0x10006000`. "RMW" changes only the named bits of the value read.
Every SPM, wrapper and PMIC word written is read first and restored in X3-X4,
except where the text says otherwise.

**Preconditions, checked by reads; any failure returns `-EBUSY` with nothing
written:** CPU0 is the only online CPU; `PCM_FSM_STA & 0x7fffff == 0x48490`;
`PCM_REG1_DATA != 1`; `MD1_PWR_CON`, `C2K_PWR_CON` and `CONN_PWR_CON`
(`0x320`, `0x328`, `0x32c`) all read `0x12` in bits 4:0 (modem, C2K and
CONNSYS off: the Wi-Fi and Bluetooth modules unloaded); the console is
suspended.

**Once, at module load (no hardware write):** `request_firmware` of
`mediatek/mt6797/pcm_suspend.bin`, checked against its SHA-256; its 1,822
code words copied into the carveout at offset 0 (RAM, not a register); the
SPM interrupt (SPI 180, level low) mapped through the `sysirq` domain,
requested `IRQF_NO_SUSPEND` and marked for wake.

PMIC (MT6351, through the PMIC wrapper's normal register access):

| # | Register | Write |
| --- | --- | --- |
| P1 | `VGPU_ANA_CON7` `0x0470` | RMW bit 1 ← 1 (VGPU low-IQ) |
| P2 | `STRUP_CON4` `0x0008`, `STRUP_CON6` `0x000c` | RMW bit 15 ← 1; RMW bit 9 ← 1 (power-good force) |
| P3 | `BUCK_VCORE_CON6` `0x060c`; `SMPS_ANA_CON9` `0x044a` | RMW bits 6:0 ← `0x10` (0.7 V sleep voltage); RMW bits 9:8 ← 0. **With S0's values:** `0x0040` → `0x0010`; `0xfb21` → `0xf821` |

S1 leaves out the vendor's static regulator sleep modes (hardware control and
low-power mode on `SRCLKEN0` for the bucks and LDOs, §6 of the hardware
page). Without them every rail stays in its normal mode during the sleep, and
the program's slot commands alone set VCORE. That is a smaller saving but no
rail changes behaviour. They come back as their own stage if S1 works.

PMIC wrapper (`0x1000d000`): the 32 slot words saved, then

| # | Register | Write |
| --- | --- | --- |
| W1 | `DVFS_ADRn` `0x1000d10c + 8n`, `DVFS_WDATAn` `0x1000d110 + 8n`, n = 0-15 | The suspend-phase table on the hardware page: slots 0-6 `0x060a` ← `0x40`, `0x3e`, `0x3b`, `0x38`, `0x36`, `0x33`, `0x30`; 7 `0x060c` ← `0x00`; 8 `0x044a` ← (read \| `0x0300`); 9 `0x060a` ← `0x1c`; 10, 11 `0x06a8` (`0x06aa` if HWCID is `0x5140`) ← `0x40`, `0x50`; 12, 13 `0x045c` ← read \| `0x2`, read & ~`0x2`; 14 `0x060c` ← `0x10`; 15 `0x044a` ← read & ~`0x0300`. **With S0's values:** 8 `0x044a` ← `0xfb21`; 10, 11 `0x06aa`; 12 `0x045c` ← `0x0002`; 13 ← `0x0000`; 15 `0x044a` ← `0xf821` |

SPM, in order:

| # | Register | Write |
| --- | --- | --- |
| S1 | `SPM_CLK_CON` `0x00c`; `SPM_CLK_SETTLE` `0x010` | RMW bit 4 ← 1; `0x010` ← 0, read it as `m`, then ← 99 − `m` |
| S2 | `PCM_CON0` `0x018` | `0x0b168004`; poll `PCM_FSM_STA` for `0x48490` (5 ms bound; on timeout stop, X3); `0x0b160004`; `0x0b16000c` |
| S3 | `PCM_CON1` `0x01c` | `0x0b165c48` \| (read & `0x300`) |
| S4 | `SPM_SW_INT_CLEAR` `0x094` | `0x1` |
| S5 | `PCM_IM_PTR` `0x020`; `PCM_IM_LEN` `0x024` | carveout physical address, plus `0x40000000` if 4 GB mode is on and the address is in `0x40000000`-`0xbfffffff`; `0x71d`. **With S0's values:** `0xffdd0000` (carveout `0xbfdd0000`, 4 GB mode on) |
| S6 | `PCM_CON0` | `0x0b16000e`, then `0x0b16000c` (instruction fetch) |
| S7 | `PCM_REG_DATA_INI` `0x028`; `PCM_PWR_IO_EN` `0x02c` | ← `SPM_POWER_ON_VAL0` (`0x004`) as read; `0x00010000`; 0; ← `SPM_POWER_ON_VAL1` (`0x008`) as read; `0x00800000`; 0 |
| S8 | `PCM_EVENT_VECTOR0`-`15` `0x040`-`0x07c` | The sixteen words of the hash-pinned file's descriptor |
| S9 | `SPM_AP_STANDBY_CON` `0x014` | `0x04080011` \| (read & `0x00800000`): WFI AND, MP3 idle masked, modem 1 and CONN requests honoured, SCP request masked (no SCP firmware runs on mainline). **With S0's value:** `0x04880011` |
| S10 | `SPM_SRC_REQ` `0x0b8` | `0x00000040` (DVFS force-down only) |
| S11 | `SPM_SRC_MASK` `0x0bc` | `0x10aa007e` |
| S12 | `SPM_SRC2_MASK` `0x0c0` | `0x00f1001f` |
| S13 | `SPM_CLK_CON` | RMW bit 6 ← 1 |
| S14 | `MP0_CPU0-3_WFI_EN`, `MP1_CPU0-3_WFI_EN` `0x540`-`0x55c`; `MP2_CPU0/1_WFI_EN` `0x560`, `0x564` | 1 each |
| S15 | `PCM_TIMER_VAL` `0x030`; `PCM_CON1` | `0x000f0000` (30 s at 32,768 Hz); RMW bit 5 ← 1, with key `0x0b16` |
| S16 | `SPM_WAKEUP_EVENT_MASK` `0x0c4` | `0xffffffbe` (wake on PCM timer and EINT only) |
| S17 | `SPM_IRQ_MASK` `0x0b4` | (read & `0x4`) \| `0x3fe00` (only the PCM-return and IRQ0 interrupts reach the GIC) |
| S18 | `SPM_SCP_MAILBOX` `0x098`; `SPM_PASR_DPD_3` `0x63c` | 1 (as the vendor's efuse-path entry); 0, so the program's timer-wake loop returns on the first timer (added 2026-11-08 after the decode, restored in X3) |
| S19 | `SPM_MAS_PAUSE_MASK_B` `0x408`; `SPM_MAS_PAUSE2_MASK_B` `0x40c` | `0xffffffff` each |
| S20 | `PCM_REG_DATA_INI` | 0 |
| S21 | `SPM_SW_FLAG` `0x600`; `SPM_SW_RSV_0` `0x608` | `0x000902b1` (CPU stays powered, no VPROC/VSRAM DVS, VCORE DFS off, DRAM deep power-down off, modem-infra power-down off, SYSRAM sleep off, thermal check skipped), plus bit 18 if the chip version reads `0xca01`; 0. **With S0's value** (chip `0xca01`): `0x000d02b1`. Bit 9 was added after the decode: without it the program drives the A72 buck (DA9214) over I2C6 |
| S22 | `SPM_CLK_CON` | RMW bit 5 ← 1 (infra DCM lock) |
| S23 | `PCM_PWR_IO_EN` | `0x81` |
| S24 | `PCM_CON0` | `0x0b16000d`, then `0x0b16000c` (the program starts) |

CPU0:

| # | Register | Write |
| --- | --- | --- |
| C1 | MCUCFG `MP0_AXI_CONFIG` `0x1022002c`, `MP1_AXI_CONFIG` `0x1022022c`, `MP2_AXI_CONFIG` `0x1022220c` | RMW bit 4 ← 1, bit 4 ← 1, bits 4 and 0 ← 1, each only if not already set (direct writes, as the vendor suspend file does) |
| C2 | — | `dsb sy; wfi` at EL1. No PSCI or SiP call |
| C3 | the three AXI words | restored to the values read before C1 |

After the wake:

| # | Register | Write |
| --- | --- | --- |
| X1 | — | Reads: `0x028`, `0x608`, `0x144`, `0x15c`, `0x160`, `0x41c`, `0x420`, `0x424`, `0x134`, `0x170`, `0x604`, `0x158`, logged as the wake reason |
| X2 | `SPM_CPU_WAKEUP_EVENT` `0x0b0`; `SPM_WAKEUP_EVENT_MASK`; `SPM_IRQ_MASK`; `SPM_IRQ_STA` `0x158`; `SPM_SW_INT_CLEAR` | 0; `0xffffffff`; RMW bits 17:9 ← 1; `0x8`; `0x3ff` |
| X3 | `PCM_PWR_IO_EN`; `PCM_CON1`; `PCM_CON0`; every word S1-S23 changed | 0; RMW bit 5 ← 0 with key; `0x0b168004`, poll, `0x0b160004` (the idle state C0 read); all others back to the values read before S1 |
| X5 | Infra gates GCE, AUXADC, I2C_APPM (set `0x10001080`/`88`/`a8`, clear `84`/`8c`/`ac`) | Only where the program left one different from before entry (status `0x10001090`/`94`/`b0`), written back to its state before entry. `CLK_CFG_0` (`0x10000040`) is read before and after and logged, not written |
| X4 | Wrapper slots; P3, P2, P1 | The 32 saved words; P3 restored; P2 bits ← 0 and P1 bit ← 0, as the vendor does |

Nothing in this list is a new firmware call. Every write is new on mainline.
What the program itself writes while it runs (DRAM, clocks, infra, VCORE
through the slots, the CPU buck isolation) cannot be listed by Linux; the
register scan on the hardware page is the best available view of it.

**After S1 the A72s need their preparation again**, since the program
touches `CPU_EXT_BUCK_ISO`. The resume path brings CPU8 back through 0645's
re-preparation, so no change is expected; S1 checks it.

### S1 procedure, outcomes and stops

**Hypothesis.** With only CPU0 online and the vendor suspend program running
in "CPU stays powered" mode, the station sleeps for the 30 s PCM timer and
resumes with every CPU and driver back, and the current during the sleep is
well below 96 mA.

**Unique observation.** The first SPM program run on mainline, and the first
current figure below the hotplug floor.

**Candidate.** The running boot2 image and the module built from the commit
that records S1, loaded by hand. Wi-Fi and Bluetooth modules unloaded
(CONNSYS off), A53 cpufreq loaded, A72 module as the custodian runs it.

**Measurement.** The MT6351 coulomb counter (`FG_CAR`,
[fuel gauge](../../docs/hardware/gemini-fuel-gauge.md)) read before and after
three back-to-back 30 s suspends on battery, against the same span idle with
CPU0 alone. At about 90 µAh per count, 90 s at 96 mA is about 27 counts, so
a large drop is visible and a small one is not.

| Outcome | Next |
| --- | --- |
| Three cycles resume, wake reason PCM timer, current clearly below 96 mA | Record the figure. Add the static regulator sleep modes as their own stage, then decide S2 |
| Resume works, no saving | The program's "CPU stays powered" path gates too little to matter. S2 is the only remaining SPM path |
| Wake reason other than the timer, or abort before sleeping | Keep the status words; analyse before any retry |
| No resume within 60 s | Force-off by the owner, as for any hang. Keep the S0 values and module log; no retry until the cause is known |

**Stop** at the first: a precondition fails; the reset poll times out; an
Oops, `WARNING` or RCU stall; a CPU that does not return after resume; USB
SSH absent 60 s after the expected wake. No retry.

### S1 implementation (2026-11-08)

The owner chose to measure what the vendor program delivers before
considering a program of the project's own ("We can check the vendors
outcome first", relayed by the device custodian). The S1 write list itself
is not yet approved; the custodian puts it in its combined test plan.

**The module.**
[0667](../../patches/proposals/0667-soc-mediatek-add-an-MT6797-SPM-mem-suspend-experimen.patch)
adds `mt6797-spm-sleep` (`CONFIG_MT6797_SPM_SLEEP`, tristate, default N). It
contains no vendor code and no program bytes, only the program's SHA-256. At
load it:

- finds the `spm-reserve-memory` carveout, requests
  `mediatek/mt6797/pcm_suspend.bin`, refuses any other hash, copies the 1,822
  code words to the carveout and keeps the sixteen vectors;
- computes the SPM pointer (4 GB mode adds `0x40000000`), the flags (bit 18
  on chip `0xca01`) and the PMIC revision;
- maps the SPM interrupt (SPI 180 through `sysirq`), leaves it disabled;
- registers `mem` suspend operations. `timer_sec` (default 30, 1-600) sets
  the PCM timer.

`.prepare` enables the SPM interrupt for wake and writes P1-P3 through the
PMIC wrapper's regmap. `.enter` runs the S1 list. `.finish` restores P1-P3,
disables the interrupt and logs one `wake:` line (returned flag, WFI loop
count, `r12`, raw wake status, timer-out and the other X1 words). Failed
preconditions return `-EBUSY` with nothing written; a PCM reset timeout
returns `-EIO` after restoring.

**What the program itself does (decode, 2026-11-08).** A separate session
decoded `pcm_suspend.bin` in full, privately; the durable result is
[MT6797 SPM programs](../../docs/hardware/mt6797-spm-programs.md). In short:

- Flag bit 0 is tested at four places. Set, the program skips powering off
  `MP0_CPU0`, `MP0_CPUSYS` and `MCUSYS`, skips `CPU_EXT_BUCK_ISO` at entry
  and exit, and skips the CPU power-up. So "CPU stays powered" is a real
  path, and S1 does not undo the A72 preparation.
- With flag bit 9 clear, the program reprograms I2C6 and writes register
  `0x1d` of slave `0x68` (the station's DA9214, the A72 buck) at entry and
  exit. S1 now sets bit 9.
- Unconditionally it soft-resets I2C6 (`0x1100e050` ← 1), ungates I2C_APPM
  and gates it again at exit, gates GCE at entry and ungates it at exit, and
  moves `ddrphycfg_sel` (`CLK_CFG_0`) to parent 0 and back to parent 1. Its
  APSRC handlers gate AUXADC and flip `CLK_CFG_0` bit 8. These were not on
  the S1 list; the module now puts the three gates back as found (X5) and
  logs `CLK_CFG_0`. The I2C6 reset is covered by `i2c-mt65xx`'s resume,
  which reinitialises the controller; the station's iDVFS variant (0115)
  writes only per-transfer registers outside `mtk_i2c_init_hw`, so the reset
  loses nothing it relies on.
- When the timer fires with `SPM_WAKEUP_MISC` bit 19 set, it compares
  `SPM_SCP_MAILBOX` with `SPM_PASR_DPD_3` and may sleep again. S1 now zeroes
  `PASR_DPD_3` (S18).
- Flag bits 4, 5, 7, 16 and 18 are never tested by this program; they stay
  set as the vendor sets them.

**Differences from the S1 list as approved for review:**

- C1 (`ACINACTM` on the three clusters) is written **first**, before any SPM
  write, and read back; if `MP0_AXI_CONFIG` does not take it, `.enter`
  returns `-EIO` having changed nothing else. The vendor sets it just before
  `wfi`.
- C2 is `wfi` in a loop that ends when `SPM_IRQ_STA` shows the PCM return,
  bounded at 1,000,000 passes, so a wake that is not the program's does not
  start the cleanup while the program still runs.
- **No new firmware call.** S1 makes no PSCI or SiP call. `CPU_SUSPEND`
  `0x1010000` belongs to S2 only.

**Checks.** Compiled as an external module against the VM's prepared 7.1.3
tree (patches through 0655) with `W=1`: no warning. Final linking was not
possible without that tree's `Module.symvers`; every undefined symbol was
checked against a full 7.1.3 build's exports and the source tree's
`EXPORT_SYMBOL`s. `checkpatch` on the file: no error, no warning left (it reports only the missing `Signed-off-by`, which project patches do
not invent, and MAINTAINERS). The Kconfig parses (`allnoconfig`). 0667 applies
cleanly after 0656-0666. It is in `patches/series` and
`patches/series-a53-station`, and
[`gemini-a53-station-spm-sleep.fragment`](../../configs/gemini-a53-station-spm-sleep.fragment)
(`CONFIG_MT6797_SPM_SLEEP=m`) is added to profiles `mt6797-a53-station-a72`
and `mt6797-a53-station-dvfs`. Nothing loads the module at boot. Not built
on Buildbox. Never run.

**Where the program comes from.** The module asks for
`mediatek/mt6797/pcm_suspend.bin`, so on the RAM root the file goes to
`/lib/firmware/mediatek/mt6797/pcm_suspend.bin` (where `firmware-get` puts the
radio files) and on the card root to `/usr/lib/firmware/mediatek/mt6797/`.
Source: `/vendor/firmware/pcm_suspend.bin` inside Gemian's `/data/system.img`,
read read-only as `firmware-get` does, or the custodian's private copy.
SHA-256 `d6e8a0b8851e78e95891c995605ffbf210eade56583b14cf6b4a67e7d770f4e0`.

**Device steps, in order** (after the owner approves the write list and a
package carries the module):

1. **Root and identity.** Boot the RAM root, not the card root, so a forced
   power-off cannot corrupt a mounted file system. Record boot ID, boot2
   identity, release, module SHA-256 and the program hash. Battery at least
   50 %, cable in.
2. **Quiet the station.** Unload the Wi-Fi and Bluetooth modules so CONNSYS
   powers off; check `0x1000632c` bits 4:0 read `0x12`. Freeze every
   `backlight-policy` and lid-suspend process with `kill -STOP` (they would
   otherwise suspend through this module, or hotplug CPUs, mid-run). A72
   module not loaded. Blank the display through `fb0/blank`.
3. **Load.** `insmod mt6797-spm-sleep.ko timer_sec=30`. Expect
   `program 1822 words at 0x00000000bfdd0000, SPM pointer ffdd0000` and
   `flags 000d02b1, HWCID 5140`. Immediately
   `echo s2idle > /sys/power/mem_sleep`, because loading makes `deep` the
   default.
4. **Functional cycle, cable in.** `echo deep > /sys/power/mem_sleep;
   echo mem > /sys/power/state`. Expect the USB link to drop and return
   about 30 s later, `wake: returned=1`, `r12` bit 0 (PCM timer), `online`
   `0-7` afterwards, and no warning. Then `echo s2idle > /sys/power/mem_sleep`.
5. **Measurement, on battery.** As a script started with `nohup` before the
   unplug: wait 20 s; read `FG_CAR` (PMIC `0x0ca6`-`0x0caa`) and
   `CLOCK_BOOTTIME`; 300 s idle with CPU1-7 offline (the 96 mA reference);
   read both again; set `timer_sec=300`; three `mem` suspends back to back;
   read both again; restore `s2idle`; save `dmesg`. Replug after about
   20 minutes.
6. **Restore.** `rmmod mt6797-spm-sleep`, `mem_sleep` `s2idle`, CPUs online,
   `kill -CONT` the frozen processes, reload the radios.

**What tells the vendor outcome.** Average suspended current
= ΔQ(suspends) / time asleep, from `FG_CAR` (about 90 µAh per count; 900 s at
10 mA is about 28 counts, at 96 mA about 270), against the idle window's
ΔQ / 300 s, which should reproduce about 96 mA. The `wake:` lines show the
program returned on its timer each time and give `timer_out`.

| Outcome | Next |
| --- | --- |
| Suspended current far below 96 mA, resumes clean | The vendor programs deliver; record it; the static regulator modes next, then S2 |
| Resumes clean, current near 96 mA | The bit 0 path does not reach the low-power states, or the slots are not honoured; S2 decides |
| `wake: returned=0` or `loops=1000000` | The program never signalled; stop, keep the log |

**Stop** at the first: `insmod` error; `.enter` returning an error; a
`wake:` line other than `returned=1`, or one whose `clk_cfg_0` before and
after differ; an Oops, `WARNING` or RCU stall; a CPU
that does not return; no USB link 60 s after the expected wake in step 4.
No retry.

**Hang recovery.** If the program never returns, CPU0 sits in `wfi` with
every other interrupt masked and the station is dead to USB and keys. The
only recovery is the owner's forced power-off (long press), then boot2 by
hand. Nothing persists across that except what is already on storage, so
the RAM root keeps the cards safe; the S0 values and this list are the
starting point for the analysis.

### S1 attempt 1 (2026-11-08): watchdog reset in the first suspend

The custodian's run is recorded in the test plan,
[boot 3](../2026-11-08-cpu-power-test-plan/README.md#boot-3-result-2026-11-08):
the module loaded as expected, the last log line came just before the first
30 s `mem` suspend, and the next boot was Gemian with `boot_reason=4`
(`wdt_by_pass_pwk`) and RAM console `hw_status: 1`. No `wake:` line.

**The watchdog explains the reset, and would have reset it even if the
program worked** (from v7.1 source; not traced on the device):

- `mtk_wdt` registers with `max_hw_heartbeat_ms` 31000 and timeout 31 s. With
  `CONFIG_WATCHDOG_HANDLE_BOOT_ENABLED` and nobody holding `/dev/watchdog`,
  the watchdog core marks it `WDOG_HW_RUNNING` and pings it from a kernel
  worker every half heartbeat, about 15.5 s.
- `mtk_wdt_suspend()` stops it only `if (watchdog_active())`, which is false
  for a watchdog that is only `WDOG_HW_RUNNING`. So it keeps counting.
- In `mem` suspend no CPU runs the worker. At entry the last ping is 0 to
  15.5 s old; add 30 s of PCM timer and the 31 s expiry falls inside the
  sleep every time.
- s2idle survives because the kick worker's timer still runs on the idle
  CPU, which fits the 600 s s2idle results.

So boot 3 says nothing about whether the program returns: a program that
hangs and a program that wakes on time both end in this reset. I see no
reason to think something other than the watchdog caused it; nothing points
at the program, and nothing could, with this timing.

**For the retry** (owner's choice, as the custodian put it):

- (a) A feeder holding `/dev/watchdog` open for the run makes
  `watchdog_active()` true, so the driver stops the watchdog at suspend and
  restarts and pings it at resume. No new code. Close it with the magic
  `V` afterwards. (This record first said a close without `V` was also fine;
  the retry disproved that: the watchdog stays active, and with its timeout
  equal to `max_hw_heartbeat_ms` the core does not ping it after the close,
  so it reset the station.)
- (b) Patch `mtk_wdt_suspend()`/`mtk_wdt_resume()` to also stop and restart a
  watchdog that is `watchdog_hw_running()`. A few lines, upstreamable, and the
  durable fix: every future `mem` suspend on the station hits this. It is
  built in, so it needs an image.
- Either way, **make the first cycle short**: a PCM timer of 10 s. Then even
  if the watchdog is still running, at most 15.5 + 10 s plus entry and exit
  passes before the resume kicks it, under 31 s. A clean return on that
  cycle shows the program returns, independently of the watchdog fix; the
  30 s and 300 s cycles follow.

### S1 retry (2026-11-08): the program returns on its timer

Run by the custodian with a `/dev/watchdog` feeder and a 10 s first cycle;
recorded in the test plan,
[boot 3 retry](../2026-11-08-cpu-power-test-plan/README.md#boot-3-retry-2026-11-08).

- **The vendor suspend program ran and returned on its timer, on mainline,
  once.** The wake line read `returned=1 loops=1`, `r12=00000001` (bit 0,
  the PCM timer, in the vendor's wake-source layout), `timer_out=00050088`,
  `clk_cfg_0` `01010101` before and after; uptime advanced 10.3 s, with no
  warning and no taint.
- The 30 s cycle did not start: MTU3 refused the suspend (`-16`) after it
  forced a B-session on resume. That is the suspend session's to fix.
- A later reset came from closing the feeder without `V` (see above), not
  from the program.
- **No current figure yet,** so the outcome table's question, whether the
  vendor program saves power, is still open.

### S1 measured (2026-11-08)

Run by the custodian on D1, boot `263ae72a…`, with the feeder closed with `V`
and the `mtu3` gadget unbound; recorded in the test plan,
[boot 3 second retry](../2026-11-08-cpu-power-test-plan/README.md#boot-3-second-retry-s1-measured-2026-11-08).

- **Five `mem` suspends (10 s, 30 s, three of 300 s) all returned on the PCM
  timer**: `returned=1 loops=1 r12=00000001` each time, gates and `clk_cfg_0`
  unchanged, `timer_out` matching 10, 30 and 300 s, no fault, taint 0.
- **Current**, from `charge_counter` (about ±3 % per window): the idle
  reference with CPU0 alone, screen blank and radios off read 271 mA over
  301 s; the three 300 s suspends read 43, 42 and 42 mA, each including about
  0.7 s of entry and resume. s2idle on the same kind of setup read 73 mA (P6).

By the S1 outcome table this is the first row: **the vendor program's
"CPU stays powered" path delivers**, about 31 mA below s2idle and well under
the 96 mA hotplug floor of R1b.

Two things this does not settle:

- **The awake floor has moved.** The 271 mA reference agrees with C0
  attempt 2's W3 (290 mA, CPU0 alone) and not with R1b's 96 mA. Two runs on
  two later images now show about 180 mA more awake draw than R1b with the
  same CPUs, radios off and the backlight off. It vanishes in a `mem`
  suspend, so it is something Linux keeps running while awake. That is now
  the largest single power item, larger than anything S2 or S3 can win.
- **What stays in the 42 mA** is not split: CPU0 and its cluster stay powered
  in this mode, DRAM and the board's own loads are unknown.

### Recommendation for owner decision 5 (S2 and S3)

1. **First make S1 the station's suspend.** It already halves s2idle. What
   it needs: the `mtk_wdt` fix (option b above) so no feeder is needed, the
   `mtu3` fix (0676, in D2), and the static regulator sleep modes the S1
   table names as the next stage. Then lid close uses `mem` instead of
   `s2idle`. This is the largest practical gain for the least new risk: no
   new firmware call, the module already exists.
2. **Find the awake regression before S2.** About 180 mA awake against
   R1b's figure dwarfs what S2 can save. A stepwise unload on battery (the
   display driver, the GPU, the A53 DVFS modules, then the rest) on one boot
   should name it.
3. **Build S2 after 1, as one image stage.** Estimate, from C0 attempt 2's
   differences at the idle points (CPU1-3 about 3 mA per core in WFI, the
   whole L cluster 25.6 mA): powering down CPU0, the LL cluster, MCUSYS and
   CCI could save on the order of 10-20 mA of the 42 mA. That is an
   inference from awake WFI figures; a suspended core with its PLL off may
   leak less. The costs: one built-in export so the module can call
   `CPU_SUSPEND` `0x1010000`, a firmware call never issued on mainline; a
   resume through the secure firmware's warm boot, where a failure loses
   CPU0 and needs the owner's force-off; and keeping flag bit 9 set, so the
   program still leaves the DA9214 to the A72 module and the DVFS work.
   Worth doing, but after 1 and 2.
4. **Do not build S3 now.** Deep idle and SODI keep 26 MHz and infra, so
   they save less than suspend. They also need P3 (clock gating), a GPT
   clockevent and CIRQ, and every device's interrupt to wake them. With S1
   on lid close and the CPU policy on blank, S3 adds the least per unit of
   risk. Revisit it after P3.
5. **Do not wait for a project-written program.** The decode already answered
   feasibility: a reduced program (no DRAM self-refresh) is original work and
   possible, but it saves less than the vendor program now does. It matters
   only if the station must stop depending on the unit's own vendor files,
   for example for redistribution. That is a separate owner choice.

### Item 1: S1 as the station's suspend (prepared 2026-11-08)

The owner approved the order above ("Its order: suspend, idle", relayed by
the custodian). Item 1 has three parts:

- [`0678`](../../patches/proposals/0678-watchdog-mtk_wdt-stop-a-watchdog-running-from-boot-a.patch),
  built in: `mtk_wdt_suspend()` and `mtk_wdt_resume()` also stop and restart a
  watchdog that is only `watchdog_hw_running()`. The core keeps owning and
  kicking it after resume. No feeder is needed any more. Upstreamable.
- [`0679`](../../patches/proposals/0679-soc-mediatek-mt6797-spm-sleep-add-the-static-PMIC-sl.patch),
  module: the static PMIC sleep modes in `mt6797-spm-sleep`, behind a new
  `pmic_modes` parameter (default off, writable at runtime), so one boot can
  compare with and without them. The table follows the vendor's
  `spm_pmic_power_mode(PMIC_PWR_SUSPEND)`, minus three things: each rail's
  enable and enable-control bits (the vendor turns rails on that mainline
  keeps off, and clearing enable control could turn one off), VSRAM_PROC's
  0.7 V sleep voltage (CPU0 stays powered in this mode), and the vendor's
  unexplained whole-word write of `0x020e` to `LDO_VA10_CON0`.
- [`backlight-policy.c`](../2026-10-30-mainline-dev-station/backlight-policy.c):
  on a lid close, if `/sys/power/mem_sleep` offers `[deep]` (that is, the SPM
  module is loaded), it writes `mem` to `/sys/power/state`. A refusal (a
  charger attached, a radio on) is logged once and waits for the next close.
  After a PCM-timer wake with the lid still closed it suspends again, unless
  that suspend returned within 2 s. Without the module nothing changes:
  `mem` would mean s2idle, which this policy does not use. Lid open wakes
  through the Hall EINT, which S1's wake mask (S16) admits.

Loading the module at boot stays out until this stage passes, as the project
does for every new module.

Checks: in a private VM worktree of the series through 0677, both patches
compile with `W=1` and no warning (`mtk_wdt.o`; the module with `M=`), and
checkpatch reports only the missing sign-off, which the project does not
invent. `backlight-policy` builds with the release flags. None of it has
run.

**Writes for owner approval**, beyond the S1 list already approved for
boot 3:

| # | Where | Write |
| --- | --- | --- |
| D1 | TOPRGU `WDT_MODE` `0x10007000` | At suspend: enable bit 0 cleared, written with the mode key, by the driver's existing stop. At resume: the driver's existing start and kick (timeout, mode, `WDT_RST` kick), as at boot |
| M1-M8 | MT6351 `BUCK_VCORE_CON9` `0x0612`, `BUCK_VGPU_CON9` `0x0626`, `BUCK_VS1_CON9` `0x0676`, `BUCK_VS2_CON9` `0x068a`; `BUCK_VCORE_CON1` `0x0602`, `BUCK_VGPU_CON1` `0x0616`, `BUCK_VS1_CON1` `0x0666`, `BUCK_VS2_CON1` `0x067a` | Only with `pmic_modes=1`, in `.prepare`: CON9 bit 8 ← 1 (sleep voltage enabled); CON1 bits 5:3 ← 0 (selected by SRCLKEN0) |
| M9-M14 | MT6351 `LDO_VA18_CON0` `0x0a00`, `LDO_VUSB33_CON0` `0x0a16`, `LDO_VIO28_CON0` `0x0a34`, `LDO_VIO18_CON0` `0x0a4c`, `LDO_VA10_CON0` `0x0a6e`, `LDO_VLDO28_CON0` `0x0a9c` | Only with `pmic_modes=1`: bit 2 ← 1 (low-power mode under hardware control), bits 7:5 ← 0 (SRCLKEN0). Bits 1 and 3 (enable, on control) untouched |
| M15 | MT6351 `TOP_CON` `0x0204` | Only with `pmic_modes=1`: bit 6 ← 1 (oscillator in hardware mode) |
| M-restore | the same fields | In `.finish`, each field back to its value read in `.prepare` |
| L1 | `/sys/power/state` | `mem`, from `backlight-policy` on a lid close; the suspend is the S1 path |

The sleep voltages these select are whatever the preloader left in each
buck's `CON6`; T0 reads them, since the vendor relied on the same
preloader values.

**Candidate.** Profile `mt6797-a53-station-dvfs` from the commit that records
this stage: D2's inputs plus 0678 and 0679. 0678 is built in, so it needs a
new image (a boot2 write under the standing approval). The module and
`backlight-policy` come from the same package and commit; the vendor program
is staged by hand as for boot 3.

**Procedure** (owner present; Wi-Fi, Bluetooth and FM unloaded; A72 module
not loaded; no watchdog feeder):

| Stage | Action | Pass | Stop |
| --- | --- | --- | --- |
| T0 | Cable in: identity, taint; load `mt6797-spm-sleep`; read `mem_sleep` (expect `s2idle [deep]`); read the 15 M-fields and the four bucks' `CON6` through the wrapper regmap's debugfs | Module lines as in boot 3; values recorded | Load error |
| T1 | Unplug. `timer_sec=60`, `pmic_modes=0`, one `mem` suspend | `wake: returned=1`, r12 bit 0, uptime +60 s, no reset. This is 0678: a 60 s sleep outlives the 31 s timeout | A reset or no wake within 120 s: force-off, no retry |
| T2 | `timer_sec=300`. Two suspends with `pmic_modes=0`, then two with `pmic_modes=1`, with `charge_counter` read before and after each | All four return on the timer; after each `pmic_modes=1` suspend the 15 fields read back as in T0 | A field not restored; a wake other than the timer |
| T3 | Copy the new `backlight-policy` over `/bin/backlight-policy`, kill the old one so init respawns it. `timer_sec=30`. Close the lid for about 90 s, then open it. Repeat twice more | Each close logs `PM: suspend entry (deep)`; the first close shows at least two timer wakes and re-suspends; the open wakes it with the EINT bit in r12; display back, a key works, no warning | A wake loop (`woke at once`), a missing display or keyboard, a warning |
| T4 | Cable in, close the lid | `lid suspend refused` logged once, station stays up | A suspend with the cable in |

Stops shared by every stage: an Oops, `WARNING` or RCU stall; taint
changing; USB SSH absent 60 s after an expected wake (owner's force-off).

| Result | Next |
| --- | --- |
| T1-T4 pass, T2 shows 3 mA or more saved with the modes | `pmic_modes` defaults on; load the module at boot after a longer soak |
| T1-T4 pass, the modes save less | Leave them off; load at boot after the soak |
| T1 resets | 0678 does not stop the watchdog on this path; read `WDT_MODE` before suspend on the next boot |
| T3 fails | The policy or the lid wake needs work before lid-close suspend is used |

### Item 1 result (2026-11-08)

Run by the custodian on D3 (station-work-94, boot2 `1f201b4e…`, from
`5ed802b4`); recorded in the test plan,
[D3 item 1](../2026-11-08-cpu-power-test-plan/README.md#d3-item-1-s1-as-the-stations-suspend-2026-11-08).

- **T0:** the module loaded as in boot 3, and `mem_sleep` read `s2idle [deep]`.
  Before any write the fields read: `TOP_CON` `0x010b`; all four bucks
  `CON1` `0x0000` and `CON9` `0x0001`; the LDOs `da68`, `da68`, `da62`,
  `da62`, `da62`, `0260` in table order; the bucks' `CON6` `0040`, `0040`,
  `0040`, `000c`.
- **T1: 0678 works.** A 60 s `mem` suspend with no feeder returned on the
  timer, with no reset.
- **T2:** two suspends with `pmic_modes=0` read 44.6 and 43.3 mA, then two
  with `pmic_modes=1` read 42.1 and 40.9 mA (about ±1 mA per window). Every
  field read back as before after each suspend.
- **T3:** three lid closes, with 2, 16 and 1 timer re-suspends; each open
  woke with `r12=0x40`; `returned=1` throughout, no warning. One resume logged
  `i2c 4-0020: Unbalanced pm_runtime_enable!` (sent to the suspend session).
- **T4:** with the cable in, the close was refused once, logged, and the
  station stayed up.
- **Blocking defect, outside this record:** after a `mem` resume on battery,
  USB never enumerates again on a replug, even after `soft_connect` and role
  cycles; only a reboot recovers it. The suspend session has it.

**Reading.** The suspend path, the watchdog fix and lid-close suspend work.
The modes show no effect that can be told from drift: the four windows fell
steadily (44.6, 43.3, 42.1, 40.9 mA), about 1.2 mA per window both within
each setting and between them, so the 2.5 mA "saving" is the same size as
the trend. By the table, and on this reading, `pmic_modes` stays off. If
it is ever worth another look, interleave the windows (off, on, off, on).
Loading the module at boot waits for the USB fix and a soak.

### Item 2: find the awake regression (proposal)

**Question.** With CPU0 alone, the screen blanked, the radios off and
`backlight-policy` stopped, the station drew 96 mA in R1b (image from
`e4e09b1a`) and about 271-290 mA in the last two runs (station-work-91 and
D1). What draws the other ~180 mA?

**Method.** One boot, on battery, cable out after setup. Hold the R1b state:
CPU1-9 offline, `fb0` blanked, the policy frozen with `kill -STOP`, radios
unloaded. Then remove one group at a time and measure each step for 120 s
with `charge_counter` and `current_now` at 1 Hz, after 10 s of settling.
With each window also record: `/proc/stat` CPU0 idle share, `/proc/interrupts`
deltas, the five busiest threads (`top -bn1`), VPROC1 and VCORE voltages
from their regulators, and at the start and end `clk_summary` (enabled
clocks) and `pm_genpd_summary`.

| Window | Removed before it |
| --- | --- |
| U0 | nothing (the reference; should reproduce 271 mA) |
| U1 | the A53 DVFS and cpufreq modules (`cpufreq-dt`, the CCI devfreq, `clk-mt6797-mcusys`), after setting the policies to their lowest point; VPROC1 recorded before and after |
| U2 | the GPU (`panfrost`; MFG domain off in `pm_genpd_summary`) |
| U3 | the display stack (the DRM and panel modules), after the blank |
| U4 | audio, camera receiver, sensors, touchscreen, vibrator, AW9120 LEDs |
| U5 | userspace that is not needed: any logger other than the window's own, `getty` on tty1 |

**What decides it.** The step whose removal drops the current by 30 mA or
more names the holder; it goes to that driver's session. If U0 shows CPU0
busy (idle share under 90 %) the cause is a thread or an interrupt storm
instead, named by `top` and `/proc/interrupts`. If no step drops it, the
next step is an image comparison against R1b's inputs.

**Writes.** None new: module unloads and reloads, sysfs, reads. Nothing is
reloaded between windows; at the end the station is powered off and boots
boot2 again, so a driver that does not come back cleanly needs no recovery.

**Stops.** A module that refuses to unload is skipped and recorded; an Oops
or `WARNING`; the battery under 30 %.

### Item 2 result (2026-11-09)

Run by the custodian on D3, boot `d7f02aca…`; recorded in the test plan,
[D3 item 2](../2026-11-08-cpu-power-test-plan/README.md#d3-item-2-the-awake-regression-2026-11-09).
The boot had already run the DVFS tests, so the A53 DVFS stack was loaded
(LL 897 MHz, CCI 676 MHz, VPROC1 1060 mV). U0 read 274.5 mA; U1 (policy0 to
221 MHz, then `mtk_cci_devfreq`, `cpufreq_dt`, `clk_mt6797_mcusys` and the
VSRAM and DA9214 regulators unloaded) read 70.2 mA; nothing after U1 moved it.
CPU0 was over 98 % idle, and interrupts and `pm_genpd_summary` were the same
in U0 and U1.

**Reading.**

- **The 200 mA is a hardware state, not running code.** Boot 3's 271 mA
  reference had none of these modules loaded, and U1 is below R1b. Something
  in the boot state of the newer images costs about 200 mA, and the U1
  sequence clears it.
- **The two gauges disagree after U1.** `current_now` read 93-95 mA where
  `charge_counter` read 67-70 mA, while in U0 both read 274-275 mA. R1 and
  R1b used `current_now` (96-111 mA). So R1b's 96 mA most likely *was* the
  low state U1 reaches, and the newer images boot into the high one.
  Comparisons from here use `charge_counter`.
- **Candidates for what U1 changed:** the LL clock (897 to 221 MHz) and
  VPROC1 (1060 to 1000 mV) are too small for 200 mA at 99 % idle. More
  likely is a mode or a gate that one of the unloads reset: the DA9214
  regulator's remove or a buck mode it set (a forced-PWM buck alone can draw
  tens of mA), the `clk-mt6797-mcusys` unload unregistering three prepared
  PLLs, or something built in or loaded at boot on the newer images that
  R1b's image lacked.

### Item 3: which step holds the 200 mA (proposal)

**Question.** Is the newer images' boot state itself at about 270 mA, and if
so, which single load or unload of the DVFS stack moves it?

**Method.** A fresh boot of D3, nothing run before it. CPU0 alone, `fb0`
blanked, `backlight-policy` frozen with `kill -STOP`, radios and the A72
module unloaded. Battery, cable out after setup. Each window is 120 s after
10 s of settling, measured by `charge_counter` (with `current_now` logged
beside it). At the start of the run and after every step, record:

- `lsmod`, to settle whether any of these modules loaded at boot by
  themselves;
- MCUMIXED `0x1001a200`, `0x1001a204`, `0x1001a210`, `0x1001a214`,
  `0x1001a220`, `0x1001a224` (ARMPLL CON0 and CON1 for LL, L, CCI),
  `0x1001a270` (mux), `0x1001a274` (divider), FHCTL `0x1001af00` and
  `0x1001af04`;
- MCUCFG `0x10220740`-`0x1022074c` (sync DCM);
- INFRACFG_AO `0x10001f98`, `0x10001f9c`, `0x10001fa0` (VSRAM_L);
- DA9214 at `0x68`, direct-address reads `0x50`-`0x5f` and `0xd0`-`0xdf`
  (the read-only provider's addresses, no page change): through the
  driver's regmap debugfs while it is bound, with `i2cget` while it is not;
- SoC temperature.

| Window | Step before it |
| --- | --- |
| N0 | none: the boot state |
| N1 | load the DA9214 and VSRAM regulator modules |
| N2 | load `clk-mt6797-mcusys` |
| N3 | load `cpufreq-dt`; policy0 `userspace` at 897 MHz (the boot rate) |
| N4 | policy0 at 221 MHz |
| N5 | load the CCI devfreq at its lowest point |
| N6 | unload the CCI devfreq |
| N7 | unload `cpufreq-dt` |
| N8 | unload `clk-mt6797-mcusys` |
| N9 | unload the regulators |

About 22 minutes on battery.

**What decides it.** If N0 reads about 70 mA, the boot state is cheap and
the stack raises it: the window where it jumps, and the registers that
changed there, name the step. If N0 reads about 270 mA, the boot state is
costly: the unload window where it falls, and its register diff, name what
clears it. Either way the next change is a fix in that driver or a boot-time
setting, decided with the A53 DVFS session, which owns those drivers.

**Writes.** None new: the DVFS stack's own loads, rate requests and unloads,
already approved for V1-V7, and reads. **Stops:** an Oops or `WARNING`; a
module that refuses to load or unload (record it and skip to the next step);
the battery under 30 %. Power off at the end.

### Item 3 result (2026-11-09)

Run by the custodian on a fresh D3 boot, `2902b8f5…`; recorded in the test
plan ("D3 item 3", `ae43916e`). **The boot state is cheap:** N0 read
80.2 mA by `charge_counter`. The windows read N0 80.2, N1 77.1, N2 77.1,
N3 80.2, N4 (LL at 221 MHz) 70.3, N5 (CCI devfreq) 88.6, N6 88.7, N7
(`cpufreq-dt` out) 70.3, N8 70.3, N9 67.2 mA, with no fault and taint 0.

- No DVFS module loaded at boot. Boot registers: LL CON1 `0xC1114000`
  (897 MHz), L `0x400C4000` (1274 MHz), CCI `0xC10C1D89`, sync DCM
  `0x00070707`, VSRAM_L `0x0B`, DA9214 `0xd7` = `0x46`. N4 changed only LL
  (`0x41110000`, divider field `0x160`); at N9 `0xd7` read `0x36`.
- The CCI devfreq probe deferred (`-517`, CPU4-7 offline), yet VSRAM_L
  went to `0x0F` (1200 mV) at N5 and stayed until `cpufreq-dt` unloaded:
  about 18 mA. The custodian sent this to the cpufreq session as a probe
  error-path leak.
- The DA9214 reads while its driver was bound failed (`EBUSY`; its regmap
  has no debugfs node), so only the boot and N9 values exist.
- `current_now` again disagreed with `charge_counter` from N4 on.

**Reading.** The 271 mA state is not the boot state and not any single step
of the DVFS stack. It came from earlier work on the same boot: item 2's
reference followed the DVFS tests V1-V7, and boot 3's followed a 30 s `mem`
suspend. C0 attempt 2's 290-324 mA followed V0 on its boot. Something in that
work raises it, and the full DVFS unload of item 2 cleared it.

### Item 4: what raises the 271 mA state (proposal)

**Question.** Does a `mem` resume raise it, does the DVFS load test (V7:
CPU1-7 online under schedutil, CCI 676-988 MHz) raise it, and what register
state differs when it is high?

**Setup.** A fresh D3 boot, nothing run before it. CPU0 alone, `fb0` blanked,
`backlight-policy` frozen with `kill -STOP`, radios and the A72 module
unloaded, battery, cable out after setup. Windows of 120 s after 10 s of
settling, by `charge_counter`. "High" means 150 mA or more.

**Reads**, at boot and after every step (all reads; `devmem` for MMIO; the
DA9214 by `i2cget` only while its driver is not bound, by its regulators'
sysfs voltages while it is):

- MCUMIXED: `0x1001a200`, `0x1001a204`, `0x1001a210`, `0x1001a214`,
  `0x1001a220`, `0x1001a224`, `0x1001a270`, `0x1001a274`; FHCTL
  `0x1001af00`, `0x1001af04`.
- MCUCFG DCM and bus (vendor `mt_dcm.c` names): `0x1022002c`, `0x1022022c`,
  `0x10220648`, `0x10220660`, `0x10220668`, `0x10220740`, `0x10220744`,
  `0x1022074c`, `0x10222274`.
- INFRACFG_AO: `0x10001000` (`TOP_CKMUXSEL`), `0x10001010` (`TOP_DCMCTL`),
  `0x10001024`, `0x10001028`, `0x1000102c` (bus dividers), `0x10001070`,
  `0x10001074` (infra and peri bus DCM), `0x10001078`, `0x1000107c` (memory
  DCM), `0x10001f18`, the gate status words `0x10001090`, `0x10001094`,
  `0x100010b0`, and VSRAM_L `0x10001f98`, `0x10001f9c`, `0x10001fa0`.
- TOPCKGEN `CLK_CFG_0`-`7`, `0x10000040` to `0x100000b0` in steps of
  `0x10`.
- SPM: `0x1000600c`, `0x10006018`, `0x10006180`-`0x1000618c`, `0x10006600`.
- DRAMC `0x102141dc`, `0x102141ec`; EMI `0x10203060`.
- DA9214 at `0x68`: `0x50`-`0x5f`, `0xd0`-`0xdf`.
- `clk_summary` (enabled clocks only), `lsmod`, SoC temperature.

| Step | Action | Then |
| --- | --- | --- |
| A0 | none | window; reads (should read about 80 mA) |
| A1 | load `mt6797-spm-sleep`; one 30 s `mem` suspend | window; reads |
| A2 | only if A1 is high: load and unload `clk-mt6797-mcusys` | window; reads |
| A3 | only if still high: the DVFS stack loaded, policy0 at 221 MHz, then unloaded in item 2's order | window; reads |
| B1 | only if A1 is not high: load the DVFS stack and run V7 as the A53 DVFS session runs it, then CPU1-7 offline again | window; reads |
| B2-B5 | only if B1 is high: unload the CCI devfreq, `cpufreq-dt`, `clk-mt6797-mcusys`, the regulators, one per step | window and reads after each |

About 20-25 minutes on battery, depending on the branch.

**What decides it.** The first step whose window is high names the cause,
whether a resume or the load test. The reads that differ from A0 at that
step say which block is left changed: a PLL, a DCM bit, a bus divider, an
infra clock, VSRAM or a buck. The step that brings it back down confirms
it. The fix goes to the owner of what changed: the SPM sleep module (this
record) for a resume, the A53 DVFS session for the load test.

**Writes.** None new: the S1 list as approved for boot 3, the DVFS stack's
own writes as approved for V1-V7, and reads. **Stops:** an Oops or
`WARNING`; no wake within 60 s of the expected one (force-off); a module
that refuses to load or unload (record it and go to the next step); the
battery under 30 %. Power off at the end.

### Item 4 result (2026-11-09)

Run by the custodian on a fresh station-work-95 boot, `b7dba389…`; recorded
in the test plan ("D3 item 4", `4103b168`). Branch A ran:

| Window | Average (`charge_counter`) |
| --- | --- |
| A0 | 80.2 mA |
| A1, after one 30 s `mem` suspend (timer wake, rc 0) | 274.5 mA |
| A2, after loading and unloading `clk-mt6797-mcusys` | 234.4 mA |
| A3, after the DVFS stack loaded, LL at 221 MHz, all unloaded | 64.2 mA |

- **Every register read was identical at A0, A1 and A2**: MCUMIXED, MCUCFG,
  INFRACFG, TOPCKGEN, SPM, DRAM and the DA9214. The resume left none of the
  read registers changed. A3 showed only the known LL, divider, `0x660` and
  VPROC1 changes.
- **The display came back on after the resume.** DRM read the panel again at
  268.9 s. `clk_summary` listed 126 enabled clocks at A1 and A2
  (`mipi_tx0_pll` and 13 `mm_*` display gates) against 112 at A0 and A3.
  Nothing in the log shows when they went off between A2 and A3, with
  `consoleblank` at 120 s.
- After the resume, `soc-thermal` reads `ENODATA`.

**Reading.** The 200 mA is most likely the display pipeline, not the SPM
program or the CPU clusters. The resume brought the DSI link and the display
clocks back although `fb0` had been blanked. The fall at A3 fits the
kernel's console blank turning them off again, not the DVFS unload. Item 2's
fall at U1 and C0 attempt 2's high windows may have the same cause, though
their display state was not read. What A1 does not tell yet is whether the
panel and backlight were lit, or only the pipeline was running.

**`soc-thermal` returning `ENODATA` after a `mem` resume is a safety
problem**: the passive and hot trips need that reading. Loading the SPM
module at boot, or using lid-close suspend outside a test, must wait until
the thermal driver reads again after a resume. That belongs to the suspend
session or the thermal owner.

### Item 5: the display across a resume (proposal)

**Question.** Is the 200 mA after a `mem` resume the display pipeline
coming back on while `fb0` is blanked, and does blanking again remove it?

**Setup.** As item 4: a fresh boot, CPU0 alone, radios and A72 off,
`backlight-policy` frozen with `kill -STOP`, battery. In addition, the
kernel's console blank is off (`printf '\033[9;0]' > /dev/tty1`), so no
timer changes the display behind the test. `fb0` is blanked with `4`
(powerdown).

**Reads** at each step: `fb0/blank`; the backlight's `brightness`,
`actual_brightness` and `bl_power`; each DRM connector's `status`,
`enabled` and `dpms`; the enabled `mm_*` and `mipi_*` clocks in
`clk_summary`; the MM domain in `pm_genpd_summary`; new DRM and panel lines
in `dmesg`; the SoC temperature through `soc-thermal`. The custodian or the
owner also notes whether the panel is visibly lit.

| Step | Action | Window |
| --- | --- | --- |
| E0 | none | 120 s (should read about 80 mA) |
| E1 | load `mt6797-spm-sleep`; one 30 s `mem` suspend | 120 s |
| E2 | `echo 4 > /sys/class/graphics/fb0/blank` again | 120 s |
| E3 | `echo 0` then `4` to `fb0/blank` (a full unblank and blank) | 120 s |

**What decides it.**

| Result | Next |
| --- | --- |
| E1 high with the display clocks on, E2 or E3 back to about 80 mA | The display's resume does not keep a blanked display off. The fix goes to the display session; until then lid-close suspend must blank again after each resume (`backlight-policy` can do that) |
| E1 high with the display clocks off | Something else the resume leaves on; read more blocks (GPU, MSDC, USB) |
| E1 about 80 mA | The resume alone does not raise it; look again at what else ran before A1 in item 4 |

**Writes.** None new: the S1 list as approved and `fb0` writes. **Stops:**
the usual ones; also stop if `soc-thermal` reads `ENODATA` and the SoC is
above 50 °C, since then nothing would cap it.

### Item 5 result (2026-11-09)

Run by the custodian on a fresh station-work-95 boot, `6b9cf9c0…`, on
battery with `consoleblank` 0; recorded in the test plan ("station-work-95
item 5", `6449b128`).

| Window | Display state | Average |
| --- | --- | --- |
| E0, `fb0` blanked with 4 (reads back 1) | DPMS off, `bl_power` 4, 2 display clocks | 114.1 mA |
| E1, after one 30 s `mem` suspend | `fb0` 0, DPMS on, `bl_power` 0, 16 display clocks | 286.9 mA |
| E2, `fb0` blanked with 4 again | off, 2 clocks | 77.1 mA |
| E3, `fb0` 0 then 4 | off at the step | 209.8 mA |

E0 and E3 are mixed windows: DRM read the panel again at 220.8 s (inside E0)
and 562.8 s (inside E3) with no test step behind it, and the end read found
the display on. No input was logged. `soc-thermal` read `ENODATA` after the
resume again; the battery zone stayed near 24 °C. No fault, taint 0.

**Conclusion of the search.** The "awake regression" was the display
turning itself back on, backlight included. A `mem` resume unblanks it, and
so does something else while `fb0` is blanked through sysfs, without any
input. Blanked, the station idles at about 77-80 mA with CPU0 alone, close
to R1b. With the display on, at the test's brightness, it draws about
200 mA more. Nothing in the SPM program, the CPU clusters or the DVFS stack
holds extra power. The fixes belong to the display session:

- a blanked display must stay blanked across a system resume;
- the spontaneous unblanks with `fb0` blanked through sysfs and no input.
  One candidate is the VT layer: it does not know about a blank made through
  `fb0/blank`, so console activity can redraw and unblank it. The station's
  own policy blanks through the console, which the VT does know about.
  `fb0/blank` was only the test's method.

Until the display keeps its blank, lid-close suspend would wake to a lit
screen inside a closed lid; that adds to the `soc-thermal` blocker above.

### Charger plug-in wake in `mem` (2026-11-10)

The suspend session's test W3 needs a charger plug-in (MT6351 CHRDET,
patches 0685 and 0686) to wake a `mem` suspend. No change to
`mt6797-spm-sleep` is needed for that. The MT6351 interrupt reaches the SoC
as EINT176 ([0007](../../patches/v7.1.3/0007-arm64-dts-mediatek-mt6797-add-PMIC-wrapper.patch),
IRQ 191 on the station), and S1's wake mask (S16, `0xffffffbe`) already
unmasks the EINT event, bit 6. T3's lid opens woke through that same bit
(`r12=0x40`). The EINT controller arms only lines marked for wake, so the
MT6351 interrupt chip must arm its parent when the CHRDET child is marked,
as it does for the power key and the RTC in s2idle. Not yet shown under
`mem`: W3 is the first PMIC wake there. If W3 does not wake, the next reads
are the wake line's `r12` and the EINT wake mask for EINT176.

**W3 result (2026-11-10).** On station-work-97 (boot `56832cd1…`), a `mem`
suspend with a 120 s timer, the owner plugging in at about 20 s, resumed
at about 59 s with `wake: returned=1 loops=2 r12=0x00000040`: the EINT event,
not the timer, but not at the plug. Recorded in the test plan,
"station-work-97". Two notes for reading it:

- `loops` is not an SPM loop. It counts the WFIs CPU0 ran in `.enter`
  before the PCM-return interrupt. `loops=2` means CPU0 woke once early,
  with no PCM return, most likely on the plug's interrupt itself reaching the
  GIC, and went back to WFI. So the interrupt reached CPU0 at the plug; the
  SPM program did not return until later.
- The wake line's `timer_out` gives the SPM's own sleep length (its upper
  half-word counted 5, 15 and 150 for 10, 30 and 300 s), and `raw`,
  `misc` and `isr` give its raw wake sources. They are in the kept log and
  settle when the SPM woke without a rerun.

The kept wake lines settle when the SPM woke. `timer_out` is the SPM's
sleep in 32,768 Hz ticks: the 30 s timer wake read `0x000f0088`
(30.004 s); W3 read `0x001d4850`, **58.6 s**, with `raw=0x40` (EINT) and
`misc=0x00010000` (the timer wake read `0x00080000`). So the SPM program
itself slept through the plug and woke on an EINT event about 38 s after
it. When CPU0's one early WFI exit happened is not known.

One candidate fits the plug's interrupt storm in W2 (CHRDET 4 → 47 for one
plug, cause unknown): if the MT6351's shared, level-high interrupt line was
still high when the suspend began, the SPM would see no new EINT edge at the
plug, and would wake only on a later change of the line.

**Timed W3 rerun (2026-11-10).** Same boot; recorded in the test plan,
"station-work-97 CHRDET trace and timed W3" (`d77d3feb`). The owner plugged
in 21 s after a logged start, and the station resumed 120.75 s after it. The
wake line read `loops=2 r12=0x00000041 raw=0x00000040 misc=0x00090000
timer_out=0x003c0088`: the SPM slept the full 120 s and returned on its timer
with the EINT event also latched. CHRDET counted one interrupt across the
suspend. The MT6351 `INT_STATUS0`-`3` all read `0000`, and its `INT_CON`
words were unchanged, before and after both this suspend and a plain 30 s
one. The "line already high" candidate is out: the W2 "storm" was a counting
error (offline CPUs drop their `/proc/interrupts` columns).

**Reading.** The plug's interrupt reached the SPM (EINT latched) and the GIC
(CPU0 left WFI once, the interrupt was counted), but the program did not end
its sleep on it. What differs from the vendor flow is that S1 leaves the
GIC as Linux left it: every wake interrupt stays enabled, so the plug takes
CPU0 out of WFI at the GIC while the program sleeps. The vendor masks every
GIC interrupt but the SPM's before its suspend (`mt_irq_mask_all`, then
`mt_irq_unmask_for_sleep(SPM_IRQ0_ID)` in `mt_spm_sleep.c`), so in its flow
only the program wakes the CPU. The suspend program likely reads CPU0
leaving `STANDBYWFI` (S9 sets "WFI AND") in its own way, and misses the
wake event; that is inferred, not traced. The lid wakes in T3 did end the
sleep on EINT, but their timing against the open was not measured.

[`0688`](../../patches/proposals/0688-soc-mediatek-mt6797-spm-sleep-optionally-mask-the-GI.patch)
adds a `gic_mask` parameter (default off): around the WFI loop it disables
every SPI but the SPM's (SPI 180, INTID 212) at the GIC distributor and puts
the saved enable bits back afterwards. A wake interrupt then stays pending at
the GIC and is taken after the resume, as in the vendor flow. Compile-checked
with `W=1`, checkpatch quiet. Module only: no new image if the package is
otherwise identical to the running one.

**Writes for owner approval** (only with `gic_mask=1`, CPU0 with interrupts
off, inside `.enter`):

| # | Register | Write |
| --- | --- | --- |
| G1 | GICD `ISENABLER1`-`n` `0x19000104` + 4i | read and saved (`n` from `GICD_TYPER` bits 4:0, at most 31) |
| G2 | GICD `ICENABLER1`-`n` `0x19000184` + 4i | the saved enables, minus INTID 212's bit (register 6, bit 20) |
| G3 | GICD `CTLR` `0x19000000` | read until RWP (bit 31) clears, 10 ms bound |
| G4 | GICD `ISENABLER1`-`n` | after the loop, the saved words again (only set bits; nothing newly enabled) |

**Test W3b** (fresh boot, cable out since boot, the usual S1 setup, timer
120 s; the script logs `date +%s.%N` before each `echo mem`, and the owner
acts on a logged "GO"):

| Step | `gic_mask` | Owner action at 20 s | Pass |
| --- | --- | --- | --- |
| G0 | 0 | open the lid (closed before `mem`) | records how the lid behaves without the mask: `timer_out` and `loops` |
| G1 | 1 | open the lid | `timer_out` about 20 s, `r12` EINT, `loops=1` |
| G2 | 1 | plug the charger in | `timer_out` about 20 s, `r12` EINT, `loops=1`, CHRDET counted |
| G3 | 1 | none | a plain timer wake, `loops=1`, no fault |

Also read before and after each suspend: `/proc/interrupts` 191 and 209
(summed over the online CPUs only), and the EINT bank holding EINT176
(bank 5, bit 16): status, mask and sensitivity at base `+0x014`, `+0x094`,
`+0x154` from the station DT's EINT `reg`. **Stop** on an Oops or `WARNING`,
a missing wake within 60 s of the timer, or interrupts that do not work
after the resume (keyboard, USB SSH): G4 should restore every enable bit,
and a lost one would show there.

| Result | Next |
| --- | --- |
| G1 and G2 wake at the action with `loops=1` | The GIC race is the cause; `gic_mask` defaults on |
| G2 still sleeps to the timer with the mask on | Not the GIC race; the program's handling of a level EINT is next (read the EINT controller's wake output) |
| G0 already wakes at the open | Lid edges get through without the mask and only the level PMIC line fails; G2 decides it |

**W3b result (2026-11-10).** Run by the custodian on the same boot,
`56832cd1…`, with the 0688 module (`53f9eb60…`, from `2054b72e`) swapped in
by `insmod`, which loaded cleanly. Recorded in the test plan,
"station-work-97 W3b". Each case is a `mem` suspend with a 120 s timer, the
owner acting at about 20 s:

| Case | `gic_mask` | Action | SPM slept | `r12` | `loops` |
| --- | --- | --- | --- | --- | --- |
| G0 | 0 | lid open | 17.6 s | `0x40` | 3 |
| G1 | 1 | lid open | 18.9 s | `0x40` | 0 |
| G2 | 1 | charger plug | 23.8 s | `0x40` | 0 |
| G3 | 1 | none | 120.0 s | `0x1` | 0 |

A key worked within 1-4 s after G1 and G2, so every enable came back; no
fault, taint 0, USB back after the replug. The EINT bank holding EINT176 read
status 0, mask `0xFFFEFFFF` (EINT176 unmasked), sensitivity `0xFFFFFFFF` at
every entry and exit; IRQs 191 and 209 each rose by one across G2.

**Reading.**
- **The GIC race was the cause.** With the mask the charger plug woke the
  program at the plug. The lid's EINT woke it promptly even without the mask
  (G0), so only the PMIC's interrupt was lost to the race.
- `loops` counts CPU0's early WFI exits; 0 means none. Unmasked, CPU0 left
  WFI early in every suspend, timer wakes included (`loops=1` before); masked,
  it never did.
- `/sys/power/mem_sleep` keeps listing `deep` after the module is removed
  (`[s2idle] deep`): the kernel does not drop the label with the operations.
  `deep` is only selected while the module is loaded, which is what
  `backlight-policy` checks, and a `mem` request without the module is
  refused by the kernel, so it is harmless.

[`0689`](../../patches/proposals/0689-soc-mediatek-mt6797-spm-sleep-mask-the-GIC-by-default.patch)
makes `gic_mask` default to on, as the vendor flow is; `gic_mask=0` still
gives the old behaviour. One line in the module; it applies on
`series-a53-station` through 0688 as `scripts/kernel` applies patches.

**Blockers cleared (2026-11-10).** The custodian reports all three passed on
the device, recorded in the test plan: USB after a resume (0681, U2 on
station-work-96, and after W2, W3 and W3b), `soc-thermal` after a resume
(0683, T-M on station-work-96: banks set up again, the 117 °C reset re-armed,
readable for 10 minutes), and the display's blank (0684 on station-work-97,
74.5 mA after the resume).

### K1: an overnight soak before `mem` becomes the default (proposal)

Five suspends per run is not yet a default. One long run on the station
first, then the module loads at boot (station image) and the card moves from
`MemorySleepMode=s2idle` (its `gemini-base/sleep.conf` waits on this
record) to `deep`.

- **Candidate:** the running station image with the module from 0689
  (`gic_mask` on by default) by `insmod`, `pmic_modes` off, `timer_sec` 600,
  `backlight-policy` with lid-close suspend, the radios unloaded (the card's
  sleep hook does that there), no A72 module.
- **Run:** on battery, lid closed for at least two hours, so the station
  re-suspends after each 10-minute timer wake (about 12 cycles an hour). At
  the end: open the lid, check a key, the display, USB after a replug, and
  `soc-thermal`; then one charger-plug wake with the lid closed.
- **Measure:** `charge_counter` and time across the whole run (the average,
  awake gaps included); every wake line (`returned=1`, `r12` timer or EINT,
  `loops=0`); the count of cycles.
- **Pass:** every cycle returns, no fault or taint, all checks at the end
  pass, and the average stays near 42 mA plus the short awake gaps.
- **Stop:** any `returned=0`, a missing wake (no USB 60 s after the lid
  opens: the owner's force-off), an Oops or `WARNING`.
- **Writes:** none new: the S1 list, G1-G4, `mem` from the policy.

After K1 passes: the station image loads `mt6797-spm-sleep` at boot (the
program file is the owner's, staged as for the radio firmware), and the
Arch root session switches the card to `deep` with the module and
`pcm_suspend.bin` installed there.

## Deep idle with the screen off: the SODI route (plan, 2026-11-13)

The owner chose to pursue the vendor's system idle states instead of more
hotplug automation ("Pursue SODI instead", relayed by the custodian). The
target is the screen-off state while the station stays awake: music playing,
a download running, the Wi-Fi link kept. This section plans it from what is
already known (the [programs page](../../docs/hardware/mt6797-spm-programs.md),
the [SPM sleep page](../../docs/hardware/mt6797-spm-sleep.md), this record's
S0-S1, W3b and items 1-5). Nothing is built yet.

### Which state

The vendor has three system idle states, all entered from the last online
CPU's idle path, each a different SPM program (§4-5 of the programs page):

| State | Program | Display | What it gates (observed in the program) | Vendor entry conditions |
| --- | --- | --- | --- | --- |
| Deep idle | `pcm_deepidle.bin` | domain **off** | DRAM self-refresh, DRAM PHY off, MAINPLL off, the CPU (or not, flag 0); VCORE to 0.775 V through the wrapper slots; 26 MHz and infra stay on | one CPU online (CPU0 or CPU4); ISP, VDEC, VENC, MFG, MJC and the display domain off; the listed infra gates off; MSDC clocks off; next timer at least 2 ms away |
| SODI | `pcm_sodi.bin` | may stay on | DRAM clocks gated or the PHY down when no master needs DRAM (APSRC); 26 MHz, infra and VRF18 stay up | as deep idle, but the display domain may stay on and only the listed display clocks must be off |
| SODI3 | `pcm_sodi.bin`, flag 14 | may stay on | as SODI, two APSRC steps changed (not traced) | as SODI, plus UNIVPLL and MSDCPLL off, the audio bus and 26 MHz gates off, the display PWM on the low-power oscillator, uptime over 30 s |

**For a dark screen the vendor's state is deep idle, not SODI.** SODI is
its screen-*on* idle state, used when the display domain must stay up. Deep
idle saves more because MAINPLL and the PHY go down too. The plan therefore
aims at deep idle and keeps SODI as the fallback while the display domain
cannot be powered down on a blank. Both use the same loader, entry path and
wake handling, so the work is shared. SODI3 is out: it needs MSDCPLL off,
and the eMMC runs from it.

**What stays possible inside it.** The vendor's deep-idle wake mask adds
APXGPT and the audio interrupt to suspend's sources, and its PMIC table keeps
VA18 and VUSB33 out of low-power mode "for audio MP3". So music playback is a
designed case: the audio DMA interrupt ends each idle period, and the AFE's
APLL and 26 MHz stay up. CONNSYS keeps its 26 MHz, infra and DRAM requests
honoured through the SPM masks (`conn_mask_b` 1 in the vendor's deep-idle
`pwr_ctrl`) and wakes the program through CONN2AP (wake bit 5), so a joined,
idle Wi-Fi link is designed to survive it; each beacon or packet ends one
idle period. A download keeps DRAM, MSDC and Wi-Fi busy, so the state simply
is not entered while data moves.

**Exit latency.** The vendor accepts deep idle and SODI only when the next
timer is at least 2 ms away, and its DT gives the cluster power-down 800 us
entry, 1000 us exit and 2000 us minimum residency. The exit includes DRAM
self-refresh exit and the MAINPLL relock. So about 1 ms exit is the working
estimate, to be measured in stage D3.

### How it enters and leaves the one-CPU state

Deep idle needs exactly one CPU online. The station already has that
whenever the screen is dark: `backlight-policy` takes CPU1-7 down on a blank
or lid close, and since H1 it takes CPU8-9 down too when the A72 module has
them online. This route builds on that existing dark-screen hotplug; it is
not the cluster-hotplug automation the owner declined. When the screen
lights, the CPUs come back and the state is no longer entered, with no extra
code. The SPM itself does not hotplug.

The **A72 retest** matters only in one way: if the A72s end up online by
default, the dark policy must keep taking them down first, which H1 already
does. The programs never touch the A72 buck while flag 9 is set (as in S1),
and they leave the A72s' `CPU_EXT_BUCK_ISO` alone while flag 0 is set.

### The mainline mechanism

A `=m` module (`mt6797-spm-idle`, or a second mode of `mt6797-spm-sleep`
sharing the loader) registers a **cpuidle driver for CPU0 only**, with two
states: WFI, and "deep idle". `cpuidle_register()` is exported, so the
driver can live in a module; the kernel needs `CONFIG_CPU_IDLE` and a
governor (`menu` or `teo`), both built in. The deep-idle state's `enter`:

1. Checks its conditions each time and falls back to WFI with a counted
   reason if one fails (as the vendor's block counters do): one CPU online;
   the infra gate status words (`0x10001090`, `0x10001094`, `0x100010b0`)
   against the vendor masks; MSDC idle; the display domain (deep idle) or
   display clocks (SODI); next timer at least 2 ms away.
2. Hands the tick to the SPM: the PCM timer is set to the next timer event
   less the exit latency, and the local timer is masked for the wait. The
   vendor uses APXGPT GPT4 for this because it powers the CPU down; with the
   CPU kept powered (flag 0, as S1), the PCM timer avoids a new timer
   driver.
3. Masks the GIC as 0688 does and **clones the enabled edge SPIs into
   SYS_CIRQ** (`0x10204000`), so that any device interrupt, not just the
   suspend wake sources, ends the state through the SYS_CIRQ wake (bit 22).
   This is the lesson of W3: in idle, every interrupt must wake the program,
   not CPU0 behind its back. Upstream `irq-mtk-cirq` has the same register
   layout but no MT6797 entry; the module can program the block itself while
   it is in the state.
4. Loads the PMIC wrapper's deep-idle phase, sets the deep-idle `pwr_ctrl`
   and wake mask, kicks the program, executes WFI, and on the PCM return
   reads the wake reason, restores the GIC and CIRQ, replays CIRQ, and
   reprograms the local timer with what is left.

Keeping the program in the SPM's instruction memory between entries,
instead of fetching it each time, is a later optimisation; the first stages
reload it each time, as S1 does.

### What must exist first, in order

1. **K1 passes** (`mem` as the station's suspend). Same loader, same
   program handling, same GIC mask; deep idle reuses all of it.
2. **The idle conditions can be met.** Today they cannot: `clk_ignore_unused`
   keeps the infra gates the vendor requires off (SPI0-5, UART1-3, PWM,
   I2C, SSUSB, ...) running, R2 found PLLs with no user, and the display
   domain was not seen to power down on a blank. That is P3 in the
   [power-management record](../2026-11-06-gemini-power-management/README.md#plan)
   plus the display session's blank, owned elsewhere and built in or DT, so
   they go into one image. **This is the long pole.** It also saves power on
   its own, before any SPM state.
3. **The cpuidle core** (`CONFIG_CPU_IDLE`, a governor) in the image, in the
   same batch as 2. With no driver registered it changes nothing.
4. Then the module stages below.

### Stages

| Stage | What | Writes | Image |
| --- | --- | --- | --- |
| D0 | Census in the dark state (CPU0 alone, blanked), three cases: idle; Wi-Fi joined and idle; music playing. Reads only | None | Running |
| D1 | A `=m` module that only evaluates the entry conditions at each CPU0 idle and counts how often each one blocks, through debugfs (no SPM write) | None | Running, plus the module |
| D2 | P3 and the display blank (other sessions), then D1 again | Theirs | New, batched with `CONFIG_CPU_IDLE` |
| D3 | One deep-idle period on demand from debugfs, PCM-timer wake, CPU kept powered, GIC masked, no cpuidle yet; then a DRAM hash check | The S1 list adapted (below) | Running |
| D4 | D3 with a device interrupt as the wake: a key, then an audio period, then a Wi-Fi packet, each through SYS_CIRQ | D3 plus CIRQ | Running |
| D5 | The cpuidle state enabled, dark screen: idle, Wi-Fi joined, music; current and residency | D4 | Running |
| D6 | The CPU power-down variant (as S2), if D5 shows CPU0 in WFI is still worth taking down | D5 plus `CPU_SUSPEND` `0x1010000` and one export | New |

**D0 reads** (dark, CPU0 alone, 60 s per case): the three infra gate status
words; `PWR_STATUS`/`_2ND` (`0x10006180`/`184`: the display domain is bit 3);
the PLL enables in APMIXED for MSDCPLL, UNIVPLL, MAINPLL, APLL1/2 and the MIPI
TX PLLs; `CLK_CFG_0`-`7`; the enabled clocks in `clk_summary`; every MSDC
host's runtime PM status; GICD `ISENABLER1`-`n` (which SPIs CIRQ would have
to clone); the SYS_CIRQ block's registers at `0x10204000` (read only, to see
its reset state); `/proc/interrupts` deltas for CPU0 (how often idle would
be broken, by whom); and the governor's view of idle lengths from
`/sys/devices/system/cpu/cpu0/cpuidle` once the core is built (not today).

- *Hypothesis:* the blanked station fails the vendor's conditions on the
  infra gates and the display domain, and passes on one CPU, MSDC and the
  multimedia domains.
- *Unique observation:* the exact list of blocking gates and domains in each
  of the three cases.
- *Decision:* the list becomes P3's work list; if Wi-Fi or audio themselves
  hold a required gate, deep idle with them active is out and only plain
  dark idle remains for those cases.

**D0 script** (owner-approved 2026-11-13, "please proceed"):
[`tools/d0-census.py`](tools/d0-census.py), run as root with `python3 -I`.
`run CASE` waits for the desktop's own idle blank (DPMS off, `bl_power` 4;
it does not blank by itself), records whether anything hotplugged on the
blank, takes CPU1-9 offline (descending), records 60 s at 1 Hz, and brings
them back in ascending order, so CPU8 is first back to the A72 cluster. It
writes `/tmp/d0-CASE.log`. `cirq` reads the SYS_CIRQ block once, separately
and last.

- Every register access is a single 32-bit load through `/dev/mem`
  (`CONFIG_DEVMEM=y`, `CONFIG_STRICT_DEVMEM=y` without `IO_STRICT` in the
  station fragment); the mapping is read-write only so that `ctypes` can make
  that load, and nothing is stored.
- Only always-on blocks: INFRACFG_AO gate status `0x10001090`, `0x10001094`,
  `0x100010b0`; SPM `0x10006018`, `0x10006174`, `0x1000617c`, `0x10006180`-
  `0x1000618c`; TOPCKGEN `CLK_CFG_0`-`7` (`0x10000040` + `0x10`·i); APMIXED
  PLL `CON0` at `0x1000c220`, `230`, `240`, `250`, `260`, `270`, `290`,
  `2a0`, `2b4`, `2e4`; GICD `TYPER` `0x19000004` and `ISENABLER1`-`n`
  `0x19000104` + 4i; SYS_CIRQ (`cirq` only) `0x10204000`-`018`, `080`-`098`,
  `140`-`158`, `200`-`218`, `300`.
- MMSYS, AUDIO and MSDC registers are never read; their state comes from
  `clk_summary`, `pm_genpd_summary` and runtime PM in sysfs.
- The vendor's deep-idle and SODI gate masks (`mt_idle_mt6797.c`; INFRA0 is
  `0x94`, INFRA1 `0x90`, INFRA2 `0xb0`) and its power-status bits (display
  3, ISP 5, VDEC 7, MFG 12, MJC 20, VENC 21, audio 24) are applied to every
  sample, so the log names the blocking bits and how often each blocks.

**Cases.** Wi-Fi is the custodian's SSH path on the card root, so the "idle"
case is Wi-Fi joined and idle, with the SSH session quiet (start the script
detached). `music`: start playback in the owner's session first (`mpv` or
`pw-play` with a file of at least 5 minutes, to the speaker), then run the
case. A `download` case (a large `curl` to a file) is optional. Dry-run on a
fake sysfs and register file on the host; not run on the device.

**D3 writes** (for approval when D3 is prepared, register level now, values
pinned from S0-style reads first, as for S1): the S1 list with the deep-idle
program (`pcm_deepidle.bin`, hash-pinned) in place of the suspend one; the
deep-idle phase in wrapper slots 7 and 8 (`TOP_CON` bit 3, `SRCLKEN_IN2`)
instead of suspend's; the vendor deep-idle `pwr_ctrl` in `SPM_AP_STANDBY_CON`,
`SPM_SRC_REQ`, `SPM_SRC_MASK` and `SPM_SRC2_MASK` (CONN and modem requests
honoured, DVFS force-down); its wake mask (the vendor's suspend sources,
which already include SYS_CIRQ, plus APXGPT and audio; S1 used only the
timer and EINT); flags 0, 9 and 19 as in S1; G1-G4 as in 0688; and the
CPU0 timer mask around the WFI. No PSCI or SiP call. **D4 adds** the
SYS_CIRQ block: its sensitivity, polarity and mask words cloned from the GIC
for the enabled edge SPIs, its enable at entry, and its flush and disable at
exit.

### D0 result (2026-11-13)

Run by the custodian on the card root (card-32, boot `e7e3b009…`,
station-work-116, A72s online and taken down by the script), script
`c59e96d3` with its hash checked on the device. Cases `wifi-idle` and
`music` (a tone through `pw-play` to the speaker, PCM running), then `cirq`;
the optional download case was skipped. No error, taint 0, CPUs back to 0-9
each time. Nothing hotplugged on the blank: the card root, unlike the
station's init, has no dark-screen CPU policy. The custodian's own loggers
ran throughout (an evdev reader, a 10 s `/proc/interrupts` loop writing to the
microSD, `dmesg -w` over Wi-Fi), so part of the `mmc1` interrupts are theirs.
Raw logs stay private with the custodian.

**Both cases gave the same result in all 60 samples.**

| Word | Value | Blocking for deep idle (mainline clock names) |
| --- | --- | --- |
| `0x10001090` (mainline infra0) | `0x00001800` | ICUSB; I2C2, I2C3; PWM_HCLK, PWM1-4, PWM; UART1-3 |
| `0x10001094` (mainline infra1) | `0x00004014` | SPI (SPI0); CPUM; DISP_PWM (deep idle only); AP_DMA; L2C_SRAM |
| `0x100010b0` (mainline infra2) | `0x000000e7` | I2C2 IMM and ARB; SSUSB_REF, SSUSB_BUS, SSUSB_SYS; SPI1-5; ANC_MD32, ANC_MD32_32K; AES_TOP1; IRTX; VAD_WRAP |

SODI's list is the same without DISP_PWM. Power domains on: the display
(DIS) and AUDIO in every sample, with the panel DPMS off and `bl_power` 4;
ISP, VDEC, MFG, MJC and VENC off. `PCM_CON0` `0x4` and `PCM_FSM_STA`
`0x02848490`: the SPM idle, as before. SYS_CIRQ: no status, every line
masked, `CONTROL` `0x80000000` (not enabled); its sensitivity and polarity
words hold reset-like values, so D4 has to program them all.

CPU0's interrupts per 60 s, with CPU1-9 offline:

| Source | Wi-Fi idle | Music |
| --- | --- | --- |
| `arch_timer` | 8,683 (145/s) | 11,397 (190/s) |
| `asys-isr` (audio) | — | 2,831 (47/s) |
| I2C `1100e000` | 885 | 675 |
| `mmc1` (microSD, mostly the loggers) | 697 | 433 |
| IRQ work | 247 | 198 |
| I2C `11007000` | 84 | 70 |

No CONSYS or Wi-Fi interrupt line appeared in either window.

**Decision, by the record's table.**

- **The hypothesis holds.** The idle conditions fail on infra gates and,
  for deep idle, on the display domain and DISP_PWM. One CPU, MSDC and the
  multimedia domains pass.
- **Audio and Wi-Fi do not rule deep idle out.** Neither added a gate bit
  or a domain the vendor requires off. The AUDIO domain is not a deep-idle
  or SODI condition (only SODI3 adds the audio gates), and the joined Wi-Fi
  link held none of the listed gates. So the case "deep idle with them
  active is out" does not apply.
- **P3's work list**, sorted by who can clear each item:
  1. *Gates with no driver on the station* (R2 also found them on with no
     user): ICUSB, PWM_HCLK, PWM1-4, PWM, UART1-3, SPI0-5, IRTX, AES_TOP1,
     ANC_MD32 and its 32k clock, VAD_WRAP, CPUM, L2C_SRAM. Nothing on the
     station drives these blocks (the console is UART0, the backlight is
     DISP_PWM, the LEDs are on I2C), so they only stay on because
     `clk_ignore_unused` skips the late gating.
  2. *Gates with a driver that should release them:* I2C2 and I2C3 with
     their IMM and ARB clocks, and AP_DMA (`i2c-mt65xx` enables both per
     transfer; whether a bus on I2C2/3 is held open needs the clock
     summary from the run); SSUSB_REF, BUS and SYS (MTU3 with the cable out,
     which 0634 already powers down at runtime only with a wake path).
  3. *Display:* DISP_PWM and the DIS domain, both still on with the panel
     blanked. They block deep idle only; SODI allows them. That is the
     display session's.
- **Next step for group 1**, cheaper than a boot without
  `clk_ignore_unused` (which the display, Wi-Fi and GPU still need): a small
  `=m` module that, for exactly those named clocks and only if the clock
  framework shows no user, runs `clk_prepare_enable` then
  `clk_disable_unprepare`. That gates each one through the framework,
  writing only the infra clock-gate set and clear registers (`0x10001080`/
  `84`, `0x10001088`/`8c`, `0x100010a8`/`ac`) for those bits. Then D0
  again shows what is left, and measures the current change.

**Wake rate.** On CPU0 alone the local timer fires about 145 times a
second idle and 190 with music, and the audio interrupt 47 times a second
(about 21 ms periods). With `NO_HZ_IDLE` and HZ 250 that is high for an
idle system: timers from userspace (the desktop, PipeWire, the loggers)
keep waking CPU0. Each wake would end a deep-idle period, and each exit
costs about 1 ms, so at about 175 wakes a second idle the exits alone would
take some 15-20 % of the time. Average gaps of 5-7 ms still leave room
above the 2 ms threshold, and the 21 ms audio period is long enough. But
fewer wakeups is its own lever and worth chasing alongside P3, starting with
which processes arm the timers (`/proc/timer_list` or a short trace of
`hrtimer_start` on CPU0).

### G1: gating the unused infra clocks (prepared 2026-11-13)

The owner approved the module and its writes ("yes", relayed by the
custodian).
[`0768`](../../patches/proposals/0768-soc-mediatek-add-a-module-that-gates-the-MT6797-s-un.patch)
adds `mt6797-gate-unused` (`=m`, `CONFIG_MT6797_GATE_UNUSED` in
`gemini-a53-station-spm-sleep.fragment`). At load it gates D0's group 1, and
only a gate that is still on, that no enabled device tree node lists in its
`clocks`, and that the clock framework shows unprepared (no user):

- **One change from the proposal:** it writes the infra set registers
  directly instead of `clk_prepare_enable` then `clk_disable_unprepare`.
  Through the framework, the disable would also gate an unused parent:
  `spi_sel`, `anc_md32_sel` and possibly `mm_sel` (L2C_SRAM's parent, which
  the display may hold without a framework user) are TOPCKGEN muxes, and
  writing them is outside the approved list. The direct write touches only
  the approved registers and leaves the framework's counts as they were. A
  driver that later enables one of these clocks ungates it as usual.
- **Unloading restores the hardware.** `rmmod` writes the clear register
  for exactly the bits the module set.
- **Nothing on the station uses these.** UART1-3 are `disabled` in
  `mt6797.dtsi` and nothing enables them; the console is UART0 (`ttyS0` and
  `tty1` on the command line). The SPI controllers come from
  [0073](../../patches/v7.1.3/0073-arm64-dts-mediatek-mt6797-add-disabled-SPI-controllers.patch)
  and are disabled; no MT6797 PWM, IR or AES node exists; ICUSB is only on
  the disabled USB 1.1 node from 0070. The module checks all of this again
  at run time and logs every gate it leaves on and why.
- Compile-checked with `W=1` in a clean tree of `series-a53-station` plus
  0768, applied as `scripts/kernel` does; checkpatch quiet apart from the
  usual new-file `MAINTAINERS` note.

**Writes for owner approval (approved 2026-11-13):**

| # | Register | Write |
| --- | --- | --- |
| G1a | INFRACFG_AO `INFRA0` set `0x10001080` | `0x03af8100` at most: ICUSB 8, PWM_HCLK 15, PWM1-4 16-19, PWM 21, UART1-3 23-25 |
| G1b | `INFRA1` set `0x10001088` | `0x00400802` at most: SPI 1, CPUM 11, L2C_SRAM 22 |
| G1c | `INFRA2` set `0x100010a8` | `0x20fa3400` at most: SPI1 10, ANC_MD32 12, ANC_MD32_32K 13, AES_TOP1 17, SPI2-5 19-22, IRTX 23, VAD_WRAP 29 |
| G1d | the clear registers `0x10001084`, `0x1000108c`, `0x100010ac` | at `rmmod` only, the same bits the module set |

"At most": a bit is left out when its gate is already off or has a user.

**Request G1** (the running card root, boot `e7e3b009…`, station-work-116):

1. Baseline: the blanked current on the same software, as the custodian
   plans, just before the load.
2. `insmod mt6797-gate-unused.ko` (built from the commit recording this
   stage; only this module differs from the running `850e177e` package).
   Keep the `mt6797_gate_unused` lines from `dmesg`.
3. D0 `wifi-idle` again with the same script.
4. The blanked current again, same method and length as step 1.
5. Watch for anything that stops working: display, keyboard and LEDs,
   audio, Wi-Fi, microSD, the touchscreen, the fuel gauge.
6. `rmmod mt6797-gate-unused`, read the three status words: they must be
   back to step 2's "before" values.

- *Hypothesis:* the listed gates have no user, so gating them breaks
  nothing, removes them from D0's blocking list, and lowers the blanked
  current a little.
- *Unique observation:* D0's list with group 1 gone, and the current change
  from gating only driverless infra clocks.
- *Decision:*

| Result | Next |
| --- | --- |
| All listed gates gated, nothing breaks, D0 lists only groups 2 and 3 | Keep the module; group 2 (I2C2/3, AP_DMA, SSUSB) next with their drivers' owners |
| A gate is left on with a user named in the log | Find that user; if it is real, drop the gate from the list |
| Something breaks after the load | `rmmod` at once (it restores); find which gate it was by bisecting the list |
| The current does not move | Expected for gates alone: their value is unblocking deep idle, not the gating itself |

### G1 result (2026-11-13)

Run by the custodian on the card root (boot `e7e3b009…`, station-work-116),
module `5f274cd8…`. The load gated 22 gates and left `infra_icusb` on because
the enabled `/usb@11200000` node lists it.

| Word | Before | Gated |
| --- | --- | --- |
| `0x10001090` | `0x00001800` | `0x03af9800` |
| `0x10001094` | `0x00004014` | `0x00404816` |
| `0x100010b0` | `0x080000e7` | `0x28fa34e7` |

- **Current**, screen blanked, CPU0 alone, 600 samples at 1 Hz each:
  152.8 mA before, 149.9 mA gated, **2.9 mA less**.
- **Nothing broke:** the owner checked the display, keyboard and LEDs, touch
  and audio; the custodian checked Wi-Fi, a microSD read and the fuel gauge;
  taint 0.
- **D0 with the gates off:** deep idle is blocked by `0x094` bits 17 and 18
  (DISP_PWM, AP_DMA), `0x090` bits 8, 13 and 14 (ICUSB, I2C2, I2C3) and
  `0x0b0` bits 3, 4, 9, 18 and 24 (I2C2 IMM and ARB, SSUSB_REF, BUS and
  SYS); SODI by the same less DISP_PWM.
- **`rmmod` restored exactly the module's bits:** `0x090` and `0x0b0`
  matched their values before the load. In `0x094` the module's bits 1, 11
  and 22 were back, and bits 4 (MSDC1) and 14 (MFG_VCG) had been changed
  meanwhile by their own drivers at runtime.

**Decision, by the G1 table:** the first row. The module stays. The 2.9 mA
is about what gates alone were expected to give; their value is that
group 1 is gone from the blocking list.

**What is left, and who can clear it** (traced in `mt6797.dtsi` and the
drivers):

- **I2C2, I2C3 and the I2C2 IMM and ARB clocks** belong to the controllers
  `i2c8` (`0x11009000`) and `i2c9` (`0x1100d000`). Both are `disabled` and
  nothing in the series enables them, so these gates are driverless too,
  left on by the loader. They can join the module's list, which needs the
  owner's approval of four more bits (below).
- **AP_DMA** is the `bus` clock of every UART and I2C controller. The
  `8250_mtk` driver keeps UART0's clocks on while the port is in use and
  releases them in runtime suspend, but a console on the port keeps it in
  use. Both command lines carry `console=ttyS0`. On the card root, where
  nobody reads the internal UART, dropping it lets UART0 suspend and
  AP_DMA gate between I2C transfers. That is an Arch root setting, the
  Arch root session's to decide; the station keeps its serial console.
- **ICUSB and SSUSB_REF, BUS and SYS** are held by the enabled USB node,
  that is, by MTU3 with the cable out. The USB sessions own its runtime
  power-down.
- **DISP_PWM and the display domain** are the display session's. They block
  deep idle only; **SODI does not need them**.

So once the I2C bits are gated and the console is off the UART, SODI is
blocked only by the USB controller's clocks. Deep idle also needs the
display's two items.

**G2 writes for owner approval:** the same module with four more gates, all
under the same checks (still on, no enabled DT node, no clock framework
user):

| # | Register | Write |
| --- | --- | --- |
| G2a | `INFRA0` set `0x10001080` (and clear `0x10001084` at `rmmod`) | I2C2 bit 13, I2C3 bit 14 |
| G2b | `INFRA2` set `0x100010a8` (and clear `0x100010ac` at `rmmod`) | I2C2_IMM bit 3, I2C2_ARB bit 4 |

**The baseline is high.** 152.8 mA blanked with CPU0 alone on the card
root, against 77-80 mA on the station's RAM root, has nothing to do with
these gates. It is worth a separate look at what the card root's software
(the desktop, the joined Wi-Fi link, the loggers) keeps busy.

### G2: the disabled I2C controllers' gates (prepared 2026-11-13)

The owner approved G2 ("go", relayed by the custodian).
[`0770`](../../patches/proposals/0770-soc-mediatek-mt6797-gate-unused-gate-the-disabled-I2.patch)
adds I2C2 and I2C3 (`0x10001080` bits 13 and 14) and I2C2_IMM and I2C2_ARB
(`0x100010a8` bits 3 and 4) to `mt6797-gate-unused`, with the matching
clears at `rmmod`, under the same three checks.

**Nothing on the station uses them**, from the source: the clocks belong to
`i2c8` (`0x11009000`: I2C2, I2C2_ARB), `i2c9` (`0x1100d000`: I2C3,
I2C3_ARB) and `i2c2` (`0x11013000`: I2C2_IMM, I2C2_ARB), all three
`disabled` in `mt6797.dtsi`, and no patch in the series enables them. A
disabled node gets no platform device, so no driver can hold their clocks.
On the device the module checks again (enabled DT node, clock framework
user), and the custodian can confirm beforehand, read-only:
`ls /sys/bus/platform/devices | grep -E '11009000|1100d000|11013000'`
(expect nothing) and
`/sys/kernel/debug/clk/infra_i2c2{,_imm,_arb}/clk_prepare_count` and
`infra_i2c3` (expect 0).

Compile-checked with `W=1` on `series-a53-station` through 0769 plus 0770;
checkpatch quiet. The `.ko` comes from a Buildbox build of the commit that
records this, as every loaded module does; a VM build is for compile checks
only. G1's sequence repeats with it.

### G2 result (2026-11-13)

Run by the custodian on the same boot, `e7e3b009…`, with the module from
the Buildbox build of `6a90f367` (`c83879e6…`, vermagic matching). The
pre-checks found no platform device for `0x11009000`, `0x1100d000` or
`0x11013000`, and a prepare count of 0 on all four clocks. The load gated 26
gates, ICUSB left on as before:

| Word | Before | Gated |
| --- | --- | --- |
| `0x10001090` | `0x00001800` | `0x03aff800` (G1 plus bits 13 and 14) |
| `0x10001094` | `0x00004014` | `0x00404816` (as G1) |
| `0x100010b0` | `0x080000e7` | `0x28fa34ff` (G1 plus bits 3 and 4) |

- **Current**, blanked, CPU0 alone, 600 samples each, battery at 72 %:
  156.3 mA before, 153.5 mA gated, 2.7 mA less, the same as G1's 2.9 mA.
  The four I2C gates add nothing measurable; the baseline rose about
  3.5 mA since G1 with the lower charge.
- **D0 `wifi-idle`** (60 samples, none unblanked): deep idle is now blocked
  by `0x094` bits 17 and 18 (DISP_PWM, AP_DMA), `0x090` bit 8 (ICUSB) and
  `0x0b0` bits 9, 18 and 24 (SSUSB_REF, BUS, SYS); SODI by the same less
  DISP_PWM. `0x090` bit 11 (I2C0) blocked in 1 of 60 samples: a transfer on
  `i2c0` caught in flight, which its driver gates between transfers.
- The `0x090` bits 13 and 14 that left the list *are* the module's: I2C2 and
  I2C3 (the census's "INFRA1" is the vendor name for `0x090`).

**What blocks SODI now:** AP_DMA, which 0769 should free on the card root,
and the USB controller's ICUSB and SSUSB clocks. Deep idle also needs
DISP_PWM and the display domain. The module's own list is done.

**G2 finished and passed.** With the 26 gates off the owner found
"everything still works". `rmmod` returned 0, and `0x090` and `0x0b0` read
back exactly as before the load. In `0x094` the module's bits 1, 11 and 22
were ungated again; bit 4 (MSDC1) is driven at runtime by its own driver.
Taint 0, no new SD errors. The module is ready to load at boot on the card
root, which is the Arch root session's to set up.

### AP_DMA and the detached serial console (0769, 2026-11-13)

The Arch root session detached the `ttyS0` console on the card
(`console=N` through the port's sysfs `console` attribute, the getty masked),
but `11002000.serial` stayed runtime-active, so AP_DMA still could not gate.
Checked against v7.1:

- `uart_configure_port()` powers every port on and powers down only
  non-console ports, so a console port stays at `UART_PM_STATE_ON`. On
  `8250_mtk` that state holds a runtime PM reference
  (`mtk8250_do_pm`), and runtime suspend is what releases the UART and AP_DMA
  clocks.
- `uart_console()` only compares the console's index with the line, so it
  stays true after `unregister_console()`.
- `port->console` is set once in `serial_core_add_one_port()`, and
  `tty_port_shutdown()` returns early on it, so a close never powers the
  port off either.
- In addition, `uart_resume_port()` powers a console port back on after
  every suspend, which would undo any detach at the first resume.

[`0769`](../../patches/proposals/0769-serial-core-power-a-port-down-when-its-console-is-de.patch)
(built in, `serial_core.c`, which no other patch in the series touches):
on detach it clears `port->console` and powers the port off unless it is
open; on re-attach it powers it on and sets the flag before registering;
a hangup and a resume treat the port as a console only while its console is
registered. Compiled with `W=1` on pristine 7.1.3, checkpatch quiet; it
applies with `--unidiff-zero`. It is meant to be upstreamable. It goes into
the next batched image. The station keeps `console=ttyS0` and its serial
boot log; only the card's detach unit uses this.

**Check on that image** (card root):

1. After boot, with the detach unit run: `11002000.serial`
   `power/runtime_status` reads `suspended` and `runtime_usage` reads 0.
2. D0 `wifi-idle`: INFRA1 (`0x094`) bit 18, AP_DMA, gated in most samples
   (I2C transfers still ungate it briefly).
3. One `mem` suspend and resume: still `suspended` afterwards.
4. `echo 1 > /sys/class/tty/ttyS0/console`: the console prints again and the
   port is active; `echo 0` suspends it again.

### 0769 on the device, and 0777 (2026-11-13)

On station-work-120 (`64c1f85e`, with 0769), boot `3f3e037b…`, card root
(custodian's report): after the card's detach unit ran (`console=N`, nobody
holding `/dev/ttyS0`, `/proc/consoles` listing only `tty1` and `ramoops`),
`11002000.serial` was still runtime-active with a usage count of 1, and
AP_DMA (`0x094` bit 18) stayed on. Attaching the console again raised the
count to 2 and detaching brought it back to 1.

**Why** (from the source, fits all three numbers): at boot the port holds two
references, one from `serial8250_console_setup()` and one from
`uart_configure_port()`'s power-on. Something opened and closed `ttyS0`
while it was still the console. That close skipped the shutdown
(`tty_port_shutdown()` returns early for a console port), so the port
stayed *initialized* with nobody holding it. 0769 powers a port off on
detach only if it is not initialized, so it skipped the power-off. The
console's own reference is the one that came and went with each toggle.

[`0777`](../../patches/proposals/0777-serial-core-shut-down-a-closed-port-when-its-console.patch)
(built in, on top of 0769): on detach, a port that no one has open but
that is still initialized gets the shutdown the earlier close skipped,
which ends in the power-off; a never-initialized port is powered off as
before. Compile-checked with `W=1` on 7.1.3 plus 0769, checkpatch quiet,
applies with `--unidiff-zero`. Expected on the image with 0777: usage 0,
runtime suspended, AP_DMA gated between I2C transfers.

**G2 on that image.** `mt6797-gate-unused` was not in the station image,
because `compose-station.py` packs a fixed module list; the custodian
loaded the G2 module by hand (same 26 gates) and is adding it to the list.
`0x0b0` read `0xe7` before gating, where it read `0x080000e7` on the earlier
boot: bit 27 has no mainline clock, and the vendor's SODI3 mask names bits 26
and 27 as the audio 26 MHz gates. It is not a deep-idle or SODI condition.

### Screen-on SODI and the scanout FIFO (note, 2026-11-14)

The custodian found in the vendor display driver (`disp_lowpower.c`,
`_acquire_wrot_resource`; recorded in
[display-panel §3.6](../../docs/hardware/display-panel.md)) that in video
mode the vendor lends MDP WROT's SRAM to RDMA0 while the display idles
(`DISP_REG_RDMA_SRAM_SEL`, RDMA `0x0b0`, then the RDMA FIFO settings again),
"to increase the SODI ratio". A deeper scanout FIFO leaves longer gaps
without DRAM traffic, which is when SODI can gate DRAM.

That matters only for **screen-on** SODI, where the panel keeps scanning out.
The target here is the dark screen, where DPMS is off and RDMA reads nothing,
so it changes nothing in the current plan or its blocking list. If
screen-on SODI is ever pursued, mainline `mediatek-drm` would need the same
SRAM borrowing, and the display session would own it.

### What it should save

| State | Today | Expected |
| --- | --- | --- |
| Awake, blanked, CPU0 alone | 77-80 mA | unchanged until P3 |
| After P3 alone | unmeasured | some of the gap to `mem`: unused PLLs and gates off |
| Deep idle when nothing is active | — | between 42 mA (`mem`, which also turns 26 MHz and infra off) and the post-P3 figure; inferred about 50-65 mA |
| With music or a joined Wi-Fi link | — | weighted by residency: every audio period or Wi-Fi beacon ends one idle period, and each exit costs about 1 ms awake |
| s2idle / `mem` (for reference) | 73 / 42 mA | unchanged |

These are inferences from the program's behaviour and this record's
measurements, not vendor figures; D5 measures them. If P3 alone closes most of
the gap, deep idle may add little, and D1's counters will show whether the
conditions are met often enough to matter.

### Main risks

- **DRAM in self-refresh while a bus master needs it.** The program brings
  DRAM back on a master's request (APSRC) only for masters whose requests
  the masks honour. A device the masks do not cover (audio DMA, MSDC, USB)
  writing DRAM during the sleep would corrupt memory or hang the bus. The
  vendor's conditions keep those blocks gated; D1 checks them every entry,
  and D3/D4 end with a hash check.
- **A missed wake.** W3 showed what happens when an interrupt reaches CPU0
  but not the program. In idle every interrupt must reach the program,
  which depends on SYS_CIRQ covering every enabled edge SPI and on level
  SPIs reaching it as events. D4 tests the three that matter.
- **A hang with no recovery but force-off**, as for every SPM stage.
- **The dependency on P3 and the display blank**, owned by other sessions
  and not yet started.
- **Entry cost.** Reloading 2,000 words and re-initialising the PCM at
  every entry may cost hundreds of microseconds; if D5 shows it matters, the
  program stays resident between entries.
- **Rights:** the same as Route A. The program is the owner's own vendor
  file, loaded at runtime and never shipped.

## The SPM programs decoded (2026-11-08)

The owner asked for the programs themselves to be understood before deciding
whether the project could write its own. This pass decoded all nine
`pcm_*.bin` files statically in the RE VM; no device was touched. The
instruction set and each program's behaviour, with observed and inferred
kept apart, are in [MT6797 SPM programs](../../docs/hardware/mt6797-spm-programs.md).
The decoder and the listings stay private.

- **Instruction set:** every one of the 12,542 instructions decodes into
  thirteen classes. These are register and immediate ALU operations, move and
  load (absolute and register-indirect), three store forms, jumps and calls
  (plain and conditional) with an 11-bit target and a delay slot, and return.
  Still unsettled: the exact predicates of three compare opcodes, one
  opcode used three times in the VCORE-DVFS programs, and the conditional
  wait modes of `r14`.
- **How the sleep works:** the programs are event-driven resource arbiters.
  After a fixed entry (bus-master pause, CPU and cluster power-down, external
  buck off over I2C6, ARM PLLs off), the SPM hardware raises events as the
  merged resource requests drop. The PCM handles six wake/sleep pairs (26
  MHz, infra, APSRC, VRF18, DDREN, NFC clock buffer). Suspend's 26 MHz sleep
  handler also powers infra down and releases the 26 MHz clock buffer, which
  is what lets VCORE fall to its PMIC sleep voltage. Deep idle keeps 26 MHz
  and infra. SODI only arbitrates DRAM.
- **S1's "CPU stays powered" mode:** `pcm_suspend.bin` tests flag bit 0 at
  four points and skips the CPU, cluster and MCUSYS power steps and the
  `CPU_EXT_BUCK_ISO` writes. The path exists in the shipped code. The decode
  also found writes that S1's list lacked: the I2C6 soft reset, the external
  buck write when flag bit 9 is clear, the `PASR_DPD_3` thermal-period
  compare, the GCE, AUXADC and I2C_APPM gates, and `ddrphycfg_sel`. They
  went to the S1 session, which took them in `8958275a`.
- **A project-written program:** a reduced one (CPU, 26 MHz, infra and the
  PMIC sleep voltage, without DRAM self-refresh) is feasible as original
  work. A full replacement would have to copy the vendor's DRAM
  self-refresh and PHY sequence and its timings as opaque constants, so it
  would not be clean-room. The S1 measurement should decide whether the
  reduced program is worth writing.

## Observations

### Attempt 1 (2026-11-07)

Run by the device custodian. Boot `b15c1ad0-1fc1-4be6-9519-a63a1e8ff60c`,
release `7.1.3-gemini-a53-station`, boot2 `be1dbf5a…` (station-work-87, by GPT
name), `clk-mt6797-mcusys.ko` `8163e541…`, `cpufreq-dt.ko` `2c451b82…`,
`cpu-mhz` `4168cfe5…`. A72 module not loaded. Battery 77 % to 74 %,
27.3 °C to 25.4 °C. The raw logs stay private with the custodian.

**c0** (cable in) passed: `online` `0-7`, taint 0, both drivers loaded,
policy0 CPU0-3 and policy4 CPU4-7 on schedutil, `faulted=0`, sync DCM
`0x00070707`. SPM reads (offsets from `0x10006000`):

| Offset | Value | Offset | Value |
| --- | --- | --- | --- |
| `018` `PCM_CON0` | `00000004` | `180` `PWR_STATUS` | `2B00005E` |
| `01c` `PCM_CON1` | `00006C00` | `184` `PWR_STATUS_2ND` | `2B00004E` |
| `020` `PCM_IM_PTR` | `00000000` | `188` `CPU_PWR_STATUS` | `003DA008` |
| `024` `PCM_IM_LEN` | `00000FFF` | `18c` `CPU_PWR_STATUS_2ND` | `003D82FF` |
| `028` `PCM_REG_DATA_INI` | `00000000` | `1e4` `CPU_RET_STATUS` | `000000F6` |
| `02c` `PCM_PWR_IO_EN` | `00000000` | `210`, `214` `MP0/MP1_CPUSYS_PWR_CON` | `0009004D` each |
| `174` `CPU_IDLE_STA` | `0003EC00` | `220`-`23c` A53 core `PWR_CON` | `0001004D` each |
| `17c` `PCM_FSM_STA` | `02848490` | `540`-`55c` `WFI_EN` | `0` each |
| `600` `SPM_SW_FLAG` | `0` | `608`-`614` `SPM_SW_RSV_0-3` | `0` each |
| `618`, `61c` `SPM_SW_RSV_4-5` | `FFFFFFFF` each | MCUCFG `0x10220744` | `00070707` |

**The procedure fault.** `backlight-policy` was killed before c1, but busybox
init restarted it at once (`backlight-policy: start: lid open` at 926.11 s).
The new copy blanked the console at 1043.22 s, inside W2, and took CPU1-3
down (`psci: CPU1/2/3 killed`, 1043.24-1043.29 s). It unblanked and brought
them back at 1945.45 s, after the replug. It probably lit the backlight when
it started, before W1; the logs cannot confirm that.

**Windows** (battery, charger offline in every sample):

| Window | Online | Samples | Mean | Range | Clocks (policy0/policy4, MHz) |
| --- | --- | --- | --- | --- | --- |
| W1 | `0-7` | 60 | −158.8 mA at 4.060 V | −140.0 to −187.3 | 624/325 in 30 samples, 221/832 in 26 |
| W2, first part | `0-3` | 4 | −128.3 mA | — | — |
| W2, rest | `0` (CPU1-3 taken by the policy) | 56 | −133.8 mA at 4.066 V | −114.2 to −144.4 | — |

`arch_timer` rose from 20509 to 40490 over W1.

**c2:** CPU4-7 down, rc 0, `psci: CPU4-7 killed` at 1029.30-1029.44 s. The
clock driver before: `ckdiv` `0x2900`, PLL0 715 MHz, PLL1 325 MHz (CON1
`0x410c8000`), changes 1877/1940, sync DCM `0x00070707`, `faulted=0`.

**c3:** CPU4-7 back, rc 0, at 1107.91-1108.10 s. `online` read `0,4-7`, so the
stage stopped by its rule. The clock driver after: `ckdiv` `0x2160`, PLL0
221 MHz, PLL1 832 MHz (CON1 `0x41100000`), changes 2453/1998, sync DCM
`0x00070707`, `faulted=0`. The `cpu-mhz` and hash check, W3 and W4 did not
run. At the end: taint 0, no new fault line, unblank rc 0.

### Attempt 2 (2026-11-08)

Run by the device custodian with the [attempt 2 changes](#attempt-2-changes),
owner-approved. Boot `52f4c5fd-c191-4955-9277-42bc774ea4c1`, release
`7.1.3-gemini-a53-station`, boot2 `6c0fd742…` (station-work-91, by GPT name),
station RAM root. `clk-mt6797-mcusys.ko` `501a3876…` and `cpufreq-dt.ko`
`f558be9b…` from that image's own package, `cpu-mhz` `4168cfe5…`. A72 module
not loaded. Battery 98 % to 87 %; SoC 35.1 °C at the end. Raw logs stay private
with the custodian.

**c0** (cable in): `mac` and `mt6797-consys` unloaded at once;
`mt6797-wlan-core` refused once with `EAGAIN` and unloaded on a retry (CONN
off, VCN28/VCN18/VCN33 off). Console blanking off, `backlight-policy` stopped
(state `T`), both drivers loaded, `faulted=0`, policy0 CPU0-3 and policy4
CPU4-7 on schedutil, held at 221 and 325 MHz. Taint 0.

**Windows** (battery, charger offline in every sample, `fb0` blanked, online
mask as expected in every sample, clocks 221/325 MHz in every sample):

| Window | Online | Samples | Mean | Range |
| --- | --- | --- | --- | --- |
| W1 | `0-7` | 60 | −324.4 mA at 4.189 V | −313.1 to −337.9 |
| W2 | `0-3` | 60 | −298.8 mA at 4.191 V | −281.9 to −360.8 |
| W3 | `0` | 60 | −289.9 mA at 4.188 V | −282.6 to −346.6 |
| W4 | `0-7` | 60 | −324.3 mA at 4.171 V | −310.6 to −396.4 |

**c2-c5:** every `online` write rc 0. After c3 and c5 PLL1, `ckdiv` and sync
DCM matched the c2 reads exactly and the driver stayed `faulted=0`. `cpu-mhz`
read CPU4 at 321 MHz (325 requested) after c3 and c5, and CPU1 at 218 MHz
(221 requested), with the reference hash each time. `stop=0`, no new fault
line, taint 0.

**SPM at each window's end:**

| Word | W1 (`0-7`) | W2 (`0-3`) | W3 (`0`) | W4 (`0-7`) |
| --- | --- | --- | --- | --- |
| `0x174` `CPU_IDLE_STA` | `0001FC00` | `0023DC00` | `0023F800` | `0002FC00` |
| `0x188` `CPU_PWR_STATUS` | `003D9008` | `00399008` | `00398008` | `003D8408` |
| `0x1e4` `CPU_RET_STATUS` | `000000FC` | `0000000A` | `00000000` | `000000DE` |
| `0x214` `MP1_CPUSYS_PWR_CON` | `0009004D` | `00091132` | `00091132` | `0009004D` |

`MP0_CPUSYS_PWR_CON` stayed `0009004D` and sync DCM `00070707` throughout.

**The baseline is high.** W1 is about twice attempt 1's 159 mA and three
times R1's 111 mA. Afterwards, with the cable in (the charge guard holding at
98 %, so the battery still reported current), `fb0` blank set the backlight's
`bl_power` to 4, so the blank did reach the backlight. CONN and its supplies
were off. The cause of the extra draw is not found.

## Analysis

**Attempt 1.**

- **The L cluster went down and came back with the clock driver bound,
  without a fault.** All four CPUs returned, sync DCM did not change, the
  driver stayed unfaulted and kept scaling PLL1 afterwards (its change count
  rose from 1940 to 1998). The PLL and divider differed from the c2 reads only
  because schedutil was still changing them. That points away from the
  firmware touching the L cluster clock on power-up. It is not proof: the
  measured clock on CPU4 after c3 is missing, and a firmware change that the
  driver later overwrote would not show.
- **No current figure can be used.** W1 (159 mA) is well above R1's 111 mA,
  which fits a lit backlight, and the clocks were not at the idle points. W2
  mixes a probably unlit backlight with CPU1-3 also offline. Neither D nor L
  can be taken from this run.
- **No SPM program appears to be running on mainline** (inferred from the c0
  reads). `PCM_CON0` holds only the PCM clock enable (vendor bit 2), without
  the kick bits or the run-state `EN_IM_SLEEP_DVS`. `PCM_IM_PTR`,
  `PCM_REG_DATA_INI`, `PCM_PWR_IO_EN`, `SPM_SW_FLAG` and every `WFI_EN` word
  are 0. *Confirmed 2026-11-08:* the low 23 bits of `PCM_FSM_STA`
  (`0x48490`) are the vendor's PCM reset value.
- **`CPU_IDLE_STA` sees WFI.** Bits 10-17 read `0xFB`: seven A53s in
  `STANDBYWFI`, one not, which fits one CPU running the read.

**Attempt 2.**

- **The clock question is settled for this path.** Two L-cluster down/up
  cycles, one with CPU1-3 too, left PLL1, the divider and sync DCM exactly as
  before, the driver unfaulted and the measured clocks within 2 %. The
  firmware's `CPU_ON` does not touch the A53 cluster clocks on this image.
- **Differences, at the idle points:** D = W1 − W3 = 34.5 mA; L = W1 − W2 =
  25.6 mA, 74 % of D; CPU1-3 add 8.9 mA. W1 and W4 agree to 0.1 mA, so the
  windows did not drift. By the decision table that is the "L cluster carries
  the saving" row.
- **The absolute level is unexplained.** The differences are measured inside
  one run at one battery voltage, but the 324 mA floor is far above every
  earlier blanked figure. A battery just off a charge stop at 4.19 V, or some
  load this image leaves on, may inflate both the floor and the differences.
  Until a run reproduces about 111 mA with the same steps, D and L are
  provisional.

## Conclusion

On the installed firmware there is no per-core idle state below WFI: the
power-down states wait for an SPM program, and no MT6797 per-core program
exists. The working levers on this unit are:

- **hotplug** on a dark screen, for all three clusters (P2f and H1);
- **`mem` suspend through the vendor suspend program** (Route A, S1): 42 mA
  against 73 mA for s2idle, with the boot watchdog handled by 0678 and
  suspend on lid close in `backlight-policy`. The PMIC sleep modes (0679)
  showed no effect beyond drift and stay off.

The supposed 200 mA awake regression was the display relighting itself; a
blanked station with CPU0 alone idles at about 77-80 mA. The three
resume defects that blocked `mem` suspend outside tests (USB, `soc-thermal`,
the display's blank) are fixed by other sessions, and masking the GIC
(0688, default on in 0689) lets a charger plug-in wake it. An overnight soak
(K1) comes before it loads at boot and the card switches to it; S2 (CPU0
powered down in suspend) follows, per the owner's order.

## Follow-up

- The three blockers for `mem` suspend outside tests: USB after a resume
  (suspend session), `soc-thermal` after a resume (suspend session or the
  thermal owner), the display's blank across a resume and its spontaneous
  unblanks (display session).
- Then S2, as recommended for owner decision 5.
- The SPM route: an owner decision. Route A's S0 (reads only) can run any
  time; S1 needs approval of its write list and a module, which is a separate
  owner decision. P3 is no longer a prerequisite for suspend, only for the
  idle states (S3).
- The [power-management record](../2026-11-06-gemini-power-management/README.md#the-firmware-side)
  says the secure firmware writes no SPM power control; that holds for
  suspend only (`CPU_ON` and `CPU_OFF` do write them). Its owner session may
  want to note it.
- If C1 follows, it reuses P2f's mechanism and needs no new write.
- A GPT broadcast timer node and the cpuidle-psci skip for CPU8-9 are needed
  only once a real state exists; neither is worth a patch before then.
