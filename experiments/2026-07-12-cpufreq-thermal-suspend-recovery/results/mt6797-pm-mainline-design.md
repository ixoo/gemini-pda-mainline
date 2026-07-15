# MT6797 power-management boundary for Linux 7.1.3

## Result

The Gemini can reuse the generic ARM64 CPU topology and PSCI plumbing, and a
future MT6797 cpufreq implementation can reuse Linux's OPP/regulator and clock
transition helpers. The complete vendor MT6797 CPU-frequency, thermal, DVFSP,
and deep-idle paths are not a drop-in match for Linux 7.1.3: the CPU path
directly couples cluster-specific ARM PLL/mux registers, efuse/date/segment
selection, calibrated PMIC rails, CCI changes, and private SPM PCM firmware.
A chipset-specific cpufreq or thermal variant/driver is therefore a valid
future outcome if the recovered register protocol proves it is needed;
making the nearest generic driver emulate the vendor ABI is not.

No new runtime power-management patch is proposed by this experiment. The
series remains limited to the disabled-only thermal and DVFSP resources in
[patch 46](../../../patches/v7.1.3/0046-arm64-dts-mediatek-mt6797-add-disabled-thermal-dvfsp-resources.patch).

## Reproducible provenance

- Vendor source: Gemian MT6797 kernel commit
  `d388d350cb2dda8f23b99be6fa5db9628896e87f`.
- Linux source: prepared `7.1.3` tree in the development VM. The tree is
  generated from the pinned manifest rather than treated as a repository
  input; the analyzer records vendor Git blob IDs and Linux per-file SHA-256
  values.
- Re-run from the repository root in the VM:

  ```sh
  ./experiments/2026-07-12-cpufreq-thermal-suspend-recovery/scripts/analyze-mt6797-pm-contract.sh
  ```

The analyzer reads Git objects and source text only. It does not copy vendor
files, load firmware, access device registers, or exercise a DVFS, thermal,
idle, or suspend transition.

## Recovered vendor contracts

### CPU frequency and voltage

The Planet source snapshot contains the complete MT6797 implementation in
`mt_cpufreq.c`, `mt_cpufreq_hybrid.c`, `mt_eem.c`, `mt_eem2.c`, and the
MT6797 PLL provider. It has three CPU clusters (LL, L, and B) plus a CCI path.
The driver selects frequency/voltage tables using function-code efuse index 22
and date-code efuse index 61, with four CPU levels and a B-cluster TT-segment
override. It uses DA9214/external-buck and SRAM voltage tracking, writes
cluster-specific ARM PLL/mux registers directly, and includes frequency
hopping, PTP/EEM callbacks, and hotplug coupling. The resulting table is
silicon- and calibration-dependent, not a board OPP table that can safely be
transcribed into `operating-points-v2`.

The recovered PLL windows are LL `0x200/0x204/0x208`, L
`0x210/0x214/0x218`, CCI `0x220/0x224/0x228`, and a backup PLL window at
`0x230/0x234/0x238`; the B cluster uses a special BigiDVFS path. The divider
mux/select registers are `0x270` and `0x274`. The external-buck path enforces
`Vsram >= Vproc`, a 10--30 mV
difference, 1000--1200 mV Vsram limits, and bounded settle delays. A mainline
driver must prove these values against the actual PMIC and clock providers;
the live 16-entry tables are evidence, not defaults.

The vendor accessors route the ARM PLL reads/writes through
`mt6797_0x1001AXXX_reg_read/write/set()` rather than a normal Linux CCF rate
change. This is an important reuse boundary: a future driver may use the
mainline MT6797 PLL provider only after read-only comparison proves that its
register ownership and mux sequencing cover the vendor path. The companion
frequency-hopping source shows that this wrapper takes a DVFSP/CSPM hardware
semaphore shared with SPM and ATF; B-cluster PLL/SRAM operations use secure
BigiDVFS calls instead of ordinary MMIO. The resulting dedicated-provider
boundary is documented in the [MT6797 CPU clock backend result](../../2026-07-12-mt6797-clock-power-reset-recovery/results/mt6797-cpu-clock-backend.md).

### EEM/PTP calibration and mutable OPPs

The vendor EEM implementation is active calibration logic, not just a debug
block. Four CPU detectors (BIG bank 0, L bank 3, 2L bank 4, and CCI bank 5)
run INIT01/INIT02/MON phases. INIT02 reads eight hardware voltage anchors and
interpolates a 16-entry table; MON reapplies thermal offsets, detector offsets,
VMIN/VMAX clamps, and per-frequency `recordTbl` caps before calling
`mt_cpufreq_update_volt*()`. A detector error or explicit disable restores the
default table. The EEM register window is `0x1100b000 + 0x1000`, shared with
the vendor thermal-controller node, with a separate EEM IRQ and MFG/power
clocks. The shared resource must be represented before either driver is
enabled.

Linux 7.1.3's MediaTek SVS driver is the closest architectural reuse: it has
the same phase/error shape, thermal offsets, NVMEM calibration inputs, default
voltage rollback, and `dev_pm_opp_adjust_voltage()` integration. Its match
table is limited to newer SVS SoCs and has no MT6797 entry; its register,
efuse, and clock/reset contract is not interchangeable with MT6797 EEM. Reuse
the SVS/OPP pattern where it fits, but implement an MT6797 EEM variant or a
separate provider rather than copying another SoC's tables.

The optional hybrid path is a second protocol: it maps CSPM at
`0x11015000`, maps 12 KiB of CSRAM at `0x0012a000`, and runs an embedded PCM
instruction array from `mt_cpufreq_hybrid_fw.h`. Its timeout and command
semantics are not a Linux firmware interface.

