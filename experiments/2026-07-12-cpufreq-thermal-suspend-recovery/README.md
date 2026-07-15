# Experiment: Gemini CPU DVFS, thermal, idle, and suspend recovery

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-12-cpufreq-thermal-suspend-recovery` |
| Status | `inconclusive` for mainline runtime support; live policy and resource contracts captured |
| Subsystem | MT6797 CPU DVFS, thermal zones, cpuidle, PSCI, and suspend/power management |
| Device variant | Gemini PDA running Gemian; exact retail sub-variant not independently established |
| Date(s) | 2026-07-12 through 2026-07-14 |
| Investigator(s) | Repository maintainer with Codex assistance |
| Tracking issue | None |

## Question or hypothesis

Which parts of the Gemini's CPU, thermal, idle, and suspend behavior can use
generic Linux 7.1.3 facilities, and which depend on MT6797-specific silicon,
PMIC calibration, or vendor firmware?

The working hypothesis is to retain generic PSCI and CPU topology support, but
not enable CPU OPPs, thermal trips, deep idle, or suspend until their exact
register, regulator, calibration, and firmware contracts are independently
recovered.

## Provenance and environment

- Live kernel: Linux `3.18.41+`, AArch64, Gemian Debian 9 userspace.
- Live device: `gemini@192.168.1.50` over the owner's private LAN.
- Vendor source: Gemian MT6797 tree commit
  `d388d350cb2dda8f23b99be6fa5db9628896e87f` and Planet MT6797 tree commit
  `c5b0be85017ad0c599725e8273842efdbecdd88a`.
- Mainline comparison: Linux `7.1.3` in the development VM.
- Sanitized summary: [`results/runtime-summary.txt`](results/runtime-summary.txt).
- Historical 46-patch build: [`results/mainline-build.txt`](results/mainline-build.txt).
- Historical PM build/provenance result (before the retained-LK reservation
  correction):
  [`results/mainline-pm-current-validation.txt`](results/mainline-pm-current-validation.txt).
- Current 72-patch package provenance:
  [`../2026-07-13-kernel-integration/results/mainline-72-patch-current-20260714.txt`](../2026-07-13-kernel-integration/results/mainline-72-patch-current-20260714.txt).
- Current 72-patch CPU/DVFS/thermal/idle package boundary:
  [`results/mainline-pm-current-72-package-20260714.txt`](results/mainline-pm-current-72-package-20260714.txt).
- CPU-DVFS source-contract validation:
  [`results/mainline-cpufreq-source-validation.txt`](results/mainline-cpufreq-source-validation.txt).
- EEM/PTP calibration contract:
  [`results/eem-calibration-contract.md`](results/eem-calibration-contract.md).
- Mainline cpufreq/DTS API gap:
  [`results/mainline-cpufreq-dt-gap.md`](results/mainline-cpufreq-dt-gap.md).
- Fresh bounded vendor CPU-policy capture:
  [`results/runtime-cpu-policy-20260714.txt`](results/runtime-cpu-policy-20260714.txt).
- Source-contract analyzer and mainline boundary: [`results/mt6797-pm-mainline-design.md`](results/mt6797-pm-mainline-design.md).
- Android power-HAL static boundary: [`results/power-hal-elf-audit-20260714.txt`](results/power-hal-elf-audit-20260714.txt).
- Android thermal/lights-HAL static boundary: [`results/android-thermal-lights-hal-audit-20260714.txt`](results/android-thermal-lights-hal-audit-20260714.txt).
- Private raw captures, if regenerated, belong only under the Git-ignored
  `artifacts/device-inventory/20260712-live/` or
  `artifacts/device-inventory/20260713-live/` directories. The current EEM/PTP
  capture is `20260713-live/eem-ptp.txt` and contains calibration diagnostics.

## Safety assessment

The collector is read-only. It reads `/proc`, CPU and thermal sysfs, power
supply metadata, cpuidle state counters, `/sys/power` metadata, interrupts, and
filtered kernel messages. It never changes a governor, frequency, voltage,
thermal mode, CPU online state, cpuidle state, suspend state, or PMIC register.
It does not write `mem`, freeze the device, or exercise a DVFS transition.

## Associated code

Run from the repository root:

```sh
mkdir -p artifacts/device-inventory/20260712-live
ssh -i artifacts/credentials/gemini_ed25519 \
  -o IdentitiesOnly=yes -o IdentityAgent=none -o BatchMode=yes \
  gemini@192.168.1.50 'bash -s' \
  < experiments/2026-07-12-cpufreq-thermal-suspend-recovery/scripts/collect-live-cpufreq-thermal.sh \
  > artifacts/device-inventory/20260712-live/cpufreq-thermal.txt
