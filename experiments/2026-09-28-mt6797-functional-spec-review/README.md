# Experiment: MT6797 functional specification cross-check

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-28-mt6797-functional-spec-review` |
| Status | completed |
| Subsystem | Wi-Fi/HIF, AP-DMA, I2C6, thermal and peripheral architecture |
| Device variant | Project MT6797X Gemini; no device accessed |
| Date | 2026-09-28 |
| Investigator | Codex, at owner request |
| Tracking issue | None created; owner-requested documentation review |

## Reconciliation with main (2026-10-17)

Restored against `598040b5`. This is the September source assessment, not the
current activation plan. The [HIF executor review](../2026-09-28-mt6797-hif-executor-review/README.md)
already answers the setup/data, TX-boundary and selected INIT RX questions.
Later [common-init runtime](../2026-10-06-mt6797-wifi-common-init/RUNTIME_3.md)
and [bounded WPA2 lifecycle](../2026-10-07-mt6797-wifi-phase-b-join/RUNTIME_31_RESULT.md)
supersede the earlier first-execution prerequisites below. Retain the example
errors, mode-specific framing, global DMA visibility and acquisition caveats
as documentary constraints; they neither revoke those results nor select a
new boot. The [roadmap](../../docs/ROADMAP.md) owns current ordering.

## Question and provenance

Does the owner-supplied functional specification corroborate the existing RE,
expose errors, or supply a discriminating next observation?

Source: privately supplied `MT6797.pdf`, *MT6797 LTE-A Smartphone Application
Processor Functional Specification for Development Board*, version 1.0,
2016-07-19, 291 pages. SHA-256:
`89a2929aed35f31d00e23be0ba8758980604d6d0ecdee6e8a28f1dc2711cb573`.
Page references below are one-based PDF pages, matching printed numbering.
The checksum identifies the reviewed bytes; it does not authenticate MediaTek
authorship, completeness or applicability to the Gemini silicon revision.
The file carries proprietary/confidential markings. No PDF, extracted text,
page image or copied implementation is included here; this note records
independently written analysis and technical facts. The source remains private.

Repository baseline when recording: `0611803028c1ce5f28af221557602573557e0097`.
Comparison inputs are the [Wi-Fi contract](../../docs/hardware/mt6797-wifi.md),
[HIF DMA analysis](../2026-09-05-mt6797-wifi-contract/HIF_DMA_CONTRACT.md),
[PIO design](../2026-09-05-mt6797-wifi-contract/PIO_TRANSPORT_DESIGN.md),
[INIT RX span](../2026-09-05-mt6797-wifi-contract/INIT_CREDITS_RX.md),
[I2C6 boundary](../../docs/hardware/da921x-i2c6-a72.md) and
[thermal freshness audit](../2026-09-04-mt6797-thermal-snapshot/SENSOR_FRESHNESS_AUDIT.md).
These records retain their own source and hardware provenance. Agreement with
this document does not prove that their vendor sources are independent of it.

## Procedure and safety

Read-only document/source review; no device, firmware analysis, kernel build,
boot candidate, register access or radio operation. Text extraction used pypdf;
suspect pages were rendered with Poppler and visually checked. Inspection
focused on the relevant chapters, not an exhaustive validation of all 291 pages.
A temporary strict-C11 host program called the existing
[`mt6797_hif_encode_command`](../2026-09-05-mt6797-wifi-contract/src/hif_command.h)
with PIO-only policy and capacity 1024 for the three vectors below. It compiled
with `-std=c11 -Wall -Wextra -Werror`; all calls returned zero. Temporary
extraction, renders and executable were removed. No permanent test harness was
needed. Reproduce by verifying the PDF digest, inspecting the cited pages and
calling that helper with the listed direction, port and payload length.

## Observations: corroboration and limits

| PDF pages | Documentary claim and comparison | Interpretation limit |
| --- | --- | --- |
| 215-237 | AHB slave with SDIO-like command setup at +0 and data aperture +0x1000; agrees with the selected HIF model and PIO primitive. | Does not establish standard SDIO attachment, runtime ownership or firmware success. |
| 238-243 | TX packets must not cross command boundaries; RX uses aligned packets plus an extra word. Enhanced interrupt data is 112 bytes; RX-enhance mode requires data and metadata in one CMD53 transaction. | Selected INIT RX already reads 32 bytes for a 28-byte response. General packet/aggregation behavior still needs matching-mode validation. |
| 142-146 | HIF is a channel of shared AP-DMA; hard reset can disrupt outstanding bus transactions. | Supports existing shared-owner and failure-lifetime requirements, not permission for a reset. |
| 146 | Non-secure global status reads report zero for secure engines. | Candidate visibility constraint: a global zero is not whole-controller idle proof. This does not describe channel-local EN reads or EMI registers and does not invalidate those separate observations. |
| 192-196 | Eight-byte I2C FIFO; I2C6 at 0x1100e000 is I2C_dual, with a repeated-start multiple-transfer restriction. | Corroborates controller specialization, not a ban on the already observed combined short write/read. Arbitrary message shapes remain unproved. |
| 188 | AUXADC can trigger another conversion on data-register read when AUTOSET is enabled; thermal controller also requests measurements. | Direct AUXADC data-register semantics cannot be assigned to thermal measurement-register reads. No sample age, sensor placement or calibrated accuracy is established. |
| 17 | MT6631 is described as the RF companion. | Stronger identification hypothesis, not proof of the fitted Gemini part, revision or calibration pairing. |
| 262 | Display PWM description mentions an operating clock and MMSYS mutex. | Does not resolve the actual consumer/parent identities or the upstream two-clock contract. |
| 251, 287 | SSUSB roles and Mali-T880 MP4 architecture are described. | No board port routing, PHY/rail ownership, GPU power or runtime support follows. |

## Observations: errors and unresolved contradictions

| PDF pages | Finding | Consequence |
| --- | --- | --- |
| 231-232 | A 32-byte RX example encodes count 0x22 (34), while its eight word reads total 32. | Internally inconsistent. Existing encoder gives 0x1000a020 for 32 bytes. |
| 233, 235 | RX DMA examples assign the HIF FIFO address to both source and destination while describing transfer to memory. | Do not copy these destination assignments. |
| 229-230 | Prose specifies register 0x0010; table and 0x10001404 encode 0x000a. | Derive fields from the intended operation; do not trust example literals. |
| 236, 250 | Block count greater than one is requested in one passage; count one is explicitly allowed in another. | Contradictory wording, not grounds to reject the existing one-block implementation. |
| 188 | Time-trigger mode is described as removed, then discussed as supported on the same page. | No acquisition-timing contract can be inferred from that prose alone. |
| 217 | Table heading uses base 0x180f0000 while address entries start at 0x50200000. | Unresolved address-context inconsistency; no usable alias established. |

The host encoder cross-check returned:

| Direction / port | Payload bytes | Command word | Transfer bytes | Comparison |
| --- | --- | --- | --- | --- |
| TX / 0x34 | 24 | 0x90006818 | 24 | Matches page 230. |
| RX / 0x50 | 32 | 0x1000a020 | 32 | Consistent with field arithmetic; differs from erroneous page 231. |
| TX / 0x34 | 768 | 0x98006802 | 1024 | Matches zero-padded two-block example on pages 232-233. |

Page 226 documents byte-mode count zero as 512 bytes and prohibits zero-count
block mode. The existing size helper deliberately refuses zero-count encoding;
its earlier lack-of-documentation rationale now has a candidate reference.
The new status is **documented here, not validated on this silicon**. The
conservative refusal remains valid; changing it is not necessary for the
selected PIO path. Do not conflate this with the contradictory block-count-one
wording above, or silently change transfer framing to bypass a refusal.

## Conclusion and follow-up

Confirmed: the document contains internal inconsistencies, and the three host
encoding results above are reproducible arithmetic observations. No new
implementation defect was established by this review. Silicon applicability
and the document's disputed claims remain inconclusive.

The reference strengthens existing transport and shared-resource reasoning.
It does not resolve CONSYS writer exclusion, effective EMI domain routing,
overlapping-region priority, HIF ADDR2/fabric translation, rail sequencing or
thermal freshness. Low FIFO addresses in examples cannot settle the bit-32
alias question. The [support matrix](../../docs/HARDWARE_SUPPORT.md) receives
no promotion; existing candidate and session budgets remain unchanged.

The follow-up proposed at review time was HIF executor review, then PIO
execution after EMI/power ownership, with DMA visibility/translation and
thermal acquisition treated separately. See the reconciliation above for work
that subsequently landed and the [roadmap](../../docs/ROADMAP.md) for current
ordering. Firmware/calibration bytes and source document stay private.
