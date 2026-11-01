# Experiment: all ten MT6797 cores online on the station

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-01-mt6797-all-cores` |
| Status | `planned`; patches 0424-0428 written on the owner's approval and built, not run; one module-free boot of the opt-in `mt6797-a53-station-a72` profile is owner-approved and queued after audio and Wi-Fi; the bring-up test is not admitted |
| Subsystem | MT6797 Cortex-A72 CPU8/CPU9, arm64 late CPU admission, DA9214 BUCKB, PMIC wrapper |
| Device variant | Planet Computers Gemini PDA, MT6797X, named development unit |
| Date(s) | 2026-11-01 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | None; the [roadmap](../../docs/ROADMAP.md) has A72 default integration parked, and the owner has now asked for it |

## Question or hypothesis

CPU8 and CPU9 have run on mainline, but only on isolated candidates. What is the
smallest change that gets all ten cores online on the normal station kernel,
next to Wi-Fi, audio and GNSS?

Hypothesis: the hardware sequence is already known and repeatable, and almost
all of the roughly 190 A72 patches are one-shot gating and evidence capture, not
things the cores need. A small module plus three small built-in changes should
be enough. This is untested. The source review below supports it; only a boot
can show it.

## Provenance and environment

- Reviewed at `origin/main` `97c55871`, in the station tree (series
  `patches/series-a53-station`, a compile tree prepared in the development VM)
  and the kernel configuration of the package built from `7ab57de0`.
- The station boots with `maxcpus=8`. Its configuration has every A72 option off
  (`MTK_MT6797_A72_*`, `ARM64_MT6797_A72_CAPABILITY_PROFILE`), and also
  `MTK_MT6797_DVFSP_HANDOFF` and `REGULATOR_DA9213_LEGACY`.
- Nothing was built or run for this record.

## Safety assessment

This record changes nothing on the device. The bring-up it proposes writes the
DA9214 BUCKB enable bit, SPM, the TOPRGU PWRAP reset and MCUCFG DCM, and makes
the secure SRAM-LDO call. Under [safety](../../docs/SAFETY.md) those need an
admitted protocol and the owner's approval, so the protocol is drafted here and
**is not yet admitted**. The read-only request below needs no new approval.

No voltage or frequency value is changed. BUCKB stays on the selector the
preloader left (`0x46`, 1.0 V by the register encoding; never measured on the
pin), and the B cluster stays at the 750 MHz that firmware sets. Thermal
protection stays as it is on the station.

## What is proven, inferred and unknown

### Observed

- Both A72s came online under mainline Linux 7.1.3 on at least nine distinct
  boot IDs, for example the
  [same-boot CPU9 run](../2026-08-31-mainline-a72-cpu9-same-boot-successor/README.md),
  the [topology run](../2026-09-02-mainline-mt6797-cpu-map/README.md) and the
  [integrated run](../2026-09-04-mt6797-a72-frequency-observation/results/zero-divider-runtime-pass-20260904.txt).
- They kept exact affinity and independent scheduler accounting, and passed
  [concurrent multi-line RAM checks](../2026-09-02-mainline-dual-a72-concurrent-multiline/README.md).
  All of these were short, bounded runs.
- CPU9 alone [went down and came back](../2026-09-02-mainline-a72-hotplug-lifecycle-gate/README.md)
  with CPU8 retained. The last-A72 power-down was never run on mainline.
- Live values during those runs: B 750 MHz, LL 897 MHz, L 1274 MHz, CCI
  629.5 MHz, and a temperature rise of up to 6.3 C under the bounded load. A
  second boot [failed its thermal comparison](../2026-09-04-mt6797-a72-frequency-observation/results/cold-rise-runtime-thermal-rejected.txt)
  against the first, so the thermal behaviour is not settled. No long load has
  ever run.
- The sequence those runs used, from patches
  [0390](../../patches/v7.1.3/0390-soc-mediatek-add-serialized-A72-platform-effects.patch),
  [0294](../../patches/v7.1.3/0294-regulator-add-positive-DA921x-Buck-B-provider-transaction.patch)
  and [0392](../../patches/v7.1.3/0392-soc-mediatek-add-one-shot-A72-SRAM-LDO-owner.patch):

  | Step | Operation | Proven state |
  | --- | --- | --- |
  | 1 | SPM `0x10006218` bit 0 set (MP2 reset release) | `0x00010132` to `0x00010133` |
  | 2 | Ordering read of `0x102224a0` | |
  | 3 | Assert TOPRGU PWRAP SPI reset | status 1 |
  | 4 | DA9214 `0x5e` from `0x00` to `0x01` over I2C6 at `0x68`, then wait | selectors stay `0x46` |
  | 5 | SPM `0x10006290` clear bits 1:0 | `0x2` to `0x0` |
  | 6 | Deassert PWRAP reset, wait 240 to 260 us | status 0 |
  | 7 | SMC `0xc20003bf` with 110000 (SRAM LDO 1.1 V), wait 240 us | selector `0x102222b0` bits 11:0 reads `0x8fb` twice |
  | 8 | PSCI `CPU_ON` for `0x200` | CPU8 online |
  | 9 | MCUCFG `0x10222274`: write `0x0f`, then `0x0d` | CPU8 online, CPU9 not yet |
  | 10 | PSCI `CPU_ON` for `0x201` | no further cluster step |

- On the station, by source: `add_cpu()` is the only entry needed;
  `machine_restart()` and `machine_power_off()` use `smp_send_stop()`, while only
  `machine_shutdown()`, used by kexec, needs CPUs to go offline.

### Inferred

- **The firmware offers no Spectre workaround calls.** It implements PSCI v0.2,
  and Linux only probes SMCCC 1.1 on PSCI 1.0 or later. So on an A72,
  `spectre_v2_enable_mitigation()` ends as vulnerable, and
  `spectre_bhb_enable_mitigation()` stops early because of that. If so, the
  mitigation callbacks need no boot-time patching for the A72s. The read-only
  request checks the first half of this.
- **Most of the existing machinery is not needed by the hardware.** The
  transaction owners, tokens, retained-RAM ledgers, P30E checkpoints and identity
  hashes exist to make one-shot experiments attributable. Their configuration
  hashes bind to exact old kernels, so they cannot simply be enabled on the
  station anyway. Quarantined profiles are not foundations, so new work goes in
  new patches.
- **PWRAP concurrency is a new risk the proven runs did not face.** Steps 3 to 6
  hold the PMIC wrapper's SPI side in reset for over a millisecond. Those runs
  were quiet. The station has the fuel gauge, the battery-temperature AUXADC, and
  audio and Wi-Fi regulators all using the wrapper. A transaction during the
  window could time out or leave the wrapper stuck. It has not been observed,
  because nothing has tried it.
- A correction to [the PCM study](../2026-10-31-mt6797-vendor-cpu-policy-re/results/pcm-idvfs-ownership.md):
  it labels `0x1100e000` as PWRAP, but the device tree has I2C6 there. That fits
  the PCM's job of driving the DA9214 directly. The evidence file stays as
  recorded.

### Unknown

- Whether I2C6 is bound on the station. Its tree overrides the controller to
  `mediatek,mt6797-i2c`, while every proven write used
  `mediatek,mt6797-idvfs-i2c` with the DVFSP handoff, and that handoff is off in
  the station configuration.
- Whether the station's A72-off register state matches the proven one.
- How much battery two idle, always-on A72s cost. There is no CPU idle driver, so
  they sit in WFI with the cluster powered.
- Behaviour under long load, across many cold boots, and on any other unit.
- Whether the 750 MHz B clock is stable across boots in general; it is the only
  value ever seen, and the sample is small.
- Why the vendor resets PWRAP during the window. The sequence is copied, not
  understood.

## Why the cores are not simply online today

1. **Rail and isolation.** `CPU_ON` is unsafe until steps 1 to 7 are done. Step 4
   needs I2C6, which does not exist when `smp_init()` runs, so these cores must
   come up late. The same is true of the vendor kernel, which boots with
   `maxcpus=5`.
2. **Late CPU capabilities.** Boot detects capabilities on A53s only. An A72 then
   has five local capabilities the system never set (`ARM64_SPECTRE_V2`,
   `ARM64_SPECTRE_V4`, `ARM64_SPECTRE_BHB`, `ARM64_WORKAROUND_1742098`,
   `ARM64_WORKAROUND_SPECULATIVE_AT`), and `verify_local_cpu_caps()` kills it.
   The old stack seeded these before finalization. This must be built in.
3. **The gate.** `mt6797_psci_cpu_boot()` refuses CPU8 and CPU9 by default. That
   refusal is correct until a sequence exists, and it must stay the default.

## Proposed design

Four patches, new work on the station series, written after the owner approved
this design on 2026-11-01:

| Patch | What | Where |
| --- | --- | --- |
| [0424](../../patches/proposals/0424-arm64-set-the-capabilities-of-the-late-MT6797-A72s.patch) | Set the five capability bits before finalization, on this board only | Built in: capabilities cannot change after boot |
| [0425](../../patches/proposals/0425-arm64-mediatek-let-the-MT6797-A72-gate-open.patch) | A gate-open call, so `cpu_boot` reaches PSCI only after the sequence ran | Built in: `cpu_ops` is in the Image |
| [0426](../../patches/proposals/0426-soc-mediatek-pmic-wrap-let-a-caller-hold-PMIC-access.patch) | A mutex in the PMIC wrapper's regmap accessors, held across steps 1 to 6 (regmap already sleeps here, so waiters just sleep) | Built in: the wrapper driver is built in |
| [0427](../../patches/proposals/0427-soc-mediatek-bring-up-the-MT6797-A72-pair-from-a-mod.patch) | `mt6797-a72`: runs steps 1 to 10, then `add_cpu(8)` and `add_cpu(9)` | A module, so it can be retried across loads without a boot |

Loading the module is the only trigger. Later the station's init loads it, and
that is "all cores online in normal use".

Choices that keep it small:

- **One-way.** The A72s come up once and stay up, with `cpu_can_disable` still
  false. The missing vendor inverse stops mattering, and no down path is carried.
  The cost is no offlining, which also rules out kexec (`BUG_ON` in
  `smp_shutdown_nonboot_cpus()`).
- **No clock or voltage control.** Fixed 750 MHz, 1.0 V and SRAM 1.1 V. The vendor
  table runs 845 MHz at 800 mV on this unit, so this point is not aggressive by
  that table. No cpufreq means no throttling either, so the protection stays the
  existing power-off and hardware reset.
- **Reuse the proven I2C path.** Set the idvfs compatible and turn the DVFSP
  handoff on for the station, rather than a new, untested transport. It is large
  (3350 lines), but it exists and it checks that the CSPM firmware is stopped.
  Replacing it with something smaller can come after the cores work.
- **Refuse on any mismatch.** The module checks the prestate in the table and does
  nothing if it differs. Nothing is retried.

All of this is opt-in, through the `mt6797-a53-station-a72` profile and
`mt6797-gemini-pda-station-a72.dtb` ([0428](../../patches/proposals/0428-soc-mediatek-keep-the-MT6797-A72-boot-changes-opt-in.patch)).
The plain station carries the patches with their options off, keeps its device tree,
and gains only three unused exported functions, an unused flag and an unused mutex. Its accessors
take no new lock. What the opt-in profile does at every boot is the next section.

What the A72s would lack: Spectre v2, v4 and BHB mitigation (firmware has none, if
the inference holds). The A53s are not affected either way.

## What the A72 profile does at every boot

The custodian asked this before flashing anything with the handoff on. Approving the
patches did not approve this running at each boot, and the owner has since approved it
for one test boot only. It
applies only to the `mt6797-a53-station-a72` profile with its device tree, and it
applies even if the module is never loaded.

Evidence: source of the station series, undefined symbols of the compiled handoff
object, and the resolved `kernel.config` and `System.map` of Buildbox package
`eff98241...` (job `e1add137...-mt6797-a53-station-m1`), whose options match this
profile. **None of this has booted on the station configuration.** Older candidates ran
the same handoff, but never beside Wi-Fi, audio and GNSS.

| Target | At boot | What stops anything more |
| --- | --- | --- |
| DA9214 | **No transfer and no write.** The adapter registers and the client appears, with no bus traffic | `REGULATOR_DA9211` and `REGULATOR_DA9213_LEGACY` are off and no such module is packaged. The adapter sets no detect class, so nothing scans the bus. The only kernel writer is `mt6797-a72.ko` |
| Any regulator or PMIC | No access. The handoff and I2C code call no regulator or PMIC function | Absent from the code path |
| DVFS and PCM (CSPM) | Reads only: exact stopped-signature samples at probe and 45 s later | No `writel` in the handoff source. The object's only register-map import is `regmap_read`. `mt6797_dvfsp_cspm_execute` exists, but its only caller (the clock backend) is not built |
| Infracfg | Reads only, to observe the clock gate | As above |
| Clocks | **Yes.** `I2C_APPM` goes one balanced enable and disable through the clock framework, so firmware's ungated clock ends gated. I2C6 then enables and disables its main and AP-DMA clocks once at probe | The gate is the point of the handoff. A mismatch faults it and I2C6 stays unusable. The AP-DMA clock is reference-counted, and by source the keyboard's I2C already toggles it |
| I2C6 controller | **Yes, its own registers only.** `mtk_i2c_init_hw()` clears flags and sets timing. It writes `0` to the start register, which starts nothing | Existing driver behaviour, the same as the other I2C buses |
| SCP | No access | The firmware-writer attestation option is **off**, so this configuration does not check the SCP is stopped. Binding I2C6 does not start or signal it |
| Secure firmware | No SMC from the handoff or I2C driver. 0424's A53 callbacks make no SMC with no SMCCC conduit | Conduit check in 0424 |

Behaviour worth noting:

- The handoff probes asynchronously and waits up to 50 s, so boot does not wait on it.
  I2C6 binds after its 45 s check, and only if the CSPM signature matches exactly. On a
  mismatch it reports `access_grant=denied`, I2C6 stays unusable, and the module refuses.
- **A new path exists for root.** `I2C_CHARDEV=y` makes the bus reachable as a new
  `/dev/i2c-N`, so `i2cset` from a shell could write the DA9214, including changing a
  voltage selector. Nothing does this, and the kernel guards above do not cover
  it. **Do not point I2C tools at that bus.** It should number after the existing two,
  because it binds last; confirm on the first boot.
- 0424 sets five capability bits at boot and runs each one's callback on the A53s, which
  read ID registers and report unaffected. No device register is touched, by source.

Unproven until a boot shows it: that the clock change disturbs nothing else, that these
effects hold together beside the station's other drivers, and that the CSPM signature
still matches on this kernel. The first check on that boot is the handoff's log line and
`0x1100e000.i2c` binding, with everything else unchanged.

## Boot order

Agreed with the custodian's default: boot the audio and Wi-Fi work first without this
profile, then this profile alone as its own boot, so a failure can be attributed. Main's
plain station no longer carries these effects, so nothing needs backing out.

## Associated code

Patches 0424-0428, and [the opt-in fragment](../../configs/gemini-a53-station-a72.fragment). The module has
no DT binding document yet; that belongs with upstream work.

Choices made while writing them:

- **Capabilities:** an audit of every A72 match in the errata tables gives the five
  bits for this configuration. `ARM64_SPECTRE_V3A` also matches A72 but only exists
  with `RANDOMIZE_BASE`, which the station has off, so the option depends on it being
  off. If SMCCC 1.1 is present the bits stay clear and the A72s are rejected, rather
  than run with vectors nothing patched.
- **BUCKB settle:** 1 ms, the vendor's value. The old code carries both a 100 us and
  a 1000 us constant, and which one ran was not resolved. Longer is the cautious side.
- **Topology:** the station tree deletes `cpu-map`, so the cores come up flat. That is
  the state of the proven [RAM run](../2026-09-02-mainline-dual-a72-ram-coherency/README.md).
  Restoring 4+4+2 changes A53 scheduling too, so it stays a follow-up.
- **Load failure:** a failed probe fails the load and leaves no driver. A retry is safe
  only before the isolation clear, and the off-state check refuses any retry after it.

Tested: compile only, in the development VM, for the changed objects and the station
DTB, and strict checkpatch reports only the missing `Signed-off-by`, which is left for
the owner. Nothing built in the VM is booted.

## Procedure

### Read-only reading on the running station (done)

Unique observation: the station's own state, which no earlier run could show.

```sh
uname -r; cat /proc/sys/kernel/random/boot_id; cat /proc/cmdline
for f in present online offline; do echo "$f $(cat /sys/devices/system/cpu/$f)"; done
dmesg | grep -iE 'psci|smccc|mt6797-psci|dvfsp|detected:'
grep . /sys/devices/system/cpu/vulnerabilities/*
ls -l /sys/bus/platform/devices/1100e000.i2c/driver /sys/bus/i2c/devices/
for a in 0x10006188 0x1000618c 0x10006218 0x10006240 0x10006244 0x10006290 0x10222274; do
  echo "$a $(busybox devmem $a 32)"
done
for f in current_now voltage_now temp status; do echo "$f $(cat /sys/class/power_supply/battery/$f)"; done
grep . /sys/class/thermal/thermal_zone*/temp
```

Every devmem address was read directly in the A72-off state by the
[platform snapshot](../2026-08-24-mainline-a72-platform-snapshot-first-read/results/runtime-attempt-1-pass-20260825.txt).
No I2C, write, CPU or module action. Stop rule: if a read hangs, stop, do not
retry, and report; the watchdog returns the device to Gemian, and then a
physical boot2 selection brings the station back.

| Observation | Decision |
| --- | --- |
| SPM and MCUCFG match the proven `2a00005c 2a00004c`-class state: `0x10006218=00010132`, `0x10006290=00000002`, `0x10222274` bits 6:0 clear | Same prestate; the table applies |
| Any of those differs | Explain the difference before writing code |
| No SMCCC 1.1 in dmesg | Capability bits alone are enough, as designed |
| SMCCC 1.1 present, or a workaround reported | Mitigation seeding must be redesigned |
| `1100e000.i2c` bound or deferred | Sets what the DT change must undo |

The current and temperature lines are the baseline for the battery cost.

### Boot-only test (owner-approved, one boot, not run)

The owner approved on 2026-11-01 one boot of the `mt6797-a53-station-a72` profile with
the module not loaded, after the audio and Wi-Fi boot. This approves the at-every-boot
effects above for this one boot, and no module load.

Hypothesis: with the handoff on and I2C6 rebound, the station behaves as before, I2C6
binds and the DA9214 sees no traffic. Unique observation: these effects on the station's
own configuration, beside its other drivers.

Attribution: build the profile from the same commit as the last good plain-station boot
(if that commit has 0424-0428), so the options and device tree are the only difference.
Compose with `station-dt.sh` from `mt6797-gemini-pda-station-a72.dtb`, and leave
`mt6797-a72.ko` out of the initramfs module list. Station init loads only named modules,
and `UEVENT_HELPER` is off, so nothing can then load it.

After at least 60 s of uptime, read:

```sh
uname -r; cat /proc/sys/kernel/random/boot_id; cat /proc/cmdline
for f in present online offline; do echo "$f $(cat /sys/devices/system/cpu/$f)"; done
dmesg | grep -iE 'dvfsp|1100e000|I2C6_GUARD|mt6797-a72|CPU features: detected|SMCCC'
ls -l /sys/bus/platform/devices/1100e000.i2c/driver /sys/bus/i2c/devices/
grep . /sys/devices/system/cpu/vulnerabilities/spectre_v2 /sys/devices/system/cpu/vulnerabilities/spec_store_bypass
for a in 0x10006188 0x1000618c 0x10006218 0x10006240 0x10006244 0x10006290 0x10222274; do
  echo "$a $(busybox devmem $a 32)"
