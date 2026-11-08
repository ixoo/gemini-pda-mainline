# Experiment: all ten MT6797 cores online on the station

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-01-mt6797-all-cores` |
| Status | `running`; bring-up attempt 2 passed on one boot: both A72s online beside the station, a finite load on each, idle, and a clean reboot. A 30 min soak also passed on one boot, with every hash correct, and the cluster map reads 4+4+2 with the A72s joining late. Capacity, idle cost, a longer soak and loading at init remain, each its own owner decision |
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
  window could time out or leave the wrapper stuck. Two bring-ups beside that
  traffic showed no PMIC error, which is too few to exclude it.
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
| DVFS and PCM (CSPM) | Reads only: exact stopped-signature samples at probe and 100 ms later (45 s before 0446) | No `writel` in the handoff source. The object's only register-map import is `regmap_read`. `mt6797_dvfsp_cspm_execute` exists, but its only caller (the clock backend) is not built |
| Infracfg | Reads only, to observe the clock gate | As above |
| Clocks | **Yes.** `I2C_APPM` goes one balanced enable and disable through the clock framework, so firmware's ungated clock ends gated. I2C6 then enables and disables its main and AP-DMA clocks once at probe | The gate is the point of the handoff. A mismatch faults it and I2C6 stays unusable. The AP-DMA clock is reference-counted, and by source the keyboard's I2C already toggles it |
| I2C6 controller | **Yes, its own registers only.** `mtk_i2c_init_hw()` clears flags and sets timing. It writes `0` to the start register, which starts nothing | Existing driver behaviour, the same as the other I2C buses |
| SCP | No access | The firmware-writer attestation option is **off**, so this configuration does not check the SCP is stopped. Binding I2C6 does not start or signal it |
| Secure firmware | No SMC from the handoff or I2C driver. 0424's A53 callbacks make no SMC with no SMCCC conduit | Conduit check in 0424 |

Behaviour worth noting:

- **Correction:** this record first said boot does not wait on the handoff. That was
  wrong, and boot `7dd24578` showed it: `kernel_init()` calls `async_synchronize_full()`
  before `/init`, so the async probe's wait held `/init` for its whole late check.
  [0446](../../patches/proposals/0446-soc-mediatek-stop-the-DVFSP-handoff-holding-up-init.patch)
  runs that check after 100 ms instead of 45 s, and the module repeats it just before
  its write, refusing on a mismatch.
- I2C6 binds after that check, and only if the CSPM signature matches exactly. On a
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
- **Topology:** the station tree deletes `cpu-map`, so the cores came up flat, as in the
  proven [RAM run](../2026-09-02-mainline-dual-a72-ram-coherency/README.md). Restoring 4+4+2
  changes A53 scheduling too, so [0455](../../patches/proposals/0455-arm64-dts-mediatek-describe-the-clusters-on-the-Gemin.patch) restores it in the
  A72 tree only. The plain station stays flat. See "Cluster map" below.
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

Candidate for this boot: package `af871fff...` (job
`39fde673...-mt6797-a53-station-a72-m1`, Buildbox-2), Image.gz `42b794d6...`, against
the plain package `3700c7b9...` from `b36b2f7f`, Image.gz `933a7d70...`, which passed
boot `24465562`. `scripts/buildbox` builds only a branch tip, so this came from main's
`39fde673`, whose `patches`, `configs`, `kernel` and `scripts` are identical to
`b36b2f7f`; the two packages record the same patchset `d96acd6b...`.

What differs from the plain package:

- Configuration: `ARM64_MT6797_LATE_A72=y`, `MTK_MT6797_DVFSP_HANDOFF=y`,
  `MTK_MT6797_A72=m`, and `MTK_MT6797_DVFSP_STATE_DECODERS=y`, which the handoff brings.
- Image: those options' code, which includes the taken wrapper mutex and the handoff's
  I2C paths.
- Device tree: `mt6797-gemini-pda-station-a72.dtb` (`417250d9...`) differs from the
  plain station DTB by the I2C6 compatible, the `a72-power` node and its phandles.
- Modules: `mt6797-a72.ko` is added, to be left out of the image; every other module
  is byte-identical.

### Second module-free boot (owner-approved, one boot, not run)

The owner approved one more module-free boot on 2026-11-01, to confirm 0446. The
reads, stop rules and table above apply, with these added:

| Observation | Meaning | Next |
| --- | --- | --- |
| `/init` within about 1 s of the plain image's time, `access_grant=ready`, I2C6 bound | The fix works | Ask the owner to admit the bring-up test |
| `/init` still late | 0446 is incomplete | Read the log, no repeat |
| Fault on a first join again | Stronger reason to suspect these changes | Compare with plain over several joins before the bring-up test |
| First joins clean | Finding 2 stays one unexplained sample | Keep counting in later boots |

Also check GNSS if the image carries it. Candidate: package `db7b42af...` (job
`d20613ad...-mt6797-a53-station-a72-m1`, Buildbox-2), Image.gz `3e637a85...`, DTB
`91ca8aae...`. Against `af871fff...`: the handoff change in the Image, the module, the
`access-controllers` line, and the AUDIO domain clocks from 0445, another session's
station patch. All other modules and the configuration are identical.

### Bring-up test, attempt 1 (owner-approved, run; see Observations)

The owner approved this on 2026-11-01, keeping the proposed 75 C limit, for one module
load on boot `e1706072`.

This writes the DA9214 enable bit, SPM, the PWRAP reset and MCUCFG DCM, and makes the
secure SRAM-LDO call, for the first time beside live PMIC traffic. It changes no voltage
selector or clock. It is one load of `mt6797-a72.ko`, once, with no retry.

No new image is needed: boot `e1706072` runs package `db7b42af...`, whose module has
SHA-256 `1e13d34d...`. Copy that file to RAM on the running station and verify the hash.

Hypothesis: the load brings CPU8 and CPU9 online, and the station keeps working. Unique
observation: the sequence beside Wi-Fi, audio and PMIC users, on this kernel.

Before the load: the owner is present and can force power off; external power is stable;
Wi-Fi is associated and the fuel gauge and thermal zones are running as normal; a `dmesg
-w` from a second USB SSH session is logging to the host, so a hang still leaves a log;
and busybox `taskset` is confirmed present.

```sh
# Baseline, then the load, which blocks until done
for f in online offline; do echo "$f $(cat /sys/devices/system/cpu/$f)"; done
insmod /tmp/mt6797-a72.ko; echo "insmod=$?"
for f in online offline; do echo "$f $(cat /sys/devices/system/cpu/$f)"; done
cat /sys/devices/system/cpu/vulnerabilities/spectre_v2 /proc/sys/kernel/tainted
dmesg | grep -iE 'mt6797-a72|CPU[89]|conflict|SANITY|pwrap|Oops|WARNING'
for f in voltage_now temp status; do echo "$f $(cat /sys/class/power_supply/battery/$f)"; done
grep . /sys/class/thermal/thermal_zone*/temp; grep -E '^cpu[89] ' /proc/stat
# Finite load: 60 rounds per A72, counted rather than timed, in the background
for c in 8 9; do taskset -c $c sh -c 'i=0; while [ $i -lt 60 ]; do
  dd if=/dev/zero bs=1M count=64 2>/dev/null | sha256sum >/dev/null; i=$((i+1)); done' & done
