# Experiment: cpufreq for the MT6797 A53 clusters

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-07-mt6797-a53-cpufreq` |
| Status | `in progress`: attempt A1 stopped at t2 (sync DCM refusal, no writes); driver revised for A2 |
| Subsystem | MT6797 MCUMIXED PLLs and MCU FHCTL, cpufreq-dt, CPU cooling |
| Device variant | Named Gemini PDA development unit, mainline station on boot2 |
| Date(s) | 2026-11-07 |
| Investigator(s) | Julien Etienne; Claude (analysis, code) |
| Tracking issue | none |

## Question or hypothesis

Can a standard governor (schedutil) scale CPU0-3 and CPU4-7 through the
vendor's own frequency-change mechanism, at the voltage the firmware already
set, with every operating point and every transition inside the vendor table
for that voltage, and can those clusters then serve as cooling devices on the
existing `soc-thermal` passive trip?

The hypothesis is yes. It fails if a requested rate is not the measured clock,
if any CPU computes a wrong result, if the driver faults, or if cooling does
not lower and restore the clusters' limit.

## What Gemian has, and what this takes from it

Gemian's `mt_cpufreq.c` drives LL, L, B and CCI through either a kernel
sequence or the CSPM PCM firmware, with EEM-calibrated voltages and a
power-budget thermal policy (see [CPU clusters](../../docs/hardware/mt6797-cpu-clusters.md)
sections 3.5 to 4). The A53 frequency change itself is three steps, recorded in
[section 3.7](../../docs/hardware/mt6797-cpu-clusters.md#37-how-an-a53-frequency-change-is-made):
an FHCTL hop of the PLL, a cluster divider, and a post-divider change bridged
through MAINPLL. This experiment reproduces those steps exactly and nothing
else:

- no voltage change: VPROC1 stays at the firmware's 1.00 V and VSRAM_L where
  the firmware left it;
- no CCI change: it stays at the firmware's 629.5 MHz;
- no B cluster: CPU8-9 have no table and cpufreq-dt leaves them out;
- no PCM firmware, no EEM, no vendor governor or PPM policy.

### Why these operating points

VPROC1 is shared by LL, L and CCI and reads 1.00 V on the station (selector 70,
[DA921x read-only provider](../2026-08-17-mainline-da921x-readonly-provider-baseline/results/runtime-attempt-1-success-20260817.txt)).
The tables hold the vendor SB-bin points whose base (pre-EEM) voltage is
1.00 V or less, so each point runs at or above the voltage the vendor assigns
it before calibration, and well above its EEM value:

| Cluster | Points (MHz) | Vendor base voltage | EEM voltage on this unit |
| --- | --- | --- | --- |
| CPU0-3 (LL) | 221, 338, 481, 624, 715, 806, 897 | 770-1000 mV | 770-920 mV |
| CPU4-7 (L) | 325, 468, 650, 832, 962, 1092, 1209 | 770-1000 mV | 770-900 mV |

The firmware boots L at 1274 MHz, which is above the 1.00 V base table
(1209 MHz); that is the firmware's own choice and only the first transition
leaves it. The clock driver independently refuses any rate above the one it
found at probe (897 and 1274 MHz), and refuses a post-divider change on a
cluster that booted below MAINPLL's 1092 MHz, so the MAINPLL bridge never runs
a cluster faster than the firmware did. The LL cluster never needs one.

## Provenance and environment

- Kernel: Linux 7.1.3, profile `mt6797-a53-station-a72`, patches
  `0639`-`0642` (listed below) plus the configuration fragment
  [`gemini-a53-station-cpufreq.fragment`](../../configs/gemini-a53-station-cpufreq.fragment).
- A1 candidate: commit `a143ecb7`, Buildbox job
  `a143ecb74f970bfe8711bf18814be560b0e97fef-mt6797-a53-station-a72-m1`,
  package `linux-7.1.3-gemini-acd8293f0f55753c42e4b2f1f96cbbd1e5e555af61e9aa80781133183b110c9d`,
  `Image.gz` `69bbb559a860c5418e15ef1d41c9c23078051b394b9038fe3bedf9119b1e6e0a`,
  config `4bbd1bdb4b7563599d5be14ee865a1ac94ff4bbb4ff6f1adfc3bf12b7894f560`,
  `clk-mt6797-mcusys.ko` `c29d692157ba1b31626a44ebdc0d220e6f1941511171396822e0e232ea5fc1d6`,
  `cpufreq-dt.ko` `2c451b82224a8734e1cfb0908226efbcbff26a53822ca0dc20e60463101bb483`;
  boot image station-work-85 (boot2 `00bc384f…`), release
  `7.1.3-gemini-a53-station`.
- A2 candidate: the same running kernel and boot image; only
  `clk-mt6797-mcusys.ko` is rebuilt from the revised patch `0640` (see
  [attempt A2](#attempt-a2-plan)).
- Vendor source: Gemian Linux 3.18 [`59e00a91`](https://github.com/gemian/gemini-linux-kernel-3.18/tree/59e00a9144d782e148332009a835b99c43382467),
  `drivers/misc/mediatek/base/power/mt6797/mt_cpufreq.c` (`set_cur_freq`,
  `adjust_posdiv`, `adjust_clkdiv`, `set_cur_volt_extbuck`), `mt_dcm.c`
  (sync DCM), and `drivers/misc/mediatek/freqhopping/mt6797/mt_freqhopping.c`
  (`mt_fh_hal_dfs_armpll`, `mt_fh_hal_hopping_mcu`, `mt_fh_hal_init`,
  `mt6797_0x1001AXXX_lock`).

## Associated code

| Patch | Change |
| --- | --- |
| [`0639`](../../patches/proposals/0639-dt-bindings-clock-mediatek-add-the-MT6797-A53-cluste.patch) | Binding and `mediatek,mt6797-mcusys.h` |
| [`0640`](../../patches/proposals/0640-clk-mediatek-add-the-MT6797-A53-cluster-PLLs.patch) | `clk-mt6797-mcusys` (`=m`): LL and L PLLs through MCU FHCTL, cluster divider, MAINPLL-bridged post-divider, DVFSP semaphore 3, debugfs `registers` |
| [`0641`](../../patches/proposals/0641-cpufreq-dt-leave-out-CPUs-that-have-no-OPPs.patch) | cpufreq-dt skips a present CPU with no OPP table and no OPPs instead of failing the whole probe (CPU8-9) |
| [`0642`](../../patches/proposals/0642-arm64-dts-mediatek-gemini-station-scale-the-A53-clus.patch) | Station DT: clock node, two OPP tables, CPU clocks, `#cooling-cells`, cooling maps on `gpu-passive` (58 °C) |

