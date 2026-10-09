# Phase C compile 16: proposal 0152, BSSID tag 15 admitted before the BSS command completes

Status: validated compile-only; no candidate composed, no device test.

- Repository input: `707e2d716188076e2952354ae88965a17b739481`, clean, the revision accepted in review.
- Profile: `mt6797-a53-wifi-phase-b-compile`, 651 patches: the compile-15
  selection plus proposal 0152 after 0151, in canonical order; the package
  provenance series equals the selected series.
- Builder: Buildbox-1, 32 jobs, one heavy build through the managed backend
  after capacity, lock and free-space checks; generated `2026-10-09T20:20:49Z`.
- Job: `707e2d716188076e2952354ae88965a17b739481-mt6797-a53-wifi-phase-b-compile-m0`.
- Validated package inventory SHA-256: `642165d43bec41f07618436006426dc4bcb138914912b3426feb41f57c0d50ed`.
- Release: `7.1.3-gemini-a53-wifi-phase-b-compile`.
- Managed job log SHA-256: `a08a3e800ad115c04707c776108880c2fff8adc1d7bc8e73b6bc57c2e262a434`.
- `Image.gz` SHA-256: `1541bc8762bfd9c70a909099f07d4e72adf50687e42d52fc5a7ad4e837dbeb4c`.

`kernel.config` (`153ea2d0…`) and the board DT (`07b097d5…`) are
byte-identical to compiles 7 to 15; only the image differs. All 805 package
checksums pass after fetch (805 entries, 805 files, one more than compile 15
for the new patch in the provenance); proposal 0152 in the provenance is
identical to the repository's patch at this input. Warnings against the
documented baseline: exactly the same two pre-existing non-driver lines as
compiles 12 to 15 (the trailing-whitespace note while applying v7.1.3 patch
0261 and the unused-function warning in `kernel/cpu.c`), and zero MT6797
driver warnings.

Candidate 11 pairs this package with candidate 10's RAM root unchanged; see
the [runtime 12 bindings](README.md#runtime-12-bindings-2026-10-09).
