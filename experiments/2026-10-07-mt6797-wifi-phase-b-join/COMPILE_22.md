# Phase C compile 22: proposal 0160, the target's protected group data discarded before the group key

Status: validated compile-only; no candidate composed, no device test.

- Repository input: `6a3b000de5c28094de1dcae83dc2de6dede07a76`, clean, the revision accepted in review.
- Profile: `mt6797-a53-wifi-phase-b-compile`, 659 patches: the compile-21
  selection plus proposal 0160 after 0159, in canonical order; patchset
  `32ff74fa…`, source `be41c068…` unchanged; the package provenance series
  equals the selected series.
- Builder: Buildbox-1, 32 jobs, one heavy build through the managed backend
  after the existing-job, clean-input, capacity, lock and free-space checks;
  generated `2026-10-10T12:17:19Z`.
- Job: `6a3b000de5c28094de1dcae83dc2de6dede07a76-mt6797-a53-wifi-phase-b-compile-m0`.
- Validated package inventory SHA-256: `096b50b5840e7666dc34079d6a47661204e7f41caa7a74befdb960aaabe66192`.
- Release: `7.1.3-gemini-a53-wifi-phase-b-compile`.
- `kernel.config` SHA-256: `975f8703…`, identical to compiles 19 to 21.
- `Image.gz` SHA-256: `13dbdeb6a269d3e1ac921df39a3c28a36a329ba8699f283cd22895d3b1993437`
  (decompressed 15960072 bytes, the same as compiles 19 to 21).

The board DT is unchanged (123 DTBs, checksums passed at validation).
Warnings against the documented baseline: exactly the same two pre-existing
non-driver lines (the trailing-whitespace note while applying v7.1.3 patch
0261 and the unused-function warning in `kernel/cpu.c`); zero MT6797 driver
warnings.

## Candidate 17 composition

The owner composes candidate 17 privately with the reviewed composer at the
pushed head: this package with candidate 16's RAM root, release gate, Phase
C1 helper `bc499f28…` and supplicant `0487b710…` unchanged (63 members,
initramfs `449832a3…`), the same board DT `25ab60f4…` and the same kernel
configuration `975f8703…`; only the kernel image, boot image and padded
partition change. The candidate-17 receipt then binds deployment 17 (over the
installed candidate 16, full padded boot2 `c773902c…`) and runtime 18 with
fresh `capture-18` and `session-18`; those bindings wait for the receipt.