done
for f in voltage_now temp status; do echo "$f $(cat /sys/class/power_supply/battery/$f)"; done
grep . /sys/class/thermal/thermal_zone*/temp
```

Then the custodian's usual regression: keyboard, USB SSH, Wi-Fi, audio, GNSS and display,
and about 10 minutes of normal use with the same reads repeated at the end.

| Observation | Meaning | Next |
| --- | --- | --- |
| `access_grant=ready`, `1100e000.i2c` bound, registers as before, regression passes | Boot effects are acceptable | Ask the owner to admit the bring-up test |
| `access_grant=denied` or another handoff fault, station otherwise fine | The module would refuse; no harm shown | Keep the log, explain it, no repeat boot |
| I2C6 does not bind and no handoff line appears | Probe or dependency problem | Keep the log and read the deferred list, no repeat boot |
| The existing I2C bus numbers change | A tool may read the wrong bus | Stop those tools and fix numbering first |
| Registers differ from the reading | Boot changed A72 state | Stop, explain before any module test |
| Regression fails: keyboard, Wi-Fi, audio, GNSS or PMIC reads | Attributable to these effects | Return to the previous image, investigate offline |
| No boot | Built-in change or DT | Watchdog or owner to Gemian, reinstall the previous boot2, no repeat |

Stop rules: do not load the module, do not use I2C tools on the new bus, make no register
writes, and do not repeat the boot without a new decision. Stop on the safety document's
conditions: unexpected heat, charging anomalies, repeated filesystem errors or
watchdog loops. Recovery that needs the owner: selecting boot2, and returning to Gemian
if the boot fails.

### Bring-up test (draft, not admitted)

1. Build the `mt6797-a53-station-a72` profile from a pushed commit on Buildbox, with
   `BUILD_MODULES=1`, and boot `mt6797-gemini-pda-station-a72.dtb`.
2. Boot it with the module not loaded, and confirm Wi-Fi, audio, GNSS and PMIC
   readings are unchanged, and that I2C6 bound after about 45 s. That covers the
   built-in changes on their own.
3. Hypothesis: `insmod mt6797-a72.ko` brings up both cores. Unique observation:
   the first time this sequence runs beside live PMIC traffic.
4. Check `online` is `0-9`, per-CPU accounting under a pinned load,
   a fuel-gauge reading and AUXADC after the window, and temperature.
5. Finite load: pinned work on both A72s for a fixed time, watching temperature.
   Stop at 75 C SoC, a limit proposed here that the owner can change.

| Result | Meaning | Next |
| --- | --- | --- |
| `0-9`, PMIC readings fine | Works on the station | Soak, then measure idle cost, then load at init |
| Module refuses on prestate | No hardware changed | Read the logged value, no retry |
| CPU8 rejected on a capability conflict | Patch 0424 incomplete; the CPU parks | Read the log, fix, new boot |
| `CPU_ON` returns, core never arrives | Sequence differs from the proven runs | Stop, compare, no retry |
| PMIC errors after the window | Patch 0426 insufficient | Stop, keep logs, recover |
| Hang | Unknown | Watchdog to Gemian if the whole system stops; a single stuck CPU may not trigger it, so the owner may need to force power off |

Recovery after a failed module load: the module is not loaded at boot, so a
reboot and the owner's boot2 selection return a working station. Only the built-in
changes and the DT change can stop boot2 booting. Step 2 tests those, and a
failure there means returning to Gemian and reinstalling the previous boot2 image.

## Observations

One read-only reading on station 30, boot `4ac95e75`, with Wi-Fi associated and audio
modules loaded and idle. No hang, write or module action.

| Check | Value | Against the proven state |
| --- | --- | --- |
| `0x10006218`, `0x10006240`, `0x10006244` | `00010132`, `00010332`, `00010332` | Exact match |
| `0x10006290`, `0x10222274` | `00000002`, `00000000` | Exact match |
| `0x10006188`, `0x1000618c` | `003D8108`, `003DC2FF` | A72 bits 7:6 give the same off result. Bits 8, 9 and 14 differ and are not explained; the module does not read them |
| `0x10006180`, `0x10006184` | `2B00005E`, `2B00004E` with audio | Bit 24 is AUDIO and bit 1 is CONN, which fits audio and Wi-Fi on. The module does not read them |
| PSCI | `PSCIv0.2 detected`, no SMCCC version line | Supports the capability design |
| CPUs | present `0-9`, online `0-7` | As expected |
| `1100e000.i2c` | No driver bound | Expected: the handoff is off there. Whether it was deferred was not checked |
| Battery | `current_now` 0, Not charging, 4338720 uV | **Not a usable idle baseline**, so the A72 idle cost needs another method |

So the prestate table applies on this station. The driver's checks are the same ones
compared here, and it would refuse on any difference.

Package `eff98241...` (job `e1add137...-m1`, Buildbox-2) built and linked the module and
the Image with the earlier version of the options. It is an audit input, and superseded
for booting because the plain station no longer carries these options.

Package `e1eeb6a7...` (job `f33b84a6...-mt6797-a53-station-a72-m1`, Buildbox-2) is the
opt-in profile: Image.gz `42b794d6...`, the module, and
`mt6797-gemini-pda-station-a72.dtb`, with its checksums passing. A build authorizes no
boot.

## Analysis

The project's [2026-10-03 review](../2026-10-03-project-review/README.md) parked
this work because it had consumed the most effort for the least usability, and
because it waited on measurement contracts. The change since then is the
station's own thermal protection and the owner's request. The old method tried to
prove each effect before the next, which is why it grew. The method here takes
those results as given and stops at what the cores need.

## Conclusion

No result yet. The gap is integration, not missing hardware knowledge, with one
new risk (PWRAP concurrency) and a few open costs.

## Follow-up

After the first working boot, in order: soak; idle power; load at init; then, as
their own work, scheduler capacity (a 750 MHz A72 next to faster-clocked A53s),
the down path, cpufreq and thermal cooling.
