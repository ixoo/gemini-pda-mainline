# Experiment: MT6797 M4U and SMI recovery

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-12-mt6797-m4u-smi-recovery` |
| Status | `inconclusive` for mainline runtime; source, live, and port contracts recovered |
| Subsystem | MT6797 multimedia IOMMU and Smart Multimedia Interface |
| Device variant | Gemini PDA running Gemian |
| Date | 2026-07-12 |
| Investigator | Repository maintainer with Codex assistance |

## Question

What exact M4U, SMI-common, larb, port, clock, power-domain, and fault-ID
contract must Linux 7.1 model before multimedia DMA consumers can safely be
enabled on MT6797?

## Provenance and environment

- Exact Gemian GPL tree: commit `d388d350`, paths below
  `drivers/misc/mediatek/m4u/mt6797/` and `drivers/misc/mediatek/smi/`.
- Planet board tree: commit `c5b0be85`.
- Mainline comparison: checksum-verified Linux 7.1.3 source prepared by the
  repository workflow.
- Live target: Gemini PDA running its current Gemian kernel; unique device
  identifiers are excluded.

## Safety assessment

The collector's default path reads kernel-exported state only. The optional
`--read-registers` path was audited against the exact downstream
`m4u_debug.c` and MT6797 `m4u_hw.c`: reading the debugfs file performs ordinary
32-bit reads from M4U offsets `0x000` through `0x17c` and logs them. Because
that vendor log level is disabled on the target, the same opt-in path performs
twelve targeted ordinary reads in that audited range. It also reads always-on
INFRACFG_AO `REG_INFRA_MISC` at `0x10001f00`. It does not write a register,
issue a TLB read-entry command, or change a clock or power state. Neither path
attaches or detaches an IOMMU consumer.
Private raw output is retained below the Git-ignored
`artifacts/device-inventory/` tree.

## Associated code

- [`scripts/collect-live-m4u-smi.sh`](scripts/collect-live-m4u-smi.sh) collects
  interrupts, resources, IOMMU groups, bindings, runtime-PM state, clocks,
  device-tree identities, and matching kernel messages.
- [`scripts/compare-port-table.py`](scripts/compare-port-table.py) mechanically
  compares every downstream port name and larb/port tuple with the proposed
  DT binding header and checks compact-ID uniqueness.
- [`scripts/analyze-mt6797-m4u-smi-contract.sh`](scripts/analyze-mt6797-m4u-smi-contract.sh)
  records vendor/Linux source hashes, bounded M4U/SMI register-generation
  anchors, and the MT8167-versus-MT8173 larb-register distinction before
  running the port comparison.
- The source-backed mainline boundary is recorded in
  [`results/mt6797-m4u-smi-mainline-design.md`](results/mt6797-m4u-smi-mainline-design.md).
- The default collector requires no arguments. `--read-registers` opts into
  the audited read-only M4U register snapshot. Root access improves debugfs and
  kernel-log coverage but does not change either path's read-only behavior.

## Procedure

1. Audit every collector input against the script and confirm it is read-only.
2. Run the collector as root on the authorized Gemini and retain raw output
   privately.
3. Compare live bindings with the two pinned downstream trees.
4. Derive the smallest Linux 7.1 platform-data and device-tree contract.
5. Validate bindings, objects, DTBs, and the canonical patch-series build.

## Observations

The normalized live capture is committed as
[`results/runtime-summary.txt`](results/runtime-summary.txt). Private captures
are retained at `artifacts/device-inventory/20260712-live/m4u-smi.txt`,
`m4u-smi-registers.txt`, `m4u-smi-registers-v2.txt`, and
`m4u-smi-registers-v3.txt`, with SHA-256 values
`8ada54423c0a830ad03beffebbe38d39d0585ef5c7261f3999bf3d116b3de1a6`
`b8d385596928ca792bd5f106ddc490a0f14efc7322d16fffeddf6861993fff54`,
`f82b8b7b921033939fb2f55128b85dd8f68d7948a383fef0315e594dfeb6df2f`,
and `cf890abac1db39cf04f7b0705b9fadbe1a313fc2bc94577f0d98f6ceacb68254`.

Source analysis has established one M4U at `0x10205000`, IRQ SPI 156
level-low, one shared translation domain, seven larbs, and 71 named ports.
Larb0 routes to internal M4U slave 1; larbs1 through 6 route to slave 0. The
fault transaction ID is `(larb << 7) | (port << 2)`, which matches the
generation-two format already decoded by the upstream driver.

The seven larb bases are `0x14020000`, `0x16010000`, `0x1a001000`,
`0x17001000`, `0x12002000`, `0x14021000`, and `0x15001000`; SMI common is at
`0x14022000`. The live platform devices match all eight addresses. Linux IRQ
188 is the expected SPI156 plus the GIC SPI base; it had zero interrupts at
capture. The vendor stack exposes no IOMMU groups.

All nine SMI/larb gate clocks used by the topology were prepared once by the
vendor M4U driver and disabled at capture. They reported 325 MHz except the
VDEC engine clock, which is a separate 338 MHz gate. No distinct M4U block
clock exists in debugfs. This agrees with the downstream `m4u_clock_on()`
being a no-op and rejects the upstream `HAS_BCLK` flag for MT6797.

The audited debugfs register read produced no output because `m4u_dump_reg()`
logs through a disabled vendor information level. No log level was changed.
This is a negative result, not a zero-valued register snapshot.

## Analysis

The register layout matches the older generation-two M4U family: generation-1
invalidate select, legacy IVRP encoding, the `STANDARD_AXI_MODE` register at
`0x48`, and the older fault-ID layout. The source-backed IOMMU flags are
`HAS_4GB_MODE`, `RESET_AXI`, `HAS_LEGACY_IVRP_PADDR`, and
`MTK_IOMMU_TYPE_MM`, with invalidate select at `0x38`; `HAS_BCLK` and
`TF_PORT_TO_ADDR_MT8173` are false. The latter is important: MT6797 programs
the generic translation-fault protection value `2 << 4` (`0x20`), whereas the
MT8173-special path writes `0x50`.

The MT6797 M4U source's larb MMU-enable register is `0xfc0`; Linux's existing
MT8167 SMI helper writes that same offset, while the MT8173 helper writes
`0xf00`. The dedicated MT6797 compatible therefore reuses the MT8167 helper,
not the superficially similar MT8173 record. The full source comparison and
bring-up boundary are in the [mainline design result](results/mt6797-m4u-smi-mainline-design.md).

A direct read of always-on INFRACFG_AO offset `0xf00` returned `0x6d403a00`.
Bit 13 is set, directly confirming the upstream `HAS_4GB_MODE` detection path
on this Gemini rather than inferring it from installed RAM size.

Targeted ordinary M4U reads also reproduce the vendor initialization contract:
invalidate select is `3`; standard AXI and DCM-disable are zero; control is
`0x22`, containing the generic `0x20` fault-protection selection; write-length
bit 5 is clear; and the legacy coherence/in-order/table-walk trio is exactly
`3`, `0`, `0`. L2 interrupt enable is `0x6f`, main fault status is zero, and
the vendor main interrupt mask is `0x003fffff`. The IVRP value is deliberately
excluded from normalized evidence because it derives from a live allocation
address.

This evidence adds `WR_THROT_EN` and a narrowly scoped legacy-misc flag to the
MT6797 record. The latter makes mainline reproduce the three explicit vendor
writes at offsets `0x80`, `0x84`, and `0x88` rather than relying on reset state.

MT6797 differs from existing upstream SMI records in its seven-larb topology,
larb MMU-enable register at `0xfc0`, and SMI common bus-select value `0x1554`.
The latter assigns the seven two-bit route fields exactly as initialized by
the SMI_EV vendor configuration; it must not be replaced by MT6795's one-bit
larb0 mask.

Linux 7.1 lacked CAM and MJC clock providers, blocking honest runtime-PM
descriptions for larb2 and larb4. Patches 21 and 22 add the public binding IDs
and compact gate drivers. Both objects build with `W=1`, and the focused clock
schema passes. This is compile validation only.

Patches 23 through 25 add the complete 71-port header, dedicated M4U/SMI
platform records, and disabled seven-larb SoC topology. The mechanical port
comparison passes with 71 unique DT IDs and independently recovers 63 ports
on downstream slave 0 plus the eight larb0 ports on slave 1. Both modified
driver objects compile with `W=1`; focused bindings and all three MT6797 DTBs
validate. Runtime support remains unproven because the fabric stays disabled.

The complete series builds as the checksum-clean package
`linux-7.1.3-gemini-56ac63222f6f`. Its patch-set SHA-256 is
`56ac63222f6f4c8e6460b302ffd1f116af47c3e41cd47e5595e5185ce86ab6bd` and
configuration SHA-256 is
`a393c946209c69a7678ab133e55543798470bb4af86efbfc4ce74448b77da04e`.
The packaged `Image` SHA-256 is
`0719316f6a8b8636704ddccee3da3e7f00b8188ad81ac90cf523f01be85627b9`,
and the Gemini DTB SHA-256 is
`9cd8a99a8f0b8d3f43147cb806d7d6895be2917ff5acffbe897b7c7c5985f969`.
All package manifest checks pass after export to the host's ignored artifacts
tree.

## Conclusion

The static MT6797 M4U/SMI contract is recovered and its live, source, and
mechanical evidence agree. The implementation is compile- and schema-tested,
but runtime support remains unproven: all new fabric nodes intentionally stay
disabled and no mainline image has been booted or flashed.

## Follow-up

Complete the canonical patch-series package, then recover and connect one
multimedia consumer at a time. Enable the M4U/SMI fabric only with the first
consumer whose clocks, power domain, reset, interrupts, and DMA port bindings
have all been independently recovered; validate that step on hardware before
expanding the graph.