The fragment sets `CPU_FREQ=y` with schedutil, performance, powersave and
userspace governors, statistics, `CPUFREQ_DT=m`, `CPUFREQ_DT_PLATDEV=y` and
`COMMON_CLK_MT6797_MCUSYS=m`. The default governor is `performance` for this
first image, so loading cpufreq-dt makes one predictable change (L to
1209 MHz); schedutil is selected in stage t6.

Test tools: [`tools/cpu-mhz.c`](tools/cpu-mhz.c) measures a CPU's clock from a
dependent-add chain against the architected timer, and hashes 32 MiB pinned to
one CPU; [`tools/a53-cpufreq-test.sh`](tools/a53-cpufreq-test.sh) runs each
stage and stops at the first fault.

The clock driver:

- holds DVFSP semaphore 3 (through the handoff's `mt6797_dvfsp_cspm_execute`,
  as the proven protected-clock read did) for every MCUMIXED access, with a
  2 ms bound; a timeout refuses the change and touches nothing;
- reads back every write, repeats a zero read, and on any failure stops: the
  device is marked faulted and refuses further changes;
- checks before each change that the PLL is exactly as it left it;
- refuses to probe if a cluster's mux is not on its ARMPLL, its dividers are
  not codes it knows, or FHCTL is already hopping;
