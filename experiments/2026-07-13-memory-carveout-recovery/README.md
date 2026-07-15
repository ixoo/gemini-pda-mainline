# Experiment: Gemini memory ownership and reserved-region recovery

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-13-memory-carveout-recovery` |
| Status | `completed` for live/vendor comparison; mainline boot remains untested |
| Subsystem | DRAM map, reserved memory, firmware handoff, modem/connectivity/SCP ownership |
| Device variant | Gemini PDA running Gemian; exact retail sub-variant is not independently established |
| Date(s) | 2026-07-13 |
| Investigator(s) | Repository maintainer with Codex assistance |
| Tracking issue | None |

## Question or hypothesis

Does the running device's memory map match the reservations represented by the
local Gemini Linux 7.1.3 DT, and which regions must remain protected before
mainline boot or multimedia/firmware drivers are enabled?

## Provenance and safety

- Live kernel: Linux `3.18.41+`, AArch64, Gemian Debian 9 userspace.
- Live capture: `artifacts/device-inventory/20260713-live/memory-map.txt`
  (Git-ignored and access-restricted).
- A second owner-authorized read-only capture was taken on the same device and
  is normalized in [`results/live-memory-repeat-20260713.txt`](results/live-memory-repeat-20260713.txt).
- A fresh sanitized identity/device-tree/kernel handoff refresh was collected
  on 2026-07-14 under the ignored
  `artifacts/device-inventory/20260714T-handoff-refresh/` directory and
  normalized in [`results/live-handoff-refresh-20260714.txt`](results/live-handoff-refresh-20260714.txt).
- Vendor source: Planet MT6797 tree commit
  `c5b0be85017ad0c599725e8273842efdbecdd88a`.
- Mainline comparison: Linux `7.1.3` and the local patch series.

The capture reads `/proc/meminfo`, the flattened device-tree
`reserved-memory` properties, and `/proc/iomem`. It does not read block
contents, firmware payloads, NVRAM, or arbitrary physical memory, and it makes
no reservation or boot-image changes. `/proc/iomem` was read through an
owner-authorized sudo session; the password is not recorded.

## Procedure

The repeatable collector is
[`collect-live-memory-map.sh`](scripts/collect-live-memory-map.sh). It uses
`sudo -n` for `/proc/iomem` and reports a permission gate instead of prompting.
For this capture, the same read-only `/proc/iomem` command was run through an
interactive owner-authorized sudo session because the device's `sudo -n` path
requested a password.

The source comparison runs in the development VM:

```sh
./scripts/dev-vm run bash -lc \
  experiments/2026-07-13-memory-carveout-recovery/scripts/analyze-memory-contract.sh