# Every 10 s until both finish: SoC zone temperature. Then confirm no loop is left
```

Then check `/proc/stat` advanced on both A72s, repeat the PMIC reads, run the regression
(keyboard, USB SSH, Wi-Fi ping, audio tone), and leave it idle for 10 minutes with the same
reads at the end. Finish with one clean reboot to show that path, which has never run with
A72s up. `taint` `S` and a `SANITY CHECK` line about CPU feature differences are expected
with mixed cores, and are not by themselves a failure. So is `spectre_v2` turning
`Vulnerable`.

Stop rules: one load only, never retried. Stop the load loop and report at 75 C on the SoC
zone, a limit proposed here that the owner can change. Stop on unexpected heat, charging
anomalies, repeated filesystem errors or watchdog loops. No I2C tools on the new bus.

| Result | Meaning | Next |
| --- | --- | --- |
| `0-9`, PMIC reads fine, regression and reboot pass | Works on the station | Soak, then measure idle cost, then ask about loading at init |
| Load fails on the off-state or firmware check | No hardware changed | Read the logged value, no retry |
| Load fails before the isolation clear | Sequence undone, by source | Keep logs, no retry; a reboot is the clean state |
| Failure after the isolation clear | Rail left on with nothing to undo it | Keep logs, reboot, no retry |
| CPU8 rejected on a capability conflict | 0424 incomplete; the CPU parks | Read the log, fix, new boot |
| `CPU_ON` returns, core never arrives | Sequence differs from the proven runs | Stop, compare, no retry |
| PMIC errors after the window | 0426 insufficient | Stop, keep logs, reboot |
| A72s online, a later fault under load | Stability problem, the real unknown here | Stop, keep logs, no repeat until explained |
| `insmod` never returns, others still running | A CPU may be stuck in secure firmware, as CPU_ON is unbounded there | Save the log, reboot if it still can, else owner forces power off |
| Whole system hangs | Unknown | Watchdog to Gemian; if it does not fire, owner forces power off |

Recovery: the module is not in the image, so any reboot returns a station without it,
once the owner selects boot2. If the force-off path is needed, it is the owner's physical
action.

### Bring-up test, attempt 2 (owner-approved, run; see Observations)

The owner approved this on 2026-11-01. The same writes, steps, stop rules and table as attempt 1, on a new image with 0448,
compared with the module-free results above. One boot and one load, no retry. Changes:

Candidate: package `932520bc...` (job `7fc89f36...-mt6797-a53-station-a72-m1`, Buildbox-2),
Image.gz `0bb6ad36...`. Against `db7b42af...`: 0448 in the Image, and another session's
0447 in `snd-soc-mt6351.ko`. The configuration, the DTB (`91ca8aae...`), `mt6797-a72.ko`
(`1e13d34d...`) and every other module are identical.


- Before the load, `spectre_v2` and `spec_store_bypass` should read `Vulnerable`, and
  everything else as in the module-free boots.
- **Any new `WARNING` is now a failure**, as is an A72 going quiet: `/proc/stat` is read
  every 10 s from the load onward, and a CPU frozen for 15 s stops the test.
- Taint `S` was not seen in attempt 1, so it is reported rather than assumed.
- Workers are started by one shell that records their PIDs and `wait`s, and the temperature
  loop runs until that shell ends, because busybox shows them under other names.
- If an A72 stops again, go to `sync` and `reboot -f`. Plain `reboot` can block on RCU.

### Soak (owner-approved, run; see Observations)

The owner approved this on 2026-11-01 with the limits below, then asked for 30 min rather
than 4 h. It repeats the bring-up writes on a new boot and changes no voltage selector or
clock. One boot, one module load, no retry.

Candidate: the same package `932520bc...`, Image.gz `0bb6ad36...`, DTB `91ca8aae...`,
module `1e13d34d...`, so a result compares directly with attempt 2. No new build. Newer
audio and GNSS patches stay out on purpose. If boot2 no longer holds this image, reinstall
it under the standing boot2 approval.

Hypothesis: both A72s stay online and compute correctly for 30 min, with Wi-Fi, audio and
PMIC traffic running. This does not answer whether they last for hours, which still needs a
longer run before loading at init. Three observations attempt 2 could not give:

- **Duration:** 25 min of load, against 2 min, then 5 min of idle. Most of the time goes to
  load, because attempt 2 already had about 20 min online after its load.
- **Correct results:** attempt 2 discarded its hashes, so a wrong answer would not have
  shown. BUCKB's voltage on the pin has never been measured, so silent errors are the
  failure to look for. Each round now compares against one reference hash.
- **Concurrency:** load, Wi-Fi and audio at the same time, which has not run.

[`soak.sh`](soak.sh) runs from RAM on the device and stops itself, so it does not depend on
the host link. It hashes a 64 MiB random file in a loop on CPU8 and CPU9, and on CPU7 as an
A53 control, so a mismatch can be placed. Every 15 min it runs a ping, a finite download
and a tone. Logic checked in the dev VM with substituted CPU and sysfs paths: normal end,
temperature stop and hash mismatch all behaved. Not run on the device's busybox, and the
fault-line stop was not exercised, because the VM denies `dmesg`.

Before the load: the owner is present throughout and can force power off; USB power is stable; Wi-Fi is associated; a
`dmesg -w` from a second USB SSH session logs to the host; `tail -f /tmp/soak-load.log`
logs to the host; the module hash is verified on the device.

```sh
insmod /tmp/mt6797-a72.ko; echo "insmod=$?"; cat /sys/devices/system/cpu/online
export PING_TARGET=<gateway> WGET_URL=<finite file on a LAN host> TONE_CMD=<usual tone command>
/tmp/soak.sh load 1500; echo "load=$?"
# Only if load=0
/tmp/soak.sh idle 300; echo "idle=$?"
```

Run `load` and `idle` so that they outlive the SSH session. Afterwards: repeat the
registers and PMIC reads, read the Wi-Fi restart count, and have the owner confirm the
keyboard, display and one tone by ear. Finish with one clean reboot.

Stop rules, enforced by the script: SoC zone at 75 C, the owner's limit from the earlier
attempts; battery at 45 C, proposed here; capacity under 30%; a hash mismatch; an A72 quiet
for 10 s; `online` other than `0-9`; a taint change; any new `WARNING`, Oops, stall or
wrapper error line. No `end` line within 5 min of the deadline also counts as a stop. Then
keep the logs and go to `sync` and `reboot`, or `reboot -f` if an A72 stopped. No I2C tools
on the new bus.

| Result | Meaning | Next |
| --- | --- | --- |
| Both phases finish, regression and reboot pass | Stable for 30 min on one boot | Measure idle cost; a longer run comes before loading at init |
| Mismatch on an A72, none on CPU7 | Silent errors on the A72s at firmware's voltage and clock | Stop. Do not load at init. Explain before any repeat |
| Mismatch on CPU7 too | Memory or the file, not specific to the A72s | Keep logs, look at memory first, no repeat until explained |
| 75 C reached | Load needs cooling the station does not have for these CPUs | Record the curve. Cooling comes before loading at init |
| A72 frozen, or stall lines | The stability problem | Keep logs, no repeat until explained |
| New wrapper or PMIC errors | 0426 insufficient under long traffic | Stop, keep logs, reboot |
| New `WARNING` or Oops, taint change | Depends on the trace | Keep logs, read it, no repeat until explained |
| Wi-Fi restart or tone failure, A72s fine | Not attributed from one sample | Compare with the plain station before blaming the A72s |
| Capacity under 30% | Power budget, not a fault | Record the rate, recharge, then decide |
| Whole system hangs | Unknown | Watchdog to Gemian; if it does not fire, owner forces power off |

Recovery: as for the bring-up attempts. The module is not in the image, so any reboot
returns a station without it, once the owner selects boot2.

### Cluster map (owner-approved, run; see Observations)

The owner approved this on 2026-11-01.

The [topology run](../2026-09-02-mainline-mt6797-cpu-map/README.md) showed the kernel publishing
4+4+2 from this map on an isolated candidate. 0455 adds the same map to the A72 tree. It writes
no register and changes no clock. Compiled in the dev VM: the A72 DTB has 3 clusters and 10
cores with the right CPU nodes, and the plain station DTB has no map.

Candidate: package `976f9716...` (job `34c0e48d...-mt6797-a53-station-a72-m1`, Buildbox-2),
Image.gz `ac6be841...`, DTB `65fa07ba...`, module `1e13d34d...`, the same module as the soak.
The configuration is unchanged from `932520bc...`; the image also carries the audio and GNSS
patches 0449 to 0454. Its A72 DTB has the 3 clusters and 10 cores. A build authorizes no boot.

What it gives: with `CONFIG_SCHED_CLUSTER=y`, the scheduler should balance within a cluster
first, read from source and not yet seen on this profile. What it does not give: all CPUs
still have the same capacity, so Linux does not know that one cluster is slower than another.
Declaring capacity needs a measured basis, because the
[Gemian values](../../docs/hardware/gemini-gemian-baseline.md) are not to be used.

Hypothesis: on the A72 profile, `cluster_cpus_list` reads `0-3`, `4-7`, `8-9`, with the A72s
joining their cluster at load, and the station keeps working. Unique observations: the
domains on this profile with late A72s, and each cluster's single-CPU hash rate, the first
measured input for capacity. One boot and one module load, no retry.

```sh
grep . /sys/devices/system/cpu/cpu[0-7]/topology/cluster_cpus_list   # before the load
insmod /tmp/mt6797-a72.ko; echo "insmod=$?"
grep . /sys/devices/system/cpu/cpu*/topology/cluster_cpus_list
grep . /sys/devices/system/cpu/cpu*/topology/package_cpus_list
mount -t debugfs none /sys/kernel/debug
grep . /sys/kernel/debug/sched/domains/cpu[048]/domain*/name
# One CPU at a time, nothing else loaded: seconds for one 64 MiB hash, three each
dd if=/dev/urandom of=/tmp/rate.dat bs=1M count=64 2>/dev/null
for c in 0 4 8; do for i in 1 2 3; do
  s=$(cut -d' ' -f1 /proc/uptime); taskset -c $c sha256sum </tmp/rate.dat >/dev/null
  echo "cpu$c $s $(cut -d' ' -f1 /proc/uptime)"
