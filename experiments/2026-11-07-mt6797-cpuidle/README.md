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
  the vendor's kernel,
  the vendor's `spm_v2` code (`mt_spm_mcdi.c`,
  `mt_spm_internal.c`, `mt_idle.c`, `mt_idle_mt6797.c`),
  `mt_spm_reg_mt6797.h`,
  `mt_cpuidle.c` and
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
| D3 | One deep-idle period on demand from debugfs, PCM-timer wake, CPU kept powered, GIC masked, no cpuidle yet; then a DRAM hash check | The S1 list adapted (below) | Running; passed on image 134 |
| D4 | D3 with a device interrupt as the wake: a key and an inbound Wi-Fi packet, with the vendor's SODI wake set and SYS_CIRQ (audio waits for AFE SRAM playback) | D3 plus CIRQ | Running; prepared |
| D5 | The cpuidle state enabled, dark screen: idle, Wi-Fi joined, music; current and residency | D4 | New (`CONFIG_CPU_IDLE`); periods hang under the two-state cpuidle driver, not the OPP (D5a-D5l); D5m hung with no driver, also with no resource events; D5o: the module decides, not the boot; D5p: no PCM-watchdog wake; the fetch and the clock select are cleared (D5q, D5r); the CPU8 observer hung with no line kept (D5s); D5t passed every window, and the SYS_CIRQ acknowledgement ended the early aborts; D5t run 2 hung in period 2 and lost its evidence to Gemian; run 3 hung in period 29 and also landed in Gemian; run 4's RAM console, read in Gemian, has no observer line; D5u: CPU8 never ticks in a period, so the observer is retired; D5v hung in window C's first period with CPU0 alone and no A72 up, and lost the marker to Gemian; D5w hung in period 11 without the side key held, and its gate read shows the vendor's infra clock condition met; D5w run 2 hung in period 1 and also landed in Gemian; run 3 hung in period 28; D5x showed the held side key selects boot2 after a watchdog reset, and gave a no-SODI latch reference equal to D5l's hang values; D5y hung in period 14 with the vendor's display terms met, so the open display gates are not the cause; D5z hung in period 7 with MP2 left alone; run 2 hung in period 3 and showed the SMI async DCM already on, so the vendor's write is a no-op; both landed in Gemian without latches; D5aa was skipped, since nothing can wake CPU0 in the window; D5ab hung in period 2 with ACINACTM set only around WFI, so the entry now matches the vendor's on every listed difference; D5ac's stage lines place the hang inside the period, after the kick; D5ad variant 1 hung in period 2 without the clock cut; an independent review found the vendor's SODI flags keep 26 MHz and infra forced awake (bit 15) and power CPU0 down; D5ae passed 60 of 60 periods with bit 15 on the timer-only setup, but D5af passed 60 of 60 without it, so today's module no longer hangs there; D5ah hung in period 13 with bit 15 on the two-state setup, stopping at the same `kick` crumb, so bit 15 is not the cause; `d5m.sh` unchanged on today's module passed run 1 and hung in run 2, so the no-driver, timer-only hang survives with the module's defaults; D5aj, `d5m.sh`'s timing with D5af's options, hung at the first kick, so the options and the self-refresh path are not needed; D5ak, with a 5 s settle after offlining, returned period 1 and hung in period 2, so the start is not the cause; D5al hung at period 1's kick with 2000 ms periods, so the length is not the cause either; D5am was withdrawn, since the logged infra gates of `d5m.sh` and D5af match and USB was already suspended; D5ao: on one boot `d4.sh` passed 80 periods and `d5m.sh` then hung at its first kick, so the script decides, not the boot; D5ap, `d5m.sh` with CPU0 pinned at its top OPP, passed 15 of 15 periods, so CPU0's operating point at the kick decides the no-driver hang; D5aq, `d4.sh` pinned at 221 MHz, hung at its first kick, so the operating point decides from both sides; D5as, `d5m.sh` at 221 MHz without the master pause (variant 2), passed 15 of 15, so the pause at a low OPP is the hazard; D5ar hung at 1118 MHz in period 2, so the edge is above the divider boundary; 0847 adds variants 6 (longer pause wait) and 7 (cluster ports not paused); D5au, the two-state setup pinned at 1547 MHz, passed 227 periods, so the original hang is the same low-OPP hazard; D5at variants 7 (cluster ports unpaused) and 6 (pause wait ten times longer) both hung at 221 MHz at the first kick; 0849 adds the pause-mask variants 8-10 for D5av; variant 8 (deep idle's masks) hung at the first kick; variant 10 (no master selected, request kept) passed 15 of 15 and variant 9 (all selected) hung, so a set bit pauses a master and one master in SODI's selection breaks at a low OPP; D5aw bisects it with 0850: groups H and I alone passed, group C (`0x0ff00000`) alone hung, and C bisects to bit 25 alone, and SODI's masks minus bit 25 passed 15 of 15 at 221 MHz; D5ay found no safe floor (1274 MHz hung at kick 1, 1339 MHz at kick 5); the owner stopped the legacy entry there for the PSCI power-down entry (D6a, 0851-0852) |
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

**A measurement caveat** (from the camera session, 2026-11-14): in 7.1,
reading `clk_summary` runtime-resumes every clock provider that has runtime
PM. The camera receiver provides the MCLK clocks, so each read briefly powers
the ISP domain and enables `cam_camsys` and `cam_seninf`. The script's
`clk_summary` snapshots therefore show those blocks on; per-clock
`clk_enable_count` files do not perturb anything. The 1 Hz samples are
register reads and are unaffected, but the first ones came one second after
the start snapshot. Since 2026-11-14 the script waits 10 s after that
snapshot before the window.

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

**0777 on the device** (station-work-124, built from `fd9ca150` with 0769
and 0777, boot `9c688df7…`, card root, custodian's report): after the
detach, `11002000.serial` reads `suspended` with `runtime_usage` 0, and
`/proc/consoles` lists only `tty1` and `ramoops`. The UART part works.
AP_DMA (`0x094` bit 18) still read on in 200 of 200 samples at 50 ms, so
something else holds it. `i2c-mt65xx` enables its clocks, AP_DMA included,
only for each transfer, and a disable back to a count of zero would gate the
hardware, so another consumer must be holding an enable. The next read, on
any later boot: the `infra_ap_dma` line and its consumers in
`/sys/kernel/debug/clk/clk_summary`, and its `clk_enable_count`.

**Who holds AP_DMA** (custodian's read, same boot, Wi-Fi joined):
`infra_ap_dma` had an enable count of 2 and a prepare count of 9. Its
consumers are CONSYS (`ap-dma`), seven I2C controllers (`dma`) and the UART
(`bus`, now suspended). From the source, the two lasting enables are both
the Wi-Fi stack's:

- the CONSYS owner (0393) enables `ap-dma` when it sets up the WMT channel
  (`mt6797_wmt_query_setup`) and releases it only when CONSYS unloads;
- the WLAN driver (0392) takes the same clock for its HIF data path
  (`hif->dma_clk`) and releases it only at teardown.

The I2C controllers enable it per transfer only. So AP_DMA stays on for as
long as Wi-Fi is up, which on the card root is always. The vendor allows
Wi-Fi during deep idle, so its stack does not hold the clock that way. The
change belongs to the Wi-Fi and CONSYS owner: enable `ap-dma` only around a
WMT exchange and while a HIF DMA transfer is in flight, and release it in
between. Until then, SODI and deep idle cannot be entered with Wi-Fi up.

**AP_DMA freed (2026-11-14).** Wi-Fi's fix, 0782 (the WLAN HIF enables
the clock only around each DMA transfer) and 0783 (CONSYS enables it only to
check that the BTIF channels are idle), ran on station-work-125 (boot2
`8d413f38…`, from `f6a93500`), boot `0da78fe9…`, card root, Wi-Fi joined at
about −67 dBm, `mt6797-gate-unused` loaded. Custodian's report:

- `infra_ap_dma` enable count 0 in every read, idle and after a download;
  `0x094` bit 18 gated in 199 of 200 samples at 50 ms (0 of 200 before);
- D0 `wifi-idle`, 60 samples, none unblanked: AP_DMA is in neither list.
  **SODI is now blocked only by ICUSB (`0x090` bit 8) and SSUSB_REF, BUS
  and SYS (`0x0b0` bits 9, 18, 24)**, every sample. Deep idle adds DISP_PWM
  (`0x094` bit 17) and the display domain;
- three 64 MiB downloads at about 39.5 Mbit/s against about 40 before, no new
  Wi-Fi error; Bluetooth probed and `hci0` set up, powered off as before.

So the only blocker left for SODI with Wi-Fi joined is the USB controller
holding its clocks with the cable out. That is the USB sessions' runtime
power-down; deep idle also waits on the display's two items.

**Deep idle versus SODI, and the display (2026-11-14).** The display
session fixed DISP_PWM (0788, built in, next image) and assessed powering the
MM domain down on a blank. That is a larger step: the station DT names no
power domain on the display nodes, SMI larb0 has no driver and would lose
its loader bypass, the PWM duty latches through display mutex membership that
DRM does not restore, and the camera receiver holds MM clocks. Its question,
whether deep idle saves measurably more than SODI, has no evidence behind
either answer. The vendor material holds no current figures. In the
programs, deep idle adds MAINPLL off, the SRCLKEN_IN2 sleep phase, VCORE
low-IQ and SYSRAM sleep to SODI's DRAM arbitration. Both power the CPU side
down and bring VCORE to 0.775 V. **Decision:** SODI first (D3-D5), measured
against the blanked awake current; the MM-domain work is planned only if
deep idle's extra plus the domain's own leakage then look worth more than a
few mA.

**ICUSB (0789, 2026-11-14).** usb-c's idle read (`0c57166a`) found
`infra_icusb` with no user in the clock framework and no driver bound to
`/usb@11200000` (the MUSB driver is neither loaded nor autoloaded): a loader
leftover that `mt6797-gate-unused` skipped only because an enabled node lists
it.
[`0789`](../../patches/proposals/0789-soc-mediatek-mt6797-gate-unused-gate-a-clock-whose-n.patch)
counts a listing node as a user only when a driver is bound to its platform
device; a node that is not a platform device still counts as one, and a
driver that binds later enables the clock through the framework as usual. It
writes the same ICUSB bit that G1 approved (`0x10001080` bit 8, clear at
`rmmod`), so no new write. Compile-checked with `W=1` on the full station
series; checkpatch quiet. SSUSB_REF, BUS and SYS stay with usb-c: MTU3
(`11271000.usb`) holds them, with runtime PM forbidden and the gadget pulled
up, until its runtime power-off is written.

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

### State table (2026-11-16)

Where each way of saving CPU and SoC power stands on this unit:

| State | Mechanism | Status | Measured | Blocked by |
| --- | --- | --- | --- | --- |
| WFI with A53 retention | Hardware, every idle A53 (firmware enables SPARK on `CPU_ON`) | Works | — | — |
| Per-core power-down in idle | Would need an MT6797 MCDI program | Not possible | — | No such program; firmware waits in EL3 |
| Hotplug on a dark screen | `backlight-policy` (station), CPU1-9 | Works (station; the card root has no such policy) | about 15 mA for CPU1-7 (R1b) | — |
| s2idle | Kernel | Works | 73 mA | — |
| `mem` suspend (Route A, S1) | `mt6797-spm-sleep` + vendor `pcm_suspend.bin`, CPU kept powered | Works on the station; lid close, charger wake (0688/0689) | 42 mA | Soak K1; loading at boot |
| Unused infra gates | `mt6797-gate-unused` (0768, 0770, 0789) | Works, 26 gates (+ ICUSB with 0789) | about 3 mA | — |
| SODI (dark screen, awake) | Vendor `pcm_sodi.bin`, CPU kept powered, from CPU0's idle | Periods on demand return, CG and PDN (D3); a key and an inbound packet wake them (D4, D4c); cpuidle (D5) reset the device in run 1; withheld | — | — |
| Deep idle | Vendor `pcm_deepidle.bin` | Deferred | — | SODI first; then DISP_PWM (0788) and the display domain |
| Lazy RCU | Config | Folded into the station fragments | tick restarts −7 % | — |
| HZ 100 | Config | T2 pending | — | — |

### D3: one SODI period on demand (design, 2026-11-16)

The first SODI test needs no cpuidle driver. A debugfs file in
`mt6797-spm-sleep` runs one SODI period on CPU0 with interrupts off, ended by
the PCM timer, while the system is otherwise awake: CPU1-9 offline, display
blanked, radios unloaded, the USB gadget unbound with the cable out (the one
remaining blocker removed by hand, as for S1), `mt6797-gate-unused` loaded.
It reuses S1's loader, PCM reset, kick, wake read-back and restore, and
0688's GIC mask. Values derived from the vendor's MT6797 `sodi_ctrl`
(`mt_spm_sodi.c`) through the MT6797 `__spm_set_power_control`
(`mt_spm_internal.c`); the same derivation reproduces S1's suspend values
exactly (`SPM_SRC_MASK` `0x10aa007e`), which checks it.

| Item | S1 (suspend) | D3 (SODI) |
| --- | --- | --- |
| Program | `pcm_suspend.bin` | `pcm_sodi.bin`, 1,583 words, SHA-256 `dda8cca1…122ae4` |
| `SPM_AP_STANDBY_CON` | `0x04080011` \| bit 23 as read | the same: WFI AND, MD1 and CONN requests honoured, SCP masked (no SCP firmware), MP3 idle masked |
| `SPM_SRC_REQ` | `0x00000040` | `0x00000000` (no DVFS force-down) |
| `SPM_SRC_MASK` | `0x10aa007e` | `0x10aa007e` |
| `SPM_SRC2_MASK` | `0x00f1001f` | `0x08ff009f`: display, display OD, MFG, GCE and CONN DDR requests honoured |
| `WFI_EN` | MP0, MP1, MP2 | MP0 and MP1 only (the vendor leaves MP2 at 0) |
| Wake mask | `0xffffffbe` (timer, EINT) | the same for D3; the vendor's full SODI set (`0x0f57c5f5`) comes with D4 and SYS_CIRQ |
| Flags | `0x000d02b1` | the same with bit 12 clear (PDN mode): CPU kept powered, no VPROC/VSRAM DVS, VCORE DFS off, SYSRAM sleep off (the vendor's only SODI flag), segment bit, thermal check skipped |
| PMIC wrapper | suspend phase | deep-idle phase (§6 of the SPM sleep page): slot 7 and 8 `TOP_CON` with `SRCLKEN_IN2` normal and sleep, from the live `TOP_CON` |
| PMIC power-good force | P2 | the same (`__spm_pmic_pg_force_on`) |
| PCM timer | 10-300 s | 1 s, then 10 s |

**The open points, answered by the PCM decode session** (2026-11-16, from
its private listing):

1. `SPM_SW_RSV_5` bit 23 only picks which wrapper slot the PDN-mode APSRC
   wake handler restores VCORE with. With DIS_VCORE_DVS (flag 3) set, SODI
   issues **no wrapper command at all**, so the register and the wrapper
   table do not matter. No DRAM-frequency or PLL step depends on it.
2. **Flag 7 means something else in `pcm_sodi`** (it drives an unidentified
   register pair at `0x10229004`/`0x10229008` in the NFC clock-buffer
   handlers), so D3 clears it. Bits 4, 5, 16, 18 and 19 are not tested by
   `pcm_sodi`.
3. Entry mode is CG (DRAM self-refresh only) when flag 12 or
   `DUMMY1_PWR_CON` bit 1 is set, otherwise PDN (DRAM PHY down, MEMPLL off).
   The program can rewrite `SPM_AP_STANDBY_CON` bits 24, 25 and 27 and uses
   `SPM_PASR_DPD_0` as a counter, so both are restored afterwards. Entry
   gates the ARM PLLs and exit restores them unconditionally; I2C_APPM is
   ungated and the I2C6 soft reset happens, as in suspend.

The SMI async DCM and the BSI setting stay out of D3: the display is off,
and the BSI setting applies only with modem, C2K and CONN off.

### D3 implementation (0802, 2026-11-16)

[`0802`](../../patches/proposals/0802-soc-mediatek-mt6797-spm-sleep-run-one-SODI-period-on.patch)
turns S1's `.enter` into one function for both programs and adds a debugfs
file, `/sys/kernel/debug/sodi_once_ms`. Writing 1-2000 runs one SODI period
of that many milliseconds on CPU0 and logs a `sodi cg:` (or `sodi pdn:`)
wake line like S1's, plus `DUMMY1_PWR_CON` and `SPM_PASR_DPD_0`. The SODI
program is optional at load; suspend works without it.

The period is refused unless:
- CPU0 is the only online CPU and the PCM is idle;
- the modem and C2K are off (CONN may be on, as SODI honours it);
- **AP DMA (`0x094` bit 18) and SSUSB (`0x0b0` bits 9, 18, 24) are gated**,
  since SODI does not honour their DRAM requests, as the vendor's
  conditions require.

For the wait, I2C6 is locked so that the program's reset cuts no transfer,
and CPU0's local timer interrupt is masked so that CPU0 stays in WFI.
Compile-checked with `W=1` on the full station series; checkpatch quiet.
Module only.

**D3 writes for owner approval.** S1's approved list with these
differences:

| # | Register | D3 |
| --- | --- | --- |
| program | carveout + `0x2000` (RAM) | `pcm_sodi.bin`, 1,583 words, SHA-256 `dda8cca1…122ae4` |
| W1 | PMIC wrapper slots | **not written** |
| S5 | `PCM_IM_PTR`, `PCM_IM_LEN` | `0xffdd2000` (carveout + `0x2000`, 4 GB mode), `0x62e` |
| S8 | event vectors | the SODI file's sixteen words |
| S10 | `SPM_SRC_REQ` | `0x00000000` |
| S12 | `SPM_SRC2_MASK` | `0x08ff009f` |
| S14 | `WFI_EN` | `0x540`-`0x55c` only (MP0 and MP1) |
| S15 | `PCM_TIMER_VAL` | the period in 32,768 Hz ticks (1-2000 ms) |
| S21 | `SPM_SW_FLAG` | `0x000d1239` in CG mode, `0x000d0239` in PDN mode (`sodi_pdn=1`) |
| X3 | restore | also `SPM_PASR_DPD_0` (`0x630`); `SPM_AP_STANDBY_CON` was already restored |
| T1 | CPU0 `CNTV_CTL_EL0`, `CNTP_CTL_EL0` (system registers) | IMASK set for the wait, then the values read before |
| R1 | `DUMMY1_PWR_CON` (`0x2b4`) | read and logged only |

P1-P3 (PMIC sleep-side bits) and G1-G4 (GIC mask) as already approved. What
the program itself does inside: gate the ARM PLLs, put DRAM in self-refresh
(CG) or also power the PHY and MEMPLL down (PDN), ungate I2C_APPM and
reset I2C6, then undo all of it on the way out.

**USB side (usb-c's design, 2026-11-16, 0800 and 0801).** A "none" role
for MTU3 while VBUS is absent stops the gadget and lets runtime PM power the
controller down without a wake path: PHY off, and `sys_ck`, `ref_ck` and
`mcu_ck` (SSUSB_SYS, REF and BUS) disabled. It needs
`11271000.usb/power/control` set to `auto`, which something at boot must
write on the card (the Arch root session's). A plug is seen through the
PMIC's CHRDET EINT, which the type driver turns back into the device role;
that is the wake path W3b already proved under the GIC mask. Once on an
image, D3 can run with the cable out and `auto` set instead of an unbound
gadget, and 0802's own gate check confirms SSUSB is gated.

### Request D3 (proposed)

- **Candidate:** the running image with `mt6797-spm-sleep.ko` from a
  Buildbox build of the commit recording this stage (module only), and the
  owner's `pcm_sodi.bin` staged at `/lib/firmware/mediatek/mt6797/` next to
  `pcm_suspend.bin`. Its hash must match, or the load says "no SODI
  program".
- **Setup:** a detached script with its log on storage. On battery, cable
  out, the USB gadget unbound (so SSUSB gates), the radios unloaded
  (Wi-Fi off, so AP DMA stays gated), `mt6797-gate-unused` loaded, CPU1-9
  offline, the screen blanked, no watchdog feeder needed (0678).
- **Steps:**
  1. A memory reference: `cpu-mhz` hash on CPU0.
  2. `echo 100 > /sys/kernel/debug/sodi_once_ms`, then the hash again.
  3. 1000 ms, then the hash.
  4. Ten periods of 1000 ms in a row, then the hash.
  5. `sodi_pdn=1`, then 100 ms and 1000 ms, each followed by the hash.
  6. Restore: radios, gadget, CPUs.
- **Hypothesis:** the SODI program runs and returns on its timer in both
  modes while the system is otherwise awake, with memory intact.
- **Unique observation:** the first SODI period on mainline, and whether
  PDN mode (PHY down) returns as CG mode does.
- **Pass:** every write returns 0 and logs `returned=1 loops=0`, `r12` with
  bit 0 (timer), `timer_out` matching the period; every hash equal; clocks
  and gates as before (the logged before/after words); no warning, taint 0.
- **Stop** at the first of: a refusal (the log names which gate); `returned=0`;
  a wrong hash (power off: memory may be corrupt); an Oops, `WARNING` or RCU
  stall; no USB SSH after the restore within 60 s (a hang: the owner's
  force-off). No retry.

**Script:** [`tools/d3.sh`](tools/d3.sh), run detached as root on the card
root with the module path as its argument; it logs to `/var/tmp/d3.log`,
synced line by line. Control link: Wi-Fi SSH to start it with the cable
already out (the owner pulls it before the launch; the script refuses with
external power on). Thirty seconds later it unloads the radios through the
card's own sleep hook (`/usr/lib/systemd/system-sleep/gemini-radios pre`),
so SSH drops. Then, on an image with usb-c's 0800/0801 (image 133 on), it
sets the gadget's `power/control` to `auto`, so that with the cable out MTU3
powers down at runtime and the SSUSB clocks gate; on image 131 (no 0801)
`D3_UNBIND=1` unbinds the gadget instead, as S1 did. Images with 0801
should not have MTU3 unbound: usb-c reports that role control would not
come back after a rebind there, and the window between the role class's
registration check and the call races an unbind (the class's check itself
prevents the callback running after an unbind; fixed in `a8533226` by a
lookup per VBUS change). Without a module path the script loads the image's
own module. At the end it puts `power/control` back (or binds the gadget),
runs the hook's `post` (Wi-Fi first, then whatever else was loaded) and SSH
returns; the custodian then reads the log over Wi-Fi. It checks the module's vermagic, the program's and
`cpu-mhz`'s hashes and that `mt6797-gate-unused` is loaded before changing
anything. A wrong memory hash syncs the log and powers off.

**D3, first try (2026-11-16, image 133, boot `9a1464ca…`).** Custodian's
report; nothing reached the SPM, taint 0 before and after, the restore
worked.

- Run 1 stopped at setup: the module did not load because
  `pcm_suspend.bin` was not staged on the card root (S1 ran from the RAM
  root). d3.sh now checks both programs' hashes before it starts.
- Run 2: the module loaded both programs (`ffdd0000` and `ffdd2000`), MTU3
  was runtime-suspended with `power/control` `auto`, CPU0 alone, screen
  blank. Writing 100 to `sodi_once_ms` returned `ENODEV` with nothing
  logged.

**Cause:** 0802 found the I2C6 adapter by the compatible
`mediatek,mt6797-i2c`, but the Gemini DT gives I2C6 its own,
`mediatek,mt6797-idvfs-i2c` (0116), so the lookup found nothing and the path
returned without a log line.
[`0803`](../../patches/proposals/0803-soc-mediatek-mt6797-spm-sleep-find-I2C6-by-path-and-.patch)
finds it by path, `/i2c@1100e000`, as the project's other I2C6 code does
(`i2c-mt65xx` binds that compatible and registers a normal adapter), and logs
a line for every refusal. Module only; compile-checked with `W=1` on the
full series. No write list change.

| Result | Next |
| --- | --- |
| CG and PDN both pass | D4: the vendor's full SODI wake set, SYS_CIRQ, and wakes from a key, an audio period and a Wi-Fi packet |
| CG passes, PDN fails | Keep CG mode; find what PDN mode needs |
| CG fails | Read the wake line and `SPM_SW_DEBUG`; no retry until analysed |

**D0 and D3 on image 134 (2026-11-16, boot `fef9e0f2…`).** Custodian's
report. Image 134 is `753574f7` (`Image.gz` `d78174ab…`); the SPM module
(`3a4a13ab…`) came from the `73e8f7b7` build, whose `Image.gz` is the same
`d78174ab…`, so it matches the kernel exactly. `d3.sh` `4d95f17d…`,
`d0-census.py` `431a75de…`. Cable out, MTU3 `power/control` `auto` and
runtime-suspended, `mt6797-gate-unused` loaded, battery 100 %, taint 0
before and after.

- **D0, Wi-Fi joined and idle** (blanked, CPU1-7 offline, 60 s): every
  sample blanked. **Nothing blocks SODI:** the INFRA0, INFRA1 and INFRA2
  blocking bits are `0` in every sample and no power domain blocks. For
  deep idle only the display domain (DIS) remains; DISP_PWM no longer shows.
  This is the first time all SODI conditions hold on mainline.
- **D3:** both programs loaded (`pcm_suspend` 1822 words at `bfdd0000`,
  `pcm_sodi` 1583 words at `+0x2000`, SPM pointer `ffdd2000`). All 14
  periods returned on the PCM timer (`returned=1 loops=0 r12=00000001`) and
  the memory hash (`5abed55b4a4c85e5`) was equal after each:

| Periods | Mode | `timer_out` | Slept |
| --- | --- | --- | --- |
| 1 × 100 ms | CG | `0ccf` | 100 ms |
| 1 × 1000 ms | CG | `8003` | 1000 ms |
| 10 × 1000 ms | CG | `8003` each | 1000 ms each |
| 1 × 100 ms | PDN | `0ccf` | 100 ms |
| 1 × 1000 ms | PDN | `8003` | 1000 ms |

The rest of every wake line was the same: the infra gate words
(`03eff900`, `00464816`, `21fe36ff`) and `clk_cfg_0` (`01010101`)
unchanged across each period; `r12_ext` 0, `raw` 0, `r13` `00060400`,
`idle` `000001f7`, event `90100000`, `dummy1` `0000000d`,
`pasr_dpd_0` 0. The restore brought back CPUs 0-7, `power/control` and the
radios; Wi-Fi SSH returned within two minutes. No WARNING, Oops, BUG or RCU
stall; `done, PASS`.

**Decision:** CG and PDN both pass, so the next stage is D4. The SODI program
runs and returns on its timer with the system otherwise awake. This says
nothing yet about current (D3 did not measure it) or about wakes from
devices.

After D3: D4 adds SYS_CIRQ and the vendor's full wake set, and wakes from a
key, an audio period and a Wi-Fi packet; D5 is the CPU0-only cpuidle driver.

### D4: device wakes through SYS_CIRQ (prepared 2026-11-16)

**What changes from D3.**
[`0804`](../../patches/proposals/0804-soc-mediatek-mt6797-spm-sleep-SODI-device-wakes-thro.patch)
(module only) gives a SODI period the vendor's SODI wake sources and
SYS_CIRQ:

- **Wake set.** `WAKE_SRC_FOR_SODI` for MT6797 without the TEE variant,
  `0x0f57c5f5`: the PCM timer, keypad, APXGPT, CONN2AP, EINT, CONN watchdog,
  CCIF0, SCP, both USB lines, C2K watchdog, secure EINT, CCIF1, audio,
  SYS_CIRQ, the debug power request, modem watchdog, CLDMA and SEJ. D3 used
  the suspend pair (timer and EINT).
- **SYS_CIRQ.** Upstream `irq-mtk-cirq` cannot be used as it is: it sits in
  the interrupt hierarchy, needs a DT node and only acts in syscore suspend.
  So the module programs the block itself, as the vendor does around SODI.
  - *Before the GIC mask:* it records every enabled edge SPI from SPI 72
    upwards (220 lines) in SYS_CIRQ, with its polarity from the sysirq
    words, and enables the block in edge-only mode.
  - *After the return, before the GIC is restored:* it reads the status,
    flushes (the block replays the recorded edges into the GIC), disables
    the block and masks every line, which was its state in D0.
  - The register layout is upstream's v1. Level SPIs need no clone: the
    ones that matter have their own wake bits (EINT, keypad, CONN2AP,
    audio), and they stay asserted until the GIC is unmasked.
- **Two more refusals.** The vendor's conditions also require the MSDC
  clocks off (its `msdc_clk_status`), and its audio driver forbids SODI
  while a buffer is in DRAM (`AudDrv_Emi_Clk_On()`, see the
  [audio page](../../docs/hardware/gemini-audio.md)). The period is refused
  in two cases:
  - MSDC0 (eMMC) or MSDC1 (microSD) is clocked (`0x10001094` bits 2 and 4
    not gated);
  - an AFE memory interface is on (`AFE_DAC_CON0` bits 1-9). Mainline's AFE
    keeps its clocks on for as long as it is bound, so the word is read
    only then.

  All the gate checks now run with interrupts off, just before the PCM
  kick, so CPU0 cannot start a transfer after the check.
- **Logging.** Each period logs one more line: the number of cloned lines,
  their mask words and the CIRQ status at the wake.

Compile-checked with `W=1` on the full station series; checkpatch is
quiet. Suspend is unchanged.

**The audio wake is out of D4.** Mainline plays from DRAM, so SODI must not
run during playback, and 0804 refuses it. Music in SODI needs the AFE to
play from its 48 KiB SRAM, which is the audio session's work. D4 therefore
tests a key and an inbound Wi-Fi packet.

**D4 writes for owner approval.** D3's approved list
and these differences, on SODI periods only:

| # | Register | D4 |
| --- | --- | --- |
| S16 | `SPM_WAKEUP_EVENT_MASK` (`0x100060c4`) | `0xf0a83a0a` (the complement of `0x0f57c5f5`) instead of `0xffffffbe` |
| Q1 | CIRQ `MASK_SET` `0x102040c0`-`0d8` (7 words) | `0xffffffff`, at entry and again at exit |
| Q2 | CIRQ `ACK` `0x10204040`-`058` | `0xffffffff`, at entry (drops old status) |
| Q3 | CIRQ `SENS_CLR` `0x102041c0`-`1d8` | the cloned lines (edge) |
| Q4 | CIRQ `POL_SET` `0x10204240`-`258`, `POL_CLR` `0x10204280`-`298` | the cloned lines, rising and falling |
| Q5 | CIRQ `MASK_CLR` `0x10204100`-`118` | the cloned lines |
| Q6 | CIRQ `CON` `0x10204300` | read value \| `0x3` (enable, edge only) at entry; \| `0x4` (flush) after the return, then with `0x3` cleared |
| R2 | GICD `ICFGR` `0x19000c00` + 4n, sysirq `0x10220620`-`63c` and `0x10220690`-`69c`, CIRQ `STA` `0x10204000`-`018`, `AFE_DAC_CON0` `0x11220010` | reads only (the AFE word only while its driver is bound) |

There is no PSCI or SiP call, and no PMIC wrapper write, as in D3.

**Approved** by the owner on 2026-11-16 ("Approve D4"), for the list above
with the 0804 module from `54d1d448` or later.

**What the D4 module still does not handle.** An edge interrupt that is
already pending at the GIC when the period starts doesn't wake the program.
It is served when the period ends: late, but not lost. CIRQ's flush may
also deliver an edge a second time, as in upstream suspend. Both matter for
D5, where idle periods follow each other. D5's driver checks the GIC
pending words before each entry.

### Request D4 (approved 2026-11-16)

- **Candidate:** the running image (134 or later) with `mt6797-spm-sleep.ko`
  from a Buildbox build of the commit recording this stage (module only).
  `pcm_sodi.bin` and `pcm_suspend.bin` stay staged as for D3.
- **Setup:** a detached script with its log on storage. On battery with the
  cable out; **Wi-Fi joined and left up**; MTU3 `power/control` `auto`;
  `mt6797-gate-unused` loaded; no audio playing; the screen blanked; CPU1-9
  offline. Every period is 2000 ms in CG mode.
- **Windows:**
  - **C, inbound packets.** The custodian pings the device from the laptop
    once a second for about three minutes, starting any time after the
    launch. The script waits up to 300 s for echo requests to arrive
    (`/proc/net/snmp` `InEchos`), then runs 60 periods back to back while
    they keep coming. The hash follows the window.
  - **A, quiet.** Once the pings stop: 20 periods, each followed by the
    hash.
  - **B, a key.** The custodian tells the owner to press one key once. The
    window runs up to 300 s and ends at the first period a key ends. The
    hash follows each period.
- **Hypothesis:** an inbound packet ends a period early, through CONN2AP or
  SYS_CIRQ, and so does a key press, through EINT. Memory stays intact.
- **Unique observation:** the first device wakes from SODI on mainline, the
  wake source each one uses, and how often SODI is broken with Wi-Fi joined
  and nothing happening.
- **Pass:**
  - every write returns 0 or is refused (refusals are logged and counted);
  - every period returns;
  - in C, most periods end early by `conn2ap` or `cirq`, and the laptop's
    ping shows no loss and RTTs well under the 2000 ms period (a missed
    wake shows as RTTs near 2 s);
  - in B, one period ends early by `eint` (the keyboard's EINT10), and the
    key reaches the input layer (its EINT count goes up);
  - every hash is equal, and no warning appears.
- **Stop** at the first of: a failed write that is not a refusal; ten
  refusals in a row; `returned=0`; a wrong hash (power off); an Oops,
  `WARNING` or RCU stall; no Wi-Fi SSH within 120 s of the end (a hang: the
  owner's force-off). No retry.

**Script:** [`tools/d4.sh`](tools/d4.sh), run detached as root with the
module path; it logs to `/var/tmp/d4.log`. It checks the same things as
d3.sh, and also that the module contains 0804's CIRQ line. Wi-Fi is not
touched, so the custodian can read the log over SSH at the end. They should
stay off SSH during A, since their traffic would end A's periods early.

| Result | Next |
| --- | --- |
| Packets and the key wake SODI, memory intact | D5: the CPU0-only cpuidle driver, with the GIC pending check before each entry |
| Packets wake, the key does not | Check whether the EINT wake bit or the CIRQ clone misses EINT10; no D5 until a key wakes |
| Packets do not wake (RTTs near 2 s, timer wakes in C) | Read `r12` and the CIRQ status; find CONSYS's wake path (CONN2AP or which SPI) before anything else |
| Periods end at once with a source no one triggered (for example a USB bit) | Drop that source from the wake set, record why, and repeat only that window |
| Refusals dominate a window (MSDC or AP DMA) | Name the holder, as for AP DMA and SSUSB; it is D5's work list |

**D4, first run (2026-11-16, image 135, boot `4cc2b9ba…`).** Custodian's
report:
- *Candidate:* image 135 is `27f2e76b` (`Image.gz` `785d7151…`); the module
  (`849818e4…`) came from the `cedacc07` build, whose `Image.gz` is the same;
  `d4.sh` `6c51a79c`.
- *Setup:* battery 95 %, cable out, Wi-Fi up, MTU3 `auto` and suspended,
  taint 0 at the start and the end.
- **Safe but uninformative.** All 500 periods returned at once with `r12`
  `00000010`: APXGPT, slept 0 ms. No other wake source appeared. The memory
  hash (`5abed55b4a4c85e5`) was equal after every period. The restore worked
  and dmesg had no warning.
- **C:** 60 of 60 periods ended early, none by a packet; 19 echo requests
  arrived in the window. The laptop's 180 pings: no loss, RTT
  32.9/49.5/119.2 ms (min/avg/max). Those numbers say nothing about SODI,
  since CPU0 was in fact never asleep.
- **A:** 20 of 20 ended early.
- **B:** one refusal ("AP DMA running"). The screen lit with no key wake
  seen. The keyboard's EINT10 count went from 195 to 231, so the presses
  reached the input layer between periods.
- **SYS_CIRQ cloned 0 lines** in every period: no enabled SPI from 72
  upwards is configured as edge on this station. So CIRQ has nothing to do
  here; device wakes depend on the SPM's own wake bits (EINT, CONN2AP,
  keypad).

**Cause (inference, not measured):** mainline has no APXGPT node, so nothing
programs, acknowledges or disables the GPT block at `0x10008000`. Its event
to the SPM stays asserted from whatever the boot loader left there. D3 never
saw it because its wake set was only the timer and EINT. The PCM timer
already ends each period, so APXGPT is not needed.

**Change.**
[`0805`](../../patches/proposals/0805-soc-mediatek-mt6797-spm-sleep-leave-APXGPT-out-of-th.patch)
leaves APXGPT out by default. The wake set becomes a module parameter,
`sodi_wake_src`, always limited to the vendor set with the timer forced on,
so another source found stuck can be dropped without a new build (`D4_WAKE=`
in d4.sh). The default mask is `0xf0a83a1a`, which is the approved
`0xf0a83a0a` with APXGPT masked, so it stays inside the approved list.
d4.sh now checks that the module has 0805. It also stops after five periods
in a row ended at once by the same source, since such a run cannot answer
anything. Compile-checked with `W=1`; checkpatch is quiet.

**Rerun:** the same request with the module from a build of the commit that
records this. If another source turns out stuck, the script stops early,
and the rerun drops that source with `D4_WAKE` and repeats.

**D4, second run (2026-11-16, same boot `4cc2b9ba…`).** Custodian's report:
- *Candidate:* module `72b2966a…` from the `b4ad7ebd` build, whose
  `Image.gz` is image 135's `785d7151…`; `d4.sh` `53b6e211`.
- *Setup:* battery 92 %, cable out, Wi-Fi up, taint 0 before and after, no
  refusals. Every hash was equal; no warning.
- **Totals over 80 periods:** 79 ended on the timer at 2000 ms, and one on
  EINT at 456 ms. SYS_CIRQ cloned 0 lines, status 0.
- **A key wakes SODI.** In window A, `r12` `00000040`, slept 456 ms: the
  owner's key press, through the keyboard's EINT10 (its count went from 241
  to 263). Memory was intact. The custodian asked for the key while A was
  still running (A took 53 s), so window B then found the screen already
  lit.
- **Inbound packets do not wake SODI.** In window C, 0 of 60 periods ended
  early, though 119 echo requests arrived in the window. The laptop's 180
  pings: no loss, RTT 31.5/592.7/2631.2 ms (min/avg/max). Each packet waited
  for the 2 s PCM timer. CONSYS never raised CONN2AP.
- **The screen scrambled briefly when it lit** (the owner's report). dmesg
  shows only the lines earlier unblanks on this boot also show (`swiotlb
  buffer is full` from the OVL, and a DSI read). **Probably SODI:** A does
  not check the backlight, so after the key woke the panel, A went on
  running SODI periods while the display lit and scanned out. SODI honours
  the display's DRAM requests (`SPM_SRC2_MASK`), but the screen-on case is
  the open scanout-FIFO question (note of 2026-11-14), not part of D4. The
  custodian asked the owner whether ordinary unblanks also scramble; the
  answer was "No, first time". That supports SODI as the cause. So D5's
  driver must refuse SODI while the display scans out, until the screen-on
  case is studied.

**Why packets did not wake.** The WLAN HIF interrupt is SPI 283, which is
level-triggered. 0804 clones only edge SPIs into SYS_CIRQ, as upstream does
for suspend, and run 1 showed that no enabled SPI here is edge. The vendor
relies on CONSYS raising CONN2AP. On mainline it never did; perhaps it
needs a WMT host-sleep handshake that mainline doesn't send (not
investigated). The general fix, which matches the plan's rule that in idle
every interrupt must reach the program, is to record **level** SPIs in
SYS_CIRQ too.

**Change.**
[`0806`](../../patches/proposals/0806-soc-mediatek-mt6797-spm-sleep-optionally-record-leve.patch)
adds `sodi_cirq_level`, off by default. When set:
- every enabled level SPI in the CIRQ range is recorded too, with its
  polarity;
- the block leaves edge-only mode;
- the SPM's own SPI 180 and the CIRQ output SPI 291 are never recorded.

That level lines are recorded outside edge-only mode is inferred from
upstream's name for the bit ("edge_only mode, record edge-triggered
interrupts"). The run tests it. On the flush, the block may replay a level
line that has already dropped. Its driver then sees one interrupt with
nothing to do, which is harmless in a short test.

d4.sh: `D4_CIRQ_LEVEL=1` loads the module with the parameter. No period
starts while the screen is lit, in any window. Compile-checked with `W=1`;
checkpatch is quiet. With the parameter off, the module behaves as 0805.

**D4b writes for owner approval** (only with `sodi_cirq_level=1`; in
addition to the approved D4 list):

| # | Register | D4b |
| --- | --- | --- |
| Q3b | CIRQ `SENS_SET` `0x10204180`-`198` (7 words) | the cloned level lines |
| Q4, Q5 | `POL_SET`/`POL_CLR`, `MASK_CLR` | as D4, now including the level lines |
| Q6 | CIRQ `CON` `0x10204300` | at entry: read value with `0x2` (edge only) cleared and `0x1` (enable) set; the exit is unchanged |

Nothing outside SYS_CIRQ changes.

**Approved** by the owner on 2026-11-16 ("Approve D4b"), for the list above
with the 0806 module from `147b0400` or later.

### Request D4b (approved 2026-11-16)

- **Candidate:** `mt6797-spm-sleep.ko` from a Buildbox build of the commit
  recording this (0806), on image 135 or later; d4.sh from the same commit,
  run with `D4_CIRQ_LEVEL=1`.
- **Windows and stops:** as D4. The custodian should ask for the key only
  after the log shows "B: press one key once". Reading the log over SSH
  during B is fine, since B ends only on a key wake (EINT or keypad).
- **Hypothesis:** with level SPIs recorded, an inbound packet ends a period
  through the SYS_CIRQ wake (`r12` bit 22), and the CIRQ status names SPI
  283. The key still wakes through EINT.
- **Unique observation:** whether SYS_CIRQ records level lines, and the
  natural wake rate with every interrupt able to end SODI.
- **Pass:** in C, most periods end early by `cirq` with the status showing
  SPI 283 (line 211: word 6, bit 19), and the laptop's RTTs fall well under
  2 s. In B, one key wake. Every hash is equal, and the screen never lights
  during a period.

| Result | Next |
| --- | --- |
| Packets wake through CIRQ, the key through EINT | D5, with `sodi_cirq_level` on by default and the display-blank check in the driver |
| Periods end at once on `cirq` with no packet | Read the status words for the line that is always asserted; leave it out or find its holder |
| Packets still do not wake | CIRQ records edges only; the WLAN wake then needs CONSYS's CONN2AP handshake (wifi-daily) |

**D4b result (2026-11-16, same boot `4cc2b9ba…`).** Custodian's report:
- *Candidate:* module `9cf7b397…` from the `40e98f28` build (`Image.gz`
  `785d7151…`, image 135); `d4.sh` `7eaa5029` with `D4_CIRQ_LEVEL=1`.
- *Setup:* battery 91 %, cable out, Wi-Fi up, taint 0 throughout, no
  refusals. Every hash was equal; no warning.
- **SYS_CIRQ records level lines.** 22 lines were cloned in all 91 periods.
  In window B the owner's key, asked for at the right time, ended a period
  after 649 ms with `r12` `00400000` (SYS_CIRQ) and CIRQ status word 3 bit
  2: line 98, SPI 170, the EINT controller's level parent. With edge-only
  CIRQ (run 2) the same key woke through the SPM's EINT bit instead. Either
  way, a key wakes SODI.
- **A quiet baseline:** in window A, 0 of 20 periods ended early. With Wi-Fi
  joined and every enabled SPI able to wake the program, nothing woke SODI
  in 40 s.
- **Packets still did not wake.** In window C, 0 of 60 periods ended early,
  with 155 echo requests in the window and the CIRQ status 0 throughout. The
  laptop's 180 pings: no loss, RTT 6.2/701.2/2051.4 ms (min/avg/max).
- d4.sh logged "no key wake" because it counted only the EINT and keypad
  bits as a key. The CIRQ wake above is the key (the EINT10 count went from
  263 to 277).

**Why packets do not wake (found from the evidence and the source).** In
every period the cloned word 6 was `00000001`, so line 211 (SPI 283, the
WLAN HIF interrupt) was **not enabled at the GIC**. The mainline Wi-Fi
driver (`drivers/net/wireless/mediatek/mt6797/`) requests no WLAN
interrupt: it polls the HIF from delayed work (the join pump, 20 ms
passes when busy, longer when quiet). `mt6797-consys` requests only the STP
interrupt. So nothing in hardware announces a packet to the AP. A packet
waits for the next poll, and during a SODI period the poll's timer cannot
fire until the period ends. This is not a SODI fault. The same latency
would follow any idle state that holds the timer off, and the poll itself
is a regular wakeup.

**Conclusion of D4.** SODI periods return with memory intact. A key wakes
them through EINT, or through SYS_CIRQ with level recording. SYS_CIRQ does
record level SPIs, so `sodi_cirq_level` becomes D5's default: any device
that uses its interrupt can end a period. A packet can wake SODI only once
the Wi-Fi driver takes its RX on SPI 283 instead of polling, which is the
Wi-Fi driver's work. Until then, under D5's idle driver, the menu governor
will see the poll timer as the next event, so SODI periods end at each poll
and packet latency stays what polling gives today.

D5 also has to keep three findings from D4:
- refuse SODI while the screen is lit (the scramble);
- check the GIC pending words before each entry;
- leave APXGPT out.

### Request D4c: packets with interrupt-driven Wi-Fi RX (2026-11-16)

The owner chose interrupt-driven Wi-Fi RX before D5 ("interrupt driven
wifi", relayed by the custodian). The Wi-Fi session pushed 0807 (the driver
takes RX on its interrupt) and 0808 (DT: SPI 283, level-low) in `35259fb3`:
- the line is enabled at the GIC from link-up on, and masked only from the
  handler to the end of the worker pass;
- a quiet link is still polled once a second for the driver's own
  deadlines.

D4c is window C again, within the approved D4b list, with no write change:
- **Candidate:** an image built from `35259fb3` or later. It carries 0804-0806
  and 0807/0808, so its own `mt6797-spm-sleep.ko` is used, given by path to
  d4.sh. Run with `D4_CIRQ_LEVEL=1`, d4.sh from the commit recording this.
- **Hypothesis:** an inbound packet now asserts SPI 283, which SYS_CIRQ
  records, and that ends the period.
- **Unique observation:** the WLAN line as a SODI wake source, and the RTT
  the laptop sees with it.
- **Pass:**
  - in C, most periods end early with CIRQ status word 6 bit 19, which
    d4.sh now counts as a packet wake (and status word 3 bit 2, SPI 170, as
    a key in B);
  - the laptop's RTTs are well under 2 s;
  - the hashes are equal.

  The driver's 1 s poll cannot end a period, since its timer is masked
  during the wait. So C still isolates the packet wake. A and B run as
  before.

| Result | Next |
| --- | --- |
| Packets wake SODI through SPI 283 | D5, with the Wi-Fi poll counted among the idle wakers in its census |
| No early wakes, word 6 bit 19 never set | Check that the line was cloned (the `cloned=` word 6) and whether the driver had fallen back to polling (its log) |

**D4c result (2026-11-16, image 136, boot `2d4dcc57…`).** Custodian's report:
- *Candidate:* image 136 (`35259fb3`), with the `mt6797-consys` (`ea4e60fe…`)
  and mac (`7b34e126…`) modules swapped in from the `917113e8` build. That
  build adds 0811, which enables CONSYS's interrupt outputs at probe; the
  details are in the Wi-Fi records.
- The image's `mt6797-spm-sleep.ko` was `9cf7b397…`; `d4.sh` `97ae6706`
  (`6c6a34f9`), run with `D4_CIRQ_LEVEL=1`. Cable out, battery 83 %.
- **Packets now wake SODI.** In window C, all 60 periods ended early, and
  every wake named both `conn2ap` and `cirq`: the WLAN line through SYS_CIRQ
  and, now that CONSYS's outputs are enabled, CONN2AP too. Slept
  min/median/max: 11/253/667 ms. The laptop's 180 pings: no loss, RTT
  3.4/29.5/266.7 ms (min/avg/max), against up to 2.6 s in D4b. 38 echo
  requests arrived in the window; the other wakes were other inbound
  traffic.
- Memory hash equal, no refusals, taint 0, no warning; the CPUs were
  restored.
- Windows A and B did not run: the screen was lit when A started, so the
  script started no period. The key wake already passed in D4b. The
  owner was not sure whether they touched the device around 15:52:05,
  but the aw9523 line 4 count went from 0 to 1 by the time A started, so
  a keypad edge did happen: most likely an accidental key press, not a
  spontaneous unblank.

#### D4c rerun of windows A and B

With the owner's yes, the device untouched until the custodian asked for
the key, and no SSH connection from 18:07:16 until B was running. Same
boot 2d4dcc57 and image 136 with the 0811 CONSYS module, the image's
`mt6797-spm-sleep.ko` (9cf7b397), `D4_CIRQ_LEVEL=1`, cable out, battery
73 %. The script runs C first, so C ran again.

- **C:** all 60 periods ended early on conn2ap and SYS_CIRQ; slept
  19/246/834 ms (min/median/max), 43 echo requests in the window. Laptop
  ping 180 sent, 177 received; round trips 4.9/41.7/556.8 ms.
- **A (quiet):** all 20 periods ended early, each on conn2ap and
  SYS_CIRQ (STA6 bit 19); slept 4/56/956 ms. With no laptop traffic and
  no SSH, the joined Wi-Fi link still ends a SODI period within about
  56 ms at the median. Whether that is real inbound traffic (broadcast,
  multicast, beacons passed up) or CONSYS events on CONN2AP is unknown.
- **B (key):** 101 periods, all ended by conn2ap and SYS_CIRQ; slept
  0/317/1219 ms, none with an EINT or key bit. The owner pressed one key
  at about 18:13:10; the aw9523 line 4 count went from 2 to 3 and the
  screen lit, but no period recorded the key. With periods this short
  and awake gaps for the hash check, the key was most likely taken while
  the CPU was awake. Inconclusive, neither pass nor fail; D4b showed the
  key wake with polled Wi-Fi. An isolated key test with this driver
  needs Wi-Fi quiet (down, or the WLAN line out of the wake set).
- Every hash equal, no refusals, taint 0, no warning; CPUs restored.

A read-only quiet-link census on the same boot (CPU awake, screen
blanked, no SSH, 60 s) counted 2.9 handled `mt6797-wlan` interrupts per
second and 3.1 received frames per second on wlan0 (1.4/s of them
dropped), with nothing sent. Window A's 56 ms median period means 10-15
SODI wakes per second, all flagged conn2ap and STA6 bit 19: several times
the handled interrupt rate. Untested explanations: CONN2AP asserts
without a WLAN interrupt the driver handles; the level-mode SYS_CIRQ
record for SPI 283 persists or fires again after each exit; or CONSYS
behaves differently while the AP is in SODI.

Inference, untested (from the Wi-Fi session, agreed by the custodian):
the wakes fit beacon timing. A 102.4 ms beacon interval at a random phase
gives a median wait of about 51 ms and about 10 wakes a second. The
driver refuses power save (`IEEE80211_CONF_PS` returns `-EOPNOTSUPP`), so
the firmware listens for every beacon, and CONSYS probably asserts
CONN2AP for its resources each time, without a WLAN interrupt the driver
handles. Beacon timing alone does not explain the 956 ms longest period.
Firmware power save that wakes only at DTIM would cut these wakes; it
needs new firmware commands and changes on air, so it waits for the
owner's admission. Until then, long SODI residency needs Wi-Fi down.

For D5 this is the main finding: an idle joined link rarely lets a
period run to its timer, so the WLAN wake rate bounds what SODI can
save while Wi-Fi is up, until the extra wakes are explained.

**D4 is complete.** SODI periods are ended by the PCM timer, a key (EINT,
or SYS_CIRQ), and an inbound packet (SYS_CIRQ and CONN2AP), with memory
intact. The next stage is D5.

### D5: SODI as CPU0's idle state (prepared 2026-11-16)

**What changes.**
[`0816`](../../patches/proposals/0816-soc-mediatek-mt6797-spm-sleep-SODI-as-CPU0-s-idle-st.patch)
(module only) registers a cpuidle driver for CPU0 alone, with two states:
WFI and SODI. SODI starts disabled; writing 0 to
`/sys/devices/system/cpu/cpu0/cpuidle/state1/disable` enables it. The menu
governor then picks it when it expects CPU0 to stay idle for at least
2 ms. Its exit latency is set at 1 ms, the vendor's figure, until D5
measures it.

Each SODI entry runs with interrupts off. It falls back to WFI, and counts
why, unless all of these hold:
- CPU0 is the only online CPU;
- the backlight is off (`pwm-backlight` blank), which keeps SODI away from
  a display that scans out (the D4 scramble);
- no suspend or `sodi_once_ms` test is in progress;
- the next local timer event is at least 2 ms away;
- I2C6 is free (a trylock, since the program resets it);
- AP DMA, USB, MSDC and the audio DMA are idle (as in D4).

The PCM timer ends the period 1 ms before the next local timer event,
capped at 2 s (`sodi_idle_max_ms`), and the local timer is masked for the
wait, as in D3. The wait itself is an RCU idle period. Any error other than
a refusal (a period that never returns, a PCM reset that fails) stops SODI
for good until the module is reloaded.

Three changes apply to every SODI period, the `sodi_once_ms` test
included:
- **Before the PCM reset**, SYS_CIRQ records the enabled interrupts and the
  GIC masks them. These are the same writes as D4b, made earlier, so an
  interrupt that arrives while the program loads is recorded too.
- **The GIC pending check.** If an enabled interrupt is already pending
  after the mask, the period is refused: SYS_CIRQ never saw it, so it would
  wait for the PCM timer. This was D4's open point.
- **Level recording is the default** (`sodi_cirq_level=1`), as D4b and D4c
  showed it records the WLAN line and ends the period.

`/sys/kernel/debug/sodi_idle` reports:
- entries and refusals by reason;
- wakes by source (timer, keypad, CONN2AP, EINT, SYS_CIRQ, other);
- the SYS_CIRQ lines that ended periods;
- the time spent entering, sleeping and leaving, from the arch counter.

**No PMIC write in idle.** D3 and D4 applied P1-P3 (VGPU low-IQ, the
power-good force, the VCORE sleep voltage) around each test period through
the PMIC wrapper's regmap. That regmap sleeps, so the idle path cannot use
it, and holding P2 for hours while awake would mask power-good faults. The
inference is that SODI does not need them:
- P1 and P3 act only while `SRCLKEN0` is low, and SODI keeps 26 MHz up;
- with VCORE DVS off (flag 3), SODI issues no wrapper command, so no rail
  moves and power-good has nothing to guard.

This is not tested. D5 is the first SODI run without them, and an early
reset in D5 points here first. `sodi_once_ms` still applies them.

**The cpuidle core needs a new image.** The station config has
`# CONFIG_CPU_IDLE is not set` (from `gemini-handoff.fragment`; image 136
has it too). The station SPM fragment now sets `CONFIG_CPU_IDLE=y` and the
menu governor, and keeps `ARM_PSCI_CPUIDLE` out. With no driver
registered, idle stays the plain WFI it is today, so this config change can
go into the next batched image with nothing else depending on it.

Compile-checked with `W=1` with and without `CONFIG_CPU_IDLE`; checkpatch
`--strict` is quiet.

**D5 writes for owner approval.** The approved D4 and D4b lists, with
these differences, on SODI periods only:

| # | Register | D5 |
| --- | --- | --- |
| S15 | `PCM_TIMER_VAL` | per period, from cpuidle: the time to the next local timer event less 1 ms, at most 2 s (1-65,536 ticks), inside D3's approved 1-2000 ms |
| G1-G4, Q1-Q6, Q3b | GIC mask, SYS_CIRQ | the same values, written before the PCM reset instead of after the kick |
| G5 | GICD `ISENABLER6` `0x19000118` bit 20 (SPI 180, the SPM) | set after the kick, from cpuidle only, for the wait |
| G6 | GICD `ICENABLER6` `0x19000198` bit 20 | after the return's interrupt clear, from cpuidle only |
| R3 | GICD `ISPENDR0`-`n` `0x19000200` + 4n | reads only |
| P1-P3 | PMIC | **not written** from cpuidle |

T1 (CPU0's timer masks) is as in D3. Outside the SPM, the run writes the
state's sysfs `disable` file and takes CPU1-9 offline, as D4 did.

**Approved** by the owner on 2026-11-17 ("Approve D5"), for the list above,
with no PMIC write from idle, and the 0816 module from the same Buildbox
build as an image with `CONFIG_CPU_IDLE`.

### Request D5 (approved 2026-11-17)

- **Candidate:** an image with `CONFIG_CPU_IDLE=y` and the menu governor,
  built on Buildbox from a commit at or after the one recording this stage,
  with `mt6797-spm-sleep.ko` from the same build, and `pcm_sodi.bin` staged
  as before. Batch the image with any other built-in changes waiting.
- **State:** cable out, Wi-Fi joined and quiet, `mt6797-gate-unused`
  loaded, nobody touching the device, no SSH connection until the log says
  "done".
- **Script:** [`tools/d5.sh`](tools/d5.sh), run as root and detached. It
  reloads the module, waits for the idle blank and takes CPU1-9 offline.
  Then it runs four windows of 180 s: SODI off, on, off, on. Each window
  logs the charge-counter current, the state's usage and time, the
  interrupt count, and in the on windows the module's counters. It checks
  the memory hash after each window.
- *Hypothesis:* with the screen dark and CPU0 alone, the governor enters
  SODI by itself, memory stays intact, and the current falls against the
  off windows by the share of time spent in SODI.
- *Unique observation:* the first autonomous SODI residency, its entry and
  exit cost, the refusal census, and the lines that end the periods.
- **Stops:** a period with no return (the module's "stopped" counter); a
  new WARNING, Oops, BUG or RCU stall; the screen lit or CPU1-9 back; a
  wrong hash, after which the script powers off.

| Outcome | Decision |
| --- | --- |
| SODI entered, memory intact, current lower than off | D5 continues with the Wi-Fi power-save and music cases; keep the program resident if entry cost is a large share |
| SODI entered, no current gain | Compare entry and exit cost with the period length; with about 10 beacon wakes a second, Wi-Fi power save comes before more SODI work |
| Entries mostly refused | The leading reason is the work list (MSDC or I2C6 most likely), as for AP DMA and SSUSB |
| A reset or hang early in the run | Recover by force-off; check P2's absence first, then the earlier CIRQ programming |
| Hash mismatch | Power off (the script does); SODI idle is withheld until the cause is found |

**Wi-Fi power save, measured since (custodian, 2026-11-16).** These
figures come from the Wi-Fi record's test, without SODI. On boot
2d4dcc57, on battery, with the screen blanked and the link idle, the
Wi-Fi driver's fast power save (0815, `power_save=2`) cut the current from
142.7 mA to about 85 mA (A/B/A, 10 min each). The handled WLAN interrupts
rose from 3.8 to about 5.6 per second, with the same received traffic. So
power save lets the firmware sleep between DTIMs, but it does not reduce
the host wakes. Whether it changes how often CONN2AP ends a SODI period is
not measured yet. D5 should run with power save on, the realistic case,
and the custodian should note its setting in the log.

**SODI periods with power save on and off (custodian, 2026-11-16).** These
are D4 windows A, B and C under `d4.sh` with `D4_CIRQ_LEVEL=1`, not D5. The
run used boot 2d4dcc57 (image 136), cable out, 59 % battery and hands off.
It ran with power save on (`power_save=2`), then off. In both runs every
period was ended by CONN2AP through SYS_CIRQ. Memory hashes were equal at
every check, taint stayed 0 and nothing stopped. Sleep per period in ms
(median / mean / p90):

| Window | Power save on | Power save off |
| --- | --- | --- |
| C, inbound ping | 47 / 98 / 243 (n 60) | 256 / 280 / 432 (n 60) |
| A, quiet | 186 / 226 / 482 | 57 / 225 / 511 |
| B, quiet 300 s | 144 / 225 / 460 (n 280) | 250 / 291 / 824 (n 239) |

Refusals were 0 with power save on, and 3 with it off (1 AP DMA, 2 MSDC).
The average ping round trip was 89 ms on and 28 ms off, with no loss either
way. *Inference:* with power save on, the firmware's sleep and wake notices
on the WLAN line end SODI periods at least as often. This matches the rise
in handled interrupts from 3.8 to 5.6 per second. So power save saves about
57 mA in the radio but does not lengthen SODI periods. A WLAN-line filter or
a wake-reason check is follow-up work after D5. D5 still runs with power
save on, the realistic case.

### D5 run 1: reset in the first SODI window (custodian, 2026-11-17)

**Setup.** Image 137 (Buildbox `735859f0`, `Image.gz` 397820cd,
boot2 0653d4a3 with a verified readback), `mt6797-spm-sleep.ko`
b24a657e and `d5.sh` 8368909f. Boot c9ee1c96. The cpuidle driver was
`mt6797_sodi` with the menu governor, exit latency 1000 us and residency
2000 us. `sodi_cirq_level` was on and `sodi_wake_src` was `0f57c5e5`.
Wi-Fi power save was on (`power_save=2`). Cable out, battery 52 %,
`mt6797-gate-unused` loaded, hands off.

**Observed.**
- **off1:** 180 s at 80 mA by the charge counter, 0 SODI entries,
  6087 interrupts, hash equal. With CPU0 alone and Wi-Fi power save on,
  the station draws 80 mA without SODI.
- **on1:** started 15:32:58. `d5.log` has no later line. The script logged
  only at the end of a window, so the reset came 0-180 s into on1. The
  owner saw Gemian at about 15:36, then shut down and selected boot2 (boot
  e40ab1c4, boot2 still 0653d4a3, taint 0).
- **Nothing recorded the cause.** pstore was empty (a Gemian boot came
  between, or the reset cleared DRAM). The persistent journal ends at
  15:29:42, when CPU1-7 went offline. No watchdog or reset-reason line
  survived.

**Result.** The SODI idle state reset the device within 180 s. The entry
count before the reset and the reset's time are unknown. SODI idle is
withheld.

**Suspects.** The decision table puts the absent P1-P3 first and the
SYS_CIRQ and GIC mask moved before the PCM reset second. D5 also differs
from D4 in ways the table did not name:
- the entry rate, with many periods back to back;
- short periods from the governor;
- the SPM interrupt enabled in the GIC for the wait (G5, G6);
- the wait as an RCU idle period.

**`d5.sh` change.** Each window now logs its start. Each SODI-on window
logs, synced every 10 s:
- the state's usage and time;
- the module's `tried`, `entered`, `stopped` and `error` counters.

A rerun dates a reset to within 10 s and gives the entries before it.

### Request D5a (approved 2026-11-17): 0816's shared path under D4

D5a splits the suspects with no new write. Image 137 and module b24a657e
run [`tools/d4.sh`](tools/d4.sh) with `D4_CIRQ_LEVEL=1`, Wi-Fi power save
on, cable out and hands off. These test periods (`sodi_once_ms`) still
apply P1-P3 and are not cpuidle entries. They do take 0816's SYS_CIRQ and
GIC mask before the PCM reset, and the GIC pending check. The writes are
within the approved D4b and D5 lists.

- *Hypothesis:* the reset comes from the cpuidle path, not from the
  programming 0816 moved.
- *Unique observation:* whether 0816's moved SYS_CIRQ and GIC programming
  survives D4's windows A, B and C on image 137.
- **Stops:** as in D4. A reset is recovered as in D5 run 1.

| Outcome | Decision |
| --- | --- |
| D4 windows pass, hashes equal | The cause is in the idle path: P1-P3, the entry rate, G5/G6 or the RCU idle wait. Next: D5 again with the per-10 s log and `sodi_idle_max_ms` lowered, to count entries before the reset |
| Reset or hang | The moved programming is the cause. Restore 0806's order (mask after the kick) and keep only the pending check |

### D5a: 0816's test periods reset the device (custodian, 2026-11-17)

**Approved** by the owner ("Approve D5a").

**Setup.** Image 137 (`735859f0`, boot2 0653d4a3), boot e40ab1c4, module
b24a657e (0816), `d4.sh` 97ae6706 with `D4_CIRQ_LEVEL=1`. Wi-Fi power save
on (`power_save=2`), cable out, battery 49 %, hands off. The laptop pinged
during window C.

**Observed.**
- Window C started at 15:50:11. Pings arrived from 15:50:20.
- 21 periods returned, all reading "r12 00400020, wake: conn2ap cirq, 23
  lines" with SYS_CIRQ status bit 19 of word 6 (SPI 283, WLAN). They slept
  0-504 ms, including 0, 1 and 5 ms periods, and each logged
  `returned=1 loops=0`.
- The journal's last lines, at 15:50:30.022-.024, are period 21's return
  and its `sodi cirq` line. The driver prints that line after the period's
  return line, so it belongs to period 21, not 22.
- Period 22 logged nothing. Pings stopped answering after `icmp_seq` 10,
  at about 15:50:30. The device then reset into Gemian.
- pstore was empty, with no warning or Oops before the reset. The next
  boot, ea40fba9, was clean (taint 0) and boot2 was still 0653d4a3.

**Result.** The same `d4.sh` windows passed on image 136 with module
9cf7b397 (0806) earlier the same day: 360 and 319 periods, hashes equal.
On image 137 with 0816 a test period never returned, and the reset
followed. These test periods are not cpuidle entries and still apply
P1-P3. So D5 run 1's reset does not need the idle path or the missing
P1-P3 to explain it.

Two things differ from the passing run:
- 0816's SYS_CIRQ and GIC programming, moved before the PCM reset, and
  the pending check;
- the cpuidle core and the registered `mt6797_sodi` driver, with the
  SODI state disabled.

The decision table points at the first. *Inference, not tested:* with
level recording, an interrupt that arrives while the program loads leaves
the SYS_CIRQ wake asserted before the kick. The program may not see a wake
asserted before it starts, and with the GIC masked nothing else takes CPU0
out of WFI. That the PCM timer did not end the period either is not
explained.

### Request D5b (approved 2026-11-17): the order up to 0806, on image 137

[`0817`](../../patches/proposals/0817-soc-mediatek-mt6797-spm-sleep-program-SYS_CIRQ-after.patch)
(module only) programs SYS_CIRQ and masks the GIC after the kick again, as
up to 0806. It keeps the pending check, now before the PCM reset with the
GIC unmasked. It is compile-checked with `W=1`, with and without
`CONFIG_CPU_IDLE`, and checkpatch `--strict` is quiet. Its writes are the
D4b list in D4b's order.

- **Candidate:** image 137, unchanged, and `mt6797-spm-sleep.ko` from a
  Buildbox build of the commit recording this stage. Only the module
  changes, so no boot2 write.
- **Run:** [`tools/d4.sh`](tools/d4.sh) with `D4_CIRQ_LEVEL=1`, Wi-Fi power
  save on, cable out and hands off, with pings in window C as in D5a.
- *Hypothesis:* with the order up to 0806, the test periods return on
  image 137 as they did on image 136.
- *Unique observation:* whether the cpuidle core and 0816's other changes
  pass D4's windows when the moved programming is gone.
- **Stops:** as in D4. A reset is recovered as in D5a.

| Outcome | Decision |
| --- | --- |
| Windows A-C pass, hashes equal | The moved programming caused the D5a reset, and the image is cleared. Next: D5 again with the 0817 module and the per-10 s log (owner's yes) |
| Reset or hang | The cause is elsewhere in 0816 or in the cpuidle image. Next: the 0806 module built for image 137, to split the two |

### D5b: 0817's test periods reset the device too (custodian, 2026-11-17)

**Approved** by the owner ("Approve D5b").

**Setup.** Image 137, unchanged (boot2 0653d4a3, `Image.gz` 397820cd), on
boot ea40fba9. Module 3f0d96d6 (0817) came from Buildbox `d3092b37`, whose
`Image.gz` is also 397820cd. `d4.sh` 97ae6706 with `D4_CIRQ_LEVEL=1`, Wi-Fi
power save on, cable out, battery 46 %, hands off, pings in window C.

**Observed.**
- Window C started at 16:24:41. Pings arrived from 16:24:50.
- 14 periods returned, all ended by CONN2AP through SYS_CIRQ, with
  `returned=1 loops=0`.
- The last journal lines, at 16:24:56.62, are a period's return and its
  `sodi cirq` line. Period 15 logged nothing.
- 8 of 180 pings were answered. The device reset into Gemian (the owner
  confirmed).
- pstore was empty, with no warning or Oops. The next boot, b8d5a469, was
  clean (taint 0) and boot2 was still 0653d4a3.

**Result.** Putting SYS_CIRQ and the GIC mask back after the kick did not
help. Image 137 has now reset three times:
- D5: a cpuidle SODI window, within 180 s;
- D5a: the 0816 module, period 22, about 10 s after the pings began;
- D5b: the 0817 module, period 15, about 6 s after the pings began.

On image 136 the 0806 module (9cf7b397) passed the same windows twice that
day. The moved programming is cleared as the cause.

Three differences remain:
- **image 137:** it adds `CONFIG_CPU_IDLE` and the menu governor. The other
  additions between the two images' series are Wi-Fi and CONSYS modules
  (0809-0815), which run only if loaded;
- **the cpuidle driver registration:** in D5a and D5b, CPU0's ordinary idle
  went through `mt6797_sodi`'s WFI state;
- **0816's other shared changes,** such as the pending check.

### Request D5c (approved 2026-11-17): the 0806 module on image 137

The station config has `# CONFIG_MODVERSIONS is not set`, and images 136
and 137 share a release string. So module 9cf7b397, the 0806 build that
passed on image 136, loads on image 137 unchanged. This needs no new code,
no build and no boot2 write. Its writes are the D4b list. *Inference:* the
0806 module uses no cpuidle interface, and `CONFIG_CPU_IDLE` changes no
structure it uses. The run should still check that it loads cleanly.

- **Run:** [`tools/d4.sh`](tools/d4.sh) with module 9cf7b397 and
  `D4_CIRQ_LEVEL=1`, exactly as on image 136: Wi-Fi power save on, cable
  out, hands off, pings in window C. Log the hashes of the loaded Wi-Fi and
  CONSYS modules and compare them with the image-136 runs.
- *Hypothesis:* the resets come from 0816's module changes, mainly the
  cpuidle driver registration, not from image 137.
- *Unique observation:* whether image 137 resets with the module that
  passed on image 136.
- **Stops:** as in D4. A reset is recovered as in D5a.

| Outcome | Decision |
| --- | --- |
| Windows A-C pass, hashes equal | The cause is in 0816's module. Next: an 0817 module that skips the cpuidle registration (a parameter), to split the registration from the rest |
| Reset or hang | The cause is image 137 or the Wi-Fi module set, not 0816. Compare the Wi-Fi and CONSYS module hashes with the image-136 runs; if they differ, rerun with the image-136 set |

### D5c: the 0806 module passes on image 137 (custodian, 2026-11-17)

**Approved** by the owner ("Approve D5c").

**Setup.** Image 137 (boot2 0653d4a3), boot b8d5a469. Module 9cf7b397 (the
0806 build from 35259fb3) loaded cleanly with a matching vermagic. `d4.sh`
97ae6706 with `D4_CIRQ_LEVEL=1`, Wi-Fi power save on, cable out, battery
42 %, hands off. The radio modules on disk were mac e989cbc1, wlan-core
0f3a9a9e and consys ea4e60fe, the same as in the image-136 runs. 180 of
180 pings were answered, averaging 93 ms.

**Observed.** Sleep per period in ms:

| Window | Periods | Median | Mean | p90 |
| --- | --- | --- | --- | --- |
| C, pings | 60, all ended early by a packet | 97 | 126 | 293 |
| A, quiet | 20 | 378 | 292 | — |
| B, quiet | 347, no key | 320 | 296 | 641 |

Every period was ended by CONN2AP through SYS_CIRQ. All 368 hash checks
were equal. There was 1 refusal (MSDC), taint stayed 0, and there was no
warning or Oops.

**Result.** Image 137 and the Wi-Fi module set are cleared: the 0806
module ran 427 periods there. The 0816 and 0817 modules reset the device
within 15-22 periods under pings. So the cause is in 0816's changes that
0817 kept. By reading the code, `sodi_once` differs from 0806 in only two
ways:
- the GIC pending check, which runs before any SPM change and only reads;
- the CPU0 cpuidle driver, registered at load. With the SODI state
  disabled, CPU0's ordinary idle still runs through the cpuidle core and
  the driver's WFI state instead of the default idle.

Level recording is set by `d4.sh` in every run. The rest of 0816 is only
reached from the SODI state.

### Request D5d (approved 2026-11-17): 0817 without the cpuidle driver

[`0819`](../../patches/proposals/0819-soc-mediatek-mt6797-spm-sleep-optionally-skip-the-SO.patch)
(module only) adds `sodi_idle` (default on). Loaded with `sodi_idle=0`, the
module does not register the cpuidle driver and is otherwise 0817. It is
compile-checked with `W=1`, with and without `CONFIG_CPU_IDLE`, and
checkpatch `--strict` is quiet. There is no write change.

- **Candidate:** image 137, unchanged, and `mt6797-spm-sleep.ko` from a
  Buildbox build of the commit recording this stage. No boot2 write.
- **Run:** [`tools/d4.sh`](tools/d4.sh) with `D4_CIRQ_LEVEL=1`, as in D5c,
  and `D4_IDLE=0`, which loads the module with `sodi_idle=0`. Check that
  `/sys/devices/system/cpu/cpuidle/current_driver` reads `none` before
  the windows.
- *Hypothesis:* without the cpuidle driver, the 0817 module passes as 0806
  did.
- *Unique observation:* whether the cpuidle registration alone separates
  the resets from the passes.
- **Stops:** as in D4. A reset is recovered as in D5a.

| Outcome | Decision |
| --- | --- |
| Windows A-C pass | The registered cpuidle driver causes the resets, even with SODI disabled. Next: find how CPU0's idle under cpuidle differs from the default idle (the WFI state, the governor's tick handling), before any SODI idle |
| Reset or hang | The pending check, or another 0816 change, is the cause. Next: 0817 without the pending check |

### D5d: 0817 without the cpuidle driver passes (custodian, 2026-11-17)

**Approved** by the owner ("Approve D5d").

**Setup.** Image 137 (boot2 0653d4a3), boot b8d5a469. Module 6db2a032
(0819, Buildbox `ef11657d`, whose `Image.gz` 397820cd is image 137's).
`d4.sh` 18a4f9ec with `D4_CIRQ_LEVEL=1 D4_IDLE=0`. Wi-Fi power save on,
cable out, battery 41 %, hands off. 180 of 180 pings were answered,
averaging 93 ms. `current_driver` read `none` before the run, and again
during window C at 17:13:47 (with `sodi_idle` N).

**Observed.**

| Window | Periods | Median sleep (ms) | p90 (ms) |
| --- | --- | --- | --- |
| C, pings | 60, all ended by a packet | 142 (mean 161) | 304 |
| A, quiet | 20 | 287 | — |
| B, quiet | 297 | 231 | 541 |

Every period was ended by CONN2AP through SYS_CIRQ. All 318 hash checks
were equal. There was 1 refusal (MSDC), taint stayed 0, and the run
ended at 17:22:11.

**Result.** On image 137, under pings:

| Module | CPU0 cpuidle driver | Outcome |
| --- | --- | --- |
| 0816 (D5a) | registered | reset at period 22 of C |
| 0817 (D5b) | registered | reset at period 15 of C |
| 0806 (D5c) | none | passed, 427 periods |
| 0819, `sodi_idle=0` (D5d) | none | passed, 377 periods |

The pending check is cleared. The cause is in `sodi_idle_register()`, which
D5d skipped as a whole. Its parts are references to the backlight and
I2C6 devices, and the cpuidle registration. *Inference:* the registration
is the active part. With it, CPU0's ordinary idle runs through the cpuidle
core and the driver's WFI state between periods, with SODI disabled.

With two states, `cpuidle_idle_call()` asks the menu governor, which keeps
the tick when it predicts an idle shorter than a tick. Pings make that
the usual case. With no driver, the idle loop stops the tick as usual. So
under pings, the registered driver mainly means **the tick runs while
CPU0 idles between periods**. The resets came in window C, under pings,
and C runs first. So the runs do not show whether the driver also fails
on a quiet link.

### Request D5e (approved 2026-11-17): the WFI state alone

[`0820`](../../patches/proposals/0820-soc-mediatek-mt6797-spm-sleep-optionally-register-th.patch)
(module only) adds `sodi_idle_states` (default 2). Loaded with
`sodi_idle_states=1`, the module registers the cpuidle driver with the WFI
state alone. The idle loop then skips the governor and stops the tick as
with no driver, but still enters through the cpuidle core and the
driver's WFI. It is compile-checked with `W=1`, with and without
`CONFIG_CPU_IDLE`, and checkpatch `--strict` is quiet. There is no write
change.

- **Candidate:** image 137, unchanged, and `mt6797-spm-sleep.ko` from a
  Buildbox build of the commit recording this stage. No boot2 write.
- **Run:** [`tools/d4.sh`](tools/d4.sh) with `D4_CIRQ_LEVEL=1 D4_STATES=1`,
  as in D5d. Check that `current_driver` reads `mt6797_sodi` and that
  `cpu0/cpuidle` has no `state1`.
- *Hypothesis:* the governor's retained tick is what makes the registered
  driver fail; with one state the run passes.
- *Unique observation:* whether the cpuidle core's entry path, without the
  governor, separates the resets from the passes.
- **Stops:** as in D4. A reset is recovered as in D5a.

| Outcome | Decision |
| --- | --- |
| Windows A-C pass | The governor's choices, most likely the retained tick, cause the resets. Next: find how a tick running between periods breaks the next period, starting with the local timer's state at entry |
| Reset or hang | The cpuidle entry path or the held references cause it. Next: compare the driver's WFI with the kernel's `cpu_do_idle`, and drop the references |

### D5e: the driver with the WFI state alone passes (custodian, 2026-11-17)

**Approved** by the owner ("Approve D5e").

**Setup.** Image 137 (boot2 0653d4a3), boot b8d5a469. Module 24960448
(0820, Buildbox `a5e43fde`, `Image.gz` 397820cd). `d4.sh` 88f66438 with
`D4_CIRQ_LEVEL=1 D4_STATES=1`. Wi-Fi power save on, cable out, battery
39 %, hands off. 180 of 180 pings were answered, averaging 94 ms.
`current_driver` read `none` before the load. At 17:48:12, after the load
and before C, it read `mt6797_sodi` with the menu governor, `cpu0/cpuidle`
had `state0` (WFI) alone, and `sodi_idle_states` was 1.

**Observed.**

| Window | Periods | Median sleep (ms) | p90 (ms) |
| --- | --- | --- | --- |
| C, pings | 60, all ended by a packet | 156 (mean 187) | 402 |
| A, quiet | 20 | 151 | — |
| B, quiet | 292 | 103 | 402 |

Every period was ended by CONN2AP through SYS_CIRQ. All 313 hash checks
were equal. There were 0 refusals, taint stayed 0, and the run ended at
17:56:35.

**Result.** On image 137 under pings:

| CPU0 cpuidle driver | Outcome |
| --- | --- |
| WFI and SODI, SODI disabled (D5a, D5b) | reset at periods 22 and 15 |
| none (D5c, D5d) | passed |
| WFI alone (D5e) | passed, 372 periods |

The cpuidle core's entry path and the held backlight and I2C6 references
are cleared. What remains is the two-state idle, where `cpuidle_idle_call()`
asks the menu governor. *Inference, not measured:* the governor keeps the
tick through short idles under pings. CPU0's local timer would then
usually be due within a tick (10 ms at `HZ=100`) when a period starts, and
would expire, masked, during it. With the tick stopped that is rarer.

D5 run 1 fits this only in part. The idle state already ends its periods
1 ms before the next local timer event. That run also differs in the
missing P1-P3 and in SODI entered from idle.

### Request D5f (approved 2026-11-17): two states, test periods end before the tick

[`0821`](../../patches/proposals/0821-soc-mediatek-mt6797-spm-sleep-optionally-end-test-pe.patch)
(module only) adds a line to each test period's log: the time from entry
to CPU0's next local timer event, and the period's length. It also adds
`sodi_timer_cap` (default off). With it on, a test period ends 1 ms before
that event and is refused if the event is under 2 ms away, as the idle
state does. It is compile-checked with `W=1`, with and without
`CONFIG_CPU_IDLE`, and checkpatch `--strict` is quiet. Only `PCM_TIMER_VAL`
(S15) changes, and it stays inside the approved 1-2000 ms.

- **Candidate:** image 137, unchanged, and `mt6797-spm-sleep.ko` from a
  Buildbox build of the commit recording this stage. No boot2 write.
- **Run:** [`tools/d4.sh`](tools/d4.sh) with `D4_CIRQ_LEVEL=1
  D4_TIMER_CAP=1` and two states, as in D5a and D5b, otherwise as in D5e.
  The periods are short when the tick is kept. Expect some "timer due"
  refusals.
- *Hypothesis:* a local timer that expires inside a period breaks it; with
  the cap, two states pass.
- *Unique observation:* the time to the next local timer at each entry
  with two states under pings, which shows whether the tick is kept, and
  whether two states pass with the cap.
- **Stops:** as in D4. A reset is recovered as in D5a.

| Outcome | Decision |
| --- | --- |
| Pass, timer mostly due within 10 ms | A timer expiring inside a period is the hazard, and the idle state's cap avoids it. D5 again, with P1-P3's absence as the first suspect for run 1 |
| Pass, timer rarely due soon | The cap was not exercised; the governor's effect is elsewhere. Next: repeat without the cap but with the timer log, to see the entry state before a reset |
| Reset or hang | The timer expiring inside a period is not the hazard. The log lines before the reset show the timer state at entry; look at other governor effects |

**D5f attempt 1 did not run (custodian, 2026-11-17).** `d4.sh` stopped at
setup with "the running SPM module did not unload". No period ran and the
device was unaffected. The 0820 module from D5e still had its cpuidle
driver registered, and the cpuidle core holds a reference on the
driver's owner, so `rmmod` refuses. `lsmod` showed a use count of 1.
D5a and D5b followed resets, and D5c-D5e started with no driver
registered, so this had not shown before. From 0816 on, a module that
registered the driver needs a fresh boot before the next run. `d4.sh` and
`d5.sh` now check the use count before changing anything. Making the
module unloadable again is for later, outside this bisection, so that
D5f's candidate stays unchanged.

### D5f: two states reset even with periods ending before the tick (custodian, 2026-11-17)

**Approved** by the owner ("Approve D5f"). The run was on a fresh boot,
a4b787c7, after the first attempt.

**Setup.** Image 137, module 1c122f03 (0821, Buildbox `c24b1d73`). `d4.sh`
0a9ac3a9 with `D4_CIRQ_LEVEL=1 D4_TIMER_CAP=1` and two states.
`current_driver` read `none` before the load. Wi-Fi power save on, battery
34 %, hands off. C started at 18:29:01 and pings arrived from 18:29:09.

**Observed, every SODI journal line.**
- 18:29:09.388-.413, period 1: returned on the PCM timer (r12
  `00000001`), with the next local event 2663 us after entry. The period
  was capped to 54 ticks (1.6 ms) and slept 1 ms.
- 18:29:09.758: a "timer due" refusal. The `.764`, `.789` and `.790` lines
  after it are that refusal's: `sodi_once` printed the previous period's
  wake and SYS_CIRQ lines again, since a refusal leaves `s.entered` set.
  Its timer line (198 us, 65,536 ticks) shows the cap refused it as
  designed, with the period length left uncapped.
- Period 2, retried 0.5 s later, logged nothing. 2 of 180 pings were
  answered, and the device reset into Gemian. pstore was empty.

**Result.** With two states, a period that ended before the next local
timer event still never returned, and this time on the second period. A
timer expiring inside a period is ruled out as the hazard. That matches
D5 run 1, whose idle periods were capped the same way.

**A gap in the pending check.** The GIC is a GICv3 (`arm,gic-v3`, GICR at
`0x19200000`). CPU0's SGIs and PPIs live in its redistributor, and GICD
word 0 reads as zero. So the pending check never saw them, and the mask,
which starts at word 1, leaves them enabled. With interrupts off, an SGI
pending at entry, such as an IPI CPU0 raised for itself, takes CPU0 out
of WFI at once. The wait then reads `SPM_IRQ_STA` while the program
sleeps. No log has shown `loops` above 0, so an early wake mid-period has
never been seen to survive.

*Inference, not tested:* the two-state idle path leaves such an interrupt
pending more often than the other configurations, and an SPM read in the
middle of a SODI period hangs the bus.

### Request D5g (approved 2026-11-17): check CPU0's SGIs and PPIs

[`0822`](../../patches/proposals/0822-soc-mediatek-mt6797-spm-sleep-check-CPU0-s-SGIs-and-.patch)
(module only) maps CPU0's redistributor, checking that its affinity is 0.
The pending check then also refuses a period when:
- an enabled SGI or PPI is pending there (`GICR_ISPENDR0` &
  `GICR_ISENABLER0`), or
- `ISR_EL1` shows an IRQ pending at CPU0.

Each test period logs both with its timer line. A refusal no longer
prints the previous period's lines. It is compile-checked with `W=1`,
with and without `CONFIG_CPU_IDLE`, and checkpatch `--strict` is quiet.
The new accesses are reads only: GICR `0x19200008` (TYPER) and
`0x19210100`/`0x19210200`.

- **Candidate:** image 137, unchanged, on a fresh boot, and
  `mt6797-spm-sleep.ko` from a Buildbox build of the commit recording this
  stage. No boot2 write.
- **Run:** [`tools/d4.sh`](tools/d4.sh) with `D4_CIRQ_LEVEL=1`, two states
  and no cap, the conditions of D5a and D5b, with pings in C.
- *Hypothesis:* an SGI or PPI pending at entry wakes CPU0 mid-period;
  refusing those periods, two states pass.
- *Unique observation:* the SGI and PPI state at each entry under the
  two-state idle, and whether refusing pending ones prevents the hang.
- **Stops:** as in D4. A reset is recovered as in D5a.

| Outcome | Decision |
| --- | --- |
| Pass, with "interrupt pending" refusals showing SGI or PPI bits | The early wake is the hazard. Keep the check; find which interrupt the two-state idle leaves pending; then D5 again |
| Pass, no such refusals | Not explained by pending interrupts; the timer lines bound the entry state. Repeat once to see whether the pass holds |
| Reset or hang | Not this. The logged entry states before the reset are the next evidence; then check `loops` and the SPM read in the wait |

### D5g: no pending interrupt at entry, reset anyway (custodian, 2026-11-17)

**Approved** by the owner ("Approve D5g").

**Setup.** Fresh boot 69228e22 of image 137, with no SODI module loaded
before. Module 68aa478c (0822, Buildbox `30b591ac`). `d4.sh` 0a9ac3a9 with
`D4_CIRQ_LEVEL=1`, two states and no cap. Wi-Fi power save on, battery
29 %, hands off. C started at 19:19:09 and pings arrived from 19:19:18.

**Observed.** Five periods returned, each ended by CONN2AP through
SYS_CIRQ (r12 `00400020`). They slept 12, 90, 90, 91 and 273 ms.

| Period | Next local event after entry | GICR pending | GICR enabled | ISR_EL1 |
| --- | --- | --- | --- | --- |
| 1 | 4094 us | `01000000` | `408000ff` | 0 |
| 2 | 2089 us | same | same | 0 |
| 3 | 5993 us | same | same | 0 |
| 4 | 4695 us | same | same | 0 |
| 5 | 185 us | same | same | 0 |

The journal ends with period 5's SYS_CIRQ line at 19:19:20.635. Period 6
logged nothing, and the device reset into Gemian with an empty pstore.
The owner recovered to boot2 (boot eac12171, taint 0). There were 0
"interrupt pending" refusals.

**Result.**
- **No CPU-private interrupt was pending at entry.** INTID 24 (PPI 8,
  with no owner in the device tree) was pending at every entry but is not
  enabled. The enabled set is SGIs 0-7, INTID 23 (PPI 7, the PMU node)
  and INTID 30 (the physical timer). ISR_EL1 was 0. The GICR theory is
  ruled out.
- **The tick is kept under two states:** the next local event was always
  0.2-6 ms away (`HZ=100`). The expiring tick itself was ruled out by
  D5f.

Four explanations have now failed: the moved SYS_CIRQ programming, the
pending check, the expiring tick and a pending CPU-private interrupt. The
only firm finding is that a two-state driver resets the device within
2-22 periods under pings, while one state or none passes.

**What is not known: is the hang inside a period or between periods?**
`sodi_once` prints nothing until a period returns, and `d4.sh` logged
only results. So "period 6 logged nothing" fits both:
- a hang inside period 6;
- a hang in CPU0's ordinary idle between periods. With two states, that
  idle runs with the tick kept, about a hundred WFI entries a second right
  after SODI periods.

The two point at different code: the period itself, or the state a
period leaves behind.

### Request D5h (approved 2026-11-17): place the hang

**Approved** by the owner ("Approve D5h").

`d4.sh` (now 4c6e9193) logs a synced `start` line before each period
attempt. No kernel change: the candidate is D5g's module.

- **Run:** as D5g, on a fresh boot with the battery charged first (the
  run itself needs the cable out).
- *Hypothesis:* none favoured. This is a placement measurement.
- *Unique observation:* whether the last line before a reset is a
  `start`, so the hang came inside the period, or a period's result, so it
  came between periods.
- **Stops:** as in D4. A reset is recovered as in D5a.

| Outcome | Decision |
| --- | --- |
| Last line `start` | The period hangs. Next: what the two-state idle changes in the state a period starts from (SPM, MCUCFG, CPU0's idle registers), compared with one state |
| Last line a result | CPU0's idle hangs after SODI periods. Next: what a period leaves behind (`spm_restore`, the WFI enables, SYS_CIRQ) under frequent idle WFI |
| Passes | The synced writes changed the timing. Repeat without them, or move on to one state |

**An alternative to more bisection.** Register SODI as a single state
whose entry falls back to WFI itself. The idle loop then skips the
governor and stops the tick, as in the one-state runs that passed (D5e).
That avoids the unexplained hazard rather than explaining it, so it is
held until the owner chooses it.

**D5h attempt 1: every period refused (custodian, 2026-11-18).** The run was
on boot 360cde5b of image 137 (taint 0), with module 68aa478c and
`d4.sh` 4c6e9193. Cable out at 98 %, Wi-Fi power save on. 180 of 180
pings were answered. Window C made ten attempts, 06:19:32-06:19:40. Each
logged `start`, then got "sodi: MSDC running, refused". The script stopped
on "ten refusals in a row" and restored, with taint 0. No period entered
SODI, so the run did not place the hang.

The synced `start` line wrote to the card just before each attempt, so
the MSDC clock was still on. `d4.sh` logs `start` once per
period, then waits 1 s before the first attempt; retries do not log
again. A refusal's own synced line could refuse the next try in the same
way, so retries also wait 1 s (`d4.sh` 787dbcf3). `mtk-sd`'s autosuspend
delay is 50 ms. The placement reading is unchanged. The module stayed registered
(`state1` usage 0), so the rerun needs a fresh boot.

### D5h: the hang is inside the first period (custodian, 2026-11-18)

**Setup.** Boot 685c02c8 of image 137, taint 0, cable out at 93 %, Wi-Fi
power save on. `d4.sh` 787dbcf3, module 68aa478c (0822), `D4_CIRQ_LEVEL=1`,
two states, no cap. MSDC `autosuspend_delay_ms` read 50 on the device.

**Observed.** The `d4.log` tail:
- 16:40:52: blanked.
- 16:40:53: CPUs online `0`.
- 16:40:58: hash reference taken; window C waiting.
- 16:40:59: pings arriving, then `start`.

Nothing follows: no refusal and no period result. 66 of 180 pings were
answered, and the replies stopped around the first period. The previous
boot's journal ends at 16:40:53.48 with CPU1 going offline. pstore was
empty. The device came up in Gemian, and the owner recovered to boot2
(boot 09980766).

**Result.** This is the first reset in a first period; earlier resets came
after 2-22 periods. After `start` the script idles 1 s, then makes the
attempt. The two-state idle alone was tested twice without a hang:
- D5 run 1's off window: 180 s with the driver registered and SODI
  disabled;
- D5h's first attempt: 12 minutes up, ten refused attempts.

*Inference:* the hang is inside the first SODI period. It needs no
earlier period, so it is not state that a previous period left behind.

**Where this leaves D5.** Over eight runs, a period hangs only while the
two-state driver is registered. It hangs whether or not the tick expires
inside the period, with nothing pending at entry, and on the first period
as well as later ones. One state or no driver passed about 1,900 periods.
The mechanism is still unknown.

Two ways on:
- **One-state SODI:** register SODI as the only state. Its entry function
  chooses SODI or WFI itself, so the idle loop skips the governor as in
  D5e. This targets D5's goal with the configuration that passed. It
  avoids the unexplained hazard without explaining it, and needs its own
  run script (no `state1/disable`).
- **Keep diagnosing:** compare the SPM, MCUCFG and CPU0 state at period
  entry between one and two states. This is open-ended after four
  disproved explanations.

### Request D5i (approved 2026-11-18): a backstop for the period that never returns

**Approved** by the owner ("Approve D5i").

The owner chose to keep diagnosing ("Keep diagnosing"). The open question
is what is stuck when a period does not return:
- the SPM program, still sleeping or blocked mid-sequence;
- CPU0 or its bus, so that CPU0 cannot resume at all.

During a period, nothing but the program can end CPU0's wait: its timers
are masked, and so is every device interrupt at the GIC.

[`0824`](../../patches/proposals/0824-soc-mediatek-mt6797-spm-sleep-bound-the-SODI-wait-wi.patch)
(module only) arms CPU0's physical timer (CNTP, INTID 30, which stays
enabled through the GIC mask) as a backstop for SODI periods. It fires
100 ms after the PCM timer should end the period. If it fires first:
- the wait ends as a period with no return (`returned=0 backstop=1`);
- the existing return path records the program's state, including
  `SPM_SW_DEBUG` (the program's step flag), the PCM PC, `r12` and now
  `PCM_FSM_STA`, then restores and logs it;
- `d4.sh` then stops on "no return from a period".

The kernel's CNTP compare value and control are saved and restored around
the wait. It is compile-checked with `W=1`, with and without
`CONFIG_CPU_IDLE`, and checkpatch `--strict` is quiet. There is no new
SPM, GIC or PMIC write; CNTP is CPU0's own timer.

- **Candidate:** image 137 on a fresh boot, `mt6797-spm-sleep.ko` from a
  Buildbox build of the commit recording this stage. No boot2 write.
- **Run:** as D5h: `d4.sh` 787dbcf3, `D4_CIRQ_LEVEL=1`, two states, no
  cap, pings in C, cable out, hands off.
- *Unique observation:* the state of a period that does not return, or
  that CPU0 cannot resume from one.
- **Stops:** as in D4. A reset is recovered as in D5a.

| Outcome | Decision |
| --- | --- |
| A `backstop=1` line, the station alive | The program stalls. Its step flag and PC name the step. Next: what that step waits for, and what two states change in it |
| A `backstop=1` line, then a reset | The program stalls, and the state it leaves (gated clocks) breaks the station after the wait. The logged state still names the step |
| Reset with no `backstop=1` line | CPU0 does not resume from WFI, or the bus hangs on the first SPM read. The program has stopped CPU0 itself, so look at what the two-state idle changes in CPU0's power or clock control |
| Passes | An armed, unmasked CNTP during the period changes the outcome. That points at the timer masking; compare with D5g's masked runs |

### D5i: no backstop, CPU0 does not resume (custodian, 2026-11-18)

**Setup.** Boot 09980766 of image 137, taint 0, with no SODI module loaded
before. Cable out at 90 %, Wi-Fi power save on. `d4.sh` 787dbcf3. Module
97add2b2 (0824, built from `148b46b8`; that build's image 905f4d8f differs
only by the built-in 0823 and was not booted). `D4_CIRQ_LEVEL=1`, two
states, no cap.

**Observed.**
- Window C: 14 periods returned between 17:00:32 and 17:00:52. All were
  ended by CONN2AP through SYS_CIRQ and slept 15-557 ms. Every one logged
  `backstop=0 fsm=02048490 debug=00000000 pc=00000000`.
- The last `d4.log` line is `start` at 17:00:52. The journal ends with
  period 14's lines, the last at 17:00:52.278.
- No `returned=` line followed, and no `backstop=1` line appeared. The
  device reset into Gemian with an empty pstore. The owner recovered to
  boot2 (boot 6c447b07).

**Result.** CPU0's own timer, armed to fire 100 ms after the period
should have ended, did not get CPU0 to run again. The wait did not just
go on for ever. CPU0 could not resume at all, or hung on its first SPM
read. *Inference:* in SODI the program controls CPU0's cluster clock and
the path that delivers its interrupts. A program that never completes its
wake sequence leaves CPU0 unable to see even its own timer. So the
backstop cannot tell a stalled program from a dead CPU, and CPU0 cannot
observe the failure from inside.

**What reset the device is not recorded.** The station runs `mtk_wdt`
with a 31 s timeout. So a CPU hang alone would be reset by the watchdog
about 31 s later. A power event, such as a rail collapsing, would reset
it sooner and by another path. LK passes the preloader's reason to Gemian
as `boot_reason`: 0 power key, 3 watchdog, 4 watchdog reboot, 6 two-second
reboot ([LK](../../docs/hardware/lk.md)). Gemian booted after every D5
reset, so its kernel log for those boots holds the reason, if Gemian
keeps it.

### Request D5j (approved 2026-11-18): read why the device reset

This is a read-only inspection of Gemian's logs, with no SODI run and no
writes. From the station, mount Gemian's root read-only without journal
replay (`ro,noload`). Then read the kernel command line and boot time of
each Gemian boot that followed a D5 reset: D5 run 1, D5a, D5b, D5f, D5g,
D5h and D5i.

- *Unique observation:* the reset reason, and the time from the last
  mainline journal line to Gemian's start.
- From now on, after any reset into Gemian, the custodian reads
  `/proc/cmdline` there before powering off.

| Outcome | Decision |
| --- | --- |
| `boot_reason=3` or 4, about 31 s after the last line | The watchdog reset a hung CPU. The program stalls with CPU0 clocked off. Next: observe the SPM from outside CPU0, for example a second CPU kept online and polling the PCM registers, which SODI normally forbids, so this needs its own review |
| Another reason, or seconds after the last line | A power or hardware reset, not a hang. P1-P3 and the rails come first, even for test periods |
| No log kept | Record the reason on the next reset, then decide |

### D5j: Gemian kept no reason; resets follow within 28-42 s (custodian, 2026-11-18)

**Approved** by the owner ("Approve D5j"). From boot 6c447b07, the
custodian mounted Gemian's root `ro,noload`, read its logs and unmounted
it.

**Observed.** Gemian keeps no journal. Its rsyslog files hold no kernel
lines, so no command line or `boot_reason` survives for any boot. Only
rsyslogd's start time is kept per boot.

| Run | Last mainline line | Gemian rsyslogd start | Gap |
| --- | --- | --- | --- |
| D5 run 1 | 15:32:58 (on1 start) | 15:33:30 | 32 s |
| D5a | 15:50:30 | 15:51:06 | 36 s |
| D5b | 16:24:56 | 16:25:24 | 28 s |
| D5f | 18:29:09 | 18:29:45 | 36 s |
| D5g | 19:19:20 | 19:19:57 | 37 s |
| D5h | 16:40:59 | 16:41:41 | 42 s |
| D5i | 17:00:52 | 17:01:31 | 39 s |

**Result.** The reset comes within 28-42 s of the hang, Gemian's boot to
rsyslog included. Gemian's boot time from reset to rsyslog has not been
measured. If it is 25-35 s, the reset follows the hang within seconds, or
about 15 s at most. That is quicker than a 31 s watchdog plus a boot.
*Inference, not established:* the reset is not the watchdog catching a
hung CPU. It may be a hardware or power reset that the period itself
triggers. D5k later showed this inference wrong, since Gemian's boot is
longer than assumed. Landing in Gemian shows the bootloader took its default path,
as after a reset rather than a power-key start.

### Request D5k (approved 2026-11-18): bound the reset

Read-only, with no SODI run:
1. **The station's watchdog.** Read `/sys/class/watchdog/watchdog0`
   (`state`, `timeout`) and systemd's `RuntimeWatchdogSec`, to learn
   whether the 31 s watchdog is armed at all.
2. **Gemian's boot time.** The owner starts Gemian once from the power
   key, and the custodian takes the time from the key press to rsyslogd's
   start. This turns the 28-42 s gaps into a bound on the reset delay.
3. **`expdb` (p3).** The vendor's exception store may hold a reset
   record. Read it read-only and analyse it privately. Only the
   conclusion goes into this record.

| Outcome | Decision |
| --- | --- |
| Watchdog not armed, or the bound well under its timeout | A hardware or power reset. Check rails and P1-P3 first; ask the SPM trace session which step can reset the SoC (PCM watchdog, power-down) |
| Watchdog armed, bound near 31 s | A hung CPU, as D5i suggests. Wait for the SPM trace before the next run |
| `expdb` holds a reset record | It decides between the two |

### D5k: a hang, then the hardware watchdog (custodian, 2026-11-18)

**Approved** by the owner ("Approve D5k"). All three parts were
read-only.

**The watchdog.** Linux shows `watchdog0` (`mtk_wdt`) as inactive, with a
31 s timeout, and systemd's `RuntimeWatchdogUSec` is 0. The live TOPRGU
registers, read through `/dev/mem` at `0x10007000`, show the hardware
watchdog running anyway: MODE `0x15` (enabled, external reset,
auto-start) and LENGTH 31 s. The bootloader leaves it running, and
`mtk_wdt` marks it running in hardware. So the watchdog core pings it
from a kernel worker about every 15.5 s. "Inactive" only means that no
userspace program has it open.

**`expdb` (p3).** It holds only the newest boot's preloader and LK log,
which was a power-key start (`boot_reason=0`, RGU status 0). The reset
boots' records were overwritten by the boots that followed.

**Timing, without a new boot.** Each Gemian boot logs its systemd startup
time. Kernel start is that line's time less the total, and the reset is
about 4.6 s (preloader and LK) before the kernel starts. From the last
mainline line to the estimated reset, each within 1-2 s:

| Run | D5 run 1 | D5a | D5b | D5f | D5g | D5h | D5i |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Delay | 20 s | 25 s | 18 s | 24 s | 25 s | 32 s | 27 s |

**Result.** The delays of about 18-32 s fit a 31 s watchdog pinged every
15.5 s. Its last ping comes 0-15.5 s before the hang, so it fires 15.5-31 s
later. *Inference:* a SODI period stops CPU0, or the SoC, silently, and the
hardware watchdog resets the chip later. The SPM does not reset it
quickly. A reset reason was never recorded, so this rests on the timing.

**Next.** Per D5j's table: wait for the instruction-level trace of
`pcm_sodi.bin` from the SPM program session. It covers the CPU and MCUSYS
power-down call, ARM PLL off and restore, the CONN2AP wake path and the
entry handshake, set against D5h and D5i. No device run is proposed
until then. For any future reset, the owner reads
`androidboot.bootreason` on Gemian's screen before powering off, since
`expdb` is overwritten at the next boot. Disabling the hardware watchdog
for a test would leave a hang in place to probe. It changes a safety
mechanism, so it would need its own review.

### The SODI program's trace (SPM program session, 2026-11-18)

The SPM program session traced `pcm_sodi.bin` instruction by instruction
with this stage's flags (`0x00091239`, CG mode). Its private notes are in
the session group's shared notes. The public findings:
- **No CPU or MCUSYS power-down.** With these flags the program never
  powers CPU0 or MCUSYS down.
- **Right after the kick,** gated only by one `r14` wait (`0xd00f0000`,
  condition not decoded), it:
  - pauses the bus masters (`TOP_MAS_PAU_REQ`, held until exit);
  - cuts the ARM clock and every ARMPLL/ARMBPLL stage.
- **No check of CPU0's state** was found before the cut.
- **Returned periods** all show `debug=0`, `PASR_DPD_0=0` and
  `event_reg=0x90100000` (the main-wait value). No resource handler, and
  no DRAM self-refresh, has run on mainline.
- **Vendor steps this module lacks:**
  - the GIC mask before the PCM reset;
  - SMI async DCM;
  - the PMIC power-good force bits;
  - the UART sleep request.

  The shipped flow also enters through PSCI CPU_SUSPEND, which has the
  firmware switch SPARK retention off first. Here CPU0 waits in WFI with
  SPARK retention as left, while its clock and PLL are cut.
- **The SPM latches `PCM_WDT_LATCH_0`-`4` and `DRAMC_DBG_LATCH`**
  (`0x10006190`-`0x1000619c`, `0x100061c4`, `0x100061c8`) across a reset.
  The vendor prints them at boot.

Its leading windows are:
- **W1:** CPU0 still runs module code after the kick when its clock goes,
  or holds a bus transaction across the pause;
- **W2:** CPU0 wakes during the period and reads `SPM_IRQ_STA` through the
  paused bus.

**Against this stage's runs.** W1 alone does not fit D5a. With 0816, a
test period did nothing after the kick but read the counter and enter the
wait, since SYS_CIRQ and the GIC mask came before the PCM reset. It still
hung at period 22. In 1,900 passing periods, `loops` was always 0, so a
returned period never saw a wake before the PCM return (W2). The open
discriminator is still why two states, and not one, make the period hang.

**A candidate link, not tested: CPU0's frequency.** The program cuts and
restores the ARM PLLs. With two states, the governor keeps the tick, which
changes how often schedutil re-evaluates CPU0's cluster, if A53 cpufreq
is loaded. The OPP at entry would then differ between the
configurations. Whether cpufreq was loaded in the D5 runs is not
recorded. `d4.sh` (now c1b58630) logs CPU0's `scaling_cur_freq` on each
`start` line.

**The trace session's follow-up.** The program cannot tell one cpuidle
state from two: same flags, same masks, same path. Bit 18 (segment 2) is
not tested, so `0x00091239` and `0x000d1239` behave alike. No step leaves
CPU0 or MCUSYS unpowered or unclocked without a way back. The entry-time
clock and PLL cut is undone in the exit block before `PCM_RETURN`, and no
unbounded poll remains. So a CPU0 that cannot take its CNTP backstop
means one of two things:
- the PCM stopped before or inside that exit, most plausibly on a blocked
  bus transaction;
- CPU0 was not in WFI when the pause and cut came. The program checks
  CPU0 only through the undecoded `0xd00f0000` wait.

The two-state difference is therefore on the CPU side. Suggested next:
- a two-state run with cpufreq pinned;
- logging the A53 OPP and MCU clock mux at entry, and CPU0's idle status
  at return.

**Its answers on the wait and the PLLs.**
- **The `0xd00f0000` wait** is a hardware condition chosen by its value.
  The code does not say what it waits on. On this path the program reads
  no CPU-state register (`CPU_IDLE_STA`, SPARK's `CPU_RET_STATUS`,
  MCUSYS idle). Returned periods show the main-wait value in `event_reg`,
  so the entry wait completed there. In D5i the backstop could not wake
  CPU0, so the clock cut, which follows that wait, had happened.
- **The program writes no PLL register:** no MCUMIXED, no MCU mux. It
  gates the ARM clock and PLL outputs through power-I/O signals and
  restarts them with fixed waits (`0x300`, `0x300`, `0x104` ticks) tuned
  for the vendor's OPPs. Whatever Linux set restarts.

Two unverified OPP risks follow:
- Linux changing a cluster's rate at entry;
- an A53 OPP that locks slower than the fixed waits. 0656 lets CPU0-3
  reach 1547 MHz.

The cheap discriminator is two-state runs with cpufreq pinned low, then
high.

**Reading the latches after a reset.** Every reset has landed in Gemian,
and the owner has powered off before boot2, which probably clears the
latches. To read them, the owner catches the bootloader after a reset and
selects boot2 without powering off. The custodian then reads
`0x10006190`-`0x1000619c`, `0x100061c4`, `0x100061c8` and the TOPRGU
status read-only, before anything loads the SPM module.

### Request D5l (approved 2026-11-18): two states with CPU0's frequency pinned

**cpufreq was active in every D5 run (custodian).** The station init on
image 137 loads `cpufreq_dt` and `clk_mt6797_mcusys` at each boot.
Policy0 (CPU0-3, CPU0 alone once `d4.sh` offlines the rest) runs
schedutil over 221-1547 MHz in 16 OPPs. Idle, CPU0 sits mostly at
221 MHz but ramps whenever work arrives, such as ping handling and the
script's own log writes. So every period's PLL cut and restore met
whatever OPP schedutil had just chosen. That held in the passing runs
too, so cpufreq alone does not separate pass from fail. With two states,
the kept tick and the governor's idle exits give schedutil more
updates, so periods may start at higher OPPs more often. And the
program restarts the PLL with fixed waits tuned for the vendor's OPPs.

`d4.sh` (now 1fb05241) takes `D4_PIN_KHZ`. It pins policy0 at that OPP
(min = max) after taking CPU1-7 offline, checks `scaling_cur_freq`, and
restores the range at the end or on a stop. Each `start` line already
logs CPU0's frequency.

- **Candidate:** image 137 on a fresh boot (no SODI module loaded),
  module 97add2b2 (0824, D5i's). No boot2 write and no register change:
  the pin is cpufreq's own sysfs.
- **Run:** `d4.sh` 1fb05241 with `D4_CIRQ_LEVEL=1 D4_PIN_KHZ=<policy0's
  lowest OPP, 221 MHz>`, two states, no cap. Wi-Fi power save on, pings
  in C, cable out, hands off. This is the configuration that reset in
  D5a-D5i, within 2-22 periods.
- *Hypothesis:* the hang needs CPU0 at a higher OPP when the program cuts
  and restarts its PLL; pinned at the bottom, two states pass.
- *Unique observation:* two states with the OPP held constant.
- **After a reset:** the owner catches the bootloader and selects boot2
  without powering off. Before any module loads, the custodian reads,
  read-only, the SPM latches (`0x10006190`-`0x1000619c`, `0x100061c4`,
  `0x100061c8`) and the TOPRGU status (`0x10007000` + `0x0c`), and keeps
  them privately. The record gets the conclusion.
- **Stops:** as in D4.

| Outcome | Decision |
| --- | --- |
| Windows A-C pass, about 380 periods | The OPP at entry matters. Next: the same pinned at 1547 MHz. If that hangs, the fixed PLL waits are too short above the vendor's range, and SODI entry pins or lowers CPU0's OPP |
| Reset or hang | Not the OPP. The latches and the RGU status show where the PCM stood and what reset the chip |

### D5l: pinned at 221 MHz, the first period still hangs (custodian, 2026-11-18)

**Approved** by the owner ("Approve D5l").

**Setup.** Boot 6c447b07 of image 137, taint 0, cable out at 83 %, Wi-Fi
power save on. `d4.sh` 1fb05241, module 97add2b2 (0824),
`D4_CIRQ_LEVEL=1 D4_PIN_KHZ=221000`, two states, no cap.

**Observed.**
- 17:22:04: CPUs online `0`.
- 17:22:10: policy0 pinned at 221000 kHz (it was 221000-1547000).
- 17:22:11: hash reference taken.
- 17:22:12: pings arriving, then `start, cpu0 221000 kHz`.

No period returned and no backstop line appeared. The owner caught the
bootloader after the reset and selected boot2 with no Gemian boot and no
power-off (boot b04ba5e5, 17:23:43). Read-only through `/dev/mem`, under a
minute after boot, with no SPM module loaded:

| Register | Value |
| --- | --- |
| `PCM_WDT_LATCH_0` `0x10006190` | `0x04248000` |
| `PCM_WDT_LATCH_1` `0x10006194` | `0x00000000` |
| `PCM_WDT_LATCH_2` `0x10006198` | `0xffffffff` |
| `DRAMC_DBG_LATCH` `0x1000619c` | `0x0000c0ff` |
| `PCM_WDT_LATCH_3` `0x100061c4` | `0x2a00005c` |
| `PCM_WDT_LATCH_4` `0x100061c8` | `0x003dff08` |
| TOPRGU MODE / LENGTH / STA / DEBUG_CTL | `0x15` / `0xf800` / `0` / `0xf3` |

The RGU status of 0 does not rule the watchdog out: the power-key boot
read 0 too, so the bootloader probably clears it. The preloader and LK
ran before the read and may have used the SPM.

**Result.** CPU0's OPP is ruled out: pinned at the lowest point, the first
period still hung. Like D5h, this is a first-period hang. The latches are
with the SPM program session for decoding.

**The latches do not place the PCM yet (SPM program session).** Their
field layout is not documented. Three values match what Gemian printed
on earlier, unrelated boots, so they may be generic or stale:
`LATCH_1` 0, `LATCH_2` `ffffffff`, and the `0x2X00005Y` pattern. `LATCH_0`
`0x04248000` reads as "kicked, not idle", with `SRCVOLTEN` low, only if it shares
`PCM_FSM_STA`'s layout, which is unverified. That would fit a PCM that
never reached its exit block, but cannot tell the entry wait, the clock
cut or the main wait apart. As a `pcm_sodi` PC, `LATCH_3`'s `0x5c` falls in
the 26 MHz sleep handler, which CG mode does not enable. The register
names follow the vendor's MT6797 map: `0x19c` is `DRAMC_DBG_LATCH`,
`0x1c4` and `0x1c8` are `PCM_WDT_LATCH_3` and `4` (corrected
2026-11-18). The session asked the custodian for three
read-only calibration reads: the latches now (live or latched?), after a
clean reboot without the module, and after a cold power-on. The pinned
221 MHz hang also makes a slow PLL restore at high OPPs unlikely.

**Latch calibration (custodian, 2026-11-18).** The owner approved both
reads ("Yes, do both"). All six latches read zero after a clean reboot
(86ddc17d, bootloader caught) and after a cold start (2f6b40ad). After the
D5l hang they were not zero. So they hold state from the hang, and can be
compared across hangs as long as the owner catches the bootloader. The
TOPRGU status read 0 every time, so it says nothing.

### Two readings of the hang latch (SPM program session)

The field layout of `LATCH_0` (`0x04248000`) is undocumented, which leaves
two readings:
- **A:** it uses `PCM_FSM_STA`'s layout: the PCM was kicked and not
  idle, short of the exit, stage unknown.
- **B:** it is a copy of `r13`. Bits 15 (`CONN_APSRC_REQ`), 18
  (`EMI_IDLE`), 21 (`EMI_CLK_OFF_ACK`) and 26 (`INFRA_AUX_IDLE`) are set,
  and `MM_STATE` is clear. The CG-mode APSRC handler would then have run
  its EMI clock-off handshake: DRAM in self-refresh with the EMI clock
  off, for the first time on mainline, while CONN asked for DRAM.

Under B, CPU0's read of `SPM_IRQ_STA` after WFI, or any DRAM access,
would stall even after the backstop woke it, which fits D5i. Why the
APSRC wake handler or the exit never ran would stay open. `LATCH_3` and
`LATCH_4` fit neither `r7` nor `r0`.

### Request D5m (run 2026-11-18): calibrate the latch, A or B

[`tools/d5m.sh`](tools/d5m.sh) (df07a768) loads the module as follows:
- no cpuidle driver (`sodi_idle=0`);
- the PCM timer as the only wake source (`sodi_wake_src=0`).

That is the configuration that has never hung. The script then waits for
the blank, takes CPU1-9 offline and runs three 200 ms periods, logging
the `fsm` and `r13` each left. Then it opens `/dev/watchdog0` and never
pings it, with no period in flight. The kernel stops its own pings once
the device is open, so the hardware watchdog resets the chip after its
31 s. No SPM, GIC or PMIC write is new, but the reset is deliberate.

- **Candidate:** image 137 on a fresh boot, with no SODI module loaded.
  Module 97add2b2 (0824). No boot2 write.
- **After the reset:** the owner catches the bootloader and selects boot2
  without powering off. The custodian reads the six latches read-only
  before any module loads.

| Outcome | Decision |
| --- | --- |
| `LATCH_0` close to the logged `fsm` (about `0x02048490`) | Reading A. The hang latch says only "kicked, not idle" |
| `LATCH_0` close to the logged `r13` (about `0x0006e410`) | Reading B. The hung period reached DRAM self-refresh with the EMI clock off |
| No reset within 120 s | The watchdog did not take over from the kernel's pings. Record and stop |

### D5m: a hang with no cpuidle driver, before the watchdog step (custodian, 2026-11-18)

**Setup.** Image 137, fresh boot 2f6b40ad. Module 97add2b2 (0824),
`d5m.sh` df07a768. `watchdog0` was inactive with a 31 s timeout. At
17:52:27 the module loaded with `sodi_wake_src` `00000000`
(`sodi_cirq_level` on by default), and the cpuidle driver did not
register. The screen was already blank. CPU7-1 went offline between
17:52:27.85 and 17:52:28.33.

**Observed.**
- The log's last line is `17:52:28 online: 0`. There is no
  `sodi cg: returned` line in the journal and no "opening the watchdog".
  The journal ends at 17:52:28.33, at CPU1's offline.
- The device reset. The owner missed the bootloader, so it went to Gemian,
  which reinitialises the latches. On the next boot2 (a3ea3ef3), read
  before any module: all six latches zero, TOPRGU `MODE` `0x15`,
  `STA` `0`.

**Result.**
- The hang came after CPU1 went offline, with only CPU0 online and **no
  cpuidle driver**. `d5m.sh` df07a768 printed the period lines only after
  all three periods, so the hang can be in any of periods 1-3 or the
  sleeps between them (corrected by the custodian).
- **The bisection does not hold as stated.** D5c and D5d passed about 800
  periods without the driver, but a period can hang without it. The driver
  raises the rate under pings; it is not the only way in.
- This run differed from D5c and D5d in three ways:
  - **Wake set:** the PCM timer only. CONN2AP was masked, so a CONN
    request for DRAM during the period could not end it. The program had
    to serve it through its resource handler, the path reading B points
    at. In D5c and D5d every period was ended by CONN2AP.
  - **Settle time:** the first period started about 1 s after the last
    CPU went offline. `d4.sh` waits 5 s, then for the first ping.
  - **Length:** 200 ms periods, not 2000 ms.
- D3's 14 timer-only periods returned, but with the radios unloaded, on
  an earlier image. **D5m was the first timer-only run with Wi-Fi joined**
  (SPM program session). Every Wi-Fi-up pass used the full wake set. CONN's
  APSRC and DDR requests are honoured whatever the wake mask
  (`SPM_SRC2_MASK` `0x08ff009f`), so in D5m they could reach the resource
  handlers with no CONN2AP wake to end the period.
- The two-state hangs (D5a-D5l) did not mask CONN2AP. Their test periods
  ran the same `sodi_once` as D5d, with the same wake set (`0f57c5e5`),
  level recording and CIRQ clone; only CPU0's idle between periods
  differed. In D5a, 21 periods ended on CONN2AP through SYS_CIRQ before
  the one that hung. Whether CONN2AP failed to end the hung periods is not
  known: no wake was recorded for them.
- *Inference:* the first difference fits reading B best. It does not
  separate A from B, and the latches were lost.

| Question | State |
| --- | --- |
| A or B | Open; the calibration needs a setup whose periods return, and a caught bootloader |
| Driver necessary for a hang | No |
| Resource path | Still the leading candidate; D5n tests it directly |

**Decision.** D5n is unchanged: it removes the resource events under the
configuration that hangs most often. D5m is not repeated as it stands. The
SPM program session proposed three variants, all pending owner approval:
1. D5m with `sodi_no_event=1` (`D5M_NO_EVENT=1`). Under the resource-path
   reading it should pass, and its returned periods then calibrate the
   latch with a deliberate reset as planned.
2. D5m with the Wi-Fi and CONSYS modules unloaded first. It should pass.
3. Each period's line logged and synced right after it.

[`tools/d5m.sh`](tools/d5m.sh) now does 3 in every run, takes
`D5M_NO_EVENT=1` for 1, and logs which Wi-Fi modules are loaded, so 2
needs only the modules removed before the run. Both 1 and D5n need the
0825 module from a Buildbox build of a521f913d or later.

### D5m with no resource events: period 1 still hangs (custodian, 2026-11-18)

**Approved** by the owner ("D5m, events off").

**Setup.** Image 137, boot a3ea3ef3, with no SODI module loaded before
the run. Module 74a05731 (0825), loaded with `sodi_idle=0
sodi_wake_src=0 sodi_no_event=1`. The script was the custodian's variant
e44e65bd of `d5m.sh` df07a768: it adds the `sodi_no_event` check and
logs each period's line, synced, right after the period. Wi-Fi was joined
with power save on, cable out, battery 75 %, and pings from the laptop
from 19:47:04. The script did not log the Wi-Fi modules.

**Observed.**
- The log ends at `19:46:53 online: 0`. No period line was written.
- The device reset at about 19:47:29. The owner caught the bootloader
  straight from the reset; the next boot, 34034169, started at 19:47:34.
- Read-only before any module loaded:

| Register | After D5l | After this run |
| --- | --- | --- |
| `PCM_WDT_LATCH_0` `0x190` | `0x04248000` | `0x04248000` |
| `PCM_WDT_LATCH_1` `0x194` | `0x00000000` | `0xfd8d3239` |
| `PCM_WDT_LATCH_2` `0x198` | `0xffffffff` | `0xffffffff` |
| `DRAMC_DBG_LATCH` `0x19c` | `0x0000c0ff` | `0x00003d3d` |
| `PCM_WDT_LATCH_3` `0x1c4` | `0x2a00005c` | `0x2b00005e` |
| `PCM_WDT_LATCH_4` `0x1c8` | `0x003dff08` | `0x00398008` |

TOPRGU `MODE` was `0x15` and `STA` `0`.

**Result.**
- **The resource handlers are not needed for the hang.** With
  `SODI_NO_EVENT` set, the first period hung, with no cpuidle driver and
  the timer as the only wake source. D5n's premise is weakened.
- `LATCH_0` is identical to D5l's. Under reading B it would mean the APSRC
  handler's EMI clock-off, which `SODI_NO_EVENT` should prevent.
  *Inference:* reading A ("kicked, not idle") is the likelier one, or the
  latch does not depend on the handler path. The SPM program session has
  the values.

**A confound in the bisection.** Every pass on image 137 (D5c, D5d and
D5e) came from one boot, b8d5a469, whose first SODI module was the 0806
build (9cf7b397). Every run whose boot started with an 0816 or later
module hung:

| Boot | First module on the boot | Outcome |
| --- | --- | --- |
| c9ee1c96 (D5 run 1) | 0816 | reset |
| e40ab1c4 (D5a) | 0816 | reset at period 22 |
| ea40fba9 (D5b) | 0817 | reset at period 15 |
| b8d5a469 (D5c, D5d, D5e) | **0806**, then 0819 and 0820 | about 1,900 periods passed |
| a4b787c7, 69228e22, 685c02c8, 09980766, 6c447b07 (D5f-D5l) | 0821-0824 | reset, D5h and D5l in period 1 |
| 2f6b40ad (D5m) | 0824 | hang in periods 1-3 |
| a3ea3ef3 (this run) | 0825 | hang in period 1 |

*Inference:* the driver registration may not be the cause. Two other
explanations fit all runs:
- the 0806 module's load path leaves state that 0816 and later modules
  need but do not set themselves;
- boot b8d5a469 was good by chance.

### Request D5o (approved 2026-11-18): the 0806 module first, on a fresh boot

- **Candidate:** image 137 on a fresh boot, module 9cf7b397 (0806), the
  D5c run. No build, no new write (D4b's list), no boot2 write.
- **Run:** `d4.sh` with `D4_CIRQ_LEVEL=1`, exactly as D5c. If the windows
  pass, a second `d4.sh` run on the same boot takes module 74a05731
  (0825) with two states and no cap, the D5l setup. `d4.sh` unloads the
  0806 module first; it has no cpuidle driver, so it is not pinned.
- *Hypothesis:* passes need the 0806 module loaded first on the boot.
- *Unique observation:* whether 0806 passes on a second fresh boot, and
  whether a later module passes after it.
- **Stops:** as in D4. After a reset, the owner catches the bootloader and
  the custodian reads the latches.

| Outcome | Decision |
| --- | --- |
| 0806 passes, then 0825 passes | 0806's load leaves state the later modules need. Next: diff the two modules' load and program-load paths |
| 0806 passes, 0825 hangs | The cause is in 0816's period changes, whatever the driver. Next: diff 0806's and 0816's `sodi_once` and program load |
| 0806 hangs | Passes depend on the boot, not the module. Next: compare what the bootloader leaves in the SPM between boots |

**The two modules' load paths are the same (SPM program session).** The
session reverse-applied 0816-0824 and compared the whole file with 0806.
Program load, the PCM reset and `PCM_CON0`/`PCM_CON1` setup, the event
vectors, the flag and mailbox writes and the restore list are identical.
Neither module writes `PCM_WDT_VAL` or `SPM_SW_RSV_5`, so both run on
whatever the boot left there. With no cpuidle driver, 0817 and later
differ from 0806 only in:
- level recording on by default (`d4.sh` sets it anyway);
- the read-only pending and GICR checks before the period;
- from 0824, the CNTP backstop.

0816 and 0817 hung without the backstop. *Inference:* row 3 of D5o
(passes depend on the boot) is the likelier one. The boot hands over
state no module writes before the first period. In the hang,
`SPM_SW_RSV_5` read `0xffffffff`, which sets `r6` bits 23 and 24
together.

**Added to D5o, D5p and every later run:** before any module loads, the
custodian reads read-only `PCM_CON1` (`0x01c`), `PCM_WDT_VAL` (`0x034`)
and `SPM_SW_FLAG` to `SPM_SW_RSV_5` (`0x600`-`0x61c`), and records them
with the boot. A boot that passes can then be compared with one that
hangs.

### D5o: 0806 passes, then 0825 hangs on the same boot (custodian, 2026-11-18)

**Approved** by the owner.

**Setup.** Image 137, boot 34034169, reached straight from the D5m
no-event reset with the bootloader caught. No module was loaded before
the run. Radio modules e989cbc1, 0f3a9a9e and ea4e60fe, as in D5c. Wi-Fi
power save on, cable out. `d4.sh` 04633082 with `D4_CIRQ_LEVEL=1`. The
pre-module SPM read was not yet in place for this boot.

**Observed.**
- **Part 1**, module 9cf7b397 (0806), 19:51:14-19:57:23: "C 60 early, 60
  by packet; A 20 early; B key 0". Window B got no key because the request
  reached the owner too late. Every period read `r12` `00400020`, conn2ap
  through SYS_CIRQ. There were no refusals and taint stayed 0.
- **Part 2**, module 74a05731 (0825), two states, no cap, no pin, after
  `d4.sh` unloaded 0806:
  - the SODI idle state was registered;
  - blank at 19:59:22, `online: 0` at 19:59:23, window C from 19:59:29
    with pings;
  - 22 periods returned normally (`r12` `00400020`). The last, at
    20:00:04.357, left `fsm` `02048490`, `r13` `0006e410` and `event`
    `90100000`;
  - the next period, started at 20:00:04.36, never returned, and the
    journal ends there;
  - the next boot, 58ab0d70, started at 20:01:03, about 50 s after the
    last line.
- Read before any module on 58ab0d70, at uptime 0:

| Register | Value |
| --- | --- |
| Latches `0x190`/`194`/`198`/`19c`/`1c4`/`1c8` | `04248000` / `0` / `ffffffff` / `0000c0ff` / `2a00005c` / `003dff08`, identical to D5l's |
| `PCM_CON1` `0x01c` | `0x00006c00`: watchdog enable and wake mode clear |
| `PCM_WDT_VAL` `0x034` | `0xffffffff` |
| `0x600`-`0x614` (`SPM_SW_FLAG` onwards) | `0` |
| `0x618`, `0x61c` (`SPM_SW_RSV_5`) | `0xffffffff`, `0xffffffff` |
| TOPRGU `MODE` / `STA` | `0x15` / `0` |

These were read after a reset, so they may be reset or boot-loader values,
not the hung state.

**Result.** This is D5o's second row.
- A boot straight from a hang ran 0806 cleanly. Then, on the same boot,
  0825 with the two-state driver hung at period 23. **The boot alone does
  not decide.** The difference is the module and its configuration.
- The SPM program session found no load-path difference between the
  modules. So the two-state cpuidle driver remains the factor that raises
  the hang rate. D5m showed that a timer-only period can hang without it.
- **Two latch signatures:**

| Hang | `LATCH_0` | `LATCH_1` | `DRAMC_DBG_LATCH` |
| --- | --- | --- | --- |
| Two-state driver (D5l, D5o part 2) | `04248000` | `0` | `0000c0ff` |
| No driver, timer only, no events (D5m) | `04248000` | `fd8d3239` | `00003d3d` |

- *Inference:* the PCM watchdog was off at boot (`PCM_CON1` bits 8 and 9
  clear). Unless a program exit turns it on, the resets come from the
  TOPRGU watchdog once the kernel's pings stop, not from the PCM's.

**D5p now covers both setups.** `d4.sh` takes `D4_PCM_WDT=1` and names
wake bit 13. The Buildbox build of eb5f46ea already contains 0826.

### The latches after the no-event hang (SPM program session)

The SPM program session decoded the latches from the D5m no-event hang. Its
reference is the vendor's CPU-DVFS SPM fallback, which fills the latch slots
with `PCM_FSM_STA`, `r6` and `SPM_SW_RSV_5`:
- `LATCH_0` `0x04248000` is `PCM_FSM_STA`: the PCM is kicked and not idle
  (**reading A**). Reading B is dropped.
- `LATCH_1` `0xfd8d3239` matches `r6` exactly as the program builds it near
  its start: `SPM_SW_FLAG` (`0x000d3239`), bits 23 and 24 from
  `SPM_SW_RSV_5`, and `0xfd000000`. No handler had run.
- `LATCH_2` `0xffffffff` is probably `SPM_SW_RSV_5`.
- Every program exit sets the PCM watchdog to `0xf0000` (30 s) and kicks
  it. The module keeps `PCM_CON1` bits 8 and 9 (watchdog enable, wake mode)
  as it finds them. *Inference:* if the boot loader left the watchdog
  enabled in reset mode, a period stuck for 30 s resets the chip and fills
  these latches. That fits the 30-36 s from hang to reset.

### Request D5p (approved 2026-11-18): the PCM watchdog ends a stuck period

[`0826`](../../patches/proposals/0826-soc-mediatek-mt6797-spm-sleep-optionally-end-stuck-t.patch)
(module only) adds `sodi_pcm_wdt` (default off). For test periods it sets
`PCM_WDT_VAL` (`0x034`) to the PCM timer plus 65,536 ticks (2 s), sets
`PCM_CON1` watchdog enable and wake mode before the kick, and adds wake
source bit 13 (`PCM_WDT_WAKEUP_B`). After the period it restores the
watchdog bits and value it found. The vendor's driver clears the enable
after each period. The new writes are `PCM_WDT_VAL`, and a new value for
the approved `PCM_CON1` and `SPM_WAKEUP_EVENT_MASK` writes. It is
compile-checked with `W=1`, with and without `CONFIG_CPU_IDLE`, and
checkpatch `--strict` is quiet.

[`tools/d5m.sh`](tools/d5m.sh) takes `D5M_PCM_WDT=1`, and `D5M_RESET=0`
to skip the deliberate reset. It now logs each period's full return line.

- **Candidate:** image 137 on a fresh boot, with `mt6797-spm-sleep.ko`
  from the Buildbox build of eb5f46ea (0826 included). No boot2 write.
- **Run, part 1:** `d5m.sh` with `D5M_PCM_WDT=1 D5M_RESET=0`: no cpuidle
  driver, timer-only wake, Wi-Fi joined with power save on, pings from the
  laptop, cable out. This setup hung in periods 1-3 twice (D5m, D5m
  no-event).
- **Run, part 2, same boot:** `d4.sh` with `D4_CIRQ_LEVEL=1 D4_PCM_WDT=1`,
  two states, no cap, pings in C: the D5o part 2 setup. It runs last
  because the registered driver pins the module.
- *Hypothesis:* the PCM is stuck short of its exit while CPU0 waits, and
  the PCM watchdog in wake mode can drive it to the exit.
- *Unique observation:* the full return record of a period that would
  have hung: `r12`, `fsm`, `r13`, `event`, `debug`, `timer_out`.
- **Stops:** as in D5m. After a reset, the owner catches the bootloader
  and the custodian reads the latches.

| Outcome | Decision |
| --- | --- |
| A period returns with `r12` bit 13 | The PCM was stuck in a wait that a wake ends. Next: place the wait from `debug`, `event` and `r13` with the SPM program session |
| Three periods return without bit 13 | No hang this time. Rerun once; if it passes again, compare with D5o |
| Reset, latches as before | The PCM ignores even its watchdog wake: it is stuck in a loop that ignores wakes, or its counter (and the SPM's 32 kHz clock) has stalled. Next: the SPM's own clock and the 26 MHz path |

**0826 checked against the program (SPM program session).**
- The vendor's register map gives `PCM_WDT_VAL` at `0x034` and
  `PCM_CON1` bits 5, 8 and 9 as timer enable, watchdog enable and
  watchdog wake mode. The program's own watchdog store goes to
  `0x10006034`.
- The program never writes `PCM_CON1`. Its only `PCM_WDT_VAL` store is in
  the exit sequence, after the wake is taken, so 0826's value holds for
  the whole period.
- The program's own wake masks include bit 13. After the main wait, any
  wake with `r12` bit 10 clear goes straight to the exit, which restores
  the ARM PLLs and raises the return interrupt. So a watchdog wake should
  give an ordinary returned period with `r12` bit 13 set.
- The watchdog is assumed to count on the PCM timer's base, as the
  vendor's driver assumes. If the hang is that counter stopping, the
  watchdog cannot fire either, hence the two causes in the last row.

D5o and D5p are independent: D5o needs no build, so it can run while D5p
is built.

### D5p: the PCM watchdog does not end a stuck period (custodian, 2026-11-18)

**Approved** by the owner.

**Pre-module read** on power-on boot 348d87b7, at uptime 0:
- latches all 0;
- `PCM_CON1` `0x00006c00`;
- `PCM_WDT_VAL` `0xffffffff`;
- `0x600`-`0x614` 0;
- `0x618` and `0x61c` `0xffffffff`;
- TOPRGU `MODE` `0x15`, `STA` `0`.

These match the reads after the D5o reset, so they are boot defaults. The
PCM watchdog is off at boot.

**Part 1**, boot 348d87b7. Module 06c21076 (Buildbox eb5f46ea, 0826),
`d5m.sh` e41dd3c9 with `D5M_PCM_WDT=1 D5M_RESET=0`, loaded with
`sodi_idle=0 sodi_wake_src=0 sodi_pcm_wdt=1`. The Wi-Fi modules were
`mt6797_consys` and `mt6797_wlan_core`, with power save on, pings and the
cable out.
- Blank at 20:32:54, then `online: 0`.
- Period 1 returned on the PCM timer: `r12` `00000001`, `fsm` `02048490`,
  `r13` `00066400`, `timer_out` `0000199c`, `event` `90100000`.
- Period 2 started at 20:32:55 and never returned. The journal ends with
  period 1's lines.
- The next boot, 0aae3786, started at 20:35:22, about 2 min 20 s later.
  The owner confirms that no key was pressed.
- The boot loader's log for that boot reads a power-key boot, boot reason
  0, RGU status 0, and no watchdog reboot.
- The latches read all zero at uptime 0. After every earlier TOPRGU reset
  they held values.

**Part 2**, boot 0aae3786. The same module, `d4.sh` 2b63da9b with
`D4_CIRQ_LEVEL=1 D4_PCM_WDT=1`, two states, no cap.
- Blank at 20:37:42, `online: 0` at 20:37:43. Pings arrived at 20:37:50,
  with 60 periods planned.
- No period line was logged, so it hung in the first period of C. The
  laptop got 24 of 240 replies.
- The owner missed the catch, so the device went to Gemian, which clears
  the latches. The next boot2 was 3e7b6268, at 20:42:38.

**Result.**
- **No period returned through the PCM watchdog** (`r12` bit 13) in
  either setup. Per D5p's table, the PCM either ignores its watchdog wake
  (a loop) or its counter has stopped.
- Part 1's reset was not the usual one. It came 2 min 20 s after the hang
  instead of about 30 s, it cleared the latches, and the boot loader saw
  a power-key boot with no watchdog.
- *Inference, not tested:* the TOPRGU watchdog did not fire this time.
  Something stopped both watchdog counters, and something outside them
  (perhaps the PMIC) restarted the device later. A stopped clock, rather
  than a loop, fits both watchdogs failing to fire.
- Arming the PCM watchdog may itself have changed the reset path. That
  cannot be told from one run.

**The SPM program session's reading of D5p.**
- The PCM watchdog is off at power-on, so the earlier resets with latches
  were TOPRGU resets. The PCM-watchdog explanation is withdrawn.
- Every wait in the SODI entry and main path accepts wakes, and the
  program's masks include bit 13. A watchdog wake that did not end the
  period means **the PCM had stopped advancing**: a bus transaction that
  never completed, or a stopped clock or counter.
- Two-state hangs (`r6` 0): a stall before `0x402`, which fits the IM
  fetch; 0827's poll tests it.
- Timer-only hangs: a stall after `0x411`, at a register access or a
  clock. Part 1's late reset with no TOPRGU latches fits a bus-level
  freeze.
- The session proposes an observer: keep CPU8 online (MP2 is outside
  `WFI_EN` and keeps its PLL) and poll the PCM's state registers from a
  register-only loop during a period. *Not prepared:* it changes the SODI
  conditions, and its samples would need a store that survives the reset.
  It is held until D5q says whether the two-state stall is the IM fetch.
  If it returns, it should sample every 10 ms or so:
  - `PCM_TIMER_OUT` (`0x150`): elapsed timer ticks. Advancing means the
    32 kHz time base is alive.
  - `PCM_EVENT_REG_STA` (`0x14c`): the current wait. `0x90100000` is the
    main wait, `0xd00f0000` the pre-pause wait, `0x2000xxxx` a delay.
  - `PCM_REG15_DATA` (`0x13c`): the return address, which names the
    subroutine but cannot show a stall.
  - `PCM_REG7_DATA` (`0x11c`): bits 11 and 14, the VCORE and 26 MHz
    requests.

  If the reads themselves stall, the SPM's bus side is frozen, not just
  the PCM.

**D5q is changed:** it runs without `D4_PCM_WDT`. The watchdog gave no
wake, and it may have changed the reset path and cost the latches.

### r0 and r7 drive the 26 MHz and VCORE requests (SPM program session)

- **The program cannot stop 26 MHz or 32 kHz in CG mode.**
  - Its clock cut (`0x590`-`0x597`) switches off only the ARM PLLs and the
    ARM and SMI clocks.
  - 26 MHz goes off only in event handler 1, the 26 MHz sleep handler. CG
    mode does not enable it, and D5n's `r6` confirms it never ran.
  - Nothing in the program touches 32 kHz.
- **The hardware path differs from the vendor's.**
  - At the kick, `PCM_PWR_IO_EN` `0x81` hands control to `r0` and `r7`.
    From then on, `r7` drives the 26 MHz request (`SRCCLKENO_0`) and the
    VCORE request (`SRCVOLTEN`, bit 11), and `r0` drives the 26 MHz
    oscillator and bits 26-31 the DRAM PHY.
  - `r0` and `r7` start from `SPM_POWER_ON_VAL0/1`, which the module copies
    as found. The vendor's driver writes `POWER_ON_VAL1` `0x00015820` at
    boot and keeps `POWER_ON_VAL0` equal to the last `r0`. The module does
    neither.
- **One FSM bit separates every hang from every return.**
  `EXT_SRCVOLTEN_STA` (`PCM_FSM_STA` bit 25) is 0 in both hang latches
  (`0x04248000`) and 1 in every returned period (`0x02048490`). Under
  `r7` control that is `r7` bit 11. *Inference:* at the hang the VCORE
  request was down, which would freeze far more than the PCM. The latch
  is taken at the TOPRGU reset, not at the hang.

[`0828`](../../patches/proposals/0828-soc-mediatek-mt6797-spm-sleep-log-r0-r7-and-their-st.patch)
(module only, read only) logs `POWER_ON_VAL0/1` at each entry and `r0`
and `r7` after each return. `d4.sh` logs the line. It is compile-checked
with `W=1`, with and without `CONFIG_CPU_IDLE`, and checkpatch
`--strict` is quiet. The pre-module read on each fresh boot adds
`0x004`, `0x008` (`POWER_ON_VAL0/1`) and `0x00c` (`SPM_CLK_CON`).

*Next if the values differ from the vendor's:* write `POWER_ON_VAL1`
`0x00015820` at load and refresh `POWER_ON_VAL0` from the last `r0`, as
the vendor does. That is a new write and needs its own request.

**First read, and the lead demoted (custodian, SPM program session).**
Boot 3e7b6268, which came through Gemian and a warm restart, read at 6 min
uptime with no module loaded:

| Register | Value |
| --- | --- |
| `POWER_ON_VAL0` | `0x00000000` |
| `POWER_ON_VAL1` | `0x00015830` |
| `SPM_CLK_CON` | `0x00008000` |

- `POWER_ON_VAL1` has bits 11 (`SRCVOLTEN`) and 14 (`SRCCLKENO_0`) set,
  so `r7` starts each period with the VCORE and 26 MHz requests up.
- These values are static and applied at every kick, so they cannot by
  themselves split passes from hangs.
- `r0` `0` drives the DRAM PHY controls, but 800 passing periods show
  that is harmless at the kick. Mainline switches no DRAM or VCORE state.
- *Inference:* the hang latches' clear `SRCVOLTEN` is better explained by
  the latch being taken during the TOPRGU reset, after `r7` lost control.
  That is unverified.

0828's logging stays. No `POWER_ON_VAL` write unless the logs show these
values changing near a hang.

### Request D5q (approved 2026-11-18): the IM fetch before the kick

**The two-state hangs may stop before the program's first words (SPM
program session).** In both two-state hangs (D5l, D5o part 2) `LATCH_1`
read `0`. If `LATCH_1` is `r6`, the PCM never ran word `0x402`. Words
`0x400`-`0x402` set `r1` and load `SPM_SW_FLAG`, which cannot stall.
*Inference:* the stall is in the IM fetch, the DMA that copies the
program from the DRAM carveout into the SPM's IM.
- The module starts that fetch and kicks the PCM soon after, without
  waiting, and it fetches again on every period.
- The vendor's driver fetches again only when `PCM_IM_PTR` or
  `PCM_IM_LEN` change (or for a newer program session). Otherwise it sets
  `PCM_CON1` bit 0 (`IM_SLAVE`) and reuses the resident program. All three
  vendor programs are session 2, so steady SODI idle never fetches again.
- The vendor's driver does not poll for the fetch either, so the missing
  wait alone is not the difference.

The no-driver hang (`LATCH_1` `fd8d3239`) ran past `0x411`, so it is
probably a different stall. D5p's part 1 still covers it.

[`0827`](../../patches/proposals/0827-soc-mediatek-mt6797-spm-sleep-optionally-wait-for-or.patch)
(module only) adds two test-period options, both off by default:
- `sodi_im_wait`: just before the PCM kick, poll `PCM_FSM_STA` for up to
  200 us until its IM state (bits 9:7) is back at its idle value. If it
  is not, refuse the period before the kick and restore the SPM. This only
  reads.
- `sodi_im_reuse`: when the same program returned from IM last time, set
  `IM_SLAVE` instead of fetching, as the vendor does. The first period and
  any period after a failure still fetch. This is a new value for the
  approved `PCM_CON1` write.

A log line gives the FSM after the IM kick and before the PCM kick, the
polls taken, and whether IM was reused. The encoding of "fetch done" is
unknown, so the first returned periods give the reference. It is
compile-checked with `W=1`, with and without `CONFIG_CPU_IDLE`, and
checkpatch `--strict` is quiet. `d4.sh` takes `D4_IM_WAIT=1` and
`D4_IM_REUSE=1`, logs the IM line for each period, and stops cleanly on a
stuck fetch.

- **Candidate:** image 137, with `mt6797-spm-sleep.ko` from a Buildbox
  build of the commit recording this stage (it has 0826 and 0827). No
  boot2 write.
- **Run 1, fresh boot:** `d4.sh` with `D4_CIRQ_LEVEL=1 D4_IM_WAIT=1`
  (no `D4_PCM_WDT`, after D5p), two states, no cap, pings in C: the setup that hung at
  period 23 in D5o.
- **Run 2, another fresh boot** (the driver pins the module): the same,
  plus `D4_IM_REUSE=1`.
- The pre-module SPM read on each boot. After a reset, the owner catches
  the bootloader and the custodian reads the latches.

| Outcome | Decision |
| --- | --- |
| Run 1 stops on a stuck fetch, device alive | The IM fetch is where the two-state periods stall. Run 2 tests the vendor's reuse as the fix |
| Run 1 hangs with every logged fetch settled | Not the fetch, or the settle test reads the wrong bits. Compare the logged FSM values with the SPM program session |
| Run 2 passes all windows | The vendor's reuse avoids the hang. Next: make it the default and repeat on a quiet link |

**0827 checked against the vendor's reset, fetch and kick (SPM program
session).**
- IM state 1 means "IM idle", and it already reads 1 after a reset. After
  an IM kick, 1 therefore means the fetch has finished. The first normal
  periods' "after the IM kick" value should differ from 1.
- Both hang latches have IM state 0, including D5m's, whose program ran
  past `0x411`. So 0 is at least "PCM running", and the latch cannot show
  a fetch in progress; 0827's poll can.
- `PCM_CON1` bit 0 is `IM_SLAVE`. The vendor toggles `IM_KICK` in either
  case, as 0827 does. The `PCM_CON1` re-init after each reset clears bit 0,
  so a later fetch is not left in slave mode.
- The vendor resets the PCM before every scenario and then reuses IM, so
  IM survives the software reset. The programs are non-replace (IM
  non-replace is set in `0x5c48`).

Two more differences from the vendor's reset, not addressed by 0827:
- The vendor never resets a PCM mid-program. If `r1` reads 1 and `r15` is
  not 0, it raises `SPM_CPU_WAKEUP_EVENT` and waits up to 5 ms. The module
  refuses a period when `r1` reads 1 at entry, so it does not reset a
  running program either.
- At each reset the vendor copies `r6` bits 24:23 (the VCORE state) into
  `SPM_SW_RSV_5`. The module never writes it, so the program sees
  `0xffffffff`, with both bits set.

The module is a Buildbox build of the commit recording 0828, with 0826,
0827 and 0828, so each period also logs `r0`, `r7` and their start
values.

### D5q run 1: the first fetch reads unsettled; refused, no hang (custodian, 2026-11-18)

**Approved** by the owner.

**Setup.** Boot 3e7b6268 (through Gemian, then a warm boot2). Module
0d25e7fe, a Buildbox build of e224824b (0826-0828). `d4.sh` 589a5738 with
`D4_CIRQ_LEVEL=1 D4_IM_WAIT=1`, two states, no cap, no PCM watchdog.
Wi-Fi power save on, radio modules e989cbc1, 0f3a9a9e and ea4e60fe, cable
out, battery 71 %.

**Observed.** The first period of window C, the first fetch since the
module loaded:
- `im fsm 02c48910>02448910 after 200 us, reused=0 stuck=1`;
- `io val0=00000000 val1=00015830` (`r0` and `r7` 0, since the PCM
  was not kicked).

`d4.sh` stopped: "the IM fetch did not settle; period refused before
the kick". CPUs came back, taint stayed 0, and the device stayed alive.

**Result: not yet evidence of a stuck fetch.**
- The IM state (bits 9:7) read 2 right after the IM kick and 2 again
  200 us later. No returned period has logged the IM state before its
  PCM kick.
- So 2 may be the normal "fetched, waiting for the kick" state, not a
  stuck one. 0827's test assumed "back to 1".
- If 2 is normal, every period with `sodi_im_wait` refuses. Run 2 as
  planned would refuse its first period too, since the first period
  always fetches.
- One more change from IM idle (`0x48490`): bit 9 is clear and bit 11
  set, in both reads.

**The SPM program session's reading.** Both reads also hold the FSM's
master state at 2 (idle 1), and only `EXT_SRCCLKEN` (bit 23) changed.
*Inference:* the SPM's bus read for the IM fetch was still outstanding,
which would explain the `r6` 0 hangs. The encodings are undocumented, so
a reference from passing periods decides it.

**The IM state is one-hot (SPM program session).** The vendor's CPU-DVFS
SPM driver uses the same PCM block, with the same `PCM_FSM_STA` layout. It
names bits 7, 8 and 9 IM empty, filling and ready, and after its IM kick
it spins until IM ready. Read that way:
- idle `0x48490` is "PC idle, IM empty";
- run 1's `0x02c48910` and `0x02448910` are "PC idle, IM filling", still
  filling 200 us after the kick. **Run 1's stuck fetch was real.**
- 0827's test waited for IM empty, which never returns after an IM kick.
  So as written it would have refused every period, good fetch or not.
  `0829` (added in 2677aae7a)
  waits for bit 9 (IM ready) instead. It is compile-checked with `W=1`,
  and checkpatch `--strict` is quiet.
- Bit 11 is the master state moving from its idle bit (10) to the next.
  It is unnamed, and is perhaps "master transaction issued".
- That driver also wraps its IM fetch in an EMI hardware semaphore, held
  from before the IM kick until IM ready. *Inference:* the vendor saw IM
  fetches from DRAM conflict with another EMI user.

The reference below stays, now with a module built from the commit
recording 0829. Part 1 times a good fetch, and part 2 checks the
corrected test on the passing setup. Its table reads with "IM ready" for
"1/1" and "filling" for "2/2".

**Next: an IM reference** (proposed, needs the owner's approval). On one
fresh boot, the same module, with no cpuidle driver, so `d4.sh` can
unload it between parts. This is the D5d setup that passed 377 periods.
1. `d4.sh` with `D4_CIRQ_LEVEL=1 D4_IDLE=0`, no `D4_IM_WAIT`. Each
   returned period logs its IM state right after the IM kick and just
   before the PCM kick. This part runs first, so no earlier refused fetch
   can be outstanding.
2. The same with `D4_IM_WAIT=1`.

| Part 1, before the PCM kick | Part 2 | Decision |
| --- | --- | --- |
| IM and master state 1 | periods return, few polls | A settled fetch reads 1/1. Run 1 caught a real stuck fetch in the two-state setup. Next: the fixes below |
| 2/2 | stops on a "stuck" fetch | 2/2 is normal at that point, or fetches are slow everywhere. 0827's test cannot separate them; run 1 shows nothing |
| 2/2 | periods return | Fetches finish within 200 us. Run 1's fetch was blocked |

Fixes held until the reference, from the SPM program session:
- set `SPM_LOCK_INFRA_DCM` before the IM kick, so the infra bus clock
  stays up for the SPM's read (one line);
- fetch once while the system is active and reuse afterwards, as the
  vendor does. 0827's reuse still fetches on the first period after
  loading, which is where run 1 stuck;
- after a stuck fetch, stop SODI for the boot, since the PCM reset may not
  cancel an outstanding bus read.

### IM reference part 1: passing periods show "IM filling" before the kick (custodian, 2026-11-18)

**Approved** by the owner.

**Setup.** Power-on boot d5994d6b. Pre-module read:
- latches 0;
- `POWER_ON_VAL0` 0, `POWER_ON_VAL1` `00015830`;
- `SPM_CLK_CON` `00008000`, `PCM_CON1` `00006c00`;
- `PCM_WDT_VAL` `ffffffff`, `SPM_SW_FLAG` 0, `SPM_SW_RSV_5` `ffffffff`.

Module 0d25e7fe (0826-0828), `d4.sh` 589a5738 with `D4_CIRQ_LEVEL=1
D4_IDLE=0`, no `D4_IM_WAIT`. Wi-Fi up, pings in C.

**Observed.** "C 60 early, 60 by packet; A 20 early; B key 0", with no
refusals. The run finished at 21:12:07. B saw no key because it was
pressed after the window. Across all 230 logged periods:
- `im fsm` was `02c48910>02448910` 72 times and `02c48910>02c48910` 158
  times. Bit 9 (IM ready) never appeared.
- The `io` line was identical every time: `val0=00000000
  val1=00015830 r0=00000000 r7=01415830`.

**Result.**
- **D5q run 1's "stuck" fetch was not a stall.** Its values are exactly
  those of periods that return. In this SPM, IM filling with no IM ready is
  the normal state just before the PCM kick. The fetch evidently completes
  after the kick, or IM ready is not shown here.
- The vendor's CPU-DVFS spin does not carry over. 0827's wait option
  cannot separate a good fetch from a bad one by these bits, in either form.
  `0829` (added in 2677aae7a)
  would refuse every period. It is **withdrawn** from both series and was
  never loaded. 0827's `sodi_im_wait` stays off.
- Returned periods leave `r7` `01415830`: bits 11 (`SRCVOLTEN`) and 14
  (`SRCCLKENO_0`) set, as `POWER_ON_VAL1` seeds them.
- The two-state hangs still stop before `0x402` by the latch reading. That
  the IM fetch causes them is now neither shown nor ruled out.

**Next: D5q run 2, revised** (needs the owner's approval). Fresh boot,
module 0d25e7fe, `d4.sh` with `D4_CIRQ_LEVEL=1 D4_IM_REUSE=1`, no
`D4_IM_WAIT`, two states, pings in C. Period 1 fetches. Later periods reuse
IM when the previous one returned, and each logs `reused=1`.

| Outcome | Decision |
| --- | --- |
| Passes all windows | Fetching on every period is implicated. Next: a fetch at load, so no SODI period fetches |
| Hangs after periods logged `reused=1` | The fetch is not the cause. Next: the CPU8 observer |
| Hangs in period 1, before any reuse | No answer. Rerun once |

**Run 2 checked (SPM program session).**
- The vendor's CPU-DVFS SPM reaches IM ready with no PCM kick. Our SPM
  uses IM sleep DVS and non-replace IM, which are the vendor SPM's own
  settings for these programs.
- *Inference:* one of those keeps IM filling until the PCM runs, so a
  fetch at load without a kick may not be possible. Run 2 does not need
  one. Reuse after a period that returned runs IM content that ran to
  completion, in the same mode the vendor's reuse uses.
- A two-state hang after `reused=1` periods, with `LATCH_1` 0 again, would
  rule out the DRAM fetch. The stall would then be in the kick or the first
  instruction. The owner's catch of the bootloader matters for this run.

### D5q run 2: a hang after 17 reused periods (custodian, 2026-11-18)

**Approved** by the owner.

**Setup.** Power-on boot d16289fb. The pre-module read matched
d5994d6b's. Module 0d25e7fe, `d4.sh` 589a5738 with `D4_CIRQ_LEVEL=1
D4_IM_REUSE=1`, no `D4_IM_WAIT`, two states, no cap. Wi-Fi power save on,
cable out, battery 69 %.

**Observed.** Window C started at 21:20:02 with pings, and 18 periods
returned:
- Period 1 fetched: `im fsm 02c48910>02c48910 reused=0`.
- The 17 periods with `reused=1` logged `02c48610>02c48610` 12 times and
  `02c48610>02448610` 5 times. **In IM slave mode the IM reads ready**
  (bit 9).
- The `io` line stayed `val1 00015830`, `r7 01415830`.
- Returned periods alternated between two kinds:
  - CONN2AP through SYS_CIRQ (`r12` `00400020`), slept 60-176 ms;
  - `r12` `00400000` (SYS_CIRQ alone), slept 0 ms, with `timer_out` 0,
    `event` `900f0000` and every SYS_CIRQ status word zero.
- The last return, at 21:20:29.257, was of the second kind, with
  `reused=1`. Period 19 never returned. The journal ends at 21:20:29.26.
- After the reset the first start did not complete and restarted by
  itself. The second came up on boot2: boot 45dfa658, with the kernel
  starting at 21:21:28.
- Latches read at uptime 0, before any module: `04248000`, `0`,
  `ffffffff`, `0000c0ff`, `2a00005c`, `003dff08`. They are identical to
  D5l and D5o part 2.

**Result.**
- **The per-period IM fetch is cleared.** Periods ran from a resident IM
  that read ready, and the two-state hang came anyway, with the same latch
  signature (`r6` 0).
- By the SPM program session's reading, the stall is in the PCM kick or
  the first instruction, not in the fetch.
- 0827's reuse option stays available but is not a fix.
- *Not yet explained:* the zero-length SYS_CIRQ returns, which show a
  SYS_CIRQ wake with no line recorded. Their `event` `900f0000` differs
  from the main wait's `90100000`. The period just before the hang was one
  of them. In D5o part 2 the last return before the hang was an ordinary
  CONN2AP return, so this is not a rule.

**Next, before any new code:** the station image carries pstore with a
RAM console. After a reset caught to boot2, the console of the hung boot
may hold kernel lines journald never wrote. The custodian checks it
read-only on 45dfa658.

**pstore after D5q run 2 (custodian).** systemd-pstore had archived a
single `console-ramoops-0` (286 bytes, three warning lines up to 28 s of
uptime). It is the console of the failed first start after the reset,
which ran at least 28 s before dying, not of the hung boot. There was no
`dmesg-ramoops` record. The station DT reserves ramoops with a 64 KiB
console. The console keeps only messages at the console log level, so the
module's `dev_info` lines never reach it.
- **From D5r on**, the run sets the console log level to 8
  (`/proc/sys/kernel/printk`) before loading the module. The RAM console
  then holds the module's lines up to the hang, and they can be read after
  a reset caught to boot2.
- *Not yet explained:* after the D5p part 1 and D5q run 2 resets, the next
  start died on its own. This time it happened with no SODI module loaded.

### Request D5r (approved 2026-11-18): r7 from the vendor's value

**The SPM program session's reading of D5q run 2.**
- The reused periods read `02c48610`: PC idle, IM ready, master idle. The
  program was resident, yet the hung kick never wrote `r6`. **The PCM never
  started executing:** its clock failed, or the kick did not take.
- The zero-length returns are the program's early abort at `0x434`-`0x436`.
  A wake was already pending (a SYS_CIRQ level line from the pings), so the
  program went straight to its exit, before the bus pause or clock cut.
  That is a legitimate path, and a hang does not need one before it.
- `LATCH_0` `04248000` has the PCM kick bit and no PC, IM or master bit, in
  every hang. It is probably taken mid-reset, so it reads only as
  "kicked".

**The candidate.** Every boot so far reads `POWER_ON_VAL1` `0x00015830`.
The vendor's driver writes `0x00015820`. The difference is bit 4
(`R7_PCM_CK_SEL0`), so `r7` starts with both PCM clock-select bits set.
The vendor never uses that combination, and the program's 26 MHz handlers
always set exactly one.

*Inference:* if the clock selects drive the PCM's clock mux at the kick,
two at once could leave it unclocked, depending on timing. That would
give "kicked, never ran `0x402`". Against it:
- the 230 periods of the IM reference passed with the same value;
- the FSM's clock-select status reads 1 even in the hang latch.

So it can only be a timing-dependent cause.

[`0830`](../../patches/proposals/0830-soc-mediatek-mt6797-spm-sleep-optionally-start-r7-fr.patch)
(module only) adds `sodi_r7_vendor` (default off). For test periods, `r7`
starts from `0x00015820`. Only the value of the approved
`PCM_REG_DATA_INI` write changes. `POWER_ON_VAL1` itself is not written,
so the `io` line's `val1` still shows the boot value, and `r7` after
each return shows the effect. It is compile-checked with `W=1`, with and
without `CONFIG_CPU_IDLE`, and checkpatch `--strict` is quiet. `d4.sh`
takes `D4_R7_VENDOR=1`.

- **Candidate:** image 137 on a fresh boot, with `mt6797-spm-sleep.ko`
  from a Buildbox build of the commit recording 0831 (see below). No boot2
  write.
- **Run:** `d4.sh` with `D4_CIRQ_LEVEL=1 D4_IM_REUSE=1 D4_R7_VENDOR=1`,
  two states, no cap, pings in C: D5q run 2 with one change. The
  pre-module read, console log level 8 before the load, and after a reset
  the latches and the archived RAM console.
- *Hypothesis:* `r7` starting with both clock selects set is why some
  kicks never start the PCM.

| Outcome | Decision |
| --- | --- |
| All windows pass (C, A, B), `r7` after returns with bit 4 clear | The double clock select is implicated. Repeat once, then make the vendor value the default |
| Hang, same latches | Not the clock select. Next: the event vectors below, then the CPU8 observer, or the one-state driver as the practical route |

**A second candidate: event vectors left enabled (SPM program session).**
- The program enables its event vectors in `PCM_EVENT_VECTOR_EN`
  (`0x080`): first 0, then `0xc0c0` in CG mode (vectors 6, 7, 14 and 15).
  No exit path clears it, and neither the vendor's driver nor this module
  writes it.
- If the PCM reset does not clear it, every kick after a normal period
  starts with the vectors enabled. An event pending at the kick could then
  vector into a handler before `0x402`, leaving `r6` 0. Vector 15 is the
  APSRC sleep handler: EMI clock off, then DRAM self-refresh. Entered at
  the kick, while CPU0 still needs DRAM, that would freeze everything.
- *Inference.* Unknown: whether vectors preempt straight-line code or only
  fire in waits. The first wait is at `0x42e`, after `0x402`.
- The zero-length returns stop at the pre-pause wait (`0x42e`) and exit
  before `0x47a`, where the program writes the enable.

[`0831`](../../patches/proposals/0831-soc-mediatek-mt6797-spm-sleep-log-PCM_EVENT_VECTOR_E.patch)
(module only) logs `PCM_EVENT_VECTOR_EN` after the PCM reset and just
before the kick (`vec_en=A>B` on the `io` line). This only reads. It also
adds `sodi_vec_clear` (default off), which writes 0 there before the kick
in test periods, as the program does first. That is a new register write,
not used in D5r. It is compile-checked with `W=1`, with and without
`CONFIG_CPU_IDLE`, and checkpatch `--strict` is quiet. `d4.sh` takes
`D4_VEC_CLEAR=1`.

**D5r's build** is the commit recording 0831 (0826-0828, 0830 and 0831),
so D5r also reads the vector enable:
- if it reads 0 at every kick, this candidate is dead;
- if it reads `0xc0c0`, a run with `D4_VEC_CLEAR=1` follows. That run
  needs the owner's approval for the new write.

**Weight (SPM program session): low for the two-state hang.**
- `0x080` is confirmed by the vendor's register map and by the program's
  own stores.
- The handlers overwrite registers the main path holds live across
  straight-line code. So the program is written as if vectors fire only
  in its waits.
- There is no wait between `0x400` and `0x402`, so a stale enable could
  not act before `r6` is written.
- *Inference:* it could still stall at the first wait (`0x42e`), with `r6`
  already written. That is the no-driver signature (`LATCH_1`
  `fd8d3239`), not the two-state one. The log stays.

### D5r: the vendor's r7 does not stop the hang (custodian, 2026-11-18)

**Approved** by the owner ("Approve D5r").

**Setup.** Power-on boot e87e134c. Module 45a0e7e1 (Buildbox 7895e88c:
0826-0828, 0830 and 0831). `d4.sh` 1407eb33 with `D4_CIRQ_LEVEL=1
D4_IM_REUSE=1 D4_R7_VENDOR=1`, no `D4_VEC_CLEAR`, two states, no cap.
Console log level 8. Wi-Fi power save on, cable out, battery 67 %. The
pre-module read matched earlier power-on boots.

**Observed.**
- **C:** 60 of 60 ended early, 30 by CONN2AP or the WLAN line.
- **A:** 20 of 20 ended early.
- **B:** started at 21:46:14 and ran 8 periods, with no key pressed.
- **88 periods returned**, then one hung.
- `r7` read `01415820` in every period, so bit 4 was clear and the change
  took.
- `vec_en` read `00000000>00000000` in period 1 (fetched), and
  `0000c0c0>0000c0c0` in every reused period. **The vector enable survives
  the PCM reset**, so every later kick starts with `0xc0c0`, in the
  periods that return too.
- The last return, at 21:46:28, was an early abort: `r12` `00400000`,
  slept 0, `timer_out` 0, SYS_CIRQ status all zero. The next period's
  start line was logged at 21:46:28, and that period never returned.
- The next boot, 66a4a99a, started its kernel at 21:47:34.
- Latches at uptime 0: `04248000`, `0`, `ffffffff`, `0000c0ff`,
  `2a00005c`, `003dff08`, identical to D5l, D5o and D5q run 2.
- **The RAM console reached the hang.** `console-ramoops-0` (64 KiB, kept
  privately) ends at [411.132], with the early-abort period's SYS_CIRQ
  line. Nothing was printed after the hung period was entered: no RCU
  stall, Oops or watchdog line.

**Result.**
- **The double clock select is not the cause.** With the vendor's `r7`, a
  two-state period still hung with the same latch signature. It came
  later than usual (88 periods), but one run does not show a rate change.
- **The vector enable stays at `0xc0c0` across resets**, in passing periods
  as in hung ones. Alone it does not cause the hang, which fits the
  session's low weight.
- In both reuse runs (D5q run 2, D5r) the hung period directly followed an
  early abort. In D5o (no reuse) it followed a normal return, and D5h and
  D5l hung in period 1. So an early abort is not needed.
  - The no-reuse passing runs (D5c-D5e, the IM reference) logged only
    CONN2AP returns. D5a's and D5o's reported returns were CONN2AP too.
  - *Inference:* early aborts may come with IM reuse.
- **CPU0 never prints again once the hung period is entered**, even to the
  RAM console. So the kick, or the first moments after it, freeze CPU0
  itself, not only the PCM.

**Counts and the SPM program session's reading.**
- Early aborts were 44 of 88 returns in D5r and 9 of 18 in D5q run 2.
  They **strictly alternate** with normal periods, but only with IM reuse:
  D5o part 2 (22), the IM reference (230) and D5o part 1 logged none.
  - So half of the reuse runs' periods did not sleep at all. D5r had 44
    real periods, not 88.
  - A hang must follow an abort in that pattern, so "a hang after an
    abort" says nothing.
  - Within those runs both kinds were reused periods (D5r: 44 aborts and
    43 normal among 87 reused), so the alternation is not fetch against
    reuse.
  - *Inference (SPM program session, from the 0824 source):*
    - `spm_cirq_enable()` acknowledges every SYS_CIRQ status word, and
      since 0817 it runs after the kick. `spm_cirq_disable()` flushes but
      never acknowledges.
    - A normal period ends on a recorded line, and that status stays set.
    - With resident code, the next kick reaches the pre-pause check
      (`0x434`) within microseconds, before the enable acknowledges. The
      stale status wakes SYS_CIRQ, and the period aborts.
    - That abort's enable then clears everything, which is why aborts read
      status all zero. So the next period is normal again.
    - A fetching kick reaches `0x434` more slowly, after the enable.
  - *Proposed fix, not prepared:* acknowledge every status word in
    `spm_cirq_disable()` after the flush, as the vendor's exit flushes,
    then disables. It would make reuse usable, but it does not touch the
    `r6` 0 hang.
- Aborts also came in window B, with no pings. That supports a SYS_CIRQ
  pulse while SYS_CIRQ is configured after the kick.
- The vector enable is live through the pre-pause wait (`0x42e`), until
  the program clears it at `0x47a`. That does not match the program's
  intent, and `sodi_vec_clear` is cheap. It cannot explain the two-state
  hangs (no wait before `0x402`), or D5n, whose period 1 had it at 0.
- The session has no program-side explanation left for "kicked, resident
  code, never runs `0x402`". It names three candidates outside the program:
  - the kick write itself;
  - `PCM_CK_EN` in `PCM_CON0`;
  - the SPM's APB side.

  Only an observer during a hung period, or a kick sequence equivalent to
  the vendor's, can separate them.

**Where this leaves D5.** Tested and cleared as the cause of the two-state
hang:
- the moved CIRQ order;
- the pending check;
- the tick inside the period;
- a pending SGI or PPI;
- the OPP;
- resource events (for the no-driver hang);
- the PCM watchdog;
- the per-period IM fetch;
- the double clock select.

What is left points at the instant of the kick, in a way the SPM's
registers do not record. Two ways on, for the owner to choose:
1. **The CPU8 observer.** Keep CPU8 online (MP2 is outside `WFI_EN`) and
   sample `PCM_TIMER_OUT`, `PCM_EVENT_REG_STA`, `PCM_REG15_DATA`,
   `PCM_REG7_DATA` and `PCM_FSM_STA` every 10 ms during each period,
   printing at console level. The RAM console now survives the reset, so
   the samples from the hung period would be read afterwards. It changes
   the SODI conditions (a second CPU online), so the hang may not
   reproduce. Its own reads stalling would itself show a frozen bus. This
   is a module change of moderate size.
2. **The practical route.** The WFI-only driver passed (D5e). Build SODI
   idle so that the governor's two-state path, the configuration that
   raises the hang rate, is not used, and measure whether real idle
   entries hang. This works around the hang without explaining it.

### Request D5s (run 2026-11-19): the CPU8 observer

The owner chose option 1, the CPU8 observer.

[`0832`](../../patches/proposals/0832-soc-mediatek-mt6797-spm-sleep-acknowledge-SYS_CIRQ-w.patch)
(module only) is the fix for the early aborts above. `spm_cirq_disable()`
now writes `~0` to every `CIRQ_ACK` word right after the flush, so no
status is left for the next kick. That is a new write at a new time, and
it applies to every SODI period, with no parameter.

[`0833`](../../patches/proposals/0833-soc-mediatek-mt6797-spm-sleep-optionally-observe-the.patch)
(module only) adds `sodi_obs` (default off, load time only):
- **What may stay online.** CPU8 may stay online beside CPU0. Test and idle
  periods then accept CPU0 and CPU8 as the only online CPUs. A period
  leaves `MP2_AXI_CONFIG` alone, so the A72 cluster keeps taking snoops
  while CPU8 runs; that is one approved write left out. The A72 cluster
  is outside the program's `WFI_EN` already.
- **Sampling.** A timer pinned to CPU8 samples every 10 ms while a period
  is in flight. These are reads only:
  - `PCM_FSM_STA`, `PCM_EVENT_REG_STA` (`0x14c`), `PCM_REG15_DATA`
    (`0x13c`), `PCM_REG6_DATA` (`0x118`), `PCM_REG7_DATA`,
    `PCM_TIMER_OUT` (`0x150`) and `PCM_CON0`;
  - readbacks of what the period wrote: `PCM_CON1`, `PCM_PWR_IO_EN` and
    `SPM_CLK_CON`;
  - `SPM_POWER_ON_VAL1`, as a known constant;
  - the time since the kick, and how long the reads took.

  The SPM program session asked for the reads after the first five, and
  for the read timing.
- **No printing during a period.** The samples stay in memory, so CPU8
  sends CPU0 no interrupt during a period. A pending interrupt would keep
  CPU0's wait loop from sleeping. The first period sampled 20 times or
  more is kept as a reference.
- **A stuck period.** If a period is still in flight 500 ms after its end,
  CPU0 is taken as stuck. CPU8 then prints, at console level:
  - `sodi obs: period N in flight 500 ms after its end; CPU0 is stuck`;
  - the reference (`sodi obs ref`, every fourth sample);
  - the stuck period (`sodi obs stuck`);
  - one `sodi obs late` sample every 200 ms for 3 s.

  Each sample line holds the time since the kick in µs, the read time in
  ns, then `FSM`, `EVENT_REG_STA`, `r15`, `r6`, `r7`, `TIMER_OUT` and
  `CON0`. The readbacks and the constant come on a line of their own for
  the first and last sample of each group. That keeps the output under
  the RAM console's 64 KiB.

  It then restarts the system with `emergency_restart()`, the same reset
  path as `reboot`. A period that does end after all is logged
  (`ended after all`), and sampling goes on.

Both patches are compile-checked with `W=1`, with and without
`CONFIG_CPU_IDLE`, and checkpatch `--strict` is quiet (both lack a
sign-off, like the other proposals).

[`d4.sh`](tools/d4.sh) takes `D4_OBS=1`, which needs `D4_NO_EVENT=1`:
- With no resource event the APSRC handler cannot put DRAM in
  self-refresh while CPU8 runs. Hangs occurred without resource events
  (D5m).
- CPU8 is left online. After the other CPUs go offline, every task, IRQ
  and unbound workqueue is moved to CPU0 (`taskset`, `smp_affinity`, the
  workqueue cpumask), and moved back at the end. Only CPU8's per-CPU
  threads and the observer stay there.

**Changed conditions.** All of these differ from D5r:
- a second CPU online, with its cluster powered and snooped, and the
  A72 module and policy loaded (CPU8 pinned at its lowest frequency);
- the whole load on CPU0;
- no resource events;
- the SYS_CIRQ acknowledgement;
- the IM fetch every period (no `D4_IM_REUSE`);
- `r7` from the boot value.

So the hang may not reproduce. `r15` is read as "advancing or not", not as
an exact PC, until the reference period shows it moving.

**Bringing CPU8 up.** On image 137 the A72s are online only with
`mt6797-a72.ko`, and nothing loads it unless `/mnt/data/a72-at-boot`
exists.
- The init loads it before the CPU frequency modules, as it must: the
  cluster clock driver keeps the words it finds at its probe, and bringing
  the A72s up changes some of them
  ([all-cores T9](../2026-11-01-mt6797-all-cores/README.md)). A hand load
  after those modules would break that order.
- So D5s boots with `a72-at-boot` set, the default the owner chose on
  2026-11-17, and `cpufreq-at-boot` as it is now. That gives `online 0-9`,
  with A72 policies when cpufreq loads.
- The observer is not moved to CPU7: the A53 clusters are in `WFI_EN`, and
  the program's clock cut stops their ARM PLLs in a passing period, while
  that cluster would still be taking snoops.
- `d4.sh` takes CPU9 offline with the others. When CPU8 has a cpufreq
  policy, it pins it at its lowest frequency (min = max) for the run, so
  no A72 rail changes during a period, and restores it at the end.

- **Candidate:** image 137, booted fresh with `a72-at-boot` set (and
  `cpufreq-at-boot` unchanged), with `mt6797-spm-sleep.ko` from a
  Buildbox build of the commit recording this stage (0826-0828,
  0830-0833). No boot2 write. The init status line must show
  `a72=loaded cpus=0-9`.
- **Run:** `d4.sh` with `D4_CIRQ_LEVEL=1 D4_NO_EVENT=1 D4_OBS=1`, two
  states, no cap, pings in C, cable out, hands off. Console log level 8
  before the load.
- **After a restart or reset:**
  - the owner catches the bootloader and selects boot2;
  - read the latches as after D5r;
  - archive the RAM console and `d4.log`;
  - the `sodi obs` lines are the result.
- *Hypothesis:* after a hung kick, the PCM either does not run at all
  (its timer and state frozen from the first sample), or runs and waits
  somewhere the registers name.
- *Unique observation:* the PCM's live state during a hung period, read
  by a CPU that keeps running.

| Outcome | Decision |
| --- | --- |
| Stuck period printed; `FSM` bit 21 (`PCM_KICK`) 0, PC idle, `CON0` sane | The kick never registered: the kick write or its ordering |
| `PCM_KICK` 1, `CON0` bit 2 (`PCM_CK_EN`) 1, `r6` 0, `r15` not advancing, `TIMER_OUT` advancing | The core is not clocked or is stalled, while the timer runs |
| As above, with `TIMER_OUT` frozen too | The PCM's whole clock domain stopped. *Inference:* the SPM program session assumes the timer and the core share a clock |
| `CON0` bit 2 0, or bit 15 (`PCM_SW_RESET`) 1 | The clock enable was lost, or the reset is stuck |
| Long read times, a wrong `val1`, or readbacks that do not match | The SPM's APB side, not the PCM |
| `r6` nonzero in the stuck period | The timer-only signature (past `0x411`); the stuck `ev` and `r15` name the wait |
| No `sodi obs` lines from the hung period; TOPRGU reset with latches | CPU8 stopped too: a system-level freeze. Next: an observer that does not read the SPM, to tell its reads from the freeze |
| All windows pass | One of the changed conditions avoids the hang. Next: the same run without `D4_OBS`, which separates the observer from the acknowledgement and `SODI_NO_EVENT` |

### D5s: period 2 hung, and the reset lost the latches and the RAM console (custodian, 2026-11-19)

**Setup.** Power-on boot 2d63e1b4, image 137, `a72-at-boot` set, init
status `a72=loaded cpus=0-9`. Module 3c331721 (Buildbox 515ff190e,
0826-0828 and 0830-0833). `d4.sh` 2d24d45c (blob 1ebcec80) with
`D4_CIRQ_LEVEL=1 D4_NO_EVENT=1 D4_OBS=1`, two states, no cap. Console log
level 8, cable out, battery 97 %.

**Observed.**
- The module loaded at 16:28:10 and logged `sodi obs: sampling on CPU8`.
  The screen blanked at 16:28:12.
- At 16:28:13 CPU8's policy was pinned at 338000 kHz, 8 tasks stayed on
  CPU8 (its per-CPU threads), and `online` read `0,8`.
- Window C started at 16:28:19 with pings arriving.
- Period 1 returned: `r12` `00400020`, slept 110 ms, woken by CONN2AP
  through SYS_CIRQ (word 7 `00080000`), IM `fsm` `02c48910` (fill),
  `r7` `01415830`.
- Period 2 started at 16:28:21. `d4.log` ends there. The journal ends at
  16:28:21.189 with period 2's `sodi cirq` line, with no `sodi obs` line.
- The device reset on its own; the owner pressed no key. The owner caught
  the bootloader and selected boot2. The next kernel (boot 3374f06c)
  started at 16:29:25, 64 s after period 2 began.
- Read before any module: **all six latches zero**. VAL1 `0x15830`,
  `SPM_CLK_CON` `0x8000`, `PCM_CON1` `0x6c00`, `0x618`/`0x61c`
  `ffffffff`: power-on defaults. TOPRGU `MODE` `0x15`, `STA` 0.
- **pstore was empty**: no RAM console.

**Result.**
- The hang came with CPU8 online and observing, on the second period.
- The reset was not the kind D5r saw. A TOPRGU watchdog reset after a hung
  period, with the bootloader caught, has kept the latch signature (D5l,
  D5o, D5q run 2, D5r) and the RAM console (D5r). Here both were lost.
- *Inference:* two readings fit, and 64 s does not separate them.
  - **(a) The observer's restart.** After a stuck period the module called
    `emergency_restart()` about 4 s after the period's start. A software
    restart clears the latches ([latch calibration](#d5l-pinned-at-221-mhz-the-first-period-still-hangs-custodian-2026-11-18):
    zero after a clean reboot). It kept the RAM console after an idle
    `reboot` and a panic
    ([pstore T1](../2026-11-03-gemini-pstore-retention/README.md#t1-result)),
    but that has not been tested with a period hung, and DRAM may not be
    in a state that survives it then.
  - **(b) A power-level reset.** Something tied to CPU8 being up (the A72
    rail, or CPU8 itself freezing) caused a cold reset, which clears both
    (a key restart lost the RAM in the pstore experiment).
- No observer line exists, so none of the decision table's rows can be
  read.
- *Inference (SPM program session):* all-zero latches differ from every
  watchdog hang, which always latched `LATCH_0` `0x04248000`. That fits a
  reset that bypassed or preceded the SPM's capture. An empty RAM console
  fits a reset that did not take the preloader's DDR-reserve path. The
  retained firmware does not show what PSCI `SYSTEM_RESET` does on this
  ATF.

### Request D5t (run 2026-11-19): the observer leaves the reset to the watchdog

**0834** (`let the watchdog reset after a stuck observed period`) removes
the observer's `emergency_restart()`. After the stuck period and its 3 s
tail, CPU8 logs `sodi obs: stopped; the watchdog resets the system` and
stops its timer. CPU0 stays stuck, so nothing pings the TOPRGU watchdog
and it resets the chip about 31 s later, as in D5r. Compile-checked with
`W=1` with and without `CONFIG_CPU_IDLE`; no other change.

`d4.sh` (blob fb2b0c34) adds one check with `D4_OBS=1`: after the move to
CPU0, the `watchdogd` thread must be allowed on CPU0 only. Otherwise CPU8
could keep pinging the watchdog and a stuck system would never reset; the
script then stops before any period.

- **Candidate:** as D5s: image 137 booted fresh with `a72-at-boot` set,
  init status `a72=loaded cpus=0-9`, with `mt6797-spm-sleep.ko` from a
  Buildbox build of the commit recording this stage (0826-0828,
  0830-0834). No boot2 write.
- **Run:** as D5s: `d4.sh` with `D4_CIRQ_LEVEL=1 D4_NO_EVENT=1
  D4_OBS=1`, two states, no cap, pings in C, cable out, hands off,
  console log level 8.
- **After the reset:** the owner catches the bootloader and selects boot2;
  read the latches before any module; archive the RAM console and
  `d4.log`.
- *Hypothesis:* D5s's reset was the observer's software restart (reading
  a).
- *Unique observation:* a stuck observed period whose only reset is the
  TOPRGU watchdog's.

| Outcome | Decision |
| --- | --- |
| Latches kept, RAM console with `sodi obs` lines | Reading (a). Read the lines with D5s's table |
| Latches kept, RAM console without `sodi obs` lines | CPU8 stopped too: D5s's table's system-level freeze row |
| Latches kept, RAM console empty | The watchdog reset did not keep DRAM this time. Next: the observer writes its lines somewhere other than DRAM (the console UART or USB) before it stops |
| Latches zero and RAM console empty again | Reading (b): a cold reset with CPU8 up. Next: the same run with CPU8 online but no observer (`D4_OBS` without `sodi_obs`), to tell the A72 cluster from the observer's reads |
| No reset within 120 s of the hang | `watchdogd` or something else pinged it. The owner resets with the keys; record and stop |
| All windows pass | As in D5s's table |

### D5t: every window passed with the observer (custodian, 2026-11-19)

**Setup.** Power-on boot 16c56d74, image 137, init status
`a72=loaded cpus=0-9`; the latches read zero before the module. Module
d452e299 (Buildbox 5758d1571, 0826-0828 and 0830-0834). `d4.sh` 29ec1867
(blob fb2b0c34) with `D4_CIRQ_LEVEL=1 D4_NO_EVENT=1 D4_OBS=1`, two states,
no cap. Console log level 8, cable out, battery 91 %.

**Observed.**
- CPU8 pinned at 338000 kHz (was 338000-1495000), `watchdogd` confined
  to CPU0, 11 tasks left on CPU8.
- **C:** 60 of 60 ended early, all by CONN2AP or the WLAN line, with 95
  echo requests in the window. Hash equal.
- **A:** 20 of 20 ended early.
- **B:** the owner pressed one key. The script logged that the screen lit
  with no key wake seen, then no key wake within the window. The keypad
  IRQ count went from 0 to 1.
- No refusal, CPUs back to 0-9, taint 0. No hang and no reset.
- **Early aborts nearly gone:** of 176 periods, 175 read `r12` `00400020`.
  One read `00400000`, the early-abort signature, which alternated with
  normal periods before 0832 (D5q run 2, D5r).
- IM `fsm`: 110 periods read `02c48910>02c48910`, 66 `02c48910>02448910`
  (bit 23 clears after the fetch).
- The observer logged only `sodi obs: sampling on CPU8`: no period
  stuck.
- CPU8's policy was restored to 338000-1131000 kHz, not 1495000.

**Result.**
- **0832's SYS_CIRQ acknowledgement works:** the stale-status early
  aborts dropped from about half of all periods to 1 of 176.
- D5s hung in period 2 under the same conditions apart from the restart
  path, which acts only after a hang. So the hang is intermittent under
  the observer setup. One passing run does not separate "a changed
  condition avoids the hang" from chance.
- *Inference:* the restored maximum reads the policy's effective limit.
  `d4.sh` writes back the saved 1495000; another cap on CPU8's policy (a
  board or battery limiter) probably lowered the effective maximum during
  the run. Not checked on the device.

### Request D5t run 2 (run 2026-11-19): the same run again

The measurement D5t was built for, a stuck period seen by the observer, has
not happened yet. Run 2 repeats D5t with the same module (d452e299) and
`d4.sh` blob, from a fresh boot with `a72-at-boot` set. No code change.

- After a hang: as in D5t's request and table.
- If run 2 passes too, run it once more. If three observer runs in a row
  pass (about 530 periods), run D5n's no-event setup without `D4_OBS` and
  with CPU8 offline. That separates the observer setup (CPU8 up) from 0832
  and `SODI_NO_EVENT`.

### D5t run 2: period 2 hung again; the reset went to Gemian (custodian, 2026-11-19)

**Approved** by the owner ("Approve run 2").

**Setup.** Power-on boot 6a4fdc32, image 137, init status
`a72=loaded cpus=0-9`; the latches read zero before the module. Module
d452e299, `d4.sh` 29ec1867 (blob fb2b0c34), as D5t. Console log level 8,
cable out, battery 88 %.

**Observed.**
- Blank at 18:10:22. CPU8 pinned at 338000 kHz at 18:10:23; its maximum
  already read 1001000, lowered by the battery cap. `watchdogd` confined
  to CPU0, 9 tasks left on CPU8.
- Window C started at 18:10:30 with pings arriving.
- Period 1 returned: `r12` `00400020`, slept 247 ms, CONN2AP through
  SYS_CIRQ (word 7 `00080000`), IM `02c48910>02c48910`, `r7` `01415830`.
- Period 2 started at 18:10:32. `d4.log` ends there. The journal ends at
  18:10:31.82 with period 2's `sodi cirq` line; its only observer line is
  `sampling on CPU8`. 71 of 240 pings were answered.
- At 18:13:28 the device was unreachable. The owner missed the bootloader
  and found Gemian, so the latches and the RAM console were lost. When the
  reset came is not known.

**Result.**
- The second hang under the observer setup, again in period 2 right after
  one returned period. The journal cannot hold observer lines from a stuck
  period, since its writer runs on the stuck CPU0; only the RAM console can.
- **Period 2 is not specific to CPU8.** Earlier hangs with CPU8 offline came
  in period 1 (D5h, D5l, D5p part 2), period 2 (D5f, D5p part 1) and later
  (15, 19, 22, 23 and 89 periods: D5b, D5q run 2, D5a, D5o, D5r).
- **Correction to D5s's reading.** D5p part 1 already had a reset with all
  latches zero, which the bootloader logged as a power-key boot with no
  watchdog reboot, with CPU8 offline and no observer. So a latch-clearing
  reset happens without `emergency_restart()`, and D5s's reading (a) is
  weaker than recorded there. D5p part 1 ran the PCM watchdog
  (`sodi_pcm_wdt=1`); D5s did not.
- Reset delays have ranged from about 50 s (D5o) to 2 min 20 s (D5p
  part 1) after the hung period.

### Request D5t run 3 (run 2026-11-20): the same run, with the bootloader caught

Run 2's measurement was lost to the missed catch, not to the setup. Run 3
repeats it with the same module and `d4.sh` blob, from a fresh boot with
`a72-at-boot` set. The custodian warns the owner at the start of window C
to watch for the bootloader from about 30 s to 3 min after the pings stop.
After the reset, D5t's request and table apply. If it passes, D5t's plan
(three passes in a row, then D5n's setup) applies.

### D5t run 3: period 29 hung; the reset went to Gemian again (custodian, 2026-11-20)

**Approved** by the owner ("Approve run 3").

**Setup.** Power-on boot fc07b91b, as runs 1 and 2: image 137,
`a72=loaded cpus=0-9`, module d452e299, `d4.sh` 29ec1867. Battery 60 %,
cable out.

**Observed.**
- Module loaded 09:00:06 (`sampling on CPU8`), blank 09:01:06, CPU8
  pinned and `watchdogd` on CPU0 at 09:01:08 (12 tasks left on CPU8),
  window C from 09:01:15.
- 28 periods returned (`returned=1 backstop=0`, CONN2AP through SYS_CIRQ,
  slept 0-354 ms, no early abort).
- Period 29 started at 09:02:03 and never returned. The journal ends at
  09:02:02.913 with period 28's `sodi cirq` line; no observer line after
  `sampling on CPU8`. 112 of 240 pings were answered.
- The device stopped answering by 09:07. No reset was seen in the 50 s to
  2 min 20 s range of earlier hangs. By about 09:18 it was in Gemian; the
  owner saw no bootloader. The next boot2 (da54a9db, 09:32) read all
  latches zero and an empty pstore, as after any Gemian boot.

**Result.**
- Four observer runs: one pass, hangs in periods 2, 2 and 29. The hang
  points stay within the spread without CPU8.
- Two of the three hangs reset into Gemian with no bootloader catch, which
  loses the RAM console on the next boot2. The catch cannot be relied on.
- When the reset came, and of which kind, is unknown.

### Request D5t run 4 (run 2026-11-20): read the RAM console in Gemian

Gemian uses the same ramoops layout as the station
([baseline](../../docs/hardware/gemini-gemian-baseline.md#exact-active-ramoops-layout)),
and has shown a station's console record in its own pstore after a station
`reboot` (station boot eda50de3). Booting Gemian again, or booting boot2,
overwrites that zone. So when a hang lands in Gemian, the custodian reads
the record there first, read-only, before any restart:

- copy `/sys/fs/pstore/*` (mounting pstore if needed) and anything
  Gemian's `systemd-pstore` moved to `/var/lib/systemd/pstore/`, from the
  first Gemian boot after the hang;
- if Gemian is not reachable over the LAN, the owner leaves it running
  rather than restarting it.

The run is otherwise run 3 again: same module and `d4.sh` blob, fresh
boot with `a72-at-boot` set. No code change. If the bootloader is caught
instead, D5t's request applies.

*Unique observation:* whether the RAM console survives a hang's reset into
Gemian, and if so, the observer's lines.

| Gemian's first boot after the hang shows | Decision |
| --- | --- |
| The station's console with `sodi obs` lines from the stuck period | Decode them with D5s's table |
| The station's console, ending at the period start with no stuck lines | CPU8 stopped too (or could not print): D5s's system-level freeze row |
| No station console record | The reset lost DRAM. Next: evidence from a path that does not depend on DRAM |
| All windows pass | Run again; D5t's plan applies |

**A check needing no device:** the laptop's ping log. If its replies carry
times, the last answered reply shows whether CPU0 answered after the
journal ended, that is, whether the system lived on after the last
logged period start.

### D5t run 4: the RAM console survived into Gemian, with no observer line (custodian, 2026-11-20)

**Approved** by the owner ("Approve run 4"). A first attempt on boot
18467448 never started: logind suspended the system 21 s after boot, most
likely on the lid, before the run's header. The owner powered off and
booted boot2 again.

**Setup.** Power-on boot 8113cbb7, image 137, `a72=loaded cpus=0-9`.
Module d452e299, `d4.sh` 29ec1867, as runs 1-3. Battery 73 %, cable out,
lid open. Pings timestamped.

**Observed.**
- The run started at 10:34:42. Pings started at 10:35:30. Replies came for
  `icmp_seq` 0-57; the last at 10:36:27, none after (58 of 240).
- The reset landed in Gemian (boot 822f7b33, up from about 10:37), the
  first Gemian boot after the hang. Read-only, its
  `/sys/fs/pstore/console-ramoops` (37533 bytes, kept privately) is **the
  station's console from boot 8113cbb7**, kernel time 12.98-650.22 s.
  Gemian has no `/var/lib/systemd/pstore`.
- In it: `sodi obs: sampling on CPU8` at 585.77 s, CPU9 and CPU7-1 taken
  offline at 586.18-586.79 s, then 35 periods of window C, all
  `returned=1 backstop=0`, no IM stuck, `val1` `00015830`, woken by CONN2AP
  through SYS_CIRQ.
- The record ends at 650.221934 s with period 35's `sodi cirq` line,
  then null padding. That is about 10:36:3x, where the pings stop.
- **No other `sodi obs` line:** no stuck report, no late sample, no
  `stopped` line.

**Result.**
- **Reading the RAM console in Gemian works.** The record survived this
  reset, and the boot2 catch is no longer needed for it.
- Period 36 hung, and CPU0 stopped answering pings at the same time: the
  station's journal ends at 10:36:26.865 with period 35's `sodi cirq`
  line, and the last ping reply came at 10:36:27.
- D5s's table row "no `sodi obs` lines from the hung period" applies: the
  observer's stuck line was due 500 ms after the period's end and never
  reached the console. Three causes fit:
  - CPU8 stalled in one of its SPM reads once the period hung;
  - CPU8 stopped by itself (a system-level freeze);
  - CPU8 does not run during periods at all, in passing ones too. This has
    never been shown either way, since its samples are printed only after a
    stuck period.

### Request D5u (run 2026-11-20): count the observer's ticks, reads off

**0835** (`count the observer's ticks in each period`):
- After each period, CPU0 logs `sodi obs: period N, T ticks on CPU8,
  longest gap G us`: how often CPU8's 10 ms timer ran during the period,
  and the longest gap between two runs. The stuck line also gives the
  count.
- `sodi_obs_noread`: CPU8 only counts in a period and reads no SPM
  register. Once a period is stuck it prints the stuck line, then
  `first late read`, then reads the SPM as before.
- Compile-checked with `W=1`, with and without `CONFIG_CPU_IDLE`; no new
  checkpatch item. No register writes.

**0836** (`optionally mark each kick in the SPM software registers`),
from the SPM program session's reading:
- On this path (CG, `flag0`) the program writes `SW_DEBUG` and
  `SW_RSV_0` to 0 at `0x413`/`0x419`, and `SW_RSV_0` to the wake status
  only at its exit (`0x4f4`) or in the early abort (`0x433`). `SW_DEBUG`
  then stays 0, which fits every `debug=00000000` line.
- With `sodi_mark`, the module writes both to `0x5a5a0000` plus the kick
  count before each kick, instead of `SW_RSV_0` = 0. **This is a changed
  register write and needs the owner's approval with the run:**
  `SW_DEBUG` (`0x10006604`) is new, and `SW_RSV_0` (`0x10006608`) gets
  the marker instead of 0. The program overwrites both itself.
- Compile-checked with `W=1` in both configurations; no new checkpatch
  item.

`d4.sh` (blob b03337d0) adds `D4_OBS_NOREAD=1` (`sodi_obs_noread`) and
`D4_MARK=1` (`sodi_mark`).

- **Candidate:** image 137, booted fresh with `a72-at-boot` set, init
  status `a72=loaded cpus=0-9`, lid open, with `mt6797-spm-sleep.ko`
  from a Buildbox build of the commit recording 0836 (0826-0828,
  0830-0836). No boot2 write.
- **Run:** `d4.sh` with `D4_CIRQ_LEVEL=1 D4_NO_EVENT=1 D4_OBS=1
  D4_OBS_NOREAD=1 D4_MARK=1`, otherwise as D5t, with timestamped pings.
- **After a hang:** as run 4. If it lands in Gemian, copy
  `/sys/fs/pstore/*` there first, read-only, before any restart. If the
  bootloader is caught, read the latches and the RAM console as in D5t,
  and also `SPM_SW_DEBUG`-`SPM_SW_RSV_4` (`0x10006604`-`0x1000661c`),
  read-only. The SPM program session expects the program's software
  registers may survive a watchdog reset, since the power-on values seen
  so far are what the bootloader writes. The marker's count is the number
  of periods set up since the load, refused ones included, so it matches
  the count of periods logged since the load, with the hung one last.
- *Hypothesis:* CPU8 runs through passing periods, and in run 4 it
  stalled in an SPM read once the period hung.
- *Unique observation:* CPU8's tick count in every period, and a hung
  period's stuck line from a CPU8 that has not read the SPM.

| Outcome | Decision |
| --- | --- |
| Passing periods: ticks about the sleep time / 10 ms, longest gap near 10 ms. Hung period: stuck line, then `first late read` and no sample | CPU8 runs through periods, and an SPM read stalls once a period hangs: the SPM's register path is blocked. The SPM program session looks for what in the program can block it |
| As above, with the late samples printed | The reads do not stall after the hang. Run 4's silence is then unexplained: compare with a run with reads |
| Passing ticks as above; no stuck line | CPU8 stops by itself in the hung period: a system-level freeze, not the reads |
| Passing periods: few or no ticks, or a longest gap near the period's length | CPU8 does not run during periods (its timer or clock stops). An observer on CPU8 cannot see inside a period; the SPM program session looks at what the program does to the A72 cluster and the system counter |
| All windows pass | Rerun; the ticks still answer whether CPU8 runs through periods |

After a caught reset, `SW_RSV_0` and `SW_DEBUG` also read:

| Value | Decision |
| --- | --- |
| The hung period's marker | The PCM never reached `0x413`: the hang is before the program's first steps, on the kick or CPU side |
| 0 | Inconclusive alone: every power-on read so far has `0x604`-`0x614` at 0 (fresh boots 2d63e1b4, 16c56d74, 18467448 and fc07b91b, and 6b669bb4 after Gemian), so a 0 may be a reset value. A watchdog reset without a power cycle is untested. Only with `LATCH_1` (`r6`) nonzero does it bracket a freeze between `0x413` and the exit |
| A wake status in `SW_RSV_0` | It reached its exit or the early abort |
| `ffffffff`, a bootloader value or an older marker | These registers do not survive the reset, or were rewritten; this channel is closed |

**Prior view (SPM program session).** On the CG path, right before the main
wait (`0x472`), `pcm_sodi` sets `R0_SC_ARM_CK_OFF` and the ARM PLL off bits
for both PLLs (`ARMPLLOUT_OFF`, `ARMBPLLOUT_OFF` and their stages), with no
check of which CPUs are in WFI, and gives them back only on exit (`0x4f5`).
From `0x43e` to `0x511` it also holds the infra bus-master pause. The vendor's
driver enters SODI only with one CPU online. *Inference:* CPU8 has no clock
for the whole period, so the observer cannot tick in it, and its SPM reads
may wait behind the pause. The predicted D5u outcome is the "few or no ticks"
row. Every hang before D5s ran with CPU0 alone (CPU1-9 offline, which
`spm_run` required), so the vendor's one-CPU precondition was met there and
the hang does not need a second CPU online.

### D5u: CPU8 does not tick in any period; window A hung (custodian, 2026-11-20)

**Approved** by the owner, with the 0836 marker writes.

**Setup.** Power-on boot 6b669bb4, image 137, `a72=loaded cpus=0-9`.
Module c08b03df (Buildbox 845fdc1f6, 0826-0828 and 0830-0836), `d4.sh`
679615a5 (blob b03337d0) with `D4_CIRQ_LEVEL=1 D4_NO_EVENT=1 D4_OBS=1
D4_OBS_NOREAD=1 D4_MARK=1`. Pre-module read: latches at their defaults,
`0x604`-`0x614` 0, `0x618`/`0x61c` `ffffffff`. Battery 47 %, lid open,
cable out. Started at 16:14:22.

**Observed.**
- `sodi obs: sampling on CPU8` at 326.8 s.
- **Window C:** 23 periods, then the owner touched the keyboard at about
  16:15:47 and the window ended (period 23 woken by the key's line, CIRQ
  word 5 `00002000`, `r12` `00400000`). 22 were ended by CONN2AP or the
  WLAN line; 36 echo requests in the window; hash equal.
- **Every period logged `0 ticks on CPU8, longest gap 0 us`**, including
  periods that slept 205-323 ms, where a running 10 ms timer would have
  ticked 20-32 times.
- The pings (240 of 240 answered, 16:15:10-16:19:10) ran out, and window
  A waited for them to stop.
- The device reset into Gemian. Gemian (boot a653c275) was up at
  16:20:25, so the hang and the reset fell between 16:19:10 and about
  16:20.
- **Gemian's pstore** held station boot 6b669bb4's console (28055 bytes,
  kept privately): the 23 period lines, the last at 370.789 s, then four
  `mediatek-disp-ovl 1400b000.ovl: swiotlb buffer is full` lines at
  491.15-491.66 s, and nothing more. No line from window A: no `sodi cg`
  line, no stuck line, no `first late read`.
- The marker registers could not be read: Gemian reinitialises the SPM.

**Result.**
- **CPU8 does not run during a period.** Its pinned 10 ms timer never
  fired while a period was live. That is the "few or no ticks" row, and
  what the SPM program session predicted from the program: before the
  main wait it cuts the ARM clock and both ARM PLLs for the whole period.
  The tick logic counts any tick in a live period, so 0 means none. Not
  checked: that the timer ran on CPU8 outside periods (its interrupt
  count). The module went with the reset.
- **An observer on another CPU cannot see inside a period,** and the stuck
  lines of D5s and D5t runs 2-4 were never possible. The CPU8 observer
  is retired.
- **The hang was window A's first period.** `d4.log` ends with `16:19:18
  A: 20 periods`, and the station's journal ends at 16:17:47.911 with the
  `swiotlb` line (the console's 491 s), so the period started about 91 s
  after the last kernel line and never returned. With CPU8 stopped in the hung period too, the hung period got
  at least as far as whatever stops CPU8. *Inference:* if that is the
  program's clock cut at `0x472`, this hang passed `0x402`, unlike the
  `r6` = 0 hangs; the latches were lost, so this is not shown.
- **The SPM program session's bracket.** Before `0x472`, only the infra
  bus-master pause at `0x43e` (`TOP_MAS_PAU_REQ`, masks `0x6ff00b01` and
  `0xfe00ffff`) could plausibly stop the A72s; nothing earlier touches MP2,
  MCUSYS, the system counter's clock, 26M or the GIC. So CPU8's zero ticks
  come from the pause or the clock cut, and a hung period that leaves CPU8
  stopped got at least to `0x43e`. Which mask bit is which master is not
  known. The module's GIC mask is not the cause: it clears only SPI enables
  in the distributor, and CPU8's timer is a PPI in its redistributor, which
  the module only reads.
- The display's `swiotlb buffer is full` lines are a separate fault and
  not part of this stage.

### Request D5v (proposed): CPU0 alone, with the marker

The observer setup only adds risk now. D5v goes back to the setup of every
hang before D5s, CPU0 alone with CPU1-9 offline, and keeps 0836's marker,
the one channel that does not need a running CPU. It needs the bootloader
caught after the reset; a reset into Gemian clears the SPM.

- **Candidate:** image 137, booted fresh with `a72-at-boot` back to `.off`
  (as before D5s), with module c08b03df (845fdc1f6). No new build, no
  boot2 write.
- **Run:** `d4.sh` blob b03337d0 with `D4_CIRQ_LEVEL=1 D4_NO_EVENT=1
  D4_MARK=1`, two states, no cap, lid open, cable out, timestamped pings.
- **The owner watches the screen for the whole run,** from window C to the
  end of B, and catches the bootloader as soon as it shows.
- **After a caught reset:** before any module, read the latches and
  `0x10006604`-`0x1000661c`. If it lands in Gemian, read Gemian's pstore
  first as in D5t run 4; the marker is then lost.
- *Unique observation:* `SW_RSV_0` and `SW_DEBUG` after a watchdog reset
  with no power cycle, read with the latches.

The decision is D5u's marker table, with `LATCH_1` (`r6`) alongside. If
the marker survives, the next runs can place each hang without the RAM
console. It cannot tell a freeze at the pause (`0x43e`) from one at the
clock cut (`0x472`): both come after the program clears the marker at
`0x413`-`0x419`.

### D5v: window C's first period hung with CPU0 alone; the reset went to Gemian (custodian, 2026-11-20)

**Approved** by the owner in the custodian's session.

**Setup.** Fresh boot2, boot ac886c40, image 137 with `a72-at-boot` off
(CPU0-7 online, no A72s). Module c08b03df (845fdc1f6, 0836), `d4.sh`
679615a5 (blob b03337d0) with `D4_CIRQ_LEVEL=1 D4_NO_EVENT=1 D4_MARK=1`,
no observer. Battery 37 %, lid open, cable out. Pre-module read: latches 0,
`0x600`-`0x614` 0, `0x618`/`0x61c` `ffffffff`, TOPRGU `0x15`.

**Observed.**
- `d4.log`: 21:26:53 `sodi_cirq_level` Y, wake source `0f57c5e5`; 21:27:41
  blanked; 21:27:42 `online: 0`; 21:27:47 window C waiting; 21:27:48
  `C: pings arriving, 60 periods`, then `start, cpu0 1339000 kHz`, the last
  line.
- Pings were answered through 21:27:49 (sequence 57) and none after
  (58 of 240).
- The station's kernel journal and Gemian's copy of its RAM console both
  end at `psci: CPU1 killed` (151.6 s). No `sodi cirq` or period line:
  period 1 of window C never returned.
- The owner did not see the bootloader; LK booted Gemian, which
  reinitialises the SPM. The next boot2 (160e6e96) read the latches and
  `0x600`-`0x61c` at their defaults, so the marker was lost.

**Result.**
- **A hang with only CPU0 online and no A72 ever up.** The hang needs
  neither CPU8 nor the observer, and it came with the vendor's
  precondition met (one CPU online). It is the earliest hang yet: the
  first period after the other CPUs went offline.
- The marker channel is still untested. Every hang since D5t run 2 reset
  into Gemian; watching the screen for the bootloader does not work when
  the reset comes 50 s to over ten minutes after the hang.

### Request D5w (proposed): D5v again, with the side key held through the reset

LK selects boot2 when the side key is held as it starts
([keyboard](../../docs/hardware/keyboard.md)), so the catch does not need
the owner to see the bootloader. The custodian sees the hang live: the
pings stop. From then the owner holds the side key down until the boot2
kernel is up, however long the reset takes. A clip or a rubber band can
hold it. Holding it before the hang would send key events into the run,
and a key ended D5u's window C, so the owner presses it only after the
custodian reports the pings stopped.

- **Candidate:** as D5v: image 137, fresh boot2 with `a72-at-boot` off,
  module c08b03df (845fdc1f6). No new build, no boot2 write.
- **Run:** `d4.sh` blob b03337d0 with `D4_CIRQ_LEVEL=1 D4_NO_EVENT=1
  D4_MARK=1`, two states, no cap, lid open, cable out, timestamped pings.
- **Hang call:** no ping answered for 10 s during a window. The custodian
  tells the owner, and the owner holds the side key.
- **After the reset:** before any module, read the latches and
  `0x10006600`-`0x1000661c`, then the pstore. If it still lands in Gemian,
  read Gemian's pstore first, and record that the held key did not select
  boot2 after a watchdog reset.
- **Clock gates, read only:** read the infra gate status words
  `0x10001090`, `0x10001094` and `0x100010b0` before the module loads and
  again in the script's 30 s SSH wait, after the module loads and before
  the blank. No write. A read after the blank would need a script step;
  the masters this lead names (DMA, modem, audio) should not change with
  the blank, though `DISP_PWM` may.
- *Unique observation:* `SW_RSV_0` and `SW_DEBUG` after a watchdog reset
  with no power cycle, read with the latches.

**Why the gate read.** The SPM program session finds no unbounded wait in
the program on this path: every `r14` wait is timed, and the polling
helpers are skipped by flags 0 and 9. A freeze after `0x402` would then be
a PCM bus access that never completes, such as the stores after the pause:
`CLK_CFG_0` (`0x10000048`), `CLK_CFG_UPDATE` (`0x10000004`) and APMIXED
`0x1000cf38` at `0x57f`. The vendor's driver also refuses SODI while any
clock in its idle mask is ungated: for infra, masks `0x00440802`,
`0x03aff900` and `0x21fe36fd` over the inverted gate status words. With
the mainline gate shifts (numbering assumed to match) those include UART0,
AP_DMA, audio and the three SSUSB clocks; MSDC is not in them. The station
does not check this. *Inference:* the infra pause landing on a USB or DMA
transaction in flight, followed by a PCM store that never completes, would
hang intermittently. This cannot explain the hangs that latched `r6` = 0,
which stopped before the program ran. With the cable out, an ungated but
idle SSUSB has no transaction to catch, so the lead needs a master active
at random moments: AP_DMA (infra word 1 bit 18, used by UART and I2C DMA),
CLDMA and the CCIF gates, audio (word 1 bit 25) or GCPU. If D5w latches a
nonzero `r6` and one of those is ungated, the next run gates it; SSUSB
ungated with the rest gated points away from this lead.

The decision is D5u's marker table, with `LATCH_1` (`r6`) alongside:
the marker intact means the program never reached `0x413`; 0 is
inconclusive unless `LATCH_1` is nonzero; a wake status means it reached
the exit at `0x4f4`; a bootloader value means the channel is closed.

### D5w: period 11 of window C hung; the side key was not held (custodian, 2026-11-21)

**Approved** by the owner in the custodian's session.

**Setup.** Fresh boot2, boot 7e976a0d (CPU0-7 online, no A72s), module
c08b03df (845fdc1f6, 0836), `d4.sh` 679615a5 (blob b03337d0) with
`D4_CIRQ_LEVEL=1 D4_NO_EVENT=1 D4_MARK=1`. Battery 61 %, lid open, cable
out. Pre-module read: latches 0, `0x600`-`0x614` 0, `0x618`/`0x61c`
`ffffffff`, TOPRGU `0x15`.

**Observed.**
- **Gate status words** `0x10001090`/`0x94`/`0xb0`: `03eff900`,
  `00444816`, `21fe36ff` before the module loaded, and the same at
  12:22:16 with the module loaded, before the blank. The script loads the
  module after its SSH wait, so this read came in the idle-blank wait, not
  the SSH wait.
- 12:22:04 module loaded; 12:22:21 blanked; 12:22:22 `online: 0`;
  12:22:28 window C, pings arriving.
- 10 periods returned, all with `r12` `00400020`, mostly woken by CONN2AP
  through SYS_CIRQ, slept 18-320 ms. In 5 of them the `im` FSM word went
  `02c48910` > `02448910`. Period 10 returned at 12:22:44; its next local
  event was 24 us after entry.
- Each period's `sodi cg` line: `cg0` `03eff900`, `cg1` `00464816`,
  `cg2` `21fe36ff`, `clk_cfg_0` `01010101`, unchanged through the period.
  `cg1` has bit 17 set inside periods, clear outside.
- Period 11 started at 12:22:44, with the last ping answered the same
  second. The hang was called at 12:22:54.
- The owner did not hold the side key. The device reset into Gemian, and
  the next boot2 (209712fd) read everything at its defaults.
- Gemian's copy of the RAM console held all 10 period lines (91 lines,
  kept privately). The station journal agrees.

**Result.**
- **The masked infra clocks are all gated, in and out of a period**, if
  the vendor's first two masks belong to the second and first status words:
  `~0x03eff900 & 0x03aff900`, `~0x00444816 & 0x00440802` and
  `~0x21fe36ff & 0x21fe36fd` are all 0. In the order first reported, the
  second word would show 15 masked clocks running. *Confirmed* by the SPM
  program session from the vendor's idle code, which reads its first group
  from `0x94` and its second from `0x90`; the mainline gate table names
  them the other way, which caused the first decode. So **the station meets
  the vendor's infra clock condition**, and the gate lead is withdrawn for
  infra. The bit names given for the first two words in D5w's request are
  unreliable. Display and multimedia groups were not read.
- A hang 11 periods in, with CPU0 alone, as in D5v.
- The held-key catch is untested: the key was not held, so nothing is
  known about whether it selects boot2 after a watchdog reset.

### Request D5w run 2 (proposed): the same run, with the side key held

No change from D5w, except that the owner holds the side key from the hang
call until the boot2 kernel is up. A clip or rubber band can hold it for a
reset that takes minutes. The gate reads can be skipped; they showed no
change after the module loaded. Instead, before the module loads, read
`SPM_PWR_STATUS` (`0x10006180`) and `PWR_STATUS_2ND` (`0x10006184`), read
only, to check the vendor's remaining condition that the image, GPU and
video power domains are off. With CPU0 alone and the infra condition met,
no other unmet condition is known in the vendor's idle code.

- **Candidate and run:** as D5w.
- **After the reset:** before any module, read the latches and
  `0x10006600`-`0x1000661c`, then the pstore. If it lands in Gemian with the
  key held, read Gemian's pstore and record that the held key did not
  select boot2.
- The decision is D5u's marker table with `LATCH_1` (`r6`).

### D5w run 2: window C's first period hung; the reset went to Gemian (custodian, 2026-11-21)

**Approved** by the owner in the custodian's session.

**Setup.** Boot 209712fd (boot2, CPU0-7, up 1 h 26 min, no module loaded
before the run), module c08b03df (845fdc1f6, 0836), `d4.sh` 679615a5
(blob b03337d0) with `D4_CIRQ_LEVEL=1 D4_NO_EVENT=1 D4_MARK=1`. Battery
47 %, lid open, cable out. Pre-module SPM read at its defaults.

**Observed.**
- `SPM_PWR_STATUS` (`0x10006180`) `2b00005e`, `PWR_STATUS_2ND`
  (`0x10006184`) `2b00004e`, before the module: they differ in bit 4.
  With the mainline domain table, ISP (5), VDEC (7), VENC (21) and MFG
  (11-13) are off, MM (3) and audio (24) on; bits 1, 2, 4, 6, 25, 27 and
  29 are not named there.
- 16:56:15 module loaded; 16:56:43 blanked; 16:56:44 `online: 0`;
  16:56:50 window C, pings arriving, then `start, cpu0 1547000 kHz`, the
  last line. The last ping was answered at 16:56:51 (32 of 40). The hang
  was called at 16:57:01.
- The station journal and Gemian's copy of the RAM console (20 lines,
  kept privately) both end at `psci: CPU1 killed`, as in D5v.
- The device reset into Gemian. The next boot2 (eb0d5403) read
  everything at its defaults. The owner confirms the side key was not
  held, so the held-key catch is still untried.

**Result.**
- With the A72s never up and CPU0 alone, three runs hung in periods 1, 11
  and 1 (D5v, D5w, run 2).
- **The vendor's power-domain condition for SODI is met.** The SPM program
  session decoded the bits from the vendor's power-domain driver: on are
  CONN (1), DRAM PHY channel 0 (2), display (3), DRAM PHY channel 1 (4),
  infra (6) and audio (24); off are MD1, C2K, ISP, VDEC, the GPU, MJC
  (20) and VENC. The vendor's check refuses SODI only for GPU, ISP, VDEC,
  VENC or MJC power; audio and DRAM PHY channel 1 are not in it, and the
  display blocks only in command mode.
- **DRAM PHY channel 1 reads half switched:** set in the status word, clear
  in the second one. The two are the domain's two power-switch acks, and
  the vendor's driver waits for both to agree on every domain it controls.
  It has no sequence for channel 1, which belongs to the SPM and DRAM side.
  Whether 1/0 is its normal resting state is not known.
- The marker is still lost.

### Request D5w run 3 (proposed): the same run, key ready at the call

As D5w run 2, including the power-status read, with `0x100063b8` (DRAM
PHY channel 1 power control) added to it. If it lands in Gemian, read
`0x10006180`, `0x10006184` and `0x100063b8` there at idle, read only,
before anything else: Gemian showing the same 1/0 drops the half-switched
lead; 1/1 or 0/0 means the station leaves channel 1 half switched, which
matters for a program that drives DRAM-side power. Also before the
module, with the panel lit: re-read `0x10006180`/`0x10006184`, and only if
bit 3 (display) is set in both, read the display gate terms `0x14000100`,
`0x14000110`, `0x14000894` and `0x14000898`. The vendor's idle code reads
exactly these under the same condition; the block's bus clock (`mm_sel`)
has no gate in either kernel. Never during a period: the program changes
`CLK_CFG_0`. The hangs now come within
seconds of window C's start, so the owner has the clip or rubber band in
hand from the blank, and puts it on the side key at the custodian's hang
call, not before. It stays on until the boot2 kernel is up. The decision is
D5u's marker table with `LATCH_1` (`r6`); a landing in Gemian with the key
held means the held key does not select boot2 after a watchdog reset.

### D5w run 3: period 28 of window C hung (custodian, 2026-11-21)

**Approved** by the owner in the custodian's session.

**Setup.** Fresh boot2 eb0d5403 (CPU0-7), module c08b03df, `d4.sh`
679615a5 (blob b03337d0) with `D4_CIRQ_LEVEL=1 D4_NO_EVENT=1 D4_MARK=1`.
Battery 41 %, lid open, cable out. Pre-module SPM read at its defaults;
`0x10006180` `2b00005e`, `0x10006184` `2b00004e`, as in run 2.
`0x100063b8` was not read: the request reached the custodian after the
run had started.

**Observed.**
- 27 periods returned, all with `r12` `00400020`, mostly woken by CONN2AP
  through SYS_CIRQ. The journal has all 27 period lines and ends with
  period 27's lines (next local event 1092 us after entry).
- Period 28 started at 17:43:56; the last ping was answered at 17:43:57
  (47 answered); the hang was called at 17:44:07.
- The next boot2 (ae48468a) came up at 19:01, 77 minutes later, with
  everything at its defaults and an empty pstore. The owner does not
  recall whether the clip went on at the call or whether Gemian booted in
  between; both are unknown. The empty pstore and the gap suggest Gemian
  (inference). The held-key catch is still untested.

**Result.**
- A fourth hang with CPU0 alone and the A72s never up: periods 1, 11, 1
  and 28.
- In both hangs that followed returned periods, the last returned period
  changed the `im` FSM word `02c48910` > `02448910` (D5w period 10, run 3
  period 27). The change is common (5 of 10 and 13 of 27 periods), so two
  of two is about a 1 in 4 chance; noted, not a lead.

### Request D5x (proposed): test the held-key catch with a deliberate watchdog reset

Three runs have left the held-key catch untested, each time because the
key was not held at an unpredictable moment. D5x tests it alone, at a
known moment, with no cpuidle module.

- **Before:** on a fresh boot2, before any module, the reads the last
  runs missed: `0x10006180`, `0x10006184`, `0x100063b8`, and, with the
  panel lit and display bit 3 set in both status words, `0x14000100`,
  `0x14000110`, `0x14000894` and `0x14000898`. Read only.
- **Reset:** the owner puts the clip on the side key first; key events do
  not matter with no run. Then the custodian opens `/dev/watchdog` and
  holds it without feeding it, so TOPRGU resets after its 31 s timeout.
- **Owner reports at the reset:** the key is on, and what booted.
- **Decision:** boot2 means the clip works after a watchdog reset, and the
  next hang run uses it, with the clip on from the hang call. Gemian with
  the key held means it does not; the latches then need another route
  (for example, reading them in Gemian before its SPM driver starts),
  which is a separate proposal. A cold boot instead of a reset means the
  feeder test did not produce a watchdog reset.

### D5x: the held side key selects boot2 after a watchdog reset (custodian, 2026-11-21)

**Approved** by the owner in the custodian's session.

**Setup.** Boot2 ae48468a (CPU0-7, up 6 min, no module ever loaded),
battery 37 %, panel lit.

**Observed.**
- Read only, before the reset: `0x10006180` `2b00005e`, `0x10006184`
  `2b00004e`, `0x100063b8` `0000000d`. Display bit 3 was set in both, so:
  `0x14000100` `00110000`, `0x14000110` `ffffff00`, `0x14000894` 0,
  `0x14000898` 0.
- The watchdog (`mtk-wdt`, 31 s, systemd's runtime watchdog off) was
  inactive. The owner put the clip on the side key; at 19:07:56 the
  custodian synced and held `/dev/watchdog` open without feeding it. The
  journal ends at 19:07:57; the next boot, 8a49c253, started at
  19:08:57, and the owner reports boot2.
- Before any module on 8a49c253:

| Register | After D5x (no SODI) |
| --- | --- |
| `PCM_WDT_LATCH_0` `0x190` | `0x04248000` |
| `PCM_WDT_LATCH_1` `0x194` | `0x00000000` |
| `PCM_WDT_LATCH_2` `0x198` | `0xffffffff` |
| `DRAMC_DBG_LATCH` `0x19c` | `0x00003d3d` |
| `PCM_WDT_LATCH_3` `0x1c4` | `0x2b003f5e` |
| `PCM_WDT_LATCH_4` `0x1c8` | `0x003d8008` |

  `0x600`-`0x614` 0, `0x618`/`0x61c` `ffffffff`, TOPRGU `MODE` `0x15`,
  status 0.
- On boot2, systemd-pstore moves the RAM console at boot to
  `/var/lib/systemd/pstore/`; that is why `/sys/fs/pstore` read empty on
  boot2. Here it held only the last 286 bytes of ae48468a's console. Run
  3's boot ae48468a found no new file there, which supports Gemian having
  taken run 3's console (inference).

**Result.**
- **The clip works.** Held on the side key, it selects boot2 after a
  TOPRGU watchdog reset, and the latches survive into that boot2.
- **A no-SODI reference for the latches.** With no module ever loaded,
  `LATCH_0` `04248000`, `LATCH_1` 0 and `LATCH_2` `ffffffff` are
  exactly D5l's hang values. So those values do not show a program stopped
  early; they are what a reset with no program running leaves. D5l's hang
  left the PCM looking idle, while the later run with `LATCH_1`
  `fd8d3239` did not. `LATCH_3` matches the power-status pattern
  (`2b00005e`) with `0x3f00` added; its layout is with the SPM program
  session.
- **Display gate terms, with the panel lit:** by the vendor's formula,
  `~0x100 & 0x4000` = `0x4000` and `~0x110 & 0xd0` = `0xd0`, so both
  display terms would refuse SODI at that moment. The runs blank the panel
  first, so this read is not the run's state, and whether the terms apply
  in video mode is with the SPM program session.

**The display gates and the latches (SPM program session).**
- The vendor's display terms depend only on the display domain being on,
  so they apply in video mode too: with the panel lit, the station's values
  would refuse SODI. With the mainline gate names, the open gates are
  `mm_fake_eng` (CG0 bit 14, a dummy engine), DPI (CG1 bit 4, unused by a
  DSI panel) and the two LARB4 AXI bridges to MM and MJC (CG1 bits 6 and
  7). None is on the DSI path, and CG0 `00110000` / CG1 `ffffff00` show
  nearly every MMSYS gate open: unused gates were never closed. Blanking
  stops only the CRTC's own engines, so it should not change these.
- *Lead (inference):* bit 7 clocks the bridge into MJC, whose power domain
  is off. The program's master pause (`0x2b0`, called at `0x43e`) and the
  stores after it cross the MM bus, and an open bridge into a powered-off
  domain could leave a bus handshake that never completes: the stuck PCM
  store.
- `LATCH_3` matches the power-status layout, so it reads as a snapshot of
  the domains at the reset, not a hang signature: D5x's `2b003f5e` adds
  bits 8-13 (the GPU domains) to the live value, D5l's `2a00005c` lacks
  CONN and audio. `LATCH_4` has no known layout; hang values are compared
  with D5x's `003d8008`.

### Request D5y (proposed): close the four display gates, with the clip on at the call

0837 adds `sodi_mm_cg` to the module: 1 logs MMSYS CG0 and CG1 and the
vendor's terms, 2 also closes the four gates through the set registers
(`0x4000` to `0x14000104`, `0xd0` to `0x14000114`). Both refuse unless
the display domain shows both power acks. `d4.sh` runs it after the blank
with `D4_MM=1` or `2`.

- **Candidate:** a new module from a Buildbox build with 0837; no boot2
  write. `d4.sh` with `D4_CIRQ_LEVEL=1 D4_NO_EVENT=1 D4_MARK=1 D4_MM=2`,
  fresh boot2, CPU0 alone, two states, no cap, lid open, cable out,
  timestamped pings.
- **New writes:** the two set-register writes close four MMSYS gates with
  no mainline consumer on this panel: DPI, a dummy engine, and the LARB4
  bridges into a powered-off MJC. The other gate bits are untouched; the
  gates stay closed until the next boot. They need the owner's approval.
- **At a hang call** the owner puts the clip on the side key and says so;
  at the reset the owner says what booted. After a boot2, before any
  module: the latches, `0x10006600`-`0x1000661c`, then
  `/var/lib/systemd/pstore/`.
- *Unique observation:* the gate words after the blank, and whether
  periods hang with the vendor's display condition met.

| Outcome | Reading |
| --- | --- |
| Every window passes | Consistent with the open gates causing the hangs; one pass is not proof (D5t passed once), so repeat before concluding |
| A hang | The gates are not the cause, or not the only one; the latches and marker place it |
| The gates do not close, or the terms stay nonzero | The write path is wrong; stop and recheck |

### D5y: period 14 hung with the four display gates closed (custodian, 2026-11-21)

**Approved** by the owner in the custodian's session, with the two MMSYS
writes.

**Setup.** Boot2 8a49c253 (D5x's watchdog-reset boot, up 43 min, no
module ever loaded, CPU0-7). Module d384c996 (Buildbox b1b018d7f, 0837),
`d4.sh` blob d14c22b8 with `D4_CIRQ_LEVEL=1 D4_NO_EVENT=1 D4_MARK=1
D4_MM=2`. Battery 34 %, lid open, cable out. The pre-module latches still
held D5x's reset values, so a caught reset on this boot giving D5x's
values would have been ambiguous: the next runs start from a boot whose
latches read 0.

**Observed.**
- Right after the blank (19:54:28): `sodi mm: cg0 3f9f8000 cg1 ffffff03,
  SODI terms 00004000 000000d0`, then `gated, cg0 3f9fc000 cg1 ffffffd3,
  SODI terms 00000000 00000000`. The blank closed many MMSYS gates
  (CG0 was `00110000` lit in D5x) but not these four; the writes closed
  exactly them.
- 19:54:29 `online: 0`; 19:54:36 window C. 13 periods returned, all with
  `r12` `00400020`, mostly woken by CONN2AP through SYS_CIRQ. Period 14
  started at 19:54:57, with the last ping answered the same second (58
  answered); the hang was called at 19:55:07.
- The device reset into Gemian. Its copy of the RAM console (102 lines,
  kept privately) and the station journal both hold the `sodi mm` lines
  and the 13 period lines. The next boot2 (accc6c52) read everything at
  its defaults; `/var/lib/systemd/pstore/` had no new file. The owner
  confirms the clip was not on at the reset, so the landing in Gemian does
  not contradict D5x.
- Period 13, the last to return, left the `im` FSM word unchanged
  (`02c48910`); it changed only in periods 5 and 9.

**Result.**
- **The display gates are not the cause.** With the vendor's display
  terms at 0 and its infra and power-domain conditions met, CPU0 alone,
  a period still hung. The open-bridge lead is refuted.
- The `im` FSM pattern of D5w and run 3 is refuted.
- Five hangs with CPU0 alone: periods 1, 11, 1, 28 and 14.

**What the vendor's SODI entry does that the module does not (SPM
program session).** Rebuilt from 0802-0837 against the vendor's entry; the
PCM initialisation, kick block and flag logic match. Ranked by how plausibly
each could stall a bus store:
1. **The SMI async DCM.** Before each entry the vendor's driver saves the
   M4U's `MMU_SMI_ASYNC_CFG` (`0x10205b80`), ORs in
   `SMI_COMMON_ASYNC_DCM` (`0xc000`), and writes the saved word back after
   the wake. It sits on the async bridge between SMI common (the MM bus)
   and the M4U/EMI side, the path of the program's master pause and clock
   cut. The module never touches it. The vendor reads it with no clock
   call; its M4U clocks are MM-side, and no infra gate guards it.
2. **The UART sleep handshake.** The vendor's driver asks the UART to
   sleep first and refuses SODI if it is busy. The station's console is
   `ttyS0` at log level 4, so the per-period lines never reach the UART;
   the next run logs its transmit counter around window C to confirm.
3. **The module does more: MP2.** In this flag mode the vendor sets
   `ACINACTM` only on MP0 and MP1 and leaves the powered-off A72
   cluster's `MP2_AXI_CONFIG` alone; the module writes it every period.
4. The vendor switches the PMIC wrapper to its deep-idle phase table; it
   matters only if `pcm_sodi` issues wrapper commands on this path.
5. Four `pwrctrl` registers the vendor writes and the module leaves:
   `SW_CRTL_EVENT`, `SPM_SW_RSV_6`, `SPM_WAKEUP_EVENT_EXT_MASK`,
   `SPM_SLEEP_MD32_WAKEUP_EVENT_MASK`. Low risk.
6. Known: the vendor masks every GIC interrupt but the SPM's before the
   PCM reset, wakes CPU0 with a GPT timer, and re-kicks its VCORE DVFS
   program after the wake.

### Request D5z (proposed): the vendor's SMI async DCM, and MP2 left alone

0838 adds two parameters. `sodi_no_mp2` leaves `MP2_AXI_CONFIG` alone.
`sodi_smi_async` ORs `0xc000` into `0x10205b80` before each SODI period
and writes the saved word back after it, only while the display domain
has both power acks and `mm_smi_common` is ungated (MMSYS CG0 bit 0
clear); `sodi_smi_async_val` reports the saved word, or `ffffffff` if the
guard refused. `d4.sh` adds `D4_NO_MP2=1` and `D4_SMI_ASYNC=1`, and logs
the `ttyS0` transmit counter around window C.

- **Candidate:** a new module from a Buildbox build with 0838; no boot2
  write. Fresh boot2 with latches 0 (accc6c52 qualifies), CPU0 alone,
  `D4_CIRQ_LEVEL=1 D4_NO_EVENT=1 D4_MARK=1 D4_MM=2 D4_NO_MP2=1
  D4_SMI_ASYNC=1`, two states, no cap, lid open, cable out, timestamped
  pings.
- **New writes:** `0x10205b80`, the vendor's own value and restore, each
  period. It needs the owner's approval. MP2 loses a write.
- **At a hang call** the owner puts the clip on the side key and says so;
  at the reset the owner says what booted. After a boot2, before any
  module: the latches, `0x10006600`-`0x1000661c`, then
  `/var/lib/systemd/pstore/`.

| Outcome | Reading |
| --- | --- |
| Every window passes | Consistent with the async DCM or MP2; repeat, then split the two |
| A hang | Neither is the cause alone; the latches place it |
| `sodi_smi_async_val` `ffffffff` | The guard refused; the DCM was not set, so the run did not test it |
| `ttyS0` transmit count rises in window C | The UART was active; item 2 comes back |

### D5z: period 7 hung with the SMI async DCM and MP2 left alone (custodian, 2026-11-22)

**Approved** by the owner in the custodian's session, with the M4U write.

**Setup.** Boot2 accc6c52, pre-module latches 0. Module 659c86b4
(Buildbox 794f55e39, 0838), `d4.sh` blob 78ab4180 with `D4_CIRQ_LEVEL=1
D4_NO_EVENT=1 D4_MARK=1 D4_MM=2 D4_NO_MP2=1 D4_SMI_ASYNC=1`. CPU0 alone,
cable out.

**Observed.**
- `sodi mm: gated, cg0 00114000 cg1 ffffffd0, SODI terms 00000000
  00000000`: the display terms were met again.
- Pings from 10:18:16. Six periods returned normally: `r12` `00400020`,
  CONN2AP wakes through SYS_CIRQ, sleeps of 88-246 ms, the `im` FSM word
  alternating between `02c48910` and `02448910`. Period 7 started at
  10:18:25, the second of the last ping reply, and never returned.
- `ttyS0 tx:-`: `d4.sh` found no transmit counter at the start of window C.
  The saved SMI word was to be logged at the end of window C, which the run
  never reached, so the log does not show whether the guard let the write
  through.
- The station journal ends at 51680.26 s; Gemian's copy of the RAM console
  (kept privately) runs to 51680.94 s, the end of period 6's dump, and holds
  nothing later.
- The device reset into Gemian; the clip state at the reset is unknown. The
  next boot2 (e367f52b) read the latches at their defaults before any
  module (`6190`-`61c8` 0, `6600`-`6614` 0, `6618`/`661c` `ffffffff`,
  TOPRGU `0x15`). No latch evidence from this hang.

**Result.**
- **Leaving MP2 alone does not prevent the hang.** That holds whatever
  the SMI guard did.
- **The SMI async DCM is not cleared**: the run does not show that the
  write happened. If it did, it does not prevent the hang either.
- Six hangs with CPU0 alone: periods 1, 11, 1, 28, 14 and 7. None has
  left latches from the hang itself. The clip has worked once, in D5x's
  deliberate reset, and has not been confirmed on at any SODI hang.

### Request D5z run 2 (proposed): the same run, logged per period, with the clip on

Removing vendor differences one run at a time has not changed the outcome
in four runs, and each hang has lost its latches to Gemian. The next
decision-changing measurement is the SPM latches from a hang with this
configuration: whether the program is running, and at which PC, when the
watchdog fires. D5x gives the no-program reference to compare against.

`d4.sh` now logs, after every period of window C, the `ttyS0` transmit
count and, with `D4_SMI_ASYNC=1`, the saved SMI word. Without
`/proc/tty/driver/serial`, it counts the UART's interrupts in
`/proc/interrupts`.

- **Candidate:** module 659c86b4 (0838) again, the new `d4.sh`; no boot2
  write. The current boot2 e367f52b has latches 0. Same env as D5z, CPU0
  alone, two states, no cap, lid open, cable out, timestamped pings.
- **New writes:** none beyond D5z's.
- **At the hang call** the owner puts the clip on the side key before the
  watchdog fires and says so; at the reset, what booted. After a boot2,
  before any module: the latches, `0x10006600`-`0x1000661c`, `0x10006630`,
  `0x1000641c`-`0x10006424`, then `/var/lib/systemd/pstore/`.

**Reading the latches (SPM program session).** They hold no PC: LATCH_0
(`0x190`) is the one-hot FSM state, LATCH_1 (`0x194`) is `r6`, LATCH_2
(`0x198`) is `RSV_5` and should stay `ffffffff`. On the CG path only `r6`
moves with the program's position, which places it in one of four windows.
The run's `SW_FLAG` is `000d3239`, from 0838's source: the station's base
flags `000d02b1` (logged at insmod) without bit 7, with bits 3 and 12 (CG
mode) and with bit 13 for `sodi_no_event`. D5z logs no SODI flag line.

| LATCH_1 (`r6`) | Program window | Stores leaving the SPM |
| --- | --- | --- |
| `0` | Before `0x402`, or nothing latched | None |
| `000d3239` | `0x402`-`0x407` | None |
| `018d3239` | `0x409`-`0x410` | `0x40a` infra CG2 clear (`0x100010ac`), `0x40d` I2C6 soft reset (`0x1100e050`) |
| `fd8d3239` | `0x411` to the return | Entry: TOPCKGEN `0x10000048`, the mux update `0x10000004`, APMIXED `0x1000cf38` bit 4 set. Exit: `0x1000cf38` bit 4 clear, `0x10000044`, `0x10000004`, infra `0x100010a8` |

At a stalled store LATCH_0 should carry a PC state bit (`PC_STAL` bit 6 or
`PC_INCR` bit 5) with `IM_REDY` (bit 9), unlike `04248000`. Within the last
window the markers split it: `SW_DEBUG` (`0x604`) is cleared at `0x413`;
`SW_RSV_0` (`0x608`) is 0 at `0x419` and `0x433` and the wake status at
`0x4f4`; `PASR_DPD_0` (`0x630`) is 0 at `0x416` and `r8` at `0x4f0`; the
three `BSI_D*_SR` words (`0x1000641c`-`0x10006424`) are written only at exit.
Whether they survive a TOPRGU reset is untested.

| Outcome | Reading |
| --- | --- |
| Boot2 with latches unlike D5x's | The program's position at the hang, by window (below) |
| Boot2 with D5x's values (`04248000`, `0`, `ffffffff`) | Ambiguous: before word `0x402` of the hung period, or nothing latched (D5l read the same after returned periods) |
| Smi saved `ffffffff` | The guard refused; the DCM is still untested |
| Transmit or interrupt count rises during window C | The UART was active; item 2 comes back |
| Every window passes | Repeat once before reading it |

**UART check (custodian, e367f52b, read-only).** `ttyS0` is not an active
console: `/proc/consoles` lists only `tty1` and `ramoops-1`, and the boot log
disables the legacy `ttyS0` console at 13.96 s despite `console=ttyS0` on the
command line. The 8250 driver's file is `/proc/tty/driver/serial_8250`
(`0: uart:ST16650V2 mmio:0x11002000 irq:208 tx:0 rx:0`), and IRQ 208 has no
line in `/proc/interrupts` because no process holds the port open. The kernel
does not drive the UART during the windows, so **item 2, the UART sleep
handshake, is closed**. Run 2's per-period `ttyS0 tx:-` fields carry no
information; the SMI word on the same lines does.

### D5z run 2: period 3 hung; the SMI async DCM was already on (custodian, 2026-11-22)

**Approved** by the owner in the custodian's session, with the four extra
reads.

**Setup.** Boot2 e367f52b, pre-module latches 0. Module 659c86b4 (0838),
`d4.sh` blob 840458dd, D5z's env. Battery 90 %, cable out.

**Observed.**
- At the blank: `sodi mm: cg0 3f9f8000 cg1 ffffff03`, then `gated, cg0
  3f9fc000 cg1 ffffffd3, SODI terms 00000000 00000000`. The values before
  gating match D5y's, not D5z's (`00110000`, `ffffff00`). Either way the
  terms were 0 once gated.
- Pings from 12:13:05. Periods 1 and 2 returned (`r12` `00400020`, CONN2AP
  through SYS_CIRQ, 293 and 184 ms, `im` FSM `02448910`). Period 3 started
  at 12:13:08, the second of the last ping reply, and never returned.
- `smi async saved 01c4c41f` after both periods. `sodi_smi_async_val` holds
  the word read before the module's write, so `SMI_COMMON_ASYNC_DCM`
  (`0xc000`) was already set and the write changed nothing.
- `ttyS0 tx:-`, as expected.
- Hang called at 12:13:22; the device came up in Gemian (fa818c64) at
  12:14:08. The clip state is unconfirmed. On the next boot2 (608ff693),
  before any module, every latch and marker read its default: `6190`-`61c8`
  0, `6600`-`6614` 0, `6618`/`661c` `ffffffff`, `0x630` 0,
  `0x1000641c`-`424` 0, TOPRGU `0x15`. `/var/lib/systemd/pstore/` held no new
  file. Gemian's copy of the RAM console (kept privately) ends at 4872.21 s,
  the station journal at 4872.27 s.

**Result.**
- **The SMI async DCM is closed**: mainline already runs with it on, so the
  vendor's write is a no-op here. With MP2 also refuted (D5z) and the UART
  idle, items 1-3 of the vendor-difference list are done.
- Seven hangs with CPU0 alone: periods 1, 11, 1, 28, 14, 7 and 3. None has
  reached boot2 after the hang.

**What the next run waits on.** Whether the clip was on between 12:13:22 and
12:14:08 decides the evidence path. If it was off, the procedure stands and
the next run needs the clip confirmed on at the call. If it was on, a SODI
hang's reset does not take the held-key path that D5x's watchdog reset took,
and the latches cannot be caught this way. Gemian's log of its fa818c64 boot,
if kept, may show the boot loader's reset reason; reading it is bounded
read-only Gemian inspection.

### The remaining vendor differences, and CPU0's interrupts (SPM program session, 2026-11-22)

Inference from the program listing and the module's source.
- **Item 4, the PMIC wrapper phase, cannot matter.** With flag bit 3 the
  program never writes `SPM_DVFS_CON`; the wrapper's sleep commands follow
  `SRCVOLTEN`, which only the 26 MHz handler drops, and the CG path does not
  enable it.
- **Item 5, the four `pwrctrl` registers, cannot stall a store.** They
  route wakes and aborts; nothing in the hung window waits on them.
- **Item 6.** The GPT wake is not a stall source. The VCORE DVFS re-kick
  matters only with a VCORE DVFS program running; the station's
  configuration has none, and this module loads the only SPM programs.
- **The live lead: CPU0's own interrupts.** The module's GIC mask disables
  SPIs only. CPU0's SGIs and PPIs live in the redistributor and stay
  enabled. The vendor masks every interrupt but the SPM's, so CPU0 stays in
  WFI until the program returns. The program never checks that CPU0 is in
  WFI: it holds the master pause from `0x43e` and stops the ARM clock at
  `0x590`. A PPI or SGI in that window, a millisecond or two, would bring
  CPU0 out of WFI to read `SPM_IRQ_STA` under the pause and go back to WFI,
  and stopping the clock with that read outstanding could wedge MCUSYS.
  That would leave the backstop unable to fire, and it fits a hang at a
  random period.
- A lower-odds difference: the module sets `ACINACTM` on MP0 and MP1 before
  the PCM reset; the vendor sets it just before WFI and clears it right
  after the wake.

**Checked against the kept logs (D5w, run 3, D5y, D5z, D5z run 2).** Every
returned period has `loops=0` and `backstop=0`, so no returned period saw
CPU0 leave WFI early. That does not clear the lead: if every early wake
hangs, no returned period can show one. Every entry reads `rd en 408000ff
pend 01000000`. The enabled set is SGIs 0-7, PPI 23 (the PMU) and PPI 30,
the physical timer, which carries the kernel's tick and the module's
backstop; PPI 27, the virtual timer, is off. The SODI state has no
`CPUIDLE_FLAG_TIMER_STOP`; the module saves CNTP, re-arms it as the backstop
100 ms past the PCM timer, and restores it after.

### Request D5aa (proposed): CPU0's SGIs and PPIs masked for the period

0839 adds `sodi_mask_ppi`. After the SPI mask, it disables CPU0's SGIs and
PPIs in the redistributor's `GICR_ICENABLER0`, waits for `GICR_CTLR.RWP`,
and enables the saved set again in `spm_gic_restore`. The SPM's return
interrupt is then the only thing that can wake CPU0, as in the vendor's
entry. The backstop can no longer end a period, which it never has in a
returned period anyway. `d4.sh` adds `D4_MASK_PPI=1`.

- **Candidate:** a new module from a Buildbox build with 0839; no boot2
  write. Boot2 608ff693 (latches 0), CPU0 alone, `D4_CIRQ_LEVEL=1
  D4_NO_EVENT=1 D4_MARK=1 D4_MM=2 D4_MASK_PPI=1`, two states, no cap, lid
  open, cable out, timestamped pings. MP2 and the SMI word go back to the
  D5y behaviour, since both are closed.
- **New writes:** `GICR_ICENABLER0` and `GICR_ISENABLER0` for CPU0, each
  period. They need the owner's approval.
- **At a hang call** the clip goes on as before, with the same reads after a
  boot2.

| Outcome | Reading |
| --- | --- |
| All three windows pass (about 180 periods; seven hangs came within 1-28) | CPU0's interrupts are the lead; repeat, then the PPI or SGI that fires can be found |
| A hang | CPU0 leaving WFI is not the cause; the `ACINACTM` timing is next |

**Before D5aa: is anything counting on the PMU? (SPM program session.)** The
lead needs a wake between the kick and `0x590`, at the very start of the
period. No timer can fire there: the kernel's tick is on CNTP, which the
module moves past the period. A self-IPI before the period would be pending
at entry and refused. That leaves the PMU overflow, PPI 23. The PMU driver
is bound on the station (0646; `armv8_pmuv3`, 7 counters), and the kernel
has no hard-lockup detector (`CONFIG_HARDLOCKUP_DETECTOR` unset), so only
a running perf user could make it fire. Two read-only reads on the station
decide whether D5aa tests anything: CPU0's count on the PMU's line in
`/proc/interrupts`, and any process holding a `perf_event` descriptor. With
the count at 0 and no holder, D5aa is expected to hang and is skipped for
the `ACINACTM` timing: set it just before the first `wfi` and clear it right
after the loop, as the vendor does.

### D5aa skipped: nothing counts on the PMU (custodian, 2026-11-22)

Read-only, on boot2 608ff693 (10 min up, all eight CPUs, no module): the
PMU's line (`GICv3 23 Level arm-pmu`) reads 0 on every CPU; no process holds
a `perf_event` descriptor; `/proc/sys/kernel/nmi_watchdog` does not exist.
`d4.sh` starts no perf user. With no timer, no PMU overflow and no pending
SGI possible in the kick-to-`0x590` window, D5aa would test almost nothing,
and it is skipped. 0839 stays in the series for a later need; the Buildbox
build of 167d98880 that was already running is not staged.

### Request D5ab (proposed): ACINACTM set only around WFI

0840 adds `sodi_acinactm_late`. The early write and readback of `ACINACTM`
on MP0 and MP1 stays, so a period is still refused before any SPM change if
MCUCFG ignores it, but the saved words go straight back. `ACINACTM` is set
again after the kick, the GIC mask and the backstop, just before CPU0's
first WFI, and cleared right after the wait loop, before SYS_CIRQ is
disabled: the vendor's order. `d4.sh` adds `D4_ACINACTM_LATE=1`.

- **Candidate:** a new module from a Buildbox build with 0840; no boot2
  write. Boot2 with latches 0, CPU0 alone, `D4_CIRQ_LEVEL=1 D4_NO_EVENT=1
  D4_MARK=1 D4_MM=2 D4_NO_MP2=1 D4_ACINACTM_LATE=1`, two states, no cap,
  lid open, cable out, timestamped pings. `D4_NO_MP2=1` matches the
  vendor, which touches only MP0 and MP1.
- **New writes:** none to new registers; the same `MP0`/`MP1_AXI_CONFIG`
  writes at new points in the period, which need the owner's approval.
- **At a hang call** the clip goes on as before, with the same reads after a
  boot2.

| Outcome | Reading |
| --- | --- |
| At least 50 periods with no hang, summed over windows | The entry-long `ACINACTM` is the lead; repeat |
| Fewer clean periods, then a stop with no hang | Not decided: seven hangs came at a mean of about 9 periods, so 45 clean ones happen by chance about 1 % of the time |
| A hang | The module's entry now matches the vendor's on every listed difference; the latches, if caught, are the next evidence |

**Already settled for this run (SPM program session's questions).**
- The program assumes the DRAM PHY configuration mux (`CLK_CFG_0` bits
  17:16) at index 1: it clears both bits on entry and sets bit 16 on exit.
  Every logged period reads `clk_cfg_0=01010101` before and after, so it
  is at index 1 and the program leaves it as found.
- No CPU DVFS engine runs outside the kernel: the station uses
  `cpufreq-dt`, and no FHCTL node is bound, so nothing else drives the ARM
  PLLs the program cuts.
- The self-IPI case is closed: `spm_gic_pending` runs after the SPI mask and
  nothing prints between it and the WFI.

**If D5ab hangs**, the next module change is a breadcrumb in `SW_RSV_2`
(`0x10006610`), which `pcm_sodi` touches only with flag 9 clear: one stage
value before the kick, after the wait loop, after the SPM restore and after
the last restore. With the program's state it separates a freeze in the
program from a CPU0 hang after the return, which nothing has ruled out. A
`pcm_deepidle` control on the same entry is the other option, if admitted.

### D5ab: period 2 hung with ACINACTM set only around WFI (custodian, 2026-11-22)

**Approved** by the owner in the custodian's session.

**Setup.** Boot2 608ff693, pre-module latches 0. Module 77237991 (Buildbox
fb75e5826, 0840), `d4.sh` blob f98469b0 with `D4_CIRQ_LEVEL=1 D4_NO_EVENT=1
D4_MARK=1 D4_MM=2 D4_NO_MP2=1 D4_ACINACTM_LATE=1`. Battery 70 %, cable out.

**Observed.**
- At the blank, the same MMSYS values as run 2; the terms gated to 0.
- Pings from 13:23:25. Period 1 (CPU0 at 1339 MHz) returned: `r12`
  `00400020`, 103 ms, CONN2AP through SYS_CIRQ, `im` FSM `02c48910`.
  Period 2 started at 13:23:27 (1547 MHz), the second of the last ping
  reply, and never returned. One clean period: no pass.
- No line confirms the parameter: `d4.sh` logged only `sodi_cirq_level`
  back from the module. `insmod` refuses an unknown parameter and the
  script checked the module holds it, so it was set, but this is inference.
- Hang called at 13:23:41; Gemian (d17d9fa7) at 13:24:27; clip unconfirmed.
  On boot2 ad22b7b1, before any module, every latch and marker read its
  default, TOPRGU `0x15`. Gemian's copy of the RAM console holds one SODI
  entry and nothing later.

**Result.**
- **Moving `ACINACTM` to the vendor's points does not prevent the hang.**
  The module's entry now matches the vendor's on every difference listed.
- Eight hangs with CPU0 alone: periods 1, 11, 1, 28, 14, 7, 3 and 2.
- Three runs in a row have landed in Gemian with the clip unconfirmed, so
  the latch and marker reads have given nothing since D5x.

### Request D5ac (proposed): stage lines in the RAM console

The RAM console is the one record that has survived every reset into
Gemian: its last line is always the previous period's dump. 0841 adds
`sodi_crumbs`, one kernel line at each stage of a period: before the PCM
kick, after the wait (`back`, with `returned` and the WFI loop count),
after the SPM restore and at the end. The last line kept after
a hang says where CPU0 stopped, with no clip and no latch. `d4.sh` adds
`D4_CRUMBS=1`, and now logs every parameter it passes as the module reads
it back.

**A print can wake CPU0 (SPM program session).** With interrupts off,
printk still queues irq_work for the log readers, which raises a self-SGI.
A print before the pending check would make it refuse every period, so
there is no line at the period's start. The `kick` line leaves an SGI
pending into the period, where it would take CPU0 out of WFI, the case
D5aa was to exclude. So D5ac also sets 0839's `sodi_mask_ppi`: the SGI stays
pending until `spm_gic_restore`. Returned periods should still show
`loops=0`; more means a wake got through. `d4.sh` refuses `D4_CRUMBS=1`
without `D4_MASK_PPI=1`.

- **Candidate:** a new module from a Buildbox build with 0839 and 0841; no
  boot2 write. Boot2 ad22b7b1, CPU0 alone, D5ab's env plus `D4_MASK_PPI=1
  D4_CRUMBS=1`, cable out, timestamped pings. After the reset, wherever it lands, the RAM
  console copy (Gemian's or `/var/lib/systemd/pstore/`) before anything
  else; the latch reads too if it is boot2.
- **New writes:** 0839's `GICR_ICENABLER0` and `GICR_ISENABLER0` for CPU0,
  each period, which need the owner's approval.

| Last line kept for the hung period | Reading |
| --- | --- |
| None after the previous period's dump | CPU0 stopped before the kick, in the module's entry checks or saves |
| `kick` | CPU0 stopped during the period: in the program's window or in WFI |
| `back` | The program returned, or CPU0 left WFI; CPU0 stopped in the SPM restore |
| `restored` | CPU0 stopped in the gate, AXI or SMI restores |
| `done` | The period finished; the hang came after `spm_run` |

**If `kick` is the last line.** D5p's PCM watchdog never woke anything, so
the program is frozen, not waiting. The sharpest next test patches the copy
of `pcm_sodi` the module loads, replacing one call with the program's no-op
word: without the clock cut and its restore (`0x472`, `0x4f5`), or without
the master pause (`0x43e`), each to the 50-period rule. It changes the
vendor's firmware image in RAM, so the owner admits it first, and the
patched image stays private. A cheaper side check is one deliberate TOPRGU
reset with the clip on after writing known values to `SW_RSV_2` and
`BSI_D0`, as D5x did for the latches: if they survive, the program's own
writes to `SW_RSV_0` and the `BSI` registers become a record of where it
stopped.

The lines add time on CPU0 at each stage, outside the program's window, and
could shift the hang; a pass would itself be informative.

### D5ac: the hung period's last line is the kick (custodian, 2026-11-22)

**Approved** by the owner in the custodian's session, with 0839's mask.

**Setup.** Boot2 ad22b7b1, pre-module latches 0. Module e85c08a3 (Buildbox
4a9a2db47, 0839-0841), `d4.sh` blob 46248d9f with `D4_CIRQ_LEVEL=1
D4_NO_EVENT=1 D4_MARK=1 D4_MM=2 D4_NO_MP2=1 D4_ACINACTM_LATE=1
D4_MASK_PPI=1 D4_CRUMBS=1`; the log reads every parameter back as set.
Battery 82 %, cable out.

**Observed.**
- Pings from 15:22:03. Periods 1-8 returned, each with `loops=0` (period 8:
  329 ms, CONN2AP through SYS_CIRQ, `r12` `00400020`); kick to `back` took
  330-340 ms in periods 7 and 8. Period 9 hung. Eight clean periods: no
  pass.
- Gemian's copy of the RAM console (kept privately) ends:
  `crumb 8: back, returned=1 loops=0`, `restored`, `done`, period 8's
  `sodi cg` and `sodi cirq` lines, then `crumb 9: kick` at 3410.895 s, about
  1.5 s later, the usual gap between periods. The station journal ends
  before it, at 3409.55 s.
- Gemian (6ac0aaeb) came up 46 s after the last ping reply; clip
  unconfirmed. Boot2 39dc8d55 read every latch and marker at its default.

**Result.**
- **The hang is inside the period: after the kick, before CPU0 is back from
  the wait.** CPU0's SGIs and PPIs were masked, so nothing but the SPM could
  wake it; with D5p's silent PCM watchdog, the program is frozen, not
  waiting. The module's exit path is cleared.
- Nine hangs with CPU0 alone: periods 1, 11, 1, 28, 14, 7, 3, 2 and 9.
- The stage lines are the first evidence channel to survive a hang; they
  stay on for the next runs.

### Request D5ad (proposed): the program without its clock cut, then without its master pause

0842 adds `sodi_variant`. After the SHA-256 check, it replaces single-word
calls in the RAM copy of `pcm_sodi` with the program's no-op word, and logs
each word's original value. Variant 1 drops the call at `0x472` (the ARM,
SMI and PLL clock cut with the mux and APMIXED stores) and its restore at
`0x4f5`. Variant 2 drops the infra master pause at `0x43e`; the exit's clear
at `0x519` is harmless with the bit never set. The firmware file is not
changed and no patched image is kept. `d4.sh` adds `D4_VARIANT=1|2`.

The word indices count from IM word 0, the first word after the file's
16-bit word count (1583 words; word `0x400`, the entry, is `1840001f`).
The insmod log must show these originals (SPM program session):

| Word | Original | Instruction |
| --- | --- | --- |
| `0x43e` | `c0c05600` | call `0x2b0`: master pause and a `0x20` wait |
| `0x472` | `c0c0afe0` | call `0x57f`: the mux, APMIXED and ARM/SMI clock and PLL cut |
| `0x4f5` | `c0c0b340` | call `0x59a`: its restore |

Only the call word changes: the delay-slot words after `0x472` and `0x4f5`
are already no-ops, and `0x43f` runs either way. Nothing else calls `0x57f`
or `0x59a`. Variant 1 runs first: variant 2 keeps the clock cut and the
mux switch with bus masters live, which the vendor never does, a mildly
riskier state.

- **Candidate:** a new module from a Buildbox build with 0842; no boot2
  write. Boot2 39dc8d55, CPU0 alone, D5ac's env plus `D4_VARIANT=1`, then a
  second run with `D4_VARIANT=2`, each to the 50-period rule.
- **Admission:** a test variant of the vendor's firmware image in RAM is a
  new kind of test; the owner admits it first. No new register writes.
- After a hang, the RAM console copy first; latch reads if it lands in boot2.

| Variant 1 | Variant 2 | Reading |
| --- | --- | --- |
| Passes | Hangs | The clock cut or its stores freeze the period |
| Hangs | Passes | The master pause freezes it |
| Hangs | Hangs | Something before `0x43e`, or the main wait itself |
| Passes | Passes | Both are needed together; repeat before reading it |

### D5ad variant 1: period 2 hung without the clock cut (custodian, 2026-11-22)

**Approved** by the owner in the custodian's session.

**Setup.** Boot2 39dc8d55. Module b3085139 (Buildbox 29071fe2b, 0839-0842),
`d4.sh` blob 83a516ad with the custodian's guard f6e860ed, D5ac's env plus
`D4_VARIANT=1`.

**Observed.**
- The insmod log shows both originals as expected (`0x472` `c0c0afe0`,
  `0x4f5` `c0c0b340`), each replaced by `17c07c1f`.
- Period 1 returned (kick to `back` about 116 ms). The RAM console's last
  line is `crumb 2: kick` at 2470.792 s. One clean period.
- The guard logged the originals matching at 16:04:56; window C started
  at 16:05:55 and logged period 1 at 16:05:57. The station journal ends at
  16:05:56 with period 1's lines.
- The last ping reply was at 16:05:57; Gemian (057b8c02) was up at
  16:06:58. RAM console copy and journal kept privately.
- **The clip was never on in any run** (owner, 2026-11-22). The latch
  readings from hangs (D5l, D5o part 2, D5m's no-event run) came from
  resets where the owner caught the bootloader; every hang since D5x went
  to Gemian, which clears them.

**Result.**
- **The clock cut and its restore are not needed for the hang.** Ten hangs
  with CPU0 alone: periods 1, 11, 1, 28, 14, 7, 3, 2, 9 and 2.
- Variant 2 moves to the faster reproducer below, if D5ae hangs.

### Independent review of the hangs (2026-11-22)

A separate session reviewed the record, the module, the program listing,
the vendor's SPM sources and the secure firmware, and changed nothing. The
points below were checked against the listing and the vendor's driver here.

**Confirmed.**
- **The flag word differs from the vendor's.** The vendor's MT6797 SODI
  flags are `DIS_SYSRAM_SLEEP` (16), `ENABLE_SODI3` (14) and
  `DIS_SRCCLKEN_LOW` (15), with CG mode (12) added at entry and bit 18 on
  segment 2: `0x0001d000`. The module's are `0x000d3239`. Leaving out our
  test bit 13 (`SODI_NO_EVENT`), eight bits differ: 0, 3, 4, 5, 9 and 19
  set only in ours, 14 and 15 only in the vendor's.
- **Bit 15 is used once.** At `0x41c` the program tests it; if set,
  `0x41f`-`0x420` set `r7` bits 27 and 29, the 26 MHz and infra force-wake
  requests, which the exit clears at `0x52a`-`0x52b`. The vendor's SODI
  keeps both forced awake for the whole period; ours never did. The D5y
  comparison compared code paths and missed this flag.
- **Bit 14 is inert in CG mode** (reviewer, from the listing). It is tested
  only at `0x12e`, in the EV9 handler, where it arms the SODI3 stage's
  further vectors. EV9 is enabled only without CG mode, so the vendor's
  bit 14 does nothing in its CG-mode SODI either.
- **Bit 13 is already settled on the reproducer.** With it set (every
  `d4.sh` run since D5n) the program enables no event vector and waits
  with `r12` 0, a path the vendor's word never takes. But D5m hung with it
  clear and D5m's no-event run hung with it set, both timer-only with
  Wi-Fi joined, so it is not the cause on its own.
- **Bit 0 (CPU stays powered) is not in any vendor entry on this chip.** It
  appears only in disabled legacy-sleep and FPGA paths. The vendor's CPU0
  goes down through PSCI first; ours sits in WFI with retention armed while
  the program cuts its clock and PLLs. Clearing it is S2, which needs an
  image.
- **`SPM_AP_STANDBY_CON`**: the module writes the vendor's suspend value
  `0x04080011` (MP3 idle masked); the vendor's SODI value is `0x04080001`.
  Minor, untested.

**Corrections to this record.**
- "**Frozen, not waiting**" (D5ac) is too strong. A PCM stalled on a bus
  store would not service its watchdog wake either, so D5p's silent
  watchdog fits a frozen program, a stalled store (the exit does five bus
  stores between the clock restore and the pause release at `0x519`), or
  CPU0 not resuming after the program ends. `0x2b0` requests the master
  pause and waits `0x20` without checking its acknowledgement. With 0839's
  mask the backstop timer cannot wake CPU0, so the reviewer's
  backstop-into-a-held-pause path does not apply to D5ac or D5ad, but the
  three readings stay open. A latch read after a hang would separate them
  (`LATCH_1` places the program).
- The tick argument for the two-state driver does not hold for test
  periods, which run from process context after a 1 s sleep. What the
  driver changes for them is unestablished.
- D5l pinned CPU0 only at the low end (221 MHz); no run pinned it high.
- `r13` at return and the entry frequency do not discriminate: both values
  occur in hanging runs.

**The faster reproducer.** Timer-only wake (`sodi_wake_src=0`), Wi-Fi
joined, no cpuidle driver: D5m, D5m with no events and D5p part 1 all hung
within three periods. With the radios unloaded (D3, 14 periods) or off
(`mem`), timer-only has not hung, and the full wake set without the driver
passed about 800 periods (D5c, D5d). CONN activity during a period that
nothing ends early is the common factor. The reviewer's estimates: missing
force-wake with CONN active about 30 %; the clock and PLL cut under a
retained core 15-20 % (D5ad variant 1 now weighs against it); another pause
or bus cause about 20 %.

**The program session's answers (2026-11-22).**
- `r7` bits 27 and 29 are the 26 MHz and infra force-wake requests (28 is
  APSRC, 30 VRF18). No program word reads `r7` back; they act only in the
  SPM's request arbitration. In our CG path only EV1 drops the clock and
  voltage requests, and EV1 is not enabled, so the program itself never
  drops 26 MHz or infra. Bit 15 can matter only if the hardware
  arbitration drops them with the sources masked; that cannot be ruled
  out from the program, so D5ae stays a fair test.
- The CONN APSRC and DDR handlers (EV6, EV7, EV14, EV15) do not read
  `r7`, and `SODI_NO_EVENT` disables all four.
- After variants 1 and 2, the program's only stores outside the SPM are
  three: `0x40a` ungates I2C_APPM (I2C6's clock) in infra CG2, `0x40d`
  soft-resets I2C6, and `0x511` gates I2C_APPM again at every exit,
  behind the clock framework. The last leaves Linux and the hardware
  disagreeing after the first period; that would hang a later I2C6 access
  outside a period, not inside one, so it does not explain these hangs.

### Request D5ae (proposed): the vendor's bit 15 on the fast reproducer

0843 adds `sodi_keep_26m`, which sets `SW_FLAG` bit 15
(`DIS_SRCCLKEN_LOW`) for test periods and the idle state; `d4.sh` adds
`D4_KEEP_26M=1`. The flag only forces resources on; no new register is
written.

0844 adds variant 3 for the follow-up, in the same build: variants 1 and 2
together plus no-op words over the three outside stores (`0x40a`-`0x40f`,
`0x511`-`0x513`), so the program only sets its timer, waits and exits.
`d4.sh` takes `D4_VARIANT=3`. The insmod log must show the originals
`e8208000 100010ac 00000002`, `e8208000 1100e050 00000001` and
`e8208000 100010a8 00000002` besides the three calls.

- **Candidate:** a module from a Buildbox build with 0843; no boot2 write.
  Boot2 39dc8d55, CPU0 alone, Wi-Fi joined, `D4_WAKE=0 D4_IDLE=0` with
  D5ac's env (`D4_MASK_PPI=1 D4_CRUMBS=1`, so a hang still leaves its stage
  line) plus `D4_KEEP_26M=1`.
- **Pass rule:** 20 clean periods. The reproducer hung by period 3 in 3 of
  3 runs; at a hang rate of even 0.25 per period, 20 clean periods happen
  by chance under 0.4 % of the time.
- **Admission:** a SODI flag value the program has not run with here, so the
  owner admits it first. D5ad variant 2 on the two-state setup is withdrawn
  in its favour.
- After a hang: the RAM console copy first. The clip has never been on,
  so a hang lands in Gemian and the latches are lost unless the owner
  holds the side key for the reset.
- **Started** 2026-11-22 18:56 on boot 5ea39fb6: module d157e512
  (Buildbox 1d7d434ea), `d4.sh` blob 0a0567a2, env `D4_WAKE=0 D4_IDLE=0
  D4_CIRQ_LEVEL=1 D4_NO_EVENT=1 D4_MARK=1 D4_MM=2 D4_NO_MP2=1
  D4_ACINACTM_LATE=1 D4_MASK_PPI=1 D4_CRUMBS=1 D4_KEEP_26M=1`, cable out,
  battery 78 %.

| Result | Reading | Next |
| --- | --- | --- |
| Passes 20 | The missing force-wake is the likely cause | The same env without `D4_KEEP_26M`, to confirm the reproducer still hangs with this module; then the two-state setup with it, to the 50-period rule |
| Hangs | Not bit 15 alone | D5ad variant 2 on this reproducer, then variant 3. If variant 3 hangs, the program's own actions are cleared and the SPM's WFI and idle handshakes, or the missing CPU power-down, remain: the reviewer's CPU0 retention check (`MCUCFG` SPARK enable off around the period, a new register write needing its own admission), the radios-unloaded control, or S2 |

Clearing bit 0 with a PSCI entry (S2) remains the vendor's configuration
and the likely end state; it needs a new image and comes after the cause
is found or the module tests run out.

### D5ae: 60 of 60 clean periods with bit 15 (custodian, 2026-11-22)

**Approved** by the owner in the custodian's session.

**Setup.** Boot 5ea39fb6, module d157e512 (Buildbox 1d7d434ea), `d4.sh`
blob 0a0567a2, env as started above; every parameter read back as set
(`sodi_keep_26m` Y, `sodi_idle` N, `sodi_wake_src` `00000000`). CPU0
alone, Wi-Fi joined, pings throughout window C.

**Observed.**
- Window C, 18:57:13-19:00:46: 0 of 60 periods ended early. Every period
  woke by the PCM timer (`returned=1`, backstop 0, `loops=0`, `r12`
  `00000001`); the program hash was unchanged after the window. The
  crumbs show kick, back, restored and done for all 60.
- Per period: `timer_out` `00010003`, `idle` `000001f7`, `event`
  `90100000`, no IM FSM stall.
- Ping loss 0.5 % (6 of 1200), average 128 ms.
- The script then stopped in window A ("pings still arriving after
  300 s"), because the custodian's ping run outlasted window C. Not a
  device fault: CPUs and the gadget were restored, taint 0, no warning
  lines, station up. The module stayed loaded (corrected by the
  custodian); `d4.sh` unloads it at the start of the next run.

**Result.**
- **Pass:** 60 clean periods against a rule of 20, on a setup that hung
  by period 3 in 3 of 3 earlier runs (D5m, D5m no-event, D5p part 1).
- *Not yet shown:* that this setup still hangs with today's module and
  env without bit 15. D5m and D5p ran an older module without the SYS_CIRQ
  acknowledgement, 0839's mask, ACINACTM late or `D4_NO_MP2`, and `d5m.sh`
  rather than `d4.sh`. The control below decides whether bit 15 is the
  cause.

### Request D5af (proposed): the D5ae control without bit 15

- **Candidate:** the same module and `d4.sh`, boot 5ea39fb6 or a later
  boot of the same boot2 image, D5ae's env without `D4_KEEP_26M`. Pings
  stop when window C ends, so windows A and B can run.
- **Admission:** a configuration run before (D5ac's flags, timer-only); the
  owner approves the run.
- **Budget:** one window C of 60 periods; a hang ends it. RAM console copy
  first after a hang.

| Result | Reading | Next |
| --- | --- | --- |
| Hangs | Bit 15 avoids the hang: the missing 26 MHz and infra force-wake is the cause, most likely an SPM request drop under CONN activity | The two-state setup (D5ac's env) with `D4_KEEP_26M=1`, to the 50-period rule; then bit 15 becomes the module's default and the record's S2 plan carries it |
| Passes 60 | Today's module no longer hangs on this setup; D5ae says nothing about bit 15 | The two-state setup with and without bit 15, to the 50-period rule each |

### D5af: 60 of 60 clean periods without bit 15 too (custodian, 2026-11-22)

**Approved** by the owner in the custodian's session.

**Setup.** Boot 5ea39fb6, module d157e512, `d4.sh` blob 0a0567a2, D5ae's
env without `D4_KEEP_26M`, pings over window C only.

**Observed.** Window C, about 19:23-19:27:22: 0 of 60 periods ended early,
every one on the PCM timer (`r12` `00000001`, 2000 ms), program hash
unchanged, 270 of 270 pings answered. The window's CONN count was 60
periods, against 58 in D5ae.
Window A, 19:27:28-19:28:42: 0 of 20 ended early. Window B,
19:28:43-19:33:46, no key pressed: 79 periods, no key wake. No refusals,
CPUs 0-7 back, taint 0: **159 clean periods** in all, every one a timer
wake.

**Result.**
- **Pass.** Today's module and `d4.sh` no longer hang on the timer-only,
  no-driver setup, so **D5ae says nothing about bit 15**, and D5ag is
  withdrawn.
- What differs from the three earlier hangs on this setup (D5m, D5m
  no-event, D5p part 1):
  - **Period length:** `d5m.sh` ran 200 ms periods (`timer_out`
    `0000199c` in D5p); `d4.sh` runs 2000 ms.
  - **Start:** `d5m.sh` began about 1 s after the last CPU went offline,
    with periods back to back; `d4.sh` waits 5 s, then for pings, with
    about 1.5 s between periods.
  - **Module:** since 0826 the module gained the SYS_CIRQ acknowledgement
    (D5t), level-triggered SYS_CIRQ, 0839's PPI mask, ACINACTM only around
    WFI, MP2 left alone, the MMSYS gates closed and the stage lines.
    `SODI_NO_EVENT` is not among them: D5m's no-event run hung with it.
- The reviewer sees no length-dependent path in the program: entry and
  exit are the same for any timer value, and only the wait at `0x498`
  lasts longer. The hang rates fit a hazard per entry or exit, or one tied
  to what came just before the entry, more than one growing with time in
  the wait.
- The two-state setup still hangs with every one of those module changes
  (D5ab, D5ac, D5ad variant 1), so it is now the only live reproducer.
  Its control without bit 15 already exists: D5ac's env hung in period 9
  (D5ac) and, with variant 1, in period 2. 0842-0845 are inert unless
  selected.

### Request D5ah (run, hung): bit 15 on the two-state setup

- **Candidate:** module d157e512 (Buildbox 1d7d434ea), `d4.sh` blob
  0a0567a2. D5ac's env (`D4_CIRQ_LEVEL=1 D4_NO_EVENT=1 D4_MARK=1 D4_MM=2
  D4_NO_MP2=1 D4_ACINACTM_LATE=1 D4_MASK_PPI=1 D4_CRUMBS=1`, two states)
  plus `D4_KEEP_26M=1`. Pings stop when window C ends.
- **Pass rule:** 50 clean periods, summed over windows. Ten hangs in this
  setup without bit 15 came at periods 1-28; at the observed rate (about
  one in nine periods) 50 clean periods happen by chance under 0.5 % of
  the time.
- **No separate control run:** D5ac is the same env without the flag.
- **Timer (program session):** the SODI path never reads or compares
  `PCM_TIMER_VAL`; it only arms the timer (`0x410`), disarms it (`0x517`)
  and copies `PCM_TIMER_OUT` at exit. Its one time-dependent branch is the
  early abort at `0x434`-`0x436` and `0x456`: a wake already pending skips
  the pause, the clock cut and the wait. Two-state idle entries can be as
  short as one tick (about 30 µs) and may take it; 2000 ms test periods
  never do. The `0x514` watchdog store runs after the wake.
- **Admission:** the same flag value D5ae ran; the owner approves the run.

| Result | Reading | Next |
| --- | --- | --- |
| Passes 50 | Bit 15 avoids the hang in the two-state setup | Make bit 15 the module's default; then the split (variants 4 and 5) if worth knowing, and a longer idle soak |
| Hangs | Not bit 15 | `d5m.sh` unchanged on today's module with `D5M_RESET=0` (no deliberate reset), up to three runs of its three 200 ms periods, no new code. If it hangs, the fast reproducer is back: split the short gap, the early start and the length, in that order. Then D5ad variants 2 and 3 on whichever setup hangs |

**The program session on the arbiter (2026-11-22).**
- The vendor's SODI flags always include bit 15, so D5ae ran the vendor's
  configuration; every earlier SODI period here ran a mode the vendor
  never uses.
- In CG mode no program handler serves the 26 MHz or infra arbiter events
  (only APSRC's, EV14 and EV15), so without bit 15 both are left to the
  SPM's hardware arbiter.
- Our `SPM_SRC_MASK`, `SPM_SRC2_MASK` and `SPM_SRC_REQ` match the vendor's
  SODI fields; `SPM_AP_STANDBY_CON` adds the MP3 idle mask.
- **The likeliest drop is infra.** `SPM_SRC_MASK` lets only the CONN and
  modem APSRC (DRAM) requests hold the infra channel, not CONN's
  SRCCLKENA. With Wi-Fi joined but between DRAM accesses, CONN holds
  26 MHz and drops APSRC, so infra can sleep while CPU0 is in WFI. The
  26 MHz channel's holders are boot values in `SPM_CLK_CON` bits 16-29,
  undecoded. *Inference.*
- The two force-wakes are separate channels and split with one program
  word each.
- **The 26 MHz request to the PMIC cannot drop in a period.** With
  `PCM_PWR_IO_EN` `0x81`, SRCLKENA0 follows `r7` bit 14, which starts set
  from `SPM_POWER_ON_VAL1` (`0x15830` here) and which the SODI path never
  writes. So bit 27 can only pin the arbiter's internal 26 MHz state,
  whose effect the vendor's source does not say. *Inference.* Infra stays
  the lead, and no live register read is needed.
- **`SPM_CLK_CON` divergence, not ranked as a cause.** It reads `0x8000`
  at boot (the reset value; `0x8040` in a period). The vendor's SPM init
  also sets bits 2, 3, 12, 16 and 27, the modem's SYSCLK1 and CLKSQ1
  control and two source masks; CONN is not among them, and the modem is
  off here. `SPM_AP_STANDBY_CON` bit 23 makes no difference with
  `SPM_SRC_MASK` bit 16 clear.

0845 adds variants 4 and 5 for that split, with `sodi_keep_26m`: 4 drops
`0x41f` (26 MHz force-wake; original `a1dd8407`), keeping only infra's;
5 drops `0x420` (infra; original `a1de8407`), keeping only 26 MHz's.
Neither word is a branch target or a delay slot. `d4.sh` takes
`D4_VARIANT=4|5` only with `D4_KEEP_26M=1`.

**D5af started** 2026-11-22 19:22 on boot 5ea39fb6: module d157e512,
`d4.sh` blob 0a0567a2, D5ae's env without `D4_KEEP_26M`, pings over
window C only.

### Request D5ag (withdrawn: D5af passed): which force-wake avoids the hang

- **Candidate:** a module from a Buildbox build with 0845; D5ae's env with
  `D4_VARIANT=4` (infra only), then `D4_VARIANT=5` (26 MHz only), one
  window C of 60 periods each, pings stopped after window C.
- **Admission:** program variants in RAM, as D5ad; the owner admits them.
- Runs only if D5af hangs; if D5af passes, D5ae's reading is void and the
  two-state comparison comes first.

| Variant 4 (infra only) | Variant 5 (26 MHz only) | Reading |
| --- | --- | --- |
| Passes | Hangs | The infra channel drops with CONN active: the inferred path |
| Hangs | Passes | The 26 MHz channel drops; decode `SPM_CLK_CON`'s holders |
| Passes | Passes | Either force is enough |
| Hangs | Hangs | Both are needed |

### D5ah: bit 15 hangs the two-state setup in period 13 (custodian, 2026-11-22)

**Approved** by the owner in the custodian's session.

**Setup.** Boot 5ea39fb6, module d157e512, `d4.sh` blob 0a0567a2, env as
requested (D5ac's plus `D4_KEEP_26M=1`), two states. Started 21:25:09,
cable out, battery 67 %, pings over window C only (270 sent).

**Observed.**
- 12 clean periods, then a hang in period 13 of window C. Pings from about
  21:26:10; the last reply came at 21:27:30.
- No clip: the chip landed in Gemian (boot ddf94cbc) at 21:28:28, so no
  latches. Gemian powered off at 21:30:24; the station's `d4.log` section
  is saved on its next boot.
- The RAM console, kept privately (65764 B), ends at `sodi crumb 13:
  kick` (printed just before the kick) with no `back`, the same crumb as D5ac and
  D5ad variant 1.
- Period 12, the last good one: `returned=1 backstop=0`, `r12`
  `00400020` (CONN2AP), `timer_out` `00000fd0`, misc 0, the next local
  timer event 399 µs after entry, `im fsm` `02c48910>02448910`, not
  stuck.
- D5ae and D5af periods (timer only, no driver) ended instead with `r12`
  `00000001`, misc `00080000` and `timer_out` `00010003`.

**Result.**
- **Hang: bit 15 does not avoid it.** The forced 26 MHz and infra wakes
  are not the cause in the two-state setup. Eleven hangs on this setup
  now fall at periods 1-28.
- The two-state periods end early on CONN2AP, but that wake alone is not
  the trigger: no-driver runs with the same default wake set passed
  (D5c 427 periods, D5d 377, the IM reference). The split since D5d
  stands: the hazard comes with the two-state cpuidle registration.
- **Next, by the D5ah table:** `d5m.sh` unchanged on today's module with
  `D5M_RESET=0`, rmmod first or a fresh boot, up to three runs. It asks
  whether the no-driver, timer-only 200 ms hang (D5m, D5p part 1) still
  exists with today's module. If it hangs, it is a three-period
  reproducer without the driver, and the gap, the early start and the
  length are split in that order. If three runs pass, the two-state
  registration is the only reproducer, and D5ai, then D5ad variants 2 and
  3, run on it.

**Reading the `kick` crumb (reviewer).** The `kick` line is printed
before the kick, and the next line is `back`. A hang at `kick` therefore
lies anywhere from the two `PCM_CON0` writes through the SYS_CIRQ enable,
the GIC and GICR masks, the CNTP arming, the ACINACTM writes and the WFI
loop. It does not show that CPU0 reached WFI or that the hang is in the
wait.

### Request D5ai (proposed): the two-state setup with the governor held at state 0

The one known discriminator is the state count: one state, or no driver,
passed about 2200 periods; two states hang about once in nine. The period
path is the same in both cases: `sodi_idle_wfi` is a bare `dsb`/`wfi`, and
the SODI state carries `CPUIDLE_FLAG_OFF`. The difference is in the idle
loop between periods, read from this tree (7.x):
- **One state or no driver:** `cpuidle_idle_call()` skips the governor.
  It stops the tick only when the last wake was a tick (`got_tick`), and
  otherwise retains it.
- **Two states:** menu runs. It calls `tick_nohz_get_sleep_length()` when
  its prediction is long or the tick is stopped, and it retains the tick
  whenever the predicted idle is under a tick (4 ms at `HZ=250`). Wi-Fi
  interrupts keep that prediction short.
- **Two states with a CPU latency request of 0:** menu takes its early
  return, always state 0, with the tick stopped (WFI is not a polling
  state). This is **not** the one-state behaviour: it never retains the
  tick, where one state retains it after every non-tick wake.

The test needs no code. Hold `/dev/cpu_dma_latency` open at 0 for the
whole run from a detached process, started before `d4.sh`:

    setsid sh -c 'exec 3>/dev/cpu_dma_latency; printf "\000\000\000\000" >&3; exec sleep 7200' </dev/null >/dev/null 2>&1 &

Reading the device returns the aggregate target, which must read 0. Kill
the holder after the run.

- **Candidate:** module d157e512, `d4.sh` blob 0a0567a2, D5ac's env (D5ah's
  without `D4_KEEP_26M`), two states, pings over window C only.
- **Pass rule:** 50 clean periods, as D5ah.
- **Order:** after `d5m.sh`, before D5ad variants 2 and 3.
- **Admission:** a new kind of condition, a kernel QoS request with no
  register write; the owner approves it.

| Result | Reading | Next |
| --- | --- | --- |
| Passes 50 | Menu's tick handling between periods leads to the hang, not the registration as such. One state also retains the tick after Wi-Fi wakes, so the factor is narrower: menu's retained-tick choices, or its `tick_nohz_get_sleep_length()` calls | Look at what the entry inherits (the pending CNTP event, the time since the last wake); a two-state run with the tick forced on would separate the two |
| Hangs | The governor's tick decision is not it | D5ad variants 2 and 3 on the two-state setup |

**The program session on what follows the kick (2026-11-22).**
- **No sticky CONN2AP.** With bit 0 set, the program checks for a pending
  wake once, at `0x434`. After the wait (`0x49b`-`0x4aa`), `0x4ad` tests
  `r12` bit 10, the SCP-to-SPM interrupt. Every other wake, CONN2AP
  included, exits after one pass.
- **An SCP wake loops the program.** Bit 10 is in the default wake set
  (`0x0f57c5f5` includes `0x400`), which D5ac and D5ah used; `d5m.sh`'s
  `sodi_wake_src=0` excludes it. When `SPM_SW_RSV_3` (`0x10006614`) has
  a zero upper half, which is the mainline value unless something writes
  it, the program runs the SCP DVFS handshake (`0x4c4`-`0x4e2`):
  - it stores 0 to `0x100a0020`, in the SCP block (`0x4d9`; `0x4bc` on the
    other branch);
  - it sets bit 3 in `SW_RSV_3`;
  - it re-arms and waits again, so the period does not end.

  An unclocked SCP block could stall the bus on that store, and an SCP
  line left asserted would loop the program without SW_INT. *Inference;*
  D5c and D5d passed with the same wake set and no driver, so this fits
  only if two states make SCP wakes likelier. Its signature can be
  checked: `SW_RSV_3` bit 3 after clean periods shows the path has run,
  and any returned period with `r12` bit 10 set would show an SCP wake.
- **A wake pending at entry** takes the normal exit within microseconds of
  the kick. Checked in the module: the period runs with IRQs masked at
  the CPU (no pseudo-NMI in this build), `spm_gic_mask()` keeps the SPM's
  SPI enabled, and the loop tests `SPM_IRQ_STA` after every `wfi`. So a
  return that comes before the masking stays pending and ends the first
  `wfi` at once. This is not a race in the module. With `D4_MASK_PPI=1`
  the GICR mask also disables CNTP's PPI, so the backstop cannot wake
  `wfi`; only the SPM's SPI can.
- **Added to D5ai, read-only:** `SW_RSV_3` read before `d4.sh` and after
  the run (if it survives), and the retained `d4` logs searched for any
  returned period with `r12` bit 10. If bit 10 or bit 3 shows, the next
  run is D5ah's setup with `D4_WAKE=0x0f57c1e5` (the default minus SCP),
  ahead of variants 2 and 3.
- **No existing variant covers the SCP branch:** variant 3 leaves both the
  store and the jumps back to `0x498` (`0x4c2`, `0x4e8`, `0x4ec`). The
  wake-mask run is cleaner: without bit 10 in `SPM_WAKEUP_EVENT_MASK`,
  `0x4b2`-`0x4ec` never runs, which tests the store and the loop at once,
  on unmodified firmware.
- **Log search (custodian, 2026-11-22):** no retained log shows `r12`
  bit 10. Across the station logs, journals and RAM console copies, the
  wake values are `00400020`, `00000001`, `00000000` and `00400000`. The
  two-state hang runs' returned periods show only `00400020`, with an
  occasional `00400000`. Only returned periods are logged, so the hung
  period's `r12` stays unseen. `SW_RSV_3` read 0 in every latch read so
  far, but those come before a module loads or after a Gemian landing,
  not after two-state periods on the same boot. **Reading (corrected by
  the program session):** the logged `r12` is only the wake that ended
  the period. After an SCP wake the program re-arms and waits again, so a
  period that ran the branch and then ended on the timer or CONN2AP logs
  no bit 10. The search shows only that bit 10 never ended a period, not
  that the branch never ran. `SW_RSV_3` bit 3, which the program sets at
  `0x4e2` and never clears, is the only check. It is read after D5ai's
  periods on the same boot: if set, the wake-mask run comes next; if
  clear, the lead is weak.

### D5m redone: run 1 passed, run 2 hung (custodian, 2026-11-22)

**Approved** by the owner in the custodian's session.

**Setup.** Boot 9b2d25eb, module d157e512, `d5m.sh` blob e41dd3c9 with
`D5M_RESET=0`, so insmod `sodi_idle=0 sodi_wake_src=0` and every other
parameter at its default. Wi-Fi modules loaded, cable out.

**Observed.**
- **Run 1:** blank and `online: 0` at 21:40:33. Periods at 21:40:34, :35
  and :36 all returned on the PCM timer: `backstop=0`, `r12` `00000001`,
  `r12_ext` `00000020`, misc `00080000`, `timer_out` `0000199c`, `199c`
  and `199d`, `r13` `00066000`, `00066000` and `00026000`, `debug`
  `00000300`. The run ended at 21:40:38. The owner pressed a key by
  mistake after it ended; the key press is not in the log. The module
  was removed cleanly, followed by a 30 s wait.
- **Run 2:** started 21:41:43. The station was silent from 21:43:41, and
  Gemian (boot 095ab31a) booted at about 21:43:39, with no clip.
- The RAM console holds nothing from the run (286 B, boot lines only):
  the console log level was not raised for `d5m.sh`.
- **`d5m.log` places the hang in period 1.** Insmod 21:42:13 (CONSYS and
  WLAN core loaded), blank 21:42:38, `online: 0`, then `period 1, try 1`
  at 21:42:38 and nothing more. The previous boot's journal ends in the
  same second with the PSCI lines for CPUs 1-4 being killed. In both runs
  period 1 started about 1 s after the CPUs went offline. The blank came
  24 s after insmod in run 2, against 82 s in run 1.
- New boot 02f760b3; the latches after Gemian were cleared as before.
- **The backstop did not bring CPU0 back (reviewer's point, checked in
  the module).** Crumbs were off, and the console kept no line from the
  run. But with the defaults the SODI scenario uses SYS_CIRQ, so the
  CNTP backstop was armed 100 ms after the period's timer, and without
  `sodi_mask_ppi` its PPI stayed enabled through the SPI mask. Had the
  backstop or the PCM ended the wait, the period would have returned to
  `d5m.sh`, which syncs a line after each return or retry; none came. So
  CPU0 did not get back to the script with a wake source that needs
  nothing from the SPM.
  - What remains: CPU0 never left WFI (its clock or the GIC path lost),
    or it woke and stalled on its next SPM or bus access, or it stalled
    later in the restore.
  - It weighs against "the program is still waiting while CPU0 is fine".
  - *Inference;* without crumbs, the stage is unknown.

**Result.**
- **The no-driver, timer-only hang still exists on today's module**, as in
  D5m, D5m no-event and D5p part 1. The two-state registration is not
  needed for a hang, and SCP wakes are excluded (`sodi_wake_src=0`).
- **Correction to D5af's list of differences:** `d5m.sh` loads the
  module with its defaults, so none of D5af's options were set: level
  SYS_CIRQ, `NO_EVENT`, the mark, MP2 left alone, the PPI mask, ACINACTM
  only around WFI, the MMSYS gates and the crumbs. So against D5af
  (159 clean periods, no driver, timer only), this hang differs in those
  options as well as in period length (200 against 2000 ms) and start
  (about 1 s after the CPUs go offline, periods 1 s apart).
- Every two-state hang ran with those options, so they do not prevent
  that hang. Whether they prevent the no-driver hang is the next
  question.
- D5ai (the governor held at state 0) is deferred: its premise, that the
  hang needs the cpuidle driver, no longer holds on its own.
- *Inference:* a period that starts while the PSCI CPU power-downs are
  settling is a candidate. `d4.sh` waits 5 s after the CPUs go offline,
  and D5af never hung. D5aj keeps `d5m.sh`'s early start, so if it hangs,
  the start delay is split before the length.

### Request D5aj (proposed): `d5m.sh`'s timing with D5af's options

`d5m.sh` (blob given at the commit) adds `D5M_ARGS`, extra module
parameters read back into the log; with `sodi_crumbs=1` it raises the
console log level to 8. `D5M_MM=1|2` writes `sodi_mm_cg` after the blank,
as `d4.sh`'s `D4_MM`. There is no module change.

- **Candidate:** module d157e512, fresh station boot or after rmmod,
  `D5M_RESET=0 D5M_MM=2 D5M_ARGS="sodi_cirq_level=1 sodi_no_event=1
  sodi_mark=1 sodi_no_mp2=1 sodi_mask_ppi=1 sodi_acinactm_late=1
  sodi_crumbs=1"`. That is D5af's module configuration with `d5m.sh`'s
  three 200 ms periods, about 1 s apart, right after the CPUs go
  offline.
- **Runs:** up to five, with rmmod and 30 s between runs, stopping at the
  first hang.
- **Pass rule:** all five runs clean, 15 periods. The `d5m.sh` default
  configuration hung in four of its five recorded runs (D5m, D5m
  no-event, D5p part 1 and this run 2), each within three periods. A
  per-period hazard of 1 in 4 would give 15 clean periods about 1 % of
  the time, and 1 in 8 about 13 %, so a pass excludes only the higher
  rate firmly.
- **Admission:** parameter values the owner has approved before, in a
  script shape already run; the owner approves the run.

| Result | Reading | Next |
| --- | --- | --- |
| Hangs | The options do not prevent it: timing or length makes the no-driver hang, and the crumbs place it | Split the start first: the same with a 5 s wait after the CPUs go offline (a one-line `d5m.sh` option), then the 200 ms length |
| Passes 15 | One of D5af's options prevents the no-driver hang, yet the two-state hang survives them all, so it may be a separate hazard (kept open) | Split the options in two groups on `d5m.sh` timing: the interrupt side (`sodi_cirq_level`, `sodi_mask_ppi`, `sodi_no_event`) and the bus and cluster side (`sodi_acinactm_late`, `sodi_no_mp2`, `D5M_MM=2`), with `sodi_mark` and the crumbs in both; then one by one within the group that passes |

**The program session on `NO_EVENT` (2026-11-22).**
- With `NO_EVENT` clear, as in the vendor's flags and `d5m.sh`'s
  defaults, CG mode arms only EV15 (APSRC sleep) and EV14 (APSRC wake).
- When no DRAM requester remains, EV15 requests the EMI clock off and
  waits for its ack. It then sets `0x1000cf4c` bit 4 and drives DRAM
  channel 0 into self-refresh through `r0`: the memory clock off, the PHY
  DLLs and VREF off.
- EV14 undoes it. On the way out, only a conditional call to EV14 after
  the wait (`0x4a3`/`0x4a4`, on `r6` bit 31) undoes it; the `0x59a`
  restore does not touch those bits. The decoder marks that call's
  polarity as uncertain.
- A skipped undo would return with DRAM still in self-refresh, and
  CPU0's first fetch after WFI would stall. That fits both the `kick`
  crumb and run 2's silent CPU0. *Inference.*
- **The path ran in D5m redo run 1:** `debug` `00000300` has bits 8
  (EV14) and 9 (EV15, self-refresh entered) set.
- **Against it as the only cause:** D5m with `NO_EVENT` set (older module)
  hung in period 1, and D5ah hung with it set. So at least one mechanism
  needs no self-refresh.
- Reading D5aj, which sets `NO_EVENT`:
  - a pass at 200 ms implicates this path; a run with `NO_EVENT` clear
    and the entry (`0x204`-`0x212`) skipped would then split it;
  - a hang clears it for this setup.
- **Polarity settled (program session):** the `0x4a4` call is
  call-if-zero, by the same field the jumps use (checked at `0x41d`), and
  by meaning. `0x411` marks every resource awake, the sleep handlers clear
  their bits, and the chain wakes only those still asleep. So the exit
  undo exists and is gated correctly.
- **Residual window (inference):** `PCM_EVENT_VECTOR_EN` stays `0xc0c0`
  through the exit. If vectors are serviced during the exit's timed
  delays, EV15 could re-enter self-refresh after the chain, while CPU0 is
  still in WFI. The program does not show whether that happens.
- **Variant held until D5aj passes (corrected by the program session):**
  EV15 raises the EMI clock-off request (`0x2a5`, `r7 |= 1<<1`) and gets
  its ack before the self-refresh steps. So a variant that keeps DRAM
  available must no-op `0x2a5`, optionally with `0x209`, `0x20d` and
  `0x212`, the self-refresh steps.
  - EV15 then sees no ack, writes `SPM_CPU_WAKEUP_EVENT` = 1 and takes its
    no-ack exit. That write may end periods early, with an `r12` other
    than `00000001`.
  - None of the four words is a branch target or a delay slot.
  - It is needed only to split the EMI clock-off from the PHY steps.
    D5aj, with `NO_EVENT` set, already removes the whole path.

### D5aj run 1: D5af's options hang at the first kick (custodian, 2026-11-22)

**Approved** by the owner in the custodian's session.

**Setup.** Boot 02f760b3, module d157e512, `d5m.sh` blob 8f70b789 with
the requested `D5M_RESET=0 D5M_MM=2 D5M_ARGS=...`, printk 8 set
beforehand. Started 22:50:32.

**Observed.**
- The station was silent from about 22:52:30, and Gemian (boot 4487123b)
  booted at about 22:53:10, with no clip.
- The RAM console (2020 B, kept privately) ends:
  - two `sodi mm:` lines, the four MMSYS gates closed and the vendor's
    SODI terms 0;
  - the PSCI lines for CPUs 7 to 1 killed, 3944.745-3945.296 s;
  - `sodi crumb 1: kick` at 3946.533 s, the last line.
- So period 1 hung after the kick, about 1.2 s after CPU1 went offline.
- `d5m.log` (checked on boot 5fdb8672): all seven options read back `Y`,
  `sodi_idle` N, `sodi_wake_src` 0, printk `8 4 1 7`. The `sodi mm:` lines
  came after the blank, then `online: 0` and `period 1, try 1` at
  22:52:20, and nothing more. The previous boot's journal ends with CPU1's
  PSCI kill line at 22:52:20. The latches after Gemian were cleared as
  before.

**Result.**
- **Hang: D5af's options do not prevent the no-driver hang.** `NO_EVENT`
  was set, so the DRAM self-refresh path is not needed for it.
  Interrupt-side options, bus-side options and the MMSYS gates make no
  difference here.
- What separates this hang from D5af's 159 clean periods is now `d5m.sh`'s
  timing: the start about 1 s after the CPUs go offline, periods 1 s
  apart, and 200 ms periods. Both hangs since D5m was redone came in
  period 1.

### Request D5ak (proposed): D5aj with a 5 s settle after offlining

`d5m.sh` (blob given at the commit) adds `D5M_SETTLE=N`, a wait of N
seconds after the CPUs go offline and before period 1; the default 0
keeps today's start.

- **Candidate:** D5aj's command plus `D5M_SETTLE=5`, which matches
  `d4.sh`'s 5 s wait. Up to five runs, with rmmod and 30 s between them,
  stopping at the first hang.
- **Pass rule:** all five runs clean, as D5aj.
- **Per run, record** the time from the last PSCI kill line to period 1's
  `kick` crumb (about 1.2 s in D5aj), so passes and hangs sit on one axis.
- **Admission:** no new register write or parameter; the owner approves
  the run.

| Result | Reading | Next |
| --- | --- | --- |
| Passes | A period started while the CPU power-downs settle hangs; D5af's start avoided it | One run at 2 s to bracket it; the reviewer reads what the firmware's CPU and cluster power-down still do in the second after the last CPU_OFF; the two-state hang, which comes long after offlining, is then a separate hazard |
| Hangs in period 1 | Not the start delay | The length: `d5m.sh` with 2000 ms periods |
| Hangs later | The settle helps period 1 only; the periods still run back to back, so the missing gap between periods is the lead, not offlining | Longer gaps between periods (1 s here, about 1.5 s in `d4.sh`), then the length |

**The program session on what a recent power-down could reach
(2026-11-22).**
- On our path, the program reads no CPU, cluster or idle status:
  - With `SW_FLAG` bit 0 set, `0x440` skips the CPU power routine
    (`0x5bb`) and its unbounded status polls.
  - With `NO_EVENT` set, `0x480` skips the `DUMMY1_PWR_CON` read, and the
    EMI ack poll belongs to EV15, which is never armed.
- A power-down still settling can only reach the program through the
  hardware inputs to the wait at `0x498`: `SPM_AP_STANDBY_CON`'s WFI AND
  and the wake sources. Our value `0x04080011` masks only MP3, so the
  MP0-MP2 cluster idle, MP_TOP idle and MCUSYS idle signals all feed the
  AND.
- *Inference:* a just-killed cluster's idle signal still settling would
  gate the AND, and the program never re-checks it. If D5ak passes, a
  cheaper split is to mask the clusters that hold the offlined CPUs as
  well (bits 2 and 3, MP1 and MP2): a new value for an approved write.
- Caveats:
  - A gated AND alone delays only the program. In D5m redo run 2,
    CPU0's armed backstop did not bring it back either, so CPU0 itself
    was stuck, or it stalled on an access.
  - The one known `SPM_AP_STANDBY_CON` readback, `0x04f80000`, does not
    match the value written. A read inside a period would show which
    masks are live.

### D5ak run 1: the settle moves the hang to period 2 (custodian, 2026-11-22)

**Approved** by the owner in the custodian's session.

**Setup.** Boot 5fdb8672, module d157e512, `d5m.sh` blob e9fc5bdd, D5aj's
command plus `D5M_SETTLE=5`, printk 8. Started 23:01:46.

**Observed.**
- **Settle:** CPU1's PSCI kill line came at 148.908 s and period 1's kick
  at 155.077 s: 6.17 s, against about 1.2 s in D5aj.
- **Period 1 returned** at 155.278 on the PCM timer:
  - `returned=1 loops=0 backstop=0`, `fsm` `02048490`, `r12` `00000001`;
  - `r12_ext` 0, raw 0, ext `0001aaa9`, misc `00080000`;
  - `timer_out` `0000199c`, `r13` `00066000`, `idle` `000001f7`, `debug` 0;
  - `im fsm` `02c48910>02448910`, not stuck;
  - the next local timer event was 4789 µs after entry.
- **Period 2 hung:** its kick came at 156.548 s, 1.27 s after period 1
  ended, and `sodi crumb 2: kick` is the console's last line (3447 B,
  kept privately).
- The station was silent by about 23:03:20, and Gemian (boot 198b93ed)
  booted at 23:04:01, with no clip.

**Result.**
- **The start delay is not the cause:** a period 6 s after offlining
  returned, and the next one hung. The 200 ms reproducer still hangs.
  Hangs on it now came in period 1 twice, then period 2.
- Against D5af's 159 clean periods, two differences remain: the period
  length (200 against 2000 ms) and the gap between periods (1.27 s
  here, about 1.5 s in `d4.sh`, which also does more between periods).
  The gaps barely differ, so the length is tested first.

**Evidence read on the next station boot** (64f3768b, 2026-11-23, module
not loaded; all files kept privately):
- **Log** (25 lines): every option read back `Y`, printk 8, CPUs offline
  at 23:03:01, period 1 at 23:03:06 with the values above, and
  `period 2, try 2` at 23:03:07 as the last line. Period 1's
  `isr` was `00000018` and `event` `90100000`.
- **Journal** (2734 lines) ends at 23:03:07 with period 1's crumbs
  `kick`, `back`, `restored` and `done`, then period 2's lines before
  its kick: `im fsm` `02c48910>02448910`, `io r7` `01415830`, the next
  local timer event 4789 µs ahead, a period of 6553 ticks, and the 23
  SYS_CIRQ lines. The `im fsm` and next-event values equal period 1's.
  Only the RAM console has period 2's `kick` crumb.
- **Latches** were read after Gemian and hold its usual cleared set: zero
  except `008` 15830, `00c` 8000, `01c` 6c00, `034`, `618` and `61c`
  ffffffff, and TOPRGU 0x15. `SW_RSV_3` (614) is 0, as Gemian leaves it,
  so it says nothing about the SCP branch.

### Request D5al (proposed): D5ak with 2000 ms periods

`d5m.sh` (blob 1eafd081, commit 90c89dc32) adds `D5M_MS=N`, the period length,
with 200 as the default.

- **Candidate:** D5ak's command plus `D5M_MS=2000`, keeping
  `D5M_SETTLE=5`. Up to five runs, with rmmod and 30 s between them,
  stopping at the first hang.
- **Pass rule:** all five runs clean (15 periods). Record the gap from
  each period's `done` to the next `kick`.
- **Admission:** the period length D5af ran; the owner approves the run.

| Result | Reading | Next |
| --- | --- | --- |
| Passes | Short periods hang; 2000 ms do not, in the same script | What a 200 ms period changes: the timer's arming value, or a hazard tied to how soon the exit follows the entry. Try 500 ms and 1000 ms to find the edge |
| Hangs | Not the length; the gap or what `d4.sh` does between periods | Longer gaps (a `d5m.sh` option), then `d4.sh`'s between-period steps |

**Between periods, from the scripts (for the reviewer).**

Both scripts write one synced log line (`date`, `echo`, `sync`), sleep
1 s and write the next period's length to `sodi_once_ms`, so the last
`sync` comes about 1 s before each kick in both. After a period returns:

| Script | Steps |
| --- | --- |
| `d5m.sh` | one `dmesg \| grep \| tail \| sed`, one `sync`, then the next period's synced line |
| `d4.sh` | `dmesg \| wc` before the write; after the return, several `dmesg` reads, `grep` and `sed` parses, one or two synced log lines, the cpufreq `scaling_cur_freq` read, and the window's per-period line (`uart_tx` in C); in A and B a program hash check through the `mhz` helper after every period |

The extra work in `d4.sh` all happens before its synced line and sleep,
so the 1 s just before each kick looks the same in both. *Inference:*
if D5al hangs, the hash check and the extra syncs are the candidates.

**The program session on the period length (2026-11-22).** No program
decision depends on the timer value:
- `0x410` and `0x517` set and clear `R7_PCM_TIMER_SET`; the hardware
  raises `r12` bit 0 at the match.
- `PCM_TIMER_OUT` is only copied out at `0x522`.
- The `r14` waits have constant counts.
- The exit writes `PCM_WDT_VAL` = `0xf0000`, the same for any length.
- Nothing wraps or saturates.

So a 200 ms period takes the same program path as a 2000 ms one. D5al
counts per kick: it runs the same three periods per run as D5ak, so 15
clean kicks against hangs within three kicks is a fair comparison. What
changes is the time from each kick to its exit, and therefore what
Linux, the other blocks and the previous wake have done by the next
kick. A pass would place the cause outside the program. *Inference.*

### D5al run 1: 2000 ms periods hang at the first kick (custodian, 2026-11-23)

**Approved** by the owner in the custodian's session.

**Setup.** Boot 64f3768b, module d157e512, `d5m.sh` blob 1eafd081,
D5ak's command plus `D5M_MS=2000` (`D5M_SETTLE=5 D5M_RESET=0 D5M_MM=2`
and all seven options), cable out, printk 8. Run 1 started 07:52:26.

**Observed** (RAM console read in Gemian, 1442 B, kept privately):
- insmod at 288.642 s; both programs loaded.
- `sodi mm` at 289.080 s: `cg0` `3f9f8000`, `cg1` `ffffff03`, terms
  `00004000` `000000d0`; gated, `3f9fc000` `ffffffd3`, terms 0 0. D5ak's
  boot read `00110000` `ffffff00`, then `00114000` `ffffffd0`, so more
  MMSYS clocks were open at this blank. The gating still met the terms.
- CPU7 to CPU1 killed at 289.247-289.676 s.
- `sodi crumb 1: kick` at 295.806 s, 6.13 s after the last kill; nothing
  after it.
- The station stopped answering at 07:53:39, and Gemian (boot 1afd6b5c)
  was up at 07:54:13. Runs 2-5 did not happen. The latches are Gemian's
  cleared set.
- **Log and journal** (read on boot 552b5453, kept privately): the blank
  came within 1 s of the wait (07:52:58), CPUs offline at 07:52:59,
  `periods of 2000 ms` at 07:53:04, then `period 1, try 1` and nothing
  after. The journal (2721 lines) ends at 07:52:59 with CPU1's kill, so
  only the RAM console has the kick.

**Result.**
- **The period length is not the cause:** a 2000 ms period, `d4.sh`'s
  length, hung at its first kick in `d5m.sh`.
- The hang came before any period ended, so the work between periods
  (`d4.sh`'s hash checks and extra syncs) cannot be the difference
  either. D5al's "hangs" row is overtaken.
- What `d4.sh` does before its first period that `d5m.sh` does not:
  - sets the USB gadget's `11271000.usb/power/control` to `auto` and
    waits 10 s, so with the cable out MTU3 runtime-suspends and the SSUSB
    clocks gate (0800, 0801); `d5m.sh` leaves it as the boot set it;
  - loads `mt6797-gate-unused` if it is not loaded;
  - checks the programs' and `cpu-mhz`'s file hashes and external power:
    reads only;
  - in window C, waits for the custodian's pings before period 1.
- *Inference:* the USB controller is the strongest lead. If the boot
  leaves `power/control` `on`, every `d5m.sh` period ran with SSUSB
  powered and clocked, a bus master the vendor's SODI never runs with.
  `d4.sh`'s log records the old value as `(was ...)`; D5af's log shows
  which it was.

### Request D5am (withdrawn: the gates already match): `d5m.sh` with `d4.sh`'s setup

`d5m.sh` (commit recording this stage) adds `D5M_USB_AUTO=1`, which sets
the gadget's `power/control` to `auto`, waits 10 s and puts the old value
back at the end, and `D5M_GATE_UNUSED=1`, which loads
`mt6797-gate-unused`. Every run now logs both states before insmod, so
the defaults are recorded even without the options.

- **First, a read only:** on the next station boot, before any test,
  `cat /sys/bus/platform/devices/11271000.usb/power/{control,runtime_status}`
  and whether `mt6797_gate_unused` is loaded, plus the `(was ...)` value in
  D5af's `d4.log`. If the boot already leaves `auto`, suspended and the
  module loaded, D5am is moot and the pings are the remaining difference.
- **Candidate:** D5al's command plus `D5M_USB_AUTO=1 D5M_GATE_UNUSED=1`,
  module d157e512. Up to five runs, with rmmod and 30 s between them,
  stopping at the first hang.
- **Pass rule:** all five runs clean (15 periods), against four `d5m.sh` runs in a
  row that hung within two periods (D5m redo run 2, D5aj, D5ak, D5al).
- **Admission:** both steps are what `d4.sh` has done before every run
  since D3; no new register write. The owner approves the run.

| Result | Reading | Next |
| --- | --- | --- |
| Passes | One of the two setup steps prevents the no-driver hang | Split: `D5M_USB_AUTO=1` alone, then the reviewer reads what a powered SSUSB holds in the period (its clocks and bus requests against `SPM_SRC_MASK`) |
| Hangs | Not the setup | The pings: window C's inbound traffic before and during period 1 |

**D5af's log on the USB step (custodian, 2026-11-23).** D5af's `d4.log`
reads `gadget power/control auto (was auto), runtime suspended`, and D5ae
and D5ah read the same: the boot already leaves `auto`, and the
controller was suspended before insmod. `d5m.sh` waits for the blank, up
to 300 s, after SSH ends, so its runs very likely had MTU3 suspended too.
*Inference:* the USB step is probably not a difference. No saved `d4.log`
records `mt6797-gate-unused`, since `d4.sh` loads it without a log line.
The boot read decides: if the module is loaded at boot, D5am is moot and
the pings remain; if it is absent, D5am runs with `D5M_GATE_UNUSED=1`
(keeping `D5M_USB_AUTO=1` costs nothing).

**The reviewer and the program session on D5am (2026-11-23).**
- **Reviewer:** the vendor's SODI admission refuses a period while any
  clock in its infra masks (`0x00440802`, `0x03aff900`, `0x21fe36fd`,
  bit set = must be gated) or its display masks is running; `sodi_busy()`
  checks only AP_DMA, the three SSUSB gates, MSDC0/1 and audio.
  `mt6797-gate-unused` is the step that closes most of the rest. The
  SSUSB gates were already off at every `d5m.sh` kick, or `sodi_busy()`
  would have refused, so the gate step is the half expected to matter.
  The bit names the reviewer gave follow the mainline word order, which
  D5w found reversed against the vendor's (first mask on `0x94`, second on
  `0x90`); the masks themselves stand.
- **Program session:** neither `SPM_SRC_MASK` nor `SPM_SRC2_MASK` has a
  USB input, so a powered SSUSB cannot hold infra or 26 MHz through the
  SPM. But every period pauses the top bus masters: `0x438` writes
  `SPM_MAS_PAUSE_MASK_B` `0x6ff00b01` and `MAS_PAUSE2_MASK_B`
  `0xfe00ffff`, and `0x43e` calls `0x2b0`, which sets `r7` bit 2
  (`TOP_MAS_PAU_REQ`), waits a fixed delay and polls no acknowledgement;
  the exit clears it at `0x519`. Which masters those masks select is not
  named. *Inference:* a master with its clock running, paused in the
  middle of a transaction, is a plausible way an ungated clock blocks the
  exit, and a reason the vendor refuses SODI with those clocks on.
  Removing the pause would be an IM patch at `0x2b0` (`a1d10407`), like
  variants 4 and 5; it needs the owner's admission and is not proposed.
  *Correction (program session, same day):* no vendor header names any
  bit of the two mask registers; a later header calls them
  `RG_PCM_PAUSE_MASK_B` and `RG_PCM_PAUSE2_MASK_B`, which may mean they
  select what pauses the PCM, not which masters `r7` bit 2 pauses. The
  pause request itself stands; its link to these masks is unproven.
  `PAUSE2`'s low half is stepped (`f00f` to `ffff` and back) around the
  CPU and cluster power routine (`0x5e9`) here and in other programs, so it
  looks tied to that sequence rather than to peripherals. *Inference.*
- **No new read is needed for the gate words:** the module's return line
  carries `cg0`, `cg1` and `cg2` (`0x10001090`, `0x94`, `0xb0`) before
  and after each period. D5ak's period 1 and D5m redo run 1 have them for
  `d5m.sh`, and D5af's `d4.log` for `d4.sh`. With the masks applied as D5w
  did (`~cg1 & 0x00440802`, `~cg0 & 0x03aff900`, `~cg2 & 0x21fe36fd`),
  nonzero terms in `d5m.sh`'s runs and zero in D5af's would make the gate
  step the difference and name the clocks. G1's boot values without the
  module (`0x00001800`, `0x00004014`, `0x080000e7`) give large nonzero
  terms, so if the boot no longer loads `mt6797-gate-unused`, that is
  what to expect.

### The gate words already match (custodian, 2026-11-23)

From logs already held, no device access. The `before` words of the
return line:

| Run | `cg0` (`0x90`) | `cg1` (`0x94`) | `cg2` (`0xb0`) |
| --- | --- | --- | --- |
| D5ak period 1 (`d5m.sh`, hung in period 2) | `03eff900` | `00464816` | `21fe36ff` |
| D5m redo run 1 (`d5m.sh`, passed), three periods | `03eff900` | `00444816` | `21fe36ff` |
| D5af window C period 1 (`d4.sh`, passed), from the journal | `03eff900` | `00464816` | `21fe36ff` |

All 231 return lines on D5af's boot (D5ae, D5af, D5ah) equal D5af's row,
and every row is unchanged after its period. `~cg0 & 0x03aff900`,
`~cg1 & 0x00440802` and `~cg2 & 0x21fe36fd` are 0 in all three.

**Result.**
- **No vendor-blocking infra clock runs in either script**, and D5ak's
  words equal D5af's exactly. The only difference, `cg1` bit 17 clear in
  D5m redo run 1, is outside the mask and came in a passing run.
- So `mt6797-gate-unused` is already loaded at boot, or makes no
  difference here, and D5am's gate step is moot; its USB step was moot
  already. **D5am is withdrawn.**
- D5al's `sodi mm` words (`3f9f8000`/`ffffff03`, against D5ak's
  `00110000`/`ffffff00`) are MMSYS gates, a different block; D5ak hung
  with the lower set, so they do not separate the scripts either.

**What still differs before period 1.** Reading `d4.sh` again, after the
CPUs go offline it:
- sleeps 5 s, which D5ak and D5al matched;
- **runs `cpu-mhz 0 hash`**, the memory reference: CPU0 busy hashing
  memory a few seconds before window C. D5am's list called this a read;
  it is a load on CPU0 and DRAM;
- greps `/proc/interrupts`;
- **waits for inbound pings** and runs window C while they arrive.

`d5m.sh` (commit recording this stage) adds `D5M_HASH=1`, which runs the
same hash after the settle, checking `cpu-mhz`'s file hash as `d4.sh`
does.

### Request D5an (withdrawn: D5ap passed): `d5m.sh` with the hash and the pings

- **Candidate:** D5al's command plus `D5M_HASH=1`, with the custodian
  pinging the device once a second from before the launch until the run
  ends, as in window C. Module d157e512. Up to five runs, with rmmod and
  30 s between them, stopping at the first hang.
- **Pass rule:** all five runs clean (15 periods), against four `d5m.sh`
  runs in a row that hung within two periods.
- **Both at once:** each hang costs a Gemian round trip, and both steps
  are what `d4.sh` did before every passing period; a pass is then split.
- **Admission:** the hash and the pings are what `d4.sh` has done before
  every window C since D4; no new register write. The owner approves the
  run.

| Result | Reading | Next |
| --- | --- | --- |
| Passes | The CPU0 and DRAM load or the Wi-Fi traffic just before the kicks prevents the hang | Split: the pings alone, then the hash alone |
| Hangs | No pre-period step of `d4.sh` is the difference | A control: `d4.sh` with D5af's env on the same boot. If it passes, diff the scripts step by step; if it hangs, D5af's 159 periods were luck or that boot, and the no-driver hang has no clean configuration |

**The reviewer on D5an's order (2026-11-23).** A hang ends the boot, so
D5an's "hangs" row could not run its `d4.sh` control on the same boot.
Run the control first: a passing `d4.sh` run leaves the boot up for
`d5m.sh`. Against 0 hangs in 219 `d4.sh` timer-only periods, `d5m.sh`
hung within two periods in four of its last five runs.

**Every write up to the first kick, from the two scripts.**

| Step | `d4.sh` (D5af's env) | `d5m.sh` (D5aj's command) |
| --- | --- | --- |
| USB `power/control` | `auto` (already `auto`), then 10 s | not touched |
| `mt6797-gate-unused` | loaded if absent | not touched |
| Console log level | 8, set by the custodian before the launch (from D5r on) | 8, with `sodi_crumbs=1` |
| insmod | `sodi_wake_src=0 sodi_idle=0` and the seven options | the same |
| After the blank | `sodi_mm_cg=2` | the same |
| CPUs | 9 to 1 offline | the same |
| Before period 1 | 5 s, `cpu-mhz` hash on CPU0, `/proc/interrupts` read, wait for pings | 0 or 5 s (`D5M_SETTLE`) |
| Each period | synced line with a cpufreq read, 1 s, `dmesg \| wc`, `echo 2000` | synced line, 1 s, `echo 200` (or `D5M_MS`) |

No other sysfs or debugfs write happens before the kick. The console
level is new to this list; D5m redo run 2 hung at the default level,
without crumbs, so it is not needed for the hang. The MMSYS term of the
vendor's condition is read by `sodi_mm_cg`: after gating it was 0 in D5ak
and D5al, as in D5af.

**The serial console (reviewer's question, 2026-11-23).** The reviewer
asked whether the UART still transmitting a line printed just before the
kick could be the variable. The records answer it without a run:
- The station's command line sets `console=ttyS0,921600n8` and
  `loglevel=4`, so `dev_info` lines reach neither the UART nor the RAM
  console unless a run raises the level.
- **D5m redo run 2 hung in period 1 at level 4**, with no crumbs: its RAM
  console holds nothing from the run, so nothing was printed to the
  console before that kick.
- The custodian raises the level to 8 for `d4.sh` runs from D5r on, and
  D5ac's and D5ah's crumbs were read from the RAM console, so `d4.sh`'s
  crumb runs printed to `ttyS0` right before each kick. D5af ran with
  crumbs and passed; the custodian's launch record sets
  level 8 right before it (the log does not record it), the same level
  `d5m.sh` read back in D5aj, D5ak and D5al.
- `d4.sh`'s `uart_tx` only reads the transmit count after each period; it
  does not wait for the transmitter to drain.
- So the no-driver hang needs no console output, and console output
  before the kick has not caused hangs in `d4.sh`. The console is not
  the variable. The vendor's UART sleep handshake (item 2 of the list
  above) stays unneeded at level 4.

### Request D5ao (proposed): `d4.sh`, then `d5m.sh`, on one boot

- **Candidate:** module d157e512, one fresh station boot, cable out.
  1. `d4.sh` blob fb0e30dd (D5af's 0a0567a2 plus variants 4 and 5,
     inert here) with D5af's env (`D4_WAKE=0 D4_IDLE=0
     D4_CIRQ_LEVEL=1 D4_NO_EVENT=1 D4_MARK=1 D4_MM=2 D4_NO_MP2=1
     D4_ACINACTM_LATE=1 D4_MASK_PPI=1 D4_CRUMBS=1`), pings over window C,
     windows A and B as in D5af.
  2. `rmmod mt6797_spm_sleep` (no cpuidle driver, so it unloads), 30 s.
  3. `d5m.sh` blob d96713b3 with D5aj's command (`D5M_RESET=0 D5M_MM=2`
     and the seven options), no hash, no pings: up to five runs, with
     rmmod and 30 s between them, stopping at the first hang.
- **Admission:** both are commands run before; the owner approves the
  run.

| `d4.sh` | `d5m.sh` | Reading | Next |
| --- | --- | --- | --- |
| Passes | Hangs | The boot is not the cause; something in `d4.sh`'s steps prevents the hang | D5an's hash and pings on `d5m.sh`, then split |
| Passes | Passes 15 | The boot matters, or `d4.sh` leaves a lasting state behind | `d5m.sh` first and `d4.sh` second on the next boot |
| Hangs | — | D5af's pass does not repeat: that boot, or luck | No clean no-driver configuration is left; reread D5ae/D5af's boot against later ones |

### D5ao: `d4.sh` passes, then `d5m.sh` hangs, on one boot (custodian, 2026-11-23)

**Approved** by the owner in the custodian's session.

**Setup.** Boot 552b5453, module d157e512, cable out, battery 55 %,
printk 8. Before the run: latches at the usual post-Gemian values, USB
`power/control` `auto`, runtime suspended.

**Observed.**
- **Step 1**, `d4.sh` blob fb0e30dd with D5af's env, 08:27:05-08:38:33:
  window C 0 of 60 early, with 270 of 270 pings answered (214 echo
  requests in the window); A 0 of 20 early; B no key wake. 80 clean
  periods plus B's, CPUs back. Log (877 lines) and ping record kept
  privately.
- **Step 2:** rmmod at 08:39:20. *Deviation:* the next run started 7 s
  later, not 30 s; with `d5m.sh`'s own 30 s wait, its insmod came about
  38 s after the rmmod.
- **Step 3**, `d5m.sh` blob d96713b3 with D5aj's command (no `D5M_MS`,
  `D5M_SETTLE`, `D5M_HASH` or pings), run 1:
  - `sodi mm` before gating already read `3f9fc000`/`ffffffd3`, terms 0
    0: `d4.sh`'s run had left the MMSYS gates closed (D5al's fresh boot
    read them open);
  - CPU7 to CPU1 killed at 2128.023-2128.454 s;
  - `sodi crumb 1: kick` at 2129.621 s, 1.17 s after the last kill;
    nothing after it.
  - The station stopped answering at 08:40:39; Gemian (boot df2ffb28)
    was up at 08:41:14. RAM console (65524 B, with step 1's late crumbs,
    the last d4 kick being crumb 162) kept privately.
  - **Log and journal** (read on boot 1d3a0381, kept privately): before
    insmod, USB `auto` and runtime suspended, `mt6797-gate-unused`
    loaded (by step 1), every option `Y`, printk `8 4 1 7`; the MMSYS
    gates already closed before gating (terms 0); `online: 0`, `periods
    of 200 ms` and `period 1, try 1` at 08:40:00, nothing after. The
    journal (4454 lines) ends at 08:39:59 with CPU1's kill.
  - So step 3 hung with every `d4.sh` setup state in place: the gates,
    USB and MMSYS as `d4.sh` leaves them.

**Result.**
- **The script decides, not the boot.** On one boot, `d4.sh` ran 80
  clean periods and `d5m.sh`, with the same module configuration, hung
  at its first kick.
- **`d4.sh` leaves no lasting protection.** Whatever it does protects
  only its own periods, or did not carry across the rmmod and reload.
- The MMSYS gates being already closed did not help, which agrees with
  D5ak and D5al.
- What is left is in the step table above: before period 1, `d4.sh`
  runs the `cpu-mhz` hash on CPU0 and waits for pings; in windows A and
  B the hash runs after every period, so every `d4.sh` period follows
  either the hash or ongoing pings. Each period also does a cpufreq read
  and a `dmesg | wc` that `d5m.sh` lacks.

**Next: D5an, on D5ao step 3's command.** D5aj's command (as D5ao step 3)
plus `D5M_HASH=1`, with the custodian pinging once a second from before
the launch until the run ends. Its table stands: a pass splits into
pings alone and hash alone. *Inference:* if it hangs, the per-period
reads (`scaling_cur_freq`, `dmesg | wc`) are the last listed difference,
and `d4.sh` itself can be cut down step by step instead.

**The reviewer on D5an (2026-11-23): one variable, CPU0's operating
point at the kick.**
- The `cpu-mhz` hash is a load burst on CPU0, which leaves schedutil at a
  high OPP; the pings add some load too. `d5m.sh` does nothing on CPU0
  before its kicks but offline the others and sleep 1 s, so it most
  likely kicks at or near the lowest OPP.
- `d4.sh` logs CPU0's frequency before its 1 s sleep, not at the kick;
  `d5m.sh` logged none.
- *Conjecture (reviewer):* schedutil lowers the frequency only on an
  update, so whether CPU0's tick stops during the sleep changes how far it
  has decayed by the kick, which could also tie the two-state hang to it.
- At low OPPs the A53 cluster clock runs through the PLL post-divider and
  a clock divider, and the program stops the ARM clocks and cycles the
  ARM PLLs. Variant 1 (no clock cut) still hung, so the mechanism, if
  this holds, is not the PLL cycle itself.
- **Against it, partly:** D5l pinned CPU0 at 221 MHz and hung at once,
  but that was the two-state setup on module 97add2b2, so it bears on the
  other reproducer. No `d4.sh` timer-only run has been pinned low.

`d5m.sh` (commit recording this stage) adds `D5M_PIN_KHZ=N`, which pins
policy0 at N kHz (min = max) before period 1 and restores it at the end,
as `d4.sh`'s `D4_PIN_KHZ`. Each returned period's log entry now also gives
CPU0's frequency read just before the write (lost if that period hangs).

### Request D5ap (proposed): `d5m.sh` with CPU0 pinned at its top OPP

- **First, a read only:** the `start, cpu0 ... kHz` lines in D5ao step
  1's log (80 periods): how many read the lowest OPP. Many clean periods
  that started at the lowest OPP would weaken the lead before any run.
- **Candidate:** D5ao step 3's command (D5aj's) plus
  `D5M_PIN_KHZ=<policy0's highest OPP>` (1547000 on D5l's boot; the
  script refuses a value not in `scaling_available_frequencies`), module
  d157e512, fresh station boot, no hash, no pings. Up to five runs, with
  rmmod and 30 s between them, stopping at the first hang.
- **Pass rule:** all five runs clean (15 periods).
- **Admission:** a cpufreq limit through sysfs, as D5l did; no register
  write. The owner approves the run.

| Result | Reading | Next |
| --- | --- | --- |
| Passes | CPU0's operating point at the kick decides the no-driver hang | The converse: `d4.sh` as D5af with `D4_PIN_KHZ` at the lowest OPP; then the two-state setup pinned high to the 50-period rule; then read the cluster divider and PLL words at entry in the module |
| Hangs | Not the operating point | D5an as written |

**The read (custodian, 2026-11-23, from logs held).** CPU0's frequency in
`d4.sh`'s `start` lines, read about 1 s before each kick:

| Run | Periods | 1547000 | 1391000 | 1339000 | 1274000 |
| --- | --- | --- | --- | --- | --- |
| D5ao step 1 (C 60, A 20, B 82) | 162 | 157 | 2 | 3 | 0 |
| D5af | 161 | 146 | 6 | 2 | 5 |

Every clean `d4.sh` timer-only period started at 1274-1547 MHz, almost
always at the top OPP, and none near the bottom of the table. This fits
the lead without proving it: `d5m.sh`'s frequency at its kicks is not
recorded. The current kernel's OPP table was not at hand; the script
checks the pin value against it.

### D5ap: pinned at 1547 MHz, `d5m.sh` passes 15 of 15 (custodian, 2026-11-23)

**Approved** by the owner in the custodian's session.

**Setup.** Boot 1d3a0381, cable out, module d157e512, `d5m.sh` blob
218631f5, printk 8. D5ao step 3's command plus `D5M_PIN_KHZ=1547000`;
no hash, no pings; rmmod and a check that the module is gone between
runs. Runs at 09:45:46, 09:46:58, 09:48:34, 09:50:11 and 09:51:46.

**Observed.**
- Every run: `policy0 pinned at 1547000 kHz (was 221000-1547000)`, so
  this kernel's policy0 spans 221-1547 MHz.
- **15 of 15 periods returned**, each `returned=1`, `timer_out`
  `0000199c`, `isr` `00000018`, every one with CPU0 at 1547000 kHz
  just before the write.
- Each run restored `221000-1547000` and ended `done`. The station stayed
  up; log (188 lines) kept privately.

**Result.**
- **Pass. CPU0's operating point at the kick decides the no-driver
  hang.** The same command hung at its first or second kick in five runs
  in a row (D5m redo run 2, D5aj, D5ak, D5al, and D5ao step 3) and ran
  clean when pinned at the top OPP.
- That explains D5af and D5ao step 1: 303 of 323 clean `d4.sh` periods
  started at 1547 MHz and none below 1274 MHz.
- It fits D5l, the two-state setup pinned at 221 MHz, which hung at its
  first period. *Inference:* the two-state hang may be the same hazard,
  met whenever CPU0's frequency has decayed by the time it enters SODI.
- The mechanism is not known. At low OPPs the A53 cluster clock runs
  through the PLL post-divider and a clock divider; variant 1 (no clock
  cut) still hung on the two-state setup, so it is not the program's ARM
  PLL cycle alone. *Open.*
- D5an is withdrawn.

### Request D5aq (proposed): `d4.sh` pinned at the lowest OPP

The converse: the passing script, held at the bottom of the table.

- **Candidate:** the running boot 1d3a0381 (D5ap left it up) or a fresh
  one, module d157e512, `d4.sh` blob fb0e30dd with D5af's env plus
  `D4_PIN_KHZ=221000`, pings over window C, cable out. `d4.sh` pins
  policy0 after the CPUs go offline and restores it at the end.
- **Budget:** window C's 60 periods, then A and B as usual; a hang ends
  the run. RAM console copy first after a hang.
- **Admission:** a cpufreq limit through sysfs, as D5l and D5ap did; no
  register write. The owner approves the run.

| Result | Reading | Next |
| --- | --- | --- |
| Hangs early in C | Confirmed from both sides: a low OPP at the kick hangs, whatever the script | The two-state setup pinned at 1547 MHz to the 50-period rule; then the edge (1274 MHz and lower) and, with a build, the cluster divider and PLL words read at entry |
| Passes | The operating point is not sufficient alone: `d4.sh`'s load or pings matter beyond the frequency | D5an's hash and pings on `d5m.sh` pinned at 221 MHz |

**The reviewer on the mechanism (2026-11-23).** No proof; what the
sources fix:
- The cluster clock driver changes no voltage, so this is not a rail
  effect.
- The SODI program writes no cluster PLL, mux or divider register (its
  only MCUCFG-range stores are `0x10229004` and `0x10229008`). Any
  dependence is on the state CPU0's clock is in, or on CPU0's speed.
- The mainline cluster clock sets its dividers by rate: 1050 MHz and up,
  post-divider 1 and clock divider 1; 525-1049, 2 and 1; 263-524, 2 and
  2; below 263 (221 MHz), 2 and 4. Every clean `d4.sh` period started at
  1274 MHz or more, with both dividers at 1.

Two families, which the edge separates:
- **A, divider state:** something at entry or exit cannot take a divided
  cluster clock (the ARM clock stop and restart, the FHCTL pause, or the
  sync DCM divider at MCUCFG `0x744`, whose select follows the rate).
  Predicts a step at a divider boundary.
- **B, CPU0's speed:** between the kick and CPU0's first WFI, CPU0 still
  programs SYS_CIRQ, the GIC masks, the timer and the late ACINACTM while
  the program runs; at 221 MHz that takes about seven times longer. At
  `0x42e` the program waits for standby or a wake, then pauses the bus
  masters (`0x438`-`0x43e`) and never checks again that CPU0 is still in
  WFI. CPU0 leaving WFI once and reading `SPM_IRQ_STA` under the pause
  would hang it. Predicts a gradual rise as the frequency falls, and a
  dependence on the work after the kick. Variant 1 kept the pause, so
  its hang fits B.

*Fix direction, either way:* the vendor pauses its DVFS processor before
SODI and enters with CPU0 powered down. A frequency QoS request from the
module, holding policy0 at a full-rate point across each period, is the
module-level equivalent.

### Request D5ar (proposed, after D5aq): the edge, four pinned points

On `d5m.sh` with D5ao step 3's command, five runs each, stopping a point
at its first hang:
- the lowest OPP at or above 1050 MHz (dividers 1 and 1);
- the highest below 1050 MHz (post-divider 2);
- the highest below 525 MHz (clock divider 2);
- 221 MHz (clock divider 4): dropped, since D5aq hung there.

Entries come from policy0's `scaling_available_frequencies`, read on
boot 1d3a0381: 221000, 338000, 481000, 624000, 715000, 806000, 897000,
1014000, 1118000, 1222000, 1274000, 1339000, 1391000, 1443000, 1495000
and 1547000 kHz. **The points are 1118000, 1014000, 481000 and 221000
kHz.** The owner approved the order D5aq, D5as, D5ar, each stopping at its
first hang. A step between the first two points to A and the
post-divider; a step at 525 MHz to the clock divider; a gradual change
to B. Every hang costs a Gemian round trip, so the order runs from the
top down. *A build, later:* the counter at the kick write and before the
first WFI on the return line, to time B directly; `loops` already counts
WFI returns without the PCM interrupt.

### D5aq: `d4.sh` pinned at 221 MHz hangs at its first kick (custodian, 2026-11-23)

**Approved** by the owner in the custodian's session, as part of the
order D5aq, D5as, D5ar.

**Setup.** Boot 1d3a0381, after D5ap's five runs on the same boot (each
with rmmod and a check the module was gone). Cable out, battery 48 %,
module d157e512, `d4.sh` blob fb0e30dd with D5af's env plus
`D4_PIN_KHZ=221000`, pings over window C, printk 8. Launched 09:59:00.

**Observed** (RAM console read in Gemian, 34433 B, kept privately):
- insmod at 3784.118 s; `sodi mm` already gated (`3f9fc000`/`ffffffd3`,
  terms 0) at 3810.056 s; CPU7 to CPU1 killed at 3810.256-3810.827 s.
- `sodi crumb 1: kick` at 3821.191 s, 10.36 s after the last kill, with
  the pin and the `cpu-mhz` hash run in between, at 221 MHz; nothing
  after it.
- The last ping reply came at 10:00:14 and the hang was called at
  10:00:24. Gemian (boot e68e6a29) was up at 10:01:12. The same ring
  holds D5ap's last run returning its three periods.
- **Log and journal** (read on boot ccca15a4, kept privately): `cpufreq
  policy0 pinned at 221000 kHz` at 10:00:10, the hash, then window C's
  period 1 `start, cpu0 221000 kHz` at 10:00:12 and nothing after.

**Result.**
- **Confirmed from both sides:** the script that never hung, pinned at
  221 MHz, hangs at its first kick; the script that always hung, pinned at
  1547 MHz, passed 15 of 15. CPU0's operating point decides the no-driver
  hang, whatever the script does.
- **The load does not protect by itself:** the hash and the pings ran,
  at 221 MHz, before this kick.
- D5ar's 221000 point is covered and dropped; it keeps 1118000, 1014000
  and 481000 kHz.

**The program session on the CPU clock (2026-11-23).**
- On the whole SODI path the program writes, outside the SPM, only the
  `ddrphycfg` mux (`0x10000044`/`48`/`04`), APMIXED `0x1000cf38` bit 4 and
  `0x1000cf4c` (EV15 only), the I2C6 gate, I2C6 itself (skipped here) and
  `0x100a0020` (SCP branch only). The `0x10229xxx` stores are the RF
  BPI/BSI block, in handlers our `r6` never calls. **No MCUCFG, ARM PLL,
  mux or divider register.**
- Its only ARM clock action is through `r0` output lines at `0x57f`
  (ARM and SMI clock off, the ARM PLL outputs and stages off, `r7` bit 7
  frequency-hopping pause), undone at `0x59a` with fixed PCM-cycle delays
  and no lock poll. Variant 1 removes both calls, so with it the program
  never touches the ARM clock. Nothing assumes a CPU clock speed.
- With variant 1, the remaining `r7`/`r0` effects on our path are the
  timer, the bit 15 forces, the wake-select toggles, the master pause
  (`r7` bit 2, `0x43e` to `0x519`, removed by variant 2) and, at exit,
  `CSYSPWRUPACK` and the watchdog kick. None is a clock or voltage control.
- *Inference:* the link is CPU-side timing, family B. Whether the wait at
  `0x42e` (`r14` `0xd00f0000`) waits for the WFI AND is not decoded; if it
  does not, the entry and the master pause run while a slow CPU0 is still
  executing.
- **Variant 2 has never run**, and variant 1's hang (D5ad, two states)
  came at an unrecorded OPP. Module d157e512 already carries variant 2.

### Request D5as (proposed): pinned low, without the master pause

- **Candidate:** `d5m.sh` blob 218631f5 with D5ao step 3's command plus
  `D5M_PIN_KHZ=221000` and `sodi_variant=2` in `D5M_ARGS`, module
  d157e512. The insmod log must show variant 2's patched word at `0x43e`
  (original `c0c05600`). Five runs, with rmmod and 30 s between them,
  stopping at the first hang.
- **Order:** after D5aq, which shows whether 221 MHz hangs the passing
  script; before D5ar, since a pass here names the pause directly.
- **Admission:** a firmware test variant in RAM, admitted as a kind with
  D5ad but never run in this form; the owner approves it.

| Result | Reading | Next |
| --- | --- | --- |
| Passes 15 | At a low OPP, the master pause is the hazard: not the entry running early (see the `0x42e` decode below), but the pause itself, catching a master a slow CPU0 still needs or a CPU0 that leaves WFI under it | The kick-to-WFI counter and `loops` at low OPPs; the fix holds CPU0's OPP across a period |
| Hangs | Not the pause alone: the divider state (family A) or another CPU-side access | D5ar's edge |

### D5as: at 221 MHz without the master pause, 15 of 15 (custodian, 2026-11-23)

**Approved** by the owner in the custodian's session, as part of the
order D5aq, D5as, D5ar.

**Setup.** Fresh boot ccca15a4, cable out, battery 47 %, module
d157e512, `d5m.sh` blob 218631f5, printk 8. D5ao step 3's command plus
`D5M_PIN_KHZ=221000` and `sodi_variant=2`; rmmod and a check the module
was gone between runs.

**Observed.**
- Each of the five loads logged `SODI variant 2: word 0x43e c0c05600 ->
  17c07c1f` (82.8, 226.2, 322.1, 418.7 and 514.5 s), and each log read
  back `sodi_variant 2`.
- Every run pinned policy0 at 221000 kHz and restored 221000-1547000;
  all 15 periods read 221000 kHz just before the write.
- **15 of 15 periods returned**, each `returned=1`, `timer_out`
  `0000199c`, `isr` `00000018`. Runs ended 10:20:00 to 10:26:07. Log
  (198 lines) kept privately.

**Result.**
- **Pass. At 221 MHz the master pause is the hazard.** The same pin
  without the variant hung at the first kick in D5aq, and `d5m.sh`
  unpinned hung within two kicks five runs in a row; without the call at
  `0x43e`, 15 periods at 221 MHz returned.
- With the `0x42e` decode, the pause most likely starts only after AP
  standby, so what fails is the pause itself at a low OPP: a master CPU0
  or its cluster still needs while slow, or CPU0 leaving WFI under it.
  *Inference.* The pause polls no acknowledgement.
- *Fix directions:* hold CPU0's OPP above the edge across each period (a
  frequency QoS request from the module), or run without the pause, which
  leaves the clock cut and the `ddrphycfg` mux switch with bus masters
  live, a state the vendor never uses. The edge decides how high the
  hold must be.
- D5ar runs as planned, without the variant, to find the edge.

**The reviewer on the fix and the master (2026-11-23).**
- **Build the frequency hold first:** it is the only fix with evidence
  (D5ap, and 323 clean periods all at 1274 MHz or more). The vendor
  always pauses the masters before its clock cut and `ddrphycfg` switch;
  variant 2's 15 periods say nothing about a master caught mid-transfer
  at the cut, the rare case the pause exists for. Variant 2 stays a
  diagnostic.
- *Shape:* a frequency QoS minimum on policy0, held from before the
  pending check until after the restore, at a point above D5ar's edge,
  refusing the period (`EBUSY`) if the rate read back at entry is still
  below it, since a queued change can leave CPU0 low at the kick. The
  two-state setup then needs the same hold in its idle path, and its
  50-period run says whether it is the same hazard.
- **The master cannot be named:** the pause mask bits are unnamed. One
  frequency-dependent thing on the cluster side that neither the program
  nor the module controls is the **idle clock**: the vendor rewrites the
  sync DCM divider selects (MCUCFG `0x744`, select = MHz / 70 for LL, L
  and CCI, then an update toggle) on every frequency change, so an idle
  cluster and the CCI run at about 55-67 MHz at every OPP. The mainline
  cluster clock reads `SYNC_DCM_CONFIG` once at probe and never rewrites
  it. At 221 MHz the idle LL and CCI clocks are then 221 MHz over the
  boot's selects. *Conjecture:* a pause handshake crossing into a domain
  that slow outlasts the fixed `0x20` wait.
- **Tests, cheapest first:**
  1. Read only: `SYNC_DCM_CONFIG` (`0x744`) and the cluster word at
     `0x74c` on the station, from the clock driver's probe line or its
     debugfs file; the idle clocks at 221 and 1547 MHz follow.
  2. A one-word variant: the delay at `0x2b0` lengthened from `0x20` to
     about `0x200`, pause kept, at 221 MHz. A pass says the pause
     completes late; a hang says it never completes or the fault comes
     after it. Needs a build.
  3. Only if 1 and 2 point there: at 221 MHz with the selects the
     vendor's formula gives (3 at 221 MHz), no variant; a register write
     with its own admission.

### D5ar: 1118 MHz hangs in period 2 (custodian, 2026-11-23)

**Approved** by the owner in the custodian's session, as part of the
order D5aq, D5as, D5ar.

**Setup.** Boot ccca15a4, after D5as's five runs. Cable out, module
d157e512, `d5m.sh` blob 218631f5, D5ao step 3's command plus
`D5M_PIN_KHZ=1118000`, no variant, printk 8. Started 10:28:30.

**Observed** (RAM console read in Gemian, 36280 B, kept privately):
- insmod at 698.830 s; MMSYS already gated; CPU7 to CPU1 killed at
  699.521-700.021 s.
- Period 1: kick at 702.244 s, back at 702.445 s with `returned=1`,
  `fsm` `02048490`, the usual gate words, `im fsm` `02c48910>02c48910`;
  the next local event was 601 µs after entry.
- `sodi crumb 2: kick` at 703.733 s, 1.29 s after period 1 ended;
  nothing after it. Gemian (boot b9a3b87d) was up at 10:30:19. The
  1014000 and 481000 points did not run.
- **Log and journal** (read on boot 58210a12, kept privately): `policy0
  pinned at 1118000 kHz (was 221000-1547000)` at 10:29:04; period 1
  returned with `timer_out` `0000199c`; `cpu0 1118000 kHz just before the
  write` and `period 2, try 2` at 10:29:06, nothing after. **The pin held
  at 1118 MHz for the hanging kick.** The journal (3064 lines) ends at
  10:29:05 with period 1's timer and SYS_CIRQ lines.

**Result.**
- **1118 MHz hangs**, with both cluster dividers at 1, while 1547 MHz
  passed 15 of 15. The edge is not the post-divider boundary at 1050
  MHz: it lies above 1118 MHz, or the rate falls gradually. Family A
  (divider state) loses its prediction.
- `d4.sh`'s clean periods at 1274-1391 MHz (20 of 323) say those points
  are at least much safer; a hold would need 1274 MHz or more, at a power
  cost on every period.

**Sync DCM (custodian, from saved journals).** Every current boot's
MCUSYS probe line reads `SYNC_DCM_CONFIG=0x00070707, floors 210000000
and 210000000 Hz`: CCI, MP0 and MP1 each enabled with select 3. The
vendor's formula gives select 3 at 221 MHz (221 / 70), so at 221 MHz the
idle clocks match the vendor's; at higher OPPs mainline's idle clocks run
faster than the vendor's (select 22 at 1547 MHz). **The idle-clock lead
does not explain the hang:** the low OPP is where mainline agrees with
the vendor. Test 3 is dropped.

**The program session on the pause (2026-11-23).** Inferred from the
programs, no vendor text.
- Deep idle (`0x2c4`), suspend (`0x350`) and SODI (`0x2b0`) share the
  pause routine: `r7` bit 2, a fixed wait, return. No program reads
  `TOP_MAS_PAU_ACK`.
- **The masks are master selects** (correcting the earlier softening):
  SODI's APSRC handler widens `MAS_PAUSE_MASK_B` to `0x6ff10fbf` just
  before the EMI clock-off request and narrows it after, which only
  makes sense if a set bit pauses that master.
- **The difference is `PAUSE2`:** deep idle and suspend write
  `MAS_PAUSE2_MASK_B` `0xfe00f000` at entry, SODI `0xfe00ffff`, pausing
  the low 12 bits too. The CPU power routines step exactly those bits
  (`f00f` > `f0ff` > `f7ff` > `ffff`) just before MP0 powers off, and
  back on power-up, so they look like the CPU cluster's bus ports. The
  vendor's SODI powers CPU0 down right after the pause; with flag 0 set
  ours keeps the cluster powered and clocked with its ports paused, a
  state the vendor never runs.
- *Inference:* at a low OPP the cluster drains slower; write-backs,
  snoop responses or DVM traffic still in flight when its ports pause can
  wedge a handshake, either within the unacknowledged wait or because the
  pause holds for the whole period.
- The wait is one immediate, `0x2b2` `20000020` (plain delay, about
  1.2 µs if it counts 26 MHz PCM cycles); `0x20000200` is about 20 µs.

**Variants 6 and 7 (0847).**
[`0847`](../../patches/proposals/0847-soc-mediatek-mt6797-spm-sleep-add-SODI-variants-chan.patch)
(module only) adds two variants that change one data word each, checked
against its original before the write (the load fails otherwise):
- **6:** `0x2b2` `20000020` > `20000200`, the pause wait ten times longer,
  pause kept. A pass says the handshake completes late; a hang says the
  pause held across the period is the problem.
- **7:** `0x43d` `fe00ffff` > `fe00f000`, deep idle's `PAUSE2`, so the
  cluster ports stay unpaused and the other masters still pause. A pass
  pins the hazard to the cluster ports and is a candidate fix: the
  vendor's own selection for idle modes that keep the cluster powered.
  A hang points at the other masters (`PAUSE_MASK_B`).
Compile-checked with `W=1`, with and without `CONFIG_CPU_FREQ` and
`CONFIG_CPU_IDLE`; checkpatch `--strict` is quiet. One Buildbox build
carries 0846 and 0847.

**The reviewer on 0847 (2026-11-23).** Both words are right: `0x2b2` is
the data word of the two-word `r14` load at `0x2b1`, and `0x43d` the data
word of the three-word store to `MAS_PAUSE2_MASK_B` at `0x43b`. Two
cautions:
- *Polarity:* "a cleared bit leaves that master out" is the coherent
  reading (the power-down routine clears the low bits as it takes cores
  down, and a powered-off core cannot acknowledge), not a proven one. A
  pass of 7 confirms it; a hang of 7 does not clear the cluster ports
  before 6 has run.
- *The vendor comparison:* the vendor's own SODI also pauses with
  `0xfe00ffff` while the cluster is still powered; the stepping comes
  later, in the power-down routine. What differs is how CPU0 got there
  (the firmware's suspend path, against a retained core in WFI here).
  The stronger precedent for 7 is deep idle and suspend, which never
  pause those ports.
- The program's first handler also stores `0xfe00ffff` (`0x015`,
  `0x108`); with flag 13 those handlers do not run, so `0x43b` is the
  only store before the pause. A run with the vectors enabled would need
  those words too.
- No mechanism gives a gradual dependence once `0x42e` is an exact
  standby gate. There are about fifteen instructions from the kick to
  that wait; if the gate were not exact, the race would be CPU0's work
  after the kick against the program reaching `0x43e`, the one reading
  that predicts this shape. A pass of 7 would still not explain why the
  paused ports only matter at lower rates.

**Kick to first WFI (0848).**
[`0848`](../../patches/proposals/0848-soc-mediatek-mt6797-spm-sleep-log-the-time-from-the-.patch)
(module only) reads the arch counter at the PCM kick write and just
before CPU0's first WFI and logs `<what>: kick to first WFI N ns` after
each returned period. In between CPU0 programs SYS_CIRQ, the GIC masks,
the backstop timer and, with `sodi_acinactm_late`, the cluster ACINACTM
writes. Compared at 1547 and 221 MHz against the program's few
instructions to `0x42e`, it says whether the standby gate can be
outrun. Compile-checked as 0846; checkpatch `--strict` is quiet. The
build for D5at should be of the commit recording 0848, carrying 0846-0848.

### Request D5at (proposed): variant 7 at 221 MHz, then variant 6

- **Candidate:** a module from a Buildbox build carrying 0846-0848,
  fresh station boot, `d5m.sh` blob 218631f5
  with D5ao step 3's command plus `D5M_PIN_KHZ=221000` and
  `sodi_variant=7` in `D5M_ARGS`. The insmod log must show `SODI variant
  7: word 0x43d fe00ffff -> fe00f000`. Five runs, with rmmod and 30 s
  between them, stopping at the first hang.
- **Then, on the same boot if 7 passes, or the next:** the same with
  `sodi_variant=6`, five runs.
- **Admission:** firmware data variants in RAM, a kind admitted with D5ad;
  new words, so the owner approves them.

| Variant 7 | Variant 6 | Reading |
| --- | --- | --- |
| Passes | either | The paused cluster ports are the hazard; variant 7's value is the fix candidate, then the two-state setup with it to the 50-period rule |
| Hangs | Passes | The pause handshake needs more than the fixed wait at a low OPP |
| Hangs | Hangs | The pause of the other masters, held across the period, at a low OPP; the hold (0846) at 1547 MHz is the fallback fix |

**The reviewer on 0846 (2026-11-23).** No blocking finding.
- `policy->cur` is enough: cpufreq-dt without fast switching writes it
  after the clock driver's `set_rate` returns, and the clock driver
  already checks its PLL and divider words on each change.
- Every path drops the request and the policy reference; the early
  refusals hold nothing.
- A ceiling below the floor (`scaling_max_freq`, a thermal cooling
  request) leaves `cur` short of the floor, and the period is refused
  after about 100 ms. That is intended: the hold must not override a
  ceiling.
- Nits, left for a later revision so the pending build stays valid: `cur`
  is not initialised before the loop (it always runs once; `W=1` gave no
  warning), and the `sodi hold:` line prints on every period, fine for
  tests but not for an idle path.
- *Scope:* the idle state cannot sleep, so a two-state hold would refuse
  SODI when `policy->cur` is below the floor and fall back to WFI, which
  means SODI would rarely run when the system is idle and CPU0 low. A
  standing floor costs power, the owner's call. That tension is the
  argument for the mechanism (variants 6 and 7) over the hold.

### Request D5au (proposed): the two-state setup pinned at 1547 MHz

The reproducer the investigation started from, with no build: `d4.sh`
pins CPU0 through cpufreq itself (`D4_PIN_KHZ`), which also covers the
idle path that 0846 does not.

- **Candidate:** module d157e512 (or the 0846/0847 build, variants off),
  fresh station boot, `d4.sh` blob fb0e30dd with D5ah's env without
  `D4_KEEP_26M` (D5ac's: `D4_CIRQ_LEVEL=1 D4_NO_EVENT=1 D4_MARK=1
  D4_MM=2 D4_NO_MP2=1 D4_ACINACTM_LATE=1 D4_MASK_PPI=1 D4_CRUMBS=1`, two
  states) plus `D4_PIN_KHZ=1547000`, pings over window C, cable out.
- **Pass rule:** 50 clean periods, summed over windows, against eleven
  hangs at periods 1-28 without the pin (about one in nine).
- **Admission:** a cpufreq limit, as D5l and D5ap; the owner approves the
  run.

| Result | Reading | Next |
| --- | --- | --- |
| Passes 50 | The two-state hang is the same hazard: a low OPP at entry | Variant 7 on the two-state setup unpinned, the fix candidate |
| Hangs | The two-state setup has a second hazard besides the OPP | Variant 7 there too, then its own split |

**The hold, as a module option (0846).**
[`0846`](../../patches/proposals/0846-soc-mediatek-mt6797-spm-sleep-optionally-hold-CPU0-a.patch)
(module only) adds `sodi_min_khz` (default 0, off). With it set, each
`sodi_once_ms` period adds a frequency QoS minimum on CPU0's policy
before the PMIC preparation and drops it after the restore. The limit is
applied from a work item, so the period waits up to about 100 ms for
`policy->cur` to reach the floor; if it does not, the period is refused
with `EBUSY` and a `sodi hold:` line, before anything touches the SPM.
Each held period logs `sodi hold: CPU0 at N kHz (floor M)`. It covers
the test path only; the cpuidle path cannot sleep, so the two-state setup
needs a different hold later. Compile-checked with `W=1`, with and
without `CONFIG_CPU_FREQ` and `CONFIG_CPU_IDLE`; checkpatch `--strict`
is quiet. It waits for a Buildbox build, which can carry the delay
variant (test 2) too once its word is known; D5ar's edge picks the floor.

**The program session on the `0x42e` wait (2026-11-23).** *Inferred
from the programs' structure, not observed.*
- `r14`'s top nibble decomposes into bits: bit 29 alone is a plain delay;
  bit 28 marks every conditional wait; bit 31 is an enabled wake event
  (the main wait, `0x9`); bit 30 is AP standby. Bit 30's reading: with
  flag 0 clear, the path waits with `0x5000aaaa` and goes straight on to
  cut CPU0's power, whose routine checks nothing about WFI, so that wait
  is the only guarantee CPU0 is in WFI.
- `0xd00f0000` is then standby or a wake. The `r12 & 0x2fffe3ff` check
  right after it (`0x434`) aborts on a wake, which only makes sense if the
  wait can end on one. So **the entry passes `0x434` only once AP standby
  holds**, or on a wake. The count (`0xf0000`) is about 38 ms at 26 MHz or
  30 s at 32 kHz, either far longer than CPU0 needs to reach WFI at
  221 MHz.
- Standby here is the WFI AND of the 8 A53 cores enabled in `WFI_EN`,
  with the cluster-idle and MCUSYS idle signals (`SPM_AP_STANDBY_CON`
  `0x04080011` masks only MP3).
- `r12`'s mask includes bit 29, the GIC CPU interface's nIRQOUT/nFIQOUT.
  The pause at `0x2b0` never polls `R13_TOP_MAS_PAU_ACK` (bit 22); it waits
  a fixed `0x20`.
- So family B's "the entry runs while CPU0 is still working" is unlikely.
  What stays open: CPU0 leaving WFI after the pause (the module's loop
  reads `SPM_IRQ_STA` after every return), or the pause failing at a low
  OPP for its own reasons (a master a slow CPU0 still needs, or the
  unacknowledged delay). D5as reads accordingly.
- **A read-only split for a hang**, if the SPM is read after the watchdog
  reset and before Gemian's SPM init (the side key to boot2, as in D5x):
  `PCM_EVENT_REG_STA` (`0x1000614c`) mirrors the last `r14`: `d00f0000`
  stuck at the entry wait, `90100000` in the main wait, `2000xxxx` inside
  a delay. `SW_RSV_0` keeps `sodi_mark`'s `5a5a00xx` only if the program
  never reached `0x419`.

### D5au: the two-state setup pinned at 1547 MHz passes 227 periods (custodian, 2026-11-23)

**Approved** by the owner in the custodian's session.

**Setup.** Fresh boot 58210a12, cable out, battery 45 %, module
d157e512, `d4.sh` blob fb0e30dd, D5ac's two-state env (`D4_CIRQ_LEVEL=1
D4_NO_EVENT=1 D4_MARK=1 D4_MM=2 D4_NO_MP2=1 D4_ACINACTM_LATE=1
D4_MASK_PPI=1 D4_CRUMBS=1`, no `D4_IDLE` or `D4_WAKE`) plus
`D4_PIN_KHZ=1547000`, pings over window C, printk 8.

**Observed.**
- 10:42:14 `online: 0`; 10:42:20 policy0 pinned at 1547000 kHz (was
  221000-1547000), then the hash.
- Window C: 60 of 60 periods ended early, all by CONN2AP or the WLAN
  line; 270 of 270 pings answered. Window A: 20 of 20 early. Window B
  (10:46:44-10:51:47): no key wake.
- **227 periods, no hang**, every `start` line at 1547000 kHz, every
  period woken by CONN2AP through SYS_CIRQ. Policy0 and CPUs 0-7 were
  restored at 10:51:47-48. Log (1206 lines) and ping record kept
  privately.
- `rmmod` then refused, the cpuidle driver holding the module, as
  expected for two states; the next boot is fresh.

**Result.**
- **Pass. The two-state hang is the same hazard:** the setup that hung
  eleven times at periods 1-28 (one in nine; D5ah at period 13) ran 227
  periods with CPU0 held at the top OPP, past the 50-period rule.
- So one cause explains both reproducers: a SODI entry with CPU0 at a
  low operating point hangs in the program's master pause.
- The hold here is cpufreq's own, for the whole window, so CPU0 ran at
  1547 MHz through idle; as a fix that costs power on battery (the
  reviewer's scope note on 0846). Variant 7 is the candidate without
  that cost.

**Build for D5at (custodian).** Buildbox build of eb6c9d626 (0846-0848):
module sha256 a6e92c44, vermagic `7.1.3-gemini-a53-station`, with
`sodi_min_khz`, variants 1-7 with the original check, and the kick-to-WFI
line. D5at needs a fresh boot.

**Next after D5at.** If variant 7 passes at 221 MHz: the two-state setup
unpinned with `D4_VARIANT=7`, to the 50-period rule. `d4.sh` (commit
recording this) now takes `D4_VARIANT=6|7`, checking the module carries
them (0847).

### D5at variant 7: hangs at 221 MHz at the first kick (custodian, 2026-11-23)

**Approved** by the owner in the custodian's session.

**Setup.** Fresh boot fcebb465, cable out, battery 43 %, module a6e92c44
(Buildbox eb6c9d626, 0846-0848), `d5m.sh` blob 218631f5, D5ao step 3's
command plus `D5M_PIN_KHZ=221000` and `sodi_variant=7`, printk 8.
Started 11:26:57.

**Observed** (RAM console read in Gemian, 2167 B, kept privately):
- insmod at 72.830 s; `SODI variant 7: word 0x43d fe00ffff -> fe00f000`
  at 72.833 s.
- `sodi mm` at 147.396 s, on this fresh boot ungated (`00110000`/
  `ffffff00`, terms `4000`/`d0`), then gated (`00114000`/`ffffffd0`).
- CPU7 to CPU1 killed at 147.581-148.210 s.
- `sodi crumb 1: kick` at 150.655 s, 2.44 s after the last kill; nothing
  after it, so no kick-to-WFI line.
- Gemian (boot 1fe13bef) was up at 11:29:32. Variant 6 did not run; it
  goes to the next boot as approved, after this boot's log and journal
  are saved.

**Result.**
- **Hang: leaving the cluster ports out of the pause does not prevent
  the 221 MHz hang**, while removing the pause call entirely (variant 2,
  D5as) did.
- As the reviewer cautioned, this does not clear the cluster ports
  before variant 6 has run, and the polarity of `PAUSE2`'s low bits is
  inferred. If the polarity holds, the hazard is the pause of the other
  selected masters (`MAS_PAUSE_MASK_B` `0x6ff00b01` and `PAUSE2`'s upper
  bits), or the request itself, not the cluster ports.

| Variant 6 | Reading | Next |
| --- | --- | --- |
| Passes | The pause completes late at a low OPP: the fixed wait is too short | Variant 6 on the two-state setup unpinned, to the 50-period rule, as the fix candidate |
| Hangs | The pause held across the period breaks at a low OPP, whichever masters it selects | Split `MAS_PAUSE_MASK_B`, or fall back to the hold (0846) |

**The reviewer on variant 2 and the next splits (2026-11-23).**
- Variant 2 is "no pause request" plus one side effect: `r7` bit 2 is set
  only at `0x2b0`, called only from `0x43e`, cleared only at `0x519`, and
  its acknowledgement is never read. Removing the call also removes the
  `0x20`-cycle wait inside `0x2b0`. Variants 2 and 6 bracket that wait. A
  variant that no-ops only `0x2b0` would drop the request alone.
- If variant 6 hangs, use the shipped programs' values before bisecting
  unnamed bits. `MAS_PAUSE_MASK_B` at entry: SODI `0x6ff00b01`, deep idle
  and suspend `0x6ff00b07` (SODI's own handlers write `0x6ff00b07` too);
  `PAUSE2`: SODI `0xfe00ffff`, the others `0xfe00f000`. So:
  1. **the deep-idle pair**, `0x43a` `0x6ff00b07` with `0x43d`
     `0xfe00f000`, the combination two shipped programs use;
  2. **the polarity pair**, request kept, both mask words `0xffffffff`,
     then both `0x00000000`: with "a clear bit leaves the master out",
     all-zero should pass like variant 2 and all-ones hang.
  Each hang costs a boot; stop there if neither opens a path.
- **Otherwise accept the hold.** It is tested on both reproducers (15 of
  15 and 227 periods), its cost is known, and the PSCI power-down entry,
  the end state anyway, takes CPU0 out of the paused cluster. It needs
  the idle-path half (refuse SODI below the floor) and the owner's
  decision between a standing floor and rare entry.

### D5at variant 6: hangs at 221 MHz at the first kick (custodian, 2026-11-23)

**Approved** by the owner in the custodian's session, as D5at's second
part.

**Setup.** Fresh boot 63da1a49, cable out, battery 40 %, module a6e92c44,
`d5m.sh` blob 218631f5, D5at's command with `sodi_variant=6`, printk 8.
Started 11:43:00.

**Observed** (RAM console read in Gemian, 2294 B, kept privately):
`SODI variant 6: word 0x2b2 20000020 -> 20000200` at 67.950 s; `sodi mm`
ungated then gated at 147.939 s; CPU7 to CPU1 killed at 148.146-148.748
s; `sodi crumb 1: kick` at 151.184 s, 2.44 s later, and nothing after it.
Gemian (boot fdaac085) was up at 11:45:52. Its log (read on boot
bf0be86d) confirms `sodi_variant 6`, the pin at 221000 kHz at 11:44:54,
then `period 1, try 1` and nothing after; the journal (2724 lines) is
kept privately. Variant 7's log (read on this
boot) confirms its pin at 221000 kHz and `sodi_variant 7`, then `period
1, try 1` and nothing after; its journal (2717 lines) is kept privately.

**Result.**
- **Hang: a ten times longer wait after the request does not help.** So
  the pause does not just complete late; held across the period, it
  breaks at a low OPP.
- At 221 MHz only variant 2 (no request) has passed; variants 6 and 7
  hung at the first kick.

**Variants 8-10 (0849).**
[`0849`](../../patches/proposals/0849-soc-mediatek-mt6797-spm-sleep-add-SODI-variants-sett.patch)
(module only) sets both pause mask data words at entry, request kept,
each checked against its original before any is written:

| Variant | `0x43a` (`MAS_PAUSE_MASK_B`) | `0x43d` (`MAS_PAUSE2_MASK_B`) | Meaning |
| --- | --- | --- | --- |
| 8 | `6ff00b01` > `6ff00b07` | `fe00ffff` > `fe00f000` | The deep-idle and suspend pair |
| 9 | > `ffffffff` | > `ffffffff` | Every master selected |
| 10 | > `00000000` | > `00000000` | No master selected |

Compile-checked with `W=1`, with and without `CONFIG_CPU_FREQ` and
`CONFIG_CPU_IDLE`; checkpatch `--strict` is quiet. Buildbox build of
638e88cbe (custodian): module sha256 b5399d6c, vermagic
`7.1.3-gemini-a53-station`, listing variants 8-10.

### Request D5av (proposed): the pause masks at 221 MHz

- **Candidate:** a module from a Buildbox build carrying 0846-0849, fresh
  station boot, `d5m.sh` blob 218631f5 with D5at's command and, in turn,
  `sodi_variant=8`, then 10, then 9. Each variant up to five runs, rmmod
  and 30 s between runs, stopping that variant at its first hang; a hang
  ends the boot, so the next variant goes to the next boot. The insmod
  log must show each variant's two word changes.
- **Admission:** firmware data variants in RAM, new words; the owner
  approves them.

| 8 | 10 | 9 | Reading |
| --- | --- | --- | --- |
| Passes | — | — | The deep-idle selection works with a powered cluster at a low OPP: the fix candidate, then on the two-state setup |
| Hangs | Passes | Hangs | Polarity confirmed (a clear bit leaves the master out); some master in SODI's and deep idle's selection breaks at a low OPP: bisect from the deep-idle pair |
| Hangs | Hangs | — | The request itself breaks, whatever the masks; accept the hold (0846) |
| Hangs | Passes | Passes | The polarity reading is wrong or the masks are not master selects; stop and reread |

**The reviewer on 0849 (2026-11-23).** The words and values are right;
variant 8's pair matches deep idle's and suspend's entry stores. The new
loops sit inside the existing bound check on `sodi_variant` (an
out-of-range value fails the load first), and the `BUILD_BUG_ON` ties the
two tables' sizes. On reading 9 and 10: all ones is the registers'
resting value (the module and the vendor's init write it before each
kick), and SODI's entry narrows it, so whichever of the two means "every
master" may pause something the shipped values leave out; a hang of one
alone says little. Only the pair informs: exactly one passing gives the
polarity and allows a bisection; both hanging means the masks do not gate
what breaks, and the splitting stops at the hold.

### D5av variant 8: deep idle's pause masks hang at 221 MHz (custodian, 2026-11-23)

**Approved** by the owner in the custodian's session, as D5av's first
part.

**Setup.** Boot bf0be86d (fresh at 11:59, idle until 12:37), cable out,
battery 40 %, module b5399d6c (Buildbox 638e88cbe), `d5m.sh` blob
218631f5, D5at's command with `sodi_variant=8`, printk 8. Started
12:37:22.

**Observed** (RAM console read in Gemian, 2130 B, kept privately):
`SODI variant 8: word 0x43a 6ff00b01 -> 6ff00b07` and `word 0x43d
fe00ffff -> fe00f000` at 2384.555 s; `sodi mm` ungated then gated at
2462.310 s; CPU7 to CPU1 killed at 2462.482-2463.052 s; `sodi crumb 1:
kick` at 2465.726 s, 2.67 s later, and nothing after it. Gemian (boot
e5e2d723) was up at 12:40:04. The log and journal wait for the next
boot.

**Result.**
- **Hang: the pause selection two shipped programs use does not avoid
  it** with a powered cluster at 221 MHz.
- Variants 10 and 9 follow on the next boots, as approved. Only their
  pair informs (see the reviewer's note above): exactly one passing gives
  the polarity; both hanging ends the splitting at the hold.

### D5av variants 10 and 9: no master passes, all masters hang (custodian, 2026-11-23)

**Approved** by the owner in the custodian's session, as D5av's second
and third parts.

**Setup.** Fresh boot 02e267c5, cable out, battery 35 %, module
b5399d6c, `d5m.sh` blob 218631f5, D5at's command (`D5M_PIN_KHZ=221000`)
with `sodi_variant=10`, then 9.

**Observed** (RAM console read in Gemian, 36370 B, kept privately):
- **Variant 10, 15 of 15 periods, 5 of 5 runs** (12:51:02 to 12:57:09),
  each load logging `word 0x43a 6ff00b01 -> 00000000` and `word 0x43d
  fe00ffff -> 00000000`. Kick to first WFI, all 15 periods: 96.9 to
  98.6 µs at 221 MHz.
- **Variant 9 hung** in run 1, period 1: `word 0x43a 6ff00b01 ->
  ffffffff` and `word 0x43d fe00ffff -> ffffffff` at 639.362 s; CPU7 to
  CPU1 killed at 640.042-640.513 s; `sodi crumb 1: kick` at 642.908 s,
  2.40 s later, and nothing after it. Gemian (boot 11de809e) was up at
  13:00:16.
- **Log and journal** (read on boot 6b302727, kept privately): the pin
  line in all six runs, `cpu0 221000 kHz` before all 15 variant 10
  periods; variant 9's log ends at `period 1, try 1` at 12:59:07.

**Result.**
- **Polarity confirmed: a set bit pauses that master.** With the pause
  request raised but no master selected, 15 periods at 221 MHz returned;
  with every master selected, the first hung. Variant 2's pass was the
  absence of paused masters, not of the request or its wait.
- **So a master in SODI's selection breaks when paused at a low OPP**,
  one also in deep idle's selection (variant 8 hung). Their common bits
  are `MAS_PAUSE_MASK_B` `0x6ff00b01` and `MAS_PAUSE2_MASK_B`
  `0xfe00f000`: bits 0, 8, 9, 11, 20-27, 29 and 30 of the first, 12-15
  and 25-31 of the second, 25 in all.
- CPU0 needs about 97 µs at 221 MHz from the kick to its first WFI; the
  program waits for standby before the pause, so this time alone does not
  race it.

**Variant 11 (0850).**
[`0850`](../../patches/proposals/0850-soc-mediatek-mt6797-spm-sleep-add-a-SODI-variant-tak.patch)
(module only) adds variant 11, which writes the two mask words from
load-time parameters `sodi_pause_mask` and `sodi_pause2_mask` (defaults:
the program's own values), after the same check of the originals. The
bisection then needs no build per step. Compile-checked as before;
checkpatch `--strict` is quiet.

### Request D5aw (proposed): bisect the paused masters at 221 MHz

- **Candidate:** a module from a Buildbox build carrying 0846-0850,
  `d5m.sh` blob 218631f5 with D5at's command and `sodi_variant=11
  sodi_pause_mask=X sodi_pause2_mask=Y` in `D5M_ARGS`. A hang ends the
  boot. The insmod log must show both words.
- **The program session's groups (2026-11-23),** from which paths widen
  or narrow each mask (no source names the bits; 1 = paused):

  | Group | Word | Bits | Where the programs pause it |
  | --- | --- | --- | --- |
  | A | 1 | 0 (`0x00000001`) | every value |
  | B | 1 | 8, 9, 11 (`0x00000b00`) | every value |
  | C | 1 | 20-27 (`0x0ff00000`) | every value; never touched by a power step |
  | D | 1 | 29, 30 (`0x60000000`) | every value |
  | E | 1 | 1, 2 | deep idle and suspend; exempt in SODI (likely display or MM) |
  | F | 1 | 3-5, 7, 10, 16 | only for the EMI clock-off |
  | G | 1 | 12-15, 17-19, 28, 31 | only before the AXI clock goes off |
  | H | 2 | 12-15 (`0x0000f000`) | every value; next to the cluster steps, never stepped |
  | I | 2 | 25-31 (`0xfe000000`) | every value |
  | J | 2 | 0-11 | the CPU cluster steps around MP0's power-off |
  | K | 2 | 16-24 | only before the AXI clock goes off |

  The common hanging set is A-D and H-I. *Inference:* H could be an
  MCUSYS-level port (the CCI or the A72 path), which would fit a clock-rate
  effect; C looks like core infra masters.
- **Steps by group** (each alone, the rest 0), in this order: H
  (`0`/`0x0000f000`), I (`0`/`0xfe000000`), C (`0x0ff00000`/`0`), D, B,
  A. The first group that hangs is bisected bit by bit. If none hangs
  alone, two groups are needed together; stop and report.
- **Steps by halves** (the fallback if the groups mislead), starting from
  the common set (`0x6ff00b01`/`0xfe00f000`), assuming one master:
  1. `0x6ff00b01`/`0`: the first word alone. Hangs → the culprit is in
     it; passes → step 1b, `0`/`0xfe00f000`, to confirm the second.
  2. Halve the word that hung, keeping the other 0, until one bit is
     left: about four more steps for the first word's 14 bits, four for
     the second's 11. A pass costs five runs, a hang a boot.
  3. Confirm with SODI's own values minus that bit, five runs.
- If no single bit hangs alone but a set does, two masters interact;
  stop and report.
- **Pass rule per step (reviewer):** every hang at 221 MHz has come at the
  first kick, so an intermediate step passes after two runs (six
  periods); only the final checks run five (15 periods): SODI's masks
  minus the bit must pass, and the bit alone must hang.
- **Reviewer on 0850:** correct, no finding; variant 11 without mask
  parameters reproduces the stock program, a control to run only if a
  later result looks odd. A culprit bit is a fix only if its master can
  be named or shown idle here; leaving an unnamed master unpaused before
  the clock cut may not be acceptable, and then the hold stays the fix and
  the bit is the explanation.
- **Admission:** firmware data variants in RAM, new values each step;
  the owner approves the bisection as a whole or step by step.

**What a culprit bit gives.** SODI with its own masks minus that master is
the fix candidate, a pause selection nearest the vendor's, at no power
cost; it then goes to the two-state setup unpinned, to the 50-period rule.

### D5aw: the group bisection at 221 MHz (custodian, 2026-11-23, running)

**Approved** by the owner in the custodian's session, as a whole.

**Setup.** Boot 6b302727 (up 13:03, no SPM module before 13:19), cable
out, battery 32 %, module 17a226f4 (Buildbox 296a8dbf2), `d5m.sh` blob
218631f5, D5at's command (`D5M_PIN_KHZ=221000`) with `sodi_variant=11`
and each group's masks; two runs per step.

| Step | Group | `sodi_pause_mask` / `sodi_pause2_mask` | Result |
| --- | --- | --- | --- |
| 1 | H | `0` / `0x0000f000` | **Passed**, 6 of 6 periods at 221 MHz (13:20:57, 13:22:18); both words logged as set |
| 2 | I | `0` / `0xfe000000` | **Passed**, 6 of 6 (13:24:29, 13:26:05) |
| 3 | C | `0x0ff00000` / `0` | **Hung**, run 1 period 1: words logged `0ff00000`/`00000000` at 1530.614 s, CPU7-1 killed by 1532.023 s, `kick` at 1534.505 s and nothing after; Gemian (boot 69575400) at 13:29:19. RAM console (29668 B) kept privately |
| 4 | C, bits 20-23 | `0x00f00000` / `0` | **Passed**, 6 of 6 on fresh boot 8cac7635 (13:36:47, 13:38:06): the GPU pair (21, 23) and bits 20 and 22 alone do not hang |
| 5 | C, bits 24-27 | `0x0f000000` / `0` | **Hung**, run 1 period 1, same boot after step 4: words logged `0f000000`/`00000000` at 353.748 s, CPU7-1 killed by 354.965 s, `kick` at 357.354 s and nothing after; Gemian (boot 85c7fa18) at 13:41:11. RAM console (15854 B) kept privately |
| 6 | bits 24-25 | `0x03000000` / `0` | **Hung**, run 1 period 1, fresh boot 6b69c5e9: words logged `03000000`/`00000000` at 65.251 s, CPU1 killed at 148.130 s, `kick` at 150.568 s and nothing after; Gemian (boot 31de2d5c) at 13:45:07. RAM console (2259 B) kept privately; boot 8cac7635's log and journal also kept |
| 7 | bit 24 | `0x01000000` / `0` | **Passed**, 6 of 6 on fresh boot 7ffdbbaf (13:48:14, 13:49:32) |
| 8 | bit 25 | `0x02000000` / `0` | **Hung**, run 1 period 1, same boot after step 7: words logged `02000000`/`00000000` at 354.494 s, CPU1 killed at 355.708 s, `kick` at 358.022 s and nothing after; Gemian (boot 08d4dfdc) at 13:52:34. RAM console (15854 B) kept privately |
| 9 | SODI's masks minus bit 25 | `0x6df00b01` / `0xfe00ffff` | **Passed**, 15 of 15 periods in five runs on fresh boot 5b631a0d (13:56:10 to 14:03:38), every load logging `6ff00b01 -> 6df00b01` and `fe00ffff -> fe00ffff`, CPU0 at 221000 kHz before every write; kick to first WFI 97.0-98.4 µs. Logs and journals kept privately |

**D5aw result.** **Bit 25 of `MAS_PAUSE_MASK_B` is the whole of the
no-driver hang at 221 MHz:** paused alone it hangs at the first kick;
SODI's own selection without it runs 15 of 15 periods at the rate that
otherwise always hangs. Its neighbour bit 24 and every other group pass
alone.

- **The culprit is bit 25 of `MAS_PAUSE_MASK_B`.** Paused alone, it
  hangs the first period at 221 MHz; its neighbour bit 24 alone passes,
  as do every other group tested alone. So one master, not a shared
  acknowledgement. No source names it; it lies in group C, which all
  three of the vendor's programs always pause.
- Bit 25 alone is not repeated: its hang came at the first kick, as every
  221 MHz hang has, and a repeat would end there too.

**The program session on bit 25 (2026-11-23).** No source names it.
- Nothing in the vendor's MT6797 tree writes or polls bit 25 of
  `0x10001220` or `0x10001228`. The one table with a bit 25 (a legacy
  power file with MD1 at 24-28) matches mainline's MT6735 definitions
  exactly and contradicts this chip's measured MD1 bits, so it is carried
  over and discounted.
- MT8173's mainline bus-protect table parallels this chip's in places
  (MM at 1 and 2, MFG at 21-23) but defines nothing above 23; other
  mainline tables reuse bit 25 for unrelated masters, so it has no
  cross-chip meaning.
- *Decision input, inference:* bit 25 reads active in `PROTECTSTA1` in
  normal running, sits in a group no power-down step touches, and is
  paused by every program at entry, through the AXI clock-off. Leaving it
  unpaused in SODI is plausibly safe only while nothing in the period
  cuts the clock or power under that master; that would not hold for the
  EMI clock-off or infra-down paths, which assume it is paused. Our
  periods run with `SODI_NO_EVENT` (no self-refresh), but the program
  still cuts the ARM clocks and switches the `ddrphycfg` mux. A safer fix
  than unpausing would stop that master before the kick, which needs its
  name; a read of the infra bus idle status (the vendor's power driver
  defines `INFRA_BUS_IDLE_STA5` at infra `0x190`) around the kick might
  identify it.

**The reviewer on bit 25 (2026-11-23).**
- The same searches: the vendor's compiled power table names nothing at
  24-27; the older file with MD1 at 24-28 is not even compiled and
  contradicts the measured `PROTECTEN`. Mainline has no table for this
  chip or its siblings. On at least one other MediaTek chip, bits in that
  range of a second protect register are CPU-side bridge requests (an
  infra bridge at 24, a cluster L2 FIFO at 27), so "a bridge on the AP
  MCU side" is a reasonable guess here, no more.
- Deep idle (`0x4b8`), suspend (`0x49c`) and the vcore programs store
  `0xffff` to `INFRA_TOPAXI_PROTECTEN`; SODI never writes it.
- *Reading, low confidence:* a master on the AP MCU side that is busy or
  slow to quiesce when the cluster clock is low, paused without an
  acknowledgement check, then the clock cut. The vendor never meets it
  because its CPU0 has left coherency in the firmware before the pause.
  If so, the hold is a workaround for the missing firmware entry, the
  PSCI power-down path is the fix that removes the cause, and SODI minus
  bit 25 would be safe only by luck.
- **Identifying it by behaviour, cheapest first:**
  1. Read only, no period: `PROTECTSTA0` (`0x10001224`) and
     `PROTECTSTA1` (`0x10001228`) with CPU0 pinned at 221 MHz, then at
     1547 MHz. A bit that differs between the rates is a first direct
     link between the OPP and a master.
  2. The queued check (SODI's masks minus bit 25, 15 periods at
     221 MHz), then the same on the two-state setup unpinned, to 50
     periods.
  3. Only with a register-write admission: set `PROTECTEN` bit 25 from
     Linux at 1547 MHz without SODI and watch `PROTECTSTA1` bit 25 and
     the system. If it dies at once, bit 25 is a path CPU0 itself needs.
     It costs a boot; last.

- **The culprit is in bits 24-27** of `MAS_PAUSE_MASK_B`. No source names
  them (program session: none of the vendor's CPU DVFS, hotplug or SPM
  CPU code writes them). All four read 0 in `PROTECTSTA1` at
  the GPU probe (`0xe0415cb8`), which under the program session's reading
  of that register as idle status means not idle. *Inference (program session):* with the
  GPU, display and modem cleared and the hang tied to CPU0's clock, they
  may be MCUSYS-side ports into infra (cluster or CCI paths) or
  peripheral DMA paths.

- **Group C holds the culprit:** with only its eight bits paused, the
  first period at 221 MHz hung, as SODI's full selection does. Groups H
  and I alone passed. *Inference (program session):* C is never touched
  by a power step and looks like core infra masters.
- **Bisection of C:** bits 20-23 (`0x00f00000`) first. If they hang,
  `0x00300000`, then one bit; if they pass, bits 24-27 (`0x0f000000`)
  must hang to confirm, then `0x03000000`, then one bit. If neither half
  hangs alone, two bits of C are needed together; stop.

**The reviewer on group C (2026-11-23).**
- No source names bits 20-27: every vendor header describes
  `SPM_MAS_PAUSE_MASK_B` as one 32-bit field written `0xffffffff` at
  init, and no code touches single bits.
- Every value any of the three programs writes to the first word has
  bits 20-27 set (`0x6ff00b01`, `0x6ff00b07`, `0x6ff10fbf`,
  `0xffffffbf`): the vendor pauses these masters in every mode, so the
  failure is specific to our entry, a retained, clocked cluster at a low
  OPP.
- They are never stepped by a power routine. *Guess from shape:* eight
  contiguous always-set bits fit the ports of one shared resource, such
  as the memory controller's master ports (the AP cluster's among them).
- Once a bit hangs, test its neighbours alone too: exactly one points at
  one master, all eight at a shared acknowledge.
- *A later option:* the program never reads the acknowledgement
  (`R13` bit 22), but a second CPU could read `PCM_REG13_DATA` during a
  passing variant 10 or 11 period and before a hang; an acknowledgement
  that never comes at 221 MHz but does at 1547 MHz would be the
  mechanism. The CPU8 observer was retired at D5u, so that is a new kind
  of test, not proposed now.
- **The fix stays cautious:** with all three shipped programs pausing
  this group, stock masks minus the bit should not ship without an
  explanation of why it is safe here; the hold stays the default until
  then.

**The program session: the first word looks like the infra bus-protect
layout (2026-11-23).** *Inference from matching groups.*
- `MAS_PAUSE_MASK_B`'s groups match the vendor's MT6797 bus-protect masks
  for `INFRA_TOPAXI_PROTECTEN` (`0x10001220`): MD1 = bits 3, 4, 5, 7, 10,
  16, exactly group F (paused only around the EMI clock-off); the display
  = bits 1, 2, exactly group E (exempt in SODI; mainline's scpsys uses the
  same bits for the MM domain); CONN = 17, 18 and C2K = 13-15, inside
  group G (paused only before the AXI clock goes off); **MFG (the GPU) =
  bit 21, inside group C**. An older vendor power file with another layout
  disagrees with both and is discounted.
- So in C, bit 21 is the GPU and bits 20 and 22-27 are unnamed.
  *Inference:* the rest of C is likely always-on infra or peripheral DMA
  paths, since modem, CONN and display have their own groups.
- **A read-only check that could shrink the search:**
  `INFRA_TOPAXI_PROTECTEN` (`0x10001220`), `PROTECTSTA0` (`0x10001224`),
  `PROTECTSTA1` (`0x10001228`), `PROTECTEN_1` (`0x10001250`) and
  `PROTECTSTA1_1` (`0x10001258`) on the running station. A bit already
  protected marks a master already parked, unlikely to wedge when paused
  again; the unprotected bits of C are the candidates.
- If the bisection lands on bit 21, the next question is whether mainline
  leaves the GPU's power domain on and unprotected while idle.

**The reviewer on the GPU path (2026-11-23),** from the station's tree:
- The GPU's bus protection is two bits, 21 and 23 of
  `INFRA_TOPAXI_PROTECTEN` (polled on `PROTECTSTA1`), both in group C and
  both in the first half being tested (`0x00f00000`).
- The panfrost glue for this chip enables runtime PM with a 50 ms
  autosuspend: on suspend it waits for the GPU to idle, sets protection on
  bits 21 and 23, then powers the domains off; on resume it releases the
  protection last; at probe it asserts it first. The power-domain table
  gives the MFG domains no protection of their own and keeps them off by
  default; the bootloader may leave `MFG_ASYNC` on.
- So the GPU port's state at a period depends on whether the GPU module
  is loaded: loaded and idle, it is off and protected, as the vendor's
  idle is; not loaded, nothing has protected it, and its domain is as the
  bootloader left it. The bus-protect read answers which.
- *Caution:* a parked or unpowered master that never acknowledges would
  fail at every rate, yet D5ap and D5au passed 242 periods at 1547 MHz
  with the stock masks. If the bit is 21 or 23, either the GPU's state
  differed between those boots and the hanging ones (whether the GPU
  module was loaded on each is worth checking in the journals), or the
  rate dependence comes through something shared with the cluster clock.
- *Cheap discriminators if it lands there, no build:* the same pinned-low
  run with the GPU module loaded and idle, against not loaded, each with
  the bus-protect bits read first.

**The GPU on every boot (custodian, from saved journals).** On all eight
boots checked (1d3a0381, 58210a12, ccca15a4, fcebb465, 63da1a49,
bf0be86d, 02e267c5, 6b302727), the panfrost module and the MFG clocks
load at boot with identical lines, timestamps aside, passing and hanging
boots alike. So the GPU module's presence does not separate them. The
journal has no runtime-PM lines; whether MFG was suspended at a kick
would need a sysfs read, not yet approved.

The panfrost glue prints, at probe, `protect 0x104b8/0xe0415cb8`: the
values of `INFRA_TOPAXI_PROTECTEN` and `PROTECTSTA1` before it asserts
its own protection. Decoded:
- `PROTECTEN` `0x000104b8` = bits 3, 4, 5, 7, 10 and 16, **exactly the
  vendor's MD1 mask and group F**: the modem is off and protected. This
  is direct support for the program session's reading that the pause mask
  and the bus-protect register share one layout. No bit of group C is
  enabled at that point.
- `PROTECTSTA1` `0xe0415cb8` = bits 3, 4, 5, 7, 10, 11, 12, 14, 16, 22,
  29, 30 and 31: of group C only bit 22 reads acknowledged, without its
  enable; 21 and 23 (the GPU's) do not.
- After probe panfrost protects 21 and 23 whenever the GPU
  runtime-suspends (50 ms autosuspend), so at an idle period they are most
  likely protected on every boot.

**The program session on the order (2026-11-23).** No source names bits
20, 22 or 24-27. `PROTECTSTA1` also reports bits never requested in
`PROTECTEN` (11, 12, 14, 22, 29-31), so it reads as per-master idle
status, not only a protect acknowledgement (*inference*); bit 22 is then
already idle, and 20, 21 and 23-27 are the active candidates. **Revised
bisection of C:** if `0x00f00000` hangs, test the GPU pair `0x00a00000`
(21 and 23) next, then 21 and 23 alone; if it passes, `0x00500000`. If
`0x00f00000` passes, `0x0f000000` as before. If the GPU pair is the
culprit, the GPU's runtime-PM state at the kick (powered with live ports,
or off without its protection) is the next question, testable without a
firmware patch by unbinding panfrost or holding the GPU powered.

### Request D5ax (proposed): the two-state setup unpinned, without bit 25

Whether the one master accounts for the original reproducer too, with
CPU0 free to run at any OPP.

- **Candidate:** module 17a226f4 (Buildbox 296a8dbf2), fresh station
  boot, `d4.sh` (commit recording this, which takes `D4_VARIANT` 8-11 and,
  for 11, `D4_PAUSE_MASK` and `D4_PAUSE2_MASK`) with D5ac's two-state env
  (`D4_CIRQ_LEVEL=1 D4_NO_EVENT=1 D4_MARK=1 D4_MM=2 D4_NO_MP2=1
  D4_ACINACTM_LATE=1 D4_MASK_PPI=1 D4_CRUMBS=1`) plus `D4_VARIANT=11
  D4_PAUSE_MASK=0x6df00b01 D4_PAUSE2_MASK=0xfe00ffff`, no pin, pings over
  window C, cable out.
- **Pass rule:** 50 clean periods summed over windows, against eleven
  hangs at periods 1-28 in the same setup with the stock masks.
- **Admission:** a variant value already run (D5aw step 9); the owner
  approves the run.

| Result | Reading | Next |
| --- | --- | --- |
| Passes 50 | One paused master explains both reproducers | The fix decision, with the master unnamed: the hold (0846, and its idle-path half), SODI minus bit 25, or the PSCI power-down entry that removes the cause; the owner's call, with the reviewer's caution that minus bit 25 may be safe only by luck |
| Hangs | The two-state setup has a second hazard besides bit 25 | Pin it at 1547 MHz with the variant to separate them |

**The reviewer on what the fix decision needs (2026-11-23).**
1. **The hold's floor:** with stock masks, D5ar hung at 1118 MHz and
   every clean period started at 1274 MHz or more. Pinned `d5m.sh` runs
   at the table entries between (1222, 1274, 1339 MHz) would state the
   floor and so the hold's power cost.
2. **Minus bit 25 where the pause matters:** the passes so far show that
   periods return, not that cutting clocks with that master running is
   safe. Two checks: the same masks under activity (pings, card I/O just
   before a period, the GPU not yet suspended), and a long unpinned run of
   several hundred periods watching for faults other than hangs (a
   corrupted wake line, an odd `r13`, later MMC or Wi-Fi errors), since a
   master cut mid-transfer more likely shows as a rare downstream fault.
3. **The acknowledgement:** `R13` bit 22 seen from a second CPU during a
   stock-mask period at 1547 MHz and a minus-bit-25 period at 221 MHz.
   Set at 1547 MHz with bit 25 paused would say the master quiesces there
   and fails to at low rates. It needs the retired CPU8 observer, a new
   kind of test.
- *The reviewer's recommendation:* the hold now (tested on both
  reproducers, cause-agnostic, its floor from measurement 1), the PSCI
  power-down entry as the fix (the vendor's configuration, which removes
  the clocked, coherent cluster under the pause; it needs an image and
  its own bring-up), and minus bit 25 kept as the explanation unless 2
  and 3 make it trustworthy, and even then provisional.

### The bus-protect reads at rest and at two rates (custodian, 2026-11-23)

**Approved** by the owner in the custodian's session (read only).

**Setup.** Fresh boot 3bc7b33e (14:32:50), cable out, no SPM module
loaded, panfrost loaded; read at about 30 s of uptime. Policy0 was
221000-1547000 (schedutil, `cur` 481000) and was restored after.

| Register | At rest | Pinned 221000 kHz (3 reads) | Pinned 1547000 kHz (3 reads) |
| --- | --- | --- | --- |
| `PROTECTEN` `0x10001220` | `00a104b8` | — | — |
| `PROTECTSTA0` `0x10001224` | `effffdff` | `effffdff`, `effffdfe`, `effffdff` | `effffdff` ×3 |
| `PROTECTSTA1` `0x10001228` | `e0e15cb8` | `e0e15cb8` ×3 | `e0e15cb8` ×3 |
| `PROTECTEN_1` `0x10001250` | `00000000` | — | — |
| `PROTECTSTA1_1` `0x10001258` | `00000000` | `00000000` ×3 | `00000000` ×3 |

**Reading.**
- `PROTECTEN` now holds the modem's bits (`0x000104b8`) plus 21 and 23,
  the GPU's, and `PROTECTSTA1` shows 21 and 23 as well, against the GPU
  probe's `0x104b8`/`0xe0415cb8`: the idle GPU is runtime-suspended and
  protected, as the panfrost glue does. `PROTECTSTA1` acknowledges each
  requested bit.
- **No bit differs with CPU0's rate at rest,** bit 25 included: it reads
  0 in `PROTECTSTA1` at both rates, and 1 in `PROTECTSTA0`, whose only
  change was bit 0, clear in one read at 221 MHz. So the rate link to
  bit 25's master does not show while CPU0 is running; if it exists, it
  shows only once the cluster is in WFI and the master is paused.
- The second protect register is unused here (0 throughout).

### Request D5ay (proposed): the floor with stock masks

- **Candidate:** module 17a226f4 (variants off), `d5m.sh` blob 218631f5
  with D5ao step 3's command and `D5M_PIN_KHZ` at 1274000, then 1222000
  if 1274000 passes, or 1339000 if it hangs. Five runs per point, first
  hang ends the boot.
- **Admission:** cpufreq limits, as D5ap and D5ar; the owner approves.
- Its result sets the hold's floor (`sodi_min_khz` for test periods, and
  the threshold of a future idle-path refusal).

### D5ay at 1274 MHz: hangs at the first kick (custodian, 2026-11-23)

**Approved** by the owner in the custodian's session, with D5ax; D5ay
ran first so D5ax could follow on the same boot after a pass.

**Setup.** Boot 3bc7b33e (fresh at 14:32, only the read-only protect
reads before), cable out, battery 23 %, module 17a226f4 with stock masks
(no variant), `d5m.sh` blob 218631f5, D5ao step 3's command plus
`D5M_PIN_KHZ=1274000`. Started 14:59:16.

**Observed** (RAM console read in Gemian, 1950 B, kept privately): no
variant line at insmod; `sodi mm` ungated then gated at 1687.528 s; CPU1
killed at 1688.337 s; `sodi crumb 1: kick` at 1690.684 s, 2.35 s later,
and nothing after it. Gemian (boot 9d72e249) was up at 15:01:20. D5ax did
not run.

**Result.**
- **1274 MHz hangs** with the stock masks. `d4.sh`'s clean periods that
  logged 1274-1391 MHz read the frequency about 1 s before the kick, so
  CPU0 may have been higher at the kick itself; they do not contradict
  this.
- The floor lies above 1274 MHz: 1339000 next, and if it hangs, 1443000,
  then 1495000. A floor near the top OPP would make the hold close to a
  standing maximum frequency for every period.

### D5ay at 1339 MHz: four clean periods, then a hang (custodian, 2026-11-23)

**Setup.** Fresh boot cbe2c769, cable out, battery 25 %, module 17a226f4
with stock masks, `d5m.sh` blob 218631f5, D5ao step 3's command plus
`D5M_PIN_KHZ=1339000`. D5ay at 1274 MHz's log (read on this boot)
confirms its pin at 1274000 kHz before period 1.

**Observed** (RAM console read in Gemian, 10071 B, kept privately):
- Run 1: 3 of 3 periods returned (done 15:25:34); kick to first WFI
  29.0, 29.2 and 29.5 µs.
- Run 2: insmod at 225.92 s; CPU1 killed at 227.077 s; period 1 kick at
  229.265 s, returned (29.4 µs to WFI); `sodi crumb 2: kick` at
  230.672 s and nothing after it. Gemian (boot 54e83e64) was up at
  15:27:47. D5ax did not run.
- **Log and journal** (read on boot a3c38b62, kept privately): the pin at
  1339000 kHz in both runs; run 2's last lines are `cpu0 1339000 kHz just
  before the write` at 15:26:49 and `period 2, try 2`, so the pin held for
  the hanging kick.

**Result.**
- **1339 MHz hangs too, but later:** four clean periods, then a hang at
  the fifth kick. With stock masks and CPU0 pinned, the first hang came
  at kick 1 at 221 and 1274 MHz, kick 2 at 1118 MHz and kick 5 at 1339
  MHz, while 1547 MHz ran 15 of 15 (D5ap) and the two-state setup 227
  periods. The hazard falls as the rate rises rather than stopping at a
  clean edge; whether 1443 or 1495 MHz is safe needs those points.
- Kick to first WFI: about 29 µs at 1339 MHz against 97-98 µs at
  221 MHz, a ratio of about 3.3 for a rate ratio of about 6, so CPU0's
  path to WFI is not purely CPU-clock bound.
- *For the decision:* a hold would sit at or near the top OPP for every
  period.

**The reviewer's recommendation after D5ay (2026-11-23).**
- **The hold is withdrawn as a fix.** A graded hazard has no safe floor,
  only a rate: 0 hangs in about 545 periods at 1547 MHz bounds the rate
  near 0.5 % per period (95 % confidence), and the trend says it falls
  without reaching zero. An idle state entered thousands of times an hour
  would still reboot within hours or days, and the hold would cost the
  top OPP on every entry. It stays a test convenience; its idle-path half
  is not drafted.
- **No interim is needed:** the SODI idle state is off by default and no
  user path enters it.
- **Minus bit 25** becomes the better tool for experiments if D5ax
  passes, since it does not depend on the rate; it is still not a fix,
  and the graded result fits a master that is sometimes mid-activity at
  the pause.
- **Recommendation:** stop refining the legacy entry and build the PSCI
  power-down entry: flag 0 clear, CPU0 through `CPU_SUSPEND`, flag 15
  set as the vendor has it, bits 3, 4, 5 and 9 kept at first so no rail
  moves; test it first pinned at 221 MHz, where the legacy entry fails at
  the first kick. 1443 and 1495 MHz are then not worth their boots.
- About 15 µs of the kick-to-WFI window does not scale with the CPU
  clock (bus register access, most likely); it does not change the
  conclusion.
- *The one reading still worth a boot on the legacy path:* `R13` bit 22
  from a second CPU on a returning and a hanging period at 1339 MHz,
  which would say whether PSCI removes the cause or only the symptom.
  That needs the retired observer.

### The owner's decision: stop for the PSCI entry (2026-11-23)

The owner chose "stop for PSCI work" in the custodian's session. D5ay's
1443 and 1495 MHz points and D5ax were not run. Refinement of the legacy
entry (CPU0 powered and coherent in WFI under the program) stops here,
with all its evidence saved.

**The diagnosis it rests on.** With CPU0 kept powered and coherent, the
program's pause of one bus master, bit 25 of `MAS_PAUSE_MASK_B`, hangs
with a probability that falls as CPU0's clock rises (D5ap-D5ay); without
that bit, or without any paused master, periods return at 221 MHz
(D5av, D5aw). The vendor never meets it: its CPU0 is flushed, out of
coherency and in the firmware's WFI before the pause.

### The PSCI power-down entry (0851, 0852)

- [`0851`](../../patches/proposals/0851-firmware-psci-export-psci_cpu_suspend_enter.patch)
  (**built in**) exports `psci_cpu_suspend_enter()`, the helper that
  issues PSCI `CPU_SUSPEND` with arm64's context save and resumes at
  `cpu_resume`. It is the one built-in change S2 always needed; it needs
  a new image and changes nothing until a module calls it.
- [`0852`](../../patches/proposals/0852-soc-mediatek-mt6797-spm-sleep-optionally-power-CPU0-.patch)
  (module) adds `sodi_cpu_pdn` (default off). In `sodi_once_ms` periods
  it clears flag bit 0, skips the `ACINACTM` writes, and in place of the
  WFI loop calls `cpu_pm_enter()`, `psci_cpu_suspend_enter(0x01010000)`
  and `cpu_pm_exit()`; the return is read from `SPM_IRQ_STA` as before.
  CPU0's timer compare values are saved and restored around the period,
  since a powered-down core comes back with its timer registers reset.
  The kick-to-WFI line also logs `cpu pdn` and the PSCI path's result.
  The cpuidle path is unchanged.
- What the firmware does with that request is on the
  [hardware page](../../docs/hardware/mt6797-spm-sleep.md#1-the-secure-firmwares-suspend-path):
  it clears CPU0's retention, sets the warm-boot entry, turns off the GIC
  CPU interface, takes the cluster out of CCI and lets the L2 reset, then
  waits in WFI for the program to power the core off and back on.
- Compile-checked with `W=1`, with and without `CONFIG_CPU_FREQ` and
  `CONFIG_CPU_IDLE` (without `CONFIG_CPU_IDLE` the PSCI call compiles out
  and returns `-EOPNOTSUPP`); checkpatch `--strict` is quiet.

**The program session on the flag-0-clear path (2026-11-23),** with
D6a's `SPM_SW_FLAG` `0x0009b238`. It needs no flag we do not set.
- **Entry:** `0x427` waits for AP standby alone (`0x5000aaaa`, no wake
  escape), then the pause masks and the master pause (`0x438`-`0x43e`)
  as before: **the pause still precedes the power-down.** `0x445`
  clears `R7_CSYSPWRUPACK`. `0x5bb`-`0x610` power off `MP0_CPU0`,
  `MP0_CPUSYS` (stepping `PAUSE2` `f00f` > `f0ff` > `f7ff` > `ffff`),
  `MP_TOP` SRAM and `MCUSYS`, and set `CPU_EXT_BUCK_ISO` to 3; the polls
  have no timeout and no step checks CPU state. `0x44a` is this path's
  wake abort, which powers back up without a clock restore. Flag 9 skips
  the I2C6 buck write; then the clock cut and the main wait.
- **Exit:** the clock restore, then `0x318` powers `MCUSYS`, `MP_TOP`
  SRAM, `MP0_CPUSYS` (stepping `PAUSE2` back to `fe00f000`) and
  `MP0_CPU0` on, reset last, sets `CPU_EXT_BUCK_ISO` to 2, releases the
  pause and raises `SW_INT`. CPU0 restarts into the firmware's warm boot.
- **What must already hold:**
  - CPU1-3, the whole MP1 cluster and MP2 fully powered off, cluster
    `CPUSYS` included, since `MCUSYS` going off cuts everything below it.
  - The standby AND over the eight `WFI_EN` cores; powered-off cores
    satisfied it in every returned period so far. If it never holds, the
    program waits at `0x5000aaaa` for ever.
  - `CPU_EXT_BUCK_ISO` bit 1 stays set after each period; the A72
    module's bring-up already clears bits 1:0 before CPU8 returns
    ([cluster page](../../docs/hardware/mt6797-cpu-clusters.md#33-a72-external-preparation-and-mp2-control)).
- **Bit 25:** the PSCI path protects only if that master's stuck traffic
  originates in the cluster, which the firmware's flush and CCI exit
  remove; unproven. Test with the stock masks first; SODI's masks minus
  bit 25 stay as the fallback.

**Flags and the power check (program session, 2026-11-23).**
- SODI tests only flags 0, 8, 9, 10, 12, 13 and 15 on this path. With
  `0x0009b238`: 0 clear (power-down), 8 clear (`CSYSPWRUPACK` dropped and
  restored), 9 set (I2C6 buck write skipped), 10 clear (SCP branch as
  before), 12, 13 and 15 set. Bit 7 is tested only inside handlers that
  never run here, and bits 16-19 nowhere. `SW_RSV_5` feeds `r6` bits 23
  and 24 and stays as in the passing runs.
- **`CPU_PWR_STATUS` (`0x10006188`) and `_2ND` (`0x1000618c`):** CPU n at
  bit 15 - n (from the firmware's power waits; CPU0 = 15 also from the
  program), `MP2_CPUSYS` 17 (the firmware's A72 power-off polls it, then
  sets `CPU_EXT_BUCK_ISO` bit 1 itself), `MP0_CPUSYS` 19, `MCUSYS` 21;
  `MP1_CPUSYS` 18 and `MP_TOP` 20 inferred from the ordering. The
  firmware treats CPUs 6 and 7 specially in one path.
- **0852 now refuses a powered-down period** unless both words read 0 in
  bits 6-14, 17 and 18 (CPU1-9, MP2 and MP1), and logs the two words and
  `CPU_EXT_BUCK_ISO` before and after with the kick-to-WFI line. A wrong
  inferred bit refuses periods rather than letting one through, except
  that an unpowered MP1 reported elsewhere would pass unseen; the first
  read below settles it.
- **A read first, before D6a:** both status words and `CPU_EXT_BUCK_ISO`
  with all ten CPUs online, then with CPU4-7 offline, then with CPU1-9
  offline (read only). It confirms bits 18 and 20 and the CPU6/7 case,
  and `CPU_EXT_BUCK_ISO` bit 1 should read set once the A72s are off.

**The reviewer on 0851 and 0852 (2026-11-23),** against the firmware
disassembly, the vendor's entry and the saved boot logs. No blocking
finding.
- Every saved boot reports PSCI 0.2, so `0x01010000` takes the
  `cpu_suspend()` branch with the context save; the vendor's DT and SODI
  use the same value.
- For this state the firmware clears CPU0's retention, sets the warm
  entry, deactivates the GIC CPU interface, takes the cluster out of CCI,
  **sets `ACINACTM` for MP0 itself**, lets the L2 reset, backs up the
  timer and saves the GIC distributor and redistributor. So skipping the
  module's `ACINACTM` writes and leaving GIC state to the firmware are
  right; after resume the vendor re-initialises only the GIC CPU
  interface, timer and debug registers, as mainline's `CPU_PM_EXIT`
  notifiers do.
- `cpu_pm_enter`/`exit` is enough (no cluster notifier is needed); the
  GIC masks are harmless, since the program, not the GIC, powers CPU0
  back on and the firmware restores the masked state, which
  `spm_gic_restore()` then undoes; the debugfs task's context is
  acceptable, as system suspend does the same (at most one cosmetic WARN
  with `CONFIG_RCU_EQS_DEBUG`), provided `sc->idle` stays false here and no
  RCU read lock is held.
- **Two changes, made in 0852:** a powered-down period needs CPU0 to be
  the only online CPU (the observer's CPU8 included; D6a runs without
  `sodi_obs`); and the return flag is polled for up to 5 ms after the
  warm boot, since the program raises its interrupt last.
- **One invariant, now commented in 0852:** after a failed power-down the
  kicked program still waits for CPU0's standby with flag 0 clear, so
  CPU0 must take no WFI before `spm_restore()` stops the PCM, or the
  program would power it off without the firmware.
- This firmware's `psci_power_down_wfi` is `wfi; b .`: a WFI that falls
  through leaves CPU0 spinning in EL3, so there is no abort return on this
  chip, one candidate if D6a hangs after the `kick` crumb. The CNTP
  backstop cannot fire with CPU0 off.
- **What D6a runs for the first time:** the program's CPU power-down and
  power-up routines under this module, and CPU0 through the firmware's
  warm entry on mainline. The flag word still differs from the vendor's
  in bits 3, 4, 5, 9, 13, 18 and 19; it stays as planned for the first
  run.
- **Reading a pass:** five clean runs at 221 MHz with `cpu pdn 1 ret 0`
  and a sane wake line, then the tick running, interrupts counting and
  CPU1 coming back online (MCUSYS and the CCI after a cluster power
  cycle). After a hang the crumbs cannot say whether CPU0 reached the
  firmware; the SPM status read from boot2 is the tool.

### Request D6a (proposed): SODI with CPU0 powered down, pinned at 221 MHz

- **Hypothesis:** with CPU0 out of coherency in the firmware's WFI, the
  pause of bit 25's master no longer hangs at a low OPP.
- **Unique observation:** the first SODI period on mainline with CPU0
  powered down through the firmware, and whether it returns at 221 MHz,
  where the legacy entry fails at the first kick.
- **Candidate:** a station image carrying 0851 (and 0846-0850, 0852 as
  modules) from a Buildbox build of the commit recording this stage,
  written to boot2 with `flash-boot2`; module `mt6797-spm-sleep.ko` from
  the same build.
- **Run:** `d5m.sh` blob 218631f5 with D5ao step 3's command plus
  `D5M_PIN_KHZ=221000` and `sodi_cpu_pdn=1 sodi_keep_26m=1` in
  `D5M_ARGS` (flag 15 set as the vendor has it; flags 3, 4, 5 and 9 stay
  set, so no rail moves). Stock masks. Five runs, stopping at the first
  hang.
- **Admission:** a new firmware call (PSCI `CPU_SUSPEND` power-down,
  never issued on mainline), a new image and a boot2 write; the owner
  approves each.
- **Stop conditions:** any hang (a CPU0 that never returns stays in EL3;
  the watchdog resets it, as with the earlier hangs); a returned period
  with `cpu pdn 1 ret` nonzero; any warning, Oops or RCU stall.

| Result | Reading | Next |
| --- | --- | --- |
| Passes 15 at 221 MHz | The power-down entry removes the hazard | Unpinned on `d5m.sh`, then the two-state setup with the same entry in the idle path (a cpuidle state through PSCI), to the 50-period rule |
| `ret` nonzero, no hang | The firmware refused the request; read why before any retry | — |
| Hangs | The pause hazard is not only coherency, or the power-down path has its own fault | Read the RAM console and latches; the observer's `R13` bit 22 reading becomes the next question |

### Request D5n (proposed): two states with no resource events

[`0825`](../../patches/proposals/0825-soc-mediatek-mt6797-spm-sleep-optionally-set-SODI_NO.patch)
(module only) adds `sodi_no_event` (default off). With it on, test
periods set `SPM_SW_FLAG` bit 13 (`SODI_NO_EVENT`). The program then arms
no resource event, so the APSRC handler, and DRAM self-refresh, cannot
run. This is a new value for one approved register write, S-step
`SPM_SW_FLAG`. It is compile-checked with `W=1`, with and without
`CONFIG_CPU_IDLE`, and checkpatch `--strict` is quiet. `d4.sh` (04633082)
takes `D4_NO_EVENT=1`.

- **Candidate:** image 137 on a fresh boot, with `mt6797-spm-sleep.ko`
  from a Buildbox build of the commit recording this stage. No boot2
  write.
- **Run:** `d4.sh` 04633082 with `D4_CIRQ_LEVEL=1 D4_NO_EVENT=1`, two
  states, no cap, Wi-Fi power save on, pings in C, cable out, hands off.
  This is the configuration that reset in D5a-D5l.
- **After a reset:** the latches as after D5l.

| Outcome | Decision |
| --- | --- |
| Windows A-C pass | The DRAM self-refresh path is implicated, whatever the latch means. Next: why it hangs under two states, against the vendor's APSRC handling |
| Reset | Not the resource path. Compare the latches with D5l's |

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
