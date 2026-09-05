# Gen3 HIF DMA and EMI resource contract

This bounded offline item follows `850b05698d82c97655cba9552a2eb38d7c36d9ff`.
It uses the existing Planet public pin and Linux API pin listed in the
[source ledger](results/hif-dma-sources.json), plus the previously retained
kernel/board mappings. Earlier evidence is unchanged. No device, radio,
calibration, capture or kernel-build action was performed.

## Decision

Packet DMA and CONSYS reserved EMI are different interfaces. The selected
packet path maps ordinary host buffers to one AP-DMA channel and transfers
through the HIF data aperture. It does not allocate packet buffers from CONSYS
reserved EMI. That reservation contains firmware and shared WMT state and
cannot become a generic DMA pool.

The channel and low address registers are attributable, but the meaning of its
unconditionally enabled address-extension bits is not resolved. Consequently
neither a 32-bit nor a 33-bit DMA mask/encoding is admitted by this record.
A DMA backend also needs exclusive channel ownership and a proven quiescence
path before it can safely release mappings after error or removal.

One independently written component is ready for integration review now:
[transfer-size validation](src/hif_transfer_size.h). It computes the selected
HIF padded length and command count without mapping memory, encoding addresses,
selecting an IRQ or accessing hardware. It does not admit the unresolved backend.

## Engine, endpoint and interrupts

| Resource | Selected source / retained mapping | Required ownership |
| --- | --- | --- |
| HIF | `0x180f0000`, extent `0x1100`; CMD53 data aperture at `+0x1000` | One host driver; safe CONSYS power and host ownership before access |
| HIF PDMA | AP-DMA `0x11000080`, extent `0x80` | One serialized channel owner; no overlapping full-block or channel mapping |
| Packet endpoint | Both directions use bus endpoint corresponding to `0x180f1000`; command setup selects the logical port | Do not DMA directly to the logical port offset or assume CPU physical equals DMA bus address |
| Host IRQ | Wi-Fi DT SPI 283, level low | HIF host interrupt, not an observed PDMA-completion IRQ |
| Generic AP-DMA node | DT covers `0x11000000..0x11000fff`, SPI 97 | Its interrupt does not establish a per-HIF-channel completion assignment |
| Other AP-DMA users | I2C and BTIF occupy other channels; retained BTIF TX/RX windows are `+0xa00/+0xa80` | Shared clock/reset/protection remain coordinated even when channel windows do not overlap |