done; done; rm /tmp/rate.dat
/tmp/soak.sh load 300; echo "load=$?"
```

Then the regression (keyboard, Wi-Fi, one tone) and one clean reboot. The soak's stop rules
apply.

| Result | Meaning | Next |
| --- | --- | --- |
| Cluster lists as above, load and regression pass | Map works with late A72s | Use the rates to decide on capacity |
| Lists flat, or only the A53 clusters are right | Parser or late-CPU path | Read the source, no repeat until explained |
| A fault after the load | New with the map, or the newer patches in this image | Compare with the soak, no repeat until explained |

### Step 1: ten cores beside A53 cpufreq (owner-approved, run; see Observations)

The owner approved this on 2026-11-07. One boot, one A72 module load, no retry.

Agreed with the cpufreq session on 2026-11-07: the A72 module loads first, then
`clk-mt6797-mcusys`, then `cpufreq-dt`; the clock-first order is forbidden. The clock
driver keeps the whole `0x10220744` word from its probe and faults if it changes, so it
must probe after CPU_ON. It reads no B-cluster field. Whether the firmware's CPU_ON path
takes DVFSP semaphore 3 is unverified, so no A53 rate change may overlap a B CPU_ON;
here CPU_ON happens before cpufreq-dt loads.

Candidate: the A53 cpufreq A3 package `395047bd...` (job `8996f539...-m1`), Image.gz
`b025af20...`, `mt6797-gemini-pda-station-a72.dtb` `30bdeff8...` (cluster map, `a72-power`
node, both A53 OPP tables), through `station-dt.sh` at `ba2c097a` or later;
`mt6797-a72.ko` `bf228fbc...` (same source as `1e13d34d...`, rebuilt in the newer tree),
`clk-mt6797-mcusys.ko` `8163e541...`, `cpufreq-dt.ko` `2c451b82...`, the cpufreq stage
script at `429a80d5` (`2df2cc04...`, which accepts CPU8-9 online), `cpu-mhz`, and
`soak.sh` `f3697965...`. No build.

Writes: the A72 module's, as admitted for the bring-up attempts, then the A53 cpufreq
record's A3 items 1-5, at stages t2, t3 and t6 only. Nothing new.

Hypothesis: all ten CPUs stay online while schedutil scales CPU0-7, the clock driver
never faults, and the A72 clock measures about 750 MHz. Unique observations: the A72
clock measured, and A53 scaling with the A72s online.

Stages, stopping at the first fault. Console blanking off first.

| Stage | What | Expected |
| --- | --- | --- |
| s0 | cpufreq script `t0`; `devmem 0x10220744 32` | online `0-7`; as A3 t0 |
| s1 | `insmod mt6797-a72.ko`; `devmem 0x10220744 32`; `cpu-mhz 8 5`, `cpu-mhz 9 5`; `cpu-mhz 8 hash` against t0's reference | online `0-9`, taint 0; both A72s near 750 MHz; hash equal. `0x10220744` before and after is recorded either way |
| s2 | script `t2`, then `t3` | as A3: two policies, CPU0-3 and CPU4-7; `cpu8 has no OPPs` and `cpu9`; online `0-9` |
| s3 | script `t6`, then `soak.sh load 600` under schedutil, then `cpu-mhz 8 5` | `t6` as A3; soak result 0; A72 clock unchanged; `faulted=0` |
| s4 | registers, PMIC read, keyboard and one tone, one clean reboot | as the soak |

Stop rules: both records' together. Any STOP from the cpufreq script, `faulted=1`, a
hash mismatch, CPU8 or CPU9 leaving `online`, a soak.sh stop, a new `WARNING`, Oops or
stall, or the SoC at 75 C. The A72s have no cooling; the 58 C passive trip cools the
A53s only.

| Result | Meaning | Next |
| --- | --- | --- |
| All stages pass | Ten cores work beside A53 cpufreq in this order | Step 2, down and up |
| `t2` or `t3` refuses, or the driver faults after `s1` | CPU_ON changed a word the clock driver keeps | Read `0x10220744`; the cpufreq session narrows the check; no repeat until fixed |
| A72 clock far from 750 MHz | Firmware state differs from the earlier reads | Record it; it changes step 4's table, not this result |
| A72 stops, or a hash mismatch | A72 or coherency fault beside scaling | Keep logs, `reboot -f` if needed, no repeat until explained |
| Bring-up failure in `s1` | As attempt 1's table | As attempt 1's table |

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

Boot-only test, boot `7dd24578`, image boot2 `e99adaa3...`, package `af871fff...`,
compared with plain boot `24465562`. Module absent from the root and not loaded; no I2C
tools on the new bus and no register writes. Evidence stays with the custodian's private
station work.

- **Handoff and I2C6:** `access_grant=ready` at 46.05 s, `1100e000.i2c` bound with zero
  clock validation failures. Existing buses kept their numbers; I2C6 is `i2c-2`, with a
  `2-0068` client and no driver or log line for it.
- **Registers:** `0x10006218`, `0x10006240`, `0x10006244`, `0x10006290` and `0x10222274`
  match the reading at both 62.89 s and 637.39 s. `0x10006188` and `0x1000618c` changed
  between those two reads (`003D8408`/`003D82FF`, then `003D8208`/`003DA0FF`), so their
  bits outside the A72 mask are live, whatever they mean. A72 bits 7:6 stayed off.
- **Regression:** USB SSH, keyboard, display and audio passed, untainted, no Oops or
  warning by the custodian's filter. **GNSS was not tested**, because it is not in this
  image. `spectre_v2` and `spec_store_bypass` stayed `Not affected`.
- **Finding 1, `/init` delayed 44 s (cause confirmed).** `probe of
  11015000.dvfsp-handoff returned 0 after 45270453 usecs`, and `/init` ran only then. The
  owner saw a frozen console with a cursor. The decision table had no row for this, and
  the record had claimed the opposite. Fixed in 0446, which has not booted.
- **Finding 2, one Wi-Fi fault at the first join (not attributed).** Authenticated at
  101.61 s, then `join stopped: status=-110 first=0 submitted=0x800` at 102.36 s and a
  driver restart, rejoined at 107.69 s; `udhcpc` had exited, so `wifi-up.sh` was rerun, and
  ping passed 5/5 twice. One sample. The same failure form appears in
  [older Wi-Fi records](../2026-10-13-mt6797-wifi-native-delivery-probe/TX_AUTORATE_RESULT.md)
  with no A72 code. No mechanism connects it to these changes, but this boot does not
  exclude one, so the next boot counts first joins.

Bring-up attempt 1, boot `e1706072`, package `db7b42af...`, module `1e13d34d...`. The
owner was present, 75 C limit, USB power. One load, no retry. Evidence stays with the
custodian's private station work.

- **Came online:** `insmod=0` in about 60 ms, `online 0-9`, `CPU8 and CPU9 online`, with
  both CPUs booted as `0x410fd081`. This is the first run of this sequence beside live
  PMIC traffic, and no PMIC error appeared by the custodian's filter.
- **Six warnings:** `update_mitigation_state` at `proton-pack.c:52`, from the v2, v4 and
  BHB callbacks on each A72. Taint `W`. `spectre_v2` still read `Not affected`.
- **Then both stopped:** by 1102 s their `/proc/stat` had frozen, and timer counts stayed
  at 11 and 12. Pinned workers stayed `R` without running a round, so **no load ever ran
  on an A72**. RCU reported stalls on 8 and 9 from at most about 1086 s, `softirq=8/8`,
  and the NMI gave no backtrace. The nesting field read `/1/0x4000000000000000`, so RCU
  saw them as not idle.
- **A53s kept going:** SSH, Wi-Fi ping 2/2, SoC at most 41.9 C. The custodian stopped
  there, so audio, keyboard and PMIC repeats did not run. Their temperature monitor had
  also stopped at 1104 s through a script fault, though nothing was loading the A72s.
- **Reboot:** a clean reboot blocked over 280 s in `umount`, presumably on RCU.
  `reboot -f` at 1482 s worked, and Gemian came up by itself as boot `4252396b`, with an
  ext4 journal recovery on its root. No force-off was needed.

Second boot-only test, boot `e1706072`, image boot2 `01280137...`, package `db7b42af...`.
Module absent; no I2C tools, no writes.

- **0446 works:** `Run /init` at 1.293 s, against about 1.25 s on plain stations and 46 s
  before. The handoff probe took 126 ms; `access_grant=ready` at 0.90 s and I2C6 bound.
- **Wi-Fi:** one first join, clean, ping 5/5 twice. Finding 2 stays one fault in two boots,
  one join each, which is too few to say anything about its cause.
- **Registers:** the same five match. `0x10006188` and `0x1000618c` moved again within the
  boot, so the bits above the A72 mask are live; what they mean is still unknown, and
  the module does not use them. A72 bits 7:6 read off.
- **Regression:** USB SSH, keyboard and audio passed, untainted, no Oops or warning by the
  custodian's filter. The owner saw no lag at startup. **GNSS is still untested on this
  profile**, because it is not in the image.

Bring-up attempt 2, boot `04cc38ee`, image boot2 `38116570...`, package `932520bc...`,
module `1e13d34d...` verified on the device. The owner was present, 75 C limit, not
charging at 95%. One load, no retry. Evidence stays with the custodian's private station
work.

- **Before the load:** `Run /init` at 1.216 s, `spectre_v2` and `spec_store_bypass` read
  `Vulnerable`, no `proton-pack.c` line, taint 0. One first Wi-Fi join, clean. Finding 2
  stays one fault in three boots, one join each.
- **Came online:** `insmod=0` at 1535.20 s, `online 0-9`, taint 0, no warning. Both CPUs
  booted as `0x410fd081`. The module's firmware recheck and probe took 36 ms in all.
- **Load:** 60 of 60 rounds on each A72, 1565.47 to 1686.06 s, with no `WARNING` and no
  frozen 10 s sample. Each CPU accounted about 113 s user and 7 s system by the end of
  the load, against none in attempt 1. SoC at most 43.9 C from 30.5 C; battery at most
  24.2 C.
- **After the load:** timer interrupts 30545 and 30493 on CPU8 and CPU9, against 11 and 12
  in attempt 1. PMIC read rc=0 with no wrapper error line. Ping 3/3.
- **Idle:** by 2882.40 s, 1347 s online with no event, 1196 s of it after the load. Taint
  0, no warning, and no match for `rcu_preempt detected|self-detected|Sending NMI`. Each
  A72's `/proc/stat` sums to the full 1347 s, nearly all of the rest idle. Ping 5/5 at
  2396.93 s. **This was not pure idle:** at the owner's choice, another session removed and
  reloaded the audio modules at about 2016 s and played tones during it. The load had
  already ended, and no load ran on an A72 afterwards.
- **Registers with the A72s up:** `0x10006218=00010127`, `0x10006290=00000000`,
  `0x10222274=0000000D`, `0x10006240` and `0x10006244` `00010337`, unchanged from 1710 s to
  2397 s. Bits 7:6 now read on in both `0x10006188` (`003F80C8`, then `003FA0C8`) and
  `0x1000618c` (`003D80FF`, then `003D90FF`); the bits above the mask moved again.
  `00010127` also appears with CPU8 up in the
  [first-cycle run](../2026-08-02-gemian-a72-first-cycle-latch/results/runtime-first-natural-pair-20260802.txt),
  in the field that reads `00010132` with it off. That the field is this register is
  inferred from those values.
- **Regression:** USB SSH and the host's log stream held from before the load to the
  reboot. The owner: "keyboard fine", and the tone at 1779.41 s "Heard in both ears". Five
  more tones on the audio tests returned rc=0. The display was not asked about, and
  **GNSS is still untested on this profile**, because it is not in the image.
- **Reboot:** plain `reboot` after stopping the workload and unmounting data, with no `-f`.
  `EXT4 ... unmounting` logged, and Gemian came up as boot `30f405b2`, reachable about 20 s
  later, with no journal recovery line by the custodian's filter. One clean reboot.
- **Not covered:** A72 load together with audio or Wi-Fi traffic, soak, idle battery cost,
  suspend, and any down path. Frequency and voltage were not measured on this run.

Soak, boot `20e1429e`, image boot2 `38116570...`, package `932520bc...`, module
`1e13d34d...`, `soak.sh` `f3697965...`. The owner was present, on USB. One load, no retry.
Both phases ended with result 0, and no stop rule fired.

- **Came online:** `insmod=0` at 87.37 s, `online 0-9`, taint 0. One first Wi-Fi join, clean.
- **Results:** every hash correct. 777 rounds on each of CPU8 and CPU9 and 779 on CPU7, over
  25 min, or about 1.93 s for 64 MiB. Each A72 accounted about 1494 s of the 1500 s as busy.
- **Traffic:** three rounds, at 95, 1002 and 1595 s. Ping 5/5, a 4 MiB download over Wi-Fi and
  a tone, all succeeding each time. Restarts 0 at the end.
- **Temperature:** the SoC zone rose from 31.1 C to 45.5 C after a minute and 51.0 C after
  8 min, then stayed between about 51 and 52.5 C, sampled every 60 s, until the load ended.
  It fell to 38 C within a minute and 34.9 C by the end of idle. The hardware reset stayed
  armed at 117 C. This load kept three CPUs busy, not ten, so it is not a worst case.
- **Battery:** the status read `Discharging` under load while the owner's charge guard held
  charging off. Capacity read 85 to 89% under load and 92% after, tracking voltage (4.11 to
  4.19 V, then 4.26 V), so these readings do not give a power figure. The temperature read
  flipped between about 15.5 C and 25 C in both phases, as before on this gauge; no limit
  was near either value.
- **After, at 1915 s:** `online 0-9`, taint 0, no warning, stall or wrapper error line, PMIC
  read rc=0, no `wget` left. Registers as in attempt 2, except for the moving bits above the
  A72 mask (`0x10006188=003F84C8`, `0x1000618c=003D80FF`).
- **Regression:** the owner answered "Fine" for keyboard and display, and heard a tone at
  1970.20 s in both ears. **GNSS is still untested on this profile.**
- **Reboot:** plain `reboot` at 1989.56 s, with `EXT4 ... unmounting` logged. Gemian answered
  about 36 s later as boot `220a19fa`, with no journal recovery line by the custodian's
  filter. That is two clean reboots with the A72s up.
- **Finding 2 update:** first-join faults on this kernel family stand at 2 of 5 boots, by the
  custodian's count: `7dd24578` and `c09fb418`, the second with the A72 module not loaded and
  the first before it. So the module load is not the cause. Whether the profile's boot-time
  changes matter is still open, because no plain-station count is available to compare.

Cluster map, boot `5895e1f1`, image boot2 `d1a882db...`, package `976f9716...`, module
`1e13d34d...`. The owner was present. One load, no retry. `station-dt.sh` first refused this
tree, because the map moved a phandle it held as a literal; fixed in `ba2c097a` with
byte-identical output on the trees it already accepted.

- **Topology:** `cluster_cpus_list` read `0-3` and `4-7` before the load. After `insmod=0` at
  122.73 s, CPU8 and CPU9 read `8-9`, with the A53 lists unchanged. `package_cpus_list` read
  `0-9` on all ten.
- **Scheduler domains not read:** debugfs was already mounted, so the mount returned busy,
  and `sched/domains` was absent. By source, that directory exists only with
  `sched/verbose` set. So balancing inside a cluster first is still read from source, not
  seen.
- **Single-CPU rate, one at a time, 64 MiB, three runs each:** CPU0 about 2.55 s, CPU4 about
  1.81 s, CPU8 about 1.93 s. Relative to CPU4: CPU0 0.71, CPU8 0.94.
- **Load, 300 s:** result 0, all hashes correct, CPU7 164 rounds, CPU8 and CPU9 154. SoC 44.5
  to 48.4 C. Ping, download and tone succeeded. CPU7 took about 1.83 s a round here and about
  1.93 s over the 25 min soak; the A72s took about 1.95 s and 1.93 s. Not explained, and the
  images differ.
- **After:** `online 0-9`, taint 0, no warning, stall or wrapper error line, restarts 0, one
  clean first join, so finding 2 stands at 2 of 6 boots. Registers as in the soak, except the
  moving bits above the A72 mask (`0x1000618c=003D82FF`).
- **Regression and reboot:** the owner confirmed the keyboard and a tone. Plain `reboot`,
  Gemian about 32 s later as boot `1b08f05b`.

Step 1, boot `f50ee883`, image boot2 `a101d944...` (package `395047bd...` with the A72
tree), modules and tools verified on the device. The owner was present. One A72 load, no
retry.

- **Order held:** t0 passed with `online 0-7`. `insmod=0` at 120.9 s, `online 0-9`, taint 0,
  and `0x10220744` read `00070707` before and after, so CPU_ON did not change the word the
  clock driver keeps. Its t2 then bound with the A3 floors and PLL readings.
- **A72 clock, measured:** CPU8 750 MHz and CPU9 748 MHz, hashes equal to the A53
  reference. After the soak, both read 750 MHz. The first measurement of it; earlier values
  were read from registers.
- **Shared words the bring-up changed:** against A3's t2, `muxsel` `0x55` (`0x54`), `ckdiv`
  `0x8` (`0x0`) and TOPCKGEN `clk_misc_cfg_0` `0x01ff0000` (`0xffff0000`). The cpufreq session
  confirmed none of these is a field its driver reads or writes.
- **t3 stopped on a log line:** cpufreq-dt logs `failed to find data for cpu8` (and cpu9)
  when the core offers it the already-online A72s, and returns `-ENODEV`. The script
  matched `failed`. Everything else in t3 matched A3: policy0 CPU0-3, policy4 CPU4-7, L at
  1209 MHz, hashes equal, `faulted=0`. The run continued on the same boot after `57178716`
  excluded exactly that line and moved the LL measurement off CPU0, which read 843-874 MHz
  with Wi-Fi and the log reader on it while CPU3 read 897.
- **Scaling with ten online:** t6 passed: schedutil moved policy0 over 221-897 MHz and
  policy4 over 832-1209 MHz through idle, load and idle, with every hash correct on CPU0-7.
- **Load, 600 s under schedutil:** result 0, every hash correct, CPU7 311 rounds, CPU8 and
  CPU9 309. SoC at most 51.6 C. About 7700 PLL changes in all by the end, `faulted=0`, and
  `0x10220744` still `00070707`. Ping, download and tone ran.
- **After:** `online 0-9`, taint 0, no warning, Oops, stall or wrapper error line, Wi-Fi
  restarts 0 with one clean first join (finding 2 at 2 of 7). The keyboard worked. The tone
  was heard only after the custodian switched the speaker route on, so `soak.sh`'s tone
  result shows that playback ran, not that it was audible.
- **Power-off:** clean, with the data partition unmounted. A plain reboot now lands in
  Gemian on this device, so this replaced the reboot.

Package `eff98241...` (job `e1add137...-m1`, Buildbox-2) built and linked the module and
the Image with the earlier version of the options. It is an audit input, and superseded
for booting because the plain station no longer carries these options.

Package `e1eeb6a7...` (job `f33b84a6...-mt6797-a53-station-a72-m1`, Buildbox-2) is the
opt-in profile: Image.gz `42b794d6...`, the module, and
`mt6797-gemini-pda-station-a72.dtb`, with its checksums passing. A build authorizes no
boot.

## Analysis

**Why the A72s stopped (derived from source, fits every log above, and attempt 2 fits the
fix).** Only 0448 changed in the Image, and the warnings and the stop both went away, so the
fix is observed; the mechanism below is still read from source, not traced. This was a defect in 0424, and the design text above was wrong to say the
capability bits were all the A72s need:

1. After capabilities are final, `update_mitigation_state()` warns and refuses any change.
   That is the six warnings, and why `spectre_v2` stayed `Not affected`.
2. `spectre_bhb_enable_mitigation()` gives up only if Spectre-v2 reads vulnerable. It read
   unaffected, so an A72 went on and selected `EL1_VECTOR_BHB_LOOP`.
3. That vector's loop runs `mov x30, #max_bhb_k` then counts down to zero. The immediate is
   patched at boot, when only A53s had been seen, so it is 0. The count wraps, and the
   loop runs about 2^64 times with interrupts masked.
