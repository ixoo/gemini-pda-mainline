# Experiment: MT6797 CMDQ/GCE recovery

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-12-mt6797-cmdq-gce-recovery` |
| Status | `inconclusive` for mainline runtime; provider and event contracts recovered |
| Subsystem | MT6797 Global Command Engine / Command Queue |
| Device variant | Gemini PDA running Gemian |
| Date | 2026-07-12 |
| Investigator | Repository maintainer with Codex assistance |

## Question

What exact GCE mailbox, thread, address, interrupt, clock, subsystem-address,
and hardware-event contract must Linux 7.1 model before display and other
multimedia clients can submit safe CMDQ packets on MT6797?

## Provenance and environment

- Exact Gemian GPL tree: commit `d388d350`, principally
  `drivers/misc/mediatek/cmdq/v2/` and `arch/arm64/boot/dts/mt6797.dts`.
- Mainline comparison: checksum-verified Linux 7.1.3 prepared by the
  repository workflow.
- Live target: Gemini PDA running its current Gemian kernel; unique device
  identifiers are excluded.

## Safety assessment

The associated collector's default path reads kernel-exported state only. It
does not read GCE MMIO directly, submit a CMDQ packet, modify an event token,
change a clock, or interact with the vendor test interface. The two-second
interrupt sample only rereads `/proc/interrupts` while the existing display
workload continues normally. `--read-proc` opts into the source-audited
vendor record and status callbacks. They take driver locks and copy history;
the status callback may also perform ordinary GCE status/PC reads for an
active thread, but has no write path. Its output can contain kernel, DMA, and
process addresses and must remain private. All raw output is retained under
the Git-ignored `artifacts/device-inventory/` tree.

## Associated code

- [`scripts/collect-live-cmdq-gce.sh`](scripts/collect-live-cmdq-gce.sh)
  captures the bound platform device, IRQ activity, runtime-PM state, clock,
  device-tree identity, debug interfaces, and matching kernel messages. Its
  explicit `--read-proc` mode also captures the audited address-bearing
  history/status interfaces for private analysis.
- [`scripts/derive-gce-contract.py`](scripts/derive-gce-contract.py) joins the
  downstream DTS with its event and subsystem declaration tables, generates
  the expected binding constants, and compares both a proposed header and a
  byte-order-stable live capture.
- [`scripts/summarize-cmdq-proc.py`](scripts/summarize-cmdq-proc.py) reduces a
  private address-bearing history/status capture to scenario/thread/priority
  tuples and aggregate engine health without emitting addresses or process
  identifiers.
- [`scripts/analyze-mt6797-cmdq-contract.sh`](scripts/analyze-mt6797-cmdq-contract.sh)
  records vendor/Linux source hashes, bounded register/platform anchors, and
  invokes the event/subsystem derivation check.

The source-backed mainline boundary is recorded in
[`results/mt6797-cmdq-mainline-design.md`](results/mt6797-cmdq-mainline-design.md).

## Procedure

1. Recover the vendor GCE platform contract and dynamic event remapping.
2. Compare it with Linux 7.1's mailbox driver and closest platform records.
3. Run the read-only live collector and retain normalized evidence.
4. Mechanically derive and check subsystem and event constants.
5. Add only the source-supported binding, header, and disabled or standalone
   SoC description; validate schemas, objects, DTBs, and the full series.

## Observations

The normalized live capture is committed as
[`results/runtime-summary.txt`](results/runtime-summary.txt). Private raw
captures are retained at
`artifacts/device-inventory/20260712-live/cmdq-gce.txt`,
`cmdq-gce-v2.txt`, `cmdq-gce-v3.txt`, and `cmdq-gce-proc.txt`, with SHA-256
values
`d5c3dd693e1819fcadb5028ede804f8fde76bee5238c2f771676952fba266059`,
`a3381b7d82d4da1aa852f23c61bf925c409fc4ccd3f9604fc49a2faec3ba75dc`,
`f4cb91ff8b7a2037430b26f63178864d6cc66bf89905f1bcaa1705d63a18282d`,
and `0642dd2df5f1342b04f439ce6e1dc39502e2a6119bc507f60756a7f5ab174067`.

The live `10212000.gce` platform device is bound to `mtk_cmdq`. Linux IRQ184
is SPI152 plus the GIC SPI base and had handled 3,427 interrupts across the
two online CPUs at capture. The downstream DT also describes SPI153 for its
optional secure-world path, but that IRQ is not registered by this kernel.
This matches the build configuration: the second IRQ is requested only when
both secure-path and normal-world-secure-IRQ support are compiled.

The `infra_gce` clock is the public MT6797 infracfg gate at ID 10. It reports
136.5 MHz and is unprepared and disabled when sampled idle. The source-audited
status read caught it enabled during periodic display work, confirming that
the vendor driver gates it around CMDQ activity rather than treating the GCE
as an always-on block.

The vendor implementation has 16 hardware threads. Normal IRQ status is
masked with `0xffff`; threads 12, 13, and 14 are reserved for secure primary
display, secondary display, and MDP respectively. Its command-buffer address
conversion macros truncate directly to 32 bits and do not shift, exactly
matching Linux 7.1's MT8173 platform record (`thread_nr = 16`, `shift = 0`,
no software global-control bits). The register offsets, 0x80-byte thread
stride, active-low IRQ bitmap, slot-cycle value `0x3200`, and token-update
register also match the upstream mailbox driver.

The private history capture shows real primary-display work on thread 0 at
hardware priority 4, primary memory output on thread 4, the display trigger
loop on thread 7 at priority 2, ESD checks on thread 6, and screen capture on
thread 3. No task was active or waiting at the status snapshot, and every
reported MDP engine had zero failures and resets. Address-bearing command
history and process identifiers are excluded from normalized evidence.

MT6797 dynamically remaps logical event enums from its DT. The mechanically
derived contract contains 26 subsystem selectors and 112 event macros. The
checker matches all 141 comparable numeric properties among the pinned DTS,
the running device tree, and the proposed header. MT6795 event IDs are not a
valid substitute: for example, MT6797 OVL0 SOF is 10 rather than 11, mutex0
stream EOF is 58 rather than 52, and DSI0 TE is 70 rather than 2.

Patches 26 and 27 add the dedicated binding header and an enabled standalone
GCE provider using the MT8173 fallback. Only normal-world SPI152 is exposed.
The mailbox object builds with `W=1`; the focused binding passes, and the EVB,
X20 development board, and Gemini DTBs all pass the focused schema check.
No multimedia consumer is attached by these patches.

The complete series builds as the checksum-clean package
`linux-7.1.3-gemini-daf0521e6e67`. Its patch-set SHA-256 is
`daf0521e6e677586719b3dc3bae05f5f1dc1c41bb58f6d89d2085e6e109be390` and
configuration SHA-256 is
`024f4a432e3b06163003bfde2cfd2133dff039da1098ba735c7ecdeb3c18209b`.
The packaged `Image` SHA-256 is
`3222cf14d36a65485c07d48e2645e76702846478d926a940f114fed26c934317`,
and the Gemini DTB SHA-256 is
`77a8ecf303f73d3e254e61bf1e7830fc61eb35c145673abe56003613ab503915`.
Every package manifest entry passes after export to the host's ignored
`artifacts/20260712T065606Z/` tree. The packaged DTB contains one normal-world
SPI152 interrupt, infracfg clock ID 10, and two mailbox cells as intended.

## Conclusion

The provider contract is recovered and the live, source, and mechanical
evidence agree. Compile and schema validation pass, but mainline runtime is
unproven because no Linux 7.1 image has been booted on the Gemini.

## Follow-up

Recover the MT6797 MM mutex and minimal OVL0/RDMA0/DSI0 display path. Attach
each consumer only after its event, subsystem selector, clocks, power domain,
interrupt, reset, and M4U port are independently verified.
