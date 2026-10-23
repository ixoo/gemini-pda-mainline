# MT6797 Wi-Fi TX DMA transfer contract — implementation held

Offline source audit, 2026-10-23. No DMA programming, clock/reset operation,
firmware command or device experiment was used. The retained map inputs were
verified against their preserved checksums. The existing
[DMA/EMI contract](../2026-09-05-mt6797-wifi-contract/HIF_DMA_CONTRACT.md),
[address-routing analysis](../2026-09-05-mt6797-wifi-contract/ADDR2_TRANSLATION.md)
and [shared-resource audit](../2026-09-07-mt6797-wifi-observer-feasibility/results/shared-resource-boundary.json)
remain applicable. They are reused, not superseded by guesses.

The reference is gen3 AHB SDIO-like HIF at public revision
`59e00a9144d782e148332009a835b99c43382467`. In this MT6797/OF build,
`HifPdmaInit()` selects **HIF PDMA**, not a generic GDMA backend.
[PDMA implementation](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/wlan/gen3/os/linux/hif/ahb_sdioLike/ahb_pdma.c),
[register definitions](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/wlan/gen3/os/linux/hif/ahb_sdioLike/include/hif_pdma.h).

| Item | Source-supported contract | Implementation consequence |
| --- | --- | --- |
| Register/channel layout | AP-DMA block `0x11000000`; dedicated HIF0 window `0x11000080+0x80`. Relative registers: INT_FLAG `0x00`, INT_EN `0x04`, EN `0x08`, RST `0x0c`, STOP `0x10`, FLUSH `0x14`, CON `0x18`, SRC `0x1c`, DST `0x20`, LEN `0x24`, internal-buffer size `0x38`, debug `0x50`, SRC_ADDR2 `0x54`, DST_ADDR2 `0x58`. | Own that channel, not the entire shared AP-DMA block. Do not infer a generic GDMA channel number from an IRQ macro. |
| Count | `DmaConf.Count` receives the padded HIF byte count; PDMA writes it directly to LEN bits 19:0. It is **bytes**, not words or the CMD53 block count. | Validate both HIF command count and DMA byte count before any transfer. Never silently truncate Count through the register mask. |
| Dir | TX=0, RX=1; programmed into CON bit 0. | TX: host memory source, HIF-aperture destination. RX reverses them. RX DMA remains out of scope. |
| Burst | Generic `hif.h` labels 1/4/8 DW as 0/1/2. The actual PDMA callback overrides Burst with `HIF_PDMA_BURST_4_4`, encoded **3** at CON bits 17:16; its enum is 1_4/2_4/3_4/4_4. | The generic enum is not the PDMA encoding. A 1/4/8-DW semantic interpretation of hardware encoding 3 is not established by these files; do not invent it. |
| Wsize, Ratio, Connect | Present in the generic config structure but never read or programmed by selected `HifPdmaConfig()`. | Not programmed fields in this selected backend. Do not copy another SoC's GDMA register semantics. |
| Fix_en | Callback forces FALSE, clears CON bit 1, and sets MT6797 BUS_INCR bit 31. The SDIO-like command separately selects FIXED_PORT mode. | Distinguish bus transfer controls from the logical FIFO-port selector. The files establish exact writes, not a complete bus-increment/fixed-address routing model. |
| SRC/DST and FIFO | TX maps host bytes with `dma_map_single(..., DMA_TO_DEVICE)` and sets destination to `HIF_DRV_BASE + SDIO_GEN3_CMD53_DATA`, nominal CPU-physical `0x180f1000`; RX uses that aperture as source. | It is not `HIF_BASE + logical_port`. Command setup chooses the port. CPU physical address is not automatically the DMA master's bus address. |
| Address extension | START unconditionally ORs bit 0 into both ADDR2 registers, including the FIFO side; prior register audit identifies bit 0 as address bit 32. | Effective host/FIFO bus alias and correct DMA mask remain UNKNOWN. Do not truncate a dma_addr_t, force bit 32, assume an IOMMU translation or borrow another master's 4-GB policy. |
| Rounding/alignment | TX initially rounds to four bytes; transfers reaching the configured block size round to whole blocks. RX byte-mode DMA rounds to eight bytes except WHISR. Selected block size is 512 bytes. These are transfer-length rules, not proof of all DMA address-alignment requirements. | Reuse existing [validated size arithmetic](../2026-09-05-mt6797-wifi-contract/src/hif_transfer_size.h). Initialize TX padding, map padded capacity, and preserve exact command count. Do not impose an invented universal eight-byte TX rule. |
| Eligible logical ports | RX selects WRDR0/WRDR1; TX selects **WTDR1 only** in this source. WTSR0/1 are not the selected packet TX DMA ports. | Keep all status/register traffic and unsupported ports on PIO. WHISR remains a four-byte status read and is explicitly excluded from DMA RX padding/selection. |
| Completion | Selected `CONF_HIF_DMA_INT=0`: poll channel INT_FLAG bit 0, acknowledge by writing that bit zero via RMW, disable INT_EN, then separately poll EN bit 0 clear. | Neither HIF host IRQ nor a generic AP-DMA IRQ is proof of PDMA completion. `MT_GDMA2_IRQ_ID` belongs to the disabled alternative registration, not an exercised completion assignment. |
| Errors/quiescence | Vendor paths include mapping-error refusal, fatal-state checks, poll timeouts and EN polling, but some timeout branches can return success or unmap without proven idle. `DmaStop()` only masks the interrupt; its STOP write is compiled out. | Do not copy timeout success or unmap on uncertainty. A new owner must retain mapping/buffer/resources until quiescence is proved. No fallback replay after possible FIFO consumption. |
| Clock/reset | `wifi-dma` uses shared `INFRA_AP_DMA`. Clock enable precedes CMD53 setup/DMA use, then channel lock/config/start, completion/ACK/EN handling, unlock/unmap and clock disable. Reset helper writes warm reset 1 and polls EN; if needed writes hard reset 2, waits 1 ms and clears reset. | No global AP-DMA reset or forced shared-clock shutdown. Clock failures must refuse. The vendor reset lacks sufficient final quiescence proof for a safe new error path. |

The [public transfer path](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/wlan/gen3/os/linux/hif/ahb_sdioLike/ahb.c)
programs SDIO-like CMD53 setup before using the aperture. Firmware must see the
same command bytes, port choice, transfer length/padding, ordering, page debit,
returned-page reconciliation, TX completion PID and timeout policy as PIO.
DMA completion is a bus-transfer result, never firmware command application or
returned credit. Do not merge the credit handshake with DMA completion.

## Admission decision for the requested TX-only implementation

**REFUSED while UNKNOWN:** effective bit-32 address routing/DMA mask, complete
bus/fixed-address semantics where not established, exact DMA-safe address
alignment, exclusive channel/common-resource ownership and bounded quiescence
on uncertain completion. The historical source/count and read-only resource
audits do not close these points. A correct PIO fallback remains the baseline;
flag-off or pre-submission ineligibility can select PIO, but uncertain DMA must
not replay a possibly consumed FIFO transaction.

No TX DMA build option or hardware path is added in this pass, and no DMA
comparison boot is queued. This follows the owner's explicit refusal-on-unknown
rule; implementation must wait for the missing transfer contract. The separate
[PIO throughput baseline](THROUGHPUT_BASELINE_PREDECLARATION.md) needs no DMA
assumption or rebuild and can proceed on the installed image.