4. Kernel exceptions use other vector entries, so an A72 kept working until its first entry
   from userspace. That fits about a second of life, the not-idle RCU state, no
   interrupts, no NMI backtrace, and sshd dropping when it landed there.

The old stack avoided this because it recorded these states as vulnerable before
finalization, which this design dropped as unnecessary.
[0448](../../patches/proposals/0448-arm64-record-the-late-MT6797-A72s-as-vulnerable-at-b.patch)
does the same in three lines. The system then reports `Vulnerable` from boot, including
on the A53s, which are themselves unaffected. The kernel cannot report per-CPU here.

The bring-up sequence itself gave no sign of trouble. Attempt 2 is a first answer on
stability: two minutes of load and about twenty minutes online, on one boot and one unit.
It says nothing yet about hours of use, cold boots or load beside other traffic.

**What the A72s add at this clock (inferred).** They hashed at the same rate as CPU7, an A53.
That is not a sign of a fault. Earlier runs read B at 750 MHz and L at 1274 MHz, a ratio of
1.7, and an A72 doing more per clock could close that gap. At about 33 MiB/s this hash is
probably limited by the core rather than by memory. Neither clock was measured on this run,
and one integer workload says little about others. So today the A72s add two more CPUs of
about A53 speed for this work, and no faster one. A faster A72 needs clock and voltage
writes, which are outside this work and need their own protocol.

