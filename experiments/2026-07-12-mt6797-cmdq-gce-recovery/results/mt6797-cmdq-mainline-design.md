# MT6797 CMDQ/GCE boundary for Linux 7.1.3

## Result

The MT6797 Global Command Engine is register-compatible with Linux's existing
MT8173 mailbox implementation. No new CMDQ core driver is justified. The
mainline addition should be a named MT6797 binding/header carrying its own
subsystem and event IDs, with the MT8173 platform record as an explicit
fallback for the proven hardware layout.

The vendor secure path remains outside the generic provider. Only normal-world
SPI 152 is exposed; secure SPI 153 and secure threads 12--14 are proprietary
world-boundary evidence, not a reason to invent a Linux secure CMDQ ABI.

## Reproducible provenance

- Vendor source: Gemian MT6797 kernel commit
  `d388d350cb2dda8f23b99be6fa5db9628896e87f`.
- Linux source: prepared and patched Linux `7.1.3` tree in the development VM.
- Source analyzer:

  ```sh
  ./experiments/2026-07-12-mt6797-cmdq-gce-recovery/scripts/analyze-mt6797-cmdq-contract.sh
  ```

- Event/subsystem derivation:
  `scripts/derive-gce-contract.py` mechanically reconstructs the 26 subsystem
  selectors and 112 hardware-event values from the vendor DTS and declaration
  tables, then checks the local MT6797 header.

The analyzer records source hashes and bounded anchors only. It does not submit
a packet, read GCE MMIO, copy vendor source, or emit private command-buffer
addresses.

## Recovered hardware contract

The vendor `cmdq_reg.h` and live capture agree on:

- GCE resource `0x10212000 + 0x1000`;
- 16 hardware threads with an `0x80`-byte thread stride;
- global IRQ status at `0x10`, thread status/enable/PC registers beginning at
  `0x100`, and token update at `0x68`;
- slot-cycle value `0x3200`;
- direct, unshifted 32-bit command-buffer addresses;
- normal IRQ bitmap `0xffff` (one bit per thread);
- four prefetch-capable threads and the vendor's retained prefetch sizes.

The live vendor kernel bound `10212000.gce` to `mtk_cmdq` at Linux IRQ 184,
which corresponds to SPI 152. It had real display activity. Private history
was normalized to scenario/thread/priority tuples: primary display on thread 0,
primary memory output on thread 4, trigger loop on thread 7, ESD checks on
thread 6, and screen capture on thread 3. The capture showed no active task,
MDP failure, or reset at the snapshot; this is health evidence, not proof of a
mainline packet path.

## Event and subsystem boundary

The vendor driver loads logical event and subsystem values from the MT6797 DTS
at probe time. The reconstructed contract contains 26 subsystem selectors and
112 event macros. The retained live/source comparison reports 141 comparable
numeric properties matching across the pinned DTS, running device tree, and
local header. MT6795 values are not interchangeable: MT6797 uses
OVL0 SOF `10`, mutex0 stream EOF `58`, and DSI0 TE `70`.

The event header is therefore board/SoC data, not a copy of the MT6795 header.
Consumers must use the named MT6797 constants and the correct subsystem for
each register aperture. A wrong event number can wait forever or trigger the
wrong display block even though the mailbox driver itself probes successfully.

## Linux 7.1.3 comparison

Linux `gce_plat_mt8173` already describes `thread_nr = 16`, `shift = 0`, one
GCE clock, and the original mailbox register generation. The shared mailbox
driver also provides the correct 64-bit instruction format, WFE/EOC/JUMP
semantics, IRQ handling, runtime-PM, and DMA address conversion.

The local patches consequently:

1. add `mediatek,mt6797-gce` to the binding with
   `mediatek,mt8173-gce` as the fallback;
2. add the MT6797-specific event/subsystem header;
3. describe only the normal-world resource and SPI 152 in the SoC DTS.

The provider is standalone and can be enabled without a display consumer. The
vendor `/dev/mtk_cmdq` ioctl ABI, secure metadata, and address-debug interfaces
must not be copied into mainline; clients should use the Linux mailbox API and
DMA/IOMMU ownership rules.

## Mainline bring-up boundary

Before attaching a multimedia client, verify all of the following together:

- the client's exact subsystem selector and event IDs from the MT6797 header;
- the client clock and MM power-domain sequencing;
- its GCE channel/thread and hardware priority;
- its reset and interrupt resources;
- its M4U/SMI larb and port ID, if it performs DMA;
- a bounded packet with a visible completion event and recovery path.

The first diagnostic should be a minimal, non-secure display transaction with
one verified event chain. Do not attach the full retained display graph merely
because the GCE provider and schemas compile. Keep secure threads, secure
metadata, and vendor event remapping out of the first mainline path.
