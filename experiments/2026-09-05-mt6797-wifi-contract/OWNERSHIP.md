# Selected gen3 shared-memory and register ownership

This offline source audit follows the first milestone at
`bbe78e38a3a089ec674a9106e2529ea20a14b04a`. It performs no device operation
and defines no boot candidate. Vendor source below is Planet commit
`c5b0be85017ad0c599725e8273842efdbecdd88a`; facts are independently described,
not imported vendor code. The selected gen3 files carry GPLv2 notices.

## Concrete dependency: two clients share one remap register

The common WMT owner and selected WLAN AHB driver both access **0x10001340**.
WMT configures the CONSYS-to-AP memory mapping in its low bits; WLAN's dynamic
CONSYS mapping changes the upper half and intends to preserve the low half
when its caller supplies an aligned address. Separate
drivers with independent read-modify-write operations can lose each other's
state. This is an immediate shared-provider requirement, not a reason to add
a second uncoordinated Wi-Fi register mapping.

| Resource | Source-visible use | Required mainline ownership boundary |
| --- | --- | --- |
| Post-LK `consys-reserve-memory` | Common reserved-memory callback supplies `gConEmiPhyBase`; historical capture had a 2 MiB no-map reservation | Resolve actual live reservation and validate extent/alignment; never substitute a historical physical base or expose all reserved RAM |
| Reservation `[base, base+0x80000)` | Selected WLAN loader conditionally copies MTKE sections at index 2 onward using destination low 20 bits and a 32-bit offset-plus-length check against 512 KiB | Exclusive bounded WLAN firmware extent, overflow-safe source/destination checks, ordering and cache/access contract; retain other regions |
| Reservation `[base+0x80000, base+0x100000)` | Common owner protects this half-MiB range as MPU region 19; maps and clears only its 343 KiB coredump/control extent | Separate WMT owner; preserve irreplaceable pending diagnostic records before any restart/clear path |
| Remaining reservation | These audited functions do not establish every user of the rest of the 2 MiB | Unknown ownership is reserved, not free workspace or DMA memory |
| MPU region 18 | WLAN source temporarily grants all listed domains access while copying, then restores a restricted policy | Do not reproduce blanket permissions; establish actual bus-master/domain mapping and the narrowest valid secure-world/provider contract, with rollback on failure |
| MPU region 19 | Common source applies a different policy to WMT shared memory | One coordinated protection authority; numeric vendor policy alone is not a reviewed Linux API |
| TOPCKGEN `0x10001340+4` | Common owner ORs encoded base/remap-enable bits; WLAN uses the upper 16 bits for temporary `0x180e0000` window remapping | Shared regmap/provider serialization and validated field masks, preservation of the other owner and failure restoration; no raw competing MMIO clients |
| Wi-Fi AHB HIF `0x180f0000+0x1100` | Selected driver maps HIF; netdev parent is the platform object | Exact transport owner with safe power state before any register read |
| CONSYS MCU `0x18070000+0x200` | WLAN AHB glue maps MCU registers also used by the common CONSYS owner | Explicit shared-resource contract; read-only diagnostic claims must account for live firmware and side-effect registers |
| AP-DMA `0x11000080+0x80` | Selected HIF PDMA header defines this CONFIG_OF channel | Validate exact DMA channel, address extension bits, IRQ, clock and protection ownership; do not reset the whole AP-DMA block |

The A53 worker reports preserved I2C5 and I2C6 DMA windows at
`0x11000380+0x80` and `0x11000500+0x80`, sharing `infra_ap_dma`, with no
new Wi-Fi/CONSYS node. Its exact retained DT remains that workstream's
responsibility. Non-overlapping offsets do not make a shared DMA clock,
reset, protection unit or firmware semaphore independent.

## What the selected source actually does

`wlanImageDividDownload()` sends the first two sections through HIF/PDA and
conditionally copies later sections into the first half-MiB of the
reservation. Its 32-bit offset-plus-length check neither establishes
overflow-safe validation nor reports a failure when the condition fails;
the path also ignores mapping/protection errors. It changes MPU permissions
around that copy. A new implementation must validate ranges independently
and propagate failures. The
[validated private MTKE metadata](results/firmware-mtke.json) has exactly two
sections in each route, but no hardware load was performed. A file-level CRC
pass therefore cannot admit the memory-protection changes.

