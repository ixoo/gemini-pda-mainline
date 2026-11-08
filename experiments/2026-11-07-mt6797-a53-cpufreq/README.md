# Experiment: cpufreq for the MT6797 A53 clusters

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-07-mt6797-a53-cpufreq` |
| Status | `pass`: A3 passed t0-t8 on station-work-86 (A1 and A2 stopped before any clock change) |
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
  `0639`-`0643` (listed below) plus the configuration fragment
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
  `clk-mt6797-mcusys.ko` is rebuilt from the revised patch `0640`
  (`8163e54101a9aec185dbb14b0446db5835766befb99b65d61127130a96fe5f1d`, Buildbox
  job `708f75adb6a91b715c31477101ae0d2cd61bd676-mt6797-a53-station-a72-m1`).
- A3 candidate: commit `8996f539`, Buildbox job
  `8996f539c980e2700b7b732071541d0b9dd6aca6-mt6797-a53-station-a72-m1`,
  package `linux-7.1.3-gemini-395047bdaecb27b7fc461a3a2fa601c2836f3212d037ad8dfbfacee4998d8bc6`,
  `Image.gz` `b025af20eb8c8143ce158d256f8643156464ca075c34b614005f0b4f505c1d1a`;
  config, station DTB and every module identical to the A2 package
  (`clk-mt6797-mcusys.ko` `8163e541…`, `cpufreq-dt.ko` `2c451b82…`); boot
  image station-work-86 (boot2 `a101d944…`).
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
| [`0643`](../../patches/proposals/0643-OPP-of-leave-CPUs-without-an-OPP-table-out-of-a-shar.patch) | OPP core (built in): a CPU without an OPP table no longer fails the opp-shared scan, which made cpufreq-dt put every CPU in one policy |

The fragment sets `CPU_FREQ=y` with schedutil, performance, powersave and
userspace governors, statistics, `CPUFREQ_DT=m`, `CPUFREQ_DT_PLATDEV=y` and
`COMMON_CLK_MT6797_MCUSYS=m`. The A1-A3 images default to `performance`, so
loading cpufreq-dt makes one predictable change (L to 1209 MHz); schedutil is
selected in stage t6. After A3 the fragment defaults to schedutil; no image
with that default has booted yet.

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

- CPUs online other than `0-7` (checked at the start of every stage);
- a policy whose `related_cpus` is not exactly CPU0-3 or CPU4-7 (t3);
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
Turn console blanking off first: blanking makes `backlight-policy` take CPU1-7
offline. On the station, `printf '\033[9;0]\033[13]' > /dev/tty1` and SIGUSR1
to `backlight-policy` brought them back (A2).

| Stage | Expected observation | If not |
| --- | --- | --- |
| t0 read-only | Boot ID new; `CONFIG_CPU_FREQ` core present, no policies; `0x10220744` decoded, each enabled divider at most 3 (CPU0-3) or 4 (CPU4-7); CPU0/3 about 897 MHz, CPU4/7 about 1274 MHz; `mainpll_hz` 1092000000; hash reference | Divider above that: stop. Clock not as recorded: stop |
| t2 load clock driver | Driver bound to `1001a000.clock-controller`; `SYNC_DCM_CONFIG=0x00070707, floors 210000000 and 210000000 Hz`; `PLL0 at 897000000 Hz (PCW 0x114000 /2 /1)`, `PLL1 at 1274000000 Hz (PCW 0x0c4000 /1 /1)`; `registers` shows `hp_en=0`, `clk_con` bits 0-1 set, `sync_dcm=0x00070707`, `faulted=0` | Not bound, no debugfs node, probe refusal or fault: stop |
| t3 load cpufreq-dt | policy0 `related_cpus` exactly `0 1 2 3`, policy4 `4 5 6 7`, governor performance, tables as above; one change: L to 1209 MHz (CON1 PCW `0xba000`), measured; `cpu8 has no OPPs` line; two `cpufreq-cpu*` cooling devices | No policy, wrong clock or hash: stop |
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

### Attempt A2 (2026-11-07)

Same boot as A1 (`64401d75-9757-4793-8e30-d14960004264`). The custodian saved
the A1 log privately and cleared the kernel log. Staged hashes matched the
request: script `3c7f6eb4…`, `clk-mt6797-mcusys.ko` `8163e541…`,
`cpufreq-dt.ko` `2c451b82…`, `cpu-mhz` `4168cfe5…` (A1 had used the
custodian's own build of the same source, `89c0f11e…`, with the same hash
reference).

The first t0 stopped in `sched_setaffinity` with an empty CPU4 hash: only
CPU0 was online. The console had blanked at 237 s and `backlight-policy` had
taken CPU1-7 offline (`psci: CPU1..7 killed`). The custodian turned blanking
off and signalled `backlight-policy`; CPU0-7 came back and t0 was run again.

| Stage | Result |
| --- | --- |
| t0 | PASS. Same three words as A1; `sync_dcm` both clusters enabled, divider 3, floor 210 MHz; `mainpll_hz` 1092000000; CPU0/3/4/7 at 897/894/1273/1273 MHz; hash reference `5abed55b4a4c85e5`, CPU4 equal; 27.5 °C |
| t2 | PASS. `SYNC_DCM_CONFIG=0x00070707, floors 210000000 and 210000000 Hz`; PLL0 897000000 Hz (PCW `0x114000` /2 /1), PLL1 1274000000 Hz (`0x0c4000` /1 /1); `muxsel=0x54`, `ckdiv=0`, `hp_en=0`, `clk_con=0x3`, `clk_misc_cfg_0=0xffff0000`, con1 `0xc1114000` and `0x400c4000`, `fh_cfg=0`, `min_rate=210000000`, `changes=0`, `faulted=0` |
| t3 | STOP `no policy4`. One policy: policy0 `related_cpus` 0-9 (affected 0-7), performance, 221000-897000 kHz, latency 100000 ns, cur 897000; `cpu4` and `cpu8` link to policy0. Log: `/cpus/cpu@200: Couldn't find opp node`, `debugfs: 'cpu1' already exists in 'opp'` (and cpu2, cpu3) |