### Thermal and AUXADC

The vendor thermal controller uses compatible
`mediatek,mt6797-therm_ctrl`, an MT6797-specific bank/sensor layout, and a
global thermal interrupt. Its calibration path extracts fields from efuse
windows around `0x10206180`--`0x10206188`, including gain/offset, slope, and
four sensor offsets. The controller programs AUXADC mux/enable/valid/data
addresses and applies vendor sentinel/validity rules; it is not enough to
copy trip temperatures from the vendor thermal-zone names.

### Suspend, idle, and SPM firmware

The vendor SPM v2 code maps a `mediatek,sleep` block plus topckgen, infracfg,
MCU/PLL, efuse, thermal, DDRPHY, vcorefs, and system-CIRQ resources. Its
dynamic path requests private images such as `pcm_suspend*.bin`,
`pcm_sodi*.bin`, and `pcm_deepidle*.bin`; the vcorefs path also contains an
embedded PCM image. MT6797 dpidle hooks change PMIC-wrapper phases and gate
MIPID/MIPIC/MDPLLGP/SSUSB 26 MHz clocks. These operations are a firmware and
power-sequencing boundary, not generic PSCI idle states.

The live capture supports this separation: WFI/regular idle is active, deep
vendor states have zero usage or vendor block diagnostics, and `/sys/power/state`
advertises `freeze mem` without a suspend cycle having been attempted.

## Linux 7.1.3 comparison

- `drivers/cpufreq/mediatek-cpufreq.c` has no MT6797 compatible. It expects a
  CPU/intermediate clock pair, `proc` and optional `sram` regulators, shared
  OPP tables, and an intermediate OPP used while changing PLL parents. Its
  voltage-tracking and rollback sequence is reusable, but the vendor code does
  not yet provide the same DT resource contract or safe calibrated OPP data.
- The current Gemini DTS patch adds only static per-CPU `clock-frequency` boot
  hints. CPU/intermediate clock handles, `proc`/`sram` supplies,
  `operating-points-v2`, CCI phandles, and MT6797 machine data are absent, so
  the generic driver cannot probe even before the EEM ownership problem is
  considered. See the [cpufreq/DTS gap result](mainline-cpufreq-dt-gap.md).
- The existing MT6797 CCF provider exposes main/universal and peripheral PLLs,
  but no ARMPLL definitions, CPU muxes, or CCI PLL clock. The vendor CPU PLL
  windows therefore need a clock-provider extension or a dedicated clock
  backend before generic cpufreq reparenting can be used.
- Linux 7.1.3's `mediatek-cpufreq` match table names MT2701/2712, MT7622/7623,
  MT7988A, MT8167, MT817x/8173/8176, MT8183/8186, MT8365, and MT8516; it does
  not name MT6797. Generic `cpufreq-dt` also has no MT6797-specific fallback.
- `drivers/thermal/mediatek/auxadc_thermal.c` matches MT8173, MT2701, MT2712,
  MT7622, MT7986, MT8183, and MT8365, but not MT6797. Its bank data, raw-to-
  temperature formulas, efuse extraction, and AUXADC binding must not be
  assumed to cover `mt6797-therm_ctrl`.
- Generic `cpufreq-dt` and standard OPP/regulator infrastructure remain useful
  only after the board's clock, regulator, calibration, and transition
  contract has been independently established.
- Generic PSCI remains the preferred CPU-on/off and basic idle boundary. The
  vendor suspend parameters (`0x0010000` and `0x1010000`) do not establish
  that mainline `mem` or vendor deep-idle PCM is safe.

## Mainline implementation boundary

1. Keep CPU topology and PSCI generic; do not add vendor cpuidle state names or
   PSCI parameters without firmware-level evidence.
2. Treat a future cpufreq implementation as an MT6797 variant or new driver
   unless a register-level comparison proves the generic MediaTek driver has
   the same clock, regulator, OPP, and calibration contract. Reuse its OPP,
   regulator-tracking, clock-reparenting, and cpufreq-core pieces where they
   fit, but fail closed on missing calibration and never make a live vendor
   table the board default.
3. Treat a future thermal implementation as either a narrowly scoped MT6797
   extension of the common AUXADC framework or a new driver, depending on the
   recovered bank protocol. It must prove raw conversion, calibration cells,
   IRQ status/clear, sensor validity, and safe trip behavior before enabling
   thermal throttling.
4. Keep DVFSP, SPM deep idle, and suspend PCM disabled. Do not redistribute
   private PCM images or infer a firmware ABI from image names alone.

## Bring-up gates

Before enabling CPU DVFS:

- identify the populated cluster/PLL topology from CCF and read-only device
  evidence;
- decode efuse/PTP/EEM calibration without publishing serials or raw keys;
- prove regulator ownership, Vproc/Vsram tracking, and rollback on a bounded
  frequency sweep;
- verify thermal throttling and emergency shutdown independently.

Before enabling thermal zones:

- map each bank and AUXADC transaction from register traces or a complete
  source implementation;
- recover efuse calibration and all invalid sentinels;
- validate IRQ status/clear and trip conversion against an external reference;
- start with read-only temperature reporting and conservative limits.

Before enabling suspend/deep idle:

- verify the boot firmware's PSCI version and CPU suspend state semantics;
- test WFI and CPU hotplug/wakeup cycles with a serial or equivalent recovery
  path;
- establish wake-source, PMIC, clock, DDR, and SPM ownership;
- obtain a redistributable firmware contract or keep the vendor PCM path
  private and disabled.