The common WMT memory setup computes the mapping from the reservation base,
uses register offset `0x1340`, and maps/clears its control/coredump region at
`base+0x80000`. The old comment referring to another address does not override
the actual offset macro and source expression.

WLAN dynamic remapping checks that the upper half contains `0x180e` before
changing it and checks/restores its upper-half selection on unmap. The helper
combines the old lower 16 bits with the unmasked `consysAddr` argument, so
lower-half preservation requires that argument's low 16 bits to be zero;
the helper does not enforce this. These checks are useful evidence of field
sharing. They are not an atomic lease and do not prove another CPU or firmware agent cannot
change the register concurrently. A production provider must represent that
ownership explicitly, require aligned remap inputs and refuse unknown state.

The selected AHB chip-normalization code maps the low 16-bit chip field of
HIF `MCR_WCIR` from `0x0279` to software ID `0x6797`. This supplies a
**source naming relationship**
consistent with retained WMT label `MT279`; it is not an observed read of the
Wi-Fi RF silicon revision and does not establish a separate MT6625L chip.

## Source identities and reproduction

Read these raw files at the fixed commit and verify their SHA-256; no Linux
tree or firmware download is required. Existing identities for the gen3
loader/AHB/PDMA files are in [FIRMWARE_FORMAT.md](FIRMWARE_FORMAT.md).

| Additional file below `drivers/misc/mediatek/connectivity/` | SHA-256 |
| --- | --- |
| `wlan/gen3/os/linux/hif/ahb_sdioLike/include/hif.h` | `e9d18516cc49e6290203a827551ea7cb890af155d2ae9ddd0fd9ec03888fb87c` |
| `wlan/gen3/os/linux/hif/ahb_sdioLike/include/hif_pdma.h` | `898874f9f3180000a393fab0a13666fd4960364f3c4b7517a1f965f027213028` |
| `wlan/gen3/os/linux/hif/ahb_sdioLike/sdio_bus_driver.c` | `3cb1e502b0873038827d5a1e2cb537be08e784156394859d45f1d2a351f994c1` |
| `common/common_main/mt6797/include/mtk_wcn_consys_hw.h` | `3ee7631a95a12f5cddd860c213e51e75e1cb3146ca858a892aaae55b4d22fad1` |
| `common/common_main/mt6797/mtk_wcn_consys_hw.c` | `0ec8e9c1594626d0b31f2d2623927d614f63af4437c16df838e10e11258663ce` |

Primary references:
[WLAN section routing and MPU](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/common/wlan_lib.c#L828),
[WMT reservation and remap](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/common/common_main/mt6797/mtk_wcn_consys_hw.c#L1017),
[common offsets and coredump extent](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/common/common_main/mt6797/include/mtk_wcn_consys_hw.h#L191),
[WLAN remap field preservation](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/os/linux/hif/ahb_sdioLike/ahb.c#L1717),
[HIF chip normalization](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/os/linux/hif/ahb_sdioLike/ahb.c#L365).

## Readiness consequence

Current upstream Linux at `4d7d9486c04d917265f64c55bd23b2cc4fe7749c`
already matches `mediatek,mt6797-scpsys`, but its MT6797 domain table contains
VDEC, VENC, ISP, MM, AUDIO, MFG_ASYNC and MJC, with no CONN entry. Therefore
the existing generic power-domain framework is a reuse candidate, while
merely enabling that compatible does not supply the radio power domain.
The selected-source CONN reset/protection/rail contract must precede a
reviewable domain-data extension and active use.
[Current upstream controller](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/pmdomain/mediatek/mtk-scpsys.c)
has SHA-256 `9ce2b2c95a38bc4c7b801aff9b7c26da2dc8ec2e3fd34199adaedf1db3007226`.

Power-on, HIF register identification, DMA and firmware-start candidates
remain **planned**. A kernel implementation must enforce reservation extent,
field/memory ownership, finite transfer/timeout behavior and recovery before
an active probe. Preserve the current A53 baseline while those interfaces are
specified. The packet-format work can proceed independently in host fixtures;
neither this audit nor firmware redistribution uncertainty requires a new
device boot or full open-firmware replacement.