- never writes MCUCFG sync DCM. It reads each cluster's divider at probe and
  refuses rates below 70 MHz per divider step, the vendor's own rule; the
  firmware's divider of 3 gives a 210 MHz floor, below every table point. It
  refuses to probe if a cluster starts below its floor, and faults if
  `SYNC_DCM_CONFIG` changes after probe.

## Safety assessment

Not read-only from t2 on. Recovery: the boot2 image is the only change, and
the standing project rules for boot2 writes, physical selection, Gemian
recovery and evidence apply. No protected area is touched.

### Writes for owner approval

From t2 on the driver writes these registers, and nothing else. Stages t0 and
t1 are read-only.

At probe (t2):

1. CSPM `0x11015000` ← `0x0b160001` before each semaphore acquire (as the
   proven protected-clock read).
2. CSPM `0x11015440` ← `1` to take and ← `1` to release semaphore 3, once per
   transaction; the `INFRA_I2C_APPM` gate is enabled for the transaction only.
3. MCU FHCTL `CLK_CON` `0x1001af04` bits 0 and 1 ← 1; `RST_CON` `0x1001af08`
   bits 0 and 1 ← 0 then ← 1; `CFG` `0x1001af34`/`0x1001af48`, `UPDNLMT`
   `0x1001af38`/`0x1001af4c` and `DDS` `0x1001af3c`/`0x1001af50` ← 0.

Per frequency change, PLL `n` = 0 (LL) or 1 (L), items 1-2 plus:

4. `ARMPLLDIV_CKDIV` `0x1001a274`, the cluster's field only (LL bits 9:5,
   L bits 14:10) ← `8` (/1), `10` (/2) or `11` (/4); other fields preserved.
5. FHCTL hop: `CFG` ← 0; `DDS` ← current PCW | bit 31; `CFG` ← `0x5`;
   `SLOPE0` `0x1001af0c` ← `0x6003c97`; `HP_EN` `0x1001af00` bit `n` ← 1;
   `DVFS` `0x1001af40`/`0x1001af54` ← target PCW | bit 31; CON1
   `0x1001a204`/`0x1001a214` ← reached PCW, bits 30:21 preserved, bit 31 set;
   `HP_EN` bit `n` ← 0; `CFG` ← 0.

   Target PCWs (VCO): LL `0x114000` (1794 MHz), `0xf8000` (1612), `0xdc000`
   (1430), `0xc0000` (1248), `0x128000` (1924), `0xd0000` (1352), `0x110000`
   (1768); L `0xba000` (1209), `0xa8000` (1092), `0x128000` (1924),
   `0x100000` (1664), `0xc8000` (1300), `0x120000` (1872).

Only for L below 1092 MHz (t5b):

6. TOPCKGEN `CLK_MISC_CFG_0` `0x10000104` bits 5:4 ← 3, then ← 0; other bits
   preserved.
7. `ARMPLLDIV_MUXSEL` `0x1001a270` bits 5:4 ← 2 (MAINPLL), then ← 1 (ARMPLL).
8. CON1 `0x1001a214` post-divider bits 26:24 ← 1 (/2) or 0 (/1), PCW
   unchanged, bit 31 set; 2 us on MAINPLL in between.

No regulator, PMIC, DA9214, VSRAM, EEM, CCI, A72 or secure call. No voltage
changes, so no voltage is raised. Without approval of items 6-8, run t5b with
`scaling_min_freq` 1092000 or skip it; the LL sweep and L 1092-1209 MHz need
items 1-5 only.

### Limits

- Voltage: none written; VPROC1 stays at the firmware's 1.00 V.
- Frequency: CPU0-3 221-897 MHz, CPU4-7 325-1209 MHz; never above the boot
  rates (897 and 1274 MHz), including mid-transition; the L bridge runs at
  MAINPLL's 1092 MHz for about 2 us (measure `mainpll_hz` in t0).
- VCO: 1092-1924 MHz, every value one the vendor uses.
- Temperature: stop above 80 °C; the existing 95 °C hot, 110 °C critical and
  117 °C hardware reset stay armed.

### Stop conditions

Stop the test at the first of these, preserve `dmesg` and the stage output,
and do not retry:

