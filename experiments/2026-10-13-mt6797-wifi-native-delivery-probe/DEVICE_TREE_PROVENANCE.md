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

## The connectivity node, property by property

Built from the committed series alone (`9d276157`, plain board tree) and
compared with the booted tree with `tests/dtdiff.py`, the
`consys@10001340` node differs in exactly these items; nothing else in
that node differs.

| Item | Committed series | Booted tree | Why the booted value is the wiring the driver runs with |
|---|---|---|---|
| `mediatek,one-shot-wmt-negotiate` | absent | present | the connectivity owner negotiates the WMT mode on the scan line before Wi-Fi start; every lifecycle boot shows `WMT negotiation: result=0` |
| `mediatek,one-shot-wmt-common-init` | absent | present | the owner runs the 285-step common initialisation; every lifecycle boot shows `common init 285/285`; without it the AFE stage never runs |
| `mediatek,coex-antenna-mode = <1>` | absent | `<1>` | the coexistence antenna setting the common init programs; the value the vendor firmware is configured with on this board |
| `reg`/`reg-names` entry `afe` (`0x180b6000`, `0x100`) | absent | present | the AFE register window the common init owns; the owner refuses common init without it |
| `mediatek,one-shot-wmt-identity-capture` | present | absent | an earlier isolated chip-capture mode (2026-10-03); the binding makes it exclusive with negotiation |
| `wifi { status }` | `"disabled"` | absent (enabled) | the wireless child must probe for the station driver to exist |

All six are board wiring and configuration, not driver policy, so they
belong in a board DTS. 0261 sets them in a variant rather than in the base
board file because the base file still serves the chip-capture and
Bluetooth profiles that select the other mode; moving the AFE resource and
the antenna mode into the base file is the natural next step once those
profiles are retired.

## The composer was the defect

The candidate composer copied `board.dtb` and `initramfs.img` from the
parent candidate, so nothing validated them against the build. From this
record on, composers take the kernel and the board tree from the build
package and declare anything inherited with its hash
([`hosts/candidate_inputs.py`](hosts/candidate_inputs.py)): the RAM root
is the one inherited artefact (no kernel build produces it) and is
recorded as such in the candidate record; composition refuses when a
declared hash does not match or when a parent's tree differs from the
build's output beyond phandle numbering
([`tests/candidate-inputs-test.py`](tests/candidate-inputs-test.py) is
the fixture: a parent with a differing tree is refused, a wrong hash is
refused, a missing tree is refused, an equivalent tree is accepted).

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