After the stop every clock still read its boot value (CPU0/3/4/7 at
896/897/1272/1273 MHz, CPU4 hash equal, both PLLs at boot rate, `changes=0`,
`faulted=0`). cpufreq-dt was unloaded (rc 0); the clock driver stayed bound.
No clock changed in A2: with the performance governor and policy0's table
topping out at the 897 MHz boot rate, the one change requested was a no-op.
The full kernel log is kept privately.

### Attempt A3 (2026-11-07)

Station-work-86 (boot2 `a101d944…`, package `395047bd…` from `8996f539`),
fresh boot `f38301d7-26bf-4988-9fb7-d8b7d1d1fd7f`, `7.1.3-gemini-a53-station`,
battery 80 % not charging, console blanking off, CPU0-7 online. Staged hashes
matched: script `78aba034…`, `clk-mt6797-mcusys.ko` `8163e541…`,
`cpufreq-dt.ko` `2c451b82…`, `cpu-mhz` `4168cfe5…`. The custodian reports
that the owner approved writes 6-8 in chat before t5b. Every stage printed
PASS, and the kernel log has no fault string.

| Stage | Result |
| --- | --- |
| t0 | Same words as A2 (`0x10220744` `0x00070707`, divider 3, floor 210 MHz on both clusters), MAINPLL 1092 MHz; CPU0/3/4/7 897/894/1271/1273 MHz; hash reference `5abed55b4a4c85e5`; 28.9 °C |
| t2 | `SYNC_DCM_CONFIG=0x00070707, floors 210000000 and 210000000 Hz`; PLL0 897 MHz (`0x114000` /2 /1), PLL1 1274 MHz (`0x0c4000` /1 /1); `faulted=0` |
| t3 | policy0 CPU0-3, 221000-897000 kHz, cur 897000; policy4 CPU4-7, 325000-1209000 kHz, cur 1209000. Log: `cpu8 has no OPPs, leaving it out` (and cpu9), `CPU4: Running at unlisted initial frequency: 1274000 kHz, changing to: 1209000 kHz`; no `Couldn't find opp node` or `already exists` line. PLL1 con1 `0xc00ba000`, `changes=1`. CPU0 895, CPU4 1206 MHz measured, hashes equal. Cooling devices `cpufreq-cpu0` and `cpufreq-cpu4`, `max_state` 6 each |
| t4 | All 14 CPU0-3 steps within 5 % (221 MHz measured 218-219), hashes equal; `changes=14`, `max_poll` 3. `ckdiv` went `0x0` → `0x140` (/2) at 481 MHz, `0x160` (/4) at 221, `0x100` (/1) from 624 up; 27.7-28.4 °C |
| t5a | 1092 and 1209 MHz twice each, measured 1088-1091 and 1205-1208 MHz |
| t5b | 1092 → 962 → 832 → 650 → 468 → 325 and back, then 325 → 1209 → 325 → 1209; every point within 1 % (325 measured 322), hashes equal; `changes=19`; 27.9-30.2 °C |
| t6 | schedutil. Idle: policy0 221000, policy4 832000; load: 897000 and 1209000; after load 624000 and 832000. Transitions policy0 14 → 293, policy4 22 → 423. `time_in_state` policy0: 221 MHz 2230, 897 MHz 6408, others 113-153; policy4: 325 MHz 2187, 1209 MHz 6397, 1092 MHz 236, others 106-138 (10 ms units). 60-69 load hashes per CPU on all 8, all equal. PLL1 `changes=490`, `faulted=0`, 29.6 °C |
| t7 | Both cooling devices on trip 0. Emulated 62 °C capped policy0 at 806000 and policy4 at 1092000 (cur followed) for 10 s; within 1 s of release the limits returned to 897000 and 1209000 |
| t8 | Both modules unloaded and reloaded; schedutil; policy0 624000, policy4 962000; PLL1 `changes=8`, `faulted=0`. PLL1 reported `1209000000` as its ceiling, because `rmmod` left it at 1209 MHz |