```

The fixed-range follow-up is a local, read-only parser over the sanitized live
range list and the board patches:

```sh
python3 experiments/2026-07-13-memory-carveout-recovery/scripts/audit-memory-ranges.py
```

## Observations

- `/proc/meminfo` reports `MemTotal=3860680 kB` (~3.68 GiB), with no swap in
  use in this capture. `/proc/iomem` exposes discontiguous System RAM from
  `0x40000000` through `0x13fffffff`, with holes at firmware and device-owned
  regions; it is not equivalent to a contiguous EVB memory declaration.
- Fixed vendor reservations are present for ram console `0x44400000/0x10000`,
  pstore `0x44410000/0xe0000`, minidump `0x444f0000/0x10000`, ATF
  `0x44600000/0x10000`, ATF ramdump `0x44610000/0x30000`, cache dump
  `0x44640000/0x30000`, preloader `0x44800000/0x100000`, and LK
  `0x46000000/0x400000`.
- Firmware/display/modem reservations are framebuffer `0x7dfb0000/0x1f90000`,
  ATF log `0x7ff40000/0x40000`, log-store `0x7ff80000/0x80000`, CCCI regions
  `0x88000000/0x6000000`, `0xb4000000/0xa000000`, and `0xbe000000/0xc00000`,
  SCP share (dynamic, 16 MiB), connectivity (dynamic, 2 MiB, no-map), and SCP
  `0xbfdf0000/0x200000`.
- Dynamic nodes also include `spm-reserve-memory` (size `0x16000`, no-map),
  two 4 KiB dummy-read reservations, and a dynamic `consys-reserve-memory`
  with size/alignment `0x200000` and no fixed `reg` address in the live FDT.
- The 2026-07-14 handoff refresh shows LK-injected bootargs
  `maxcpus=5`, `console=ttyMT0,921600n1`, and `printk.disable_uart=1`; only
  CPUs 0–1 are online in that live snapshot. This is a loader policy
  observation, not a mainline CPU failure. The current mainline candidate's
  header command line uses `ttyS0` and has no `maxcpus`; only a final
  post-LK `/chosen` capture can determine which policy reaches Linux.
- The repeat capture reproduced every fixed range and all five dynamic nodes,
  but sysfs still exposed sizes rather than allocated addresses for the
  dynamic nodes. This confirms the unresolved boundary is bootloader placement
  and handoff ownership, not a one-off missing node in the first capture.
- The local patch 0020 preserves the fixed pre-LK firmware regions and the
  vendor's five size/alignment-based CCCI, CONSYS, SCP-share, and SPM
  reservations. It deliberately does not snapshot the post-LK `mblock-*`
  addresses observed in one live handoff.
- Linux 7.1.3's generic `mt6797-evb.dts` declares a contiguous
  `0x40000000`/`0x1e800000` memory range and no Gemini firmware reservations.
  It must not be used as the Gemini memory model.

## Analysis

The live FDT is the strongest evidence for the retained vendor boot chain, but
dynamic reserved-memory addresses are allocated by firmware and may change
between boots or variants. A fixed address copied from one capture can protect
the wrong region; omitting a dynamic reservation can allow Linux or a DMA
consumer to overwrite firmware-owned memory. Conversely, moving a region in a
mainline DT without coordinating LK/ATF/CONSYS ownership can make firmware
access stale memory.

The safe initial board description must not use the generic EVB's smaller
contiguous range without firmware reservations. The current candidate uses a
4 GiB physical window plus explicit fixed pre-LK holes and dynamic
consys/SCP-share/SPM reservations; this is a provisional handoff model, not
proof that all RAM is usable. Dynamic reservations should remain represented as
size/alignment or be retained from the bootloader-provided FDT; their final
placement contract must be resolved before enabling connectivity, modem, SCP,
or camera/display DMA users. The `mblock-1-log-store` node is an additional
warning: it lacks `no-map` in the live FDT but is still a named firmware log
region and should not be treated as disposable RAM until its owner is known.

## Conclusion

`confirmed` for the live memory extents and reserved-node inventory. The
mainline boot boundary is not yet proven: the local board DT is conservative
but incomplete for dynamic reservations, and no mainline boot or memory-stress
test has occurred. Keep RAM and all firmware/shared-memory consumers out of
runtime support claims.

## Follow-up

- Capture two owner-authorized boots and compare dynamic reservation placement
  before choosing fixed versus dynamic DT representation. The current repeat
  capture is not a second boot and must not be treated as that evidence.
- Verify the final post-LK FDT after a mainline boot. The retained LK source
  audit shows that it rewrites `/memory`, `/chosen`, model/CPU metadata, and
  appends runtime mblock reservations; its pre-Linux conflict check rejects
  overlapping static `reg` nodes.
- Capture the final post-LK bootargs and online CPU list alongside the UART
  log; do not infer them from the Android header or input DT alone.
- The focused [LK FDT fixup audit](../2026-07-13-lk-fdt-fixup-recovery/README.md)
  confirms no static post-LK mblock overlap in the rebuilt candidate.
- Do not enable modem, CONSYS, SCP, framebuffer, M4U, camera, or display DMA
  consumers until the reserved-memory ownership map is resolved.
