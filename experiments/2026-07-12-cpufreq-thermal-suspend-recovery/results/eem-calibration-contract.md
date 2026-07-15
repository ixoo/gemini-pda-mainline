# MT6797 EEM/PTP calibration contract

## Evidence

- Planet vendor tree: commit `c5b0be85017ad0c599725e8273842efdbecdd88a`.
- Gemian vendor tree: commit `d388d350cb2dda8f23b99be6fa5db9628896e87f`.
- Linux comparison tree: `7.1.3`.
- Vendor sources: `mt_eem.c`, `mt_eem2.c`, `mt_eem2.h`, `mt_ptp.h`, and
  `mt_defptp.h`. The Planet tree contains `mt_eem2.c`; the older Gemian tree
  does not.
- The private runtime capture is
  `artifacts/device-inventory/20260713-live/eem-ptp.txt`. It contains raw
  calibration diagnostics and must not be committed or shared as public
  hardware documentation.

## Recovered vendor protocol

The MT6797 EEM controller is mapped at `0x1100b000` for `0x1000` bytes. The
same window is named `therm_ctrl` in the vendor DT, so EEM and thermal are not
independent register resources. EEM uses a second interrupt, SPI 129 LOW, and
the clocks `MFG_BG3D`, `SCP_SYS_MFG`, and `INFRA_THERM`; the thermal controller
uses SPI 78 LOW and `INFRA_THERM`. A future mainline implementation must model
the shared register/clock ownership explicitly rather than probing two
uncoordinated MMIO drivers.

The EEM register contract includes:

- bank selection at `+0x400`;
- phase configuration at `+0x200`--`+0x238` (`DESCHAR`, `TEMPCHAR`,
  `DETCHAR`, `AGECHAR`, frequency percentages, limits, VBOOT, detector
  window, and enable);
- INIT2 input/output at `+0x23c`, `+0x240`, `+0x244`, `+0x248`, and `+0x24c`;
- interrupt/status registers at `+0x254`--`+0x25c` and thermal/protection
  status through `+0x404` onward.

Four CPU-relevant detectors are active in the vendor implementation:

| Detector | EEM bank | CPU-DVFS consumer |
| --- | ---: | --- |
| `EEM_DET_BIG` | 0 | `MT_CPU_DVFS_B` |
| `EEM_DET_L` | 3 | `MT_CPU_DVFS_L` |
| `EEM_DET_2L` | 4 | `MT_CPU_DVFS_LL` |
| `EEM_DET_CCI` | 5 | `MT_CPU_DVFS_CCI` |

GPU and SOC detectors are separate consumers. Each CPU detector runs the
following state machine:

1. `INIT01` programs the detector and records DC and ageing offsets from the
   hardware interrupt result.
2. `INIT02` supplies the recorded offsets, reads eight voltage anchors from
   `VOP30`/`VOP74`, and interpolates a 16-entry voltage table against the
   detector's frequency-percentage table.
3. `MON` applies thermal effects and rewrites the voltage table while the
   detector remains enabled.

The source uses 10-uV units. EEM values use base `70000` and step `625`; CPU
PMIC values use base `30000` and step `1000`; SRAM record conversion uses base
`90000` and step `2500`. Before publishing an OPP update, the vendor path:

- adds an optional temperature offset of `6250` when temperature is at or below
  `33000` (or the thermal reading is invalid);
- applies a detector/phase offset and clamps to detector VMIN/VMAX;
- caps each result against the per-frequency `recordTbl` safety value;
- converts to the PMIC selector and calls
  `mt_cpufreq_update_volt_b()` or `mt_cpufreq_update_volt()`;
- can restore the default table after a detector error or explicit disable.

This means the static vendor OPP table is only an input. The active voltage
table is mutable, temperature-dependent, and bounded by calibration and
recorded safety values.

## Live read-only correlation

At the 2026-07-13 capture, `/proc/eem/EEM_DET_BIG`, `EEM_DET_L`, `EEM_DET_2L`,
and `EEM_DET_CCI` all reported `enable (1)`. They reported banks 0, 3, 4, and 5,
temperatures near 25 °C, and zero user voltage offset. The global EEM log and
iTurbo controls were disabled; `/proc/cpufreq/enable_cpuhvfs` was `1`, hardware
governor was `0`, and `cpufreq_idvfs_mode` was `1`. The status files exposed
16-point calibrated voltage/frequency results, but those values remain only in
the private capture.

This is observational evidence that the vendor kernel has an active
calibration-to-cpufreq path. It is not evidence that the same path is safe to
enable in a new kernel.

## Linux 7.1.3 reuse boundary

Linux 7.1.3's `drivers/soc/mediatek/mtk-svs.c` is the closest reusable
architecture. It also models INIT01/INIT02/MON/error phases, consumes NVMEM
calibration cells, applies thermal offsets, clamps against default voltages,
and calls `dev_pm_opp_adjust_voltage()`. The OPP core emits
`OPP_EVENT_ADJUST_VOLTAGE`, which the generic MediaTek cpufreq driver already
handles for the currently active frequency.

However, Linux 7.1.3's SVS match table contains MT8183/8186/8188, MT8192, and
MT8195 only. It has no MT6797 compatible, and its NVMEM cell names, SVS register
map, bank data, clock/reset contract, and regulator assumptions do not match
the MT6797 EEM source. Reuse the phase/error/OPP-update pattern; do not copy
the SVS tables or pretend the MT6797 block is an SVS-compatible register map.

## Bring-up gates

Before an MT6797 EEM provider or cpufreq variant can change an OPP:

1. define a shared ownership model for the `0x1100b000` EEM/thermal window and
   both IRQ paths;
2. map the EEM efuse fields into a private NVMEM provider without publishing
   raw calibration words;
3. prove the PMIC selector conversion and Vproc/Vsram sequencing against the
   DA9214 and internal SRAM rails;
4. implement INIT01/INIT02/MON error handling with default-voltage rollback;
5. connect calibrated updates through the OPP notifier path and test that a
   failed update cannot leave an undervolted active frequency;
6. start with read-only detector status and fixed safe clocks. Keep EEM,
   cpufreq transitions, DVFSP, and suspend disabled until those gates pass.
