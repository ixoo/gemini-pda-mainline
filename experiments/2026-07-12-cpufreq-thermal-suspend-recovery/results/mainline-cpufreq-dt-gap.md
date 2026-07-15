# MT6797 mainline cpufreq Device Tree/API gap

## Scope and provenance

This is a source-only comparison of Linux 7.1.3 and the current repository
patch set. It does not read the device, copy vendor source, or enable a kernel
transition. The analyzer is
[`scripts/analyze-mainline-cpufreq-dt-gap.sh`](../scripts/analyze-mainline-cpufreq-dt-gap.sh).

The VM's Linux source directory is the prepared 7.1.3 tree but does not carry
a usable Git `HEAD`; the individual source hashes below are therefore the
reproducible identity for this comparison.

| Input | SHA-256 |
| --- | --- |
| `drivers/cpufreq/mediatek-cpufreq.c` | `2b251ca6a28525619e8bf2fd13064836df7b07beec8e571ae5a85652f91fb56d` |
| `drivers/opp/core.c` | `7abb501d648d74e6d6313cdb3346c0ecb6e31b14202e818ae49d6421008e7014` |
| `drivers/soc/mediatek/mtk-svs.c` | `a4c23b8767cf3bf1a0152abb0587ab9377c28965775ece108e96f67c161867fc` |
| `drivers/clk/mediatek/clk-mt6797.c` | `aea5041078556536d0bac36fb76e5b3fcd2746fbae78c4a730c70fae0ab76b4a` |
| `include/dt-bindings/clock/mt6797-clk.h` | `20341c99924a7e9e71370eef12817f9d4fafee601692ce26c069eddc4ca40b60` |
| `arch/arm64/boot/dts/mediatek/mt6797.dtsi` | `35d0414a91f6798d1f9ebfee0086a4dfb2de85ea3317132536915ae347372531` |
| `patches/v7.1.3/0020-arm64-dts-mediatek-add-Planet-Gemini-PDA.patch` | `0645db11ed98b2b090bc8668c220ce9aa59e9466264a3150ecc491ce6d27e4a6` |

Generated at `2026-07-13T08:00:41Z` with Linux version `7.1.3`.

## Linux cpufreq contract

The generic MediaTek driver is a platform-data driver selected by a machine
compatible. It currently has no `mediatek,mt6797` match. For each present CPU
it expects the following consumer resources and standard interfaces:

- CPU clock named `cpu`;
- stable intermediate clock named `intermediate` for PLL reparenting;
- optional regulators named `proc` and `sram`;
- an `operating-points-v2` table shared by each policy's CPUs;
- optional `mediatek,cci` phandle when the platform-data enables CCI support;
- OPP voltage-adjustment notifications, which update the currently active
  voltage through the regulator/tracking path.

The driver already supplies reusable transition sequencing: scale voltage up,
reparent to the intermediate clock, program the PLL through the clock API,
reparent back, then scale voltage down. It also rolls back the clock and rail
when a stage fails. The OPP core and notifier path are the correct integration
point for a future calibrated EEM update.

The existing MT6797 clock provider does not expose the CPU-side contract. Its
PLL table contains main/universal and media/peripheral PLLs, but no ARMPLL
definitions, CPU muxes, or CCI PLL clock. The CPU PLL windows recovered from
the vendor driver therefore cannot be reached through the current CCF solely
by adding a cpufreq compatible.

The vendor CPU windows are LL `0x200/0x204/0x208`, L
`0x210/0x214/0x218`, CCI `0x220/0x224/0x228`, and a backup window at
`0x230/0x234/0x238`; divider selection uses `0x270` and `0x274`. The B
cluster follows a special BigiDVFS path rather than the normal `armpll_addr`
field. These are clock-provider ownership requirements, not OPP data.

## Current MT6797/Gemini contract

The base MT6797 DTS and the Gemini board patch do not currently provide the
consumer contract above:

| Item | Current state | Interpretation |
| --- | --- | --- |
| CPU frequency | `clock-frequency` on all ten board CPU nodes | Static boot hint only; not a cpufreq table or PLL provider binding |
| CPU/intermediate clocks | Missing from CPU nodes | Generic driver cannot obtain its clock handles |
| `proc`/`sram` supplies | Missing from CPU nodes | No safe generic regulator consumer relationship |
| OPP table/sharing | Missing | No calibrated or board-safe frequency/voltage input |
| CCI phandle | Missing | CCI coupling has no mainline resource owner |
| MT6797 cpufreq match data | Missing | Generic driver does not probe this SoC |
| ARMPLL/CPU mux CCF data | Missing | Existing MT6797 clock provider lacks the vendor CPU PLL windows and muxes |
| EEM owner | Missing | No provider owns mutable calibrated OPP updates or the shared EEM/thermal window |

The board's ten `clock-frequency` values are useful for describing the boot
snapshot, but must not be converted into `operating-points-v2` entries. The
vendor source selects silicon/date-code tables and then mutates voltages using
EEM/PTP calibration, so a static table would omit both the selection and
rollback contract.

## Decision and next gate

Reuse the generic cpufreq target, OPP notifier, regulator-tracking, and
clock-reparenting code where the proven MT6797 clock/rail provider can satisfy
its API. Add an MT6797-specific platform-data variant only after the missing
clock, intermediate-clock, regulator, CCI, and calibrated-OPP ownership are
implemented and independently validated. If the direct MT6797 PLL/CCI/EEM
protocol cannot be represented cleanly through those interfaces, a dedicated
MT6797 cpufreq/EEM driver is the correct outcome.

The safe next step is a disabled resource/provider contract or read-only
status path. Keep cpufreq transitions, EEM writes, DVFSP, and suspend disabled;
this audit performed no hardware write.