- a module refuses to load or the clock driver does not bind, or any line
  with `did not hold`, `not granted`, `not released`, `stopped at PCW`,
  `behind the driver`, `refusing`, `failed`, `error`, an Oops, a `BUG` or a
  `WARNING` from cpufreq or the clock driver;
- an enabled sync DCM divider above the lowest table point's MHz / 70 (t0);
- debugfs `registers` missing, or showing `faulted=1`;
- a measured clock more than 5 % from the requested one;
- any hash differing from the reference (power off: a wrong result may mean
  corrupted state);
- `scaling_cur_freq` not equal to the requested point;
- the SoC above 80 °C;
- the station unreachable over USB SSH for 60 s, or a hang: the owner
  long-presses power, and the next boot is the unchanged image.

## Procedure

Station: the new boot2 image from this commit, written with `flash-boot2`, the
A72 module not loaded (no secure MCUMIXED writer), stable power. Copy
`cpu-mhz` (static build of [`tools/cpu-mhz.c`](tools/cpu-mhz.c)),
`clk-mt6797-mcusys.ko`, `cpufreq-dt.ko` and the script into one directory.

| Stage | Expected observation | If not |
| --- | --- | --- |
| t0 read-only | Boot ID new; `CONFIG_CPU_FREQ` core present, no policies; `0x10220744` decoded, each enabled divider at most 3 (CPU0-3) or 4 (CPU4-7); CPU0/3 about 897 MHz, CPU4/7 about 1274 MHz; `mainpll_hz` 1092000000; hash reference | Divider above that: stop. Clock not as recorded: stop |
| t2 load clock driver | Driver bound to `1001a000.clock-controller`; `SYNC_DCM_CONFIG=0x00070707, floors 210000000 and 210000000 Hz`; `PLL0 at 897000000 Hz (PCW 0x114000 /2 /1)`, `PLL1 at 1274000000 Hz (PCW 0x0c4000 /1 /1)`; `registers` shows `hp_en=0`, `clk_con` bits 0-1 set, `sync_dcm=0x00070707`, `faulted=0` | Not bound, no debugfs node, probe refusal or fault: stop |
| t3 load cpufreq-dt | policy0 `0-3`, policy4 `4-7`, governor performance, tables as above; one change: L to 1209 MHz (CON1 PCW `0xba000`), measured; `cpu8 has no OPPs` line; two `cpufreq-cpu*` cooling devices | No policy, wrong clock or hash: stop |
| t4 LL sweep | Every point measured within 5 %, every hash equal, `ckdiv` field 8/10/11 as listed, post-divider stays /2 | Stop |
| t5a L 1209/1092 | As t4, post-divider stays /1 | Stop |
| t5b L below 1092 (items 6-8) | As t4; post-divider /2 from 962 MHz down; `muxsel` ends `…01……` for L; `clk_misc_cfg_0` bits 5:4 end 0 | Stop |
| t6 schedutil | Idle near the lowest points, load at the highest, `total_trans` rising, all 8 load hashes equal | Stop |
| t7 cooling | Both cooling devices on `gpu-passive`; at 62 °C emulated, `scaling_max_freq` falls step by step; after release both return to 897000 and 1209000 | Cooling not bound or not released: stop, record |
| t8 unload and reload | Both modules leave and return; probe reports the rates as left (L now 1209 MHz, the new ceiling); schedutil set | Stop |

One run of each stage; t4 and t5b each include a full-range jump both ways.

## Observations

### Attempt A1 (2026-11-07)

Run by the device custodian on station-work-85, boot ID
`64401d75-9757-4793-8e30-d14960004264`, release `7.1.3-gemini-a53-station`,
battery 80 % on charger. Staged files matched their recorded SHA-256.

t0 printed PASS:

| Read | Value |
| --- | --- |
| `0x10000104` (TOPCKGEN `CLK_MISC_CFG_0`) | `0xFFFF0000` |
| `0x10220744` (MCUCFG `SYNC_DCM_CONFIG`) | `0x00070707` |
| `0x1022074c` (MCUCFG `SYNC_DCM_CLUSTER_CONFIG`) | `0x00009090` |
| `mainpll_hz` | 1092000000 |
| CPU0, CPU3 / CPU4 / CPU7 measured | 897 / 1273 / 1271 MHz |
| Hash reference, CPU4 hash | `5abed55b4a4c85e5`, equal |
| SoC temperature | 33 °C |
| `/sys/devices/system/cpu/cpufreq` | present, empty |

