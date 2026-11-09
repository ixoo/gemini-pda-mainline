# Experiment: combined device test plan for all cores, frequency scaling and power management

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-08-cpu-power-test-plan` |
| Status | `running`: Phase 0 ran on 2026-11-08 (V0 passed, C0 attempt 2 completed); Phase 1 waits for image D1 and the owner's approval |
| Subsystem | A53 DVFS and CCI, A72, cpuidle hotplug policy, s2idle sleep hooks, SPM mem suspend |
| Device variant | Named Gemini PDA development unit, mainline station on boot2 |
| Date(s) | 2026-11-08 |
| Investigator(s) | Julien Etienne; Claude (device custodian) |
| Tracking issue | none; [roadmap](../../docs/ROADMAP.md) section 2, Power |

## Question or hypothesis

The owner asked for every feature that all ten cores, frequency scaling and power
management need, and then a test plan. Four sessions wrote the code. All of it is
compile-checked and none of it has run. This record orders their device tests into
as few images and boots as possible, puts the riskiest step last on its own boot,
and names every approval the owner has to give. Each test's literal write list,
expected output and stop conditions stay in its own record; this plan links to them
rather than copying them.

## The work under test

| Area | Commits | Record | State |
| --- | --- | --- | --- |
| A53 voltage scaling, CCI, boot gate | `93dc36c7`, `8a848ed3`, `a847fe2f` (patches 0656-0666) | [A53 DVFS](../2026-11-08-mt6797-a53-dvfs/README.md) | Built on Buildbox, profile `mt6797-a53-station-dvfs` |
| Sleep hooks: touch, LEDs, CONSYS, camera, audio | `c3bfc627` (0651-0655) | [power management, P6](../2026-11-06-gemini-power-management/README.md#p6-2026-11-08-sleep-hooks-for-the-remaining-station-drivers) | Compile-checked |
| Dark-screen policy takes the A72s too | `70c75c6e` (`backlight-policy.c`) | [cpuidle, H1](../2026-11-07-mt6797-cpuidle/README.md#stage-h1-the-a72s-in-the-dark-screen-policy) | Compile-checked |
| SPM mem suspend with the vendor program (Route A, S1) | `0d299452`, `8958275a` (0667) | [cpuidle, S1](../2026-11-07-mt6797-cpuidle/README.md#s1-implementation-2026-11-08) | Compile-checked |
| A72 load at boot behind a marker | `764471d3` | [all cores](../2026-11-01-mt6797-all-cores/README.md#follow-up-full-support-before-loading-by-default) | In init, off |
| A72 frequency, voltage, cooling, capacity | not yet written | [all cores](../2026-11-01-mt6797-all-cores/README.md#follow-up-full-support-before-loading-by-default) | Waits on the B-clock move into `clk-mt6797-mcusys` |

## Plan

### Phase 0: the current image (station-work-91), no boot2 write

| Test | What | Writes | Owner action |
| --- | --- | --- | --- |
| V0 | DVFS read-only baseline: INFRACFG_AO VSRAM words and DA9214 `0xd7`, `0x5d`, `0xd9` | none | none |
| C0 attempt 2 | cpuidle measurement, A72 module not loaded, about 6 min on battery ([attempt 2 changes](../2026-11-07-mt6797-cpuidle/README.md#attempt-2-changes)) | the approved A3 cpufreq list only | unplug, replug |
| V0g (optional) | Gemian read-only: the vendor's VSRAM_L and VPROC1 codes at low A53 points; settles the 1.0 V floor question in the DVFS record | none (read-only Gemian inspection) | boot Gemian, then boot2 |

V0 and C0 run from the station RAM root. V0g costs two owner boots and is only
needed if the owner wants the low points below 1.0 V decided by measurement rather
than kept at the safe 1.0 VSRAM floor the code uses now.

### Phase 1: image D1, one boot2 write

D1 is built on Buildbox from a clean clone of main at the newest pushed commit that
holds all of the work above (at least `2ddfe0fd`), profile
`mt6797-a53-station-dvfs`. That profile is the station profile plus the DVFS
fragment, so it carries the sleep hooks, 0667, the A72 module and the new
`backlight-policy`. Two gaps in the station composer must be closed before D1:

- `compose-station.py` always takes `mt6797-gemini-pda-station-a72.dtb`; D1
  needs `mt6797-gemini-pda-station-dvfs.dtb`.
- The composer does not pack `da9213-legacy-regulator`, `mt6797-vsram-regulator`,
  `clk-mt6797-mcusys`, `cpufreq-dt`, `mtk-cci-devfreq` or `mt6797-spm-sleep`. For
  V2-V10 and S1 they are copied to the RAM root by hand from the same package; the
  init's at-boot gate (V11) needs them packed.

On the card root the image's modules are loaded only by name: the Arch root
removes `modules.alias`, so udev cannot load them around the gate.

Every test in this phase runs from the RAM root (a key at the boot prompt), so a
forced power-off cannot damage a card. Order, lowest risk first:

| Boot | Tests | Record | New writes needing approval | Owner action |
| --- | --- | --- | --- | --- |
| 1 | V1 identity; H1, five blank/wake cycles with the A72 module loaded | [DVFS](../2026-11-08-mt6797-a53-dvfs/README.md#device-tests-in-order), [H1](../2026-11-07-mt6797-cpuidle/README.md#stage-h1-the-a72s-in-the-dark-screen-policy) | none (hotplug and the 0645 re-preparation, both approved) | select boot2 |
| 1 | Suspend C, H, K, L | [P6](../2026-11-06-gemini-power-management/README.md#p6-2026-11-08-sleep-hooks-for-the-remaining-station-drivers) | AW9120 at suspend and resume (0652) | press a key at about 20 s (K); close the lid at about 10 s and open it at about 40 s (L) |
| 1 | Suspend S, then S2 if S is under 60 mA: s2idle current over 600 s | P6 | none | unplug, replug after about 25 min |
| 2 | DVFS V2-V8, then V9 heat soak | [DVFS writes](../2026-11-08-mt6797-a53-dvfs/README.md#writes-for-owner-approval) | DA9214 `0xd7`; INFRACFG_AO `0x10001f9c`/`0x10001fa0`; MCUMIXED LL, L and CCI PLL items 1-8; VPROC1 and VSRAM_L to 1.2 V when the CCI driver probes; `emul_temp` | select boot2 |
| 2 | DVFS V10 energy model, on battery | DVFS | as V4-V9 | unplug, replug |
| 3 | SPM S1: one 30 s mem suspend with the cable in, then the measurement on battery: 300 s of today's idle as the reference, then three 300 s mem suspends | [S1 write list](../2026-11-07-mt6797-cpuidle/README.md#s1-the-write-list-for-owner-approval), [S1 steps](../2026-11-07-mt6797-cpuidle/README.md#s1-implementation-2026-11-08) | the S1 list (P1-P3, W1, S1-S24, C1-C3, X1-X5); no PSCI or SiP call | select boot2; unplug, replug after about 20 min; a long-press forced power-off if it hangs |

Boot 2 gets its own boot because a DVFS stop (a hash mismatch) ends in a power-off.
S1 gets its own boot and runs last because a program that never returns leaves CPU0
in wfi with every interrupt masked: dead to USB and keys, and recoverable only by
the owner's forced power-off. S1 runs with Wi-Fi/BT, the DVFS modules and the A72
module all unloaded: the vendor program resets I2C6 on entry, and I2C6 carries the
DA921x rails the DVFS and A72 code use.

**What decides the vendor outcome.** S1's suspended current against the reference
window, which should reproduce about 96 mA, and against S's s2idle figure. Far below
96 mA: the vendor program delivers, and S2/S3 (CPU0 powered down, deep idle) are
worth building. Near 96 mA: the flags or the PMIC sleep slots did not take, and S2
decides. The [PCM decode](../../docs/hardware/mt6797-spm-programs.md) runs in
parallel and decides whether a project-written program is feasible.

### Phase 2: the boot gates, no new image

| Test | Precondition | What | Owner action |
| --- | --- | --- | --- |
| V11 | V9 passed | Create `/mnt/data/cpufreq-at-boot`; power off | select boot2 |
| A72 at boot | Phase 3 passed | Create `/mnt/data/a72-at-boot` | select boot2 |

The A72 marker stays off until the A72s have frequency control and cooling: today
their only heat protection is the 117 °C hardware reset.

### Phase 3: A72 frequency, voltage and cooling (image D2)

Not written yet. The all-cores session found that the firmware's B-PLL service
gates the A72 clock on every call, so the A72s must be moved to another clock
source first, under the hardware lock at `0x11015448`. That clock-source register is
the A53 clock driver's, so the B clock moves into `clk-mt6797-mcusys`, which changes
that module and the V3 write list. Its tests (frequency at 1.0 V, then BUCKB
voltage, then cooling, capacity, a long soak with all ten cores, s2idle with the A72s
online) are added here when that code exists. D2 is a second boot2 write.

## Owner decisions

1. Approve, per phase, the write lists linked above. No message from another session
   counts as that approval.
2. V0g: boot Gemian for the read-only vendor measurement, or keep the 1.0 V floor.
3. Charger attached during a suspend (P6): (a) turn the bq25890 watchdog off for the
   suspend, a new charger write class; or (b) let it wake the device every 40 s.
4. Wi-Fi across a suspend: unload and reload the radio modules around every suspend.
   Until this is agreed, CONSYS refuses a suspend while Wi-Fi is on, so the card
   cannot suspend on lid close with Wi-Fi up.
5. After S1: whether to build S2 and S3 on the vendor programs, or wait for the PCM
   decode's feasibility answer.

## Limits

- One unit. Every pass is one boot unless a test says otherwise.
- Battery measurements use the fuel gauge, at about 90 µAh per count; short windows
  are coarse.
- The card root (Arch) is not exercised here. Suspend on lid close there needs
  logind and sleep settings from the arch-root session after decision 4.

## Observations

**Phase 0 (2026-11-08), boot `52f4c5fd…` on station-work-91, owner-approved.**

- V0 passed: VPROC1 1.00 V, VSRAM code 11 in both control words
  ([DVFS observations](../2026-11-08-mt6797-a53-dvfs/README.md#observations)).
- C0 attempt 2 ran every stage with no stop: the A53 cluster clocks survive
  hotplug, and CPU1-7 in WFI cost 34.5 mA over offline at the idle points, 74 %
  of it in the L cluster. The blanked floor read 324 mA, about three times the
  earlier 111 mA, with no cause found, so those figures are provisional
  ([attempt 2](../2026-11-07-mt6797-cpuidle/README.md#attempt-2-2026-11-08)).
- V0g was not run.

**Image D1 installed (2026-11-08).** `station-work-92`, composed from Buildbox job
`980309cf…-mt6797-a53-station-dvfs-m1` (package inventory `642ab49b…`) with the
`station-dvfs` tree: Image.gz `08247521…`, DTB `55e030ae…`, initramfs `8ff876b4…`,
boot2 `09ae90fd…` (12.75 MB). `flash-boot2` verified the write from the
station-work-91 RAM root (predecessor `6c0fd742…`). It carries 0651-0670,
`CONFIG_CMA_SIZE_MBYTES=512`, the gated CPU modules and the rebuilt
`backlight-policy` (`f66962ab…`). The card was rewritten with Arch card-23 (gemini-base
24) for the same boot, readback equal.

- First boot of D1 with card-23 (`d4a5ac06…`): the desktop came up and Wi-Fi joined
  (Wi-Fi fixes 0669 and 0670); one `systemctl restart iwd` triggered one WLAN restart
  and reconnected in 4 s with Bluetooth and FM still present. Details belong to the
  Wi-Fi record.
- Phase 1 boot 1 (boot `17a3859e…`): H1 passed five of five cycles (CPU1-9 down on a
  console blank, all ten back within a second of the key, CPU8 first after "cluster prepared
  again", correct hashes on both A72s). The suspend tests passed C, H, K and S, with S at
  73.3 mA suspended; L failed (a lid close woke the system through the keyboard expander),
  and audio breaks across a suspend
  ([P6 result](../2026-11-06-gemini-power-management/README.md#p6-result-2026-11-08-c-h-k-and-s-pass-audio-breaks-across-a-suspend-a-lid-close-wakes-through-the-keyboard)).
- Phase 1 boot 2 (boot `e79a664d…`): V1-V3 passed; V4 stopped on a kernel BUG when
  `cpufreq-dt` could not set the CCI required OPP
  ([DVFS observations](../2026-11-08-mt6797-a53-dvfs/README.md#observations)); V5-V10 wait
  for a fix. On the same boot the AFE reads confirmed the audio reset across a suspend and L2
  passed, with keypad IRQ warnings after it
  ([power-management record](../2026-11-06-gemini-power-management/README.md)).
- Phase 1 boot 3 (D1, boot `f7004450…`): S1 stopped in its first 30 s mem suspend with a
  watchdog reset ([boot 3](#boot-3-result-2026-11-08)). In the retry (boot `93284025…`), a
  10 s suspend returned on the PCM timer. The next suspend was refused by `mtu3`
  ([retry](#boot-3-retry-2026-11-08)).
- Boot 3 second retry (boot `263ae72a…`): all five mem suspends returned. Suspended current
  was about 42 mA, against 271 mA idle and 73 mA for s2idle
  ([S1 measured](#boot-3-second-retry-s1-measured-2026-11-08)).
- D2 (station-work-93, boot2 `ed088a5a…`, from `4a1c6f22`; boot `bb910b05…`): V1-V6
  passed. V4 now loads cleanly: policy4 moved 1274 → 1352 MHz, VPROC1 1040 mV, VSRAM_L
  1100 mV. V7 stopped: the CCI followed the clusters by interpolation to 626.08 MHz, which
  is not a table point, while VPROC1 held 1020 mV, the 611 MHz point's voltage. The station
  was powered off at that stop. Details are in the
  [DVFS record](../2026-11-08-mt6797-a53-dvfs/README.md); the private logs are in
  `artifacts/station-work-93/phase1/`.
- D3 (station-work-94, boot2 `1f201b4e…`, from `5ed802b4`): item 1 of the cpuidle plan, S1
  as the station's suspend. T1, T2, T3 and T4 passed, with one USB defect
  ([D3 item 1](#d3-item-1-s1-as-the-stations-suspend-2026-11-08)).

### Boot 3 result (2026-11-08)

**Setup, observed.** The module `mt6797-spm-sleep` (`a614fa91…`, from D1's package) loaded
with the expected lines: program 1,822 words at `0xbfdd0000`, SPM pointer `ffdd0000`, flags
`000d02b1`, HWCID `5140`. The vendor program's hash matched. The radios were unloaded,
with CONNSYS off (`0x1000632c` = `0x112`), and `backlight-policy` was stopped. CPU1-7 were
offline, the screen was blanked and nothing was tainted. The charger driver refuses a
suspend with the cable in (0630), so the functional cycle ran on battery. The run was a
detached script that synced its log before each suspend.

**Observed.** The script logged its last line just before the first `mem` suspend
(timer 30 s). Then the device rebooted by itself into Gemian. Gemian's command line
reported `boot_reason=4`, `androidboot.bootreason=wdt_by_pass_pwk`, and its RAM console
reported `hw_status: 1, fiq step 0`. Nothing else survived. No `wake:` line was written,
so it is not known whether the program returned on its timer.

**Inference, not proven.** The reset was the TOPRGU watchdog, not the program. The station
kernel keeps the boot-armed watchdog running (`mtk-wdt`: timeout 31 s;
`CONFIG_WATCHDOG_HANDLE_BOOT_ENABLED=y`). Mainline `mtk_wdt_suspend()` stops it only when
`watchdog_active()`, that is, when userspace has opened `/dev/watchdog`. A watchdog the
kernel keeps alive only through `WDOG_HW_RUNNING` keeps counting. In s2idle the core's
kick timer still runs, which is why the 600 s s2idle tests survived. In a mem suspend no
CPU runs, and a 30 s PCM timer plus entry and exit passes 31 s. The vendor kernel stops
its watchdog around suspend.

**Next.** Two ways to stop the watchdog for the suspend:
- Hold `/dev/watchdog` open with a feeder for the run. The driver then stops the watchdog
  at suspend and restarts it at resume, with no new code or register writes.
- Fix `mtk_wdt` to stop a watchdog that is only `WDOG_HW_RUNNING` at suspend.

Either way, the first retry also tells whether the program returns on its timer.

### Boot 3 retry (2026-11-08)

The owner chose the feeder ("Hold it open, retry"). It ran on D1 again, boot `93284025…`,
with the same module and program. A shell feeder held `/dev/watchdog` open, and
`watchdog0` read `active`, timeout 31 s. On the cable-in cycle, the first suspend was 10 s,
as the cpuidle session advised.

**Observed:**
- **F1, 10 s mem suspend: the vendor program returned on its timer.** The `wake:` line was
  `returned=1 loops=1 r12=00000001`. All three clock-gate words and `clk_cfg_0`
  (`01010101`) matched before and after, and `timer_out` was `00050088`. Uptime advanced
  10.3 s across the suspend. CPU0 stayed alone online, nothing was tainted, and there was
  no warning.
- **F2, 30 s: refused before sleeping.** On the F1 resume, `mtk-tphy` logged
  `u2 phy0: forcing valid B-device session` and the gadget pulled D+ up, with no cable
  attached. At F2 entry, `mtu3` failed with `ip sleep failed!!!` and `platform_pm_suspend`
  returned -16, so the suspend aborted. The script stopped there. The earlier s2idle runs
  suspended back to back on battery without this, so it follows a mem resume only.
- **About 30 s after the script ended, the TOPRGU watchdog reset the device into Gemian:**
  `boot_reason=4`, `hw_status: 1`. The feeder closed `/dev/watchdog` without the magic
  `'V'` (a custodian choice, to keep the watchdog armed), so the kernel logged
  `watchdog did not stop!`. With the timeout equal to `max_hw_heartbeat` (31 s), the core
  does not ping an active watchdog that userspace has closed, so it expired. This is a
  procedure error, not a program or kernel fault.

**Result.** The program's "CPU stays powered" path enters and returns on its own PCM timer
on mainline. The current measurement has not run. Before the next attempt:
- The feeder closes with `'V'`.
- The `mtu3` B-session forced on a mem resume must be fixed, or the gadget unbound for the
  run.

### Boot 3 second retry: S1 measured (2026-11-08)

The owner chose the retry with USB unbound. It ran on D1, boot `263ae72a…`, with the same
module and program. The feeder held `/dev/watchdog` and closed it with `'V'`. The `mtu3`
gadget was unbound after the unplug and bound again at the end. Otherwise the setup matched
the first retry: CONNSYS `0x112`, `backlight-policy` stopped, CPU1-7 offline, screen blank.

**Observed:** all five mem suspends returned on the PCM timer: F1 10 s, F2 30 s, M1-M3
300 s each.
- Every `wake:` line read `returned=1 loops=1 r12=00000001` (bit 0, the PCM timer).
- The three clock-gate words and `clk_cfg_0` (`01010101`) matched before and after.
- `timer_out` read `00050088`, `000f0088`, then `00960088`/`00960088`/`00960089`, which is
  10, 30 and 300 s in the upper half-word.
- The run ended `stop=0` with no new fault line and taint 0. The kernel log holds five
  `PM: suspend exit` lines.

Charge from the fuel gauge's `charge_counter`, which moves in steps of about 103 µAh:

| Window | Δcharge (µAh) | Elapsed (s) | Average current |
| --- | --- | --- | --- |
| R: idle, CPU0 alone, screen blank, radios off | 22,658 | 301.05 | 271 mA |
| M1: mem suspend, PCM timer 300 s | 3,621 | 300.75 | 43 mA |
| M2 | 3,518 | 300.74 | 42 mA |
| M3 | 3,518 | 300.75 | 42 mA |

Each M window includes about 0.7 s of entry and resume. The count resolution is about
±3 % per window.

**Analysis.**
- The vendor program's "CPU stays powered" path (flag bit 0) cuts the current to about
  42 mA, against 73 mA for s2idle (P6 S) and 271 mA idle in this run.
- The idle reference came out at 271 mA, not the 96 mA C0 predicted. The C0 floor question
  is still open, and this run does not settle it.
- So the program delivers a real saving. That argues for S2 (CPU0 powered down) and the
  static regulator sleep modes as the next steps, per the S1 decision table.

**Procedure faults, for the next run.** Unbinding and rebinding `mtu3` brought the
controller back with `usb0` down and the SSH server gone. The owner restored them from the
console: `ip link set usb0 up`, the address, and an `init` respawn of `usb-ssh`. The `mtu3`
fix 0676 (in D2) removes the need to unbind.

**Next.** D2 (station-work-93, boot2 `ed088a5a…`, from `4a1c6f22`) is written and verified
(predecessor D1 `09ae90fd…`). The owner decides whether to build S2/S3 (owner decision 5).

### D3 item 1: S1 as the station's suspend (2026-11-08)

The candidate was D3: D2's inputs plus 0677 (CCI rounding), 0678 (`mtk_wdt` stops a
`HW_RUNNING` watchdog across suspend) and 0679 (static PMIC sleep modes, `pmic_modes`,
default off). It was written over D2 (`ed088a5a…`) and verified. The owner approved the
D1, M1-M15 and L1 writes ("go for D3"). The procedure is in the
[cpuidle record](../2026-11-07-mt6797-cpuidle/README.md), "Item 1". The setup matched
boot 3: radios unloaded, CPU1-7 offline, vendor program staged by hand, no watchdog
feeder, `mtu3` left bound.

**Boot `1d20d160…`, T0-T2, observed:**
- **T0.** The module loaded as in boot 3, `mem_sleep` read `s2idle [deep]`, and the 15
  M-fields read through the PMIC wrapper regmap: `0204` `010b`; bucks CON1 `0000`, CON9
  `0001`; LDOs `da68`/`da68`/`da62`/`da62`/`da62`/`0260`. The four bucks' CON6 read
  `0040`, `0040`, `0040` and `000c`.
- **T1.** One 60 s suspend returned on the PCM timer (`r12=1`) after 60.3 s, with no
  reset. 0678 kept the boot-armed 31 s watchdog stopped.
- **T2.** Four 300 s suspends, each returning on the timer, with the M-fields read back
  equal after every one. The run ended `stop=0` with no fault and no taint.

| Run | `pmic_modes` | Δcharge (µAh) / time (s) | Average |
| --- | --- | --- | --- |
| T1 | off | 724 / 60.4 | 43.2 mA |
| T2 off a | off | 3,725 / 300.75 | 44.6 mA |
| T2 off b | off | 3,621 / 300.76 | 43.3 mA |
| T2 on a | on | 3,517 / 300.76 | 42.1 mA |
| T2 on b | on | 3,414 / 300.77 | 40.9 mA |

The modes saved about 2.5 mA, which is under the 3 mA bar the plan set for turning them on
by default. Each window resolves to about ±1 mA, so the figure is borderline.

**USB defect, observed.** After the run the owner replugged, and the host never
enumerated the gadget. The UDC state read `not attached` while the charger reported
online. A `soft_connect` disconnect/connect and a `usb_role` none/device cycle did not
bring it back. With 0676, every suspend logged `pullup D-` and every resume logged
`forcing valid B-device session` then `pullup D+`. Nothing from `mtu3` was logged after
the last resume or at the replug. The owner powered off from the console. This went to the
suspend session.

**Boot `54c9d47b…`, T3-T4, observed.** The new `backlight-policy` (`7fc1cadd…`, from
`5ed802b4`) was renamed over `/bin/backlight-policy` and respawned by init, with
`timer_sec=30`.
- **T4, cable in.** A lid close tried a deep suspend; the bq25890 guard refused it, the
  policy logged `lid suspend refused` once, and the station stayed up. Two further closes
  before the unplug did the same.
- **T3, on battery, three closes.** Each close logged `PM: suspend entry (deep)`. While the
  lid stayed closed the policy suspended again after each timer wake: 2, 16 and 1
  re-suspends in the three closes. Each open woke the station on `r12=0x40` (the EINT bit
  in S1's wake mask), and `gemini-lid` restored the keyboard. Every `wake:` line read
  `returned=1` with unchanged gates and `clk_cfg_0`.
- One resume logged `i2c 4-0020: Unbalanced pm_runtime_enable!`, a `dev_warn`, not a
  `WARNING` splat. This went to the suspend session.

**Analysis.** S1 works as the station's suspend: the watchdog no longer needs a feeder,
lid close suspends to about 42 mA and re-suspends on timer wakes, and lid open wakes it.
Two defects block making it the default: USB does not re-enumerate after a mem resume on
battery, and the `4-0020` runtime-PM imbalance.

### D3 item 2: the awake regression (2026-11-09)

Item 2's stepwise unload, as in the [cpuidle record](../2026-11-07-mt6797-cpuidle/README.md),
"Item 2", ran on boot `d7f02aca…` (D3, boot2 `1f201b4e…`). That boot had already run
V1-V7, so the A53 DVFS modules were loaded with both policies on `userspace`: LL 897 MHz,
L 1209 MHz (CPU4-7 offline), CCI 676 MHz, VPROC1 1060 mV. The radios were unloaded and
`backlight-policy` stopped. The first arming saw no unplug within 15 minutes and ran
nothing; the second ran in full. Each window was 120 s after 10 s of settling.

| Window | Removed before it | Δcharge (µAh) / time (s) | Average | CPU0 idle |
| --- | --- | --- | --- | --- |
| U0 | nothing | 9,208 / 120.8 | 274.5 mA | 99.6 % |
| U1 | policy0 to 221 MHz, then `mtk_cci_devfreq`, `cpufreq_dt`, `clk_mt6797_mcusys`, the VSRAM and DA9214 regulators | 2,379 / 121.9 | 70.2 mA | 98.5 % |
| U2 | the GPU (nothing loaded) | 2,380 / 121.9 | 70.3 mA | 98.5 % |
| U3 | the display stack (13 modules) | 2,276 / 121.9 | 67.2 mA | 98.5 % |
| U4 | audio, haptics, AW9120 LEDs (camera, sensors, touchscreen not loaded) | 2,276 / 121.9 | 67.2 mA | 98.5 % |
| U5 | `dropbear`, `backlight-policy`, the login shell stopped | 2,380 / 121.9 | 70.3 mA | 98.5 % |

Observed:
- Every module unloaded; no fault line, taint 0 throughout.
- U0 reproduced the 271 mA reference. U1 dropped it by 204 mA; nothing after U1 changed
  it by more than one `charge_counter` step.
- Interrupts were the same in U0 and U1 (about 30 timer ticks a second, 1.1 a second on
  `11007000.i2c`), and so was `pm_genpd_summary`. The three ARMPLLs left
  `clk_summary` at the unload, with `clk_unregister: unregistering prepared clock`
  for each, so their hardware state in U1 was not read.
- From U1 on, the `current_now` average (93-95 mA) no longer agreed with
  `charge_counter` (67-70 mA); in U0 both read 274-275 mA.

Inference: what U1 removed was not running drivers. Boot 3's 271 mA reference
(`263ae72a…`) ran without any of these modules loaded. So the drop came from the
hardware state the steps left behind: LL at 221 MHz instead of the boot's 897 MHz,
whatever the DA9214 held at its unload (VPROC1 was 1000 mV after the 221 MHz step), or
something the mcusys unload did to the PLLs. The 96 mA of R1b and the 70 mA here
suggest the boot leaves the A53 clusters at a costly point that nothing lowers unless
the DVFS stack runs. Separating these needs one more stepwise run: the boot state,
then the stack loaded at its lowest points, then each unload. That went to the cpuidle
and cpufreq sessions.

### D3 V1-V9 with the traced schedutil phases (2026-11-09)

Owner-approved, tracing included. Boot `6dbf6d59…` (D3, boot2 `1f201b4e…`), cable in,
`v-test.sh` and `v-trace-check.awk` from `d9e52a18` with their hashes checked on the
station. Two setup slips stopped stages before any DVFS check failed:
- debugfs was not mounted on this boot, so V3 found no `registers` file. The mcusys
  module was unloaded, debugfs and tracefs mounted, and the run resumed at V3.
- `backlight-policy` blanked the console at 238 s and took CPU1-7 offline in V5's
  1547 MHz step. It was frozen with `kill -STOP`, CPU1-7 brought back, and V5 rerun.

Observed:
- **V1-V8 passed.** V5 and V6 swept every point with clocks within 5 %, equal hashes and
  exact table voltages.
- **V7's traced schedutil phase:** 28,884 clock and rail events, no violation, no ring
  overrun. Idle 221/1625 MHz with CCI 819 MHz; load 1495/1950 MHz with CCI 975 MHz.
- **V8:** emulated 62 °C capped both policies one step (1495/1950 MHz); the cap
  released at 0. Its trace had no violation.
- **V9 stopped on its 80 °C limit at t+150 s.** It started warm (64 °C at t+10 s, after
  V5-V8). The 58 °C passive trip under `step_wise` held the caps only one to three
  steps down, swinging between 1339/1755 and 1391/1820 MHz every 10 s, while the SoC
  rose about 1 °C every 10 s to 80.1 °C. Hashes were not reached; no fault, taint 0.
  The load stopped and the SoC was back at 34 °C minutes later.

Inference: the cooling acts, but too weakly to hold an 8-CPU load. `step_wise` moves
one state per poll and gives a step back whenever the trend dips, so it never reaches
the deep caps a sustained load needs. V9 is the boot gate, so cpufreq at boot (V11)
stays closed. The trip and governor tuning went to the cpufreq session.

### D3 R-USB: what a mem suspend resets (2026-11-09)

The suspend session's read-only check, on boot `6dbf6d59…` after the V runs. CPU1-7
offline, radios unloaded, `mt6797-spm-sleep` loaded with the vendor program
(`d6e8a0b8…`). The SSUSB MAC, IPPC and U2 PHY registers it named were read at each
point. The `freeze` control woke from a 30 s RTC alarm; the `mem` path from S1's
30 s PCM timer.

| Point | UDC | MAC | IPPC | U2 PHY |
| --- | --- | --- | --- | --- |
| Enumerated | configured | reference | reference | reference |
| Unplugged | configured | as reference (`0x2460` 12→13) | as reference | as reference |
| After `freeze` | not attached | `0x0084` and `0x0800` cleared by the disconnect | as reference | as reference |
| Replugged after `freeze` | configured at once | as reference | as reference | as reference |
| Unplugged again | configured | as reference | as reference | as reference |
| After `mem` (rc 0, `r12=1`) | not attached | **all nine read 0** | **`0x00` 0x00011000→0x00011001, `0x10` 0x01003D0F→0, `0x50` 0xC8→0x4D** | as reference |

After the `mem` resume the charger reported no cable for the script's ten-minute wait,
so no replug point was read. The gadget never returned and the owner restarted the
station.

Inference: S1's `mem` program resets the SSUSB MAC and IPPC, while the U2 PHY keeps its
settings. That matches the suspend session's first decision branch: run the device
controller's start sequence again at resume when the reset is detected; `phy_init` is
not needed. Sent to the suspend session.

### D3 item 3: the boot state is cheap (2026-11-09)

The cpuidle session's item 3, on a fresh boot `2902b8f5…` with nothing run first.
CPU0 alone, `fb0` blanked, `backlight-policy` stopped, radios unloaded, on battery.
Each window was 120 s after 10 s of settling.

| Window | Step before it | Average (charge counter) | `current_now` |
| --- | --- | --- | --- |
| N0 | none: the boot state | 80.2 mA | 78.7 mA |
| N1 | DA9214 and VSRAM regulators loaded | 77.1 mA | 78.5 mA |
| N2 | `clk-mt6797-mcusys` loaded | 77.1 mA | 78.2 mA |
| N3 | `cpufreq-dt` loaded, policy0 `userspace` 897 MHz | 80.2 mA | 78.0 mA |
| N4 | policy0 221 MHz | 70.3 mA | 98.9 mA |
| N5 | CCI devfreq loaded (probe deferred) | 88.6 mA | 122.8 mA |
| N6 | CCI devfreq unloaded | 88.7 mA | 124.8 mA |
| N7 | `cpufreq-dt` unloaded | 70.3 mA | 98.2 mA |
| N8 | `clk-mt6797-mcusys` unloaded | 70.3 mA | 98.9 mA |
| N9 | regulators unloaded | 67.2 mA | 98.0 mA |

Observed:
- Every load and unload succeeded; no fault line, taint 0.
- At boot no DVFS module was loaded. The boot state read LL at `0xC1114000` (897 MHz),
  L at `0x400C4000` (1274 MHz), CCI at `0xC10C1D89` (630 MHz), sync DCM `0x00070707`,
  VSRAM_L `0x0B` (1100 mV) and DA9214 `0xd7` `0x46` (1000 mV).
- N4 changed only LL (`0x41110000`, divider `0x160`); at N9 `0xd7` read `0x36` (840 mV).
- The CCI devfreq probe deferred (`failed to add devfreq device: -517`, CPU4-7 offline).
  Even so, VSRAM_L rose to `0x0F` (1200 mV) at N5 and stayed there until `cpufreq-dt`
  unloaded at N7.
- With the driver bound, the DA9214 reads failed (`Device or resource busy`), because
  its regmap is not in debugfs. Only the boot and N9 values were read.
- The `current_now` average disagreed with the charge counter from N4 on, as it did in
  item 2.

Inference:
- The 271 mA state is not where the boot leaves the station: N0 drew 80 mA. Item 2's
  U0 (`d7f02aca`, after V1-V7) and boot 3's R (`263ae72a`, after a `mem` suspend) both
  came after earlier work on the same boot. Something that work did, and the DVFS
  unload in item 2 cleared, holds the extra current.
- The DVFS stack itself costs little: LL at 221 MHz and 840 mV saves about 10 mA.
- The deferred CCI probe leaves VSRAM_L at 1200 mV, which costs about 18 mA, until
  `cpufreq-dt` goes. That is a leak in the probe's error path, for the DVFS session.

### D3 item 4: one mem suspend raises the current (2026-11-09)

The cpuidle session's item 4 ran on a fresh station-work-95 boot `b7dba389…`. The image
was boot2 `b2b13892…` (unpadded `ba637ff9…`), with init `73e709dc…`. Nothing ran before
the item. The setup matched item 3: CPU0 alone, `fb0` blanked, `backlight-policy`
stopped, radios unloaded, on battery, and each window was 120 s after 10 s of settling.
A1 read high, so the script took branch A.

| Window | Step before it | Average (charge counter) | `current_now` |
| --- | --- | --- | --- |
| A0 | none: the boot state | 80.2 mA | 80.1 mA |
| A1 | `mt6797-spm-sleep` loaded, one 30 s `mem` suspend | 274.5 mA | 275.9 mA |
| A2 | `clk-mt6797-mcusys` loaded and unloaded | 234.4 mA | 236.0 mA |
| A3 | DVFS stack loaded, policy0 221 MHz, CCI devfreq loaded, then all unloaded | 64.2 mA | 92.8 mA |

Observed:
- The suspend returned `rc=0` after 30.3 s, and the PCM timer woke it (`r12=00000001`).
  Every load and unload succeeded. There was no fault line, taint stayed 0, and the
  device powered off by itself at 700 s.
- On a boot where nothing else ran, one `mem` suspend reproduced the 271 mA state.
- The A0-A2 register reads were identical: MCUMIXED, MCUCFG, INFRACFG, TOPCKGEN, SPM,
  DRAM and DA9214. The suspend left no visible change in any of them.
- At A3, only the item 3 N4/N9 pattern changed: LL `0x1001a204` went `0xC1114000` to
  `0x41110000`, the divider `0x1001a274` went 0 to `0x160`, MCUCFG `0x10220660` went
  `0x157` to `0x117`, and DA9214 `0xd7` went `0x46` to `0x36`.
- The A2 unload logged `clk_unregister: unregistering prepared clock` for
  `mcu-armpll-cci`, `-l` and `-ll`. The A3 unload logged the same.
- The CCI probe deferred again (`-517`).
- After the resume, DRM read the panel again (`dsi get 1 byte data`, 268.9 s).
  - The clock summary listed 126 enabled clocks at A1 and A2, as at boot. A0 and A3
    listed 112.
  - The 14 extra clocks are `mipi_tx0_pll` and the display `mm_*` gates.
  - Nothing in `dmesg` marks when the display clocks went off between A2 (431 s) and
    A3 (566 s).
  - `consoleblank` reads 120 s.
- The soc-thermal zone read failed (`No data available`) after the resume.

Inference:
- The extra ~195 mA comes from the `mem` suspend and resume. The resumed display
  pipeline is one candidate. The A3 drop happened alongside both the DVFS cycle and
  the display clocks going off, so this run can't separate the two.
- The `mcusys` load and unload alone was worth about 40 mA (A2).
- The next run should hold the display state fixed across the resume, or read it
  between steps. That run belongs to the cpuidle session.

### station-work-95 V1-V9 with power_allocator (2026-11-09)

The rerun after the cpufreq session's 0680 (`1768fe04`, identity `63d58a82`). The owner
approved the two new writes: `power_allocator` in the soc-thermal `policy`, and an
emulated 77 °C in place of 62 °C. The image was station-work-95: boot2 `b2b13892…`,
init `73e709dc…`. It ran on boot `f49ed0bf…`, the boot after item 4, cable in.

Setup:
- `v-test.sh` `c7725a3f…` and `v-trace-check.awk` `1a24f2a8…`, with hashes checked on the
  station.
- debugfs and tracefs mounted, `backlight-policy` frozen and CPU0-7 online before V1.
- The radios stayed loaded.

Observed:
- **V1-V9 passed in one run.** There was no fault line and taint stayed 0.
- **V7 traced schedutil:** 14,492 events, no violation. Idle was 1014/1352 MHz with the
  CCI at 754 MHz; load was 1495/1950 MHz with the CCI at 975 MHz.
- **V8:** the emulated 77 °C capped both policies to their lowest points (221/325 MHz)
  within 5 s, and the cap released at 0. The trace had 2,138 events, no violation.
- **V9:** a 600 s load on all eight CPUs.
  - It started at 34.5 °C and reached 67.7 °C at t+10 s.
  - `power_allocator` (sustainable power 1500) then held the SoC between 62.7 and
    75.4 °C. The caps moved every poll, between 1547/2002 and 338/468 MHz, with VPROC1
    between 890 and 1200 mV.
  - The SoC never reached the 80 °C stop, and fell to 42.8 °C after the load ended.
  - Every CPU's hashes matched.
  - The trace had 158,882 clock and rail events and no violation.

Inference:
- 0680's thermal setup holds a sustained 8-CPU load below 76 °C, where `step_wise` let
  it reach 80 °C in 150 s.
- V9, the boot gate, now passes on station-work-95. Whether cpufreq loads at boot
  (V11) is the cpufreq session's call.

### station-work-95 item 5: the display across a resume (2026-11-09)

The cpuidle session's item 5, on a fresh station-work-95 boot `6b9cf9c0…`, on battery.
Setup as item 4, plus console blank off (`consoleblank` read 0) and `fb0` blanked with
`4`. The V9p sessions before it ran on earlier boots.

| Window | Step before it | `fb0/blank`, connector `dpms`, `bl_power` | `mm_*`/`mipi_*` clocks on | Average (charge counter) |
| --- | --- | --- | --- | --- |
| E0 | `fb0` blank 4 | 1, Off, 4 | 2 | 114.1 mA |
| E1 | one 30 s `mem` suspend (`rc=0`, timer wake) | 0, On, 0 | 16 | 286.9 mA |
| E2 | `fb0` blank 4 again | 1, Off, 4 | 2 | 77.1 mA |
| E3 | `fb0` 0, then 4 | 1, Off, 4 at the step | 2 at the step | 209.8 mA |

Observed:
- After the resume, `fb0/blank` read 0. The connector read `dpms On`, `bl_power` read 0
  (backlight on), and the 14 display clocks were back on. Blanking again (E2) brought
  the draw to 77 mA.
- `fb0/blank` reads back 1 after a write of 4.
- DRM read the panel again three times with no step of the test behind it: at 220.8 s
  (inside E0), at 562.8 s (inside E3), and after E3, where the end read showed the
  display on.
  - The log shows no input event, but input is not logged.
  - E0 and E3 are therefore mixed windows, which explains their 114 and 210 mA.
- soc-thermal read `ENODATA` from the resume on, as in item 4. `battery-thermal` stayed
  at 23.9-24.5 °C, so the extra stop never applied.
- No fault line, taint 0. The device powered off by itself at 670 s.

Inference:
- The ~200 mA after a `mem` resume is the display: the resume turns a blanked display
  fully back on, backlight included. Blanking again removes it. The fix belongs to the
  display session.
- Something else also unblanks the display while `consoleblank` is 0. A key or lid
  event is the likeliest cause. Until it is known, power windows need the display state
  read at both ends.

## Analysis

None yet.

## Conclusion

Pending.

## Follow-up

- Close the two composer gaps, then build D1.
- Add Phase 3's tests when the A72 frequency code is pushed.