The selected header enables DMA but sets `CONF_HIF_DMA_INT=0`. The OF IRQ
registration installs the HIF handler; PDMA completion is polled from channel
`INT_FLAG` bit 0. Its acknowledgement writes that bit as zero through a
read-modify-write. Do not substitute a write-one-to-clear operation, use the
host IRQ as completion, or infer a dedicated DMA IRQ from the generic node.
The HIF handler masks its source and wakes its service thread; these are
separate interrupt responsibilities.
[PDMA registers](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/os/linux/hif/ahb_sdioLike/include/hif_pdma.h#L58),
[IRQ selection](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/os/linux/hif/ahb_sdioLike/ahb.c#L535).

RX packet DMA is selected only for `MCR_WRDR0/WRDR1`; TX only for `MCR_WTDR1`.
This is an SDIO-like command interface on AHB, not proof of a native SDIO bus
or compatibility with an existing matching-family DMA/network driver.
[Transfer selection](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/os/linux/hif/ahb_sdioLike/ahb.c#L867).

## Address width: real low registers, unresolved upper semantics

`HifPdmaConfig()` writes source/destination through 32-bit registers at
channel `+0x1c/+0x20` and masks length to 20 bits at `+0x24`. Although its
software address members are `ULONG`, that does not preserve addresses above
32 bits in those writes. `HifPdmaStart()` separately ORs bit 0 into **both**
`+0x54/+0x58`, independent of the mapped address and including the HIF endpoint.
The source names them address-extension fields but does not derive them from
`upper_32_bits(dma_addr)` or explain their bus-alias semantics.
[Configuration and start](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/os/linux/hif/ahb_sdioLike/ahb_pdma.c#L232).

The existing retained kernel's named `HifPdmaInit` confirms the channel mapping;
its `HifPdmaStart` confirms both unconditional bit sets. These are static binary
facts, not successful DMA-address observations. The retained board DT contains
the HIF and generic AP-DMA nodes, without a separately declared HIF channel.
Its reserved-memory description is an input to LK, not proof of the current
post-LK allocation. Private identity references, disassembly and selected DT
blocks stay in `~/reverse-engineering/work/wifi-hif-dma-20260905/`.

A same-valued extension bit or another MT6797 block's 4-GB mode cannot establish
this channel's translation. The concrete missing evidence is how channel
`ADDR2` changes the effective host-buffer and HIF-endpoint bus addresses,
including the retained platform's DRAM alias mode and any DMA/IOMMU translation.
Refuse active DMA until that contract fixes the device mask and lossless address
encoding. Truncation plus forced extension bits is not an acceptable substitute.

## Smallest Linux DMA API boundary

Once those admission conditions are established, use the device representing
the actual AP-DMA master and its firmware-described DMA translation. The vendor
uses the Wi-Fi platform device for `dma_map_single()`; an upstream split
controller/client design must use the controller's mapping domain instead.
An inline channel owner may use the host device only after the same bus-domain
contract is established. Do not use a convenient unrelated device merely to
obtain an address that fits.

- Set the established streaming DMA mask with `dma_set_mask()` and refuse
  failure before allocation/mapping. No numeric mask is selected here.
- Use a dedicated, DMA-safe linear packet buffer with capacity covering the
  padded transfer and no unrelated object sharing its DMA cache lines. Initialize
  all TX padding before mapping. Do not map stack, arbitrary `vmalloc` storage,
  or a reserved firmware window as an ordinary streaming buffer.
- Map TX with `DMA_TO_DEVICE`, RX with `DMA_FROM_DEVICE`; check
  `dma_mapping_error()` and retain the full `dma_addr_t`. Encode it only through
  the established channel-address contract. The mapping must cover padded
  bytes, not just payload bytes, and be unmapped with the same device/size/direction.
- Keep CPU access out of the mapped ownership interval. For deliberately reused
  mappings, use the matching `dma_sync_single_for_cpu/device()` ownership calls.
  Coherent allocation would not eliminate the channel ordering requirements.
- Resolve the FIFO endpoint in the master's bus address space. If the platform
  requires `dma_map_resource()` for that MMIO resource, check its result and keep
  its mapping until quiescence. That API must not be used to map the RAM-backed
  CONSYS reservation.

[DMA mapping contract](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/Documentation/core-api/dma-api-howto.rst#L580),
[resource mapping restriction](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/Documentation/core-api/dma-api.rst#L297).
No scatter-gather descriptor format or compatible DMAengine provider is
established by the selected single-transfer source. Do not invent one.

A completion flag alone does not authorize freeing memory. The source's
`HifPdmaStop()` only disables its interrupt; its stop/idle loop is compiled out.
The caller separately polls EN, but can break and unmap without proving idle.
Its reset helper can escalate to a hard channel reset without a final idle
proof. A new owner must serialize command setup, channel programming and
completion; refuse new work after an uncertain transfer and retain the buffer,
mapping and prerequisites until proven quiescent. A probe-error/devres/remove
path that releases them anyway is not ready. No whole-AP-DMA reset or forced
shared clock shutdown is justified.
[Stop and completion](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/os/linux/hif/ahb_sdioLike/ahb_pdma.c#L310).

## EMI is shared firmware memory

The [existing ownership record](OWNERSHIP.md) separates the first 512 KiB WLAN
firmware extent, the following 512 KiB WMT region, and the remaining reservation
whose users are not established. Preserve that separation. Require the actual
post-LK base, extent, alignment and explicit common-owner grant; absence or
unknown ownership is refusal. A `no-map` reservation is not a reusable
`shared-dma-pool`, and unused-looking space is not permission to allocate.

The selected loader copies later firmware sections through a CPU mapping and
changes MPU region 18. It temporarily requests unrestricted access in all eight
domains, then leaves domain 2 unrestricted and others forbidden. Region 19's
WMT policy permits domains 0 and 2. The permission macro's argument order makes
those domain numbers explicit, but this does not prove the complete mapping
from every AP-DMA/CONSYS/BT/GNSS master to a domain, nor isolation between
CONSYS clients sharing a domain. Do not replay the blanket permission change.
[WLAN MPU/copy path](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/common/wlan_lib.c#L838),
[permission encoding](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/include/mt-plat/mt6797/include/mach/emi_mpu.h#L278).

WMT and WLAN also share remap register `0x10001340`. Memory ownership, MPU
policy and remap updates need the common owner; a Linux DMA mapping alone does
not configure them or make the firmware ranges exclusive. In particular, the
PDMA initializer's old region-12 programming is under `#if 0`; its log text
must not be promoted to an executed memory-protection contract.

## Delivered arithmetic component

The header implements only the selected 512-byte block sizing rules: initial
four-byte rounding, block mode when that result reaches 512, and eight-byte
RX rounding in byte mode. It rejects zero length, insufficient padded capacity,
count overflow and size overflow. It returns padded DMA bytes, block-mode
selection and the nine-bit command count; it emits no hardware word or address.

The accepted block-mode maximum is 511 blocks (261632 bytes). Zero-count special
encoding is deliberately not assumed for this private HIF. Thus RX payloads
505–508 are refused: the selected byte-mode calculation rounds them to 512,
which does not fit nine bits. Payload 509 enters block mode and uses count 1.
This is an explicit conservative refusal policy, not a claim that hardware
cannot implement a special zero-count transfer. Callers must not silently split
or change framing when refused.
[Selected count layout](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/os/linux/hif/ahb_sdioLike/include/sdio.h#L76).

The helper and [30-case fixture](src/hif_transfer_size_test.c) are original
GPL-2.0-only code, not copied vendor implementation. The selected HIF sizing
sources carry GPLv2 notices. Host tests cover padding boundaries, maximum count,
capacity refusal, empty output on failure and `SIZE_MAX` overflow. This prepares
one arithmetic component; the kernel include path and an active driver are not
built or selected. Exact checks are in the
[validation receipt](results/hif-dma-validation.txt).