**What the clusters look like to the work (inferred).** CPU0's rate against CPU4's, 0.71, is
close to 897/1274 = 0.70, the clocks read on earlier runs. That fits two A53 clusters running
the same way at those clocks, though no clock was read here. All ten CPUs still count as equal
to the scheduler, so a heavy task on CPU0-3 runs about 30% slower than it could, and the map
does not change that. The
capacity binding, `Documentation/devicetree/bindings/cpu/cpu-capacity.txt`, takes
direct values when there is no cpufreq, so measured figures of about 727, 1024 and 960 could
express this. They rest on one integer workload, and would need replacing once cpufreq exists.

The project's [2026-10-03 review](../2026-10-03-project-review/README.md) parked
this work because it had consumed the most effort for the least usability, and
because it waited on measurement contracts. The change since then is the
station's own thermal protection and the owner's request. The old method tried to
prove each effect before the next, which is why it grew. The method here takes
those results as given and stops at what the cores need.

## Conclusion

All ten cores can run on the station kernel: the opt-in `mt6797-a53-station-a72` profile
brought CPU8 and CPU9 online from a module on two boots. They returned correct results for
25 min beside Wi-Fi and audio traffic, and the station rebooted cleanly. This is one unit,
loaded by hand, at firmware's B clock. It is not default integration: PWRAP concurrency,
runs of hours and idle cost stay open, all ten CPUs have not been loaded at once, GNSS has
not run beside it, and the whole system now reports
`Vulnerable` for Spectre-v2 and speculative store bypass.

