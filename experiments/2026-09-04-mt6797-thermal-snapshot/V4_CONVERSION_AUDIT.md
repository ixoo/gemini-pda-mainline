# V4 conversion and calibration-index audit

The [post-recovery decision](PASSIVE_DISCRIMINATOR_DECISION.md) found no passive
freshness discriminator. This source and synthetic-input audit instead finds a
specific arithmetic discrepancy in the deployed V4 conversion. No private
calibration or runtime ADC values were read. The deployed kernel is unchanged.

## Source identity and method

The existing production `drivers/thermal/mediatek/auxadc_thermal.c` on Buildbox
still matches SHA256 `e2ce72fa105be597a5c7a3cea37499512093c86ba4cc4ac85b92c10b0254c481`.
This is the file tied to the exact candidate in the
[source receipt](results/sensor-freshness-source-audit.txt). The pinned archive's
`drivers/misc/mediatek/thermal/mt6797/src/mtk_tc.c` still matches its previously
reviewed hash; pin and full identities are in the
[arithmetic receipt](results/v4-conversion-audit.txt). No source tree was copied,
prepared or changed. Only the pure production conversion body was extracted
into a temporary host test translation unit on Buildbox and removed afterward.

The independently written [harness](scripts/audit-v4-conversion.py) pins the
production file, tests it with undefined-behavior sanitization, and compares it
with a mathematical expression of the reviewed reference contract. It does not
compile vendor code. Reproduce on Buildbox with Python 3 and a C compiler:

```sh
python3 experiments/2026-09-04-mt6797-thermal-snapshot/scripts/audit-v4-conversion.py \
  --source /workspace/gemini-pda/src/linux-7.1.3-series-source/drivers/thermal/mediatek/auxadc_thermal.c
```

## Encoded offset normalization

The production decoder at line 2063 keeps the unsigned ten-bit encoded ADC
OE field. Its accepted range is 265..758. The conversion at lines 898--901
subtracts this stored field directly from both raw and room-temperature terms.
The pinned reference's `tscpu_thermal_cal_prepare_2()` instead defines the offset
as encoded OE minus 512 before calculating both terms. No V4 normalization
occurs elsewhere in the inspected production path.

Subtracting the same constant from both terms would cancel in exact arithmetic.
Here each term is separately shifted and divided by gain before subtraction,
so integer rounding makes the expressions differ. A wholly synthetic example
is encoded GE/OE=265/265, VTS=0, calibration degree=1, slope=0, raw=2926:
production returns 55700 mC, while the normalized reference returns 55600 mC.
These are test inputs, not device calibration or measurements.

The test grid uses GE/OE in {265,512,758}, VTS in {0,260,484}, degree in
{1,40,63}, slope in {0,31,63}, both signs, and every nonzero 12-bit raw code.
It covers 1,990,170 combinations, not every possible calibration tuple.
393,255 differed; maximum difference was 200 mC over all outputs and 100 mC
where both outputs were in the driver's accepted -20000..150000 mC range.
37,449 differences were inside the experiment's 0..58500 mC ceiling.
A local test-only variant normalizing OE in both terms matched the reference
for every tested combination. This admits a focused correction design, not a
claim that the deployed kernel has already been fixed.

The tested discrepancy is too small to account for the several-degree rise in
the retained traces. Since actual ADC/calibration inputs were not used and the
grid is finite, this is not a computed correction to any published temperature.
All historical thermal rejections stand; no threshold changes follow.

## Width, sign, range and indices

The decoder bounds GE/OE to 265..758, degree to 1..63, VTS to at most 484,
and slope to six bits (ID=0 forces slope zero). Gain is positive and the slope
denominator is at least 1033. For these bounds, intermediate numerators are
well within signed 64 bits and final scaled results fit signed 32 bits.
Both measured expressions intentionally use arithmetic right shift for negative
numerators; replacing that shift with signed division would change rounding.
Room numerators are positive under both offset conventions. The test found no
undefined arithmetic, increasing temperature with increasing raw code, or
non-100-mC output. Zero low-12-bit codes were rejected and 3,980,340 upper-bit
mask comparisons preserved output. Plausibility filtering remains necessary:
valid calibration plus an arbitrary raw code can still yield an out-of-range
temperature. These arithmetic properties do not establish sensor accuracy.

The active seven bank slots pass sensor IDs 0/3/1/2/1/1/1 directly to V4;
`VTS1..VTS4` occupy indices 0..3, so active conversion indices agree with the
calibration extraction and mux table. The declared ABB sensor ID is 4, but
`VTSABB` is array index 5 because index 4 is `VTS5`. V4 uses `vts[sensno]`
rather than `vts[conf->vts_index[sensno]]`. **This is a dormant mapping hazard:**
no current bank includes ABB, so it cannot explain the observed active-slot
response and no ABB runtime support is claimed. A future correction must test
distinct synthetic per-sensor coefficients and preserve the existing bank layout.

## Decision and limits

A focused offset correction and explicit V4 sensor-to-calibration mapping are
justified for offline implementation and regression work. The existing policy
KUnit suite tests calibration admission, not numeric equivalence of this pure
conversion; its pass did not cover this discrepancy. Full production extraction,
decoder boundary cases and mutation checks remain necessary for a correction.
No kernel build or boot is admitted by this audit alone. Any subsequent build
must use the clean published revision and explicit Buildbox workflow. Thermal
repeatability, protection, OPP, broader workload and default integration remain
closed. Ordered implementation is owned by the [roadmap](../../docs/ROADMAP.md).
