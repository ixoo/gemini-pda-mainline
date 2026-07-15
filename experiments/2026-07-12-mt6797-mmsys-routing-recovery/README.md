# Experiment: MT6797 MMSYS routing recovery

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-12-mt6797-mmsys-routing-recovery` |
| Status | `completed` |
| Subsystem | MT6797 multimedia routing and reset controller |
| Device variant | Gemini PDA running Gemian |
| Date | 2026-07-12 |
| Investigator | Repository maintainer with Codex assistance |

## Question

What routing registers, mux values, reset banks, and GCE address tuple must
Linux 7.1 model to construct the Gemini's active OVL/RDMA/UFOE/DSI display
path without inheriting the vendor aggregate `dispsys` ABI?

## Provenance and safety

The static source is exact Gemian commit
`d388d350cb2dda8f23b99be6fa5db9628896e87f`, principally MT6797
`ddp_path.c`, `ddp_reg.h`, and `ddp_dump.c`. The mainline comparison is the
repository's checksum-verified Linux 7.1.3 tree.

The collector reads platform, DT, and log state only. Its explicit
`--read-history` path reads `/sys/kernel/debug/mtkfb`, whose read callback was
audited in the pinned source. The retained driver ring buffer may contain
kernel and DMA addresses, so the complete capture stays in Git-ignored
`artifacts/`; the collector emits only fixed routing and mutex lines. Direct
MMIO through `devmem` is forbidden: DEVAPC rejected the earlier audited probe,
all returned zeros were invalid, and retrying adds no information.

## Associated code

- [`scripts/collect-live-mmsys-routing.sh`](scripts/collect-live-mmsys-routing.sh)
  collects the safe live provider/DT view and an opt-in filtered history.
- [`scripts/check-routing-contract.py`](scripts/check-routing-contract.py)
  checks all recovered register offsets, the 29 high-level Linux routes, the
  active path, both reset banks, and the GCE tuple against the pinned trees.

## Observations

The private source-audited capture is
`artifacts/device-inventory/20260712-live/display-state-mtkfb.txt`, SHA-256
`1f709ae04ff506635423d39e9b122a7dac8142efc635bceb464ea407df8a3ded`.
It says the display was asleep at query time, but its retained active boot
dump records `ovl0 to dsi0 is connected`, the complete scenario, and the
register values normalized in
[`results/runtime-summary.txt`](results/runtime-summary.txt).

The route is:

```text
OVL0-2L -> OVL1-2L -> OVL0 virtual -> COLOR0 -> CCORR -> AAL ->
GAMMA -> OD -> DITHER -> RDMA0 -> PATH0 -> UFOE -> DSI0
```

`OVL0` and `PWM0` are controlled alongside the path but are skipped by the
vendor routing connector. `OVL0 virtual` and `PATH0` are register-only routing
nodes, so Linux must collapse them into multiple writes associated with each
adjacent high-level component pair. Linux's MMSYS core supports that model by
executing every table entry whose source and target pair match.

The complete vendor graph becomes 29 representable high-level routes.
`SPLIT0` and dual-DSI routes cannot yet be expressed because Linux 7.1 has no
matching DDP component ID; this is a documented dual-panel gap and is not part
of the Gemini's active single-DSI path.

The vendor defines active-low software-reset banks at offsets `0x140` and
`0x144`. Both were `0xffffffff` in the retained active dump, establishing 64
linear reset bits. The panel's `LCM_RST_B` output at `0x150` is a separate
one-bit signal, not a third software-reset-bank member; the active vendor panel
callback writes it directly. MMSYS occupies the complete `SUBSYS_1400XXXX` GCE
window, offset zero, size `0x1000`.

## Result

Patches 31–32 add the dedicated route table and reset-provider data, then
expose `#reset-cells` and the GCE client tuple. The mechanical checker reports:

```text
PASS registers=22 high-level-routes=29 active-writes=12 active-values=17 resets=64 panel-reset=separate-0x150 gce-subsys=SUBSYS_1400XXXX
```

Both patches pass strict `checkpatch.pl` (with the generic new-file ownership
notice ignored because the existing MMSYS maintainer pattern applies). The
MMSYS object builds with `W=1`; MT6797 EVB, X20 development, and Gemini DTBs
build; and focused MMSYS binding and DT schema checks pass.

The complete series reconstructs cleanly from the pinned Linux archive and
builds as `linux-7.1.3-gemini-b2a58d835666`. Its 32-patch set SHA-256 is
`b2a58d835666dc2a3bd5fa4cea4d218f654ced21ac4cc686d3ec457da7faea04`.
The package was exported to the Git-ignored host path
`artifacts/20260712T121409Z/gemini-pda/linux-7.1.3-gemini-b2a58d835666`, where
every `SHA256SUMS` entry verifies. The Image is
`bcfb473f96f58ea7a77eef783fd4bce4927374f0b715dcdffa78d2760dade33c`,
the Gemini DTB is
`2b2e2904f8d3fcbc45842245315be0749ea0b43aa3a542848fcf3a2a234e4c44`,
and the packaged configuration is
`0f98f03129508907261efaa6f1b195799313530628505e319d48427105ac385f`.

## Follow-up

Recover and attach DRM component drivers one at a time, beginning with the
retained active path. Do not add MMSYS mailbox channels until the consuming
DRM path's GCE thread and priority are independently verified. Keep SPLIT0 and
dual-DSI as a separate extension rather than inventing a component mapping.
