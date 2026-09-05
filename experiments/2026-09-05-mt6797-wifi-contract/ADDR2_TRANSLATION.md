# HIF ADDR2: selected writes established, translation unresolved

This is the bounded follow-up to [the HIF DMA contract](HIF_DMA_CONTRACT.md).
The retained kernel establishes unconditional channel extension writes and a
separate runtime 4G selector. It does **not** establish the HIF bus-address
translation. No DMA mask, driver, DT policy or hardware action is admitted.

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
receive 32-bit writes; these observations alone do not say how the fabric
interprets their combination with ADDR2.

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

## Comparators distinguish, rather than resolve, the meanings

| Public path | Selection and write | Limit of comparison |
| --- | --- | --- |
| `cqdma/cqdma.c`, `mt_config_gdma` | Low addresses are cast to 32 bits; `enable_4G()` sets or clears bit 0 in source/destination/jump “4G support” registers. | These registers are at `+0x40/+0x44/+0x48` on the non-MT6755 branch, not HIF `+0x54/+0x58`. This is a different engine; no retained CQDMA execution is claimed. |
| `drivers/i2c/busses/i2c-mt65xx.c` | On `support_33bits` variants, `mtk_i2c_set_4g_mode()` extracts address bit 32 and writes it to `+0x54/+0x58`. | The generic compatible table is not proof of the selected MT6797 HIF hardware. Shared offsets and “4G” names do not establish shared semantics. |
| Vendor `i2c/mt6797/` files | Inspected implementation/header do not supply the sought ADDR2 or `enable_4G` contract. | Retained configuration selects `CONFIG_MTK_I2C=y`; generic I2C code must not silently be treated as its executed implementation. |

Thus “4G” names cover both a global-mode policy and an address-bit policy in
these sources. HIF's unconditional writes are compatible with an assumed
global remapping environment, but this remains an inference. Interpreting
them simply as address bit 32 would also raise the unresolved fixed-endpoint
alias question: its low address is `0x180f1000`, yet its ADDR2 bit is set too.
No evidence here proves which alias reaches that endpoint or that an ordinary
33-bit concatenation applies to this channel.

## Exact remaining observation and decision boundary

For a future independently authorized session on the exact retained kernel,
the minimal mode observation is the existing boot log's `[EMI MPU] 4G mode`
or `Not 4G mode` message, attributed to that kernel and boot. An absent message
is inconclusive. If the log is unavailable, a separately reviewed read-only
observation of INFRACFG_AO `0x10001f00` bit 13 resolves the hardware selector
at the observation time; it does not prove its earlier value or HIF semantics.
No register read was performed or scheduled by this investigation.

A set selector would support the global-mode assumption; a clear selector
would expose a mismatch with unconditional HIF programming. Neither result
alone establishes effective DMA addresses. Passive ADDR2 readback would only
confirm the already-attributed writes. Translation still requires a matching
MT6797 HIF/APDMA register/fabric contract or independently attributable evidence
correlating a known DMA address and endpoint with the actual transfer target.
Such transfer evidence requires separate experimental admission, including
ownership, quiescence and observation budgets; it is not requested here.

Until that translation is established, choosing 32 or 33 bits, forcing an
upper bit, applying an address offset, or borrowing another engine's mode
policy would encode an unverified assumption. The earlier DMA and EMI
admission gaps remain open. This record owns the bounded result, not roadmap
ordering or a claim of hardware support.