## Follow-up: full support before loading by default

The owner's goal, 2026-11-07: support the A72s fully, then load them by default. Since the
last run, [A53 cpufreq](../2026-11-07-mt6797-a53-cpufreq/README.md) passed with the A72
module unloaded, and its patch 0643 keeps CPU8-9 out of cpufreq. In order, each step its
own boot request and owner decision, and each new register or regulator write listed
literally first:

1. **Ten cores beside A53 cpufreq, and the A72 clock.** Passed on one boot, see Step 1. The A72 bring-up is a one-way
   sequence at module load, and `clk-mt6797-mcusys` faults if sync DCM changes after its
   probe. So the load order is the A72 module first, then the clock driver, then
   cpufreq-dt, and the clock driver stays the only MCUMIXED writer in Linux. Settled with
   the cpufreq session before any request. The same run measures CPU8's clock with that
   experiment's `cpu-mhz` tool; 750 MHz has only been read, never measured. No new write.
2. **Down and up.** CPU9 down and back is proven on isolated candidates; both A72s down,
   and the cluster power after it, never ran on mainline. Needed for thermal emergencies,
   and so CPU_ON's firmware path (which programs the B PLL) can be coordinated with the
   clock driver. First CPU9, then both with the rail left on.
3. **Idle cost.** On battery, A72s online against offline on one image, using step 2.
   The fuel gauge reads 0 on USB, so this needs unplugged runs.
4. **A72 cpufreq.** First frequency only, at the 1.0 V the preloader left, within the
   vendor's points for that voltage, through the secure BigiDVFS interface firmware owns
   for the B PLL. Then voltage through a writable DA9214 BUCKB provider and the SRAM LDO,
   each with its own write list. This is the largest step and has its own record.
5. **Cooling on the A72s.** Follows from step 4 as cpufreq cooling on the passive trip.
   Until then the A72s have only the 117 C hardware reset, and step 1's loads stay short.
6. **Capacity and energy model.** `capacity-dmips-mhz` scales by each CPU's clock, and the
   A72s have none, so capacity waits for step 4 (or a fixed clock on the A72 nodes). The
   energy model needs measured power per point, using step 3's method.
7. **Long soak under heat,** all ten loaded, with cooling.
8. **Suspend and resume.** The station suspends with s2idle only, so the A72s stay online
   in WFI and no hotplug is needed. One s2idle cycle with them online, then several.
9. **Loading at init,** in step 1's order, once the above pass.

Open beside these: PWRAP concurrency during the bring-up window, the system reporting
`Vulnerable` for Spectre-v2, and Wi-Fi finding 2 (2 of 6 first joins).
