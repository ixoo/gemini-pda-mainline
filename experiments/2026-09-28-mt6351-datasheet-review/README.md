# Experiment: MT6351 datasheet cross-check

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-28-mt6351-datasheet-review` |
| Status | completed |
| Date | 2026-09-28 |
| Investigator | Codex, at owner request |
| Subsystem | MT6351 regulators, MFD/IRQ, keys, RTC and audio |
| Device variant | Project MT6797X Gemini, previously identified MT6351 E2; no device accessed |
| Tracking issue | None created; owner-requested documentation review |

## Reconciliation with main (2026-10-17)

Restored against `598040b5`. The VS1/VS2/VPA conflict remains: the integration
patch still uses the cited conversion, and the later
[PMIC basics F8](../2026-10-04-gemini-pmic-basics-re/README.md#regulators)
repeats the vendor descriptor values without electrical validation. Keep this
qualification attached to future regulator constraints and active consumers.
The VCN and storage tables below retain documentary omissions and trim limits,
not a claim that September's connectivity blockers remain current.

The [C1 read review](../2026-10-04-gemini-c1-preparation/PMIC_READ_REVIEW.md)
and [first C1 runtime](../2026-10-04-gemini-c1-preparation/README.md#first-c1-boot-2026-10-06)
supersede the old key/reset prerequisite; PMIC basics F15 separately refines
the RTC reload question. Preserve their selected policies and runtime results.
The physical long-press outcome and rail conversion are separate questions.

## Question, provenance and method

Can the supplied datasheet corroborate the RE, expose incorrect assumptions,
or resolve the next PMIC ownership decision?

Private source: `MT6351_PMIC_Data_Sheet_V12-Final.pdf`, 322 pages, SHA-256
`05bd18e2ff98d9c887a97759d50343080ad0202d06fbff9ce308568cd019508a`.
The cover says version 1.1, dated 2016-09-12; the revision history says 1.2
on that date. Cite the digest and page, not an assumed unambiguous revision.
Pages below are one-based PDF pages, matching printed numbering. Authenticity,
completeness and exact E2 applicability have not been established. Proprietary
markings and embedded recipient metadata are present; the PDF, extracted text,
renders and recipient identifiers remain outside Git. This note contains
independently written technical analysis only.

Repository baseline during review: `fbbc851b159b1553c93a6e38d859f8e26b0bbc52`.
Text extraction used pypdf; Poppler page renders checked the cover/history,
reset fields, voltage formulas, VCN controls and suspicious trim table entries.
Review covered relevant chapters rather than every field in the document.
Temporary extraction, public-source copy and renders were removed afterward.
No device, binary-analysis, rail, reset, radio, build or deployment operation
was performed. Existing hardware evidence is linked rather than reclassified.

## Highest-priority finding: buck voltage conversion conflict

Pages 129-131 specify VS1/VS2 voltage as `(0.6 + 0.00625 * code) * 2` volts
and VPA as `(0.16 + 0.016 * code) * 3.125` volts. The latter simplifies to
`0.5 + 0.05 * code`. Both the
[integration regulator patch](../../patches/v7.1.3/0015-regulator-mt6351-add-regulator-driver.patch)
and the [upstream-preparation patch](../../patches/upstream-4d7d9486/mt6351/0005-regulator-mt6351-add-E2-rails-with-device-local-desc.patch)
instead use 600000 microvolts plus 6250 per selector for all three rails.
The local regulator operations map these selectors directly through regmap;
there is no scaling stage in those operations.

| Rail / raw selector | Existing local conversion | Datasheet formula | Interpretation |
| --- | --- | --- | --- |
| VS1 / 64 | 1.000 V | 2.000 V | Datasheet reset selector also agrees with its 2 V summary default. |
| VS2 / 12 | 0.675 V | 1.350 V | Datasheet reset selector also agrees with its 1.35 V summary default. |
| VPA / 0 | 0.600 V | 0.500 V | Base differs. |
| VPA / 10 | 0.6625 V | 1.000 V | Step differs by a factor of eight. |

These are host arithmetic comparisons, not measured outputs. A fresh read of
the [pinned Gemian PMIC source](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/power/mt6797/pmic.c#L1643-L1664)
reproduced SHA-256
`c08786d5ad44006d1fdc0f885e43f6ca1e9398f9c6e5e14c4ec6fe167e3d143c`,
matching the existing [VCN33 source ledger](../2026-09-08-mt6351-mfd-upstream-preparation/VCN33.md).
Its descriptor table repeats the same 600000/6250 parameters, including VPA;
its list-voltage path uses the descriptor's linear conversion. Thus matching
the vendor table is not independent validation of the electrical conversion.

Classification: **confirmed source/document conflict; likely inherited
conversion defect, not yet electrically verified**. The previous descriptor
replay established source equivalence, not correctness of every rail's voltage.
Do not promote the full regulator topic or add active VS1/VS2/VPA consumers
until this is resolved. Do not change existing rail settings to test the PDF.
This finding does not invalidate demonstrated VEMC/VIO18 storage operation or
create a dependency on VPA validation for PIO Wi-Fi.

## Connectivity rails: useful evidence and important omissions

| Pages | Finding | Consequence |
| --- | --- | --- |
| 9, 42, 191 | One VCN33 output pin J17; shared selector at 0x0ada[10:9] maps 0-3 to 3.3/3.4/3.5/3.6 V; trim occupies [4:0]. | Corroborates the existing shared-selector and reference-schematic model. Does not prove Gemini continuity or BT/Wi-Fi enable combination logic. |
| 74, 180-181 | VCN33 control coverage skips 0x0a98 and 0x0a9a, the source/binary-proven separate enable registers. | The datasheet is incomplete for the exact ownership question. Do not consolidate enables or delete source-proven fields because they are omitted. |
| 157 | VCN28 bit 3 selects software versus SRCLKEN hardware enable control; bit 1 is software enable, bit 15 reported enable. Header default is 0x1a60. | Corroborates the distinction between a regulator vote and on-control ownership. The documented default matches the recorded mainline word, but does not identify its producer. |
| 157 | VCN28 bits 13:11 and 7:5 are blank despite the header default setting them and the retained source naming them. | The live source-field value 3 still has no VCN28-specific truth table here. Do not borrow another LDO's source-clock selection table from page 155. |
| 187 | VCN28 selector description gives only code 0 = 2.8 V; the local driver advertises four values. | Incomplete documentary coverage, not proof the other three source-backed encodings are invalid. Audit before wider voltage use; ordinary 2.8 V use does not require them. |

The existing [mainline sample](../2026-09-27-mt6351-vcn28-boot-observe/results/runtime-1.json)
is 0x1a60. The separately recorded [Gemian sample](../2026-09-08-mt6351-mfd-upstream-preparation/VCN28.md)
is 0xda6a. Host decoding gives on-control/software-enable/reported-enable
`0/0/0` and `1/1/1`, respectively; both source fields decode to 3 in both
words. Their difference also includes bit 14, whose description is blank here.
This is a comparison across different boots, not a transition trace or a
proof that reset created the mainline value. Repeating the consumed samples
without a new discriminator will not identify the source-clock owner.

## Storage, interrupts, recovery and other blocks

| Pages | Finding | Assessment of existing RE |
| --- | --- | --- |
| 187-189 | VMCH/VEMC selector 0 is described as 2.9 V with trim 5, or 3.0 V with trim 0; selector 1 is 3.3 V with trim 0. | A nominal driver table value is not an electrical measurement. Strengthens the existing [storage trim boundary](../2026-07-12-mt6797-msdc-recovery/MICROSD_POWER.md); preserve calibration and establish applicable trim before new pad/power transitions. |
| 60-63 | Four IRQ enable banks at 0x02c2/0x02c8/0x02ce/0x02d4 and status banks at 0x02e0/0x02e2/0x02e4/0x02e6; listed statuses are write-one-to-clear. Keys occupy bank-0 bits 0-3 and RTC bit 9. | Agrees with the local MFD layout and key/RTC numbering. Does not prove all 64 slots exist, wake delivery, parent transport or persistent-fault recovery. |
| 118-119, 319 | Key reset enable bits 9/8 and durations 5/8/11/14 seconds are documented; the timeout selector field is omitted. Page 319 describes forced PMU power-off. | Corroborates duration choices, not selector order or physical post-event behavior. Keep the existing [source/binary duration mapping and recovery-policy gate](../2026-09-08-mt6351-keys-preparation/RESET_POLICY.md). |
| 64, 119 | Broad watchdog-reset prose is qualified by a selectable digital-reset versus re-power behavior. | Do not infer an actual power cycle or fresh secure epoch solely from a watchdog event. |
| 54-55 | RTC overview describes clock/backup/alarm functionality, but no BBPU RELOAD/WRTGR contract was found. | Existing [RTC reload uncertainty](../2026-07-11-mt6351-pmic-recovery/results/rtc-source-audit-20260908.md) remains; do not restore the old supposedly read-only RTC collector. |
| 46-48, 53-54 | Codec paths, AUXADC and fuel-gauge architecture are described. | Useful component-level inputs, not Gemini analog routing, sense-resistor calibration or charger identity. No audio, charging, or SoC thermal-protection support follows. |

## Document defects and applicability limits

- Cover version 1.1 disagrees with the revision-history 1.2 entry.
- VCN33 is default-off in page 42's summary, but its page 181 enable-status
  reset bit is one. Do not choose a runtime state from either claim.
- Pages 189 and 191 repeat trim code 00000 and omit 10000; the positive
  sequence includes 10001 = +320 mV and 11001 = +150 mV. The duplicate/missing
  encoding is a concrete coverage defect; unusual numerical entries remain
  suspect, not license to invent a corrected trim table.
- The VS1/VS2 summary's 50 mV steps on page 41 do not match the 12.5 mV
  register formulas. VPA's full six-bit formula exceeds the summary's 3.4 V
  upper range. Register encoding range and recommended operating range must
  be reconciled separately; do not enable every representable selector.
- MT6351V and MT6351DV have different platform/default descriptions. A product
  suffix, document revision and silicon E2 identity are different facts.

## Conclusion and follow-up

The PDF makes the buck-conversion audit a concrete priority and strengthens
several existing control/trim interpretations. It does not close VCN33 enable
logic, VCN28 source selection, exclusive PMIC writers, RTC reload or physical
recovery behavior. No driver changes or new hardware-support claims result
from this assessment. The [roadmap](../../docs/ROADMAP.md)
owns current follow-up; the reconciliation above qualifies the historical
open questions. The
[support matrix](../../docs/HARDWARE_SUPPORT.md) retains its demonstrated scope.

Validation: document/source cross-check, visual inspection of the material
tables, host arithmetic for the four voltage vectors and two recorded words,
and repository documentation checks. No kernel compile, DT check or hardware
test is implied. Reproduce from the PDF digest/pages, the linked patches and
the pinned public source digest; no private calibration values are required.
