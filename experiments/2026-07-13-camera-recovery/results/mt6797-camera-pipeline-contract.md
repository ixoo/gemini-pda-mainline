# MT6797 camera pipeline contract

## Status

The pinned Planet tree contains a substantial MT6797 camera ISP/SENINF
implementation, but it is a vendor character-device ABI rather than a Linux
media-controller driver. This result recovers the resource, interrupt, clock,
SENINF, CAMSV, and DMA boundaries needed to design a new mainline backend.

No camera register was read or written on hardware. No sensor stream, I2C
transaction, GPIO transition, regulator transition, or DMA operation was
performed.

## Provenance

The source-only analyzer is
[`analyze-mt6797-camera-pipeline.sh`](../scripts/analyze-mt6797-camera-pipeline.sh).
It reads Git objects from Planet commit
`c5b0be85017ad0c599725e8273842efdbecdd88a` and compares Linux `7.1.3` in the
development VM. Vendor source is not copied into this repository.

| Source | SHA-256 |
| --- | --- |
| vendor `camera_isp.c` | `d0d95f82f0feff270f529fa74cca7d0e4d35ba8f4c6235c685710084b306ac05` |
| vendor `camera_isp.h` | `8e2341024a19087077222baa04c1c54c0a6318bc5b5d26a4cf6ca513e48ce979` |
| vendor `mt6797.dtsi` | `eaac86c8752ebd8ddf18b831eb3bc52a08f87475a213bb521650bf95dabb3e5e` |
| vendor `m4u_platform.h` | `8ae0f40beafa3d01dc10b862540087c156d2647092b232fc10f379aebcc5bf8d` |
| Linux `mt6797.dtsi` | `35d0414a91f6798d1f9ebfee0086a4dfb2de85ea3317132536915ae347372531` |
| Linux `clk-mt6797-cam.c` | `f049c889db24564e3bd92357c71536a07e90d049a061d5c0558a7cbcc7a03467` |
| Linux `mt6797-clk.h` | `20341c99924a7e9e71370eef12817f9d4fafee601692ce26c069eddc4ca40b60` |
| Linux `mt6797-larb-port.h` | `1187eab0c1fdaf9a84b3040086d91812e4786c057b9945d69a874bf04c1faa9b` |

## Vendor platform shape

`camera_isp.c` registers `/dev/camera-isp` with private `ioctl` and `mmap`
operations. Its device-tree match table requires this ordered set of platform
nodes:

1. `imgsys_config`
2. `dip_a`
3. `camsys_config`
4. `camtop`
5. `cama`
6. `camb`
7. `camsv00`, `camsv01`, `camsv10`, `camsv11`, `camsv20`, `camsv21`

The driver indexes the mapped devices by this order, requests per-node IRQs,
and exposes one aggregate character device. This ordering and aggregate UAPI
must not be reproduced in a V4L2 media graph.

The vendor DTS additionally declares:

| Block | Base and size | IRQ |
| --- | --- | --- |
| IMGSYS config | `0x15000000` + `0x1000` | none in this driver |
| DIP A | `0x15022000` + `0x4500` | SPI260, level-low |
| CAMSYS config | `0x1a000000` + `0x1000` | none |
| CAMTOP | `0x1a003000` + `0x1000` | SPI247, level-low |
| CAM A/B | `0x1a004000`/`0x1a005000` + `0x1000` | SPI248/SPI249, level-low |
| CAMSV00..21 | `0x1a050000`..`0x1a055000` + `0x1000` | SPI252..SPI257, level-low |
| SENINF0..7 | `0x1a040000`..`0x1a047000` + `0x1000` | no per-node IRQ in this DTS block |

There is an important legacy overlap: `kd_camera_hw1` and `kd_camera_hw2`
also claim `0x1a040000` (SENINF0). They are vendor wrappers, not independent
resources for a mainline driver.

## SENINF and MIPI boundary

The vendor ISP initialization explicitly maps `mediatek,seninf0` through
`mediatek,seninf3` with `of_find_compatible_node()`. Its backup/restore code
also treats IMGSYS offsets beginning at `0x8000` as SENINF-related registers,
including mux, timing-generator, CSI2, and NCSI2 fields. The DTS declares
SENINF4..7, but this legacy initialization path does not map them into the
four global SENINF pointers. That is source evidence of a split between the
declared hardware inventory and the configured path, not proof that those
inputs are unusable.

