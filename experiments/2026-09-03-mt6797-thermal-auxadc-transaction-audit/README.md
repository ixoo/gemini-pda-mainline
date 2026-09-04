# Experiment: MT6797 thermal/AUXADC transaction audit

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-03-mt6797-thermal-auxadc-transaction-audit` |
| Status | `completed` source audit; runtime enablement rejected |
| Subsystem | MT6797 infracfg reset, AUXADC, thermal controller, thermal IRQ/protection |
| Device variant | Planet Computers Gemini PDA, MT6797 |
| Date(s) | 2026-09-03 to 2026-09-04 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | CPU8/CPU9 thermal/frequency-observability gate |

## Question or hypothesis

Can the currently disabled MT6797 AUXADC and thermal nodes be enabled using
the present Linux 7.1.3 integration, or does the source evidence require a
different reset, ownership, and controller transaction before any device boot?

The hypothesis was that the recovered topology and calibration constants were
necessary but not sufficient: exact reset and enable ordering would expose at
least one fail-closed prerequisite.

## Provenance and environment

- Repository parent: `b26475fdcefccc16ff5522d12abbfe48e64a2f76`.
- Canonical series: 502 entries, SHA-256 `51d8eaf6...`.
- Exact Buildbox prepared source state: `49084a29...`; recursive integrity:
  `d23fbc75...`.
- Exact current-source file hashes and pinned repository inputs are in
  [`contract.json`](contract.json).
- Public vendor source:
  `lineage-geminipda/android_kernel_planet_mt6797` commit
  `c5b0be85017ad0c599725e8273842efdbecdd88a`.
- Buildbox was used only for read-only inspection of its managed prepared
  Linux source and existing vendor Git mirror. No native VM build was run.
- Boot path: none. No candidate, device endpoint, partition, or hardware was
  used.

## Safety assessment

This was a read-only source audit. It performed no build, MMIO access, clock or
reset transition, thermal sampling, IRQ request, device write, reboot, or CPU
load. Both MT6797 DT nodes remain disabled. The audit explicitly rejects using
a device boot to discover missing ordering or ownership rules.

## Associated code and records

- [`DESIGN.md`](DESIGN.md) freezes the required transaction and failure order.
- [`contract.json`](contract.json) pins source identities and the selected
  prerequisite.
- [`results/transaction-matrix.tsv`](results/transaction-matrix.tsv) compares
  each vendor requirement with current mainline behavior.
- [`results/source-audit-20260903.txt`](results/source-audit-20260903.txt)
  records the compact sanitized result.
- [`scripts/validate.py`](scripts/validate.py) checks the contract, pinned
  repository inputs, exact prepared source, and pinned vendor tree without
  modifying them.

## Procedure

1. Pin the current prepared Linux source state and the public vendor commit.
2. Trace standalone AUXADC conversion, power, suspend, and ownership order.
3. Trace thermal reset, APMIXED buffer, six-bank programming, global channel
   enable, periodic sensing, first read, IRQ, and watchdog-protection order.
4. Compare those paths with the current MT6797 match data, probe order, reset
   provider, DT resources, and active reset consumers.
5. Separate confirmed register facts from unresolved IRQ/protection semantics.
6. Select the earliest hardware-free repair while retaining both DT nodes as
   disabled.

## Observations

- Vendor thermal reset asserts bit 0 through infracfg SET `+0x120` and
  deasserts it through CLEAR `+0x124`. Vendor PMIC-wrap reset independently
  uses SET/CLEAR `+0x140/+0x144`.
- Canonical patch `0002` instead registers offsets `0x120`, `0x124`, and
  `0x128` as three `MTK_RST_SIMPLE` banks. The reset core consequently
  read/modify/writes one register for both assert and deassert. Thermal ID 0
  never reaches `+0x124`, and PMIC-wrap ID 64 is translated to `+0x128`, the
  documented RST0 status register. The live PMIC-wrapper DT node is the sole
  current infracfg-reset consumer; the thermal node has no reset property.
- Vendor AUXADC checks global idle before clearing and triggering a channel.
  The current MT6797 match reuses `mt8173_compat`, whose global-idle poll occurs
  after the trigger. Its probe also sets `AUXADC_MISC.PDN_EN` bit 14, but the
  pinned Gemini vendor defconfig explicitly leaves
  `CONFIG_AUXADC_NEED_POWER_ON` unset and therefore makes the corresponding
  vendor write a no-op. Bit-14 semantics are unresolved and must not be guessed.
- Vendor thermal initialization clears only APMIXED `TS_CON1[5:4]`, waits 200
  microseconds, and verifies the result. Current MT6797 match data also clears
  bits 2:0 and then sets bit 0, modifying unrelated fields.
- Vendor code pauses and disables periodic sensing, clears channel 11, fully
  programs all six banks, sets channel 11 once, enables each bank, and only
  then releases periodic sensing. Current code releases channel 11 and bank 0
  before bank setup, then enables each bank before its final write-control
  programming.
- The current driver does not reject failed `of_iomap()` results, has no
  bounded first-valid-sample gate, and treats raw zero as 0 C, which passes its
  generic `-20 C..150 C` validity range. It programs the AHB timeout while
  requesting no IRQ, and it has no MT6797 watchdog direct-reset protection or
  suspend/resume ownership.
- The recovered `0x30d` poll, `0x492` sample-control, `0x2c` valid-mask,
  channel-11, six-bank/five-sensor topology, and SPI 78 low DT resource agree
  with the pinned vendor source. Those correct constants do not repair the
  surrounding transaction.

## Analysis

Immediate DT enablement is rejected. The reset provider is the earliest hard
dependency because a correct thermal probe must reset the controller, while
the same provider already serves PMIC wrap. Attaching thermal to the current
provider would convert a known source defect into a hardware action; changing
the provider without testing the PMIC-wrap consumer would be equally
uncontrolled.

The first repair must model the source-proven SET/CLEAR pairs
`0x120/0x124` and `0x140/0x144`, and must prove the ID-to-offset translation
for thermal ID 0 and PMIC-wrap ID 64. The intervening RST1 candidate
`0x130/0x134` follows the mainline MediaTek bank convention but was not found
in the pinned MT6797 vendor sources; its IDs must gain a primary source or
remain quarantined. The repair stays hardware-free and disabled-node-only until
the existing PMIC-wrap consumer has an explicit serviceability candidate.

Thermal should remain the sole first-stage owner of the AUXADC block, with the
standalone IIO node disabled. That requires the thermal driver to own the
AUXADC clock, indirect sampling, teardown, and resume state while preserving
the unresolved power bit—not merely borrow the current IIO driver's
incompatible post-trigger idle check.

Only after reset correctness is closed should a pure transaction-plan helper
encode all-banks-before-enable and failure unwind. IRQ acknowledgement and
watchdog direct-reset semantics remain unresolved and must stay disabled rather
than being guessed from vendor-private APIs.

## Conclusion

`rejected`: the current MT6797 thermal/AUXADC path is not safe to enable.
Calibration and topology are correct, but reset translation, AUXADC power-bit
semantics and idle ownership, APMIXED masking, bank commit order, first-sample
validity, IRQ/timeout handling, unwind, and suspend/resume are incomplete.

`confirmed`: the next implementation is a hardware-free repair of the two
source-proven MT6797 infracfg SET/CLEAR reset paths, exact translation tests,
closure or quarantine of the inferred RST1 path, and an audit of the sole
existing PMIC-wrap consumer. Both thermal and standalone AUXADC DT nodes remain
disabled, and no boot candidate follows solely from that repair.

## Follow-up

After the reset-provider repair passes source checks, focused tests, and an
exact Buildbox build, construct a separate PMIC-wrapper serviceability
candidate before using the repaired provider for thermal. Then implement and
hardware-free-test the ordered thermal/AUXADC transaction in
[`DESIGN.md`](DESIGN.md). Do not enable either DT node, add trips/cooling,
increase A72 load, or add cpufreq/OPP, idle, or suspend behavior before those
gates pass.
