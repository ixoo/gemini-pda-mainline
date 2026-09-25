# Refuse a failed WLAN DMA clock enable

The selected gen3 WLAN AHB HIF calls `DmaClockCtrl(TRUE)` before data-port
CMD53 setup. Its native callback returned `void`: it logged a failed
`clk_prepare_enable()` but both RX and TX continued into HIF register and DMA
work. A later unconditional disable could also run without a matching
successful enable. This is a [source finding](results/shared-resource-boundary.json),
not a failure observed on the PDA.

The [experiment patch](patches/dma-clock-admission/0001-wlan-refuse-failed-DMA-clock-enable-before-port-comm.patch)
makes the callback report success only in the captured build. The RX and TX
data-port paths refuse a missing callback or failed enable, set the existing
fatal-DMA flag, abort capture and return failure before CMD53 setup, HIF
interrupt masking or DMA programming. A failed enable does not call the
matching disable. Ordinary builds keep the original callback and call sites.
The selected build has `CONFIG_MTK_CLKMGR=n`; the alternate legacy clock-manager
branch is outside this experiment's status claim.

The [source receipt](results/dma-clock-admission-sources.json) pins all three
parent and output files. The patch replays against the 55-patch prepared
source, reverses from the exact output, and passes strict Checkpatch. The
[focused fixture](test-dma-clock-admission.py) runs the extracted native
callback with injected clock success and failure and checks the two native
port refusal sites precede command setup. The patch is the 56th compile-only
input; a complete Buildbox link is pending.

This does not establish concurrent AP-DMA ownership, all clock reference
balances, an effect-bearing radio protocol or a boot candidate. No device
write or radio action occurred.
