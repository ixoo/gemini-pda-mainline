# Experiment: MT6351 PMIC auxiliary ADC

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-31-mt6351-pmic-adc` |
| Status | `completed` for the static source, document and firmware study; no hardware read is claimed |
| Subsystem | MT6351 auxiliary ADC, PMIC wrapper, battery/charger telemetry, modem ADC share |
| Device variant | Planet Computers Gemini PDA, MT6797X, vendor Android/Gemian 3.18 stack |
| Date(s) | 2026-10-31 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | none; telemetry prerequisite for the M5 power gate |

## Question or hypothesis

What does the MT6351 auxiliary ADC measure, how is it requested, scaled and
calibrated, who consumes each channel, and how is it shared between the AP, the
modem and the boot chain — given that upstream Linux has no MT6351 ADC driver?

The hypothesis was that the block is a conventional request/ready/result ADC
whose only unusual feature is the modem ring configured by the PMIC wrapper,
and that the vendor path applies no software calibration.

## Provenance and environment

- Vendor kernel `planet-community/android_kernel_planetcom_mt6797`, commit
  `8cfe6596a503612e3332d9c26e292a19525a7f07`. Built MT6797 PMIC path:
  `drivers/misc/mediatek/power/mt6797/`; wrapper:
  `drivers/misc/mediatek/pmic_wrap/mt6797/`. The MT6353-family copies under
  `drivers/misc/mediatek/pmic/mt6353/` are not built
  (`CONFIG_MTK_PMIC_CHIP_MT6353` unset in the retained Gemian configuration).
- MT6351 PMIC datasheet v12 (section 3.2.9, register summary) and MT6797
  register-table part 1 (PMIC wrapper, page 608).
- Retained private preloader, SCP, TEE, md1/md3 and vendor firmware images.
- Upstream comparison: Linux 7.1.3 in the prepared Buildbox tree
  (`mt6359-auxadc`, `mt6392-auxadc`, `mt6323-auxadc`, `mtk-pmic-wrap`).

## Safety assessment

Read-only. No device access, no PMIC write, no boot candidate and no firmware
change. Private images and documents stayed outside Git; only conclusions,
public source citations, register offsets and short generic strings are
recorded.

## Associated code

None. The work is source reading, document extraction and string scanning; the
firmware scan uses the existing
[thermal experiment's scanner](../2026-10-31-mt6797-thermal-management/scripts/scan-firmware-thermal.py).

## Procedure

1. Read the built MT6797 PMIC AUXADC helper and its channel/scaling table.
2. Extract the register map from the vendor headers and cross-check against the
   PMIC datasheet register summary and the MT6797 wrapper register table.
3. Trace every in-tree caller of the immediate-conversion helper.
4. Read the wrapper initialisation that configures the modem ADC share.
5. Scan each retained firmware image for PMIC ADC strings and register use.
6. Compare against the upstream IIO/MFD ADC drivers and the MT6797 wrapper
   model.

## Observations

- [PMIC ADC inventory](results/pmic-adc-inventory.md) — registers, channels,
  scaling, consumers, modem ring, firmware strings and upstream gap with exact
  citations.

Key observations:

1. Access is request/ready/result through the wrapper: write a channel bit to
   `AUXADC_RQST0_SET` (PMIC `0x0E98`), poll bit 15 of the channel result
   register, read the data.
2. Scaling is fixed in code: 1800 mV reference, ÷32768 for 15-bit channels,
   ÷4096 for 12-bit channels, and ×3 for `BATSNS`/`ISENSE`. No gain/offset
   calibration is applied; the `deCount`/`trimd` arguments are unused.
3. Battery temperature is measured on channel 3 (`BATON`), not by the fuel
   gauge; the fuel-gauge ADC is used for current only.
4. Channel 4 is shared between the PMIC die temperature and the DCXO/TSX
   crystal through a mux; the thermal driver uses the die-temperature setting.
5. The wrapper programs a modem share: command address `AUXADC_RQST1_SET`,
   latest result `ADC32`, write pointer `MDBG_1`, and a 32-entry ring of
   `AUXADC_BUF0..31`. The AP does not read the ring; the modem firmware does and
   applies its own NVRAM calibration (`l1cal_temperatureADC_T`).
6. The preloader carries its own copy of the immediate helper; the SCP and TEE
   images contain no PMIC ADC code.
7. Upstream covers MT6351 only as an MFD/regulator child; the nearest ADC model
   is `mt6359-auxadc`, and the MT6797 wrapper table has no ADC-modem registers.

## Analysis

The hypothesis held. The block is a conventional polled ADC; the unusual parts
are the fixed (uncalibrated) scaling and the modem ring, which makes the block
shared state rather than an AP-only peripheral. That sharing is the main design
constraint for a future driver: any AP request engine must not disturb the
wrapper-programmed modem pointers, and the ring's channel selection is not
documented in the extractable register text.

The absence of software calibration also bounds accuracy claims: the datasheet's
±1 % full-scale and ±2 LSB figures are the only specification, and the vendor
does not improve on them.

## Conclusion

`confirmed`, scoped to the vendor sources, documents and retained images above:

- register window, request/ready/result model and per-channel scaling;
- absence of software gain/offset calibration in the vendor path;
- channel-to-consumer mapping, including battery temperature on `BATON`;
- the wrapper-configured modem ring and the AP's non-use of it;
- the upstream coverage gap.

Not established: which channel the modem ring samples, whether `ADC32` is the
THR_MD result, the channel-2 divider, and any runtime value on this unit.

## Follow-up

- Durable summary: [MT6351 PMIC auxiliary ADC](../../docs/hardware/mt6351-pmic-adc.md).
- Next discriminating step: a read-only request on an unused channel with the
  modem ring untouched, after establishing the PMIC-wrapper ownership boundary,
  before any driver or telemetry patch.
