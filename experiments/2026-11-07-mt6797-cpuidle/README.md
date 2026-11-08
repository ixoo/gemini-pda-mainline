# Experiment: idle states below WFI for the MT6797 clusters

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-07-mt6797-cpuidle` |
| Status | `planned`: research done, no device run; C0 attempt 1 stopped at c3 on a procedure fault (a respawned `backlight-policy` took CPU1-3); the L cluster came back with the clock driver intact; attempt 2 proposed |
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
writes too. No MT6797 per-core SPM program exists in the evidence, and the PCM
instruction set is not documented, so the project cannot write its own.

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
and brings back the ones it took. C0 must hold the CPU set itself, so the
policy is stopped for the run and restarted afterwards.

## Plan

| Stage | What | Writes | Image | Status |
| --- | --- | --- | --- | --- |
| C0 | Idle current with A53 cpufreq at its idle points: all A53s online in WFI, then the L cluster down, then CPU1-7 down; SPM status reads in each state; the L clock checked after its cluster returns | None new (see below) | Running boot2 image | Attempt 1 run 2026-11-07, stopped at c3; **attempt 2 proposed** |
| C1 | Depends on C0: a cluster-first idle hotplug policy (screen on), or nothing | Hotplug only | none, userspace | Not proposed |
| C2 | Per-core power-down in idle, through an SPM program or a firmware port | New SPM or `tee1` writes | New | Owner decision; blocked on a program that does not exist in the evidence |

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
  are 0. `PCM_FSM_STA` was not compared against a known idle value, so this is
  not confirmed.
- **`CPU_IDLE_STA` sees WFI.** Bits 10-17 read `0xFB`: seven A53s in
  `STANDBYWFI`, one not, which fits one CPU running the read.

## Conclusion

Pending C0. From the research alone: per-core and per-cluster idle power-down
are not available on the installed firmware without an MT6797 SPM program,
which the vendor evidence does not contain. Hotplug is the working way to
power idle cores down on all three clusters.

## Follow-up

- C0 attempt 2, through the custodian, after owner approval.
- If C1 follows, it reuses P2f's mechanism and needs no new write.
- A GPT broadcast timer node and the cpuidle-psci skip for CPU8-9 are needed
  only once a real state exists; neither is worth a patch before then.
