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
  Boots 2 and 3 have not run.

## Analysis

None yet.

## Conclusion

Pending.

## Follow-up

- Close the two composer gaps, then build D1.
- Add Phase 3's tests when the A72 frequency code is pushed.
