# Experiment: MT6797 EINT and pinctrl recovery

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-12-mt6797-eint-recovery` |
| Status | `inconclusive` for mainline runtime; source, live, and authored-map contracts recovered |
| Subsystem | MT6797 pinctrl, GPIO, external interrupts, and debounce |
| Device variant | Gemini PDA running Gemian |
| Date | 2026-07-12 |
| Investigator | Repository maintainer with Codex assistance |

## Question

What part of the MT6797 pinctrl/EINT implementation is reusable from Linux
7.1.3, and which chipset-specific data and virtual-input behavior must be
restored before board interrupts can be enabled?

## Safety and scope

This experiment is source-only, except for the already-authorized private
device-tree capture used for a mechanical map check. It does not access MMIO,
change pinmux or debounce state, request an interrupt, stimulate a consumer,
or enable direct GIC routing. Raw captures and extracted vendor material stay
under Git-ignored paths.

## Associated code

- [`scripts/analyze-mt6797-eint-contract.sh`](scripts/analyze-mt6797-eint-contract.sh)
  records vendor Git blob IDs, Linux SHA-256 values, bounded source anchors,
  and the optional private-capture map check.
- [`results/mt6797-eint-mainline-design.md`](results/mt6797-eint-mainline-design.md)
  records the implementation boundary and bring-up gates.
- [`results/eint-map-recheck-20260714.txt`](results/eint-map-recheck-20260714.txt)
  records the repeated-capture result: the v5 capture has a complete 172-entry
  map matching the current Linux header, while earlier captures do not include
  the decoded mapping property.
- The existing [`decode-eint-capture.py`](../2026-07-11-gemian-hardware-inventory/scripts/decode-eint-capture.py)
  parses the private live table and validates the authored Linux header.

Run from the development VM:

```sh
./experiments/2026-07-12-mt6797-eint-recovery/scripts/analyze-mt6797-eint-contract.sh
```

The analyzer reads the sparse vendor checkout through Git objects, so it does
not require materializing proprietary source into the workspace.

## Evidence

- Gemian reference commit: `d388d350cb2dda8f23b99be6fa5db9628896e87f`.
- Vendor DT declares `mediatek,mt-eic` at `0x1000b000 + 0x1000`, parent GIC
  SPI170 level-high, 192 channels, four optional direct routes (SPIs
  206–209), and ten debounce timing entries.
- The private live DT capture decodes 172 entries in the GPIO-to-EINT table:
  171 physical GPIO mappings plus pseudo-GPIO262→EINT176. It also records
  built-in EINT186 alternate muxes on GPIO61, GPIO93, GPIO107, and GPIO181.
- Relevant live board candidates are GPIO67→EINT6 (microSD), GPIO85→EINT8
  (touch), GPIO88→EINT11 (ALS/proximity), and EINT10 for the AW9523 keyboard
  interrupt. These are candidates until each is stimulated and observed under
  a mainline kernel.

## Reproducibility and negative evidence

The vendor pinctrl implementation is not equivalent to the live contract:

- its pin header marks the ordinary pins `NO_EINT_SUPPORT`;
- its EINT offset structure is commented out and reports a stale `ap_num = 224`
  inside that comment;
- the vendor DT nevertheless exposes the separate `mt-eic` block and board
  consumers use raw EINT numbers from `cust_eint.dtsi`.

This is why the local series adds a new MT6797 EINT data record and map rather
than copying a nearby SoC's table or making the generic driver emulate the
vendor ABI. `cust_eint.dtsi` is useful evidence but is contradictory for board
assignment: it contains alternatives such as MSDC1 `<5>`, touch `<10>`, ALS
`<65>`, and gyro `<67>`, while the live Gemini capture and pinmux correlation
identify GPIO67/EINT6, GPIO85/EINT8, and GPIO88/EINT11. Those alternatives
must not be copied into the Gemini board DTS without a controlled test.

## Conclusion

Linux's generic MediaTek EINT register operations, IRQ-domain handling,
debounce framework, wake support, and virtual-GPIO mechanism are reusable.
The MT6797-specific pin map, six-bank/192-line sizing, debounce table, EINT
parent resource, and virtual PMIC/built-in lines are new data. Runtime support
is not established until a mainline image demonstrates delivery, polarity,
mask/ack, debounce, and wake for one controlled consumer at a time.
