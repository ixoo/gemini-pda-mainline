# Device-tree provenance of the Wi-Fi runs, and the service tree that reproduces it

Record, 2026-10-24. Owner direction: no further device work until the tree
the Wi-Fi runs boot can be regenerated from committed inputs.

## What booted

Every Wi-Fi candidate composed between 2026-10-17 and 2026-10-24 carried the
same board device tree as a binary: `board.dtb`, SHA-256 `25ab60f4…`,
28,671 bytes, copied by each experiment's candidate composer from the parent
candidate (`for name in ['initramfs.img', 'board.dtb']: copy(parent/name)`).
The transmit-DMA boot 2 candidate is the one exception: it booted that tree
with one entry added (`wifi-hif-dma`, `87a637c7…`, 28,703 bytes). No kernel
package on the host produces either tree (1,529 packaged MediaTek trees
compared), and the series' own board file differs from it in 21 nodes it
adds, 5 it lacks and 33 properties.

Where it came from: the closest packaged tree is the plain board tree of
the 2026-08-15 build lineage (`09ba93db…`, 40 property differences, all
later hand edits). The experiments of July and early October edited the
carried binary with `fdtput` and recorded each edit in their
`build-candidate.py` or `build-*-dtb.sh`: the keyboard and I2C5 enables
and timing (2026-07-18/19), the USB gadget and simple-framebuffer
restoration (2026-07-22), the WMT negotiation and chip-capture selection
(2026-10-03), WMT common init with the AFE resource and the coexistence
antenna mode (2026-10-06), the connectivity node's resources and
supplies (September). Three `consys` properties the driver depends on
(`mediatek,one-shot-wmt-common-init`, `mediatek,one-shot-wmt-negotiate`,
`mediatek,coex-antenna-mode`) existed in no source file, and the series'
board file selects `mediatek,one-shot-wmt-identity-capture` instead,
without the AFE resource, with the wireless child disabled, and with board
changes the carried tree never received (toprgu watchdog interrupt, iDVFS
I2C6 and legacy DA9214 description, DVFSP nvmem cells and backends, CPU
topology, A72 platform state, RAM-console node).

The 600 s gate, the delivery taxonomy, both lifetimes and the throughput
series were therefore produced on a tree reproducible only from the
candidate lineage, not from a build of the series.

## The fix: proposal 0261, the Wi-Fi service tree

[`0261`](../../patches/proposals/0261-arm64-dts-mediatek-add-the-Gemini-PDA-Wi-Fi-service-tree.patch)
adds `mt6797-gemini-pda-wifi-service.dts`, built on the current board file:
the service enables, the connectivity configuration the driver runs with,
and the later board changes undone. Proof, offline: the variant built in
the development VM against the boot-2 tree with
[`tests/dtdiff.py`](tests/dtdiff.py) (property-level comparison with
phandle references resolved to node paths through each provider's
`#*-cells`) shows zero nodes and zero properties differing; the only
delta is phandle numbering and property order (28,664 bytes against
28,703). Checkpatch reports the three reserved-memory compatibles as
undocumented; they are the booted tree's, kept for fidelity.

## Equivalence boot (predeclared)

Candidate composed from the package's own
`dtbs/mediatek/mt6797-gemini-pda-wifi-service.dtb`, never from a parent
candidate; kernel and configuration as transmit-DMA boot 2 (lifecycle
profile, transmit DMA admitted, receive PIO). Expected: identity and
kernel notes as the package states; firmware start; WMT common init
285/285; the DMA attach record as on boot 2; TX 2.6–3.4 Mbit/s per chunk,
RX about 7 Mbit/s host-side and 11–13 device-side. Any departure is the
finding and outranks everything queued behind it. Candidate composers take
the board tree from the package from here on.
