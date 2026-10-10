# Phase C compile 20: proposal 0158, the EAPOL BSSID tag bound to the measured intervals

Status: validated compile-only; no candidate composed, no device test.

- Repository input: `67a37ca130885e76c18a3b8c89969beacfaa99f9`, clean, the revision accepted in review.
- Profile: `mt6797-a53-wifi-phase-b-compile`, 657 patches: the compile-19
  selection plus proposal 0158 after 0157, in canonical order; patchset
  `c27bcf6a…`, source `be41c068…` unchanged; the package provenance series
  equals the selected series.
- Builder: Buildbox-1, 32 jobs, one heavy build through the managed backend
  after the existing-job, capacity, lock and free-space checks; generated
  `2026-10-10T02:24:49Z`.
- Job: `67a37ca130885e76c18a3b8c89969beacfaa99f9-mt6797-a53-wifi-phase-b-compile-m0`.
- Validated package inventory SHA-256: `ee32128de75a20ab64da1ebd82d25e7b88ea41e826fb6a875bce471025a7df9e`.
- Release: `7.1.3-gemini-a53-wifi-phase-b-compile`.
- `kernel.config` SHA-256: `975f8703…`, identical to compile 19 (no configuration change).
- `Image.gz` SHA-256: `6aba6108dc4fbff0c10cd417ab60e9e22fc39592dd000b17890db4ff98f406b8`
  (decompressed 15960072 bytes, the same as compile 19).

The board DT is unchanged (123 DTBs, checksums passed at validation).
Warnings against the documented baseline: exactly the same two pre-existing
non-driver lines as compiles 12 to 18 (the trailing-whitespace note while
applying v7.1.3 patch 0261, present again because this job prepared the
source tree afresh, and the unused-function warning in `kernel/cpu.c`); zero
MT6797 driver warnings.

## Candidate 15 composition

The owner composes candidate 15 privately with the reviewed composer at the
pushed head: this package with candidate 14's RAM root, release gate, Phase
C1 helper `bc499f28…` and supplicant `0487b710…` unchanged (63 members,
initramfs `449832a3…`), the same board DT `25ab60f4…` and the same kernel
configuration `975f8703…`; only the kernel image, boot image and padded
partition change. The candidate-15 receipt then binds deployment 15 (over the
installed candidate 14, full padded boot2 `911e3d67…`) and runtime 16 with
fresh `capture-16` and `session-16`.