chmod 700 artifacts/device-inventory/20260712-live
```

The output must remain below the ignored `artifacts/` tree. Review it before
sharing: governor tunables and thermal-zone names can disclose device policy.

The CPU-policy-only capture uses the same key-only SSH path and reads only the
vendor `/proc/cpufreq` policy files, CPU masks, and filtered existing dmesg:

```sh
mkdir -p artifacts/device-inventory/20260714-live
ssh -i artifacts/credentials/gemini_ed25519 \
  -o IdentitiesOnly=yes -o IdentityAgent=none -o BatchMode=yes \
  gemini@192.168.1.50 'bash -s' \
  < experiments/2026-07-12-cpufreq-thermal-suspend-recovery/scripts/collect-live-cpu-policy.sh \
  > artifacts/device-inventory/20260714-live/cpu-policy.txt
chmod 600 artifacts/device-inventory/20260714-live/cpu-policy.txt
```

The source-only comparison runs in the development VM and reads the immutable
Planet and Gemian vendor Git objects plus the prepared Linux 7.1.3 tree:

```sh
./experiments/2026-07-12-cpufreq-thermal-suspend-recovery/scripts/analyze-mt6797-pm-contract.sh
```

It records source hashes and bounded register/firmware anchors without
copying vendor source or exercising the device.

The current packaged-kernel boundary is audited read-only in the VM:

```sh
./scripts/dev-vm run bash -lc \
  'CURRENT_PACKAGE=/home/julien.guest/artifacts/gemini-pda/linux-7.1.3-gemini-c2d9eea95daa \
   experiments/2026-07-12-cpufreq-thermal-suspend-recovery/scripts/audit-current-package-pm.sh'
