# HIF ADDR2: bit-32 encoding established, bus routing unresolved

This is the bounded follow-up to [the HIF DMA contract](HIF_DMA_CONTRACT.md).
The retained kernel establishes unconditional channel extension writes and a
separate runtime 4G selector. A later register-reference check establishes the
ADDR2 fields' bit-32 meaning, but **not** how the fixed HIF endpoint is routed
on the bus. No DMA mask, driver, DT policy or hardware action is admitted.

## Inputs and method

Public comparisons use Planet revision
`c5b0be85017ad0c599725e8273842efdbecdd88a`; exact file identities are in
[the source ledger](results/addr2-sources.json). Public files were read in
memory, without another source checkout. The existing prepared retained kernel
and its embedded IKCONFIG were inspected in the RE VM. Private configuration,
input hashes and named-function disassembly remain in its restricted analysis
workspace. No new capture or source extraction was made. Retained input
attribution follows [the existing record](RETAINED_SPM_ATTRIBUTION.md).

## What the selected implementation establishes

The earlier retained `HifPdmaInit` and `HifPdmaStart` inspection establishes
channel base `0x11000080`, extent `0x80`, and read/OR/write of bit 0 at both
`+0x54` and `+0x58` on every start. Neither write is conditional on a DMA
address, its upper bits, transfer direction, or `enable_4G()`. The same writes
appear in public `ahb_pdma.c`, `HifPdmaStart`. They apply to the fixed HIF
endpoint as well as the memory endpoint. Low source/destination registers
receive 32-bit writes; these observations alone did not identify the extension
fields' encoding or the resulting bus route.

## Register-reference check, 2026-09-26

