# Refuse missing HIF resources before the captured WLAN probe

The selected gen3 AHB HIF previously continued after a failed `wifi-dma`
clock lookup, and `HifPdmaInit()` marked DMA available even if its AP-DMA
register mapping failed. The native `glSetHifInfo()` returned `void`; its
caller could not reject either failure. The same caller returned a non-null
wireless-device pointer from some allocation-failure exits. These are
[pinned source findings](results/shared-resource-boundary.json), not observed
PDA failures.

The [experiment patch](patches/hif-admission/0001-wlan-refuse-missing-HIF-resources-in-captured-cycle.patch)
adds a captured-build-only Boolean HIF setup result. It checks the main HIF,
MCU and remap mappings, then acquires the `wifi-dma` clock and maps the AP-DMA
channel before the native `sdio_open()` call. The normal later DMA initializer
uses that mapping, publishes DMA operations only on success, and does not map
twice. A failed acquisition aborts capture; `wlanNetCreate()` releases its
partial mappings and returns null so `wlanProbe()` takes its existing
`NET_CREATE_FAIL` path. No AP-DMA register read, clock enable, SDIO function
enable or firmware request is added by these checks. Ordinary builds retain
their original source branches.

The [source receipt](results/hif-admission-sources.json) pins all four parent
and output files. The patch replays against the unchanged 54-patch prepared
source and reverses from its exact output. Linux 7.1.3 strict Checkpatch has
zero findings with legacy CamelCase and the synthetic, non-certifying sign-off
category excluded. The patch is selected as the 55th compile-only input. The
[complete Buildbox link](results/hif-admission-link.json) passed with a verified
package inventory, zero undefined symbols and the inherited 69 section
mismatches. Failure-injection review is still required before any boot
candidate.

This change does not propagate a later `clk_prepare_enable()` failure from the
void DMA clock callback, guarantee clock reference balance, isolate other
AP-DMA users, or make an effect-bearing radio cycle admissible. No device
write or radio action occurred.
