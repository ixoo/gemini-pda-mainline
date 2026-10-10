# Phase C compile 21: proposal 0159, refused software frames and refused key commands named

Status: validated compile-only, diagnostic build; no candidate composed, no device test.

- Repository input: `4983499ee0115c66d82011a216dac9e17660b83c`, clean, the revision accepted in review.
- Profile: `mt6797-a53-wifi-phase-b-compile`, 658 patches: the compile-20
  selection plus proposal 0159 after 0158, in canonical order; patchset
  `f694d79a…`, source `be41c068…` unchanged; the package provenance series
  equals the selected series.
- Builder: Buildbox-1, 32 jobs, one heavy build through the managed backend
  after the existing-job, capacity, lock and free-space checks; generated
  `2026-10-10T11:33:45Z`.
- Job: `4983499ee0115c66d82011a216dac9e17660b83c-mt6797-a53-wifi-phase-b-compile-m0`.
- Validated package inventory SHA-256: `f429ebe96d8a2297fa488b11af71bf895dd8efc7665691992276f2a5fa6227f5`.
- Release: `7.1.3-gemini-a53-wifi-phase-b-compile`.
- `kernel.config` SHA-256: `975f8703…`, identical to compiles 19 and 20.
- `Image.gz` SHA-256: `4429011bff6f0dc771a70ce99636cb30fe46d2fd0580e1aa877801afb8811b20`
  (decompressed 15960072 bytes, the same as compiles 19 and 20).

The board DT is unchanged (123 DTBs, checksums passed at validation).
Warnings against the documented baseline: exactly the same two pre-existing
non-driver lines (the trailing-whitespace note while applying v7.1.3 patch
0261 and the unused-function warning in `kernel/cpu.c`); zero MT6797 driver
warnings. Proposal 0159 changes no receive admission or effect; it names
refused software frames and refused key commands.

## Candidate 16 composition

The owner composes candidate 16 privately with the reviewed composer at the
pushed head: this package with candidate 15's RAM root, release gate, Phase
C1 helper `bc499f28…` and supplicant `0487b710…` unchanged (63 members,
initramfs `449832a3…`), the same board DT `25ab60f4…` and the same kernel
configuration `975f8703…`; only the kernel image, boot image and padded
partition change. The candidate-16 receipt then binds deployment 16 (over the
installed candidate 15, full padded boot2 `eb43ddef…`) and runtime 17 with
fresh `capture-17` and `session-17`, a diagnostic boot that names the frame
runtime 16 refused.