The [96Boards-hosted X20 register table](https://www.96boards.org/documentation/consumer/mediatekx20/additional-docs/docs/MT6797_Register_Table_Part_1.pdf)
is a 1,637-page PDF, SHA-256
`e8ef503a32a8bb318a000fe6727d2bcdaa3557992a0ffed344e9de37acc2caff`.
Only the HIF channel entries on PDF pages 416–419 were inspected as private
source evidence. The reference labels bit 0 of `AP_DMA_HIF_0_SRC_ADDR2` at
`0x110000d4` as source address bit 32, and bit 0 of
`AP_DMA_HIF_0_DST_ADDR2` at `0x110000d8` as destination address bit 32.
The memory/FIFO roles swap between TX and RX; the corresponding lower
32 bits are at `0x1100009c` and `0x110000a0`. This resolves the local HIF
register encoding independently of the I2C comparator below. The PDF is
marked proprietary and remains ignored private reference material; no page or
table is copied here.

The register labels do not describe the MT6797 fabric's 4G-mode remapping or
the alias by which a fixed FIFO whose low address is `0x180f1000` is reached
when its bit-32 field is set. They also do not show the executing boot's DMA
addresses. Thus a driver still cannot select an address mask or copy the
vendor's unconditional extension writes solely from this reference.

The retained embedded configuration has `CONFIG_ARM64=y`,
`CONFIG_ZONE_DMA=y`, `CONFIG_SWIOTLB=y` and `CONFIG_MTK_LM_MODE=y`.
The public board defconfig also selects LM mode. This is compile-time support,
not evidence that the runtime selector was set for a particular boot.

The retained `dram_4gb_init` reads INFRACFG_AO `+0xf00`, tests bit 13 and saves
zero or one in `enable_4gb`; retained `enable_4G` returns that variable. This
matches public `emi_mpu.c:2401-2432`, including its early-init registration.
The DT resource base is `0x10001000`, so the selector is physical
`0x10001f00` bit 13. The initializer reads hardware; it does not configure the
mode. Public EMI-MPU initialization uses the saved Boolean to select its own
physical offset (zero versus `0x40000000`). That MPU accounting choice is not
an APDMA address-translation specification.

`support_4GB_mode()` in the DRAM driver instead compares reported DRAM size
with 4 GiB. It is a different predicate and cannot replace the register test.
Historical M4U mode observations likewise do not prove HIF routing or the
selector value in a new boot.

## DMA API boundary

At the public pin, ARM64 `phys_to_dma` and `dma_to_phys` are identity casts
(`arch/arm64/include/asm/dma-mapping.h:64-72`). The SWIOTLB mapping path either
returns the page physical address plus offset or a bounce-buffer address,
subject to device capability and forced bouncing (`lib/swiotlb.c:735-765`).
It does not force bit 32 from `enable_4G()`.

Retained `swiotlb_map_page` was checked through the normal direct-return and
bounce-success paths: the computed address is checked against the device mask
and returned, without an injected ADDR2 bit. Retained `__swiotlb_map_page`
preserves that result across cache maintenance and returns it unchanged.
This corroborates that mapping path; it does not inspect a live Wi-Fi device's
DMA-ops pointer or exclude a device-specific override elsewhere. A successful
DMA API mapping is not itself proof of the HIF channel's effective bus address.

## Separate-engine comparators

| Public path | Selection and write | Limit of comparison |
| --- | --- | --- |
| `cqdma/cqdma.c`, `mt_config_gdma` | Low addresses are cast to 32 bits; `enable_4G()` sets or clears bit 0 in source/destination/jump “4G support” registers. | These registers are at `+0x40/+0x44/+0x48` on the non-MT6755 branch, not HIF `+0x54/+0x58`. This is a different engine; no retained CQDMA execution is claimed. |
| `drivers/i2c/busses/i2c-mt65xx.c` | On `support_33bits` variants, `mtk_i2c_set_4g_mode()` extracts address bit 32 and writes it to `+0x54/+0x58`. | This is a separate engine; the HIF bit-32 meaning is now established by its own register reference, not by borrowing I2C behavior. |
| Vendor `i2c/mt6797/` files | Inspected implementation/header do not supply the sought ADDR2 or `enable_4G` contract. | Retained configuration selects `CONFIG_MTK_I2C=y`; generic I2C code must not silently be treated as its executed implementation. |

Thus “4G” names cover both a global-mode policy and an address-bit policy in
these sources. HIF's unconditional writes program bit 32 for both endpoints;
their correctness under the observed global mode remains an inference. In
particular, the fixed endpoint's low address is `0x180f1000` while its bit-32
field is set. No evidence here proves which bus alias reaches that endpoint
or that CPU-physical-address concatenation is the right driver policy.

## Exact remaining observation and decision boundary

The [retained Gemian reference](../2026-09-26-gemian-wifi-reference/results/4g-mode-reference.json)
now resolves that minimal boot-time mode observation for two later,
individually identified instrumented boots. Each checksum-bound log contains
one `[EMI MPU] 4G mode` message and no `Not 4G mode` message. The exact
Gemian source revision emits the positive message only after the early
`dram_4gb_init` read finds INFRACFG_AO `0x10001f00` bit 13 set and assigns
`enable_4gb=1`. This supports the global-mode assumption for those early
boot moments, not selector stability through each transfer or the value in
the pending v3 or any mainline boot. No new register read or device action
was performed for this finding.
The same pinned register reference, PDF pages 187–188, independently identifies
INFRACFG `0x10001f00` bit 13 as the DDR 4GB-support enable. It does not define
the HIF FIFO's bus alias or the DMA master's address translation.

The set selector and register bit labels do not establish effective bus
addresses. Passive ADDR2 readback would only confirm the already-attributed
writes. Routing still requires a matching MT6797 fabric/4G-mode contract or
independently attributable evidence correlating a known DMA address and
endpoint with the actual transfer target.
Such transfer evidence requires separate experimental admission, including
ownership, quiescence and observation budgets; it is not requested here.

Until that routing is established, selecting a DMA mask, forcing an upper bit,
applying an address offset, or borrowing another engine's mode policy would
encode an unverified assumption. The earlier DMA and EMI
admission gaps remain open. This record owns the bounded result, not roadmap
ordering or a claim of hardware support.
