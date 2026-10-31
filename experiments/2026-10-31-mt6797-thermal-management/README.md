# Experiment: MT6797 thermal management, calibration and firmware ownership

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-31-mt6797-thermal-management` |
| Status | `completed` for the static source, document and firmware study; no hardware behaviour is claimed |
| Subsystem | MT6797 thermal controller, AUXADC, calibration, cooling policy, firmware boundaries |
| Device variant | Planet Computers Gemini PDA, MT6797X, vendor Android/Gemian 3.18 stack |
| Date(s) | 2026-10-31 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | M5 power gate (thermal trips and cooling) in the roadmap |

## Question or hypothesis

What temperature-measurement, calibration and throttling mechanism does the
vendor MT6797 Gemini stack implement, which firmware owns each stage, and which
parts are reproducible for a mainline driver?

The hypothesis was that the earlier mainline work had the measurement and
conversion boundary right, but that the policy chain, the calibration handoff
and the firmware division of labour remained undocumented.

## Provenance and environment

- Vendor kernel: `planet-community/android_kernel_planetcom_mt6797`, commit
  `8cfe6596a503612e3332d9c26e292a19525a7f07`, shallow checkout on Buildbox.
- Bootloader: `dguidipc/gemini-lk-android8`, commit
  `f4988d74bb70a0a15d7f362f412afba7e7fcda46`.
- Android device tree: `planet-community/android_device_planetcom_geminipda`
  branch `cm-14.1`; vendor tree
  `planet-community/android_vendor_planetcom_geminipda` branch `cm-14.1`.
- Retained private images: preloaders `boot0`/`boot1`, `scp1`/`scp2`, `lk`/`lk2`,
  `tee1`/`tee2`, `md1img`, `md1dsp`, `md1arm7`, `md3img`, plus the installed
  Gemian vendor firmware set. Integrity was checked against the archive
  `SHA256SUMS` (41/41 OK).
- Vendor documents: MT6797 functional specification v1.0, register table parts
  1 and 2, MT6351 PMIC datasheet v12, MT6631 external datasheet.
- Mainline comparison: Linux 7.1.3 patches `0046`, `0057`, `0057a`,
  `0203`-`0245`, `0512`, `0513`, `0517`.
- Tools: `pdftotext -layout`, `strings`, `od`, AArch64 `objdump`, Python 3;
  scans executed on Buildbox-1.

## Safety assessment

Read-only. No device was accessed, no boot candidate was built or installed, no
firmware was modified, loaded or redistributed. Private firmware and documents
stayed outside Git; only independently written conclusions, public source
citations, sizes, digests and short generic strings are recorded here.

## Associated code

- [`scripts/scan-firmware-thermal.py`](scripts/scan-firmware-thermal.py) —
  read-only string, entropy and address-constant triage of a private firmware
  directory:

  ```sh
  ./scripts/scan-firmware-thermal.py /path/to/private/firmware \
    > results/firmware-thermal-scan.tsv
  ```

  The path is supplied by the operator; no private path is stored in Git.
- [`scripts/mtk-tp-policy.py`](scripts/mtk-tp-policy.py) — decoder/encoder for
  the stock `.tp` thermal policy, recovered from the vendor loader. Decoded
  output is vendor material and is not committed.

## Procedure

1. Clone the public vendor kernel, LK and Android device/vendor trees at the
   commits above; read the MT6797 thermal driver, the common thermal framework,
   PPM v1, EEM/PTP, SPM and the MT6797 device tree.
2. Decode the calibration fields and both temperature conversions from the
   vendor source and compare them with the mainline MT6797 patches.
3. Extract every thermal-related string, the module list and the 32-bit address
   constants from each retained firmware image; validate each address hit
   manually (several are instruction encodings or halfword tables).
4. Read the vendor documents page by page for thermal sensing, register maps,
   conversion and calibration; record the negative results explicitly.
5. Search the retained Gemian runtime captures for live thermal evidence
   (WMT temperature queries, battery/NTC device-tree parameters, charge
   temperature windows).
6. Inspect the Android thermal policy files and daemons for the userspace
   layer, including the `.tp` format.

## Observations

- [Kernel thermal inventory](results/kernel-thermal-inventory.md) — vendor
  driver structure, bank map, calibration decode, conversions, trips, coolers,
  PPM/DVFSP split and EEM coupling, with `path:line` citations.
- [Firmware thermal findings](results/firmware-thermal-findings.md) — per-image
  thermal content and the boot-chain handoff.
- [Datasheet thermal extract](results/datasheet-thermal-extract.md) — documented
  facts, page citations and the document gaps.
- [Firmware scan table](results/firmware-thermal-scan.tsv) — reproducible raw
  triage output (names, sizes, digests, entropy, matched terms, constants).
- [Userspace policy](results/userspace-policy.md) — recovered `.tp` obfuscation,
  decoded record format, boot-default trips and daemon roles.

The decisive observations:

1. Thermal calibration is a boot-chain handoff: efuse `0x10206180/84/88` →
   LK 100-word `atag,devinfo` → devinfo driver → `mtk_tc` decode. Words 31, 32
   and 33 are the thermal cell.
2. The vendor conversion is an integer closed form with per-part ADC gain and
   offset, per-sensor room-temperature codes, a die-temperature constant and a
   slope; the mainline V4 conversion reproduces it.
3. The only kernel-polled zone is `mtktscpu` (40 ms). All other zones read on
   demand; their trips do not fire autonomously.
4. Cooling is a power-budget stack (mW) arbitrated by `ap_thermal_limit` and
   converted to CPU/GPU limits by PPM v1; there is no direct CPU-frequency
   cooler and no DDR cooler.
5. Hardware protection is a 117 °C threshold programmed into the thermal
   controller with SPM state2 and TOPRGU thermal-reset arming, plus a software
   data-abort reset cooler at the same temperature.
6. The SCP image contains a DVFS/IPI/SPM service but no thermal policy. The
   CPU DVFSP is separate CSPM PCM firmware. Modem and Wi-Fi firmware run their
   own thermal loops.
7. The vendor documents do not contain the thermal-controller register map, the
   sensor inventory, the calibration fields or any conversion equation; those
   facts are vendor-source, not datasheet, facts.
8. The userspace `.tp` policy is obfuscated with a reversible period-10 column
   rotation, not encrypted, and decodes to a list of procfs writes. The shipped
   boot policy replaces the kernel defaults: CPU reset at 110 °C with adaptive
   coolers at 58/57 °C, and battery charge throttling from 46 °C — the battery,
   not the SoC, is the constrained subsystem.

## Analysis

The measurement path is now fully accounted for, and it matches the mainline
V4 implementation. What was missing for a thermal *management* claim is the
policy layer, and that layer is AP-side: zones produce power budgets, PPM
converts them to OPP limits, and the vendor performs CPU DVFS in software
because the hybrid DVFSP path is not enabled in the Android defconfigs or in
the retained Gemian configuration. The observed active CSPM firmware state on
the vendor boot is not explained by this and remains an open question; the
non-hybrid build still has code paths that pause and resume the firmware, so an
active-but-parked state is plausible.

Two documentary results constrain what can be claimed: the thermal controller
register block is absent from both register-table parts, and the calibration
efuse words are absent from every MT6797 document. Any future mainline work that
cites a datasheet for those values would be citing the wrong source.

## Conclusion

`confirmed`, scoped to the named vendor stack and commits:

- bank topology, calibration decode, both conversion formulas and the
  cal→EEM/SPM coupling;
- the boot-chain calibration handoff;
- the trip/cooler/budget/PPM chain and its thresholds;
- the firmware division of labour (preloader/LK/ATF/SCP/DVFSP/SPM/modem/Wi-Fi);
- the absence of a thermal register map and calibration description in the
  available documents.

Not established: any runtime behaviour on hardware, absolute temperature
accuracy, whether the 117 °C hardware path resets the unit, which `.tp` policy
a given SKU selects at runtime, and the exact meaning of the remaining trip
tuple fields.

## Follow-up

- Durable summary: [MT6797 thermal management and calibration](../../docs/hardware/mt6797-thermal-management.md).
- Support matrix: observation stays `partial`; no trip, cooling or suspend
  claim is added.
- Next discriminating work: confirm the shipped DTB compatibles and the
  presence of `/chosen/atag,devinfo` on a normal boot, then a calibration-gated
  read-only conversion comparison against an independent thermometer before any
  trip-point or cooling patch.