The full kernel log and every stage's output are kept privately.

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

### A2

The clock driver bound and touched nothing beyond its probe: the sync DCM
floor and the PLL readings are exactly as the A1 analysis predicted.

The t3 stop is an OPP core behaviour. `dev_pm_opp_of_get_sharing_cpus()`
walks every possible CPU to find the ones that share an opp-shared table and
returns `-ENOENT` at the first CPU with no OPP table at all, here the A72 at
`cpu@200` (`Couldn't find opp node`). cpufreq-dt reads `-ENOENT` as "no
operating-points-v2" and falls back to marking every CPU as sharing
(`cpumask_setall`), so CPU0-9 shared policy0 and CPU0's table. The
`debugfs: 'cpu1' already exists` lines come from the same fallback adding
tables twice. Patch `0641` did not cover this: it only stops cpufreq-dt
failing when a CPU without OPPs is the one being initialised.

Patch [`0643`](../../patches/proposals/0643-OPP-of-leave-CPUs-without-an-OPP-table-out-of-a-shar.patch)
makes the scan skip a CPU with no OPP table, which cannot share the table
being asked about. `-ENOENT` still means the CPU being asked about has none.
The OPP core is built in (`CONFIG_PM_OPP=y`), so A3 needs a new image.
Putting a dummy OPP table on the A72s in the DT would also need a new image,
and would give cpufreq-dt a policy with no clock.

The stage scripts gained two checks from A2: CPU0-7 online at the start of
every stage (the first A2 t0 failed in `sched_setaffinity` because blanking
had taken CPU1-7 offline), and t3 now checks each policy's `related_cpus`.

### Attempt A3 plan

- Candidate: a new boot2 image from the commit that adds `0643`, written
  with `flash-boot2` and selected by the owner; same profile, modules from the
  same package.
- Writes: boot2 (standing approval), then the same register list as A1,
  items 1-5, and items 6-8 for t5b only. Sync DCM is read, never written.
- Stages: console blanking off, then t0 to t8.
- Unique observation: two policies, CPU0-3 and CPU4-7, then every point
  measured within 5 % with equal hashes.
- Decision: pass, then switch the default governor to schedutil and record
  support; a stop decides from its stage which mechanism needs work.

### A3

The hypothesis holds on this unit. Under schedutil, CPU0-3 scale over
221-897 MHz and CPU4-7 over 325-1209 MHz through the vendor's FHCTL hop,
cluster divider and MAINPLL-bridged post-divider, at the firmware's 1.00 V.
Every requested point measured within 5 % (most within 1 %), every hash
matched across about 500 L-cluster transitions and 8 loaded CPUs, and the
driver never faulted. Both clusters cooled on the 58 °C passive trip and
recovered when the emulated temperature was released.

Two behaviours are expected and harmless:

- After the sweep the LL divider field reads `0x100` (code 8, /1) at 897 MHz
  where the firmware left `0x0`. Both codes are /1; the driver writes the
  vendor's code 8.
- The ceiling is the rate found at probe, so a reload after `rmmod` at
  1209 MHz caps L at 1209 MHz until the next boot. The table tops out at
  1209 MHz, so nothing is lost; 1274 MHz was only the firmware's boot rate.

Limits of the result: one unit, one boot, 27-31 °C, cooling shown only by
emulated temperature, at most a few minutes of load, and the drivers loaded
by hand.

## Conclusion

A53 cpufreq works on the station: schedutil drives both A53 clusters over
the vendor's 1.00 V operating points, with CPU cooling on the passive trip.
The default governor is now schedutil in the fragment; loading the modules
at boot and longer runs are the next steps.

## Follow-up

- Load `clk-mt6797-mcusys` and `cpufreq-dt` at boot on the station, after a
  longer soak under real heat, and confirm the schedutil default on that
  image.
- Voltage scaling: VPROC1 on DA9214 BUCKA and VSRAM_L, with the vendor
  ordering (VSRAM before VPROC up, after it down, 10-30 mV apart), to reach the
  upper points (LL 1547, L 2002 MHz) and lower the rail at low points. Needs a
  writable DA921x provider and a separate owner-approved write list.
- CCI frequency following the clusters (upstream `mtk-cci-devfreq` pattern).
- `capacity-dmips-mhz` and an energy model from measured data, so the
  scheduler sees LL and L as different capacities.
- The B cluster through the secure BigiDVFS interface.