The auxiliary windows are MIPI analog at `0x10217000` and GPIO at
`0x10002000`. The SLS sensor source selects a two-lane MIPI-NCSI2 link, but
the receiver lane routing, PHY timing, data-type filters, and board endpoint
are not recovered by this source audit. They must be represented by a new
receiver driver and a verified DT graph, not inferred from the sensor's
`mipi_lane_num` field alone.

## Clock and interrupt ownership

The vendor ISP driver obtains these clock handles and enables them as one
private camera-ISP transaction:

`ISP_SCP_SYS_DIS`, `ISP_MM_SMI_COMMON`, `ISP_SCP_SYS_ISP`, `ISP_IMG_LARB6`,
`ISP_IMG_DIP`, `ISP_IMG_DPE`, `ISP_IMG_FDVT`, `ISP_CAM_LARB2`,
`ISP_CAM_CAMSYS`, `ISP_CAM_CAMTG`, `ISP_CAM_SENINF`, and `ISP_CAM_CAMSV0`–`2`.

CAM interrupts distinguish frame/timing signals (`VS`, `TG`, exposure-done,
pass-1, `SOF`) from DMA-done status for IMGO, UFEO, RRZO, EISO, FLKO, AFO,
LCSO, AAO, BPCI, LSCI, and PDO. CAMSV has a smaller signal set and its own
error mask. This is useful interrupt semantics, but the vendor tasklets and
wait queues are coupled to the private ioctl ABI.

The source exposes six CAMSV register/IRQ nodes while the configured ISP clock
set only names CAMSV0–2. The M4U setup likewise configures only CAMSV0–2
ports. This discrepancy must remain explicit until a hardware or trace-based
explanation is found; it is unsafe to enable all six consumers by node count.

## DMA and memory boundary

The vendor M4U table maps camera output and input clients as follows:

| Larb | Ports | Functions |
| --- | --- | --- |
| Larb2 | 0–13 | `CAM_IMGO`, `CAM_RRZO`, `CAM_AAO`, `CAM_AFO`, `CAM_LSCI_0/1`, `CAM_SV0/1/2`, `CAM_LCSO`, `CAM_UFEO`, `CAM_BPCI`, `CAM_PDO`, `CAM_RAWI` |
| Larb6 | 0–9 | `CAM_IMGI`, `CAM_IMG2O`, `CAM_IMG3O`, `CAM_VIPI`, `CAM_ICEI`, `CAM_RP`, `CAM_WR`, `CAM_RB`, `CAM_DPE_RDMA`, `CAM_DPE_WDMA` |

Linux 7.1.3 already has matching MT6797 clock gates, `camsys`/`imgsys`
providers, disabled `larb2`/`larb6` nodes, and the same MT6797 larb-port
identifiers. These are reusable platform data, not proof that a capture node
is safe to enable. The vendor buffer path relies on the multimedia ION heap,
M4U port configuration, dma-buf import, and private buffer queues. Mainline
should use standard dma-buf/VB2/IOMMU ownership and never copy the vendor ION
or ioctl ABI.

## Linux 7.1.3 boundary

Linux has no matching SENINF, CSI2 receiver, CAM/CAMSV capture, or MT6797 ISP
V4L2 media-controller driver. It does have reusable clock, SCPSYS, SMI/IOMMU,
media-controller, fwnode-endpoint, and dma-buf frameworks. The required new
work is therefore:

1. an MT6797 SENINF/CSI2 receiver with verified lane routing and timing;
2. CAM/CAMSV capture entities and interrupts, initially limited to one proven
   path;
3. a standard V4L2 media graph connecting the SP5509 sub-device, receiver, and
   capture node; and
4. verified M4U larb/port attachment and buffer ownership.

The private `/dev/camera-isp`, Android camera HAL, ION heap assumptions, and
vendor `camera_hw` wrappers remain evidence only.

## Safe next gates

- Keep all camera resources and consumers disabled in the Gemini DT.
- Recover the exact SENINF/NCSI2 programming sequence and board endpoint from
  source, immutable ELF, or controlled traces before enabling a receiver.
- Start with one SP5509 mode, one receiver path, and one verified larb2 output;
  do not enable all CAMSV nodes based only on their DTS presence.
- Attach standard V4L2/VB2/dma-buf interfaces only after IRQ and IOMMU fault
  handling are independently validated.

The [SP5509 source contract](sp5509-source-contract.md) supplies the sensor
side of this boundary. It does not establish the physical slot or receiver
endpoint.