```

## Procedure

1. Confirm the key-only, noninteractive SSH path with `BatchMode=yes`.
2. Run the collector once while the device is idle; do not change policies or
   take the device through suspend.
3. Compare the live policy/zone topology with the vendor DVFS and SPM source,
   then compare the resource names with Linux 7.1.3.
4. Treat all invalid temperature sentinels and zero deep-idle counters as
   observations, not as proof that the sensors or firmware are broken.

## Observations

- The live kernel exposes CPUs 0--9 as possible, with CPUs 0 and 1 online at
  capture. CPU0's vendor `mt-cpufreq` driver reports related CPUs 0--3 and a
  16-entry 221--1547 MHz LITTLE-cluster table. The policy uses the `interactive`
  governor and reports a 1 us transition latency.
- A fresh read-only capture confirms that the vendor policy is not represented
  through standard `cpufreq/policy*` sysfs directories: the active interface is
  the private `/proc/cpufreq` tree. At capture, only CPUs 0 and 1 were online
  while all ten CPUs were present/possible. The four policy tables remain
  16-entry tables; instantaneous states were LL 1014 MHz (OPP 8), L 325 MHz
  (OPP 15), B 845 MHz (OPP 13), and CCI 611 MHz (OPP 9), with vendor per-cluster
  Vproc/Vsram values. Existing dmesg shows live LL/L/B/CCI transitions, so this
  is an active dynamic policy rather than static boot metadata. A previous
  bounded probe observed CPU 4 online, demonstrating that the online mask is
  dynamic and must not be copied into the mainline topology.
- The Planet MT6797 source snapshot contains the complete CPU DVFS path, not
  only headers: `mt_cpufreq.c`, the hybrid/DVFSP implementation, EEM/PTP, and
  the MT6797 PLL provider are present. It implements three DVFS clusters (LL,
  L, and B) plus CCI, with efuse/date-code-selected frequency/voltage tables,
  DA9214/ext-buck and SRAM tracking, direct PLL/mux programming, frequency
  hopping, and CCI coupling. The hybrid path embeds a PCM instruction array
  and maps CSPM at `0x11015000` plus CSRAM at `0x0012a000`; it is not a generic
  Linux firmware interface.
- Table selection uses function-code efuse index 22, date-code efuse index 61,
  four CPU levels, and a B-cluster TT-segment override. The source enforces
  `Vsram >= Vproc`, a 10--30 mV tracking window, and 1000--1200 mV SRAM limits
  while sequencing the external buck. These inputs must be recovered before
  any mainline frequency transition is attempted.
- The Planet EEM/PTP source contains an active calibration-to-cpufreq path.
  BIG/L/2L/CCI detectors use banks 0/3/4/5 and INIT01/INIT02/MON phases to
  produce mutable 16-entry voltage tables, then apply thermal offsets, bounds,
  safety caps, and rollback before calling the vendor voltage-update hooks.
  The EEM window at `0x1100b000` is shared with the thermal controller; the
  current read-only capture observed all four CPU detectors enabled, while raw
  calibration values remain private.
- The vendor SPM v2 implementation is a second, distinct firmware boundary:
  `mt_spm.c` maps the vendor `mediatek,sleep` block and several MT6797 clock,
  efuse, thermal, DDRPHY, and vcorefs nodes, and can load dynamic PCM images
  through `request_firmware`. The MT6797 vcorefs path also contains an embedded
  PCM image. `mt_idle_mt6797.c` gates dpidle/soidle/mcidle on multimedia clock,
  power-domain, and PLL status, while the dpidle hooks toggle PMIC-wrapper and
  26 MHz clock state. These are not generic PSCI idle states and must not be
  enabled by naming the vendor states alone.
- Thirteen vendor thermal zones are enabled as names and trip tables but report
  `mode=disabled` in the captured sysfs view. Several readings use vendor
  invalid sentinels such as `-127000`, `-275000`, or `2` millidegrees Celsius.
  Both historical trees contain the common thermal-zone sources and the
  MT6797 controller source. The complete vendor source is used as evidence,
  not copied into this repository.
- cpuidle exposes vendor `dpidle`, `SODI3`, `SODI`, `MCDI`, `slidle`, and `rgidle`
  states. Only `rgidle` had non-zero usage in the sample. The vendor DT uses
  PSCI suspend parameters `0x0010000` and `0x1010000`, while mainline currently
  carries only the generic PSCI node and no idle-state description.
- `/sys/power/state` reports `freeze mem`; no suspend attempt was made. The
  vendor source contains extensive MT6797 SPM/PCM code and PMIC-wrapper hooks,
  including the dynamic/embedded PCM paths and clock/PLL gating described
  above, so generic `mem` support cannot be inferred from the string alone.
- The current 7.1.3 package selects generic CPU/PM/thermal frameworks and
  packages SVS, AUXADC, and generic MediaTek cpufreq helpers, but has no MT6797
  cpufreq symbol, no CPU OPP or idle-state table, and no enabled thermal/AUXADC
  node. This records the built-in safety boundary; no frequency, voltage,
  thermal, idle, or suspend transition was attempted. See the [current PM
  package audit](results/mainline-pm-current-72-package-20260714.txt).

## Linux 7.1.3 comparison

Linux 7.1.3's generic PSCI and ARMv8 CPU support can describe the ten-core
topology. Its MediaTek cpufreq driver matches a fixed list of other SoCs, has
no `mt6797` match, and expects CPU/intermediate clocks, PMIC regulators, and
standard OPP tables. Its voltage-tracking and clock-reparenting sequence is a
useful framework, but the vendor MT6797 clock, calibration, CCI, and external
buck contract still needs a dedicated variant/backend. Its MediaTek AUXADC
thermal driver has no `mt6797-thermal` match, and the MT6797 vendor thermal
compatible is `mediatek,mt6797-therm_ctrl` with a different one-clock contract.
Mainline has no MT6797 DVFSP/SPM driver or binding. Its newer MediaTek SVS
driver provides a reusable phase/error and mutable-OPP pattern, but no MT6797
match and no interchangeable EEM register or calibration contract.

The current Gemini DTS patch only supplies static `clock-frequency` boot hints;
it has no CPU/intermediate clock handles, `proc`/`sram` supplies,
`operating-points-v2` tables, CCI phandle, or MT6797 cpufreq machine data. The
exact API/DT gap is recorded in the [cpufreq/DTS result](results/mainline-cpufreq-dt-gap.md).

The evidence supports a disabled-only resource description for the MT6797
thermal controller, but not enabling it, adding guessed OPP voltages, or copying
the vendor PCM firmware. The DVFSP register/IRQ observations remain in the
experiment, while patch 0065 removes its disabled DTS candidate because Linux
has no driver or binding for that compatible. A future driver may be new if
register-level and calibration evidence establishes a different chipset
contract; it must still keep unsafe transitions disabled by default.

## Analysis

The live frequency table is useful for identifying the populated LITTLE policy,
but it is not a board OPP table: the vendor selects among multiple silicon
segments and date-code tables and can rewrite voltage values through efuse/PTP
calibration. The complete source makes a new MT6797 cpufreq backend a credible
option when the PLL, regulator, and calibration protocol is proven; it does not
justify copying the downstream table or making the generic driver emulate the
vendor ABI. Mainline's OPP/regulator voltage-tracking and clock-reparenting
framework remain reusable above that backend.

The live thermal zone policy being disabled makes it unsafe to convert the trip
values directly into a mainline thermal zone. The SPM deep-idle states also
rely on secure firmware and vendor PCM sequencing, so generic PSCI state names
cannot establish wakeup or rail safety.

The extracted Android power HAL does not change that conclusion: its callbacks
only log Android hints and do not access cpufreq, thermal, regulator, or
sysfs/procfs interfaces. It is a compatibility shim, so the kernel/firmware
policy—not the HAL callback names—remains the authoritative reverse-engineering
target.

## Conclusion

`inconclusive`: generic CPU topology/PSCI is reusable, but no safe mainline
MT6797 cpufreq, thermal, deep-idle, or suspend implementation has been proven.
The current patch boundary keeps the thermal candidate disabled and defers the
undocumented DVFSP node through [patch 65](../../patches/v7.1.3/0065-arm64-dts-mediatek-mt6797-defer-undocumented-dvfsp.patch);
patch 46 remains the historical source of the recovered register/IRQ evidence.
The source-level comparison and future-driver boundary are recorded in the
[mainline design result](results/mt6797-pm-mainline-design.md).

## Follow-up

1. Correlate the live CPU cluster masks, regulator consumers, and efuse/PTP
   calibration outputs with a controlled read-only source/register experiment.
2. Recover the thermal-controller register layout, AUXADC calibration cells,
   and sensor-bank mapping before proposing a new mainline thermal driver.
3. Determine whether the platform firmware implements the vendor PSCI idle
   parameters on the Gemini; begin with WFI/PSCI CPU bring-up only.
4. Add OPPs, thermal trips, DVFSP, or deep-idle patches only after a bounded
   runtime test plan and explicit stop/recovery conditions exist.
