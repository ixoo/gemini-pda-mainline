# Phase C compile 23: proposal 0161, the target's directed clear Action frame discarded while active

Status: validated compile-only; no candidate composed, no device test.

- Repository input: `f5477df6b79a2885e64a8002fd2aac30ca735f68`, clean, the revision accepted in review.
- Profile: `mt6797-a53-wifi-phase-b-compile`, 660 selected patches (the validated
  provenance count): the compile-22 selection plus proposal 0161 after 0160, in
  canonical order; patchset `64c12979…`, source `be41c068…` unchanged; the
  package provenance series equals the selected series.
- Builder: Buildbox-1, 32 jobs, one heavy build through the managed backend
  after the existing-job, clean-input, capacity, lock and free-space checks;
  generated `2026-10-10T12:51:15Z`.
- Job: `f5477df6b79a2885e64a8002fd2aac30ca735f68-mt6797-a53-wifi-phase-b-compile-m0`
  (record and log under the managed `jobs/` directory on Buildbox-1; job log
  SHA-256 `ed3167a7…`).
- Validated package inventory SHA-256: `4f07d57195b784f2b7ac713fd8ff1ec8ef5213a105972c30b5270cb7b1d5ec85`.
- Release: `7.1.3-gemini-a53-wifi-phase-b-compile`.
- `kernel.config` SHA-256: `975f8703…`, identical to compiles 19 to 22.
- `Image.gz` SHA-256: `104cec2ab0f8d7fdd2395dfa2ac60b34fd909d1ef63141bff3b92fb20d925d15`
  (decompressed 15960072 bytes, the same as compiles 19 to 22).

The board DT is unchanged (123 DTBs, checksums passed at validation).
Warnings against the documented baseline: exactly the same two pre-existing
non-driver lines (the trailing-whitespace note while applying v7.1.3 patch
0261 and the unused-function warning in `kernel/cpu.c`); zero MT6797 driver
warnings.

## Candidate 18 composition

The owner composes candidate 18 privately with the reviewed composer at the
pushed head: this package with candidate 17's RAM root, release gate, Phase
C1 helper `bc499f28…` and supplicant `0487b710…` unchanged (63 members,
initramfs `449832a3…`), the same board DT `25ab60f4…` and the same kernel
configuration `975f8703…`; only the kernel image, boot image and padded
partition change. The candidate-18 receipt then binds deployment 18 (over the
installed candidate 17, full padded boot2 `5135b2f8…`) and runtime 19 with
fresh `capture-19` and `session-19`; those bindings wait for the receipt.
