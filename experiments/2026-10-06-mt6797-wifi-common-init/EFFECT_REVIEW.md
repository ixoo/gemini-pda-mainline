# Common-init effect review

Bounded effect review for Phase A, 2026-10-07. It answers the gate in
[COMMON_INIT_REVIEW.md](../2026-10-03-mt6797-wifi-audit/COMMON_INIT_REVIEW.md),
which admits no full initialization until the DLM, MCU clock, LTE, PA and
calibration effects have a contract. No later record closed that gate; this
document is that review. Compile success and table fidelity are not effect
evidence and are not used as such here.

## Evidence used

- **Vendor source.** `wmt_ic_soc.c`, `sw_init()`, at public vendor revision
  `c5b0be85` and Gemian v8 `59e00a91`; the two files are byte-identical
  (SHA-256 `22d98e9e…`, [startup receipt](../2026-10-03-mt6797-wifi-audit/results/startup-followup.json)).
  The selected configuration is in the
  [common-init receipt](../2026-10-03-mt6797-wifi-audit/results/common-init-review.json).
- **Routine execution on this unit.** The retained Gemian v8 boot log (private,
  SHA-256 `a058ddf2…`) records both patch downloads with fragment summaries
  47/444 and 211/876, then the coexistence configuration lookup. In the
  selected source, DLM and the MCU clock raise precede the patches, the clock
  restore follows them, and LTE coexistence, PA-on, calibration and PA-off
  precede the coexistence lookup; a calibration failure returns before it. So
  every step below ran on a Gemian boot of this unit, in this order. This is a
  source-conditioned inference; compiled-function equivalence is not proved.
- **No register documentation.** No document reviewed for this project
  describes the CONSYS MCU addresses below. Bit meanings come from the vendor
  table names only.

## Effects by step

| Step | What is written | Address space | Vendor name |
| --- | --- | --- | --- |
| DLM | `0x80100060`: clear bits 11:8, then 7:4, then 3 | CONSYS MCU, via WMT opcode 8 | power on DLM |
| MCU clock raise | `0x81021110` bit 28 set; `0x8000010c` bits 7:6 = 01; `0x80021118` bits 5:0 = 7; `0x81021100` bits 2:0 = 4 | CONSYS MCU, opcode 8 | enable, ratio, divider, HCLK |
| ROM patches | `0x02090508` = 0 and `0x02090b2c` = patch address, then the patch body, then WMT reset | CONSYS firmware, opcodes 8, 1, 7 | patch address, download, reset |
| MCU clock restore | `0x81021100` bits 2:0 = 0; `0x8000010c` bits 7:6 = 0; `0x81021110` bit 28 clear | CONSYS MCU, opcode 8 | disable HCLK, ratio, clock |
| LTE coexistence | five configuration commands, opcode 0x10, fixed vendor bytes, external component 0 | CONSYS firmware state | filter spec, frequency table, unsafe channel, LTE flag |
| PA rails | VCN33-BT then VCN33-WIFI enabled at 3.3 V | MT6351 PMIC, through the regulator framework | PA LDO on |
| Calibration | one `01 14 01 00 01` | CONSYS firmware and RF | start RF calibration |
| PA rails off | both rails disabled | MT6351 PMIC | PA LDO off |
| Antenna mode | coexistence `01 10 02 00 01 01` | CONSYS firmware state | WMT antenna mode |

Every WMT write targets the CONSYS MCU or firmware, never AP or PMIC
registers directly. The PA rails are the only AP-side effect; they use the
standard regulator API at the vendor's 3.3 V. The sequence switches both off
again before it ends, which the following HIF stage requires.

## Bounds

- Each step runs once. Every exchange waits at most 2 s for its exact event;
  the whole sequence is capped at 60 s.
- The first failed step stops the sequence. No later step, retry or cleanup
  write follows; power, clocks and any rail stay as they are.
- Calibration is the only step that may drive RF. It is one firmware-internal
  run, the same one Gemian performs at every power-on, with no host transmit,
  association or scan around it. Treat it as a radio action covered by the
  owner's reviewed-test authorization for this protocol.

## Reset contract

All firmware-side effects live in CONSYS, whose power domain the reviewed native
recovery restarts with the SoC, as in every earlier WMT boot. Nothing is written
to storage, NVRAM or calibration partitions. A failure between PA-on and
PA-off leaves the rails on until the reviewed recovery; whether the PMIC keeps
them across the restart is not established, and Gemian's own power-on switches
them as it needs. A failure before the clock restore leaves the CONSYS MCU on
the raised clock until that restart; Gemian raises and restores it on every
boot.

## Open items

- Bit meanings for the DLM and MCU-clock addresses are vendor names, not
  documented semantics.
- Calibration success semantics are unknown. The driver records the two status
  bytes and does not treat them as success; any interpretation of the scan must
  allow for an unverified calibration.
- The FM strap, crystal trim, co-clock and merged-PCM steps are not selected, as
  in the vendor build.