The README's t0 row required bits 8 and 16 of `0x10220744` clear and said to
stop otherwise; both were set, but the script did not check that word.

t2: `insmod` returned 0 but the driver did not bind. The kernel log showed
`SYNC_DCM_CONFIG=0x00070707`, `sync DCM on for cluster 0` and probe failure
-95 (`-EOPNOTSUPP`). The script printed `regs: no debugfs node` and PASS. The
custodian stopped there. No register write happened: the check runs before
the semaphore, FHCTL or any MCUMIXED access. After `rmmod` (rc 0) the word
still read `0x00070707`. cpufreq-dt was never loaded. The full kernel log is
kept privately.

## Analysis

### A1

The driver's refusal worked as written; the assumption behind it did not
hold. The firmware leaves sync DCM on for CCI, CPU0-3 and CPU4-7: each byte of
`0x00070707` is enable 1, divider 3, update toggle 0. That is exactly the
state Gemian's `dcm_mcusys_sync_dcm(ON)` leaves (`MCUCFG_SYNC_DCM_ON |
DIV_SEL4`, toggled 1 then 0), so this is the vendor's generic DCM-on value,
not a frequency-specific one.

Gemian's `mt_cpufreq.c` calls `sync_dcm_set_mp0_freq` or `_mp1_freq` with the
target MHz before a frequency drop and after a rise, and `mt_dcm.c` sets the
divider to `MHz / 70` (at most 31); its register comment gives the hardware
limit as `CPU MHz / (4 × system timer MHz)`, with the 13 MHz system timer.
So the vendor invariant is: an enabled divider never exceeds the cluster's
MHz / 70. A divider of 3 meets it for every clock of 210 MHz or more, which
covers every point in both tables (lowest 221 and 325 MHz). The vendor would
set larger dividers at higher clocks; a smaller divider only divides the
idle clock less, which costs some idle power and keeps more margin above the
limit.

The revised driver therefore needs no new write. It reads the dividers at
probe, refuses any rate below 70 MHz per divider step, and faults if the
register changes behind it. Programming the divider per frequency, as the
vendor does, is a later power optimisation with its own write list.

The A1 script had two gaps: t0 did not check the sync DCM word, and t2
printed PASS when the driver was not bound. A third was found in review:
`step` piped `regs` into `grep`, so a STOP inside `regs` would only have left
the pipeline's subshell. All three are fixed; `check_log` now also stops on
`failed` or `error` lines.

### Attempt A2 plan

- Candidate: the running station-work-85 kernel, with `clk-mt6797-mcusys.ko`
  rebuilt from the revised `0640`. The profile has no module signing or
  module versions, and the rebuild changes no other output (checked against
  the A1 package), so no boot2 write or restart is needed.
- Writes: the same list as A1, items 1-5 for t2-t5a and t6-t8, items 6-8 for
  t5b only. Sync DCM is read, never written.
- Stages: t0 to t8 as in [Procedure](#procedure), with the revised script.
- Unique observation: the driver binds with floors of 210 MHz and every point
  measures within 5 % with equal hashes.
- Decision: pass, then switch the default governor to schedutil and record
  support; a stop decides from its stage which mechanism needs work.

## Conclusion

Pending A2.

## Follow-up

- Voltage scaling: VPROC1 on DA9214 BUCKA and VSRAM_L, with the vendor
  ordering (VSRAM before VPROC up, after it down, 10-30 mV apart), to reach the
  upper points (LL 1547, L 2002 MHz) and lower the rail at low points. Needs a
  writable DA921x provider and a separate owner-approved write list.
- CCI frequency following the clusters (upstream `mtk-cci-devfreq` pattern).
- `capacity-dmips-mhz` and an energy model from measured data, so the
  scheduler sees LL and L as different capacities.
- The B cluster through the secure BigiDVFS interface.
