# Phase C compile 24: proposal 0162, the firmware's add-key-done event admitted once

Status: validated compile-only; no candidate composed, no device test.

- Repository input: `4be81db83258790a107a7d47f01f8402e23b685e`, clean, the revision accepted in review.
- Profile: `mt6797-a53-wifi-phase-b-compile`, 661 selected patches (the validated
  provenance count): the compile-23 selection plus proposal 0162 after 0161, in
  canonical order; patchset `90a752b9…`, source `be41c068…` unchanged; the
  package provenance series equals the selected series.
- Builder: Buildbox-1, 32 jobs, one heavy build through the managed backend
  after the existing-job, clean-input, capacity, lock and free-space checks;
  generated `2026-10-10T13:31:36Z`.
- Job: `4be81db83258790a107a7d47f01f8402e23b685e-mt6797-a53-wifi-phase-b-compile-m0`
  (record and log under the managed `jobs/` directory on Buildbox-1; job log
  SHA-256 `c54b8344…`).
- Validated package inventory SHA-256: `295e881b1e7b851675f7f80a2c255e60896395b898ba6ced6f036d5bf09a6461`.
- Release: `7.1.3-gemini-a53-wifi-phase-b-compile`.
- `kernel.config` SHA-256: `975f8703…`, identical to compiles 19 to 23.
- `Image.gz` SHA-256: `7b3a1dadaaf2082c79c9c010c7791809a3a18c9604406ad312d927aef0370918`
  (decompressed 15960072 bytes, the same as compiles 19 to 23).

The board DT is unchanged (123 DTBs, checksums passed at validation).
Warnings against the documented baseline: exactly the same two pre-existing
non-driver lines (the trailing-whitespace note while applying v7.1.3 patch
0261 and the unused-function warning in `kernel/cpu.c`); zero MT6797 driver
warnings.

## Candidate 19 composition

The owner composes candidate 19 privately with the reviewed composer at the
pushed head: this package with candidate 18's RAM root, release gate, Phase
C1 helper `bc499f28…` and supplicant `0487b710…` unchanged (63 members,
initramfs `449832a3…`), the same board DT `25ab60f4…` and the same kernel
configuration `975f8703…`; only the kernel image, boot image and padded
partition change. The candidate-19 receipt then binds deployment 19 (over the
installed candidate 18, full padded boot2 `dfdf6bcb…`) and runtime 20 with
fresh `capture-20` and `session-20`; those bindings wait for the receipt.
