# AHB PIO admission: encoding known, bounded completion missing

Historical assessment: the blanket implementation gate below is narrowed by
[the subsequent MMIO/transport reassessment](PIO_TRANSPORT_DESIGN.md).
Its source observations remain valid; absence of a per-access timeout or
PIO-specific completion bit is not by itself a reason to forbid a transport.

The selected gen3 source does not supply the complete bounded PIO completion
contract required by this investigation. Therefore **no encoder is added**
and PIO is not admitted for first host-driver bring-up. This is a bounded
negative source result, not proof that PIO cannot work. DMA translation and
overall Wi-Fi usability requirements remain unchanged.

## Source-supported portion

All references use Planet revision
`c5b0be85017ad0c599725e8273842efdbecdd88a`, under
`drivers/misc/mediatek/connectivity/wlan/gen3/`.
[Eight exact source identities](results/pio-sources.json) were read in memory
over HTTPS. No backend, retained-input or device access was used.

`ahb_sdioLike/include/sdio.h:76-87` defines the command word fields: count
bits 0–8, logical port bits 9–25, increment bit 26, block-mode bit 27,
function bits 28–30 and write bit 31. Port transfers select fixed-address
mode. `sdio_open` selects Wi-Fi function 1 and block size 512, but also sets
`use_dma=1`; this is not evidence of an already-selected PIO-only startup.

`nicTxInitCmd` passes the aligned INIT record through `HAL_WRITE_TX_PORT` to
WTDR1 (`0x34`). Response reads select WRDR0 (`0x50`) or WRDR1 (`0x54`),
using WRPLR (`0x90`) low/high 16-bit lengths respectively. These are logical
ports encoded in the command word, not physical FIFO offsets. Command setup
is written at HIF `+0`; the repeated 32-bit data access is at HIF `+0x1000`.
[INIT TX](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/nic/nic_tx.c#L2259),
[port routing](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/include/nic/hal.h#L291).

Both port paths round size to four bytes, then round up to 512-byte blocks
when the initial rounded size is at least 512. A PIO-only configuration
(`use_dma=0`) does not take the extra RX eight-byte alignment. Merely falling
through to PIO with `use_dma=1` can still take that alignment for non-WHISR
reads. Thus the [existing DMA-oriented sizing helper](HIF_DMA_CONTRACT.md)
must not silently be reused as the PIO-only RX policy. The source assigns
counts into a nine-bit bitfield without a general overflow refusal; zero
count semantics and padded capacity would need explicit bounds in a future
encoder. Field widths alone do not validate a transfer.

## Exact completion gap

The RX/TX port helpers lock `HifLock` with `spin_lock_bh`, mask the HIF
interrupt at `+0x200`, write setup and execute a write barrier. In the PIO
branch they perform `count / 4` accesses to the data aperture, unmask and
unlock, and return true. There is no PIO-specific FIFO-ready, busy, terminal
status or error check in these loops, no timeout around the individual
access, and no partial-transfer abort/drain procedure.
[RX loop](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/os/linux/hif/ahb_sdioLike/ahb.c#L1011),
[TX loop](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/os/linux/hif/ahb_sdioLike/ahb.c#L1272).

A finite access count is a software-work bound, not evidence of a maximum
access latency or successful device consumption. The source does not
establish whether return from the final access is a sufficient completion
witness, or how an unavailable/full/empty/stalled endpoint terminates. This
does not assert that accesses actually stall; their failure behavior is the
missing contract. A write barrier alone does not supply that evidence.

`nicRxWaitResponse` does have an elapsed-time check while WRPLR reports zero,
then performs the port read when a nonzero length appears. That timer does
not wrap the synchronous MMIO operation or the PIO data loop. It supplies
neither PIO completion nor partial-transfer recovery. `nicTxInitCmd` returns
success after the port macro; that return is also not an independent
completion observation. Additionally, the port RX helper can return true
from its fatal/reset/firmware-own guard before reading any data. These
software success values must not be promoted to transfer evidence.
[Response wait](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/nic/nic_rx.c#L3633).

## Stop condition and unresolved requirements

The missing input is a matching MT6797 HIF PIO contract establishing FIFO
access preconditions, completion/error observability (or guaranteed
synchronous completion), bounded failure behavior, and safe handling of a
partially consumed command while ownership and resources remain held.
No undocumented busy bit, APDMA interrupt, generic SDIO response, arbitrary
timeout or reset is substituted. Host arithmetic fixtures could verify an
encoding but could not close this missing hardware contract.

This item stops here as requested. It supplies no transport, encoder,
driver-readiness claim, experimental candidate or action request. The earlier
power/lifetime, firmware attribution, calibration, EMI and DMA requirements
remain open. Prior handoffs and shared planning files are unchanged.
