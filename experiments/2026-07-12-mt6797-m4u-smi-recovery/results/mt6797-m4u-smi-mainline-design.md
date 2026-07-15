# MT6797 M4U/SMI boundary for Linux 7.1.3

## Result

The MT6797 multimedia memory fabric can reuse Linux's generation-two MediaTek
IOMMU and SMI frameworks, but it needs a dedicated MT6797 platform record and
port binding. The chipset has one multimedia M4U, seven SMI larbs, a distinct
legacy M4U initialization sequence, and the MT8167-style larb MMU-enable
register at `0xfc0`. The nearby MT8173 helper uses `0xf00` and must not be
selected by analogy.

The local implementation remains disabled at the SoC level. This experiment
does not claim runtime DMA or display support and does not add an M4U mapping
to the GPU, whose recovered port table has no GPU client.

## Reproducible provenance

- Vendor source: Gemian MT6797 kernel commit
  `d388d350cb2dda8f23b99be6fa5db9628896e87f`.
- Linux source: prepared and patched Linux `7.1.3` tree in the development VM.
- Source-only analyzer:

  ```sh
  ./experiments/2026-07-12-mt6797-m4u-smi-recovery/scripts/analyze-mt6797-m4u-smi-contract.sh
  ```

- Port checker:
  `scripts/compare-port-table.py` compares the complete downstream table with
  `include/dt-bindings/memory/mt6797-larb-port.h`.

The analyzer records vendor Git blob IDs, Linux SHA-256 values, bounded source
anchors, and the mechanical port result. It never copies vendor source,
accesses MMIO, or submits a DMA job.

## Recovered contract

### M4U and ports

The vendor port table contains 71 named ports: 63 use internal slave 0 and the
eight larb0 display/MDP ports use slave 1. Larb IDs span 0--6 and the vendor
fault transaction ID is `(larb << 7) | (port << 2)`. That fault ID is not the
device-tree ID; Linux consumers must use the standard
`MTK_M4U_ID(larb, port)` encoding.

The physical M4U resource is `0x10205000 + 0x1000`, with SPI 156 (Linux GIC
IRQ 188 on the live vendor kernel). The vendor source names the corresponding
virtual mapping `M4U_BASE0 = 0xf0205000`; this is an ioremap address and must
not be copied into a mainline `reg` property. The live system exposes no IOMMU
groups and the M4U interrupt had zero events during the capture.

The MT6797 register contract is:

- generation-one invalidation selection at `0x38`;
- legacy IVRP physical-address encoding;
- `STANDARD_AXI_MODE` reset path at `0x48`;
- write-throttling control at `0x54`;
- generic translation-fault protection value `2 << 4` at control `0x110`;
- older coherence, in-order-write, and table-walk controls at `0x80`, `0x84`,
  and `0x88`;
- 4-GiB remapping selected through the always-on INFRACFG bit observed live.

The local MT6797 data therefore uses `HAS_4GB_MODE`, `RESET_AXI`,
`WR_THROT_EN`, `HAS_LEGACY_IVRP_PADDR`, `HAS_LEGACY_MMU_MISC`, and
`MTK_IOMMU_TYPE_MM`. It intentionally omits `HAS_BCLK` and
`TF_PORT_TO_ADDR_MT8173`. The three legacy misc writes are explicit because
they are part of the downstream initialization rather than a reset-state
assumption.

### SMI common and larbs

The seven larb resources are:

| Larb | Physical base | Mainline power domain | Mainline clock source |
| ---: | ---: | --- | --- |
| 0 | `0x14020000` | MM | MMSYS |
| 1 | `0x16010000` | VDEC | VDECSYS |
| 2 | `0x1a001000` | ISP | CAMSYS |
| 3 | `0x17001000` | VENC | VENCSYS |
| 4 | `0x12002000` | MJC | MJCSYS |
| 5 | `0x14021000` | MM | MMSYS |
| 6 | `0x15001000` | ISP | IMGSYS |

SMI common is `0x14022000`. Its bus-select register is a two-bit field per
larb. Larb0 stays on the first M4U path; larbs1--6 select the second path,
which is `F_MMU1_LARB(1) | ... | F_MMU1_LARB(6) = 0x1554`. This is not the
one-bit or larb0-only layout used by nearby MT6795 records.

The MT6797 M4U source defines its larb MMU-enable register as `0xfc0`. Linux's
existing SMI code already has the matching MT8167 helper
(`MT8167_SMI_LARB_MMU_EN = 0xfc0`) and a different MT8173 helper at `0xf00`.
The MT6797 compatible must use the former. The generic helper writes the
consumer-provided per-port bitmap; it does not require a new SMI driver.

The vendor code also gates each larb through the matching multimedia clock and
power domain. Live debugfs showed the nine SMI/larb topology clocks prepared
but gated, generally at 325 MHz, with no separate always-on M4U block clock.

## Linux 7.1.3 comparison

Linux already supplies the IOMMU domain, fault, TLB, 4-GiB, legacy IVRP, and
device-link machinery. The MT6797 addition is platform data and a binding, not
a new IOMMU core. Likewise, Linux's SMI common/larb framework supports the
required bus-select and per-port bitmap callbacks; MT6797 needs the exact
MT8167-style register generation and its own bus-select value.

The local patches add:

1. MT6797 IOMMU/SMI binding compatibles and a 71-port DT header;
2. dedicated MT6797 IOMMU flags and legacy-misc initialization;
3. MT6797 SMI common routing and MT8167-style larb configuration;
4. disabled M4U, common, larb, CAMSYS, and MJCSYS resources.

The analyzer and port checker report `PASS ports=71 slave0=63 slave1=8`.
Schema/object/full-series build checks are recorded in the experiment README;
they are compile evidence only because no patched image has been booted.

## Mainline bring-up boundary

Keep all fabric nodes disabled until a single consumer has a complete,
source-backed contract for:

- its larb and exact `iommus` port ID;
- clocks and power domain, including CAM/MJC providers;
- reset, interrupt, and runtime-PM ordering;
- buffer address width and 4-GiB remapping;
- an observable DMA transaction and fault-recovery path.

The first candidate should be one retained display DMA client, such as OVL0,
RDMA0, or the panel path, and it should be enabled one block at a time. Keep
the M4U/IOMMU association separate from Panfrost until a GPU-specific port is
proven; the current 71-port table contains none. Do not enable camera, video,
or writeback consumers merely because their larb nodes compile.

