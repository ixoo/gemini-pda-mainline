# Experiment: retained LK FDT fixup and reservation contract

## Question

Does the retained Planet Gemini LK accept the mainline board DT as an initial
description, or does it rewrite the DT in a way that makes static snapshots of
runtime firmware allocations unsafe?

## Evidence and method

The audit uses the public Android 8 LK source at
`$HOME/src/reference/dguidipc-gemini-lk-android8`, the locally retained vendor
boot image, and the DTB produced by the current patch series. It reads source
text and decodes the candidate DTB only; it does not boot, flash, or write the
device. The repeatable check is
`scripts/audit-lk-fdt-fixup.sh`, normally run inside the development VM.

## Findings

- `CFG_DTB_EARLY_LOADER_SUPPORT` causes LK to load the appended kernel DTB into
  `tags_addr` before the normal Linux handoff.
- LK then rewrites the model, CPU nodes, `/memory`, `/chosen`, Android firmware
  metadata, and other handoff properties. The board DT is therefore an input
  contract, not the final Linux DT.
- With `MBLOCK_LIB_SUPPORT=2`, LK runs `mblock_sanity_check()` before calling
  `mblock_reserved_append()`. Existing `/reserved-memory` `reg` entries are
  compared against runtime mblock entries, and any overlap enters an infinite
  failure loop. Exact duplicate static entries are not harmless.
- The shipping pre-LK DT declares the CCCI, CONSYS, SCP-share, and SPM ranges
  as size/alignment/alloc-range reservations. The mainline board DT preserves
  those dynamic declarations and the fixed pre-LK firmware regions.
- The post-LK `mblock-*` ranges observed on the running device are deliberately
  not copied into the initial board DT. Their placement belongs to LK's runtime
  mblock handoff and is not stable evidence for a static board reservation.

## Result

The corrected candidate has no static `reg` entries at the known post-LK
mblock addresses and retains the five pre-LK dynamic reservation contracts.
This removes a concrete pre-Linux overlap hazard. Mainline boot and hardware
validation remain unattempted.

See [`results/lk-fdt-fixup-audit-20260713.txt`](results/lk-fdt-fixup-audit-20260713.txt)
for the exact source/package hashes and checks.

## Follow-up

- Capture a successful LK-to-mainline boot and the final `/reserved-memory`
  tree, then compare it with the dynamic allocation contract.
- Only add a fixed post-LK reservation if repeated boots and LK source/runtime
  evidence prove that its address is stable and that LK does not reject it.
- Keep modem, CONSYS, SCP, framebuffer, and other DMA users disabled until
  ownership and final-address handoff are tested.
